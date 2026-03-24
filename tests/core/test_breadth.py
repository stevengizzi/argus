"""Tests for BreadthCalculator (Sprint 27.6, Session 2)."""

from collections import deque

import pytest

from argus.core.breadth import BreadthCalculator
from argus.core.config import BreadthConfig
from argus.core.events import CandleEvent

# Symbols used to reach min_symbols=10 threshold
_RISING = [10.0, 11.0, 12.0, 13.0, 20.0]  # current (20) > mean (13.2) → above
_FALLING = [20.0, 15.0, 12.0, 10.0, 5.0]  # current (5) < mean (12.4) → below
_SYMS_10 = [f"SYM{i}" for i in range(10)]
_SYMS_12 = [f"SYM{i}" for i in range(12)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candle(symbol: str, close: float) -> CandleEvent:
    """Create a minimal CandleEvent with the given symbol and close."""
    return CandleEvent(symbol=symbol, timeframe="1m", close=close)


def _feed_candles(calc: BreadthCalculator, symbol: str, closes: list[float]) -> None:
    """Feed a sequence of close prices for a single symbol."""
    for close in closes:
        calc.on_candle(_make_candle(symbol, close))


def _build_calculator(
    ma_period: int = 20,
    thrust_threshold: float = 0.80,
    min_symbols: int = 10,
    min_bars_for_valid: int = 5,
) -> BreadthCalculator:
    """Build a BreadthCalculator with test-friendly defaults."""
    config = BreadthConfig(
        ma_period=ma_period,
        thrust_threshold=thrust_threshold,
        min_symbols=min_symbols,
        min_bars_for_valid=min_bars_for_valid,
    )
    return BreadthCalculator(config)


def _feed_n_rising(calc: BreadthCalculator, n: int, bars: int = 5) -> None:
    """Feed n symbols with rising close prices (above MA)."""
    for i in range(n):
        _feed_candles(calc, f"RISE{i}", _RISING[:bars])


def _feed_n_falling(calc: BreadthCalculator, n: int, bars: int = 5) -> None:
    """Feed n symbols with falling close prices (below MA)."""
    for i in range(n):
        _feed_candles(calc, f"FALL{i}", _FALLING[:bars])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConstruction:
    """BreadthCalculator construction and config validation."""

    def test_construction_with_config(self) -> None:
        """BreadthCalculator initializes with a BreadthConfig."""
        config = BreadthConfig(ma_period=10, min_symbols=20)
        calc = BreadthCalculator(config)
        snapshot = calc.get_breadth_snapshot()
        assert snapshot["symbols_tracked"] == 0
        assert snapshot["universe_breadth_score"] is None

    def test_construction_rejects_non_config(self) -> None:
        """BreadthCalculator raises TypeError for non-BreadthConfig input."""
        with pytest.raises(TypeError, match="BreadthConfig"):
            BreadthCalculator(config={"ma_period": 20})  # type: ignore[arg-type]


class TestOnCandle:
    """on_candle updates rolling deque per symbol."""

    def test_on_candle_updates_rolling_deque(self) -> None:
        """on_candle appends close price to the symbol's deque."""
        calc = _build_calculator()
        _feed_candles(calc, "AAPL", [100.0, 101.0, 102.0])
        assert len(calc._symbol_closes["AAPL"]) == 3
        assert list(calc._symbol_closes["AAPL"]) == [100.0, 101.0, 102.0]

    def test_on_candle_tracks_multiple_symbols(self) -> None:
        """on_candle maintains separate deques per symbol."""
        calc = _build_calculator()
        _feed_candles(calc, "AAPL", [100.0, 101.0])
        _feed_candles(calc, "MSFT", [200.0])
        assert len(calc._symbol_closes) == 2
        assert len(calc._symbol_closes["AAPL"]) == 2
        assert len(calc._symbol_closes["MSFT"]) == 1

    def test_on_candle_rejects_non_candle_event(self) -> None:
        """on_candle raises TypeError for non-CandleEvent input."""
        calc = _build_calculator()
        with pytest.raises(TypeError, match="CandleEvent"):
            calc.on_candle("not_an_event")  # type: ignore[arg-type]


class TestBreadthScoreAllAbove:
    """universe_breadth_score when all symbols are above their MA."""

    def test_all_above_ma_returns_positive_one(self) -> None:
        """When all qualifying symbols are above MA, score is +1.0."""
        calc = _build_calculator(min_bars_for_valid=3)
        _feed_n_rising(calc, 10)

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["universe_breadth_score"] == 1.0


class TestBreadthScoreAllBelow:
    """universe_breadth_score when all symbols are below their MA."""

    def test_all_below_ma_returns_negative_one(self) -> None:
        """When all qualifying symbols are below MA, score is -1.0."""
        calc = _build_calculator(min_bars_for_valid=3)
        _feed_n_falling(calc, 10)

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["universe_breadth_score"] == -1.0


class TestBreadthScoreMixed:
    """universe_breadth_score with mixed symbols."""

    def test_mixed_symbols_returns_between_negative_one_and_one(self) -> None:
        """Mixed above/below MA produces a score between -1 and +1."""
        calc = _build_calculator(min_bars_for_valid=3)
        # 7 above, 3 below → (7 - 3) / 10 = 0.4
        _feed_n_rising(calc, 7)
        _feed_n_falling(calc, 3)

        snapshot = calc.get_breadth_snapshot()
        score = snapshot["universe_breadth_score"]
        assert score is not None
        assert -1.0 < score < 1.0
        assert abs(score - 0.4) < 1e-9


class TestBreadthThrust:
    """breadth_thrust flag behavior."""

    def test_thrust_true_when_above_threshold(self) -> None:
        """breadth_thrust is True when above_count/qualifying >= thrust_threshold."""
        calc = _build_calculator(min_bars_for_valid=3, thrust_threshold=0.75)
        # 8 above, 2 below → 8/10 = 0.80 >= 0.75
        _feed_n_rising(calc, 8)
        _feed_n_falling(calc, 2)

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["breadth_thrust"] is True

    def test_thrust_false_when_below_threshold(self) -> None:
        """breadth_thrust is False when above_count/qualifying < thrust_threshold."""
        calc = _build_calculator(min_bars_for_valid=3, thrust_threshold=0.80)
        # 5 above, 5 below → 5/10 = 0.50 < 0.80
        _feed_n_rising(calc, 5)
        _feed_n_falling(calc, 5)

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["breadth_thrust"] is False

    def test_configurable_thrust_threshold(self) -> None:
        """Different thrust thresholds change the thrust flag result."""
        # With threshold=0.50: 5/10 = 0.50 → True
        calc_low = _build_calculator(min_bars_for_valid=3, thrust_threshold=0.50)
        _feed_n_rising(calc_low, 5)
        _feed_n_falling(calc_low, 5)
        assert calc_low.get_breadth_snapshot()["breadth_thrust"] is True

        # Same ratio, threshold=0.90 → False
        calc_high = _build_calculator(min_bars_for_valid=3, thrust_threshold=0.90)
        _feed_n_rising(calc_high, 5)
        _feed_n_falling(calc_high, 5)
        assert calc_high.get_breadth_snapshot()["breadth_thrust"] is False


class TestRampUp:
    """Ramp-up: symbols with fewer than min_bars_for_valid don't qualify."""

    def test_insufficient_bars_symbol_does_not_qualify(self) -> None:
        """A symbol with fewer bars than min_bars_for_valid is not counted."""
        calc = _build_calculator(min_bars_for_valid=5)
        # 10 symbols with 5 bars (qualify), 2 with only 3 bars (don't)
        _feed_n_rising(calc, 10)
        _feed_candles(calc, "SHORT_A", [10.0, 11.0, 12.0])
        _feed_candles(calc, "SHORT_B", [10.0, 11.0, 12.0])

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["symbols_tracked"] == 12
        assert snapshot["symbols_qualifying"] == 10


class TestPreThreshold:
    """Pre-threshold: fewer than min_symbols qualifying returns None."""

    def test_fewer_than_min_symbols_returns_none(self) -> None:
        """When qualifying count < min_symbols, all outputs are None."""
        calc = _build_calculator(min_bars_for_valid=5, min_symbols=50)
        # Only 10 symbols qualify (< 50)
        _feed_n_rising(calc, 10)

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["universe_breadth_score"] is None
        assert snapshot["breadth_thrust"] is None
        assert snapshot["symbols_tracked"] == 10
        assert snapshot["symbols_qualifying"] == 10


class TestMemoryBounded:
    """Memory bounded: deque maxlen is enforced."""

    def test_deque_maxlen_enforced(self) -> None:
        """Deque does not grow beyond ma_period."""
        calc = _build_calculator(ma_period=5)
        _feed_candles(calc, "AAPL", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])

        closes = calc._symbol_closes["AAPL"]
        assert len(closes) == 5
        assert list(closes) == [4.0, 5.0, 6.0, 7.0, 8.0]
        assert isinstance(closes, deque)
        assert closes.maxlen == 5


