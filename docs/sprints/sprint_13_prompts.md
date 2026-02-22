# Sprint 13 — Claude Code Prompts

> **Pre-requisite:** Commit `docs/sprints/sprint_13_spec.md` to the repo before starting.
> **Each prompt assumes:** Claude Code reads `CLAUDE.md`, `docs/sprints/sprint_13_spec.md`, and relevant source files.

---

## Prompt 1: Foundation — IBKRConfig + BrokerSource Enum

Read `docs/sprints/sprint_13_spec.md` (the full Sprint 13 spec). This is the IBKRBroker adapter sprint — ~10 prompts, ~91 tests, targeting ~765+ total.

This first prompt establishes the config foundation.

**Tasks:**

1. Add `ib_async>=2.1.0` to dependencies (requirements.txt and/or pyproject.toml).

2. In `argus/core/config.py`:
   - Add `BrokerSource` enum (`alpaca`, `ibkr`, `simulated`) — same pattern as `DataSource` enum from Sprint 12 (DEC-090).
   - Add `IBKRConfig` Pydantic model with fields per spec Section 4, Component 1. Key fields: host (default "127.0.0.1"), port (default 4002 — paper), client_id (default 1), account (default ""), timeout_seconds (30), readonly (False), reconnection params, max_order_rate_per_second (45.0).
   - Add `broker_source: BrokerSource = BrokerSource.SIMULATED` and `ibkr: IBKRConfig = IBKRConfig()` to `SystemConfig`.

3. Update `config/brokers.yaml` — add `broker_source` field and `ibkr:` section per spec.

4. Tests (3): config loading from YAML with ibkr values, default values correct, validation (e.g., port range, positive timeout).

Run all tests. Ruff clean.

---

## Prompt 2: Contracts + Error Handling

Read `docs/sprints/sprint_13_spec.md` Section 4, Components 2 and 3.

**Tasks:**

1. Create `argus/execution/ibkr_contracts.py`:
   - `IBKRContractResolver` class with `get_stock_contract()`, `qualify_contracts()`, `clear_cache()`.
   - V1 is US equities only: `Stock(symbol, 'SMART', 'USD')`.
   - Cache contracts by symbol. `qualify_contracts()` takes an IB instance and list of symbols, calls `ib.qualifyContractsAsync()`, caches results.
   - See spec for full code sketch.

2. Create `argus/execution/ibkr_errors.py`:
   - `IBKRErrorSeverity` enum (CRITICAL, WARNING, INFO).
   - `IBKRErrorInfo` dataclass.
   - `IBKR_ERROR_MAP` dict with all error codes from spec (1100, 1101, 1102, 502, 504, 103, 104, 105, 110, 135, 161, 200, 201, 202, 203, 321, 354, 10167, 2103, 2104, 2105, 2106, 2158).
   - `classify_error()`, `is_order_rejection()`, `is_connection_error()` functions.

3. Tests for contracts (4): stock creation, cache hit, qualification with mock IB, SMART exchange default.

4. Tests for errors (6): classify known code, classify unknown code (defaults to WARNING), is_order_rejection true/false, is_connection_error true/false, critical severity codes correct.

Run all tests. Ruff clean.

---

## Prompt 3: IBKRBroker Core — Constructor + Connection

Read `docs/sprints/sprint_13_spec.md` Section 4, Component 4a.

**Tasks:**

1. Create `argus/execution/ibkr_broker.py` with:
   - `IBKRBroker(Broker)` class.
   - Constructor: takes `IBKRConfig` and `EventBus`. Creates `IB()` instance, wires event subscriptions (`orderStatusEvent`, `errorEvent`, `disconnectedEvent`), initializes ULID↔IBKR ID mapping dicts, creates `IBKRContractResolver`.
   - `async connect()`: calls `await self._ib.connectAsync(...)` with config params. Sets `_connected = True`. Snapshots positions for reconnection verification. Logs connection info.
   - `async disconnect()`: calls `self._ib.disconnect()`. Sets `_connected = False`.
   - `is_connected` property: `self._connected and self._ib.isConnected()`.

