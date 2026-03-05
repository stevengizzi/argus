## Sprint 4a Polish — Final Cleanup

Two items were missed in the previous polish session:

### 1. Add missing test_place_limit_order test

File: tests/execution/test_alpaca_broker.py

Add `test_place_limit_order` — test place_order() with a limit order. Verify
LimitOrderRequest is constructed with correct limit_price and submitted to
TradingClient. Follow the existing test_place_market_order and
test_place_stop_order patterns.

### 2. Fix remaining ruff warnings

Run `ruff check argus/ tests/` (NO grep filter) and fix ALL warnings:

- 2× SIM105 in argus/data/alpaca_data_service.py (lines ~191, ~198):
  Replace try/except asyncio.CancelledError/pass with
  `async with contextlib.suppress(asyncio.CancelledError):`
  Note: contextlib.suppress works with await in Python 3.11+.
  Actually — for async tasks, `contextlib.suppress` works fine since
  the await is inside the `with` block. Add `import contextlib` at module level.

- 1× SIM105 in tests/data/test_alpaca_data_service.py (line ~503): Same fix.

- 1× SIM117 in tests/data/test_alpaca_data_service.py (line ~154):
  Combine nested `with` statements into a single `with` using comma separation.

After fixes:
1. Run `ruff check argus/ tests/` with NO grep filter — must show 0 errors/warnings
2. Run `pytest tests/ -x -q` — all tests pass
3. Report final count (target: 283+)
4. Commit: `fix: Sprint 4a final cleanup — missing limit order test + ruff warnings`
5. Push to origin