"""Tests for Sprint 27.65 Session S3: Strategy Fixes.

Tests cover:
- R2G produces evaluations when prior_close is missing (telemetry)
- R2G gap-down detection with UM reference data (initialize_prior_closes)
- R2G state machine transitions with initialized prior_close
- Pattern strategy backfill_candles method
- Pattern strategy partial history evaluation telemetry
- Pattern strategy full history evaluation (normal path)
- Pattern strategy bar accumulation outside operating window
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from argus.core.config import RedToGreenConfig, StrategyConfig
from argus.core.events import CandleEvent, Side
from argus.strategies.pattern_strategy import (
    PatternBasedStrategy,
    candle_event_to_bar,
)
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule
from argus.strategies.red_to_green import (
    KeyLevelType,
    RedToGreenState,
    RedToGreenStrategy,
    RedToGreenSymbolState,
)
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_r2g_config(**overrides: object) -> RedToGreenConfig:
    """Build a RedToGreenConfig with sensible defaults."""
    defaults: dict[str, object] = {
        "strategy_id": "strat_red_to_green",
        "name": "Red-to-Green",
        "version": "1.0.0",
        "min_gap_down_pct": 0.02,
        "max_gap_down_pct": 0.10,
        "level_proximity_pct": 0.003,
        "min_level_test_bars": 2,
        "volume_confirmation_multiplier": 1.2,
        "max_chase_pct": 0.003,
        "max_level_attempts": 2,
        "target_1_r": 1.0,
        "target_2_r": 2.0,
        "time_stop_minutes": 20,
        "stop_buffer_pct": 0.001,
    }
    defaults.update(overrides)
    return RedToGreenConfig(**defaults)


def _make_candle(
    symbol: str = "TSLA",
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 50000,
    timestamp: datetime | None = None,
) -> CandleEvent:
    """Build a CandleEvent with sensible defaults (10:45 ET)."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp or datetime(2026, 3, 24, 14, 45, tzinfo=UTC),
    )


@dataclass
class MockReferenceData:
    """Minimal stand-in for SymbolReferenceData."""

    symbol: str = "TSLA"
    prev_close: float | None = 100.0
    avg_volume: float | None = 1_000_000.0
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    float_shares: float | None = None
    exchange: str | None = None
    is_otc: bool = False


class MockPattern(PatternModule):
    """Minimal PatternModule for testing."""

    def __init__(
        self,
        detection: PatternDetection | None = None,
        score_value: float = 75.0,
        lookback: int = 5,
    ) -> None:
        self._detection = detection
        self._score_value = score_value
        self._lookback = lookback

    @property
    def name(self) -> str:
        return "mock_pattern"

    @property
    def lookback_bars(self) -> int:
        return self._lookback

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        return self._detection

    def score(self, detection: PatternDetection) -> float:
        return self._score_value

    def get_default_params(self) -> dict[str, object]:
        return {"lookback": self._lookback}


BASE_TIME = datetime(2026, 3, 23, 14, 0, 0, tzinfo=UTC)  # 10:00 ET


def _make_pattern_candle(
    symbol: str = "AAPL",
    close: float = 150.0,
    time_offset_minutes: int = 0,
) -> CandleEvent:
    """Build a CandleEvent at BASE_TIME + offset."""
    ts = BASE_TIME + timedelta(minutes=time_offset_minutes)
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=close - 0.5,
        high=close + 0.5,
        low=close - 1.0,
        close=close,
        volume=10000,
        timestamp=ts,
    )


def _make_pattern_config(**overrides: object) -> StrategyConfig:
    """Build a StrategyConfig for pattern testing."""
    defaults = {
        "strategy_id": "test_pattern",
        "name": "Test Pattern Strategy",
        "version": "1.0.0",
        "operating_window": {
            "earliest_entry": "09:45",
            "latest_entry": "11:30",
            "force_close": "15:50",
        },
    }
    defaults.update(overrides)
    return StrategyConfig(**defaults)


# ---------------------------------------------------------------------------
# R1: R2G Tests
# ---------------------------------------------------------------------------


