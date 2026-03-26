# Sprint 27.95, Session 1b: Trade Logger Reconciliation Close Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/analytics/trade_logger.py` — trade logging logic, fields required
   - `argus/execution/order_manager.py` — reconciliation close path (post-Session 1a)
   - Existing trade logger tests (grep for "trade_logger" or "log_trade")
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/analytics/ -x -q
   ```
   Expected: all passing (full suite confirmed by Session 1a close-out)
3. Verify you are on the correct branch with Session 1a changes committed

## Objective
Fix the ERROR-level "Failed to log trade" messages produced during reconciliation synthetic closes. Ensure reconciliation closes produce valid trade records with gracefully defaulted missing fields.

## Requirements

1. **In `argus/analytics/trade_logger.py`**, identify the failure point for reconciliation closes:
   - Find the `log_trade` method (or equivalent) and determine which fields are required
   - Identify which fields are missing when called from the reconciliation close path (likely: `exit_price`, `entry_price`, or strategy-specific metadata)
   - Add graceful defaults for missing fields: `exit_price=0.0`, `entry_price` from position's stored entry if available else `0.0`, `exit_reason="reconciliation"`
   - Ensure the trade record is valid for DB insertion but clearly identifiable as a reconciliation close

2. **In the reconciliation close path** (in `order_manager.py`, the code that calls trade logger during cleanup), ensure all required fields are passed:
   - If the close path currently passes incomplete data, add the missing fields with appropriate defaults
   - The reconciliation close should pass: symbol, shares, entry_price (from position record), exit_price=0.0, pnl=0.0, exit_reason="reconciliation", strategy_id, hold_time

3. **Verify** that normal trade close paths (stop_loss, target_1, target_2, time_stop, eod_flatten) are NOT affected by these changes — they must continue to pass real prices and P&L values.

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/data/`
- Do NOT change: the trade record schema (no new columns), normal close trade logging behavior
- Do NOT change: how P&L is calculated for normal trades
- Reconciliation trades with PnL=0 should NOT be counted in performance summaries (verify existing filtering handles exit_reason="reconciliation")

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~5):
  1. Reconciliation close produces valid trade record (no ERROR log)
  2. Reconciliation trade record has PnL=0.0, exit_reason="reconciliation"
  3. Reconciliation close with minimal position data (only symbol + shares) succeeds
  4. Normal stop_loss close still produces correct trade record with real prices
  5. Normal target_1 close still produces correct trade record
- Minimum new test count: 5
- Test command: `python -m pytest tests/analytics/ -x -q`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 5+ new tests written and passing
- [ ] Zero ERROR-level log entries from trade logger during reconciliation close
- [ ] Normal trade close paths unchanged
- [ ] Close-out report written to `docs/sprints/sprint-27.95/session-1b-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Normal trade logging unchanged | Run existing trade logger tests |
| Reconciliation close no longer produces ERROR | Mock reconciliation close, check no ERROR log |
| Trade record schema unchanged | Verify no new DB columns added |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.
**Write the close-out report to:** `docs/sprints/sprint-27.95/session-1b-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-27.95/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.95/session-1b-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/analytics/ -x -q`
5. Files NOT modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/`, `argus/data/`

Review report: `docs/sprints/sprint-27.95/session-1b-review.md`

## Post-Review Fix Documentation
If CONCERNS reported and fixed, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify reconciliation close path now passes all required fields to trade logger
2. Verify normal close paths are NOT changed (diff should not touch normal close code paths)
3. Verify reconciliation trade records are distinguishable from real trades (exit_reason field)
4. Check that PnL=0 reconciliation trades won't pollute performance calculations

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Normal position lifecycle unchanged
- [ ] Trade logging for real exits (stop, target, time_stop) unchanged
- [ ] Full test suite passes, no hangs

## Sprint-Level Escalation Criteria (for @reviewer)
1. Trade logger change breaks normal trade recording → halt, escalate
2. Pre-flight test failures → investigate
