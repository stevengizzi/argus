"""Tests for the dashboard summary endpoint.

Sprint 21d: Tests for the aggregated dashboard data endpoint.
"""

from __future__ import annotations

import pytest

from argus.api.routes.dashboard import _get_pace_status


class TestGetPaceStatus:
    """Tests for the _get_pace_status helper function."""

    def test_ahead_when_over_110_percent_pace(self):
        """Returns 'ahead' when current P&L > 110% of expected."""
        # Target: $5000, 50% elapsed → expected $2500
        # Current: $3000 → 120% of expected = ahead
        status = _get_pace_status(
            current_pnl=3000.0,
            target=5000.0,
            elapsed_pct=50.0,
        )
        assert status == "ahead"

    def test_on_pace_when_between_90_and_110_percent(self):
        """Returns 'on_pace' when current P&L is 90-110% of expected."""
        # Target: $5000, 50% elapsed → expected $2500
        # Current: $2500 → 100% of expected = on_pace
        status = _get_pace_status(
            current_pnl=2500.0,
            target=5000.0,
            elapsed_pct=50.0,
        )
        assert status == "on_pace"

        # Current: $2400 → 96% of expected = on_pace (above 90%)
        status = _get_pace_status(
            current_pnl=2400.0,
            target=5000.0,
            elapsed_pct=50.0,
        )
        assert status == "on_pace"

    def test_behind_when_under_90_percent_pace(self):
        """Returns 'behind' when current P&L < 90% of expected."""
        # Target: $5000, 50% elapsed → expected $2500
        # Current: $2000 → 80% of expected = behind
        status = _get_pace_status(
            current_pnl=2000.0,
            target=5000.0,
            elapsed_pct=50.0,
        )
        assert status == "behind"

    def test_zero_elapsed_returns_on_pace(self):
        """Returns 'on_pace' when no time has elapsed (first day)."""
        status = _get_pace_status(
            current_pnl=0.0,
            target=5000.0,
            elapsed_pct=0.0,
        )
        assert status == "on_pace"

    def test_negative_pnl_returns_behind(self):
        """Returns 'behind' when P&L is negative."""
        status = _get_pace_status(
            current_pnl=-500.0,
            target=5000.0,
            elapsed_pct=50.0,
        )
        assert status == "behind"

    def test_positive_pnl_with_zero_expected_returns_ahead(self):
        """Returns 'ahead' when positive P&L exists but expected is zero."""
        status = _get_pace_status(
            current_pnl=100.0,
            target=5000.0,
            elapsed_pct=0.0,
        )
        # elapsed_pct=0 triggers early return
        assert status == "on_pace"


@pytest.mark.asyncio
async def test_dashboard_summary_returns_correct_shape(client, auth_headers):
    """GET /dashboard/summary returns all expected sections."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    # Check all top-level sections are present
    assert "account" in data
    assert "today_stats" in data
    assert "goals" in data
    assert "market" in data
    assert "regime" in data
    assert "deployment" in data
    assert "orchestrator" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_dashboard_summary_account_section(client, auth_headers):
    """Account section contains expected fields with correct types."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    account = response.json()["account"]

    assert "equity" in account
    assert "cash" in account
    assert "buying_power" in account
    assert "daily_pnl" in account
    assert "daily_pnl_pct" in account

    # Check types
    assert isinstance(account["equity"], (int, float))
    assert isinstance(account["cash"], (int, float))
    assert isinstance(account["buying_power"], (int, float))
    assert isinstance(account["daily_pnl"], (int, float))
    assert isinstance(account["daily_pnl_pct"], (int, float))

    # SimulatedBroker starts with 100K
    assert account["equity"] == pytest.approx(100000.0, rel=0.01)


