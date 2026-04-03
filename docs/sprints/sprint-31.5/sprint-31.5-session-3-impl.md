# Sprint 31.5, Session 3: Filter YAMLs + CLI Workers Flag + Integration Polish

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `scripts/run_experiment.py` (just modified in Session 2)
   - `argus/intelligence/experiments/config.py`
   - `config/universe_filters/` (read all existing YAMLs for consistency)
   - `config/experiments.yaml`
2. Run the scoped test baseline (DEC-328):
   Scoped: `python -m pytest tests/intelligence/experiments/ tests/scripts/ -x -q`
   Expected: all passing (full suite confirmed by Session 2 close-out)
3. Verify you are on the correct branch: `main`
4. Verify Session 2 is committed and `universe_filter` parameter exists on `run_sweep()`

## Objective
Create missing universe filter YAML files for Bull Flag and Flat-Top Breakout, add `--workers` CLI flag to `run_experiment.py`, add `max_workers: 4` to `config/experiments.yaml`, and write integration tests verifying the full end-to-end flow (CLI → runner → parallel execution → store).

## Requirements

1. Create `config/universe_filters/bull_flag.yaml`:
   ```yaml
   # Bull Flag pattern — continuation after pole/flag.
   # Needs liquid mid-to-large cap names with enough volatility for visible poles.
   min_price: 10.0
   max_price: 500.0
   min_avg_volume: 500000
   ```

2. Create `config/universe_filters/flat_top_breakout.yaml`:
   ```yaml
   # Flat-Top Breakout — resistance cluster consolidation + breakout.
   # Needs liquid names with defined resistance levels.
   min_price: 10.0
   max_price: 500.0
   min_avg_volume: 500000
   ```

3. In `scripts/run_experiment.py`, add `--workers` argument:
   ```python
   parser.add_argument(
       "--workers",
       type=int,
       default=None,
       help="Number of parallel workers (default: from config max_workers, fallback 4)",
   )
   ```
   In `run()`, resolve workers count:
   ```python
   workers = args.workers if args.workers is not None else config.max_workers
   ```
   Pass to `runner.run_sweep(..., workers=workers)`.
   **Note:** Do NOT use `args.workers or config.max_workers` — `0` is falsy in Python, so `--workers 0` would silently fall through to the config default. The `is not None` check is correct.

4. In `config/experiments.yaml`, add below the existing fields:
   ```yaml
   max_workers: 4
   ```

5. Write an integration test that verifies the full CLI → runner → parallel flow with mocked BacktestEngine:
   - Mock `BacktestEngine.run()` to return a minimal `BacktestResult`
   - Call `run_experiment.main(["--pattern", "bull_flag", "--dry-run", "--workers", "2"])` and verify it completes
   - Verify that `--workers 1` and `--workers 4` both parse correctly

6. Write a test that loads each universe filter YAML and verifies it parses into a valid `UniverseFilterConfig`:
   ```python
   @pytest.mark.parametrize("name", [
       "bull_flag", "flat_top_breakout", "abcd", "dip_and_rip",
       "gap_and_go", "hod_break", "micro_pullback", 
       "narrow_range_breakout", "premarket_high_break", "vwap_bounce",
   ])
   def test_universe_filter_yaml_valid(name):
       ...
   ```

## Constraints
- Do NOT modify: `argus/intelligence/experiments/runner.py` (finalized in S1+S2), `argus/backtest/engine.py`, `argus/data/historical_query_service.py`, any frontend files, any strategy files
- Do NOT change: Existing universe filter YAML files (abcd, dip_and_rip, gap_and_go, hod_break, micro_pullback, narrow_range_breakout, premarket_high_break, vwap_bounce)
- Do NOT add: REST endpoints, WebSocket handlers, notifications
- Universe filter YAML values should be reasonable for each pattern type — not just copy-paste

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_universe_filter_yamls_all_valid` — parametrized test loading all 10 filter YAMLs into UniverseFilterConfig
  2. `test_cli_workers_flag_parsed` — verify `--workers 8` sets args.workers to 8
  3. `test_cli_workers_default_from_config` — verify default workers comes from ExperimentConfig.max_workers
  4. `test_experiments_yaml_max_workers_field` — load config/experiments.yaml, verify `max_workers` key is recognized by ExperimentConfig
- Minimum new test count: 4
- Test command (final session — full suite): `python -m pytest -x -q --tb=short -n auto`

## Config Validation
Verify `max_workers: 4` in `config/experiments.yaml` roundtrips through `ExperimentConfig`:
1. Load YAML, construct `ExperimentConfig(**raw)`
2. Assert `.max_workers == 4`
3. Assert no extra keys present (extra="forbid" catches this)

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| `max_workers` | `max_workers` |

## Definition of Done
- [ ] `config/universe_filters/bull_flag.yaml` exists with sensible values
- [ ] `config/universe_filters/flat_top_breakout.yaml` exists with sensible values
- [ ] `--workers` CLI flag on `run_experiment.py`
- [ ] `max_workers: 4` in `config/experiments.yaml`
- [ ] All 10 universe filter YAMLs parse successfully
- [ ] CLI integration test with mocked engine
- [ ] All existing tests pass (full suite — final session)
- [ ] 4+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All 10 filter YAMLs valid | Parametrized UniverseFilterConfig test |
| `config/experiments.yaml` loads without error | `ExperimentConfig(**yaml.safe_load(...))` |
| `--workers` defaults correctly | Test with no `--workers` flag |
| Existing CLI flags unaffected | `--pattern X --dry-run` same output |
| Full pytest suite passes | `python -m pytest -x -q --tb=short -n auto` |
| Full Vitest suite passes | `cd ui && npx vitest run` |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31.5/session-3-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.5/session-3-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (final session — full suite): `python -m pytest -x -q --tb=short -n auto`
5. Files that should NOT have been modified: `argus/intelligence/experiments/runner.py` (finalized in S1+S2), `argus/backtest/engine.py`, `argus/data/historical_query_service.py`, existing universe filter YAMLs, any frontend files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31.5/session-3-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the post-review fix
documentation protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify Bull Flag and Flat-Top filter values are reasonable (not just copy-paste of another pattern)
2. Verify `--workers` flag defaults to `config.max_workers`, not hardcoded 4
3. Verify `max_workers: 4` in experiments.yaml is recognized by ExperimentConfig (extra="forbid" would catch typos)
4. Verify existing universe filter YAMLs are NOT modified (only new files created)
5. Verify full test suite passes (this is the final session)

## Sprint-Level Regression Checklist (for @reviewer)
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
| 9 | 4,823+ pytest pass | `python -m pytest -x -q --tb=short -n auto` |
| 10 | 846 Vitest pass | `cd ui && npx vitest run` |
| 11 | Existing experiment tests pass | `python -m pytest tests/intelligence/experiments/ -x -q` |
| 12 | Existing CLI flags work | All pre-sprint flags function unchanged |

## Sprint-Level Escalation Criteria (for @reviewer)
1. BacktestEngineConfig not picklable → escalate
2. SQLite corruption from worker writes → escalate
3. Memory per worker > 2 GB → escalate
4. Worker hangs indefinitely → escalate
5. Test count delta exceeds +30 or -5 → pause