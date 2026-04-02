# Sprint 32.8, Session 5: Trades Feature Additions

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/TradesPage.tsx`
   - `argus/ui/src/features/trades/ShadowTradesTab.tsx`
   - `argus/ui/src/features/trades/TradeFilters.tsx`
   - `argus/ui/src/hooks/useShadowTrades.ts`
   - `argus/ui/src/hooks/useTradeFilters.ts` (reference for how Live Trades filters work)
2. Run scoped test baseline:
   Vitest: `cd argus/ui && npx vitest run src/features/trades/ src/pages/TradesPage`
   Expected: all passing (including S4's new tests)
3. Verify you are on the correct branch: `main`
4. Confirm Session 4 is complete and merged (this session depends on S4's styling)

## Objective
Add Outcome toggle, time presets, infinite scroll, sortable columns, and Reason tooltip to Shadow Trades — bringing it to feature parity with Live Trades.

## Requirements

### 1. Outcome toggle on Shadow Trades (`ShadowTradesTab.tsx`)
Add an Outcome toggle (All / Wins / Losses / BE) to the Shadow Trades filter bar:
- **Wins**: filter where `theo_pnl > 0` (or if theo_pnl is null, exclude)
- **Losses**: filter where `theo_pnl < 0`
- **BE**: filter where `theo_pnl == 0` or `theo_pnl is null` (no outcome data = effectively break-even / unknown)
- **All**: no filter

If the backend doesn't return `theo_pnl` on shadow trade records, this filter may need to operate on the `r_multiple` field instead. Check the API response shape in `useShadowTrades.ts` and adapt accordingly. If neither field is available (all values are null/zero as seen in current data), the toggle should still render but show a badge count of 0 for Wins/Losses.

### 2. Time presets on Shadow Trades
Add Today / Week / Month / All time preset buttons to the Shadow Trades filter bar. These should set the From/To date range filters:
- **Today**: `from = today 00:00`, `to = today 23:59`
- **Week**: `from = start of current week (Monday)`, `to = now`
- **Month**: `from = start of current month`, `to = now`
- **All**: clear date range filters

Model the implementation on how Live Trades handles its time presets (check `TradeFilters.tsx` and `useTradeFilters.ts`).

### 3. Infinite scroll replacing pagination (`ShadowTradesTab.tsx`, `useShadowTrades.ts`)
Replace the current pagination (Page 1 of 291) with infinite scroll:
- Load initial page of results
- When the user scrolls near the bottom of the table, fetch the next page and append
- Show a small loading indicator at the bottom while fetching
- Use an IntersectionObserver on a sentinel element at the bottom of the table

If the backend `GET /api/v1/counterfactual/positions` endpoint supports `offset`/`limit` or cursor pagination, use that. If it only returns all results at once, implement client-side infinite scroll (render in batches of ~50 rows, append on scroll).

### 4. Sortable columns on Shadow Trades (`ShadowTradesTab.tsx`)
Make the Shadow Trades table headers clickable for sorting:
- Sortable columns: Symbol, Strategy, Entry Time, Entry $, Theo P&L, R-Multiple, MFE (R), MAE (R), Stage, Grade
- Click toggles ascending/descending
- Show sort indicator (▲/▼) on active column
- Default sort: Entry Time descending (most recent first)

Implement client-side sorting (data is already loaded). Match the sort indicator styling used in Live Trades.

### 5. Reason column wider + tooltip (`ShadowTradesTab.tsx`)
The Reason column currently truncates with `...`. Fix:
- Set `min-width: 200px` (or wider) on the Reason column
- Add `title={reason}` attribute on the Reason cell so hovering shows the full text
- Optionally use `text-ellipsis overflow-hidden whitespace-nowrap` with the title attribute

### 6. Extract shared filter component (optional)
If the filter bars for Live and Shadow Trades are sufficiently similar after these changes, extract a `SharedTradeFilters.tsx` component that both tabs use. This is optional — only do it if it reduces code duplication meaningfully. If the two tabs' filter requirements are different enough that a shared component would be more complex than two separate ones, skip this.

## Constraints
- Do NOT modify: any Python backend files
- Do NOT change: Live Trades tab functionality or data hooks
- Do NOT change: the Shadow Trades API endpoint or backend logic
- This session builds on S4's styling — do not revert S4's visual changes

## Visual Review
1. **Outcome toggle**: All/Wins/Losses/BE buttons visible in Shadow Trades filter bar with counts
2. **Time presets**: Today/Week/Month/All buttons visible and functional
3. **Infinite scroll**: No pagination controls; scrolling to bottom loads more rows seamlessly
4. **Sortable columns**: Click Strategy header → sorts by strategy; click again → reverses. Arrow indicator visible.
5. **Reason tooltip**: Hover over a truncated Reason cell → full text shown in tooltip
6. **14K+ rows**: Scroll through shadow trades without performance degradation

Verification conditions:
- ARGUS running with shadow trade history (14K+ trades visible in current data)
- Vite dev server on port 5175

## Test Targets
- New tests:
  1. `test_outcome_toggle_filters_wins` — Outcome toggle filters to positive theo_pnl
  2. `test_outcome_toggle_filters_losses` — Outcome toggle filters to negative theo_pnl
  3. `test_time_preset_today` — Today preset sets date range to current day
  4. `test_time_preset_all` — All preset clears date range
  5. `test_sortable_columns_toggle` — clicking column header toggles sort direction
  6. `test_reason_tooltip` — Reason cell has title attribute with full text
- Minimum new test count: 6
- Test command: `cd argus/ui && npx vitest run src/features/trades/ src/pages/TradesPage src/hooks/useShadowTrades`

## Definition of Done
- [ ] Outcome toggle on Shadow Trades (All/Wins/Losses/BE)
- [ ] Time presets on Shadow Trades (Today/Week/Month/All)
- [ ] Infinite scroll replacing pagination
- [ ] Sortable columns with sort indicators
- [ ] Reason column wider with tooltip on hover
- [ ] All existing tests pass
- [ ] 6+ new tests passing
- [ ] Close-out report written to docs/sprints/sprint-32.8/session-5-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Shadow Trades still loads data | Navigate to Shadow tab, verify table populated |
| Shadow Trades strategy filter still works | Select a strategy, verify filtered results |
| Live Trades tab unaffected | Switch to Live tab, verify all functionality |
| Date range filters still work | Set From/To dates, verify filtered results |

## Close-Out
**Write the close-out report to a file:**
docs/sprints/sprint-32.8/session-5-closeout.md

The close-out MUST run the full test suite (final session):
`python -m pytest --ignore=tests/test_main.py -n auto -q && cd argus/ui && npx vitest run`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32.8/review-context.md`
2. Close-out report: `docs/sprints/sprint-32.8/session-5-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command (full suite — final session): `python -m pytest --ignore=tests/test_main.py -n auto -q && cd argus/ui && npx vitest run`
5. Files that should NOT have been modified: any Python files, any non-Trades UI files

## Session-Specific Review Focus (for @reviewer)
1. Verify Outcome toggle correctly handles null/zero theo_pnl values
2. Verify infinite scroll doesn't load all 14K+ rows at once (check for batching/pagination in the hook)
3. Verify sort is client-side only (no API calls on sort)
4. Verify Reason tooltip uses native `title` attribute (not a custom tooltip component that could cause perf issues at 14K rows)
5. Verify Live Trades tab is completely unmodified in this session's diff

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`
