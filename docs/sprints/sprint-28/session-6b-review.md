# Sprint 28, Session 6b — Tier 2 Review

---BEGIN-REVIEW---

## Review Summary

**Session:** Sprint 28, Session 6b — Learning Insights Panel + Performance Page Integration
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-28
**Verdict:** CLEAR

## Scope Verification

| Spec Requirement | Status | Notes |
|---|---|---|
| LearningInsightsPanel composes recommendation cards | PASS | WeightRecommendationCard + ThresholdRecommendationCard rendered in grid layout |
| Performance page has "Learning" tab (Amendment 14) | PASS | 6th tab added to PerformanceTab union type and tabSegments array |
| Lazy loading: data only fetched when tab active | PASS | `enabled` parameter added to useLearningReport, useLearningReports, useConfigProposals; gated by `isActive` prop |
| Tab badge shows pending count | PASS | `useConfigProposals('PENDING')` count rendered via SegmentedTab `count` prop |
| Empty and disabled states | PASS | `data-testid="learning-empty"` and `data-testid="learning-disabled"` present |
| >= 4 Vitest tests | PASS | 7 tests written |
| No modification to existing Performance tabs | PASS | Existing 5 tab content components untouched; only PageHeader signature changed (new `tabSegments` prop) |
| No S6c scope creep (StrategyHealthBands, CorrelationMatrix, Dashboard card) | PASS | None created |

## Session-Specific Focus Items

### 1. Learning is a new TAB, not added to main Performance view (Amendment 14)

**PASS.** Learning is the 6th entry in `tabSegments` array (line 118, PerformancePage.tsx). It is rendered conditionally via `{activeTab === 'learning' && ...}` in AnimatePresence (line 340), following the same pattern as all other tabs. The PerformanceTab type union includes `'learning'`. This is correctly a tab, not inline content.

### 2. TanStack Query `enabled` flag gates data fetch on tab selection

**PASS.** Three hooks received `enabled` parameters:
- `useLearningReport(enabled)` -- gates both the list and detail queries
- `useLearningReports(startDate, endDate, enabled)` -- gates the reports list query
- `useConfigProposals(statusFilter, enabled)` -- gates the proposals query

In `LearningInsightsPanel`, all three are called with `isActive && enabled` as the enabled argument. The test at line 241-251 of the test file verifies that `isActive={false}` passes `false` to all three hooks.

**Note:** Because LearningInsightsPanel is only mounted when `activeTab === 'learning'` (conditional rendering in AnimatePresence), the `isActive` prop is redundant in the current architecture -- when the tab is not active, the component unmounts entirely, so hooks never execute. The `isActive` prop would only matter if the component were rendered but hidden (e.g., CSS display:none). This is belt-and-suspenders, not a bug.

**Separate concern:** `useConfigProposals('PENDING')` at PerformancePage line 109 runs unconditionally (regardless of active tab) to power the tab badge. The close-out acknowledges this as a deliberate judgment call. The query has a 60s stale time, making it a lightweight fetch. Acceptable.

### 3. Existing Performance tabs render identically (no layout regression)

**PASS.** The diff shows:
- No changes to OverviewTabContent, HeatmapsTabContent, DistributionTabContent, PortfolioTabContent, or ReplayTabContent
- PageHeader gained one new prop (`tabSegments`) but the rendering logic is identical -- `SegmentedTab` receives the same segments plus one additional entry
- All 10 existing PerformancePage tests pass (verified: 670/670 Vitest)
- The existing tests don't mock `useConfigProposals`, but this works because TanStack Query with `retry: false` returns undefined data, and `pendingProposalCount` falls back to 0 via `?? 0`

### 4. Empty and disabled states

