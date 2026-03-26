# Sprint 27.9, Session 2b: Four Calculator Classes + RegimeClassifierV2 Wiring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/regime.py` (RegimeClassifierV2, existing calculators for pattern reference)
   - `argus/data/vix_data_service.py` (VIXDataService API)
   - `argus/data/vix_config.py` (enums, VixRegimeConfig, boundary models)
   - `argus/core/breadth.py` or `argus/core/market_correlation.py` (existing calculator pattern reference)
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/core/test_regime_vector_expansion.py tests/core/test_regime*.py -x -q
   ```
   Expected: all passing (confirmed by Session 2a close-out)

## Objective
Implement 4 VIX-based calculator classes following the Sprint 27.6 calculator pattern. Wire them into RegimeClassifierV2. All calculators return None when VIX data unavailable.

## Requirements

1. **Create `argus/core/vix_calculators.py`** (~150 lines):

   All 4 calculators follow this pattern:
   - Accept `VIXDataService` reference in constructor
   - Have a `classify()` method returning the enum value or None
   - Check `vix_data_service.is_ready` and `not vix_data_service.is_stale` before computing
   - Use boundary thresholds from `VixRegimeConfig` (passed at init or accessed from service)

   **a) VolRegimePhaseCalculator:**
   ```python
   def classify(self) -> Optional[VolRegimePhase]:
       latest = self.vix_service.get_latest_daily()
       if latest is None: return None
       x = latest.get('vol_of_vol_ratio')
       y = latest.get('vix_percentile')
       if x is None or y is None: return None
       bounds = self.boundaries  # VolRegimeBoundaries
       if y >= bounds.crisis_min_y: return VolRegimePhase.CRISIS
       if x <= bounds.calm_max_x and y <= bounds.calm_max_y: return VolRegimePhase.CALM
       if x <= bounds.transition_max_x and y <= bounds.transition_max_y: return VolRegimePhase.TRANSITION
       return VolRegimePhase.VOL_EXPANSION
   ```
   Note: CRISIS check first (highest priority).

   **b) VolRegimeMomentumCalculator:**
   - Get current and `momentum_window`-days-ago vol-of-vol coordinates from VIXDataService
   - Compute Euclidean displacement magnitude and direction
   - If magnitude < `momentum_threshold`: NEUTRAL
   - If moving toward lower x and lower y (toward attractor ~(0.94, 0.38)): STABILIZING
   - Otherwise: DETERIORATING
   - Need `get_history(days_back: int)` method on VIXDataService (add if not present — minor addition)

   **c) TermStructureRegimeCalculator:**
   ```python
   def classify(self) -> Optional[TermStructureRegime]:
       latest = self.vix_service.get_latest_daily()
       if latest is None: return None
       x = latest.get('term_structure_proxy')
       y = latest.get('vix_percentile')
       if x is None or y is None: return None
       bounds = self.boundaries
       is_contango = x <= bounds.contango_threshold
       is_low = y < bounds.low_high_percentile_split
       if is_contango and is_low: return TermStructureRegime.CONTANGO_LOW
       if is_contango and not is_low: return TermStructureRegime.CONTANGO_HIGH
       if not is_contango and is_low: return TermStructureRegime.BACKWARDATION_LOW
       return TermStructureRegime.BACKWARDATION_HIGH
   ```

   **d) VarianceRiskPremiumCalculator:**
   ```python
   def classify(self) -> Optional[VRPTier]:
       latest = self.vix_service.get_latest_daily()
       if latest is None: return None
       vrp = latest.get('variance_risk_premium')
       if vrp is None: return None
       bounds = self.boundaries
       if vrp <= bounds.compressed_max: return VRPTier.COMPRESSED
       if vrp <= bounds.normal_max: return VRPTier.NORMAL
       if vrp <= bounds.elevated_max: return VRPTier.ELEVATED
       return VRPTier.EXTREME
   ```
   Also expose `vrp_value: Optional[float]` for continuous value access.

2. **Modify `argus/core/regime.py`** (RegimeClassifierV2):
   - Add optional `vix_data_service: Optional[VIXDataService]` parameter to constructor
   - If vix_data_service provided and config enabled: instantiate 4 VIX calculators
   - In `classify()` method: after existing 6 dimensions, call VIX calculators. Populate new RegimeVector fields. If any calculator returns None, that field stays None.
   - Pass `vix_close` from VIXDataService latest daily to RegimeVector.

3. **Modify `argus/data/vix_data_service.py`** (if needed):
   - Add `get_history(days_back: int) -> Optional[list[dict]]` method for momentum calculator. Returns last N daily records from SQLite, ordered by date descending.

4. **Modify `config/regime.yaml`**:
   - Add section for VIX calculator enable flags (under `regime_intelligence`):
     ```yaml
     vix_calculators_enabled: true  # Master enable for all 4 VIX calculators
     ```

5. **Create `tests/core/test_vix_calculators.py`** (8 tests):
   - `test_vol_regime_phase_calm`: Mock VIXDataService returning x=0.85, y=0.30 → CALM
   - `test_vol_regime_phase_crisis`: x=1.5, y=0.90 → CRISIS (y takes priority)
   - `test_vol_regime_phase_unavailable`: Mock VIXDataService returning None → None
   - `test_term_structure_contango_low`: x=0.95, y=0.30 → CONTANGO_LOW
   - `test_term_structure_backwardation_high`: x=1.15, y=0.70 → BACKWARDATION_HIGH
   - `test_vrp_tiers`: Test all 4 VRP thresholds with boundary values
   - `test_momentum_stabilizing`: 5-day displacement toward lower coordinates → STABILIZING
   - `test_classifier_v2_populates_new_fields`: Full RegimeClassifierV2 with mocked VIXDataService → RegimeVector has non-None VIX fields

## Constraints
- Do NOT modify existing 6 calculator classes or their logic
- Do NOT modify RegimeVector field definitions (done in 2a)
- Do NOT modify strategy files (Session 2c)
- Calculator pattern: match existing Sprint 27.6 calculator structure exactly
- If adding `get_history()` to VIXDataService, keep it minimal

## Test Targets
- Existing tests: all must still pass
- New tests: 8 in `tests/core/test_vix_calculators.py`
- Test command: `python -m pytest tests/core/test_vix_calculators.py -x -q`

## Definition of Done
- [ ] 4 calculator classes implemented following existing pattern
- [ ] RegimeClassifierV2 wires VIX calculators when VIXDataService provided
- [ ] Calculators return None when VIX data unavailable
- [ ] RegimeVector populated with VIX dimensions after classification
- [ ] 8 new tests passing
- [ ] Existing regime tests still pass
- [ ] R12 verified: existing 6 dimensions produce same values
- [ ] Close-out written to `docs/sprints/sprint-27.9/session-2b-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| R12: Existing 6 dims produce same values | Run existing regime tests + new test with mocked VIXDataService=None → 6 dims unchanged |
| R1: primary_regime unchanged | Existing test from 2a still passes |
| Existing calculators unmodified | `git diff argus/core/breadth.py argus/core/market_correlation.py argus/core/sector_rotation.py argus/core/intraday_character.py` → empty |

