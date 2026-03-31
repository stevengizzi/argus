# Sprint 29 — Session 5 Fix Close-out

**Date:** 2026-03-31
**Scope:** Targeted fix for Tier 2 review finding F1 (MAJOR) — `PatternBasedStrategy` missing `indicators["symbol"]` wiring.

## Problem

`GapAndGoPattern.detect()` reads `indicators["symbol"]` to look up prior close from the reference data cache. However, `PatternBasedStrategy.on_candle()` never populated that key in the indicators dict passed to `detect()`. The pattern was non-functional in production — every `detect()` call would KeyError or silently fail on the missing symbol lookup.

## Fix

**File:** `argus/strategies/pattern_strategy.py` (line 322)

Added `indicators["symbol"] = symbol` after the indicator-building loop and before the `self._pattern.detect()` call. One-line fix.

## Test Added

**File:** `tests/strategies/patterns/test_pattern_strategy.py`

`test_indicators_include_symbol_key` — uses a `CapturingPattern` subclass that records the indicators dict, then asserts `"symbol"` is present and matches the candle's symbol.

## Test Delta

| Suite | Before | After | Delta |
|-------|--------|-------|-------|
| Pattern tests | 131 | 132 | +1 |
| Full pytest suite | 3,966 → 4,069* | 4,070 | +1 |

*Full suite count varies slightly due to parameterized test expansion across sprints.

## Verification

```
python -m pytest tests/strategies/patterns/ -x -q       → 132 passed (0.14s)
python -m pytest --ignore=tests/test_main.py -n auto -q  → 4,070 passed (49.12s)
```

## Self-Assessment

**CLEAN** — Single-line production fix + one test. No scope deviation. No regressions.

## Context State

GREEN — minimal context usage.
