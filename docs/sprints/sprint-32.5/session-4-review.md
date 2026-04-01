---BEGIN-REVIEW---

# Sprint 32.5, Session 4 — Tier 2 Review

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-01
**Session:** Sprint 32.5 S4 — DEF-134 Reference-Data Patterns (gap_and_go, premarket_high_break)
**Diff:** `git diff 96f4c33...66e0817` (S4-only: 5 files, +719 lines)
**Branch:** sprint-32.5-session-4

---

## 1. Scope Verification

### Files Modified (S4 only)
| File | Change | In Spec? |
|------|--------|----------|
| `argus/backtest/config.py` | +2 enum values (GAP_AND_GO, PREMARKET_HIGH_BREAK) | Yes |
| `argus/backtest/engine.py` | +156 lines: 2 factory methods, `_derive_prior_closes()`, `_supply_daily_reference_data()`, wiring in `_run_trading_day()` | Yes |
| `argus/intelligence/experiments/runner.py` | +4 lines: 2 mapping entries in `_PATTERN_TO_STRATEGY_TYPE` | Yes |
| `tests/backtest/test_engine_refdata_patterns.py` | +481 lines: 21 new tests | Yes (spec: 8+ tests) |
| `docs/sprints/sprint-32.5/session-4-closeout.md` | Close-out report | Yes |

### Files NOT Modified (verified clean)
All 7 protected files confirmed unmodified via `git diff`:
- `argus/strategies/patterns/gap_and_go.py` -- clean
- `argus/strategies/patterns/premarket_high_break.py` -- clean
- `argus/strategies/patterns/base.py` -- clean
- `argus/strategies/pattern_strategy.py` -- clean
- `argus/backtest/historical_data_feed.py` -- clean
- `argus/core/sync_event_bus.py` -- clean
- `argus/core/fill_model.py` -- clean

### Scope Assessment
All changes are strictly within spec scope. No out-of-scope modifications detected. Reference data mechanism is localized entirely within `backtest_engine.py` -- no Tier 3 escalation trigger.

---

## 2. Session-Specific Review Focus

### F1: Reference data derivation localized within backtest_engine.py
**PASS.** Both `_derive_prior_closes()` and `_supply_daily_reference_data()` are private methods on `BacktestEngine`. No other production files were modified for this mechanism. The only other changes are enum additions (config.py) and mapping entries (runner.py), which are expected wiring.

