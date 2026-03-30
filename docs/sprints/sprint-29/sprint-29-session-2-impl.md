# Sprint 29, Session 2: Retrofit Existing Patterns + PatternBacktester Grid Generation

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternParam from S1)
   - `argus/strategies/patterns/bull_flag.py` (current `get_default_params()`)
   - `argus/strategies/patterns/flat_top_breakout.py` (current `get_default_params()`)
   - `argus/backtest/vectorbt_pattern.py` (current grid generation logic)
2. Run the scoped test baseline:
   `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q --timeout=30`
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on branch `sprint-29`

## Objective
Convert Bull Flag and Flat-Top Breakout `get_default_params()` returns from `dict[str, Any]` to `list[PatternParam]` with complete metadata (ranges, steps, descriptions, categories). Update PatternBacktester to generate parameter sweep grids from PatternParam metadata instead of hardcoded ±20%/±40% percentage variations.

## Requirements

1. In `argus/strategies/patterns/bull_flag.py`, replace the `get_default_params()` method:
   - Current: returns `dict[str, Any]` with param names → default values
   - New: returns `list[PatternParam]` with each parameter wrapped in PatternParam
   - Every numeric parameter must have `min_value`, `max_value`, and `step`
   - Every parameter must have a non-empty `description`
   - Assign `category` to each param: "detection", "scoring", or "filtering"
   - The `default` values must EXACTLY match the current dict values (behavioral preservation)
   - Expected: ≥8 PatternParam entries

2. In `argus/strategies/patterns/flat_top_breakout.py`, apply the same conversion:
   - Same rules as Bull Flag
   - Expected: ≥8 PatternParam entries

3. In `argus/backtest/vectorbt_pattern.py`, update grid generation:
   - Current: takes `get_default_params()` dict, generates variations at ±20% and ±40%
   - New: takes `get_default_params()` list of PatternParam, generates grid from `(min_value, max_value, step)`
   - For each PatternParam with numeric type (int or float):
     - Generate values from `min_value` to `max_value` stepping by `step`
     - Always include the `default` value in the grid
     - For `param_type=int`, round generated values to int
   - For `param_type=bool`: include both True and False
   - For params with `min_value=None` or `max_value=None`: use only the default value (no sweep)
   - Produce a list of param dicts (each dict is one parameter combination for a backtest run)
   - Add a helper: `params_to_dict(params: list[PatternParam]) -> dict[str, Any]` that extracts `{name: default}` for use in code that needs the old dict format

4. Verify that the PatternBacktester can still run a backtest on Bull Flag with the new grid generation. This is a functional check, not a full validation — just confirm it completes without error.

## Constraints
- Do NOT modify: `argus/strategies/patterns/base.py` (locked after S1)
- Do NOT modify: `core/events.py`, `execution/order_manager.py`, `ui/`, `api/`
- Do NOT change: Bull Flag or Flat-Top `detect()` or `score()` methods — only `get_default_params()`
- The `default` values in PatternParam MUST exactly match the current dict values
- Do NOT change: PatternBasedStrategy wrapper

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Bull Flag `get_default_params()` returns `list[PatternParam]`
  2. Bull Flag all params have non-empty description and valid category
  3. Flat-Top `get_default_params()` returns `list[PatternParam]`
  4. Flat-Top all params have non-empty description and valid category
  5. Grid generation from PatternParam produces valid combinations
  6. Grid generation includes default values
  7. Grid generation for int params produces int values
  8. Grid generation for bool params produces [True, False]
  9. `params_to_dict()` helper produces correct dict
  10. PatternBacktester on Bull Flag completes without error (integration)
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q --timeout=30`

## Definition of Done
- [ ] Bull Flag `get_default_params()` returns `list[PatternParam]` with ≥8 params
- [ ] Flat-Top `get_default_params()` returns `list[PatternParam]` with ≥8 params
- [ ] All params have complete metadata (description, type, range, step, category)
- [ ] Default values exactly match pre-retrofit values
- [ ] PatternBacktester generates grids from PatternParam ranges
- [ ] `params_to_dict()` helper available
- [ ] PatternBacktester on Bull Flag completes without error
- [ ] 10+ new tests passing
- [ ] All existing tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Bull Flag detect() unchanged | `git diff argus/strategies/patterns/bull_flag.py` — no detect() changes |
| Bull Flag score() unchanged | `git diff argus/strategies/patterns/bull_flag.py` — no score() changes |
| Flat-Top detect() unchanged | `git diff argus/strategies/patterns/flat_top_breakout.py` — no detect() changes |
| Flat-Top score() unchanged | `git diff argus/strategies/patterns/flat_top_breakout.py` — no score() changes |
| Default values preserved | New test compares PatternParam defaults vs known values |
| PatternBacktester produces results | Integration test on Bull Flag |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-29/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-29/review-context.md`
2. The close-out report path: `docs/sprints/sprint-29/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q --timeout=30`
5. Files that should NOT have been modified: `argus/strategies/patterns/base.py`, `argus/strategies/pattern_strategy.py`, `core/events.py`, `execution/order_manager.py`, `ui/`, `api/`

## Post-Review Fix Documentation
If @reviewer reports CONCERNS and you fix them, update both close-out and review files per template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify Bull Flag and Flat-Top `detect()` and `score()` methods are UNCHANGED
2. Verify all PatternParam `default` values exactly match pre-retrofit dict values
3. Verify grid generation handles edge cases: bool params, None min/max, int rounding
4. Verify `params_to_dict()` helper round-trips correctly
5. Verify no changes to base.py or pattern_strategy.py (locked after S1)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-29/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-29/review-context.md`
