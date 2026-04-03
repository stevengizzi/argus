# Sprint 31A, Session 4: VWAP Bounce Pattern (Complete)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC)
   - `argus/strategies/patterns/micro_pullback.py` (S3 output — follow this structure exactly)
   - `argus/strategies/patterns/factory.py` (verify S3 additions, add new entries)
   - `argus/core/config.py` (verify MicroPullbackConfig from S3, add new config)
   - `argus/main.py` (verify S3 wiring, add new block)
   - `argus/backtest/config.py` (StrategyType enum — verify MICRO_PULLBACK, add new)
   - `argus/backtest/engine.py` (verify S3 creation method, add new)
   - `argus/intelligence/experiments/runner.py` (verify S3 mapping, add new)
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/strategies/patterns/ -x -q -n auto`
   Expected: all passing (including S3 tests)
3. Verify you are on the correct branch: `main` (with S1–S3 committed)

## Objective
Implement the VWAP Bounce pattern as a complete PatternModule with full integration stack, following the exact structure established by Micro Pullback in S3.

## Pattern Design: VWAP Bounce

**Mechanic:** Stock trading above VWAP pulls back to test VWAP as support. Price touches/tests VWAP, then bounces with volume confirmation. Continuation-side complement to VWAP Reclaim (which enters from below).

**Operating window:** 10:30 AM – 15:00 ET.

## Requirements

### 1. Create `argus/strategies/patterns/vwap_bounce.py`

Implement `VwapBouncePattern(PatternModule)` with:

**Constructor params:**
- `vwap_approach_distance_pct: float = 0.005` — Distance from VWAP to start monitoring (0.5%)
- `vwap_touch_tolerance_pct: float = 0.002` — How close low must get to VWAP (0.2%)
- `min_bounce_bars: int = 2` — Consecutive bars closing above VWAP after touch
- `min_bounce_volume_ratio: float = 1.3` — Bounce bar volume / avg recent volume
- `min_prior_trend_bars: int = 10` — Min bars price was above VWAP before approach
- `min_price_above_vwap_pct: float = 0.003` — During prior trend, avg distance above VWAP (0.3%)
- `stop_buffer_atr_mult: float = 0.5` — ATR mult for stop below VWAP
- `target_ratio: float = 2.0` — Target distance ratio
- `target_1_r: float = 1.0` — First target R-multiple
- `target_2_r: float = 2.0` — Second target R-multiple
- `min_score_threshold: float = 0.0` — Min confidence to emit

**Properties:**
- `name` → `"VWAP Bounce"`
- `lookback_bars` → `30`

**`detect(candles, indicators)` logic:**
1. Get VWAP from `indicators["vwap"]`. If unavailable or ≤ 0, return None.
2. Verify prior uptrend: count bars (from oldest in window) where close > VWAP. Need ≥ `min_prior_trend_bars`.
3. Find approach: scan for the transition zone where price moves within `vwap_approach_distance_pct` of VWAP from above.
4. Find touch: candle whose low is within `vwap_touch_tolerance_pct` × VWAP of the VWAP value. The low can slightly undershoot VWAP (the tolerance allows for wicks below).
5. Bounce confirmation: `min_bounce_bars` consecutive candles after the touch with close > VWAP, and bounce bar volume ≥ `min_bounce_volume_ratio` × avg volume.
6. Entry at confirmation candle close. Stop below VWAP - ATR buffer. Targets via R-multiples.
7. Return PatternDetection with metadata: vwap_value, prior_trend_bars, touch_depth_pct, bounce_volume_ratio, approach_quality.

**`score(detection)` — 30/25/25/20:**
- VWAP interaction quality (30): cleaner touch + faster bounce
- Prior trend strength (25): more bars above VWAP + greater avg distance
- Volume profile (25): bounce volume ratio
- Price structure (20): higher lows during approach (bullish structure)

**`get_default_params()`:** All constructor params as PatternParam with appropriate ranges.

### 2–7. Wiring (follow S3 pattern exactly)

- `argus/core/config.py`: Add `VwapBounceConfig(StrategyConfig)` — follow MicroPullbackConfig structure
- `config/strategies/vwap_bounce.yaml`: strategy_id `"strat_vwap_bounce"`, family `"continuation"`, window 10:30–15:00, force_close 15:50
- `config/universe_filters/vwap_bounce.yaml`: min_price 5.0, max_price 200.0, min_avg_volume 500000
- `argus/main.py`: Add creation block following Micro Pullback wiring
- `argus/backtest/config.py`: `VWAP_BOUNCE = "vwap_bounce"`
- `argus/backtest/engine.py`: Add `_create_vwap_bounce_strategy()` using `build_pattern_from_config()`
- `argus/strategies/patterns/factory.py`: Add registry + alias entries
- `argus/intelligence/experiments/runner.py`: Add mapping entry

### 8. Cross-validation tests (same pattern as S3)

## Constraints
- Same as S3. Do NOT modify micro_pullback.py or any other existing pattern file.
- VWAP must come from `indicators["vwap"]` — do NOT compute VWAP from candle data (VWAP requires cumulative volume × price from market open, which the pattern doesn't have).
- If VWAP is unavailable, detect() returns None cleanly (no exception).

## Test Targets
- New tests: detect positive case, reject no-VWAP, reject below-VWAP, reject insufficient prior trend, reject no volume, score boundaries, get_default_params count, cross-validation ×2, config loading, BacktestEngine dispatch
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q -n auto`

## Config Validation
Same pattern as S3: verify YAML keys match `VwapBounceConfig.model_fields`.

## Definition of Done
- [ ] VwapBouncePattern implements PatternModule ABC
- [ ] Detection handles VWAP approach → touch → bounce flow
- [ ] Returns None when VWAP unavailable
- [ ] Full wiring (main.py, BacktestEngine, factory, runner)
- [ ] Cross-validation tests pass
- [ ] All existing tests pass, ≥10 new tests
- [ ] Close-out report + Tier 2 review

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing pattern changes | `git diff argus/strategies/patterns/ -- ':!vwap_bounce.py' ':!factory.py' ':!__init__.py'` empty |
| Existing strategies untouched | `git diff config/strategies/ -- ':!vwap_bounce.yaml'` empty |
| Factory registry correct | Test: `get_pattern_class("vwap_bounce")` returns VwapBouncePattern |
| BacktestEngine dispatch works | Test: StrategyType.VWAP_BOUNCE creates strategy |

## Sprint-Level Escalation Criteria
1. Pattern signals appear outside 10:30–15:00 window → STOP
2. Test count decreases → STOP
3. Cross-validation test reveals Pydantic silently ignoring config fields → fix before proceeding

## Close-Out
Write to: `docs/sprints/sprint-31a/session-4-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context file: `docs/sprints/sprint-31a/review-context.md`
2. Close-out: `docs/sprints/sprint-31a/session-4-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q -n auto`
5. NOT modified: any pattern file except vwap_bounce.py, factory.py, __init__.py

## Session-Specific Review Focus (for @reviewer)
1. Verify VWAP comes from indicators dict, not computed from candles
2. Verify "prior trend above VWAP" check prevents entering when price was recently below VWAP
3. Verify touch tolerance allows slight undershoot (wick below VWAP)
4. Verify this pattern is distinct from VWAP Reclaim (bounce from above, not reclaim from below)
5. Verify BacktestEngine creation uses build_pattern_from_config()
6. Verify cross-validation tests exist and pass
