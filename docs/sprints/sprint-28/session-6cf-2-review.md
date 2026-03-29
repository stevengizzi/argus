---BEGIN-REVIEW---

# Sprint 28, Session S6cf-2 Review: Trade Overlap Count + Dead Code Cleanup

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-29
**Commit range:** Uncommitted working tree changes on top of 15de122
**Close-out report:** `docs/sprints/sprint-28/session-6cf-2-closeout.md`

## 1. Scope Compliance

All 8 Definition of Done items from the implementation prompt are satisfied:

| Item | Status | Notes |
|------|--------|-------|
| A6: Dead reconciliation heuristic removed | PASS | 11 lines removed from `outcome_collector.py` lines 105-115. No test referenced this code (grep confirmed `test_data_quality_preamble_gaps` does not exist). |
| B1: overlap_counts computed (main loop + early return) | PASS | Union of date sets in main loop; empty dict in early-return path. |
| B2: overlap_counts field on CorrelationResult | PASS | `dict[tuple[str, str], int]` field added. |
| B3: to_dict() serialization | PASS | Pipe-delimited key pattern, same as correlation_matrix. |
| B4: from_dict() deserialization | PASS | Pipe-split with len==2 guard, int() cast. |
| B5: TS interface | PASS | `overlap_counts: Record<string, number>` added. |
| B6: Tooltip "Aligned days: N" | PASS | Conditional render with `tooltip.overlapDays !== null`. |
| B7: Test mock updates | PASS | `:` to `|` fix in test mock; overlap_counts added to all 4 test fixtures. |

## 2. Review Focus Items

### 2.1 overlap_counts uses union of dates (not intersection)

**PASS.** Line 106-109 of `correlation_analyzer.py`:
```python
overlap_counts[pair] = len(
    set(daily_pnl[strat_a].keys())
    | set(daily_pnl[strat_b].keys())
)
```
This is the union operator (`|`), matching how `_compute_pearson` aligns data (line 214: `all_dates = sorted(set(pnl_a.keys()) | set(pnl_b.keys()))`). Consistent.

### 2.2 to_dict() / from_dict() round-trip

**PASS.** Serialization (models.py line 203-207) uses `f"{k[0]}|{k[1]}"` pattern identical to correlation_matrix. Deserialization (line 269-275) uses `split("|")` with `len(parts) == 2` guard and `int(val)` cast. The existing `test_round_trip_with_all_fields` test in `test_models.py` covers this path since the fixture now includes `overlap_counts`.

### 2.3 Tooltip graceful null handling

**PASS.** The lookup uses optional chaining (`correlationResult.overlap_counts?.[overlapKey1]`) with nullish coalescing to `null`. The render is gated by `tooltip.overlapDays !== null`. Both key orderings are checked (forward and reverse).

### 2.4 Dead code removal does not break tests

**PASS.** No test named `test_data_quality_preamble_gaps` exists. All 135 learning tests pass. The removed code was provably dead: trade-sourced OutcomeRecords always have `rejection_reason=None` (set at line 224 of `_collect_trades` where no `rejection_reason` field is populated).

### 2.5 CorrelationMatrix test mock uses `|` delimiter

**PASS.** The `makeCorrelation` helper in `CorrelationMatrix.test.tsx` now uses `'orb_breakout|vwap_reclaim'` (line 15) instead of the stale colon delimiter. The empty-state test also includes `overlap_counts: {}`.

### 2.6 ruff check on modified files

**PASS (no new warnings).** Ruff reports 2 E501 errors in `outcome_collector.py` at lines 320-321 -- these are pre-existing on untouched lines (counterfactual record construction). Zero warnings on lines modified by this session.

## 3. Test Results

- **Backend:** 135 learning tests passed (133 existing + 2 new overlap_counts tests)
- **Frontend:** 680 Vitest tests passed (100 test files)
- **Ruff:** 2 pre-existing E501 warnings on untouched lines; zero new warnings

## 4. Regression Checklist (Sprint-Level, Applicable Items)

- [x] Data Access: OutcomeCollector changes are read-only code removal; no new writes.
- [x] Frontend: Learning UI components render gracefully (overlap_counts optional chaining).
- [x] Test Suite: All learning pytest + all Vitest pass, no hangs.
- [x] No files outside scope modified (only the 10 files listed in close-out).

## 5. Escalation Criteria Check

None triggered. No config safety issues, no mathematically impossible results, no data integrity concerns. This session is a narrow cross-layer feature addition + dead code removal.

## 6. Findings

No issues found. The implementation exactly follows the spec across all layers. Code quality is consistent with the existing codebase patterns.

## 7. Close-Out Report Accuracy

The close-out report accurately reflects the changes. Self-assessment of CLEAN is justified. Test count (135 pytest) matches actual run. Context state GREEN is appropriate.

**Note:** The close-out reports "133 existing + 2 new" but the total is 135, not 147 as mentioned in the implementation prompt's pre-flight check. The discrepancy is in the pre-flight expectation (147), not in the actual implementation. The session correctly reports the actual count.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "summary": "All 8 Definition of Done items satisfied. overlap_counts correctly uses union of dates matching _compute_pearson alignment. to_dict/from_dict round-trip with pipe-delimited keys verified. Tooltip gracefully handles null overlap_counts. Dead code removal is safe (trade-sourced records never have rejection_reason). All 135 learning tests + 680 Vitest tests pass. Zero new ruff warnings.",
  "findings": [],
  "tests_passed": true,
  "tests_total": 815,
  "tests_backend": 135,
  "tests_frontend": 680,
  "files_modified": 10,
  "escalation_triggers": []
}
```
