# Sprint 24.5, Session 2: ORB Family Instrumentation

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/telemetry.py` (Session 1 output — event model and buffer)
   - `argus/strategies/base_strategy.py` (Session 1 output — record_evaluation method)
   - `argus/strategies/orb_base.py` (main instrumentation target)
   - `argus/strategies/orb_breakout.py`
   - `argus/strategies/orb_scalp.py`
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/strategies/ tests/test_telemetry.py -x -q
   ```
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify branch: `sprint-24.5`

## Objective
Instrument `OrbBaseStrategy.on_candle()` and both ORB subclass strategies with
evaluation events at every decision point, making the ORB strategies' reasoning
visible in the Decision Stream.

## Requirements

1. **In `argus/strategies/orb_base.py` — `on_candle()` method**, add
   `self.record_evaluation()` calls at each decision point:

   a. **Watchlist check** (early return for symbol not in watchlist):
      - No event needed here (too noisy — thousands of non-watchlist symbols)

   b. **OR window accumulation** (symbol is in OR window, candle accumulated):
      - Event type: `OPENING_RANGE_UPDATE`, result: `INFO`
      - Reason: "OR candle accumulated ({n} candles)"
      - Metadata: `{"candle_count": len(state.or_candles)}`

   c. **OR finalization** (first candle after OR window):
      - Event type: `OPENING_RANGE_UPDATE`, result: `PASS` if valid, `FAIL` if invalid
      - Reason: "Opening range established: high={h:.2f} low={l:.2f}" or
        "Opening range invalid: {reason}"
      - Metadata: `{"or_high": ..., "or_low": ..., "or_range_pct": ..., "or_valid": ...}`

   d. **DEC-261 same-symbol exclusion check**:
      - Event type: `CONDITION_CHECK`, result: `FAIL`
      - Reason: "DEC-261: Symbol already triggered by another ORB strategy"

   e. **Entry window check** (before earliest / after latest):
      - Event type: `TIME_WINDOW_CHECK`, result: `FAIL`
      - Reason: "Before earliest entry time" or "After latest entry time"

   f. **Internal risk limits check**:
      - Event type: `CONDITION_CHECK`, result: `FAIL` if blocked
      - Reason: "Internal risk limits exceeded"

   g. **Concurrent positions check**:
      - Event type: `CONDITION_CHECK`, result: `FAIL` if blocked
      - Reason: "Max concurrent positions reached ({active}/{max})"

   h. **Breakout conditions check** (in `_check_breakout_conditions`):
      - Event type: `ENTRY_EVALUATION`, result: `PASS` or `FAIL`
      - On breakout detected: reason with direction, metadata with price levels
      - On no breakout: reason explaining what didn't trigger

   i. **Signal generation** (in `_build_breakout_signal`):
      - Event type: `SIGNAL_GENERATED`, result: `PASS`
      - Metadata: `{"direction": ..., "entry": ..., "stop": ..., "target1": ...}`

   **Important:** Every `record_evaluation()` call must be an addition — do NOT
   restructure the control flow of `on_candle()`. Insert calls at the natural
   logging points before existing `return None` statements or after state changes.

2. **In `argus/strategies/orb_breakout.py` — `_calculate_pattern_strength()`**:
   - After computing the score, add:
     Event type: `QUALITY_SCORED`, result: `INFO`
     Reason: "ORB Breakout pattern strength: {score}"
     Metadata: component scores dict

3. **In `argus/strategies/orb_scalp.py` — `_calculate_pattern_strength()`**:
   - Same as above but with "ORB Scalp" prefix

## Constraints
- Do NOT modify the control flow or return values of any method
- Do NOT modify: `argus/core/events.py`, `argus/main.py`, `argus/strategies/telemetry.py`
- Do NOT add any new imports beyond what's needed for telemetry enums
- Every `record_evaluation()` call must be try/except guarded (the base method does this, but verify)
- Keep instrumentation lightweight — no string formatting unless the event will actually be recorded

## Test Targets
After implementation:
- Existing tests: all must still pass (especially all ORB strategy tests)
- New tests in `tests/strategies/test_orb_telemetry.py`:
  1. `test_orb_on_candle_or_accumulation_emits_event` — candle in OR window → OPENING_RANGE_UPDATE
  2. `test_orb_on_candle_or_finalization_emits_event` — first post-OR candle → OPENING_RANGE_UPDATE with PASS/FAIL
  3. `test_orb_on_candle_exclusion_emits_event` — DEC-261 triggered → CONDITION_CHECK FAIL
  4. `test_orb_on_candle_time_window_fail_emits_event` — before/after entry window → TIME_WINDOW_CHECK FAIL
  5. `test_orb_on_candle_breakout_emits_entry_evaluation` — breakout conditions → ENTRY_EVALUATION
  6. `test_orb_on_candle_signal_generated_emits_event` — full signal → SIGNAL_GENERATED
  7. `test_orb_breakout_pattern_strength_emits_quality_scored` — score computed → QUALITY_SCORED
  8. `test_orb_scalp_pattern_strength_emits_quality_scored` — same for scalp
- Minimum new test count: 8
- Test command (scoped): `python -m pytest tests/strategies/test_orb_telemetry.py tests/strategies/ -x -q`

## Definition of Done
- [ ] OrbBaseStrategy.on_candle() emits evaluation events at all decision points
- [ ] ORB Breakout and ORB Scalp _calculate_pattern_strength() emit QUALITY_SCORED
- [ ] All existing ORB strategy tests pass unchanged
- [ ] ≥8 new tests written and passing
- [ ] No control flow changes to on_candle() or any strategy method
- [ ] ruff linting passes
- [ ] Close-out report written to docs/sprints/sprint-24.5/session-2-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| on_candle() returns same signals | Existing ORB tests pass: `python -m pytest tests/strategies/ -k "orb" -x -q` |
| DEC-261 exclusion still works | Existing exclusion test passes |
| Pattern strength unchanged | Existing pattern strength tests pass |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-24.5/review-context.md`
2. Close-out: `docs/sprints/sprint-24.5/session-2-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped, non-final): `python -m pytest tests/strategies/ -x -q`
5. Files NOT to modify: `argus/core/events.py`, `argus/main.py`, `argus/strategies/telemetry.py`

## Session-Specific Review Focus (for @reviewer)
1. Verify NO changes to on_candle() control flow (only additions of record_evaluation calls)
2. Verify every record_evaluation call is positioned BEFORE the associated return statement (not after — would be dead code)
3. Verify DEC-261 exclusion path still returns None correctly
4. Verify metadata dicts contain useful diagnostic values (not empty)
5. Verify no expensive string formatting happens unconditionally (lazy evaluation)

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
