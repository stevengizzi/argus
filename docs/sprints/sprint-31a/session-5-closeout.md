# Sprint 31A Session 5 — Close-Out Report

## Session: Narrow Range Breakout Pattern

**Date:** 2026-04-03
**Status:** CLEAN

---

## Change Manifest

### New Files
| File | Purpose |
|------|---------|
| `argus/strategies/patterns/narrow_range_breakout.py` | NarrowRangeBreakoutPattern(PatternModule) — 11-param constructor, detect/score/_compute_atr/_find_narrowing_run_length/_compute_confidence |
| `config/strategies/narrow_range_breakout.yaml` | Strategy config YAML (strat_narrow_range_breakout, family: breakout, 10:00–15:00 ET) |
| `config/universe_filters/narrow_range_breakout.yaml` | Universe filter (min_price: 5.0, max_price: 200.0, min_avg_volume: 300000) |
| `tests/strategies/patterns/test_narrow_range_breakout.py` | 20 new tests |

### Modified Files
| File | Change |
|------|--------|
| `argus/core/config.py` | Added `NarrowRangeBreakoutConfig(StrategyConfig)` + `load_narrow_range_breakout_config()` (after VwapBounceConfig) |
| `argus/backtest/config.py` | Added `NARROW_RANGE_BREAKOUT = "narrow_range_breakout"` to `StrategyType` enum |
| `argus/backtest/engine.py` | Added `NarrowRangeBreakoutConfig` import, dispatch branch, `_create_narrow_range_breakout_strategy()` factory method |
| `argus/intelligence/experiments/runner.py` | Added `"narrow_range_breakout": StrategyType.NARROW_RANGE_BREAKOUT` to `_PATTERN_TO_STRATEGY_TYPE` |
| `argus/main.py` | Added `load_narrow_range_breakout_config` import, startup block, orchestrator registration, experiment base strategies entry |
| `argus/strategies/patterns/factory.py` | Added `NarrowRangeBreakoutPattern` to `_PATTERN_REGISTRY` + `narrow_range_breakout` to `_SNAKE_CASE_ALIASES` |

---

## Pattern Design Decisions

**min_detection_bars:** Set to `min_narrowing_bars + 1` (not `nr_lookback + 1`) — detection begins as soon as there are enough bars for the minimum viable window. The `lookback_bars=20` deque capacity is independent of the detection gate. This matches the spirit of other patterns (e.g., VwapBounce uses `min_prior_trend_bars + min_bounce_bars + 3`).

**Narrowing run detection:** `_find_narrowing_run_length()` counts backward from `window[-1]` (= candles[-2]) until the tolerance condition breaks. This correctly identifies the run ending immediately before the breakout bar and is consistent with the "longest run ending at the bar before breakout" interpretation.

**Consolidation zone window:** Uses `candles[max(0, len-nr_lookback-1):-1]` — dynamically clips to the most recent nr_lookback bars (excluding breakout), adapting gracefully when fewer bars are available.

**Long-only gate:** Checked before the margin test — a close below consolidation_low is rejected immediately as a downward breakout.

---

## Test Results

| Run | Tests | Status |
|-----|-------|--------|
| Scoped (patterns + backtest) | 827 | All pass |
| Full suite (--ignore test_main.py) | 4,758 | All pass |
| New tests in this session | +20 | All pass |

Baseline at session start: 324 tests in `tests/strategies/patterns/`.
After session: 344 tests in `tests/strategies/patterns/` (+20).

---

## Scope Verification (vs. Spec)

- [x] NarrowRangeBreakoutPattern implements PatternModule ABC
- [x] detect() handles narrowing scan → consolidation → breakout flow
- [x] Long-only enforced (downward breakout rejected)
- [x] Full wiring: config.py, backtest/config.py, engine.py, runner.py, main.py, factory.py
- [x] Cross-validation tests pass (factory resolution + build_pattern_from_config)
- [x] Config validation test passes (YAML keys match Pydantic fields)
- [x] BacktestEngine dispatch test passes
- [x] ≥10 new tests (20 total)
- [x] All existing tests pass

---

## Regression Checklist

| Check | Result |
|-------|--------|
| No existing pattern files changed | PASS — only factory.py modified (registry addition) |
| Existing strategies untouched | PASS — no config/strategies/ changes except new file |
| Factory registry correct | PASS — `get_pattern_class("narrow_range_breakout")` returns NarrowRangeBreakoutPattern |
| BacktestEngine dispatch works | PASS — `_create_narrow_range_breakout_strategy()` creates PatternBasedStrategy with NarrowRangeBreakoutPattern |

---

## Context State

GREEN — session completed well within context limits.

---

## Self-Assessment: CLEAN

All spec items completed. No scope expansion. No deviations from S3/S4 wiring pattern.
