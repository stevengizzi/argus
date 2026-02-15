# ARGUS — Sprint 4a Polish (Pre-Sprint 4b Fixes)

> **Context:** Sprint 4a is complete (277 tests, 276 passing, 1 flaky). A code review identified 3 required fixes before Sprint 4b begins. This is a short polish session — no new features, just hardening.
>
> **Starting state:** All Sprint 4a code committed and pushed. 276 passing, 1 flaky (`test_reconnection_with_exponential_backoff`).
> **Target end state:** 280+ tests, 0 flaky, ruff clean, committed and pushed.

---

## Fix 1: Fix the Flaky Reconnection Test

**File:** `tests/data/test_alpaca_data_service.py`  
**Test:** `TestAlpacaDataServiceReconnection::test_reconnection_with_exponential_backoff`  
**Problem:** The test is timing-dependent — it relies on real `asyncio.sleep` delays and sometimes fails due to race conditions.

**Fix:** Mock `asyncio.sleep` so the test is deterministic. The test should verify:
1. After a WebSocket disconnect, `_run_stream_with_reconnect()` retries
2. Backoff increases exponentially (1s → 2s → 4s → ...)
3. Jitter is applied (±20%)
4. After `ws_reconnect_max_failures_before_alert` consecutive failures, a critical log is emitted

Use `unittest.mock.patch("asyncio.sleep", new_callable=AsyncMock)` and assert the sleep was called with approximately correct delay values. Don't rely on wall-clock timing at all.

**Verify:** Run the fixed test 10 times in a loop to confirm it's no longer flaky:
```bash
for i in $(seq 1 10); do pytest tests/data/test_alpaca_data_service.py::TestAlpacaDataServiceReconnection::test_reconnection_with_exponential_backoff -x -q; done
```

## Fix 2: Move `import random` to Module Level

**File:** `argus/data/alpaca_data_service.py`  
**Problem:** `import random` is inside the `_run_stream_with_reconnect()` method body instead of at the top of the file with other imports.

**Fix:** Move `import random` to the module-level imports section. One-line change.

## Fix 3: Add Missing AlpacaBroker Tests

**File:** `tests/execution/test_alpaca_broker.py`  
**Problem:** Sprint 4a delivered 19 AlpacaBroker tests against a target of ~25. The review identified these coverage gaps:

Add the following tests:

### 3a: `test_place_limit_order`
Test `place_order()` with a limit order (not just market). Verify the `LimitOrderRequest` is constructed with correct `limit_price` and submitted to `TradingClient`.

### 3b: `test_place_stop_limit_order`
Test `place_order()` with a stop-limit order. Verify `StopLimitOrderRequest` is constructed with both `stop_price` and `limit_price`.

### 3c: `test_modify_order_success`
Test `modify_order()` happy path. Place an order first, then modify it (change quantity or limit price). Verify `TradingClient.replace_order_by_id` is called with correct `ReplaceOrderRequest`.

### 3d: `test_flatten_all_with_positions`
Test `flatten_all()` when there are open positions. Mock `TradingClient.close_all_positions` to return a list of position-closing responses. Verify:
- `cancel_orders()` is called first
- `close_all_positions(cancel_orders=True)` is called
- Returned `OrderResult` list has correct length and status

### 3e: `test_get_account_with_positions_value`
Test `get_account()` when equity > cash (i.e., there are open positions contributing to equity). Verify `positions_value = equity - cash` is computed correctly and `daily_pnl = equity - last_equity` is correct.

### 3f: `test_on_trade_update_partial_fill`
Test `_on_trade_update()` with a `partial_fill` event (distinct from `fill`). Verify an `OrderFilledEvent` is published with the partial `filled_qty` and `filled_avg_price`.

**Pattern:** Follow the existing test patterns in the file. All tests use mocked `TradingClient` and `TradingStream`. No network calls. Use the existing `broker` fixture.

---

## After All Fixes

1. Run full test suite: `pytest tests/ -x` — all tests must pass, 0 failures, 0 flaky
2. Run ruff: `ruff check argus/ tests/` — must be clean
3. Report final test count (target: 280+)
4. Commit with message: `fix: Sprint 4a polish — flaky test fix, missing broker tests, import cleanup`
5. Push to origin

## What NOT To Do

- Do not start Sprint 4b work
- Do not refactor existing passing tests
- Do not add new production code beyond the `import random` move
- Do not modify any component interfaces
