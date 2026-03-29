# Sprint 28, Session S6cf-2: Close-Out Report

## Session Summary
Trade overlap count added to CorrelationResult + dead reconciliation heuristic removed.

## Change Manifest

| File | Change |
|------|--------|
| `argus/intelligence/learning/outcome_collector.py` | Removed dead reconciliation heuristic (11 lines, lines 105–115) |
| `argus/intelligence/learning/models.py` | Added `overlap_counts: dict[tuple[str, str], int]` to `CorrelationResult`; `to_dict()` serializes with `\|` key pattern; `from_dict()` deserializes with `\|` key parsing |
| `argus/intelligence/learning/correlation_analyzer.py` | Computes `overlap_counts` (union of date sets) in main loop + early-return path |
| `argus/ui/src/api/learningApi.ts` | Added `overlap_counts: Record<string, number>` to TS `CorrelationResult` interface |
| `argus/ui/src/components/learning/CorrelationMatrix.tsx` | `overlapDays` in TooltipState; lookup via both key orderings; renders "Aligned days: N" |
| `argus/ui/src/components/learning/CorrelationMatrix.test.tsx` | Fixed `:` → `\|` keys; added `overlap_counts` mock data |
| `tests/intelligence/learning/test_correlation_analyzer.py` | 2 new tests: `test_overlap_count_computed_per_pair`, `test_overlap_count_empty_result` |
| `tests/intelligence/learning/test_models.py` | Added `overlap_counts` to `_make_correlation_result()` fixture |
| `tests/intelligence/learning/test_learning_store.py` | Added `overlap_counts` to `CorrelationResult` fixture |
| `tests/intelligence/learning/test_learning_service.py` | Added `overlap_counts` to `_make_correlation_result()` fixture |

## Judgment Calls
None. All changes followed the implementation prompt exactly.

## Scope Verification

- [x] A6: Dead reconciliation heuristic removed from `outcome_collector.py`
- [x] B1: `overlap_counts` computed in `correlation_analyzer.py` main loop + early return
- [x] B2: `overlap_counts` field added to `CorrelationResult` dataclass
- [x] B3: `to_dict()` serializes `overlap_counts` with `|` key pattern
- [x] B4: `from_dict()` deserializes `overlap_counts` with `|` key parsing
- [x] B5: TS `CorrelationResult` interface includes `overlap_counts`
- [x] B6: Tooltip shows "Aligned days: N"
- [x] B7: Existing test mocks updated (`:` → `|` keys, `overlap_counts` field added)
- [x] No regressions: 135 pytest + 680 Vitest pass

## Deferred Items
None.

## Test Results
- **Backend:** 135 pytest learning tests passed (133 existing + 2 new)
- **Frontend:** 680 Vitest tests passed
- **Ruff:** 2 pre-existing E501 warnings on untouched lines in `outcome_collector.py`; zero new warnings

## Self-Assessment: CLEAN

## Context State: GREEN
