# Sprint 32.75, Session 7: Arena WebSocket

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `argus/api/websocket/observatory_ws.py` (established WS pattern), `argus/api/websocket/live.py`, `argus/api/server.py` (WS registration)
2. Scoped tests: `python -m pytest tests/api/ -x -q`
3. Verify branch: `main`
4. S6 merged (REST endpoints available)

## Objective
Create the `/ws/v1/arena` WebSocket channel streaming real-time position data, candles, and aggregate stats.

## Requirements

1. **Create `argus/api/websocket/arena_ws.py`** following the Observatory WS pattern:
   - JWT auth on connection (same as observatory_ws.py)
   - Subscribe to Event Bus: `PositionUpdatedEvent`, `CandleEvent`, position open/close events
   - Message types:
     - `arena_tick`: `{type, symbol, price, unrealized_pnl, r_multiple, trailing_stop_price}` — on each PositionUpdatedEvent for a managed position
     - `arena_candle`: `{type, symbol, time, open, high, low, close, volume}` — on CandleEvent for symbols with open positions only
     - `arena_position_opened`: `{type, symbol, strategy_id, entry_price, stop_price, target_prices, side, shares, entry_time}`
     - `arena_position_closed`: `{type, symbol, strategy_id, exit_price, pnl, r_multiple, exit_reason}`
     - `arena_stats`: `{type, position_count, total_pnl, net_r, entries_5m, exits_5m}` — computed and published every 1 second via asyncio timer

2. **CandleEvent filtering**: Only forward candles for symbols that currently have open managed positions. Maintain a `_tracked_symbols: set[str]` updated on position open/close.

3. **Entries/exits rate tracking**: Ring buffer of last 5 minutes of open/close events for the `entries_5m`/`exits_5m` stats.

4. **Register** the WS endpoint in `argus/api/server.py`.

## Constraints
- Do NOT modify existing WS channels (/ws/v1/live, /ws/v1/observatory, /ws/v1/ai/chat)
- Do NOT modify Event Bus subscription mechanism
- Do NOT modify PositionUpdatedEvent or CandleEvent schemas
- Arena WS must handle client disconnect gracefully (no leaked subscriptions)
- Must not degrade main trading pipeline performance

## Test Targets
- Test WS connection + auth
- Test arena_tick message format on PositionUpdatedEvent
- Test arena_candle filtering (only open position symbols)
- Test arena_stats computation
- Test position open/close messages
- Test client disconnect cleanup
- Minimum: 8 new tests
- Command: `python -m pytest tests/api/test_arena_ws*.py -x -q`

## Definition of Done
- [ ] WS endpoint functional at /ws/v1/arena
- [ ] All 5 message types working
- [ ] CandleEvent filtering by open positions
- [ ] Stats published every 1s
- [ ] Graceful disconnect handling
- [ ] Close-out: `docs/sprints/sprint-32.75/session-7-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-32.75/session-7-closeout.md`

## Tier 2 Review
Test: `python -m pytest tests/api/test_arena*.py -x -q`. Files NOT to modify: existing WS handlers, Event Bus, OrderManager.

## Session-Specific Review Focus
1. Verify event bus subscriptions are cleaned up on client disconnect (no memory leak)
2. Verify CandleEvent filtering only forwards open position symbols (not entire universe)
3. Verify arena_stats timer is cancelled on shutdown
4. Verify this WS does not interfere with /ws/v1/live message delivery
