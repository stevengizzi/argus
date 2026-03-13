# Sprint 24, Session 5a: Dynamic Position Sizer + Config Models

## Pre-Flight Checks
1. Read: `argus/intelligence/quality_engine.py` (SetupQuality, QualityGrade), `argus/intelligence/config.py` (existing CatalystConfig pattern), `argus/core/events.py` (SignalEvent)
2. Scoped test: `python -m pytest tests/intelligence/test_quality_engine.py -x -q`
3. Branch: `sprint-24`

## Objective
Create DynamicPositionSizer. Add QualityEngineConfig + sub-config Pydantic models with validators to intelligence/config.py.

## Requirements

### 1. In `argus/intelligence/config.py`, add:

```python
class QualityWeightsConfig(BaseModel):
    pattern_strength: float = 0.30
    catalyst_quality: float = 0.25
    volume_profile: float = 0.20
    historical_match: float = 0.15
    regime_alignment: float = 0.10

    @model_validator(mode="after")
    def validate_weight_sum(self) -> "QualityWeightsConfig":
        total = (self.pattern_strength + self.catalyst_quality + self.volume_profile
                 + self.historical_match + self.regime_alignment)
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Quality weights must sum to 1.0, got {total:.4f}")
        return self

class QualityThresholdsConfig(BaseModel):
    a_plus: int = 90
    a: int = 80
    a_minus: int = 70
    b_plus: int = 60
    b: int = 50
    b_minus: int = 40
    c_plus: int = 30
    # Validator: all in [0,100], strictly descending

class QualityRiskTiersConfig(BaseModel):
    a_plus: list[float] = [0.02, 0.03]
    a: list[float] = [0.015, 0.02]
    a_minus: list[float] = [0.01, 0.015]
    b_plus: list[float] = [0.0075, 0.01]
    b: list[float] = [0.005, 0.0075]
    b_minus: list[float] = [0.0025, 0.005]
    c_plus: list[float] = [0.0025, 0.0025]
    # Validator: each pair [min, max] with min <= max, both in [0, 1]

class QualityEngineConfig(BaseModel):
    enabled: bool = True
    weights: QualityWeightsConfig = QualityWeightsConfig()
    thresholds: QualityThresholdsConfig = QualityThresholdsConfig()
    risk_tiers: QualityRiskTiersConfig = QualityRiskTiersConfig()
    min_grade_to_trade: str = "C+"
    # Validator: min_grade_to_trade in valid grade strings
```

### 2. Create `argus/intelligence/position_sizer.py` (~80 lines):

```python
class DynamicPositionSizer:
    def __init__(self, config: QualityEngineConfig): ...

    def calculate_shares(self, quality: SetupQuality, entry_price: float,
                         stop_price: float, allocated_capital: float,
                         buying_power: float) -> int:
        """Grade → risk % (midpoint of range) → shares."""
        tier = self._get_risk_tier(quality.grade)
        risk_pct = (tier[0] + tier[1]) / 2  # Flat midpoint
        risk_dollars = allocated_capital * risk_pct
        risk_per_share = abs(entry_price - stop_price)
        if risk_per_share <= 0:
            return 0
        shares = int(risk_dollars / risk_per_share)
        # Buying power check
        if shares * entry_price > buying_power:
            shares = int(buying_power / entry_price)
        return max(0, shares)
```

## Constraints
- Do NOT modify: `argus/core/config.py` (that's Session 5b)
- Do NOT add quality_engine to SystemConfig yet (Session 5b)

## Test Targets
- `test_weight_sum_valid`: Default config passes validation
- `test_weight_sum_invalid`: Weights summing to 0.9 → ValidationError
- `test_thresholds_descending`: Valid thresholds pass
- `test_thresholds_not_descending`: a_plus < a → ValidationError
- `test_risk_tiers_valid`: Default tiers pass
- `test_risk_tiers_min_exceeds_max`: [0.03, 0.02] → ValidationError
- `test_sizer_a_plus_larger_than_b`: A+ grade → more shares than B grade
- `test_sizer_midpoint_calculation`: A grade (1.5-2.0%) → risk_pct = 0.0175
- `test_sizer_zero_risk_per_share`: entry == stop → 0 shares
- `test_sizer_buying_power_limit`: Large position reduced by buying power
- `test_sizer_returns_zero_for_tiny_position`: Very small capital → 0 shares
- Minimum: 12
- Test command: `python -m pytest tests/intelligence/test_position_sizer.py tests/intelligence/test_quality_config.py -x -q`

## Definition of Done
- [ ] All config models with validators
- [ ] Weight sum validation rejects invalid configs at startup
- [ ] Sizer produces correct share counts per grade
- [ ] 12+ new tests passing

## Close-Out
Write report to `docs/sprints/sprint-24/session-5a-closeout.md`.

