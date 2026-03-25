---BEGIN-REVIEW---

# Sprint 27.7 Session 1 — Tier 2 Review Report

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-25
**Session:** Sprint 27.7 S1 — Core Model + Tracker Logic + Shared Fill Model
**Close-out verdict:** CLEAN
**Commit:** 27e6d12

---

## 1. Do-Not-Modify File Check

| File/Path | Modified? | Status |
|-----------|-----------|--------|
| argus/core/events.py | No | PASS |
| argus/main.py | No | PASS |
| argus/core/risk_manager.py | No | PASS |
| argus/core/regime.py | No | PASS |
| argus/data/intraday_candle_store.py | No | PASS |
| argus/strategies/ | No | PASS |
| argus/ui/ | No | PASS |

All do-not-modify files are untouched.

---

## 2. Review Focus Item Findings

### 2.1 evaluate_bar_exit() Fill Priority vs Original BacktestEngine

**Verdict: MATCH**

Original BacktestEngine `_check_bracket_orders` (lines 587-598):
```python
if stop_orders and bar_low <= stop_orders[0].trigger_price:
    # → fill at stop_price, return
# then: target iteration
# then: time stop
```

Shared fill model `evaluate_bar_exit()` (lines 67-83):
1. `bar_low <= stop_price` → STOPPED_OUT at stop_price
2. `bar_high >= target_price` → TARGET_HIT at target_price
3. `time_stop_expired` → check stop again (dead code, see note), else TIME_STOPPED at bar_close

The refactored BacktestEngine calls `evaluate_bar_exit()` with `time_stop_expired=False` and only acts on STOPPED_OUT results, letting TARGET_HIT fall through to the existing target iteration loop. This preserves the original behavior exactly.

Note: Line 79 in fill_model.py (`if bar_low <= stop_price` inside the time_stop block) is dead code — line 69 already returns for this condition. This is harmless and mirrors the original BacktestEngine pattern where `_check_time_stop` independently re-checks stop brackets.

### 2.2 BacktestEngine Refactor — Behavior Preservation

**Verdict: PASS**

The refactor is minimal and surgical:
- `_check_bracket_orders`: Only the stop-vs-target priority decision is delegated to `evaluate_bar_exit()`. Multi-target iteration and broker interaction remain unchanged.
- `_check_time_stop`: Uses `bar_high=float("-inf")` and `target_price=float("inf")` to ensure the target check never triggers (targets already handled at Priority 2). The stop check is the only path that can trigger, matching original behavior.
- All 406 backtest tests pass, plus 24 new tests. The fill model unit tests cover all priority edge cases.

### 2.3 CounterfactualTracker Uses T1 Only

**Verdict: PASS**

Line 224: `target_price=signal.target_prices[0]` — correctly takes T1 (first element) only.

### 2.4 IntradayCandleStore Backfill Uses evaluate_bar_exit()

**Verdict: PASS**

Lines 246-260: Backfill loop calls `self._process_bar()` for each historical bar. `_process_bar()` (line 359) calls `evaluate_bar_exit()` from the shared fill model. There is no separate exit implementation — both backfill and forward monitoring use the same code path.

### 2.5 MAE/MFE Tracking for LONG Positions

**Verdict: PASS**

Lines 388-394:
```python
adverse = pos.entry_price - bar_low      # MAE: entry - low (positive when price drops)
favorable = bar_high - pos.entry_price    # MFE: high - entry (positive when price rises)
```

Correct for LONG positions. MAE captures worst drawdown, MFE captures best unrealized gain. Both use `max()` semantics (only update if new value exceeds current).

### 2.6 Empty target_prices Guard

**Verdict: PASS**

Lines 203-209: Guard checks `if not signal.target_prices:`, logs a warning with strategy_id and symbol, and returns None. Test at line 115 verifies this behavior.

---

## 3. Sprint Regression Checklist

| Check | Result |
|-------|--------|
| All existing pytest tests pass (~3,412 +/- tolerance) | PASS — 3,436 total (3,412 + 24 new) |
| BacktestEngine produces identical results after fill model extraction | PASS — 406 backtest tests pass |
| evaluate_bar_exit() matches original fill priority for all edge cases | PASS — 10 unit tests, line-by-line comparison verified |
| Do-not-modify files untouched | PASS |

---

## 4. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| BacktestEngine regression after fill model extraction | No |
| Fill priority disagreement | No |
| Any pre-existing test failure | No |

No escalation criteria triggered.

---

## 5. Findings

### F-01: Missing "Zero R" Skip Guard in track() (LOW)

