# Backtesting Rules

The ARGUS backtesting stack has evolved through three generations. These rules
reflect the current strategic posture: **shadow-first validation** (DEC-382)
with `BacktestEngine` as the primary re-validation harness, VectorBT as the
legacy grid-sweep harness, and DuckDB-backed historical queries for
universe-aware sweep pre-filtering.

## Primary Harness: BacktestEngine (Sprint 27+)

[argus/backtest/engine.py](argus/backtest/engine.py) is the production-grade
backtester. It reuses the live codepath (SynchronousEventBus, Risk Manager,
Order Manager, TheoreticalFillModel) and runs over Databento OHLCV-1m data
cached as Parquet. This is the canonical harness for re-validating a
strategy and for producing `MultiObjectiveResult` records consumed by the
Evaluation Framework (Sprint 27.5, regime-tagged) and the Experiment
Pipeline (Sprint 32, promotion evaluation).

**When to use:**
- Re-validating any strategy against Databento-direct data (DEC-132 PROVISIONAL
  backtests → production-grade).
- Producing the `MultiObjectiveResult` that feeds the Experiment Registry.
- Walk-forward validation with `oos_engine="backtest_engine"` (DEC-047, WFE > 0.3).
- Anything that needs bar-level fill semantics (stop > target > time_stop > EOD
  priority) or calibrated slippage (`BacktestEngineConfig.slippage_model_path`).

**Strategy factory:** BacktestEngine builds strategies via
`_create_*_strategy()` helpers. For PatternModule-based strategies the
factory delegates to `build_pattern_from_config()` (Sprint 31A S1, DEF-143
resolution) — direct PatternModule constructors bypass YAML parameter
wiring and were removed.

## Shadow-First Validation (DEC-382, Sprint 31.75)

The current strategic posture for variant promotion is **shadow-first**, not
grid-sweep-first. Instead of computing a large exhaustive parameter grid
upfront, we deploy a small fleet of variants to shadow mode
(`StrategyConfig.mode: shadow`), let the CounterfactualTracker accumulate
real-session data (MAE/MFE, filter accuracy, regime performance), and promote
via Pareto + hysteresis (PromotionEvaluator).

This supersedes the "run a 768-combination VectorBT grid, pick the best
Sharpe, deploy" model. Twenty-two shadow variants are live as of Sprint 31.75.
BacktestEngine is still used for the initial sanity-check on a candidate
variant (does it produce ≥ 10 trades over a 6-month window? does it make
sense in a regime-tagged comparison?) — but the authoritative signal comes
from live shadow data.

## DuckDB Historical Query Layer (Sprint 31A.5)

[argus/data/historical_query_service.py](argus/data/historical_query_service.py)
exposes a read-only analytical view over the Parquet cache via DuckDB.
`validate_symbol_coverage(symbols, min_bars=...)` is the authoritative
pre-filter for sweep universes — ExperimentRunner uses it before spawning
any backtest (`run_sweep(universe_filter=...)`, DEF-146 resolution).

The Parquet cache comes in two flavors (Sprint 31.85):

- `data/databento_cache/` — ~983K monthly files, the read-only source of
  truth for `BacktestEngine`.
- `data/databento_cache_consolidated/` — ~24K per-symbol files with
  embedded `symbol` column, a derived artifact for `HistoricalQueryService`.

`HistoricalQueryConfig.cache_dir` in `config/historical_query.yaml` points
at the consolidated cache after operator activation. The consolidation
script (`scripts/consolidate_parquet_cache.py`) has non-bypassable
row-count validation — see `architecture.md` § Non-Bypassable Validation.

## Legacy Harness: VectorBT

The VectorBT sweep infrastructure in [argus/backtest/vectorbt_*.py](argus/backtest/)
is the legacy exhaustive-grid path. It remains in place for:

- Cross-validation of BacktestEngine trade counts (DEC-069: VectorBT trade
  count must be ≥ Replay trade count for PASS).
- Historical grid sweeps over already-validated strategies where a dense
  parameter surface is actually informative.

For any new strategy, default to the BacktestEngine + shadow-first approach.
Reach for VectorBT only when the grid dimensionality and iteration speed
actively justify it. The implementation rules below remain authoritative
when VectorBT *is* the right tool.

### VectorBT Sweep Architecture (MANDATORY when used)

All VectorBT parameter sweep implementations MUST follow the precompute +
vectorize pattern established in `vectorbt_orb.py` and
`vectorbt_vwap_reclaim.py`. Never use the naive per-combination approach.

1. **Precompute entries per day ONCE** — Entry candidate detection is
   parameter-independent. Compute all potential entries for each qualifying
   day in a single pass. Store results with NumPy arrays for post-entry
   price data.
2. **Filter entries by parameters at runtime** — The outer parameter loop
   only filters the precomputed entries by (pullback depth, bars, volume,
   etc.), never re-detects entries.
3. **Vectorized exit detection** — Use NumPy boolean masks to find
   stop/target/time-stop/EOD exits. Never use `iterrows()` or per-bar Python
   loops in the exit path.

### Antipatterns to AVOID

```python
# WRONG — 500x slower. Per-combination Python loops with DataFrame operations.
for params in param_combos:           # 768 iterations
    for day in trading_days:           # ~700 days
        trades = simulate_day(df, params)  # iterrows() inside

# CORRECT — Precompute + vectorize
entries = precompute_entries_for_day(day_df)  # ONCE per day, NumPy arrays
for params in param_combos:
    filtered = [e for e in entries if passes_filter(e, params)]
    for entry in filtered:
        trade = find_exit_vectorized(entry.highs, entry.lows, ...)  # NumPy masks
```

### Performance Expectation

The ORB sweep remains the internal reference: a full parameter grid over
the ORB precompute pipeline completes in tens of seconds, not hours. If a
new VectorBT sweep takes more than a couple of minutes on the comparable
dataset, the architecture is wrong — compare against the ORB or VWAP
reference before accepting the runtime. Pre-Databento benchmarks
("29-symbol, 35-month in 30s") are no longer meaningful as absolute
numbers; they only mattered as a relative sanity check against the naive
path.

### Parallel Sweep Infrastructure (Sprint 31.5)

`ExperimentRunner.run_sweep(workers=N)` uses `ProcessPoolExecutor` with
`_run_single_backtest()` as the module-level worker. Fingerprint dedup and
ExperimentStore writes happen in the main process (not in workers) to avoid
SQLite contention. CLI flag: `--workers`.

### Exit Priority (Worst-Case-for-Longs)

When multiple exit conditions trigger on the same bar, priority order is:
1. **Stop loss** — always uses stop price (worst case)
2. **Target** — uses target price
3. **Time stop** — uses close, BUT check if stop also hit (use stop price if so)
4. **EOD** — uses close, BUT check if stop also hit (use stop price if so)

This ensures backtest results are conservative (never better than reality).
BacktestEngine's `TheoreticalFillModel.evaluate_bar_exit()` is the
authoritative implementation; VectorBT paths must match it.
