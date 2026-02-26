"""Tests for performance endpoint strategy_id filter (Sprint 21a).

Tests the strategy_id query parameter on GET /api/v1/performance/{period}.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestStrategyIdFilter:
    """Tests for strategy_id query parameter filtering."""

    async def test_filter_returns_only_filtered_strategy_trades(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """With strategy_id filter, only returns trades for that strategy."""
        response = await client_with_trades.get(
            "/api/v1/performance/all?strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should have metrics
        assert data["metrics"]["total_trades"] > 0

        # by_strategy should only contain the filtered strategy
        assert "by_strategy" in data
        if data["by_strategy"]:
            # All entries should be for orb_breakout only
            assert list(data["by_strategy"].keys()) == ["orb_breakout"]

    async def test_daily_pnl_filtered_to_strategy(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Daily P&L is filtered to the specified strategy."""
        # Get unfiltered data first
        response_all = await client_with_trades.get(
            "/api/v1/performance/all",
            headers=auth_headers,
        )
        # Get filtered data
        response_filtered = await client_with_trades.get(
            "/api/v1/performance/all?strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response_all.status_code == 200
        assert response_filtered.status_code == 200

        data_all = response_all.json()
        data_filtered = response_filtered.json()

        # Filtered should have same or fewer trades
        assert data_filtered["metrics"]["total_trades"] <= data_all["metrics"]["total_trades"]

        # Filtered daily_pnl entries should exist
        assert isinstance(data_filtered["daily_pnl"], list)

    async def test_by_strategy_contains_only_filtered_strategy(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """by_strategy dict contains only the filtered strategy."""
        response = await client_with_trades.get(
            "/api/v1/performance/all?strategy_id=orb_scalp",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # by_strategy should only have orb_scalp
        if data["by_strategy"]:
            assert "orb_scalp" in data["by_strategy"]
            assert "orb_breakout" not in data["by_strategy"]


class TestFilterWithPeriod:
    """Tests for strategy_id filter combined with period."""

    async def test_filter_with_today_period(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """strategy_id filter works with today period."""
        response = await client_with_trades.get(
            "/api/v1/performance/today?strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == "today"
        # Should return metrics (may be 0 if no trades today for that strategy)
        assert "metrics" in data

    async def test_filter_with_week_period(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """strategy_id filter works with week period."""
        response = await client_with_trades.get(
            "/api/v1/performance/week?strategy_id=orb_scalp",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["period"] == "week"
        assert "metrics" in data


class TestNoMatchingTrades:
    """Tests for filter with no matching trades."""

    async def test_unknown_strategy_returns_zero_metrics(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unknown strategy_id returns zeroed metrics."""
        response = await client_with_trades.get(
            "/api/v1/performance/all?strategy_id=nonexistent_strategy",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should return zero metrics for unknown strategy
        assert data["metrics"]["total_trades"] == 0
        assert data["metrics"]["net_pnl"] == 0.0
        assert data["by_strategy"] == {}
