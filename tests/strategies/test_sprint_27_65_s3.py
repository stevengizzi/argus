"""Tests for Sprint 27.65 S3: R2G prior_close initialization + pattern strategy warm-up.

Tests cover:
- R2G `initialize_prior_closes()` from reference data
- R2G produces evaluation telemetry when prior_close is missing
- R2G state machine transitions with prior_close set
- Pattern strategy `backfill_candles()` prepend + overflow
- Pattern strategy evaluation with partial history (warm-up)
- Pattern strategy accumulation before operating window
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.events import CandleEvent
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule
from argus.strategies.red_to_green import (
    RedToGreenState,
    RedToGreenStrategy,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_r2g_config(**overrides: object) -> MagicMock:
    """Build a RedToGreenConfig-like object with defaults."""
    from argus.core.config import RedToGreenConfig

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


def _make_r2g(config: object | None = None) -> RedToGreenStrategy:
    """Build a RedToGreenStrategy with default config."""
    cfg = config or _make_r2g_config()
    return RedToGreenStrategy(config=cfg)


def _make_candle(
    symbol: str = "TSLA",
    open_: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 50000,
    ts: datetime | None = None,
) -> CandleEvent:
    """Build a CandleEvent with sensible defaults."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=ts or datetime(2026, 3, 24, 14, 45, tzinfo=UTC),  # 10:45 ET
    )


@dataclass
class FakeRefData:
    """Minimal stand-in for SymbolReferenceData."""

    prev_close: float | None = None


# ---------------------------------------------------------------------------
# R2G Prior Close Initialization Tests
# ---------------------------------------------------------------------------


class TestR2GPriorCloseInit:
    """Tests for R2G initialize_prior_closes()."""

    def test_initializes_prior_close_from_reference_data(self) -> None:
        """Symbols with valid prev_close in reference data get initialized."""
        strategy = _make_r2g()
        strategy.set_watchlist(["TSLA", "AAPL", "NVDA"], source="test")

        ref_data = {
            "TSLA": FakeRefData(prev_close=180.0),
            "AAPL": FakeRefData(prev_close=150.0),
            "NVDA": FakeRefData(prev_close=120.0),
        }

        count = strategy.initialize_prior_closes(ref_data)  # type: ignore[arg-type]

        assert count == 3
        # Verify internal state updated
        assert strategy._get_symbol_state("TSLA").prior_close == 180.0
        assert strategy._get_symbol_state("AAPL").prior_close == 150.0
        assert strategy._get_symbol_state("NVDA").prior_close == 120.0

    def test_skips_symbols_with_no_reference(self) -> None:
        """Symbols not in reference_data are skipped."""
        strategy = _make_r2g()
        strategy.set_watchlist(["TSLA", "AAPL"], source="test")

        ref_data = {
            "TSLA": FakeRefData(prev_close=180.0),
            # AAPL not in ref_data
        }

        count = strategy.initialize_prior_closes(ref_data)  # type: ignore[arg-type]

        assert count == 1
        assert strategy._get_symbol_state("TSLA").prior_close == 180.0
        assert strategy._get_symbol_state("AAPL").prior_close == 0.0  # default

    def test_skips_zero_and_none_prev_close(self) -> None:
        """Symbols with None or zero prev_close are skipped."""
        strategy = _make_r2g()
        strategy.set_watchlist(["TSLA", "AAPL", "MSFT"], source="test")

        ref_data = {
            "TSLA": FakeRefData(prev_close=None),
            "AAPL": FakeRefData(prev_close=0.0),
            "MSFT": FakeRefData(prev_close=-1.0),
        }

        count = strategy.initialize_prior_closes(ref_data)  # type: ignore[arg-type]

        assert count == 0

    def test_only_initializes_watchlist_symbols(self) -> None:
        """Symbols in ref_data but NOT in watchlist are ignored."""
        strategy = _make_r2g()
        strategy.set_watchlist(["TSLA"], source="test")

        ref_data = {
            "TSLA": FakeRefData(prev_close=180.0),
            "AAPL": FakeRefData(prev_close=150.0),  # Not in watchlist
        }

        count = strategy.initialize_prior_closes(ref_data)  # type: ignore[arg-type]

        assert count == 1


# ---------------------------------------------------------------------------
# R2G Telemetry: Evaluation recorded when prior_close missing
# ---------------------------------------------------------------------------


