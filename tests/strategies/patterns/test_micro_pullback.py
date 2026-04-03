"""Tests for MicroPullbackPattern detection module.

Sprint 31A, Session 3.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from argus.core.config import MicroPullbackConfig
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternParam
from argus.strategies.patterns.micro_pullback import MicroPullbackPattern

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_MICRO_PULLBACK_YAML = _PROJECT_ROOT / "config" / "strategies" / "micro_pullback.yaml"

BASE_TIME = datetime(2026, 3, 31, 11, 0, 0)


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


def _build_impulse_pullback_bounce_candles(
    base_price: float = 100.0,
    impulse_bars: int = 5,
    impulse_pct: float = 0.03,
    pullback_bars: int = 3,
    avg_volume: float = 1000.0,
    bounce_volume_mult: float = 1.5,
    ema_period: int = 9,
) -> list[CandleBar]:
    """Build a candle sequence with a detectable impulse → pullback → bounce.

    Structure:
        - ema_period flat warmup bars at base_price
        - impulse_bars rising bars covering impulse_pct
        - pullback_bars declining back toward base + add EMA proximity candle
        - 1 bounce bar closing above EMA with high volume

    Returns:
        List of CandleBar (oldest first, bounce last).
    """
    candles: list[CandleBar] = []
    minute = 0

    # Warmup: flat bars at base_price to seed the EMA
    for _ in range(ema_period + 5):
        candles.append(_bar(base_price, volume=avg_volume, offset_minutes=minute))
        minute += 1

    # Impulse: rising bars
    high_price = base_price * (1 + impulse_pct)
    step = (high_price - base_price) / max(1, impulse_bars)
    for i in range(impulse_bars):
        price = base_price + step * (i + 1)
        candles.append(_bar(price, volume=avg_volume, offset_minutes=minute))
        minute += 1

    # Pullback: partial decline back toward EMA (which is ~base_price after warmup)
    # We want low to touch near EMA, so pull back ~60% of the impulse
    pullback_target = base_price + (high_price - base_price) * 0.3
    # Divide by pullback_bars - 1 so the last of the range() bars lands near EMA
    pull_step = (high_price - pullback_target) / max(1, pullback_bars - 1)
    for i in range(pullback_bars - 1):
        price = high_price - pull_step * (i + 1)
        candles.append(_bar(price, volume=avg_volume, offset_minutes=minute))
        minute += 1

    # Last pullback bar: low very close to EMA zone (touches base_price level)
    ema_touch_price = base_price * 1.005
    candles.append(
        _bar(
            close=ema_touch_price,
            volume=avg_volume,
            offset_minutes=minute,
            low=base_price * 0.999,  # low dips into EMA zone
        )
    )
    minute += 1

    # Bounce: closes above EMA with high volume.
    # EMA lags the impulse — use impulse_high * 0.99 to reliably close above
    # the lagging EMA (which is roughly midway between base and impulse peak).
    bounce_price = base_price * (1 + impulse_pct * 0.75)
    candles.append(
        _bar(
            close=bounce_price,
            volume=avg_volume * bounce_volume_mult,
            offset_minutes=minute,
        )
    )

    return candles


# ---------------------------------------------------------------------------
# Test 1: Positive detection with synthetic impulse + pullback + bounce
# ---------------------------------------------------------------------------


def test_detect_returns_detection_on_valid_impulse_pullback_bounce() -> None:
    """detect() returns PatternDetection when valid impulse → pullback → bounce."""
    pattern = MicroPullbackPattern(
        ema_period=9,
        min_impulse_percent=0.02,
        min_impulse_bars=3,
        max_impulse_bars=15,
        max_pullback_bars=5,
        pullback_tolerance_atr=0.5,
        min_bounce_volume_ratio=1.2,
    )
    candles = _build_impulse_pullback_bounce_candles(
        base_price=100.0,
        impulse_bars=5,
        impulse_pct=0.04,
        pullback_bars=4,
        avg_volume=1000.0,
        bounce_volume_mult=1.5,
        ema_period=9,
    )
    indicators = {"atr": 0.5, "vwap": 100.0}
    result = pattern.detect(candles, indicators)

    assert result is not None
    assert result.pattern_type == "micro_pullback"
    assert result.entry_price > 0
    assert result.stop_price < result.entry_price
    assert len(result.target_prices) == 2
    assert result.target_prices[0] > result.entry_price
    assert result.target_prices[1] > result.target_prices[0]
    assert "impulse_percent" in result.metadata
    assert "bounce_volume_ratio" in result.metadata


# ---------------------------------------------------------------------------
# Test 2: Returns None when impulse too small
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_impulse_too_small() -> None:
    """detect() returns None when the price move is below min_impulse_percent."""
    pattern = MicroPullbackPattern(
        ema_period=9,
        min_impulse_percent=0.03,  # require 3% impulse
    )
    # Build candles with only 1% impulse
    candles = _build_impulse_pullback_bounce_candles(
        base_price=100.0,
        impulse_bars=5,
        impulse_pct=0.01,  # only 1% — below threshold
        pullback_bars=3,
        avg_volume=1000.0,
        bounce_volume_mult=1.5,
        ema_period=9,
    )
    indicators = {"atr": 0.5, "vwap": 100.0}
    result = pattern.detect(candles, indicators)

    assert result is None


# ---------------------------------------------------------------------------
# Test 3: Returns None when no pullback to EMA
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_no_pullback_to_ema() -> None:
    """detect() returns None when price never pulls back into EMA zone."""
    pattern = MicroPullbackPattern(
        ema_period=9,
        min_impulse_percent=0.02,
        pullback_tolerance_atr=0.1,  # very tight tolerance — won't be met
    )
    # Build candles but with a pullback that stays far above EMA
    candles: list[CandleBar] = []
    minute = 0
    base = 100.0
    avg_vol = 1000.0

    # Warmup
    for _ in range(14):
        candles.append(_bar(base, volume=avg_vol, offset_minutes=minute))
        minute += 1

    # Impulse: 3% up
    for i in range(5):
        candles.append(_bar(base * (1 + 0.006 * (i + 1)), volume=avg_vol, offset_minutes=minute))
        minute += 1

    # "Pullback" that never gets close to EMA (stays 10% above it)
    for i in range(4):
        candles.append(
            _bar(
                close=base * 1.05,
                volume=avg_vol,
                offset_minutes=minute,
                low=base * 1.04,  # stays far above EMA at ~base
            )
        )
        minute += 1

    # Bounce bar
    candles.append(_bar(base * 1.06, volume=avg_vol * 2.0, offset_minutes=minute))

    indicators = {"atr": 0.5, "vwap": 100.0}
    result = pattern.detect(candles, indicators)

    assert result is None


# ---------------------------------------------------------------------------
# Test 4: Returns None when bounce volume insufficient
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_bounce_volume_insufficient() -> None:
    """detect() returns None when bounce bar volume ratio is below threshold."""
    pattern = MicroPullbackPattern(
        ema_period=9,
        min_impulse_percent=0.02,
        min_bounce_volume_ratio=2.0,  # require 2x volume
        pullback_tolerance_atr=0.5,
    )
    # Build candles with only 1.1x bounce volume (below 2.0 threshold)
    candles = _build_impulse_pullback_bounce_candles(
        base_price=100.0,
        impulse_bars=5,
        impulse_pct=0.04,
        pullback_bars=4,
        avg_volume=1000.0,
        bounce_volume_mult=1.1,  # well below 2.0 threshold
        ema_period=9,
    )
    indicators = {"atr": 0.5, "vwap": 100.0}
    result = pattern.detect(candles, indicators)

    assert result is None


# ---------------------------------------------------------------------------
# Test 5: score() boundary values
# ---------------------------------------------------------------------------


def test_score_returns_value_in_range() -> None:
    """score() returns a float in [0, 100] for any detection."""
    pattern = MicroPullbackPattern()
    detection = PatternDetection(
        pattern_type="micro_pullback",
        confidence=50.0,
        entry_price=102.0,
        stop_price=100.0,
        target_prices=(104.0, 106.0),
        metadata={
            "impulse_percent": 0.03,
            "impulse_bars": 5,
            "pullback_depth": 0.3,
            "ema_value": 100.5,
            "pullback_low": 100.3,
            "bounce_volume_ratio": 1.5,
            "atr": 0.4,
            "vwap": 101.0,
        },
    )
    score = pattern.score(detection)
    assert 0.0 <= score <= 100.0


def test_score_higher_for_strong_impulse_and_volume() -> None:
    """score() is higher when impulse is large and bounce volume is high."""
    pattern = MicroPullbackPattern()
    base_meta: dict[str, object] = {
        "impulse_percent": 0.02,
        "impulse_bars": 10,
        "pullback_depth": 0.5,
        "ema_value": 100.0,
        "pullback_low": 100.2,
        "bounce_volume_ratio": 1.2,
        "atr": 0.5,
        "vwap": 99.0,
    }
    strong_meta: dict[str, object] = {
        "impulse_percent": 0.06,
        "impulse_bars": 3,
        "pullback_depth": 0.2,
        "ema_value": 100.0,
        "pullback_low": 100.05,
        "bounce_volume_ratio": 2.5,
        "atr": 0.5,
        "vwap": 101.0,
    }
    weak_detection = PatternDetection(
        pattern_type="micro_pullback",
        confidence=30.0,
        entry_price=101.0,
        stop_price=99.5,
        metadata=base_meta,
    )
    strong_detection = PatternDetection(
        pattern_type="micro_pullback",
        confidence=80.0,
        entry_price=102.0,
        stop_price=100.5,
        metadata=strong_meta,
    )
    assert pattern.score(strong_detection) > pattern.score(weak_detection)


# ---------------------------------------------------------------------------
# Test 6: get_default_params() returns list[PatternParam] with correct count
# ---------------------------------------------------------------------------


def test_get_default_params_returns_correct_count() -> None:
    """get_default_params() returns 12 PatternParam entries."""
    pattern = MicroPullbackPattern()
    params = pattern.get_default_params()

    assert isinstance(params, list)
    assert len(params) == 12
    assert all(isinstance(p, PatternParam) for p in params)


def test_get_default_params_all_have_required_fields() -> None:
    """Every PatternParam has name, param_type, default, and category."""
    pattern = MicroPullbackPattern()
    params = pattern.get_default_params()

    for p in params:
        assert p.name, f"PatternParam missing name: {p}"
        assert p.param_type in (int, float, bool), f"Unexpected param_type: {p.param_type}"
        assert p.default is not None, f"PatternParam '{p.name}' missing default"
        assert p.category, f"PatternParam '{p.name}' missing category"


# ---------------------------------------------------------------------------
# Test 7: Cross-validation — config defaults match pattern defaults
# ---------------------------------------------------------------------------


def test_config_defaults_match_pattern_defaults() -> None:
    """MicroPullbackConfig field defaults must match MicroPullbackPattern constructor defaults."""
    config = MicroPullbackConfig(strategy_id="test", name="Test")
    pattern = MicroPullbackPattern()
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

    assert not mismatches, f"Config/pattern default mismatches:\n" + "\n".join(mismatches)


# ---------------------------------------------------------------------------
# Test 8: Cross-validation — PatternParam ranges within Pydantic bounds
# ---------------------------------------------------------------------------


def test_pattern_param_ranges_within_pydantic_bounds() -> None:
    """PatternParam min_value/max_value must be within MicroPullbackConfig ge/le bounds."""
    from pydantic.fields import FieldInfo

    config_class = MicroPullbackConfig
    pattern = MicroPullbackPattern()
    params = pattern.get_default_params()

    violations: list[str] = []
    for param in params:
        if param.min_value is None or param.max_value is None:
            continue
        if param.name not in config_class.model_fields:
            continue

        field_info: FieldInfo = config_class.model_fields[param.name]
        metadata = field_info.metadata

        # Extract ge/le/gt/lt from metadata
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
# Test 9: Config loading — YAML → Pydantic with no ignored keys
# ---------------------------------------------------------------------------


def test_config_yaml_loads_without_ignored_keys() -> None:
    """All detection/trade keys in micro_pullback.yaml must be known to MicroPullbackConfig."""
    if not _MICRO_PULLBACK_YAML.exists():
        pytest.skip("config/strategies/micro_pullback.yaml not found")

    with open(_MICRO_PULLBACK_YAML) as f:
        raw = yaml.safe_load(f)

    # Standard StrategyConfig fields that are expected/allowed to be in YAML
    base_strategy_fields = {
        "strategy_id", "name", "version", "enabled", "mode",
        "asset_class", "pipeline_stage", "family", "description_short",
        "time_window_display", "operating_window", "risk_limits",
        "benchmarks", "backtest_summary", "universe_filter", "exit_management",
    }

    model_fields = set(MicroPullbackConfig.model_fields.keys())
    all_known = base_strategy_fields | model_fields

    pattern_keys = {k for k in raw if k not in base_strategy_fields}
    unrecognized = pattern_keys - model_fields
    assert not unrecognized, f"YAML keys not in MicroPullbackConfig: {sorted(unrecognized)}"


def test_config_yaml_round_trips_to_config_model() -> None:
    """Loading micro_pullback.yaml into MicroPullbackConfig must succeed."""
    if not _MICRO_PULLBACK_YAML.exists():
        pytest.skip("config/strategies/micro_pullback.yaml not found")

    with open(_MICRO_PULLBACK_YAML) as f:
        raw = yaml.safe_load(f)

    config = MicroPullbackConfig(**raw)
    assert config.strategy_id == "strat_micro_pullback"
    assert config.ema_period == 9
    assert config.min_impulse_percent == 0.02
    assert config.target_1_r == 1.0
    assert config.target_2_r == 2.0


# ---------------------------------------------------------------------------
# Test 10: BacktestEngine — MICRO_PULLBACK strategy type creates runnable strategy
# ---------------------------------------------------------------------------


def test_backtest_engine_strategy_type_micro_pullback_exists() -> None:
    """StrategyType.MICRO_PULLBACK must exist and equal 'micro_pullback'."""
    from argus.backtest.config import StrategyType

    assert hasattr(StrategyType, "MICRO_PULLBACK")
    assert StrategyType.MICRO_PULLBACK == "micro_pullback"


def test_backtest_engine_creates_micro_pullback_strategy(tmp_path: Path) -> None:
    """BacktestEngine._create_micro_pullback_strategy creates a PatternBasedStrategy."""
    import shutil
    from datetime import date
    from unittest.mock import MagicMock

    from argus.backtest.config import BacktestEngineConfig, StrategyType
    from argus.backtest.engine import BacktestEngine
    from argus.strategies.pattern_strategy import PatternBasedStrategy

    # Copy the YAML into a temp config dir matching engine expectations
    config_dir = tmp_path / "config" / "strategies"
    config_dir.mkdir(parents=True)
    if _MICRO_PULLBACK_YAML.exists():
        shutil.copy(_MICRO_PULLBACK_YAML, config_dir / "micro_pullback.yaml")

    engine_config = BacktestEngineConfig(
        strategy_type=StrategyType.MICRO_PULLBACK,
        strategy_id="strat_micro_pullback",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 30),
    )

    engine = BacktestEngine.__new__(BacktestEngine)
    engine._config = engine_config
    engine._data_service = MagicMock()
    engine._clock = MagicMock()

    strategy = engine._create_micro_pullback_strategy(tmp_path / "config")
    assert isinstance(strategy, PatternBasedStrategy)
    assert strategy.config.strategy_id == "strat_micro_pullback"


# ---------------------------------------------------------------------------
# Test 11: Factory registry — get_pattern_class("micro_pullback") returns correct class
# ---------------------------------------------------------------------------


def test_factory_resolves_micro_pullback_pattern() -> None:
    """get_pattern_class('micro_pullback') returns MicroPullbackPattern."""
    from argus.strategies.patterns.factory import get_pattern_class

    cls = get_pattern_class("micro_pullback")
    assert cls is MicroPullbackPattern


def test_factory_resolves_micro_pullback_pascal_case() -> None:
    """get_pattern_class('MicroPullbackPattern') also resolves correctly."""
    from argus.strategies.patterns.factory import get_pattern_class

    cls = get_pattern_class("MicroPullbackPattern")
    assert cls is MicroPullbackPattern


# ---------------------------------------------------------------------------
# Test 12: detect() returns None when insufficient candles
# ---------------------------------------------------------------------------


def test_detect_returns_none_when_insufficient_candles() -> None:
    """detect() returns None when candle count is below min_required."""
    pattern = MicroPullbackPattern(ema_period=9)
    candles = [_bar(100.0, offset_minutes=i) for i in range(10)]
    result = pattern.detect(candles, {"atr": 0.5})
    assert result is None
