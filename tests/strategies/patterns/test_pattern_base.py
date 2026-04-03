"""Tests for the PatternModule ABC, CandleBar, PatternDetection, and PatternParam."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


# ---------------------------------------------------------------------------
# Helper: concrete PatternModule for testing
# ---------------------------------------------------------------------------


class MockPattern(PatternModule):
    """Minimal concrete PatternModule for testing the ABC interface."""

    @property
    def name(self) -> str:
        return "mock_pattern"

    @property
    def lookback_bars(self) -> int:
        return 20

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        if len(candles) < 2:
            return None
        return PatternDetection(
            pattern_type="mock_pattern",
            confidence=75.0,
            entry_price=candles[-1].close,
            stop_price=candles[-1].low,
            metadata={"candle_count": len(candles)},
        )

    def score(self, detection: PatternDetection) -> float:
        return max(0.0, min(100.0, detection.confidence))

    def get_default_params(self) -> list[PatternParam]:
        return [
            PatternParam(
                name="lookback", param_type=int, default=20,
                min_value=5, max_value=50, step=5,
                description="Lookback window", category="detection",
            ),
            PatternParam(
                name="threshold", param_type=float, default=0.5,
                min_value=0.1, max_value=1.0, step=0.1,
                description="Detection threshold", category="detection",
            ),
        ]


# ---------------------------------------------------------------------------
# min_detection_bars tests (Sprint 31A S2)
# ---------------------------------------------------------------------------


class TestMinDetectionBars:
    def test_min_detection_bars_defaults_to_lookback_bars(self) -> None:
        """PatternModule.min_detection_bars defaults to lookback_bars when not overridden."""
        pattern = MockPattern()
        assert pattern.min_detection_bars == pattern.lookback_bars

    def test_pmh_lookback_bars_is_400(self) -> None:
        """PMH lookback_bars must hold full PM session (4 AM to 10:40 AM ET = ~400 bars)."""
        from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern

        pmh = PreMarketHighBreakPattern()
        assert pmh.lookback_bars == 400

    def test_pmh_min_detection_bars_is_10(self) -> None:
        """PMH can begin detection with 10 bars — enough for min PM candles + a few market bars."""
        from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern

        pmh = PreMarketHighBreakPattern()
        assert pmh.min_detection_bars == 10

    def test_pmh_min_detection_bars_less_than_lookback_bars(self) -> None:
        """PMH min_detection_bars must be strictly less than lookback_bars."""
        from argus.strategies.patterns.premarket_high_break import PreMarketHighBreakPattern

        pmh = PreMarketHighBreakPattern()
        assert pmh.min_detection_bars < pmh.lookback_bars

    def test_bull_flag_min_detection_bars_equals_lookback_bars(self) -> None:
        """BullFlagPattern does not override min_detection_bars — backward compat preserved."""
        from argus.strategies.patterns.bull_flag import BullFlagPattern

        bf = BullFlagPattern()
        assert bf.min_detection_bars == bf.lookback_bars


# ---------------------------------------------------------------------------
# CandleBar tests
# ---------------------------------------------------------------------------


class TestCandleBar:
    def test_candle_bar_creation(self) -> None:
        """Valid construction with all fields."""
        ts = datetime(2026, 3, 21, 10, 30, tzinfo=timezone.utc)
        bar = CandleBar(
            timestamp=ts,
            open=150.0,
            high=152.0,
            low=149.5,
            close=151.0,
            volume=10000.0,
        )
        assert bar.timestamp == ts
        assert bar.open == 150.0
        assert bar.high == 152.0
        assert bar.low == 149.5
        assert bar.close == 151.0
        assert bar.volume == 10000.0

    def test_candle_bar_is_frozen(self) -> None:
        """FrozenInstanceError on attribute assignment."""
        bar = CandleBar(
            timestamp=datetime(2026, 3, 21, 10, 30, tzinfo=timezone.utc),
            open=150.0,
            high=152.0,
            low=149.5,
            close=151.0,
            volume=10000.0,
        )
        with pytest.raises(FrozenInstanceError):
            bar.close = 999.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PatternDetection tests
# ---------------------------------------------------------------------------


class TestPatternDetection:
    def test_pattern_detection_creation(self) -> None:
        """Valid construction with required + optional fields."""
        det = PatternDetection(
            pattern_type="bull_flag",
            confidence=82.5,
            entry_price=155.0,
            stop_price=152.0,
            target_prices=(158.0, 161.0),
            metadata={"pole_bars": 5},
        )
        assert det.pattern_type == "bull_flag"
        assert det.confidence == 82.5
        assert det.entry_price == 155.0
        assert det.stop_price == 152.0
        assert det.target_prices == (158.0, 161.0)
        assert det.metadata == {"pole_bars": 5}

    def test_pattern_detection_default_targets(self) -> None:
        """Empty tuple when target_prices not specified."""
        det = PatternDetection(
            pattern_type="flat_top",
            confidence=60.0,
            entry_price=100.0,
            stop_price=98.0,
        )
        assert det.target_prices == ()

    def test_pattern_detection_with_targets(self) -> None:
        """target_prices populated correctly."""
        targets = (105.0, 110.0, 115.0)
        det = PatternDetection(
            pattern_type="bull_flag",
            confidence=70.0,
            entry_price=100.0,
            stop_price=97.0,
            target_prices=targets,
        )
        assert det.target_prices == targets
        assert len(det.target_prices) == 3

    def test_pattern_detection_metadata_mutable(self) -> None:
        """metadata dict can be modified after creation."""
        det = PatternDetection(
            pattern_type="test",
            confidence=50.0,
            entry_price=100.0,
            stop_price=99.0,
        )
        assert det.metadata == {}
        det.metadata["extra_key"] = "extra_value"
        assert det.metadata["extra_key"] == "extra_value"


# ---------------------------------------------------------------------------
# PatternModule ABC tests
# ---------------------------------------------------------------------------


class TestPatternModule:
    def test_pattern_module_cannot_be_instantiated(self) -> None:
        """TypeError on direct PatternModule()."""
        with pytest.raises(TypeError):
            PatternModule()  # type: ignore[abstract]

    def test_concrete_pattern_implements_interface(self) -> None:
        """Mock concrete PatternModule instantiates and methods callable."""
        pattern = MockPattern()
        assert pattern.name == "mock_pattern"
        assert pattern.lookback_bars == 20

        ts = datetime(2026, 3, 21, 10, 30, tzinfo=timezone.utc)
        candles = [
            CandleBar(timestamp=ts, open=100.0, high=101.0, low=99.0, close=100.5, volume=5000.0),
            CandleBar(timestamp=ts, open=100.5, high=102.0, low=100.0, close=101.5, volume=6000.0),
        ]
        indicators: dict[str, float] = {"vwap": 100.8, "atr": 1.5}

        detection = pattern.detect(candles, indicators)
        assert detection is not None
        assert detection.pattern_type == "mock_pattern"
        assert detection.confidence == 75.0
        assert detection.entry_price == 101.5
        assert detection.stop_price == 100.0

        score = pattern.score(detection)
        assert score == 75.0

        params = pattern.get_default_params()
        assert isinstance(params, list)
        assert len(params) == 2
        param_names = [p.name for p in params]
        assert "lookback" in param_names
        assert "threshold" in param_names

    def test_score_bounds(self) -> None:
        """Mock pattern's score returns value clamped to 0–100."""
        pattern = MockPattern()

        # High confidence — should clamp at 100
        high_det = PatternDetection(
            pattern_type="test", confidence=150.0, entry_price=100.0, stop_price=99.0,
        )
        assert pattern.score(high_det) == 100.0

        # Negative confidence — should clamp at 0
        low_det = PatternDetection(
            pattern_type="test", confidence=-20.0, entry_price=100.0, stop_price=99.0,
        )
        assert pattern.score(low_det) == 0.0

        # Normal confidence — pass through
        normal_det = PatternDetection(
            pattern_type="test", confidence=65.0, entry_price=100.0, stop_price=99.0,
        )
        assert pattern.score(normal_det) == 65.0

    def test_lookback_bars_positive(self) -> None:
        """lookback_bars returns a positive integer."""
        pattern = MockPattern()
        assert isinstance(pattern.lookback_bars, int)
        assert pattern.lookback_bars > 0


