# Sprint 31.5 — Review Context File

> This file is the shared context for all Tier 2 reviews in Sprint 31.5.
> Each session review prompt references this file by path.

---

## Sprint Spec

### Goal
Add multiprocessing-based parallel sweep execution to ExperimentRunner, wire universe filtering into the runner's programmatic API (resolving DEF-146), and create missing universe filter configs — enabling fast, representative parameter sweeps across all 10 PatternModule patterns.

### Deliverables
1. Parallel sweep execution in `ExperimentRunner.run_sweep()` via `ProcessPoolExecutor` with grid-point-level parallelism, main-process SQLite writes, progress reporting, error isolation.
2. DEF-146: `universe_filter: UniverseFilterConfig | None` parameter on `run_sweep()`. CLI delegates to runner.
3. Missing universe filter YAMLs: `bull_flag.yaml`, `flat_top_breakout.yaml`.
4. CLI `--workers N` flag wired to runner.
5. `ExperimentConfig.max_workers` config field.

### Acceptance Criteria
1. `run_sweep(workers=4)` distributes across 4 OS processes; worker crash doesn't terminate pool; `workers=1` identical to current sequential; progress reported; all DB writes in main process; fingerprint dedup before dispatch; `dry_run=True` doesn't spawn workers.
2. `run_sweep(universe_filter=config)` applies static filters via DuckDB + validates coverage; `symbols=None` + filter resolves from cache; both provided = intersection; 0 symbols → ValueError.
3. Both filter YAMLs exist with sensible defaults.
4. `--workers N` passes to `run_sweep()`; default from config.
5. `max_workers` field on ExperimentConfig with `default=4, ge=1, le=32`.

### Config Changes
| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `max_workers` | `ExperimentConfig` | `max_workers` | `4` |

---

## Specification by Contradiction

### Out of Scope
- BacktestEngine internal changes, distributed computing, result aggregation/Pareto analysis, REST sweep API, VariantSpawner/PromotionEvaluator wiring, GPU acceleration, ExperimentStore schema changes, actually running sweeps.

### Do NOT Modify
- `argus/backtest/engine.py`, `argus/backtest/historical_data_feed.py`, `argus/data/historical_query_service.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, `argus/intelligence/experiments/spawner.py`, `argus/intelligence/experiments/promotion.py`, any frontend files, any strategy files, `argus/core/config.py`

### Do NOT Add
- WebSocket progress streaming, sweep scheduling/cron, notifications, result visualization

---

## Sprint-Level Escalation Criteria

1. BacktestEngineConfig not picklable → blocks parallelism → escalate
2. SQLite corruption from worker writes → isolation design wrong → escalate
3. Memory per worker > 2 GB with filtered universe → escalate
4. Worker hangs indefinitely (> 10× sequential time per grid point) → escalate
5. Test count delta exceeds +30 or -5 → pause for scope assessment

## Non-Escalation
- Individual worker exceptions: expected, log as FAILED, continue
- Slower-than-expected parallelism (1.5× vs 3×): acceptable, not escalation
- Unexpected DuckDB symbol counts: log and proceed

---

## Sprint-Level Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Sequential identical to current | `run_sweep(workers=1)` matches pre-sprint output |
| 2 | Store writes main-process only | No `ExperimentStore` in worker functions |
| 3 | Fingerprint dedup works | Duplicate sweep skips all points |
| 4 | CLI unchanged without new flags | `--pattern X --dry-run` same output |
| 5 | `--dry-run` no workers | Completes instantly with `--workers 8` |
| 6 | `ExperimentConfig(extra="forbid")` valid | New field loads; unknown field raises error |
| 7 | `max_workers` config roundtrip | YAML → Pydantic → value matches |
| 8 | DEF-146 filtering matches CLI filtering | Same inputs → same symbol list |
| 9 | 4,823 pytest pass | `python -m pytest -x -q --tb=short -n auto` |
| 10 | 846 Vitest pass | `cd ui && npx vitest run` |
| 11 | Existing experiment tests pass | `python -m pytest tests/intelligence/experiments/ -x -q` |
| 12 | Existing CLI flags work | All pre-sprint flags function unchanged |