2. **Important:** ib_async is asyncio-native — NO `call_soon_threadsafe()` needed (unlike Databento Sprint 12). Event handlers fire on the same event loop.

3. Create test file `tests/execution/test_ibkr_broker.py` with `mock_ib` fixture per spec Section 7. Use `unittest.mock.patch` to inject mock IB instance into IBKRBroker.

4. Tests (8): connect success, connect failure raises, disconnect, is_connected true/false, state tracking after connect/disconnect, event subscription wiring verified, account parameter passthrough, position snapshot on connect.

Run all tests. Ruff clean.

---

## Prompt 4: Order Submission

Read `docs/sprints/sprint_13_spec.md` Section 4, Component 4b.

**Tasks:**

1. Add to `IBKRBroker`:
   - `async place_order(self, order: Order) -> OrderResult`: resolve contract, build ib_async order, generate ULID, set `orderRef = ulid`, place order, store ID mapping, return result.
   - `_build_ib_order(self, order: Order) -> IBOrder`: map ARGUS order types to ib_async types (market→MarketOrder, limit→LimitOrder, stop→StopOrder, stop_limit→IBOrder with orderType="STP LMT"). Set `tif="DAY"`, `outsideRth=False` on all.
   - Not-connected check returns error OrderResult.

2. Tests (10): market order placed, limit order with price, stop order with price, stop-limit order with both prices, ULID generated and mapped, orderRef set on ib_async order, IBKR ID mapped bidirectionally, not-connected returns error, invalid order type raises ValueError, buy/sell action mapping correct.

Run all tests. Ruff clean.

---

## Prompt 5: Native Bracket Orders (DEC-093)

Read `docs/sprints/sprint_13_spec.md` Section 4, Component 4c. This is the key differentiator from AlpacaBroker.

**Tasks:**

1. Add to `IBKRBroker`:
   - `async place_bracket_order(self, entry, stop, targets) -> BracketOrderResult`
   - **Native multi-leg bracket:** parent (entry) + stop + T1 + optional T2, all linked via `parentId`.
   - **Transmit flag pattern:** `transmit=False` on parent and all children except the last. `transmit=True` on the last child triggers atomic submission of the entire group.
   - Each leg gets its own ULID stored in `orderRef`. All legs registered in ID mapping dicts.
   - `BracketOrderResult` includes `entry_order_id`, `stop_order_id`, and `target_order_ids` (list — [t1] or [t1, t2]).

2. Implementation flow per spec:
   - Build parent from entry Order, set `transmit=False`, place to get orderId.
   - Build stop as StopOrder with `parentId=parent_id`, set `transmit` based on whether targets exist.
   - Loop over targets: build each as LimitOrder with `parentId=parent_id`. Last target gets `transmit=True`.
   - Return BracketOrderResult with all ULIDs.

3. Tests (10): bracket with T1 only (2 children), bracket with T1+T2 (3 children), market entry bracket, limit entry bracket, parentId set correctly on all children, transmit=False on parent and intermediates, transmit=True on last child only, all ULIDs mapped in both dicts, orderRef set on every leg, empty targets list works (entry + stop only).

Run all tests. Ruff clean.

---

## Prompt 6: Fill Streaming + Event Handlers

Read `docs/sprints/sprint_13_spec.md` Section 4, Component 4d.

**Tasks:**

1. Add to `IBKRBroker`:
   - `_on_order_status(self, trade: Trade)`: ib_async event callback. Schedules `_handle_order_status` via `asyncio.ensure_future()`.
   - `async _handle_order_status(self, trade: Trade)`: looks up ULID from IBKR order ID. Based on status:
     - `"Filled"` → publish `OrderFilledEvent` with avg fill price and filled quantity
     - `"Cancelled"` → publish `OrderCancelledEvent`
     - `"Inactive"` → publish `OrderCancelledEvent` with rejection reason (IBKR uses Inactive for rejections)
     - `"Submitted"` → publish `OrderSubmittedEvent`
     - `"PreSubmitted"` → debug log only (bracket children before parent fills)
     - Other → debug log
   - Unknown order IDs (not in mapping) → debug log, ignore.
   - `_on_error(self, reqId, errorCode, errorString, contract)`: classify error, handle by severity. For order rejections, publish OrderCancelledEvent. For connection errors, log (reconnection handled elsewhere).
   - `_map_ib_order_type(ib_type: str) -> str`: static method mapping MKT→market, LMT→limit, STP→stop, STP LMT→stop_limit.