## Close-Out
Write to: `docs/sprints/sprint-27.9/session-2b-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.9/review-context.md`
2. Close-out: `docs/sprints/sprint-27.9/session-2b-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/core/test_vix_calculators.py tests/core/test_regime*.py -x -q`
5. Do-not-modify: `argus/core/breadth.py`, `argus/core/market_correlation.py`, `argus/core/sector_rotation.py`, `argus/core/intraday_character.py`, `argus/strategies/`, `argus/execution/`

## Session-Specific Review Focus (for @reviewer)
1. Verify CRISIS check has highest priority in VolRegimePhaseCalculator (checked before CALM/TRANSITION)
2. Verify all 4 calculators return None (not default enum) when VIXDataService returns None
3. Verify existing 6 calculator outputs are IDENTICAL with and without VIXDataService
4. Verify RegimeClassifierV2 constructor accepts VIXDataService=None gracefully
5. Verify momentum calculator handles insufficient history (< momentum_window days)
6. If compaction occurred: verify all 4 calculators present (not just 2)

## Sprint-Level Regression Checklist (for @reviewer)
R1–R15 as in review-context.md. R1, R12 primary for this session.

## Sprint-Level Escalation Criteria (for @reviewer)
1–7 as in review-context.md. #3 (existing calculator changes) most relevant.
