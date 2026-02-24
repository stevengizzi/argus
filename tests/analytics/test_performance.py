"""Tests for argus.analytics.performance module.

Tests the shared performance metric computation used by both the
Command Center API and backtesting toolkit.
"""

from __future__ import annotations

import pytest

from argus.analytics.performance import (
    compute_max_drawdown_pct,
    compute_metrics,
    compute_sharpe_ratio,
)


class TestComputeMetricsEmpty:
    """Tests for compute_metrics with no trades."""

    def test_empty_trades_returns_zeroed_metrics(self) -> None:
        """Empty trade list returns zeroed PerformanceMetrics."""
        result = compute_metrics([])

        assert result.total_trades == 0
        assert result.wins == 0
        assert result.losses == 0
        assert result.breakeven == 0
        assert result.win_rate == 0.0
        assert result.profit_factor == 0.0
        assert result.net_pnl == 0.0
        assert result.gross_pnl == 0.0
        assert result.total_commissions == 0.0
        assert result.avg_r_multiple == 0.0
        assert result.sharpe_ratio == 0.0
        assert result.max_drawdown_pct == 0.0
        assert result.avg_hold_seconds == 0.0
        assert result.largest_win == 0.0
        assert result.largest_loss == 0.0
        assert result.consecutive_wins_max == 0
        assert result.consecutive_losses_max == 0


class TestComputeMetricsAllWins:
    """Tests for compute_metrics with all winning trades."""

    def test_all_wins_100_percent_win_rate(self) -> None:
        """All winning trades gives 100% win rate."""
        trades = [
            {
                "net_pnl": 100.0,
                "r_multiple": 1.5,
                "commission": 2.0,
                "hold_duration_seconds": 300,
                "exit_price": 150.0,
                "exit_time": "2026-02-20T10:30:00",
            },
            {
                "net_pnl": 200.0,
                "r_multiple": 2.0,
                "commission": 2.0,
                "hold_duration_seconds": 600,
                "exit_price": 160.0,
                "exit_time": "2026-02-20T11:30:00",
            },
            {
                "net_pnl": 150.0,
                "r_multiple": 1.8,
                "commission": 2.0,
                "hold_duration_seconds": 450,
                "exit_price": 155.0,
                "exit_time": "2026-02-20T12:30:00",
            },
        ]

        result = compute_metrics(trades)

        assert result.total_trades == 3
        assert result.wins == 3
        assert result.losses == 0
        assert result.win_rate == 1.0
        assert result.net_pnl == 450.0
        assert result.largest_win == 200.0
        assert result.consecutive_wins_max == 3

    def test_all_wins_profit_factor_infinity(self) -> None:
        """All wins with no losses gives infinite profit factor."""
        trades = [
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20"},
            {"net_pnl": 200.0, "exit_price": 160.0, "exit_time": "2026-02-20"},
        ]

        result = compute_metrics(trades)

        assert result.profit_factor == float("inf")


class TestComputeMetricsAllLosses:
    """Tests for compute_metrics with all losing trades."""

    def test_all_losses_0_percent_win_rate(self) -> None:
        """All losing trades gives 0% win rate."""
        trades = [
            {
                "net_pnl": -100.0,
                "r_multiple": -1.0,
                "commission": 2.0,
                "hold_duration_seconds": 300,
                "exit_price": 145.0,
                "exit_time": "2026-02-20T10:30:00",
            },
            {
                "net_pnl": -150.0,
                "r_multiple": -1.5,
                "commission": 2.0,
                "hold_duration_seconds": 450,
                "exit_price": 140.0,
                "exit_time": "2026-02-20T11:30:00",
            },
        ]

        result = compute_metrics(trades)

        assert result.total_trades == 2
        assert result.wins == 0
        assert result.losses == 2
        assert result.win_rate == 0.0
        assert result.net_pnl == -250.0
        assert result.largest_loss == -150.0
        assert result.consecutive_losses_max == 2


