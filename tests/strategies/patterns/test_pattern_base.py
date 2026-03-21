"""Tests for the PatternModule ABC, CandleBar, and PatternDetection dataclasses."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule


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

    def get_default_params(self) -> dict[str, object]:
        return {"lookback": 20, "threshold": 0.5}


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
        assert "lookback" in params
        assert "threshold" in params

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