2. Tests (12): filled event published with correct price/qty, cancelled event published, inactive (rejected) event published with reason, submitted event published, pre-submitted logged only, unknown order ID ignored, error classification routes correctly, critical error logged, order rejection via error event publishes cancel, order type mapping all variants, partial fill handling (filled < total), fill with zero avg price edge case.

Run all tests. Ruff clean.

---

## Prompt 7: Cancel, Modify, Account Queries, Flatten

Read `docs/sprints/sprint_13_spec.md` Section 4, Components 4e, 4f, 4g.

**Tasks:**

1. Add to `IBKRBroker`:
   - `async cancel_order(order_id) -> bool`: look up IBKR ID, find Trade in `self._ib.trades()`, call `self._ib.cancelOrder(trade.order)`. Return False if not found.
   - `async modify_order(order_id, modifications) -> OrderResult`: find Trade, modify in-place (STP orders use `auxPrice`, others use `lmtPrice`; `totalQuantity` for size), re-place with `self._ib.placeOrder()`.
   - `async get_order_status(order_id) -> OrderStatus`: look up Trade, return status/filled/remaining/avgPrice.
   - `async get_positions() -> list[Position]`: read `self._ib.positions()`, convert to ARGUS Position model, filter out zero-quantity.
   - `async get_account() -> AccountInfo`: read `self._ib.accountValues()`, filter USD, extract NetLiquidation, TotalCashValue, BuyingPower, MaintMarginReq, DayTradesRemaining.
   - `async flatten_all() -> list[OrderResult]`: call `self._ib.reqGlobalCancel()`, sleep 0.5s, then close all positions via MarketOrder. Both long and short positions.
   - `_find_trade_by_order_id(ib_order_id) -> Trade | None`: scan `self._ib.trades()`.
   - `_is_numeric(value) -> bool`: static helper for accountValues parsing.

2. Tests (16 total):
   - Cancel (3): cancel existing, cancel unknown returns False, cancel not-found trade
   - Modify (3): modify stop price (auxPrice), modify limit price (lmtPrice), modify quantity
   - Account (6): positions with holdings, positions empty, positions filters zero-qty, account info all fields, buying power present, non-USD values filtered
   - Flatten (4): flatten with long positions, flatten with short positions, flatten empty portfolio, flatten cancels pending orders first

Run all tests. Ruff clean.

---

## Prompt 8: Reconnection Logic + Error Integration

Read `docs/sprints/sprint_13_spec.md` Section 4, Component 5.

**Tasks:**

1. Add to `IBKRBroker`:
   - `_on_disconnected(self)`: set `_connected = False`, schedule `_reconnect()` via `asyncio.ensure_future()` if not already reconnecting. Double-reconnect guard via `_reconnecting` flag.
   - `async _reconnect(self)`: snapshot pre-disconnect positions. Loop up to `reconnect_max_retries`:
     - Calculate delay: `min(base_delay * 2^attempt, max_delay)` — exponential backoff with cap.
     - `await asyncio.sleep(delay)`, then try `await self.connect()`.
     - On success: compare pre/post positions. Log warning if mismatch. Set `_reconnecting = False`. Return.
     - On failure: log warning, continue loop.
   - If all retries exhausted: log CRITICAL, set `_reconnecting = False`. (SystemAlertEvent deferred to DEF-014.)

2. Tests (6): successful reconnect first attempt, successful reconnect after 2 failures, max retries exceeded logs critical, position verification passes (same positions), position mismatch logs warning, no double-reconnect (second disconnect during reconnection ignored), backoff delay values correct (1s, 2s, 4s, 8s... capped at max).

Run all tests. Ruff clean.

---

## Prompt 9: State Reconstruction + Order Manager T2 Changes

Read `docs/sprints/sprint_13_spec.md` Section 4, Components 6 and 7.

