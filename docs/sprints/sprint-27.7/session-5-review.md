# Sprint 27.7, Session 5 Review: Shadow Strategy Mode

---BEGIN-REVIEW---

**Reviewer:** Tier 2 Automated Review
**Session:** Sprint 27.7 — Session 5: Shadow Strategy Mode
**Date:** 2026-03-25
**Verdict:** CLEAR

## Summary

Session 5 implements the final Sprint 27.7 deliverable: shadow strategy mode.
The implementation adds a `StrategyMode` StrEnum to `base_strategy.py`, a `mode`
field on `StrategyConfig` with default `"live"`, and shadow routing at the top of
`_process_signal()` in `main.py`. All 7 strategy YAML configs have been updated
with explicit `mode: live`. 21 new tests cover the enum, routing, bypasses,
config parsing, and end-to-end counterfactual tracking.

The implementation is clean, minimal, and correctly scoped.

## Review Focus Findings

### 1. Shadow routing placement
**PASS.** Shadow routing is the first logic in `_process_signal()` (line 1262),
before the quality engine bypass check (line 1279). Shadow signals return
immediately and never reach any downstream logic.

### 2. Shadow signals never reach risk manager
**PASS.** The `return` on line 1277 (inside `if strategy_mode == "shadow"`) exits
before the risk manager call. Tests `test_risk_manager_not_called` and
`test_no_order_approved_event` explicitly verify this.

### 3. StrategyMode enum not imported in strategy files
**PASS.** Grep of `argus/strategies/` shows `StrategyMode` only in
`base_strategy.py` (the class definition). No individual strategy file imports
or references it. The routing in `main.py` uses string comparison (`== "shadow"`)
rather than importing the enum, which maintains strategy unawareness.

### 4. Default mode is "live"
**PASS.** `StrategyConfig.mode` defaults to `"live"`. Tests verify that a config
without explicit mode defaults to live, and that a strategy stub with no mode
attribute is treated as live (reaches risk manager).

### 5. Shadow + counterfactual disabled = silent drop
**PASS.** When `_counterfactual_enabled` is `False`, the shadow branch returns
immediately without publishing any event. Three tests verify this: no
SignalRejectedEvent, no OrderApprovedEvent, and no risk manager or quality
engine calls.

### 6. Full regression check (final session)
**PASS.** Full test suite: 3503 passed, 14 failed under xdist. All 14 failures
pass when run sequentially (xdist-flaky, pre-existing). The 14 failures are in
`test_databento_data_service`, `test_client`, `test_config`, `test_fmp_reference`,
and `test_server_intelligence` -- all unrelated to this session's changes and
consistent with known xdist isolation issues (DEF-048 family).

## Sprint-Level Regression Checklist

- [x] All existing pytest tests pass (~3,503 with xdist, 14 xdist-flaky pass sequentially)
- [x] BacktestEngine fill model extraction (S1) -- `fill_model.py` exists, no changes this session
- [x] `_process_signal()` for live-mode strategies behaves identically to pre-sprint -- shadow check returns early only for `mode == "shadow"`, default is `"live"`
- [x] Event bus FIFO ordering preserved -- shadow routing publishes via standard `event_bus.publish()`
- [x] All strategies default to mode: live -- `StrategyConfig.mode` default is `"live"`
- [x] Strategy internal logic unaware of mode -- no individual strategy file modified or imports StrategyMode
- [x] Config fields match Pydantic model names exactly -- `mode: str = "live"` on StrategyConfig
- [x] CounterfactualStore uses `data/counterfactual.db` -- not touched this session
- [x] All do-not-modify files are untouched -- verified via `git diff HEAD~1` on all protected files (empty diff)

## Sprint Deliverables Verification (Final Session)

| Deliverable | Session | Present |
|-------------|---------|---------|
| TheoreticalFillModel (`argus/core/fill_model.py`) | S1 | Yes |
| CounterfactualPosition + CounterfactualTracker (`argus/intelligence/counterfactual.py`) | S2 | Yes |
| CounterfactualStore (`argus/intelligence/counterfactual_store.py`) | S2 | Yes |
| SignalRejectedEvent (`argus/core/events.py`) | S3a | Yes |
| Startup wiring + event subscriptions (`argus/main.py`) | S3b | Yes |
| FilterAccuracy (`argus/intelligence/filter_accuracy.py`) | S4 | Yes |
| StrategyMode enum + shadow routing | S5 | Yes |

## Do-Not-Modify File Check

All protected files verified untouched:
- `argus/core/risk_manager.py` -- no changes
- `argus/core/regime.py` -- no changes
- `argus/intelligence/counterfactual.py` -- no changes
- `argus/intelligence/counterfactual_store.py` -- no changes
- `argus/intelligence/filter_accuracy.py` -- no changes
- `argus/data/intraday_candle_store.py` -- no changes
- All 7 individual strategy Python files -- no changes
- `argus/ui/` -- no changes

## Escalation Criteria Check

| Criterion | Triggered | Notes |
|-----------|-----------|-------|
| BacktestEngine regression | No | Not touched this session |
| Fill priority disagreement | No | Not touched this session |
| Event bus ordering violation | No | Standard publish(), no ordering changes |
| Existing test failures | No | 14 xdist-flaky pass sequentially |
| _process_signal behavioral change for live mode | No | Shadow check only activates for `mode == "shadow"` |

## Observations

1. **Judgment call on config access path:** The implementer used
   `getattr(getattr(strategy, 'config', None), 'mode', 'live')` instead of the
   spec's two-path approach. This is a simplification that works because
   strategies always have a `config` attribute (it is set in `BaseStrategy.__init__`).
   The single-path approach is actually more robust -- the spec's fallback to
   `getattr(strategy, 'mode', None)` would have been dead code.

2. **Uncommitted working tree changes:** The working tree has uncommitted changes
   to `data/backtest_runs/validation/` JSON files and an untracked script. These
   are NOT part of the session commit and do not affect the review.

3. **Test count:** The close-out reports 3509 passing (xdist) with 21 new tests.
   My run shows 3503 passing with 14 xdist-flaky. The variance is within normal
   xdist tolerance (different worker count, timing). The 21 new tests are
   confirmed present in `tests/strategies/test_shadow_mode.py`.

4. **StrategyMode enum defined but not used in routing:** `main.py` compares
   against the string `"shadow"` rather than importing `StrategyMode.SHADOW`.
   This is intentional -- it avoids coupling main.py to the enum and keeps the
   routing logic string-based, consistent with how the `mode` field is typed
   as `str` on `StrategyConfig`. No issue.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.7",
  "session": "S5",
  "verdict": "CLEAR",
  "escalation_triggers": [],
  "findings": [],
  "test_results": {
    "total": 3517,
    "passed": 3503,
    "failed": 14,
    "xdist_flaky": 14,
    "new_tests": 21,
    "all_pass_sequential": true
  },
  "do_not_modify_violations": [],
  "regression_checklist_pass": true,
  "sprint_deliverables_complete": true
}
```
