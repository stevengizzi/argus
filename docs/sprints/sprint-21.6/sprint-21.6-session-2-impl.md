# Sprint 21.6, Session 2: OrderManager Integration + Execution Record Tests

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/execution_record.py` — Session 1 output, the ExecutionRecord dataclass and save function
   - `argus/execution/order_manager.py` — full file, focus on: `PendingManagedOrder` (lines 93–108), `on_approved()` (lines 191–361), `_handle_entry_fill()` (lines 470–553)
   - `argus/core/events.py` lines 159–187 — SignalEvent.entry_price, OrderApprovedEvent.signal
   - `argus/core/events.py` lines 215–225 — OrderFilledEvent.fill_price, fill_quantity
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/execution/ -x -q
   ```
   Expected: all passing (full suite was confirmed by Session 1 close-out)
3. Verify you are on branch: `main`

## Objective
Wire ExecutionRecord logging into OrderManager's entry fill handler. When an entry order fills, capture the expected vs actual fill price and persist an ExecutionRecord to the database. This logging must be completely fire-and-forget — any failure in record creation or persistence must be caught and logged, never disrupting the order management flow.

## Requirements

1. **Modify `PendingManagedOrder` in `argus/execution/order_manager.py`** — add two new fields:
   - `expected_fill_price: float = 0.0` — set from `signal.entry_price` when the order is submitted
   - `signal_timestamp: datetime | None = None` — set from `self._clock.now()` when the order is submitted

   These fields provide the "expected" side of the execution quality comparison.

2. **Modify `on_approved()` in `argus/execution/order_manager.py`** — when creating the entry `PendingManagedOrder` (around line 297), set the two new fields:
   ```python
   pending = PendingManagedOrder(
       ...
       expected_fill_price=signal.entry_price,
       signal_timestamp=self._clock.now(),
   )
   ```
   This captures the expected fill price at the moment the signal was generated. No other changes to `on_approved()`.

3. **Modify `_handle_entry_fill()` in `argus/execution/order_manager.py`** — after the existing ManagedPosition creation and PositionOpenedEvent publication (after the `logger.info` at the end of the method), add an execution record logging block:

   ```python
   # --- Execution Quality Logging (DEC-358 §5.1) ---
   try:
       from argus.execution.execution_record import (
           create_execution_record,
           save_execution_record,
       )
       record = create_execution_record(
           order_id=pending.order_id,
           symbol=pending.symbol,
           strategy_id=pending.strategy_id,
           side="BUY",  # Long-only V1 (DEC-011)
           expected_fill_price=pending.expected_fill_price,
           actual_fill_price=event.fill_price,
           order_size_shares=filled_shares,
           signal_timestamp=pending.signal_timestamp,
           fill_timestamp=self._clock.now(),
           avg_daily_volume=None,  # TODO: wire UM reference data when available
           bid_ask_spread_bps=None,  # Requires L1 data (Standard plan = None)
       )
       if self._db_manager is not None:
           await save_execution_record(self._db_manager, record)
           logger.debug("Execution record saved: %s", record.record_id)
       else:
           logger.debug("No DB manager — execution record not persisted")
   except Exception:
       logger.warning(
           "Failed to save execution record for %s (non-critical)",
           pending.symbol,
           exc_info=True,
       )
   ```

   **Critical:** The import is inside the try block to avoid import-time failures. The entire block is wrapped in try/except. The `except Exception` catches everything and logs at WARNING. The order fill flow (ManagedPosition creation, PositionOpenedEvent) has already completed before this block runs.

4. **Add `self._db_manager` access to OrderManager** — check if OrderManager already has access to a DatabaseManager instance. Look at `__init__()` parameters. If it does not have one:
   - Add `db_manager: DatabaseManager | None = None` as an optional parameter to `__init__()`
   - Store as `self._db_manager = db_manager`
   - This is optional/nullable so it doesn't break any existing callers (backward compatible)
   - Check `server.py` or wherever OrderManager is instantiated to see if a db_manager is available to pass in. If wiring is straightforward, wire it. If it requires changes to multiple files beyond server.py, defer the wiring and leave `db_manager=None` — the logging will simply not persist until wired.

   **Alternative:** If OrderManager already has access to a db_manager (e.g., through trade_logger or another component), use that existing access path instead of adding a new parameter.

