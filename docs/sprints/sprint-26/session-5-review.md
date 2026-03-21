# Sprint 26, Session 5 — Tier 2 Review Report

---BEGIN-REVIEW---

## Session Summary

**Session:** Sprint 26, Session 5 — BullFlagPattern + Config
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-21
**Close-out self-assessment:** CLEAN

## Diff Analysis

### Files in Scope (Session 5 deliverables)

| File | Action | In Spec |
|------|--------|---------|
| `argus/strategies/patterns/bull_flag.py` | Created | Yes |
| `config/strategies/bull_flag.yaml` | Created | Yes |
| `argus/core/config.py` | Modified (+42 lines) | Yes |
| `argus/strategies/patterns/__init__.py` | Modified (+7 lines) | Yes |
| `tests/strategies/patterns/test_bull_flag.py` | Created | Yes |
| `tests/strategies/patterns/test_pattern_strategy.py` | Modified (+47 lines) | Yes |

### Files NOT in Scope (from other sessions, also uncommitted)

The working tree also contains uncommitted changes from what appears to be Session 7
(backtest/walk_forward.py, backtest/config.py, config/strategies/red_to_green.yaml,
vectorbt_red_to_green.py). These are not attributable to Session 5 and are excluded
from this review.

### Do-Not-Modify Files

All verified clean (zero diff vs HEAD):
- `argus/strategies/base_strategy.py` -- no changes
- `argus/core/events.py` -- no changes
- `argus/strategies/pattern_strategy.py` -- no changes
- `argus/strategies/patterns/base.py` -- no changes
- Existing strategies (orb_base, orb_breakout, orb_scalp, vwap_reclaim, afternoon_momentum) -- no changes

## Review Focus Items

### 1. BullFlagPattern detect() logic: pole, flag, breakout sequence

The detection logic in `bull_flag.py` follows the correct sequence:

1. **Pole validation** (lines 107-122): Scans `pole_min_bars` candles before the flag region.
   Computes pole_low (min low), pole_high (max high), verifies move percentage >= threshold.

2. **Flag validation** (lines 124-139): Checks candles between pole and breakout. Measures
   retracement from pole_high to flag_low as a fraction of pole_height. Rejects if > max retrace.

3. **Breakout validation** (lines 141-152): Confirms breakout candle closes above flag high
   and volume meets the multiplier threshold vs average flag volume.

The shortest-flag-first iteration strategy (line 76) is a reasonable design choice -- tighter
flags are generally higher quality patterns.

**Minor observation:** On line 109, `pole_low = pole_candles[0].low` is immediately overwritten
on line 113 by `pole_low = min(c.low for c in pole_candles)`. The first assignment is dead code.
This is cosmetic and does not affect correctness.

**Verdict:** PASS -- logic is correct.

### 2. Measured move target calculation

Line 158: `target_price = entry_price + pole_height` where `entry_price = breakout_candle.close`
and `pole_height = pole_high - pole_low`. This is the standard measured move calculation for
bull flag patterns.

**Verdict:** PASS -- correct.

### 3. Score components add up sensibly (no >100 without clamp)

**`score()` method (lines 227-266):** Four components sum to a theoretical maximum of 100:
- Pole strength: 0-30 pts
- Flag tightness: 0-30 pts
- Volume profile: 0-25 pts
- Breakout quality: 0-15 pts
- Total max: 30 + 30 + 25 + 15 = 100

Each component is individually bounded by `min(x, 1.0) * weight`. Final result clamped
via `max(0.0, min(100.0, total))` on line 266.

**`_compute_confidence()` method (lines 186-225):** Uses different weights (25/25/25/25 = 100 max).
Also clamped on line 225. This is noted as a judgment call in the close-out.

**Observation:** The `tightness_score` in `_compute_confidence()` (line 213) uses
`(1.0 - retrace_pct / self._flag_max_retrace_pct)`. Since `retrace_pct` has already been
validated to be <= `flag_max_retrace_pct`, this expression ranges from 0.0 to 1.0. Correct.

However, in `score()` (line 250), if `retrace_pct` is missing from metadata, the fallback is
`self._flag_max_retrace_pct`, yielding a tightness_score of 0. This is a safe default.

