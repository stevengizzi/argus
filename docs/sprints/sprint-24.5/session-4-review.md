---BEGIN-REVIEW---

# Tier 2 Review: Sprint 24.5 Session 4 — Frontend Strategy Decision Stream Component

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-16
**Commit reviewed:** 3b8c18a
**Branch:** sprint-24.5

---

## Summary

Session 4 implemented the `StrategyDecisionStream` component, `useStrategyDecisions` hook,
TypeScript types, and an API client function. The component includes color-coded event
rows, symbol filtering, summary stats, expandable metadata, and loading/error/empty states.
12 Vitest tests pass. No protected files were modified.

One significant issue was found: the frontend response type does not match the backend
endpoint's actual return shape. The backend returns a bare JSON array, but the frontend
type expects a wrapper object with `events`, `count`, and `timestamp` fields. This will
cause a runtime failure when connected to the real backend.

---

## Session-Specific Review Focus

### 1. Hook polls at 3-second intervals
**PASS.** `useStrategyDecisions.ts` line 34: `refetchInterval: 3_000` is correctly
configured. `staleTime: 3_000` is also set, which is a reasonable match.

### 2. Component handles API errors gracefully
**PASS.** The component renders an `error-state` div with the error message text when
`error` is truthy and `isLoading` is false (lines 197-203 of the component). The error
state test confirms this works. The component does not crash on errors.

### 3. No localStorage/sessionStorage usage
**PASS.** Grep confirms zero references to `localStorage` or `sessionStorage` in the
new files. Symbol filter state is component-local via `useState`.

### 4. Color coding matches spec
**PASS.** The `resultColor()` function implements:
- SIGNAL_GENERATED and QUALITY_SCORED: `text-blue-400` (checked first, overrides result)
- PASS: `text-emerald-400` (green)
- FAIL: `text-red-400` (red)
- INFO: `text-amber-400` (amber)

All match the spec exactly.

### 5. TypeScript types match backend EvaluationEvent structure
**CONCERN.** The `EvaluationEvent` interface fields (`timestamp`, `symbol`, `strategy_id`,
`event_type`, `result`, `reason`, `metadata`) match the backend `@dataclass` fields
correctly. The `result` union type `'PASS' | 'FAIL' | 'INFO'` matches the backend
`EvaluationResult(StrEnum)`.

However, the `StrategyDecisionsResponse` wrapper type is **incorrect**:
```typescript
interface StrategyDecisionsResponse {
  events: EvaluationEvent[];
  count: number;
  timestamp: string;
}
```
The backend endpoint `GET /api/v1/strategies/{strategy_id}/decisions` returns
`list[dict[str, object]]` -- a bare JSON array, not an object with `events`/`count`/
`timestamp` fields. See `argus/api/routes/strategies.py` lines 390 and 431-437.

At runtime, `data.events` will be `undefined`, `events` will default to `[]` via the
nullish coalescing, and the component will always show the empty state regardless of
actual backend data.

This is a **data shape mismatch** that will prevent the component from working when
connected to the real API. The tests pass because they mock `useStrategyDecisions` to
return the expected wrapper shape, bypassing the actual API client.

### 6. No hardcoded API URLs
**PASS.** The `getStrategyDecisions` function in `client.ts` uses the existing
`fetchWithAuth` pattern with a relative path (`/strategies/${strategyId}/decisions`).
No hardcoded base URLs.

---

## Regression Checklist (Sprint-Level, S4 Items)

| Check | Result | Notes |
|-------|--------|-------|
| No new TypeScript build errors | PASS | Close-out reports tsc --noEmit clean |
| Component renders without console errors | PASS | All 12 tests pass without console errors |
| Existing orchestrator components unaffected | PASS | 48/48 orchestrator tests pass (9 test files) |
| OrchestratorPage.tsx not modified | PASS | Confirmed via git diff |
| StrategyOperationsCard.tsx not modified | PASS | Confirmed via git diff |
| No backend files modified | PASS | Only UI files + closeout doc in diff |

---

## Findings

### F-01: StrategyDecisionsResponse type does not match backend response shape [MEDIUM]

**Location:** `argus/ui/src/api/types.ts` lines 697-701, `argus/api/routes/strategies.py` lines 390, 431-437

**Description:** The frontend expects `{ events: EvaluationEvent[], count: number, timestamp: string }` but the backend returns a bare `list[dict]`. This means `data.events` will be `undefined` at runtime, and the component will always render the empty state when connected to the real backend.

**Impact:** Component will not display any evaluation events when connected to a live backend. Tests mask this because they mock the hook return value directly.

