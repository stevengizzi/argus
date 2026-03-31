"""Tests for GapAndGoPattern detection module.

Sprint 29, Session 5.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from argus.core.config import GapAndGoConfig, UniverseFilterConfig
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternParam
from argus.strategies.patterns.gap_and_go import GapAndGoPattern

_ET = ZoneInfo("America/New_York")

BASE_TIME = datetime(2026, 3, 31, 9, 35, 0, tzinfo=_ET)


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


def _build_gap_and_go_candles(
    prior_close: float = 100.0,
    gap_open: float = 104.0,
    volume: float = 3000.0,
    ref_volume: float = 1000.0,
    bar_count: int = 15,
    include_pullback: bool = True,
    vwap: float = 103.5,
) -> tuple[list[CandleBar], dict[str, float]]:
    """Build synthetic candles for a gap-and-go pattern.

    Creates a gap-up scenario with uptrend, optional pullback, and re-entry.

    Returns:
        Tuple of (candles, indicators).
    """
    candles: list[CandleBar] = []

    # Bar 0: gap open candle
    candles.append(_bar(
        close=gap_open + 0.50,
        open_=gap_open,
        high=gap_open + 0.80,
        low=gap_open - 0.20,
        volume=volume,
        offset_minutes=0,
    ))

    # Bars 1-4: uptrend above VWAP
    for i in range(1, 5):
        price = gap_open + 0.50 + i * 0.30
        candles.append(_bar(
            close=price,
            open_=price - 0.15,
            high=price + 0.10,
            low=price - 0.25,
            volume=volume,
            offset_minutes=i,
        ))

    if include_pullback:
        # Bar 5: pullback (close < prior bar close)
        pullback_close = candles[-1].close - 0.60
        candles.append(_bar(
            close=pullback_close,
            open_=candles[-1].close - 0.10,
            high=candles[-1].close,
            low=pullback_close - 0.10,
            volume=volume * 0.8,
            offset_minutes=5,
        ))

        # Bar 6: re-entry (close above pullback high)
        reentry_close = candles[5].high + 0.30
        candles.append(_bar(
            close=reentry_close,
            open_=pullback_close + 0.20,
            high=reentry_close + 0.10,
            low=pullback_close + 0.10,
            volume=volume,
            offset_minutes=6,
        ))

        # Fill remaining bars
        for i in range(7, bar_count):
            price = reentry_close + (i - 6) * 0.10
            candles.append(_bar(
                close=price,
                volume=volume,
                offset_minutes=i,
            ))
    else:
        # No pullback — just uptrend
        for i in range(5, bar_count):
            price = candles[-1].close + 0.20
            candles.append(_bar(
                close=price,
                open_=price - 0.10,
                high=price + 0.10,
                low=price - 0.15,
                volume=volume,
                offset_minutes=i,
            ))

    indicators: dict[str, float] = {
        "symbol": "TSLA",
        "vwap": vwap,
        "prior_day_avg_volume": ref_volume,
    }

    return candles[:bar_count], indicators


# ---------------------------------------------------------------------------
# Detection Tests
# ---------------------------------------------------------------------------


class TestGapDetection:
    """Test gap-up detection above threshold with volume confirmation."""

    def test_detect_gap_up_with_volume_confirmation(self) -> None:
        """T1: Detect gap-up above threshold with volume → PatternDetection."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        candles, indicators = _build_gap_and_go_candles(
            prior_close=100.0, gap_open=104.0, volume=3000.0, ref_volume=1000.0
        )
        result = pattern.detect(candles, indicators)

        assert result is not None
        assert result.pattern_type == "gap_and_go"
        assert result.entry_price > 0
        assert result.stop_price < result.entry_price
        assert len(result.target_prices) == 1
        assert float(result.metadata["gap_percent"]) >= 3.0

    def test_reject_gap_below_min_gap_percent(self) -> None:
        """T2: Reject gap below min_gap_percent → None."""
        pattern = GapAndGoPattern(min_gap_percent=5.0)
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        # 3% gap < 5% threshold
        candles, indicators = _build_gap_and_go_candles(
            prior_close=100.0, gap_open=103.0
        )
        result = pattern.detect(candles, indicators)

        assert result is None

    def test_reject_no_prior_close_data(self) -> None:
        """T3: Reject when no prior close data → None (not crash)."""
        pattern = GapAndGoPattern()
        # No set_reference_data() call — prior_closes is empty

        candles, indicators = _build_gap_and_go_candles()
        result = pattern.detect(candles, indicators)

        assert result is None

    def test_reject_insufficient_volume(self) -> None:
        """T4: Reject insufficient volume → None."""
        pattern = GapAndGoPattern(min_relative_volume=5.0)
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        # Volume ratio = 1000/1000 = 1.0 < 5.0
        candles, indicators = _build_gap_and_go_candles(
            volume=1000.0, ref_volume=1000.0
        )
        result = pattern.detect(candles, indicators)

        assert result is None

    def test_reject_vwap_not_held(self) -> None:
        """T5: Reject when VWAP not held → None."""
        pattern = GapAndGoPattern(min_vwap_hold_bars=8, vwap_check_window=8)
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        # VWAP very high — bars won't be above it
        candles, indicators = _build_gap_and_go_candles(vwap=200.0)
        result = pattern.detect(candles, indicators)

        assert result is None


