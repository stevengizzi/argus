"""Tests for BullFlagPattern detection module.

Sprint 26, Session 5.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from argus.core.config import BullFlagConfig
from argus.strategies.patterns.base import CandleBar, PatternDetection
from argus.strategies.patterns.bull_flag import BullFlagPattern


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_TIME = datetime(2026, 3, 23, 14, 0, 0, tzinfo=UTC)


def _bar(
    close: float,
    volume: float = 1000.0,
    offset_minutes: int = 0,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
) -> CandleBar:
    """Build a CandleBar with sensible defaults."""
    o = open_ if open_ is not None else close - 0.10
    h = high if high is not None else close + 0.10
    lo = low if low is not None else close - 0.20
    return CandleBar(
        timestamp=BASE_TIME + timedelta(minutes=offset_minutes),
        open=o,
        high=h,
        low=lo,
        close=close,
        volume=volume,
    )


def _build_bull_flag_candles(
    pole_bars: int = 6,
    pole_start: float = 100.0,
    pole_end: float = 106.0,
    flag_bars: int = 5,
    flag_retrace: float = 0.30,
    flag_volume: float = 800.0,
    breakout_close: float | None = None,
    breakout_volume: float = 2000.0,
) -> list[CandleBar]:
    """Build synthetic candles for a valid bull flag pattern.

    Args:
        pole_bars: Number of candles in the pole.
        pole_start: Price at start of pole.
        pole_end: Price at top of pole.
        flag_bars: Number of candles in flag consolidation.
        flag_retrace: Fraction of pole height to retrace.
        flag_volume: Volume during flag candles.
        breakout_close: Breakout candle close (default: pole_end + small amount).
        breakout_volume: Volume on breakout candle.

    Returns:
        List of CandleBar forming a bull flag pattern.
    """
    candles: list[CandleBar] = []
    minute = 0

    pole_height = pole_end - pole_start
    step = pole_height / pole_bars

    # Pole: steadily rising candles
    for i in range(pole_bars):
        price = pole_start + step * (i + 1)
        candles.append(_bar(
            close=price,
            volume=1500.0,
            offset_minutes=minute,
            open_=price - step,
            high=price + 0.05,
            low=price - step - 0.05,
        ))
        minute += 1

    # Flag: consolidation pulling back from pole_end
    retrace_amount = pole_height * flag_retrace
    flag_mid = pole_end - retrace_amount * 0.5
    flag_high = pole_end  # flag high = pole high area
    flag_low = pole_end - retrace_amount

    for i in range(flag_bars):
        # Oscillate in the flag range
        t = i / max(flag_bars - 1, 1)
        price = flag_mid + (flag_high - flag_mid) * (0.5 - abs(t - 0.5))
        candles.append(_bar(
            close=price,
            volume=flag_volume,
            offset_minutes=minute,
            open_=price + 0.05,
            high=min(price + 0.15, flag_high),
            low=max(price - 0.15, flag_low),
        ))
        minute += 1

    # Breakout candle
    bo_close = breakout_close if breakout_close is not None else flag_high + 0.50
    candles.append(_bar(
        close=bo_close,
        volume=breakout_volume,
        offset_minutes=minute,
        open_=flag_high - 0.10,
        high=bo_close + 0.10,
        low=flag_high - 0.20,
    ))

    return candles


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_bull_flag_detection() -> None:
    """Synthetic pole+flag+breakout candles produce PatternDetection."""
    pattern = BullFlagPattern(
        pole_min_bars=5,
        pole_min_move_pct=0.03,
        flag_max_bars=20,
        flag_max_retrace_pct=0.50,
        breakout_volume_multiplier=1.3,
    )
    candles = _build_bull_flag_candles(
        pole_bars=6,
        pole_start=100.0,
        pole_end=106.0,
        flag_bars=5,
        flag_retrace=0.30,
        flag_volume=800.0,
        breakout_volume=2000.0,
    )

    result = pattern.detect(candles, {})

    assert result is not None
    assert isinstance(result, PatternDetection)
    assert result.pattern_type == "bull_flag"
    assert result.entry_price > 0
    assert result.stop_price > 0
    assert result.stop_price < result.entry_price
    assert len(result.target_prices) == 1
    # Measured move target = entry + pole_height
    assert result.target_prices[0] > result.entry_price


def test_pole_too_short() -> None:
    """Fewer than pole_min_bars in the pole -> None."""
    pattern = BullFlagPattern(pole_min_bars=10)
    # Only 4 pole bars + 3 flag + 1 breakout = 8 candles
    candles = _build_bull_flag_candles(pole_bars=4, flag_bars=3)

    result = pattern.detect(candles, {})
    assert result is None


def test_pole_move_too_small() -> None:
    """Pole move < pole_min_move_pct -> None."""
    pattern = BullFlagPattern(pole_min_move_pct=0.10)
    # Pole from 100 to 103 = 3% move, but threshold is 10%
    candles = _build_bull_flag_candles(
        pole_start=100.0,
        pole_end=103.0,
        flag_bars=5,
        breakout_volume=2000.0,
    )

    result = pattern.detect(candles, {})
    assert result is None


def test_flag_retrace_too_deep() -> None:
    """Retracement > flag_max_retrace_pct -> None."""
    pattern = BullFlagPattern(flag_max_retrace_pct=0.20)
    # Flag retraces 80% of pole — way too deep for 20% max
    candles = _build_bull_flag_candles(
        pole_start=100.0,
        pole_end=106.0,
        flag_bars=5,
        flag_retrace=0.80,
        breakout_volume=2000.0,
    )

    result = pattern.detect(candles, {})
    assert result is None


def test_flag_too_long() -> None:
    """Flag > flag_max_bars -> None."""
    pattern = BullFlagPattern(flag_max_bars=3)
    # Build with 10 flag bars but max is 3
    candles = _build_bull_flag_candles(flag_bars=10, breakout_volume=2000.0)

    result = pattern.detect(candles, {})
    assert result is None


def test_no_volume_on_breakout() -> None:
    """Volume below multiplier -> None."""
    pattern = BullFlagPattern(breakout_volume_multiplier=3.0)
    # Flag volume 800, breakout volume 1000 → ratio 1.25 < 3.0
    candles = _build_bull_flag_candles(
        flag_volume=800.0,
        breakout_volume=1000.0,
    )

    result = pattern.detect(candles, {})
    assert result is None


def test_score_ranges() -> None:
    """Verify score components produce 0-100."""
    pattern = BullFlagPattern()
    candles = _build_bull_flag_candles(
        pole_start=100.0,
        pole_end=108.0,
        flag_bars=5,
        flag_retrace=0.20,
        breakout_volume=3000.0,
    )

    detection = pattern.detect(candles, {})
    assert detection is not None

    score = pattern.score(detection)
    assert 0 <= score <= 100

    # Also test with minimal detection metadata
    minimal_detection = PatternDetection(
        pattern_type="bull_flag",
        confidence=50.0,
        entry_price=106.0,
        stop_price=104.0,
        metadata={},
    )
    minimal_score = pattern.score(minimal_detection)
    assert 0 <= minimal_score <= 100


def test_config_yaml_key_validation() -> None:
    """Config YAML keys match BullFlagConfig model_fields — no silently ignored keys."""
    config_path = Path(__file__).resolve().parents[3] / "config" / "strategies" / "bull_flag.yaml"
    assert config_path.exists(), f"Config file not found: {config_path}"

    with open(config_path) as f:
        yaml_data = yaml.safe_load(f)

    # Load should succeed without error
    config = BullFlagConfig(**yaml_data)
    assert config.strategy_id == "strat_bull_flag"
    assert config.pole_min_bars == 5
    assert config.flag_max_bars == 20

    # Verify every YAML key is a valid model field (recursively check top-level)
    model_fields = set(BullFlagConfig.model_fields.keys())
    yaml_keys = set(yaml_data.keys())

    # These are nested model keys that Pydantic handles
    nested_keys = {"risk_limits", "operating_window", "benchmarks", "backtest_summary",
                   "universe_filter"}
    top_level_yaml = yaml_keys - nested_keys
    top_level_model = model_fields - nested_keys

    unexpected = top_level_yaml - top_level_model
    assert not unexpected, f"YAML keys not in BullFlagConfig: {unexpected}"
