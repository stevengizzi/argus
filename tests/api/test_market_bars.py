"""Tests for the market bars endpoint (Sprint 21a).

Tests GET /api/v1/market/{symbol}/bars endpoint.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

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