class TestSingleSymbol:
    """Single symbol edge case."""

    def test_single_symbol_below_min_symbols_returns_none(self) -> None:
        """A single qualifying symbol returns None when below min_symbols."""
        calc = _build_calculator(min_bars_for_valid=3)
        _feed_candles(calc, "AAPL", [10.0, 11.0, 12.0, 13.0, 20.0])

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["universe_breadth_score"] is None
        assert snapshot["symbols_qualifying"] == 1


class TestEmptyUniverse:
    """Empty universe → None."""

    def test_empty_universe_returns_none(self) -> None:
        """No candles fed → all outputs are None, tracked=0."""
        calc = _build_calculator()
        snapshot = calc.get_breadth_snapshot()
        assert snapshot["universe_breadth_score"] is None
        assert snapshot["breadth_thrust"] is None
        assert snapshot["symbols_tracked"] == 0
        assert snapshot["symbols_qualifying"] == 0


class TestReset:
    """reset() clears all state."""

    def test_reset_clears_all_state(self) -> None:
        """After reset(), calculator is back to empty state."""
        calc = _build_calculator(min_bars_for_valid=3)
        _feed_n_rising(calc, 10)

        assert calc.get_breadth_snapshot()["symbols_tracked"] == 10

        calc.reset()

        snapshot = calc.get_breadth_snapshot()
        assert snapshot["symbols_tracked"] == 0
        assert snapshot["symbols_qualifying"] == 0
        assert snapshot["universe_breadth_score"] is None
        assert snapshot["breadth_thrust"] is None
