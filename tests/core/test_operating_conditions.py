"""Tests for RegimeOperatingConditions and RegimeVector.matches_conditions().

Sprint 27.6 Session 9: Operating Conditions Matching.
"""

from __future__ import annotations

from datetime import UTC, datetime

from argus.core.config import StrategyConfig
from argus.core.regime import (
    MarketRegime,
    RegimeOperatingConditions,
    RegimeVector,
)


def _make_vector(**overrides: object) -> RegimeVector:
    """Create a RegimeVector with sensible defaults, overriding as needed."""
    defaults: dict[str, object] = {
        "computed_at": datetime(2026, 3, 24, 14, 0, 0, tzinfo=UTC),
        "trend_score": 0.5,
        "trend_conviction": 0.7,
        "volatility_level": 0.15,
        "volatility_direction": 0.1,
        "universe_breadth_score": 0.6,
        "average_correlation": 0.35,
        "regime_confidence": 0.75,
        "correlation_regime": "normal",
        "sector_rotation_phase": "risk_on",
        "intraday_character": "trending",
        "primary_regime": MarketRegime.BULLISH_TRENDING,
    }
    defaults.update(overrides)
    return RegimeVector(**defaults)  # type: ignore[arg-type]


class TestRegimeOperatingConditionsConstruction:
    """Test RegimeOperatingConditions dataclass construction."""

    def test_default_construction_all_none(self) -> None:
        conditions = RegimeOperatingConditions()
        assert conditions.trend_score is None
        assert conditions.trend_conviction is None
        assert conditions.volatility_level is None
        assert conditions.universe_breadth_score is None
        assert conditions.average_correlation is None
        assert conditions.regime_confidence is None
        assert conditions.correlation_regime is None
        assert conditions.sector_rotation_phase is None
        assert conditions.intraday_character is None

    def test_construction_with_range_and_string_constraints(self) -> None:
        conditions = RegimeOperatingConditions(
            trend_score=(-0.5, 0.8),
            correlation_regime=["dispersed", "normal"],
        )
        assert conditions.trend_score == (-0.5, 0.8)
        assert conditions.correlation_regime == ["dispersed", "normal"]
        assert conditions.volatility_level is None


class TestMatchesConditionsRanges:
    """Test float range matching logic."""

    def test_all_dimensions_in_range_matches(self) -> None:
        vector = _make_vector()
        conditions = RegimeOperatingConditions(
            trend_score=(0.0, 1.0),
            trend_conviction=(0.5, 1.0),
            volatility_level=(0.10, 0.20),
            universe_breadth_score=(0.4, 0.8),
            average_correlation=(0.2, 0.5),
            regime_confidence=(0.5, 1.0),
        )
        assert vector.matches_conditions(conditions) is True

    def test_one_float_dimension_out_of_range_fails(self) -> None:
        vector = _make_vector(trend_score=0.5)
        conditions = RegimeOperatingConditions(
            trend_score=(0.6, 1.0),  # 0.5 is below 0.6
        )
        assert vector.matches_conditions(conditions) is False

    def test_boundary_inclusive_low(self) -> None:
        vector = _make_vector(trend_score=0.0)
        conditions = RegimeOperatingConditions(trend_score=(0.0, 1.0))
        assert vector.matches_conditions(conditions) is True

    def test_boundary_inclusive_high(self) -> None:
        vector = _make_vector(volatility_level=0.20)
        conditions = RegimeOperatingConditions(volatility_level=(0.10, 0.20))
        assert vector.matches_conditions(conditions) is True


class TestMatchesConditionsStrings:
    """Test string list matching logic."""

    def test_string_dimension_in_list_matches(self) -> None:
        vector = _make_vector(correlation_regime="dispersed")
        conditions = RegimeOperatingConditions(
            correlation_regime=["dispersed", "normal"],
        )
        assert vector.matches_conditions(conditions) is True

    def test_string_dimension_not_in_list_fails(self) -> None:
        vector = _make_vector(correlation_regime="concentrated")
        conditions = RegimeOperatingConditions(
            correlation_regime=["dispersed", "normal"],
        )
        assert vector.matches_conditions(conditions) is False

    def test_multiple_string_dimensions(self) -> None:
        vector = _make_vector(
            sector_rotation_phase="risk_on",
            intraday_character="trending",
        )
        conditions = RegimeOperatingConditions(
            sector_rotation_phase=["risk_on", "mixed"],
            intraday_character=["trending", "breakout"],
        )
        assert vector.matches_conditions(conditions) is True


class TestMatchesConditionsNoneHandling:
    """Test None field behavior in matching."""

    def test_none_constraint_always_matches(self) -> None:
        vector = _make_vector(trend_score=-0.9)
        conditions = RegimeOperatingConditions(
            trend_score=None,  # unconstrained
        )
        assert vector.matches_conditions(conditions) is True

    def test_none_vector_field_with_non_none_constraint_fails(self) -> None:
        vector = _make_vector(universe_breadth_score=None)
        conditions = RegimeOperatingConditions(
            universe_breadth_score=(0.3, 0.8),
        )
        assert vector.matches_conditions(conditions) is False

    def test_none_vector_string_field_with_non_none_constraint_fails(self) -> None:
        vector = _make_vector(intraday_character=None)
        conditions = RegimeOperatingConditions(
            intraday_character=["trending"],
        )
        assert vector.matches_conditions(conditions) is False

    def test_empty_conditions_vacuously_true(self) -> None:
        vector = _make_vector()
        conditions = RegimeOperatingConditions()
        assert vector.matches_conditions(conditions) is True


class TestMatchesConditionsAndLogic:
    """Test that all conditions must match (AND logic)."""

    def test_mixed_pass_and_fail_returns_false(self) -> None:
        vector = _make_vector(trend_score=0.5, volatility_level=0.30)
        conditions = RegimeOperatingConditions(
            trend_score=(0.0, 1.0),         # passes
            volatility_level=(0.10, 0.20),  # fails (0.30 > 0.20)
        )
        assert vector.matches_conditions(conditions) is False


class TestStrategyConfigOperatingConditions:
    """Test operating_conditions on StrategyConfig YAML parsing."""

    def test_yaml_with_operating_conditions_parses(self) -> None:
        cfg = StrategyConfig.model_validate({
            "strategy_id": "orb_breakout",
            "name": "ORB Breakout",
            "operating_conditions": {
                "trend_score": [0.0, 1.0],
                "correlation_regime": ["dispersed", "normal"],
                "intraday_character": ["trending", "breakout"],
            },
        })
        assert cfg.operating_conditions is not None
        assert cfg.operating_conditions.trend_score == (0.0, 1.0)
        assert cfg.operating_conditions.correlation_regime == ["dispersed", "normal"]
        assert cfg.operating_conditions.intraday_character == ["trending", "breakout"]
        assert cfg.operating_conditions.volatility_level is None

    def test_yaml_without_operating_conditions_defaults_none(self) -> None:
        cfg = StrategyConfig.model_validate({
            "strategy_id": "orb_breakout",
            "name": "ORB Breakout",
        })
        assert cfg.operating_conditions is None
