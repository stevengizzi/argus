# Sprint 32.8, Session 6g: Trades Unification + Dashboard Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files:
   - `argus/ui/src/features/trades/ShadowTradesTab.tsx`
   - `argus/ui/src/features/trades/TradeFilters.tsx`
   - `argus/ui/src/features/trades/TradeTable.tsx`
   - `argus/ui/src/features/trades/TradeStatsBar.tsx`
   - `argus/ui/src/features/dashboard/VitalsStrip.tsx`
   - `argus/ui/src/stores/tradeFilters.ts` (for `computeDateRangeForQuickFilter`)
   - `argus/ui/src/hooks/useShadowTrades.ts`
2. Kill orphaned Vitest workers:
   `pkill -f "vitest/dist/workers" 2>/dev/null; echo "Cleaned"`
3. Run scoped baseline:
   `cd argus/ui && npx vitest run src/features/trades/ src/pages/TradesPage src/features/dashboard/VitalsStrip`

## Objective
Fix remaining visual consistency between Live and Shadow Trades tabs, fix Shadow Trades
time preset bugs, and correct the Dashboard trades count data source.

## Requirements

### 1. Dashboard trades count — fix data source direction (VitalsStrip.tsx)

S6f aligned both Dashboard trade counts to `todayStats.trade_count`, which is capped at 1000.
This was the wrong direction. Fix:

- In the Today's Stats section of VitalsStrip, change the Trades value to use
  `accountData.daily_trades_count` (or whatever field provides the uncapped count)
  instead of `todayStats.trade_count`.
- The Daily P&L section should also use this uncapped source.
- Both sections must show the same number, and it must match what the Trades page shows.
- Update the VitalsStrip test that asserts `'7'` from `trade_count: 7` — change it to
  use the corresponding field from the account data mock, or adjust the mock to provide
  the uncapped value.

### 2. Shadow Trades — time preset "Today" shows no trades (BUG)

When clicking "Today", no trades appear even though trades exist with Entry Time
"4/2/2026 12:00 PM" etc. The likely cause is a timezone mismatch: `computeDateRangeForQuickFilter`
probably computes UTC midnight boundaries (e.g., `2026-04-02T00:00:00Z` to `2026-04-02T23:59:59Z`)
but the backend stores/filters entry times in ET, or the API expects date strings in a
different format.

Debug this by:
1. Check what `computeDateRangeForQuickFilter('today')` actually returns
2. Check what the Shadow Trades API (`GET /api/v1/counterfactual/positions`) expects for
   date filter params — are they ISO strings? Date-only strings? What timezone?
3. Fix the mismatch so "Today" correctly shows today's trades

### 3. Shadow Trades — double-click on time preset clears all trades (BUG)

Clicking a time preset that is already active should be a no-op, not toggle it off.
Currently it likely sets the quick filter to `null`/`undefined`, which resets the date range
and offset, causing an empty response.

Fix: in the click handler for time presets, if the clicked preset is already the active one,
return early (no-op). Do NOT toggle it off.

### 4. Live Trades and Shadow Trades — identical filter bar layout

The two tabs must have the **exact same visual structure** for their filter bars.
Currently Live Trades has a multi-row layout with differently-sized controls, and Shadow
Trades has a single-row flex-wrap.

**Target layout (ONE row, flex-wrap, for BOTH tabs):**

```
Strategy ▼ | [Rejection Stage ▼] | All Wins Losses BE | Today Week Month All | From [____] To [____] | [× Clear]
```

Where `[Rejection Stage ▼]` only appears on Shadow Trades (Live Trades skips it).

Implementation approach:
- Extract a shared filter bar component OR make both tabs use identical Tailwind classes
  and layout structure
- ALL controls must have the same height. Currently the Strategy dropdown, the Outcome
  segmented toggle, the time preset buttons, and the date pickers all have different heights.
  Standardize: every control should be `h-8` (32px) or `h-9` (36px) — pick one and apply to
  ALL of them. This means:
  - Strategy `<select>`: set explicit `h-8` (or `h-9`)
  - Rejection Stage `<select>`: same height
  - Outcome SegmentedTab buttons: same height
  - Time preset buttons: same height
  - Date `<input>` fields: same height
