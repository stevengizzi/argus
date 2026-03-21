# Sprint 26, Session 4: PatternBasedStrategy Generic Wrapper

## Pre-Flight Checks
1. Read these files:
   - `argus/strategies/patterns/base.py` (PatternModule ABC from S1)
   - `argus/strategies/base_strategy.py` (BaseStrategy — do NOT modify)
   - `argus/strategies/vwap_reclaim.py` (reference for BaseStrategy implementation pattern)
   - `argus/core/config.py` (StrategyConfig)
   - `argus/core/events.py` (SignalEvent, CandleEvent — do NOT modify)
2. Scoped test baseline:
   ```
   python -m pytest tests/strategies/patterns/ tests/strategies/test_red_to_green.py -x -q
   ```
3. Verify branch

## Objective
Create PatternBasedStrategy — a generic BaseStrategy subclass that wraps any PatternModule, handling all execution boilerplate (operating window, state management, signal generation, telemetry) while delegating pattern detection to the wrapped module.

## Requirements

1. **Create `argus/strategies/pattern_strategy.py`:**

   ```python
   class PatternBasedStrategy(BaseStrategy):
       """Generic strategy wrapper for PatternModule implementations.

       Handles all BaseStrategy contract requirements:
       - Operating window enforcement
       - Per-symbol candle window management
       - Signal generation from PatternDetection
       - Evaluation telemetry
       - Daily state management

       Pattern detection is delegated to the wrapped PatternModule.
       """
   ```

   a. **`__init__(self, pattern: PatternModule, config: StrategyConfig, data_service=None, clock=None)`:**
      - Store pattern module reference
      - Init `_candle_windows: dict[str, deque]` — per-symbol rolling window
      - Each deque has `maxlen=pattern.lookback_bars`

   b. **`async def on_candle(self, event: CandleEvent) -> SignalEvent | None`:**
      - Check symbol in watchlist (return None if not)
      - Check operating window (earliest_entry ≤ now ≤ latest_entry from config)
      - Convert CandleEvent → CandleBar and append to per-symbol deque
      - If deque length < pattern.lookback_bars → return None (insufficient history)
      - Call `pattern.detect(list(deque), indicators)` where indicators extracted from event/data_service
      - If detect returns None → record_evaluation(ENTRY_EVALUATION, FAIL) → return None
      - If detect returns PatternDetection:
        - score = pattern.score(detection)
        - Clamp score to 0–100
        - Build target_prices: use detection.target_prices if non-empty, else compute from config R-multiples
        - Generate SignalEvent with share_count=0, pattern_strength=score
        - record_evaluation(SIGNAL_GENERATED, PASS)
        - Return SignalEvent

   c. **`async def on_tick(self, event: TickEvent) -> None`:**
      - Pass (no tick management for pattern strategies V1)

   d. **`def _calculate_pattern_strength(...)`:**
      - Not used directly — score comes from pattern.score() in on_candle
      - Implement as: `return self._last_score, self._last_context` (cached from on_candle)

   e. **`def get_scanner_criteria(self) -> ScannerCriteria`:**
      - Return basic ScannerCriteria from config (price range, volume)

   f. **`def calculate_position_size(self, entry, stop) -> int`:**
      - Return 0 (Quality Engine handles per DEC-330)

   g. **`def get_exit_rules(self) -> ExitRules`:**
      - Build from config: stop_type="fixed", targets from config target_1_r/target_2_r, time_stop from config

   h. **`def get_market_conditions_filter(self) -> MarketConditionsFilter`:**
      - Return from config or sensible defaults: allowed_regimes=["bullish_trending", "range_bound"], max_vix=35

   i. **`def reset_daily_state(self)`:**
      - Clear `_candle_windows`
      - Call super().reset_daily_state()

   j. **`async def reconstruct_state(self, trade_logger)`:**
      - Basic implementation: query today's trades, note symbols already traded

2. **Update `argus/strategies/patterns/__init__.py`:**
   - Add: `from argus.strategies.pattern_strategy import PatternBasedStrategy`

## Constraints
- Do NOT modify `base_strategy.py`, `events.py`, `quality_engine.py`
- Do NOT import from any concrete pattern (bull_flag, flat_top) — wrapper is generic
- CandleEvent → CandleBar conversion should be a simple helper function, not a method on CandleBar

## Test Targets
New tests in `tests/strategies/patterns/test_pattern_strategy.py`:
1. `test_wrapper_with_mock_pattern_signal_generation` — mock pattern detect()→PatternDetection, verify SignalEvent produced
2. `test_wrapper_no_detection_returns_none` — detect()→None, verify no signal
3. `test_operating_window_enforcement` — before earliest_entry → None even if pattern detects
4. `test_candle_window_accumulation` — deque grows, detect called only when full
5. `test_pattern_strength_from_score` — verify SignalEvent.pattern_strength = pattern.score()
6. `test_share_count_zero` — verify share_count=0 in all signals
7. `test_daily_state_reset_clears_windows` — reset_daily_state clears _candle_windows
- Minimum new test count: 7
- Test command: `python -m pytest tests/strategies/patterns/test_pattern_strategy.py -x -v`

## Definition of Done
- [ ] PatternBasedStrategy wraps any PatternModule
- [ ] Operating window enforced from config
- [ ] Per-symbol candle window with correct maxlen
- [ ] SignalEvent has share_count=0, pattern_strength from score()
- [ ] Evaluation telemetry recorded
- [ ] All existing tests pass, 7 new tests passing
- [ ] Close-out: `docs/sprints/sprint-26/session-4-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-4-closeout.md`

## Tier 2 Review
1. Review context: `docs/sprints/sprint-26/review-context.md`
2. Close-out: `docs/sprints/sprint-26/session-4-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/test_pattern_strategy.py -x -v`
5. Do-not-modify: base_strategy.py, events.py, existing strategies

## Session-Specific Review Focus (for @reviewer)
1. Verify wrapper is generic — no imports from concrete patterns
2. Verify CandleEvent→CandleBar conversion exists and is correct
3. Verify operating window check uses config.operating_window fields
4. Verify deque maxlen = pattern.lookback_bars
5. Verify detect() only called when deque is full
6. Verify pattern-derived target_prices used if present, R-multiple fallback if empty

## Sprint-Level Regression Checklist
See `docs/sprints/sprint-26/review-context.md`.

## Sprint-Level Escalation Criteria
See `docs/sprints/sprint-26/review-context.md`.
