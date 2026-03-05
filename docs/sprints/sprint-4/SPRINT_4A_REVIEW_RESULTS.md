# ARGUS — Sprint 4a Review Results

**Date:** February 15, 2026  
**Reviewer:** Claude (claude.ai strategic instance)  
**Source material:** 3 Claude Code session transcripts + Sprint 4a spec  
**Verdict:** ✅ **Sprint 4a PASSES review.** Ship it. A few items to fix before Sprint 4b begins.

---

## 1. AlpacaDataService — DataService ABC Implementation

### ✅ ABC Interface Coverage

| Method | Implemented | Notes |
|--------|-------------|-------|
| `start(symbols, timeframes)` | ✅ | Validates API keys, initializes WebSocket + REST clients, subscribes to bars/trades, starts stale monitor, warms up indicators |
| `stop()` | ✅ | Cancels stream + monitor tasks, closes data stream |
| `get_current_price(symbol)` | ✅ | Returns from `_price_cache`, raises `ValueError` if unknown |
| `get_indicator(symbol, indicator)` | ✅ | Returns from `IndicatorState`, raises `ValueError` if unknown |
| `get_historical_candles(symbol, tf, start, end)` | ✅ | REST via `StockHistoricalDataClient`, returns DataFrame |
| `get_watchlist_data(symbols)` | ✅ | Aggregates price + indicator data per symbol |
| `is_stale` | ✅ | Property returning `_is_stale` flag |

### ✅ Event Flow

- **Bar handler (`_on_bar`):** Bar → IndicatorState update → CandleEvent published → IndicatorEvents published (VWAP, ATR, SMA 9/20/50, RVOL). Correct.
- **Trade handler (`_on_trade`):** Trade → price cache update → TickEvent published. Correct.
- **TickEvent field fix:** Initially used `size=` parameter, caught and fixed to `volume=` to match model definition. ✅
- **IndicatorEvent field fix:** Initially used `indicator=` parameter, caught and fixed to `indicator_name=` to match model definition. ✅

### ✅ Indicator Warm-up

