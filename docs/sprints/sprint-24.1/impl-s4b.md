# Sprint 24.1, Session 4b: Frontend Interactivity

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - Dashboard quality card components — find `QualityDistributionCard` and `SignalQualityPanel` (likely in `src/features/dashboard/`)
   - Dashboard page — find Positions table and Recent Trades table components
   - Orchestrator Recent Signals component — find RecentSignals (likely in `src/features/orchestrator/`)
   - `src/components/QualityBadge.tsx` — existing badge component pattern
   - `src/api/types.ts` — quality-related types, Signal types
   - `src/shared/quality.ts` or similar — GRADE_COLORS/GRADE_ORDER constants
2. Run the scoped test baseline:
   ```
   cd argus/ui && npm test -- --run
   ```
   Expected: all passing
3. Verify you are on branch `sprint-24.1`
4. Confirm `tsc --noEmit` exits 0

## Objective
Add interactivity to quality UI components: tooltips and legend on dashboard quality cards, quality badge column in Dashboard tables, and clickable signal rows in Orchestrator.

## Requirements

### Item 9: Dashboard Quality Card Interactivity (DEF-052)

1. **QualityDistributionCard (donut chart):**
   - Add Recharts `<Tooltip>` component to donut chart that shows on hover:
     - Grade name (e.g., "A+", "B-")
     - Count of signals with that grade
     - Percentage of total
   - Add `<Legend>` component below the donut showing all grade colors and labels
   - **Stretch (defer if not trivial):** Make donut segments clickable to filter signals by grade

2. **SignalQualityPanel (histogram):**
   - Add Recharts `<Tooltip>` to histogram bars that shows on hover:
     - Score range (e.g., "70-80")
     - Count of signals in that range
   - Use existing chart theming/color patterns

### Item 10: Quality Column in Dashboard Tables (DEF-053)

1. **Positions table on Dashboard:**
   - Add a "Quality" column showing `<QualityBadge grade={position.quality_grade} />`
   - Position where quality_grade is null/empty shows "—"
   - Use same QualityBadge component pattern as the Trades page

2. **Recent Trades table on Dashboard:**
   - Add a "Quality" column showing `<QualityBadge grade={trade.quality_grade} />`
   - Same null handling as above

### Item 11: Orchestrator Clickable Signal Rows (DEF-054)

1. **Create a signal detail component** (new file, e.g., `src/features/orchestrator/SignalDetailPanel.tsx`):
   - Expandable panel or modal that shows when a signal row is clicked
   - Content:
     - Quality grade badge (large)
     - Quality score (numerical)
     - Score breakdown by dimension (pattern_strength, catalyst_quality, volume_profile, historical_match, regime_alignment) — show each with a label and value
     - Entry price and stop price
     - Pattern strength (raw value from strategy)
     - Risk tier
   - Clean, card-like design consistent with existing panels

2. **Make RecentSignals rows clickable:**
   - Add click handler to each row
   - On click, expand/show the SignalDetailPanel for that signal
   - Only one detail panel open at a time (clicking another row switches)
   - Clicking the same row again collapses it

Note: The signal detail data must be available from the API. Check what the recent signals endpoint returns — if it doesn't include quality breakdown components, the detail panel shows only what's available and renders "—" for missing fields.

## Constraints
- Do NOT modify: backend Python files, API routes, API response shapes
- Do NOT change: existing chart configurations beyond adding tooltips/legend
- Do NOT add: new API endpoints or data fetching hooks (use existing data)
- Do NOT make: donut segments clickable unless it's trivially achievable within this session (stretch goal)
- Use existing QualityBadge component — do not create a new badge

## Visual Review
The developer should visually verify the following after this session:

1. **Dashboard donut chart:** Hovering over a segment shows tooltip with grade, count, percentage. Legend appears below chart with all grade colors.
2. **Dashboard histogram:** Hovering over a bar shows tooltip with score range and count.
3. **Dashboard Positions table:** Quality column shows colored badges for positions with quality data, "—" for positions without.
4. **Dashboard Recent Trades table:** Same as positions — quality badges where available.
5. **Orchestrator Recent Signals:** Clicking a row expands a detail panel below it showing quality breakdown. Clicking another row switches. Clicking same row collapses.
6. **Mobile rendering:** All new elements render acceptably on mobile width.

