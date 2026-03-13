# Sprint 24, Session 11: Frontend — Performance + Debrief Quality Charts

## Pre-Flight Checks
1. Read: Performance page, Debrief page, useQuality.ts hooks, Recharts/D3 usage patterns in codebase
2. Scoped test: `cd argus/ui && npx vitest run`
3. Branch: `sprint-24`

## Objective
Add "by quality grade" performance chart to Performance page. Add quality vs. outcome scatter plot to The Debrief.

## Requirements

### 1. Performance page — QualityGradeChart.tsx:
- Grouped bar chart: X-axis = quality grades (A+ through C+), bars for avg PnL, win rate, avg R-multiple
- Uses `useQualityHistory()` with date range from page's existing date filter
- Groups results by grade, computes aggregates client-side
- Grades with no data: show empty bar (not missing)
- Recharts BarChart with grade-colored bars

### 2. Debrief page — QualityOutcomeScatter.tsx:
- Scatter plot: X = composite quality score (0–100), Y = outcome R-multiple
- Each dot colored by grade (matching QualityBadge colors)
- Trend line overlay (simple linear regression client-side)
- Uses `useQualityHistory()` filtering to records with non-null outcome_r_multiple
- Empty state: "Quality vs. outcome data will appear after trades close with quality scoring active"
- D3 or Recharts ScatterChart

## Visual Review
1. **Performance chart**: Grouped bars visible with grade coloring, handles partial data
2. **Performance empty**: Shows meaningful empty state when no quality data
3. **Debrief scatter**: Points plotted with correct axes, trend line visible when enough data
4. **Debrief empty**: Informative empty state message
5. **Both charts**: Responsive, readable at different viewport sizes

Verification conditions: For scatter plot with data: requires trades that have been scored AND closed (outcome columns populated). During initial paper trading, scatter will show empty state — verify empty state rendering.

## Test Targets
- `test_quality_grade_chart_renders`: Chart with mock data shows bars
- `test_quality_grade_chart_aggregation`: Correctly groups by grade
- `test_quality_grade_chart_empty_grades`: Missing grades show empty bars
- `test_quality_grade_chart_empty_data`: Shows empty state
- `test_quality_outcome_scatter_renders`: Scatter with mock data
- `test_quality_outcome_scatter_coloring`: Dots colored by grade
- `test_quality_outcome_scatter_trend_line`: Linear trend line present
- `test_quality_outcome_scatter_empty`: Empty state message when no outcomes
- `test_performance_page_integration`: Chart appears in Performance page
- `test_debrief_page_integration`: Scatter appears in Debrief page
- Minimum: 10 Vitest
- Test command (final session — full suite): `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Performance "by grade" chart rendering
- [ ] Debrief scatter plot rendering
- [ ] Empty states for both
- [ ] Visual review items verified
- [ ] 10+ Vitest tests
- [ ] All 446+ existing Vitest pass

## Close-Out
Write report to `docs/sprints/sprint-24/session-11-closeout.md`.

