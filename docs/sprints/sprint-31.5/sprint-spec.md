# Sprint 31.5: Parallel Sweep Infrastructure

## Goal
Add multiprocessing-based parallel sweep execution to ExperimentRunner, wire universe filtering into the runner's programmatic API (resolving DEF-146), and create missing universe filter configs — enabling fast, representative parameter sweeps across all 10 PatternModule patterns.

## Scope

### Deliverables
1. **Parallel sweep execution in ExperimentRunner** — `run_sweep()` gains a `workers: int` parameter using `concurrent.futures.ProcessPoolExecutor`. Each worker runs one full BacktestEngine instance (grid-point-level parallelism). Main process handles all SQLite writes. Includes progress reporting, error isolation, and sequential fallback for `workers=1`.
2. **DEF-146: Universe filtering in ExperimentRunner** — `run_sweep()` gains a `universe_filter: UniverseFilterConfig | None` parameter. When provided, the runner applies static filters via HistoricalQueryService and validates coverage before dispatching grid points. CLI script delegates to the runner instead of doing its own filtering.
3. **Missing universe filter YAMLs** — `config/universe_filters/bull_flag.yaml` and `config/universe_filters/flat_top_breakout.yaml` created with appropriate filter parameters.
4. **CLI `--workers` flag** — `scripts/run_experiment.py` gains `--workers N` argument (default from config `max_workers`, fallback 4) that passes through to `run_sweep()`.
5. **`max_workers` config field** — `ExperimentConfig.max_workers` Pydantic field wired to `config/experiments.yaml`.

### Acceptance Criteria
1. Parallel sweep execution:
   - `run_sweep(workers=4)` distributes grid points across 4 OS processes
   - Each worker creates its own BacktestEngine — no shared mutable state
   - A worker crash (exception) does not terminate the pool; the failed grid point gets FAILED status and remaining points continue
   - `run_sweep(workers=1)` produces identical results to current sequential behavior
   - Progress is reported as completed/total during execution
   - All ExperimentStore writes occur in the main process (no SQLite from workers)
   - Fingerprint dedup checked in main process before dispatch to workers
   - `dry_run=True` does not spawn worker processes
2. DEF-146 universe filtering:
   - `run_sweep(universe_filter=filter_config)` applies min_price/max_price/min_avg_volume via DuckDB and validates coverage
   - When `symbols` is None and `universe_filter` is provided, symbols are resolved from the Parquet cache
   - When both `symbols` and `universe_filter` are provided, the filter intersects with the provided symbol list
   - When filtering produces 0 symbols, `ValueError` is raised with descriptive message
   - CLI script's `_apply_universe_filter()` and `_validate_coverage()` still work but delegate to the runner for programmatic callers
3. Missing universe filter YAMLs:
   - `config/universe_filters/bull_flag.yaml` exists with sensible defaults (min_price, max_price, min_avg_volume)
   - `config/universe_filters/flat_top_breakout.yaml` exists with sensible defaults
4. CLI `--workers` flag:
   - `--workers 8` passes `workers=8` to `run_sweep()`
   - Default uses `ExperimentConfig.max_workers` value
   - `--workers 1` forces sequential execution
5. `max_workers` config field:
   - `ExperimentConfig.max_workers` field with `default=4, ge=1, le=32`
   - `config/experiments.yaml` updated with `max_workers: 4`
   - Config loading does not break existing configs without the field (default used)

### Performance Benchmarks
| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Parallel speedup (4 workers, 20-point grid) | ≥2.5× vs sequential | Wall-clock comparison in integration test |
| Per-worker memory (200 symbols, 12 months) | < 1.5 GB | Manual observation during sweep |

### Config Changes
| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `max_workers` (in `config/experiments.yaml`) | `ExperimentConfig` | `max_workers` | `4` |

## Dependencies
- Sprint 31A.75 complete (universe-aware sweep flags in CLI) ✅
- DuckDB dependency installed (`duckdb>=1.0,<2`) ✅
- HistoricalQueryService functional ✅
- Parquet cache at `data/databento_cache` (LaCie drive — for integration testing only; unit tests use mocks)

## Relevant Decisions
- DEC-345: Separate SQLite DBs for different concerns — ExperimentStore in `data/experiments.db`; no concurrent writes from workers
- DEC-328: Test suite tiering — full suite at sprint entry + close-outs; scoped for mid-sprint pre-flights
- DEF-146: DuckDB BacktestEngine pre-filter wiring in ExperimentRunner (this sprint resolves it)
- DEF-122: ABCD O(n³) swing detection — not blocking, just slow; no optimization in this sprint

## Relevant Risks
- RSK: BacktestEngineConfig may not be fully picklable (Pydantic models generally are, but Path fields and custom types need verification)
- RSK: Memory pressure with many workers on large symbol sets (mitigated by conservative default `max_workers=4` and universe filtering)

## Session Count Estimate
3 sessions estimated. All backend, no visual review needed. Session order is strictly sequential (all modify runner.py). Low-risk sprint — well-understood patterns, no new data models or architectural changes.
