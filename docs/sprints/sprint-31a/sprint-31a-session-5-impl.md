# Sprint 31A, Session 5: Narrow Range Breakout Pattern (Complete)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/base.py` (PatternModule ABC)
   - `argus/strategies/patterns/micro_pullback.py` or `vwap_bounce.py` (S3/S4 — follow structure)
   - `argus/strategies/patterns/factory.py` (verify S3+S4 additions, add new entries)
   - `argus/core/config.py` (verify prior configs, add new)
   - `argus/main.py`, `argus/backtest/config.py`, `argus/backtest/engine.py`, `argus/intelligence/experiments/runner.py` (verify prior wiring, add new)
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/strategies/patterns/ -x -q -n auto`
   Expected: all passing (including S3+S4 tests)
3. Verify you are on the correct branch: `main` (with S1–S4 committed)

## Objective
Implement the Narrow Range Breakout pattern with full integration stack.

## Pattern Design: Narrow Range Breakout

**Mechanic:** Identifies consolidation via progressively narrowing bar ranges. After min_narrowing_bars of range contraction within a tight ATR band, a breakout candle closes above the consolidation high with volume surge. Long-only.

**Operating window:** 10:00 AM – 15:00 ET.

**Distinct from HOD Break (requires session high proximity) and Flat-Top (requires flat resistance). NRB is purely about volatility compression → expansion.**

## Requirements

### 1. Create `argus/strategies/patterns/narrow_range_breakout.py`

Implement `NarrowRangeBreakoutPattern(PatternModule)` with:

**Constructor params:**
- `nr_lookback: int = 7` — Bars to scan for narrowing range sequence
- `min_narrowing_bars: int = 3` — Min consecutive bars with decreasing range
- `range_decay_tolerance: float = 1.05` — range(i) ≤ range(i-1) × tolerance (allows 5% noise)
- `breakout_margin_percent: float = 0.001` — Min close excess above consolidation high (0.1%)
- `min_breakout_volume_ratio: float = 1.5` — Breakout bar volume / avg consolidation volume
- `consolidation_max_range_atr: float = 0.8` — Max overall consolidation range as ATR multiple
- `stop_buffer_atr_mult: float = 0.5` — ATR mult for stop below consolidation low
- `target_ratio: float = 2.0` — Target distance ratio
- `target_1_r: float = 1.0` — First target R-multiple
- `target_2_r: float = 2.0` — Second target R-multiple
- `min_score_threshold: float = 0.0` — Min confidence to emit

**Properties:**
- `name` → `"Narrow Range Breakout"`
- `lookback_bars` → `20` (needs range comparison history)

**`detect(candles, indicators)` logic:**
1. Get ATR from `indicators["atr"]`. If unavailable, compute from candles (self-contained, like PMH's `_compute_atr()`).
2. Scan the most recent `nr_lookback` bars for a narrowing sequence: find the longest run of consecutive bars where `range(i) ≤ range(i-1) × range_decay_tolerance` (where range = high - low).
3. If the longest run ≥ `min_narrowing_bars`, identify the consolidation zone: high = max(highs of narrowing bars), low = min(lows of narrowing bars).
4. Validate consolidation quality: overall range ≤ `consolidation_max_range_atr` × ATR.
5. Check the bar immediately after the narrowing sequence: does it close above `consolidation_high + breakout_margin_percent × price`?
6. Volume confirmation: breakout bar volume ≥ `min_breakout_volume_ratio` × avg volume of narrowing bars.
7. Long-only: if breakout is below consolidation low, return None.
8. Entry at breakout close. Stop below consolidation low - ATR buffer. Targets via R-multiples.
9. Return PatternDetection with metadata: narrowing_bar_count, consolidation_range, consolidation_range_atr_ratio, breakout_margin, breakout_volume_ratio, consolidation_high, consolidation_low.

**`score(detection)` — 30/25/25/20:**
- Consolidation quality (30): more narrowing bars + tighter final range (relative to ATR)
- Breakout strength (25): margin above consolidation + decisive close
- Volume profile (25): low volume during consolidation (contraction) vs high volume on breakout (expansion ratio)
- Range context (20): overall consolidation range relative to ATR (tighter = better)

**`get_default_params()`:** All constructor params as PatternParam.

### 2–7. Wiring (follow S3/S4 pattern)

- `VwapBounceConfig` → `NarrowRangeBreakoutConfig` in config.py
- YAML: strategy_id `"strat_narrow_range_breakout"`, family `"breakout"`, window 10:00–15:00
- Universe filter: min_price 5.0, max_price 200.0, min_avg_volume 300000
- StrategyType: `NARROW_RANGE_BREAKOUT = "narrow_range_breakout"`
- All other wiring identical to S3/S4 pattern

### 8. Cross-validation tests

## Constraints
- Same as S3/S4. Do NOT modify any existing pattern or config file.
- Long-only: no breakout-below-consolidation entries.
- ATR: use from indicators if available, else compute self-contained.

## Test Targets
- New tests: detect positive case (clear narrowing → breakout), reject insufficient narrowing bars, reject consolidation too wide (exceeds ATR limit), reject no breakout (close stays within range), reject downward breakout, reject insufficient volume, score boundaries, get_default_params, cross-validation ×2, config loading, BacktestEngine dispatch
- Minimum new test count: 10
- Test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q -n auto`

## Config Validation
Same pattern as S3/S4: verify YAML keys match `NarrowRangeBreakoutConfig.model_fields`.

## Definition of Done
- [ ] NarrowRangeBreakoutPattern implements PatternModule ABC
- [ ] Detection handles narrowing scan → consolidation → breakout flow
- [ ] Long-only enforced (downward breakout rejected)
- [ ] Full wiring complete
- [ ] Cross-validation + config validation tests pass
- [ ] All existing tests pass, ≥10 new tests
- [ ] Close-out report + Tier 2 review

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing pattern changes | `git diff argus/strategies/patterns/ -- ':!narrow_range_breakout.py' ':!factory.py' ':!__init__.py'` empty |
| Existing strategies untouched | `git diff config/strategies/ -- ':!narrow_range_breakout.yaml'` empty |
| Factory registry correct | Test: `get_pattern_class("narrow_range_breakout")` returns NarrowRangeBreakoutPattern |
| BacktestEngine dispatch works | Test: StrategyType.NARROW_RANGE_BREAKOUT creates strategy |

## Sprint-Level Escalation Criteria
1. Pattern signals appear outside 10:00–15:00 window → STOP
2. Test count decreases → STOP
3. Cross-validation test reveals Pydantic silently ignoring config fields → fix before proceeding

## Close-Out
Write to: `docs/sprints/sprint-31a/session-5-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context file: `docs/sprints/sprint-31a/review-context.md`
2. Close-out: `docs/sprints/sprint-31a/session-5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/strategies/patterns/ tests/backtest/ -x -q -n auto`
5. NOT modified: any pattern file except narrow_range_breakout.py, factory.py, __init__.py

## Session-Specific Review Focus (for @reviewer)
1. Verify narrowing detection uses `range_decay_tolerance` (not strict < comparison)
2. Verify "longest run" logic correctly finds the best narrowing sequence in the lookback window
3. Verify consolidation_max_range_atr check prevents triggering on wide ranges that happen to narrow
4. Verify long-only: downward breakout explicitly returns None
5. Verify ATR fallback computation matches other patterns (e.g., PMH's _compute_atr())
6. Verify BacktestEngine creation uses build_pattern_from_config()
