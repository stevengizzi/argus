# Sprint 28.5, Session S5: BacktestEngine + CounterfactualTracker Alignment

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/engine.py` (BacktestPosition, per-bar processing loop, _check_exits)
   - `argus/intelligence/counterfactual.py` (ShadowPosition, on_candle per-bar processing, backfill)
   - `argus/core/exit_math.py` (all 3 functions)
   - `argus/core/fill_model.py` (evaluate_bar_exit — DO NOT MODIFY)
   - `argus/core/config.py` (ExitManagementConfig)
2. Run scoped test baseline:
   ```
   python -m pytest tests/unit/backtest/ tests/unit/intelligence/test_counterfactual*.py tests/unit/execution/test_order_manager*.py -x -q
   ```
3. Verify branch: `sprint-28.5`

## Objective
Add trail/escalation state to BacktestPosition and ShadowPosition. Implement AMD-7 bar-processing order (prior state → evaluate → update). Verify non-trail strategies produce identical results.

## Requirements

### 1. BacktestEngine Trail/Escalation State
Add to BacktestPosition (or equivalent position tracking object in engine.py):
- `trail_active: bool = False`
- `trail_stop_price: float = 0.0`
- `escalation_phase_index: int = -1`
- `exit_config: ExitManagementConfig | None = None`
- `atr_value: float | None = None`

When BacktestEngine creates a position from a signal:
- Set `exit_config` from strategy config (use the same lookup pattern as Order Manager)
- Set `atr_value` from signal's atr_value
- Set `trail_active` based on activation mode:
  - `"immediate"`: True at entry
  - `"after_t1"`: True after T1 target hit (BacktestEngine tracks T1 fills)
  - `"after_profit_pct"`: check per bar

### 2. BacktestEngine Per-Bar Processing — AMD-7 Bar Order
**CRITICAL: The bar-processing order must be:**
1. Compute effective stop from **PRIOR bar's** trail/escalation state
2. Pass effective stop to `evaluate_bar_exit()` against **current bar's** high/low/close
3. If not exited: update high_watermark from current bar's high, recompute trail stop for next bar, advance escalation phase if applicable

This preserves worst-case-for-longs semantics. The stop used for exit evaluation never incorporates the current bar's high watermark.

Implementation approach:
```python
# In the per-bar loop:
for position in open_positions:
    # Step 1: Effective stop from PRIOR state
    effective_stop = compute_effective_stop(
        position.stop_price,
        position.trail_stop_price if position.trail_active else None,
        self._compute_escalation_for_position(position, current_bar_time),
    )
    
    # Step 2: Evaluate exit with current bar
    exit_result = evaluate_bar_exit(
        bar.high, bar.low, bar.close,
        stop_price=effective_stop,
        target_price=...,  # existing target logic
        time_stop_expired=...,
    )
    
    if exit_result:
        # Position exits — record exit
        ...
        continue
    
    # Step 3: Update state for NEXT bar
    position.high_watermark = max(position.high_watermark, bar.high)
    if position.trail_active:
        new_trail = compute_trailing_stop(position.high_watermark, position.atr_value, ...)
        if new_trail is not None:
            position.trail_stop_price = max(position.trail_stop_price, new_trail)
    # Advance escalation phase index if needed
