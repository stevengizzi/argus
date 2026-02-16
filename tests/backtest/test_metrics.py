"""Tests for the backtest metrics module."""

from argus.backtest.metrics import compute_max_drawdown, compute_sharpe_ratio


class TestComputeSharpeRatio:
    """Tests for compute_sharpe_ratio function."""

    def test_positive_returns(self) -> None:
        """Sharpe ratio is positive for consistently positive returns."""
        daily_returns = [0.01, 0.005, 0.008, -0.002, 0.012] * 50  # 250 days
        sharpe = compute_sharpe_ratio(daily_returns)
        assert sharpe > 0

    def test_zero_std_returns_zero(self) -> None:
        """Sharpe ratio is zero when there's no variance in returns."""
        daily_returns = [0.01] * 100  # No variance
        sharpe = compute_sharpe_ratio(daily_returns)
        assert sharpe == 0.0

    def test_insufficient_data(self) -> None:
        """Sharpe ratio is zero with fewer than 2 data points."""
        sharpe = compute_sharpe_ratio([0.01])
        assert sharpe == 0.0

    def test_empty_returns(self) -> None:
        """Sharpe ratio is zero with empty returns."""
        sharpe = compute_sharpe_ratio([])
        assert sharpe == 0.0

    def test_negative_returns(self) -> None:
        """Sharpe ratio can be negative for consistently negative returns."""
        daily_returns = [-0.01, -0.005, -0.008, 0.002, -0.012] * 50
        sharpe = compute_sharpe_ratio(daily_returns)
        assert sharpe < 0

    def test_custom_risk_free_rate(self) -> None:
        """Custom risk-free rate affects the calculation."""
        daily_returns = [0.01] * 10 + [0.02] * 10  # Some variance
        sharpe_5pct = compute_sharpe_ratio(daily_returns, risk_free_rate=0.05)
        sharpe_0pct = compute_sharpe_ratio(daily_returns, risk_free_rate=0.0)

        # Higher risk-free rate should lower the Sharpe ratio
        assert sharpe_5pct < sharpe_0pct


class TestComputeMaxDrawdown:
    """Tests for compute_max_drawdown function."""

    def test_simple_drawdown(self) -> None:
        """Correctly computes drawdown from a simple equity curve."""
        equity = [100, 110, 105, 95, 100, 90, 115]
        dd_dollars, dd_pct = compute_max_drawdown(equity)

        # Peak was 110, trough was 90 -> DD = 20, 18.18%
        assert dd_dollars == 20.0
        assert abs(dd_pct - (20.0 / 110.0)) < 0.01

    def test_no_drawdown(self) -> None:
        """Zero drawdown when equity only increases."""
        equity = [100, 105, 110, 115]
        dd_dollars, dd_pct = compute_max_drawdown(equity)

        assert dd_dollars == 0.0
        assert dd_pct == 0.0

    def test_empty_equity_curve(self) -> None:
        """Zero drawdown for empty equity curve."""
        dd_dollars, dd_pct = compute_max_drawdown([])
        assert dd_dollars == 0.0
        assert dd_pct == 0.0

    def test_single_point(self) -> None:
        """Zero drawdown for single point equity curve."""
        dd_dollars, dd_pct = compute_max_drawdown([100])
        assert dd_dollars == 0.0
        assert dd_pct == 0.0

    def test_drawdown_at_end(self) -> None:
        """Drawdown detected even when it occurs at the end."""
        equity = [100, 120, 130, 100]  # Peak 130, ends at 100
        dd_dollars, dd_pct = compute_max_drawdown(equity)

        assert dd_dollars == 30.0
        assert abs(dd_pct - (30.0 / 130.0)) < 0.01

    def test_multiple_drawdowns(self) -> None:
        """Correctly identifies the largest drawdown among multiple."""
        equity = [100, 110, 100, 120, 90, 130]  # Two drawdowns: 10 and 30
        dd_dollars, dd_pct = compute_max_drawdown(equity)

        # Largest drawdown: from 120 to 90 = 30
        assert dd_dollars == 30.0

    def test_consecutive_new_highs(self) -> None:
        """Peak updates correctly on consecutive new highs."""
        equity = [100, 110, 120, 130, 125, 140, 135]
        dd_dollars, dd_pct = compute_max_drawdown(equity)

        # Largest drawdown: from 130 to 125 = 5, or 140 to 135 = 5
        assert dd_dollars == 5.0