### F2: Prior close uses last bar close of previous day
**PASS.** `_derive_prior_closes()` at engine.py:1512 uses `prior_df.iloc[-1]["close"]` -- the last bar of the previous trading day. This is the correct definition of prior close (final 1-minute bar's close, which is the settlement close).

### F3: PM high timezone handling
**PASS.** BacktestEngine does NOT derive PM high itself. `PreMarketHighBreakPattern._split_pm_and_market()` at premarket_high_break.py:130 converts timestamps to ET via `candle.timestamp.astimezone(_ET).time()` before comparing against 9:30 AM. This is correct per DEC-061. The close-out report correctly documents this judgment call -- the spec assumed BacktestEngine would supply PM high, but the pattern already handles it internally.

### F4: First-day skip does not skip ALL days
**PASS.** `_derive_prior_closes()` uses `self._trading_days.index(trading_day)` to find the current day's position. Only `day_idx == 0` returns empty. Days 1+ correctly find `self._trading_days[day_idx - 1]`. No off-by-one risk. Tested by `test_derive_prior_closes_first_day_returns_empty` and `test_derive_prior_closes_two_days`.

### F5: Non-reference-data patterns unaffected
**PASS.** `_supply_daily_reference_data()` guards with `isinstance(self._strategy, PatternBasedStrategy)` and returns early for non-pattern strategies (ORB, VWAP, etc.). For pattern-based strategies that don't override `set_reference_data()`, the base no-op consumes the call harmlessly. Tested by `test_non_pattern_strategy_supply_reference_data_is_noop`.

### F6: All 7 patterns have mapping entries
**PASS.** `_PATTERN_TO_STRATEGY_TYPE` now contains: bull_flag, flat_top_breakout, dip_and_rip, hod_break, abcd, gap_and_go, premarket_high_break. All 7 present.

---

## 3. Sprint-Level Regression Checklist

| Check | Result |
|-------|--------|
| bull_flag backtest unchanged | PASS -- no changes to bull_flag factory or logic; regression test `test_runner_bull_flag_mapping_unchanged` passes |
| flat_top_breakout backtest unchanged | PASS -- same reasoning; regression test passes |
| dip_and_rip, hod_break, abcd entries from S3 | PASS -- S3 factory methods untouched; mapping regression tests pass |
| risk_overrides behavior unchanged | PASS -- `_apply_config_overrides()` not modified |
| compute_parameter_fingerprint() unchanged | PASS -- factory.py has zero diff in S4 |
| experiments.enabled=false features disabled | PASS -- no config gating changes in S4 |

---

## 4. Escalation Criteria Evaluation

| Trigger | Triggered? |
|---------|-----------|
| Reference data requires changes beyond backtest_engine.py | NO -- fully localized |
| Fingerprint backward incompatibility | NO -- factory.py untouched |

---

## 5. Test Results

```
tests/intelligence/experiments/ + tests/backtest/
555 passed, 3 warnings in 25.32s
```

21 new tests in `test_engine_refdata_patterns.py`, all passing. Test coverage is thorough: enum membership, runner mappings, factory construction, prior close derivation (2-day, first-day, missing symbol), reference data supply (happy path, first day), PM high detection (with PM candles, without PM candles), non-pattern strategy no-op, and 5 regression mapping checks. Exceeds the 8-test minimum by 2.6x.

---

## 6. Findings

### F1 (LOW): Private attribute access `self._strategy._pattern`
`_supply_daily_reference_data()` at engine.py:1544 accesses `self._strategy._pattern` which is a private attribute of `PatternBasedStrategy`. The public alternative `initialize_reference_data()` accepts `dict[str, SymbolReferenceData]` (Universe Manager format), not the raw `dict[str, float]` format that BacktestEngine produces. The implementation correctly avoids modifying `pattern_strategy.py` (per spec constraints), making the private access the pragmatic choice. This is consistent with existing patterns in tests (e.g., `test_engine_new_patterns.py` also accesses `_pattern`). Noting for documentation purposes only -- no action needed.

### F2 (LOW): `set_reference_data()` called even with empty dict on first day
On the first trading day, `_supply_daily_reference_data()` calls `set_reference_data({"prior_closes": {}})` rather than skipping the call. This is correct behavior -- patterns like GapAndGoPattern handle empty `_prior_closes` gracefully by returning `None` from `detect()`. The DEBUG log message accurately warns that reference-data patterns will skip detection.

---

## 7. Close-Out Report Assessment

The close-out report is accurate and complete. Self-assessment of CLEAN is justified. The judgment calls section correctly documents two deviations from the spec's assumptions:
1. PM high is handled internally by the pattern, not supplied by BacktestEngine.
2. Private attribute access to `_pattern` is pragmatic given spec constraints.

Context state GREEN is appropriate for this focused session.

---

## 8. Verdict

**CLEAR** -- All acceptance criteria met. Reference data mechanism is correctly localized, prior close derivation is sound, PM high delegation to the pattern is the right architectural call, first-day handling is safe, and all 7 patterns are fully wired. No regressions detected. No escalation triggers.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": "high",
  "findings": [
    {
      "id": "F1",
      "severity": "low",
      "category": "encapsulation",
      "file": "argus/backtest/engine.py",
      "line": 1544,
      "description": "Private attribute access self._strategy._pattern to call set_reference_data(). Pragmatic given constraint not to modify pattern_strategy.py. Consistent with existing test patterns.",
      "action": "none"
    },
    {
      "id": "F2",
      "severity": "low",
      "category": "defensive-coding",
      "file": "argus/backtest/engine.py",
      "line": 1544,
      "description": "set_reference_data() called with empty dict on first day rather than skipped. Correct behavior — patterns handle empty prior_closes gracefully.",
      "action": "none"
    }
  ],
  "escalation_triggers_checked": [
    "reference_data_beyond_engine: NO",
    "fingerprint_backward_incompatibility: NO"
  ],
  "tests": {
    "command": "python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q",
    "result": "555 passed, 3 warnings in 25.32s",
    "new_tests": 21
  },
  "scope_adherence": "strict",
  "close_out_accurate": true,
  "session": "sprint-32.5-session-4",
  "reviewer": "tier-2-automated"
}
```
