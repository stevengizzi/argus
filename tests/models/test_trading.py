"""Tests for trading data models."""

from datetime import UTC, datetime, timedelta

import pytest

from argus.models.trading import (
    AssetClass,
    DailySummary,
    ExitReason,
    Order,
    OrderSide,
    OrderType,
    Position,
    PositionStatus,
    Trade,
    TradeOutcome,
)


class TestOrderModel:
    """Tests for the Order model."""

    def test_order_defaults(self) -> None:
        """Order has sensible defaults."""
        order = Order(
            strategy_id="strat_orb",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
        )
        assert order.order_type == OrderType.MARKET
        assert order.asset_class == AssetClass.US_STOCKS
        assert order.time_in_force == "day"
        assert len(order.id) == 26  # ULID length

    def test_order_quantity_validation(self) -> None:
        """Order quantity must be >= 1."""
        with pytest.raises(ValueError):
            Order(
                strategy_id="strat_orb",
                symbol="AAPL",
                side=OrderSide.BUY,
                quantity=0,
            )


class TestPositionModel:
    """Tests for the Position model."""

    def test_position_fields(self) -> None:
        """Position stores all required fields."""
        pos = Position(
            strategy_id="strat_orb",
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=datetime.now(UTC),
            shares=100,
            stop_price=148.0,
            target_prices=[152.0, 154.0],
        )
        assert pos.status == PositionStatus.OPEN
        assert len(pos.target_prices) == 2


class TestTradeModel:
    """Tests for the Trade model."""

    def test_trade_calculates_derived_fields(self) -> None:
        """Trade auto-calculates net_pnl, hold_duration, r_multiple, outcome."""
        entry_time = datetime(2026, 2, 15, 10, 0, 0)
        exit_time = datetime(2026, 2, 15, 10, 30, 0)

        trade = Trade(
            strategy_id="strat_orb",
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=entry_time,
            exit_price=152.0,
            exit_time=exit_time,
            shares=100,
            stop_price=148.0,
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=200.0,
            commission=2.0,
        )

        # Net P&L should be calculated
        assert trade.net_pnl == 198.0

        # Hold duration should be 30 minutes = 1800 seconds
        assert trade.hold_duration_seconds == 1800

        # R-multiple: $1.98/share gain / $2 risk = 0.99R
        assert trade.r_multiple == pytest.approx(0.99, rel=0.01)

        # Should be a winning trade
        assert trade.outcome == TradeOutcome.WIN

    def test_trade_losing_outcome(self) -> None:
        """Trade with negative P&L is marked as loss."""
        trade = Trade(
            strategy_id="strat_orb",
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=datetime.now(UTC),
            exit_price=148.0,
            exit_time=datetime.now(UTC) + timedelta(minutes=10),
            shares=100,
            stop_price=148.0,
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-200.0,
        )

        assert trade.outcome == TradeOutcome.LOSS
        assert trade.net_pnl == -200.0


class TestDailySummaryModel:
    """Tests for the DailySummary model."""

    def test_daily_summary_defaults(self) -> None:
        """DailySummary has zero defaults."""
        summary = DailySummary(date="2026-02-15")
        assert summary.total_trades == 0
        assert summary.win_rate == 0.0
        assert summary.net_pnl == 0.0
        assert summary.strategy_id is None  # Account-wide
