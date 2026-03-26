"""Tests for the CounterfactualTracker and related models.

Verifies position opening, candle processing, MAE/MFE tracking,
IntradayCandleStore backfill, and edge cases.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from argus.core.events import CandleEvent, SignalEvent, Side
from argus.core.fill_model import FillExitReason
from argus.intelligence.counterfactual import (
    CounterfactualPosition,
    CounterfactualTracker,
    RejectionStage,
    _OpenPosition,
)
from argus.strategies.patterns.base import CandleBar


def _make_signal(
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
    entry_price: float = 100.0,
    stop_price: float = 95.0,
    target_prices: tuple[float, ...] = (110.0,),
    time_stop_seconds: int | None = None,
    signal_context: dict | None = None,
) -> SignalEvent:
    """Create a test SignalEvent."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        share_count=0,
        rationale="test signal",
        time_stop_seconds=time_stop_seconds,
        signal_context=signal_context or {},
        quality_score=72.5,
        quality_grade="B",
    )


def _make_candle(
    symbol: str = "AAPL",
    high: float = 105.0,
    low: float = 99.0,
    close: float = 102.0,
    timestamp: datetime | None = None,
) -> CandleEvent:
    """Create a test CandleEvent."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=100.0,
        high=high,
        low=low,
        close=close,
        volume=1000,
        timestamp=timestamp or datetime.now(UTC),
    )


class TestCounterfactualTrackerOpen:
    """Tests for opening counterfactual positions."""

    def test_track_returns_position_id(self) -> None:
        """track() returns a valid ULID position_id."""
        tracker = CounterfactualTracker()
        signal = _make_signal()
        pid = tracker.track(signal, "grade too low", RejectionStage.QUALITY_FILTER)
        assert pid is not None
        assert len(pid) == 26  # ULID length

    def test_track_stores_correct_fields(self) -> None:
        """Opened position has correct entry/stop/target/rejection data."""
        tracker = CounterfactualTracker()
        signal = _make_signal(
            entry_price=150.0,
            stop_price=145.0,
            target_prices=(160.0, 170.0),
        )
        pid = tracker.track(
            signal,
            "shares=0",
            RejectionStage.POSITION_SIZER,
            metadata={"extra": "data"},
        )
        assert pid is not None

        positions = tracker.get_open_positions()
        assert len(positions) == 1

        pos = positions[0]
        assert pos.position_id == pid
        assert pos.symbol == "AAPL"
        assert pos.strategy_id == "orb_breakout"
        assert pos.entry_price == 150.0
        assert pos.stop_price == 145.0
        assert pos.target_price == 160.0  # T1 only
        assert pos.rejection_stage == RejectionStage.POSITION_SIZER
        assert pos.rejection_reason == "shares=0"
        assert pos.quality_score == 72.5
        assert pos.quality_grade == "B"
        assert pos.bars_monitored == 0

    def test_empty_target_prices_returns_none(self) -> None:
        """Signal with empty target_prices tuple → track() returns None."""
        tracker = CounterfactualTracker()
        signal = _make_signal(target_prices=())
        pid = tracker.track(signal, "no targets", RejectionStage.QUALITY_FILTER)
        assert pid is None
        assert len(tracker.get_open_positions()) == 0


class TestCounterfactualTrackerCandles:
    """Tests for candle processing and exit detection."""

    @pytest.mark.asyncio
    async def test_candle_closes_at_stop(self) -> None:
        """Feed candle with low < stop → position closed as STOPPED_OUT."""
        tracker = CounterfactualTracker()
        signal = _make_signal(entry_price=100.0, stop_price=95.0, target_prices=(110.0,))
        pid = tracker.track(signal, "risk limit", RejectionStage.RISK_MANAGER)
        assert pid is not None

        candle = _make_candle(high=101.0, low=93.0, close=94.0)
        await tracker.on_candle(candle)

        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.STOPPED_OUT
        assert closed[0].exit_price == 95.0

    @pytest.mark.asyncio
    async def test_candle_closes_at_target(self) -> None:
        """Feed candle with high > target → position closed as TARGET_HIT."""
        tracker = CounterfactualTracker()
        signal = _make_signal(entry_price=100.0, stop_price=95.0, target_prices=(110.0,))
        pid = tracker.track(signal, "grade D", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        candle = _make_candle(high=112.0, low=99.0, close=111.0)
        await tracker.on_candle(candle)

        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.TARGET_HIT
        assert closed[0].exit_price == 110.0

    @pytest.mark.asyncio
    async def test_mae_mfe_tracking(self) -> None:
        """Feed multiple candles, verify MAE/MFE updated correctly."""
        tracker = CounterfactualTracker()
        signal = _make_signal(entry_price=100.0, stop_price=90.0, target_prices=(120.0,))
        pid = tracker.track(signal, "test", RejectionStage.SHADOW)
        assert pid is not None

        ts = datetime.now(UTC)

        # Bar 1: high=105, low=98 → MFE=5, MAE=2
        await tracker.on_candle(_make_candle(high=105.0, low=98.0, close=103.0, timestamp=ts))

        # Bar 2: high=108, low=97 → MFE=8, MAE=3
        await tracker.on_candle(
            _make_candle(high=108.0, low=97.0, close=106.0, timestamp=ts + timedelta(minutes=1))
        )

        # Bar 3: high=106, low=94 → MFE still 8, MAE=6
        await tracker.on_candle(
            _make_candle(high=106.0, low=94.0, close=99.0, timestamp=ts + timedelta(minutes=2))
        )

        positions = tracker.get_open_positions()
        assert len(positions) == 1
        pos = positions[0]
        assert pos.max_favorable_excursion == 8.0
        assert pos.max_adverse_excursion == 6.0
        assert pos.bars_monitored == 3

    @pytest.mark.asyncio
    async def test_time_stop_closes_position(self) -> None:
        """Position with time_stop_seconds closes when elapsed time exceeds."""
        tracker = CounterfactualTracker()
        signal = _make_signal(
            entry_price=100.0,
            stop_price=95.0,
            target_prices=(110.0,),
            time_stop_seconds=120,
        )
        pid = tracker.track(signal, "test", RejectionStage.SHADOW)
        assert pid is not None

        # Feed a candle 3 minutes after open (180s > 120s time stop)
        pos = tracker.get_open_positions()[0]
        future_ts = pos.opened_at + timedelta(seconds=180)
        candle = _make_candle(high=103.0, low=99.0, close=101.0, timestamp=future_ts)
        await tracker.on_candle(candle)

        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.TIME_STOPPED
        assert closed[0].exit_price == 101.0  # bar close

    @pytest.mark.asyncio
    async def test_eod_close_all(self) -> None:
        """close_all_eod() closes all remaining open positions."""
        tracker = CounterfactualTracker()
        signal1 = _make_signal(symbol="AAPL")
        signal2 = _make_signal(symbol="TSLA")
        tracker.track(signal1, "test", RejectionStage.SHADOW)
        tracker.track(signal2, "test", RejectionStage.SHADOW)

        assert len(tracker.get_open_positions()) == 2

        await tracker.close_all_eod()

        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 2
        assert all(p.exit_reason == FillExitReason.EOD_CLOSED for p in closed)

    @pytest.mark.asyncio
    async def test_theoretical_pnl_and_r_multiple(self) -> None:
        """Closed position has correct P&L and R-multiple."""
        tracker = CounterfactualTracker()
        signal = _make_signal(entry_price=100.0, stop_price=95.0, target_prices=(110.0,))
        tracker.track(signal, "test", RejectionStage.SHADOW)

        candle = _make_candle(high=112.0, low=99.0, close=111.0)
        await tracker.on_candle(candle)

        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        pos = closed[0]
        assert pos.theoretical_pnl == 10.0  # 110 - 100
        assert pos.theoretical_r_multiple == 2.0  # 10 / (100 - 95)


class TestCounterfactualTrackerBackfill:
    """Tests for IntradayCandleStore backfill at position open."""

    def test_backfill_closes_immediately_if_stop_hit(self) -> None:
        """Mock candle store with bars that breach stop → closed immediately."""
        store = MagicMock()
        store.has_bars.return_value = True
        store.get_bars.return_value = [
            CandleBar(
                timestamp=datetime.now(UTC),
                open=100.0,
                high=101.0,
                low=93.0,  # Below stop of 95
                close=94.0,
                volume=500,
            ),
        ]

        tracker = CounterfactualTracker(candle_store=store)
        signal = _make_signal(entry_price=100.0, stop_price=95.0, target_prices=(110.0,))
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        # Position was closed during backfill
        assert len(tracker.get_open_positions()) == 0
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.STOPPED_OUT
        assert closed[0].exit_price == 95.0

    def test_backfill_no_bars_opens_normally(self) -> None:
        """Candle store has no bars → position opens, forward monitoring only."""
        store = MagicMock()
        store.has_bars.return_value = False

        tracker = CounterfactualTracker(candle_store=store)
        signal = _make_signal()
        pid = tracker.track(signal, "test", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        assert len(tracker.get_open_positions()) == 1
        store.get_bars.assert_not_called()

    def test_backfill_multiple_bars_processes_in_order(self) -> None:
        """Backfill with multiple bars processes them sequentially."""
        ts = datetime.now(UTC)
        store = MagicMock()
        store.has_bars.return_value = True
        store.get_bars.return_value = [
            CandleBar(
                timestamp=ts,
                open=100.0, high=103.0, low=99.0, close=102.0, volume=100,
            ),
            CandleBar(
                timestamp=ts + timedelta(minutes=1),
                open=102.0, high=105.0, low=101.0, close=104.0, volume=100,
            ),
        ]

        tracker = CounterfactualTracker(candle_store=store)
        signal = _make_signal(entry_price=100.0, stop_price=90.0, target_prices=(120.0,))
        pid = tracker.track(signal, "test", RejectionStage.SHADOW)
        assert pid is not None

        # Position still open (no exit triggered), but bars were processed
        positions = tracker.get_open_positions()
        assert len(positions) == 1
        assert positions[0].bars_monitored == 2
        assert positions[0].max_favorable_excursion == 5.0  # high 105 - entry 100
        assert positions[0].max_adverse_excursion == 1.0  # entry 100 - low 99


class TestCounterfactualTrackerTimeout:
    """Tests for the no-data timeout mechanism."""

    def test_check_timeouts_expires_stale_positions(self) -> None:
        """Position with no data within timeout → EXPIRED."""
        tracker = CounterfactualTracker(no_data_timeout_seconds=1)
        signal = _make_signal()
        pid = tracker.track(signal, "test", RejectionStage.SHADOW)
        assert pid is not None

        # Manually set opened_at to the past to simulate timeout
        pos = tracker._open_positions[pid]
        pos.opened_at = datetime.now(pos.opened_at.tzinfo) - timedelta(seconds=10)

        expired = tracker.check_timeouts()
        assert len(expired) == 1
        assert expired[0] == pid
        assert len(tracker.get_open_positions()) == 0


class TestRejectionStage:
    """Tests for the RejectionStage enum."""

    def test_all_stages_exist(self) -> None:
        """All expected rejection stages are defined."""
        assert RejectionStage.QUALITY_FILTER == "quality_filter"
        assert RejectionStage.POSITION_SIZER == "position_sizer"
        assert RejectionStage.RISK_MANAGER == "risk_manager"
        assert RejectionStage.SHADOW == "shadow"
        assert RejectionStage.BROKER_OVERFLOW == "broker_overflow"

    def test_broker_overflow_stage_has_correct_value(self) -> None:
        """BROKER_OVERFLOW enum value exists with correct string representation."""
        stage = RejectionStage.BROKER_OVERFLOW
        assert stage.value == "broker_overflow"
        assert str(stage) == "broker_overflow"
