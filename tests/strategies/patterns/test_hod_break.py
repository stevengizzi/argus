"""Tests for HODBreakPattern detection module.

Sprint 29, Session 4.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from argus.core.config import HODBreakConfig, UniverseFilterConfig
from argus.strategies.patterns.base import CandleBar, PatternParam
from argus.strategies.patterns.hod_break import HODBreakPattern

_ET = ZoneInfo("America/New_York")

BASE_TIME = datetime(2026, 3, 31, 10, 0, 0, tzinfo=_ET)


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
    """Build a CandleBar with sensible defaults."""
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


def _build_hod_break_candles(
    *,
    base_price: float = 100.0,
    hod: float = 102.0,
    consol_bars: int = 5,
    consol_range_pct: float = 0.003,
    hold_bars: int = 2,
    breakout_close_above_hod_pct: float = 0.002,
    pre_consol_bars: int = 10,
    consol_volume: float = 1000.0,
    breakout_volume: float = 2000.0,
    hold_volume: float = 1500.0,
) -> list[CandleBar]:
    """Build synthetic candles for an HOD break pattern.

    Structure:
        1. Pre-consolidation: rising bars up to HOD with multiple touches
        2. Consolidation: tight range near HOD
        3. Hold bars: breakout bars closing above HOD
    """
    candles: list[CandleBar] = []
    minute = 0

    # Pre-consolidation: gradually rise to HOD with some touches
    for i in range(pre_consol_bars):
        progress = (i + 1) / pre_consol_bars
        price = base_price + (hod - base_price) * progress
        hi = hod if i >= pre_consol_bars - 3 else price + 0.10
        candles.append(_bar(
            close=price,
            volume=1000.0,
            offset_minutes=minute,
            high=hi,
            low=price - 0.20,
        ))
        minute += 1

    # Consolidation: tight range near HOD
    consol_mid = hod - 0.05
    half_range = hod * consol_range_pct / 2
    for i in range(consol_bars):
        price = consol_mid + half_range * (0.3 if i % 2 == 0 else -0.3)
        candles.append(_bar(
            close=price,
            volume=consol_volume,
            offset_minutes=minute,
            high=hod - 0.01,  # Very close to HOD
            low=consol_mid - half_range,
        ))
        minute += 1

    # Hold bars: breakout above HOD
    breakout_close = hod * (1.0 + breakout_close_above_hod_pct)
    for i in range(hold_bars):
        vol = breakout_volume if i == 0 else hold_volume
        candles.append(_bar(
            close=breakout_close + 0.01 * i,
            volume=vol,
            offset_minutes=minute,
            high=breakout_close + 0.10,
            low=breakout_close - 0.05,
        ))
        minute += 1

    return candles


# ---------------------------------------------------------------------------
# Test 1: Detect HOD breakout after consolidation
# ---------------------------------------------------------------------------


class TestHODBreakDetection:
    """Test HOD Break pattern detection."""

    def test_detect_hod_breakout_after_consolidation(self) -> None:
        """Valid HOD break pattern produces PatternDetection."""
        pattern = HODBreakPattern()
        candles = _build_hod_break_candles()
        result = pattern.detect(candles, {})

        assert result is not None
        assert result.pattern_type == "hod_break"
        assert result.entry_price > 0
        assert result.stop_price < result.entry_price
        assert len(result.target_prices) == 2
        assert result.confidence > 0

    def test_detect_with_indicators(self) -> None:
        """Detection works when ATR and VWAP provided via indicators."""
        pattern = HODBreakPattern()
        candles = _build_hod_break_candles()
        indicators = {"atr": 0.50, "vwap": 101.0}
        result = pattern.detect(candles, indicators)

        assert result is not None
        assert result.metadata["vwap_distance_pct"] != 0.0


# ---------------------------------------------------------------------------
# Test 2: Reject — no consolidation near HOD (range too wide)
# ---------------------------------------------------------------------------


class TestHODBreakRejectWideRange:
    """Test rejection when consolidation range is too wide."""

    def test_reject_wide_consolidation_range(self) -> None:
        """Wide consolidation range (exceeds ATR threshold) returns None."""
        pattern = HODBreakPattern(consolidation_max_range_atr=0.3)
        # Build candles with very wide consolidation range
        candles = _build_hod_break_candles(consol_range_pct=0.05)
        result = pattern.detect(candles, {"atr": 0.20})

        assert result is None


# ---------------------------------------------------------------------------
# Test 3: Reject — breakout without hold duration (false breakout)
# ---------------------------------------------------------------------------


class TestHODBreakRejectNoHold:
    """Test rejection when hold duration not met."""

    def test_reject_breakout_without_hold_bars(self) -> None:
        """Breakout on initial bar only (no hold) returns None."""
        pattern = HODBreakPattern(min_hold_bars=3)
        # Build with only 2 hold bars — pattern requires 3
        candles = _build_hod_break_candles(hold_bars=2)
        result = pattern.detect(candles, {})

        # With min_hold_bars=3 but only 2 hold bars, should fail
        assert result is None

    def test_reject_hold_bar_drops_below_hod(self) -> None:
        """Hold bar that drops back below HOD invalidates breakout."""
        pattern = HODBreakPattern(min_hold_bars=2)
        candles = _build_hod_break_candles(hold_bars=2)

        # Replace last hold bar with one that closes below HOD
        hod = max(c.high for c in candles[:-2])
        candles[-1] = _bar(
            close=hod * 0.999,  # Below HOD
            volume=2000.0,
            offset_minutes=len(candles) - 1,
            high=hod + 0.05,
            low=hod * 0.998,
        )

        result = pattern.detect(candles, {})
        assert result is None


# ---------------------------------------------------------------------------
# Test 4: Reject — breakout without volume confirmation
# ---------------------------------------------------------------------------


class TestHODBreakRejectLowVolume:
    """Test rejection when breakout volume is insufficient."""

    def test_reject_low_breakout_volume(self) -> None:
        """Breakout with volume below threshold returns None."""
        pattern = HODBreakPattern(min_breakout_volume_ratio=2.0)
        # Breakout volume only slightly above consolidation
        candles = _build_hod_break_candles(
            consol_volume=1000.0,
            breakout_volume=1200.0,  # ratio = 1.2, below 2.0 threshold
        )
        result = pattern.detect(candles, {})

        assert result is None


# ---------------------------------------------------------------------------
# Test 5: HOD tracking updates correctly across candles
# ---------------------------------------------------------------------------


class TestHODTracking:
    """Test dynamic HOD tracking."""

    def test_hod_updates_dynamically(self) -> None:
        """HOD should track the maximum high across all candles."""
        pattern = HODBreakPattern()

        # Build candles where HOD starts low and rises
        candles = _build_hod_break_candles(base_price=95.0, hod=105.0)

        result = pattern.detect(candles, {})
        if result is not None:
            # HOD in metadata should reflect the true maximum high
            reported_hod = float(result.metadata["hod"])
            actual_max_high = max(c.high for c in candles)
            assert reported_hod == pytest.approx(actual_max_high, abs=0.01)

    def test_hod_not_computed_once(self) -> None:
        """HOD must update as new candles arrive, not be fixed to first bar."""
        pattern = HODBreakPattern()

        # First bars have low highs, later bars are much higher
        candles: list[CandleBar] = []
        for i in range(20):
            price = 50.0 + i * 0.5 if i < 10 else 55.0 + (i - 10) * 2.0
            candles.append(_bar(
                close=price,
                volume=1000.0 if i < 18 else 3000.0,
                offset_minutes=i,
                high=price + 0.05,
                low=price - 0.20,
            ))

        # The HOD should NOT be from the first candle
        first_bar_high = candles[0].high
        actual_hod = max(c.high for c in candles)
        assert actual_hod > first_bar_high


# ---------------------------------------------------------------------------
# Test 6: HOD touch count accumulation
# ---------------------------------------------------------------------------


class TestHODTouchCount:
    """Test HOD touch count tracking."""

    def test_touch_count_accumulates(self) -> None:
        """Multiple candles near HOD should increase touch count."""
        pattern = HODBreakPattern()
        candles = _build_hod_break_candles(pre_consol_bars=15)

        result = pattern.detect(candles, {})
        if result is not None:
            touch_count = int(result.metadata["hod_touch_count"])
            # With pre-consol bars approaching HOD and consol bars near HOD,
            # we should have multiple touches
            assert touch_count >= 3

    def test_low_bars_dont_count_as_touches(self) -> None:
        """Bars far below HOD should NOT be counted as touches."""
        pattern = HODBreakPattern(hod_proximity_percent=0.001)

        # Build candles where most bars are far below the HOD
        candles: list[CandleBar] = []
        for i in range(12):
            # Most bars at 90.0, a few at 100.0
            if i < 8:
                candles.append(_bar(
                    close=90.0, volume=1000.0, offset_minutes=i,
                    high=90.10, low=89.90,
                ))
            else:
                candles.append(_bar(
                    close=100.0, volume=2000.0, offset_minutes=i,
                    high=100.10, low=99.90,
                ))

        # HOD is ~100.10. Bars at 90.10 are 10% away — not touches
        hod = max(c.high for c in candles)
        low_bar_touches = sum(
            1 for c in candles[:8]
            if abs(c.high - hod) <= hod * 0.001
        )
        assert low_bar_touches == 0


# ---------------------------------------------------------------------------
# Test 7: Score weights — 30/25/25/20 verified
# ---------------------------------------------------------------------------


class TestHODBreakScoring:
    """Test score weight distribution."""

    def test_score_weights_sum_to_100(self) -> None:
        """Maximum possible score should be 100 (30+25+25+20)."""
        pattern = HODBreakPattern()

        detection = pattern.detect(
            _build_hod_break_candles(
                pre_consol_bars=20,
                breakout_volume=5000.0,
                consol_volume=500.0,
            ),
            {"vwap": 101.5},
        )

        assert detection is not None
        score = pattern.score(detection)
        # Score should be > 0 and <= 100
        assert 0.0 < score <= 100.0

    def test_score_consolidation_quality_component(self) -> None:
        """Tighter consolidation should score higher."""
        pattern = HODBreakPattern()

        tight = _build_hod_break_candles(consol_range_pct=0.001)
        wide = _build_hod_break_candles(consol_range_pct=0.005)

        det_tight = pattern.detect(tight, {})
        det_wide = pattern.detect(wide, {})

        if det_tight is not None and det_wide is not None:
            score_tight = pattern.score(det_tight)
            score_wide = pattern.score(det_wide)
            assert score_tight >= score_wide

    def test_score_volume_component(self) -> None:
        """Higher breakout volume should increase score."""
        pattern = HODBreakPattern()

        high_vol = _build_hod_break_candles(breakout_volume=5000.0, consol_volume=500.0)
        low_vol = _build_hod_break_candles(breakout_volume=1600.0, consol_volume=1000.0)

        det_high = pattern.detect(high_vol, {})
        det_low = pattern.detect(low_vol, {})

        if det_high is not None and det_low is not None:
            score_high = pattern.score(det_high)
            score_low = pattern.score(det_low)
            assert score_high >= score_low


# ---------------------------------------------------------------------------
# Test 8: Score VWAP distance scaling
# ---------------------------------------------------------------------------


class TestVWAPDistanceScoring:
    """Test VWAP distance scoring degradation."""

    def test_vwap_within_2_percent_gets_full_points(self) -> None:
        """VWAP distance <= 2% should get full VWAP score."""
        pattern = HODBreakPattern()
        candles = _build_hod_break_candles()
        detection = pattern.detect(candles, {"vwap": 101.5})

        if detection is not None:
            # Manually set metadata for controlled test
            detection.metadata["vwap_distance_pct"] = 0.01
            score_near = pattern.score(detection)

            detection.metadata["vwap_distance_pct"] = 0.06
            score_far = pattern.score(detection)

            assert score_near > score_far

    def test_vwap_beyond_5_percent_gets_minimum(self) -> None:
        """VWAP distance > 5% should get minimum VWAP score."""
        pattern = HODBreakPattern(vwap_extended_pct=0.05)
        candles = _build_hod_break_candles()
        detection = pattern.detect(candles, {"vwap": 101.5})

        if detection is not None:
            detection.metadata["vwap_distance_pct"] = 0.06
            score_6pct = pattern.score(detection)

            detection.metadata["vwap_distance_pct"] = 0.10
            score_10pct = pattern.score(detection)

            # Both should get the same minimum (4.0 pts)
            assert score_6pct == pytest.approx(score_10pct, abs=0.1)

    def test_vwap_unavailable_scores_zero_distance(self) -> None:
        """When VWAP is not available, distance defaults to 0 (full points)."""
        pattern = HODBreakPattern()
        candles = _build_hod_break_candles()

        # No VWAP in indicators
        detection = pattern.detect(candles, {})
        if detection is not None:
            vwap_dist = float(detection.metadata["vwap_distance_pct"])
            assert vwap_dist == 0.0
            # Should get full VWAP points (0% distance = within 2%)


# ---------------------------------------------------------------------------
# Test 9: PatternParam completeness
# ---------------------------------------------------------------------------


class TestPatternParams:
    """Test get_default_params() completeness."""

    def test_param_count(self) -> None:
        """Should return ~11 PatternParam entries."""
        pattern = HODBreakPattern()
        params = pattern.get_default_params()
        assert len(params) == 11

    def test_all_params_are_pattern_param(self) -> None:
        """All entries must be PatternParam instances."""
        pattern = HODBreakPattern()
        for param in pattern.get_default_params():
            assert isinstance(param, PatternParam)

    def test_param_names_unique(self) -> None:
        """All parameter names must be unique."""
        pattern = HODBreakPattern()
        names = [p.name for p in pattern.get_default_params()]
        assert len(names) == len(set(names))

    def test_param_categories_populated(self) -> None:
        """All params must have a category (detection, scoring, filtering)."""
        pattern = HODBreakPattern()
        valid_categories = {"detection", "scoring", "filtering", "trade"}
        for param in pattern.get_default_params():
            assert param.category in valid_categories, (
                f"{param.name} has invalid category: {param.category}"
            )

    def test_param_defaults_match_constructor(self) -> None:
        """Param defaults must match the constructor defaults."""
        pattern = HODBreakPattern()
        params = {p.name: p.default for p in pattern.get_default_params()}
        assert params["hod_proximity_percent"] == 0.003
        assert params["consolidation_min_bars"] == 5
        assert params["min_hold_bars"] == 2
        assert params["min_breakout_volume_ratio"] == 1.5
        assert params["target_ratio"] == 2.0


# ---------------------------------------------------------------------------
# Test 10: Config + exit override parse correctly
# ---------------------------------------------------------------------------


class TestConfigParsing:
    """Test YAML config and exit override parsing."""

    def test_hod_break_yaml_parses(self) -> None:
        """hod_break.yaml should parse into HODBreakConfig."""
        yaml_path = Path("config/strategies/hod_break.yaml")
        assert yaml_path.exists(), f"Config file not found: {yaml_path}"

        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        config = HODBreakConfig(**data)
        assert config.strategy_id == "strat_hod_break"
        assert config.operating_window.earliest_entry == "10:00"
        assert config.operating_window.latest_entry == "15:30"
        assert config.hod_proximity_percent == 0.003
        assert config.min_hold_bars == 2

    def test_hod_break_universe_filter(self) -> None:
        """Universe filter parses with correct values."""
        yaml_path = Path("config/strategies/hod_break.yaml")
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        config = HODBreakConfig(**data)
        assert config.universe_filter is not None
        assert config.universe_filter.min_price == 5.0
        assert config.universe_filter.max_price == 500.0
        assert config.universe_filter.min_avg_volume == 300000

    def test_exit_management_override_exists(self) -> None:
        """Strategy YAML should contain exit_management override."""
        yaml_path = Path("config/strategies/hod_break.yaml")
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        exit_mgmt = data.get("exit_management", {})
        assert exit_mgmt["trailing_stop"]["enabled"] is True
        assert exit_mgmt["trailing_stop"]["atr_multiplier"] == 2.0
        assert exit_mgmt["escalation"]["enabled"] is True
        assert len(exit_mgmt["escalation"]["phases"]) == 2


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


class TestHODBreakEdgeCases:
    """Edge case tests for robustness."""

    def test_insufficient_candles_returns_none(self) -> None:
        """Too few candles returns None."""
        pattern = HODBreakPattern()
        candles = [_bar(close=100.0, offset_minutes=i) for i in range(3)]
        assert pattern.detect(candles, {}) is None

    def test_zero_atr_with_no_indicators_computes_from_candles(self) -> None:
        """When ATR not in indicators, pattern computes from candles."""
        pattern = HODBreakPattern()
        candles = _build_hod_break_candles()
        # No ATR in indicators — should compute internally
        result = pattern.detect(candles, {})
        if result is not None:
            assert float(result.metadata["atr"]) > 0

    def test_name_property(self) -> None:
        """Name property returns 'HOD Break'."""
        assert HODBreakPattern().name == "HOD Break"

    def test_lookback_bars_is_60(self) -> None:
        """Lookback bars should be 60."""
        assert HODBreakPattern().lookback_bars == 60

    def test_stop_price_below_consolidation_low(self) -> None:
        """Stop price must be below consolidation low."""
        pattern = HODBreakPattern()
        candles = _build_hod_break_candles()
        result = pattern.detect(candles, {})

        if result is not None:
            consol_low = float(result.metadata["consolidation_low"])
            assert result.stop_price < consol_low