class TestR2GEvaluationTelemetry:
    """Tests for R2G evaluation telemetry on prior_close missing."""

    @pytest.mark.asyncio
    async def test_r2g_records_evaluation_when_no_prior_close(self) -> None:
        """R2G records a CONDITION_CHECK FAIL when prior_close is 0."""
        strategy = _make_r2g()
        strategy.set_watchlist(["TSLA"], source="test")

        candle = _make_candle(symbol="TSLA")
        evals_before = len(strategy.eval_buffer)

        await strategy.on_candle(candle)

        # Should have recorded at least one evaluation
        assert len(strategy.eval_buffer) > evals_before
        events = strategy.eval_buffer.snapshot()
        prior_close_evals = [e for e in events if "prior_close" in e.reason.lower()]
        assert len(prior_close_evals) > 0

    @pytest.mark.asyncio
    async def test_r2g_state_machine_with_prior_close_set(self) -> None:
        """With prior_close set, R2G transitions to GAP_DOWN_CONFIRMED for valid gap."""
        strategy = _make_r2g()
        strategy.set_watchlist(["TSLA"], source="test")
        state = strategy._get_symbol_state("TSLA")
        state.prior_close = 100.0

        # 5% gap down: open at 95 vs prior_close 100
        candle = _make_candle(symbol="TSLA", open_=95.0, close=95.5, low=94.5, high=96.0)

        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.GAP_DOWN_CONFIRMED

    @pytest.mark.asyncio
    async def test_r2g_stays_watching_for_gap_up(self) -> None:
        """Gap up does not trigger gap-down confirmation."""
        strategy = _make_r2g()
        strategy.set_watchlist(["TSLA"], source="test")
        state = strategy._get_symbol_state("TSLA")
        state.prior_close = 100.0

        # Gap UP: open at 105 vs prior 100
        candle = _make_candle(symbol="TSLA", open_=105.0, close=105.5)
        await strategy.on_candle(candle)

        assert state.state == RedToGreenState.WATCHING


# ---------------------------------------------------------------------------
# Pattern Strategy: backfill_candles Tests
# ---------------------------------------------------------------------------


class _StubPattern(PatternModule):
    """Minimal PatternModule for testing PatternBasedStrategy."""

    @property
    def name(self) -> str:
        return "stub_pattern"

    @property
    def lookback_bars(self) -> int:
        return 10

    def detect(
        self, bars: list[CandleBar], indicators: dict[str, float] | None = None
    ) -> PatternDetection | None:
        return None

    def score(self, detection: PatternDetection, bars: list[CandleBar]) -> float:
        return 50.0

    def get_default_params(self) -> dict[str, object]:
        return {}


def _make_pattern_strategy(
    lookback: int = 10,
    earliest: str = "09:45",
    latest: str = "15:00",
) -> "PatternBasedStrategy":
    """Build a PatternBasedStrategy with a stub pattern."""
    from argus.core.config import OperatingWindow, StrategyConfig
    from argus.strategies.pattern_strategy import PatternBasedStrategy

    pattern = _StubPattern()
    # Override lookback if needed
    if lookback != 10:
        type(pattern).lookback_bars = property(lambda self, lb=lookback: lb)  # type: ignore[assignment]

    config = StrategyConfig(
        strategy_id="test_pattern",
        name="Test Pattern Strategy",
        version="1.0.0",
        operating_window=OperatingWindow(
            earliest_entry=earliest,
            latest_entry=latest,
            force_close="15:50",
        ),
    )

    return PatternBasedStrategy(pattern=pattern, config=config)


def _make_bar(
    ts: datetime | None = None,
    close: float = 100.0,
) -> CandleBar:
    """Create a CandleBar."""
    return CandleBar(
        timestamp=ts or datetime(2026, 3, 24, 15, 0, tzinfo=UTC),
        open=100.0,
        high=101.0,
        low=99.0,
        close=close,
        volume=10000.0,
    )


