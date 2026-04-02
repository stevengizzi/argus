# Sprint 32.8, Session 2: Dashboard Layout Refactor

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/DashboardPage.tsx`
   - `argus/ui/src/features/dashboard/` (directory listing, then key components)
   - `argus/ui/src/hooks/useDashboardSummary.ts`
   - `argus/ui/src/components/learning/LearningDashboardCard.tsx`
2. Run scoped test baseline:
   Vitest: `cd argus/ui && npx vitest run src/pages/DashboardPage`
   Expected: all passing
3. Verify you are on the correct branch: `main`

## Objective
Refactor the Dashboard into a dense 4-row layout that shows the primary operational workflow (vitals, allocation, positions + timeline + signal quality) without scrolling on a 1080p display.

## Requirements

### 1. Create VitalsStrip component (`argus/ui/src/features/dashboard/VitalsStrip.tsx`)

A single horizontal strip (~80–100px height) that consolidates:
- **Account Equity** — large number, with cash + buying power in smaller text beneath
- **Daily P&L** — large colored number with sparkline, trade count below
- **Today's Stats** — trades count, win rate, avg R, best trade (currently a separate card)
- **VIX / Regime** — VIX number + regime badge (Bearish/Bullish/etc.)

Use a flexbox row with 4 sections. No card borders — use subtle vertical dividers or spacing. Match the existing dark theme. Pull data from the same hooks the current cards use (`useDashboardSummary`, VIX hook, etc.).

### 2. Refactor DashboardPage layout (`argus/ui/src/pages/DashboardPage.tsx`)

Replace the current layout with:

**Row 1:** VitalsStrip (full width, ~80-100px)
**Row 2:** Strategy allocation bar (full width, ~40px — keep existing component as-is)
**Row 3:** Two-column layout:
- Left column (70%): Positions table (existing component, full height of row)
- Right column (30%): Session Timeline (top 50%) + Signal Quality (bottom 50%), stacked vertically
**Row 4:** Two-column layout:
- Left column (50%): AI Insight card
- Right column (50%): Learning Loop card
- Both must have matching heights (use CSS grid or flexbox with `align-items: stretch`)

**Remove from Dashboard:** Monthly Goal card, Universe card. Do NOT delete the components — they may be used on other pages. Simply stop rendering them on the Dashboard.

### 3. Reposition All/Open/Closed toggle

In the positions table section, move the All/Open/Closed filter toggle from right-aligned to left-aligned, positioned immediately after the "POSITIONS" header text. The table/timeline view toggle stays right-aligned.

### 4. Responsive considerations

- On viewports < 1024px, Row 3 should stack (positions full width, then timeline, then signal quality)
- Row 4 should stack on mobile (AI Insight full width, then Learning Loop)
- VitalsStrip should wrap gracefully on narrow viewports

## Constraints
- Do NOT modify: any Python backend files, any non-Dashboard frontend files
- Do NOT delete: Monthly Goal or Universe card components (just stop rendering them on Dashboard)
- Do NOT change: the data hooks or API calls — only the layout and positioning
- Do NOT change: any component's internal rendering (e.g., SessionTimeline stays the same, just repositioned)

## Visual Review
The developer should visually verify the following after this session:
1. **VitalsStrip**: Shows equity, daily P&L with sparkline, today's stats (trades/win rate/avg R/best trade), VIX + regime badge — all in one horizontal strip
2. **Row 3**: Positions table takes ~70% width, Session Timeline + Signal Quality stacked on the right ~30%
3. **Row 4**: AI Insight and Learning Loop side by side with matched heights
4. **No scroll**: Rows 1–3 visible without scrolling on 1080p (1920×1080) display
5. **Toggle position**: All/Open/Closed toggle is left-aligned next to "POSITIONS" header
6. **Monthly Goal and Universe**: NOT visible on Dashboard
7. **Mobile**: Layout stacks gracefully on narrow viewport (resize browser to ~400px width)

Verification conditions:
- ARGUS running with live data on port 8000
- Vite dev server on port 5175
- At least a few open positions for the positions table

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_vitals_strip_renders_equity` — VitalsStrip shows account equity
  2. `test_vitals_strip_renders_daily_pnl` — VitalsStrip shows daily P&L
  3. `test_vitals_strip_renders_todays_stats` — trade count, win rate present
  4. `test_dashboard_no_monthly_goal` — Monthly Goal card not in DOM
  5. `test_dashboard_no_universe_card` — Universe card not in DOM
- Minimum new test count: 5
- Test command: `cd argus/ui && npx vitest run src/pages/DashboardPage src/features/dashboard/`

## Definition of Done
- [ ] VitalsStrip created with equity, P&L, today's stats, VIX/regime
- [ ] Dashboard uses 4-row layout (VitalsStrip → Allocation → Positions+Timeline+Quality → AI+Learning)
- [ ] Row 3 is 70/30 split with stacked Timeline/Quality on right
- [ ] Row 4 has matched-height AI Insight and Learning Loop
- [ ] Monthly Goal and Universe removed from Dashboard
- [ ] All/Open/Closed toggle repositioned left
- [ ] No scroll needed for Rows 1–3 on 1080p
- [ ] Responsive stacking on mobile
- [ ] All existing tests pass
- [ ] 5+ new tests passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All Dashboard data still accessible | Visual check: equity, P&L, positions, timeline, quality, AI insight, learning loop all render |
| Positions table fully functional | Sort, filter, All/Open/Closed toggle, row click all work |
| Strategy allocation bar unchanged | Visual check: colored bars with strategy labels |
| No Python files modified | `git diff --name-only` shows only UI files |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

**Write the close-out report to a file:**
docs/sprints/sprint-32.8/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32.8/review-context.md`
2. Close-out report: `docs/sprints/sprint-32.8/session-2-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `cd argus/ui && npx vitest run src/pages/DashboardPage src/features/dashboard/`
5. Files that should NOT have been modified: any Python files, any non-Dashboard UI files

## Session-Specific Review Focus (for @reviewer)
1. Verify Monthly Goal and Universe components are NOT deleted, just not rendered on Dashboard
2. Verify VitalsStrip consumes existing hooks (no new API calls)
3. Verify positions table retains all interactivity (sort, filter, toggle, row click)
4. Verify Row 3 layout uses CSS grid or flexbox (not absolute positioning)
5. Verify responsive breakpoint stacks gracefully (check Tailwind responsive classes)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`
