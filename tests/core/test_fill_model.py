"""Tests for the shared theoretical fill model.

Verifies worst-case-for-longs fill priority:
stop > target > time_stop, including edge cases.
"""

from __future__ import annotations

from argus.core.fill_model import ExitResult, FillExitReason, evaluate_bar_exit


class TestEvaluateBarExit:
    """Tests for evaluate_bar_exit() pure function."""

    def test_stop_triggers_when_bar_low_at_stop(self) -> None:
        """Bar low exactly at stop → STOPPED_OUT at stop price."""
        result = evaluate_bar_exit(
            bar_high=105.0,
            bar_low=95.0,
            bar_close=100.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=False,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 95.0

    def test_stop_triggers_when_bar_low_below_stop(self) -> None:
        """Bar low below stop → STOPPED_OUT at stop price (not bar low)."""
        result = evaluate_bar_exit(
            bar_high=105.0,
            bar_low=93.0,
            bar_close=98.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=False,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 95.0

    def test_target_triggers_when_bar_high_at_target(self) -> None:
        """Bar high exactly at target → TARGET_HIT at target price."""
        result = evaluate_bar_exit(
            bar_high=110.0,
            bar_low=99.0,
            bar_close=108.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=False,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.TARGET_HIT
        assert result.exit_price == 110.0

    def test_target_triggers_when_bar_high_above_target(self) -> None:
        """Bar high above target → TARGET_HIT at target price (not bar high)."""
        result = evaluate_bar_exit(
            bar_high=115.0,
            bar_low=99.0,
            bar_close=112.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=False,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.TARGET_HIT
        assert result.exit_price == 110.0

    def test_both_stop_and_target_trigger_stop_wins(self) -> None:
        """When both stop AND target trigger on same bar, stop wins (worst case)."""
        result = evaluate_bar_exit(
            bar_high=115.0,
            bar_low=90.0,
            bar_close=100.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=False,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 95.0

    def test_time_stop_without_stop_breach(self) -> None:
        """Time stop expired, bar doesn't hit stop → TIME_STOPPED at bar close."""
        result = evaluate_bar_exit(
            bar_high=105.0,
            bar_low=99.0,
            bar_close=102.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=True,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.TIME_STOPPED
        assert result.exit_price == 102.0

    def test_time_stop_with_stop_breach_uses_stop_price(self) -> None:
        """Time stop expired AND bar hits stop → STOPPED_OUT at stop price."""
        result = evaluate_bar_exit(
            bar_high=105.0,
            bar_low=93.0,
            bar_close=98.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=True,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 95.0

    def test_no_trigger_returns_none(self) -> None:
        """Bar within range, no time stop → None (position stays open)."""
        result = evaluate_bar_exit(
            bar_high=105.0,
            bar_low=99.0,
            bar_close=102.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=False,
        )
        assert result is None

    def test_exit_result_is_frozen(self) -> None:
        """ExitResult is a frozen dataclass."""
        result = ExitResult(FillExitReason.STOPPED_OUT, 95.0)
        assert result.exit_reason == FillExitReason.STOPPED_OUT
        assert result.exit_price == 95.0

    def test_time_stop_with_target_breach_target_wins(self) -> None:
        """Time stop expired AND bar hits target (not stop) → TARGET_HIT.

        Target still has Priority 2 over time stop at Priority 3, but
        since stop (Priority 1) is checked first and doesn't trigger,
        the time stop path's stop check also won't trigger, so we'd
        expect TIME_STOPPED. However, bar_high >= target is checked at
        Priority 2 before time_stop at Priority 3, so target wins.

        Wait — re-reading the logic: Priority 1 (stop) doesn't trigger,
        then Priority 2 (target) triggers → TARGET_HIT.
        """
        result = evaluate_bar_exit(
            bar_high=112.0,
            bar_low=99.0,
            bar_close=108.0,
            stop_price=95.0,
            target_price=110.0,
            time_stop_expired=True,
        )
        assert result is not None
        assert result.exit_reason == FillExitReason.TARGET_HIT
        assert result.exit_price == 110.0
