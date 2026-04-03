# Sprint 31A, Session 2: PMH 0-Trade Fix — Close-Out Report

**Date:** 2026-04-03
**Self-assessment:** CLEAN

## Change Manifest

### `argus/strategies/patterns/base.py`
- Added `min_detection_bars` property to `PatternModule` class
- Non-abstract, defaults to `self.lookback_bars` — zero behavior change for all existing patterns

### `argus/strategies/pattern_strategy.py`
- Line ~290 in `on_candle()`: changed `lookback = self._pattern.lookback_bars` to `lookback = self._pattern.min_detection_bars`
- Deque maxlen in `_get_candle_window()` unchanged — still uses `self._pattern.lookback_bars`

### `argus/strategies/patterns/premarket_high_break.py`
- `lookback_bars` changed from `30` to `400`
- Added `min_detection_bars` property returning `10`

### `argus/main.py`
- Phase 9.5: Added PatternBasedStrategy reference data wiring block after R2G wiring (lines ~941–951)
- Periodic refresh: Added PatternBasedStrategy re-wiring block after R2G re-initialization (lines ~1470–1480)

### `tests/strategies/patterns/test_pattern_base.py`
- Added `TestMinDetectionBars` class with 5 tests:
  1. `test_min_detection_bars_defaults_to_lookback_bars` — MockPattern has no override
  2. `test_pmh_lookback_bars_is_400` — PMH lookback is 400
  3. `test_pmh_min_detection_bars_is_10` — PMH min_detection is 10
  4. `test_pmh_min_detection_bars_less_than_lookback_bars` — sanity invariant
  5. `test_bull_flag_min_detection_bars_equals_lookback_bars` — backward compat

### `tests/strategies/patterns/test_pattern_strategy.py`
- Added `MockPatternWithMinDetection` class (lookback=50, min_detection=3)
- Added 5 tests:
  - `test_pattern_based_strategy_uses_min_detection_bars_for_eligibility`
  - `test_pattern_without_min_detection_bars_override_uses_lookback_bars`
  - `test_initialize_reference_data_forwards_prev_close_to_pattern`
  - `test_initialize_reference_data_skips_symbols_with_no_prev_close`
  - `test_initialize_reference_data_empty_ref_data_is_no_op`

### `tests/strategies/patterns/test_premarket_high_break.py`
- Added `import pytest`
- Added `TestPMHLookbackAndMinDetectionBars` class with 2 tests:
  - `test_detect_finds_pm_high_from_large_pm_candle_set` — 300 PM candles, PM high found correctly
  - `test_resolve_prior_close_returns_value_when_set_via_set_reference_data`

## Test Results
- Baseline: 676 passing
- Final: 688 passing (+12 new tests)
- Command: `python -m pytest tests/strategies/ -x -q -n auto`

## Judgment Calls
1. **Reference data field:** Used `prev_close` (confirmed from `SymbolReferenceData` in `fmp_reference.py` — not `last_close`). `initialize_reference_data()` already had this logic; main.py wiring just calls the existing method.
2. **No changes needed to backfill logic:** With `lookback_bars=400`, `backfill_candles()` takes `combined[-400:]` which covers 335 PM + 65 market bars at 10:30 AM. This works without any change.
3. **Minimum new test count exceeded:** 12 new tests written vs. 8 required.

## Regression Checklist
| Check | Result |
|-------|--------|
| BullFlag `min_detection_bars == lookback_bars` | PASS — confirmed via test |
| PMH `lookback_bars == 400` | PASS — confirmed via test |
| PMH `min_detection_bars == 10` | PASS — confirmed via test |
| R2G wiring intact | PASS — `initialize_prior_closes` at lines 940 + 1469 |
| No other pattern files modified | PASS — `git diff HEAD -- argus/strategies/patterns/` shows only premarket_high_break.py + base.py |
| `_get_candle_window()` still uses `lookback_bars` for maxlen | PASS — line 120 unchanged |

## Scope Verification
- [x] `min_detection_bars` added to PatternModule (non-abstract)
- [x] PatternBasedStrategy uses `min_detection_bars` for detection eligibility
- [x] PMH `lookback_bars=400`, `min_detection_bars=10`
- [x] Existing patterns unchanged
- [x] Reference data wired for PatternBasedStrategy in Phase 9.5
- [x] Reference data re-wired on periodic watchlist refresh
- [x] R2G wiring unchanged
- [x] ≥8 new tests written and passing (12 written)

## Context State
GREEN — session completed well within context limits.
