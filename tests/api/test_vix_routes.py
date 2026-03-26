"""Tests for VIX data REST endpoints.

Sprint 27.9, Session 3a.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app


@pytest.fixture
def mock_vix_service_with_data() -> MagicMock:
    """VIXDataService mock that returns data."""
    service = MagicMock()
    service.is_stale = False
    service.is_ready = True
    service.get_latest_daily.return_value = {
        "data_date": "2026-03-25",
        "date": "2026-03-25",
        "vix_close": 18.5,
        "vol_of_vol_ratio": 1.12,
        "vix_percentile": 0.45,
        "term_structure_proxy": 0.98,
        "realized_vol_20d": 0.15,
        "variance_risk_premium": 117.25,
    }
    service.get_history_range.return_value = [
        {
            "date": "2026-03-20",
            "vix_close": 19.2,
            "vol_of_vol_ratio": 1.05,
            "vix_percentile": 0.50,
            "term_structure_proxy": 1.01,
            "realized_vol_20d": 0.14,
            "variance_risk_premium": 172.64,
        },
        {
            "date": "2026-03-21",
            "vix_close": 18.8,
            "vol_of_vol_ratio": 1.10,
            "vix_percentile": 0.47,
            "term_structure_proxy": 0.99,
            "realized_vol_20d": 0.15,
            "variance_risk_premium": 128.44,
        },
    ]
    return service


@pytest.fixture
def mock_vix_service_empty() -> MagicMock:
    """VIXDataService mock that returns no data."""
    service = MagicMock()
    service.is_stale = True
    service.is_ready = False
    service.get_latest_daily.return_value = None
    service.get_history_range.return_value = None
    return service


@pytest.fixture
async def client_with_vix(
    app_state: AppState,
    jwt_secret: str,
    mock_vix_service_with_data: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with VIXDataService returning data."""
    app_state.vix_data_service = mock_vix_service_with_data
    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def client_with_vix_empty(
    app_state: AppState,
    jwt_secret: str,
    mock_vix_service_empty: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Client with VIXDataService returning no data."""
    app_state.vix_data_service = mock_vix_service_empty
    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_vix_current_returns_data(
    client_with_vix: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/v1/vix/current with data returns expected fields."""
    response = await client_with_vix.get(
        "/api/v1/vix/current", headers=auth_headers
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["vix_close"] == 18.5
    assert body["data_date"] == "2026-03-25"
    assert body["vol_of_vol_ratio"] == 1.12
    assert body["vix_percentile"] == 0.45
    assert body["term_structure_proxy"] == 0.98
    assert body["realized_vol_20d"] == 0.15
    assert body["variance_risk_premium"] == 117.25
    assert body["is_stale"] is False
    assert "regime" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_vix_current_unavailable(
    client_with_vix_empty: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /api/v1/vix/current with no data returns unavailable status."""
    response = await client_with_vix_empty.get(
        "/api/v1/vix/current", headers=auth_headers
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "unavailable"
    assert "message" in body


@pytest.mark.asyncio
async def test_vix_history_date_filter(
    client_with_vix: AsyncClient,
    auth_headers: dict[str, str],
    mock_vix_service_with_data: MagicMock,
) -> None:
    """GET /api/v1/vix/history with date range returns filtered data."""
    response = await client_with_vix.get(
        "/api/v1/vix/history",
        params={"start_date": "2026-03-20", "end_date": "2026-03-21"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["count"] == 2
    assert body["start_date"] == "2026-03-20"
    assert body["end_date"] == "2026-03-21"
    assert len(body["data"]) == 2
    assert body["data"][0]["date"] == "2026-03-20"
    assert body["data"][1]["date"] == "2026-03-21"

    # Verify the service was called with correct date range
    mock_vix_service_with_data.get_history_range.assert_called_once_with(
        "2026-03-20", "2026-03-21"
    )


@pytest.mark.asyncio
async def test_vix_endpoints_require_auth(
    client_with_vix: AsyncClient,
) -> None:
    """VIX endpoints return 401 without JWT."""
    current_resp = await client_with_vix.get("/api/v1/vix/current")
    assert current_resp.status_code == 401

    history_resp = await client_with_vix.get("/api/v1/vix/history")
    assert history_resp.status_code == 401