- Fetches 60 historical 1m candles via REST for each symbol.
- Feeds through IndicatorState without publishing events (warm-up only). Correct.
- Error handling per-symbol (one failure doesn't abort others). Good.

### ✅ Stale Data Monitor

- Runs every 5 seconds.
- Checks `_last_data_time` per symbol against configurable timeout (default 30s).
- Transitions between stale/fresh states with logging.
- **⚠️ Missing market hours check** — TODO left in code. Monitor will flag stale data outside market hours, which is expected (no data = no updates). Not a blocker for Sprint 4a, but should be addressed in Sprint 4b or 5.

### ✅ WebSocket Reconnection

- Exponential backoff: base 1s, max 30s, ×2 per failure.
- Jitter: ±20% randomization. Correct.
- System alert after configurable consecutive failures (default 3).
- Runs `_run_forever()` directly on existing asyncio loop (Pattern 1 — correct choice).
- **Minor code smell:** `import random` inside the reconnect method body rather than at module level. Not a bug, but worth cleaning up.

### ✅ IndicatorState Refactor

- Session 2 started with `IndicatorEngine` from `argus.data.indicators`, then refactored mid-session to use inline `IndicatorState` dataclass matching ReplayDataService's pattern.
- Good decision — keeps the two DataService implementations consistent. Should be logged as a micro-decision.

---

## 2. AlpacaBroker — Broker ABC Implementation

### ✅ ABC Interface Coverage

| Method | Implemented | Notes |
|--------|-------------|-------|
| `connect()` | ✅ | Reads keys from env, initializes TradingClient + TradingStream, starts WebSocket stream |
| `disconnect()` | ✅ | Cancels stream task, closes stream, sets connected=false |
| `place_order(order)` | ✅ | Maps our Order → Alpaca request (market/limit/stop/stop-limit), stores ID mapping |
| `place_bracket_order(entry, stop, targets)` | ✅ | Single T1 target per spec (MD-4a-6). Alpaca limitation acknowledged. |
| `cancel_order(order_id)` | ✅ | Looks up Alpaca UUID from our ULID, calls cancel_order_by_id |
| `modify_order(order_id, mods)` | ✅ | Uses ReplaceOrderRequest, supports qty/limit_price/stop_price changes |
| `get_positions()` | ✅ | Maps Alpaca positions to our Position model |
| `get_account()` | ✅ | Maps Alpaca account to our AccountInfo model |
| `get_order_status(order_id)` | ✅ | Looks up via ID map, returns mapped status |
| `flatten_all()` | ✅ | Cancels all pending orders, then close_all_positions(cancel_orders=True) |

### ✅ Order ID Mapping

- Bidirectional dict: `_order_id_map` (ULID→UUID) and `_reverse_id_map` (UUID→ULID).
- Populated on order placement, looked up on trade updates.
- Unknown Alpaca order IDs in WebSocket updates are logged as warnings and skipped. Correct.

### ✅ TradingStream Handler (`_on_trade_update`)

- Maps Alpaca events to our events:
  - `new` → `OrderSubmittedEvent`
  - `fill` / `partial_fill` → `OrderFilledEvent`
  - `canceled` / `expired` / `rejected` → `OrderCancelledEvent`
  - `replaced` → debug log only
- All events published to Event Bus.
- Includes reject reason if available.

### ✅ Bracket Order Implementation

- Uses `OrderClass.BRACKET` with `MarketOrderRequest`.
- Single take-profit at T1 (targets[0].limit_price).
- Stop loss at stop.stop_price.
- Child order IDs not immediately available (Alpaca creates them server-side) — acknowledged in code comments.
- Validation: entry must be market order, targets non-empty, stop_price required, limit_price required. Good.

### ✅ Error Handling

- All REST calls wrapped in try/except.
- Catches general Exception (could be tighter with Alpaca-specific exceptions, but safe).
- Logs with exc_info=True for stack traces.
- flatten_all returns empty list on failure (doesn't crash). Correct for emergency operation.

### ⚠️ Observations (Non-blocking)

1. **`strategy_id=""`** on `OrderSubmittedEvent` and `Position` objects — broker doesn't have strategy context. This is expected at the broker level and will be wired when the Order Manager provides context in Sprint 4b.

2. **`datetime.now(UTC)` used directly** (lines 201, 630) instead of injected clock. This is per-spec: MD-4a-5 scoped clock injection to Risk Manager + BaseStrategy only. AlpacaBroker was not in scope. However, the `entry_time=datetime.now(UTC)` on `get_positions()` creates a new timestamp each call, which means the position's entry_time changes on every retrieval — this is explicitly commented as a known limitation.

3. **`get_positions()` creates new ULID per call** — there's no persistence of position tracking across calls. Each call returns fresh Position objects with new IDs. This is fine for Sprint 4a (no position management yet), but Sprint 4b's Order Manager must own position lifecycle tracking.

---

## 3. Clock Injection

### ✅ Implementation

| Item | Status | Notes |
|------|--------|-------|
| `Clock` protocol | ✅ | `now() → datetime`, `today() → date` |
| `SystemClock` | ✅ | Real time, configurable timezone (default America/New_York) |
| `FixedClock` | ✅ | Fixed time, `advance(**kwargs)`, `set(new_time)`. Validates timezone-aware. |
| Risk Manager injection | ✅ | `clock: Clock | None` param, defaults to SystemClock, uses `clock.now()` and `clock.today()` |
| BaseStrategy injection | ✅ | Same pattern, passes through to OrbBreakout |
| Backward compatibility | ✅ | All existing Sprint 1-3 tests pass without changes |
| DEF-001 resolved | ✅ | Deferred item for date-boundary testing is now complete |

### ✅ Good Design Choices

- Protocol-based (structural typing) rather than ABC inheritance — lighter weight, Pythonic.
- `FixedClock` requires timezone-aware datetime (raises ValueError otherwise) — prevents a common bug.
- `today()` respects timezone boundaries (11 PM EST returns EST date, not UTC date). Critical for trading.
- `advance()` method on FixedClock enables time-progression tests without reconstructing the clock.

---

## 4. Spec Deviations

| Deviation | Severity | Assessment |
|-----------|----------|------------|
| `IndicatorEngine` → `IndicatorState` dataclass in AlpacaDataService | Low | **Reasonable improvement.** Follows ReplayDataService's established pattern, reducing code duplication. Log as micro-decision. |
| `import random` inside `_run_stream_with_reconnect()` body | Trivial | Code smell. Move to module-level import. Fix before Sprint 4b. |
| Stale data monitor lacks market hours check | Medium | TODO left in code. During off-hours, lack of data is normal and will trigger false stale alerts. **Fix in Sprint 4b/5.** |
| Integration test was rewritten from a complex 15KB version to a simplified 10KB version | Low | **Good judgment.** The first attempt was too complex and both tests failed. The simplified version focuses on the core wiring (signal→risk→broker) which is the actual Sprint 4a goal. |

---

## 5. Test Quality Assessment

### Test Count

| Component | Target (spec) | Actual | Delta |
|-----------|---------------|--------|-------|
| Clock | ~14 | 14 | ✅ |
| AlpacaDataService | ~20 | 20 | ✅ |
| AlpacaBroker | ~25 | 19 | ⚠️ -6 |
| Integration | ~8 | 2 | ⚠️ -6 |
| **Total** | **~66** | **55** | **-11** |

The target was ~66, actual is 55. The gap is primarily in AlpacaBroker (19 vs 25) and Integration (2 vs 8). The reduced integration test count is justified by the complexity rewrite — 2 focused tests beat 8 fragile ones. The AlpacaBroker gap is more concerning.

### ⚠️ Coverage Gaps to Address

1. **Flaky test:** `test_reconnection_with_exponential_backoff` — timing-dependent, fails intermittently. This is the "1 flaky pre-existing test" (actually introduced in Sprint 4a Session 2). **Must fix before Sprint 4b.** Use `FixedClock` + mock `asyncio.sleep` to make it deterministic.

2. **No test for VWAP daily reset** in AlpacaDataService — the IndicatorState should reset VWAP at market open. This behavior is tested indirectly via ReplayDataService's tests but not directly for the live service.

3. **No test for concurrent multi-symbol subscriptions** — all tests use a single symbol. Should have at least one test with 2+ symbols to verify per-symbol state isolation.

4. **Missing AlpacaBroker test coverage:**
   - `modify_order()` success path
   - `flatten_all()` with positions + pending orders
   - `get_account()` with non-zero positions_value
   - `place_order()` with limit and stop-limit order types

5. **Mock realism:** Mocks are functional but sometimes overly simplified. For example, the `TradingClient.submit_order` mock returns a static object. In reality, Alpaca returns different structures for bracket vs simple orders. The bracket order test should verify child order handling more thoroughly.

### ✅ What Tests Do Well

- Clock tests are thorough — timezone boundaries, advance/set, validation.
- Event publishing tests verify actual event types and field values.
- Error paths tested: missing API keys, unknown symbols, unknown orders.
- Integration test correctly uses FixedClock for deterministic time.

---

## 6. Ruff Status

✅ Clean across all sessions. No linting issues.

---

## 7. Overall Assessment

### What Went Well

- **alpaca-py integration pattern**: The decision to use `_run_forever()` directly on the existing asyncio loop was validated early by reading alpaca-py source code. This avoided threading complexity.
- **Mid-session refactors were smart**: Switching from IndicatorEngine to IndicatorState, simplifying the integration test — both showed good judgment when the initial approach wasn't working.
- **Clean session handoffs**: Each session ended with a clear commit and detailed handoff summary. Context transfer was effective across three separate Claude Code sessions.
- **Backward compatibility maintained**: All 222 Sprint 3 tests continued passing after clock injection.

### What Could Be Better

- **Test coverage gap**: 55 vs 66 target. The 6 missing AlpacaBroker tests represent real coverage gaps.
- **Flaky test introduced**: `test_reconnection_with_exponential_backoff` is timing-dependent and should have been written with mocked timing from the start.
- **TODOs in production code**: Market hours check in stale data monitor, SystemAlertEvent publishing — these are fine as TODOs but should be tracked.

### Pre-Sprint 4b Fix List

Before starting Sprint 4b, fix these:

1. **Fix the flaky test** — `test_reconnection_with_exponential_backoff`. Mock `asyncio.sleep` to make it deterministic.
2. **Move `import random`** to module level in `alpaca_data_service.py`.
3. **Add 3-4 missing AlpacaBroker tests** — at minimum: `modify_order()` success, `flatten_all()` with positions, `place_order()` with limit order type.

---

## 8. Document Updates Needed

### DEC-039: Sprint 4a Micro-Decisions

```
### DEC-039 | Sprint 4a Micro-Decisions
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Sprint 4a implementation decisions (MD-4a-1 through MD-4a-6 from spec), plus: MD-4a-7: AlpacaDataService uses IndicatorState dataclass (matching ReplayDataService pattern) instead of separate IndicatorEngine class. |
| **Rationale** | MD-4a-1: Dual stream (bars + trades) provides reliable candles plus real-time price cache. MD-4a-2: Exponential backoff with jitter matches Architecture doc. MD-4a-3: alpaca-py is the current official SDK. MD-4a-4: Direct async integration via _run_forever() on existing event loop. MD-4a-5: Clock injection scoped to Risk Manager + BaseStrategy. MD-4a-6: Single T1 target for bracket orders (Alpaca limitation). MD-4a-7: Consistent indicator pattern across DataService implementations. |
| **Status** | Active |
```

### CLAUDE.md Updates

```
## Current State
Sprint 4a complete (277 tests, 276 passing, 1 flaky). Clock protocol, AlpacaDataService, AlpacaBroker implemented.

## Tech Stack
- alpaca-py>=0.30 (NOT alpaca-trade-api — deprecated)
- python-dotenv>=1.0

## Components
- Clock protocol (argus/core/clock.py): SystemClock, FixedClock — injectable time provider
- AlpacaDataService (argus/data/alpaca_data_service.py): Live WebSocket data via alpaca-py
- AlpacaBroker (argus/execution/alpaca_broker.py): Paper/live trading via alpaca-py

## DEF-001: RESOLVED
Clock injection into Risk Manager + BaseStrategy is complete.
```

### 02_PROJECT_KNOWLEDGE.md Updates

Under "Current Project State":
```
**Phase:** Phase 1 in progress. Sprints 1–4a complete (277 tests, 276 passing). Sprint 4b next.
**Current sprint:** Sprint 4a complete (Clock injection + AlpacaDataService + AlpacaBroker). Sprint 4b next — Order Manager + AlpacaScanner + EOD flatten.
**Next milestone:** Active position management with dynamic stop/target adjustments on paper trades: OrderManager subscribes to ticks, moves stops to breakeven on T1 hit, enforces time stops, flattens at EOD.
```

Under "Key Decisions Made":
```
- **Alpaca SDK:** alpaca-py (not alpaca-trade-api, which is deprecated). DEC-039/MD-4a-3.
- **Clock injection:** Clock protocol with SystemClock + FixedClock. Scoped to Risk Manager + BaseStrategy. DEF-001 resolved. DEC-039/MD-4a-5.
- **AlpacaDataService streams:** Subscribes to both 1m bar stream (CandleEvents) and trade stream (TickEvents + price cache). DEC-039/MD-4a-1.
- **Bracket orders:** Single T1 take-profit (Alpaca limitation). Order Manager handles T1/T2 split in Sprint 4b. DEC-039/MD-4a-6.
```

### 03_ARCHITECTURE.md Updates

In Technology Stack table, replace:
```
alpaca-trade-api → alpaca-py>=0.30 (official current SDK)
```

Add Clock protocol to Module Specifications.

### 07_PHASE1_SPRINT_PLAN.md Updates

```
### Sprint 4a — Live Connections ✅ Complete
- Clock protocol + injection: 14 tests
- AlpacaDataService: 20 tests  
- AlpacaBroker: 19 tests
- Integration: 2 tests
- Total: 277 tests (276 passing, 1 flaky — reconnection timing test)
- Commits: fe0af1a, 1535cfa, 422814d, 58067c1, fa8ceaa
```

### Risk Register

```
### RISK-NEW: Flaky reconnection test
- **Risk:** test_reconnection_with_exponential_backoff is timing-dependent and fails intermittently.
- **Impact:** Low (test reliability, not production).
- **Mitigation:** Fix with mocked asyncio.sleep before Sprint 4b.
- **Status:** Open.

### RISK-NEW: Stale data false positives outside market hours
- **Risk:** Stale data monitor runs 24/7 but only market-hours data is expected.
- **Impact:** Medium (false alerts could trigger unnecessary strategy pauses).
- **Mitigation:** Add market hours check to stale data monitor in Sprint 4b or 5.
- **Status:** Open.
```

---

**Sprint 4a is confirmed complete.** Fix the 3 pre-Sprint 4b items, commit the doc updates, and proceed to Sprint 4b planning in a separate session.