**Resolution options:**
1. Change the backend to return the wrapper format, OR
2. Change the frontend `StrategyDecisionsResponse` to `EvaluationEvent[]` and adjust the hook and component to work with a bare array.

This should be addressed in Session 5 (integration) or earlier. It does not meet escalation criteria because it does not break existing REST endpoints or modify protected files -- it is a bug in new additive code only.

### F-02: Summary stats count from unfiltered events [INFO]

**Location:** `argus/ui/src/features/orchestrator/StrategyDecisionStream.tsx` lines 137-145

**Description:** `signalCount` and `rejectedCount` are computed from the full `events` array, not `filteredEvents`. This means when a symbol filter is active, the summary stats show counts for ALL symbols, not the filtered subset. This may be intentional (showing global counts regardless of filter) but the spec says "Summary stats bar" without specifying the filtering behavior. Noting for awareness.

### F-03: Dual symbol filtering (client + server) [INFO]

**Location:** `useStrategyDecisions.ts` line 33 and `StrategyDecisionStream.tsx` line 133

**Description:** The hook passes `symbol` as a query param to the API for server-side filtering, AND the component also applies client-side filtering on the returned events. This is harmless (double-filtering produces correct results) but slightly redundant. The close-out report acknowledges this pattern.

---

## Escalation Criteria Check

| Criterion | Triggered? | Notes |
|-----------|-----------|-------|
| Strategy on_candle() behavior change | No | No backend changes |
| Ring buffer blocks candle processing | No | No backend changes |
| BaseStrategy construction breaks | No | No backend changes |
| Existing REST endpoints break | No | Only additive changes to client.ts |
| Frontend 3-column layout disruption | No | OrchestratorPage.tsx untouched |
| Test count deviation >50% | No | 12 new tests (spec: 8 minimum) |

No escalation criteria triggered.

---

## Verdict

**CONCERNS**

The implementation is well-executed within its scope -- clean component architecture,
proper use of existing patterns (Card/CardHeader, fetchWithAuth, Framer Motion, TanStack
Query), good test coverage (12 tests, all passing), and no modifications to protected
files. The color coding, symbol filter, summary stats, loading/error/empty states, and
expandable metadata all work correctly in tests.

However, finding F-01 (response type mismatch) means the component will not work when
connected to the real backend API. The backend returns a bare array but the frontend
expects a wrapper object. This is a medium-severity integration bug that will manifest
at runtime. It should be straightforward to fix (either adjust the type + hook to expect
an array, or adjust the backend to return a wrapper) but it must be addressed before or
during Session 5 integration.

The close-out self-assessment of CLEAN is slightly optimistic given F-01, which would
more accurately be MINOR_DEVIATIONS.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "24.5",
  "session": "S4",
  "reviewer": "tier2-automated",
  "verdict": "CONCERNS",
  "confidence": 0.92,
  "findings": [
    {
      "id": "F-01",
      "severity": "MEDIUM",
      "category": "type-mismatch",
      "title": "StrategyDecisionsResponse type does not match backend response shape",
      "description": "Frontend expects {events, count, timestamp} wrapper but backend returns bare list[dict]. Component will always show empty state at runtime.",
      "location": "argus/ui/src/api/types.ts:697-701, argus/api/routes/strategies.py:390",
      "escalation_trigger": false
    },
    {
      "id": "F-02",
      "severity": "INFO",
      "category": "behavior",
      "title": "Summary stats count from unfiltered events",
      "description": "signalCount and rejectedCount use full events array, not filteredEvents. Stats do not change when symbol filter is active.",
      "location": "argus/ui/src/features/orchestrator/StrategyDecisionStream.tsx:137-145",
      "escalation_trigger": false
    },
    {
      "id": "F-03",
      "severity": "INFO",
      "category": "redundancy",
      "title": "Dual symbol filtering (client + server)",
      "description": "Symbol filter applied both as API query param and client-side array filter. Harmless but redundant.",
      "location": "argus/ui/src/hooks/useStrategyDecisions.ts:33, StrategyDecisionStream.tsx:133",
      "escalation_trigger": false
    }
  ],
  "tests_pass": true,
  "test_count": 48,
  "scope_compliance": "COMPLETE",
  "protected_files_clean": true,
  "closeout_accuracy": "MINOR_DEVIATION",
  "recommendation": "Fix F-01 (response type mismatch) before or during Session 5 integration. Either change StrategyDecisionsResponse to EvaluationEvent[] or update the backend endpoint to return a wrapper object."
}
```
