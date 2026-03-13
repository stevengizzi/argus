"""Tests for QualityEngineConfig and sub-config validators.

Sprint 24, Session 5a.
"""

import pytest
from pydantic import ValidationError

from argus.intelligence.config import (
    QualityEngineConfig,
    QualityRiskTiersConfig,
    QualityThresholdsConfig,
    QualityWeightsConfig,
)


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
