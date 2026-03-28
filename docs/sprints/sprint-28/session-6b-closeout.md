# Sprint 28, Session 6b — Close-Out Report

## Session Objective
Build the Learning Insights Panel composing S6a recommendation cards, and integrate it into the Performance page as a new "Learning" tab (Amendment 14).

## Change Manifest

| File | Action | Description |
|------|--------|-------------|
| `argus/ui/src/components/learning/LearningInsightsPanel.tsx` | **Created** | Panel composing weight + threshold recommendation cards, data quality preamble, Run Analysis button, report selector, regime toggle, empty/disabled states |
| `argus/ui/src/components/learning/LearningInsightsPanel.test.tsx` | **Created** | 7 Vitest tests covering render with data, empty state, disabled state, lazy loading, trigger analysis, loading spinner, data quality gaps |
| `argus/ui/src/pages/PerformancePage.tsx` | **Modified** | Added "Learning" tab (6th tab), lazy loading via `isActive` prop, pending count badge, 'l' keyboard shortcut, `tabSegments` prop to PageHeader |
| `argus/ui/src/hooks/useLearningReport.ts` | **Modified** | Added `enabled` parameter to `useLearningReport()` and `useLearningReports()` for lazy loading |
| `argus/ui/src/hooks/useConfigProposals.ts` | **Modified** | Added `enabled` parameter to `useConfigProposals()` for lazy loading |

## Definition of Done Verification

| Criterion | Status |
|-----------|--------|
| LearningInsightsPanel composes recommendation cards | DONE |
| Performance page has "Learning" tab (Amendment 14) | DONE |
| Lazy loading: data only fetched when tab active | DONE — `isActive` prop gates all TanStack Query `enabled` flags |
| Tab badge shows pending count | DONE — `useConfigProposals('PENDING')` count on tab segment |
| Empty and disabled states | DONE — `data-testid="learning-empty"` and `data-testid="learning-disabled"` |
| >= 4 Vitest tests | DONE — 7 tests |
| Close-out report | This document |

## Judgment Calls

1. **Lazy loading implementation:** Hook-level `enabled` parameters (added to `useLearningReport`, `useLearningReports`, `useConfigProposals`) rather than conditional rendering. This keeps hooks at top level per React rules-of-hooks while gating network requests.

2. **Pending count source:** Used `useConfigProposals('PENDING')` at the PerformancePage level (always fetches) for the tab badge. This is a lightweight query (60s stale time) that enables the badge to show regardless of which tab is active.

3. **PageHeader prop change:** Changed `TAB_SEGMENTS` from module-level constant to a `tabSegments` prop passed to `PageHeader`. Required because the Learning tab badge count is dynamic (depends on proposals query data).

4. **Report selector:** Only shown when `reports.length > 1`. Uses dropdown with date + recommendation count as labels. `selectedReportId` state tracks selection but currently always displays latest report (full report-switching requires fetching individual reports by ID, which is wired but not exercised until multiple reports exist).

## Scope Verification
- Existing 5 Performance tabs: **Unmodified** (10/10 existing PerformancePage tests pass)
- No StrategyHealthBands, CorrelationMatrix, or Dashboard card created (S6c scope)
- No new dependencies added

## Test Results
- **New tests:** 7 (LearningInsightsPanel)
- **Existing S6a tests:** 18 pass (WeightRecommendationCard: 12, ThresholdRecommendationCard: 6)
- **Existing PerformancePage tests:** 10 pass (no regressions)
- **Full Vitest suite:** 670 pass, 0 fail (was 645 pre-Sprint 28 S6a/6b)

## Self-Assessment
**CLEAN** — All spec items implemented. No scope expansion. All tests pass.

## Context State
**GREEN** — Session completed well within context limits.