This prompt has two parts: IBKRBroker reconstruction AND Order Manager changes for native T2 brackets (DEC-093).

**Part A — IBKRBroker Reconstruction:**

1. Add to `IBKRBroker`:
   - `async reconstruct_state(self) -> dict`: read `self._ib.positions()` and `self._ib.openTrades()` (auto-fetched by ib_async on connect). Scan open trades for `orderRef` field to recover ULID mappings. Return dict with `"positions"` (list of Position) and `"open_orders"` (list of order dicts).
   - `_convert_position(ib_pos) -> Position`: convert ib_async position to ARGUS Position model.

2. Tests (5): reconstruct with positions and orders, reconstruct empty state, ULID recovery from orderRef, unknown orders (no orderRef) get `unknown_` prefix, reconstruction after reconnect.

**Part B — Order Manager T2 Changes:**

3. Modify `argus/execution/order_manager.py`:
   - `ManagedPosition`: add `t2_order_id: str | None = None` field.
   - `PendingManagedOrder`: add `"t2"` as valid `order_type` value.
   - `on_approved()`: pass full `targets` list (T1 + T2 if present) to `broker.place_bracket_order()`. If `BracketOrderResult.target_order_ids` has >1 entry, store `target_order_ids[1]` as `t2_order_id` on ManagedPosition and register it as a `"t2"` PendingManagedOrder.
   - `on_fill()`: add `"t2"` case — when T2 fills: cancel remaining stop, update realized P&L, close position if no shares remaining.
   - `on_tick()`: when checking T2 exit, skip tick-based monitoring if `position.t2_order_id is not None` (IBKR handles it via broker-side limit). Only tick-monitor T2 when `t2_order_id is None` (Alpaca path).

4. Create `tests/execution/test_order_manager_t2.py` with tests (8): T2 fill closes position, T2 fill cancels remaining stop, Alpaca path unchanged (t2_order_id is None → tick monitors T2), IBKR path skips tick T2 check, bracket submission passes T1+T2 targets, t2 pending order registered correctly, stop fill still works (cascades), ManagedPosition.t2_order_id defaults to None.

Run all tests. Ruff clean.

---

## Prompt 10: System Integration + Final Sweep

Read `docs/sprints/sprint_13_spec.md` Section 4, Component 8.

**Tasks:**

1. Update `argus/main.py` — broker initialization phase:
   - Branch on `config.broker_source`:
     - `BrokerSource.IBKR` → import and instantiate `IBKRBroker(config.ibkr, event_bus)`, await connect.
     - `BrokerSource.ALPACA` → existing `AlpacaBroker` path.
     - `BrokerSource.SIMULATED` → existing `SimulatedBroker` path (default).
   - Follow the same pattern as `DataSource` branching from Sprint 12.

2. Update any `__init__.py` files to export new modules (IBKRBroker, IBKRContractResolver, IBKRConfig, BrokerSource).

3. Integration tests (3): IBKR broker selected when config.broker_source = "ibkr", Alpaca broker selected when "alpaca", simulated broker as default.

4. **Final sweep:**
   - Run the full test suite. All ~765+ tests must pass.
   - Run `ruff check` — zero violations.
   - Run `ruff format --check` — zero changes needed.
   - Verify no import cycles between new modules.
   - Log final test count.

5. Commit: `feat: Sprint 13 — IBKRBroker adapter with native bracket orders (DEC-093, DEC-094)`

---

## Post-Sprint: Doc Updates

After all 10 prompts complete, update docs (Claude Code can do this directly):

- `CLAUDE.md` — update current state, test count, sprint status
- `docs/10_PHASE3_SPRINT_PLAN.md` — mark Sprint 13 complete, record test count and outcome
- `docs/05_DECISION_LOG.md` — add DEC-093 and DEC-094 (content in spec Section 9)
- `docs/02_PROJECT_KNOWLEDGE.md` — update Build Track status, add Sprint 13 to completed work
- `docs/03_ARCHITECTURE.md` — update §3.3 to mark IBKRBroker as implemented

Commit: `docs: update docs for Sprint 13 completion`
