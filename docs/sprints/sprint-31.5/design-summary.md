# Sprint 31.5 Design Summary

**Sprint Goal:** Add parallel sweep execution to ExperimentRunner (multiprocessing across grid points), wire universe filtering into the runner's programmatic API (DEF-146), and create missing universe filter YAMLs for Bull Flag and Flat-Top Breakout — enabling fast, representative parameter sweeps across all 10 PatternModule patterns.

**Session Breakdown:**
- Session 1: Parallel sweep infrastructure — add `workers` parameter to `ExperimentRunner.run_sweep()` using `concurrent.futures.ProcessPoolExecutor`; grid-point-level parallelism with shared-nothing workers; main-process-only SQLite writes; progress reporting; error isolation.
  - Creates: (none — modifications only)
  - Modifies: `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/config.py`
  - Integrates: N/A (self-contained modification to existing runner)
- Session 2: DEF-146 universe filtering in ExperimentRunner — move filtering logic from CLI into `run_sweep()` as `universe_filter` parameter; refactor CLI to delegate to runner; add `HistoricalQueryConfig` param for DuckDB access.
  - Creates: (none — modifications only)
  - Modifies: `argus/intelligence/experiments/runner.py`, `scripts/run_experiment.py`
  - Integrates: HistoricalQueryService into ExperimentRunner (Session 1 output is a prerequisite — runner.py modifications must be sequential)
- Session 3: Missing universe filter YAMLs + CLI `--workers` flag + integration tests.
  - Creates: `config/universe_filters/bull_flag.yaml`, `config/universe_filters/flat_top_breakout.yaml`
  - Modifies: `scripts/run_experiment.py` (add `--workers` flag), `config/experiments.yaml` (add `max_workers` field)
  - Integrates: Session 1 parallel infra into CLI via `--workers` flag

**Key Decisions:**
- Grid-point parallelism (not symbol-partitioning): each worker runs one full BacktestEngine instance independently. Simpler, requires zero BacktestEngine changes, memory per worker manageable with filtered universes (~200–500 symbols).
- `ProcessPoolExecutor` (not asyncio): BacktestEngine is CPU-bound (bar-level processing via SyncEventBus). asyncio provides no benefit. OS-level parallelism required.
- Main-process-only SQLite writes: workers return result dicts; main process handles all ExperimentStore persistence. Avoids SQLite concurrent write corruption.
- Fingerprint dedup before dispatch: check store in main process before spawning workers, avoiding wasted compute on already-completed experiments.
- Default `max_workers=4`, CLI `--workers` override. Conservative to avoid memory pressure.

**Scope Boundaries:**
- IN: Parallel sweep execution, DEF-146 programmatic filtering API, missing filter YAMLs, CLI `--workers` flag
- OUT: BacktestEngine internals changes, distributed computing (Ray/Dask), result aggregation/Pareto analysis (Sweep Analysis Impromptu), REST API for sweep triggering (Sprint 31B), shared-memory Parquet loading, GPU acceleration, ExperimentStore schema changes

**Regression Invariants:**
- Sequential execution (`workers=1`) produces identical results to current behavior
- ExperimentStore writes remain sequential (main process only)
- Fingerprint dedup still works
- CLI behavior unchanged when no new flags used
- `--dry-run` does not spawn worker processes
- All 4,823 pytest + 846 Vitest pass
- `ExperimentConfig(extra="forbid")` — adding `max_workers` field must not break existing config loading

**File Scope:**
- Modify: `argus/intelligence/experiments/runner.py`, `argus/intelligence/experiments/config.py`, `scripts/run_experiment.py`, `config/experiments.yaml`
- Create: `config/universe_filters/bull_flag.yaml`, `config/universe_filters/flat_top_breakout.yaml`
- Do not modify: `argus/backtest/engine.py`, `argus/backtest/historical_data_feed.py`, `argus/data/historical_query_service.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, `argus/intelligence/experiments/spawner.py`, `argus/intelligence/experiments/promotion.py`, any frontend files, any strategy files

**Config Changes:**
- YAML: `max_workers: 4` in `config/experiments.yaml` → Pydantic: `ExperimentConfig.max_workers: int = Field(default=4, ge=1, le=32)`

**Test Strategy:**
- Session 1: ~8 tests (parallel execution with mock engine, error isolation, sequential fallback, progress tracking, worker count config)
- Session 2: ~6 tests (filter application in runner, coverage validation, zero-result handling, CLI delegation equivalence)
- Session 3: ~4 tests (filter YAML loading, CLI workers flag, config field validation)
- Estimated total: ~18 new tests
- Full suite baseline: 4,823 pytest + 846 Vitest

**Runner Compatibility:**
- Mode: human-in-the-loop
- Parallelizable sessions: none (all modify runner.py sequentially)
- Runner-specific escalation notes: N/A

**Dependencies:**
- Sprint 31A.75 complete (universe-aware sweep flags in CLI) ✅
- DuckDB dependency installed (`duckdb>=1.0,<2`) ✅
- HistoricalQueryService functional ✅
- Parquet cache available at `data/databento_cache` (LaCie drive must be mounted for integration testing)

**Escalation Criteria:**
- BacktestEngineConfig not picklable → blocks parallelism entirely → escalate
- SQLite corruption from worker writes → design flaw → escalate
- Memory per worker exceeds 2GB with filtered universe → need shared-memory approach → escalate

**Doc Updates Needed:**
- `docs/project-knowledge.md` (CLAUDE.md context): update sprint history, build track, test counts, DEF status
- `CLAUDE.md`: update test counts, sprint reference
- `docs/sprint-history.md`: add Sprint 31.5 entry
- `docs/roadmap.md`: update build track progress

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates per session)
4. Implementation Prompt ×3
5. Review Prompt ×3
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Review Context File
10. Work Journal Handoff Prompt