class TestComputeMetricsMixed:
    """Tests for compute_metrics with mixed trades."""

    def test_mixed_trades_correct_win_rate_and_profit_factor(self) -> None:
        """Mixed trades compute correct win rate and profit factor."""
        trades = [
            # Wins
            {
                "net_pnl": 200.0,
                "r_multiple": 2.0,
                "exit_price": 150.0,
                "exit_time": "2026-02-20T10:00:00",
            },
            {
                "net_pnl": 100.0,
                "r_multiple": 1.0,
                "exit_price": 155.0,
                "exit_time": "2026-02-20T11:00:00",
            },
            # Losses
            {
                "net_pnl": -50.0,
                "r_multiple": -0.5,
                "exit_price": 145.0,
                "exit_time": "2026-02-20T12:00:00",
            },
            {
                "net_pnl": -100.0,
                "r_multiple": -1.0,
                "exit_price": 140.0,
                "exit_time": "2026-02-20T13:00:00",
            },
        ]

        result = compute_metrics(trades)

        assert result.total_trades == 4
        assert result.wins == 2
        assert result.losses == 2
        assert result.win_rate == 0.5
        # profit_factor = gross_wins / gross_losses = 300 / 150 = 2.0
        assert result.profit_factor == 2.0
        assert result.net_pnl == 150.0

    def test_breakeven_trades_categorized_correctly(self) -> None:
        """Breakeven trades (within $0.50) are categorized separately."""
        trades = [
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20T10:00:00"},
            {"net_pnl": 0.25, "exit_price": 150.0, "exit_time": "2026-02-20T11:00:00"},
            {"net_pnl": -0.40, "exit_price": 150.0, "exit_time": "2026-02-20T12:00:00"},
            {"net_pnl": -100.0, "exit_price": 145.0, "exit_time": "2026-02-20T13:00:00"},
        ]

        result = compute_metrics(trades)

        assert result.total_trades == 4
        assert result.wins == 1
        assert result.losses == 1
        assert result.breakeven == 2


class TestProfitFactorNoLosses:
    """Tests for profit factor edge case."""

    def test_profit_factor_no_losses_returns_infinity(self) -> None:
        """Profit factor with no losses returns infinity."""
        trades = [
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20"},
        ]

        result = compute_metrics(trades)

        assert result.profit_factor == float("inf")


class TestSharpeRatio:
    """Tests for Sharpe ratio computation."""

    def test_sharpe_ratio_with_varied_daily_pnl(self) -> None:
        """Sharpe ratio computes from varied daily P&L."""
        # Multiple days with varying P&L
        trades = [
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-18T10:00:00"},
            {"net_pnl": 50.0, "exit_price": 155.0, "exit_time": "2026-02-19T10:00:00"},
            {"net_pnl": -30.0, "exit_price": 145.0, "exit_time": "2026-02-20T10:00:00"},
            {"net_pnl": 80.0, "exit_price": 160.0, "exit_time": "2026-02-21T10:00:00"},
        ]

        result = compute_metrics(trades)

        # Just verify it's a reasonable positive number (mean is positive)
        assert result.sharpe_ratio > 0

    def test_sharpe_ratio_single_day_returns_zero(self) -> None:
        """Sharpe ratio with single day returns zero (need >= 2 days)."""
        daily_pnl = [100.0]
        sharpe = compute_sharpe_ratio(daily_pnl)
        assert sharpe == 0.0


class TestMaxDrawdown:
    """Tests for max drawdown computation."""

    def test_max_drawdown_known_equity_curve(self) -> None:
        """Max drawdown from known equity curve."""
        # Daily P&L: +100, +50, -100, -50, +200
        # Cumulative: 100, 150, 50, 0, 200
        # Peak: 150, drawdown to 0 = 150/150 = 100%
        daily_pnl = [100.0, 50.0, -100.0, -50.0, 200.0]

        drawdown = compute_max_drawdown_pct(daily_pnl)

        # Peak of 150, trough of 0, so 100% drawdown
        assert drawdown == pytest.approx(1.0, rel=0.01)

    def test_max_drawdown_no_drawdown(self) -> None:
        """Max drawdown with monotonically increasing equity is 0."""
        daily_pnl = [100.0, 100.0, 100.0]

        drawdown = compute_max_drawdown_pct(daily_pnl)

        assert drawdown == 0.0