class TestR2GEvaluationsInLiveMode:
    """Verify R2G produces evaluations even when prior_close is missing."""

    @pytest.mark.asyncio
    async def test_r2g_produces_evaluations_without_prior_close(self) -> None:
        """R2G with prior_close=0 should record evaluation (not be silent)."""
        strategy = RedToGreenStrategy(config=_make_r2g_config())
        strategy.set_watchlist(["TSLA"])

        candle = _make_candle(symbol="TSLA")
        await strategy.on_candle(candle)

        # Should have recorded at least one evaluation event
        events = strategy.eval_buffer.query(limit=10)
        assert len(events) > 0
        # Should include a FAIL about missing prior_close
        condition_events = [
            e for e in events
            if e.event_type == EvaluationEventType.CONDITION_CHECK
            and "prior_close" in e.reason
        ]
        assert len(condition_events) >= 1

    @pytest.mark.asyncio
    async def test_r2g_produces_evaluations_after_initialization(self) -> None:
        """R2G with initialized prior_close produces gap evaluations."""
        strategy = RedToGreenStrategy(config=_make_r2g_config())
        strategy.set_watchlist(["TSLA", "AAPL"])

        ref_data = {
            "TSLA": MockReferenceData(symbol="TSLA", prev_close=100.0),
            "AAPL": MockReferenceData(symbol="AAPL", prev_close=150.0),
        }
        count = strategy.initialize_prior_closes(ref_data)
        assert count == 2

        # Gap down 3% on TSLA
        candle = _make_candle(symbol="TSLA", open_=97.0, close=97.5)
        await strategy.on_candle(candle)

        state = strategy._get_symbol_state("TSLA")
        assert state.state == RedToGreenState.GAP_DOWN_CONFIRMED

        events = strategy.eval_buffer.query(limit=20)
        state_events = [
            e for e in events
            if e.event_type == EvaluationEventType.STATE_TRANSITION
        ]
        assert len(state_events) >= 1


class TestR2GGapDownDetection:
    """Verify R2G detects gap-downs using UM reference data."""

    def test_initialize_prior_closes_from_reference_data(self) -> None:
        """initialize_prior_closes populates prior_close from UM data."""
        strategy = RedToGreenStrategy(config=_make_r2g_config())
        strategy.set_watchlist(["TSLA", "AAPL", "NVDA"])

        ref_data = {
            "TSLA": MockReferenceData(symbol="TSLA", prev_close=100.0),
            "AAPL": MockReferenceData(symbol="AAPL", prev_close=150.0),
            # NVDA missing from reference data
        }
        count = strategy.initialize_prior_closes(ref_data)

        assert count == 2
        assert strategy._get_symbol_state("TSLA").prior_close == 100.0
        assert strategy._get_symbol_state("AAPL").prior_close == 150.0
        # NVDA not initialized
        assert strategy._get_symbol_state("NVDA").prior_close == 0.0

    def test_initialize_prior_closes_skips_zero_price(self) -> None:
        """Symbols with prev_close=0 or None are skipped."""
        strategy = RedToGreenStrategy(config=_make_r2g_config())
        strategy.set_watchlist(["TSLA", "AAPL"])

        ref_data = {
            "TSLA": MockReferenceData(symbol="TSLA", prev_close=0.0),
            "AAPL": MockReferenceData(symbol="AAPL", prev_close=None),
        }
        count = strategy.initialize_prior_closes(ref_data)
        assert count == 0


class TestR2GStateMachineWithInitialization:
    """Verify state machine works after prior_close initialization."""

    @pytest.mark.asyncio
    async def test_watching_to_gap_confirmed_with_um_data(self) -> None:
        """After initialization, gap-down triggers state transition."""
        strategy = RedToGreenStrategy(config=_make_r2g_config())
        strategy.set_watchlist(["TSLA"])

        ref_data = {"TSLA": MockReferenceData(symbol="TSLA", prev_close=100.0)}
        strategy.initialize_prior_closes(ref_data)

        # 3% gap down
        candle = _make_candle(symbol="TSLA", open_=97.0, close=97.5)
        await strategy.on_candle(candle)

        state = strategy._get_symbol_state("TSLA")
        assert state.state == RedToGreenState.GAP_DOWN_CONFIRMED
        assert state.gap_pct == pytest.approx(-0.03)

    @pytest.mark.asyncio
    async def test_gap_up_stays_watching_with_um_data(self) -> None:
        """Gap up stays in WATCHING after initialization."""
        strategy = RedToGreenStrategy(config=_make_r2g_config())
        strategy.set_watchlist(["TSLA"])

        ref_data = {"TSLA": MockReferenceData(symbol="TSLA", prev_close=100.0)}
        strategy.initialize_prior_closes(ref_data)

        # 3% gap up
        candle = _make_candle(symbol="TSLA", open_=103.0, close=103.5)
        await strategy.on_candle(candle)

        state = strategy._get_symbol_state("TSLA")
        assert state.state == RedToGreenState.WATCHING


# ---------------------------------------------------------------------------
# R2: Pattern Strategy Tests
# ---------------------------------------------------------------------------


