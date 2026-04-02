# Sprint 32.8, Session 1: Arena Pipeline (Backend)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/api/websocket/arena_ws.py`
   - `argus/data/intraday_candle_store.py`
   - `argus/core/events.py` (read-only — find TickEvent and CandleEvent definitions)
   - `argus/execution/order_manager.py` lines 820–862 (read-only — understand the `_publish_position_pnl` 1s throttle and `PositionUpdatedEvent` to see what we're bypassing)
2. Run the test baseline:
   Full suite: `python -m pytest --ignore=tests/test_main.py -n auto -q`
   Expected: ~4,530 tests passing (DEF-137 `test_history_store_migration` may have hardcoded date decay — known pre-existing)
   Vitest: `cd argus/ui && npx vitest run`
   Expected: ~805 tests passing (DEF-138 `ArenaPage.test.tsx` WS mock — known pre-existing)
3. Verify you are on the correct branch: `main` (or create `sprint-32.8` branch)

## Objective
Make Arena charts update at the actual Databento trade stream rate instead of the 1 Hz Order Manager throttle, and enable pre-market candle data on Arena charts.

## Requirements

### 1. Arena WS direct TickEvent subscription (`arena_ws.py`)

In `arena_websocket()`, add a new event handler:

```python
async def on_tick(event: TickEvent) -> None:
    if event.symbol not in tracked_symbols:
        return
    _enqueue({
        "type": "arena_tick_price",
        "symbol": event.symbol,
        "price": event.price,
        "timestamp": event.timestamp.isoformat(),
    })
```

Subscribe to `TickEvent` alongside the existing subscriptions. Add the import for `TickEvent` from `argus.core.events`.

**Important:** This is a NEW message type (`arena_tick_price`) separate from the existing `arena_tick`. The existing `arena_tick` from `PositionUpdatedEvent` continues to deliver P&L, R-multiple, and trail stop data at 1 Hz. The new `arena_tick_price` delivers raw price for chart forming-candle updates at the full tick rate.

Do NOT remove the existing `on_position_updated` handler or the `arena_tick` message type.

Also add an unsubscribe for `TickEvent` in the finally block.

### 2. Replace linear trail stop lookup (`arena_ws.py`)

Replace `_get_trailing_stop_price()` (which does O(n) scan of `get_all_positions_flat()`) with a dict-based approach:

Add a `trail_stop_cache: dict[str, float] = {}` to the per-connection state. Update it in `on_position_updated` (which already has the trail stop value). Read from it in `on_tick`. Remove the standalone `_get_trailing_stop_price()` function (or keep as dead code if tests reference it).

### 3. Pre-market candle store widening (`intraday_candle_store.py`)

Find the market-hours filter (likely checking for 9:30–16:00 ET) in the `on_candle()` or equivalent handler. Change the start time from 9:30 AM ET to **4:00 AM ET** (pre-market open). Keep the 16:00 ET end time.

Also increase the max bars per symbol from 390 (6.5 hours × 60 min) to **720** (12 hours × 60 min) to accommodate the extended window.

### 4. Frontend handling of new message type

In `argus/ui/src/features/arena/useArenaWebSocket.ts`, add a handler for the `arena_tick_price` message type in the `ws.onmessage` switch:

```typescript
case 'arena_tick_price': {
    const symbol = msg.symbol as string;
    if (!rafPendingRef.current.has(symbol)) {
        // Only update forming candle price, don't overwrite P&L data
        const existing = rafPendingRef.current.get(symbol);
        rafPendingRef.current.set(symbol, {
            price: msg.price as number,
            unrealized_pnl: existing?.unrealized_pnl ?? 0,
            r_multiple: existing?.r_multiple ?? 0,
            trailing_stop_price: existing?.trailing_stop_price ?? 0,
        });
    } else {
        // Update just the price on existing batch entry
        const batch = rafPendingRef.current.get(symbol)!;
        batch.price = msg.price as number;
    }
    scheduleRaf();
    break;
}
```

This ensures high-frequency price updates drive the forming candle without overwriting the P&L/R data that arrives via the slower `arena_tick` path.

## Constraints
- Do NOT modify: `argus/core/events.py`, `argus/execution/order_manager.py`, any strategy files, any other Python files
- Do NOT change: the existing `arena_tick` message format or behavior
- Do NOT change: the existing `PositionUpdatedEvent` subscription behavior
- The `arena_tick_price` message must use the SAME field names as the TickEvent (symbol, price, timestamp) — keep it simple

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_arena_ws_tick_event_filtered_to_tracked_symbols` — TickEvent for non-tracked symbol is not enqueued
  2. `test_arena_ws_tick_event_enqueued_for_tracked_symbol` — TickEvent for tracked symbol produces `arena_tick_price` message
  3. `test_arena_ws_tick_price_message_format` — verify message has type, symbol, price, timestamp fields
  4. `test_trail_stop_cache_updated_on_position_update` — trail stop cache populated from PositionUpdatedEvent
  5. `test_candle_store_accepts_premarket_bars` — CandleEvent at 8:00 AM ET is stored (was rejected before)
  6. `test_candle_store_rejects_overnight_bars` — CandleEvent at 3:00 AM ET is still rejected
  7. `test_candle_store_max_bars_increased` — verify maxlen is 720
  8. `test_arena_tick_price_frontend_handler` — useArenaWebSocket processes `arena_tick_price` and schedules rAF
- Minimum new test count: 8
- Test commands:
  - Python: `python -m pytest tests/api/websocket/ tests/data/ -x -q`
  - Vitest: `cd argus/ui && npx vitest run --reporter=verbose src/features/arena/`

## Definition of Done
- [ ] Arena WS subscribes to TickEvent, filtered to tracked_symbols
- [ ] `arena_tick_price` messages sent at TickEvent rate
- [ ] Existing `arena_tick` P&L/R messages unchanged
- [ ] Trail stop uses dict cache instead of linear scan
- [ ] IntradayCandleStore accepts pre-market bars (4:00 AM ET+)
- [ ] Max bars per symbol increased to 720
- [ ] Frontend handles `arena_tick_price` for forming candle updates
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Arena WS still delivers all 5 original message types | Existing arena WS tests pass |
| PositionUpdatedEvent still drives P&L numbers | Verify `arena_tick` messages still sent in tests |
| No modification to order_manager.py | `git diff argus/execution/order_manager.py` is empty |
| No modification to events.py | `git diff argus/core/events.py` is empty |
| IntradayCandleStore still rejects after-hours bars (post 4 PM) | Test with 5:00 PM ET candle → rejected |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-32.8/session-1-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-32.8/review-context.md`
2. The close-out report path: `docs/sprints/sprint-32.8/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/api/websocket/ tests/data/ -x -q && cd argus/ui && npx vitest run src/features/arena/`
5. Files that should NOT have been modified: anything outside `arena_ws.py`, `intraday_candle_store.py`, `useArenaWebSocket.ts`

## Session-Specific Review Focus (for @reviewer)
1. Verify TickEvent subscription is filtered to `tracked_symbols` only — unfiltered would create massive message volume
2. Verify `arena_tick_price` is a new message type, not replacing `arena_tick`
3. Verify trail stop cache is populated from PositionUpdatedEvent, not computed per-tick
4. Verify pre-market filter change is 4:00 AM ET (not UTC or local time)
5. Verify max bars increased to 720 (not left at 390)
6. Verify frontend handler merges price-only updates without clobbering P&L data

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`
