"""Tests for historical data REST endpoints.

Uses MagicMock to simulate HistoricalQueryService behavior.
No production cache is accessed during tests.

Sprint 31A.5, Session 1.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pandas as pd
import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.data.historical_query_service import ServiceUnavailableError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_service(available: bool = True) -> MagicMock:
    """Create a HistoricalQueryService mock.

    Args:
        available: Whether is_available returns True.

    Returns:
        Configured MagicMock.
    """
    svc = MagicMock()
    svc.is_available = available

    if available:
        svc.get_available_symbols.return_value = ["AAPL", "NVDA", "TSLA"]
        svc.get_cache_health.return_value = {
            "total_symbols": 3,
            "date_range": {"min_date": "2025-01-02", "max_date": "2025-01-31"},
            "total_bars": 240,
            "cache_dir": "data/databento_cache",
            "cache_size_bytes": 1_048_576,
        }
        svc.get_date_coverage.return_value = {
            "min_date": "2025-01-02",
            "max_date": "2025-01-31",
            "bar_count": 100,
        }
        svc.get_symbol_bars.return_value = pd.DataFrame(
            {
                "symbol": ["AAPL"] * 5,
                "ts_event": pd.date_range("2025-01-02 14:30", periods=5, freq="1min", tz="UTC"),
                "date": ["2025-01-02"] * 5,
                "open": [100.0] * 5,
                "high": [101.0] * 5,
                "low": [99.0] * 5,
                "close": [100.5] * 5,
                "volume": [1000] * 5,
            }
        )
        svc.validate_symbol_coverage.return_value = {
            "AAPL": True,
            "UNKN": False,
        }
    else:
        svc.get_available_symbols.side_effect = ServiceUnavailableError("not available")
        svc.get_cache_health.side_effect = ServiceUnavailableError("not available")
        svc.get_symbol_bars.side_effect = ServiceUnavailableError("not available")
        svc.validate_symbol_coverage.side_effect = ServiceUnavailableError("not available")

    return svc


@pytest.fixture
async def client_with_service(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with a live HistoricalQueryService mock."""
    app_state.historical_query_service = _make_mock_service(available=True)
    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def client_no_service(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with historical_query_service set to None (unavailable)."""
    app_state.historical_query_service = None
    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# GET /api/v1/historical/symbols
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_symbols_returns_list(
    client_with_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_with_service.get(
        "/api/v1/historical/symbols", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert "symbols" in body
    assert body["symbols"] == ["AAPL", "NVDA", "TSLA"]
    assert body["count"] == 3


@pytest.mark.asyncio
async def test_get_symbols_returns_503_when_unavailable(
    client_no_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_no_service.get(
        "/api/v1/historical/symbols", headers=auth_headers
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_symbols_requires_auth(
    client_with_service: AsyncClient,
) -> None:
    response = await client_with_service.get("/api/v1/historical/symbols")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/historical/coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_coverage_returns_health_dict(
    client_with_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_with_service.get(
        "/api/v1/historical/coverage", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert "total_symbols" in body
    assert body["total_symbols"] == 3
    assert "cache_size_bytes" in body
    assert "total_bars" in body


@pytest.mark.asyncio
async def test_get_coverage_with_symbol_param(
    client_with_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_with_service.get(
        "/api/v1/historical/coverage?symbol=AAPL", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert "bar_count" in body


@pytest.mark.asyncio
async def test_get_coverage_returns_503_when_unavailable(
    client_no_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_no_service.get(
        "/api/v1/historical/coverage", headers=auth_headers
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_coverage_requires_auth(
    client_with_service: AsyncClient,
) -> None:
    response = await client_with_service.get("/api/v1/historical/coverage")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/historical/bars/{symbol}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_bars_returns_ohlcv(
    client_with_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_with_service.get(
        "/api/v1/historical/bars/AAPL?start_date=2025-01-01&end_date=2025-01-31",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert "bars" in body
    assert body["count"] == 5
    first_bar = body["bars"][0]
    assert "open" in first_bar
    assert "close" in first_bar
    assert "volume" in first_bar


@pytest.mark.asyncio
async def test_get_bars_bad_date_format_returns_400(
    client_with_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_with_service.get(
        "/api/v1/historical/bars/AAPL?start_date=2025/01/01&end_date=2025-01-31",
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_bars_requires_auth(
    client_with_service: AsyncClient,
) -> None:
    response = await client_with_service.get(
        "/api/v1/historical/bars/AAPL?start_date=2025-01-01&end_date=2025-01-31"
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/v1/historical/validate-coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_coverage_returns_per_symbol_results(
    client_with_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_with_service.post(
        "/api/v1/historical/validate-coverage",
        json={
            "symbols": ["AAPL", "UNKN"],
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "min_bars": 100,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert body["results"]["AAPL"] is True
    assert body["results"]["UNKN"] is False


@pytest.mark.asyncio
async def test_validate_coverage_returns_503_when_unavailable(
    client_no_service: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client_no_service.post(
        "/api/v1/historical/validate-coverage",
        json={
            "symbols": ["AAPL"],
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        },
        headers=auth_headers,
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_validate_coverage_requires_auth(
    client_with_service: AsyncClient,
) -> None:
    response = await client_with_service.post(
        "/api/v1/historical/validate-coverage",
        json={"symbols": ["AAPL"], "start_date": "2025-01-01", "end_date": "2025-01-31"},
    )
    assert response.status_code == 401
