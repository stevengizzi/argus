"""Integration tests for overflow → CounterfactualTracker pipeline.

Verifies that BROKER_OVERFLOW signals flow through the full counterfactual
pipeline: tracker opens shadow positions, store records have correct fields,
FilterAccuracy groups BROKER_OVERFLOW correctly, and coexistence with other
rejection stages works.

Sprint 27.95, Session 3c.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from argus.core.events import CandleEvent, SignalEvent, Side
from argus.core.fill_model import FillExitReason
from argus.intelligence.counterfactual import (
    CounterfactualTracker,
    RejectionStage,
)
from argus.intelligence.counterfactual_store import CounterfactualStore
from argus.intelligence.filter_accuracy import compute_filter_accuracy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    symbol: str = "TSLA",
    strategy_id: str = "orb_breakout",
    entry_price: float = 150.0,
    stop_price: float = 145.0,
    target_prices: tuple[float, ...] = (160.0,),
    time_stop_seconds: int | None = None,
    quality_score: float = 72.5,
    quality_grade: str = "B+",
) -> SignalEvent:
    """Create a test SignalEvent with populated fields."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        share_count=0,
        rationale="Test signal",
        time_stop_seconds=time_stop_seconds,
        pattern_strength=75.0,
        signal_context={"source": "test"},
        quality_score=quality_score,
        quality_grade=quality_grade,
    )


def _make_candle(
    symbol: str = "TSLA",
    high: float = 155.0,
    low: float = 148.0,
    close: float = 152.0,
    timestamp: datetime | None = None,
) -> CandleEvent:
    """Create a test CandleEvent."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=150.0,
        high=high,
        low=low,
        close=close,
        volume=1000,
        timestamp=timestamp or datetime.now(UTC),
    )


async def _seed_position(
    store: CounterfactualStore,
    position_id: str,
    *,
    rejection_stage: str = "quality_filter",
    rejection_reason: str = "grade too low",
    strategy_id: str = "orb_breakout",
    quality_grade: str | None = "B",
    theoretical_pnl: float = -2.0,
    opened_at: str = "2026-03-25T10:00:00",
    closed_at: str = "2026-03-25T10:30:00",
) -> None:
    """Insert a closed counterfactual position directly into the store."""
    assert store._conn is not None
    await store._conn.execute(
        """INSERT INTO counterfactual_positions (
            position_id, symbol, strategy_id, entry_price, stop_price,
            target_price, time_stop_seconds, rejection_stage, rejection_reason,
            quality_score, quality_grade, regime_vector_snapshot, signal_metadata,
            opened_at, closed_at, exit_price, exit_reason,
            theoretical_pnl, theoretical_r_multiple, duration_seconds,
            max_adverse_excursion, max_favorable_excursion, bars_monitored
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            position_id, "TSLA", strategy_id, 150.0, 145.0,
            160.0, None, rejection_stage, rejection_reason,
            72.5, quality_grade, None, "{}",
            opened_at, closed_at,
            143.0 if theoretical_pnl < 0 else 162.0,
            "stopped_out" if theoretical_pnl < 0 else "target_hit",
            theoretical_pnl, theoretical_pnl / 5.0, 1800.0,
            2.0, 3.0, 10,
        ),
    )
    await store._conn.commit()


# ---------------------------------------------------------------------------
# Test 1: Overflow signal → CounterfactualTracker opens shadow position
# ---------------------------------------------------------------------------


class TestOverflowOpensCounterfactual:
    """End-to-end: BROKER_OVERFLOW signal creates a shadow position."""

    def test_tracker_accepts_broker_overflow_stage(self) -> None:
        """CounterfactualTracker.track() opens a position for BROKER_OVERFLOW."""
        tracker = CounterfactualTracker()
        signal = _make_signal()

        pid = tracker.track(
            signal,
            "Broker capacity reached (5/5)",
            RejectionStage.BROKER_OVERFLOW,
        )

        assert pid is not None
        assert len(pid) == 26  # ULID

        positions = tracker.get_open_positions()
        assert len(positions) == 1
        pos = positions[0]
        assert pos.rejection_stage == RejectionStage.BROKER_OVERFLOW
        assert pos.symbol == "TSLA"
        assert pos.strategy_id == "orb_breakout"


# ---------------------------------------------------------------------------
# Test 2: Counterfactual store record has stage=BROKER_OVERFLOW
# ---------------------------------------------------------------------------