class TestPatternStrategyBackfill:
    """Tests for PatternBasedStrategy.backfill_candles()."""

    def test_backfill_populates_empty_window(self) -> None:
        """Backfilling an empty window adds bars correctly."""
        strategy = _make_pattern_strategy(lookback=10)
        strategy.set_watchlist(["AAPL"], source="test")

        bars = [_make_bar(close=100.0 + i) for i in range(8)]
        added = strategy.backfill_candles("AAPL", bars)

        assert added == 8
        window = strategy._get_candle_window("AAPL")
        assert len(window) == 8

    def test_backfill_preserves_existing_bars(self) -> None:
        """Existing live bars are kept at the end after backfill."""
        strategy = _make_pattern_strategy(lookback=10)
        strategy.set_watchlist(["AAPL"], source="test")

        # Add 3 existing live bars
        window = strategy._get_candle_window("AAPL")
        for i in range(3):
            window.append(_make_bar(close=200.0 + i))

        # Backfill 5 historical bars
        hist_bars = [_make_bar(close=100.0 + i) for i in range(5)]
        added = strategy.backfill_candles("AAPL", hist_bars)

        assert added == 8  # 5 hist + 3 existing
        assert len(window) == 8
        # Last bar should be the latest live bar
        assert window[-1].close == 202.0

    def test_backfill_respects_maxlen(self) -> None:
        """Overflow is truncated from the oldest end."""
        strategy = _make_pattern_strategy(lookback=5)
        strategy.set_watchlist(["AAPL"], source="test")

        # Backfill 10 bars into a maxlen=5 window
        bars = [_make_bar(close=100.0 + i) for i in range(10)]
        added = strategy.backfill_candles("AAPL", bars)

        assert added == 5  # Only most recent 5 fit
        window = strategy._get_candle_window("AAPL")
        assert len(window) == 5
        # Should keep the 5 most recent
        assert window[0].close == 105.0
        assert window[-1].close == 109.0

    def test_backfill_empty_bars_list(self) -> None:
        """Empty backfill list is a no-op."""
        strategy = _make_pattern_strategy(lookback=10)
        strategy.set_watchlist(["AAPL"], source="test")

        added = strategy.backfill_candles("AAPL", [])
        assert added == 0


# ---------------------------------------------------------------------------
# Pattern Strategy: Partial History Evaluation
# ---------------------------------------------------------------------------


class TestPatternStrategyWarmUp:
    """Tests for partial history evaluation during warm-up."""

    @pytest.mark.asyncio
    async def test_candles_accumulate_before_operating_window(self) -> None:
        """Candles before operating window still accumulate in the deque."""
        strategy = _make_pattern_strategy(lookback=10, earliest="10:00", latest="15:00")
        strategy.set_watchlist(["AAPL"], source="test")

        # Send candle at 9:30 ET (before operating window) → 13:30 UTC
        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=5000,
            timestamp=datetime(2026, 3, 24, 13, 30, tzinfo=UTC),
        )
        result = await strategy.on_candle(candle)

        assert result is None  # No signal outside window
        window = strategy._get_candle_window("AAPL")
        assert len(window) == 1  # Bar accumulated

    @pytest.mark.asyncio
    async def test_partial_history_records_warmup_telemetry(self) -> None:
        """Between 50% and 100% lookback: records warm-up telemetry."""
        strategy = _make_pattern_strategy(lookback=10, earliest="09:45", latest="15:00")
        strategy.set_watchlist(["AAPL"], source="test")

        # Send 6 candles within operating window — first 4 below threshold,
        # bar 5+ above 50% threshold → should produce "Warming up" evals
        for i in range(6):
            ts = datetime(2026, 3, 24, 13, 50 + i, tzinfo=UTC)  # 09:50+ ET
            candle = CandleEvent(
                symbol="AAPL",
                timeframe="1m",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=5000,
                timestamp=ts,
            )
            await strategy.on_candle(candle)

        # Should have at least one warm-up evaluation
        all_evals = strategy.eval_buffer.snapshot()
        warmup_eval = [e for e in all_evals if "Warming up" in e.reason]
        assert len(warmup_eval) > 0
        # And also some "Insufficient history" from early bars
        insufficient = [e for e in all_evals if "Insufficient history" in e.reason]
        assert len(insufficient) > 0

    @pytest.mark.asyncio
    async def test_full_history_proceeds_to_detection(self) -> None:
        """With full lookback bars, pattern detection is attempted."""
        strategy = _make_pattern_strategy(lookback=5, earliest="09:45", latest="15:00")
        strategy.set_watchlist(["AAPL"], source="test")

        # Fill 5 bars (full lookback)
        for i in range(5):
            ts = datetime(2026, 3, 24, 13, 50 + i, tzinfo=UTC)
            candle = CandleEvent(
                symbol="AAPL",
                timeframe="1m",
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.5,
                volume=5000,
                timestamp=ts,
            )
            await strategy.on_candle(candle)

        evals_before = len(strategy.eval_buffer)

        # Send candle within operating window
        candle = CandleEvent(
            symbol="AAPL",
            timeframe="1m",
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=5000,
            timestamp=datetime(2026, 3, 24, 14, 0, tzinfo=UTC),
        )
        result = await strategy.on_candle(candle)

        # Stub pattern returns None → "No pattern detected" evaluation
        all_evals = strategy.eval_buffer.snapshot()
        new_evals = all_evals[evals_before:]
        no_pattern_evals = [
            e for e in new_evals if "No stub_pattern pattern detected" in e.reason
        ]
        assert len(no_pattern_evals) == 1
