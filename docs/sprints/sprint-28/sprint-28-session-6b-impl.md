# Sprint 28, Session 6b: Frontend — Learning Insights Panel + Performance Page Integration

## Pre-Flight Checks
1. Read: S6a components (WeightRecommendationCard, ThresholdRecommendationCard, hooks), `argus/ui/src/pages/Performance.tsx` (or equivalent — current Performance page layout)
2. Run: `cd argus/ui && npm test` (S6a tests passing)
3. Verify correct branch, S6a merged

## Objective
Build the Learning Insights Panel that composes the recommendation cards, and integrate it into the Performance page as a new "Learning" tab (Amendment 14).

## Requirements

1. **Create `argus/ui/src/components/learning/LearningInsightsPanel.tsx`:**
   - Composes WeightRecommendationCard list + ThresholdRecommendationCard list
   - Data quality preamble section: trading days, sample sizes, known gaps
   - "Run Analysis" button (triggers useTriggerAnalysis mutation, shows loading state)
   - Last analysis timestamp display
   - Empty state: "No analysis reports yet. Run your first analysis after a trading session."
   - Disabled state: "Learning Loop is disabled in config" (when learning_loop.enabled: false)
   - Report selector: dropdown to view historical reports (defaults to latest)
   - Per-regime toggle: checkbox to show regime-conditional breakdown (collapsed by default)

2. **Modify Performance page:**
   - **New "Learning" tab (Amendment 14):** Add tab alongside existing Performance tabs
   - Learning tab content: LearningInsightsPanel
   - **Lazy loading:** TanStack Query `enabled` flag tied to tab active state — learning data only fetched when tab is selected
   - Tab badge: show pending recommendation count on tab label

## Constraints
- Do NOT modify existing Performance page tabs or their content
- Do NOT create StrategyHealthBands, CorrelationMatrix, or Dashboard card (S6c)
- Learning tab data fetch MUST be gated by tab selection (Amendment 14 — prevent page load regression)

## Test Targets
- Vitest: LearningInsightsPanel render with mock report data, empty state render, disabled state render, tab lazy loading verification
- Minimum: 4 Vitest tests
- Test command: `cd argus/ui && npm test`

## Visual Review
After implementation, visually verify:
1. Performance page shows new "Learning" tab alongside existing tabs
2. Tab badge shows pending count (e.g., "Learning (3)")
3. LearningInsightsPanel renders with sample data showing weight + threshold recommendations
4. Empty state displays when no reports exist
5. "Run Analysis" button shows loading spinner during trigger

Verification conditions: Backend running with learning loop enabled. If no real data, verify empty state renders correctly.

## Definition of Done
- [ ] LearningInsightsPanel composes recommendation cards
- [ ] Performance page has "Learning" tab (Amendment 14)
- [ ] Lazy loading: data only fetched when tab active
- [ ] Tab badge shows pending count
- [ ] Empty and disabled states
- [ ] ≥4 Vitest tests
- [ ] Close-out to `docs/sprints/sprint-28/session-6b-closeout.md`
- [ ] @reviewer with review context

## Session-Specific Review Focus (for @reviewer)
1. Verify Learning is a new TAB, not added to main Performance view (Amendment 14)
2. Verify TanStack Query `enabled` flag gates data fetch on tab selection
3. Verify existing Performance tabs render identically (no layout regression)
4. Verify empty/disabled states

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
