"""Tests for CounterfactualTracker trail/escalation state and AMD-7 bar processing.

Sprint 28.5 Session S5 — CounterfactualTracker exit management alignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import (
    EscalationPhase,
    ExitEscalationConfig,
    ExitManagementConfig,
    TrailingStopConfig,
)
from argus.core.exit_math import StopToLevel
from argus.core.fill_model import FillExitReason
from argus.intelligence.counterfactual import (
    CounterfactualTracker,
    RejectionStage,
    _OpenPosition,
)

_ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    symbol: str = "TEST",
    strategy_id: str = "test_strategy",
    entry_price: float = 50.0,
    stop_price: float = 48.0,
    target_prices: list[float] | None = None,
    time_stop_seconds: int | None = 120,
    atr_value: float | None = 1.0,
) -> MagicMock:
    """Create a mock SignalEvent."""
    signal = MagicMock()
    signal.symbol = symbol
    signal.strategy_id = strategy_id
    signal.entry_price = entry_price
    signal.stop_price = stop_price
    signal.target_prices = target_prices or [52.0]
    signal.time_stop_seconds = time_stop_seconds
    signal.timestamp = datetime.now(_ET)
    signal.quality_score = None
    signal.quality_grade = None
    signal.signal_context = {}
    signal.atr_value = atr_value
    return signal


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
# Test 8: CounterfactualTracker trail state updates per bar
# ---------------------------------------------------------------------------


class TestCounterfactualTrailStatePerBar:
    """Verify trail state updates correctly through _process_bar."""

    def test_trail_stop_updates_from_high_watermark(self) -> None:
        """Trail stop should update based on high watermark after exit check."""
        exit_cfg = _trail_config(fixed_distance=1.0)
        tracker = CounterfactualTracker(
            exit_configs={"test_strategy": exit_cfg},
        )

        signal = _make_signal(
            entry_price=50.0, stop_price=48.0,
            target_prices=[60.0],  # High target to avoid early exit
        )
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        pos = tracker._open_positions[pid]
        assert pos.trail_active is True  # immediate activation
        assert pos.high_watermark == 50.0

        # Bar 1: high=52, low=50.5, close=51 — no exit
        bar_time = pos.opened_at + timedelta(seconds=10)
        tracker._process_bar(pid, 52.0, 50.5, 51.0, bar_time)

        # After Step 3: HWM=52, trail = 52-1 = 51
        assert pos.high_watermark == 52.0
        assert pos.trail_stop_price == 51.0

        # Bar 2: high=53, low=51.5, close=52 — no exit (low > trail of 51)
        bar_time2 = pos.opened_at + timedelta(seconds=20)
        tracker._process_bar(pid, 53.0, 51.5, 52.0, bar_time2)

        # After Step 3: HWM=53, trail = 53-1 = 52
        assert pos.high_watermark == 53.0
        assert pos.trail_stop_price == 52.0


# ---------------------------------------------------------------------------
# Test 9: CounterfactualTracker trail-triggered exit at correct price
# ---------------------------------------------------------------------------


class TestCounterfactualTrailTriggeredExit:
    """Verify trail stop triggers exit via _process_bar."""

    def test_trail_stop_closes_position(self) -> None:
        """When bar.low <= trail_stop, position should close."""
        exit_cfg = _trail_config(fixed_distance=1.0)
        tracker = CounterfactualTracker(
            exit_configs={"test_strategy": exit_cfg},
        )

        signal = _make_signal(
            entry_price=50.0, stop_price=48.0,
            target_prices=[60.0],  # High target to avoid early exit
        )
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        # Bar 1: push HWM to 53 → trail = 52
        bar_time = tracker._open_positions[pid].opened_at + timedelta(seconds=10)
        tracker._process_bar(pid, 53.0, 51.0, 52.0, bar_time)

        assert tracker._open_positions[pid].trail_stop_price == 52.0

        # Bar 2: low=51.5 → hits trail of 52? No, 51.5 < 52 → yes, STOPPED_OUT
        bar_time2 = bar_time + timedelta(seconds=10)
        tracker._process_bar(pid, 52.5, 51.5, 52.0, bar_time2)

        # Position should be closed
        assert pid not in tracker._open_positions
        closed = [p for p in tracker._closed_positions if p.position_id == pid]
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.STOPPED_OUT
        assert closed[0].exit_price == 52.0  # Effective stop = trail = 52.0


# ---------------------------------------------------------------------------
# Test 10: CounterfactualTracker escalation phase triggers
# ---------------------------------------------------------------------------


class TestCounterfactualEscalationTrigger:
    """Verify escalation phase advances and contributes to effective stop."""

    def test_escalation_advances_phase_index(self) -> None:
        """Escalation phase index should advance as time progresses."""
        exit_cfg = _escalation_config(
            phases=[(0.5, "breakeven"), (0.75, "half_profit")],
        )
        tracker = CounterfactualTracker(
            exit_configs={"test_strategy": exit_cfg},
        )

        signal = _make_signal(
            entry_price=50.0, stop_price=48.0, time_stop_seconds=120,
            target_prices=[60.0],  # High target to avoid early exit
        )
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        pos = tracker._open_positions[pid]

        # Bar at 30% elapsed (36s) — no phase reached
        bar_time1 = pos.opened_at + timedelta(seconds=36)
        tracker._process_bar(pid, 54.0, 50.0, 52.0, bar_time1)
        assert pos.escalation_phase_index == -1

        # Bar at 60% elapsed (72s) — phase 0 (breakeven) reached
        bar_time2 = pos.opened_at + timedelta(seconds=72)
        tracker._process_bar(pid, 54.0, 50.5, 52.0, bar_time2)
        assert pos.escalation_phase_index == 0

        # Bar at 80% elapsed (96s) — phase 1 (half_profit) reached
        bar_time3 = pos.opened_at + timedelta(seconds=96)
        tracker._process_bar(pid, 54.0, 52.5, 53.0, bar_time3)
        assert pos.escalation_phase_index == 1


# ---------------------------------------------------------------------------
# Test 11: Non-trail shadow position identical to pre-sprint (REGRESSION)
# ---------------------------------------------------------------------------


class TestCounterfactualNonTrailRegression:
    """Verify non-trail shadow positions behave identically to pre-sprint."""

    def test_no_exit_config_uses_original_stop(self) -> None:
        """Without exit config, effective stop is the original stop price."""
        tracker = CounterfactualTracker()  # No exit_configs

        signal = _make_signal(entry_price=50.0, stop_price=48.0)
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        pos = tracker._open_positions[pid]
        assert pos.exit_config is None
        assert pos.trail_active is False
        assert pos.trail_stop_price == 0.0

        # Bar with low hitting original stop → STOPPED_OUT at 48.0
        bar_time = pos.opened_at + timedelta(seconds=10)
        tracker._process_bar(pid, 51.0, 47.5, 49.0, bar_time)

        assert pid not in tracker._open_positions
        closed = [p for p in tracker._closed_positions if p.position_id == pid]
        assert len(closed) == 1
        assert closed[0].exit_price == 48.0
        assert closed[0].exit_reason == FillExitReason.STOPPED_OUT

    def test_disabled_config_uses_original_stop(self) -> None:
        """Disabled trailing/escalation should behave like no config."""
        exit_cfg = ExitManagementConfig()  # Both disabled by default
        tracker = CounterfactualTracker(
            exit_configs={"test_strategy": exit_cfg},
        )

        signal = _make_signal(entry_price=50.0, stop_price=48.0)
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        pos = tracker._open_positions[pid]
        assert pos.trail_active is False

        # Target hit at 52.0
        bar_time = pos.opened_at + timedelta(seconds=10)
        tracker._process_bar(pid, 53.0, 49.0, 51.0, bar_time)

        assert pid not in tracker._open_positions
        closed = [p for p in tracker._closed_positions if p.position_id == pid]
        assert len(closed) == 1
        assert closed[0].exit_price == 52.0
        assert closed[0].exit_reason == FillExitReason.TARGET_HIT


# ---------------------------------------------------------------------------
# Test 12: Backfill bars update trail state correctly
# ---------------------------------------------------------------------------


class TestCounterfactualBackfillTrailState:
    """Verify backfill bars from IntradayCandleStore update trail state."""

    def test_backfill_updates_trail_state(self) -> None:
        """Trail state should update through backfill bars."""
        exit_cfg = _trail_config(fixed_distance=1.0)

        @dataclass
        class FakeBar:
            high: float
            low: float
            close: float
            timestamp: datetime

        class FakeStore:
            def has_bars(self, symbol: str) -> bool:
                return True

            def get_bars(
                self, symbol: str, start_time: datetime | None = None,
            ) -> list[FakeBar]:
                base = start_time or datetime.now(_ET)
                return [
                    FakeBar(52.0, 50.5, 51.0, base + timedelta(seconds=5)),
                    FakeBar(53.0, 51.5, 52.0, base + timedelta(seconds=10)),
                ]

        tracker = CounterfactualTracker(
            candle_store=FakeStore(),  # type: ignore[arg-type]
            exit_configs={"test_strategy": exit_cfg},
        )

        signal = _make_signal(
            entry_price=50.0, stop_price=48.0,
            target_prices=[60.0],  # High target to avoid early exit
        )
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        # Position still open after backfill (neither bar hits trail)
        pos = tracker._open_positions.get(pid)
        assert pos is not None
        assert pos.high_watermark == 53.0
        assert pos.trail_stop_price == 52.0  # 53 - 1 = 52
        assert pos.bars_monitored == 2


# ---------------------------------------------------------------------------
# Test 13: Trail triggers during backfill → position closes
# ---------------------------------------------------------------------------


class TestCounterfactualBackfillTrailTrigger:
    """Verify trail stop triggering during backfill closes position immediately."""

    def test_backfill_trail_trigger_closes_position(self) -> None:
        """If trail triggers during backfill, position should close."""
        exit_cfg = _trail_config(fixed_distance=1.0)

        @dataclass
        class FakeBar:
            high: float
            low: float
            close: float
            timestamp: datetime

        class FakeStore:
            def has_bars(self, symbol: str) -> bool:
                return True

            def get_bars(
                self, symbol: str, start_time: datetime | None = None,
            ) -> list[FakeBar]:
                base = start_time or datetime.now(_ET)
                return [
                    # Bar 1: push HWM to 53, trail = 52
                    FakeBar(53.0, 50.5, 51.0, base + timedelta(seconds=5)),
                    # Bar 2: low=51 < trail(52) → triggers exit
                    FakeBar(53.5, 51.0, 52.0, base + timedelta(seconds=10)),
                    # Bar 3: should NOT be processed (position already closed)
                    FakeBar(55.0, 53.0, 54.0, base + timedelta(seconds=15)),
                ]

        tracker = CounterfactualTracker(
            candle_store=FakeStore(),  # type: ignore[arg-type]
            exit_configs={"test_strategy": exit_cfg},
        )

        signal = _make_signal(
            entry_price=50.0, stop_price=48.0,
            target_prices=[60.0],  # High target to avoid early exit
        )
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        # Position should be closed during backfill
        assert pid not in tracker._open_positions
        closed = [p for p in tracker._closed_positions if p.position_id == pid]
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.STOPPED_OUT
        assert closed[0].exit_price == 52.0  # Trail stop price
        assert closed[0].bars_monitored == 2  # Only processed 2 bars
