# Sprint 24.5, Session 3: VWAP + Afternoon Momentum Instrumentation

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/telemetry.py` (S1 — event model and buffer)
   - `argus/strategies/base_strategy.py` (S1 — record_evaluation method)
   - `argus/strategies/vwap_reclaim.py` (main target — 5-state machine)
   - `argus/strategies/afternoon_momentum.py` (main target — 8 entry conditions)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/strategies/ -x -q
   ```
   Expected: all passing
3. Verify branch: `sprint-24.5`

## Objective
Instrument VwapReclaimStrategy and AfternoonMomentumStrategy with evaluation
events at every decision point — state machine transitions, condition checks,
signal generation/rejection.

## Requirements

1. **In `argus/strategies/vwap_reclaim.py`**:

   a. **`on_candle()` — time window check**: If candle is outside strategy's
      operating window, emit:
      - `TIME_WINDOW_CHECK`, `FAIL`, "Outside VWAP Reclaim operating window"

   b. **`on_candle()` — terminal state check**: If symbol is in ENTERED or
      EXHAUSTED state:
      - `STATE_TRANSITION`, `INFO`, "Symbol in terminal state: {state}"

   c. **`_process_state_machine()` — every state transition**: When the state
      changes from one value to another:
      - `STATE_TRANSITION`, `INFO`, "State transition: {from_state} → {to_state}"
      - Metadata: `{"from_state": ..., "to_state": ..., "trigger": ...}` where
        trigger describes what caused the transition (e.g., "price crossed VWAP",
        "volume confirmation", "exhaustion timeout")

   d. **VWAP cross / approach detection**: When price approaches or crosses VWAP:
      - `INDICATOR_STATUS`, `INFO`, "VWAP distance: {distance:.4f} ({pct:.2f}%)"
      - Metadata: `{"vwap": ..., "price": ..., "distance_pct": ...}`

   e. **Entry condition checks** (wherever conditions are evaluated for entry):
      - Each condition: `CONDITION_CHECK`, `PASS` or `FAIL`, specific reason
      - E.g., "Volume confirmation: PASS (rvol={rvol:.1f}x, threshold={thresh}x)"

   f. **Signal generation in CONFIRMED → ENTERED transition**:
      - `SIGNAL_GENERATED`, `PASS`, "VWAP Reclaim signal: {symbol} entry at {price}"
      - Metadata: entry/stop/target details

   g. **`_calculate_pattern_strength()`**:
      - `QUALITY_SCORED`, `INFO`, "VWAP Reclaim pattern strength: {score}"
      - Metadata: component scores

2. **In `argus/strategies/afternoon_momentum.py`**:

   a. **`on_candle()` — time window check**:
      - `TIME_WINDOW_CHECK`, `FAIL`, "Outside Afternoon Momentum operating window"

   b. **Consolidation detection** (when consolidation range is being tracked):
      - `STATE_TRANSITION`, `INFO`, "Consolidation tracking: {n} candles, range={range:.2f}"
      - When consolidation confirmed: `STATE_TRANSITION`, `PASS`, "Consolidation established"

   c. **`_check_breakout_entry()` — each of the 8 entry conditions**:
      Emit a separate `CONDITION_CHECK` event for each condition with `PASS` or `FAIL`:
      1. Price above consolidation high
      2. Volume confirmation (RVOL threshold)
      3. Breakout candle body ratio
      4. Spread/range check
      5. Distance from VWAP
      6. Time remaining check
      7. Trend alignment (prior direction)
      8. Consolidation quality (tightness)

      Format: `CONDITION_CHECK`, `PASS`/`FAIL`, "Condition {n}/8: {name} — {detail}"
      Metadata: `{"condition_name": ..., "value": ..., "threshold": ..., "passed": bool}`

   d. **All conditions pass — signal generation**:
      - `SIGNAL_GENERATED`, `PASS`, "AfMo signal: {symbol} breakout at {price}"
      - Metadata: entry/stop/target details

   e. **Any condition fails — signal rejection**:
      - `SIGNAL_REJECTED`, `FAIL`, "AfMo rejected: failed condition {n} ({name})"
      - Metadata: which conditions passed/failed

   f. **`_calculate_pattern_strength()`**:
      - `QUALITY_SCORED`, `INFO`, "Afternoon Momentum pattern strength: {score}"
      - Metadata: component scores

## Constraints
- Do NOT modify control flow or return values of any method
- Do NOT modify: `argus/core/events.py`, `argus/main.py`, `argus/strategies/telemetry.py`,
  `argus/strategies/orb_base.py` (S2 output)
- Keep instrumentation purely additive — insert calls, don't restructure
- Every record_evaluation() call positioned logically (before return statements, after state changes)

## Test Targets
New tests in `tests/strategies/test_vwap_afmo_telemetry.py`:
1. `test_vwap_state_transition_emits_event` — MONITORING→APPROACHING emits STATE_TRANSITION
2. `test_vwap_exhaustion_emits_event` — transition to EXHAUSTED emits STATE_TRANSITION
3. `test_vwap_entry_conditions_emit_events` — condition checks emit CONDITION_CHECK
4. `test_vwap_pattern_strength_emits_quality_scored`
5. `test_afmo_consolidation_emits_state_transition`
6. `test_afmo_8_conditions_emit_individual_events` — verify 8 separate CONDITION_CHECK events
7. `test_afmo_signal_generated_emits_event` — all conditions pass → SIGNAL_GENERATED
8. `test_afmo_pattern_strength_emits_quality_scored`
- Minimum new test count: 8
- Test command: `python -m pytest tests/strategies/test_vwap_afmo_telemetry.py tests/strategies/ -x -q`

## Definition of Done
- [ ] VwapReclaimStrategy emits events for state transitions, conditions, signals
- [ ] AfternoonMomentumStrategy emits events for all 8 conditions individually
- [ ] All existing VWAP and AfMo tests pass unchanged
- [ ] ≥8 new tests written and passing
- [ ] ruff linting passes
- [ ] Close-out report written to docs/sprints/sprint-24.5/session-3-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| VWAP state machine unchanged | `python -m pytest tests/strategies/ -k "vwap" -x -q` |
| AfMo 8 conditions unchanged | `python -m pytest tests/strategies/ -k "afternoon" -x -q` |
| Pattern strength unchanged | Existing tests pass |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-3-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-24.5/review-context.md`
2. Close-out: `docs/sprints/sprint-24.5/session-3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped, non-final): `python -m pytest tests/strategies/ -x -q`
5. Files NOT to modify: `argus/core/events.py`, `argus/main.py`, `argus/strategies/orb_base.py`

## Session-Specific Review Focus (for @reviewer)
1. Verify NO changes to VWAP state machine logic (only additions)
2. Verify each of 8 AfMo conditions has its own CONDITION_CHECK event (not batched)
3. Verify state transition events include both from_state and to_state in metadata
4. Verify control flow unchanged — existing tests as evidence
5. Verify record_evaluation positioned before return statements, not after

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