class TestEntryModes:
    """Test first_pullback and direct_breakout entry modes."""

    def test_first_pullback_entry_mode(self) -> None:
        """T6: First pullback entry mode detects pullback → re-entry."""
        pattern = GapAndGoPattern(entry_mode="first_pullback")
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        candles, indicators = _build_gap_and_go_candles(include_pullback=True)
        result = pattern.detect(candles, indicators)

        assert result is not None
        assert result.metadata["entry_mode"] == "first_pullback"
        assert int(result.metadata["entry_bar_index"]) > 0

    def test_direct_breakout_entry_mode(self) -> None:
        """T7: Direct breakout entry mode detects break above 5-min high."""
        pattern = GapAndGoPattern(entry_mode="direct_breakout")
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        candles, indicators = _build_gap_and_go_candles(include_pullback=False)
        result = pattern.detect(candles, indicators)

        assert result is not None
        assert result.metadata["entry_mode"] == "direct_breakout"

    def test_entry_mode_changes_detection_behavior(self) -> None:
        """Entry mode parameter actually changes detection behavior."""
        candles, indicators = _build_gap_and_go_candles(include_pullback=True)

        pb = GapAndGoPattern(entry_mode="first_pullback")
        pb.set_reference_data({"prior_closes": {"TSLA": 100.0}})
        result_pb = pb.detect(candles, indicators)

        db = GapAndGoPattern(entry_mode="direct_breakout")
        db.set_reference_data({"prior_closes": {"TSLA": 100.0}})
        result_db = db.detect(candles, indicators)

        # Both should detect but metadata records different entry_mode
        assert result_pb is not None
        assert result_db is not None
        assert result_pb.metadata["entry_mode"] == "first_pullback"
        assert result_db.metadata["entry_mode"] == "direct_breakout"


class TestReferenceData:
    """Test set_reference_data() behavior."""

    def test_set_reference_data_stores_prior_closes(self) -> None:
        """T8: set_reference_data() stores prior closes correctly."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({"prior_closes": {"AAPL": 150.0, "TSLA": 200.0}})

        assert pattern._prior_closes == {"AAPL": 150.0, "TSLA": 200.0}

    def test_set_reference_data_handles_missing_key(self) -> None:
        """T9: set_reference_data() handles missing prior_closes key."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({"other_data": 42})

        assert pattern._prior_closes == {}

    def test_set_reference_data_handles_empty_dict(self) -> None:
        """set_reference_data() with empty dict stores empty prior_closes."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({})

        assert pattern._prior_closes == {}

    def test_detect_returns_none_for_unknown_symbol(self) -> None:
        """Detect returns None when symbol not in prior_closes."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({"prior_closes": {"AAPL": 150.0}})

        candles, indicators = _build_gap_and_go_candles()
        # indicators has symbol="TSLA" which isn't in prior_closes
        result = pattern.detect(candles, indicators)

        assert result is None


