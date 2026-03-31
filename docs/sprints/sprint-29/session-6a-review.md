---BEGIN-REVIEW---

# Tier 2 Review: Sprint 29 Session 6a — ABCD Core: Swing Detection + Pattern Logic

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-31
**Commit reviewed:** f05d85a (HEAD)
**Close-out self-assessment:** CLEAN

---

## 1. Scope Compliance

**Verdict: PASS**

The session delivered exactly what the spec required:
- ABCDPattern implementing all 5 PatternModule abstract members (name, lookback_bars, detect, score, get_default_params)
- Swing detection with configurable lookback and ATR minimum filtering
- Fibonacci BC retracement validation (0.382-0.618 range)
- Leg ratio validation (price and time dimensions)
- Completion zone with percentage-based tolerance
- Scoring with weights summing to 100 (35/25/20/20)
- 14 PatternParam entries with full metadata
- 19 new tests

Only 3 files changed: `argus/strategies/patterns/abcd.py` (new), `tests/strategies/patterns/test_abcd.py` (new), and the close-out document. No forbidden files modified.

---

## 2. Review Focus Item Analysis

### F1: Swing detection edge handling
**PASS.** `_find_swing_highs()` and `_find_swing_lows()` both iterate `range(lookback, len(candles) - lookback)`, correctly excluding the first and last `swing_lookback` candles from consideration. Test `test_edge_candles_excluded` verifies this with `swing_lookback=3` and a peak at index 1.

### F2: Fibonacci retracement calculation
**PASS.** Line 314: `bc_retracement = (b_price - c_price) / ab_height` where `ab_height = b_price - a_price`. This is `(B - C) / (B - A)`, the standard Fibonacci retracement formula for a bullish pattern. For a 50% retrace: C = B - 0.5*(B-A), so (B - C)/(B - A) = 0.5. Mathematically correct.

### F3: Leg ratio uses both price AND time dimensions
**PASS.** Lines 328-345: `price_ratio = cd_height / ab_height` (price dimension) and `time_ratio = cd_bars / ab_bars` (time dimension). Both are independently validated against configurable min/max bounds. Test `test_symmetric_legs_accepted` and `test_proportional_time_ratio_accepted` verify both dimensions appear in metadata.

### F4: Incomplete patterns return None
**PASS.** Multiple early-return None paths:
- Insufficient candle history (line 217)
- Insufficient swing points (line 229)
- No B candidate after A (line 243)
- No C candidate after B (line 257)
- Fibonacci out of range (line 315)
- Completion zone miss (line 324)
- Price ratio out of range (line 334)
- Time ratio out of range (line 345)
Test `test_incomplete_pattern_abc_only_returns_none` and `test_insufficient_candle_history_returns_none` verify this.

### F5: Completion zone tolerance is percentage-based
**PASS.** Line 323: `tolerance = projected_d * (self._completion_tolerance_percent / 100.0)`. The tolerance is a percentage of the projected D price, not an absolute value. With default 1.0%, a projected_d of $110 gives tolerance of $1.10.

### F6: Off-by-one errors in candle indexing
**PASS.** No off-by-one errors found:
- Swing detection slicing: `left = candles[i - lookback : i]` (excludes i), `right = candles[i + 1 : i + 1 + lookback]` (excludes i). Correct.
- CD bars: `cd_bars = len(candles) - 1 - c_index`. Uses 0-based last index minus C index. Correct.
- AB bars: `ab_bars = b_index - a_index`. Direct index difference. Correct.

### F7: Score weights sum to 100
**PASS.** With perfect inputs: fib_score = 15 + 1.0*20 = 35, symmetry_score = (1.0*0.6 + 1.0*0.4)*25 = 25, vol_score = 20 (ratio >= 1.2), trend_score = 1.0*20 = 20. Total = 100. Test `test_score_weights_sum_to_100` verifies this directly.

### F8: Synthetic test data creates mathematically valid ABCD patterns
**PASS.** The `_build_abcd_candles()` helper constructs strictly monotonic segments with a 0.50 price margin ensuring swing bars are unambiguous extrema. The candle high/low spread is 0.001 for intermediate bars (preventing false swing points) while swing bars use the actual swing price in their high or low field. The default c_retrace=0.618 is at the boundary but tests use 0.500 (well within range). Total bar count (25 flat + ~49 pattern = 74) exceeds the 60-bar lookback requirement.

---

## 3. Findings

