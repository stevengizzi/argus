# Sprint 27.9, Session 2a: RegimeVector Expansion + RegimeHistoryStore Migration

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/regime.py` (RegimeVector, RegimeClassifierV2, RegimeOperatingConditions)
   - `argus/core/regime_history.py` (RegimeHistoryStore)
   - `argus/data/vix_config.py` (enum definitions from Session 1a)
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/core/test_regime*.py -x -q
   ```
   Expected: all passing

## Objective
Extend RegimeVector frozen dataclass from 6 to 11 fields (4 new enum dimensions + vix_close float). Update `to_dict()` and `matches_conditions()`. Migrate RegimeHistoryStore to include vix_close column.

## Requirements

1. **Modify `argus/core/regime.py`**:
   - Import enums from `argus.data.vix_config`: `VolRegimePhase`, `VolRegimeMomentum`, `TermStructureRegime`, `VRPTier`
   - Add 5 new fields to `RegimeVector` frozen dataclass (AFTER existing 6 fields, all Optional with default=None):
     ```python
     vol_regime_phase: Optional[VolRegimePhase] = None
     vol_regime_momentum: Optional[VolRegimeMomentum] = None
     term_structure_regime: Optional[TermStructureRegime] = None
     variance_risk_premium: Optional[VRPTier] = None
     vix_close: Optional[float] = None
     ```
   - `primary_regime` property: NO CHANGES. Must return identical value as before.
   - `to_dict()`: Include all 11 fields. Enum values serialized as `.value` (string). None serialized as `null`.
   - **RegimeOperatingConditions**: Add 4 new Optional fields (same enum types, default=None). Update `matches_conditions()`: for each new dimension, if condition is None → skip (match-any). If condition is not None and vector value is None → match (match-any from vector side). If both non-None → compare.

2. **Modify `argus/core/regime_history.py`**:
   - Add migration check in `_init_db()` or `__init__`: after CREATE TABLE IF NOT EXISTS, check if `vix_close` column exists (PRAGMA table_info). If not, run `ALTER TABLE regime_history ADD COLUMN vix_close REAL`.
   - Update `record()` method: accept optional `vix_close: Optional[float]` parameter. Include in INSERT.
   - Update any reading methods: handle None/NULL for vix_close in old rows.

3. **Create `tests/core/test_regime_vector_expansion.py`** (6 tests):
   - `test_construction_with_original_fields_only`: Construct RegimeVector with only original 6 → no error, new fields are None.
   - `test_construction_with_all_fields`: Construct with all 11 → all values correct.
   - `test_primary_regime_unchanged`: For several known inputs, verify `primary_regime` returns same enum as pre-sprint. Hardcode expected values.
   - `test_to_dict_includes_all_fields`: Verify dict has 11 keys, None fields are None (not missing).
   - `test_matches_conditions_match_any`: Conditions specify `vol_regime_phase=CALM`, vector `vol_regime_phase=None` → match. Vector `vol_regime_phase=CALM` → match. Vector `vol_regime_phase=CRISIS` → no match.
   - `test_history_store_migration`: Create DB with old schema (6 columns), init RegimeHistoryStore → ALTER TABLE runs. Insert new row with vix_close → read back correctly. Read old row → vix_close is None.

## Constraints
- Do NOT modify `primary_regime` property logic
- Do NOT modify existing 6 RegimeVector fields or their types
- Do NOT modify RegimeClassifierV2 calculator wiring (Session 2b)
- Do NOT touch strategy files
- New fields MUST have `default=None` to preserve backward compatibility

## Test Targets
- Existing tests: all must still pass
- New tests: 6 in `tests/core/test_regime_vector_expansion.py`
- Test command: `python -m pytest tests/core/test_regime_vector_expansion.py tests/core/test_regime*.py -x -q`

## Definition of Done
- [ ] RegimeVector has 11 fields (6 original + 5 new)
- [ ] `primary_regime` returns identical values as pre-sprint
- [ ] `to_dict()` includes all 11 fields
- [ ] `matches_conditions()` handles new dimensions with match-any
- [ ] RegimeHistoryStore migration adds vix_close column
- [ ] Old rows readable without error
- [ ] 6 new tests passing
- [ ] All existing tests pass
- [ ] Close-out written to `docs/sprints/sprint-27.9/session-2a-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| R1: primary_regime identical | New test: test_primary_regime_unchanged |
| R2: Construction with original fields | New test: test_construction_with_original_fields_only |
| R3: matches_conditions match-any | New test: test_matches_conditions_match_any |
| R4: to_dict 11 fields | New test: test_to_dict_includes_all_fields |
| R5: History reads pre-sprint rows | New test: test_history_store_migration |
| R12: Existing dims unchanged | Existing regime tests still pass |

## Close-Out
Write to: `docs/sprints/sprint-27.9/session-2a-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.9/review-context.md`
2. Close-out: `docs/sprints/sprint-27.9/session-2a-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/core/test_regime_vector_expansion.py -x -q`
5. Do-not-modify: `argus/strategies/`, `argus/execution/`, `argus/backtest/`, `argus/ai/`, `argus/data/vix_data_service.py`

## Session-Specific Review Focus (for @reviewer)
1. Verify `primary_regime` logic is UNTOUCHED (diff should show NO changes to that property)
2. Verify all new fields have `default=None`
3. Verify `matches_conditions()` handles the 4 cases: both None, condition None, vector None, both set
4. Verify ALTER TABLE migration is idempotent (safe to run multiple times)
5. Verify no `asdict()` or positional unpacking of RegimeVector anywhere in existing code that would break

## Sprint-Level Regression Checklist (for @reviewer)
R1–R15 as listed in review-context.md. R1–R5, R12 are primary for this session.

## Sprint-Level Escalation Criteria (for @reviewer)
1–7 as listed in review-context.md.