**Verdict:** PASS -- no overflow possible, clamping present.

### 4. Config YAML keys match Pydantic model

The YAML file (`config/strategies/bull_flag.yaml`) contains these pattern-specific keys:
`pole_min_bars`, `pole_min_move_pct`, `flag_max_bars`, `flag_max_retrace_pct`,
`breakout_volume_multiplier`, `target_1_r`, `target_2_r`, `time_stop_minutes`.

The `BullFlagConfig(StrategyConfig)` Pydantic model in `config.py` declares the exact same
fields. The `test_config_yaml_key_validation` test confirms this programmatically by loading
the YAML and checking for unexpected keys.

The `benchmarks.min_sharpe` key (vs `min_sharpe_ratio`) is called out in the close-out as a
judgment call. The test passes, so this is accepted by the Pydantic model.

**Verdict:** PASS.

### 5. No operating window logic in pattern module

`bull_flag.py` contains zero references to time, operating windows, or market hours.
The module is pure detection logic. Operating window enforcement is handled by
`PatternBasedStrategy._is_in_entry_window()`.

**Verdict:** PASS.

## Test Results

```
33 passed in 0.03s
```

All 33 pattern tests pass:
- 8 new in `test_bull_flag.py` (detection, rejection cases, scoring, config validation)
- 3 new in `test_pattern_strategy.py` (scanner criteria, market conditions, reconstruct_state)
- 22 existing pattern tests (base + pattern_strategy)

Test count increase: +11 new tests, consistent with spec requirement.

## Regression Checklist

| # | Check | Result |
|---|-------|--------|
| R2 | BaseStrategy interface unchanged | PASS (no diff) |
| R5 | SignalEvent schema unchanged | PASS (no diff) |
| R9 | New strategy emits share_count=0 | PASS (PatternBasedStrategy.calculate_position_size returns 0) |
| R10 | Pattern strength 0-100 | PASS (score clamped) |
| R12 | BullFlagConfig YAML matches Pydantic | PASS (test_config_yaml_key_validation) |

## Escalation Criteria Check

| # | Criterion | Triggered |
|---|-----------|-----------|
| 1 | PatternModule ABC doesn't support BacktestEngine | No |
| 2 | Existing strategy tests fail | No |
| 3 | BaseStrategy interface modification required | No |
| 4 | SignalEvent schema change required | No |
| 5 | Quality Engine changes required | No |

No escalation criteria triggered.

## Findings

### LOW: Dead code assignment (line 109 of bull_flag.py)

`pole_low = pole_candles[0].low` on line 109 is immediately overwritten by
`pole_low = min(c.low for c in pole_candles)` on line 113. The first assignment
is unused dead code. No functional impact.

### LOW: Confidence vs score use different weight distributions

`_compute_confidence()` uses 25/25/25/25 weights while `score()` uses 30/30/25/15.
The close-out documents this as a judgment call. The score (30/30/25/15) matches the
spec exactly. The confidence is an internal value in PatternDetection and is not used
by the Quality Engine (which uses `score()`). Acceptable divergence.

## Verdict

**CLEAR**

All spec requirements met. Detection logic is correct (pole, flag, breakout sequence).
Measured move target calculation is standard. Score components are bounded and clamped.
Config YAML matches Pydantic model. No operating window logic in the pattern module.
11 new tests passing. No do-not-modify files touched. No escalation criteria triggered.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "severity": "LOW",
      "category": "code_quality",
      "description": "Dead code assignment on line 109 of bull_flag.py (pole_low = pole_candles[0].low immediately overwritten on line 113)",
      "recommendation": "Remove the dead assignment on line 109"
    },
    {
      "severity": "LOW",
      "category": "design",
      "description": "Confidence (25/25/25/25 weights) and score (30/30/25/15 weights) use different distributions. Score matches spec; confidence is internal only.",
      "recommendation": "Document weight rationale in code comment if this distinction is intentional"
    }
  ],
  "tests_pass": true,
  "test_count": 33,
  "new_tests": 11,
  "do_not_modify_clean": true,
  "escalation_triggered": false,
  "scope_adherence": "full"
}
```