**PASS.** Both states are implemented and tested:
- Disabled state (lines 95-108 of LearningInsightsPanel): renders when `enabled={false}`, shows "Learning Loop is disabled in config" with `data-testid="learning-disabled"`
- Empty state (lines 141-161): renders when `!activeReport`, shows the spec-required text "No analysis reports yet. Run your first analysis after a trading session." with `data-testid="learning-empty"` and a "Run Analysis" button
- Loading state (lines 111-121): skeleton placeholder with `data-testid="learning-loading"`
- Error state (lines 124-137): "Failed to load learning data" with retry button

## Code Quality Assessment

**TypeScript:** Zero compilation errors (verified via `npx tsc --noEmit`).

**Test coverage:** 7 new tests covering: render with data, empty state, disabled state, lazy loading verification, trigger analysis click, loading spinner, and data quality gaps display. All 670 Vitest tests pass.

**Component structure:** Clean composition -- LearningInsightsPanel delegates to WeightRecommendationCard and ThresholdRecommendationCard from S6a. Proposal lookup by field_path (useMemo) is efficient.

## Observations (Non-Blocking)

1. **Report selector is non-functional.** `selectedReportId` state is tracked (line 35) and the dropdown renders (line 183-198), but `activeReport` is always `latestReport` (line 63: `const activeReport: LearningReport | null = latestReport`). Changing the dropdown selection updates state but does not switch the displayed report. The close-out acknowledges this limitation. This is acceptable for V1 -- the selector will become functional when multiple reports exist and individual report fetching is needed.

2. **Redundant isActive prop.** As noted above, conditional rendering means the component unmounts when the tab is not active, making `isActive` redundant. Not harmful, but if the rendering pattern is ever changed to keep-alive (e.g., for preserving scroll position), the `isActive` prop would become essential. Keeping it is defensive.

3. **`pendingCount` naming collision.** `LearningInsightsPanel` line 166-167 computes `pendingCount` from recommendation arrays (weight + threshold counts), while PerformancePage line 110 uses `pendingProposalCount` from proposals query. These measure different things (recommendations vs proposals). No functional issue, but the naming could be clearer in a future pass.

## Regression Checklist (Session-Relevant Items)

| Check | Status |
|---|---|
| Performance page existing content renders correctly with Learning tab added | PASS |
| All Learning UI components render gracefully when `learning_loop.enabled: false` | PASS |
| All Learning UI components render gracefully when no reports exist | PASS |
| Full Vitest suite passes | PASS (670/670) |
| No test hangs | PASS |
| TypeScript compiles clean | PASS (0 errors) |

## Escalation Criteria Check

No escalation criteria triggered. This session is frontend-only (UI composition + hook modification). No config writes, no data mutations, no shutdown behavior changes, no mathematical computations.

## Files Reviewed

- `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/components/learning/LearningInsightsPanel.tsx` (NEW, 322 lines)
- `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/components/learning/LearningInsightsPanel.test.tsx` (NEW, 313 lines)
- `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/pages/PerformancePage.tsx` (MODIFIED)
- `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/hooks/useLearningReport.ts` (MODIFIED)
- `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/hooks/useConfigProposals.ts` (MODIFIED)
- `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/pages/PerformancePage.test.tsx` (existing, verified passing)

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": "HIGH",
  "summary": "Session 6b correctly implements the Learning Insights Panel and integrates it as a new Performance page tab per Amendment 14. All spec requirements met. Lazy loading via hook-level enabled parameters is correctly wired. Existing 5 tabs unmodified. 7 new tests, 670 total passing, 0 TypeScript errors.",
  "findings": [
    {
      "severity": "INFO",
      "description": "Report selector dropdown renders but does not switch displayed report (selectedReportId state unused). Acknowledged in close-out as V1 limitation.",
      "location": "LearningInsightsPanel.tsx:63"
    },
    {
      "severity": "INFO",
      "description": "isActive prop is redundant given conditional rendering (component unmounts when tab not active). Harmless defensive pattern.",
      "location": "PerformancePage.tsx:348"
    }
  ],
  "escalation_triggers": [],
  "tests_passed": true,
  "test_count": 670,
  "types_clean": true
}
```
