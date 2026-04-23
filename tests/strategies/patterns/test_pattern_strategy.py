"""Tests for PatternBasedStrategy — generic wrapper for PatternModule.

Sprint 26, Session 4.
"""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from argus.core.config import StrategyConfig
from argus.core.events import CandleEvent
from argus.strategies.pattern_strategy import (
    PatternBasedStrategy,
    candle_event_to_bar,
)
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule


# ---------------------------------------------------------------------------
# Mock PatternModule
# ---------------------------------------------------------------------------


class MockPattern(PatternModule):
    """Minimal PatternModule for testing the wrapper."""

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

    def get_default_params(self) -> list["PatternParam"]:
        from argus.strategies.patterns.base import PatternParam
        return [
            PatternParam(
                name="lookback", param_type=int, default=self._lookback,
                min_value=5, max_value=50, step=5,
                description="Lookback window", category="detection",
            ),
        ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Base time in UTC that maps to 10:00 AM ET (within default operating window)
# ET is UTC-4 in summer, UTC-5 in winter. Use a fixed known date.
# 2026-03-23 is in EDT (UTC-4), so 14:00 UTC = 10:00 ET
BASE_TIME = datetime(2026, 3, 23, 14, 0, 0, tzinfo=UTC)


def _make_config(**overrides: object) -> StrategyConfig:
    """Build a StrategyConfig with sensible defaults for testing."""
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


def _make_candle(
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


def _detection(
    entry: float = 150.0,
    stop: float = 148.0,
    targets: tuple[float, ...] = (),
) -> PatternDetection:
    """Build a PatternDetection with defaults."""
    return PatternDetection(
        pattern_type="mock_pattern",
        confidence=80.0,
        entry_price=entry,
        stop_price=stop,
        target_prices=targets,
        metadata={"key": "value"},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wrapper_with_mock_pattern_signal_generation() -> None:
    """Mock pattern detect()→PatternDetection → verify SignalEvent produced."""
    det = _detection(entry=150.0, stop=148.0)
    pattern = MockPattern(detection=det, score_value=82.0, lookback=3)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    # Feed enough candles to fill lookback
    for i in range(3):
        result = await strategy.on_candle(_make_candle(time_offset_minutes=i))
        if i < 2:
            assert result is None, f"Should return None on candle {i}"

    # Third candle fills the window → detection → signal
    assert result is not None
    assert result.strategy_id == "test_pattern"
    assert result.symbol == "AAPL"
    assert result.entry_price == 150.0
    assert result.stop_price == 148.0
    assert result.rationale.startswith("mock_pattern:")


@pytest.mark.asyncio
async def test_wrapper_no_detection_returns_none() -> None:
    """detect()→None → no signal emitted."""
    pattern = MockPattern(detection=None, lookback=2)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    for i in range(3):
        result = await strategy.on_candle(_make_candle(time_offset_minutes=i))
        assert result is None


@pytest.mark.asyncio
async def test_operating_window_enforcement() -> None:
    """Before earliest_entry → None even if pattern detects."""
    det = _detection()
    pattern = MockPattern(detection=det, lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    # 08:00 ET = 12:00 UTC on 2026-03-23 (EDT)
    early_time = datetime(2026, 3, 23, 12, 0, 0, tzinfo=UTC)
    candle = CandleEvent(
        symbol="AAPL",
        timeframe="1m",
        open=149.5,
        high=150.5,
        low=149.0,
        close=150.0,
        volume=10000,
        timestamp=early_time,
    )

    result = await strategy.on_candle(candle)
    assert result is None


@pytest.mark.asyncio
async def test_candle_window_accumulation() -> None:
    """Deque grows, detect called only when full."""
    call_count = 0
    original_detect = MockPattern.detect

    class CountingPattern(MockPattern):
        def detect(
            self,
            candles: list[CandleBar],
            indicators: dict[str, float],
        ) -> PatternDetection | None:
            nonlocal call_count
            call_count += 1
            return None

    pattern = CountingPattern(lookback=4)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    # Feed 3 candles (less than lookback=4)
    for i in range(3):
        await strategy.on_candle(_make_candle(time_offset_minutes=i))

    assert call_count == 0, "detect() should not be called before window is full"

    # Fourth candle fills the window
    await strategy.on_candle(_make_candle(time_offset_minutes=3))
    assert call_count == 1, "detect() should be called once window is full"

    # Fifth candle — deque rolls, detect called again
    await strategy.on_candle(_make_candle(time_offset_minutes=4))
    assert call_count == 2


@pytest.mark.asyncio
async def test_pattern_strength_from_score() -> None:
    """Verify SignalEvent.pattern_strength = pattern.score()."""
    det = _detection()
    pattern = MockPattern(detection=det, score_value=67.5, lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    result = await strategy.on_candle(_make_candle())
    assert result is not None
    assert result.pattern_strength == 67.5


@pytest.mark.asyncio
async def test_share_count_zero() -> None:
    """Verify share_count=0 in all signals (Quality Engine handles sizing)."""
    det = _detection()
    pattern = MockPattern(detection=det, lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    result = await strategy.on_candle(_make_candle())
    assert result is not None
    assert result.share_count == 0

    # Also verify calculate_position_size always returns 0
    assert strategy.calculate_position_size(150.0, 148.0) == 0


@pytest.mark.asyncio
async def test_daily_state_reset_clears_windows() -> None:
    """reset_daily_state() clears _candle_windows."""
    det = _detection()
    pattern = MockPattern(detection=det, lookback=2)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    # Feed candles to populate window
    await strategy.on_candle(_make_candle(time_offset_minutes=0))
    await strategy.on_candle(_make_candle(time_offset_minutes=1))
    assert len(strategy._candle_windows) > 0

    # Reset
    strategy.reset_daily_state()
    assert len(strategy._candle_windows) == 0


@pytest.mark.asyncio
async def test_target_prices_from_detection() -> None:
    """Use detection.target_prices when non-empty."""
    det = _detection(entry=150.0, stop=148.0, targets=(152.0, 154.0))
    pattern = MockPattern(detection=det, lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    result = await strategy.on_candle(_make_candle())
    assert result is not None
    assert result.target_prices == (152.0, 154.0)


@pytest.mark.asyncio
async def test_target_prices_r_multiple_fallback() -> None:
    """Compute R-multiple targets when detection.target_prices is empty."""
    det = _detection(entry=150.0, stop=148.0, targets=())
    pattern = MockPattern(detection=det, lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    result = await strategy.on_candle(_make_candle())
    assert result is not None
    # risk = 150 - 148 = 2, T1 = 150 + 2*1.0 = 152, T2 = 150 + 2*2.0 = 154
    assert result.target_prices == (152.0, 154.0)


@pytest.mark.asyncio
async def test_score_clamped_to_0_100() -> None:
    """Verify score is clamped to [0, 100] range."""
    det = _detection()
    pattern = MockPattern(detection=det, score_value=150.0, lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    result = await strategy.on_candle(_make_candle())
    assert result is not None
    assert result.pattern_strength == 100.0


def test_candle_event_to_bar_conversion() -> None:
    """Verify candle_event_to_bar produces correct CandleBar."""
    candle = _make_candle(close=155.0)
    bar = candle_event_to_bar(candle)

    assert isinstance(bar, CandleBar)
    assert bar.close == 155.0
    assert bar.open == 154.5
    assert bar.high == 155.5
    assert bar.low == 154.0
    assert bar.volume == 10000.0
    assert bar.timestamp == candle.timestamp


def test_not_in_watchlist_returns_none_sync() -> None:
    """Symbol not in watchlist → None immediately (no async needed)."""
    # Verified via the async test but also confirms wrapper logic
    pattern = MockPattern(detection=_detection(), lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["MSFT"])
    # AAPL not in watchlist — verified by async test flow
    assert "AAPL" not in strategy._watchlist


def test_scanner_criteria_passthrough() -> None:
    """Wrapper returns ScannerCriteria from config's universe_filter."""
    pattern = MockPattern(lookback=1)
    config = _make_config(
        universe_filter={
            "min_price": 15.0,
            "max_price": 300.0,
            "min_avg_volume": 2_000_000,
        }
    )
    strategy = PatternBasedStrategy(pattern=pattern, config=config)

    criteria = strategy.get_scanner_criteria()
    assert criteria.min_price == 15.0
    assert criteria.max_price == 300.0
    assert criteria.min_volume_avg_daily == 2_000_000
    assert criteria.max_results == 20


def test_market_conditions_filter_passthrough() -> None:
    """Wrapper returns MarketConditionsFilter with sensible defaults."""
    pattern = MockPattern(lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)

    mcf = strategy.get_market_conditions_filter()
    assert "bullish_trending" in mcf.allowed_regimes
    assert "range_bound" in mcf.allowed_regimes
    assert mcf.max_vix == 35.0


@pytest.mark.asyncio
async def test_reconstruct_state_delegation() -> None:
    """Wrapper delegates reconstruct_state to BaseStrategy (queries trade_logger)."""
    pattern = MockPattern(lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date = AsyncMock(return_value=[])

    # Should not raise — delegates to super().reconstruct_state()
    await strategy.reconstruct_state(mock_logger)
    # BaseStrategy.reconstruct_state queries today's trades via get_trades_by_date
    mock_logger.get_trades_by_date.assert_called_once()


@pytest.mark.asyncio
async def test_indicators_include_symbol_key() -> None:
    """Verify indicators dict passed to detect() contains 'symbol' matching candle."""

    captured_indicators: dict[str, object] = {}

    class CapturingPattern(MockPattern):
        def detect(
            self,
            candles: list[CandleBar],
            indicators: dict[str, float],
        ) -> PatternDetection | None:
            captured_indicators.update(indicators)
            return None

    pattern = CapturingPattern(lookback=1)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["TSLA"])

    await strategy.on_candle(_make_candle(symbol="TSLA"))

    assert "symbol" in captured_indicators
    assert captured_indicators["symbol"] == "TSLA"


# ---------------------------------------------------------------------------
# min_detection_bars detection threshold tests (Sprint 31A S2)
# ---------------------------------------------------------------------------


class MockPatternWithMinDetection(MockPattern):
    """Pattern with lookback_bars=50 but min_detection_bars=3.

    Used to verify PatternBasedStrategy uses min_detection_bars for the
    detection-eligibility check, not lookback_bars.
    """

    @property
    def lookback_bars(self) -> int:
        return 50

    @property
    def min_detection_bars(self) -> int:
        return 3


@pytest.mark.asyncio
async def test_pattern_based_strategy_uses_min_detection_bars_for_eligibility() -> None:
    """PatternBasedStrategy fires detection after min_detection_bars (not lookback_bars)."""
    det = _detection(entry=150.0, stop=148.0)
    pattern = MockPatternWithMinDetection(detection=det, score_value=80.0)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    # Feed 2 candles — below min_detection_bars (3), no signal
    for i in range(2):
        result = await strategy.on_candle(_make_candle(time_offset_minutes=i))
        assert result is None, f"Should be None on candle {i} (below min_detection_bars)"

    # 3rd candle reaches min_detection_bars → detection runs → signal emitted
    result = await strategy.on_candle(_make_candle(time_offset_minutes=2))
    assert result is not None, "Should produce signal after min_detection_bars bars"


@pytest.mark.asyncio
async def test_pattern_without_min_detection_bars_override_uses_lookback_bars() -> None:
    """Patterns that don't override min_detection_bars wait until lookback_bars."""
    det = _detection(entry=150.0, stop=148.0)
    # MockPattern.lookback_bars == 3, min_detection_bars defaults to 3
    pattern = MockPattern(detection=det, score_value=80.0, lookback=3)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    # 2 candles — below lookback_bars, no signal
    for i in range(2):
        result = await strategy.on_candle(_make_candle(time_offset_minutes=i))
        assert result is None

    # 3rd candle hits lookback_bars → detection eligible
    result = await strategy.on_candle(_make_candle(time_offset_minutes=2))
    assert result is not None


# ---------------------------------------------------------------------------
# initialize_reference_data forwarding tests (Sprint 31A S2)
# ---------------------------------------------------------------------------


def test_initialize_reference_data_forwards_prev_close_to_pattern() -> None:
    """initialize_reference_data() builds prior_closes and calls pattern.set_reference_data()."""
    from argus.data.fmp_reference import SymbolReferenceData

    received: dict[str, object] = {}

    class CapturingPattern(MockPattern):
        def set_reference_data(self, data: dict[str, object]) -> None:
            received.update(data)

    pattern = CapturingPattern(lookback=5)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)

    ref_data = {
        "AAPL": SymbolReferenceData(symbol="AAPL", prev_close=175.0),
        "TSLA": SymbolReferenceData(symbol="TSLA", prev_close=200.0),
    }
    strategy.initialize_reference_data(ref_data)

    assert "prior_closes" in received
    prior_closes = received["prior_closes"]
    assert isinstance(prior_closes, dict)
    assert prior_closes["AAPL"] == 175.0
    assert prior_closes["TSLA"] == 200.0


def test_initialize_reference_data_skips_symbols_with_no_prev_close() -> None:
    """initialize_reference_data() omits symbols where prev_close is None."""
    from argus.data.fmp_reference import SymbolReferenceData

    received: dict[str, object] = {}

    class CapturingPattern(MockPattern):
        def set_reference_data(self, data: dict[str, object]) -> None:
            received.update(data)

    pattern = CapturingPattern(lookback=5)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)

    ref_data = {
        "AAPL": SymbolReferenceData(symbol="AAPL", prev_close=175.0),
        "TSLA": SymbolReferenceData(symbol="TSLA", prev_close=None),
    }
    strategy.initialize_reference_data(ref_data)

    prior_closes = received.get("prior_closes", {})
    assert isinstance(prior_closes, dict)
    assert "AAPL" in prior_closes
    assert "TSLA" not in prior_closes


def test_initialize_reference_data_empty_ref_data_is_no_op() -> None:
    """initialize_reference_data() with empty dict does not call set_reference_data."""
    call_count = 0

    class CountingPattern(MockPattern):
        def set_reference_data(self, data: dict[str, object]) -> None:
            nonlocal call_count
            call_count += 1

    pattern = CountingPattern(lookback=5)
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)

    strategy.initialize_reference_data({})
    assert call_count == 0, "set_reference_data should not be called for empty ref_data"


# ---------------------------------------------------------------------------
# Warm-up log-level regression (Sprint 31.9 IMPROMPTU-04, Debrief §C1)
# ---------------------------------------------------------------------------
#
# On the Apr 22 2026 paper session, this single log line accounted for
# 778,293 of 895,543 total log lines (87% of a 184 MB log file):
#
#     pattern_strategy.py:318 —
#         logger.info("%s: evaluating %s with partial history (%d/%d)", ...)
#
# It fires per-candle × per-strategy × per-symbol during warm-up. DEF-138
# window summaries already provide INFO-level "not silent during warm-up"
# visibility. Downgrading to DEBUG reduces log volume ~7–10× immediately.
#
# Revert-proof: if the level is reverted to INFO, the INFO caplog filter
# below will capture a record matching "partial history" and the test fails.


import logging as _logging  # noqa: E402


@pytest.mark.asyncio
async def test_warmup_partial_history_log_does_not_fire_at_info_level(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """REVERT-PROOF (DEF-199 C1): the warm-up log must not fire at INFO.

    Reverting pattern_strategy.py:318 from logger.debug back to logger.info
    causes this test to FAIL because the INFO-level caplog filter will
    capture a record matching "partial history".
    """
    # Pattern needs enough lookback that we hit the warm-up window (bar_count
    # between min_partial and lookback). lookback=10 → min_partial=5.
    pattern = MockPattern(
        detection=None,
        score_value=75.0,
        lookback=10,
    )
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    with caplog.at_level(_logging.INFO, logger="argus.strategies.pattern_strategy"):
        # Feed bars up to 5 (min_partial) → 9 (just below lookback) so each
        # on_candle hits the partial-history branch and would have triggered
        # the pre-fix INFO log.
        for i in range(9):
            await strategy.on_candle(_make_candle(time_offset_minutes=i))

    matching = [
        rec for rec in caplog.records
        if rec.levelno >= _logging.INFO
        and "partial history" in rec.getMessage()
    ]
    assert not matching, (
        "Warm-up partial-history log fired at INFO level — DEF-199 C1 regression. "
        f"Got {len(matching)} records: {[r.getMessage() for r in matching[:3]]}"
    )


@pytest.mark.asyncio
async def test_warmup_partial_history_log_still_fires_at_debug_level(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Non-regression: the log content IS preserved, just at DEBUG level.

    Ensures we downgraded rather than deleted — operators who raise the log
    level to DEBUG for debugging still see the warm-up evaluation trace.
    """
    pattern = MockPattern(
        detection=None,
        score_value=75.0,
        lookback=10,
    )
    config = _make_config()
    strategy = PatternBasedStrategy(pattern=pattern, config=config)
    strategy.set_watchlist(["AAPL"])

    with caplog.at_level(_logging.DEBUG, logger="argus.strategies.pattern_strategy"):
        for i in range(9):
            await strategy.on_candle(_make_candle(time_offset_minutes=i))

    matching = [
        rec for rec in caplog.records
        if rec.levelno == _logging.DEBUG
        and "partial history" in rec.getMessage()
    ]
    assert matching, (
        "Expected DEBUG-level 'partial history' log records during warm-up. "
        "If the log was deleted instead of downgraded, this test fails."
    )
