# Sprint 24, Session 10: Frontend — Orchestrator + Dashboard Quality Panels

## Pre-Flight Checks
1. Read: Orchestrator page, Dashboard page, QualityBadge.tsx (from Session 9), useQuality.ts hooks
2. Scoped test: `cd argus/ui && npx vitest run`
3. Branch: `sprint-24`

## Objective
Add live quality scores to Orchestrator. Add quality distribution mini-card, Signal Quality Distribution panel, and filtered signals counter to Dashboard.

## Requirements

### 1. Dashboard additions:

**QualityDistributionCard.tsx** — Mini-card for dashboard grid:
- Donut/pie chart showing grade distribution using `useQualityDistribution()`
- Color segments matching QualityBadge colors
- Center text: total scored signals count
- Empty state: "No quality data yet"

**SignalQualityPanel.tsx** — Larger panel:
- Grade histogram (bar chart) using Recharts
- Each bar colored by grade
- Shows count per grade
- Below chart: "Signals today: N passed / M filtered" text

### 2. Orchestrator additions:
- Recent signals section using `useQualityHistory({ limit: 10 })`
- Each signal row shows: symbol, strategy, QualityBadge, timestamp
- Auto-refreshes on interval (match existing Orchestrator polling pattern)

## Visual Review
1. **Dashboard mini-card**: Donut chart with grade-colored segments visible in dashboard grid
2. **Dashboard panel**: Histogram bars with correct colors, filtered counter visible
3. **Dashboard empty state**: "No quality data yet" when no signals scored
4. **Orchestrator signals**: Recent signals list with quality badges
5. **Orchestrator empty state**: "No recent signals" message

Verification conditions: App in dev mode. For populated data: after paper trading session with quality engine active, or with manually inserted quality_history test rows.

## Test Targets
- `test_quality_distribution_card_renders`: Card renders with mock data
- `test_quality_distribution_card_empty`: Shows empty state message
- `test_signal_quality_panel_histogram`: Bars render per grade
- `test_signal_quality_panel_filtered_count`: "N passed / M filtered" text
- `test_orchestrator_recent_signals_renders`: Signal rows with badges
- `test_orchestrator_recent_signals_empty`: Empty state message
- `test_dashboard_quality_card_integration`: Card appears in dashboard grid
- `test_orchestrator_quality_integration`: Signals section in orchestrator page
- Minimum: 10 Vitest
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Dashboard mini-card and panel rendering
- [ ] Orchestrator recent signals with quality badges
- [ ] Empty states handled
- [ ] Visual review items verified
- [ ] 10+ Vitest tests

## Close-Out
Write report to `docs/sprints/sprint-24/session-10-closeout.md`.

