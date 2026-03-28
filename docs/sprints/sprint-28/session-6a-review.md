---BEGIN-REVIEW---

# Sprint 28, Session 6a Review
## Frontend -- Hooks + API Client + Recommendation Cards

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-28
**Close-out self-assessment:** CLEAN

---

## 1. Spec Compliance

All Definition of Done items are satisfied:

- [x] Typed API client with all 8 endpoints (`learningApi.ts`)
- [x] TanStack Query hooks with 5-minute stale time and mutations (`useLearningReport.ts`, `useConfigProposals.ts`)
- [x] WeightRecommendationCard with full state machine (PENDING, APPROVED, APPLIED, DISMISSED, SUPERSEDED)
- [x] ThresholdRecommendationCard with full state machine
- [x] Approve/dismiss UX with optional notes (two-click pattern)
- [x] 18 Vitest tests (12 weight + 6 threshold), exceeds minimum of 5
- [x] No existing page components modified (constraint honored)
- [x] No StrategyHealthBands, CorrelationMatrix, or Dashboard card created (S6c constraint honored)
- [x] Close-out report written

## 2. Review Focus Items

### 2a. TypeScript interfaces vs backend Python models

**Verdict: PASS**

All interfaces align correctly:

| TS Interface | Python Model | Notes |
|---|---|---|
| `WeightRecommendation` | `models.WeightRecommendation` | All 11 fields match. `confidence` is `ConfidenceLevel` string union vs `StrEnum` -- compatible. |
| `ThresholdRecommendation` | `models.ThresholdRecommendation` | All 7 fields match. `recommended_direction` is `'raise' \| 'lower'` vs `Literal["raise", "lower"]` -- compatible. |
| `CorrelationResult` | `models.CorrelationResult` | `correlation_matrix` is `Record<string, number>` matching the `to_dict()` serialization (pipe-delimited string keys). `strategy_pairs` is `[string, string][]` matching serialized list-of-lists. |
| `ConfigProposal` | `learning.py ProposalResponse` | All 10 fields match. Dates are ISO strings on both sides. |
| `ConfigChangeEntry` | `learning.py ChangeHistoryEntry` | All 8 fields match. |
| `DataQualityPreamble` | `models.DataQualityPreamble` | All 7 fields match. `earliest_date`/`latest_date` as `string \| null` matches ISO serialization of `datetime \| None`. |
| `LearningReport` | `models.LearningReport` | All 9 fields match. `correlation_result` nullable on both sides. |
| `ProposalStatus` | `models.PROPOSAL_STATUSES` | All 8 values match exactly. |
| `TriggerResponse` | `learning.py TriggerResponse` | All 6 fields match. |
| `ReportSummary` | `learning.py ReportSummaryResponse` | All 7 fields match. |

### 2b. Mutation hooks invalidate correct query keys

**Verdict: PASS**

All four mutation hooks (`useApproveProposal`, `useDismissProposal`, `useRevertProposal`, `useTriggerAnalysis`) invalidate:
- `['learning', 'proposals']` -- refreshes proposal list
- `['learning', 'reports']` -- refreshes report list
- `['learning', 'report']` -- refreshes individual report detail

This covers all query keys used by the read hooks. Trigger analysis also invalidates all three, which is correct since it generates new reports and proposals.

### 2c. Confidence badge color mapping

**Verdict: PASS**

`ConfidenceBadge.tsx` maps:
- HIGH = `text-emerald-400` (green)
- MODERATE = `text-amber-400` (amber)
- LOW = `text-orange-400` (orange)
- INSUFFICIENT_DATA = `text-gray-400` (gray)

Matches spec exactly. Tests verify MODERATE and INSUFFICIENT_DATA badge rendering.

### 2d. SUPERSEDED state prevents approve/dismiss interactions

**Verdict: PASS**

Both card components conditionally render action buttons only when `isPending` (status === 'PENDING'). SUPERSEDED status results in:
- No approve/dismiss buttons rendered
- Strikethrough on dimension/grade name
- "Superseded by newer report" label
- Reduced opacity (0.60)

Tests explicitly verify no action buttons appear for SUPERSEDED state.

### 2e. Notes are optional (approve without notes should work)

**Verdict: PASS**

The two-click pattern works correctly:
1. First click opens textarea
2. Second click confirms with `notes || undefined` (empty string becomes `undefined`)
3. API client sends no body when notes is `undefined`
4. Backend accepts `ApproveRequest | None = None`

Test `approve click shows notes textarea, confirm calls onApprove` verifies `onApprove` is called with `('p1', undefined)`.

## 3. Code Quality

**Strengths:**
- Clean DRY extraction of `ConfidenceBadge` as shared component
- Comprehensive test coverage (18 tests covering all states)
- Consistent data-testid attributes for testing
- Proper TypeScript typing throughout (no `any`)

**Minor observations (non-blocking):**
- `fetchWithAuth` is duplicated from `client.ts` rather than exported. The close-out notes this as a deliberate judgment call to avoid modifying the existing API surface. This is acceptable for session scope discipline but creates a maintenance surface for future sessions.
- `Content-Type: application/json` is set unconditionally, including for POST requests with no body (e.g., `triggerLearningAnalysis`). This is harmless but slightly imprecise.
- `useLearningReport` uses a two-query waterfall (list then detail). This adds an extra round-trip. Acceptable for V1 given the 5-minute stale time, but a dedicated `/reports/latest` backend endpoint could eliminate the waterfall in a future session.

## 4. Regression Check

- Vitest: 96 files, 663 tests, 0 failures (baseline was 94/645, delta is +2 files / +18 tests)
- Only existing file modified: `hooks/index.ts` (export additions only)
- No backend files modified
- No page components modified (S6b/S6c constraint honored)
- Escalation criterion 8 ("Frontend proposal mutations don't update UI") is addressed by proper cache invalidation in all mutation hooks

## 5. Verdict

**CLEAR**

All spec items implemented correctly. TypeScript interfaces precisely match backend Python models. Mutation hooks invalidate appropriate cache keys. Component state machines handle all proposal statuses correctly. Test coverage exceeds minimum. No regressions. No escalation criteria triggered.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "summary": "All 8 Definition of Done items satisfied. TypeScript interfaces match backend models exactly. Mutation hooks invalidate correct query keys. Confidence badge colors match spec. SUPERSEDED state correctly prevents interactions. Notes are optional. 18 Vitest tests pass (96 files / 663 total). No regressions, no escalation criteria triggered.",
  "findings": [],
  "tests": {
    "vitest_files": 96,
    "vitest_tests": 663,
    "vitest_failures": 0,
    "new_test_files": 2,
    "new_tests": 18
  },
  "escalation_triggers": []
}
```