### F1 (Informational): Unused `min_score_threshold` parameter
The `min_score_threshold` parameter is stored in `__init__` and included in `get_default_params()` but never checked in `detect()` or `score()`. Detections are emitted regardless of score. The close-out documents this as intentional (V1), and it is harmless -- the parameter exists for future filtering without API changes. No action needed.

### F2 (Informational): Reserved `fib_c_min`/`fib_c_max` parameters
These parameters are stored and returned via `get_default_params()` but have no effect on detection logic. Documented in the close-out as forward-compatible placeholders for CD extension validation. No action needed.

### F3 (Informational): Score metadata defaults produce ~70/100 for unscored fields
When `cd_bc_volume_ratio` (default 1.0) and `trend_aligned` (default 0.5) are not populated by `detect()`, the score formula produces fib(35) + symmetry(25) + volume(10) + trend(10) = 80 at best, and ~70 for typical non-perfect patterns. This is documented as intentional conservative scoring until enrichment is added. No action needed.

### F4 (Informational): `_make_detection` helper defined after test classes that use it
The `_make_detection` helper function at line 501 is defined after the `TestABCDScoring` class that references it. Python resolves this at runtime so it works correctly, but it is unconventional. Most test helpers in this project are defined at the top of the file. Purely cosmetic.

---

## 4. Regression Check

| Check | Result |
|-------|--------|
| Pattern test suite (151 tests) | PASS -- all pass |
| ABCD tests (19 tests) | PASS -- all pass in 0.02s |
| No forbidden files modified | PASS -- only abcd.py + test + closeout |
| base.py unchanged | PASS |
| pattern_strategy.py unchanged | PASS |
| Existing pattern detection unchanged | PASS (132 pre-existing tests pass) |

---

## 5. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| ABCD swing detection false positive rate >50% | No -- tests show clean detection |
| PatternParam backward compatibility break | No -- new file only, no modifications |
| Universe filter field silently ignored | N/A for this session |
| Reference data hook ordering issues | N/A for this session |
| Existing pattern behavior change | No -- 132 pre-existing tests pass |
| Config parse failure | N/A -- no config changes |
| Strategy registration collision | N/A -- no registration in this session |

No escalation criteria triggered.

---

## 6. Verdict

**CLEAR**

This is a clean, new-file-only session with correct mathematical implementations, comprehensive edge case handling, and no regressions. All 8 review focus items pass verification. The implementation follows the PatternModule ABC contract correctly, swing detection edge handling is sound, Fibonacci math is accurate, and scoring weights sum to 100 as specified. The 4 informational findings are all documented in the close-out and represent intentional V1 design choices.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "29",
  "session": "S6a",
  "verdict": "CLEAR",
  "findings": [
    {
      "id": "F1",
      "severity": "informational",
      "category": "unused_code",
      "description": "min_score_threshold parameter stored but never checked in detect() or score(). Documented as intentional V1 placeholder.",
      "file": "argus/strategies/patterns/abcd.py",
      "line": 63,
      "action": "none"
    },
    {
      "id": "F2",
      "severity": "informational",
      "category": "unused_code",
      "description": "fib_c_min and fib_c_max parameters reserved but unused in V1 detection logic. Documented as forward-compatible placeholders.",
      "file": "argus/strategies/patterns/abcd.py",
      "line": 53,
      "action": "none"
    },
    {
      "id": "F3",
      "severity": "informational",
      "category": "design",
      "description": "Score metadata defaults (cd_bc_volume_ratio=1.0, trend_aligned=0.5) produce ~70/100 for patterns without enrichment data. Documented as intentional conservative scoring.",
      "file": "argus/strategies/patterns/abcd.py",
      "line": 419,
      "action": "none"
    },
    {
      "id": "F4",
      "severity": "informational",
      "category": "style",
      "description": "_make_detection helper defined after test classes that use it. Works correctly at runtime but unconventional placement.",
      "file": "tests/strategies/patterns/test_abcd.py",
      "line": 501,
      "action": "none"
    }
  ],
  "tests": {
    "pattern_suite": 151,
    "abcd_new": 19,
    "all_pass": true,
    "regressions": 0
  },
  "escalation_triggers": [],
  "files_reviewed": [
    "argus/strategies/patterns/abcd.py",
    "tests/strategies/patterns/test_abcd.py",
    "docs/sprints/sprint-29/session-6a-closeout.md"
  ],
  "forbidden_file_violations": []
}
```
