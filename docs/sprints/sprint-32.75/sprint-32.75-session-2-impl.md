# Sprint 32.75, Session 2: Dashboard Overhaul

## Pre-Flight Checks
1. Read context:
   - `docs/sprints/sprint-32.75/review-context.md`
   - `argus/ui/src/pages/DashboardPage.tsx`
   - `argus/ui/src/features/dashboard/VixRegimeCard.tsx`
   - `argus/ui/src/features/dashboard/OpenPositions.tsx`
2. Run scoped tests: `cd argus/ui && npx vitest run src/pages/DashboardPage.test.tsx src/features/dashboard/`
3. Branch: `sprint-32.75-session-2`
4. Confirm S1 merged (strategy identity constants available)

## Objective
Streamline the Dashboard by removing low-value cards, repositioning remaining cards for better information hierarchy, and redesigning the VIX Regime card.

## Requirements

1. In `DashboardPage.tsx` (all 3 responsive layouts — phone, tablet, desktop):
   - Remove `<RecentTrades />` and `<HealthMini />` components and their grid wrappers
   - In the desktop 3-card row currently showing "Today's Stats | Session Timeline | AI Insight", change to "Today's Stats | Session Timeline | Signal Quality"
   - Move AI Insight to the position vacated by the removed cards (or into the below-fold row with Universe Status and Learning)
   - Remove the imports for RecentTrades and HealthMini

2. In `OpenPositions.tsx`: Move the All/Open/Closed tab toggle from its own row into the card header — inline with the "POSITIONS" title and the position count. The toggle should be right-aligned in the header.

3. In `VixRegimeCard.tsx`: Redesign from full-width row to a compact card. Show VIX close value (large), VRP tier badge, vol regime phase, and momentum direction arrow in a single horizontal layout. If VIX history data is available, add a 5-day sparkline. The card should fit comfortably in a 1/3-width column rather than spanning full width.

4. In `DashboardPage.tsx`: Move VixRegimeCard into the Account/DailyPnl/GoalTracker row (making it a 4-card row) or into its own smaller position. It should NOT occupy a full-width row.

## Constraints
- Do NOT modify any Orchestrator, Performance, Trades, or other page files
- Do NOT remove RecentTrades.tsx or HealthMini.tsx files — just remove them from DashboardPage imports/render
- Do NOT change any API endpoints or data fetching logic
- Maintain all 3 responsive layouts (phone/tablet/desktop)

## Test Targets
- Update DashboardPage.test.tsx to reflect removed components and new layout
- Test VixRegimeCard compact layout
- Minimum new/updated tests: 5
- Command: `cd argus/ui && npx vitest run src/pages/DashboardPage.test.tsx src/features/dashboard/`

## Visual Review
1. **Desktop layout**: No Recent Trades or System Status cards. VIX card compact. Signal Quality in 3-card row. AI Insight below fold.
2. **Tablet layout**: Same card removals. Layout still balanced.
3. **Phone layout**: Cards stacked correctly without gaps from removed cards.
4. **Positions card**: All/Open/Closed toggle inline with header — no extra vertical space.
5. **VIX card**: Compact, showing VIX close + phase + momentum in one row. Not spanning full width.

Verification conditions: App running during market hours (or with mock data showing VIX data)

## Definition of Done
- [ ] RecentTrades and HealthMini removed from all 3 layouts
- [ ] Signal Quality and AI Insight positions swapped
- [ ] OpenPositions toggle inline with header
- [ ] VixRegimeCard redesigned and repositioned
- [ ] All 3 responsive layouts tested
- [ ] Close-out report written to `docs/sprints/sprint-32.75/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Dashboard still renders in all 3 layouts | Visual check at 375px, 768px, 1440px widths |
| Positions card data unchanged | Open/closed counts match API response |
| Other dashboard cards unaffected | Account, DailyPnl, GoalTracker, SessionTimeline render correctly |

## Close-Out
Write to: `docs/sprints/sprint-32.75/session-2-closeout.md`

## Tier 2 Review
Invoke @reviewer with review context at `docs/sprints/sprint-32.75/review-context.md`, test command: `cd argus/ui && npx vitest run src/pages/DashboardPage.test.tsx src/features/dashboard/`. Files NOT to modify: any Python files, Orchestrator/Performance/Trades page files.

## Session-Specific Review Focus
1. Verify RecentTrades and HealthMini are removed from ALL THREE responsive layouts (phone, tablet, desktop) — easy to miss one
2. Verify VixRegimeCard no longer spans full width in any layout
3. Verify no dead imports remain in DashboardPage.tsx