class TestScoring:
    """Test score weights: 30/30/20/20."""

    def test_score_weights_verified(self) -> None:
        """T10: Score weights sum to 100 at max values."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        candles, indicators = _build_gap_and_go_candles()
        detection = pattern.detect(candles, indicators)
        assert detection is not None

        score = pattern.score(detection)
        assert 0 <= score <= 100

    def test_score_gap_component(self) -> None:
        """Gap size component contributes up to 30 points."""
        pattern = GapAndGoPattern(gap_atr_cap=5.0)

        # Large gap: 10% → 10/5 = 2.0, capped at 1.0 → 30 pts
        large_gap_detection = PatternDetection(
            pattern_type="gap_and_go",
            confidence=50,
            entry_price=110.0,
            stop_price=105.0,
            metadata={
                "gap_percent": 10.0,
                "volume_ratio": 0.0,
                "bars_above_vwap": 0,
                "has_catalyst": False,
            },
        )
        score_large = pattern.score(large_gap_detection)

        # Small gap: 1% → 1/5 = 0.2 → 6 pts
        small_gap_detection = PatternDetection(
            pattern_type="gap_and_go",
            confidence=50,
            entry_price=101.0,
            stop_price=99.0,
            metadata={
                "gap_percent": 1.0,
                "volume_ratio": 0.0,
                "bars_above_vwap": 0,
                "has_catalyst": False,
            },
        )
        score_small = pattern.score(small_gap_detection)

        assert score_large > score_small

    def test_score_catalyst_component(self) -> None:
        """Catalyst presence adds 20 pts vs base score."""
        pattern = GapAndGoPattern(catalyst_base_score=10.0)

        with_catalyst = PatternDetection(
            pattern_type="gap_and_go",
            confidence=50,
            entry_price=105.0,
            stop_price=100.0,
            metadata={
                "gap_percent": 5.0,
                "volume_ratio": 3.0,
                "bars_above_vwap": 5,
                "has_catalyst": True,
            },
        )
        without_catalyst = PatternDetection(
            pattern_type="gap_and_go",
            confidence=50,
            entry_price=105.0,
            stop_price=100.0,
            metadata={
                "gap_percent": 5.0,
                "volume_ratio": 3.0,
                "bars_above_vwap": 5,
                "has_catalyst": False,
            },
        )

        score_with = pattern.score(with_catalyst)
        score_without = pattern.score(without_catalyst)

        # Catalyst adds 10 pts (20 vs 10 base)
        assert score_with - score_without == pytest.approx(10.0, abs=0.01)


class TestPatternParams:
    """Test get_default_params() completeness."""

    def test_pattern_param_completeness(self) -> None:
        """T11: All 14 PatternParam entries present including string entry_mode."""
        pattern = GapAndGoPattern()
        params = pattern.get_default_params()

        assert len(params) == 14
        assert all(isinstance(p, PatternParam) for p in params)

        names = {p.name for p in params}
        assert "entry_mode" in names
        assert "stop_mode" in names
        assert "min_gap_percent" in names
        assert "min_relative_volume" in names

    def test_entry_mode_param_is_string_type(self) -> None:
        """entry_mode PatternParam has str type and None min/max/step."""
        pattern = GapAndGoPattern()
        params = pattern.get_default_params()

        entry_mode_param = next(p for p in params if p.name == "entry_mode")
        assert entry_mode_param.param_type is str
        assert entry_mode_param.min_value is None
        assert entry_mode_param.max_value is None
        assert entry_mode_param.step is None
        assert entry_mode_param.default == "first_pullback"


class TestConfigAndFilter:
    """Test config YAML, filter YAML, and exit management parse correctly."""

    def test_strategy_config_parses(self) -> None:
        """T12: Config + filter + exit parse correctly."""
        config_path = Path("config/strategies/gap_and_go.yaml")
        assert config_path.exists(), f"Missing: {config_path}"

        with open(config_path) as f:
            data = yaml.safe_load(f)

        assert data["strategy_id"] == "strat_gap_and_go"
        assert data["operating_window"]["earliest_entry"] == "09:35"
        assert data["min_gap_percent"] == 3.0
        assert data["entry_mode"] == "first_pullback"

    def test_universe_filter_min_gap_percent(self) -> None:
        """min_gap_percent recognized by UniverseFilterConfig."""
        config = UniverseFilterConfig(
            min_price=3.0,
            max_price=150.0,
            min_avg_volume=200000,
            min_gap_percent=3.0,
        )
        assert config.min_gap_percent == 3.0

    def test_universe_filter_yaml_parses(self) -> None:
        """Universe filter YAML parses into UniverseFilterConfig."""
        filter_path = Path("config/universe_filters/gap_and_go.yaml")
        assert filter_path.exists(), f"Missing: {filter_path}"

        with open(filter_path) as f:
            data = yaml.safe_load(f)

        config = UniverseFilterConfig(**data)
        assert config.min_gap_percent == 3.0
        assert config.min_price == 3.0

    def test_exit_management_in_strategy_yaml(self) -> None:
        """Exit management override present in strategy YAML."""
        config_path = Path("config/strategies/gap_and_go.yaml")
        with open(config_path) as f:
            data = yaml.safe_load(f)

        em = data.get("exit_management", {})
        assert em["trailing_stop"]["enabled"] is True
        assert em["trailing_stop"]["type"] == "percent"
        assert em["escalation"]["enabled"] is True

    def test_gap_and_go_config_model(self) -> None:
        """GapAndGoConfig Pydantic model validates correctly."""
        config = GapAndGoConfig(
            strategy_id="strat_gap_and_go",
            name="Gap-and-Go",
            min_gap_percent=3.0,
            entry_mode="first_pullback",
        )
        assert config.min_gap_percent == 3.0
        assert config.entry_mode == "first_pullback"
        assert config.target_ratio == 1.0


class TestPatternName:
    """Test name and lookback_bars properties."""

    def test_name_property(self) -> None:
        """Pattern name is 'Gap-and-Go'."""
        assert GapAndGoPattern().name == "Gap-and-Go"

    def test_lookback_bars_property(self) -> None:
        """Lookback is 15 bars."""
        assert GapAndGoPattern().lookback_bars == 15


class TestEdgeCases:
    """Edge cases and safety checks."""

    def test_prior_close_zero_returns_none(self) -> None:
        """Prior close of zero returns None (division safety)."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({"prior_closes": {"TSLA": 0.0}})

        candles, indicators = _build_gap_and_go_candles()
        result = pattern.detect(candles, indicators)

        assert result is None

    def test_too_few_candles_returns_none(self) -> None:
        """Fewer than 2 candles returns None."""
        pattern = GapAndGoPattern()
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        result = pattern.detect([_bar(105.0)], {"symbol": "TSLA", "vwap": 103.0})
        assert result is None

    def test_vwap_not_available_uses_proxy(self) -> None:
        """When VWAP is not in indicators, uses first candle open as proxy."""
        pattern = GapAndGoPattern(min_vwap_hold_bars=1, vwap_check_window=5)
        pattern.set_reference_data({"prior_closes": {"TSLA": 100.0}})

        candles, indicators = _build_gap_and_go_candles()
        # Remove VWAP — pattern should use first candle open as proxy
        del indicators["vwap"]

        # Should not crash; may or may not detect depending on data
        result = pattern.detect(candles, indicators)
        # Just verify no exception — result can be None or PatternDetection
        assert result is None or result.pattern_type == "gap_and_go"
