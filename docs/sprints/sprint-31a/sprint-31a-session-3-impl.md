# Sprint 31A, Session 3: Micro Pullback Pattern (Complete)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam, CandleBar)
   - `argus/strategies/patterns/dip_and_rip.py` (reference implementation — follow this structure)
   - `argus/strategies/patterns/factory.py` (`_PATTERN_REGISTRY`, `_SNAKE_CASE_ALIASES`)
   - `argus/core/config.py` (find `DipAndRipConfig` — follow this structure for new config)
   - `argus/main.py` (find the Dip-and-Rip strategy creation block — follow this wiring pattern)
   - `argus/backtest/config.py` (StrategyType enum — add new entry)
   - `argus/backtest/engine.py` (find `_create_dip_and_rip_strategy` — follow this pattern, using `build_pattern_from_config()` per S1 fix)
   - `argus/intelligence/experiments/runner.py` (`_PATTERN_TO_STRATEGY_TYPE` dict)
   - `config/strategies/dip_and_rip.yaml` (reference YAML structure)
   - `config/universe_filters/dip_and_rip.yaml` (reference filter structure)
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/strategies/patterns/ -x -q -n auto`
   Expected: all passing
3. Verify you are on the correct branch: `main` (with S1 + S2 changes committed)

## Objective
Implement the Micro Pullback pattern as a complete PatternModule with Pydantic config, config YAML, universe filter YAML, and full wiring into BacktestEngine, factory, experiment pipeline, and main.py startup.

## Pattern Design: Micro Pullback

**Mechanic:** After a strong impulsive move (≥ min_impulse_percent over min_impulse_bars), the first shallow pullback that enters the short-term EMA zone (within pullback_tolerance_atr × ATR of the EMA) is a continuation entry. The bounce candle must close above the EMA with volume confirmation.

**Operating window:** 10:00 AM – 14:00 ET. Covers the midday gap.

**Distinct from Dip-and-Rip:** D&R requires a ≥2% deep dip and VWAP/level interaction. Micro Pullback targets shallow (<1%) retracements to a moving average after a proven impulse.

## Requirements

### 1. Create `argus/strategies/patterns/micro_pullback.py`

Implement `MicroPullbackPattern(PatternModule)` with:

**Constructor params (all with defaults):**
- `ema_period: int = 9` — EMA lookback period
- `min_impulse_percent: float = 0.02` — Minimum impulse move as fraction (2%)
- `min_impulse_bars: int = 3` — Minimum bars for the impulse
- `max_impulse_bars: int = 15` — Maximum bars to look back for impulse
- `max_pullback_bars: int = 5` — Maximum bars for pullback to complete
- `pullback_tolerance_atr: float = 0.3` — How close to EMA (in ATR multiples) counts as a "touch"
- `min_bounce_volume_ratio: float = 1.2` — Bounce bar volume / avg recent volume
- `stop_buffer_atr_mult: float = 0.5` — ATR multiplier for stop below pullback low
- `target_ratio: float = 2.0` — Target distance as ratio of risk
- `target_1_r: float = 1.0` — First target R-multiple
- `target_2_r: float = 2.0` — Second target R-multiple
- `min_score_threshold: float = 0.0` — Minimum confidence to emit detection

**Properties:**
- `name` → `"Micro Pullback"`
- `lookback_bars` → `30` (needs impulse history + pullback + EMA)

**`detect(candles, indicators)` logic:**
1. Compute EMA from candle closes using exponential smoothing (self-contained — do not rely on external indicator)
2. Scan backward from recent bars to find an impulse: a sequence of `min_impulse_bars` to `max_impulse_bars` bars where the move from low to high ≥ `min_impulse_percent` × price
3. After the impulse peak, look for pullback: within `max_pullback_bars`, price drops into EMA zone (candle low within `pullback_tolerance_atr` × ATR of the EMA value at that bar)
4. Bounce confirmation: a candle that closes above EMA with volume ≥ `min_bounce_volume_ratio` × average volume of recent N bars
5. Compute entry (bounce close), stop (pullback low - ATR buffer), targets (R-multiples)
6. Return `PatternDetection` with metadata including impulse_percent, pullback_depth, ema_value, bounce_volume_ratio

**`score(detection)` — scoring (30/25/25/20):**
- Impulse strength (30): larger % move + faster completion (fewer bars)
- Pullback quality (25): shallower pullback + clean EMA touch (closer to EMA)
- Volume profile (25): higher bounce volume ratio
- Trend context (20): price position relative to VWAP (from indicators dict)

**`get_default_params()` — return `list[PatternParam]`:**
All constructor params with appropriate min/max/step values and categories (detection, filtering, trade, scoring).

### 2. Create `argus/core/config.py` addition: MicroPullbackConfig

Add `MicroPullbackConfig(StrategyConfig)` following the `DipAndRipConfig` pattern. All detection params as Pydantic Fields with `ge`/`le` bounds that encompass the PatternParam `min_value`/`max_value` ranges. Include `target_1_r`, `target_2_r`, `time_stop_minutes` fields.

### 3. Create `config/strategies/micro_pullback.yaml`

Follow `dip_and_rip.yaml` structure exactly:
```yaml
strategy_id: "strat_micro_pullback"
name: "Micro Pullback"
version: "1.0.0"
enabled: true
mode: live
asset_class: "us_stocks"
pipeline_stage: "exploration"
family: "continuation"
description_short: "First pullback to EMA after strong impulse — continuation entry with volume confirmation."
time_window_display: "10:00 AM-2:00 PM"
operating_window:
  earliest_entry: "10:00"
  latest_entry: "14:00"
  force_close: "15:50"