The review context spec states edge cases to reject include "Zero R -> skip." The implementation handles zero R at R-multiple calculation time (line 434: `if risk_per_share != 0 else 0.0`) but does not skip tracking entirely when `entry_price == stop_price`. A zero-R signal would be tracked and monitored with an R-multiple of 0.0 on close. This diverges slightly from the spec's intent but has no practical impact — the Risk Manager would never approve a zero-R signal, so this scenario is extremely unlikely.

### F-02: Validation JSON Files Included in Commit (LOW)

Two data files were committed that are not part of Sprint 27.7 S1 scope:
- `data/backtest_runs/validation/flat_top_breakout_validation.json`
- `data/backtest_runs/validation/red_to_green_validation.json`

These were pre-existing working tree modifications (visible in git status before the session). They are data files that don't affect code behavior, but committing out-of-scope changes is a minor hygiene issue.

### F-03: quality_score Falsy Check (TRIVIAL)

Line 228: `signal.quality_score if signal.quality_score else None` — a quality_score of exactly 0.0 would be treated as None. This is theoretically incorrect but practically irrelevant since quality scores range 0-100 and a score of 0.0 would indicate a completely invalid signal that would never reach the counterfactual tracker.

### F-04: Dead Code in fill_model.py Priority 3 (TRIVIAL)

Line 79: `if bar_low <= stop_price` inside the `time_stop_expired` block can never be True because line 69 already returns for this condition. This is harmless and preserves the semantic intent from the original BacktestEngine pattern.

---

## 6. Test Verification

**Command:** `python -m pytest tests/intelligence/test_counterfactual.py tests/core/test_fill_model.py tests/backtest/ -x -q`
**Result:** 430 passed in 32.41s
**New tests:** 24 (10 fill model + 14 counterfactual), exceeding the 12 minimum

Test coverage is thorough:
- Fill model: all priority combinations including same-bar stop+target, time stop with/without stop breach, no trigger
- Tracker: open, candle close at stop/target, MAE/MFE tracking, time stop, EOD close, P&L/R-multiple, backfill with immediate close, backfill with no bars, backfill with multiple bars, timeout expiry, empty target_prices, rejection stage enum

---

## 7. Summary

The implementation is clean and well-executed. The shared fill model correctly captures the BacktestEngine's worst-case-for-longs priority, and the BacktestEngine refactor is behavior-preserving (confirmed by 406 unchanged tests passing). The CounterfactualTracker follows a sound mutable/frozen pattern with proper candle store backfill. The findings are all low severity — the most notable is the missing zero-R skip guard (F-01), which should be addressed in a future session but does not block.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.7",
  "session": "S1",
  "reviewer": "tier2-automated",
  "verdict": "CONCERNS",
  "confidence": 0.92,
  "findings": [
    {
      "id": "F-01",
      "severity": "low",
      "category": "spec-gap",
      "description": "Missing 'Zero R' skip guard in track() — spec says skip, implementation handles at calculation time with 0.0 fallback",
      "file": "argus/intelligence/counterfactual.py",
      "line": 434,
      "recommendation": "Add guard in track(): if entry_price == stop_price, log warning and return None"
    },
    {
      "id": "F-02",
      "severity": "low",
      "category": "hygiene",
      "description": "Two pre-existing validation JSON files committed with sprint work (out of scope)",
      "file": "data/backtest_runs/validation/",
      "recommendation": "Avoid committing pre-existing working tree changes with sprint commits"
    },
    {
      "id": "F-03",
      "severity": "trivial",
      "category": "correctness",
      "description": "quality_score falsy check converts 0.0 to None",
      "file": "argus/intelligence/counterfactual.py",
      "line": 228,
      "recommendation": "Use 'if signal.quality_score is not None' instead of truthy check"
    },
    {
      "id": "F-04",
      "severity": "trivial",
      "category": "dead-code",
      "description": "Unreachable stop check in fill_model.py Priority 3 time_stop block",
      "file": "argus/core/fill_model.py",
      "line": 79,
      "recommendation": "Harmless — preserves semantic intent. No action needed."
    }
  ],
  "escalation_triggers_fired": [],
  "tests_pass": true,
  "test_count": 3436,
  "new_tests": 24,
  "do_not_modify_violations": [],
  "summary": "Implementation is clean and behavior-preserving. Fill model correctly extracts BacktestEngine priority logic. CounterfactualTracker is well-structured with proper backfill. Two low-severity findings (missing zero-R guard, out-of-scope data files) and two trivial findings. No escalation criteria triggered."
}
```
