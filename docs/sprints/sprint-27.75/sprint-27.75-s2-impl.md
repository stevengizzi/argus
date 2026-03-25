# Sprint 27.75, Session 2: Frontend — Suspension Display + Trades Period Filter Bug

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `CLAUDE.md`
   - `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`
   - `argus/ui/src/pages/TradesPage.tsx`
   - `argus/ui/src/features/trades/TradeStatsBar.tsx`
   - `argus/ui/src/features/trades/TradeFilters.tsx`
   - `argus/ui/src/hooks/useTrades.ts`
   - `argus/api/routes/trades.py`
   - `argus/analytics/trade_logger.py` (look for `get_trades` and `count_trades` methods)
2. Run the scoped test baseline (DEC-328):
   Scoped: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20`
   Expected: ~633 Vitest tests, all passing
3. Verify you are on branch: `main` (Session 1 already committed)

## Objective
Fix two frontend bugs: (1) Strategy Operations cards not showing circuit-breaker suspension state (only PerformanceThrottler suspensions display), and (2) Trades page Win Rate / Net P&L values not updating when toggling quick date filters (Today/Week/Month/All).

## Context

### Bug 1: Suspension Display
The StrategyOperationsCard renders a throttle section only when `throttle_action !== 'none'`. But circuit-breaker suspensions (5 consecutive losses) set `is_active = false` without setting `throttle_action`. Result: 4 strategies show green status dots while actually suspended. The Strategy Coverage Timeline correctly shows "(Susp)" because it checks `!alloc.is_active`. VWAP Reclaim correctly shows its throttle because the PerformanceThrottler sets `throttle_action = 'suspend'`.

### Bug 2: Trades Period Filter
The Trades page quick filter buttons (Today/Week/Month/All) update trade counts but Win Rate and Net P&L stay the same. The `TradeStatsBar` computes stats client-side from `data.trades`. Investigation needed: either the backend `getTrades` doesn't apply `date_from`/`date_to` to the query that returns the trades array (only to `count_trades`), or the frontend is passing different params to the count vs data queries, or `keepPreviousData` is causing stale stats to persist.

## Requirements

### Part A: Suspension Display on Strategy Operations Cards

1. **In `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`**:
   - Add a suspension section that renders when `!allocation.is_active && !isThrottled`
   - This section should appear in the same position as the throttle section (after allocation, before operating window)
   - Display: a red/amber badge saying "Suspended", the reason from `allocation.reason` if available, or "Circuit breaker — consecutive losses" as default
   - Style: similar to the throttle section but with a more muted red treatment (e.g., `bg-red-400/5 border border-red-400/20`)
   - The status dot should show `degraded` status (amber/red) — verify `deriveHealthStatus` already handles this (it does via `!alloc.is_active` check)
   - The play/resume button should already work for resuming — verify

2. **In `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`**:
   - Update the operating window "Active"/"Inactive" indicator at the bottom:
     - If `!allocation.is_active`, show "Suspended" in amber/red instead of "Active"/"Inactive"
     - This gives a third visual state beyond the window-based active/inactive

### Part B: Trades Page Period Filter Bug

3. **Investigate the root cause** — check these in order:
   a. In `argus/api/routes/trades.py`: Does `get_trades()` pass `date_from`/`date_to` to the trade_logger query? Does `count_trades()` use the same filters?
   b. In `argus/analytics/trade_logger.py`: Does the SQL query for fetching trades actually apply the date filter? Is `date_from`/`date_to` used in the WHERE clause for both the trade list AND the count?
   c. In `argus/ui/src/hooks/useTrades.ts`: Does the `queryKey` properly include the date params so TanStack Query treats different date ranges as different queries?
   d. In `argus/ui/src/pages/TradesPage.tsx`: When `handleQuickFilter` fires, does `updateFilters` actually update `date_from`/`date_to` in local state, triggering a re-fetch?

4. **Fix the root cause** — based on investigation:
   - If backend: add missing date filter to SQL WHERE clause
   - If frontend: fix the query key or state update
   - If `keepPreviousData`: the stats bar may be computing from stale `data.trades` while `data.total_count` is from the new response — if so, ensure the stats compute from the same data source as the count

5. **Verify the fix** — after the fix, toggling Today → Week → Month → All should show different Win Rate and Net P&L values (assuming trades exist across different periods).

## Constraints
- Do NOT modify any backend Python code UNLESS the bug is in the trades endpoint/trade_logger SQL
- Do NOT modify strategy logic
- Do NOT modify the throttle section's existing behavior — the new suspension section is additive
- Do NOT change the ThrottledLogger or log rate-limiting code from Session 1
- The suspension display must degrade gracefully if `allocation.reason` is null/empty

## Test Targets
After implementation:
- Existing Vitest tests: all must still pass
- New tests to write:
  1. `argus/ui/src/features/orchestrator/StrategyOperationsCard.test.tsx` (add to existing):
     - `test_shows_suspension_section_when_inactive_and_not_throttled` — render with `is_active=false, throttle_action='none'`, verify suspension badge appears
     - `test_hides_suspension_when_active` — render with `is_active=true`, verify no suspension section
     - `test_shows_throttle_not_suspension_when_throttled` — render with `is_active=false, throttle_action='suspend'`, verify throttle section appears (not suspension)
     - `test_suspension_shows_reason` — render with reason string, verify it appears
     - `test_suspension_shows_default_reason_when_empty` — render with no reason, verify fallback text
  2. If backend fix needed, add `tests/api/test_trades_date_filter.py`:
     - `test_trades_filtered_by_date_from` — verify trades before date_from excluded
     - `test_trades_count_matches_list_length` — verify total_count equals len(trades)
- Minimum new Vitest tests: 5
- Test command: `cd argus/ui && npx vitest run src/features/orchestrator/StrategyOperationsCard.test.tsx --reporter=verbose`

## Visual Review
The developer should visually verify the following after this session:
1. **Orchestrator page with suspended strategies**: Cards for circuit-breaker-suspended strategies show a suspension badge/section (not just green dot + "Active")
2. **Orchestrator page with throttled strategy**: VWAP Reclaim (if throttled) still shows the throttle section with "Override Throttle" button — behavior unchanged
3. **Trades page quick filters**: Toggle between Today/Week/Month/All — Win Rate and Net P&L values update along with trade counts
4. **Trades page "All" filter**: Shows the full trade history with correct aggregate stats

Verification conditions:
- ARGUS running with `system_live.yaml` during or after a market session with trades
- At least some trades exist for today and for the wider date ranges

## Definition of Done
- [ ] Suspension section renders on StrategyOperationsCard when `!is_active && !isThrottled`
- [ ] Suspension section shows reason or fallback text
- [ ] Operating window indicator shows "Suspended" state
- [ ] Trades page Win Rate / Net P&L update on period filter toggle
- [ ] Root cause identified and documented in close-out
- [ ] All existing tests pass
- [ ] New tests written and passing (≥5 Vitest)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Throttle section still works | Vitest: existing StrategyOperationsCard tests pass |
| Trade count still correct | Visual: Trades page count matches dashboard Daily P&L count |
| No strategy code changes | `git diff HEAD~1 -- argus/strategies/` shows no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-27.75/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: docs/sprints/sprint-27.75/review-context.md
2. The close-out report path: docs/sprints/sprint-27.75/session-2-closeout.md
3. The diff range: git diff HEAD~1
4. The test command (final session — full suite):
   Backend: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   Frontend: `cd argus/ui && npx vitest run --reporter=verbose`
5. Files that should NOT have been modified: `argus/strategies/`, `argus/intelligence/`, `argus/backtest/`

## Session-Specific Review Focus (for @reviewer)
1. Verify suspension section only appears when `!is_active && !isThrottled` (not when throttled)
2. Verify throttle section behavior is completely unchanged
3. Verify Trades page date filter fix addresses the actual root cause (not a workaround)
4. Verify `keepPreviousData` isn't causing stale stats to persist after the fix
5. If backend SQL was modified, verify both trades list AND count use the same WHERE clause

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| All pytest pass | `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto` |
| All Vitest pass | `cd argus/ui && npx vitest run` |
| No strategy changes | `git diff HEAD~1 -- argus/strategies/` |
| Session 1 changes intact | `git log --oneline -3` shows S1 commit |

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if any existing test fails
- ESCALATE if strategy logic was modified
- ESCALATE if throttle section behavior changed (not just additive suspension section)
- ESCALATE if the trades date filter fix introduces a performance regression (e.g., removing keepPreviousData entirely)