# ---------------------------------------------------------------------------
# PatternParam tests
# ---------------------------------------------------------------------------


class TestPatternParam:
    def test_construction_with_all_fields(self) -> None:
        """PatternParam stores all 8 fields correctly."""
        param = PatternParam(
            name="pole_min_bars",
            param_type=int,
            default=5,
            min_value=2,
            max_value=20,
            step=1,
            description="Minimum bars for pole",
            category="detection",
        )
        assert param.name == "pole_min_bars"
        assert param.param_type is int
        assert param.default == 5
        assert param.min_value == 2
        assert param.max_value == 20
        assert param.step == 1
        assert param.description == "Minimum bars for pole"
        assert param.category == "detection"

    def test_frozen_immutability(self) -> None:
        """PatternParam is frozen — attribute assignment raises."""
        param = PatternParam(
            name="threshold",
            param_type=float,
            default=0.5,
        )
        with pytest.raises(FrozenInstanceError):
            param.name = "other"  # type: ignore[misc]
        with pytest.raises(FrozenInstanceError):
            param.default = 0.9  # type: ignore[misc]

    def test_int_param_with_range(self) -> None:
        """Int parameter with min/max/step stores numeric metadata."""
        param = PatternParam(
            name="lookback",
            param_type=int,
            default=20,
            min_value=5,
            max_value=50,
            step=5,
            category="detection",
        )
        assert param.param_type is int
        assert param.min_value == 5
        assert param.max_value == 50
        assert param.step == 5
        assert isinstance(param.default, int)

    def test_float_param_with_range(self) -> None:
        """Float parameter with min/max/step stores numeric metadata."""
        param = PatternParam(
            name="retrace_pct",
            param_type=float,
            default=0.50,
            min_value=0.10,
            max_value=0.80,
            step=0.05,
            description="Max retracement of pole",
            category="filtering",
        )
        assert param.param_type is float
        assert param.min_value == 0.10
        assert param.max_value == 0.80
        assert param.step == 0.05
        assert isinstance(param.default, float)

    def test_bool_param_no_range(self) -> None:
        """Bool parameter has None for min/max/step."""
        param = PatternParam(
            name="require_volume_spike",
            param_type=bool,
            default=True,
            description="Require volume spike on breakout",
            category="filtering",
        )
        assert param.param_type is bool
        assert param.default is True
        assert param.min_value is None
        assert param.max_value is None
        assert param.step is None

    def test_set_reference_data_default_noop(self) -> None:
        """Default set_reference_data() does not raise."""
        pattern = MockPattern()
        # Should not raise with empty dict
        pattern.set_reference_data({})
        # Should not raise with populated dict
        pattern.set_reference_data({"prior_closes": {"AAPL": 150.0}})

    def test_default_optional_fields(self) -> None:
        """Optional fields default to None/empty string."""
        param = PatternParam(
            name="simple",
            param_type=int,
            default=10,
        )
        assert param.min_value is None
        assert param.max_value is None
        assert param.step is None
        assert param.description == ""
        assert param.category == ""
