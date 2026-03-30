"""Tests for argus.core.exit_math — pure exit management math functions."""

from __future__ import annotations

import pytest

from argus.core.exit_math import (
    StopToLevel,
    compute_effective_stop,
    compute_escalation_stop,
    compute_trailing_stop,
)


# ---------------------------------------------------------------------------
# StopToLevel enum
# ---------------------------------------------------------------------------


class TestStopToLevelEnum:
    """Verify StopToLevel has exactly the 4 AMD-5 values."""

    def test_enum_has_four_members(self) -> None:
        assert len(StopToLevel) == 4

    def test_enum_values(self) -> None:
        assert StopToLevel.BREAKEVEN == "breakeven"
        assert StopToLevel.QUARTER_PROFIT == "quarter_profit"
        assert StopToLevel.HALF_PROFIT == "half_profit"
        assert StopToLevel.THREE_QUARTER_PROFIT == "three_quarter_profit"


# ---------------------------------------------------------------------------
# compute_trailing_stop
# ---------------------------------------------------------------------------


class TestComputeTrailingStop:
    """Tests for the trailing stop computation."""

    def test_atr_type_with_valid_atr(self) -> None:
        """ATR trailing stop: hwm - (atr * multiplier)."""
        result = compute_trailing_stop(
            high_watermark=105.0,
            atr_value=2.0,
            trail_type="atr",
            atr_multiplier=2.5,
            min_trail_distance=0.01,
        )
        # 105.0 - (2.0 * 2.5) = 105.0 - 5.0 = 100.0
        assert result == pytest.approx(100.0)

    def test_percent_type(self) -> None:
        """Percent trailing stop: hwm - (hwm * percent)."""
        result = compute_trailing_stop(
            high_watermark=200.0,
            atr_value=None,
            trail_type="percent",
            trail_percent=0.02,
            min_trail_distance=0.01,
        )
        # 200.0 - (200.0 * 0.02) = 200.0 - 4.0 = 196.0
        assert result == pytest.approx(196.0)

    def test_fixed_type(self) -> None:
        """Fixed trailing stop: hwm - fixed_distance."""
        result = compute_trailing_stop(
            high_watermark=50.0,
            atr_value=None,
            trail_type="fixed",
            fixed_distance=1.50,
            min_trail_distance=0.01,
        )
        # 50.0 - 1.50 = 48.50
        assert result == pytest.approx(48.50)

    def test_atr_type_none_atr_returns_none(self) -> None:
        """ATR type with None ATR value returns None."""
        result = compute_trailing_stop(
            high_watermark=100.0,
            atr_value=None,
            trail_type="atr",
        )
        assert result is None

    def test_atr_type_negative_atr_returns_none(self) -> None:
        """AMD-12: ATR type with negative ATR returns None."""
        result = compute_trailing_stop(
            high_watermark=100.0,
            atr_value=-0.5,
            trail_type="atr",
        )
        assert result is None

    def test_atr_type_zero_atr_returns_none(self) -> None:
        """AMD-12: ATR type with zero ATR returns None."""
        result = compute_trailing_stop(
            high_watermark=100.0,
            atr_value=0.0,
            trail_type="atr",
        )
        assert result is None

    def test_min_trail_distance_floor_enforced(self) -> None:
        """Floor clamps small trail distances upward."""
        # ATR * multiplier = 0.01 * 1.0 = 0.01, but min floor is 0.50
        result = compute_trailing_stop(
            high_watermark=100.0,
            atr_value=0.01,
            trail_type="atr",
            atr_multiplier=1.0,
            min_trail_distance=0.50,
        )
        # Floor applied: 100.0 - 0.50 = 99.50
        assert result == pytest.approx(99.50)

    def test_disabled_returns_none(self) -> None:
        """When enabled=False, trailing stop returns None regardless."""
        result = compute_trailing_stop(
            high_watermark=100.0,
            atr_value=2.0,
            trail_type="atr",
            enabled=False,
        )
        assert result is None

    def test_unknown_trail_type_raises(self) -> None:
        """Unknown trail_type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown trail_type"):
            compute_trailing_stop(
                high_watermark=100.0,
                atr_value=2.0,
                trail_type="unknown",
            )


# ---------------------------------------------------------------------------
# compute_escalation_stop
# ---------------------------------------------------------------------------


class TestComputeEscalationStop:
    """Tests for the escalation stop computation (AMD-5)."""

    # Standard phases for testing: 50% elapsed → breakeven, 75% → half_profit
    PHASES: list[tuple[float, str]] = [
        (0.50, "breakeven"),
        (0.75, "half_profit"),
    ]

    def test_breakeven_phase(self) -> None:
        """AMD-5: breakeven → stop at entry_price."""
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=110.0,
            elapsed_seconds=60.0,
            time_stop_seconds=100.0,
            phases=self.PHASES,
        )
        # 60% elapsed >= 50% threshold → breakeven → entry_price = 100.0
        assert result == pytest.approx(100.0)

    def test_quarter_profit_phase(self) -> None:
        """AMD-5: quarter_profit → entry + 0.25 * (hwm - entry)."""
        phases = [(0.25, "quarter_profit")]
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=120.0,
            elapsed_seconds=30.0,
            time_stop_seconds=100.0,
            phases=phases,
        )
        # 30% elapsed >= 25% threshold → 100 + 0.25 * (120 - 100) = 105.0
        assert result == pytest.approx(105.0)

    def test_half_profit_phase(self) -> None:
        """AMD-5: half_profit → entry + 0.50 * (hwm - entry)."""
        phases = [(0.50, "half_profit")]
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=120.0,
            elapsed_seconds=60.0,
            time_stop_seconds=100.0,
            phases=phases,
        )
        # 100 + 0.50 * 20 = 110.0
        assert result == pytest.approx(110.0)

    def test_three_quarter_profit_phase(self) -> None:
        """AMD-5: three_quarter_profit → entry + 0.75 * (hwm - entry)."""
        phases = [(0.40, "three_quarter_profit")]
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=120.0,
            elapsed_seconds=50.0,
            time_stop_seconds=100.0,
            phases=phases,
        )
        # 100 + 0.75 * 20 = 115.0
        assert result == pytest.approx(115.0)

    def test_no_time_stop_returns_none(self) -> None:
        """When time_stop_seconds is None, escalation returns None."""
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=110.0,
            elapsed_seconds=60.0,
            time_stop_seconds=None,
            phases=self.PHASES,
        )
        assert result is None

    def test_disabled_returns_none(self) -> None:
        """When enabled=False, escalation returns None."""
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=110.0,
            elapsed_seconds=60.0,
            time_stop_seconds=100.0,
            phases=self.PHASES,
            enabled=False,
        )
        assert result is None

    def test_empty_phases_returns_none(self) -> None:
        """When phases list is empty, escalation returns None."""
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=110.0,
            elapsed_seconds=60.0,
            time_stop_seconds=100.0,
            phases=[],
        )
        assert result is None

    def test_no_phase_reached_yet_returns_none(self) -> None:
        """When elapsed_pct is below all phase thresholds, returns None."""
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=110.0,
            elapsed_seconds=10.0,
            time_stop_seconds=100.0,
            phases=self.PHASES,  # first phase at 50%
        )
        # 10% elapsed < 50% threshold → no phase active
        assert result is None

    def test_latest_phase_wins(self) -> None:
        """When multiple phases are reached, the latest one wins."""
        phases = [
            (0.25, "breakeven"),
            (0.50, "quarter_profit"),
            (0.75, "half_profit"),
        ]
        result = compute_escalation_stop(
            entry_price=100.0,
            high_watermark=120.0,
            elapsed_seconds=80.0,
            time_stop_seconds=100.0,
            phases=phases,
        )
        # 80% elapsed >= 75% → half_profit: 100 + 0.50 * 20 = 110.0
        assert result == pytest.approx(110.0)


# ---------------------------------------------------------------------------
# compute_effective_stop
# ---------------------------------------------------------------------------


class TestComputeEffectiveStop:
    """Tests for effective (tightest) stop selection."""

    def test_max_of_all_non_none_sources(self) -> None:
        """Returns the maximum of original, trail, and escalation stops."""
        result = compute_effective_stop(
            original_stop=95.0,
            trail_stop=98.0,
            escalation_stop=100.0,
        )
        assert result == pytest.approx(100.0)

    def test_original_stop_only(self) -> None:
        """When both trail and escalation are None, returns original_stop."""
        result = compute_effective_stop(
            original_stop=95.0,
            trail_stop=None,
            escalation_stop=None,
        )
        assert result == pytest.approx(95.0)

    def test_trail_below_original_ignored(self) -> None:
        """Trail stop below original does not loosen the stop."""
        result = compute_effective_stop(
            original_stop=95.0,
            trail_stop=90.0,
            escalation_stop=None,
        )
        assert result == pytest.approx(95.0)

    def test_escalation_tightest(self) -> None:
        """Escalation stop can be tightest even above trail."""
        result = compute_effective_stop(
            original_stop=95.0,
            trail_stop=97.0,
            escalation_stop=99.0,
        )
        assert result == pytest.approx(99.0)

    def test_trail_tightest(self) -> None:
        """Trail stop can be tightest when above both others."""
        result = compute_effective_stop(
            original_stop=95.0,
            trail_stop=101.0,
            escalation_stop=99.0,
        )
        assert result == pytest.approx(101.0)
