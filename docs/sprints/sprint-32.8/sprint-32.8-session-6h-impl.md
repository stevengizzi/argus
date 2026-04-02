# Sprint 32.8, Session 6h: Final Trades Polish

## Pre-Flight Checks
1. Read:
   - `argus/ui/src/features/trades/ShadowTradesTab.tsx`
   - `argus/ui/src/features/trades/TradeTable.tsx`
   - `argus/ui/src/features/trades/TradeStatsBar.tsx`
   - `argus/ui/src/pages/TradesPage.tsx`
2. Kill orphaned Vitest workers:
   `pkill -f "vitest/dist/workers" 2>/dev/null; echo "Cleaned"`
3. Run baseline: `cd argus/ui && npx vitest run src/features/trades/ src/pages/TradesPage`

## Objective
Fix remaining visual discrepancies between Live and Shadow Trades tabs, and fix
the Shadow Trades summary stats bug.

## Requirements

### 1. Shadow Trades summary stats not updating on filter change (BUG)

When switching between Today/Week/Month/All time presets on Shadow Trades, the
SHADOW TRADES count updates but WIN RATE, AVG THEO P&L, and AVG R-MULTIPLE
remain static.

Root cause: the summary stats are likely computed from a stale data source that
doesn't respond to filter changes. The stats need to be recomputed from the
currently loaded trades whenever the filter changes.

Debug by:
1. Find where `WIN RATE (THEORETICAL)`, `AVG THEO P&L`, and `AVG R-MULTIPLE` are computed
2. Check if they derive from the API response metadata (which may only return totals
   for the first page) or from `allTrades` (which gets cleared and repopulated on filter change)
3. The fix: ensure these stats are computed from the `allTrades` array via `useMemo`,
   recomputing whenever `allTrades` changes. Specifically:
   - Win Rate = count of trades with `theoretical_pnl > 0` / count of trades with
     non-null `theoretical_pnl` (exclude null/undefined from denominator)
   - Avg Theo P&L = mean of `theoretical_pnl` for trades with non-null values
   - Avg R-Multiple = mean of `r_multiple` for trades with non-null values
   - If all values are null, show "—" (dash)

### 2. Live Trades — gap between filter bar and stats bar

On Live Trades, the filter bar container and the stats bar container are flush
against each other with no spacing. On Shadow Trades, there's a visible gap.

In `TradesPage.tsx` or the Live Trades section, add `gap-3` (or `space-y-3`) between
the filter bar and stats bar containers. Match whatever spacing Shadow Trades uses
between its filter row and summary stats row.

### 3. Live Trades — table row background and height matching Shadow

Compare the Live Trades table (`TradeTable.tsx`) with the Shadow Trades table
(inline in `ShadowTradesTab.tsx`):

- **Row background**: Shadow Trades table rows likely use a slightly darker or
  transparent background. Check if Live Trades `<tr>` or `<tbody>` has a different
  background class than Shadow. Align them.
- **Row height**: Verify `py-2` is applied to ALL `<td>` elements in Live Trades.
  Also check `<th>` header cells — they may have different padding than Shadow's
  header cells. Align both.
- **Header row**: Compare header background color, text size, text color, and
  padding between the two tables. Make Live Trades headers match Shadow Trades headers.

Look at the actual Tailwind classes on `<table>`, `<thead>`, `<tr>`, `<th>`, and `<td>`
in both implementations and make them identical.

## Constraints
- Do NOT modify any Python backend files
- Do NOT change data fetching hooks or API calls
- Do NOT change the Shadow Trades infinite scroll behavior
- PRESERVE all existing test IDs

## Visual Review
After fixes:
1. **Shadow Trades summary stats**: Change time preset from "All" to "Today" — Win Rate,
   Avg Theo P&L, and Avg R-Multiple should update to reflect only today's trades
2. **Live Trades spacing**: Visible gap between filter bar and stats bar
3. **Table comparison**: Switch between Live and Shadow tabs rapidly — the table headers,
   row heights, and backgrounds should look identical (only column content differs)

## Definition of Done
- [ ] Shadow Trades summary stats update when time presets change
- [ ] Live Trades has proper gap between filter bar and stats bar
- [ ] Live Trades table row backgrounds match Shadow Trades
- [ ] Live Trades table header styling matches Shadow Trades
- [ ] All tests pass
- [ ] Close-out report written to docs/sprints/sprint-32.8/session-6h-closeout.md
- [ ] Tier 2 review via @reviewer subagent

## Close-Out
Run full suite: `python -m pytest --ignore=tests/test_main.py -n auto -q && cd argus/ui && npx vitest run`

Write to: `docs/sprints/sprint-32.8/session-6h-closeout.md`