# Detection params (matching constructor defaults)
ema_period: 9
min_impulse_percent: 0.02
# ... all params ...
time_stop_minutes: 30
risk_limits:
  max_loss_per_trade_pct: 0.01
  max_daily_loss_pct: 0.03
  max_trades_per_day: 5
  max_concurrent_positions: 0
# ... benchmarks, backtest_summary, universe_filter, exit_management sections
```

### 4. Create `config/universe_filters/micro_pullback.yaml`

```yaml
min_price: 5.0
max_price: 200.0
min_avg_volume: 500000
```

### 5. Wire into main.py

Add a Micro Pullback strategy creation block in main.py following the exact pattern of the Dip-and-Rip block (~line 557). Load config from `config/strategies/micro_pullback.yaml`, create pattern via `build_pattern_from_config()`, wrap in `PatternBasedStrategy`, add to strategies list.

### 5b. Wire `increment_signal_cutoff()` in main.py (S1 carry-forward)

S1 added `signal_cutoff_skipped_count` and `increment_signal_cutoff()` to OrderManager but could not wire the call site because S1 was constrained from modifying main.py. Since S3 already modifies main.py, wire this now.

In `_process_signal()` (~line 1529–1537), the pre-EOD signal cutoff block logs and returns when past cutoff time. Before the `return` on ~line 1537, add:

```python
                if self._order_manager is not None:
                    self._order_manager.increment_signal_cutoff()
```

This ensures the debrief export's `safety_summary.signals_skipped` field reflects actual cutoff events. One line, zero risk.

### 6. Wire into BacktestEngine

In `argus/backtest/config.py`: add `MICRO_PULLBACK = "micro_pullback"` to `StrategyType` enum.

In `argus/backtest/engine.py`: add `_create_micro_pullback_strategy()` method following the S1-fixed pattern (using `build_pattern_from_config()`). Add the case to the strategy dispatch in `_create_strategy()`.

### 7. Wire into factory and experiment runner

In `argus/strategies/patterns/factory.py`:
- Add to `_PATTERN_REGISTRY`: `"MicroPullbackPattern": ("argus.strategies.patterns.micro_pullback", "MicroPullbackPattern")`
- Add to `_SNAKE_CASE_ALIASES`: `"micro_pullback": "MicroPullbackPattern"`

In `argus/intelligence/experiments/runner.py`:
- Add to `_PATTERN_TO_STRATEGY_TYPE`: `"micro_pullback": StrategyType.MICRO_PULLBACK`

### 8. Cross-validation tests

Write tests that verify:
- `MicroPullbackPattern().get_default_params()` default values match `MicroPullbackConfig()` field defaults
- PatternParam `min_value`/`max_value` ranges fall within Pydantic `ge`/`le` bounds
- Loading `config/strategies/micro_pullback.yaml` into `MicroPullbackConfig` succeeds with no silently ignored keys

## Constraints
- Do NOT modify any existing pattern file
- Do NOT modify existing strategy config YAMLs
- Do NOT add API routes, frontend components, or database tables
- The EMA computation must be self-contained within the pattern (do not rely on data_service.get_indicator for EMA — it may not be available). ATR and VWAP can come from the indicators dict.
- Follow the PatternModule ABC contract exactly — no additional abstract methods or protocol changes

## Test Targets
- Existing tests: all must still pass
- New tests:
  1. MicroPullbackPattern detect() — positive detection with synthetic impulse + pullback candles
  2. MicroPullbackPattern detect() — returns None when impulse too small
  3. MicroPullbackPattern detect() — returns None when no pullback to EMA
  4. MicroPullbackPattern detect() — returns None when bounce volume insufficient
  5. MicroPullbackPattern score() — boundary values
  6. MicroPullbackPattern get_default_params() — returns list[PatternParam] with correct count
  7. Cross-validation: config defaults match pattern defaults
  8. Cross-validation: PatternParam ranges within Pydantic bounds
  9. Config loading: YAML → Pydantic with no ignored keys
  10. BacktestEngine: MICRO_PULLBACK strategy type creates runnable strategy
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q -n auto`

