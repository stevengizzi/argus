# Sprint 26, Session 6: FlatTopBreakoutPattern + Config

## Pre-Flight Checks
1. Read: `argus/strategies/patterns/base.py`, `argus/strategies/patterns/bull_flag.py` (S5 reference), `argus/core/config.py`
2. Scoped test: `python -m pytest tests/strategies/patterns/ -x -q`
3. Verify branch

## Objective
Implement FlatTopBreakoutPattern detecting horizontal resistance with multiple touches, consolidation, and volume breakout.

## Requirements

1. **Create `argus/strategies/patterns/flat_top_breakout.py`:**
   - `FlatTopBreakoutPattern(PatternModule)`:
     - `name` → `"Flat-Top Breakout"`
     - `lookback_bars` → `consolidation_min_bars + 10` (buffer)
     - `detect(candles, indicators)`:
       1. **Identify resistance level:** Scan candle highs for clusters within `resistance_tolerance_pct` of each other. Need ≥ `resistance_touches` distinct candles touching resistance.
       2. **Consolidation:** Price stays below resistance for ≥ `consolidation_min_bars`. Range narrows (high-low range of recent bars < range of earlier bars).
       3. **Breakout:** Most recent candle closes above resistance with volume ≥ `breakout_volume_multiplier` × average recent volume.
       - Entry: breakout candle close
       - Stop: lowest low during consolidation
       - Targets: entry + (entry - stop) for T1, entry + 2*(entry - stop) for T2 (R-multiple)
     - `score(detection)`:
       - Resistance touches: more touches = stronger (up to 30 pts)
       - Consolidation quality: tighter range near resistance (up to 30 pts)
       - Volume profile: lower volume during consolidation, spike on breakout (up to 25 pts)
       - Breakout candle quality: close near high, body > wick (up to 15 pts)
     - `get_default_params()` → dict

2. **Create `config/strategies/flat_top_breakout.yaml`:**
   - strategy_id: "strat_flat_top_breakout", name: "Flat-Top Breakout", family: "breakout"
   - operating_window: 10:00–15:00, force_close: 15:50
   - resistance_touches: 3, resistance_tolerance_pct: 0.002, consolidation_min_bars: 10
   - breakout_volume_multiplier: 1.3, target_1_r: 1.0, target_2_r: 2.0, time_stop_minutes: 30
   - Standard risk_limits, benchmarks, universe_filter (min_price: 10, min_avg_volume: 1M)
   - pipeline_stage: "exploration", backtest_summary: status: "not_validated"

3. **Add to `argus/core/config.py`:**
   - `FlatTopBreakoutConfig(StrategyConfig)` with pattern-specific fields
   - `load_flat_top_breakout_config(path)` loader

4. **Update `argus/strategies/patterns/__init__.py`:** Add export

## Constraints
- Do NOT modify base_strategy.py, events.py, pattern_strategy.py, base.py, bull_flag.py, existing strategies
- Pure detection — no execution logic

## Config Validation
Test flat_top_breakout.yaml keys match FlatTopBreakoutConfig model_fields.

## Test Targets
New tests in `tests/strategies/patterns/test_flat_top_breakout.py`:
1. `test_valid_flat_top_detection` — synthetic resistance+consolidation+breakout → PatternDetection
2. `test_insufficient_resistance_touches` — fewer than required → None
3. `test_resistance_tolerance_exceeded` — touches too spread out → None
4. `test_consolidation_too_short` — < min bars → None
5. `test_no_volume_on_breakout` — volume below multiplier → None
6. `test_score_ranges` — components produce 0–100
7. `test_config_yaml_key_validation` — YAML↔Pydantic match
8. `test_get_default_params` — returns dict with expected keys
- Minimum new test count: 8
- Test: `python -m pytest tests/strategies/patterns/test_flat_top_breakout.py -x -v`

## Definition of Done
- [ ] FlatTopBreakoutPattern implements all PatternModule methods
- [ ] Resistance detection with tolerance clustering
- [ ] Score 0–100 with meaningful components
- [ ] Config validates, 8+ new tests passing
- [ ] Close-out: `docs/sprints/sprint-26/session-6-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-6-closeout.md`

## Tier 2 Review
Review context: `docs/sprints/sprint-26/review-context.md`
Close-out: `docs/sprints/sprint-26/session-6-closeout.md`
Test: `python -m pytest tests/strategies/patterns/test_flat_top_breakout.py -x -v`
Do-not-modify: base_strategy.py, events.py, pattern_strategy.py, base.py, bull_flag.py, existing strategies

## Session-Specific Review Focus
1. Resistance level identification: clustering algorithm within tolerance
2. Consolidation validation: bars below resistance, range narrowing
3. Score components meaningful and bounded
4. Config YAML↔Pydantic match

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-26/review-context.md`.
