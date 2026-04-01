# Sprint 32, Session 1: Pydantic Config Alignment

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/config.py` (StrategyConfig base + all 7 pattern config classes)
   - `argus/strategies/patterns/base.py` (PatternParam dataclass)
   - `argus/strategies/patterns/bull_flag.py` (constructor params + `get_default_params()`)
   - `argus/strategies/patterns/flat_top_breakout.py` (constructor params + `get_default_params()`)
   - `argus/strategies/patterns/dip_and_rip.py` (constructor params)
   - `argus/strategies/patterns/hod_break.py` (constructor params)
   - `argus/strategies/patterns/gap_and_go.py` (constructor params)
   - `argus/strategies/patterns/abcd.py` (constructor params)
   - `argus/strategies/patterns/premarket_high_break.py` (constructor params)
2. Run the test baseline (DEC-328 — Session 1 of sprint):
   Full suite: `python -m pytest tests/ -n auto -q`
   Expected: ~4,212 tests, all passing
3. Verify you are on the correct branch: `sprint-32` (create from `main`)

## Objective
Add all missing detection parameter fields to the 6 incomplete PatternModule Pydantic config models so that every pattern constructor kwarg has a corresponding validated config field. DipAndRipConfig is already complete and serves as the reference pattern.

## Requirements

1. In `argus/core/config.py`, add these fields to **BullFlagConfig** (3 missing):
   - `min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)` — minimum detection confidence
   - `pole_strength_cap_pct: float = Field(default=0.10, gt=0, le=1.0)` — pole move % for max score
   - `breakout_excess_cap_pct: float = Field(default=0.02, gt=0, le=0.50)` — breakout excess % for max score

2. In `argus/core/config.py`, add these fields to **FlatTopBreakoutConfig** (2 missing):
   - `min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)` — minimum detection confidence
   - `max_range_narrowing: float = Field(default=0.5, ge=0, le=1.0)` — consolidation range narrowing factor

3. In `argus/core/config.py`, add this field to **HODBreakConfig** (1 missing):
   - `vwap_extended_pct: float = Field(default=0.02, gt=0, le=0.10)` — VWAP extension percentage for scoring

4. In `argus/core/config.py`, add these fields to **GapAndGoConfig** (6 missing):
   - `prior_day_avg_volume: float = Field(default=1_000_000.0, gt=0)` — baseline for relative volume calc
   - `min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)` — minimum detection confidence
   - `gap_atr_cap: float = Field(default=3.0, gt=0, le=10.0)` — cap for gap-to-ATR ratio scoring
   - `volume_score_cap: float = Field(default=5.0, gt=0, le=20.0)` — cap for relative volume scoring
   - `vwap_hold_score_divisor: float = Field(default=3.0, gt=0, le=10.0)` — divisor for VWAP hold bar scoring
   - `catalyst_base_score: float = Field(default=10.0, ge=0, le=25.0)` — base score for catalyst bonus

5. In `argus/core/config.py`, add these fields to **ABCDConfig** (13 missing — largest gap):
   - `swing_lookback: int = Field(default=5, ge=2, le=20)` — bars on each side for swing detection
   - `min_swing_atr_mult: float = Field(default=0.5, gt=0, le=5.0)` — min swing size as ATR multiple
   - `fib_b_min: float = Field(default=0.382, gt=0, le=1.0)` — min BC retracement of AB
   - `fib_b_max: float = Field(default=0.618, gt=0, le=1.0)` — max BC retracement of AB
   - `fib_c_min: float = Field(default=0.500, gt=0, le=1.0)` — reserved for CD extension lower bound
   - `fib_c_max: float = Field(default=0.786, gt=0, le=1.5)` — reserved for CD extension upper bound
   - `leg_price_ratio_min: float = Field(default=0.8, gt=0, le=2.0)` — min CD/AB price ratio
   - `leg_price_ratio_max: float = Field(default=1.2, gt=0, le=3.0)` — max CD/AB price ratio
   - `leg_time_ratio_min: float = Field(default=0.5, gt=0, le=2.0)` — min CD/AB time ratio
   - `leg_time_ratio_max: float = Field(default=2.0, gt=0, le=5.0)` — max CD/AB time ratio
   - `completion_tolerance_percent: float = Field(default=1.0, ge=0, le=5.0)` — D-zone tolerance %
   - `stop_buffer_atr_mult: float = Field(default=0.5, gt=0, le=3.0)` — ATR multiple for stop below C
   - `target_extension: float = Field(default=1.272, gt=0, le=3.0)` — Fibonacci extension for target

6. In `argus/core/config.py`, add these fields to **PreMarketHighBreakConfig** (3 missing):
   - `min_score_threshold: float = Field(default=0.0, ge=0, le=100.0)` — minimum detection confidence
   - `vwap_extended_pct: float = Field(default=0.02, gt=0, le=0.10)` — VWAP extension for scoring
   - `gap_up_bonus_pct: float = Field(default=3.0, ge=0, le=20.0)` — gap-up threshold for bonus scoring

7. Write a **cross-validation test** in `tests/test_config_param_alignment.py` that programmatically verifies alignment:
   ```python
   # For each of the 7 PatternModule patterns:
   # 1. Instantiate the pattern class with defaults
   # 2. Call get_default_params()
   # 3. For each PatternParam, verify the name exists as a field
   #    in the corresponding Pydantic config class
   # 4. Verify the Pydantic field default matches PatternParam.default
   ```

8. Write **boundary validation tests** verifying Pydantic rejects out-of-range values (at least 3 patterns).

9. Write **backward compatibility tests** verifying all 7 existing YAML configs in `config/strategies/` load without errors through their respective Pydantic models.

## Constraints
- Do NOT modify any pattern `.py` files — only `config.py` and test files
- Do NOT change any existing field defaults — only add new fields
- Do NOT add `model_config = ConfigDict(extra="forbid")` to StrategyConfig or its subclasses (this would break existing YAML configs that have `exit_management` blocks which aren't modeled on StrategyConfig — known pre-existing issue outside this sprint's scope)
- Verify each new field's default matches the corresponding pattern constructor default EXACTLY

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `tests/test_config_param_alignment.py` — cross-validation (7 patterns)
  - Boundary validation tests (3+ patterns)
  - YAML backward compat tests (7 configs)
- Minimum new test count: 8
- Test command: `python -m pytest tests/test_config_param_alignment.py -v`

## Config Validation
This session adds 28 config fields. Write a test that for each of the 7 patterns:
1. Instantiates the pattern, calls `get_default_params()`
2. Loads the corresponding Pydantic config model's `model_fields`
3. Verifies every `PatternParam.name` exists in the model fields
4. Verifies the default values match

Expected mapping: see Requirements section above for all 28 fields.

## Definition of Done
- [ ] All 28 missing fields added to 6 config classes
- [ ] All existing tests pass
- [ ] Cross-validation test passes for all 7 patterns
- [ ] Boundary tests pass
- [ ] Backward compat tests pass for all 7 YAML configs
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| R2: Existing YAML configs still load | Backward compat tests pass |
| R3: Constructor defaults unchanged | Cross-validation test verifies defaults match |
| R10: Invalid values rejected | Boundary tests pass |
| R13: No silently ignored keys | Cross-validation test covers all PatternParam names |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-32/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-32/review-context.md`
2. The close-out report path: `docs/sprints/sprint-32/session-1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/test_config_param_alignment.py tests/core/test_config.py -v`
5. Files that should NOT have been modified: any pattern `.py` file, `main.py`, `vectorbt_pattern.py`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the post-review fix
documentation protocol (see implementation prompt template).

## Session-Specific Review Focus (for @reviewer)
1. Verify every new field default matches the corresponding pattern constructor default exactly
2. Verify Pydantic Field bounds (ge/le/gt/lt) are reasonable and don't conflict with PatternParam min_value/max_value
3. Verify no existing fields were accidentally modified
4. Verify the cross-validation test is truly programmatic (not hardcoded pattern names)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md` — Regression Checklist section.

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md` — Escalation Criteria section.