class TestPatternStrategyBackfill:
    """Tests for backfill_candles method."""

    def test_backfill_candles_prepends_history(self) -> None:
        """backfill_candles fills window with historical bars."""
        pattern = MockPattern(lookback=5)
        config = _make_pattern_config()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)

        bars = [
            CandleBar(
                timestamp=BASE_TIME + timedelta(minutes=i),
                open=150.0,
                high=151.0,
                low=149.0,
                close=150.5,
                volume=10000.0,
            )
            for i in range(5)
        ]

        added = strategy.backfill_candles("AAPL", bars)
        assert added == 5
        window = strategy._get_candle_window("AAPL")
        assert len(window) == 5

    def test_backfill_candles_respects_maxlen(self) -> None:
        """backfill with more bars than lookback truncates oldest."""
        pattern = MockPattern(lookback=3)
        config = _make_pattern_config()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)

        bars = [
            CandleBar(
                timestamp=BASE_TIME + timedelta(minutes=i),
                open=150.0,
                high=151.0,
                low=149.0,
                close=150.0 + i,
                volume=10000.0,
            )
            for i in range(6)
        ]

        added = strategy.backfill_candles("AAPL", bars)
        assert added == 3  # maxlen=3
        window = strategy._get_candle_window("AAPL")
        assert len(window) == 3
        # Should have the last 3 bars (newest)
        assert window[-1].close == 155.0

    def test_backfill_preserves_existing_live_bars(self) -> None:
        """backfill + existing live bars combined correctly."""
        pattern = MockPattern(lookback=5)
        config = _make_pattern_config()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        # Simulate 2 existing live bars
        window = strategy._get_candle_window("AAPL")
        for i in range(2):
            window.append(
                CandleBar(
                    timestamp=BASE_TIME + timedelta(minutes=100 + i),
                    open=160.0,
                    high=161.0,
                    low=159.0,
                    close=160.0 + i,
                    volume=20000.0,
                )
            )

        # Backfill 3 historical bars
        bars = [
            CandleBar(
                timestamp=BASE_TIME + timedelta(minutes=i),
                open=150.0,
                high=151.0,
                low=149.0,
                close=150.0,
                volume=10000.0,
            )
            for i in range(3)
        ]

        added = strategy.backfill_candles("AAPL", bars)
        assert added == 5
        window = strategy._get_candle_window("AAPL")
        assert len(window) == 5
        # Last 2 should be live bars
        assert window[-1].close == 161.0
        assert window[-2].close == 160.0


class TestPatternStrategyPartialHistory:
    """Tests for partial history evaluation telemetry."""

    @pytest.mark.asyncio
    async def test_partial_history_records_warmup_telemetry(self) -> None:
        """With 50%+ bars, records 'Warming up' evaluation event."""
        pattern = MockPattern(detection=None, lookback=10)
        config = _make_pattern_config()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        # Feed 5 bars (50% of 10) within operating window
        for i in range(5):
            await strategy.on_candle(_make_pattern_candle(time_offset_minutes=i))

        events = strategy.eval_buffer.query(limit=50)
        warmup_events = [
            e for e in events
            if "Warming up" in e.reason and "partial history" in e.reason
        ]
        assert len(warmup_events) >= 1

    @pytest.mark.asyncio
    async def test_insufficient_history_below_threshold(self) -> None:
        """Below 50%, records 'Insufficient history' evaluation."""
        pattern = MockPattern(detection=None, lookback=10)
        config = _make_pattern_config()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        # Feed 3 bars (30% of 10 — below 50% threshold of 5)
        for i in range(3):
            await strategy.on_candle(_make_pattern_candle(time_offset_minutes=i))

        events = strategy.eval_buffer.query(limit=50)
        insufficient_events = [
            e for e in events
            if "Insufficient history" in e.reason
        ]
        assert len(insufficient_events) >= 1


class TestPatternStrategyFullHistory:
    """Tests for normal full-history evaluation path."""

    @pytest.mark.asyncio
    async def test_full_history_runs_detection(self) -> None:
        """With full lookback, pattern detection runs and can produce signal."""
        det = PatternDetection(
            pattern_type="mock",
            confidence=80.0,
            entry_price=150.0,
            stop_price=148.0,
        )
        pattern = MockPattern(detection=det, score_value=82.0, lookback=3)
        config = _make_pattern_config()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        # Feed 3 candles to fill lookback
        for i in range(2):
            result = await strategy.on_candle(
                _make_pattern_candle(time_offset_minutes=i)
            )
            assert result is None

        result = await strategy.on_candle(
            _make_pattern_candle(time_offset_minutes=2)
        )
        assert result is not None
        assert result.entry_price == 150.0
        assert result.pattern_strength == 82.0

    @pytest.mark.asyncio
    async def test_bars_accumulate_outside_operating_window(self) -> None:
        """Candles before operating window still accumulate in deque."""
        pattern = MockPattern(detection=None, lookback=5)
        config = _make_pattern_config()
        strategy = PatternBasedStrategy(pattern=pattern, config=config)
        strategy.set_watchlist(["AAPL"])

        # Feed 5 candles at 08:00 ET (before 09:45 window)
        early_base = datetime(2026, 3, 23, 12, 0, 0, tzinfo=UTC)  # 08:00 ET
        for i in range(5):
            ts = early_base + timedelta(minutes=i)
            candle = CandleEvent(
                symbol="AAPL",
                timeframe="1m",
                open=149.5,
                high=150.5,
                low=149.0,
                close=150.0,
                volume=10000,
                timestamp=ts,
            )
            result = await strategy.on_candle(candle)
            assert result is None  # Outside window → None

        # Window should have accumulated 5 bars
        window = strategy._get_candle_window("AAPL")
        assert len(window) == 5, (
            f"Expected 5 bars accumulated outside window, got {len(window)}"
        )
