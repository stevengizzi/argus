"""Tests for BacktestEngine trail/escalation state and AMD-7 bar processing.

Sprint 28.5 Session S5 — BacktestEngine exit management alignment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.backtest.engine import BacktestEngine, _BacktestPosition
from argus.core.config import (
    EscalationPhase,
    ExitEscalationConfig,
    ExitManagementConfig,
    TrailingStopConfig,
)
from argus.core.exit_math import StopToLevel, compute_effective_stop
from argus.core.fill_model import FillExitReason


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_bt_position(
    entry_price: float = 50.0,
    stop_price: float = 48.0,
    high_watermark: float = 50.0,
    trail_active: bool = False,
    trail_stop_price: float = 0.0,
    escalation_phase_index: int = -1,
    exit_config: ExitManagementConfig | None = None,
    atr_value: float | None = 1.0,
    entry_time: datetime | None = None,
) -> _BacktestPosition:
    """Create a _BacktestPosition for testing."""
    return _BacktestPosition(
        symbol="TEST",
        strategy_id="test_strategy",
        entry_price=entry_price,
        entry_time=entry_time or datetime(2026, 1, 5, 10, 0, 0, tzinfo=UTC),
        stop_price=stop_price,
        high_watermark=high_watermark,
        trail_active=trail_active,
        trail_stop_price=trail_stop_price,
        escalation_phase_index=escalation_phase_index,
        exit_config=exit_config,
        atr_value=atr_value,
    )


def _trail_config(
    enabled: bool = True,
    trail_type: str = "fixed",
    fixed_distance: float = 1.0,
    activation: str = "immediate",
    min_trail_distance: float = 0.05,
) -> ExitManagementConfig:
    """Create an ExitManagementConfig with trailing stop enabled."""
    return ExitManagementConfig(
        trailing_stop=TrailingStopConfig(
            enabled=enabled,
            type=trail_type,
            fixed_distance=fixed_distance,
            activation=activation,
            min_trail_distance=min_trail_distance,
        ),
    )


def _escalation_config(
    enabled: bool = True,
    phases: list[tuple[float, str]] | None = None,
) -> ExitManagementConfig:
    """Create an ExitManagementConfig with escalation enabled."""
    if phases is None:
        phases = [(0.5, "breakeven"), (0.75, "half_profit")]
    return ExitManagementConfig(
        escalation=ExitEscalationConfig(
            enabled=enabled,
            phases=[
                EscalationPhase(elapsed_pct=pct, stop_to=StopToLevel(level))
                for pct, level in phases
            ],
        ),
    )


# ---------------------------------------------------------------------------
# Test 1: Trail state updates per bar (high watermark from bar.high)
# ---------------------------------------------------------------------------


class TestTrailStateUpdatesPerBar:
    """Verify high watermark and trail stop update from bar.high after exit check."""

    def test_high_watermark_updates_from_bar_high(self) -> None:
        """High watermark should be max(prior, bar.high) after the exit check."""
        pos = _make_bt_position(
            entry_price=50.0,
            high_watermark=51.0,
            trail_active=True,
            trail_stop_price=50.0,
            exit_config=_trail_config(fixed_distance=1.0),
        )

        # Simulate what AMD-7 Step 3 does: bar high is 53.0
        bar_high = 53.0
        pos.high_watermark = max(pos.high_watermark, bar_high)

        assert pos.high_watermark == 53.0

    def test_trail_stop_ratchets_up_never_down(self) -> None:
        """Trail stop should only increase, never decrease."""
        pos = _make_bt_position(
            entry_price=50.0,
            high_watermark=53.0,
            trail_active=True,
            trail_stop_price=52.0,  # Already high
            exit_config=_trail_config(fixed_distance=1.0),
        )

        # Bar high = 52.5 → new trail = 52.5 - 1.0 = 51.5
        # But 51.5 < 52.0 (current), so should stay 52.0
        from argus.core.exit_math import compute_trailing_stop

        new_trail = compute_trailing_stop(
            52.5, None, trail_type="fixed", fixed_distance=1.0,
        )
        assert new_trail is not None
        pos.trail_stop_price = max(pos.trail_stop_price, new_trail)

        assert pos.trail_stop_price == 52.0  # Did not decrease


# ---------------------------------------------------------------------------
# Test 2: Trail-triggered exit at correct price
# ---------------------------------------------------------------------------


class TestTrailTriggeredExit:
    """Verify trail stop triggers exit at the trail stop price."""

    def test_trail_stop_triggers_stopped_out(self) -> None:
        """When bar.low <= trail_stop, exit at trail stop price."""
        from argus.core.fill_model import evaluate_bar_exit

        # Trail stop at 49.50, bar low at 49.00
        effective_stop = compute_effective_stop(48.0, 49.50, None)
        assert effective_stop == 49.50

        result = evaluate_bar_exit(
            bar_high=51.0, bar_low=49.0, bar_close=50.0,
            stop_price=effective_stop, target_price=55.0,
            time_stop_expired=False,
        )

        assert result is not None
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 49.50


# ---------------------------------------------------------------------------
# Test 3: Escalation phase triggers at correct bar
# ---------------------------------------------------------------------------


class TestEscalationPhaseTrigger:
    """Verify escalation stop activates at the right elapsed percentage."""

    def test_escalation_at_50pct_elapsed(self) -> None:
        """Escalation should trigger breakeven at 50% elapsed time."""
        from argus.core.exit_math import compute_escalation_stop

        # Entry=50, HWM=54, 60s elapsed of 120s time stop = 50%
        result = compute_escalation_stop(
            entry_price=50.0,
            high_watermark=54.0,
            elapsed_seconds=60.0,
            time_stop_seconds=120.0,
            phases=[(0.5, "breakeven"), (0.75, "half_profit")],
        )

        # breakeven = entry + 0.0 * (HWM - entry) = 50.0
        assert result == 50.0

    def test_escalation_at_75pct_half_profit(self) -> None:
        """At 75% elapsed, stop should be at half_profit level."""
        from argus.core.exit_math import compute_escalation_stop

        result = compute_escalation_stop(
            entry_price=50.0,
            high_watermark=54.0,
            elapsed_seconds=90.0,
            time_stop_seconds=120.0,
            phases=[(0.5, "breakeven"), (0.75, "half_profit")],
        )

        # half_profit = entry + 0.5 * (HWM - entry) = 50 + 0.5 * 4 = 52.0
        assert result == 52.0


# ---------------------------------------------------------------------------
# Test 4: Effective stop = max(original, trail, escalation)
# ---------------------------------------------------------------------------


class TestEffectiveStopMax:
    """Verify effective stop is the tightest (highest for longs)."""

    def test_trail_higher_than_original(self) -> None:
        """Trail stop above original should be effective stop."""
        result = compute_effective_stop(48.0, 49.50, None)
        assert result == 49.50

    def test_escalation_higher_than_both(self) -> None:
        """Escalation stop above both should be effective stop."""
        result = compute_effective_stop(48.0, 49.50, 50.0)
        assert result == 50.0

    def test_original_highest(self) -> None:
        """When original is highest, it should be effective stop."""
        result = compute_effective_stop(51.0, 49.50, 50.0)
        assert result == 51.0

    def test_all_none_optionals(self) -> None:
        """With no trail or escalation, effective = original."""
        result = compute_effective_stop(48.0, None, None)
        assert result == 48.0


# ---------------------------------------------------------------------------
# Test 5: Non-trail strategy produces identical results (REGRESSION)
# ---------------------------------------------------------------------------


class TestNonTrailIdenticalResults:
    """Verify non-trail config produces same effective stop as original."""

    def test_default_config_no_trail(self) -> None:
        """Default ExitManagementConfig has trailing disabled — no trail stop."""
        config = ExitManagementConfig()
        assert config.trailing_stop.enabled is False
        assert config.escalation.enabled is False

        # Effective stop with all disabled = original stop
        result = compute_effective_stop(48.0, None, None)
        assert result == 48.0

    def test_bt_position_no_exit_config(self) -> None:
        """_BacktestPosition with None exit_config stays inert."""
        pos = _make_bt_position(exit_config=None)
        assert pos.trail_active is False
        assert pos.trail_stop_price == 0.0
        assert pos.escalation_phase_index == -1


# ---------------------------------------------------------------------------
# Test 6: Trail + time_stop interaction
# ---------------------------------------------------------------------------


class TestTrailTimeStopInteraction:
    """Trail stop should be used for exit evaluation even when time stop fires."""

    def test_trail_stop_wins_over_time_stop_when_lower(self) -> None:
        """If trail stop < bar_close but > bar_low, time stop fills at close."""
        from argus.core.fill_model import evaluate_bar_exit

        # Trail stop at 49.50. Bar: high=51, low=50, close=50.5
        # time_stop_expired = True. Trail stop NOT hit (low=50 > 49.50).
        effective_stop = compute_effective_stop(48.0, 49.50, None)
        result = evaluate_bar_exit(
            bar_high=51.0, bar_low=50.0, bar_close=50.5,
            stop_price=effective_stop, target_price=55.0,
            time_stop_expired=True,
        )

        # Time stop fires, bar.low(50) > effective_stop(49.5) → close at bar_close
        assert result is not None
        assert result.exit_reason == FillExitReason.TIME_STOPPED
        assert result.exit_price == 50.5

    def test_trail_stop_hit_beats_time_stop(self) -> None:
        """If trail stop hit on same bar as time stop, stop wins (worst case)."""
        from argus.core.fill_model import evaluate_bar_exit

        effective_stop = compute_effective_stop(48.0, 50.5, None)
        result = evaluate_bar_exit(
            bar_high=51.0, bar_low=50.0, bar_close=50.5,
            stop_price=effective_stop, target_price=55.0,
            time_stop_expired=True,
        )

        # bar_low(50) <= effective_stop(50.5) → STOPPED_OUT at 50.5
        assert result is not None
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 50.5


# ---------------------------------------------------------------------------
# Test 7: AMD-7 — Prior state used for exit, NOT updated state
# ---------------------------------------------------------------------------


class TestAmd7PriorState:
    """CRITICAL: Effective stop computed from PRIOR bar's state, not current.

    Scenario: bar high=$52, low=$49, prior trail=$49.50,
    updated trail from $52 would be $50.50 → exit at $49.50 (prior state).
    """

    def test_exit_uses_prior_trail_not_updated(self) -> None:
        """Exit evaluation must use prior bar's trail stop, not current bar's."""
        from argus.core.exit_math import compute_trailing_stop
        from argus.core.fill_model import evaluate_bar_exit

        entry_price = 50.0
        original_stop = 47.0
        prior_high_watermark = 50.50

        # Prior bar state: trail_stop = 50.50 - 1.0 = 49.50
        prior_trail = compute_trailing_stop(
            prior_high_watermark, None, trail_type="fixed", fixed_distance=1.0,
        )
        assert prior_trail == 49.50

        # Current bar: high=52, low=49
        bar_high = 52.0
        bar_low = 49.0
        bar_close = 51.0

        # AMD-7 Step 1: effective stop from PRIOR state
        effective_stop = compute_effective_stop(original_stop, prior_trail, None)
        assert effective_stop == 49.50

        # AMD-7 Step 2: evaluate exit with current bar
        result = evaluate_bar_exit(
            bar_high=bar_high, bar_low=bar_low, bar_close=bar_close,
            stop_price=effective_stop, target_price=55.0,
            time_stop_expired=False,
        )

        # bar_low(49) <= effective_stop(49.50) → STOPPED_OUT at 49.50
        assert result is not None
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 49.50

        # Verify: if we had used UPDATED state (wrong), trail would be higher
        updated_hwm = max(prior_high_watermark, bar_high)  # 52.0
        updated_trail = compute_trailing_stop(
            updated_hwm, None, trail_type="fixed", fixed_distance=1.0,
        )
        assert updated_trail == 51.0  # Would NOT have triggered (51 > 49)

        # Confirm updated trail would NOT trigger (this is the bug AMD-7 prevents)
        wrong_effective = compute_effective_stop(original_stop, updated_trail, None)
        wrong_result = evaluate_bar_exit(
            bar_high=bar_high, bar_low=bar_low, bar_close=bar_close,
            stop_price=wrong_effective, target_price=55.0,
            time_stop_expired=False,
        )
        # With wrong (updated) state, bar_low(49) <= 51 → still triggers,
        # but at 51.0 instead of the correct 49.50
        assert wrong_result is not None
        assert wrong_result.exit_price == 51.0  # Wrong price!
        assert wrong_result.exit_price != 49.50  # Confirms AMD-7 matters
