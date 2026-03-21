# Sprint 26, Session 5: BullFlagPattern + Config

## Pre-Flight Checks
1. Read: `argus/strategies/patterns/base.py`, `argus/strategies/pattern_strategy.py` (S4), `argus/core/config.py`
2. Scoped test: `python -m pytest tests/strategies/patterns/ -x -q`
3. Verify branch

## Objective
Implement BullFlagPattern (PatternModule subclass) detecting bull flag continuation patterns, plus BullFlagConfig and YAML config. Also add 3 PatternBasedStrategy edge-case tests absorbed from S4 revision (scanner criteria passthrough, market conditions filter passthrough, reconstruct_state delegation).

## Requirements

1. **Create `argus/strategies/patterns/bull_flag.py`:**
   - `BullFlagPattern(PatternModule)` implementing:
     - `name` → `"Bull Flag"`
     - `lookback_bars` → `pole_min_bars + flag_max_bars + 5` (buffer)
     - `detect(candles, indicators)`:
       - Scan backwards from most recent candle to identify:
         1. **Pole:** Sequence of `pole_min_bars`+ candles with net upward move ≥ `pole_min_move_pct`
         2. **Flag:** After pole, consolidation of ≤ `flag_max_bars` candles where retracement from pole high ≤ `flag_max_retrace_pct` (typically 38–62% of pole)
         3. **Breakout:** Most recent candle closes above flag high with volume ≥ `breakout_volume_multiplier` × average flag volume
       - Entry price: breakout candle close
       - Stop price: flag low (lowest low during flag period)
       - Target prices: measured move = pole height projected above breakout (entry + pole_height)
       - Return PatternDetection with confidence based on pattern quality
     - `score(detection)`:
       - Pole strength: larger moves score higher (up to 30 pts)
       - Flag tightness: tighter retrace scores higher (up to 30 pts)
       - Volume profile: declining volume in flag + spike on breakout (up to 25 pts)
       - Breakout quality: close near high of candle (up to 15 pts)
       - Clamp 0–100
     - `get_default_params()` → dict of default parameter values

2. **Create `config/strategies/bull_flag.yaml`:**
   ```yaml
   strategy_id: "strat_bull_flag"
   name: "Bull Flag"
   version: "1.0.0"
   enabled: true
   asset_class: "us_stocks"
   pipeline_stage: "exploration"
   family: "continuation"
   description_short: "Bull flag continuation: strong pole, tight flag consolidation, breakout on volume."
   time_window_display: "10:00 AM–3:00 PM"
   operating_window:
     earliest_entry: "10:00"
     latest_entry: "15:00"
     force_close: "15:50"
   pole_min_bars: 5
   pole_min_move_pct: 0.03
   flag_max_bars: 20
   flag_max_retrace_pct: 0.50
   breakout_volume_multiplier: 1.3
   target_1_r: 1.0
   target_2_r: 2.0
   time_stop_minutes: 30
   risk_limits:
     max_loss_per_trade_pct: 0.01
     max_daily_loss_pct: 0.03
     max_trades_per_day: 6
     max_concurrent_positions: 3
   benchmarks:
     min_win_rate: 0.45
     min_profit_factor: 1.1
     min_sharpe: 0.3
     max_drawdown_pct: 0.12
   backtest_summary:
     status: "not_validated"
   universe_filter:
     min_price: 10.0
     max_price: 200.0
     min_avg_volume: 1000000
   ```

3. **Add to `argus/core/config.py`:**
   - `BullFlagConfig(StrategyConfig)` with all pattern-specific fields
   - `load_bull_flag_config(path) -> BullFlagConfig` loader

4. **Update `argus/strategies/patterns/__init__.py`:** Add BullFlagPattern export

## Constraints
- Do NOT modify base_strategy.py, events.py, existing strategies, pattern_strategy.py, base.py
- Bull Flag is a pure detection module — NO operating window logic (PatternBasedStrategy handles that)

## Config Validation
Test that bull_flag.yaml keys match BullFlagConfig model_fields.

## Test Targets
New tests in `tests/strategies/patterns/test_bull_flag.py`:
1. `test_valid_bull_flag_detection` — synthetic pole+flag+breakout candles → PatternDetection
2. `test_pole_too_short` — fewer than pole_min_bars → None
3. `test_pole_move_too_small` — move < pole_min_move_pct → None
4. `test_flag_retrace_too_deep` — retrace > flag_max_retrace_pct → None
5. `test_flag_too_long` — flag > flag_max_bars → None
6. `test_no_volume_on_breakout` — volume below multiplier → None
7. `test_score_ranges` — verify score components produce 0–100
8. `test_config_yaml_key_validation` — no silently ignored keys

Additional PatternBasedStrategy edge-case tests in `tests/strategies/patterns/test_pattern_strategy.py`:
9. `test_scanner_criteria_passthrough` — wrapper returns ScannerCriteria from config
10. `test_market_conditions_filter_passthrough` — wrapper returns filter from config/defaults
11. `test_reconstruct_state_delegation` — wrapper queries trade_logger
- Minimum new test count: 11
- Test: `python -m pytest tests/strategies/patterns/ -x -v`

## Definition of Done
- [ ] BullFlagPattern implements all PatternModule abstract methods
- [ ] detect() identifies pole, flag, breakout correctly
- [ ] score() returns 0–100 with meaningful component scoring
- [ ] Config loads and validates
- [ ] PatternBasedStrategy edge case tests from S4 revision added
- [ ] All existing tests pass, 11 new tests passing
- [ ] Close-out: `docs/sprints/sprint-26/session-5-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-5-closeout.md`

## Tier 2 Review
1. Review context: `docs/sprints/sprint-26/review-context.md`
2. Close-out: `docs/sprints/sprint-26/session-5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/strategies/patterns/ -x -v`
5. Do-not-modify: base_strategy.py, events.py, pattern_strategy.py, base.py, existing strategies

## Session-Specific Review Focus (for @reviewer)
1. BullFlagPattern detect logic: pole→flag→breakout sequence correct
2. Measured move target calculation: entry + pole_height
3. Score components add up sensibly (no >100 without clamp)
4. Config YAML keys match Pydantic model
5. No operating window logic in pattern module itself

## Sprint-Level Regression Checklist
See `docs/sprints/sprint-26/review-context.md`.

## Sprint-Level Escalation Criteria
See `docs/sprints/sprint-26/review-context.md`.
