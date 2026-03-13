# Sprint 24, Session 4: Quality Engine Core

## Pre-Flight Checks
1. Read: `argus/core/events.py` (SignalEvent with new fields), `argus/intelligence/models.py` (ClassifiedCatalyst), `argus/core/regime.py` (MarketRegime)
2. Scoped test: `python -m pytest tests/intelligence/ -x -q`
3. Branch: `sprint-24`

## Objective
Create SetupQualityEngine with 5 dimension scorers per defined rubrics. Pure stateless scoring — all dependencies passed as arguments. No IO. Target <150 lines.

## Requirements

### 1. Create `argus/intelligence/quality_engine.py`:

**Dataclass:**
```python
@dataclass(frozen=True)
class SetupQuality:
    score: float          # 0-100 composite
    grade: str            # "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-"
    risk_tier: str        # Same as grade for now (used by sizer for risk % lookup)
    components: dict      # {"pattern_strength": 82.0, "catalyst_quality": 50.0, ...}
    rationale: str        # Human-readable explanation
```

**Class:** `SetupQualityEngine`
- `__init__(self, config: QualityEngineConfig)` — stores config (weights, thresholds, tiers)
- `score_setup(self, signal: SignalEvent, catalysts: list[ClassifiedCatalyst], rvol: float | None, regime: MarketRegime, allowed_regimes: list[str]) -> SetupQuality`

**Dimension scorers (private methods, each returns 0–100):**

`_score_pattern_strength(signal)`: return `max(0.0, min(100.0, signal.pattern_strength))` (clamp)

`_score_catalyst_quality(catalysts)`: Filter catalysts to last 24 hours (compare `published_at`). If empty → 50. Otherwise → `max(c.quality_score for c in recent_catalysts)`, clamped [0, 100].

`_score_volume_profile(rvol)`: If None → 50. Breakpoint interpolation: ≤0.5→10, 1.0→40, 2.0→70, ≥3.0→95. Linear between breakpoints.

`_score_historical_match()`: return 50.0 (V1 stub)

`_score_regime_alignment(regime, allowed_regimes)`: If `allowed_regimes` empty → 70. If `regime.value in allowed_regimes` → 80. Else → 20.

**Grade mapping:** `_grade_from_score(score)` using `config.thresholds` (a_plus=90, a=80, ..., c_plus=30). Score >= threshold → that grade. Below c_plus → "C-" if >= 15, else "C".

**Risk tier:** `_risk_tier_from_grade(grade)` returns the grade string itself (sizer uses it to look up risk range).

**Rationale:** Build string like "PS:82 CQ:50 VP:70 HM:50 RA:80 → Score:68.5 (B+)"

## Constraints
- Do NOT import or access: CatalystStorage, DataService, Orchestrator, EventBus, or any IO-performing class
- Do NOT add any async methods (pure sync scoring)
- Do NOT exceed 150 lines (excluding docstrings)

## Test Targets
- Per-dimension tests (5): each dimension returns expected score for known inputs
- `test_catalyst_quality_max_from_list`: Max of multiple catalysts used
- `test_catalyst_quality_empty_list`: Returns 50
- `test_catalyst_quality_filters_to_24h`: Old catalysts excluded
- `test_volume_profile_interpolation`: RVOL 1.5 → interpolated between 40 and 70
- `test_volume_profile_none`: Returns 50
- `test_regime_in_allowed`: Returns 80
- `test_regime_not_in_allowed`: Returns 20
- `test_regime_empty_allowed`: Returns 70
- `test_pattern_strength_clamped`: Values >100 → 100, <0 → 0
- `test_grade_from_score_boundaries`: 90→A+, 89→A, 80→A, 79→A-, 30→C+, 29→C-
- `test_score_setup_full_pipeline`: All dimensions → correct composite + grade
- `test_score_setup_varied_inputs_produce_different_grades`: A+ through C- achievable
- `test_rationale_string_format`: Contains all dimension abbreviations and score
- Minimum: 20
- Test command: `python -m pytest tests/intelligence/test_quality_engine.py -x -q`

## Definition of Done
- [ ] quality_engine.py < 150 lines (excl docstrings)
- [ ] No IO, no async, no external dependencies beyond config + data models
- [ ] All 5 dimension rubrics implemented exactly per spec
- [ ] Grade boundaries correct
- [ ] 20+ new tests passing

## Close-Out
Write report to `docs/sprints/sprint-24/session-4-closeout.md`.
