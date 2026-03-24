# Sprint 27.65, Session S1: Order Management Safety

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md`
   - `argus/execution/order_manager.py`
   - `argus/execution/ibkr_broker.py`
   - `__main__.py` (shutdown sequence)
   - `docs/sprints/sprint-27.65/review-context.md`
2. Run the test baseline (DEC-328):
   Full suite: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   Expected: ~3,337 tests, all passing
3. Verify you are on branch: `main` (or create `sprint-27.65` if preferred)

## Objective
Fix the critical order management bug where duplicate flatten orders are
submitted every 5 seconds for time-stopped positions, creating phantom
positions at IBKR. Add graceful shutdown order cancellation and periodic
position reconciliation.

## Background
During the March 24, 2026 paper trading session:
- CNK: 36 duplicate SELL orders (1,759 shares each) over 3 minutes
- CSTM: 58 duplicate SELL orders (2,049 shares each) over 5 minutes
- Result: $2.8M in phantom short positions at IBKR, account NAV distorted
- Root cause: `_check_time_stops()` runs every 5 seconds and submits a new
  flatten order each cycle without checking if one is already pending

## Requirements

### R1: Flatten-pending guard in OrderManager
1. Add `_flatten_pending: dict[str, str]` instance variable (symbol → order_id)
   initialized to empty dict in `__init__`.
2. In the time-stop check path (wherever the flatten/close order is submitted
   for a timed-out position):
   - Before submitting: check if `symbol in self._flatten_pending`. If yes,
     check the status of the pending order. Only resubmit if the previous
     order has been confirmed as cancelled or rejected — NOT if it's merely
     unfilled/pending.
   - On submission: set `self._flatten_pending[symbol] = order_id`
3. Clear the flatten_pending entry when:
   - The flatten order fills (position close path)
   - The flatten order is explicitly cancelled by IBKR (error 202)
   - The flatten order is rejected (error callback)
4. On position close (any reason — stop, target, time-stop, manual), clear
   the flatten_pending entry for that symbol if present.
5. Log at INFO level when a flatten is suppressed due to pending guard:
   `"Time-stop for {symbol}: flatten already pending (order {order_id})"`

### R2: Graceful shutdown order cancellation
1. In `__main__.py` shutdown sequence (the signal handler or lifespan shutdown),
   BEFORE disconnecting from IBKR:
   - Call `broker.cancel_all_orders()` (new method) or equivalent
   - Wait up to 5 seconds for cancellation confirmations
   - Log: `"Shutdown: cancelled {N} open orders at IBKR"`
2. In `IBKRBroker`, add a `cancel_all_orders()` method that calls
   `self.ib.reqGlobalCancel()` and waits briefly for confirmations.
3. This must happen BEFORE the broker disconnect, not after.

### R3: Periodic position reconciliation
1. Add a new async task in `__main__.py` (market hours only, 60-second interval,
   same pattern as regime reclassification task):
   - Call `order_manager.reconcile_positions(broker_positions)` where
     `broker_positions` comes from `broker.get_positions()` (new method)
   - IBKRBroker.get_positions() calls `self.ib.positions()` and returns a
     dict of {symbol: quantity}
2. `OrderManager.reconcile_positions(broker_positions: dict[str, float])`:
   - Compare internal open positions dict against broker_positions
   - For each discrepancy, log at WARNING:
     `"Position mismatch: {symbol} — ARGUS={internal_qty}, IBKR={broker_qty}"`
   - Do NOT auto-correct. Warn only.
   - Return a list of discrepancies (for the API endpoint)
3. Add REST endpoint `GET /api/v1/positions/reconciliation`:
   - Returns the latest reconciliation result (timestamp + list of discrepancies)
   - If no discrepancies: `{"status": "synced", "discrepancies": []}`

## Constraints
- Do NOT modify: Risk Manager logic, strategy evaluation paths, event bus
- Do NOT change: the normal stop-loss or target-hit order flow
- Do NOT auto-correct position discrepancies — warn only
- The flatten_pending guard must NOT prevent legitimate re-flattening if IBKR
  explicitly rejects or cancels the first attempt
- SimulatedBroker and AlpacaBroker should not be affected (guard for BrokerSource)

## Canary Tests
Before making changes, verify these existing behaviors still work after:
1. A position that hits its stop loss results in exactly one SELL order
2. A position that hits T1 results in exactly one partial SELL order
3. The 5-second fallback poll still functions for open positions

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_flatten_pending_prevents_duplicate_orders` — time-stop fires, verify only 1 order submitted across 3 poll cycles
  2. `test_flatten_pending_clears_on_fill` — flatten fills, verify flag cleared, subsequent time-stop can re-trigger
  3. `test_flatten_pending_clears_on_cancel` — flatten cancelled by broker, verify flag cleared
  4. `test_flatten_pending_clears_on_reject` — flatten rejected, verify flag cleared
  5. `test_flatten_pending_clears_on_position_close` — position closed by stop/target, verify flag cleared
  6. `test_graceful_shutdown_cancels_orders` — shutdown sequence calls cancel_all_orders before disconnect
  7. `test_reconciliation_detects_mismatch` — internal has position X, broker has position Y, verify warning logged
  8. `test_reconciliation_synced` — internal matches broker, verify "synced" result
  9. `test_reconciliation_endpoint_returns_result` — API returns latest reconciliation
  10. `test_flatten_pending_does_not_block_normal_stop_loss` — stop loss path unaffected by flatten guard
- Minimum new test count: 10
- Test command: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Normal stop-loss produces exactly 1 order | Unit test: mock broker, count order submissions |
| Normal target-hit produces exactly 1 order | Unit test: mock broker, count order submissions |
| Time-stop with pending guard produces exactly 1 order over 3 cycles | New test |
| Flatten resubmits after explicit cancel | New test |
| Shutdown calls reqGlobalCancel | New test with mock broker |
| SimulatedBroker unaffected | Existing backtest tests pass |

## Definition of Done
- [ ] All requirements (R1, R2, R3) implemented
- [ ] All existing tests pass
- [ ] 10+ new tests written and passing
- [ ] No changes to Risk Manager, strategy evaluation, or event bus
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

Write the close-out report to:
docs/sprints/sprint-27.65/S1-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.65/review-context.md`
2. Close-out path: `docs/sprints/sprint-27.65/S1-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/execution/ tests/api/ -x -q`
5. Files NOT to modify: `argus/core/risk_manager.py`, `argus/strategies/`, `argus/core/event_bus.py`

Write review to: `docs/sprints/sprint-27.65/S1-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify flatten_pending guard prevents duplicate orders (not just delays them)
2. Verify flatten_pending clears on ALL exit paths (fill, cancel, reject, position close)
3. Verify shutdown cancel happens BEFORE broker disconnect
4. Verify reconciliation is warn-only, never auto-corrects
5. Verify no race conditions between flatten submission and status check
6. Verify SimulatedBroker path is not broken by new guard

## Sprint-Level Escalation Criteria (for @reviewer)
Escalate if:
1. Any change introduces a path where orders can be submitted without risk checks
2. Position reconciliation auto-corrects instead of warning
3. Flatten guard could prevent a legitimate stop-loss from executing
4. Changes break SimulatedBroker or backtest paths
