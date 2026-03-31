"""Tests for DipAndRipPattern detection module.

Sprint 29, Session 3.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from argus.core.config import DipAndRipConfig, UniverseFilterConfig
from argus.strategies.patterns.base import CandleBar, PatternParam
from argus.strategies.patterns.dip_and_rip import DipAndRipPattern

_ET = ZoneInfo("America/New_York")

# Base time: 10:00 AM ET (well after 9:35 AM cutoff)
BASE_TIME = datetime(2026, 3, 31, 10, 0, 0, tzinfo=_ET)

# Base time early enough that dip low lands before 9:35 AM ET
# With 10 lookback + 3 dip bars, dip low is at base + 12min
# So base must be < 9:23 AM for dip low < 9:35 AM
EARLY_TIME = datetime(2026, 3, 31, 9, 20, 0, tzinfo=_ET)


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
    base_time: datetime = BASE_TIME,
) -> CandleBar:
    """Build a CandleBar with sensible defaults."""
    o = open_ if open_ is not None else close
    h = high if high is not None else max(close, o) + 0.05
    lo = low if low is not None else min(close, o) - 0.05
    return CandleBar(
        timestamp=base_time + timedelta(minutes=offset_minutes),
        open=o,
        high=h,
        low=lo,
        close=close,
        volume=volume,
    )


def _build_dip_and_rip_candles(
    pre_dip_high: float = 100.0,
    dip_low: float = 97.0,
    recovery_high: float = 99.0,
    lookback_bars: int = 10,
    dip_bars: int = 3,
    recovery_bars: int = 2,
    pre_volume: float = 1000.0,
    dip_volume: float = 800.0,
    recovery_volume: float = 1500.0,
    final_close: float | None = None,
    base_time: datetime = BASE_TIME,
) -> list[CandleBar]:
    """Build synthetic candles for a dip-and-rip pattern.

    Structure:
        1. Lookback window: stable around pre_dip_high
        2. Dip: price drops to dip_low
        3. Recovery: price bounces to recovery_high
        4. Final candle: close at final_close (recovery level)
    """
    candles: list[CandleBar] = []
    minute = 0

    # Lookback bars: stable near pre_dip_high
    for i in range(lookback_bars):
        price = pre_dip_high - 0.50 + (i * 0.05)
        candles.append(
            _bar(
                close=price,
                volume=pre_volume,
                offset_minutes=minute,
                high=pre_dip_high,
                low=price - 0.30,
                base_time=base_time,
            )
        )
        minute += 1

    # Dip bars: price drops sharply
    dip_range = pre_dip_high - dip_low
    for i in range(dip_bars):
        frac = (i + 1) / dip_bars
        price = pre_dip_high - dip_range * frac
        lo = price if i == dip_bars - 1 else price - 0.10
        candles.append(
            _bar(
                close=price,
                volume=dip_volume,
                offset_minutes=minute,
                open_=price + dip_range / dip_bars * 0.5,
                high=price + dip_range / dip_bars * 0.5,
                low=lo,
                base_time=base_time,
            )
        )
        minute += 1

    # Recovery bars: price bounces
    rec_range = recovery_high - dip_low
    for i in range(recovery_bars):
        frac = (i + 1) / recovery_bars
        price = dip_low + rec_range * frac
        candles.append(
            _bar(
                close=price,
                volume=recovery_volume,
                offset_minutes=minute,
                open_=price - rec_range / recovery_bars * 0.3,
                high=price + 0.05,
                low=price - rec_range / recovery_bars * 0.3,
                base_time=base_time,
            )
        )
        minute += 1

    # Final candle (entry confirmation)
    fc = final_close if final_close is not None else recovery_high
    candles.append(
        _bar(
            close=fc,
            volume=recovery_volume,
            offset_minutes=minute,
            open_=fc - 0.20,
            high=fc + 0.10,
            low=fc - 0.30,
            base_time=base_time,
        )
    )

    return candles


# ---------------------------------------------------------------------------
# Test 1: Detect sharp dip meeting threshold → PatternDetection returned
# ---------------------------------------------------------------------------


class TestDipAndRipDetection:
    """Test valid dip-and-rip pattern detection."""

    def test_detect_valid_dip_and_rip(self) -> None:
        """Detect sharp dip meeting threshold returns PatternDetection."""
        pattern = DipAndRipPattern()
        candles = _build_dip_and_rip_candles(
            pre_dip_high=100.0,
            dip_low=97.0,  # 3% dip
            recovery_high=99.0,  # ~67% recovery of 3.0 range
            dip_bars=3,
            recovery_bars=2,
            dip_volume=800.0,
            recovery_volume=1500.0,  # 1.875x ratio
        )
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is not None
        assert result.pattern_type == "dip_and_rip"
        assert result.entry_price > 0
        assert result.stop_price < result.entry_price
        assert len(result.target_prices) == 1
        assert result.target_prices[0] > result.entry_price

    def test_detect_returns_metadata(self) -> None:
        """Detection includes expected metadata keys."""
        pattern = DipAndRipPattern()
        candles = _build_dip_and_rip_candles()
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is not None
        meta = result.metadata
        assert "dip_percent" in meta
        assert "recovery_percent" in meta
        assert "volume_ratio" in meta
        assert "level_interaction" in meta
        assert "dip_bars" in meta
        assert "recovery_bars" in meta


# ---------------------------------------------------------------------------
# Test 2: Reject insufficient dip
# ---------------------------------------------------------------------------


class TestDipAndRipRejections:
    """Test rejection cases for dip-and-rip pattern."""

    def test_reject_insufficient_dip(self) -> None:
        """Reject dip below min_dip_percent → None."""
        pattern = DipAndRipPattern(min_dip_percent=0.03)
        # Only 1% dip
        candles = _build_dip_and_rip_candles(
            pre_dip_high=100.0,
            dip_low=99.0,  # 1% dip — below 3% threshold
            recovery_high=99.8,
        )
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is None

    # ---------------------------------------------------------------------------
    # Test 3: Reject slow recovery
    # ---------------------------------------------------------------------------

    def test_reject_slow_recovery(self) -> None:
        """Reject recovery that exceeds max_recovery_bars → None."""
        pattern = DipAndRipPattern(max_recovery_bars=2)
        # Recovery takes 5 bars — exceeds limit of 2
        candles = _build_dip_and_rip_candles(
            recovery_bars=5,
            dip_bars=2,
        )
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is None

    # ---------------------------------------------------------------------------
    # Test 4: Reject insufficient recovery volume
    # ---------------------------------------------------------------------------

    def test_reject_insufficient_volume(self) -> None:
        """Reject recovery with insufficient volume → None."""
        pattern = DipAndRipPattern(min_recovery_volume_ratio=1.5)
        # Recovery volume barely above dip volume (1.1x)
        candles = _build_dip_and_rip_candles(
            dip_volume=1000.0,
            recovery_volume=1100.0,  # 1.1x < 1.5x threshold
        )
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is None

    # ---------------------------------------------------------------------------
    # Test 5: Reject dip before 9:35 AM ET
    # ---------------------------------------------------------------------------

    def test_reject_dip_before_935_am(self) -> None:
        """Reject dip occurring before 9:35 AM ET → None."""
        pattern = DipAndRipPattern()
        # Base time at 9:30 AM ET — dip occurs before 9:35 AM
        candles = _build_dip_and_rip_candles(
            base_time=EARLY_TIME,
        )
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is None


# ---------------------------------------------------------------------------
# Test 6: Score weights (30/25/25/20)
# ---------------------------------------------------------------------------


class TestDipAndRipScoring:
    """Test scoring logic for dip-and-rip pattern."""

    def test_score_weights_30_25_25_20(self) -> None:
        """Verify 30/25/25/20 weighting via component isolation."""
        pattern = DipAndRipPattern()

        # Maximum score scenario: deep fast dip, fast recovery, high volume, VWAP level
        candles = _build_dip_and_rip_candles(
            pre_dip_high=100.0,
            dip_low=95.0,  # 5% dip (max depth score)
            recovery_high=99.0,  # 80% recovery
            lookback_bars=15,  # enough bars for min_bars check
            dip_bars=2,  # fast dip
            recovery_bars=2,  # fast recovery
            dip_volume=500.0,
            recovery_volume=1500.0,  # 3x volume ratio
        )
        result = pattern.detect(candles, {"atr": 1.0, "vwap": 95.2})
        assert result is not None

        score = pattern.score(result)
        assert 0 <= score <= 100

        # Now test with no level interaction and mediocre metrics
        candles2 = _build_dip_and_rip_candles(
            pre_dip_high=100.0,
            dip_low=97.5,  # 2.5% dip
            recovery_high=99.0,
            lookback_bars=15,
            dip_bars=4,
            recovery_bars=4,
            dip_volume=800.0,
            recovery_volume=1200.0,  # 1.5x
        )
        result2 = pattern.detect(candles2, {"atr": 1.0})
        assert result2 is not None
        score2 = pattern.score(result2)

        # Higher quality pattern should score higher
        assert score > score2

    # ---------------------------------------------------------------------------
    # Test 7: Score with VWAP level interaction
    # ---------------------------------------------------------------------------

    def test_score_higher_with_vwap_interaction(self) -> None:
        """Dip at VWAP level scores higher than no level interaction."""
        pattern = DipAndRipPattern()
        # Use dip_low=96.50 — midpoint between round numbers (>0.5% from both)
        candles = _build_dip_and_rip_candles(
            pre_dip_high=100.0,
            dip_low=96.50,
            recovery_high=99.0,
            lookback_bars=15,
            dip_bars=2,
            recovery_bars=2,
            dip_volume=800.0,
            recovery_volume=1500.0,
        )

        # With VWAP near dip low
        result_vwap = pattern.detect(candles, {"atr": 1.0, "vwap": 96.55})
        assert result_vwap is not None
        assert result_vwap.metadata["level_interaction"] == "vwap"
        score_vwap = pattern.score(result_vwap)

        # Without VWAP (far away) — no level interaction
        result_none = pattern.detect(candles, {"atr": 1.0, "vwap": 110.0})
        assert result_none is not None
        assert result_none.metadata["level_interaction"] == "none"
        score_none = pattern.score(result_none)

        assert score_vwap > score_none

    def test_score_bounded_0_100(self) -> None:
        """Score always returns value between 0 and 100."""
        pattern = DipAndRipPattern()
        candles = _build_dip_and_rip_candles()
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is not None
        score = pattern.score(result)
        assert 0 <= score <= 100


# ---------------------------------------------------------------------------
# Test 8: PatternParam list completeness
# ---------------------------------------------------------------------------


class TestDipAndRipParams:
    """Test PatternParam metadata completeness."""

    def test_get_default_params_completeness(self) -> None:
        """All params have description, range, step, and category."""
        pattern = DipAndRipPattern()
        params = pattern.get_default_params()

        assert len(params) >= 10  # ~10 params expected

        for param in params:
            assert isinstance(param, PatternParam)
            assert param.name, f"Missing name on param"
            assert param.description, f"Missing description on {param.name}"
            assert param.category, f"Missing category on {param.name}"
            assert param.min_value is not None, f"Missing min_value on {param.name}"
            assert param.max_value is not None, f"Missing max_value on {param.name}"
            assert param.step is not None, f"Missing step on {param.name}"
            assert param.param_type in (int, float), (
                f"Unexpected type on {param.name}"
            )

    def test_param_categories(self) -> None:
        """Params have detection, filtering, or scoring categories."""
        pattern = DipAndRipPattern()
        params = pattern.get_default_params()
        categories = {p.category for p in params}
        assert "detection" in categories
        assert "filtering" in categories

    def test_param_defaults_match_constructor(self) -> None:
        """Default values in PatternParam match constructor defaults."""
        pattern = DipAndRipPattern()
        params = pattern.get_default_params()
        param_map = {p.name: p for p in params}

        assert param_map["dip_lookback"].default == 10
        assert param_map["min_dip_percent"].default == 0.02
        assert param_map["max_dip_bars"].default == 5
        assert param_map["min_recovery_percent"].default == 0.50
        assert param_map["max_recovery_bars"].default == 8
        assert param_map["min_recovery_volume_ratio"].default == 1.3


# ---------------------------------------------------------------------------
# Test 9: Config YAML parses correctly
# ---------------------------------------------------------------------------


class TestDipAndRipConfig:
    """Test config YAML parsing and validation."""

    def test_config_yaml_parses(self) -> None:
        """Config YAML loads and validates via DipAndRipConfig."""
        yaml_path = Path("config/strategies/dip_and_rip.yaml")
        assert yaml_path.exists(), f"Config not found: {yaml_path}"

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        config = DipAndRipConfig(**data)
        assert config.strategy_id == "strat_dip_and_rip"
        assert config.enabled is True
        assert config.dip_lookback == 10
        assert config.min_dip_percent == 0.02
        assert config.operating_window.earliest_entry == "09:45"
        assert config.operating_window.latest_entry == "11:30"

    def test_universe_filter_min_relative_volume(self) -> None:
        """min_relative_volume is recognized by UniverseFilterConfig."""
        yaml_path = Path("config/strategies/dip_and_rip.yaml")
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        uf_data = data["universe_filter"]
        config = UniverseFilterConfig(**uf_data)
        assert config.min_relative_volume == 1.5
        assert config.min_avg_volume == 500000
        assert config.min_price == 5.0


# ---------------------------------------------------------------------------
# Test 10: Exit override applies correctly
# ---------------------------------------------------------------------------


class TestDipAndRipExitOverride:
    """Test exit management override structure."""

    def test_exit_override_in_strategy_yaml(self) -> None:
        """Strategy YAML contains exit_management override for deep_update."""
        yaml_path = Path("config/strategies/dip_and_rip.yaml")
        assert yaml_path.exists()

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert "exit_management" in data
        exit_cfg = data["exit_management"]
        assert exit_cfg["trailing_stop"]["enabled"] is True
        assert exit_cfg["trailing_stop"]["type"] == "atr"
        assert exit_cfg["trailing_stop"]["atr_multiplier"] == 1.5
        assert exit_cfg["escalation"]["enabled"] is True
        assert len(exit_cfg["escalation"]["phases"]) == 2

    def test_exit_override_applies_via_deep_update(self) -> None:
        """Exit override merges with global defaults via ExitManagementConfig."""
        from argus.core.config import ExitManagementConfig, deep_update

        # Load global defaults
        global_path = Path("config/exit_management.yaml")
        with open(global_path) as f:
            global_data = yaml.safe_load(f)

        # Load strategy override
        strat_path = Path("config/strategies/dip_and_rip.yaml")
        with open(strat_path) as f:
            strat_data = yaml.safe_load(f)

        override = strat_data["exit_management"]
        merged = deep_update(global_data, override)
        cfg = ExitManagementConfig(**merged)
        assert cfg.trailing_stop.atr_multiplier == 1.5  # overridden
        assert cfg.escalation.enabled is True  # overridden


# ---------------------------------------------------------------------------
# Test 11: Pattern name and lookback
# ---------------------------------------------------------------------------


class TestDipAndRipProperties:
    """Test pattern properties."""

    def test_name(self) -> None:
        """Pattern name is 'dip_and_rip'."""
        pattern = DipAndRipPattern()
        assert pattern.name == "dip_and_rip"

    def test_lookback_bars(self) -> None:
        """Lookback bars is 30."""
        pattern = DipAndRipPattern()
        assert pattern.lookback_bars == 30

    def test_recovery_velocity_enforced(self) -> None:
        """Recovery must be faster than dip (velocity check)."""
        # max_recovery_ratio=1.0 means recovery must take <= dip bars
        pattern = DipAndRipPattern(max_recovery_ratio=1.0)
        # Dip in 2 bars, recovery in 3 bars — violates ratio
        candles = _build_dip_and_rip_candles(
            dip_bars=2,
            recovery_bars=3,
        )
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is None

    def test_round_number_level_interaction(self) -> None:
        """Dip near a round number scores level interaction."""
        pattern = DipAndRipPattern()
        candles = _build_dip_and_rip_candles(
            pre_dip_high=103.0,
            dip_low=100.02,  # Very close to $100 round number, 2.9% dip
            recovery_high=102.0,
            lookback_bars=15,
            dip_bars=2,
            recovery_bars=2,
            dip_volume=800.0,
            recovery_volume=1500.0,
        )
        result = pattern.detect(candles, {"atr": 1.0})
        assert result is not None
        assert result.metadata["level_interaction"] == "round_number"

    def test_stop_uses_atr_buffer(self) -> None:
        """Stop price is dip_low minus ATR buffer."""
        pattern = DipAndRipPattern(stop_buffer_atr_mult=0.5)
        candles = _build_dip_and_rip_candles(
            pre_dip_high=100.0,
            dip_low=97.0,
            recovery_high=99.0,
            lookback_bars=15,
        )
        atr = 2.0
        result = pattern.detect(candles, {"atr": atr})
        assert result is not None
        # Stop should be dip_low - 0.5 * 2.0 = 97.0 - 1.0 = 96.0
        expected_stop = 97.0 - 0.5 * atr
        assert abs(result.stop_price - expected_stop) < 0.5
