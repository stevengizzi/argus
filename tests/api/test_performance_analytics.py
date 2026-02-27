"""Tests for the performance analytics endpoints.

Tests the new heatmap, distribution, and correlation endpoints:
- GET /api/v1/performance/heatmap
- GET /api/v1/performance/distribution
- GET /api/v1/performance/correlation

Also tests TradeLogger.get_daily_pnl_by_strategy().
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from argus.analytics.trade_logger import TradeLogger
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.models.trading import ExitReason, OrderSide, Trade

pytestmark = pytest.mark.asyncio


# --- TradeLogger.get_daily_pnl_by_strategy Tests ---


class TestGetDailyPnlByStrategy:
    """Tests for TradeLogger.get_daily_pnl_by_strategy()."""

    async def test_empty_database_returns_empty_list(
        self,
        test_trade_logger: TradeLogger,
    ) -> None:
        """Empty database returns empty list."""
        result = await test_trade_logger.get_daily_pnl_by_strategy()
        assert result == []

    async def test_single_strategy_returns_daily_pnl(
        self,
        test_trade_logger: TradeLogger,
    ) -> None:
        """Single strategy trades are aggregated by date."""
        base_time = datetime(2026, 2, 20, 14, 0, 0, tzinfo=UTC)

        # Add two trades on same day, same strategy
        for i in range(2):
            trade = Trade(
                strategy_id="strat_orb",
                symbol="AAPL",
                side=OrderSide.BUY,
                entry_price=100.0,
                entry_time=base_time + timedelta(hours=i),
                exit_price=105.0,
                exit_time=base_time + timedelta(hours=i, minutes=30),
                shares=10,
                stop_price=95.0,
                target_prices=[105.0],
                exit_reason=ExitReason.TARGET_1,
                gross_pnl=50.0,
                commission=1.0,
            )
            await test_trade_logger.log_trade(trade)

        result = await test_trade_logger.get_daily_pnl_by_strategy()

        assert len(result) == 1
        assert result[0]["date"] == "2026-02-20"
        assert result[0]["strategy_id"] == "strat_orb"
        assert result[0]["pnl"] == 98.0  # 2 * (50 - 1)

    async def test_multi_strategy_returns_separate_rows(
        self,
        test_trade_logger: TradeLogger,
    ) -> None:
        """Multiple strategies on same day return separate rows."""
        base_time = datetime(2026, 2, 20, 14, 0, 0, tzinfo=UTC)

        # Add trades for different strategies
        strategies = ["strat_orb", "strat_scalp"]
        for strat_id in strategies:
            trade = Trade(
                strategy_id=strat_id,
                symbol="NVDA",
                side=OrderSide.BUY,
                entry_price=200.0,
                entry_time=base_time,
                exit_price=210.0,
                exit_time=base_time + timedelta(minutes=30),
                shares=5,
                stop_price=195.0,
                target_prices=[210.0],
                exit_reason=ExitReason.TARGET_1,
                gross_pnl=50.0,
                commission=1.0,
            )
            await test_trade_logger.log_trade(trade)

        result = await test_trade_logger.get_daily_pnl_by_strategy()

        # Should have 2 rows (one per strategy)
        assert len(result) == 2
        strategy_ids = {r["strategy_id"] for r in result}
        assert strategy_ids == {"strat_orb", "strat_scalp"}

    async def test_date_filter_limits_results(
        self,
        test_trade_logger: TradeLogger,
    ) -> None:
        """Date filters correctly limit results."""
        # Add trades on different dates
        dates = [
            datetime(2026, 2, 18, 14, 0, 0, tzinfo=UTC),
            datetime(2026, 2, 19, 14, 0, 0, tzinfo=UTC),
            datetime(2026, 2, 20, 14, 0, 0, tzinfo=UTC),
        ]

        for base_time in dates:
            trade = Trade(
                strategy_id="strat_orb",
                symbol="AAPL",
                side=OrderSide.BUY,
                entry_price=100.0,
                entry_time=base_time,
                exit_price=105.0,
                exit_time=base_time + timedelta(minutes=30),
                shares=10,
                stop_price=95.0,
                target_prices=[105.0],
                exit_reason=ExitReason.TARGET_1,
                gross_pnl=50.0,
                commission=1.0,
            )
            await test_trade_logger.log_trade(trade)

        # Filter to only Feb 19-20
        result = await test_trade_logger.get_daily_pnl_by_strategy(
            date_from="2026-02-19",
            date_to="2026-02-20",
        )

        assert len(result) == 2
        dates_in_result = {r["date"] for r in result}
        assert "2026-02-18" not in dates_in_result
        assert "2026-02-19" in dates_in_result
        assert "2026-02-20" in dates_in_result


# --- Heatmap Endpoint Tests ---


class TestHeatmapEndpoint:
    """Tests for GET /api/v1/performance/heatmap."""

    async def test_empty_returns_empty_cells(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """No trades returns empty cells list."""
        response = await client.get(
            "/api/v1/performance/heatmap",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cells"] == []
        assert "period" in data
        assert "timestamp" in data

    async def test_trades_grouped_by_hour_and_day(
        self,
        client_with_correlation_data: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Trades are correctly grouped by hour and day of week."""
        # Uses client_with_correlation_data which has trades at 14:00 UTC = 9:00 ET
        response = await client_with_correlation_data.get(
            "/api/v1/performance/heatmap?period=all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should have at least one cell since correlation data has market-hours trades
        assert len(data["cells"]) > 0

        # Verify cell structure
        for cell in data["cells"]:
            assert "hour" in cell
            assert "day_of_week" in cell
            assert "trade_count" in cell
            assert "avg_r_multiple" in cell
            assert "net_pnl" in cell
            # Hour should be 9-15 (market hours)
            assert 9 <= cell["hour"] <= 15
            # Day should be 0-4 (Mon-Fri)
            assert 0 <= cell["day_of_week"] <= 4

    async def test_strategy_filter_works(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Strategy filter limits heatmap to one strategy."""
        # Get all strategies heatmap
        response_all = await client_with_trades.get(
            "/api/v1/performance/heatmap?period=all",
            headers=auth_headers,
        )

        # Get single strategy heatmap
        response_filtered = await client_with_trades.get(
            "/api/v1/performance/heatmap?period=all&strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response_all.status_code == 200
        assert response_filtered.status_code == 200

        data_all = response_all.json()
        data_filtered = response_filtered.json()

        # Filtered should have fewer or equal trades
        total_all = sum(c["trade_count"] for c in data_all["cells"])
        total_filtered = sum(c["trade_count"] for c in data_filtered["cells"])
        assert total_filtered <= total_all

    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Request without auth headers returns 401."""
        response = await client.get("/api/v1/performance/heatmap")
        assert response.status_code == 401


# --- Distribution Endpoint Tests ---


class TestDistributionEndpoint:
    """Tests for GET /api/v1/performance/distribution."""

    async def test_empty_returns_zero_bins(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """No trades returns bins with zero counts."""
        response = await client.get(
            "/api/v1/performance/distribution",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_trades"] == 0
        assert data["mean_r"] == 0.0
        assert data["median_r"] == 0.0
        # Should have 28 bins (-3R to +4R in 0.25R increments)
        assert len(data["bins"]) == 28
        # All bins should have zero count
        assert all(b["count"] == 0 for b in data["bins"])

    async def test_distribution_bins_have_correct_structure(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Distribution bins have correct structure and boundaries."""
        response = await client_with_trades.get(
            "/api/v1/performance/distribution?period=all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_trades"] > 0
        assert "mean_r" in data
        assert "median_r" in data
        assert "period" in data
        assert "timestamp" in data

        # Check bin structure
        assert len(data["bins"]) == 28
        first_bin = data["bins"][0]
        assert first_bin["range_min"] == -3.0
        assert first_bin["range_max"] == -2.75

        last_bin = data["bins"][-1]
        assert last_bin["range_min"] == 3.75
        assert last_bin["range_max"] == 4.0

    async def test_strategy_filter_works(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Strategy filter limits distribution to one strategy."""
        response_all = await client_with_trades.get(
            "/api/v1/performance/distribution?period=all",
            headers=auth_headers,
        )

        response_filtered = await client_with_trades.get(
            "/api/v1/performance/distribution?period=all&strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response_all.status_code == 200
        assert response_filtered.status_code == 200

        data_all = response_all.json()
        data_filtered = response_filtered.json()

        # Filtered should have fewer or equal trades
        assert data_filtered["total_trades"] <= data_all["total_trades"]


# --- Correlation Endpoint Tests ---


class TestCorrelationEndpoint:
    """Tests for GET /api/v1/performance/correlation."""

    async def test_insufficient_data_returns_empty_matrix(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Less than 5 days of data returns empty matrix with message."""
        response = await client.get(
            "/api/v1/performance/correlation",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["matrix"] == []
        assert data["message"] is not None
        assert "Insufficient data" in data["message"]
        assert "period" in data
        assert "timestamp" in data

    async def test_correlation_matrix_structure(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Correlation matrix has correct structure with enough data."""
        response = await client_with_trades.get(
            "/api/v1/performance/correlation?period=all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Seeded data has 2 strategies across many days
        # If sufficient data, should have matrix
        if data["data_days"] >= 5 and len(data["strategy_ids"]) >= 2:
            n = len(data["strategy_ids"])
            assert len(data["matrix"]) == n
            for row in data["matrix"]:
                assert len(row) == n
            # Diagonal should be 1.0 (self-correlation)
            for i in range(n):
                assert abs(data["matrix"][i][i] - 1.0) < 0.01
        else:
            # Not enough data - message should be set
            assert data["message"] is not None

    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Request without auth headers returns 401."""
        response = await client.get("/api/v1/performance/correlation")
        assert response.status_code == 401


# --- Fixture for correlation with more data ---


@pytest.fixture
async def client_with_correlation_data(
    app_state: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with data sufficient for correlation testing.

    Creates trades across 10 days for 2 strategies to ensure correlation
    can be computed. Trades are at 15:00 UTC = 10:00 AM ET (market hours).
    """
    # 15:00 UTC = 10:00 AM ET during EST, which is within market hours
    base_time = datetime(2026, 2, 20, 15, 0, 0, tzinfo=UTC)

    # Create trades for 10 days, 2 strategies
    for day_offset in range(10):
        exit_time = base_time - timedelta(days=day_offset)
        entry_time = exit_time - timedelta(minutes=30)  # Entry 30 min before exit

        for strat_id in ["strat_orb", "strat_scalp"]:
            trade = Trade(
                strategy_id=strat_id,
                symbol="AAPL",
                side=OrderSide.BUY,
                entry_price=100.0,
                entry_time=entry_time,
                exit_price=105.0,
                exit_time=exit_time,
                shares=10,
                stop_price=95.0,
                target_prices=[105.0],
                exit_reason=ExitReason.TARGET_1,
                gross_pnl=50.0 + (day_offset * 5),  # Varying P&L
                commission=1.0,
            )
            await app_state.trade_logger.log_trade(trade)

    app = create_app(app_state)
    app.state.app_state = app_state
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client


class TestCorrelationWithData:
    """Tests for correlation endpoint with sufficient data."""

    async def test_two_strategies_returns_2x2_matrix(
        self,
        client_with_correlation_data: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Two strategies produce a 2x2 correlation matrix."""
        response = await client_with_correlation_data.get(
            "/api/v1/performance/correlation?period=all",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["strategy_ids"]) == 2
        assert len(data["matrix"]) == 2
        assert len(data["matrix"][0]) == 2
        assert len(data["matrix"][1]) == 2
        assert data["message"] is None
        assert data["data_days"] >= 5

        # Diagonal should be 1.0
        assert abs(data["matrix"][0][0] - 1.0) < 0.01
        assert abs(data["matrix"][1][1] - 1.0) < 0.01

        # Matrix should be symmetric
        assert abs(data["matrix"][0][1] - data["matrix"][1][0]) < 0.01
