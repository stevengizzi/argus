# Sprint 27.8, Session 2: Validation Orchestrator Script

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `scripts/revalidate_strategy.py` (full file — understand CLI interface and output format)
   - `argus/analytics/comparison.py` (compare, pareto_frontier, is_regime_robust)
   - `argus/analytics/evaluation.py` (MultiObjectiveResult, from_backtest_result)
   - `argus/analytics/ensemble_evaluation.py` (EnsembleResult, evaluate_cohort_addition)
   - `argus/backtest/config.py` (BacktestEngineConfig, StrategyType enum)
2. Run the scoped test baseline (DEC-328 — Session 2, scoped):
   ```
   python -m pytest tests/analytics/ -x -q
   ```
   Expected: all passing
3. Verify you are on the correct branch: `main`

## Objective
Create a validation orchestrator script that chains BacktestEngine → walk-forward validation → MultiObjectiveResult → Pareto comparison into a single CLI invocation, for use during the 6-strategy re-validation push.

## Requirements

1. Create `scripts/validate_all_strategies.py` with the following CLI interface:
   ```
   python scripts/validate_all_strategies.py --cache-dir /Volumes/LaCie/argus-cache
   python scripts/validate_all_strategies.py --cache-dir /Volumes/LaCie/argus-cache --strategies orb vwap
   python scripts/validate_all_strategies.py --cache-dir /Volumes/LaCie/argus-cache --output results.json
   ```

2. **Strategy registry:** Define a dict mapping strategy keys to their BacktestEngine configurations (dates, StrategyType, fixed params). Use the same strategy keys as `revalidate_strategy.py`. Include all 7 strategies: `orb`, `scalp`, `vwap`, `afternoon`, `r2g`, `bull_flag`, `flat_top`.

3. **Execution loop:** For each strategy:
   a. Run `revalidate_strategy.py` as a subprocess (NOT as an import — avoid import side effects and keep isolation). Capture JSON output.
   b. Parse the JSON to extract walk-forward results (Sharpe, win rate, profit factor, drawdown, WFE, trade count).
   c. Construct a `MultiObjectiveResult` from the parsed data using `from_backtest_result()` or manual construction.

4. **Comparison phase:** After all strategies complete:
   a. Run `pareto_frontier()` on the collected MultiObjectiveResults (filter to HIGH/MODERATE confidence).
   b. Run `compare()` pairwise for all strategy pairs.
   c. Run `is_regime_robust()` for each strategy.
   d. Optionally run `evaluate_cohort_addition()` to assess ensemble contribution (if `--ensemble` flag provided).

5. **Output:** Print a summary table to stdout:
   ```
   Strategy     | Sharpe | WinRate | PF   | MaxDD  | WFE  | Trades | Confidence | Pareto | Robust
   -------------|--------|---------|------|--------|------|--------|------------|--------|-------
   orb          |  1.82  |  42.1%  | 1.34 | -8.2%  | 0.56 |   847  | HIGH       |   ✓    |   ✓
   vwap         |  1.49  |  55.3%  | 1.28 | -6.1%  | 0.48 |   623  | MODERATE   |   ✓    |   ✓
   ...
   ```
   If `--output` specified, write full results as JSON (all MultiObjectiveResults + comparison matrix + Pareto membership + regime robustness).

6. **Error handling:** If a strategy's validation fails, log the error and continue with remaining strategies. Mark failed strategies in the output. Exit code 0 if all succeed, 1 if any fail.

7. **Progress reporting:** Print strategy name and status as each completes (since each validation takes minutes).

## Constraints
- Do NOT modify any existing production code files
- Do NOT import from `argus.main` or any module that triggers side effects at import time
- Do NOT modify `revalidate_strategy.py`
- The script runs outside the ARGUS runtime — no event bus, no database, no broker connections
- Use subprocess calls to `revalidate_strategy.py` for isolation
- The `--cache-dir` parameter is required (no default — the user must specify where their Parquet cache lives)

## Test Targets
After implementation:
- New tests in `tests/scripts/test_validate_all_strategies.py`:
  1. `test_strategy_registry_has_all_seven` — verify all 7 strategies defined
  2. `test_cli_help_works` — `--help` exits 0
  3. `test_cli_requires_cache_dir` — missing `--cache-dir` exits with error
  4. `test_strategies_filter` — `--strategies orb vwap` only processes those two
  5. `test_output_json_structure` — mock subprocess, verify JSON output has expected keys
  6. `test_failed_strategy_continues` — one strategy failure doesn't abort others
- Minimum new test count: 6
- Test command: `python -m pytest tests/scripts/test_validate_all_strategies.py -x -q`

## Definition of Done
- [ ] `scripts/validate_all_strategies.py` created and functional
- [ ] All 7 strategies registered with correct configs
- [ ] Subprocess isolation from `revalidate_strategy.py`
- [ ] Pareto + comparison + robustness analysis in output
- [ ] Summary table printed to stdout
- [ ] JSON output with `--output` flag
- [ ] Error handling for individual strategy failures
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No production code modified | `git diff --name-only` shows only scripts/ and tests/scripts/ |
| Existing revalidation script unchanged | `git diff scripts/revalidate_strategy.py` shows no changes |
| Import guard works | `python -c "import scripts.validate_all_strategies"` — no side effects |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-27.8/session-2-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: docs/sprints/sprint-27.8/sprint-27.8-review-context.md
2. The close-out report path: docs/sprints/sprint-27.8/session-2-closeout.md
3. The diff range: git diff HEAD~1
4. The test command (final session — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -x -q`
5. Files that should NOT have been modified: anything in `argus/`, `config/`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail so it reflects reality:

1. **Append a "Post-Review Fixes" section to the close-out report file:**
   Open docs/sprints/sprint-27.8/session-2-closeout.md and append:

   ### Post-Review Fixes
   The following findings from the Tier 2 review were addressed in this session:
   | Finding | Fix | Commit |
   |---------|-----|--------|
   | [description from review] | [what you changed] | [short hash] |

   Commit the updated close-out file.

2. **Append a "Resolved" annotation to the review report file:**
   Open docs/sprints/sprint-27.8/session-2-review.md and append after
   the structured verdict:

   ### Post-Review Resolution
   The following findings were addressed by the implementation session
   after this review was produced:
   | Finding | Status |
   |---------|--------|
   | [description] | ✅ Fixed in [short hash] |

   Update the structured verdict JSON: change `"verdict": "CONCERNS"` to
   `"verdict": "CONCERNS_RESOLVED"` and add a `"post_review_fixes"` array.
   Commit the updated review file.

If the reviewer reports CLEAR or ESCALATE, skip this section entirely.

## Session-Specific Review Focus (for @reviewer)
1. Verify NO production code files modified
2. Verify subprocess isolation (revalidate_strategy.py called via subprocess, not imported)
3. Verify strategy registry covers all 7 strategies with correct StrategyType values
4. Verify error handling — one failure doesn't abort the batch
5. Verify JSON output structure includes all expected fields

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| No production code modified | `git diff --name-only HEAD~2` shows only docs/, scripts/, tests/, config/ |
| Full test suite passes | `python -m pytest --ignore=tests/test_main.py -n auto -x -q` |

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if: any production code files (argus/) were modified in this session
- ESCALATE if: revalidate_strategy.py was modified
