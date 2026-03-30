# Sprint 28.5, Session S1: Exit Math Pure Functions

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/fill_model.py` (pattern reference — same design approach)
   - `argus/core/events.py` (ExitReason, FillExitReason for reference)
2. Run the test baseline (DEC-328 — Session 1 of sprint, full suite):
   ```
   python -m pytest -x -q -n auto && cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20
   ```
   Expected: ~3,845 pytest + 680 Vitest, all passing
3. Verify you are on the correct branch: `sprint-28.5`
4. Create the branch if needed: `git checkout -b sprint-28.5`

## Objective
Create `argus/core/exit_math.py` — a stateless pure-function library for computing trailing stop prices, escalation stop prices, and effective (tightest) stop selection. This module is shared by Order Manager, BacktestEngine, and CounterfactualTracker.

## Requirements

1. Create `argus/core/exit_math.py` with the following functions:

   a. `compute_trailing_stop(high_watermark: float, atr_value: float | None, config: TrailingStopConfig) -> float | None`
      - If `config.enabled` is False, return None
      - If `config.type == "atr"`:
        - If `atr_value` is None, zero, or negative → return None (AMD-12). Do not produce a trail price from invalid ATR.
        - Trail distance = `atr_value * config.atr_multiplier`
      - If `config.type == "percent"`: trail distance = `high_watermark * config.percent`
      - If `config.type == "fixed"`: trail distance = `config.fixed_distance`
      - Apply floor: `trail_distance = max(trail_distance, config.min_trail_distance)`
      - Return `high_watermark - trail_distance`

   b. `compute_escalation_stop(entry_price: float, high_watermark: float, elapsed_seconds: float, time_stop_seconds: float | None, config: ExitEscalationConfig) -> float | None`
      - If `config.enabled` is False, return None
      - If `time_stop_seconds` is None, return None
      - If `config.phases` is empty, return None
      - Compute `elapsed_pct = elapsed_seconds / time_stop_seconds`
      - Find the latest phase where `elapsed_pct >= phase.elapsed_pct` (phases sorted ascending)
      - Apply the phase's `stop_to` formula (AMD-5):
        - `"breakeven"` → `entry_price`
        - `"quarter_profit"` → `entry_price + 0.25 * (high_watermark - entry_price)`
        - `"half_profit"` → `entry_price + 0.50 * (high_watermark - entry_price)`
        - `"three_quarter_profit"` → `entry_price + 0.75 * (high_watermark - entry_price)`
      - Return the computed stop price
      - If no phase has been reached yet, return None

   c. `compute_effective_stop(original_stop: float, trail_stop: float | None, escalation_stop: float | None) -> float`
      - Return the maximum (tightest for longs) of all non-None values
      - `original_stop` is always non-None (it's the signal's stop)
      - If both trail_stop and escalation_stop are None, return original_stop

2. Use a `StopToLevel` StrEnum for the `stop_to` values: `BREAKEVEN`, `QUARTER_PROFIT`, `HALF_PROFIT`, `THREE_QUARTER_PROFIT`. This enum will be used by the Pydantic config model in S2.

3. All functions must be pure — no side effects, no I/O, no state, no logging. Same philosophy as `fill_model.py`.

4. Type hints on all functions. Docstrings with parameter descriptions.

5. Import the `TrailingStopConfig` and `ExitEscalationConfig` types — but since these Pydantic models don't exist yet (created in S2), use a lightweight approach: define minimal frozen dataclasses or NamedTuples in exit_math.py for the function signatures. S2 will create the real Pydantic models that are structurally compatible. Alternatively, use duck-typing with Protocol or just pass individual parameters. Choose whichever approach keeps exit_math.py self-contained in S1 without forward dependencies.

   **Recommended approach:** Pass individual parameters to the functions rather than config objects. This keeps exit_math.py zero-dependency and makes it trivially testable. Example:
   ```python
   def compute_trailing_stop(
       high_watermark: float,
       atr_value: float | None,
       trail_type: str,  # "atr" | "percent" | "fixed"
       atr_multiplier: float = 2.5,
       trail_percent: float = 0.02,
       fixed_distance: float = 0.50,
       min_trail_distance: float = 0.05,
       enabled: bool = True,
   ) -> float | None:
   ```
   S2's Pydantic models will call these functions unpacking their fields.

## Constraints
- Do NOT modify any existing files in this session
- Do NOT import from `argus.core.config` (doesn't have the models yet)
- Do NOT add I/O, logging, or state to exit_math.py
- Keep the module self-contained (zero argus imports if possible)

## Test Targets
After implementation:
- Existing tests: all must still pass (no files modified)
- New test file: `tests/unit/core/test_exit_math.py`
- Minimum new test count: 14
- Tests to write:
  1. `compute_trailing_stop` — ATR type with valid ATR value
  2. `compute_trailing_stop` — percent type
  3. `compute_trailing_stop` — fixed type
  4. `compute_trailing_stop` — ATR type with None ATR → returns None
  5. `compute_trailing_stop` — ATR type with negative ATR → returns None (AMD-12)
  6. `compute_trailing_stop` — ATR type with zero ATR → returns None (AMD-12)
  7. `compute_trailing_stop` — min_trail_distance floor enforced
  8. `compute_trailing_stop` — disabled (enabled=False) → returns None
  9. `compute_escalation_stop` — breakeven phase (AMD-5 formula)
  10. `compute_escalation_stop` — quarter_profit phase (AMD-5: entry + 0.25 × (hwm - entry))
  11. `compute_escalation_stop` — half_profit phase (AMD-5 formula)
  12. `compute_escalation_stop` — three_quarter_profit phase (AMD-5 formula)
  13. `compute_escalation_stop` — no time_stop (None) → returns None
  14. `compute_effective_stop` — max of all non-None sources
- Test command: `python -m pytest tests/unit/core/test_exit_math.py -x -q -v`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing files modified | `git diff --name-only` shows only new files |
| exit_math.py is pure (no I/O) | grep for `open(`, `print(`, `logging`, `import os` |
| StopToLevel enum has all 4 AMD-5 values | Inspect enum members |
| All functions return correct types | Type hints + test assertions |

## Definition of Done
- [ ] `argus/core/exit_math.py` created with 3 functions + StopToLevel enum
- [ ] All functions are pure (no side effects)
- [ ] AMD-5 stop_to formulas implemented using high_watermark
- [ ] AMD-12 negative/zero ATR guard implemented
- [ ] 14+ new tests written and passing
- [ ] No existing tests broken
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
`docs/sprints/sprint-28.5/session-S1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-28.5/review-context.md`
2. The close-out report path: `docs/sprints/sprint-28.5/session-S1-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/unit/core/test_exit_math.py -x -q -v`
5. Files that should NOT have been modified: all existing files

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same session, update both the close-out report and review report files per the template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify all 3 functions are pure (no side effects, no I/O, no state)
2. Verify AMD-5 formulas use `high_watermark` not T1/T2 targets
3. Verify AMD-12: negative and zero ATR values handled (return None)
4. Verify `compute_effective_stop` returns max of non-None values (never below original_stop)
5. Verify StopToLevel enum has exactly: breakeven, quarter_profit, half_profit, three_quarter_profit
6. Verify `min_trail_distance` floor is applied after trail distance computation

## Sprint-Level Regression Checklist
- [ ] Non-opt-in strategy behavior unchanged
- [ ] BacktestEngine non-trail regression (bit-identical results)
- [ ] SignalEvent backward compatibility (atr_value=None default)
- [ ] AMD-2: Flatten order is sell-first, cancel-second
- [ ] AMD-3: Escalation failure → flatten recovery
- [ ] AMD-4: shares_remaining > 0 guard
- [ ] AMD-7: Prior-state-first bar processing
- [ ] AMD-8: _flatten_pending check FIRST
- [ ] Risk Manager not touched (DEC-027)
- [ ] Config keys match Pydantic model
- [ ] Full test suite passes (0 failures)

## Sprint-Level Escalation Criteria
**Critical (HALT):** Position leak, silent behavioral change for non-opt-in strategies, trail+broker deadlock, BacktestEngine regression, naked position from escalation failure.
**Significant:** compute_effective_stop priority confusion, IBKR interaction issues, config merge complexity, fill_model.py pressure, AMD-7 bar-loop restructure.
