# Sprint 21.6: Regression Checklist

## Critical Invariants

### Order Execution Flow (Sessions 1–2)
- [ ] OrderManager `on_approved()` → `on_fill()` → `_handle_entry_fill()` flow operates identically with and without execution record logging
- [ ] `_handle_entry_fill()` creates ManagedPosition correctly regardless of whether execution record persistence succeeds or fails
- [ ] PositionOpenedEvent is published with correct data after entry fill (unaffected by execution logging)
- [ ] SimulatedBroker immediate fill path (entry fill event in `on_approved()`) still works — no timing changes from added logging
- [ ] Bracket order submission in `on_approved()` is not altered in any way
- [ ] `share_count=0` early-return in `on_approved()` still works (Dynamic Sizer pending path)
- [ ] No new exceptions can propagate from execution record code into the order management path (all wrapped in try/except)

### Database Schema (Session 1)
- [ ] `execution_records` table created with `CREATE TABLE IF NOT EXISTS` — does not fail on re-initialization
- [ ] Existing tables (`trades`, `orders`, `positions`, `quality_history`, etc.) are not modified
- [ ] WAL mode and foreign keys still enabled after schema application
- [ ] Migration pattern (try/except pass for existing columns) does not interfere with existing quality_grade/quality_score migrations
- [ ] `:memory:` database path still works for testing

### Walk-Forward & BacktestEngine (Session 3)
- [ ] `run_fixed_params_walk_forward()` behavior unchanged — harness script uses it as a consumer, does not modify it
- [ ] `_validate_oos_backtest_engine()` behavior unchanged
- [ ] BacktestEngine `run()` method behavior unchanged
- [ ] HistoricalDataFeed Parquet caching behavior unchanged
- [ ] ScannerSimulator behavior unchanged

### Strategy Configs (Session 4)
- [ ] Only `backtest_summary` sections in strategy YAMLs are modified — no changes to operating parameters, risk limits, or universe filters
- [ ] If parameters ARE changed due to divergence: original values documented in validation report, rationale provided, and change is limited to the specific parameter values (not structural YAML changes)
- [ ] All 7 strategy YAML files remain valid — loadable by their respective Pydantic config models

### Test Suite
- [ ] All existing tests pass (baseline: 3,010 pytest + 620 Vitest, 0 failures)
- [ ] No existing test behavior modified
- [ ] New tests are additive (in `tests/execution/test_execution_record.py` and `tests/backtest/test_revalidation_harness.py`)
- [ ] `--ignore=tests/test_main.py` still required for xdist runs (DEF-048)

### Files NOT Modified (Boundary Check)
- [ ] No changes to any file in `argus/strategies/` (strategy .py files)
- [ ] No changes to `argus/backtest/engine.py`
- [ ] No changes to `argus/backtest/walk_forward.py`
- [ ] No changes to `argus/backtest/historical_data_feed.py`
- [ ] No changes to `argus/core/events.py`
- [ ] No changes to `argus/core/risk_manager.py`
- [ ] No changes to `argus/core/sync_event_bus.py`
- [ ] No changes to any file in `argus/ui/` (frontend)
- [ ] No changes to any file in `argus/api/` (API routes)
