# Sprint 31.5 — Escalation Criteria

## Tier 3 Escalation Triggers

1. **BacktestEngineConfig not picklable:** If `ProcessPoolExecutor` raises `PicklingError` on config or result objects, the parallelism approach is blocked. Do NOT attempt workarounds (custom `__reduce__`, dill, cloudpickle) without Tier 3 review — the root cause may indicate a deeper serialization issue.

2. **SQLite corruption from worker writes:** If any test or run shows evidence of concurrent SQLite writes from worker processes (WAL corruption, "database is locked" errors from workers), the isolation design is wrong. Halt and escalate — the invariant that all writes occur in the main process has been violated.

3. **Memory per worker exceeds 2 GB:** If a single worker loading a filtered universe (< 500 symbols, 12 months) exceeds 2 GB resident memory, the grid-point-level parallelism approach may not scale. Escalate to evaluate symbol-partitioning or shared-memory alternatives.

4. **Worker hangs indefinitely:** If a `ProcessPoolExecutor` future does not return within 10× the sequential time for a single grid point (~300s), there may be a deadlock in BacktestEngine. Do NOT add arbitrary timeouts without understanding the root cause.

5. **Test count delta exceeds +30 or -5:** If the sprint produces more than 30 new tests or any existing test is removed/disabled, pause for scope assessment.

## Non-Escalation Guidance

- **Individual worker exceptions:** Expected behavior. Log as FAILED, continue. Not an escalation.
- **Slower-than-expected parallelism:** Speedup of 1.5× instead of 3× on 4 cores is acceptable — GIL, I/O contention, and process startup overhead reduce theoretical speedup. Not an escalation unless < 1.0× (parallel is slower than sequential).
- **DuckDB query returning unexpected symbol counts:** Log and proceed. Symbol counts depend on cache contents and filter parameters — validate manually after the sprint.
