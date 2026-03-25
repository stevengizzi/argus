# Sprint 27.75, Session 1 — Tier 2 Review Report

---BEGIN-REVIEW---

**Session:** Sprint 27.75 S1 — Backend Log Rate-Limiting + Paper Trading Config
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-26
**Diff:** `git diff HEAD~1` (commit 0605a99)

## 1. Spec Compliance

### 1.1 ThrottledLogger (argus/utils/log_throttle.py)
**Status: PASS**

- First occurrence always emits (line 57-59: `if key not in self._state` -> immediate `self._logger.warning(message)`)
- Subsequent calls within interval are suppressed (line 64-66)
- After interval, emission includes suppressed count (lines 72-75)
- Thread-safe via `threading.Lock` (line 30)
- `reset()` method for test cleanup
- Factory function `get_throttled_logger()` provided
- 8 unit tests covering first-emit, suppression, interval expiry, key independence, suppressed count, reset, thread safety, and factory

### 1.2 IBKR Error Throttling (argus/execution/ibkr_broker.py)
**Status: PASS with note**

- Error 399: throttled per symbol, 60s interval -- correct
- Error 202: throttled per orderId, 86400s interval (effectively once) -- correct
- Error 10148: throttled per orderId, 86400s interval -- correct
- All three use early `return` before general classification

**Note:** Error 202 was previously classified as `IBKRErrorSeverity.INFO` and only logged at DEBUG level. The new code promotes it to a throttled WARNING (once per orderId). This is a behavioral change -- more visible, not less -- and is documented in the close-out. Error 202 is NOT in `_ORDER_REJECTION_CODES`, so no `OrderCancelledEvent` publication is bypassed by the early return.

Errors 399 and 10148 are not in `IBKR_ERROR_MAP`, so they previously defaulted to WARNING severity with a `log` action and no event publication. The early return preserves this behavior while adding throttling.

### 1.3 Risk Manager Throttling (argus/core/risk_manager.py)
**Status: PASS**

- Three specific `logger.warning()` calls replaced with `_throttled.warn_throttled()`:
  - `concentration_floor` (check 4.5a) -- share reduction below min risk floor
  - `cash_reserve_violated` (check 5, available <= 0)
  - `cashreserve_floor` (check 5, reduced shares below min risk floor)
- Module-level `_throttled = ThrottledLogger(logger)` -- appropriate for singleton Risk Manager
- All three are rejection paths that RETURN `OrderRejectedEvent` -- the approve/reject decision logic is unchanged; only the logging wrapper changed
- Original `logger.warning(format_string, *args)` calls converted to `_throttled.warn_throttled(key, f-string)` -- functionally equivalent

### 1.4 Reconciliation Log Consolidation (argus/execution/order_manager.py)
**Status: PASS**

- Per-symbol mismatch: `logger.warning` -> `logger.debug` (detail preserved at DEBUG)
- New consolidated summary: single `logger.warning` with count and first-3-symbols preview
- Ellipsis appended when >3 mismatches
- No WARNING emitted when synced (0 discrepancies)
- 3 tests covering all paths

### 1.5 Config Changes
**Status: PASS**

- **Risk tiers 10x reduction verified:** All 14 values (7 grades x 2 bounds) confirmed exactly 10x reduction from documented live values
- **Orchestrator throttle disabled:** `consecutive_loss_throttle: 999`, `suspension_sharpe_threshold: -999.0`, `suspension_drawdown_pct: 0.50`
- **Min position risk:** `100.0` -> `10.0` in risk_limits.yaml
- All YAML files parse correctly (verified with `yaml.safe_load`)
- All config files include comments documenting paper-trading rationale and what to restore for live trading

### 1.6 Config File Placement Deviation
**Status: ACCEPTABLE**

The close-out reports that orchestrator throttle settings and min_position_risk_dollars were placed in `config/orchestrator.yaml` and `config/risk_limits.yaml` respectively, instead of `config/system_live.yaml` as specified in the prompt. The close-out's rationale is correct -- these config files are the ones actually loaded by the respective components. Modifying system_live.yaml for these values would have had no effect.

## 2. Specification by Contradiction Checks

| Contradiction | Verified? | Evidence |
|---------------|-----------|----------|
| Strategy evaluation logic was NOT modified | YES | `git diff HEAD~1 -- argus/strategies/` produces empty output |
| Risk Manager approve/reject decisions NOT changed | YES | Only `logger.warning` -> `_throttled.warn_throttled` in 3 rejection paths; return values unchanged |
| ThrottledLogger does NOT suppress first occurrence | YES | Line 56-59: `if key not in self._state` immediately emits and returns; test `test_first_message_always_emits` confirms |
| Config files parse/validate | YES | All 4 YAML files load cleanly |

## 3. Regression Analysis

