# Sprint 21.6: Session Breakdown

## Session Overview

| Session | Scope | Score | Risk |
|---------|-------|-------|------|
| S1 | ExecutionRecord dataclass + DB schema + migration | 8.5 | Low |
| S2 | OrderManager integration + execution record tests | 7.5 | Low |
| S3 | Re-validation harness script | 11.5 | Medium |
| [Human Step] | Run backtests for all 7 strategies | — | — |
| S4 | Results analysis + YAML updates + validation report | 11 | Medium |

**Dependency chain:** S1 → S2 → S3 → [Human Step] → S4

---

## Session 1: ExecutionRecord Dataclass + DB Schema

**Objective:** Create the ExecutionRecord data model and database table. This is the foundation for execution quality logging — purely data model, no integration with live code yet.

**Creates:**
- `argus/execution/execution_record.py` — ExecutionRecord dataclass with all DEC-358 §5.1 fields, plus a `save_execution_record(db_manager, record)` async helper function for DB persistence

**Modifies:**
- `argus/db/schema.sql` — Add `execution_records` table with `CREATE TABLE IF NOT EXISTS`
- `argus/db/manager.py` — Add migration block in `_apply_schema()` for the `execution_records` table (same pattern as quality_grade/quality_score migration)

**Integrates:** N/A (standalone data model, no callers yet)

**Parallelizable:** false (foundation for S2)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (execution_record.py) | 2 |
| Files modified | 2 (schema.sql, manager.py) | 2 |
| Pre-flight context reads | 3 (schema.sql, manager.py, events.py for field reference) | 3 |
| New tests | 3 (dataclass creation, DB round-trip, schema existence) | 1.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large single file (>150 lines) | 0 | 0 |
| **Total** | | **8.5** |

**Risk level:** Low (0–8 threshold boundary, proceed)

---

## Session 2: OrderManager Integration + Tests

**Objective:** Wire ExecutionRecord logging into OrderManager's entry fill handler. Add `expected_fill_price` and `signal_timestamp` to PendingManagedOrder. Create comprehensive test coverage.

**Creates:**
- `tests/execution/test_execution_record.py` — Test suite covering record creation, DB persistence, OM integration, error isolation, nullable fields

**Modifies:**
- `argus/execution/order_manager.py` — Add `expected_fill_price: float = 0.0` and `signal_timestamp: datetime | None = None` fields to `PendingManagedOrder`; set these in `on_approved()` from `signal.entry_price` and `self._clock.now()`; add execution record creation + persistence in `_handle_entry_fill()` wrapped in try/except

**Integrates:** Session 1's `ExecutionRecord` dataclass and `save_execution_record()` function

**Parallelizable:** false (depends on S1)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (test_execution_record.py) | 2 |
| Files modified | 1 (order_manager.py) | 1 |
| Pre-flight context reads | 2 (order_manager.py, execution_record.py from S1) | 2 |
| New tests | 5 (OM fill creates record, error isolation, nullable fields, SimulatedBroker path, slippage computation) | 2.5 |
| Complex integration wiring | 0 (adding to one existing handler, not 3+ components) | 0 |
| External API debugging | 0 | 0 |
| Large single file (>150 lines) | 0 | 0 |
| **Total** | | **7.5** |

**Risk level:** Low (proceed)

---

## Session 3: Re-Validation Harness Script

**Objective:** Build a CLI script that runs BacktestEngine + fixed-parameter walk-forward for any strategy, reads baseline metrics from YAML, compares results, and outputs structured JSON with divergence flags.

**Creates:**
- `scripts/revalidate_strategy.py` — CLI with `--strategy`, `--start`, `--end`, `--output-dir`, `--cache-dir` args. Supports all 7 `StrategyType` values. Reads current params from YAML, runs `run_fixed_params_walk_forward(oos_engine="backtest_engine")`, compares against `backtest_summary` baseline, outputs `{strategy}_validation.json`.
- `tests/backtest/test_revalidation_harness.py` — Tests for config loading, baseline extraction, divergence detection

**Modifies:** None

**Integrates:** Uses BacktestEngine (Sprint 27) and walk-forward infrastructure (existing) as-is, no modifications

