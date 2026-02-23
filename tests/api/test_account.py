"""Tests for the account endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from argus.api.routes.account import get_market_status
from argus.core.clock import FixedClock


class TestGetMarketStatus:
    """Tests for the get_market_status helper function."""

    def test_market_open_during_hours(self):
        """Returns 'open' during regular market hours."""
        # 10:30 AM ET on a Monday
        et_tz = ZoneInfo("America/New_York")
        market_time = datetime(2026, 2, 23, 10, 30, 0, tzinfo=et_tz)

        status = get_market_status(market_time)

        assert status == "open"

    def test_pre_market(self):
        """Returns 'pre_market' before 9:30 AM ET."""
        et_tz = ZoneInfo("America/New_York")
        pre_market_time = datetime(2026, 2, 23, 7, 0, 0, tzinfo=et_tz)

        status = get_market_status(pre_market_time)

        assert status == "pre_market"

    def test_after_hours(self):
        """Returns 'after_hours' between 4:00 PM and 8:00 PM ET."""
        et_tz = ZoneInfo("America/New_York")
        after_hours_time = datetime(2026, 2, 23, 17, 0, 0, tzinfo=et_tz)

        status = get_market_status(after_hours_time)

        assert status == "after_hours"

    def test_closed_overnight(self):
        """Returns 'closed' after 8:00 PM ET."""
        et_tz = ZoneInfo("America/New_York")
        closed_time = datetime(2026, 2, 23, 21, 0, 0, tzinfo=et_tz)

        status = get_market_status(closed_time)

        assert status == "closed"

    def test_closed_weekend(self):
        """Returns 'closed' on weekends."""
        et_tz = ZoneInfo("America/New_York")
        # Saturday
        saturday = datetime(2026, 2, 21, 10, 30, 0, tzinfo=et_tz)

        status = get_market_status(saturday)

        assert status == "closed"


@pytest.mark.asyncio
async def test_get_account_success(client, auth_headers):
    """GET /account returns correct shape with broker values."""
    response = await client.get("/api/v1/account", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    # Check all expected fields are present
    assert "equity" in data
    assert "cash" in data
    assert "buying_power" in data
    assert "daily_pnl" in data
    assert "daily_pnl_pct" in data
    assert "open_positions_count" in data
    assert "daily_trades_count" in data
    assert "market_status" in data
    assert "broker_source" in data
    assert "data_source" in data
    assert "timestamp" in data

    # Check types
    assert isinstance(data["equity"], (int, float))
    assert isinstance(data["cash"], (int, float))
    assert isinstance(data["buying_power"], (int, float))
    assert isinstance(data["daily_pnl"], (int, float))
    assert isinstance(data["daily_pnl_pct"], (int, float))
    assert isinstance(data["open_positions_count"], int)
    assert isinstance(data["daily_trades_count"], int)
    assert isinstance(data["market_status"], str)
    assert data["market_status"] in ("pre_market", "open", "closed", "after_hours")


@pytest.mark.asyncio
async def test_account_equity_from_broker(client, auth_headers, test_broker):
    """Equity value comes from broker's get_account()."""
    response = await client.get("/api/v1/account", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # SimulatedBroker starts with 100K
    # In dev mode (SimulatedBroker), small random variation is added for UI testing
    # Accept values within ±1% of 100K
    assert data["equity"] == pytest.approx(100000.0, rel=0.01)


@pytest.mark.asyncio
async def test_account_market_status_during_hours(app_state, jwt_secret):
    """Returns 'open' when clock is during market hours."""
    from httpx import ASGITransport, AsyncClient

    from argus.api.auth import create_access_token
    from argus.api.server import create_app

    # Set clock to market hours (10:30 AM ET Monday)
    et_tz = ZoneInfo("America/New_York")
    market_hours = datetime(2026, 2, 23, 10, 30, 0, tzinfo=et_tz)
    app_state.clock = FixedClock(market_hours.astimezone(UTC))

    app = create_app(app_state)
    app.state.app_state = app_state

    token, _ = create_access_token(jwt_secret)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.get("/api/v1/account", headers=headers)

    assert response.status_code == 200
    assert response.json()["market_status"] == "open"


@pytest.mark.asyncio
async def test_account_market_status_after_hours(app_state, jwt_secret):
    """Returns 'closed' when clock is outside market hours."""
    from httpx import ASGITransport, AsyncClient

    from argus.api.auth import create_access_token
    from argus.api.server import create_app

    # Set clock to after hours (9 PM ET Monday)
    et_tz = ZoneInfo("America/New_York")
    closed_time = datetime(2026, 2, 23, 21, 0, 0, tzinfo=et_tz)
    app_state.clock = FixedClock(closed_time.astimezone(UTC))

    app = create_app(app_state)
    app.state.app_state = app_state

    token, _ = create_access_token(jwt_secret)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.get("/api/v1/account", headers=headers)

    assert response.status_code == 200
    assert response.json()["market_status"] == "closed"


@pytest.mark.asyncio
async def test_account_unauthenticated(client):
    """GET /account without token returns 401."""
    response = await client.get("/api/v1/account")

    assert response.status_code == 401  # No authentication provided
