# Sprint 28.75, Session 2: Frontend Bug Fixes + UI Improvements

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md` (current project state)
   - `argus/ui/src/pages/DashboardPage.tsx`
   - `argus/ui/src/features/dashboard/VixRegimeCard.tsx`
   - `argus/ui/src/features/dashboard/TodayStats.tsx`
   - `argus/ui/src/features/dashboard/OpenPositions.tsx`
   - `argus/ui/src/pages/TradesPage.tsx`
   - `argus/ui/src/features/trades/TradeStatsBar.tsx`
   - `argus/ui/src/hooks/useTrades.ts`
   - `argus/api/routes/dashboard.py` (for win rate investigation)
2. Run the test baseline:
   Scoped: cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20
   Expected: ~680 tests, all passing
3. Verify you are on branch: sprint-28.75 (continuing from Session 1)

## Objective
Fix six frontend bugs and add two UI improvements found during the March 30
market session debrief.

## Requirements

### R1: Fix VixRegimeCard viewport fill (DEF-120)
The VixRegimeCard fills the entire viewport height on the Dashboard.
- In `VixRegimeCard.tsx`: the Card component uses `className="h-full flex flex-col"`.
  Remove `h-full` — the card should size to its content.
- Verify it's wrapped in a `<motion.div variants={staggerItem}>` in DashboardPage.tsx
  (it currently isn't on the tablet layout at line 288). Wrap it for consistency
  with other dashboard cards.
- The card should be compact — roughly 80-120px tall with VIX close, VRP badge,
  phase, and momentum arrow.

### R2: Fix TodayStats win rate showing 0% (DEF-116)
The TodayStats card shows "—" (winRate=0) despite 126+ closed trades.
- Investigate the backend first: in `argus/api/routes/dashboard.py` line ~286,
  `compute_metrics(today_trades)` filters to closed trades via
  `exit_price is not None`. Check whether `query_trades()` returns trades
  with `exit_price=None` for closed positions.
- Run a diagnostic: temporarily log the count of trades returned by
  `query_trades()` and the count after the `exit_price is not None` filter
  in `compute_metrics()`. If all trades are filtered out, the issue is in
  how TradeLogger stores exit_price.
- Fix wherever the disconnect is. If it's a backend field issue, fix the
  serialization. If it's a frontend display issue, fix the component.

### R3: Fix closed positions tab capped at 50 (DEF-115)
- In `OpenPositions.tsx` line 81: `limit: 50` for the closed tab query.
  Increase to 500 or add pagination. The badge count should reflect
  total_count from the API response, not the capped array length.
- Verify the API endpoint supports higher limits.

### R4: Fix Trades page stats freeze after connectivity loss (DEF-117)
The Net P&L and Win Rate metrics on the Trades page freeze after losing
WebSocket connectivity and don't respond to time filter toggles.
- In `useTrades.ts`: change `refetchOnWindowFocus: false` to `true`. When
  the user closes and reopens their laptop, TanStack Query should refetch.
- The stats freezing on filter toggle suggests the issue described in DEF-102:
  stats are computed client-side from a 250-trade subset. With 817 trades in
  a session, the subset is stale.
- **Fix:** Add a server-side stats endpoint: `GET /api/v1/trades/stats` that
  accepts the same filter params (strategy_id, date_from, date_to, outcome)
  and returns { total_trades, wins, losses, win_rate, net_pnl, avg_r }.
  Compute from the full dataset server-side, not from a paginated client
  subset.
- In TradeStatsBar, consume this new endpoint instead of computing from the
  trades array. Use a separate TanStack Query with the filter params as
  query key dependencies.
- This resolves DEF-102 and DEF-117 together.

### R5: Add Avg R to Trades page summary (DEF-118)
- In TradeStatsBar, add an "Avg R" metric card using the avg_r value from
  the new stats endpoint (R4). Style it the same as other metrics: green
  if positive, red if negative, "—" if null.

### R6: Add colored P&L column to Open Positions table (DEF-119)
- In the open positions table in OpenPositions.tsx, add a "P&L" column
  showing unrealized P&L in dollars with +/- prefix.
- Color: green (text-argus-profit) for positive, red (text-argus-loss) for
  negative.
- Also color the current/exit price column: green if above entry, red if
  below.
- Compute P&L from (current_price - entry_price) * shares for long positions.

## Constraints
- Do NOT modify: argus/execution/, argus/strategies/, argus/core/ (except
  minor imports if needed for the stats endpoint), argus/intelligence/,
  argus/backtest/
- Do NOT change any trading engine behavior — these are display-only changes
- The new stats endpoint must be JWT-protected (same as other /api/v1/ routes)
- Keep TanStack Query patterns consistent with existing hooks

## Test Targets
After implementation:
- Existing Vitest tests: all must still pass
- New tests to write (Vitest):
  - VixRegimeCard: renders without filling viewport (check no h-full class)
  - TradeStatsBar: renders Avg R metric
  - OpenPositions: closed tab respects higher limit
  - Stats endpoint integration (if adding backend): pytest test for the new
    /api/v1/trades/stats route
- Minimum new test count: 4 Vitest + 2 pytest (if adding backend endpoint)
- Test commands:
  - Frontend: cd argus/ui && npx vitest run --reporter=verbose
  - Backend: python -m pytest tests/api/ -x -q
  - Full: python -m pytest tests/ -n auto --ignore=tests/test_main.py -q

## Visual Review
The developer should visually verify the following after this session:
1. **VixRegimeCard**: Compact height, does not fill viewport. Shows VIX close,
   VRP badge, phase, momentum arrow in ~80-120px.
2. **TodayStats**: Win Rate shows a non-zero percentage when trades exist.
3. **Closed Positions tab**: Shows >50 rows when more exist. Badge count
   matches total.
4. **Trades page stats**: Net P&L and Win Rate update when toggling
   Today/Week/Month. Values refresh after closing and reopening laptop.
5. **Trades page Avg R**: New metric visible in stats bar.
6. **Open Positions P&L column**: Shows colored +/- dollar values. Current
   price colored green/red relative to entry.

Verification conditions:
- Run during or after a paper trading session with open positions and closed trades
- If no live session, verify with Storybook or mock data if available

## Definition of Done
- [ ] All 6 requirements implemented
- [ ] All existing Vitest tests pass
- [ ] All existing pytest tests pass
- [ ] New tests written and passing
- [ ] Visual review items verified by developer
- [ ] Close-out report written to docs/sprints/sprint-28.75/session-2-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Dashboard loads without errors | Visual: navigate to Dashboard, check console |
| All 8 existing pages render | Visual: navigate each page |
| TodayStats still shows Trades, Best Trade, Avg R | Visual: check all 4 metrics |
| Trades page table still loads and sorts | Visual: verify |
| Existing API endpoints unchanged | Run: pytest tests/api/ -x -q |
| WebSocket still connects | Visual: check status indicator in UI |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

**Write the close-out report to a file:**
docs/sprints/sprint-28.75/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: docs/sprints/sprint-28.75/review-context.md
2. The close-out report path: docs/sprints/sprint-28.75/session-2-closeout.md
3. The diff range: git diff HEAD~1
4. The test command (final session — full suite):
   python -m pytest tests/ -n auto --ignore=tests/test_main.py -q && cd argus/ui && npx vitest run
5. Files that should NOT have been modified: argus/execution/order_manager.py
   (Session 1 only), argus/strategies/, argus/core/events.py, argus/backtest/

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix them, update both the close-out
and review files per the standard protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify VixRegimeCard no longer has h-full or equivalent stretch styling
2. Verify TodayStats win rate fix addresses root cause (not just display)
3. Verify new stats endpoint is JWT-protected
4. Verify stats endpoint query uses same filter logic as trades endpoint
5. Verify OpenPositions closed tab limit increase doesn't cause performance
   issues (check if API supports pagination)
6. Verify P&L column computation is correct for long positions
7. Verify refetchOnWindowFocus change doesn't cause excessive API calls

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if: changes to trading engine code; changes to order_manager.py;
  changes to event bus or risk manager; new WebSocket endpoints
- CONCERNS if: stats endpoint duplicates significant logic from existing
  performance endpoints; P&L computation doesn't match Order Manager's
  unrealized P&L calculation
