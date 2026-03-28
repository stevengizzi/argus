# Sprint 28, Session 6c: Frontend — Strategy Health Bands + Correlation Matrix + Dashboard Card

## Pre-Flight Checks
1. Read: S6a hooks (`useLearningReport`, `useConfigProposals`), Performance page (post-S6b), Dashboard page, existing Recharts usage patterns in the codebase
2. Run: `cd argus/ui && npm test` (S6a+S6b tests passing)
3. Verify correct branch, S6b merged

## Objective
Build the three remaining frontend components: Strategy Health Bands, Correlation Matrix (both on Performance Learning tab), and Dashboard summary card.

## Requirements

1. **Create `argus/ui/src/components/learning/StrategyHealthBands.tsx`:**
   - Per-strategy horizontal bar showing trailing Sharpe, win rate, expectancy
   - Color encoding: green (above baseline), amber (near baseline), red (below baseline)
   - Baseline values from LearningReport data (or strategy config benchmarks as fallback)
   - Tooltip on hover: exact values + number of trades in window
   - Purely observational — NO throttle/boost action buttons (deferred to Sprint 40)
   - Empty state: "Strategy health data will appear after the first analysis"

2. **Create `argus/ui/src/components/learning/CorrelationMatrix.tsx`:**
   - Recharts-based heatmap (or custom SVG if Recharts heatmap is insufficient)
   - Strategy names on both axes
   - Color scale: blue (negative correlation) → white (zero) → red (positive correlation)
   - Flagged pairs (>threshold) highlighted with border/icon
   - Excluded strategies shown as grey cells
   - Tooltip: exact correlation value, trade overlap count
   - If only 1 strategy: show "Requires 2+ strategies" message

3. **Create `argus/ui/src/components/learning/LearningDashboardCard.tsx`:**
   - Compact card for Dashboard page
   - Shows: pending recommendations count, last analysis timestamp, data quality indicator (sufficient/collecting/sparse — based on data quality preamble)
   - "View Insights" link navigating to Performance page Learning tab
   - Gracefully hidden when `learning_loop.enabled: false`

4. **Modify Performance page:** Add StrategyHealthBands and CorrelationMatrix to the Learning tab (below LearningInsightsPanel from S6b)

5. **Modify Dashboard page:** Add LearningDashboardCard to appropriate position (near other intelligence/status cards)

## Constraints
- Do NOT modify existing Dashboard cards or Performance tab content
- Do NOT add throttle/boost actions to health bands (Sprint 40)
- Correlation Matrix colors must be accessible (not red-green only — use blue-red scale)

## Test Targets
- Vitest: StrategyHealthBands render with mock data, CorrelationMatrix render, DashboardCard render with pending count, empty states, disabled state (hidden card)
- Minimum: 6 Vitest tests
- Test command: `cd argus/ui && npm test` (FULL Vitest suite — this is the final frontend session)

## Visual Review
After implementation, visually verify:
1. Performance Learning tab: Health Bands render per strategy with correct colors
2. Performance Learning tab: Correlation Matrix renders with 7 strategies (or available data)
3. Dashboard: Learning card shows pending count and links to Performance
4. Dashboard: Card hidden when learning_loop disabled
5. Overall: no visual regression on existing Performance or Dashboard content

Verification conditions: Backend running with learning loop enabled and at least one report generated.

## Definition of Done
- [ ] StrategyHealthBands with color-coded bars (observational only)
- [ ] CorrelationMatrix heatmap with flagged pairs
- [ ] LearningDashboardCard with pending count + link
- [ ] All components on correct pages
- [ ] Graceful disabled/empty states
- [ ] ≥6 Vitest tests
- [ ] Full Vitest suite passes (final frontend session)
- [ ] Close-out to `docs/sprints/sprint-28/session-6c-closeout.md`
- [ ] @reviewer — FULL Vitest suite (final session): `cd argus/ui && npm test`
- [ ] @reviewer — FULL pytest suite (final session): `python -m pytest --ignore=tests/test_main.py -n auto -q`

## Session-Specific Review Focus (for @reviewer)
1. Verify health bands are observational only (no throttle/boost actions)
2. Verify correlation matrix uses accessible color scale (blue-red, not red-green)
3. Verify Dashboard card hidden when disabled
4. Verify no layout regression on existing Dashboard and Performance content
5. **Full suite verification (final session):** Run both full pytest and full Vitest

## Sprint-Level Regression Checklist / Escalation Criteria
*(See review-context.md)*
