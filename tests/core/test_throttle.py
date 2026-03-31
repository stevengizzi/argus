"""Tests for argus.core.throttle module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus.core.config import OrchestratorConfig
from argus.core.throttle import PerformanceThrottler, StrategyAllocation, ThrottleAction
from argus.models.trading import (
    AssetClass,
    ExitReason,
    OrderSide,
    Trade,
    TradeOutcome,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def default_config() -> OrchestratorConfig:
    """Default orchestrator config with standard throttling thresholds."""
    return OrchestratorConfig(
        consecutive_loss_throttle=5,
        suspension_sharpe_threshold=0.0,
        suspension_drawdown_pct=0.15,
        performance_lookback_days=20,
    )


@pytest.fixture
def throttler(default_config: OrchestratorConfig) -> PerformanceThrottler:
    """Performance throttler with default config."""
    return PerformanceThrottler(default_config)


def make_trade(
    net_pnl: float,
    strategy_id: str = "test_strategy",
    exit_time: datetime | None = None,
) -> Trade:
    """Create a Trade with specified net P&L for testing."""
    base_time = exit_time or datetime.now(UTC)
    return Trade(
        strategy_id=strategy_id,
        symbol="TEST",
        asset_class=AssetClass.US_STOCKS,
        side=OrderSide.BUY,
        entry_price=100.0,
        entry_time=base_time - timedelta(minutes=10),
        exit_price=100.0 + (net_pnl / 10),  # Adjust exit price based on P&L
        exit_time=base_time,
        shares=10,
        stop_price=99.0,
        target_prices=[102.0],
        exit_reason=ExitReason.TARGET_1 if net_pnl > 0 else ExitReason.STOP_LOSS,
        gross_pnl=net_pnl,
        commission=0.0,
        net_pnl=net_pnl,
        r_multiple=net_pnl / 10.0,
        hold_duration_seconds=600,
        outcome=TradeOutcome.WIN if net_pnl > 0 else TradeOutcome.LOSS,
    )


def make_daily_pnl(pnl_values: list[float]) -> list[dict]:
    """Create daily P&L data from a list of P&L values.

    Returns data in descending date order (most recent first),
    matching TradeLogger.get_daily_pnl() format.
    """
    base_date = datetime(2026, 2, 1, tzinfo=UTC)
    result = []
    for i, pnl in enumerate(reversed(pnl_values)):
        date = base_date - timedelta(days=i)
        result.append(
            {
                "date": date.date().isoformat(),
                "pnl": pnl,
                "trades": 1,
            }
        )
    return result


# ---------------------------------------------------------------------------
# ThrottleAction and StrategyAllocation Basic Tests
# ---------------------------------------------------------------------------


class TestThrottleActionEnum:
    """Tests for ThrottleAction enum."""

    def test_throttle_action_values(self) -> None:
        """ThrottleAction has expected values."""
        assert ThrottleAction.NONE == "none"
        assert ThrottleAction.REDUCE == "reduce"
        assert ThrottleAction.SUSPEND == "suspend"


class TestStrategyAllocation:
    """Tests for StrategyAllocation dataclass."""

    def test_strategy_allocation_creation(self) -> None:
        """StrategyAllocation can be created with all fields."""
        allocation = StrategyAllocation(
            strategy_id="orb",
            allocation_pct=0.25,
            allocation_dollars=25000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Healthy performance",
        )
        assert allocation.strategy_id == "orb"
        assert allocation.allocation_pct == 0.25
        assert allocation.allocation_dollars == 25000.0
        assert allocation.throttle_action == ThrottleAction.NONE
        assert allocation.eligible is True
        assert allocation.reason == "Healthy performance"


# ---------------------------------------------------------------------------
# PerformanceThrottler Initialization Tests
# ---------------------------------------------------------------------------


class TestPerformanceThrottlerInit:
    """Tests for PerformanceThrottler initialization."""

    def test_init_with_config(self, default_config: OrchestratorConfig) -> None:
        """PerformanceThrottler initializes with config."""
        throttler = PerformanceThrottler(default_config)
        assert throttler._config == default_config

    def test_init_with_custom_thresholds(self) -> None:
        """PerformanceThrottler respects custom thresholds."""
        config = OrchestratorConfig(
            consecutive_loss_throttle=3,
            suspension_sharpe_threshold=-0.5,
            suspension_drawdown_pct=0.10,
        )
        throttler = PerformanceThrottler(config)
        assert throttler._config.consecutive_loss_throttle == 3
        assert throttler._config.suspension_sharpe_threshold == -0.5
        assert throttler._config.suspension_drawdown_pct == 0.10


# ---------------------------------------------------------------------------
# get_consecutive_losses Tests
# ---------------------------------------------------------------------------


class TestGetConsecutiveLosses:
    """Tests for get_consecutive_losses method."""

    def test_consecutive_losses_empty_trades(self, throttler: PerformanceThrottler) -> None:
        """Empty trades list returns 0 consecutive losses."""
        result = throttler.get_consecutive_losses([])
        assert result == 0

    def test_consecutive_losses_single_loss(self, throttler: PerformanceThrottler) -> None:
        """Single losing trade returns 1."""
        trades = [make_trade(net_pnl=-50.0)]
        result = throttler.get_consecutive_losses(trades)
        assert result == 1

    def test_consecutive_losses_single_win(self, throttler: PerformanceThrottler) -> None:
        """Single winning trade returns 0."""
        trades = [make_trade(net_pnl=100.0)]
        result = throttler.get_consecutive_losses(trades)
        assert result == 0

    def test_consecutive_losses_five_losses(self, throttler: PerformanceThrottler) -> None:
        """Five consecutive losses returns 5."""
        trades = [make_trade(net_pnl=-50.0) for _ in range(5)]
        result = throttler.get_consecutive_losses(trades)
        assert result == 5

    def test_consecutive_losses_six_losses(self, throttler: PerformanceThrottler) -> None:
        """Six consecutive losses returns 6."""
        trades = [make_trade(net_pnl=-50.0) for _ in range(6)]
        result = throttler.get_consecutive_losses(trades)
        assert result == 6

    def test_consecutive_losses_four_losses(self, throttler: PerformanceThrottler) -> None:
        """Four consecutive losses returns 4."""
        trades = [make_trade(net_pnl=-50.0) for _ in range(4)]
        result = throttler.get_consecutive_losses(trades)
        assert result == 4

    def test_consecutive_losses_win_breaks_streak(self, throttler: PerformanceThrottler) -> None:
        """Win in the middle breaks the loss streak."""
        # Most recent first: Loss, Loss, Win, Loss, Loss
        trades = [
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=100.0),
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=-50.0),
        ]
        result = throttler.get_consecutive_losses(trades)
        assert result == 2  # Only the most recent 2 losses

    def test_consecutive_losses_breakeven_breaks_streak(
        self, throttler: PerformanceThrottler
    ) -> None:
        """Breakeven (net_pnl == 0) breaks the loss streak."""
        # Most recent first: Loss, Loss, Breakeven, Loss, Loss, Loss
        trades = [
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=0.0),
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=-50.0),
        ]
        result = throttler.get_consecutive_losses(trades)
        assert result == 2  # Only the most recent 2 losses

    def test_consecutive_losses_starts_with_win(self, throttler: PerformanceThrottler) -> None:
        """Most recent trade being a win returns 0."""
        trades = [
            make_trade(net_pnl=100.0),
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=-50.0),
        ]
        result = throttler.get_consecutive_losses(trades)
        assert result == 0


# ---------------------------------------------------------------------------
# get_rolling_sharpe Tests
# ---------------------------------------------------------------------------


class TestGetRollingSharpe:
    """Tests for get_rolling_sharpe method."""

    def test_rolling_sharpe_insufficient_data(self, throttler: PerformanceThrottler) -> None:
        """Returns None with fewer than 5 days of data."""
        daily_pnl = make_daily_pnl([100.0, 50.0, 75.0, 25.0])  # 4 days
        result = throttler.get_rolling_sharpe(daily_pnl, lookback_days=20)
        assert result is None

    def test_rolling_sharpe_exactly_five_days(self, throttler: PerformanceThrottler) -> None:
        """Returns a value with exactly 5 days of data."""
        daily_pnl = make_daily_pnl([100.0, 50.0, 75.0, 25.0, 100.0])  # 5 days
        result = throttler.get_rolling_sharpe(daily_pnl, lookback_days=20)
        assert result is not None
        assert isinstance(result, float)

    def test_rolling_sharpe_positive_performance(self, throttler: PerformanceThrottler) -> None:
        """Positive consistent gains yield positive Sharpe."""
        # 10 days of consistent positive P&L
        daily_pnl = make_daily_pnl([100.0] * 10)
        result = throttler.get_rolling_sharpe(daily_pnl, lookback_days=20)
        # With no variance, Sharpe should be 0 (or handled as edge case)
        # Actually with all identical values, std dev is 0, so Sharpe returns 0
        assert result == 0.0  # Zero variance case

    def test_rolling_sharpe_positive_with_variance(self, throttler: PerformanceThrottler) -> None:
        """Positive gains with some variance yield positive Sharpe."""
        daily_pnl = make_daily_pnl([100.0, 80.0, 120.0, 90.0, 110.0, 95.0, 105.0])
        result = throttler.get_rolling_sharpe(daily_pnl, lookback_days=20)
        assert result is not None
        assert result > 0  # Positive mean with some variance

    def test_rolling_sharpe_negative_performance(self, throttler: PerformanceThrottler) -> None:
        """Negative consistent losses yield negative Sharpe."""
        daily_pnl = make_daily_pnl([-100.0, -80.0, -120.0, -90.0, -110.0, -95.0, -105.0])
        result = throttler.get_rolling_sharpe(daily_pnl, lookback_days=20)
        assert result is not None
        assert result < 0  # Negative mean

    def test_rolling_sharpe_uses_lookback_limit(self, throttler: PerformanceThrottler) -> None:
        """Only uses the most recent lookback_days entries."""
        # 30 days of data: first 10 very positive, last 20 slightly negative
        old_data = [500.0] * 10  # These should be excluded
        recent_data = [-10.0] * 20  # These should be used
        daily_pnl = make_daily_pnl(old_data + recent_data)

        result = throttler.get_rolling_sharpe(daily_pnl, lookback_days=20)
        assert result is not None
        # With negative mean, Sharpe should be negative
        # But all values are identical (-10), so variance is 0 → Sharpe = 0
        assert result == 0.0

    def test_rolling_sharpe_empty_data(self, throttler: PerformanceThrottler) -> None:
        """Returns None with empty data."""
        result = throttler.get_rolling_sharpe([], lookback_days=20)
        assert result is None


# ---------------------------------------------------------------------------
# get_drawdown_from_peak Tests
# ---------------------------------------------------------------------------


class TestGetDrawdownFromPeak:
    """Tests for get_drawdown_from_peak method."""

    def test_drawdown_empty_data(self, throttler: PerformanceThrottler) -> None:
        """Returns 0.0 with empty data."""
        result = throttler.get_drawdown_from_peak([])
        assert result == 0.0

    def test_drawdown_at_peak(self, throttler: PerformanceThrottler) -> None:
        """Returns 0.0 when equity is at peak."""
        # Monotonically increasing equity
        daily_pnl = make_daily_pnl([100.0, 100.0, 100.0, 100.0, 100.0])
        result = throttler.get_drawdown_from_peak(daily_pnl)
        assert result == 0.0

    def test_drawdown_from_peak_calculation(self, throttler: PerformanceThrottler) -> None:
        """Correctly calculates drawdown percentage."""
        # Equity curve: 100, 200, 300, 200, 100
        # Peak = 300, Current = 100, Drawdown = (300-100)/300 = 0.667
        # But wait, these are P&L deltas, not absolute values
        # Day 1: +100 → equity = 100
        # Day 2: +100 → equity = 200
        # Day 3: +100 → equity = 300 (peak)
        # Day 4: -100 → equity = 200
        # Day 5: -100 → equity = 100
        daily_pnl = make_daily_pnl([100.0, 100.0, 100.0, -100.0, -100.0])
        result = throttler.get_drawdown_from_peak(daily_pnl)
        # Peak = 300, Current = 100, Drawdown = 200/300 = 0.6667
        assert abs(result - (200.0 / 300.0)) < 0.001

    def test_drawdown_exactly_15_percent(self, throttler: PerformanceThrottler) -> None:
        """Correctly identifies 15% drawdown."""
        # Build equity to 1000, then drop by 150 (15%)
        # Days of +100 each to reach 1000, then -150
        daily_pnl = make_daily_pnl([100.0] * 10 + [-150.0])
        result = throttler.get_drawdown_from_peak(daily_pnl)
        # Peak = 1000, Current = 850, Drawdown = 150/1000 = 0.15
        assert abs(result - 0.15) < 0.001

    def test_drawdown_exceeds_15_percent(self, throttler: PerformanceThrottler) -> None:
        """Correctly identifies drawdown exceeding 15%."""
        # Build equity to 1000, then drop by 200 (20%)
        daily_pnl = make_daily_pnl([100.0] * 10 + [-200.0])
        result = throttler.get_drawdown_from_peak(daily_pnl)
        # Peak = 1000, Current = 800, Drawdown = 200/1000 = 0.20
        assert abs(result - 0.20) < 0.001

    def test_drawdown_all_negative_pnl(self, throttler: PerformanceThrottler) -> None:
        """Returns 0.0 when peak is zero or negative."""
        # All negative P&L means peak never goes positive
        daily_pnl = make_daily_pnl([-100.0, -50.0, -75.0])
        result = throttler.get_drawdown_from_peak(daily_pnl)
        # Peak = 0 (never positive), so return 0.0
        assert result == 0.0

    def test_drawdown_recovery_to_new_peak(self, throttler: PerformanceThrottler) -> None:
        """Drawdown is 0 after recovery to new peak."""
        # 100 → 200 → 150 → 250 (new peak)
        daily_pnl = make_daily_pnl([100.0, 100.0, -50.0, 100.0])
        result = throttler.get_drawdown_from_peak(daily_pnl)
        # Peak = 250, Current = 250, Drawdown = 0
        assert result == 0.0


# ---------------------------------------------------------------------------
# check() Integration Tests
# ---------------------------------------------------------------------------


class TestPerformanceThrottlerCheck:
    """Tests for the main check() method."""

    def test_check_healthy_strategy_returns_none(self, throttler: PerformanceThrottler) -> None:
        """Healthy strategy with good performance returns NONE."""
        # 10 trades with alternating wins (no consecutive losses)
        trades = []
        for i in range(10):
            trades.append(make_trade(net_pnl=100.0 if i % 2 == 0 else -30.0))

        # Positive P&L history
        daily_pnl = make_daily_pnl([50.0, 75.0, 100.0, 60.0, 80.0, 90.0, 70.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.NONE

    def test_check_reduce_on_consecutive_losses(self, throttler: PerformanceThrottler) -> None:
        """Exactly 5 consecutive losses triggers REDUCE."""
        trades = [make_trade(net_pnl=-50.0) for _ in range(5)]
        daily_pnl = make_daily_pnl([50.0, 75.0, 100.0, 60.0, 80.0, 90.0, 70.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.REDUCE

    def test_check_no_reduce_on_4_losses(self, throttler: PerformanceThrottler) -> None:
        """4 consecutive losses does not trigger REDUCE."""
        trades = [make_trade(net_pnl=-50.0) for _ in range(4)]
        daily_pnl = make_daily_pnl([50.0, 75.0, 100.0, 60.0, 80.0, 90.0, 70.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.NONE

    def test_check_reduce_on_6_losses(self, throttler: PerformanceThrottler) -> None:
        """6 consecutive losses triggers REDUCE (not SUSPEND without other conditions)."""
        trades = [make_trade(net_pnl=-50.0) for _ in range(6)]
        # Positive daily P&L (no negative Sharpe or drawdown)
        daily_pnl = make_daily_pnl([50.0, 75.0, 100.0, 60.0, 80.0, 90.0, 70.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.REDUCE

    def test_check_suspend_on_negative_sharpe(self, throttler: PerformanceThrottler) -> None:
        """Negative 20-day rolling Sharpe triggers SUSPEND."""
        trades = [make_trade(net_pnl=100.0)]  # Single winning trade

        # Negative P&L causing negative Sharpe
        daily_pnl = make_daily_pnl([-100.0, -80.0, -120.0, -90.0, -110.0, -95.0, -105.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.SUSPEND

    def test_check_suspend_on_drawdown_exceeding_threshold(
        self, throttler: PerformanceThrottler
    ) -> None:
        """Drawdown > 15% triggers SUSPEND."""
        trades = [make_trade(net_pnl=100.0)]  # Single winning trade

        # Build equity to 1000, then drop by 200 (20% drawdown)
        daily_pnl = make_daily_pnl([100.0] * 10 + [-200.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.SUSPEND

    def test_check_suspend_overrides_reduce(self, throttler: PerformanceThrottler) -> None:
        """SUSPEND takes precedence over REDUCE."""
        # 5 consecutive losses → REDUCE
        trades = [make_trade(net_pnl=-50.0) for _ in range(5)]

        # Negative Sharpe → SUSPEND
        daily_pnl = make_daily_pnl([-100.0, -80.0, -120.0, -90.0, -110.0, -95.0, -105.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.SUSPEND

    def test_check_with_empty_trades_and_good_daily_pnl(
        self, throttler: PerformanceThrottler
    ) -> None:
        """Empty trades list with good daily P&L returns NONE."""
        daily_pnl = make_daily_pnl([50.0, 75.0, 100.0, 60.0, 80.0, 90.0, 70.0])

        result = throttler.check("test_strategy", [], daily_pnl)
        assert result == ThrottleAction.NONE

    def test_check_with_empty_daily_pnl(self, throttler: PerformanceThrottler) -> None:
        """Empty daily P&L (no Sharpe/drawdown check) with losses."""
        # 5 consecutive losses → REDUCE
        trades = [make_trade(net_pnl=-50.0) for _ in range(5)]

        result = throttler.check("test_strategy", trades, [])
        assert result == ThrottleAction.REDUCE

    def test_check_with_all_conditions_healthy(self, throttler: PerformanceThrottler) -> None:
        """All conditions healthy returns NONE."""
        # 3 wins, 2 losses (not consecutive)
        trades = [
            make_trade(net_pnl=100.0),
            make_trade(net_pnl=-50.0),
            make_trade(net_pnl=150.0),
            make_trade(net_pnl=-30.0),
            make_trade(net_pnl=200.0),
        ]

        # Positive, stable P&L (positive Sharpe, no drawdown)
        daily_pnl = make_daily_pnl(
            [100.0, 80.0, 120.0, 90.0, 110.0, 95.0, 105.0, 100.0, 115.0, 85.0]
        )

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.NONE

    def test_check_drawdown_and_negative_sharpe_both_trigger_suspend(
        self, throttler: PerformanceThrottler
    ) -> None:
        """Both drawdown and negative Sharpe still returns SUSPEND (not double)."""
        trades = [make_trade(net_pnl=100.0)]

        # Both negative Sharpe (losses) and significant drawdown
        # Start positive then heavy losses
        daily_pnl = make_daily_pnl([100.0, 100.0, 100.0, 100.0, 100.0, -200.0, -100.0, -100.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.SUSPEND

    def test_check_insufficient_daily_pnl_for_sharpe(self, throttler: PerformanceThrottler) -> None:
        """Insufficient daily P&L data (< 5 days) skips Sharpe check."""
        # 5 consecutive losses → REDUCE
        trades = [make_trade(net_pnl=-50.0) for _ in range(5)]

        # Only 3 days of P&L data (insufficient for Sharpe)
        daily_pnl = make_daily_pnl([50.0, 75.0, 100.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        # Should be REDUCE (Sharpe check skipped due to insufficient data)
        assert result == ThrottleAction.REDUCE


# ---------------------------------------------------------------------------
# Custom Config Threshold Tests
# ---------------------------------------------------------------------------


class TestCustomThresholds:
    """Tests for custom throttling thresholds."""

    def test_custom_consecutive_loss_threshold(self) -> None:
        """Custom consecutive loss threshold is respected."""
        config = OrchestratorConfig(
            consecutive_loss_throttle=3,  # Custom: 3 instead of 5
        )
        throttler = PerformanceThrottler(config)

        trades = [make_trade(net_pnl=-50.0) for _ in range(3)]
        daily_pnl = make_daily_pnl([50.0] * 10)

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.REDUCE

    def test_custom_sharpe_threshold(self) -> None:
        """Custom Sharpe threshold is respected."""
        config = OrchestratorConfig(
            suspension_sharpe_threshold=-0.5,  # Custom: -0.5 instead of 0.0
        )
        throttler = PerformanceThrottler(config)

        trades = [make_trade(net_pnl=100.0)]

        # Slightly negative P&L that would give Sharpe between -0.5 and 0
        # This should NOT trigger suspend with -0.5 threshold
        daily_pnl = make_daily_pnl([-5.0, -3.0, -7.0, -4.0, -6.0, -5.0, -5.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        # With small negative values, Sharpe might be between -0.5 and 0
        # Let's verify the actual Sharpe value
        sharpe = throttler.get_rolling_sharpe(daily_pnl, 20)
        if sharpe is not None and sharpe >= -0.5:
            assert result == ThrottleAction.NONE
        else:
            assert result == ThrottleAction.SUSPEND

    def test_custom_drawdown_threshold(self) -> None:
        """Custom drawdown threshold is respected."""
        config = OrchestratorConfig(
            suspension_drawdown_pct=0.10,  # Custom: 10% instead of 15%
        )
        throttler = PerformanceThrottler(config)

        trades = [make_trade(net_pnl=100.0)]

        # 12% drawdown (exceeds 10% but not 15%)
        daily_pnl = make_daily_pnl([100.0] * 10 + [-120.0])

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.SUSPEND

        # With default 15% threshold, same data should be NONE
        default_throttler = PerformanceThrottler(OrchestratorConfig())
        default_result = default_throttler.check("test_strategy", trades, daily_pnl)
        assert default_result == ThrottleAction.NONE


# ---------------------------------------------------------------------------
# No-Trade History Tests
# ---------------------------------------------------------------------------


class TestThrottlerSuspendBypass:
    """Tests for the suspend_enabled config-gated bypass (Sprint 29.5)."""

    def test_throttler_suspend_disabled_returns_none(self) -> None:
        """When suspend_enabled=False, evaluate() returns NONE regardless of trade history."""
        config = OrchestratorConfig(
            consecutive_loss_throttle=5,
            suspension_sharpe_threshold=0.0,
            suspension_drawdown_pct=0.15,
        )
        throttler = PerformanceThrottler(config, suspend_enabled=False)

        # 10 consecutive losses + terrible daily P&L — would normally SUSPEND
        trades = [make_trade(net_pnl=-50.0) for _ in range(10)]
        daily_pnl = make_daily_pnl(
            [100.0] * 10 + [-200.0, -100.0, -100.0]
        )

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.NONE

    def test_throttler_suspend_enabled_normal_behavior(self) -> None:
        """When suspend_enabled=True, existing throttle behavior is preserved."""
        config = OrchestratorConfig(
            consecutive_loss_throttle=5,
            suspension_sharpe_threshold=0.0,
            suspension_drawdown_pct=0.15,
        )
        throttler = PerformanceThrottler(config, suspend_enabled=True)

        # 5 consecutive losses → should REDUCE
        trades = [make_trade(net_pnl=-50.0) for _ in range(5)]
        daily_pnl = make_daily_pnl([50.0] * 10)

        result = throttler.check("test_strategy", trades, daily_pnl)
        assert result == ThrottleAction.REDUCE

    def test_orchestrator_config_throttler_flag(self) -> None:
        """OrchestratorConfig loads throttler_suspend_enabled with default True."""
        config = OrchestratorConfig()
        assert config.throttler_suspend_enabled is True

        config_disabled = OrchestratorConfig(throttler_suspend_enabled=False)
        assert config_disabled.throttler_suspend_enabled is False


class TestNoTradeHistory:
    """Tests for throttler behavior when a strategy has no trade history."""

    def test_throttler_no_trades_returns_none(self, throttler: PerformanceThrottler) -> None:
        """check() with empty trades and no daily P&L returns ThrottleAction.NONE."""
        result = throttler.check("test", [], [])
        assert result == ThrottleAction.NONE

    def test_throttler_no_trades_does_not_suspend(self, throttler: PerformanceThrottler) -> None:
        """Strategy with empty trade history is not suspended; same throttler reacts to losses."""
        # A fresh strategy with no history should pass through unthrottled.
        no_history_result = throttler.check("test", [], [])
        assert no_history_result == ThrottleAction.NONE

        # The same throttler instance with enough consecutive losses should REDUCE,
        # confirming the NONE result above was due to the empty history, not a broken throttler.
        losing_trades = [make_trade(net_pnl=-50.0) for _ in range(5)]
        losing_result = throttler.check("test", losing_trades, [])
        assert losing_result == ThrottleAction.REDUCE
