"""Tests for dev mode mock data supporting Sprint 21d Dashboard components.

Tests the mock data created for:
- StrategyDeploymentBar: capital deployed per strategy from positions
- GoalTracker: monthly P&L progress toward goal
- TodayStats: today's trading statistics
- SessionTimeline: uses frontend-only config (no backend tests needed)

These tests verify that dev mode produces consistent, meaningful data for
the new dashboard components.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from argus.api.dev_state import (
    _create_mock_positions,
    _generate_mock_trades,
    _generate_today_trades,
    create_dev_state,
)
from argus.models.trading import TradeOutcome


class TestGenerateTodayTrades:
    """Tests for the _generate_today_trades function."""

    def test_today_trades_count_is_18(self) -> None:
        """Today trades function generates exactly 18 trades."""
        trades = _generate_today_trades()
        assert len(trades) == 18

    def test_today_trades_all_from_today(self) -> None:
        """All today trades have exit_time on today's date."""
        trades = _generate_today_trades()
        today = datetime.now(UTC).date()

        for trade in trades:
            # exit_time is used to determine the trade's date
            trade_date = trade.exit_time.date()
            assert trade_date == today, (
                f"Trade {trade.symbol} has exit_time {trade.exit_time} "
                f"but expected today {today}"
            )

    def test_today_trades_win_rate_controlled(self) -> None:
        """Today trades have controlled 61% win rate (11W, 6L, 1BE)."""
        trades = _generate_today_trades()

        outcomes = {"win": 0, "loss": 0, "breakeven": 0}
        for trade in trades:
            if trade.gross_pnl > 5:  # Small buffer for rounding
                outcomes["win"] += 1
            elif trade.gross_pnl < -5:
                outcomes["loss"] += 1
            else:
                outcomes["breakeven"] += 1

        # Expected: 11 wins, 6 losses, 1 breakeven
        assert outcomes["win"] == 11, f"Expected 11 wins, got {outcomes['win']}"
        assert outcomes["loss"] == 6, f"Expected 6 losses, got {outcomes['loss']}"
        assert outcomes["breakeven"] == 1, f"Expected 1 breakeven, got {outcomes['breakeven']}"

    def test_today_trades_strategy_distribution(self) -> None:
        """Today trades are distributed across all 4 strategies."""
        trades = _generate_today_trades()

        strategy_counts: dict[str, int] = {}
        for trade in trades:
            strategy_counts[trade.strategy_id] = strategy_counts.get(trade.strategy_id, 0) + 1

        # Expected: 5 ORB, 6 Scalp, 4 VWAP, 3 Afternoon
        assert strategy_counts.get("orb_breakout") == 5
        assert strategy_counts.get("orb_scalp") == 6
        assert strategy_counts.get("vwap_reclaim") == 4
        assert strategy_counts.get("afternoon_momentum") == 3

    def test_today_trades_have_valid_prices(self) -> None:
        """All today trades have positive, realistic prices."""
        trades = _generate_today_trades()

        for trade in trades:
            assert trade.entry_price > 0, f"Invalid entry_price for {trade.symbol}"
            assert trade.exit_price > 0, f"Invalid exit_price for {trade.symbol}"
            assert trade.stop_price > 0, f"Invalid stop_price for {trade.symbol}"
            assert trade.shares > 0, f"Invalid shares for {trade.symbol}"

    def test_today_trades_have_valid_pnl(self) -> None:
        """All today trades have correctly calculated gross_pnl."""
        trades = _generate_today_trades()

        for trade in trades:
            expected_pnl = trade.shares * (trade.exit_price - trade.entry_price)
            # Allow small floating point tolerance
            assert abs(trade.gross_pnl - expected_pnl) < 0.01, (
                f"P&L mismatch for {trade.symbol}: "
                f"expected {expected_pnl:.2f}, got {trade.gross_pnl:.2f}"
            )


class TestGenerateMockTradesHistorical:
    """Tests for the _generate_mock_trades function with historical data."""

    def test_historical_trades_exclude_today_when_flag_false(self) -> None:
        """Historical trades exclude today when include_today=False."""
        trades = _generate_mock_trades(include_today=False)
        today = datetime.now(UTC).date()

        for trade in trades:
            trade_date = trade.exit_time.date()
            assert trade_date != today, (
                f"Trade {trade.symbol} has exit_time {trade.exit_time} on today "
                f"but include_today=False"
            )

    def test_historical_trades_count(self) -> None:
        """Historical trades generates expected count (32 total by default)."""
        trades = _generate_mock_trades(include_today=False)
        # 12 + 6 + 8 + 6 = 32 trades
        assert len(trades) == 32


class TestMockPositions:
    """Tests for _create_mock_positions function."""

    def test_mock_positions_for_strategy_deployment_bar(self) -> None:
        """Mock positions cover all 4 strategies for StrategyDeploymentBar component."""
        now = datetime.now(UTC)
        positions = _create_mock_positions(now)

        # Should have 8 positions (2 per strategy)
        assert len(positions) == 8, f"Expected 8 positions, got {len(positions)}"

        # Check positions span all 4 strategies
        strategies_with_positions = set(p.strategy_id for p in positions)
        expected_strategies = {
            "orb_breakout",
            "orb_scalp",
            "vwap_reclaim",
            "afternoon_momentum",
        }
        assert strategies_with_positions == expected_strategies, (
            f"Expected positions for {expected_strategies}, "
            f"got {strategies_with_positions}"
        )

    def test_mock_positions_deployed_capital_realistic(self) -> None:
        """Mock positions deployed capital is realistic for $100K account."""
        now = datetime.now(UTC)
        positions = _create_mock_positions(now)

        # Calculate total deployed capital
        total_deployed = sum(
            p.shares_remaining * p.entry_price for p in positions
        )

        # Account is $100K, should have meaningful deployment
        account_equity = 100_000.0

        # Deployed should be between 30% and 80% of account
        deployed_pct = total_deployed / account_equity
        assert 0.30 <= deployed_pct <= 0.80, (
            f"Deployed capital {deployed_pct:.1%} should be 30-80% of account"
        )

    def test_mock_positions_have_valid_entry_prices(self) -> None:
        """Mock positions have positive entry prices."""
        now = datetime.now(UTC)
        positions = _create_mock_positions(now)

        for pos in positions:
            assert pos.entry_price > 0, f"Invalid entry_price for {pos.symbol}"
            assert pos.shares_total > 0, f"Invalid shares_total for {pos.symbol}"
            assert pos.shares_remaining > 0, f"Invalid shares_remaining for {pos.symbol}"
            assert pos.stop_price > 0, f"Invalid stop_price for {pos.symbol}"

    def test_mock_positions_have_realistic_t1_states(self) -> None:
        """Some mock positions have T1 filled (for demo variety)."""
        now = datetime.now(UTC)
        positions = _create_mock_positions(now)

        t1_filled_count = sum(1 for p in positions if p.t1_filled)

        # Should have some T1 filled and some not (for demo variety)
        assert 2 <= t1_filled_count <= 6, (
            f"Expected 2-6 T1 filled positions for demo variety, got {t1_filled_count}"
        )
