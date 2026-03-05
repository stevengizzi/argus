"""Tests for the market bars endpoint (Sprint 21a).

Tests GET /api/v1/market/{symbol}/bars endpoint.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app

pytestmark = pytest.mark.asyncio


class TestMarketBarsEndpoint:
    """Tests for GET /market/{symbol}/bars."""

    async def test_returns_valid_ohlcv_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /market/{symbol}/bars returns valid OHLCV data."""
        response = await client.get(
            "/api/v1/market/AAPL/bars",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "1m"
        assert "bars" in data
        assert "count" in data
        assert data["count"] > 0

        # Check first bar has all OHLCV fields
        bar = data["bars"][0]
        assert "timestamp" in bar
        assert "open" in bar
        assert "high" in bar
        assert "low" in bar
        assert "close" in bar
        assert "volume" in bar

        # Verify OHLCV relationships
        assert bar["low"] <= bar["high"]
        assert bar["low"] <= bar["open"] <= bar["high"]
        assert bar["low"] <= bar["close"] <= bar["high"]
        assert bar["volume"] > 0

    async def test_respects_limit_parameter(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /market/{symbol}/bars respects the limit parameter."""
        limit = 50
        response = await client.get(
            f"/api/v1/market/TSLA/bars?limit={limit}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["count"] == limit
        assert len(data["bars"]) == limit

    async def test_deterministic_output_for_same_symbol(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Same symbol always returns same data (deterministic)."""
        # First request
        response1 = await client.get(
            "/api/v1/market/NVDA/bars?limit=10",
            headers=auth_headers,
        )
        # Second request
        response2 = await client.get(
            "/api/v1/market/NVDA/bars?limit=10",
            headers=auth_headers,
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Bars should be identical (same seed = same output)
        assert data1["bars"][0]["open"] == data2["bars"][0]["open"]
        assert data1["bars"][0]["high"] == data2["bars"][0]["high"]
        assert data1["bars"][0]["close"] == data2["bars"][0]["close"]
        assert data1["bars"][0]["volume"] == data2["bars"][0]["volume"]


class TestDifferentSymbols:
    """Tests for different symbols producing different data."""

    async def test_different_symbols_have_different_prices(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Different symbols produce different price ranges."""
        response_aapl = await client.get(
            "/api/v1/market/AAPL/bars?limit=5",
            headers=auth_headers,
        )
        response_tsla = await client.get(
            "/api/v1/market/TSLA/bars?limit=5",
            headers=auth_headers,
        )

        assert response_aapl.status_code == 200
        assert response_tsla.status_code == 200

        data_aapl = response_aapl.json()
        data_tsla = response_tsla.json()

        # Different symbols should have different base prices
        aapl_open = data_aapl["bars"][0]["open"]
        tsla_open = data_tsla["bars"][0]["open"]

        # They are seeded differently, so they should differ
        assert aapl_open != tsla_open


class TestSymbolNormalization:
    """Tests for symbol case normalization."""

    async def test_symbol_is_uppercased(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Symbol is uppercased in response."""
        response = await client.get(
            "/api/v1/market/aapl/bars?limit=5",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["symbol"] == "AAPL"


class TestMaxLimit:
    """Tests for maximum limit enforcement."""

    async def test_limit_capped_at_390(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Limit is capped at 390 (full trading day)."""
        response = await client.get(
            "/api/v1/market/MSFT/bars?limit=1000",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should be capped at 390
        assert data["count"] == 390


class TestUnauthenticated:
    """Tests for unauthenticated access."""

    async def test_returns_401_without_auth(
        self,
        client: AsyncClient,
    ) -> None:
        """GET /market/{symbol}/bars returns 401 without auth."""
        response = await client.get("/api/v1/market/AAPL/bars")

        assert response.status_code == 401


class TestRealDataIntegration:
    """Tests for real data integration (B4 fix).

    These tests verify that the bars endpoint correctly uses real Databento
    data when available, and falls back to synthetic data when not.
    """

    async def test_bars_endpoint_falls_back_to_synthetic_on_error(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns synthetic data when real data fetch fails.

        In dev mode (SimulatedBroker), the endpoint should return synthetic
        data. This test verifies the fallback behavior works correctly.
        """
        response = await client.get(
            "/api/v1/market/AAPL/bars?limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should return synthetic data (dev mode uses SimulatedBroker)
        assert data["symbol"] == "AAPL"
        assert data["count"] == 10
        assert len(data["bars"]) == 10

        # Synthetic data should still have valid OHLCV structure
        bar = data["bars"][0]
        assert bar["low"] <= bar["high"]
        assert bar["volume"] > 0

    async def test_bars_endpoint_accepts_time_parameters(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Bars endpoint accepts start_time and end_time parameters.

        Verifies that the new time parameters for real data queries
        are accepted by the API.
        """
        response = await client.get(
            "/api/v1/market/TSLA/bars?limit=50&start_time=2026-02-20T09:30:00&end_time=2026-02-20T16:00:00",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should return data (synthetic in test mode)
        assert data["symbol"] == "TSLA"
        assert "bars" in data
        assert "count" in data

    async def test_bars_endpoint_returns_real_data_when_data_service_available(
        self,
        app_state: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns real data from DataService when available.

        Mocks DataService with get_historical_candles returning a known
        DataFrame with SOFI prices at ~$15. Verifies bars response has
        prices in the $15 range, not synthetic ~$269.
        """
        # Create mock DataService with get_historical_candles
        mock_data_service = AsyncMock()

        # Create a DataFrame with SOFI prices at ~$15
        timestamps = [
            datetime(2026, 3, 5, 14, 30, 0, tzinfo=UTC),
            datetime(2026, 3, 5, 14, 31, 0, tzinfo=UTC),
            datetime(2026, 3, 5, 14, 32, 0, tzinfo=UTC),
        ]
        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": [15.10, 15.15, 15.20],
            "high": [15.25, 15.30, 15.35],
            "low": [15.05, 15.10, 15.15],
            "close": [15.20, 15.22, 15.28],
            "volume": [100000, 120000, 110000],
        })
        mock_data_service.get_historical_candles = AsyncMock(return_value=df)

        # Inject mock DataService into AppState
        app_state.data_service = mock_data_service

        # Create client with modified app_state
        app = create_app(app_state)
        app.state.app_state = app_state
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/market/SOFI/bars?start_time=2026-03-05T14:30:00&end_time=2026-03-05T15:45:00",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should return real data from mock
        assert data["symbol"] == "SOFI"
        assert data["count"] == 3
        assert len(data["bars"]) == 3

        # Prices should be in the ~$15 range (from our mock), NOT ~$269 (synthetic)
        bar = data["bars"][0]
        assert 14.0 <= bar["open"] <= 16.0, f"Expected ~$15, got {bar['open']}"
        assert 14.0 <= bar["high"] <= 16.0
        assert 14.0 <= bar["low"] <= 16.0
        assert 14.0 <= bar["close"] <= 16.0

        # Verify mock was called
        mock_data_service.get_historical_candles.assert_called_once()

    async def test_bars_endpoint_synthetic_fallback_when_data_service_none(
        self,
        app_state: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Falls back to synthetic data when data_service is None.

        Verifies that when state.data_service is None, the endpoint
        returns deterministic synthetic data.
        """
        # Ensure data_service is None
        app_state.data_service = None

        # Create client with modified app_state
        app = create_app(app_state)
        app.state.app_state = app_state
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/market/SOFI/bars?limit=10",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should return synthetic data
        assert data["symbol"] == "SOFI"
        assert data["count"] == 10
        assert len(data["bars"]) == 10

        # Synthetic SOFI data has base price derived from hash
        # md5("SOFI")[:8] = "d3f5e3a2" -> int value % 490 + 10 ≈ 269
        bar = data["bars"][0]
        assert bar["open"] > 100, f"Expected synthetic price >$100, got {bar['open']}"
        assert bar["volume"] > 0
