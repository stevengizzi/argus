"""Tests for QualityEngineConfig and sub-config validators.

Sprint 24, Session 5a.
Sprint 32.9, Session 3: weight recalibration + grade differentiation tests.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.core.events import Side, SignalEvent
from argus.core.regime import MarketRegime
from argus.intelligence.config import (
    QualityEngineConfig,
    QualityRiskTiersConfig,
    QualityThresholdsConfig,
    QualityWeightsConfig,
)
from argus.intelligence.quality_engine import SetupQualityEngine

_CONFIG_DIR = Path(__file__).parents[2] / "config"


class TestQualityWeightsConfig:
    """Tests for QualityWeightsConfig weight-sum validation."""

    def test_weight_sum_valid(self) -> None:
        """Default weights sum to 1.0 and pass validation."""
        config = QualityWeightsConfig()
        total = (
            config.pattern_strength
            + config.catalyst_quality
            + config.volume_profile
            + config.historical_match
            + config.regime_alignment
        )
        assert abs(total - 1.0) < 0.001

    def test_weight_sum_invalid(self) -> None:
        """Weights summing to 0.9 raise ValidationError."""
        with pytest.raises(ValidationError, match="must sum to 1.0"):
            QualityWeightsConfig(
                pattern_strength=0.30,
                catalyst_quality=0.25,
                volume_profile=0.20,
                historical_match=0.15,
                regime_alignment=0.00,
            )

    def test_get_returns_attribute(self) -> None:
        """get() method returns the named weight value."""
        config = QualityWeightsConfig()
        assert config.get("pattern_strength") == 0.30

    def test_get_returns_default_for_unknown_key(self) -> None:
        """get() returns the default for unknown keys."""
        config = QualityWeightsConfig()
        assert config.get("nonexistent", 0.5) == 0.5


class TestQualityThresholdsConfig:
    """Tests for QualityThresholdsConfig descending validation."""

    def test_thresholds_descending(self) -> None:
        """Default thresholds are valid and strictly descending."""
        config = QualityThresholdsConfig()
        values = [
            config.a_plus, config.a, config.a_minus,
            config.b_plus, config.b, config.b_minus, config.c_plus,
        ]
        for i in range(len(values) - 1):
            assert values[i] > values[i + 1]

    def test_thresholds_not_descending(self) -> None:
        """a_plus < a raises ValidationError."""
        with pytest.raises(ValidationError, match="strictly descending"):
            QualityThresholdsConfig(a_plus=70, a=80)

    def test_thresholds_out_of_range(self) -> None:
        """Threshold value outside [0, 100] raises ValidationError."""
        with pytest.raises(ValidationError, match="not in"):
            QualityThresholdsConfig(a_plus=110)


class TestQualityRiskTiersConfig:
    """Tests for QualityRiskTiersConfig pair validation."""

    def test_risk_tiers_valid(self) -> None:
        """Default risk tiers pass validation."""
        config = QualityRiskTiersConfig()
        assert config.a_plus == [0.02, 0.03]

    def test_risk_tiers_min_exceeds_max(self) -> None:
        """[0.03, 0.02] raises ValidationError because min > max."""
        with pytest.raises(ValidationError, match="min.*exceeds max"):
            QualityRiskTiersConfig(a_plus=[0.03, 0.02])

    def test_risk_tiers_out_of_range(self) -> None:
        """Values outside [0, 1] raise ValidationError."""
        with pytest.raises(ValidationError, match="must be in"):
            QualityRiskTiersConfig(b=[0.005, 1.5])


class TestQualityEngineConfig:
    """Tests for the top-level QualityEngineConfig."""

    def test_default_config_valid(self) -> None:
        """Default QualityEngineConfig passes all validations."""
        config = QualityEngineConfig()
        assert config.enabled is True
        assert config.min_grade_to_trade == "C+"

    def test_invalid_min_grade_to_trade(self) -> None:
        """Unknown grade string raises ValidationError."""
        with pytest.raises(ValidationError, match="min_grade_to_trade"):
            QualityEngineConfig(min_grade_to_trade="D")


# ---------------------------------------------------------------------------
# Sprint 32.9 — weight recalibration tests
# ---------------------------------------------------------------------------


class TestQualityWeightsRecalibration:
    """Tests for Sprint 32.9 quality weight recalibration.

    Verifies that the updated quality_engine.yaml has historical_match=0.0
    and that the weights still sum to 1.0 (Pydantic validator passes).
    """

    def test_quality_weights_sum_to_one(self) -> None:
        """Weights from quality_engine.yaml load into QualityWeightsConfig and sum to 1.0."""
        raw = yaml.safe_load((_CONFIG_DIR / "quality_engine.yaml").read_text())
        weights_data = raw["weights"]
        config = QualityWeightsConfig(**weights_data)
        total = (
            config.pattern_strength
            + config.catalyst_quality
            + config.volume_profile
            + config.historical_match
            + config.regime_alignment
        )
        assert abs(total - 1.0) < 0.001

    def test_historical_match_weight_is_zero(self) -> None:
        """historical_match weight is 0.0 after Sprint 32.9 recalibration."""
        raw = yaml.safe_load((_CONFIG_DIR / "quality_engine.yaml").read_text())
        weights_data = raw["weights"]
        assert weights_data["historical_match"] == 0.0

    def test_quality_grades_differentiate(self) -> None:
        """Signals with different pattern_strength and rvol produce distinct grades spanning A through C.

        With new weights (pattern_strength=0.375, volume_profile=0.275, historical_match=0.0)
        and recalibrated thresholds, signals should produce a range of grades —
        not the uniform B clustering observed before Sprint 32.9.
        """
        raw = yaml.safe_load((_CONFIG_DIR / "quality_engine.yaml").read_text())
        config = QualityEngineConfig(**raw)
        engine = SetupQualityEngine(config)

        def score(pattern_strength: float, rvol: float | None) -> str:
            signal = SignalEvent(
                strategy_id="test",
                symbol="AAPL",
                side=Side.LONG,
                entry_price=100.0,
                stop_price=99.0,
                target_prices=(102.0,),
                share_count=0,
                pattern_strength=pattern_strength,
            )
            result = engine.score_setup(
                signal=signal,
                catalysts=[],
                rvol=rvol,
                regime=MarketRegime.BULLISH_TRENDING,
                allowed_regimes=[],
            )
            return result.grade

        grade_high = score(80.0, 3.0)   # high pattern + high volume → should be A+ or A
        grade_mid = score(50.0, None)   # medium pattern + no rvol → should be B range
        grade_low = score(10.0, 0.3)   # low pattern + low volume → should be C+ or below

        assert grade_high in ("A+", "A", "A-"), f"High signal should be A-tier, got {grade_high}"
        assert grade_mid in ("B+", "B", "B-"), f"Mid signal should be B-tier, got {grade_mid}"
        # grade_low may be below minimum (below C+), confirmed by score < 40
        signal_low = SignalEvent(
            strategy_id="test",
            symbol="AAPL",
            side=Side.LONG,
            entry_price=100.0,
            stop_price=99.0,
            target_prices=(102.0,),
            share_count=0,
            pattern_strength=10.0,
        )
        result_low = engine.score_setup(
            signal=signal_low,
            catalysts=[],
            rvol=0.3,
            regime=MarketRegime.BULLISH_TRENDING,
            allowed_regimes=[],
        )
        assert result_low.score < config.thresholds.c_plus, (
            f"Low signal score {result_low.score} should be below C+ threshold "
            f"{config.thresholds.c_plus}"
        )
        assert grade_high != grade_mid, "High and mid signals should have different grades"
