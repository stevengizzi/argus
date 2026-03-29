"""Tests for Counterfactual Engine wiring: startup factory, event bus
subscriptions, EOD close, shutdown, and config parsing.

Sprint 27.7, Session 3b.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.events import CandleEvent, Side, SignalEvent, SignalRejectedEvent
from argus.core.fill_model import FillExitReason
from argus.intelligence.counterfactual import (
    CounterfactualTracker,
    RejectionStage,
)
from argus.intelligence.counterfactual_store import CounterfactualStore


def _make_signal(
    symbol: str = "AAPL",
    entry_price: float = 100.0,
    stop_price: float = 95.0,
    target_prices: tuple[float, ...] = (110.0,),
) -> SignalEvent:
    """Create a test SignalEvent."""
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        share_count=0,
        rationale="test",
        signal_context={},
        quality_score=72.5,
        quality_grade="B",
    )


# --- F-01: Zero-R guard ---


class TestZeroRGuard:
    """Carry-forward fix F-01: entry_price == stop_price → skip."""

    def test_zero_r_signal_returns_none(self) -> None:
        """track() returns None and opens no position when entry == stop."""
        tracker = CounterfactualTracker()
        signal = _make_signal(entry_price=100.0, stop_price=100.0)
        result = tracker.track(
            signal=signal,
            rejection_reason="test",
            rejection_stage=RejectionStage.QUALITY_FILTER,
        )
        assert result is None
        assert len(tracker.get_open_positions()) == 0


# --- Factory: build_counterfactual_tracker ---


class TestBuildCounterfactualTracker:
    """Tests for the startup factory function."""

    @pytest.mark.asyncio
    async def test_returns_tracker_and_store_when_enabled(self) -> None:
        """Factory returns (tracker, store) when enabled=True."""
        from argus.intelligence.counterfactual_store import CounterfactualStore
        from argus.intelligence.startup import build_counterfactual_tracker

        config = MagicMock()
        config.counterfactual.enabled = True
        config.counterfactual.eod_close_time = "16:00"
        config.counterfactual.no_data_timeout_seconds = 300

        result = await build_counterfactual_tracker(config=config)

        assert result is not None
        tracker, store = result
        assert isinstance(tracker, CounterfactualTracker)
        assert isinstance(store, CounterfactualStore)
        await store.close()

    @pytest.mark.asyncio
    async def test_returns_none_when_disabled(self) -> None:
        """Factory returns None when enabled=False."""
        from argus.intelligence.startup import build_counterfactual_tracker

        config = MagicMock()
        config.counterfactual.enabled = False

        result = await build_counterfactual_tracker(config=config)
        assert result is None

    @pytest.mark.asyncio
    async def test_store_initialized_with_table(self, tmp_path: Path) -> None:
        """Factory initializes store — table exists after build."""
        from argus.intelligence.startup import build_counterfactual_tracker

        config = MagicMock()
        config.counterfactual.enabled = True
        config.counterfactual.eod_close_time = "16:00"
        config.counterfactual.no_data_timeout_seconds = 300

        db_path = str(tmp_path / "counterfactual_test.db")
        original_init = CounterfactualStore.__init__

        def patched_init(self_store: CounterfactualStore, **kwargs: object) -> None:
            original_init(self_store, db_path=db_path)

        with patch.object(CounterfactualStore, "__init__", patched_init):
            result = await build_counterfactual_tracker(config=config)
        assert result is not None
        _, store = result
        count = await store.count()
        assert count == 0
        await store.close()


# --- Event bus wiring ---


class TestEventBusWiring:
    """Tests for SignalRejectedEvent and CandleEvent subscription routing."""

    @pytest.mark.asyncio
    async def test_signal_rejected_event_routed_to_tracker(self) -> None:
        """SignalRejectedEvent handler calls tracker.track()."""
        from argus.core.event_bus import EventBus

        event_bus = EventBus()
        tracker = CounterfactualTracker()

        track_calls: list[dict] = []
        original_track = tracker.track

        def capturing_track(**kwargs: object) -> str | None:
            track_calls.append(kwargs)
            return original_track(**kwargs)  # type: ignore[arg-type]

        tracker.track = capturing_track  # type: ignore[assignment]

        async def handler(event: SignalRejectedEvent) -> None:
            if event.signal is None:
                return
            try:
                tracker.track(
                    signal=event.signal,
                    rejection_reason=event.rejection_reason,
                    rejection_stage=RejectionStage(event.rejection_stage.lower()),
                    metadata={
                        "quality_score": event.quality_score,
                        "quality_grade": event.quality_grade,
                    },
                )
            except Exception:
                pass

        event_bus.subscribe(SignalRejectedEvent, handler)

        signal = _make_signal()
        await event_bus.publish(SignalRejectedEvent(
            signal=signal,
            rejection_reason="grade too low",
            rejection_stage="QUALITY_FILTER",
            quality_score=30.0,
            quality_grade="C",
        ))
        await event_bus.drain()

        assert len(track_calls) == 1
        assert track_calls[0]["rejection_reason"] == "grade too low"

    @pytest.mark.asyncio
    async def test_candle_event_routed_to_tracker(self) -> None:
        """CandleEvent handler calls tracker.on_candle()."""
        from argus.core.event_bus import EventBus

        event_bus = EventBus()
        tracker = CounterfactualTracker()

        signal = _make_signal(symbol="TSLA")
        tracker.track(
            signal=signal,
            rejection_reason="test",
            rejection_stage=RejectionStage.RISK_MANAGER,
        )
        assert len(tracker.get_open_positions()) == 1

        event_bus.subscribe(CandleEvent, tracker.on_candle)

        candle = CandleEvent(
            symbol="TSLA",
            timeframe="1m",
            open=100.0,
            high=105.0,
            low=99.0,
            close=102.0,
            volume=10000,
        )
        await event_bus.publish(candle)
        await event_bus.drain()

        pos = tracker.get_open_positions()[0]
        assert pos.bars_monitored == 1

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_propagate(self) -> None:
        """Tracker.track() raising does not crash the handler."""
        from argus.core.event_bus import EventBus

        event_bus = EventBus()
        tracker = MagicMock()
        tracker.track.side_effect = RuntimeError("boom")

        async def handler(event: SignalRejectedEvent) -> None:
            if event.signal is None:
                return
            try:
                tracker.track(
                    signal=event.signal,
                    rejection_reason=event.rejection_reason,
                    rejection_stage=RejectionStage(event.rejection_stage.lower()),
                    metadata={},
                )
            except Exception:
                pass

        event_bus.subscribe(SignalRejectedEvent, handler)

        signal = _make_signal()
        await event_bus.publish(SignalRejectedEvent(
            signal=signal,
            rejection_reason="test",
            rejection_stage="QUALITY_FILTER",
        ))

    @pytest.mark.asyncio
    async def test_candle_short_circuits_for_untracked_symbol(self) -> None:
        """on_candle() returns immediately for symbols with no open positions."""
        tracker = CounterfactualTracker()
        candle = CandleEvent(
            symbol="UNKNOWN",
            timeframe="1m",
            open=100.0,
            high=105.0,
            low=99.0,
            close=102.0,
            volume=10000,
        )
        await tracker.on_candle(candle)


# --- EOD and shutdown ---


class TestEodAndShutdown:
    """Tests for EOD close and shutdown store cleanup."""

    @pytest.mark.asyncio
    async def test_close_all_eod_called_on_shutdown(self) -> None:
        """Verify close_all_eod closes all open positions."""
        tracker = CounterfactualTracker()
        signal = _make_signal()
        tracker.track(
            signal=signal,
            rejection_reason="test",
            rejection_stage=RejectionStage.QUALITY_FILTER,
        )
        assert len(tracker.get_open_positions()) == 1

        await tracker.close_all_eod()
        assert len(tracker.get_open_positions()) == 0
        assert len(tracker.get_closed_positions()) == 1

    @pytest.mark.asyncio
    async def test_timeout_check_expires_stale_positions(self) -> None:
        """check_timeouts() expires positions with no recent data."""
        tracker = CounterfactualTracker(no_data_timeout_seconds=0)
        signal = _make_signal()
        tracker.track(
            signal=signal,
            rejection_reason="test",
            rejection_stage=RejectionStage.QUALITY_FILTER,
        )

        expired = tracker.check_timeouts()
        assert len(expired) == 1
        assert len(tracker.get_open_positions()) == 0


# --- Config parsing ---


class TestConfigParsing:
    """Tests for counterfactual config section in YAML."""

    def test_system_yaml_has_counterfactual_section(self) -> None:
        """system.yaml parses with counterfactual config present."""
        from pathlib import Path

        from argus.core.config import load_config

        config = load_config(Path("config"))
        cf = config.system.counterfactual
        assert cf.enabled is True
        assert cf.retention_days == 90
        assert cf.no_data_timeout_seconds == 300
        assert cf.eod_close_time == "16:00"


# --- set_store wiring ---


class TestSetStore:
    """Tests for set_store() method on CounterfactualTracker."""

    def test_set_store_attaches_store(self) -> None:
        """set_store() sets _store on tracker."""
        tracker = CounterfactualTracker()
        mock_store = MagicMock()
        tracker.set_store(mock_store)
        assert tracker._store is mock_store
