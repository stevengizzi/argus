# Sprint 27.65, Session S1: Order Management Safety — Close-Out Report

## Change Manifest

| File | Change |
|------|--------|
| `argus/execution/order_manager.py` | Added `_flatten_pending` guard dict, `_last_reconciliation` dict, `reconcile_positions()`, `last_reconciliation` property; flatten guard checks in `_flatten_position()`, clears in `_close_position()` and `on_cancel()`; `_flatten_pending` cleared in `reset_daily_state()` |
| `argus/execution/broker.py` | Added `cancel_all_orders()` abstract method |
| `argus/execution/ibkr_broker.py` | Implemented `cancel_all_orders()` via `reqGlobalCancel()` |
| `argus/execution/alpaca_broker.py` | Implemented `cancel_all_orders()` via Alpaca SDK |
| `argus/execution/simulated_broker.py` | Implemented `cancel_all_orders()` (clears pending brackets) |
| `argus/api/routes/positions.py` | Added `ReconciliationResponse` model and `GET /positions/reconciliation` endpoint |
| `argus/main.py` | Added `_reconciliation_task` periodic loop (60s, market hours); shutdown calls `broker.cancel_all_orders()` before disconnect |
| `tests/execution/test_order_manager_safety.py` | 13 new tests |
| `tests/strategies/test_sprint_27_65_s3.py` | 14 new tests (S3 scope) |

## R1: Flatten-Pending Guard

### Root Cause
`_check_time_stops()` runs every 5 seconds. For a time-stopped position, it called `_flatten_position()` on every cycle. Each call submitted a new market SELL order without checking if one was already pending. Over 3–5 minutes: 36–58 duplicate SELL orders per symbol, creating phantom short positions at IBKR.

### Fix
- `_flatten_pending: dict[str, str]` (symbol → order_id) tracks in-flight flatten orders
- `_flatten_position()` checks this dict before submitting; logs "flatten already pending" and returns early if present
- Flag cleared on: fill (via `_close_position()`), cancel (via `on_cancel()`), position close (any reason), and daily reset
- Normal stop/target paths are unaffected — they go through `on_fill()` → `_close_position()`, not `_flatten_position()`

### Tests (6)
1. `test_flatten_pending_prevents_duplicate_orders` — 3 cycles, 1 order
2. `test_flatten_pending_clears_on_fill` — fill clears flag
3. `test_flatten_pending_clears_on_cancel` — broker cancel clears flag
4. `test_flatten_pending_clears_on_reject` — rejection clears flag, retry works
5. `test_flatten_pending_clears_on_position_close` — stop-loss close clears flag
6. `test_flatten_pending_does_not_block_normal_stop_loss` — stop fill path unaffected

## R2: Graceful Shutdown Order Cancellation

### Fix
- Added `cancel_all_orders() -> int` to Broker ABC
- IBKRBroker: calls `reqGlobalCancel()`, waits `min(5s, count * 0.5s)`
- AlpacaBroker: calls `cancel_orders()` on trading client
- SimulatedBroker: clears `_pending_brackets`
- Shutdown sequence in `main.py`: calls `broker.cancel_all_orders()` BEFORE `order_manager.stop()` and broker disconnect

### Tests (2)
1. `test_graceful_shutdown_cancels_orders` — mock broker returns count
2. `test_ibkr_cancel_all_orders` — verifies `reqGlobalCancel()` called

## R3: Periodic Position Reconciliation

### Fix
- `OrderManager.reconcile_positions(broker_positions)`: compares internal vs broker positions, logs WARNING on mismatch, stores result as `_last_reconciliation`. Does NOT auto-correct.
- `_run_position_reconciliation()` in `main.py`: async task, 60-second interval, market hours only (9:30–16:00 ET), calls `broker.get_positions()` then `reconcile_positions()`
- REST endpoint `GET /api/v1/positions/reconciliation`: returns latest result or default "synced"

### Tests (5)
1. `test_reconciliation_detects_mismatch` — internal=100, broker=200
2. `test_reconciliation_synced` — matching positions
3. `test_reconciliation_detects_broker_only_position` — broker has unknown symbol
4. `test_reconciliation_endpoint_returns_result` — API returns mismatch data
5. `test_reconciliation_no_auto_correct` — positions unchanged after reconciliation

## Judgment Calls

1. **Warn-only reconciliation** — per spec. No auto-correction because discrepancies may be timing artifacts (order in flight) rather than real mismatches.
2. **`reqGlobalCancel()` over per-order cancellation** — single IB API call is more reliable than iterating and cancelling individually, especially during shutdown.
3. **Reconciliation stores result on OrderManager** — simpler than a separate service. API reads from `last_reconciliation` property.

## Scope Verification

- [x] Flatten-pending guard prevents duplicate flatten orders
- [x] Graceful shutdown cancels orders before disconnect
- [x] Periodic reconciliation with API endpoint
- [x] All existing tests pass
- [x] 13+ new tests written and passing

## Self-Assessment

**CLEAN** — All S1 scope items completed. No deviations from spec. Normal stop/target/time-stop paths verified unaffected.

## Context State

**YELLOW** — Session started fresh but continued from compacted context. All implementation was re-verified against the diff before close-out.

## Post-Review Fixes (S2)

Fixes applied in Sprint 27.65 S2 based on S1 Tier 2 review (verdict: CONCERNS):

| Finding | Severity | Resolution |
|---------|----------|------------|
| Shutdown integration test only mocks broker, doesn't verify ordering | MEDIUM | Added `test_shutdown_sequence_ordering` in S2 — verifies cancel_all_orders → order_manager.stop → broker.disconnect call order |
| `_last_reconciliation` typed as `dict[str, object]`, `type: ignore` in endpoint | LOW | Replaced with `ReconciliationResult` dataclass. `type: ignore[arg-type]` removed from `positions.py`. |
| SimulatedBroker `cancel_all_orders()` described as "no-op" in close-out | LOW | Corrected: SimulatedBroker's `cancel_all_orders()` clears `_pending_brackets` (not a no-op). |
