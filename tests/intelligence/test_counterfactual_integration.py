"""Full lifecycle integration tests for the counterfactual pipeline.

Tests the complete flow: rejection → tracking → candle monitoring →
position close → filter accuracy query.

Sprint 27.7, Session 4.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from argus.core.events import CandleEvent, SignalEvent, Side
from argus.core.fill_model import FillExitReason
from argus.intelligence.counterfactual import (
    CounterfactualTracker,
    RejectionStage,
)
from argus.intelligence.counterfactual_store import CounterfactualStore
from argus.intelligence.filter_accuracy import compute_filter_accuracy


def _make_signal(
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
    entry_price: float = 100.0,
    stop_price: float = 95.0,
    target_prices: tuple[float, ...] = (110.0,),
    time_stop_seconds: int | None = None,
    quality_score: float = 72.5,
    quality_grade: str = "B",
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
        signal_context={},
        quality_score=quality_score,
        quality_grade=quality_grade,
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


@pytest.fixture
async def store(tmp_path: Path) -> CounterfactualStore:
    """Provide an initialized CounterfactualStore."""
    s = CounterfactualStore(str(tmp_path / "cf_integration.db"))
    await s.initialize()
    yield s  # type: ignore[misc]
    await s.close()


@pytest.fixture
def tracker() -> CounterfactualTracker:
    """Provide a CounterfactualTracker without candle store."""
    return CounterfactualTracker()


class TestFullLifecycle:
    """Rejection → tracking → monitoring → close → accuracy query."""

    @pytest.mark.asyncio
    async def test_rejection_stop_hit_correct_rejection(
        self, tracker: CounterfactualTracker, store: CounterfactualStore
    ) -> None:
        """Full lifecycle: rejection → candle triggers stop → correct rejection."""
        # Open position from rejected signal
        signal = _make_signal(entry_price=100.0, stop_price=95.0, target_prices=(110.0,))
        pid = tracker.track(signal, "grade too low", RejectionStage.QUALITY_FILTER)
        assert pid is not None

        # Feed candle that triggers stop (low below stop)
        candle = _make_candle(high=101.0, low=94.0, close=94.5)
        await tracker.on_candle(candle)

        # Verify position closed as STOPPED_OUT
        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.STOPPED_OUT
        assert closed[0].theoretical_pnl is not None
        assert closed[0].theoretical_pnl < 0

        # Persist to store for accuracy query
        await store.write_open(closed[0])
        await store.write_close(closed[0])

        # Query accuracy
        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.total_positions == 1
        assert report.by_stage[0].correct_rejections == 1
        assert report.by_stage[0].accuracy == 1.0

    @pytest.mark.asyncio
    async def test_rejection_target_hit_incorrect_rejection(
        self, tracker: CounterfactualTracker, store: CounterfactualStore
    ) -> None:
        """Full lifecycle: rejection → candle triggers target → incorrect rejection."""
        signal = _make_signal(entry_price=100.0, stop_price=95.0, target_prices=(105.0,))
        pid = tracker.track(signal, "shares zero", RejectionStage.POSITION_SIZER)
        assert pid is not None

        # Feed candle that triggers target (high above target)
        candle = _make_candle(high=106.0, low=99.0, close=105.5)
        await tracker.on_candle(candle)

        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.TARGET_HIT
        assert closed[0].theoretical_pnl is not None
        assert closed[0].theoretical_pnl > 0

        await store.write_open(closed[0])
        await store.write_close(closed[0])

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.by_stage[0].incorrect_rejections == 1
        assert report.by_stage[0].accuracy == 0.0


class TestEODCloseLifecycle:
    """Rejection → no trigger → EOD close → mark-to-market P&L."""

    @pytest.mark.asyncio
    async def test_eod_close_marks_to_market(
        self, tracker: CounterfactualTracker, store: CounterfactualStore
    ) -> None:
        """Position not hitting stop or target gets EOD close with MTM P&L."""
        signal = _make_signal(entry_price=100.0, stop_price=95.0, target_prices=(110.0,))
        pid = tracker.track(signal, "risk limit", RejectionStage.RISK_MANAGER)
        assert pid is not None

        # Feed candles that don't trigger stop or target
        candle1 = _make_candle(high=103.0, low=97.0, close=101.0)
        await tracker.on_candle(candle1)

        candle2 = _make_candle(high=104.0, low=98.0, close=102.0)
        await tracker.on_candle(candle2)

        # Verify still open
        assert len(tracker.get_open_positions()) == 1

        # Close at EOD
        await tracker.close_all_eod()

        closed = tracker.get_closed_positions()
        assert len(closed) == 1
        assert closed[0].exit_reason == FillExitReason.EOD_CLOSED
        # MTM P&L based on last known price (102.0) - entry (100.0) = 2.0
        assert closed[0].theoretical_pnl is not None
        assert closed[0].theoretical_pnl > 0

        # Persist and check accuracy
        await store.write_open(closed[0])
        await store.write_close(closed[0])

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.total_positions == 1
        # Positive P&L at EOD = incorrect rejection
        assert report.by_stage[0].incorrect_rejections == 1


class TestMultipleRejectionsAccuracy:
    """Multiple rejections across stages with known outcomes."""

    @pytest.mark.asyncio
    async def test_mixed_outcomes_per_stage(
        self, tracker: CounterfactualTracker, store: CounterfactualStore
    ) -> None:
        """3 rejections across stages, verify per-stage accuracy."""
        # Quality filter: will hit target (incorrect)
        sig_qf = _make_signal(
            symbol="AAPL", entry_price=100.0, stop_price=95.0,
            target_prices=(105.0,), quality_grade="C",
        )
        pid1 = tracker.track(sig_qf, "grade too low", RejectionStage.QUALITY_FILTER)

        # Position sizer: will hit stop (correct)
        sig_ps = _make_signal(
            symbol="NVDA", entry_price=200.0, stop_price=190.0,
            target_prices=(220.0,), quality_grade="B",
        )
        pid2 = tracker.track(sig_ps, "shares zero", RejectionStage.POSITION_SIZER)

        # Risk manager: will hit stop (correct)
        sig_rm = _make_signal(
            symbol="TSLA", entry_price=150.0, stop_price=140.0,
            target_prices=(170.0,), quality_grade="B+",
        )
        pid3 = tracker.track(sig_rm, "daily limit", RejectionStage.RISK_MANAGER)

        # Feed candles:
        # AAPL hits target
        await tracker.on_candle(_make_candle(symbol="AAPL", high=106.0, low=99.0, close=105.0))
        # NVDA hits stop
        await tracker.on_candle(_make_candle(symbol="NVDA", high=201.0, low=189.0, close=191.0))
        # TSLA hits stop
        await tracker.on_candle(_make_candle(symbol="TSLA", high=151.0, low=139.0, close=141.0))

        # All should be closed
        closed = tracker.get_closed_positions()
        assert len(closed) == 3

        # Persist all
        for pos in closed:
            await store.write_open(pos)
            await store.write_close(pos)

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.total_positions == 3

        stage_map = {b.category: b for b in report.by_stage}
        assert stage_map["quality_filter"].accuracy == 0.0
        assert stage_map["position_sizer"].accuracy == 1.0
        assert stage_map["risk_manager"].accuracy == 1.0


class TestConfigDisabled:
    """Verify nothing happens when counterfactual is disabled."""

    @pytest.mark.asyncio
    async def test_empty_report_when_no_positions_tracked(
        self, store: CounterfactualStore
    ) -> None:
        """No positions tracked → empty accuracy report."""
        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.total_positions == 0
        assert report.by_stage == []
        assert report.by_reason == []
        assert report.by_grade == []
        assert report.by_strategy == []
        assert report.by_regime == []