**Parallelizable:** false (depends on S1/S2 being merged, though functionally independent — keeping sequential for simpler ordering)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 2 (revalidate_strategy.py, test file) | 4 |
| Files modified | 0 | 0 |
| Pre-flight context reads | 5 (walk_forward.py, config.py, engine.py, 1 strategy YAML, BacktestEngineConfig) | 5 |
| New tests | 5 (config loading, baseline extraction, divergence thresholds, JSON output format, missing baseline) | 2.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large single file (>150 lines) | 0 (script ~120 lines) | 0 |
| **Total** | | **11.5** |

**Risk level:** Medium (proceed with caution)

---

## Human Step: Run All 7 Backtests

**Not a Claude Code session.** The developer runs the validation script 7 times:

```bash
# Example invocations (adjust dates as needed):
python scripts/revalidate_strategy.py --strategy orb --start 2023-03-01 --end 2025-03-01 --output-dir data/backtest_runs/validation/
python scripts/revalidate_strategy.py --strategy orb_scalp --start 2023-03-01 --end 2025-03-01 --output-dir data/backtest_runs/validation/
python scripts/revalidate_strategy.py --strategy vwap_reclaim --start 2023-03-01 --end 2025-03-01 --output-dir data/backtest_runs/validation/
python scripts/revalidate_strategy.py --strategy afternoon_momentum --start 2023-03-01 --end 2025-03-01 --output-dir data/backtest_runs/validation/
python scripts/revalidate_strategy.py --strategy red_to_green --start 2023-03-01 --end 2025-03-01 --output-dir data/backtest_runs/validation/
python scripts/revalidate_strategy.py --strategy bull_flag --start 2023-03-01 --end 2025-03-01 --output-dir data/backtest_runs/validation/
python scripts/revalidate_strategy.py --strategy flat_top_breakout --start 2023-03-01 --end 2025-03-01 --output-dir data/backtest_runs/validation/
```

**Expected output:** 7 JSON files in `data/backtest_runs/validation/`, one per strategy.

**First-run data cache:** If Databento OHLCV-1m data is not cached locally, `HistoricalDataFeed` will download it on first run. This may take significant time (30+ minutes per strategy depending on symbol count). Subsequent runs use Parquet cache.

**Timing note:** Run ORB Breakout first as a smoke test. If it completes successfully and produces reasonable results, proceed with the remaining 6.

---

## Session 4: Results Analysis + YAML Updates + Validation Report

**Objective:** Read all 7 validation result JSONs. Compare against provisional Alpaca-era baselines. Update all strategy YAML `backtest_summary` sections. If any strategy shows significant divergence, analyze and document parameter change recommendations. Produce the final validation comparison report.

**Creates:**
- `docs/sprints/sprint-21.6/validation-report.md` — Per-strategy comparison table (old metrics | new metrics | divergence | status), summary assessment, forward-compatibility notes for 27.5

**Modifies:**
- `config/strategies/orb_breakout.yaml` — Update `backtest_summary` section
- `config/strategies/orb_scalp.yaml` — Update `backtest_summary` section
- `config/strategies/vwap_reclaim.yaml` — Update `backtest_summary` section
- `config/strategies/afternoon_momentum.yaml` — Update `backtest_summary` section
- `config/strategies/red_to_green.yaml` — Update `backtest_summary` section
- `config/strategies/bull_flag.yaml` — Update `backtest_summary` section
- `config/strategies/flat_top_breakout.yaml` — Update `backtest_summary` section

**Integrates:** Consumes Session 3 script output + Human Step results

**Parallelizable:** false (depends on Human Step)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (validation-report.md) | 2 |
| Files modified | 7 (strategy YAMLs) | 7 |
| Pre-flight context reads | 2 (1 result JSON for structure, 1 YAML for update pattern) | 2 |
| New tests | 0 (analysis + config updates, no new code) | 0 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large single file (>150 lines) | 0 | 0 |
| **Total** | | **11** |

**Risk level:** Medium (proceed with caution — high file modification count but each is a small, mechanical YAML edit)

---

## Test Estimate Summary

| Session | New Tests | Coverage Target |
|---------|-----------|----------------|
| S1 | 3 | ExecutionRecord dataclass, DB schema, migration |
| S2 | 5 | OM integration, error isolation, nullable fields, slippage math |
| S3 | 5 | Config loading, baseline extraction, divergence thresholds, JSON format |
| S4 | 0 | YAML updates only (validated by existing config tests) |
| **Total** | **~13** | |

Starting test baseline: 3,010 pytest + 620 Vitest
Expected final: ~3,023 pytest + 620 Vitest
