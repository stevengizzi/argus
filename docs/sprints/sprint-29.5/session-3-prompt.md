# Sprint 29.5, Session 3: Win Rate Bug + UI Fixes

## Pre-Flight Checks
1. Read: `argus/ui/src/features/trades/TradeStatsBar.tsx`, `argus/ui/src/pages/TradesPage.tsx`, `argus/ui/src/features/dashboard/OpenPositions.tsx`, `argus/ui/src/utils/format.ts`, `argus/api/routes/trades.py`, `argus/ui/src/hooks/useTradeStats.ts`
2. Run scoped baseline: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20`
3. Verify branch: `sprint-29.5`

## Objective
Fix win rate display bug (proportion not multiplied by 100), raise trades table limit, add Shares column, abbreviate Trail badge, speed up stats polling.

## Requirements

1. **Win rate fix** in `argus/ui/src/features/trades/TradeStatsBar.tsx`:
   - Line ~41: Change `formatPercentRaw(win_rate)` → `formatPercentRaw(win_rate * 100)`
   - The backend returns `win_rate` as proportion (0.13 = 13%). `formatPercentRaw` expects 0-100 scale.

2. **Dashboard win rate fix**: Find the TodayStatsCard (or equivalent Dashboard component showing "Win Rate"). Apply same `* 100` multiplication. Ensure display shows 1 decimal place (e.g., "13.0%", not "13%"). Check: `argus/ui/src/features/dashboard/` for the stats card that displays win rate.

3. **Trades table limit** in `argus/api/routes/trades.py`:
   - Line ~148: Change `limit: int = Query(50, ge=1, le=250, ...)` → `le=1000`
   - In `argus/ui/src/pages/TradesPage.tsx` line ~142: Change `limit: 250` → `limit: 1000`

4. **Shares column** in `argus/ui/src/features/dashboard/OpenPositions.tsx`:
   - Add `<th>` header "Shares" in the table header row (after Symbol, before Entry or similar)
   - Add `<td>` cell showing `pos.shares_remaining` for each position row
   - Apply to both desktop and tablet layouts. Hide on mobile (use `hidden sm:table-cell` pattern).

5. **Trail badge abbreviation** in `argus/ui/src/features/dashboard/OpenPositions.tsx`:
   - In `getExitReasonLabel()`, change the `trailing_stop` case to return `"Trail"` instead of `"Trailing Stop"`
   - Also check `argus/ui/src/features/trades/TradeTable.tsx` for the same label function and apply same change.

6. **Trade stats polling speed** in `argus/ui/src/hooks/useTradeStats.ts`:
   - Change `refetchInterval` from `30_000` to `10_000`

## Constraints
- Do NOT modify backend `performance.py` win_rate calculation (it correctly returns 0-1 proportion)
- Do NOT modify `formatPercentRaw` utility function (it works as documented)
- Do NOT add virtual scrolling (out of scope — DEF-127)
- Preserve existing sort/filter behavior on trades table

## Test Targets
- New Vitest tests:
  1. `test_win_rate_display_correct_percentage` — mock stats with win_rate=0.395, verify rendered text contains "39.5%"
  2. `test_win_rate_zero_trades` — win_rate=0, verify "0.0%"
  3. `test_shares_column_rendered` — verify OpenPositions table includes shares cell
  4. `test_trail_badge_abbreviation` — verify "trailing_stop" renders as "Trail"
  5. `test_trades_page_limit_1000` — verify API call includes limit=1000
- Minimum: 5 new Vitest tests
- Test command: `cd argus/ui && npx vitest run`

## Visual Review
The developer should visually verify:
1. **Trades page Win Rate**: Shows "39.5%" (or similar), NOT "0.39%" or "0%"
2. **Dashboard Today's Stats Win Rate**: Shows percentage with 1 decimal, matches Trades page
3. **Trades table**: Scrolling past 250 rows works, all trades visible up to 1000
4. **Dashboard Open Positions table**: "Shares" column visible on desktop, hidden on mobile
5. **Exit badges in both tables**: "trailing_stop" exits show "Trail", not "Trailing Stop"

Verification conditions:
- Argus running with paper trading data from today (or mock data with >250 trades)

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Other percentage displays unchanged | Check Performance page percentages |
| Trade filters still work with higher limit | Apply strategy filter, verify correct count |
| Mobile layout not broken | Check responsive layout at 375px |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 5+ new Vitest tests written and passing
- [ ] Visual review items verified
- [ ] Close-out report written to `docs/sprints/sprint-29.5/session-3-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write to: `docs/sprints/sprint-29.5/session-3-closeout.md`

## Tier 2 Review
Test command: `cd argus/ui && npx vitest run`
Files NOT modified: `argus/execution/`, `argus/core/`, `argus/intelligence/`

## Session-Specific Review Focus
1. Verify win_rate multiplication is at display layer only — backend returns unchanged
2. Verify no OTHER formatPercentRaw calls are affected by the change
3. Verify Shares column uses `shares_remaining` not `shares_total`