## Constraints
- Do NOT modify: any file in `argus/strategies/`, `argus/backtest/`, `argus/core/events.py`, `argus/core/risk_manager.py`, `argus/ui/`, `argus/api/`
- Do NOT change: the order of operations in `_handle_entry_fill()` — execution record logging goes AFTER ManagedPosition creation and PositionOpenedEvent publication
- Do NOT change: the order of operations in `on_approved()` — only add field values to the PendingManagedOrder constructor
- Do NOT change: fill routing logic in `on_fill()`
- Do NOT make: execution record logging a prerequisite for anything — pure fire-and-forget
- The try/except block MUST catch `Exception` (broad catch), not specific exceptions

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to add in `tests/execution/test_execution_record.py` (extending Session 1's file):
  1. `test_handle_entry_fill_creates_execution_record` — mock DB, verify save_execution_record called with correct fields after entry fill
  2. `test_handle_entry_fill_continues_on_record_failure` — mock save_execution_record to raise, verify ManagedPosition still created and PositionOpenedEvent still published
  3. `test_pending_order_carries_expected_price` — verify PendingManagedOrder has expected_fill_price set from signal.entry_price
  4. `test_pending_order_carries_signal_timestamp` — verify signal_timestamp is set from clock.now()
  5. `test_execution_record_slippage_computation_realistic` — test with realistic prices (e.g., entry_price=$45.50, fill_price=$45.52 → verify bps)
- Minimum new test count: 5
- Test command: `python -m pytest tests/execution/test_execution_record.py -x -q`

## Definition of Done
- [ ] `PendingManagedOrder` has `expected_fill_price` and `signal_timestamp` fields
- [ ] `on_approved()` sets both fields on the entry PendingManagedOrder
- [ ] `_handle_entry_fill()` creates and persists ExecutionRecord after fill processing
- [ ] Exception handling is robust — DB failures logged at WARNING, never propagate
- [ ] All 5+ new tests passing
- [ ] All existing tests still pass (especially all `test_order_manager*.py` tests)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing OM tests pass unchanged | `python -m pytest tests/execution/test_order_manager.py tests/execution/test_order_manager_t2.py -x -q` |
| PendingManagedOrder defaults are backward-compatible | `expected_fill_price` defaults to 0.0, `signal_timestamp` defaults to None |
| No behavioral change to fill routing | `on_fill()` method not modified |
| Execution record block is after position creation | Code inspection: ManagedPosition + PositionOpenedEvent precede the try/except block |
| Broad exception catch used | `except Exception:` not `except (SpecificException):` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
`docs/sprints/sprint-21.6/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-21.6/review-context.md`
2. The close-out report path: `docs/sprints/sprint-21.6/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/execution/ -x -q`
5. Files that should NOT have been modified: any file in `argus/strategies/`, `argus/backtest/`, `argus/core/events.py`, `argus/core/risk_manager.py`, `argus/ui/`, `argus/api/`

The @reviewer will write its report to:
`docs/sprints/sprint-21.6/session-2-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same session, update both the close-out and review report files per the Post-Review Fix Documentation protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify execution record logging block is AFTER ManagedPosition creation and PositionOpenedEvent publication — not before, not interspersed
2. Verify the try/except uses broad `except Exception:` — not a narrow catch that could miss unexpected errors
3. Verify `expected_fill_price` on PendingManagedOrder comes from `signal.entry_price`, not from `event.fill_price` or any other source
4. Verify existing `test_order_manager.py` and `test_order_manager_t2.py` still pass without modification
5. Verify no new imports at module level in order_manager.py (the execution_record import should be inside the try block)
6. If OrderManager was given a new `db_manager` parameter: verify it's optional with `None` default (backward compatible)

## Sprint-Level Regression Checklist
*(See `docs/sprints/sprint-21.6/review-context.md`)*

## Sprint-Level Escalation Criteria
*(See `docs/sprints/sprint-21.6/review-context.md`)*
