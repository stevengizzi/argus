# Sprint 21.6 — Review Context File

> This file is the shared reference for all Tier 2 reviews in Sprint 21.6.
> Each session review prompt references this file by path.

---

## Sprint Spec

### Goal
Re-validate all 7 active strategies using BacktestEngine with Databento OHLCV-1m data (DEC-132). Add ExecutionRecord logging to OrderManager per DEC-358 §5.1 for future slippage model calibration.

### Deliverables
1. ExecutionRecord infrastructure — dataclass, `execution_records` DB table, fire-and-forget logging in OrderManager fill handlers
2. Re-validation harness script — CLI tool for BacktestEngine + fixed-parameter walk-forward per strategy
3. Strategy re-validation results — all 7 strategies validated with Databento OHLCV-1m data
4. Updated strategy YAML configs — `backtest_summary` sections with Databento-era metrics
5. Validation comparison report — old vs new metrics per strategy

### Key Constraints
- ExecutionRecord logging is fire-and-forget — exceptions caught, never propagates
- Fixed-parameter walk-forward (current params), NOT full re-optimization
- Divergence thresholds: Sharpe diff > 0.5, win rate diff > 10pp, profit factor diff > 0.5
- No strategy `.py` files modified. No frontend work. No API endpoints.
- `expected_fill_price` from `SignalEvent.entry_price` at signal time
- DEC range: 359–361 (if needed). DEF range: 090–091 (if needed).

### Forward-Compatibility Notes
- Sprint 27.5's `RegimeMetrics` should accommodate multi-dimensional regime vectors (design note only)
- BacktestEngine results will be retroactively structured into `MultiObjectiveResult` by Sprint 27.5

---

## Specification by Contradiction

### Out of Scope
- Slippage model calibration (Sprint 27.5)
- MultiObjectiveResult format (Sprint 27.5)
- RegimeVector multi-dimensional classification (Sprint 27.6)
- Full walk-forward re-optimization
- Strategy logic changes
- Frontend work
- New API endpoints
- BacktestEngine or walk-forward engine modifications

### Do NOT Modify
- Any file in `argus/strategies/` (strategy .py files)
- `argus/backtest/engine.py`
- `argus/backtest/walk_forward.py`
- `argus/backtest/historical_data_feed.py`
- `argus/core/events.py`
- `argus/core/risk_manager.py`
- `argus/core/sync_event_bus.py`
- Any file in `argus/ui/` (frontend)
- Any file in `argus/api/` (API routes)

---

## Sprint-Level Regression Checklist

### Order Execution Flow (Sessions 1–2)
- [ ] OrderManager `on_approved()` → `on_fill()` → `_handle_entry_fill()` flow operates identically with and without execution record logging
- [ ] `_handle_entry_fill()` creates ManagedPosition correctly regardless of whether execution record persistence succeeds or fails
- [ ] PositionOpenedEvent is published with correct data after entry fill (unaffected by execution logging)
- [ ] SimulatedBroker immediate fill path still works — no timing changes
- [ ] Bracket order submission in `on_approved()` is not altered
- [ ] `share_count=0` early-return in `on_approved()` still works
- [ ] No new exceptions can propagate from execution record code into the order management path

### Database Schema (Session 1)
- [ ] `execution_records` table created with `CREATE TABLE IF NOT EXISTS`
- [ ] Existing tables not modified
- [ ] WAL mode and foreign keys still enabled
- [ ] Migration pattern does not interfere with existing migrations
- [ ] `:memory:` database path still works for testing

### Walk-Forward & BacktestEngine (Session 3)
- [ ] `run_fixed_params_walk_forward()` behavior unchanged
- [ ] BacktestEngine `run()` method behavior unchanged
- [ ] HistoricalDataFeed Parquet caching behavior unchanged

### Strategy Configs (Session 4)
- [ ] Only `backtest_summary` sections modified — no operating parameters, risk limits, or universe filters
- [ ] All 7 YAML files remain valid and loadable

### Test Suite
- [ ] All existing tests pass (baseline: 3,010 pytest + 620 Vitest)
- [ ] No existing test behavior modified
- [ ] `--ignore=tests/test_main.py` still required for xdist

### Files NOT Modified (Boundary Check)
- [ ] No changes to any file in `argus/strategies/`
- [ ] No changes to `argus/backtest/engine.py`, `walk_forward.py`, `historical_data_feed.py`
- [ ] No changes to `argus/core/events.py`, `risk_manager.py`, `sync_event_bus.py`
- [ ] No changes to any file in `argus/ui/` or `argus/api/`

---

## Sprint-Level Escalation Criteria

### During Sessions 1–2 (Execution Logging)
1. ExecutionRecord schema conflicts with DEC-358 §5.1 spec
2. OrderManager fill handler changes affect order routing behavior
3. Database migration breaks existing tables

### During Session 3 (Validation Harness)
4. Walk-forward does not support a strategy with `oos_engine="backtest_engine"`
5. Strategy YAML params cannot be mapped to walk-forward fixed params

### During Human Step / Session 4 (Results Analysis)
6. More than 3 strategies produce zero trades
7. More than 3 strategies show significant divergence
8. Any strategy's WFE drops below 0.1 on Databento data
9. BacktestEngine produces dramatically different trade counts than VectorBT (>5× difference)
