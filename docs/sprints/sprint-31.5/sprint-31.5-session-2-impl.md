# Sprint 31.5, Session 2: DEF-146 — Universe Filtering in ExperimentRunner

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/experiments/runner.py` (just modified in Session 1)
   - `scripts/run_experiment.py`
   - `argus/data/historical_query_service.py` (read-only — understand the API)
   - `argus/core/config.py` (read-only — find `UniverseFilterConfig`)
2. Run the scoped test baseline (DEC-328):
   Scoped: `python -m pytest tests/intelligence/experiments/ tests/scripts/ -x -q`
   Expected: all passing (full suite confirmed by Session 1 close-out)
3. Verify you are on the correct branch: `main`
4. Verify Session 1 is committed and the `workers` parameter exists on `run_sweep()`

## Objective
Move universe filtering logic (static DuckDB filters + coverage validation) from the CLI script into `ExperimentRunner.run_sweep()` so that programmatic callers (VariantSpawner, future Research Console) get pre-filtering automatically. Refactor the CLI to delegate to the runner instead of doing its own filtering. This resolves DEF-146.

## Requirements

1. In `argus/intelligence/experiments/runner.py`, add parameters to `run_sweep()`:
   ```python
   async def run_sweep(
       self,
       pattern_name: str,
       cache_dir: str,
       param_subset: list[str] | None = None,
       date_range: tuple[str, str] | None = None,
       symbols: list[str] | None = None,
       dry_run: bool = False,
       exit_sweep_params: list[ExitSweepParam] | None = None,
       workers: int = 1,
       universe_filter: "UniverseFilterConfig | None" = None,  # NEW — DEF-146
   ) -> list[ExperimentRecord]:
   ```

2. In `run_sweep()`, when `universe_filter` is not None, before grid dispatch:
   - Resolve the date range (existing `_resolve_date_range()`)
   - Instantiate `HistoricalQueryService` with `HistoricalQueryConfig(enabled=True, cache_dir=cache_dir)`
   - If the service is unavailable (cache missing/empty), raise `ValueError` with descriptive message
   - Apply static filters (min_price, max_price, min_avg_volume) via a SQL query against the DuckDB view — replicate the logic from `_apply_universe_filter()` in `run_experiment.py` (but as a method on ExperimentRunner or a private helper)
   - Log dynamic filters that are skipped (same `_DYNAMIC_FILTER_FIELDS` list)
   - When `symbols` is not None and `universe_filter` is provided, use `symbols` as candidate list (intersection)
   - When `symbols` is None, discover all available symbols from the service
   - Validate coverage via `service.validate_symbol_coverage(symbols, start_date_str, end_date_str, min_bars=100)`
   - Drop symbols with insufficient coverage
   - Close the service after use
   - If 0 symbols remain, raise `ValueError("No symbols remaining after universe filtering and coverage validation")`
   - Set the resolved symbols list for grid dispatch

3. In `scripts/run_experiment.py`, refactor the `run()` function:
   - Remove the inline `_apply_universe_filter()` and `_validate_coverage()` calls from the main flow
   - Instead, pass `universe_filter=filter_config` to `runner.run_sweep()` when `--universe-filter` is active
   - Keep the `_apply_universe_filter()` and `_validate_coverage()` functions in the file (they are useful standalone utilities and are tested) but the main `run()` path delegates to the runner
   - The `--symbols` flag still passes symbols directly; the runner handles the intersection
   - Print the same progress messages ("Symbols after universe filter: N", "Symbols after coverage validation: N") — the runner should return or log these counts

4. Add a private method `_resolve_universe_symbols()` on `ExperimentRunner` that encapsulates the filtering logic:
   ```python
   def _resolve_universe_symbols(
       self,
       universe_filter: UniverseFilterConfig,
       cache_dir: str,
       start_date: str,
       end_date: str,
       candidate_symbols: list[str] | None = None,
   ) -> list[str]:
   ```
   This method is synchronous (DuckDB queries are sync). Called from `run_sweep()` before the async grid dispatch.

## Constraints
- Do NOT modify: `argus/data/historical_query_service.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, `argus/backtest/engine.py`, any frontend files, any strategy files, `argus/core/config.py`
- Do NOT change: `HistoricalQueryService` API, `UniverseFilterConfig` model, BacktestEngine API
- Do NOT remove: `_apply_universe_filter()` and `_validate_coverage()` from `run_experiment.py` — keep as standalone utilities
- The `_DYNAMIC_FILTER_FIELDS` list stays in `run_experiment.py` but should also be referenced in the runner (import or duplicate)
- Type annotation for `UniverseFilterConfig` should use string annotation (`"UniverseFilterConfig"`) with `TYPE_CHECKING` import to avoid circular dependency if needed

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_run_sweep_with_universe_filter_resolves_symbols` — mock HistoricalQueryService, provide filter with min_avg_volume, verify symbols resolved and passed to grid dispatch
  2. `test_run_sweep_universe_filter_with_candidate_symbols` — provide both `symbols` and `universe_filter`, verify intersection behavior
  3. `test_run_sweep_universe_filter_zero_symbols_raises` — filter that eliminates all symbols raises ValueError
  4. `test_run_sweep_universe_filter_service_unavailable_raises` — mock unavailable service, verify ValueError
  5. `test_resolve_universe_symbols_static_filters` — unit test private method with mock service
  6. `test_cli_delegates_filter_to_runner` — verify CLI passes universe_filter to run_sweep instead of doing inline filtering
- Minimum new test count: 6
- Test command: `python -m pytest tests/intelligence/experiments/ tests/scripts/ -x -q`

## Definition of Done
- [ ] `universe_filter` parameter on `run_sweep()`
- [ ] `_resolve_universe_symbols()` private method on ExperimentRunner
- [ ] DuckDB-based static filter application inside runner
- [ ] Coverage validation inside runner
- [ ] 0-symbol ValueError
- [ ] CLI delegates to runner for filtering
- [ ] CLI standalone filter functions preserved (not removed)
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] DEF-146 resolved
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| CLI unchanged without `--universe-filter` | `--pattern X --dry-run` same output |
| CLI filter functions still exist | `grep -n "_apply_universe_filter" scripts/run_experiment.py` |
| Runner filtering matches CLI filtering | Compare symbol lists for same inputs |
| Parallel sweep still works (Session 1) | `run_sweep(workers=2)` test from Session 1 still passes |
| HistoricalQueryService not modified | `git diff argus/data/historical_query_service.py` is empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31.5/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.5/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/intelligence/experiments/ tests/scripts/ -x -q`
5. Files that should NOT have been modified: `argus/data/historical_query_service.py`, `argus/intelligence/experiments/store.py`, `argus/backtest/engine.py`, any frontend files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31.5/session-2-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the post-review fix
documentation protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify `_resolve_universe_symbols()` closes the HistoricalQueryService after use (no leaked DuckDB connections)
2. Verify dynamic filter fields are logged as skipped (not silently ignored)
3. Verify the CLI still works identically when `--universe-filter` is NOT passed (symbols=None, universe_filter=None path)
4. Verify the intersection logic: when both `symbols` and `universe_filter` provided, the filter restricts the candidate list
5. Verify no circular imports from `UniverseFilterConfig` usage in runner.py
6. Verify `run_sweep()` signature is backward compatible (all new params have defaults)

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Sequential identical to current | `run_sweep(workers=1)` matches pre-sprint output |
| 4 | CLI unchanged without new flags | `--pattern X --dry-run` same output |
| 8 | DEF-146 filtering matches CLI filtering | Same inputs → same symbol list |
| 9 | 4,823 pytest pass | `python -m pytest -x -q --tb=short -n auto` |
| 11 | Existing experiment tests pass | `python -m pytest tests/intelligence/experiments/ -x -q` |
| 12 | Existing CLI flags work | All pre-sprint flags function unchanged |

## Sprint-Level Escalation Criteria (for @reviewer)
1. BacktestEngineConfig not picklable → escalate
2. SQLite corruption from worker writes → escalate
3. Memory per worker > 2 GB → escalate
4. Worker hangs indefinitely → escalate
5. Test count delta exceeds +30 or -5 → pause
