# Sprint 31.5, Session 1: Parallel Sweep Infrastructure

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/experiments/runner.py`
   - `argus/intelligence/experiments/config.py`
   - `argus/intelligence/experiments/store.py` (read-only — understand the store API)
   - `argus/backtest/config.py` (read-only — understand `BacktestEngineConfig`, verify picklability)
2. Run the test baseline (DEC-328):
   Full suite: `python -m pytest -x -q --tb=short -n auto`
   Expected: 4,823 tests, all passing
3. Verify you are on the correct branch: `main`
4. Verify `BacktestEngineConfig` is picklable:
   ```python
   import pickle
   from argus.backtest.config import BacktestEngineConfig, StrategyType
   from datetime import date
   from pathlib import Path
   cfg = BacktestEngineConfig(strategy_type=StrategyType.BULL_FLAG, start_date=date(2025,1,1), end_date=date(2025,12,31), cache_dir=Path("data/databento_cache"))
   pickle.dumps(cfg)  # Must not raise
   ```
   If this fails, ESCALATE immediately (Tier 3 — see escalation criteria).

## Objective
Add multiprocessing-based parallel sweep execution to `ExperimentRunner`. Each grid point runs in its own OS process via `ProcessPoolExecutor`. Workers are shared-nothing (own BacktestEngine, own data loading). The main process handles all ExperimentStore writes.

## Requirements

1. In `argus/intelligence/experiments/config.py`, add to `ExperimentConfig`:
   ```python
   max_workers: int = Field(default=4, ge=1, le=32)
   ```

2. In `argus/intelligence/experiments/runner.py`, add a module-level worker function (must be top-level for pickling):
   ```python
   def _run_single_backtest(args: dict) -> dict:
       """Worker function — runs one BacktestEngine grid point in a subprocess.
       
       Args:
           args: Dict with keys: strategy_type, strategy_id, symbols, start_date,
                 end_date, cache_dir, config_overrides, detection_params, fingerprint.
       
       Returns:
           Dict with keys: fingerprint, status ("completed" | "failed"), 
           backtest_result (dict | None), error (str | None).
       """
   ```
   This function must:
   - Create a `BacktestEngineConfig` from the args
   - Create a `BacktestEngine` and call `asyncio.run(engine.run())`
   - Convert result to `MultiObjectiveResult` if possible
   - Return a result dict (never raise — catch all exceptions and return error dict)
   - NOT import or use `ExperimentStore`
   - NOT import or use any SQLite connection

3. In `ExperimentRunner.run_sweep()`, add a `workers: int = 1` parameter. When `workers > 1`:
   - Perform fingerprint dedup in the main process (existing logic) — build a list of grid points that need execution
   - Dispatch the non-skipped grid points to `ProcessPoolExecutor(max_workers=workers)`
   - Use `executor.map()` or `as_completed()` pattern to collect results
   - For each completed future: create/update `ExperimentRecord` and call `self._store.save_experiment()` in the main process
   - Log progress: `[completed/total]` after each result
   - Handle `KeyboardInterrupt`: `executor.shutdown(wait=False, cancel_futures=True)`, return partial results

4. When `workers == 1`, use the existing sequential loop (zero behavior change). This is the default and the fallback.

5. When `dry_run=True`, skip all worker dispatch regardless of `workers` value (existing behavior preserved).

6. Add progress logging during parallel execution:
   ```
   [5/50] pattern=bull_flag fingerprint=abc123... status=COMPLETED (4 workers)
   ```

## Constraints
- Do NOT modify: `argus/backtest/engine.py`, `argus/backtest/historical_data_feed.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, any frontend files, any strategy files
- Do NOT change: ExperimentStore API, BacktestEngine API, existing `run_sweep()` return type
- Do NOT add: WebSocket progress, scheduling, result visualization
- Workers must NOT import or instantiate `ExperimentStore` — all persistence in main process
- Worker function must be module-level (not a method) for pickling compatibility

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_run_sweep_parallel_distributes_work` — mock BacktestEngine, verify 4 grid points with `workers=2` all complete
  2. `test_run_sweep_parallel_worker_error_isolated` — mock one grid point to raise, verify others complete and failed one gets FAILED status
  3. `test_run_sweep_sequential_identical` — compare output of `workers=1` vs existing sequential path
  4. `test_run_sweep_parallel_skips_existing_fingerprints` — pre-populate store, verify dedup happens before dispatch
  5. `test_run_sweep_dry_run_no_workers` — verify dry_run with workers > 1 returns empty list without spawning processes
  6. `test_run_sweep_parallel_store_writes_main_process` — verify store.save_experiment is called from main process (mock store, assert call count)
  7. `test_config_max_workers_field` — verify ExperimentConfig.max_workers loads from dict, respects ge=1/le=32 bounds
  8. `test_run_single_backtest_returns_dict` — unit test the worker function directly
- Minimum new test count: 8
- Test command: `python -m pytest tests/intelligence/experiments/ -x -q`

## Config Validation
Write a test that verifies the `max_workers` field:
1. `ExperimentConfig(max_workers=4)` succeeds
2. `ExperimentConfig(max_workers=0)` raises `ValidationError` (ge=1)
3. `ExperimentConfig(max_workers=33)` raises `ValidationError` (le=32)
4. `ExperimentConfig()` has `max_workers == 4` (default)

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| `max_workers` | `max_workers` |

## Definition of Done
- [ ] `max_workers` field on ExperimentConfig
- [ ] Module-level `_run_single_backtest()` worker function
- [ ] `run_sweep()` accepts `workers` param and dispatches via ProcessPoolExecutor when > 1
- [ ] Sequential fallback for `workers=1` (identical to current)
- [ ] Fingerprint dedup in main process before dispatch
- [ ] All store writes in main process
- [ ] Progress logging with worker count
- [ ] KeyboardInterrupt handling
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Sequential identical to current | `run_sweep(workers=1)` test |
| Store writes main-process only | No ExperimentStore import in worker function |
| Fingerprint dedup before dispatch | Test with pre-populated store |
| `ExperimentConfig(extra="forbid")` still valid | Config test with new field |
| Existing experiment tests pass | `python -m pytest tests/intelligence/experiments/ -x -q` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31.5/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.5/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/intelligence/experiments/ -x -q`
5. Files that should NOT have been modified: `argus/backtest/engine.py`, `argus/backtest/historical_data_feed.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, any frontend files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31.5/session-1-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the post-review fix
documentation protocol (see implementation prompt template).

## Session-Specific Review Focus (for @reviewer)
1. Verify `_run_single_backtest()` is module-level (not a method) — required for pickling
2. Verify no `ExperimentStore` import or usage in the worker function
3. Verify `asyncio.run()` is used inside the worker (not awaiting in the main event loop)
4. Verify fingerprint dedup query happens BEFORE ProcessPoolExecutor dispatch
5. Verify KeyboardInterrupt handler calls `shutdown(wait=False, cancel_futures=True)`
6. Verify `workers=1` uses the existing sequential loop (not ProcessPoolExecutor with 1 worker)

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Sequential identical to current | `run_sweep(workers=1)` matches pre-sprint output |
| 2 | Store writes main-process only | No `ExperimentStore` in worker functions |
| 3 | Fingerprint dedup works | Duplicate sweep skips all points |
| 4 | CLI unchanged without new flags | `--pattern X --dry-run` same output |
| 5 | `ExperimentConfig(extra="forbid")` valid | New field loads; unknown field raises error |
| 9 | 4,823 pytest pass | `python -m pytest -x -q --tb=short -n auto` |
| 11 | Existing experiment tests pass | `python -m pytest tests/intelligence/experiments/ -x -q` |

## Sprint-Level Escalation Criteria (for @reviewer)
1. BacktestEngineConfig not picklable → escalate
2. SQLite corruption from worker writes → escalate
3. Memory per worker > 2 GB → escalate
4. Worker hangs indefinitely → escalate
5. Test count delta exceeds +30 or -5 → pause