- Container: `flex flex-wrap items-center gap-2 px-4 py-2 bg-argus-surface-2/50`
- Labels ("STRATEGY", "OUTCOME", etc.) should appear above their controls on Live Trades
  just as they do now, OR be removed from both — pick one approach and apply consistently.
  I recommend removing standalone labels and using placeholder text or built-in labels
  within the controls instead, which is how Shadow Trades currently works.

### 5. Live Trades and Shadow Trades — identical stats bar

Both tabs should use the same stats bar component or identical styling:
- Same background color
- Same padding
- Same font sizes for metric labels and values
- Same layout (4 evenly-spaced metric columns)

Currently the Live Trades stats bar looks different from Shadow's. Make them match —
adopt Shadow Trades' styling (darker background, more compact).

### 6. Live Trades and Shadow Trades — identical table formatting

The tables should have identical styling for shared structural elements:
- Same row height (adopt Shadow's compact `py-2`)
- Same header row styling (background, font size, font weight)
- Same text alignment patterns
- Same cell padding

The columns will differ between the tabs (Live has different columns than Shadow), but
where columns overlap (Symbol, Strategy, Entry, P&L, R-Multiple) the formatting should
be identical.

## Constraints
- Do NOT modify any Python backend files
- Do NOT change data fetching logic or API calls (except fixing date filter values)
- Do NOT change the Shadow Trades infinite scroll behavior
- Do NOT remove any existing functionality from either tab
- PRESERVE all test IDs on existing elements

## Visual Review
After all fixes, verify:
1. **Dashboard**: Both trade count displays show the same number, matching the Trades page count
2. **Shadow Trades "Today"**: Shows today's trades correctly
3. **Shadow Trades double-click**: Clicking "Today" twice does NOT clear the table
4. **Filter bar**: Both tabs have identical control heights, same one-row layout, same background
5. **Stats bar**: Both tabs have identical metric bar styling
6. **Table**: Both tabs have identical row height, header styling, and cell padding
7. **Overall**: Switching between tabs should feel like switching data, not switching to a different app

Verification conditions:
- ARGUS running with live data and trade history
- Vite dev server on port 5175
- Test both tabs with "Today" filter active

## Test Targets
- All existing tests must pass
- Fix any tests broken by the VitalsStrip data source change
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Dashboard trade counts show uncapped value, matching Trades page
- [ ] Shadow Trades "Today" shows today's trades
- [ ] Shadow Trades double-click on preset is a no-op
- [ ] Both tabs: filter bar has identical layout and control heights
- [ ] Both tabs: stats bar has identical styling
- [ ] Both tabs: table has identical row/header formatting
- [ ] All tests pass
- [ ] Close-out report written to docs/sprints/sprint-32.8/session-6g-closeout.md
- [ ] Tier 2 review via @reviewer subagent

## Close-Out
Run full test suite (final session):
`python -m pytest --ignore=tests/test_main.py -n auto -q && cd argus/ui && npx vitest run`

**Write the close-out report to:**
docs/sprints/sprint-32.8/session-6g-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32.8/review-context.md`
2. Close-out report: `docs/sprints/sprint-32.8/session-6g-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q && cd argus/ui && npx vitest run`
5. Files that should NOT have been modified: any Python files

## Session-Specific Review Focus (for @reviewer)
1. Verify Dashboard trade count uses uncapped data source
2. Verify time preset click handler has no-op guard for already-active preset
3. Verify "Today" date computation matches the timezone used in API entry times
4. Verify both tabs' filter bars have identical control heights (inspect Tailwind classes)
5. Verify both tabs' stats bars have identical background/padding/font classes
6. Verify both tabs' tables have identical row padding and header classes
7. Verify no Python files in diff
