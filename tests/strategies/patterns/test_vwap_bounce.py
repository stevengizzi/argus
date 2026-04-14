"""Tests for VwapBouncePattern detection module.

Sprint 31A, Session 4.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from argus.core.config import VwapBounceConfig
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternParam
from argus.strategies.patterns.vwap_bounce import VwapBouncePattern

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_VWAP_BOUNCE_YAML = _PROJECT_ROOT / "config" / "strategies" / "vwap_bounce.yaml"

BASE_TIME = datetime(2026, 3, 31, 11, 30, 0)
VWAP = 100.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bar(
    close: float,
    volume: float = 1000.0,
    offset_minutes: int = 0,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
) -> CandleBar:
    """Build a CandleBar with sensible OHLCV defaults."""
    o = open_ if open_ is not None else close
    h = high if high is not None else max(close, o) + 0.05
    lo = low if low is not None else min(close, o) - 0.05
    return CandleBar(
        timestamp=BASE_TIME + timedelta(minutes=offset_minutes),
        open=o,
        high=h,
        low=lo,
        close=close,
        volume=volume,
    )


def _build_vwap_bounce_candles(
    vwap: float = VWAP,
    prior_trend_bars: int = 12,
    approach_bars: int = 3,
    avg_volume: float = 1000.0,
    bounce_volume_mult: float = 1.5,
    touch_low_offset: float = 0.001,
    follow_through_bars: int = 2,
) -> list[CandleBar]:
    """Build a candle sequence with a detectable prior-trend → approach → touch → bounce.

    Structure:
        - prior_trend_bars bars clearly above VWAP (close = vwap * 1.012)
        - approach_bars bars approaching VWAP (close descending toward vwap * 1.003)
        - 1 touch bar: close near vwap, low within vwap_touch_tolerance_pct of VWAP
        - 2 bounce bars: close > vwap, first with high volume
        - follow_through_bars bars closing above VWAP after bounce confirmation

    Args:
        vwap: VWAP level.
        prior_trend_bars: Number of bars above VWAP before approach.
        approach_bars: Number of bars in the approach zone.
        avg_volume: Average volume for non-bounce bars.
        bounce_volume_mult: Multiplier on avg_volume for bounce bar.
        touch_low_offset: Fractional offset from VWAP for touch low (0 = exact touch).
        follow_through_bars: Follow-through bars closing above VWAP after bounce.

    Returns:
        List of CandleBar (oldest first, follow-through bars last).
    """
    candles: list[CandleBar] = []
    minute = 0

    # Prior uptrend: clearly above VWAP (>= min_approach_distance_pct=0.003)
    for _ in range(prior_trend_bars):
        price = vwap * 1.012
        candles.append(_bar(price, volume=avg_volume, offset_minutes=minute))
        minute += 1

    # Approach: price drifts toward VWAP from above
    approach_start_pct = 0.008
    approach_end_pct = 0.003
    step = (approach_start_pct - approach_end_pct) / max(1, approach_bars - 1)
    for i in range(approach_bars):
        pct = approach_start_pct - step * i
        price = vwap * (1 + pct)
        candles.append(_bar(price, volume=avg_volume, offset_minutes=minute))
        minute += 1

    # Touch bar: close just above VWAP, low within tolerance (0.2% of VWAP)
    touch_close = vwap * 1.0005
    touch_low = vwap * (1 - touch_low_offset) if touch_low_offset > 0 else vwap - 0.01
    candles.append(
        _bar(
            close=touch_close,
            volume=avg_volume,
            offset_minutes=minute,
            low=touch_low,
        )
    )
    minute += 1

    # Bounce bars: 2 consecutive closes above VWAP; first has high volume
    candles.append(
        _bar(
            close=vwap * 1.004,
            volume=avg_volume * bounce_volume_mult,
            offset_minutes=minute,
        )
    )
    minute += 1
    candles.append(
        _bar(
            close=vwap * 1.006,
            volume=avg_volume,
            offset_minutes=minute,
        )
    )
    minute += 1

    # Follow-through bars: close above VWAP after bounce confirmation
    for i in range(follow_through_bars):
        candles.append(
            _bar(
                close=vwap * (1.007 + 0.001 * i),
                volume=avg_volume,
                offset_minutes=minute,
            )
        )
        minute += 1

    return candles


# ---------------------------------------------------------------------------
# Test 1: Positive detection with synthetic prior-trend → approach → touch → bounce
# ---------------------------------------------------------------------------


def test_detect_returns_detection_on_valid_vwap_bounce() -> None:
    """detect() returns PatternDetection when valid prior-trend + touch + bounce."""
    pattern = VwapBouncePattern(
        vwap_approach_distance_pct=0.005,
        vwap_touch_tolerance_pct=0.002,
        min_bounce_bars=2,
        min_bounce_volume_ratio=1.3,
        min_prior_trend_bars=10,
        min_price_above_vwap_pct=0.003,
    )
    candles = _build_vwap_bounce_candles(
        vwap=VWAP,
        prior_trend_bars=12,
        approach_bars=3,
        avg_volume=1000.0,
        bounce_volume_mult=1.5,
        touch_low_offset=0.001,
    )
    indicators = {"vwap": VWAP, "atr": 0.5}
    result = pattern.detect(candles, indicators)

    assert result is not None
    assert result.pattern_type == "vwap_bounce"
    assert result.entry_price > 0
    assert result.stop_price < result.entry_price
    assert result.stop_price < VWAP
    assert len(result.target_prices) == 2
    assert result.target_prices[0] > result.entry_price
    assert result.target_prices[1] > result.target_prices[0]
    assert "vwap_value" in result.metadata
    assert "prior_trend_bars" in result.metadata
    assert "touch_depth_pct" in result.metadata
    assert "bounce_volume_ratio" in result.metadata


# ---------------------------------------------------------------------------
# Test 2: Returns None when VWAP unavailable
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_vwap_unavailable() -> None:
    """detect() returns None when vwap is missing from indicators."""
    pattern = VwapBouncePattern()
    candles = _build_vwap_bounce_candles()
    result = pattern.detect(candles, {"atr": 0.5})  # no vwap key
    assert result is None


def test_detect_returns_none_when_vwap_zero() -> None:
    """detect() returns None when vwap is 0."""
    pattern = VwapBouncePattern()
    candles = _build_vwap_bounce_candles()
    result = pattern.detect(candles, {"vwap": 0.0, "atr": 0.5})
    assert result is None


# ---------------------------------------------------------------------------
# Test 3: Returns None when price was below VWAP (insufficient prior trend)
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_below_vwap_prior() -> None:
    """detect() returns None when prior trend bars are mostly below VWAP."""
    pattern = VwapBouncePattern(min_prior_trend_bars=10)
    vwap = 100.0
    candles: list[CandleBar] = []
    minute = 0

    # Only 3 bars above VWAP — far below min_prior_trend_bars=10
    for _ in range(3):
        candles.append(_bar(vwap * 1.01, volume=1000.0, offset_minutes=minute))
        minute += 1

    # Many bars below VWAP
    for _ in range(15):
        candles.append(_bar(vwap * 0.99, volume=1000.0, offset_minutes=minute))
        minute += 1

    # Touch + bounce
    candles.append(_bar(vwap * 1.001, volume=1000.0, offset_minutes=minute, low=vwap * 0.999))
    minute += 1
    candles.append(_bar(vwap * 1.004, volume=2000.0, offset_minutes=minute))
    minute += 1
    candles.append(_bar(vwap * 1.006, volume=1000.0, offset_minutes=minute))

    result = pattern.detect(candles, {"vwap": vwap, "atr": 0.5})
    assert result is None


# ---------------------------------------------------------------------------
# Test 4: Returns None when insufficient bounce volume
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_bounce_volume_insufficient() -> None:
    """detect() returns None when bounce bar volume ratio is below threshold."""
    pattern = VwapBouncePattern(
        min_bounce_volume_ratio=2.0,  # require 2x
        vwap_touch_tolerance_pct=0.002,
        min_prior_trend_bars=10,
    )
    candles = _build_vwap_bounce_candles(
        avg_volume=1000.0,
        bounce_volume_mult=1.1,  # only 1.1x — below 2.0 threshold
    )
    result = pattern.detect(candles, {"vwap": VWAP, "atr": 0.5})
    assert result is None


# ---------------------------------------------------------------------------
# Test 5: Returns None when insufficient candle count
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_insufficient_candles() -> None:
    """detect() returns None when candle count is below min_detection_bars."""
    pattern = VwapBouncePattern(min_prior_trend_bars=10, min_bounce_bars=2)
    # Only 5 candles — far below min_prior_trend_bars + min_bounce_bars + 3
    candles = [_bar(VWAP * 1.01, offset_minutes=i) for i in range(5)]
    result = pattern.detect(candles, {"vwap": VWAP, "atr": 0.5})
    assert result is None


# ---------------------------------------------------------------------------
# Test 6: Returns None when touch is too far from VWAP
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_touch_too_far_from_vwap() -> None:
    """detect() returns None when no candle low comes within touch tolerance of VWAP."""
    pattern = VwapBouncePattern(
        vwap_touch_tolerance_pct=0.001,  # tight: 0.1% tolerance
        min_prior_trend_bars=10,
    )
    # Build candles where lows never get within 0.1% of VWAP
    candles: list[CandleBar] = []
    minute = 0

    # Prior trend: above VWAP
    for _ in range(12):
        candles.append(_bar(VWAP * 1.01, volume=1000.0, offset_minutes=minute))
        minute += 1

    # "Pullback" that stays 0.5% above VWAP — outside tolerance
    for _ in range(5):
        candles.append(
            _bar(
                close=VWAP * 1.005,
                volume=1000.0,
                offset_minutes=minute,
                low=VWAP * 1.003,  # low stays 0.3% above VWAP
            )
        )
        minute += 1

    # Bounce bars
    candles.append(_bar(VWAP * 1.008, volume=2000.0, offset_minutes=minute))
    minute += 1
    candles.append(_bar(VWAP * 1.010, volume=1000.0, offset_minutes=minute))

    result = pattern.detect(candles, {"vwap": VWAP, "atr": 0.5})
    assert result is None


# ---------------------------------------------------------------------------
# Test 7: score() boundary values
# ---------------------------------------------------------------------------


def test_score_returns_value_in_range() -> None:
    """score() returns a float in [0, 100] for any detection."""
    pattern = VwapBouncePattern()
    detection = PatternDetection(
        pattern_type="vwap_bounce",
        confidence=50.0,
        entry_price=100.4,
        stop_price=99.5,
        target_prices=(101.3, 102.2),
        metadata={
            "vwap_value": 100.0,
            "prior_trend_bars": 12,
            "touch_depth_pct": -0.001,
            "bounce_volume_ratio": 1.5,
            "approach_quality": 0.6,
            "avg_above_distance": 0.005,
            "atr": 0.4,
        },
    )
    score = pattern.score(detection)
    assert 0.0 <= score <= 100.0


def test_score_higher_for_strong_prior_trend_and_volume() -> None:
    """score() is higher when prior trend is strong and bounce volume is high."""
    pattern = VwapBouncePattern()

    weak_meta: dict[str, object] = {
        "vwap_value": 100.0,
        "prior_trend_bars": 5,
        "touch_depth_pct": 0.003,
        "bounce_volume_ratio": 1.1,
        "approach_quality": 0.2,
        "avg_above_distance": 0.002,
        "atr": 0.4,
    }
    strong_meta: dict[str, object] = {
        "vwap_value": 100.0,
        "prior_trend_bars": 20,
        "touch_depth_pct": 0.0001,
        "bounce_volume_ratio": 2.5,
        "approach_quality": 1.0,
        "avg_above_distance": 0.010,
        "atr": 0.4,
    }

    weak_detection = PatternDetection(
        pattern_type="vwap_bounce",
        confidence=20.0,
        entry_price=100.4,
        stop_price=99.5,
        metadata=weak_meta,
    )
    strong_detection = PatternDetection(
        pattern_type="vwap_bounce",
        confidence=80.0,
        entry_price=100.4,
        stop_price=99.5,
        metadata=strong_meta,
    )
    assert pattern.score(strong_detection) > pattern.score(weak_detection)


# ---------------------------------------------------------------------------
# Test 8: get_default_params() returns list[PatternParam] with correct count
# ---------------------------------------------------------------------------


def test_get_default_params_returns_correct_count() -> None:
    """get_default_params() returns 14 PatternParam entries (11 original + 3 DEF-154)."""
    pattern = VwapBouncePattern()
    params = pattern.get_default_params()

    assert isinstance(params, list)
    assert len(params) == 14
    assert all(isinstance(p, PatternParam) for p in params)


def test_get_default_params_all_have_required_fields() -> None:
    """Every PatternParam has name, param_type, default, and category."""
    pattern = VwapBouncePattern()
    params = pattern.get_default_params()

    for p in params:
        assert p.name, f"PatternParam missing name: {p}"
        assert p.param_type in (int, float, bool), f"Unexpected param_type: {p.param_type}"
        assert p.default is not None, f"PatternParam '{p.name}' missing default"
        assert p.category, f"PatternParam '{p.name}' missing category"


# ---------------------------------------------------------------------------
# Test 9: Cross-validation — config defaults match pattern defaults
# ---------------------------------------------------------------------------


def test_config_defaults_match_pattern_defaults() -> None:
    """VwapBounceConfig field defaults must match VwapBouncePattern constructor defaults."""
    config = VwapBounceConfig(strategy_id="test", name="Test")
    pattern = VwapBouncePattern()
    params = pattern.get_default_params()

    mismatches: list[str] = []
    for param in params:
        if not hasattr(config, param.name):
            continue
        config_val = getattr(config, param.name)
        pattern_val = param.default
        if config_val != pattern_val:
            mismatches.append(
                f"{param.name}: config={config_val}, pattern={pattern_val}"
            )

    assert not mismatches, "Config/pattern default mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# Test 10: Cross-validation — PatternParam ranges within Pydantic bounds
# ---------------------------------------------------------------------------


def test_pattern_param_ranges_within_pydantic_bounds() -> None:
    """PatternParam min_value/max_value must be within VwapBounceConfig ge/le bounds."""
    from pydantic.fields import FieldInfo

    config_class = VwapBounceConfig
    pattern = VwapBouncePattern()
    params = pattern.get_default_params()

    violations: list[str] = []
    for param in params:
        if param.min_value is None or param.max_value is None:
            continue
        if param.name not in config_class.model_fields:
            continue

        field_info: FieldInfo = config_class.model_fields[param.name]
        metadata = field_info.metadata

        pydantic_min: float | None = None
        pydantic_max: float | None = None
        for constraint in metadata:
            if hasattr(constraint, "ge"):
                pydantic_min = float(constraint.ge)
            if hasattr(constraint, "gt"):
                pydantic_min = float(constraint.gt)
            if hasattr(constraint, "le"):
                pydantic_max = float(constraint.le)
            if hasattr(constraint, "lt"):
                pydantic_max = float(constraint.lt)

        if pydantic_min is not None and param.min_value < pydantic_min:
            violations.append(
                f"{param.name}: PatternParam.min_value={param.min_value} < Pydantic ge/gt={pydantic_min}"
            )
        if pydantic_max is not None and param.max_value > pydantic_max:
            violations.append(
                f"{param.name}: PatternParam.max_value={param.max_value} > Pydantic le/lt={pydantic_max}"
            )

    assert not violations, "PatternParam ranges exceed Pydantic bounds:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Test 11: Config loading — YAML → Pydantic with no ignored keys
# ---------------------------------------------------------------------------


def test_config_yaml_loads_without_ignored_keys() -> None:
    """All detection/trade keys in vwap_bounce.yaml must be known to VwapBounceConfig."""
    if not _VWAP_BOUNCE_YAML.exists():
        pytest.skip("config/strategies/vwap_bounce.yaml not found")

    with open(_VWAP_BOUNCE_YAML) as f:
        raw = yaml.safe_load(f)

    base_strategy_fields = {
        "strategy_id", "name", "version", "enabled", "mode",
        "asset_class", "pipeline_stage", "family", "description_short",
        "time_window_display", "operating_window", "risk_limits",
        "benchmarks", "backtest_summary", "universe_filter", "exit_management",
    }

    model_fields = set(VwapBounceConfig.model_fields.keys())

    pattern_keys = {k for k in raw if k not in base_strategy_fields}
    unrecognized = pattern_keys - model_fields
    assert not unrecognized, f"YAML keys not in VwapBounceConfig: {sorted(unrecognized)}"


def test_config_yaml_round_trips_to_config_model() -> None:
    """Loading vwap_bounce.yaml into VwapBounceConfig must succeed."""
    if not _VWAP_BOUNCE_YAML.exists():
        pytest.skip("config/strategies/vwap_bounce.yaml not found")

    with open(_VWAP_BOUNCE_YAML) as f:
        raw = yaml.safe_load(f)

    config = VwapBounceConfig(**raw)
    assert config.strategy_id == "strat_vwap_bounce"
    assert config.vwap_touch_tolerance_pct == 0.002
    assert config.min_bounce_bars == 2
    assert config.target_1_r == 1.0
    assert config.target_2_r == 2.0


# ---------------------------------------------------------------------------
# Test 12: BacktestEngine — VWAP_BOUNCE strategy type creates runnable strategy
# ---------------------------------------------------------------------------


def test_backtest_engine_strategy_type_vwap_bounce_exists() -> None:
    """StrategyType.VWAP_BOUNCE must exist and equal 'vwap_bounce'."""
    from argus.backtest.config import StrategyType

    assert hasattr(StrategyType, "VWAP_BOUNCE")
    assert StrategyType.VWAP_BOUNCE == "vwap_bounce"


def test_backtest_engine_creates_vwap_bounce_strategy(tmp_path: Path) -> None:
    """BacktestEngine._create_vwap_bounce_strategy creates a PatternBasedStrategy."""
    import shutil
    from datetime import date
    from unittest.mock import MagicMock

    from argus.backtest.config import BacktestEngineConfig, StrategyType
    from argus.backtest.engine import BacktestEngine
    from argus.strategies.pattern_strategy import PatternBasedStrategy

    config_dir = tmp_path / "config" / "strategies"
    config_dir.mkdir(parents=True)
    if _VWAP_BOUNCE_YAML.exists():
        shutil.copy(_VWAP_BOUNCE_YAML, config_dir / "vwap_bounce.yaml")

    engine_config = BacktestEngineConfig(
        strategy_type=StrategyType.VWAP_BOUNCE,
        strategy_id="strat_vwap_bounce",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 30),
    )

    engine = BacktestEngine.__new__(BacktestEngine)
    engine._config = engine_config
    engine._data_service = MagicMock()
    engine._clock = MagicMock()

    strategy = engine._create_vwap_bounce_strategy(tmp_path / "config")
    assert isinstance(strategy, PatternBasedStrategy)
    assert strategy.config.strategy_id == "strat_vwap_bounce"


# ---------------------------------------------------------------------------
# Test 13: Factory registry — get_pattern_class("vwap_bounce") returns correct class
# ---------------------------------------------------------------------------


def test_factory_resolves_vwap_bounce_pattern() -> None:
    """get_pattern_class('vwap_bounce') returns VwapBouncePattern."""
    from argus.strategies.patterns.factory import get_pattern_class

    cls = get_pattern_class("vwap_bounce")
    assert cls is VwapBouncePattern


def test_factory_resolves_vwap_bounce_pascal_case() -> None:
    """get_pattern_class('VwapBouncePattern') also resolves correctly."""
    from argus.strategies.patterns.factory import get_pattern_class

    cls = get_pattern_class("VwapBouncePattern")
    assert cls is VwapBouncePattern


# ---------------------------------------------------------------------------
# Test 14: VWAP source is indicators dict, not computed from candles
# ---------------------------------------------------------------------------


def test_detect_uses_indicators_vwap_not_candle_average() -> None:
    """detect() returns None if vwap not in indicators, even with valid candles."""
    pattern = VwapBouncePattern(min_prior_trend_bars=10)
    # Build candles that look fine relative to 100.0 (includes follow-through bars)
    candles = _build_vwap_bounce_candles(vwap=100.0)
    # Pass indicators with a completely different VWAP — pattern should not infer its own
    result_no_vwap = pattern.detect(candles, {})
    assert result_no_vwap is None

    # With correct VWAP in indicators, should detect
    result_with_vwap = pattern.detect(candles, {"vwap": 100.0, "atr": 0.5})
    assert result_with_vwap is not None


# ---------------------------------------------------------------------------
# Tests 15–24: DEF-154 — signal density controls
# ---------------------------------------------------------------------------


def test_detect_rejects_no_approach_distance() -> None:
    """detect() returns None when price never >= 0.3% above VWAP before touch."""
    pattern = VwapBouncePattern(
        min_approach_distance_pct=0.003,
        min_prior_trend_bars=5,
        min_bounce_follow_through_bars=2,
    )
    vwap = 100.0
    candles: list[CandleBar] = []
    minute = 0

    # Many bars clearly above VWAP — satisfy prior trend check
    for _ in range(15):
        candles.append(_bar(vwap * 1.005, volume=1000.0, offset_minutes=minute))
        minute += 1

    # 12 bars only 0.1% above VWAP — within approach_window before touch, below 0.3% threshold
    for _ in range(12):
        candles.append(_bar(vwap * 1.001, volume=1000.0, offset_minutes=minute))
        minute += 1

    # Touch bar
    candles.append(_bar(vwap * 1.0005, volume=1000.0, offset_minutes=minute, low=vwap * 0.999))
    minute += 1

    # Bounce bars (high volume on first)
    candles.append(_bar(vwap * 1.004, volume=2000.0, offset_minutes=minute))
    minute += 1
    candles.append(_bar(vwap * 1.006, volume=1000.0, offset_minutes=minute))
    minute += 1

    # Follow-through bars
    candles.append(_bar(vwap * 1.007, volume=1000.0, offset_minutes=minute))
    minute += 1
    candles.append(_bar(vwap * 1.008, volume=1000.0, offset_minutes=minute))

    result = pattern.detect(candles, {"vwap": vwap, "atr": 0.5})
    assert result is None


def test_detect_requires_approach_distance() -> None:
    """detect() returns detection when price was >= 0.3% above VWAP before approach."""
    pattern = VwapBouncePattern(
        min_approach_distance_pct=0.003,
        min_prior_trend_bars=5,
        min_bounce_follow_through_bars=2,
    )
    vwap = 100.0
    # Prior trend bars at vwap * 1.012 — well above 0.3% threshold in approach window
    candles = _build_vwap_bounce_candles(vwap=vwap, prior_trend_bars=10, approach_bars=2)
    result = pattern.detect(candles, {"vwap": vwap, "atr": 0.5})
    assert result is not None


def test_detect_requires_bounce_follow_through() -> None:
    """detect() returns None when a follow-through bar closes below VWAP."""
    pattern = VwapBouncePattern(
        min_bounce_follow_through_bars=2,
        min_prior_trend_bars=5,
        min_bounce_bars=2,
        min_bounce_volume_ratio=1.3,
    )
    vwap = 100.0
    candles: list[CandleBar] = []
    minute = 0

    # Prior trend
    for _ in range(10):
        candles.append(_bar(vwap * 1.012, volume=1000.0, offset_minutes=minute))
        minute += 1

    # Approach bars (above 0.3% threshold in window)
    for _ in range(3):
        candles.append(_bar(vwap * 1.004, volume=1000.0, offset_minutes=minute))
        minute += 1

    # Touch bar
    candles.append(_bar(vwap * 1.0005, volume=1000.0, offset_minutes=minute, low=vwap * 0.999))
    minute += 1

    # Bounce bars: both above VWAP, first with high volume
    candles.append(_bar(vwap * 1.004, volume=2000.0, offset_minutes=minute))
    minute += 1
    candles.append(_bar(vwap * 1.006, volume=1000.0, offset_minutes=minute))
    minute += 1

    # Follow-through bar 1: above VWAP ✓
    candles.append(_bar(vwap * 1.003, volume=1000.0, offset_minutes=minute))
    minute += 1

    # Follow-through bar 2: BELOW VWAP ✗ — follow-through fails
    candles.append(_bar(vwap * 0.998, volume=1000.0, offset_minutes=minute))

    result = pattern.detect(candles, {"vwap": vwap, "atr": 0.5})
    assert result is None


def test_detect_with_follow_through() -> None:
    """detect() returns detection with entry_price at last follow-through bar."""
    pattern = VwapBouncePattern(
        min_bounce_follow_through_bars=2,
        min_prior_trend_bars=5,
        min_bounce_bars=2,
        min_bounce_volume_ratio=1.3,
    )
    vwap = 100.0
    candles = _build_vwap_bounce_candles(vwap=vwap, prior_trend_bars=10, follow_through_bars=2)
    result = pattern.detect(candles, {"vwap": vwap, "atr": 0.5})

    assert result is not None
    # Entry must be at the last follow-through bar (last candle in the sequence)
    assert result.entry_price == candles[-1].close


def test_max_signals_per_symbol_cap() -> None:
    """detect() returns None after max_signals_per_symbol detections for same symbol."""
    pattern = VwapBouncePattern(max_signals_per_symbol=3, min_prior_trend_bars=5)
    vwap = 100.0
    candles = _build_vwap_bounce_candles(vwap=vwap, prior_trend_bars=10)
    indicators = {"vwap": vwap, "atr": 0.5, "symbol": "TSLA"}

    # First 3 calls should detect
    for i in range(3):
        result = pattern.detect(candles, indicators)
        assert result is not None, f"Expected detection on call {i + 1}"

    # 4th call must be capped
    result = pattern.detect(candles, indicators)
    assert result is None


def test_max_signals_per_symbol_different_symbols() -> None:
    """Signal cap is per-symbol, not global — exhausting TSLA does not cap AAPL."""
    pattern = VwapBouncePattern(max_signals_per_symbol=2, min_prior_trend_bars=5)
    vwap = 100.0
    candles = _build_vwap_bounce_candles(vwap=vwap, prior_trend_bars=10)

    # Exhaust cap for TSLA
    for _ in range(2):
        pattern.detect(candles, {"vwap": vwap, "atr": 0.5, "symbol": "TSLA"})

    # TSLA is now capped
    assert pattern.detect(candles, {"vwap": vwap, "atr": 0.5, "symbol": "TSLA"}) is None

    # AAPL still has full capacity
    assert pattern.detect(candles, {"vwap": vwap, "atr": 0.5, "symbol": "AAPL"}) is not None


def test_reset_session_state() -> None:
    """reset_session_state() clears signal counts so the cap resets for a new session."""
    pattern = VwapBouncePattern(max_signals_per_symbol=1, min_prior_trend_bars=5)
    vwap = 100.0
    candles = _build_vwap_bounce_candles(vwap=vwap, prior_trend_bars=10)
    indicators = {"vwap": vwap, "atr": 0.5, "symbol": "TSLA"}

    # Exhaust the cap
    assert pattern.detect(candles, indicators) is not None
    assert pattern.detect(candles, indicators) is None

    # Reset and verify the cap is lifted
    pattern.reset_session_state()
    assert pattern.detect(candles, indicators) is not None


def test_min_prior_trend_bars_floor() -> None:
    """PatternParam min_value for min_prior_trend_bars must be 10 (raised from 5, DEF-154)."""
    pattern = VwapBouncePattern()
    params = {p.name: p for p in pattern.get_default_params()}
    assert params["min_prior_trend_bars"].min_value == 10


def test_new_params_in_default_params() -> None:
    """All 3 DEF-154 PatternParams appear with correct names and bounds."""
    pattern = VwapBouncePattern()
    params = {p.name: p for p in pattern.get_default_params()}

    assert "min_approach_distance_pct" in params
    p_approach = params["min_approach_distance_pct"]
    assert p_approach.min_value == 0.001
    assert p_approach.max_value == 0.010

    assert "min_bounce_follow_through_bars" in params
    p_follow = params["min_bounce_follow_through_bars"]
    assert p_follow.min_value == 0
    assert p_follow.max_value == 5

    assert "max_signals_per_symbol" in params
    p_cap = params["max_signals_per_symbol"]
    assert p_cap.min_value == 1
    assert p_cap.max_value == 10


def test_min_detection_bars_includes_follow_through() -> None:
    """min_detection_bars accounts for follow-through bars: prior + bounce + follow + 3."""
    pattern = VwapBouncePattern(
        min_prior_trend_bars=15,
        min_bounce_bars=2,
        min_bounce_follow_through_bars=2,
    )
    assert pattern.min_detection_bars == 22  # 15 + 2 + 2 + 3

    pattern2 = VwapBouncePattern(
        min_prior_trend_bars=10,
        min_bounce_bars=3,
        min_bounce_follow_through_bars=4,
    )
    assert pattern2.min_detection_bars == 20  # 10 + 3 + 4 + 3
