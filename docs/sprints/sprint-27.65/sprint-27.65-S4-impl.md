# Sprint 27.65, Session S4: IntradayCandleStore + Live P&L

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md`
   - `argus/data/databento_data_service.py`
   - `argus/api/routes/market.py` (the bars endpoint)
   - `argus/api/websocket/live.py`
   - `argus/execution/order_manager.py` (position tracking)
   - `docs/sprints/sprint-27.65/S3-closeout.md` (verify S3 complete)
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/data/ tests/api/ tests/execution/ -x -q`
   Expected: all passing
3. Verify you are on the correct branch

## Objective
Build a centralized intraday candle store that makes live session bars queryable
on demand (fixing the synthetic bar fallback), and add real-time unrealized P&L
push for open positions via WebSocket.

## Requirements

### R1: IntradayCandleStore
1. Create `argus/data/intraday_candle_store.py`:
   - Class `IntradayCandleStore`
   - Subscribes to `CandleEvent` on the event bus
   - Stores bars in `dict[str, deque[CandleBar]]` (symbol → deque of bars)
   - Max deque length: 390 per symbol (full trading day of 1-min bars)
   - Each stored bar should include: symbol, timestamp, open, high, low, close,
     volume (mirror CandleEvent fields)
   - Public API:
     - `get_bars(symbol: str, start_time: datetime | None = None, end_time: datetime | None = None) -> list[CandleBar]`
     - `get_latest(symbol: str, count: int = 1) -> list[CandleBar]`
     - `has_bars(symbol: str) -> bool`
     - `bar_count(symbol: str) -> int`
     - `symbols_with_bars() -> list[str]`
   - Thread-safe: candle events arrive from the Databento reader thread via
     `call_soon_threadsafe`, so the store's callback is already on the asyncio
     thread. No additional locking needed if accessed only from asyncio context.
   - Clear all data on `reset()` (for start-of-day cleanup)

2. Initialize in `__main__.py`:
   - Create IntradayCandleStore after event bus, before strategies
   - Subscribe to CandleEvent
   - Store instance on app state for API access

3. Wire into market bars API endpoint:
   - In `argus/api/routes/market.py`, the `GET /api/v1/market/{symbol}/bars`
     endpoint should query IntradayCandleStore first
   - If store has bars for the symbol: return them (filtered by time range)
   - If store has no bars: fall back to existing synthetic bar generation
   - Remove or downgrade the "Failed to fetch real bars, falling back to
     synthetic" ERROR log to DEBUG (since it's now expected only for symbols
     with zero activity)

4. Make IntradayCandleStore available to PatternBasedStrategy (from S3) for
   backfill — expose via a method or pass a reference during initialization.

### R2: Real-time position P&L via WebSocket
1. In OrderManager, when processing tick/trade events for open positions
   (the existing tick subscription path):
   - After checking stop/target levels, compute unrealized P&L:
     `unrealized_pnl = (current_price - entry_price) * shares * direction`
   - Compute R-multiple: `r_multiple = unrealized_pnl / risk_amount`
     (where risk_amount = abs(entry_price - stop_price) * shares)
   - Publish a `PositionUpdateEvent` (new event type) or push directly via
     the WebSocket bridge
   - Throttle: at most once per second per symbol (don't flood on every tick)

2. In `/ws/v1/live` WebSocket handler:
   - Add a new message type: `position_update`
   - Payload: `{symbol, unrealized_pnl, r_multiple, current_price, entry_price,
     shares, strategy_id}`
   - Frontend clients receive this and update position displays in real-time

3. For account-level metrics (equity, daily P&L):
   - If IBKR pushes account updates (via `accountSummary` or `pnl` callbacks):
     forward these through the WebSocket as `account_update` messages
   - Payload: `{equity, daily_pnl, buying_power, timestamp}`
   - If IBKR doesn't push these frequently enough, add a 30-second poll

## Constraints
- Do NOT modify: event bus architecture (use existing pub/sub pattern)
- Do NOT modify: strategy candle consumption (strategies still get their own
  CandleEvents — IntradayCandleStore is a parallel subscriber)
- Do NOT modify: existing WebSocket message types (add new ones, don't change
  existing `signal`, `fill`, `trade_complete` etc.)
- IntradayCandleStore must not accumulate pre-market bars (filter by market hours)
- P&L throttle must not suppress the final update when a position closes

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_candle_store_accumulates_bars` — publish CandleEvents, verify stored
  2. `test_candle_store_get_bars_time_range` — filter by start/end time
  3. `test_candle_store_max_length` — verify deque doesn't exceed 390
  4. `test_candle_store_get_latest` — returns N most recent bars
  5. `test_candle_store_reset` — clears all data
  6. `test_market_bars_endpoint_uses_candle_store` — API returns real bars when available
  7. `test_market_bars_endpoint_fallback` — API falls back when store has no data
  8. `test_position_update_event_published` — tick event for open position triggers P&L update
  9. `test_position_update_throttle` — multiple ticks within 1s produce only 1 update
  10. `test_position_update_r_multiple_calculation` — verify R-multiple math
- Minimum new test count: 10
- Test command: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`

## Definition of Done
- [ ] IntradayCandleStore created, initialized, subscribed to events
- [ ] Market bars endpoint queries store first, falls back to synthetic
- [ ] Position P&L updates pushed via WebSocket on tick events
- [ ] Account updates pushed via WebSocket
- [ ] All existing tests pass
- [ ] 10+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write close-out to: `docs/sprints/sprint-27.65/S4-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.65/review-context.md`
2. Close-out path: `docs/sprints/sprint-27.65/S4-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/data/ tests/api/ tests/execution/ -x -q`
5. Files NOT to modify: `argus/strategies/` (except PatternBasedStrategy backfill wire), `argus/core/risk_manager.py`

Write review to: `docs/sprints/sprint-27.65/S4-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify IntradayCandleStore doesn't duplicate data with existing candle paths
2. Verify P&L throttle doesn't suppress position close updates
3. Verify WebSocket message format is consistent with existing message types
4. Verify candle store doesn't accumulate pre-market data
5. Verify thread safety of candle store access pattern
