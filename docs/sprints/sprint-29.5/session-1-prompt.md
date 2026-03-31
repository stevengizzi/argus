# Sprint 29.5, Session 1: Flatten/Zombie Safety Overhaul

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-29.5/review-context.md`
   - `argus/execution/order_manager.py` (focus on `_check_flatten_pending_timeouts`, `eod_flatten`, `_flatten_unknown_position`, `_reconstruct_from_broker`)
   - `argus/execution/ibkr_broker.py` (focus on error handling, `get_positions`)
   - `argus/core/config.py` (OrderManagerConfig)
2. Run the test baseline:
   Full suite: `python -m pytest --ignore=tests/test_main.py -n auto -q`
   Expected: ~4178 tests, all passing
3. Verify you are on branch: `sprint-29.5` (create from `main` if not exists)

## Objective
Fix the root cause of unfillable SELL orders (IBKR error 404 qty mismatch), add global circuit breaker for flatten retry exhaustion, make EOD flatten cover broker-only zombie positions, queue startup zombie flattens for market open, and suppress time-stop log spam for abandoned positions.

## Requirements

1. **IBKR error 404 root-cause fix** in `argus/execution/order_manager.py`:
   - In `_check_flatten_pending_timeouts()`, before resubmitting a flatten order, call `self._broker.get_positions()` to query IBKR's actual position for the symbol.
   - If IBKR reports a different qty than `position.shares_remaining`, log WARNING with both quantities and use IBKR's qty for the resubmit order.
   - If IBKR reports no position for the symbol (qty 0), remove from `_flatten_pending`, log INFO "IBKR position already closed for {symbol}", and skip resubmit.
   - Add specific detection for IBKR error code 404 in `ibkr_broker.py` — on SELL order error 404, set a flag on the order result or publish an event that the Order Manager can detect during the next timeout check.

2. **Global circuit breaker** in `argus/execution/order_manager.py`:
   - Add `max_flatten_cycles: int = 2` to `OrderManagerConfig` in `argus/core/config.py`.
   - Add `_flatten_abandoned: set[str] = field(default_factory=set)` to OrderManager `__init__`.
   - Add `_flatten_cycle_count: dict[str, int] = field(default_factory=dict)` to track cycles per symbol.
   - When `_check_flatten_pending_timeouts()` pops a symbol after `max_flatten_retries` exhaustion, increment `_flatten_cycle_count[symbol]`.
   - If `_flatten_cycle_count[symbol] >= max_flatten_cycles`, add to `_flatten_abandoned` and log ERROR once: "Flatten for {symbol} abandoned after {cycles} cycles ({total_attempts} total attempts) — requires manual intervention or EOD flatten".
   - In `_flatten_position()`, skip immediately if `symbol in self._flatten_abandoned` (log DEBUG).
   - In time-stop check loop, skip flatten attempt if `symbol in self._flatten_abandoned`.
   - `_flatten_abandoned` is cleared by `eod_flatten()` (EOD gets one final attempt for everything).

3. **EOD flatten covers broker-only positions** in `argus/execution/order_manager.py`:
   - At the end of `eod_flatten()`, after iterating `_managed_positions`, add a second pass:
     ```python
     # Pass 2: Flatten broker-only positions not tracked by Argus
     try:
         broker_positions = await self._broker.get_positions()
         managed_symbols = set(self._managed_positions.keys())
         for pos in broker_positions:
             symbol = getattr(pos, "symbol", str(pos))
             qty = int(getattr(pos, "qty", 0))
             if symbol not in managed_symbols and qty > 0:
                 logger.warning("EOD flatten: closing untracked broker position %s (%d shares)", symbol, qty)
                 await self._flatten_unknown_position(symbol, qty)
     except Exception as e:
         logger.error("EOD flatten: broker position query failed: %s", e)
     ```

4. **Startup zombie flatten queued for market open** in `argus/execution/order_manager.py`:
   - Add `_startup_flatten_queue: list[tuple[str, int]] = field(default_factory=list)` to OrderManager.
   - In `_flatten_unknown_position()`, check if market is currently open. If NOT open (before 9:30 ET or after 16:00 ET), append `(symbol, qty)` to `_startup_flatten_queue` and log INFO "Queued startup flatten for {symbol} ({qty} shares) — will execute at market open".
   - Add `async def _drain_startup_flatten_queue(self)` method that iterates the queue and submits market sells for each.
   - Subscribe to `CandleEvent` with a one-shot handler: on first CandleEvent with timestamp ≥ 9:30 ET, call `_drain_startup_flatten_queue()`, then unsubscribe.
   - Alternatively: in the poll loop, check if queue is non-empty and current time ≥ 9:30 ET.

5. **Time-stop log suppression** in `argus/execution/order_manager.py`:
   - In the time-stop check section of the poll loop, before logging "Time stop for {symbol}: open N sec", check if `symbol in self._flatten_pending or symbol in self._flatten_abandoned`.
   - If yes, use ThrottledLogger with 60s interval per symbol instead of logging every 5s.

6. **Add `max_flatten_cycles` to config** in `argus/core/config.py`:
   - Add field to `OrderManagerConfig`: `max_flatten_cycles: int = 2`
   - Add to `config/order_manager.yaml` with comment.

## Constraints
- Do NOT modify fill callback handling logic (`_handle_fill`, `_handle_entry_fill`, `_handle_target_fill`, `_handle_stop_fill`)
- Do NOT modify reconciliation logic (`_reconcile_positions`) beyond what's specified
- Do NOT modify trailing stop logic (`_trail_flatten`, trail state management)
- Do NOT modify bracket order placement logic
- Do NOT change the `_broker_confirmed` dict behavior (DEC-369)
- Preserve all existing flatten-pending timeout/retry behavior — additions only

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_flatten_error_404_requery_qty` — SELL order gets 404, next retry re-queries broker, gets correct qty, resubmits
  2. `test_flatten_error_404_position_gone` — SELL order gets 404, broker re-query shows 0 qty, flatten removed
  3. `test_flatten_circuit_breaker_single_cycle` — after max_retries exhausted, cycle count incremented
  4. `test_flatten_circuit_breaker_abandoned` — after max_cycles exhausted, symbol added to abandoned set
  5. `test_flatten_abandoned_skips_new_attempts` — time-stop check skips flatten for abandoned symbols
  6. `test_flatten_abandoned_cleared_by_eod` — eod_flatten clears abandoned set
  7. `test_eod_flatten_broker_only_positions` — eod_flatten queries broker, sells untracked positions
  8. `test_eod_flatten_broker_query_failure` — broker query fails, logged, no crash
  9. `test_startup_flatten_queue_premarket` — pre-market zombie flatten queued, not executed
  10. `test_startup_flatten_queue_drain` — queue drained on first market-hours candle
  11. `test_time_stop_log_suppressed_when_flatten_pending` — verify throttled logging
  12. `test_max_flatten_cycles_config_validation` — config loads with new field