### 3.1 Test Results
- **New tests:** 15 (8 ThrottledLogger, 2 IBKR, 2 Risk Manager, 3 reconciliation)
- **Full suite:** 3,521 passed under xdist. 12 failures observed, all pre-existing:
  - 3 AI client tests (pre-existing, no ANTHROPIC_API_KEY)
  - 1 AI config test (pre-existing)
  - 1 server intelligence test (pre-existing)
  - 6 Databento data service tests (xdist-only flakes, pass in isolation)
  - 1 FMP reference test (xdist-only flake, passes in isolation)
- **Session-specific tests:** 15/15 passing

### 3.2 No Forbidden File Modifications
- `argus/strategies/` -- no changes
- `argus/ui/` -- no changes
- `argus/backtest/` -- no production code changes (only test assertions updated)
- `argus/intelligence/counterfactual*.py` -- no changes

## 4. Findings

### Finding 1: Tests Coupled to Paper-Trading Config Values (MEDIUM)

Two existing test files (`tests/backtest/test_engine_sizing.py`, `tests/core/test_config.py`) had assertions updated from production values to paper-trading values:
- `min_position_risk_dollars`: `100.0` -> `10.0`
- `risk_tiers.a_plus`: `[0.02, 0.03]` -> `[0.002, 0.003]`

These tests now assert on paper-trading values. When config is restored to live values before going live, these tests will break. The comments note "currently paper-trading" but there is no mechanism to prevent silent breakage when configs are reverted.

**Recommendation:** Consider either (a) adding a "restore for live" checklist that includes these test files, or (b) rewriting the tests to be config-value-independent (e.g., asserting that the config loads without error rather than asserting specific values).

### Finding 2: Error 202 Severity Promotion (LOW)

Error 202 ("Order Canceled - reason:") was previously logged at DEBUG level (`IBKRErrorSeverity.INFO` -> `logger.debug`). It is now logged at WARNING level (via `_throttled.warn_throttled`), throttled to once per orderId. This is a behavior change that makes the error more visible, not less. Acceptable for paper trading diagnostics but may warrant reconsideration for production if 202 events are expected/benign.

### Finding 3: ThrottledLogger Log Emission Outside Lock (LOW)

In `warn_throttled()`, lines 70-75, the actual `self._logger.warning()` call for the "interval elapsed" case happens outside the lock. This is intentionally correct -- Python's logging module is thread-safe, and emitting under the lock would risk deadlock if a logging handler tries to acquire the same lock. However, a tight race could cause two emissions for the same key if two threads both see the interval as elapsed. This is benign (one extra log message at most) and does not affect correctness.

### Finding 4: Close-Out Reports 3,528 Passed but Full Suite Shows 3,521 (LOW)

The close-out states "3,533 run, 3,528 passed, 5 failed." The review's full suite run shows 3,521 passed with 12 failed. The discrepancy is explained by xdist ordering variability -- 7 additional tests flake under xdist (all pass in isolation). The 5 pre-existing failures are a subset of the 12 observed. This is not a regression.

## 5. Verdict

All escalation criteria checked:
- [x] No existing tests fail due to this session's changes (all failures are pre-existing)
- [x] No strategy logic was modified
- [x] Risk Manager approve/reject decisions unchanged (only logging wrappers)
- [x] ThrottledLogger always emits on first occurrence

**VERDICT: CONCERNS**

The implementation is correct and complete. The single medium-severity finding (tests coupled to paper-trading config values) does not meet escalation criteria but warrants documentation for the live-trading transition checklist. All other findings are low severity.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.75",
  "session": "S1",
  "verdict": "CONCERNS",
  "findings_count": {
    "critical": 0,
    "high": 0,
    "medium": 1,
    "low": 3
  },
  "escalation_triggers": [],
  "concerns": [
    {
      "id": "F1",
      "severity": "MEDIUM",
      "summary": "Tests coupled to paper-trading config values — will break when configs restored for live trading",
      "files": ["tests/backtest/test_engine_sizing.py", "tests/core/test_config.py"],
      "recommendation": "Add these files to a live-trading restoration checklist, or rewrite tests to be config-value-independent"
    },
    {
      "id": "F2",
      "severity": "LOW",
      "summary": "Error 202 promoted from DEBUG to throttled WARNING — intentional but behavioral change",
      "files": ["argus/execution/ibkr_broker.py"],
      "recommendation": "Revisit severity for production if 202 events are expected/benign"
    },
    {
      "id": "F3",
      "severity": "LOW",
      "summary": "ThrottledLogger emits log call outside lock for interval-elapsed case — benign race possible",
      "files": ["argus/utils/log_throttle.py"],
      "recommendation": "None needed — correct design choice to avoid deadlock risk"
    },
    {
      "id": "F4",
      "severity": "LOW",
      "summary": "Close-out test count (3,528 passed) differs from review run (3,521 passed) due to xdist flakes",
      "files": [],
      "recommendation": "None — pre-existing xdist variability"
    }
  ],
  "tests_pass": true,
  "tests_pass_note": "3,521 passed under xdist; 12 failures all pre-existing (AI client/config, xdist ordering flakes)",
  "spec_compliance": "FULL",
  "config_placement_deviation": "ACCEPTABLE — orchestrator.yaml and risk_limits.yaml are the correct files for these settings"
}
```