class TestOverflowStoreRecord:
    """Verify store records have correct BROKER_OVERFLOW stage value."""

    @pytest.mark.asyncio
    async def test_store_persists_broker_overflow_stage(
        self, tmp_path: Path
    ) -> None:
        """Closed overflow position persisted with rejection_stage=broker_overflow."""
        store = CounterfactualStore(db_path=tmp_path / "test_cf.db")
        await store.initialize()

        try:
            await _seed_position(
                store,
                "01OVERFLOW001",
                rejection_stage="broker_overflow",
                rejection_reason="Broker capacity reached (5/5)",
                theoretical_pnl=-3.0,
            )

            positions = await store.get_closed_positions(
                start_date="2026-03-24T00:00:00",
                end_date="2026-03-26T00:00:00",
            )
            assert len(positions) == 1
            assert positions[0]["rejection_stage"] == "broker_overflow"
            assert "Broker capacity reached" in str(positions[0]["rejection_reason"])
        finally:
            await store.close()


# ---------------------------------------------------------------------------
# Test 3: Store record has correct signal data
# ---------------------------------------------------------------------------


class TestOverflowStoreSignalData:
    """Verify store records preserve signal fields for overflow positions."""

    @pytest.mark.asyncio
    async def test_signal_fields_preserved_in_store(
        self, tmp_path: Path
    ) -> None:
        """Symbol, entry, stop, target preserved in overflow store record."""
        store = CounterfactualStore(db_path=tmp_path / "test_cf.db")
        await store.initialize()

        try:
            assert store._conn is not None
            await store._conn.execute(
                """INSERT INTO counterfactual_positions (
                    position_id, symbol, strategy_id, entry_price, stop_price,
                    target_price, time_stop_seconds, rejection_stage, rejection_reason,
                    quality_score, quality_grade, regime_vector_snapshot, signal_metadata,
                    opened_at, closed_at, exit_price, exit_reason,
                    theoretical_pnl, theoretical_r_multiple, duration_seconds,
                    max_adverse_excursion, max_favorable_excursion, bars_monitored
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "01OVERFLOW002", "NVDA", "bull_flag", 200.0, 195.0,
                    215.0, None, "broker_overflow",
                    "Broker capacity reached (3/3)",
                    85.0, "A-", None, json.dumps({"source": "test"}),
                    "2026-03-25T10:00:00", "2026-03-25T10:30:00",
                    193.0, "stopped_out",
                    -7.0, -1.4, 1800.0,
                    7.0, 5.0, 15,
                ),
            )
            await store._conn.commit()

            positions = await store.get_closed_positions(
                start_date="2026-03-24T00:00:00",
                end_date="2026-03-26T00:00:00",
            )
            assert len(positions) == 1
            pos = positions[0]
            assert pos["symbol"] == "NVDA"
            assert pos["strategy_id"] == "bull_flag"
            assert pos["entry_price"] == 200.0
            assert pos["stop_price"] == 195.0
            assert pos["target_price"] == 215.0
            assert pos["rejection_stage"] == "broker_overflow"
        finally:
            await store.close()


# ---------------------------------------------------------------------------
# Test 4: FilterAccuracy includes BROKER_OVERFLOW in breakdown
# ---------------------------------------------------------------------------


class TestFilterAccuracyOverflow:
    """Verify FilterAccuracy groups BROKER_OVERFLOW as a separate category."""

    @pytest.mark.asyncio
    async def test_by_stage_includes_broker_overflow(
        self, tmp_path: Path
    ) -> None:
        """compute_filter_accuracy by_stage includes broker_overflow category."""
        store = CounterfactualStore(db_path=tmp_path / "test_cf.db")
        await store.initialize()

        try:
            # Seed positions with different stages
            await _seed_position(
                store, "01QF001",
                rejection_stage="quality_filter",
                theoretical_pnl=-2.0,
            )
            await _seed_position(
                store, "01BO001",
                rejection_stage="broker_overflow",
                rejection_reason="Broker capacity reached (5/5)",
                theoretical_pnl=-3.0,
            )
            await _seed_position(
                store, "01BO002",
                rejection_stage="broker_overflow",
                rejection_reason="Broker capacity reached (6/5)",
                theoretical_pnl=5.0,  # Would have profited
            )

            report = await compute_filter_accuracy(
                store,
                start_date=datetime(2026, 3, 24),
                end_date=datetime(2026, 3, 26),
                min_sample_count=1,
            )

            assert report.total_positions == 3

            # Find broker_overflow in by_stage
            stage_categories = {b.category for b in report.by_stage}
            assert "broker_overflow" in stage_categories

            overflow_breakdown = next(
                b for b in report.by_stage if b.category == "broker_overflow"
            )
            assert overflow_breakdown.total_rejections == 2
            assert overflow_breakdown.correct_rejections == 1  # -3.0 lost
            assert overflow_breakdown.incorrect_rejections == 1  # +5.0 profited
        finally:
            await store.close()


# ---------------------------------------------------------------------------
# Test 5: Coexistence — multiple rejection stages in same session
# ---------------------------------------------------------------------------


class TestCoexistenceMultipleStages:
    """Verify quality_filter + position_sizer + broker_overflow all tracked."""

    def test_tracker_handles_all_three_stages_concurrently(self) -> None:
        """Three different rejection stages produce three shadow positions."""
        tracker = CounterfactualTracker()

        # Quality filter rejection
        pid_qf = tracker.track(
            _make_signal(symbol="AAPL"),
            "Grade D below minimum B-",
            RejectionStage.QUALITY_FILTER,
        )

        # Position sizer rejection
        pid_ps = tracker.track(
            _make_signal(symbol="MSFT"),
            "Position sizer returned 0 shares",
            RejectionStage.POSITION_SIZER,
        )

        # Broker overflow rejection
        pid_bo = tracker.track(
            _make_signal(symbol="NVDA"),
            "Broker capacity reached (5/5)",
            RejectionStage.BROKER_OVERFLOW,
        )

        assert pid_qf is not None
        assert pid_ps is not None
        assert pid_bo is not None

        positions = tracker.get_open_positions()
        assert len(positions) == 3

        stages = {p.rejection_stage for p in positions}
        assert stages == {
            RejectionStage.QUALITY_FILTER,
            RejectionStage.POSITION_SIZER,
            RejectionStage.BROKER_OVERFLOW,
        }

        symbols = {p.symbol for p in positions}
        assert symbols == {"AAPL", "MSFT", "NVDA"}


# ---------------------------------------------------------------------------
# Test 6: Overflow counterfactual position closes via fill model
# ---------------------------------------------------------------------------


class TestOverflowPositionCloses:
    """Overflow counterfactual positions close correctly via TheoreticalFillModel."""

    @pytest.mark.asyncio
    async def test_overflow_position_closes_at_stop(self) -> None:
        """Overflow shadow position stops out when bar breaches stop price."""
        tracker = CounterfactualTracker()
        signal = _make_signal(
            symbol="TSLA",
            entry_price=150.0,
            stop_price=145.0,
            target_prices=(160.0,),
        )

        pid = tracker.track(
            signal,
            "Broker capacity reached (5/5)",
            RejectionStage.BROKER_OVERFLOW,
        )
        assert pid is not None

        # Feed candle that breaches stop
        candle = _make_candle(symbol="TSLA", high=151.0, low=143.0, close=144.0)
        await tracker.on_candle(candle)

        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.STOPPED_OUT
        assert closed[0].exit_price == 145.0
        assert closed[0].rejection_stage == RejectionStage.BROKER_OVERFLOW

    @pytest.mark.asyncio
    async def test_overflow_position_closes_at_target(self) -> None:
        """Overflow shadow position hits target when bar exceeds target price."""
        tracker = CounterfactualTracker()
        signal = _make_signal(
            symbol="TSLA",
            entry_price=150.0,
            stop_price=145.0,
            target_prices=(160.0,),
        )

        pid = tracker.track(
            signal,
            "Broker capacity reached (5/5)",
            RejectionStage.BROKER_OVERFLOW,
        )
        assert pid is not None

        # Feed candle that hits target
        candle = _make_candle(symbol="TSLA", high=162.0, low=149.0, close=161.0)
        await tracker.on_candle(candle)

        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.TARGET_HIT
        assert closed[0].exit_price == 160.0
        assert closed[0].rejection_stage == RejectionStage.BROKER_OVERFLOW

    @pytest.mark.asyncio
    async def test_overflow_position_closes_at_eod(self) -> None:
        """Overflow shadow position closes at EOD via close_all_eod()."""
        tracker = CounterfactualTracker()
        signal = _make_signal(
            symbol="TSLA",
            entry_price=150.0,
            stop_price=145.0,
            target_prices=(160.0,),
        )

        pid = tracker.track(
            signal,
            "Broker capacity reached (5/5)",
            RejectionStage.BROKER_OVERFLOW,
        )
        assert pid is not None

        # Feed a neutral candle (no stop/target hit)
        candle = _make_candle(symbol="TSLA", high=153.0, low=148.0, close=151.0)
        await tracker.on_candle(candle)

        assert len(tracker.get_open_positions()) == 1

        # EOD close
        await tracker.close_all_eod()

        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.EOD_CLOSED
        assert closed[0].rejection_stage == RejectionStage.BROKER_OVERFLOW
        assert closed[0].theoretical_pnl is not None