```

### 3. CounterfactualTracker Trail/Escalation State
Add same fields to ShadowPosition. Same per-bar processing logic in `on_candle()`:
- Step 1: effective stop from prior state
- Step 2: evaluate via evaluate_bar_exit
- Step 3: update state for next bar
- Same AMD-7 ordering

Also applies to backfill processing: when processing backfill bars from IntradayCandleStore, trail state updates through each bar. If trail triggers during backfill, position closes immediately (correct behavior).

### 4. ExitManagementConfig Loading
Both BacktestEngine and CounterfactualTracker need access to ExitManagementConfig:
- BacktestEngine: pass via constructor or config (it already has access to strategy configs)
- CounterfactualTracker: receives signals via SignalRejectedEvent which carries strategy_id — can look up exit config same way as Order Manager

### 5. Non-Trail Behavior Preservation
When `exit_config` is None or trail/escalation disabled:
- effective_stop = original stop (compute_effective_stop with all None optionals)
- No high watermark updates for trail (existing high_watermark updates for other purposes are fine)
- Bit-identical results to pre-sprint for existing strategies

## Constraints
- Do NOT modify `argus/core/fill_model.py` — exit_math supplements, doesn't replace
- Do NOT modify Order Manager (that's S4a/S4b)
- Do NOT change the existing stop/target/time_stop priority in evaluate_bar_exit
- Preserve exact behavior for non-trail strategies (regression critical)

## Test Targets
- New test files: `tests/unit/backtest/test_engine_exit_management.py`, `tests/unit/intelligence/test_counterfactual_exit_management.py`
- Minimum new test count: 13
- Tests:
  1. BacktestEngine: trail state updates per bar (high watermark from bar.high)
  2. BacktestEngine: trail-triggered exit at correct price
  3. BacktestEngine: escalation phase triggers at correct bar
  4. BacktestEngine: effective stop = max(original, trail, escalation)
  5. BacktestEngine: non-trail strategy produces identical results (REGRESSION)
  6. BacktestEngine: trail + time_stop interaction
  7. **AMD-7:** Bar high=$52, low=$49, prior trail=$49.50, updated trail from $52 would be $50.50 → exit at $49.50 (prior state), NOT $50.50
  8. CounterfactualTracker: trail state updates per bar
  9. CounterfactualTracker: trail-triggered exit at correct price
  10. CounterfactualTracker: escalation phase triggers
  11. CounterfactualTracker: non-trail shadow position identical to pre-sprint (REGRESSION)
  12. CounterfactualTracker: backfill bars update trail state correctly
  13. CounterfactualTracker: trail triggers during backfill → position closes
- Test command (FINAL SESSION — full suite): `python -m pytest -x -q -n auto`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| BacktestEngine non-trail identical | Test #5 — run existing config, compare results |
| CounterfactualTracker non-trail identical | Test #11 |
| fill_model.py not modified | `git diff argus/core/fill_model.py` shows nothing |
| AMD-7 ordering correct | Test #7 — specific bar scenario |
| All existing backtest tests pass | Full backtest test suite |
| All existing counterfactual tests pass | Full counterfactual test suite |

## Definition of Done
- [ ] BacktestPosition extended with trail/escalation state
- [ ] ShadowPosition extended with trail/escalation state
- [ ] AMD-7 bar-processing order implemented in both engines
- [ ] Non-trail behavior bit-identical (regression tests pass)
- [ ] 13+ new tests passing
- [ ] **Full test suite passes (final session): `python -m pytest -x -q -n auto`**
- [ ] Close-out written to `docs/sprints/sprint-28.5/session-S5-closeout.md`
- [ ] Tier 2 review via @reviewer (FINAL REVIEW — full suite)

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.
The close-out report MUST include a structured JSON appendix fenced with ```json:structured-closeout.
**Write to:** `docs/sprints/sprint-28.5/session-S5-closeout.md`

## Tier 2 Review (FINAL SESSION — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-28.5/review-context.md`
2. Close-out: `docs/sprints/sprint-28.5/session-S5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (FINAL — full suite): `python -m pytest -x -q -n auto && cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20`
5. Files NOT to modify: fill_model.py, risk_manager.py, order_manager.py, any UI files

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL: AMD-7 bar-processing order.** Verify effective stop computed from PRIOR bar's state, not current bar's. Check the exact position of high_watermark update relative to evaluate_bar_exit call.
2. Verify fill_model.py is NOT modified.
3. Verify non-trail BacktestEngine results are bit-identical to pre-sprint.
4. Verify CounterfactualTracker backfill bars update trail state correctly (not skipped).
5. Verify ExitManagementConfig loaded correctly in both engines.
6. Verify all new test assertions use specific numeric values (not approximate).

## Sprint-Level Regression Checklist
[See review-context.md — full checklist]

## Sprint-Level Escalation Criteria
[See review-context.md — full criteria]
