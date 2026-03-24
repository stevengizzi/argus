---BEGIN-REVIEW---

# Sprint 27.65, Session S4: IntradayCandleStore + Live P&L — Tier 2 Review

## Summary

Session S4 implements two features: (1) a centralized IntradayCandleStore that
accumulates live CandleEvents during market hours and makes them queryable via
the market bars API endpoint, and (2) real-time unrealized P&L publishing for
open positions via WebSocket, with a 30-second account metrics poll loop.

## Spec Compliance

All Definition of Done items are met:
- IntradayCandleStore created, initialized, and subscribed to CandleEvent
- Market bars endpoint queries store first (Priority 1), falls back to
  DataService (Priority 2), then synthetic (Priority 3)
- Position P&L updates published via PositionUpdatedEvent on ticks (throttled)
- Account updates pushed via WebSocket (30s poll loop in WS bridge)
- All existing tests pass (3,408 passed, 0 new failures)
- 16 new tests written and passing (exceeds 10 minimum)
- Close-out report written

## Review Focus Findings

### 1. IntradayCandleStore does not duplicate data with existing candle paths

PASS. The store is a parallel CandleEvent subscriber in main.py (line 776),
independent of the strategy routing subscription (line 784). The store
maintains its own `dict[str, deque[CandleBar]]` storage, completely separate
from each strategy's `_candle_windows`. No shared mutable state. The
backfill path in PatternBasedStrategy calls `get_bars()` read-only.

### 2. P&L throttle does not suppress position close updates

PASS. `_flatten_position()` (line 1338) calls
`self._pnl_last_published.pop(position.symbol, None)` before any other
logic, clearing the throttle for that symbol. This ensures the next P&L
update (or PositionClosedEvent from the fill handler) is never throttled.
The `_publish_position_pnl` method also skips `is_fully_closed` positions
(line 532), so positions mid-flatten (sell submitted but not yet filled)
correctly get a final P&L update with accurate numbers.

### 3. WebSocket message format is consistent with existing types

PASS. PositionUpdatedEvent was already mapped to `position.updated` in
EVENT_TYPE_MAP. The new fields (symbol, r_multiple, entry_price, shares,
strategy_id) are added with defaults, so `dataclasses.asdict()` serialization
includes them automatically without breaking existing consumers. The
`account.update` message type follows the same `{type, data, sequence,
timestamp}` structure used by all other WS messages.

### 4. Candle store does not accumulate pre-market data

PASS. `on_candle()` (lines 66-74) converts timestamps to ET per DEC-061
and filters: only bars with `_MARKET_OPEN (9:30) <= time < _MARKET_CLOSE
(16:00)` are stored. Non-1m timeframes are also filtered. Tests
`test_candle_store_filters_pre_market` and `test_candle_store_filters_post_market`
verify this explicitly.

### 5. Thread safety of candle store access pattern

PASS. As documented in the module docstring, CandleEvents arrive via
`call_soon_threadsafe` (DEC-088), so the `on_candle` callback runs on the
asyncio thread. The market bars API endpoint also runs on the asyncio thread
(FastAPI async handler). All access is single-threaded asyncio -- no locking
needed.

## Findings

### F-1: AccountUpdateEvent class is dead code (LOW)

`AccountUpdateEvent` is defined in `events.py` (line 385) and imported/mapped
in `live.py` EVENT_TYPE_MAP, but the account poll loop (`_account_poll_loop`)
constructs WebSocket messages manually via `self._broadcast()` and never
publishes an `AccountUpdateEvent` through the event bus. The event class and
its EVENT_TYPE_MAP entry are unused. This is not a correctness issue -- the
manual message construction produces the correct WS format -- but it is dead
code that could confuse future maintainers who expect it to be used.

### F-2: Account poll loop uses `getattr` with defaults for broker account fields (LOW)

The `_account_poll_loop` (line 398-402) uses `getattr(account, "equity", 0.0)`
etc. to extract fields from the broker account object. This is defensive but
masks potential issues: if the broker returns an object without these fields,
the frontend silently receives zeros rather than an error. This is acceptable
for a V1 implementation with multiple broker backends but worth noting.

### F-3: Duck-typed candle store reference in PatternBasedStrategy (LOW)

`set_candle_store()` accepts `object` and uses `hasattr()` checks (lines
155-162). This avoids circular imports but sacrifices type safety. The
close-out correctly identifies this as a judgment call. Consistent with the
project's existing pattern (e.g., `Orchestrator._latest_regime_vector: object
| None`). A Protocol type could improve this in a future cleanup pass.

## Escalation Criteria Check

1. New order path without risk checks? NO -- `_publish_position_pnl` only
   publishes events, never submits orders.
2. Position reconciliation auto-corrects? N/A -- no reconciliation changes.
3. Bracket amendment leaves position unprotected? N/A -- no bracket changes.
4. BrokerSource.SIMULATED bypass broken? NO -- no changes to that path.
5. Risk Manager circuit breaker/daily loss logic affected? NO -- risk_manager.py
   has zero diff.

## Regression Checklist

| Check | Result |
|-------|--------|
| Normal stop-loss path works | PASS -- on_tick exit checks unchanged |
| Normal target-hit path works | PASS -- T2 target check unchanged |
| Time-stop fires exactly once | PASS -- flatten guard logic unchanged |
| CandleStore accumulates bars | PASS -- 11 dedicated tests |
| Existing WS message types unchanged | PASS -- only additions (account.update) |

## Test Results

```
Scoped tests:  16 passed (0.62s)
Full suite:    3,408 passed, 0 failed, 60 warnings (90.42s)
```

No new test failures introduced. The 4 pre-existing DEF-048 xdist
failures in test_main.py (excluded from the run) are unchanged.

## Verdict

All scope items completed per spec. No escalation criteria triggered.
Three low-severity findings documented (dead AccountUpdateEvent code,
getattr defensiveness, duck-typed store reference). None affect
correctness or safety.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "confidence": 0.92,
  "findings": [
    {
      "id": "F-1",
      "severity": "LOW",
      "category": "dead-code",
      "description": "AccountUpdateEvent class defined in events.py and mapped in EVENT_TYPE_MAP but never published through the event bus. The account poll loop constructs WS messages manually via _broadcast().",
      "recommendation": "Either publish AccountUpdateEvent through the event bus and let the standard WS bridge path handle serialization, or remove the unused event class and EVENT_TYPE_MAP entry."
    },
    {
      "id": "F-2",
      "severity": "LOW",
      "category": "defensive-coding",
      "description": "Account poll loop uses getattr with zero defaults for broker account fields, silently masking missing fields.",
      "recommendation": "Acceptable for V1 multi-broker support. No action needed unless debugging account data issues."
    },
    {
      "id": "F-3",
      "severity": "LOW",
      "category": "type-safety",
      "description": "PatternBasedStrategy.set_candle_store() accepts object type with hasattr() checks, sacrificing type safety to avoid circular imports.",
      "recommendation": "Consider a Protocol type in a future cleanup pass. Consistent with existing project patterns."
    }
  ],
  "tests_pass": true,
  "test_count": 3408,
  "new_test_count": 16,
  "escalation_triggers": [],
  "scope_adherence": "FULL",
  "files_not_to_modify_check": "PASS"
}
```
