# Sprint 26, Session 3: R2G Entry/Exit/PatternStrength Completion

## Pre-Flight Checks
1. Read these files:
   - `argus/strategies/red_to_green.py` (S2 output — your primary work target)
   - `argus/strategies/vwap_reclaim.py` (reference for entry logic, exit rules, reconstruct_state)
   - `argus/strategies/afternoon_momentum.py` (reference for _calculate_pattern_strength)
   - `argus/core/events.py` (SignalEvent fields — do NOT modify)
   - `argus/models/strategy.py` (ScannerCriteria, ExitRules, MarketConditionsFilter)
2. Run scoped test baseline:
   ```
   python -m pytest tests/strategies/test_red_to_green.py -x -q
   ```
3. Verify branch

## Objective
Complete the RedToGreenStrategy: implement TESTING_LEVEL→ENTERED transition with full entry criteria, exit rules, `_calculate_pattern_strength()`, scanner criteria, market conditions filter, position sizing, and `reconstruct_state()`. Replace all S2 STUBs.

## Requirements

1. **Complete `_handle_testing_level()` in `argus/strategies/red_to_green.py`:**
   - Check operating window (earliest_entry ≤ now ≤ latest_entry)
   - Count level_test_bars (candles where price is within level_proximity_pct of current_level_price)
   - If level_test_bars ≥ min_level_test_bars AND candle closes above key level:
     - Volume confirmation: candle volume ≥ volume_confirmation_multiplier × avg volume
     - Chase guard: close is not > max_chase_pct above level
     - If all pass → generate SignalEvent, transition to ENTERED
     - If volume or chase fails → stay in TESTING_LEVEL, record evaluation
   - If price drops significantly below level (e.g., > level_proximity_pct × 3 below) → level failed:
     - Increment level_attempts
     - If level_attempts < max_level_attempts → back to GAP_DOWN_CONFIRMED (try next level)
     - If level_attempts >= max_level_attempts → EXHAUSTED

2. **Implement `_identify_key_levels(symbol, candle, state) -> list[tuple[KeyLevelType, float]]`:**
   - Returns list of (level_type, level_price) sorted by proximity to current price
   - VWAP: from indicators (via data_service or event metadata)
   - PREMARKET_LOW: stored in state (set during GAP_DOWN_CONFIRMED phase from first candle)
   - PRIOR_CLOSE: from gap calculation or reference data

3. **Implement `_calculate_pattern_strength(candle, state, level_type, volume_ratio)`:**
   - Returns tuple of (float 0–100, dict signal_context)
   - Scoring components (weighted):
     - Level type quality: VWAP=35, PRIOR_CLOSE=30, PREMARKET_LOW=25 (base points)
     - Volume ratio: (volume_ratio / volume_confirmation_multiplier) × 25, capped at 25
     - Gap magnitude: smaller gaps (2–4%) score higher than large gaps (8–10%), up to 20 points
     - Level test quality: more test bars = stronger confirmation, up to 20 points
   - Clamp to 0–100

4. **Complete remaining abstract methods:**
   - `get_scanner_criteria()` → ScannerCriteria with min_gap_pct=-0.02 (negative for gap down), price range, volume
   - `get_exit_rules()` → ExitRules with stop below key level (level_price - buffer), T1/T2 at config R-multiples, time stop
   - `get_market_conditions_filter()` → allowed_regimes: ["bullish_trending", "range_bound"], max_vix: 35
   - `calculate_position_size()` → return 0 (Quality Engine pipeline handles sizing per DEC-330)

5. **Complete `reconstruct_state(trade_logger)`:**
   - Query today's trades for this strategy from trade_logger
   - For each open position: set symbol state to ENTERED
   - For each closed position today: set symbol state to EXHAUSTED (already traded)

