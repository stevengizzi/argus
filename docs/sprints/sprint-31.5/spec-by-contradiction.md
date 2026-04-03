# Sprint 31.5: What This Sprint Does NOT Do

## Out of Scope
1. **BacktestEngine internal changes:** No symbol partitioning within a single engine run, no shared-memory Parquet loading, no changes to bar processing or fill model. BacktestEngine is used as-is.
2. **Distributed computing:** No Ray, Dask, cluster computing, or remote worker dispatch. Workers are local OS processes only.
3. **Result aggregation / Pareto analysis:** Sweep results are stored in ExperimentStore; comparative analysis (Pareto frontier, ranking, auto-selection) is deferred to the Sweep Analysis Impromptu.
4. **REST API for sweep triggering:** No HTTP endpoint for starting sweeps — that is Sprint 31B (Research Console).
5. **VariantSpawner/PromotionEvaluator wiring:** The parallel sweep and programmatic API are not wired into the live variant lifecycle pipeline. The runner is invoked via CLI or direct Python call.
6. **GPU acceleration or vectorized backtesting:** Out of scope.
7. **ExperimentStore schema changes:** No new tables, columns, or migrations.
8. **Actually running and analyzing universe-aware sweeps:** The infrastructure is the deliverable. Running 10-pattern sweeps and analyzing results is an operational step after the sprint.

## Edge Cases to Reject
1. **Worker process segfault / OOM:** Handled by ProcessPoolExecutor — the future returns an exception. Log as FAILED, continue with remaining grid points. Do NOT implement custom signal handling or watchdog timers.
2. **Partial sweep resume:** If a sweep is interrupted, re-running will skip already-completed fingerprints (existing dedup behavior). No checkpoint/restart logic within the parallel pool itself.
3. **Workers > grid points:** If `workers=8` but grid has 3 points, ProcessPoolExecutor handles this naturally (only 3 workers active). No special casing needed.
4. **Ctrl+C during parallel sweep:** `ProcessPoolExecutor.shutdown(wait=False, cancel_futures=True)` on KeyboardInterrupt. Print partial results. Do NOT implement graceful drain or result salvaging.
5. **DuckDB unavailable for filtering:** When HistoricalQueryService can't initialize (cache missing/empty), raise `ValueError` with clear message. Do NOT fall back to unfiltered sweep.

## Scope Boundaries
- Do NOT modify: `argus/backtest/engine.py`, `argus/backtest/historical_data_feed.py`, `argus/data/historical_query_service.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, `argus/intelligence/experiments/spawner.py`, `argus/intelligence/experiments/promotion.py`, any frontend files, any strategy files, `argus/core/config.py`
- Do NOT optimize: ABCD O(n³) swing detection (DEF-122) — accept the slowness
- Do NOT refactor: BacktestEngine data loading, ExperimentStore API, existing CLI argument handling (extend, don't rewrite)
- Do NOT add: WebSocket progress streaming, sweep scheduling/cron, email/notification on sweep completion, result visualization

## Interaction Boundaries
- This sprint does NOT change the behavior of: ExperimentStore API, BacktestEngine API, HistoricalQueryService API, VariantSpawner, PromotionEvaluator, any strategy, any REST endpoint, any WebSocket endpoint
- This sprint does NOT affect: live trading pipeline, Command Center frontend, AI layer, Learning Loop, paper trading operation

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Sweep result Pareto analysis | Sweep Analysis Impromptu | — |
| Research Console (REST sweep API) | Sprint 31B | DEF-147 |
| ABCD O(n³) optimization | Unscheduled | DEF-122 |
| Shared-memory Parquet loading | Unscheduled | — |
| FRED macro service for regime context | Sprint 34 | DEF-148 |
