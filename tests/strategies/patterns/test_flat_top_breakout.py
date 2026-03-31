"""Tests for FlatTopBreakoutPattern detection module.

Sprint 26, Session 6.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from argus.core.config import FlatTopBreakoutConfig
from argus.strategies.patterns.base import CandleBar, PatternDetection
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern


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


def _build_flat_top_candles(
    resistance_level: float = 105.0,
    resistance_touches: int = 4,
    consolidation_bars: int = 12,
    consolidation_volume: float = 800.0,
    breakout_close: float | None = None,
    breakout_volume: float = 2000.0,
    resistance_tolerance: float = 0.002,
    range_narrowing: bool = True,
) -> list[CandleBar]:
    """Build synthetic candles for a valid flat-top breakout pattern.

    Creates candles that touch resistance multiple times, consolidate
    below it with narrowing range, then break out on volume.

    Args:
        resistance_level: The horizontal resistance price.
        resistance_touches: Number of candles that touch resistance.
        consolidation_bars: Total bars in the consolidation zone.
        consolidation_volume: Volume during consolidation.
        breakout_close: Breakout candle close (default: resistance + 0.50).
        breakout_volume: Volume on breakout candle.
        resistance_tolerance: Max distance from resistance for a "touch".
        range_narrowing: Whether to narrow range in second half.

    Returns:
        List of CandleBar forming a flat-top breakout pattern.
    """
    candles: list[CandleBar] = []
    minute = 0
    tolerance = resistance_level * resistance_tolerance

    # Build consolidation bars that touch resistance
    touch_indices = list(range(0, consolidation_bars, max(1, consolidation_bars // resistance_touches)))
    touch_indices = touch_indices[:resistance_touches]

    # Ensure we have enough touches spread across the consolidation
    while len(touch_indices) < resistance_touches and len(touch_indices) < consolidation_bars:
        next_idx = touch_indices[-1] + 1 if touch_indices else 0
        if next_idx < consolidation_bars:
            touch_indices.append(next_idx)

    for i in range(consolidation_bars):
        is_touch = i in touch_indices

        if is_touch:
            # Touch candle: high reaches resistance (within tolerance)
            close_price = resistance_level - 0.30
            high_price = resistance_level - (tolerance * 0.5)
            low_price = close_price - 0.40
        else:
            # Non-touch candle: high below resistance, each unique
            # Uses i-based offset on close/high/low to prevent
            # any clustering among non-touch highs.
            base_offset = 3.0 + i * 0.50  # well below resistance
            close_price = resistance_level - base_offset
            high_price = close_price + 0.10  # just above close, unique
            if range_narrowing and i >= consolidation_bars // 2:
                low_price = close_price - 0.30  # tighter range
            else:
                low_price = close_price - 1.00  # wider range

        candles.append(CandleBar(
            timestamp=BASE_TIME + timedelta(minutes=minute),
            open=close_price + 0.05,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=consolidation_volume,
        ))
        minute += 1

    # Breakout candle
    bo_close = breakout_close if breakout_close is not None else resistance_level + 0.50
    candles.append(CandleBar(
        timestamp=BASE_TIME + timedelta(minutes=minute),
        open=resistance_level - 0.10,
        high=bo_close + 0.10,
        low=resistance_level - 0.20,
        close=bo_close,
        volume=breakout_volume,
    ))

    return candles


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_flat_top_detection() -> None:
    """Synthetic resistance+consolidation+breakout -> PatternDetection."""
    pattern = FlatTopBreakoutPattern(
        resistance_touches=3,
        resistance_tolerance_pct=0.002,
        consolidation_min_bars=10,
        breakout_volume_multiplier=1.3,
    )
    candles = _build_flat_top_candles(
        resistance_level=105.0,
        resistance_touches=4,
        consolidation_bars=12,
        breakout_volume=2000.0,
    )

    result = pattern.detect(candles, {})

    assert result is not None
    assert isinstance(result, PatternDetection)
    assert result.pattern_type == "flat_top_breakout"
    assert result.entry_price > 0
    assert result.stop_price > 0
    assert result.stop_price < result.entry_price
    assert len(result.target_prices) == 2
    # T1 and T2 are R-multiples above entry
    assert result.target_prices[0] > result.entry_price
    assert result.target_prices[1] > result.target_prices[0]
    # Metadata populated
    assert "resistance_level" in result.metadata
    assert "resistance_touches" in result.metadata
    assert "consolidation_bars" in result.metadata


def test_insufficient_resistance_touches() -> None:
    """Fewer than required resistance touches -> None."""
    pattern = FlatTopBreakoutPattern(resistance_touches=5)
    # Only 2 touches, need 5
    candles = _build_flat_top_candles(
        resistance_touches=2,
        consolidation_bars=12,
        breakout_volume=2000.0,
    )

    result = pattern.detect(candles, {})
    assert result is None


def test_resistance_tolerance_exceeded() -> None:
    """Touches too spread out (tolerance too tight) -> None."""
    pattern = FlatTopBreakoutPattern(
        resistance_touches=3,
        resistance_tolerance_pct=0.0001,  # extremely tight tolerance
    )
    # Build with normal tolerance — touches will be too spread for 0.01%
    candles: list[CandleBar] = []
    for i in range(15):
        # Highs spread over a wide range — won't cluster within 0.01%
        high_price = 100.0 + i * 0.5
        candles.append(_bar(
            close=99.0,
            volume=800.0,
            offset_minutes=i,
            high=high_price,
            low=98.0,
        ))
    # Breakout candle
    candles.append(_bar(
        close=108.0,
        volume=3000.0,
        offset_minutes=15,
        high=108.5,
        low=107.0,
    ))

    result = pattern.detect(candles, {})
    assert result is None


def test_consolidation_too_short() -> None:
    """Consolidation < min_bars -> None."""
    pattern = FlatTopBreakoutPattern(
        consolidation_min_bars=10,
        resistance_touches=2,
    )
    # Only 5 consolidation bars, need 10
    candles = _build_flat_top_candles(
        resistance_touches=3,
        consolidation_bars=5,
        breakout_volume=2000.0,
    )

    result = pattern.detect(candles, {})
    assert result is None


def test_no_volume_on_breakout() -> None:
    """Volume below multiplier -> None."""
    pattern = FlatTopBreakoutPattern(
        breakout_volume_multiplier=3.0,
        resistance_touches=3,
        consolidation_min_bars=10,
    )
    # Consolidation volume 800, breakout volume 1000 → ratio 1.25 < 3.0
    candles = _build_flat_top_candles(
        resistance_touches=4,
        consolidation_bars=12,
        consolidation_volume=800.0,
        breakout_volume=1000.0,
    )

    result = pattern.detect(candles, {})
    assert result is None


def test_score_ranges() -> None:
    """Verify score components produce 0-100."""
    pattern = FlatTopBreakoutPattern()
    candles = _build_flat_top_candles(
        resistance_level=105.0,
        resistance_touches=5,
        consolidation_bars=15,
        breakout_volume=3000.0,
    )

    detection = pattern.detect(candles, {})
    assert detection is not None

    score = pattern.score(detection)
    assert 0 <= score <= 100

    # Also test with minimal detection metadata
    minimal_detection = PatternDetection(
        pattern_type="flat_top_breakout",
        confidence=50.0,
        entry_price=106.0,
        stop_price=103.0,
        metadata={},
    )
    minimal_score = pattern.score(minimal_detection)
    assert 0 <= minimal_score <= 100


def test_config_yaml_key_validation() -> None:
    """Config YAML keys match FlatTopBreakoutConfig model_fields."""
    config_path = (
        Path(__file__).resolve().parents[3]
        / "config"
        / "strategies"
        / "flat_top_breakout.yaml"
    )
    assert config_path.exists(), f"Config file not found: {config_path}"

    with open(config_path) as f:
        yaml_data = yaml.safe_load(f)

    # Load should succeed without error
    config = FlatTopBreakoutConfig(**yaml_data)
    assert config.strategy_id == "strat_flat_top_breakout"
    assert config.resistance_touches == 3
    assert config.consolidation_min_bars == 10

    # Verify every YAML key is a valid model field
    model_fields = set(FlatTopBreakoutConfig.model_fields.keys())
    yaml_keys = set(yaml_data.keys())

    nested_keys = {
        "risk_limits", "operating_window", "benchmarks",
        "backtest_summary", "universe_filter",
    }
    top_level_yaml = yaml_keys - nested_keys
    top_level_model = model_fields - nested_keys

    unexpected = top_level_yaml - top_level_model
    assert not unexpected, f"YAML keys not in FlatTopBreakoutConfig: {unexpected}"


def test_get_default_params() -> None:
    """get_default_params returns list[PatternParam] with expected values."""
    pattern = FlatTopBreakoutPattern(
        resistance_touches=4,
        resistance_tolerance_pct=0.003,
        consolidation_min_bars=15,
        breakout_volume_multiplier=1.5,
        target_1_r=1.0,
        target_2_r=2.5,
    )

    params = pattern.get_default_params()

    assert isinstance(params, list)
    defaults = {p.name: p.default for p in params}
    assert defaults["resistance_touches"] == 4
    assert defaults["resistance_tolerance_pct"] == 0.003
    assert defaults["consolidation_min_bars"] == 15
    assert defaults["breakout_volume_multiplier"] == 1.5
    assert defaults["target_1_r"] == 1.0
    assert defaults["target_2_r"] == 2.5


def test_breakout_below_resistance_rejected() -> None:
    """Breakout candle closing below resistance -> None."""
    pattern = FlatTopBreakoutPattern(
        resistance_touches=3,
        consolidation_min_bars=10,
    )
    # Breakout candle closes below resistance
    candles = _build_flat_top_candles(
        resistance_level=105.0,
        resistance_touches=4,
        consolidation_bars=12,
        breakout_close=104.5,  # below 105.0 resistance
        breakout_volume=2000.0,
    )

    result = pattern.detect(candles, {})
    assert result is None


def test_too_few_candles_returns_none() -> None:
    """Not enough candles for minimum detection window -> None."""
    pattern = FlatTopBreakoutPattern(consolidation_min_bars=10)
    # Only 3 candles, need consolidation_min_bars + 2 = 12
    candles = [_bar(close=100.0 + i, offset_minutes=i) for i in range(3)]

    result = pattern.detect(candles, {})
    assert result is None


def test_name_and_lookback_properties() -> None:
    """Verify name and lookback_bars properties."""
    pattern = FlatTopBreakoutPattern(consolidation_min_bars=10)

    assert pattern.name == "Flat-Top Breakout"
    assert pattern.lookback_bars == 20  # consolidation_min_bars + 10
