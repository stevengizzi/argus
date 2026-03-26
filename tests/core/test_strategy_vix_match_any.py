"""Verification: all 7 strategies match-any for VIX regime dimensions (Sprint 27.9 S2c).

Confirms that no strategy is blocked by VIX dimension values, since all strategy
configs leave operating_conditions at default None (match-any for every field).
"""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import pytest
import yaml

from argus.core.regime import RegimeOperatingConditions, RegimeVector
from argus.data.vix_config import (
    TermStructureRegime,
    VolRegimeMomentum,
    VolRegimePhase,
    VRPTier,
)

STRATEGY_DIR = Path("config/strategies")

STRATEGY_YAMLS = [
    "orb_breakout.yaml",
    "orb_scalp.yaml",
    "vwap_reclaim.yaml",
    "afternoon_momentum.yaml",
    "red_to_green.yaml",
    "bull_flag.yaml",
    "flat_top_breakout.yaml",
]


def _base_regime_vector(**overrides: object) -> RegimeVector:
    """Build a valid RegimeVector with sensible defaults, applying overrides."""
    defaults: dict[str, object] = {
        "computed_at": datetime.now(timezone.utc),
        "trend_score": 0.3,
        "trend_conviction": 0.6,
        "volatility_level": 0.15,
        "volatility_direction": 0.0,
        "universe_breadth_score": 0.55,
        "breadth_thrust": False,
        "average_correlation": 0.40,
        "correlation_regime": "normal",
        "sector_rotation_phase": "mixed",
        "leading_sectors": [],
        "lagging_sectors": [],
        "opening_drive_strength": 0.3,
        "first_30min_range_ratio": 1.0,
        "vwap_slope": 0.0001,
        "direction_change_count": 2,
        "intraday_character": "choppy",
        "primary_regime": "range_bound",
        "regime_confidence": 0.7,
        "vol_regime_phase": None,
        "vol_regime_momentum": None,
        "term_structure_regime": None,
        "variance_risk_premium": None,
        "vix_close": None,
    }
    defaults.update(overrides)
    return RegimeVector(**defaults)  # type: ignore[arg-type]


# All enum member combinations for the 4 VIX dimensions
VIX_COMBOS = list(
    product(
        list(VolRegimePhase),
        list(VolRegimeMomentum),
        list(TermStructureRegime),
        list(VRPTier),
    )
)

# Subset for parametrize: one representative per VIX dimension enum
VIX_REPRESENTATIVE_VALUES: list[
    tuple[VolRegimePhase, VolRegimeMomentum, TermStructureRegime, VRPTier]
] = [
    (VolRegimePhase.CALM, VolRegimeMomentum.STABILIZING,
     TermStructureRegime.CONTANGO_LOW, VRPTier.COMPRESSED),
    (VolRegimePhase.CRISIS, VolRegimeMomentum.DETERIORATING,
     TermStructureRegime.BACKWARDATION_HIGH, VRPTier.EXTREME),
    (VolRegimePhase.VOL_EXPANSION, VolRegimeMomentum.NEUTRAL,
     TermStructureRegime.CONTANGO_HIGH, VRPTier.NORMAL),
    (VolRegimePhase.TRANSITION, VolRegimeMomentum.STABILIZING,
     TermStructureRegime.BACKWARDATION_LOW, VRPTier.ELEVATED),
]


@pytest.fixture()
def strategy_configs() -> dict[str, dict[str, object]]:
    """Load all 7 strategy YAML configs."""
    configs: dict[str, dict[str, object]] = {}
    for filename in STRATEGY_YAMLS:
        path = STRATEGY_DIR / filename
        assert path.exists(), f"Strategy config missing: {path}"
        with open(path) as fh:
            configs[filename] = yaml.safe_load(fh)
    return configs


def test_no_strategy_defines_operating_conditions(
    strategy_configs: dict[str, dict[str, object]],
) -> None:
    """All 7 strategies leave operating_conditions unset → implicit match-any."""
    for filename, cfg in strategy_configs.items():
        assert cfg.get("operating_conditions") is None, (
            f"{filename} defines operating_conditions — expected None for match-any"
        )


@pytest.mark.parametrize(
    "phase,momentum,term,vrp",
    VIX_REPRESENTATIVE_VALUES,
    ids=["calm_stable", "crisis_deteriorating", "expansion_neutral", "transition_stable"],
)
def test_default_conditions_match_all_vix_combos(
    phase: VolRegimePhase,
    momentum: VolRegimeMomentum,
    term: TermStructureRegime,
    vrp: VRPTier,
) -> None:
    """Default RegimeOperatingConditions (all None) matches any VIX state."""
    conditions = RegimeOperatingConditions()
    vector = _base_regime_vector(
        vol_regime_phase=phase,
        vol_regime_momentum=momentum,
        term_structure_regime=term,
        variance_risk_premium=vrp,
    )
    assert vector.matches_conditions(conditions), (
        f"Default conditions should match VIX state: "
        f"phase={phase}, momentum={momentum}, term={term}, vrp={vrp}"
    )


def test_exhaustive_vix_combos_match_default_conditions() -> None:
    """Every possible VIX enum combination matches default conditions."""
    conditions = RegimeOperatingConditions()
    for phase, momentum, term, vrp in VIX_COMBOS:
        vector = _base_regime_vector(
            vol_regime_phase=phase,
            vol_regime_momentum=momentum,
            term_structure_regime=term,
            variance_risk_premium=vrp,
        )
        assert vector.matches_conditions(conditions), (
            f"Exhaustive check failed: phase={phase}, "
            f"momentum={momentum}, term={term}, vrp={vrp}"
        )


def test_none_vix_fields_also_match_default_conditions() -> None:
    """RegimeVector with all VIX fields None still matches default conditions."""
    conditions = RegimeOperatingConditions()
    vector = _base_regime_vector()  # all VIX fields default to None
    assert vector.matches_conditions(conditions)


def test_existing_dimension_behavior_unchanged() -> None:
    """Non-VIX operating conditions still constrain correctly."""
    # Condition: trend_score must be in [0.0, 1.0] (bullish only)
    bullish_only = RegimeOperatingConditions(trend_score=(0.0, 1.0))

    bullish_vector = _base_regime_vector(trend_score=0.5)
    bearish_vector = _base_regime_vector(trend_score=-0.5)

    assert bullish_vector.matches_conditions(bullish_only)
    assert not bearish_vector.matches_conditions(bullish_only)


def test_vix_constraint_would_filter_if_set() -> None:
    """When a VIX constraint IS set, it does filter — proving match-any is opt-in."""
    constrained = RegimeOperatingConditions(vol_regime_phase=VolRegimePhase.CALM)
    calm_vector = _base_regime_vector(vol_regime_phase=VolRegimePhase.CALM)
    crisis_vector = _base_regime_vector(vol_regime_phase=VolRegimePhase.CRISIS)

    assert calm_vector.matches_conditions(constrained)
    assert not crisis_vector.matches_conditions(constrained)
