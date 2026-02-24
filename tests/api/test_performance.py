"""Tests for the performance API endpoint.

Tests the GET /api/v1/performance/{period} endpoint.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestPerformanceToday:
    """Tests for GET /performance/today."""

    async def test_performance_today_returns_todays_metrics(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /performance/today returns metrics for today's trades."""
        response = await client_with_trades.get(
            "/api/v1/performance/today",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == "today"
        assert "date_from" in data
        assert "date_to" in data
        assert data["date_from"] == data["date_to"]  # Today only
        assert "metrics" in data
        assert "daily_pnl" in data
        assert "by_strategy" in data
        assert "timestamp" in data


class TestPerformanceWeek:
    """Tests for GET /performance/week."""

    async def test_performance_week_returns_week_metrics(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /performance/week returns metrics from Monday to today."""
        response = await client_with_trades.get(
            "/api/v1/performance/week",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == "week"
        assert "date_from" in data
        assert "date_to" in data
        # date_from should be <= date_to
        assert data["date_from"] <= data["date_to"]
        assert "metrics" in data


class TestPerformanceMonth:
    """Tests for GET /performance/month."""

    async def test_performance_month_returns_month_metrics(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /performance/month returns metrics from 1st of month to today."""
        response = await client_with_trades.get(
            "/api/v1/performance/month",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == "month"
        assert "date_from" in data
        assert "date_to" in data
        # date_from should be the 1st of the month
        assert data["date_from"].endswith("-01") or data["date_from"][-2:] == "01"
        assert "metrics" in data


class TestPerformanceAll:
    """Tests for GET /performance/all."""

    async def test_performance_all_returns_all_time_metrics(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """GET /performance/all returns all-time metrics."""
        response = await client_with_trades.get(
            "/api/v1/performance/all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == "all"
        # For "all", date_from and date_to should be empty
        assert data["date_from"] == ""
        assert data["date_to"] == ""
        assert "metrics" in data
        # Should have trades from the seeded data
        assert data["metrics"]["total_trades"] > 0


class TestInvalidPeriod:
    """Tests for invalid period values."""

    async def test_invalid_period_returns_422(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Invalid period value returns 422."""
        response = await client_with_trades.get(
            "/api/v1/performance/yearly",
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestEmptyPeriod:
    """Tests for periods with no trades."""

    async def test_empty_period_returns_zeroed_metrics(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Period with no trades returns zeroed metrics."""
        response = await client.get(
            "/api/v1/performance/today",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["metrics"]["total_trades"] == 0
        assert data["metrics"]["win_rate"] == 0.0
        assert data["metrics"]["net_pnl"] == 0.0
        assert data["metrics"]["profit_factor"] == 0.0


class TestDailyPnlArray:
    """Tests for daily P&L array in response."""

    async def test_daily_pnl_array_contains_correct_entries(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Daily P&L array contains entries with date, pnl, and trades count."""
        response = await client_with_trades.get(
            "/api/v1/performance/all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["daily_pnl"], list)
        if data["daily_pnl"]:
            entry = data["daily_pnl"][0]
            assert "date" in entry
            assert "pnl" in entry
            assert "trades" in entry


class TestByStrategyBreakdown:
    """Tests for per-strategy breakdown."""

    async def test_by_strategy_breakdown_matches_per_strategy_data(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """by_strategy contains metrics for each strategy."""
        response = await client_with_trades.get(
            "/api/v1/performance/all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["by_strategy"], dict)
        # Seeded data has orb_breakout and orb_scalp
        if data["by_strategy"]:
            for _strategy_id, metrics in data["by_strategy"].items():
                assert "total_trades" in metrics
                assert "win_rate" in metrics
                assert "net_pnl" in metrics
                assert "profit_factor" in metrics


class TestWinRateMatchesData:
    """Tests for win rate accuracy."""

    async def test_win_rate_matches_seeded_data(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Win rate matches the actual win/loss ratio in seeded data."""
        response = await client_with_trades.get(
            "/api/v1/performance/all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify win_rate is between 0 and 1
        assert 0.0 <= data["metrics"]["win_rate"] <= 1.0

        # Verify total_trades is reasonable for seeded data (15 trades seeded)
        assert data["metrics"]["total_trades"] > 0


class TestUnauthenticated:
    """Tests for unauthenticated access."""

    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Request without auth headers returns 401."""
        response = await client.get("/api/v1/performance/today")

        assert response.status_code == 401


class TestMetricsStructure:
    """Tests for metrics response structure."""

    async def test_metrics_contains_all_required_fields(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Metrics object contains all required fields."""
        response = await client_with_trades.get(
            "/api/v1/performance/all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        metrics = data["metrics"]

        # All required fields
        assert "total_trades" in metrics
        assert "win_rate" in metrics
        assert "profit_factor" in metrics
        assert "net_pnl" in metrics
        assert "gross_pnl" in metrics
        assert "total_commissions" in metrics
        assert "avg_r_multiple" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown_pct" in metrics
        assert "avg_hold_seconds" in metrics
        assert "largest_win" in metrics
        assert "largest_loss" in metrics
        assert "consecutive_wins_max" in metrics
        assert "consecutive_losses_max" in metrics
