# Sprint 32, Session 6: Experiment Runner (Backtest Pre-Filter)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/factory.py` (S2 — factory + fingerprint + grid extraction)
   - `argus/intelligence/experiments/store.py` (S4 — ExperimentStore)
   - `argus/intelligence/experiments/models.py` (S4 — ExperimentRecord, ExperimentStatus)
   - `argus/backtest/engine.py` (BacktestEngine — public API, `BacktestEngineConfig`)
   - `argus/backtest/vectorbt_pattern.py` (PatternBacktester — grid generation reference, `params_to_dict`)
   - `argus/strategies/patterns/base.py` (PatternParam — min_value, max_value, step)
2. Run the test baseline (DEC-328 — Session 2+):
   Scoped: `python -m pytest tests/intelligence/experiments/ -v`
   Expected: all passing
3. Verify Sessions 1–5 committed

## Objective
Create the experiment runner that generates parameter grids from PatternParam metadata, runs BacktestEngine for each configuration against the Parquet cache, and stores results. This is the backtest pre-filter — only configs that clear a minimum bar are eligible for shadow spawning.

## Requirements

1. Create `argus/intelligence/experiments/runner.py` with **`ExperimentRunner`**:

   a. `__init__(self, store: ExperimentStore, config: dict)` — experiment config section

   b. `generate_parameter_grid(self, pattern_name: str, param_subset: list[str] | None = None) -> list[dict[str, Any]]`:
      - Get pattern class via factory's `get_pattern_class()`
      - Instantiate with defaults, call `get_default_params()`
      - For each PatternParam with numeric `min_value`/`max_value`/`step`:
        - If `param_subset` specified and param not in subset, use default only
        - Otherwise generate range: `[min_value, min_value+step, ..., max_value]`
      - Compute cartesian product of all param ranges
      - Return list of param dicts (each is a complete detection param set)
      - Log grid size at INFO level

   c. `async def run_sweep(self, pattern_name: str, cache_dir: str, param_subset: list[str] | None = None, date_range: tuple[str, str] | None = None, symbols: list[str] | None = None, dry_run: bool = False) -> list[ExperimentRecord]`:
      - Generate parameter grid
      - If `dry_run`: log grid size + sample configs, return empty list
      - For each grid point:
        - Compute fingerprint
        - Check if experiment already exists in store with this fingerprint → skip
        - Create ExperimentRecord with status RUNNING
        - Build strategy config with variant params
        - Construct pattern via factory
        - Run BacktestEngine with:
          - The constructed pattern (via a PatternBasedStrategy wrapping)
          - `cache_dir` for Parquet data
          - `date_range` if specified
          - `symbols` if specified (else BacktestEngine uses auto-detection)
          - `risk_overrides` for permissive single-strategy backtesting (DEC-359)
        - Convert BacktestResult to MultiObjectiveResult via `to_multi_objective_result()`
        - Apply pre-filter: if expectancy < `backtest_min_expectancy` or trades < `backtest_min_trades` → status FAILED
        - Otherwise → status COMPLETED
        - Save to store
        - Log progress: `[N/total] pattern=X fingerprint=Y status=Z`
      - Return list of all ExperimentRecords

   d. `def estimate_sweep_time(self, grid_size: int) -> str`:
      - Rough estimate based on ~30s per grid point
      - Return human-readable string ("~25 minutes for 50 grid points")

2. **Grid generation details:**
   - Use PatternParam `param_type` to determine value generation:
     - `int`: `range(min_value, max_value + 1, step)` cast to int
     - `float`: numpy-style `arange(min_value, max_value + step/2, step)` using list comprehension (no numpy dependency)
     - `bool`: `[True, False]`
   - For params without `min_value`/`max_value` (e.g., string params like `entry_mode`): use default only
   - Cap grid size: if cartesian product exceeds 500 points, log WARNING and suggest `param_subset`

3. **BacktestEngine integration:**
   - Use `BacktestEngineConfig` with `risk_overrides` for permissive single-strategy testing (per DEC-359)
   - The runner does NOT modify BacktestEngine — it just invokes it correctly
   - Handle BacktestEngine exceptions gracefully: catch, log ERROR, mark experiment as FAILED

## Constraints
- Do NOT modify BacktestEngine or any backtest module
- Do NOT add numpy as a dependency (use pure Python for float ranges)
- Do NOT run actual backtests in tests — mock BacktestEngine
- Grid generation should be deterministic (same params → same grid order)
- Do NOT import anything from `argus/ui/`

## Test Targets
After implementation:
- New tests in `tests/intelligence/experiments/test_runner.py`:
  - Grid generation: BullFlag with defaults → expected grid size
  - Grid generation: param_subset → only subset varied
  - Grid generation: grid cap warning at >500 points
  - Grid generation: int params produce int values, float params produce float values
  - Sweep: mock BacktestEngine → ExperimentRecords created and stored
  - Pre-filter: negative expectancy → FAILED status
  - Pre-filter: insufficient trades → FAILED status
  - Pre-filter: passing config → COMPLETED status
  - Dry run: no BacktestEngine calls made
  - Duplicate detection: existing fingerprint → skipped
- Minimum new test count: 8
- Test command: `python -m pytest tests/intelligence/experiments/test_runner.py -v`

## Definition of Done
- [ ] `runner.py` created with grid generation + sweep orchestration
- [ ] Grid generation uses PatternParam metadata (no hardcoded params)
- [ ] BacktestEngine invoked per grid point with proper config
- [ ] Pre-filter rejects bad configs
- [ ] Results stored in ExperimentStore
- [ ] All existing tests pass
- [ ] New tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only` |
| BacktestEngine API unchanged | No changes to backtest/ directory |
| Grid generation deterministic | Call twice, assert equal |

## Close-Out
**Write the close-out report to:** docs/sprints/sprint-32/session-6-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32/review-context.md`
2. Close-out report: `docs/sprints/sprint-32/session-6-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/intelligence/experiments/test_runner.py -v`
5. Files that should NOT have been modified: anything in `argus/backtest/`, `main.py`, any strategy file

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify grid generation uses PatternParam introspection only
2. Verify BacktestEngine is mocked in tests (no actual backtest runs)
3. Verify pre-filter thresholds come from config (not hardcoded)
4. Verify grid cap at 500 points with WARNING
5. Verify exception handling around BacktestEngine calls (graceful degradation)
6. Verify duplicate fingerprint check before running backtest

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`
