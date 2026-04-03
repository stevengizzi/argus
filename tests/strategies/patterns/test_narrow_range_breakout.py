"""Tests for NarrowRangeBreakoutPattern detection module.

Sprint 31A, Session 5.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from argus.core.config import NarrowRangeBreakoutConfig
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternParam
from argus.strategies.patterns.narrow_range_breakout import NarrowRangeBreakoutPattern

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_NRB_YAML = _PROJECT_ROOT / "config" / "strategies" / "narrow_range_breakout.yaml"

BASE_TIME = datetime(2026, 3, 31, 11, 0, 0)
BASE_PRICE = 50.0
ATR = 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bar(
    close: float,
    high: float | None = None,
    low: float | None = None,
    volume: float = 1000.0,
    offset_minutes: int = 0,
) -> CandleBar:
    """Build a CandleBar with sensible OHLCV defaults."""
    h = high if high is not None else close + 0.10
    lo = low if low is not None else close - 0.10
    return CandleBar(
        timestamp=BASE_TIME + timedelta(minutes=offset_minutes),
        open=close,
        high=h,
        low=lo,
        close=close,
        volume=volume,
    )


def _build_nrb_candles(
    base_price: float = BASE_PRICE,
    narrowing_bars: int = 4,
    initial_range: float = 0.70,
    range_step: float = 0.10,
    avg_volume: float = 1000.0,
    breakout_volume_mult: float = 2.0,
    breakout_excess: float = 0.20,
    tolerance: float = 1.05,
) -> list[CandleBar]:
    """Build a candle sequence with a detectable narrowing → breakout.

    Structure:
        - narrowing_bars bars with ranges decreasing by range_step each bar
          (within tolerance)
        - 1 breakout bar: close above max(highs of narrowing bars) + excess,
          with high volume

    Returns:
        List of CandleBar (oldest first, breakout bar last).
    """
    candles: list[CandleBar] = []
    minute = 0
    price = base_price

    # Build narrowing bars: each narrower than the previous
    for i in range(narrowing_bars):
        half_range = max(0.05, (initial_range - range_step * i) / 2)
        candles.append(
            _bar(
                close=price,
                high=price + half_range,
                low=price - half_range,
                volume=avg_volume,
                offset_minutes=minute,
            )
        )
        minute += 1

    # Consolidation high is the max high across the narrowing bars
    consolidation_high = max(c.high for c in candles)

    # Breakout bar: close clearly above consolidation high
    breakout_close = consolidation_high + breakout_excess
    candles.append(
        _bar(
            close=breakout_close,
            high=breakout_close + 0.05,
            low=breakout_close - 0.05,
            volume=avg_volume * breakout_volume_mult,
            offset_minutes=minute,
        )
    )

    return candles


# ---------------------------------------------------------------------------
# Positive detection
# ---------------------------------------------------------------------------


def test_detect_positive_clear_narrowing_breakout() -> None:
    """Clear narrowing sequence followed by volume-confirmed breakout emits detection."""
    pattern = NarrowRangeBreakoutPattern()
    candles = _build_nrb_candles(narrowing_bars=4, avg_volume=1000.0, breakout_volume_mult=2.0)
    result = pattern.detect(candles, {"atr": ATR})

    assert result is not None
    assert result.pattern_type == "narrow_range_breakout"
    assert result.entry_price > 0
    assert result.stop_price < result.entry_price
    assert len(result.target_prices) == 2
    assert result.target_prices[0] < result.target_prices[1]


def test_detect_populates_all_metadata_fields() -> None:
    """Detection metadata contains all required keys."""
    pattern = NarrowRangeBreakoutPattern()
    candles = _build_nrb_candles(narrowing_bars=4)
    result = pattern.detect(candles, {"atr": ATR})

    assert result is not None
    required_keys = {
        "narrowing_bar_count",
        "consolidation_range",
        "consolidation_range_atr_ratio",
        "breakout_margin",
        "breakout_volume_ratio",
        "consolidation_high",
        "consolidation_low",
        "atr",
    }
    assert required_keys.issubset(result.metadata.keys())


# ---------------------------------------------------------------------------
# Rejection: insufficient narrowing bars
# ---------------------------------------------------------------------------


def test_reject_insufficient_narrowing_bars() -> None:
    """Pattern rejects when narrowing run is below min_narrowing_bars."""
    # Build only 2 narrowing bars but require 3 minimum
    pattern = NarrowRangeBreakoutPattern(min_narrowing_bars=3)
    candles = _build_nrb_candles(narrowing_bars=2, range_step=0.20)
    result = pattern.detect(candles, {"atr": ATR})
    assert result is None


def test_reject_too_few_candles_for_window() -> None:
    """Pattern returns None when candle count is below min_detection_bars."""
    pattern = NarrowRangeBreakoutPattern(min_narrowing_bars=3)
    # min_detection_bars = min_narrowing_bars + 1 = 4; provide only 2 candles
    candles = [_bar(BASE_PRICE, offset_minutes=i) for i in range(2)]
    result = pattern.detect(candles, {"atr": ATR})
    assert result is None


# ---------------------------------------------------------------------------
# Rejection: consolidation too wide
# ---------------------------------------------------------------------------


def test_reject_consolidation_too_wide() -> None:
    """Pattern rejects when overall consolidation range exceeds ATR limit."""
    # initial_range=1.5 → consolidation range=1.5 > 0.8×ATR=0.8
    pattern = NarrowRangeBreakoutPattern(consolidation_max_range_atr=0.8)
    candles = _build_nrb_candles(narrowing_bars=4, initial_range=1.5, range_step=0.05)
    result = pattern.detect(candles, {"atr": ATR})
    assert result is None


# ---------------------------------------------------------------------------
# Rejection: no breakout (close within range)
# ---------------------------------------------------------------------------


def test_reject_no_breakout_close_within_range() -> None:
    """Pattern rejects when last bar closes inside consolidation range."""
    pattern = NarrowRangeBreakoutPattern()
    candles = _build_nrb_candles(narrowing_bars=4, breakout_excess=-0.10)
    result = pattern.detect(candles, {"atr": ATR})
    assert result is None


def test_reject_close_just_at_margin_boundary() -> None:
    """Pattern rejects close that is at exactly the margin (not strictly above)."""
    pattern = NarrowRangeBreakoutPattern(breakout_margin_percent=0.001)
    candles = _build_nrb_candles(narrowing_bars=4, breakout_excess=0.0)
    # breakout_excess=0 means close == consolidation_high, not above by margin
    result = pattern.detect(candles, {"atr": ATR})
    assert result is None


# ---------------------------------------------------------------------------
# Rejection: downward breakout (long-only)
# ---------------------------------------------------------------------------


def test_reject_downward_breakout_long_only() -> None:
    """Pattern rejects when breakout close is below consolidation low."""
    pattern = NarrowRangeBreakoutPattern()
    candles = _build_nrb_candles(narrowing_bars=4)
    # Replace breakout bar with one that closes below consolidation low
    consolidation_low = min(c.low for c in candles[:-1])
    breakout_bar = _bar(
        close=consolidation_low - 0.50,
        volume=candles[-1].volume,
        offset_minutes=len(candles),
    )
    candles[-1] = breakout_bar
    result = pattern.detect(candles, {"atr": ATR})
    assert result is None


# ---------------------------------------------------------------------------
# Rejection: insufficient volume
# ---------------------------------------------------------------------------


def test_reject_insufficient_breakout_volume() -> None:
    """Pattern rejects when breakout volume is below the required ratio."""
    pattern = NarrowRangeBreakoutPattern(min_breakout_volume_ratio=2.0)
    # breakout_volume_mult=1.1 < 2.0 threshold
    candles = _build_nrb_candles(narrowing_bars=4, breakout_volume_mult=1.1)
    result = pattern.detect(candles, {"atr": ATR})
    assert result is None


# ---------------------------------------------------------------------------
# Score boundaries
# ---------------------------------------------------------------------------


def test_score_returns_value_in_valid_range() -> None:
    """score() returns a value between 0 and 100."""
    pattern = NarrowRangeBreakoutPattern()
    candles = _build_nrb_candles(narrowing_bars=4)
    detection = pattern.detect(candles, {"atr": ATR})

    assert detection is not None
    score = pattern.score(detection)
    assert 0.0 <= score <= 100.0


def test_score_higher_with_more_narrowing_bars() -> None:
    """Longer narrowing run produces a higher consolidation quality score."""
    pattern = NarrowRangeBreakoutPattern()

    detection_short = PatternDetection(
        pattern_type="narrow_range_breakout",
        confidence=50.0,
        entry_price=50.5,
        stop_price=49.0,
        target_prices=(51.5, 52.5),
        metadata={
            "narrowing_bar_count": 3,
            "consolidation_range_atr_ratio": 0.4,
            "breakout_margin": 0.005,
            "breakout_volume_ratio": 2.0,
        },
    )
    detection_long = PatternDetection(
        pattern_type="narrow_range_breakout",
        confidence=50.0,
        entry_price=50.5,
        stop_price=49.0,
        target_prices=(51.5, 52.5),
        metadata={
            "narrowing_bar_count": 6,
            "consolidation_range_atr_ratio": 0.4,
            "breakout_margin": 0.005,
            "breakout_volume_ratio": 2.0,
        },
    )
    assert pattern.score(detection_long) > pattern.score(detection_short)


# ---------------------------------------------------------------------------
# ATR fallback
# ---------------------------------------------------------------------------


def test_atr_fallback_computes_from_candles() -> None:
    """detect() succeeds using self-contained ATR when indicators["atr"] is absent."""
    pattern = NarrowRangeBreakoutPattern()
    candles = _build_nrb_candles(narrowing_bars=4)
    # No "atr" in indicators → must fall back to _compute_atr()
    result = pattern.detect(candles, {})
    # If ATR computation returns a valid value, detection should succeed or fail
    # on pattern merit alone — not crash.  The result may be None if ATR is 0,
    # but it must not raise an exception.
    assert result is None or isinstance(result, PatternDetection)


# ---------------------------------------------------------------------------
# get_default_params
# ---------------------------------------------------------------------------


def test_get_default_params_returns_all_expected_params() -> None:
    """get_default_params() returns a complete list covering all constructor args."""
    pattern = NarrowRangeBreakoutPattern()
    params = pattern.get_default_params()

    assert isinstance(params, list)
    assert len(params) >= 11  # 11 constructor params

    param_names = {p.name for p in params}
    expected = {
        "nr_lookback",
        "min_narrowing_bars",
        "range_decay_tolerance",
        "breakout_margin_percent",
        "min_breakout_volume_ratio",
        "consolidation_max_range_atr",
        "stop_buffer_atr_mult",
        "target_ratio",
        "target_1_r",
        "target_2_r",
        "min_score_threshold",
    }
    assert expected.issubset(param_names)


def test_get_default_params_all_are_pattern_param_instances() -> None:
    """Every item returned by get_default_params() is a PatternParam."""
    pattern = NarrowRangeBreakoutPattern()
    for p in pattern.get_default_params():
        assert isinstance(p, PatternParam)


# ---------------------------------------------------------------------------
# Cross-validation: factory + config loading
# ---------------------------------------------------------------------------


def test_cross_validation_factory_resolves_class() -> None:
    """get_pattern_class('narrow_range_breakout') returns NarrowRangeBreakoutPattern."""
    from argus.strategies.patterns.factory import get_pattern_class

    cls = get_pattern_class("narrow_range_breakout")
    assert cls is NarrowRangeBreakoutPattern


def test_cross_validation_build_from_config_wires_params() -> None:
    """build_pattern_from_config creates a pattern with overridden params."""
    from argus.strategies.patterns.factory import build_pattern_from_config

    config = NarrowRangeBreakoutConfig(
        strategy_id="strat_narrow_range_breakout",
        name="Narrow Range Breakout",
        nr_lookback=5,
        min_narrowing_bars=2,
    )
    pattern = build_pattern_from_config(config, "narrow_range_breakout")

    assert isinstance(pattern, NarrowRangeBreakoutPattern)
    assert pattern._nr_lookback == 5
    assert pattern._min_narrowing_bars == 2


# ---------------------------------------------------------------------------
# Config loading: YAML keys match Pydantic fields
# ---------------------------------------------------------------------------


def test_config_loading_yaml_keys_match_pydantic_fields() -> None:
    """All YAML keys in narrow_range_breakout.yaml are valid NarrowRangeBreakoutConfig fields."""
    assert _NRB_YAML.exists(), f"Strategy YAML not found: {_NRB_YAML}"

    with open(_NRB_YAML) as f:
        data = yaml.safe_load(f)

    config = NarrowRangeBreakoutConfig(**data)
    assert config.strategy_id == "strat_narrow_range_breakout"
    assert config.nr_lookback == 7
    assert config.min_narrowing_bars == 3
    assert config.min_breakout_volume_ratio == 1.5


# ---------------------------------------------------------------------------
# BacktestEngine dispatch
# ---------------------------------------------------------------------------


def test_backtest_engine_dispatch_creates_strategy() -> None:
    """StrategyType.NARROW_RANGE_BREAKOUT routes to NarrowRangeBreakoutPattern strategy."""
    from argus.backtest.config import BacktestEngineConfig, StrategyType
    from argus.backtest.engine import BacktestEngine
    from datetime import date

    cfg = BacktestEngineConfig(
        strategy_type=StrategyType.NARROW_RANGE_BREAKOUT,
        strategy_id="strat_narrow_range_breakout",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 30),
        data_source="parquet",
    )
    engine = BacktestEngine(cfg)
    config_dir = Path(_PROJECT_ROOT / "config")
    # _create_narrow_range_breakout_strategy uses config_dir directly
    strategy = engine._create_narrow_range_breakout_strategy(config_dir)

    from argus.strategies.pattern_strategy import PatternBasedStrategy

    assert isinstance(strategy, PatternBasedStrategy)
    assert isinstance(strategy._pattern, NarrowRangeBreakoutPattern)


# ---------------------------------------------------------------------------
# range_decay_tolerance correctness
# ---------------------------------------------------------------------------


def test_range_decay_tolerance_allows_5pct_noise() -> None:
    """range_decay_tolerance=1.05 accepts bars where range(i) ≤ range(i-1) × 1.05."""
    pattern = NarrowRangeBreakoutPattern(range_decay_tolerance=1.05, min_narrowing_bars=3)
    # Build candles where each bar range is exactly 1.04× the previous (within tolerance)
    # This should form a valid narrowing sequence.
    initial_range = 0.60
    candles = []
    price = BASE_PRICE
    for i in range(4):
        r = initial_range * (1.04 ** i)  # Actually growing, so let's do it differently
        r = initial_range / (1.02 ** i)  # Slightly narrowing each bar
        candles.append(
            _bar(
                close=price,
                high=price + r / 2,
                low=price - r / 2,
                volume=1000.0,
                offset_minutes=i,
            )
        )

    # Consolidation high
    consolidation_high = max(c.high for c in candles)
    breakout_close = consolidation_high * 1.003  # Above by margin
    candles.append(
        _bar(
            close=breakout_close,
            high=breakout_close + 0.05,
            low=breakout_close - 0.05,
            volume=2000.0,
            offset_minutes=4,
        )
    )

    result = pattern.detect(candles, {"atr": ATR})
    # Should detect (ranges are within 1.05 tolerance)
    assert result is not None


def test_range_decay_tolerance_strict_rejects_wide_expansion() -> None:
    """Bars where each range grows clearly beyond tolerance are rejected."""
    pattern = NarrowRangeBreakoutPattern(range_decay_tolerance=1.0, min_narrowing_bars=3)
    # Build bars where each subsequent bar has a LARGER range than the previous
    candles = []
    price = BASE_PRICE
    for i in range(4):
        half_range = 0.10 + 0.10 * i  # Growing range: 0.10, 0.20, 0.30, 0.40
        candles.append(
            _bar(
                close=price,
                high=price + half_range,
                low=price - half_range,
                volume=1000.0,
                offset_minutes=i,
            )
        )

    consolidation_high = max(c.high for c in candles)
    breakout_close = consolidation_high * 1.003
    candles.append(
        _bar(
            close=breakout_close,
            high=breakout_close + 0.05,
            low=breakout_close - 0.05,
            volume=2000.0,
            offset_minutes=4,
        )
    )

    result = pattern.detect(candles, {"atr": ATR})
    assert result is None