class TestConsecutiveStreaks:
    """Tests for consecutive win/loss streak computation."""

    def test_consecutive_streaks_computed_correctly(self) -> None:
        """Consecutive win/loss streaks are tracked correctly."""
        # Pattern: W, W, W, L, L, W, W, L
        trades = [
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20T10:00:00"},
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20T10:30:00"},
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20T11:00:00"},
            {"net_pnl": -50.0, "exit_price": 145.0, "exit_time": "2026-02-20T11:30:00"},
            {"net_pnl": -50.0, "exit_price": 145.0, "exit_time": "2026-02-20T12:00:00"},
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20T12:30:00"},
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20T13:00:00"},
            {"net_pnl": -50.0, "exit_price": 145.0, "exit_time": "2026-02-20T13:30:00"},
        ]

        result = compute_metrics(trades)

        # Max consecutive wins: 3 (first three)
        assert result.consecutive_wins_max == 3
        # Max consecutive losses: 2 (fourth and fifth)
        assert result.consecutive_losses_max == 2


class TestOpenTradesExcluded:
    """Tests for open trade exclusion."""

    def test_open_trades_excluded_from_metrics(self) -> None:
        """Trades without exit_price are excluded from metrics."""
        trades = [
            {"net_pnl": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20"},  # closed
            {"net_pnl": 200.0, "exit_price": None},  # open - should be excluded
            {"net_pnl": 50.0, "exit_price": 155.0, "exit_time": "2026-02-20"},  # closed
        ]

        result = compute_metrics(trades)

        # Only 2 closed trades should be counted
        assert result.total_trades == 2
        assert result.net_pnl == 150.0  # 100 + 50, not 350


class TestCommissionSumming:
    """Tests for commission summation."""

    def test_commission_summing_correct(self) -> None:
        """Total commissions are summed correctly."""
        trades = [
            {"net_pnl": 100.0, "commission": 2.50, "exit_price": 150.0, "exit_time": "2026-02-20"},
            {"net_pnl": 50.0, "commission": 1.75, "exit_price": 155.0, "exit_time": "2026-02-20"},
            {"net_pnl": -30.0, "commission": 3.00, "exit_price": 145.0, "exit_time": "2026-02-20"},
        ]

        result = compute_metrics(trades)

        assert result.total_commissions == pytest.approx(7.25)


class TestHoldDurationAverage:
    """Tests for hold duration averaging."""

    def test_avg_hold_seconds_computed_correctly(self) -> None:
        """Average hold duration is computed from hold_duration_seconds."""
        trades = [
            {
                "net_pnl": 100.0,
                "hold_duration_seconds": 300,
                "exit_price": 150.0,
                "exit_time": "2026-02-20",
            },
            {
                "net_pnl": 50.0,
                "hold_duration_seconds": 600,
                "exit_price": 155.0,
                "exit_time": "2026-02-20",
            },
            {
                "net_pnl": -30.0,
                "hold_duration_seconds": 900,
                "exit_price": 145.0,
                "exit_time": "2026-02-20",
            },
        ]

        result = compute_metrics(trades)

        # Average: (300 + 600 + 900) / 3 = 600
        assert result.avg_hold_seconds == 600.0


class TestAlternateFieldNames:
    """Tests for alternate field name handling."""

    def test_pnl_dollars_field_name_works(self) -> None:
        """Alternate field name pnl_dollars works."""
        trades = [
            {"pnl_dollars": 100.0, "exit_price": 150.0, "exit_time": "2026-02-20"},
        ]

        result = compute_metrics(trades)

        assert result.net_pnl == 100.0
        assert result.wins == 1

    def test_pnl_r_multiple_field_name_works(self) -> None:
        """Alternate field name pnl_r_multiple works."""
        trades = [
            {
                "net_pnl": 100.0,
                "pnl_r_multiple": 2.0,
                "exit_price": 150.0,
                "exit_time": "2026-02-20",
            },
            {
                "net_pnl": 50.0,
                "pnl_r_multiple": 1.0,
                "exit_price": 155.0,
                "exit_time": "2026-02-20",
            },
        ]

        result = compute_metrics(trades)

        assert result.avg_r_multiple == 1.5