- Minimum new test count: 12
- Test command: `python -m pytest tests/execution/test_order_manager.py tests/execution/test_ibkr_broker.py -x -q`

## Config Validation
Write a test that loads `config/order_manager.yaml` and verifies `max_flatten_cycles` is recognized by `OrderManagerConfig`.

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| `max_flatten_cycles` | `max_flatten_cycles` |

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing flatten-pending timeout still works | Run test_flatten_pending_timeout (existing) |
| EOD flatten still triggers shutdown | Verify ShutdownRequestedEvent still published |
| Broker-confirmed positions still protected | Verify _broker_confirmed dict unchanged |
| Trailing stop flatten path unchanged | Run existing trail flatten tests |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 12+ new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to `docs/sprints/sprint-29.5/session-1-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
Write the close-out report to: `docs/sprints/sprint-29.5/session-1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-29.5/review-context.md`
2. Close-out: `docs/sprints/sprint-29.5/session-1-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/execution/ -x -q`
5. Files NOT modified: `argus/intelligence/`, `argus/backtest/`, `argus/strategies/patterns/`

## Session-Specific Review Focus (for @reviewer)
1. Verify error 404 detection does NOT interfere with normal SELL order flow
2. Verify circuit breaker `_flatten_abandoned` is cleared by EOD flatten
3. Verify EOD broker-only flatten does NOT close broker-confirmed positions (check for overlap with `_broker_confirmed`)
4. Verify startup queue drain only fires once (no repeated execution)
5. Verify `_flatten_unknown_position` correctly queues vs executes based on market hours

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-29.5/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-29.5/review-context.md`
