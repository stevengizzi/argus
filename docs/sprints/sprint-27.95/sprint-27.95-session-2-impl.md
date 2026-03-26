# Sprint 27.95, Session 2: Order Management Hardening

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/order_manager.py` — post-Session 1a (broker-confirmed, reconciliation redesign in place)
   - `argus/core/events.py` — event types
   - Existing order manager tests
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/execution/ -x -q
   ```
   Expected: all passing (full suite confirmed by Session 1b close-out)
3. Verify Session 1a and 1b changes are committed

## Objective
Cap stop resubmission retries (max 3 with backoff, then emergency flatten), handle bracket amendment "Revision rejected" errors by resubmitting fresh orders, and deduplicate fill callbacks from `ib_async`.

## Requirements

### Stop Resubmission Cap (Issue 3)

1. **In `argus/execution/order_manager.py`**, add retry tracking:
   - Add `_stop_retry_count: dict[str, int]` — per-symbol retry counter
   - Add config field `max_stop_retries: int = 3` (add to appropriate config model)

2. **In the stop cancellation/rejection handler** (find where "Stop order cancelled for {symbol}. Resubmitting." is logged):
   - Before resubmitting: increment `_stop_retry_count[symbol]`
   - If count > `max_stop_retries`: do NOT resubmit. Log ERROR "Stop resubmission exhausted for {symbol} after {count} attempts — triggering emergency flatten". Call `close_position(symbol)` or equivalent (must respect `_flatten_pending` guard).
   - If count <= max: resubmit with backoff delay. Use `asyncio.sleep(2 ** (count - 1))` for exponential backoff (1s, 2s, 4s).
   - Reset counter when a stop order is successfully acknowledged (not just submitted — when IBKR confirms the order is active/working)

3. Clear `_stop_retry_count[symbol]` on position close.

### Bracket Amendment Revision-Rejected Handling (Issue 4)

4. **In the order cancellation callback**, detect "Revision rejected" cancellation reason:
   - Check if the cancel reason string contains "Revision rejected"
   - If detected AND the cancelled order was a stop or target leg:
     - Do NOT enter the normal stop resubmission retry flow
     - Instead, create a fresh new order with the amended prices (the DEC-366 amendment logic already computed new stop/target prices — use those)
     - Submit as a brand-new order (new order ID, not an amendment)
     - If the fresh order also gets rejected: THEN enter the normal stop resubmission flow (subject to retry cap from above)
   - Log INFO "Bracket amendment rejected for {symbol} — resubmitting as fresh order"

### Duplicate Fill Deduplication (Issue 5)

5. **In `argus/execution/order_manager.py`**, add fill dedup:
   - Add `_last_fill_state: dict[str, float]` — maps IBKR order_id (str) → last seen cumulative_filled_qty
   - In the fill callback (wherever order fills are processed):
     - Extract the order's IBKR order ID and cumulative filled quantity from the fill event
     - If `(order_id)` is in `_last_fill_state` AND `cumulative_qty == _last_fill_state[order_id]`: log DEBUG "Duplicate fill callback ignored: order {order_id} cumulative {qty}". Return early (do not process).
     - Otherwise: update `_last_fill_state[order_id] = cumulative_qty` and process normally
   - Clear `_last_fill_state` entries when the associated position closes

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/intelligence/`
- Do NOT change: signal generation, quality pipeline, risk manager logic, bracket amendment price calculation (DEC-366)
- Preserve: `_flatten_pending` guard behavior, normal bracket placement flow, normal fill processing for non-duplicate callbacks
- The emergency flatten must work even when the account has no buying power (it's a SELL, not a BUY)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~12):
  1. Stop rejected once → retry (attempt 2)
  2. Stop rejected twice → retry (attempt 3)
  3. Stop rejected 3 times → no retry, emergency flatten triggered
  4. Emergency flatten respects _flatten_pending guard
  5. Retry counter resets on successful stop placement
  6. Retry counter cleared on position close
  7. Exponential backoff timing (1s, 2s, 4s progression)
  8. Revision-rejected detection → fresh order submitted (not retry)
  9. Fresh order after revision-rejected also fails → enters retry flow
  10. Duplicate fill (same order_id, same cumulative_qty) → ignored
  11. Legitimate partial fill (same order_id, increased cumulative_qty) → processed
  12. Fill dedup state cleared on position close
- Minimum new test count: 12
- Test command: `python -m pytest tests/execution/ -x -q`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 12+ new tests written and passing
- [ ] Close-out report written to `docs/sprints/sprint-27.95/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Normal bracket placement unchanged | Run existing bracket tests |
| Normal fill processing unchanged for first fill | Run existing fill tests |
| `_flatten_pending` guard intact | Run existing flatten tests |
| Bracket amendment price calculation (DEC-366) unchanged | Verify amendment logic not modified |
| Stop order success path unaffected | Test stop placed → acknowledged → no retry counter |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.
**Write the close-out report to:** `docs/sprints/sprint-27.95/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-27.95/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.95/session-2-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/execution/ -x -q`
5. Files NOT modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/`, `argus/data/`

Review report: `docs/sprints/sprint-27.95/session-2-review.md`

## Post-Review Fix Documentation
If CONCERNS reported and fixed, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify stop retry cap is per-symbol, not global (one symbol's retries don't affect another)
2. Verify emergency flatten uses existing close_position path (not a raw IBKR call)
3. Verify revision-rejected detection uses substring match, not exact match (IBKR may vary wording)
4. Verify duplicate fill dedup uses IBKR order ID (not ARGUS internal order ID) — fills come from IBKR callbacks
5. Verify partial fills with increasing cumulative quantity still work correctly
6. Verify no asyncio.sleep calls in non-async context

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Normal position lifecycle unchanged
- [ ] `_flatten_pending` guard (DEC-363) intact
- [ ] Bracket amendment (DEC-366) price calculation intact
- [ ] Fill processing for non-duplicate callbacks unchanged
- [ ] Full test suite passes, no hangs

## Sprint-Level Escalation Criteria (for @reviewer)
1. Stop resubmission cap causes unprotected positions → halt, design fallback
2. Pre-flight test failures → investigate
3. Test hang → halt