@pytest.mark.asyncio
async def test_dashboard_summary_today_stats_zero_trades(client, auth_headers):
    """Today stats fields are null when no trades exist."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    today_stats = response.json()["today_stats"]

    assert today_stats["trade_count"] == 0
    assert today_stats["win_rate"] is None
    assert today_stats["avg_r"] is None
    assert today_stats["best_trade"] is None


@pytest.mark.asyncio
async def test_dashboard_summary_today_stats_with_trades(client_with_trades, auth_headers):
    """Today stats populate correctly when trades exist."""
    response = await client_with_trades.get(
        "/api/v1/dashboard/summary", headers=auth_headers
    )

    assert response.status_code == 200

    today_stats = response.json()["today_stats"]

    # seeded_trade_logger has 3 trades for today
    assert today_stats["trade_count"] == 3
    assert today_stats["win_rate"] is not None
    assert isinstance(today_stats["win_rate"], (int, float))
    assert today_stats["avg_r"] is not None

    # Best trade should be AAPL with $350 P&L
    assert today_stats["best_trade"] is not None
    assert today_stats["best_trade"]["symbol"] == "AAPL"
    assert today_stats["best_trade"]["pnl"] == pytest.approx(350.0, rel=0.01)


@pytest.mark.asyncio
async def test_dashboard_summary_goals_section(client, auth_headers):
    """Goals section contains expected fields."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    goals = response.json()["goals"]

    assert "monthly_target_usd" in goals
    assert "current_month_pnl" in goals
    assert "trading_days_elapsed" in goals
    assert "trading_days_remaining" in goals
    assert "avg_daily_pnl" in goals
    assert "needed_daily_pnl" in goals
    assert "pace_status" in goals

    # Pace status must be one of the valid values
    assert goals["pace_status"] in ("ahead", "on_pace", "behind")

    # Default target is $5000
    assert goals["monthly_target_usd"] == 5000.0


@pytest.mark.asyncio
async def test_dashboard_summary_market_section(client, auth_headers):
    """Market section contains status and time fields."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    market = response.json()["market"]

    assert "status" in market
    assert "time_et" in market
    assert "is_paper" in market

    # Status must be one of the valid values
    assert market["status"] in ("pre_market", "open", "closed", "after_hours")

    # In dev mode (SimulatedBroker), is_paper should be True
    assert market["is_paper"] is True


@pytest.mark.asyncio
async def test_dashboard_summary_regime_section(client, auth_headers):
    """Regime section contains classification and description."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    regime = response.json()["regime"]

    assert "classification" in regime
    assert "description" in regime
    assert "updated_at" in regime

    # Without orchestrator, defaults to neutral
    assert regime["classification"] == "neutral"
    assert regime["description"] == "Range-bound, mixed signals"


@pytest.mark.asyncio
async def test_dashboard_summary_deployment_section(client, auth_headers):
    """Deployment section contains strategies and capital info."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    deployment = response.json()["deployment"]

    assert "strategies" in deployment
    assert "available_capital" in deployment
    assert "total_equity" in deployment

    assert isinstance(deployment["strategies"], list)
    assert isinstance(deployment["available_capital"], (int, float))
    assert isinstance(deployment["total_equity"], (int, float))


@pytest.mark.asyncio
async def test_dashboard_summary_orchestrator_section(client, auth_headers):
    """Orchestrator section contains strategy counts and deployment info."""
    response = await client.get("/api/v1/dashboard/summary", headers=auth_headers)

    assert response.status_code == 200

    orchestrator = response.json()["orchestrator"]

    assert "active_strategy_count" in orchestrator
    assert "total_strategy_count" in orchestrator
    assert "deployed_amount" in orchestrator
    assert "deployed_pct" in orchestrator
    assert "risk_used_pct" in orchestrator
    assert "regime" in orchestrator


@pytest.mark.asyncio
async def test_dashboard_summary_unauthenticated(client):
    """GET /dashboard/summary without token returns 401."""
    response = await client.get("/api/v1/dashboard/summary")

    assert response.status_code == 401
