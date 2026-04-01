# Sprint 32.75, Session 3: Orchestrator Page Fixes

## Pre-Flight Checks
1. Read context:
   - `docs/sprints/sprint-32.75/review-context.md`
   - `argus/api/routes/orchestrator.py` (lines 300-400 for P&L bug)
   - `argus/ui/src/features/orchestrator/SessionOverview.tsx`
   - `argus/ui/src/features/orchestrator/StrategyCoverageTimeline.tsx`
2. Run scoped tests: `python -m pytest tests/api/test_orchestrator*.py -x -q && cd argus/ui && npx vitest run src/features/orchestrator/`
3. Verify branch: `sprint-32.75-session-3`
4. Confirm S1 merged

## Objective
Fix Orchestrator page P&L/trades display bug and polish Capital Allocation legend and Catalyst links.

## Requirements

1. **P&L bug fix** — In `argus/api/routes/orchestrator.py`, replace the broken `getattr(strategy, '_trade_count_today', 0)` / `getattr(strategy, '_daily_pnl', 0.0)` pattern (lines ~306-312) with a direct query to `state.trade_logger.get_trades()` filtered to today's ET date per strategy. Compute per-strategy `trade_count_today` and `daily_pnl` from the query results. This is more robust than the never-called `record_trade_result()` path.

2. **Capital Allocation legend** — Verify that after S1's identity additions, the AllocationDonut now correctly shows display names. If the Orchestrator page has any additional hardcoded `strat_xxx` formatting in its own components, fix those to use `getStrategyDisplay()`.

3. **Catalyst headlines clickable** — In the CatalystAlertPanel component (find in `features/orchestrator/` or `features/dashboard/`), wrap headline text in `<a href={item.url} target="_blank" rel="noopener noreferrer" className="hover:underline">`. If the catalyst data model doesn't include a URL field, add a link icon that opens a web search for the headline.

## Constraints
- Do NOT modify OrderManager position management logic
- Do NOT modify BaseStrategy.record_trade_result() — leave it as-is for potential future use
- Do NOT change the AllocationInfo Pydantic model schema (keep the fields, just populate them correctly)
- Do NOT modify any non-Orchestrator frontend pages

## Test Targets
- New backend tests: verify orchestrator API returns non-zero P&L for a strategy with closed trades today
- Test catalyst link rendering
- Minimum: 5 new tests
- Command: `python -m pytest tests/api/test_orchestrator*.py -x -q`

## Visual Review
1. **Session Overview**: P&L shows actual sum of today's closed trade P&L (not $0.00)
2. **Trades Today**: Shows actual count (not 0)
3. **Capital Allocation legend**: Display names like "ORB Scalp", "ABCD", not "strat_orb_scalp"
4. **Catalyst headlines**: Clickable with hover underline, opening in new tab

Verification conditions: App running with paper trading active, trades closed today

## Definition of Done
- [ ] Orchestrator P&L and trades populated from trade_logger query
- [ ] Capital Allocation legend uses display names
- [ ] Catalyst headlines clickable
- [ ] All tests pass
- [ ] Close-out written to `docs/sprints/sprint-32.75/session-3-closeout.md`
- [ ] Tier 2 review via @reviewer

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Orchestrator page still loads without errors | Verify 200 response from `/api/v1/orchestrator/allocations` |
| AllocationInfo schema unchanged | Existing test assertions still pass |
| Strategy cards still show correct status | Visual check — active/inactive badges correct |

## Close-Out
Write to: `docs/sprints/sprint-32.75/session-3-closeout.md`

## Tier 2 Review
Test command: `python -m pytest tests/api/test_orchestrator*.py -x -q && cd argus/ui && npx vitest run src/features/orchestrator/`. Files NOT to modify: OrderManager, BaseStrategy, Risk Manager.

## Session-Specific Review Focus
1. Verify the trade_logger query uses ET date correctly (not UTC) — trades at 3:30 PM ET = 7:30 PM UTC must show as "today"
2. Verify the query doesn't break when trade_logger has zero trades
3. Verify catalyst links have `rel="noopener noreferrer"` for security