6. **Add evaluation telemetry throughout:**
   - `ENTRY_EVALUATION` with conditions_passed/conditions_total for TESTING_LEVEL checks
   - `SIGNAL_GENERATED` when signal emitted
   - `STATE_TRANSITION` on each transition
   - `CONDITION_CHECK` for individual entry conditions (volume, chase, window)

7. **Generate SignalEvent correctly:**
   ```python
   SignalEvent(
       strategy_id=self.strategy_id,
       symbol=symbol,
       side=Side.LONG,
       entry_price=candle.close,
       stop_price=state.current_level_price - (state.current_level_price * self._config.stop_buffer_pct),
       target_prices=(
           candle.close + 1.0 * (candle.close - stop_price),
           candle.close + 2.0 * (candle.close - stop_price),
       ),
       share_count=0,  # Quality Engine handles
       pattern_strength=pattern_strength,
       signal_context=signal_context,
       time_stop_seconds=self._config.time_stop_minutes * 60,
       rationale=f"R2G: {level_type.value} reclaim on {symbol}",
   )
   ```

## Constraints
- Do NOT modify `base_strategy.py`, `events.py`, any existing strategy files
- Do NOT modify `config.py` or `red_to_green.yaml` (config is set from S2)
- VWAP indicator data: access via data_service if available, gracefully handle None (skip VWAP level, use prior_close and premarket_low)

## Test Targets
New tests in `tests/strategies/test_red_to_green.py` (extending S2's file):
1. `test_entry_at_vwap_level` — candle near VWAP, volume confirmed → SignalEvent
2. `test_entry_at_prior_close` — candle near prior close → SignalEvent
3. `test_entry_rejected_no_volume` — volume below multiplier → None
4. `test_entry_rejected_chase` — close too far above level → None
5. `test_entry_rejected_outside_window` — before earliest_entry → None
6. `test_level_failure_to_gap_confirmed` — level break → back to GAP_DOWN_CONFIRMED
7. `test_pattern_strength_scoring` — verify score components and bounds
8. `test_scanner_criteria_negative_gap` — min_gap_pct is negative
9. `test_market_conditions_filter` — allowed_regimes contains expected values
10. `test_exit_rules_stop_below_level` — stop price below key level
11. `test_reconstruct_state_open_position` — sets ENTERED state
12. `test_signal_event_share_count_zero` — share_count=0 in generated signal
- Minimum new test count: 12
- Test command: `python -m pytest tests/strategies/test_red_to_green.py -x -v`

## Definition of Done
- [ ] All STUBs from S2 replaced with implementations
- [ ] TESTING_LEVEL→ENTERED transition with full entry criteria
- [ ] _calculate_pattern_strength returns 0–100
- [ ] All BaseStrategy abstract methods implemented (no more abstractmethod violations)
- [ ] Evaluation telemetry at every decision point
- [ ] SignalEvent has share_count=0 and pattern_strength set
- [ ] All existing tests pass
- [ ] 12 new tests passing
- [ ] Close-out: `docs/sprints/sprint-26/session-3-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-3-closeout.md`

## Tier 2 Review
1. Review context: `docs/sprints/sprint-26/review-context.md`
2. Close-out: `docs/sprints/sprint-26/session-3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/test_red_to_green.py -x -v`
5. Do-not-modify: base_strategy.py, events.py, existing strategies, config.py, red_to_green.yaml

## Session-Specific Review Focus (for @reviewer)
1. Verify all S2 STUBs are resolved (grep for `# TODO: Sprint 26 S3`)
2. Verify pattern_strength is clamped 0–100
3. Verify share_count=0 in SignalEvent
4. Verify entry conditions include: operating window, level proximity, volume, chase guard
5. Verify level failure increments level_attempts and respects max_level_attempts
6. Verify reconstruct_state queries trade_logger correctly
7. Verify VWAP absence is handled gracefully (other levels still checked)

## Sprint-Level Regression Checklist
See `docs/sprints/sprint-26/review-context.md`.

## Sprint-Level Escalation Criteria
See `docs/sprints/sprint-26/review-context.md`.
