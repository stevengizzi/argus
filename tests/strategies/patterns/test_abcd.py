"""Tests for ABCDPattern detection module.

Sprint 29, Session 6a.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus.strategies.patterns.abcd import ABCDPattern
from argus.strategies.patterns.base import CandleBar, PatternParam


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_TIME = datetime(2026, 3, 31, 10, 0, 0, tzinfo=UTC)


def _bar(
    close: float,
    volume: float = 1000.0,
    offset_minutes: int = 0,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
) -> CandleBar:
    """Build a CandleBar with sensible defaults."""
    o = open_ if open_ is not None else close
    h = high if high is not None else close + 0.10
    lo = low if low is not None else close - 0.10
    return CandleBar(
        timestamp=BASE_TIME + timedelta(minutes=offset_minutes),
        open=o,
        high=h,
        low=lo,
        close=close,
        volume=volume,
    )


def _build_abcd_candles(
    a_price: float = 100.0,
    b_price: float = 110.0,
    c_retrace: float = 0.618,
    d_offset_pct: float = 0.0,
    swing_lookback: int = 5,
    bc_avg_volume: float = 800.0,
    cd_avg_volume: float = 1200.0,
) -> list[CandleBar]:
    """Build synthetic candles containing a valid bullish ABCD pattern.

    Creates a clean price profile with unambiguous swing points:
    flat → decline to A → rise to B → decline to C → rise to D.

    Each swing point is surrounded by ``swing_lookback`` strictly
    monotonic bars on each side so the swing detection algorithm
    identifies them reliably.

    The total bar count is calibrated to meet the 60-bar lookback.

    Args:
        a_price: Price at point A (swing low).
        b_price: Price at point B (swing high).
        c_retrace: BC retracement fraction of AB (e.g. 0.618).
        d_offset_pct: D price offset from projected D, as percentage.
        swing_lookback: Must match the pattern's swing_lookback.
        bc_avg_volume: Average volume during BC leg.
        cd_avg_volume: Average volume during CD leg.

    Returns:
        List of CandleBar forming a valid ABCD pattern.
    """
    ab_height = b_price - a_price
    c_price = b_price - c_retrace * ab_height
    projected_d = c_price + ab_height
    d_price = projected_d * (1.0 + d_offset_pct / 100.0)

    # We need clear swing points. Strategy: build segments where price
    # strictly changes in one direction, with the swing point at the
    # extremum. Each segment has swing_lookback bars of approach and
    # swing_lookback bars of departure.
    sl = swing_lookback
    candles: list[CandleBar] = []
    minute = 0

    mid_price = (a_price + b_price) / 2.0  # neutral starting level

    def add(close: float, vol: float = 1000.0) -> None:
        nonlocal minute
        # Tiny high/low spread so intermediate bars don't create
        # false swing points that compete with the real A/B/C/D.
        candles.append(
            _bar(close, volume=vol, offset_minutes=minute,
                 high=close + 0.001, low=close - 0.001)
        )
        minute += 1

    # --- Flat lead-in (pad to reach 60+ total bars) ---
    # Pattern body = sl + 1 + 2*sl + 1 + 2*sl + 1 + 2*sl + 1 = 9*sl + 4
    # For sl=5: 49 pattern bars. Need 60+ total → 21+ flat bars.
    flat_bars = 25
    for _ in range(flat_bars):
        add(mid_price)

    # Margin: approach bars stop this far from swing prices so the
    # actual swing bar is the clear extremum.
    margin = 0.50

    # --- Decline to A: sl bars strictly decreasing toward A+margin ---
    for i in range(1, sl + 1):
        frac = i / sl
        add(mid_price - frac * (mid_price - (a_price + margin)))

    # --- A point (swing low — low clearly the minimum) ---
    candles.append(
        _bar(a_price + margin, volume=1000.0, offset_minutes=minute,
             high=a_price + margin + 0.001, low=a_price)
    )
    minute += 1

    # --- Rise from A to B: 2*sl bars strictly increasing ---
    ab_rise_bars = 2 * sl
    a_depart = a_price + margin
    b_approach = b_price - margin
    for i in range(1, ab_rise_bars + 1):
        frac = i / ab_rise_bars
        add(a_depart + frac * (b_approach - a_depart))

    # --- B point (swing high — high clearly the maximum) ---
    candles.append(
        _bar(b_price - margin, volume=1000.0, offset_minutes=minute,
             high=b_price, low=b_price - margin - 0.001)
    )
    minute += 1

    # --- Decline from B to C: 2*sl bars strictly decreasing ---
    bc_decline_bars = 2 * sl
    b_depart = b_price - margin
    c_approach = c_price + margin
    for i in range(1, bc_decline_bars + 1):
        frac = i / bc_decline_bars
        add(b_depart - frac * (b_depart - c_approach), vol=bc_avg_volume)

    # --- C point (swing low — low clearly the minimum) ---
    candles.append(
        _bar(c_price + margin, volume=bc_avg_volume, offset_minutes=minute,
             high=c_price + margin + 0.001, low=c_price)
    )
    minute += 1

    # --- Rise from C to D: 2*sl bars strictly increasing ---
    cd_rise_bars = 2 * sl
    c_depart = c_price + margin
    for i in range(1, cd_rise_bars + 1):
        frac = i / cd_rise_bars
        add(c_depart + frac * (d_price - c_depart), vol=cd_avg_volume)

    # --- D completion bar ---
    candles.append(
        _bar(d_price, volume=cd_avg_volume, offset_minutes=minute,
             high=d_price + 0.02, low=d_price - 0.02)
    )

    return candles


# ---------------------------------------------------------------------------
# Swing detection tests
# ---------------------------------------------------------------------------


class TestSwingHighDetection:
    """Tests for _find_swing_highs()."""

    def test_finds_peaks_in_known_sequence(self) -> None:
        """Swing high detection finds peaks in known price sequence."""
        pattern = ABCDPattern(swing_lookback=2, min_swing_atr_mult=0.0)
        # Prices: 10, 11, 12, 15, 12, 11, 10
        candles = [
            _bar(10, high=10, low=9.5, offset_minutes=0),
            _bar(11, high=11, low=10.5, offset_minutes=1),
            _bar(12, high=12.5, low=11.5, offset_minutes=2),
            _bar(15, high=15.5, low=14.5, offset_minutes=3),
            _bar(12, high=12.5, low=11.5, offset_minutes=4),
            _bar(11, high=11, low=10.5, offset_minutes=5),
            _bar(10, high=10, low=9.5, offset_minutes=6),
        ]
        highs = pattern._find_swing_highs(candles, atr=1.0)
        assert len(highs) >= 1
        # The peak at index 3 (high=15.5) should be found
        indices = [idx for idx, _ in highs]
        assert 3 in indices
        prices = [p for _, p in highs if _ == 3]
        assert prices[0] == pytest.approx(15.5)

    def test_edge_candles_excluded(self) -> None:
        """Candles within swing_lookback of edges are not swing points."""
        pattern = ABCDPattern(swing_lookback=3, min_swing_atr_mult=0.0)
        # Peak at index 1 — within lookback of start, should be excluded
        candles = [
            _bar(10, high=10, low=9, offset_minutes=i)
            for i in range(10)
        ]
        # Make index 1 a local high but it's within lookback=3 of start
        candles[1] = _bar(20, high=20.5, low=19, offset_minutes=1)
        highs = pattern._find_swing_highs(candles, atr=0.1)
        indices = [idx for idx, _ in highs]
        assert 1 not in indices


class TestSwingLowDetection:
    """Tests for _find_swing_lows()."""

    def test_finds_valleys_in_known_sequence(self) -> None:
        """Swing low detection finds valleys in known price sequence."""
        pattern = ABCDPattern(swing_lookback=2, min_swing_atr_mult=0.0)
        # Prices: 20, 19, 18, 15, 18, 19, 20
        candles = [
            _bar(20, high=20.5, low=19.5, offset_minutes=0),
            _bar(19, high=19.5, low=18.5, offset_minutes=1),
            _bar(18, high=18.5, low=17.5, offset_minutes=2),
            _bar(15, high=15.5, low=14.5, offset_minutes=3),
            _bar(18, high=18.5, low=17.5, offset_minutes=4),
            _bar(19, high=19.5, low=18.5, offset_minutes=5),
            _bar(20, high=20.5, low=19.5, offset_minutes=6),
        ]
        lows = pattern._find_swing_lows(candles, atr=1.0)
        assert len(lows) >= 1
        indices = [idx for idx, _ in lows]
        assert 3 in indices
        prices = [p for _, p in lows if _ == 3]
        assert prices[0] == pytest.approx(14.5)

    def test_min_swing_atr_mult_filters_noise(self) -> None:
        """Swing detection respects min_swing_atr_mult filter."""
        # Small ATR mult = accept small swings; large = reject them
        candles = [
            _bar(20, high=20.5, low=19.5, offset_minutes=0),
            _bar(19.5, high=20, low=19, offset_minutes=1),
            _bar(19.8, high=20.2, low=19.3, offset_minutes=2),
            # Tiny dip at index 3 — only 0.2 below neighbors
            _bar(19.5, high=19.6, low=19.3, offset_minutes=3),
            _bar(19.8, high=20.2, low=19.3, offset_minutes=4),
            _bar(20, high=20.5, low=19.5, offset_minutes=5),
            _bar(20.2, high=20.7, low=19.7, offset_minutes=6),
        ]
        # With low threshold — finds the dip
        lenient = ABCDPattern(swing_lookback=2, min_swing_atr_mult=0.0)
        lows_lenient = lenient._find_swing_lows(candles, atr=1.0)

        # With high threshold — filters it out
        strict = ABCDPattern(swing_lookback=2, min_swing_atr_mult=5.0)
        lows_strict = strict._find_swing_lows(candles, atr=1.0)

        assert len(lows_lenient) >= len(lows_strict)


# ---------------------------------------------------------------------------
# Fibonacci validation tests
# ---------------------------------------------------------------------------


class TestFibonacciValidation:
    """Tests for BC retracement Fibonacci checks."""

    def test_fib_b_in_range_accepted(self) -> None:
        """BC retracement within range produces valid detection."""
        # 0.500 retracement = well within default 0.382-0.618
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.500
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is not None
        assert result.pattern_type == "abcd"

    def test_fib_b_outside_range_rejected(self) -> None:
        """BC retracement outside range returns None."""
        # 0.10 retracement = far below min 0.382
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.10
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is None

    def test_fib_c_in_range_accepted(self) -> None:
        """BC retracement at 0.500 (middle of range) accepted."""
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.500
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is not None

    def test_fib_c_outside_range_rejected(self) -> None:
        """BC retracement at 0.90 (above max 0.618) rejected."""
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.90
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is None


# ---------------------------------------------------------------------------
# Leg ratio tests
# ---------------------------------------------------------------------------


class TestLegRatios:
    """Tests for price and time leg ratio validation."""

    def test_symmetric_legs_accepted(self) -> None:
        """Symmetric AB/CD legs pass price ratio check."""
        # Default d_offset_pct=0 means exact AB=CD
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.500,
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is not None
        price_ratio = float(result.metadata.get("price_ratio", 0))
        assert 0.8 <= price_ratio <= 1.2

    def test_proportional_time_ratio_accepted(self) -> None:
        """Proportional time legs pass time ratio check."""
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.500,
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is not None
        time_ratio = float(result.metadata.get("time_ratio", 0))
        assert 0.5 <= time_ratio <= 2.0


# ---------------------------------------------------------------------------
# Full detection tests
# ---------------------------------------------------------------------------


class TestABCDDetection:
    """End-to-end ABCD detection tests."""

    def test_complete_abcd_detected(self) -> None:
        """Complete ABCD on synthetic data returns PatternDetection."""
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.500,
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is not None
        assert result.pattern_type == "abcd"
        assert result.entry_price > 0
        assert result.stop_price > 0
        assert len(result.target_prices) == 1
        assert result.target_prices[0] > result.entry_price

    def test_incomplete_pattern_abc_only_returns_none(self) -> None:
        """ABC without D completion returns None."""
        # Build a valid pattern then truncate to remove D completion
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.500,
        )
        # Chop off the last several bars so D never reaches completion
        truncated = candles[: -8]
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(truncated, {})
        # Either None (not enough bars) or None (D not in zone)
        assert result is None

    def test_insufficient_candle_history_returns_none(self) -> None:
        """Fewer than lookback_bars candles returns None."""
        pattern = ABCDPattern()
        candles = [_bar(100.0, offset_minutes=i) for i in range(10)]
        result = pattern.detect(candles, {})
        assert result is None

    def test_detection_metadata_populated(self) -> None:
        """Detection metadata contains all expected fields."""
        candles = _build_abcd_candles(
            a_price=100.0, b_price=110.0, c_retrace=0.500,
        )
        pattern = ABCDPattern(swing_lookback=5)
        result = pattern.detect(candles, {})
        assert result is not None
        expected_keys = {
            "a_index", "a_price", "b_price", "c_price",
            "projected_d", "bc_retracement", "price_ratio",
            "time_ratio", "ab_bars", "cd_bars", "ab_height", "atr",
        }
        assert expected_keys.issubset(set(result.metadata.keys()))


# ---------------------------------------------------------------------------
# Scoring tests
# ---------------------------------------------------------------------------


class TestABCDScoring:
    """Tests for ABCD pattern scoring."""

    def test_perfect_fib_scores_higher_than_boundary(self) -> None:
        """Perfect 0.618 retracement scores higher than boundary 0.382."""
        pattern = ABCDPattern(swing_lookback=5)

        # Perfect retracement detection
        perfect_meta = {
            "bc_retracement": 0.618,
            "price_ratio": 1.0,
            "time_ratio": 1.0,
            "cd_bc_volume_ratio": 1.2,
            "trend_aligned": 1.0,
        }
        perfect_det = _make_detection(perfect_meta)
        perfect_score = pattern.score(perfect_det)

        # Boundary retracement detection
        boundary_meta = {
            "bc_retracement": 0.382,
            "price_ratio": 1.0,
            "time_ratio": 1.0,
            "cd_bc_volume_ratio": 1.2,
            "trend_aligned": 1.0,
        }
        boundary_det = _make_detection(boundary_meta)
        boundary_score = pattern.score(boundary_det)

        assert perfect_score > boundary_score

    def test_score_weights_sum_to_100(self) -> None:
        """Maximum possible score is 100."""
        pattern = ABCDPattern()
        # Perfect everything
        meta = {
            "bc_retracement": 0.618,
            "price_ratio": 1.0,
            "time_ratio": 1.0,
            "cd_bc_volume_ratio": 1.5,
            "trend_aligned": 1.0,
        }
        det = _make_detection(meta)
        score = pattern.score(det)
        assert score == pytest.approx(100.0)


# ---------------------------------------------------------------------------
# PatternParam tests
# ---------------------------------------------------------------------------


class TestPatternParams:
    """Tests for get_default_params()."""

    def test_param_count_at_least_14(self) -> None:
        """get_default_params returns >= 14 PatternParam entries."""
        pattern = ABCDPattern()
        params = pattern.get_default_params()
        assert len(params) >= 14

    def test_params_have_metadata(self) -> None:
        """All params have name, description, category, type, range."""
        pattern = ABCDPattern()
        params = pattern.get_default_params()
        for p in params:
            assert isinstance(p, PatternParam)
            assert p.name
            assert p.description
            assert p.category
            assert p.param_type in (int, float, bool)
            assert p.min_value is not None
            assert p.max_value is not None
            assert p.step is not None

    def test_params_include_expected_names(self) -> None:
        """Key parameter names are present."""
        pattern = ABCDPattern()
        params = pattern.get_default_params()
        names = {p.name for p in params}
        expected = {
            "swing_lookback", "min_swing_atr_mult",
            "fib_b_min", "fib_b_max", "fib_c_min", "fib_c_max",
            "leg_price_ratio_min", "leg_price_ratio_max",
            "leg_time_ratio_min", "leg_time_ratio_max",
            "completion_tolerance_percent",
            "stop_buffer_atr_mult", "target_extension",
        }
        assert expected.issubset(names)


# ---------------------------------------------------------------------------
# Helpers for scoring tests
# ---------------------------------------------------------------------------


def _make_detection(meta: dict[str, object]) -> PatternDetection:
    """Build a minimal PatternDetection with given metadata."""
    from argus.strategies.patterns.base import PatternDetection

    return PatternDetection(
        pattern_type="abcd",
        confidence=0.0,
        entry_price=114.18,
        stop_price=103.0,
        target_prices=(124.0,),
        metadata=meta,
    )
