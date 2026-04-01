# Sprint 32.75, Session 6: Arena REST API

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `argus/api/routes/positions.py` (existing position endpoint pattern), `argus/data/intraday_candle_store.py` (IntradayCandleStore API), `argus/api/routes/__init__.py` (route registration)
2. Scoped tests: `python -m pytest tests/api/ -x -q`
3. Branch: `sprint-32.75-session-6`

## Objective
Create REST endpoints for Arena page initial data load — position list with levels and candle history per symbol.

## Requirements

1. **Create `argus/api/routes/arena.py`** with two JWT-protected endpoints:

   **`GET /api/v1/arena/positions`** — Returns all open managed positions:
   ```python
   # Response schema
   {
     "positions": [
       {
         "symbol": "AAPL",
         "strategy_id": "strat_orb_breakout",
         "side": "long",
         "shares": 100,
         "entry_price": 150.25,
         "current_price": 151.10,
         "stop_price": 149.50,
         "target_prices": [152.00, 153.50],
         "trailing_stop_price": 150.80,  # null if trail not active
         "unrealized_pnl": 85.00,
         "r_multiple": 1.13,
         "hold_duration_seconds": 342,
         "quality_grade": "B+",
         "entry_time": "2026-04-01T13:36:02Z"
       }
     ],
     "stats": {
       "position_count": 42,
       "total_pnl": -720.17,
       "net_r": -0.34
     }
   }
   ```
   Source: `state.order_manager._managed_positions` (iterate, extract levels from ManagedPosition fields).

   **`GET /api/v1/arena/candles/{symbol}?minutes=30`** — Returns recent 1-min candles:
   ```python
   {
     "symbol": "AAPL",
     "candles": [
       {"time": 1711968000, "open": 150.10, "high": 150.50, "low": 149.90, "close": 150.25, "volume": 12500},
       ...
     ]
   }
   ```
   Source: `state.intraday_candle_store.get_latest(symbol, count=minutes)`. Convert CandleBar to dict. Time as Unix timestamp (TradingView LC format).

2. **Register routes** in `argus/api/routes/__init__.py` and include in server app.

## Constraints
- Do NOT modify IntradayCandleStore or OrderManager — read-only queries
- Do NOT create any new database tables
- Follow existing API patterns (JWT auth, Pydantic response models, error handling)
- Do NOT expose internal ManagedPosition fields beyond what's listed

## Test Targets
- Test /arena/positions returns correct structure with mock managed positions
- Test /arena/candles/{symbol} returns correct candle format
- Test /arena/candles with non-existent symbol returns empty array
- Test /arena/positions with zero open positions returns empty array
- Test JWT auth required on both endpoints
- Minimum: 8 new tests
- Command: `python -m pytest tests/api/test_arena*.py -x -q`

## Definition of Done
- [ ] Both endpoints functional and JWT-protected
- [ ] Response schemas match spec
- [ ] Candle timestamps in Unix format for TradingView LC
- [ ] Tests passing
- [ ] Close-out: `docs/sprints/sprint-32.75/session-6-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-32.75/session-6-closeout.md`

## Tier 2 Review
Test: `python -m pytest tests/api/test_arena*.py -x -q`. Files NOT to modify: OrderManager, IntradayCandleStore, existing API routes.

## Session-Specific Review Focus
1. Verify ManagedPosition field access is safe (no private field access that could break)
2. Verify candle timestamps are UTC Unix timestamps, not ISO strings
3. Verify trailing_stop_price is null (not 0.0) when trail not active
4. Verify JWT auth decorator applied to both endpoints
