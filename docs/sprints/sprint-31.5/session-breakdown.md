# Sprint 31.5 — Session Breakdown

## Session Dependency Chain
```
Session 1 → Session 2 → Session 3
```
All sessions modify `runner.py` sequentially. No parallelization possible.

---

## Session 1: Parallel Sweep Infrastructure

**Scope:** Add `workers` parameter to `ExperimentRunner.run_sweep()` using `ProcessPoolExecutor`. Grid-point-level parallelism with shared-nothing workers. Main-process SQLite writes. Progress reporting. Error isolation. `max_workers` config field.

| Column | Details |
|--------|---------|
| Creates | (none) |
| Modifies | `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/config.py` |
| Integrates | N/A (self-contained) |
| Parallelizable | false — subsequent sessions modify runner.py |

### Compaction Risk Score

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 0 | 0 |
| Files modified | 2 (runner.py, config.py) | 2 |
| Pre-flight context reads | 4 (runner.py, config.py, engine.py, store.py) | 4 |
| New tests | ~8 | 4 |
| Complex integration wiring | 0 (modifying existing runner, no new component) | 0 |
| External API debugging | 0 | 0 |
| Large single file (>150 lines) | 0 | 0 |
| **Total** | | **10 (Medium)** |

---

## Session 2: DEF-146 — Universe Filtering in ExperimentRunner

**Scope:** Add `universe_filter: UniverseFilterConfig | None` parameter to `run_sweep()`. Move static filter application (DuckDB query) and coverage validation from CLI into the runner. Refactor CLI to delegate. Add `cache_dir_for_query` plumbing.

| Column | Details |
|--------|---------|
| Creates | (none) |
| Modifies | `argus/intelligence/experiments/runner.py`, `scripts/run_experiment.py` |
| Integrates | HistoricalQueryService into ExperimentRunner |
| Parallelizable | false — modifies runner.py (same file as S1) |

### Compaction Risk Score

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 0 | 0 |
| Files modified | 2 (runner.py, run_experiment.py) | 2 |
| Pre-flight context reads | 4 (runner.py, run_experiment.py, historical_query_service.py, core/config.py for UniverseFilterConfig) | 4 |
| New tests | ~6 | 3 |
| Complex integration wiring | 1 (wiring HQS into runner + refactoring CLI delegation) | 3 |
| External API debugging | 0 | 0 |
| Large single file (>150 lines) | 0 | 0 |
| **Total** | | **12 (Medium)** |

---

## Session 3: Filter YAMLs + CLI Workers Flag + Integration Polish

**Scope:** Create Bull Flag and Flat-Top Breakout universe filter YAMLs. Add `--workers` CLI flag wired to runner. Add `max_workers` to `config/experiments.yaml`. End-to-end integration test with mocked BacktestEngine.

| Column | Details |
|--------|---------|
| Creates | `config/universe_filters/bull_flag.yaml`, `config/universe_filters/flat_top_breakout.yaml` |
| Modifies | `scripts/run_experiment.py` (add `--workers`), `config/experiments.yaml` (add `max_workers`) |
| Integrates | Session 1 parallel infra into CLI via `--workers` flag |
| Parallelizable | false — modifies run_experiment.py (same file as S2) |

### Compaction Risk Score

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 2 (YAML configs — trivial) | 4 |
| Files modified | 2 (run_experiment.py, experiments.yaml) | 2 |
| Pre-flight context reads | 3 (run_experiment.py, config.py, existing filter YAMLs) | 3 |
| New tests | ~4 | 2 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large single file (>150 lines) | 0 | 0 |
| **Total** | | **11 (Medium)** |