## Config Validation
Write a test that loads `config/strategies/micro_pullback.yaml` and verifies all keys are recognized by `MicroPullbackConfig`:
1. Load YAML, extract all top-level keys
2. Filter to detection/trade params (exclude standard StrategyConfig fields like strategy_id, name, etc.)
3. Compare against `MicroPullbackConfig.model_fields.keys()`
4. Assert no YAML keys absent from model

## Definition of Done
- [ ] MicroPullbackPattern implements PatternModule ABC (5 required members)
- [ ] Detection logic handles impulse → pullback → bounce flow correctly
- [ ] Score function weights 30/25/25/20
- [ ] get_default_params returns list[PatternParam] with correct metadata
- [ ] MicroPullbackConfig Pydantic model with proper Field bounds
- [ ] Config YAML + universe filter YAML created
- [ ] Wired into main.py, BacktestEngine, factory, experiment runner
- [ ] `increment_signal_cutoff()` wired in main.py `_process_signal()` cutoff block (S1 carry-forward)
- [ ] Cross-validation tests pass
- [ ] All existing tests pass
- [ ] ≥10 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing pattern changes | `git diff argus/strategies/patterns/ -- ':!micro_pullback.py' ':!factory.py' ':!base.py' ':!__init__.py'` empty |
| Existing strategies untouched | `git diff config/strategies/ -- ':!micro_pullback.yaml'` empty |
| Factory registry correct | Test: `get_pattern_class("micro_pullback")` returns MicroPullbackPattern |
| BacktestEngine dispatch works | Test: StrategyType.MICRO_PULLBACK creates strategy |
| Signal cutoff wiring | `grep -n "increment_signal_cutoff" argus/main.py` returns the call in `_process_signal()` |

## Sprint-Level Escalation Criteria
1. Pattern signals appear outside 10:00–14:00 window → STOP
2. Test count decreases → STOP
3. Cross-validation test reveals Pydantic silently ignoring config fields → fix before proceeding

## Close-Out
Write the close-out report to: `docs/sprints/sprint-31a/session-3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context file: `docs/sprints/sprint-31a/review-context.md`
2. Close-out report: `docs/sprints/sprint-31a/session-3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q -n auto`
5. Files NOT modified: any existing pattern file, orchestrator.py, risk_manager.py, any frontend file, existing strategy config YAMLs

## Session-Specific Review Focus (for @reviewer)
1. Verify EMA computation is self-contained (no dependency on external indicator service)
2. Verify detect() returns None for all edge cases (insufficient bars, no impulse, no pullback, no volume)
3. Verify PatternParam step values are reasonable for parameter sweeps (not too fine, not too coarse)
4. Verify config YAML values match constructor defaults exactly
5. Verify factory registry entries use correct module path and class name
6. Verify BacktestEngine creation method uses `build_pattern_from_config()` (not no-arg constructor)
7. Verify `increment_signal_cutoff()` is called before `return` in the pre-EOD cutoff block of `_process_signal()` (S1 carry-forward)