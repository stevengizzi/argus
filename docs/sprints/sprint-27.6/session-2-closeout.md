# Sprint 27.6, Session 2: BreadthCalculator — Close-Out Report

## Change Manifest

| File | Action | Description |
|------|--------|-------------|
| `argus/core/breadth.py` | **Created** | BreadthCalculator class — standalone breadth dimension calculator |
| `tests/core/test_breadth.py` | **Created** | 17 tests covering all spec requirements |

## Implementation Summary

BreadthCalculator tracks per-symbol rolling close prices via bounded deques and
computes universe breadth metrics on demand:

- **`on_candle(event)`**: O(1) per call — dict lookup + deque append
- **`get_breadth_snapshot()`**: Computes `universe_breadth_score` (-1.0 to +1.0),
  `breadth_thrust` (bool), `symbols_tracked`, `symbols_qualifying`
- **`reset()`**: Clears all state for new trading day

Key design decisions:
- Uses `statistics.mean()` for MA computation (stdlib, no NumPy dependency)
- Type validation on constructor and `on_candle()` inputs
- Symbols exactly at their MA count as neither above nor below (conservative)

## Scope Verification

| Requirement | Status |
|------------|--------|
| BreadthCalculator with all methods | Done |
| Ramp-up handling with min_bars_for_valid | Done |
| Returns None when thresholds not met | Done |
| Memory bounded via fixed-size deques | Done |
| 14+ new tests passing | Done (17 tests) |
| No Event Bus subscription | Done — standalone module |
| No modifications to existing files | Done — `git diff --name-only` shows 0 modified files |

## Regression Checklist

| Check | Result |
|-------|--------|
| No files modified outside breadth.py | Confirmed — only 2 new files (breadth.py + test) |
| O(1) per candle | Confirmed — dict lookup + deque append, no loops over all symbols |
| Memory bounded | Confirmed — deque maxlen = config.ma_period |
| Regime tests still pass | Confirmed — 70 tests passing |

## Test Results

```
tests/core/test_breadth.py: 17 passed (0.03s)
tests/core/test_regime.py:  70 passed (0.33s)
```

## Judgment Calls

1. **`statistics.mean()` vs manual sum/len**: Used stdlib `statistics.mean()` for
   clarity. Performance is adequate — called once per `get_breadth_snapshot()`,
   not per candle.
2. **BreadthConfig min_symbols ge=10**: Tests use min_symbols=10 (the config
   minimum) and feed 10+ symbols to reach threshold. This matches production
   reality where breadth needs a meaningful sample size.

## Self-Assessment

**CLEAN** — All spec items implemented, 17 tests passing (exceeds 14 minimum),
no existing files modified, no scope deviations.

## Context State

**GREEN** — Session completed well within context limits.
