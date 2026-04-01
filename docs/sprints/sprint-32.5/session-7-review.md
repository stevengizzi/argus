---BEGIN-REVIEW---

# Sprint 32.5, Session 7 — Tier 2 Review

**Reviewer:** Automated Tier 2
**Date:** 2026-04-01
**Session objective:** DEF-131 Experiments Dashboard — 9th Command Center page
**Branch:** sprint-32.5-session-5 (uncommitted working tree changes)
**Close-out self-assessment:** CLEAN

---

## 1. Spec Compliance

All spec items verified present and correct:

| Spec Item | Verdict |
|-----------|---------|
| `useExperimentVariants()` TanStack Query hook | PASS |
| `usePromotionEvents()` TanStack Query hook | PASS |
| TypeScript interfaces match S5 API response shapes | PASS |
| Variant status table with 8 columns | PASS |
| Mode badge (green LIVE / gray SHADOW) | PASS |
| Sortable columns (5 sort keys) | PASS |
| Group by pattern name | PASS |
| Promotion event log (newest first) | PASS |
| Event type badges (up/down arrows) | PASS |
| Pattern comparison on group header click | PASS |
| Best Sharpe (accent) / best Win Rate (profit) highlighted | PASS |
| Disabled state (503) with data-testid | PASS |
| Empty state with data-testid | PASS |
| Route at `/experiments` | PASS |
| Nav entry with FlaskConical icon | PASS |
| Keyboard shortcut `9` | PASS |
| Page lazy-loaded (React.lazy + Suspense) | PASS |
| No promote/demote/trigger buttons (read-only) | PASS |
| Existing 8 pages unaffected | PASS |

---

## 2. Regression Checklist

| Check | Result |
|-------|--------|
| All 8 existing page components unmodified | PASS -- `git diff` confirms zero changes to any existing page file |
| Keyboard shortcuts 1-8 unchanged | PASS -- NAV_ROUTES positions 0-7 identical to pre-session |
| Shortcut 9 added cleanly | PASS -- `/experiments` appended as index 8 |
| Sidebar divider count = 3 | PASS -- only Performance, Pattern Library, and Debrief have `divider: true` |
| Lazy-loaded via React.lazy + Suspense | PASS -- App.tsx lines 25-27 and 67-75 |
| Hooks follow TanStack Query patterns | PASS -- `useQuery` with typed generics, staleTime, refetchInterval |
| 503 detection for disabled state | PASS -- checks `ApiError.status === 503` |
| No backend files modified | PASS -- `git diff` confirms zero backend changes |

---

## 3. Test Results

**Vitest:** 706 passed, 3 failed (pre-existing GoalTracker failures, unchanged)
- 5 new ExperimentsPage tests all pass
- No pre-existing test regressions

**Pytest:** 4489 passed, 0 failures
- No backend regressions

---

## 4. Type Shape Verification

Frontend `ExperimentVariant` interface fields match backend `query_variants_with_metrics()` return:
- variant_id, pattern_name, detection_params, exit_overrides, config_fingerprint, mode, status, trade_count, shadow_trade_count, win_rate, expectancy, sharpe -- all present with correct nullability.

Frontend `PromotionEvent` interface fields match backend `query_promotion_events()` return:
- event_id, variant_id, pattern_name, event_type, from_mode, to_mode, timestamp, trigger_reason, metrics_snapshot, shadow_trades, shadow_expectancy -- all present with correct nullability.

---

## 5. Findings

**F3-1 (Minor): Repeated bestSharpe/bestWr computation inside comparison map loop**
File: `ExperimentsPage.tsx`, lines 221-224. `Math.max(...)` over all variants is computed once per variant row inside the `.map()` callback. Should be lifted above the `.map()`. No functional or performance impact at expected scale (single-digit variants per pattern group). Cosmetic only.

**F3-2 (Minor): Mode column sorted by trade_count**
File: `ExperimentsPage.tsx`, line 169. The "Mode" column header uses `sortKey="trade_count"`, which means clicking "Mode" sorts by trade count rather than by mode string. This is a minor UX inconsistency -- the header says "Mode" but the sort behavior is trade_count. Likely intentional (sorting by mode string is not very useful), but the dual sort keys on the same column could confuse users.

---

## 6. Observations (Non-Findings)

- The `retry: false` on both hooks is a good judgment call. When experiments are disabled (503), retrying wastes requests.
- The closeout correctly noted the divider count constraint and avoided adding a 4th divider.
- Changes are uncommitted in the working tree, which is noted in the closeout. This is a workflow note, not a code quality issue.

---

## 7. Verdict

**CLEAR**

All spec items implemented correctly. No regressions. Types match backend API shapes. Navigation integration is clean. Read-only constraint honored. Two minor cosmetic findings (F3-1, F3-2) that do not warrant CONCERNS status.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "id": "F3-1",
      "severity": "minor",
      "category": "code-quality",
      "description": "bestSharpe/bestWr recomputed inside .map() loop in comparison view. Should be lifted above the loop. No functional impact at expected scale.",
      "file": "argus/ui/src/pages/ExperimentsPage.tsx",
      "lines": "221-224"
    },
    {
      "id": "F3-2",
      "severity": "minor",
      "category": "ux",
      "description": "Mode column SortHeader uses sortKey='trade_count', making it a duplicate sort target with the Trades column. Minor UX inconsistency.",
      "file": "argus/ui/src/pages/ExperimentsPage.tsx",
      "line": "169"
    }
  ],
  "tests": {
    "vitest_passed": 706,
    "vitest_failed": 3,
    "vitest_failed_preexisting": true,
    "vitest_new_tests": 5,
    "pytest_passed": 4489,
    "pytest_failed": 0
  },
  "spec_compliance": "full",
  "regression_check": "pass",
  "escalation_triggers": []
}
```
