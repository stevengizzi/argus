# Sprint 32.8, Session 4: Trades Visual Unification + Hotkeys

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/TradesPage.tsx`
   - `argus/ui/src/features/trades/ShadowTradesTab.tsx`
   - `argus/ui/src/features/trades/TradeTable.tsx`
   - `argus/ui/src/features/trades/TradeStatsBar.tsx`
   - `argus/ui/src/features/trades/TradeFilters.tsx`
2. Run scoped test baseline:
   Vitest: `cd argus/ui && npx vitest run src/features/trades/ src/pages/TradesPage`
   Expected: all passing
3. Verify you are on the correct branch: `sprint-32.8`

## Objective
Unify Live Trades and Shadow Trades tab styling to share the Shadow tab's denser, higher-contrast visual style. Add `l`/`s` keyboard shortcuts for tab switching.

## Requirements

### 1. Adopt Shadow Trades density on Live Trades tab
The Shadow Trades tab has tighter row height, darker background colors, and higher color contrast than the Live Trades tab. Make Live Trades match:

- **Row height**: Reduce Live Trades table row padding to match Shadow Trades (likely `py-2` or smaller vs current `py-3` or `py-4`)
- **Background**: Match Shadow's darker table body background
- **Text sizing**: Match Shadow's smaller text size for table cells
- **Stats bar**: Make the Live Trades stats bar (trades, win rate, net P&L, avg R) match Shadow's visual density and styling

Identify the specific Tailwind classes that differ between the two tabs and standardize on the Shadow tab's values. Extract shared CSS classes or a shared table row component if beneficial.

### 2. Consistent filter bar styling
Make the filter bar area (strategy dropdown, outcome toggles, date range) visually consistent between both tabs. The Shadow tab currently has a more condensed filter bar. Apply the same padding, background, and font sizing to both.

### 3. `l` / `s` hotkeys for tab switching (`TradesPage.tsx`)
Add a `useEffect` with a keydown listener:
- `l` key (when no input focused): switch to Live Trades tab
- `s` key (when no input focused): switch to Shadow Trades tab
- Guard: only fire when `document.activeElement` is not an input, textarea, or select (prevent interference with search/filter inputs)

### 4. Tab header visual consistency
Ensure the "Live Trades" and "Shadow Trades" tab headers have the same font size, weight, and active/inactive styling. Currently they may differ.

## Constraints
- Do NOT modify: any Python backend files, any non-Trades frontend files
- Do NOT change: data fetching hooks, API calls, or table data logic
- Do NOT change: the Shadow Trades table column definitions or data display
- Do NOT change: the Live Trades functionality (sort, filter, outcome toggle, infinite scroll, trade detail panel)
- This session is STYLING ONLY + hotkeys. Feature additions are Session 5.

## Visual Review
1. **Row density**: Live Trades table rows should be as compact as Shadow Trades rows
2. **Background contrast**: Both tabs should have the same dark background with high-contrast text
3. **Stats bar**: Both tabs' stats bars should have identical visual styling
4. **Filter bar**: Both tabs' filter bars should have identical visual styling
5. **Tab headers**: Both tabs' headers should have identical font/weight/color
6. **Hotkeys**: Press `l` and `s` to switch between tabs (verify no conflict with search inputs)

Verification conditions:
- ARGUS running with trade history
- Vite dev server on port 5175
- Navigate to Trades page, compare both tabs side by side

## Test Targets
- New tests:
  1. `test_hotkey_l_switches_to_live` — pressing 'l' activates Live tab
  2. `test_hotkey_s_switches_to_shadow` — pressing 's' activates Shadow tab
  3. `test_hotkey_ignored_in_input` — hotkeys don't fire when input is focused
  4. `test_trade_table_row_density` — Live Trades rows have compact styling class
- Minimum new test count: 4
- Test command: `cd argus/ui && npx vitest run src/features/trades/ src/pages/TradesPage`

## Definition of Done
- [ ] Live Trades row density matches Shadow Trades
- [ ] Background colors and contrast match between tabs
- [ ] Stats bar styling identical between tabs
- [ ] Filter bar styling identical between tabs
- [ ] `l`/`s` hotkeys work for tab switching
- [ ] Hotkeys don't fire when input is focused
- [ ] All existing tests pass
- [ ] 4+ new tests passing
- [ ] Close-out report written to docs/sprints/sprint-32.8/session-4-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Live Trades sort still works | Click column headers, verify sort |
| Live Trades outcome toggle still works | Click Wins/Losses/BE, verify filter |
| Live Trades infinite scroll still works | Scroll to bottom, verify more rows load |
| Shadow Trades data still displays | Navigate to Shadow tab, verify data loads |
| Trade detail panel still opens on row click | Click a Live trade row, verify detail panel |

## Close-Out
**Write the close-out report to a file:**
docs/sprints/sprint-32.8/session-4-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32.8/review-context.md`
2. Close-out report: `docs/sprints/sprint-32.8/session-4-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `cd argus/ui && npx vitest run src/features/trades/ src/pages/TradesPage`
5. Files that should NOT have been modified: any Python files, any non-Trades UI files

## Session-Specific Review Focus (for @reviewer)
1. Verify styling changes are CSS/Tailwind only — no data logic changes
2. Verify hotkey guard checks `document.activeElement` tag name
3. Verify Live Trades functionality (sort, filter, infinite scroll, detail panel) is not broken by styling changes
4. Verify both tabs render correctly with real data

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`