Verification conditions:
- Run `npm run dev` in `argus/ui/`
- Load sample data (seed script + quality history seed if available)
- Check at desktop and mobile widths

## Test Targets
After implementation:
- Vitest: all existing tests pass
- New tests:
  1. SignalDetailPanel renders with quality data
  2. SignalDetailPanel renders with partial/missing data (graceful "—")
  3. QualityBadge in Positions table renders (snapshot or render test)
- Minimum new test count: 3
- Test command: `cd argus/ui && npm test -- --run`

## Definition of Done
- [ ] Donut chart has tooltips and legend
- [ ] Histogram has tooltips
- [ ] Dashboard Positions table has quality column
- [ ] Dashboard Recent Trades table has quality column
- [ ] Signal rows are clickable with detail panel
- [ ] Detail panel shows quality breakdown
- [ ] Null/missing quality handled gracefully
- [ ] All Vitest tests pass
- [ ] `tsc --noEmit` still exits 0
- [ ] Visual review items verified
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Dashboard loads without error | Navigate to /dashboard — no console errors |
| Orchestrator loads without error | Navigate to /orchestrator — signals visible |
| Existing chart behavior preserved | Donut and histogram still show data correctly (tooltips are additive) |
| `tsc --noEmit` still clean | `cd argus/ui && npx tsc --noEmit -p tsconfig.app.json` exits 0 |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file:**
`docs/sprints/sprint-24.1/session-4b-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.1/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.1/session-4b-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped — non-final session):
   ```
   cd argus/ui && npm test -- --run
   ```
5. Files that should NOT have been modified:
   - Any Python files
   - `src/api/types.ts`
   - Orchestrator layout (that was Session 4a)
   - Debrief/Performance tabs (that was Session 4a)

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-24.1/session-4b-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **Recharts Tooltip integration:** Verify tooltips use Recharts' `<Tooltip>` component, not custom hover handlers.
2. **Donut Legend:** Verify legend uses consistent grade colors from shared constants (GRADE_COLORS).
3. **QualityBadge reuse:** Verify Dashboard tables use the existing `QualityBadge` component, not a reimplementation.
4. **Null handling:** Verify positions/trades with null quality_grade show "—" (not broken badge or error).
5. **SignalDetailPanel data access:** Verify detail panel reads from existing API data — no new fetch calls.
6. **Click behavior:** Verify only one detail panel opens at a time. Re-clicking collapses.
7. **TypeScript compliance:** Verify `tsc --noEmit` still exits 0. New components properly typed.
8. **No new API calls:** Verify no new `useQuery` hooks or fetch calls were added.

## Visual Review (for @reviewer)
The developer should visually verify:
1. **Donut tooltips:** Hover shows grade, count, percentage
2. **Donut legend:** All grade colors shown with labels
3. **Histogram tooltips:** Hover shows score range and count
4. **Dashboard Positions:** Quality column with badges
5. **Dashboard Recent Trades:** Quality column with badges
6. **Orchestrator signals:** Click row → detail panel expands
7. **Signal detail panel:** Shows grade, score, breakdown, prices
8. **Mobile:** All elements render without overflow

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Order Manager position lifecycle unchanged
- [ ] TradeLogger handles quality-present and quality-absent trades
- [ ] Schema migration idempotent, no data loss
- [ ] Quality engine bypass path intact
- [ ] All pytest pass (full suite with `-n auto`)
- [ ] All Vitest pass
- [ ] TypeScript build clean (`tsc --noEmit` exits 0)
- [ ] API response shapes unchanged
- [ ] Frontend renders without console errors

## Sprint-Level Escalation Criteria (for @reviewer)
### Critical (Halt immediately)
1. Vitest tests fail after UI changes

### Warning (Proceed with caution, document)
2. Signal detail data not available from API — show partial detail, document gaps
3. Mobile rendering issues — document and defer
