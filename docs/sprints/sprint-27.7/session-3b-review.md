# Sprint 27.7 Session 3b — Tier 2 Review

---BEGIN-REVIEW---

**Session:** Sprint 27.7 S3b — Startup Wiring + Event Subscriptions + EOD Task
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-25
**Close-Out Self-Assessment:** MINOR_DEVIATIONS

## 1. Spec Compliance

All Definition of Done items are satisfied:

| Requirement | Status | Notes |
|-------------|--------|-------|
| `build_counterfactual_tracker()` factory | PASS | `startup.py` — follows `build_catalyst_pipeline()` pattern |
| Tracker + store initialized in main.py | PASS | Phase 10.7, after Phase 10.5 (intraday character) |
| `_counterfactual_enabled` set True after init | PASS | Line 829, inside `if cf_result is not None:` guard |
| SignalRejectedEvent subscription | PASS | Line 833 |
| CandleEvent subscription | PASS | Line 838 |
| EOD close wired into shutdown | PASS | Line 1637, before debrief export |
| Timeout check task (60s) | PASS | `_run_counterfactual_maintenance()` |
| Retention enforcement at startup | PASS | Line 844, once-per-boot |
| counterfactual YAML sections | PASS | Both system.yaml and system_live.yaml |
| F-01 zero-R guard | PASS | Line 213 in counterfactual.py |
| >= 6 new tests | PASS | 12 new tests |

## 2. Session-Specific Review Focus

### 2.1 Handler wrapped in try/except (Focus #1)
**PASS.** `_on_signal_rejected_for_counterfactual()` (main.py:1463-1482) has the entire `tracker.track()` call inside a `try/except Exception` block that logs a warning with `exc_info=True`. Counterfactual failures cannot disrupt the signal pipeline.

### 2.2 CandleEvent short-circuit (Focus #2)
**PASS.** `on_candle()` (counterfactual.py:326-327) checks `position_ids = self._symbols_to_positions.get(event.symbol)` and returns immediately if falsy. This is a dict lookup -- O(1) -- so the hot path for ~3,000 untracked symbols is negligible.

### 2.3 `_counterfactual_enabled` only set after init (Focus #3)
**PASS.** The flag is set at main.py:829, inside the `if cf_result is not None:` block, which only executes after `build_counterfactual_tracker()` successfully returns a (tracker, store) tuple. If the factory returns None (disabled) or raises, the flag stays False.

### 2.4 EOD close called during shutdown (Focus #4)
**PASS.** `close_all_eod()` is called in two places: (a) the shutdown method at main.py:1637-1642 (with try/except), and (b) the maintenance task at main.py:1514 when market hours end. The shutdown call is the safety net. `close_all_eod()` is idempotent (iterates `self._open_positions` which is empty after first call).

### 2.5 store.close() called during shutdown (Focus #5)
**PASS.** At main.py:1734-1737, `self._counterfactual_store.close()` is called and the reference is set to None. This is step 0a1d in the shutdown sequence, after the maintenance task is cancelled (0a1c) and before evaluation store close (0a2). Correct ordering.

### 2.6 YAML config matches Pydantic model (Focus #6)
**PASS.** `CounterfactualConfig` (intelligence/config.py:234-247) has fields: `enabled: bool`, `retention_days: int`, `no_data_timeout_seconds: int`, `eod_close_time: str`. Both YAML files have exactly these four fields with matching names and compatible values.

## 3. Do-Not-Modify File Check

| Protected File | Modified? |
|---------------|-----------|
| argus/core/risk_manager.py | No |
| argus/core/regime.py | No |
| argus/data/intraday_candle_store.py | No |
| argus/core/events.py | No |
| argus/strategies/* | No |
| argus/ui/* | No |

**PASS.** No protected files were modified.

## 4. Regression Checklist

| Check | Result |
|-------|--------|
| Event bus FIFO ordering preserved | PASS — no priority changes |
| `_process_signal()` for live-mode + counterfactual disabled = identical path | PASS — `_counterfactual_enabled` defaults False, S3a code is behind guard |
| `_process_signal()` for live-mode + counterfactual enabled = identical order results | PASS — rejection events are published *after* the rejection decision, so order flow is unaffected |
| Config fields match Pydantic model names | PASS |
| CounterfactualStore uses data/counterfactual.db | PASS (hardcoded in factory) |

## 5. Test Results

Scoped test command: `python -m pytest tests/intelligence/ tests/test_signal_rejected.py -x -q`
Result: **280 passed** in 26.04s. Zero failures.

## 6. Findings

### 6.1 CONCERN (LOW): Unrelated validation JSON files in commit

The commit includes changes to `data/backtest_runs/validation/flat_top_breakout_validation.json` and `data/backtest_runs/validation/red_to_green_validation.json`. These are backtest revalidation data files unrelated to S3b scope. While they are not on the do-not-modify list and pose no functional risk, including them in the S3b commit breaks the one-logical-change-per-commit principle. This appears to be unstaged working-directory changes that were accidentally swept into the commit.

### 6.2 CONCERN (LOW): `asyncio.get_event_loop().create_task()` deprecation path

The fire-and-forget persistence calls in `track()` (line 299) and `_close_position()` (line 524) use `asyncio.get_event_loop().create_task()`. In Python 3.12+, `get_event_loop()` emits a DeprecationWarning when no running loop exists. The `try/except RuntimeError` guard handles the no-loop case, but on Python 3.12+ the warning may fire before the RuntimeError. The close-out notes this follows the EvaluationEventStore pattern, which is accurate -- this is a pre-existing pattern in the codebase, not a new antipattern. However, if the project upgrades to Python 3.12+, both sites (plus the existing EvaluationEventStore usage) should migrate to `asyncio.get_running_loop().create_task()` with a try/except for RuntimeError.

### 6.3 CONCERN (LOW): RejectionStage case mismatch between S3a and S3b

S3a publishes rejection stages as uppercase enum names (`"QUALITY_FILTER"`, `"POSITION_SIZER"`, `"RISK_MANAGER"`) while the `RejectionStage` StrEnum values are lowercase (`"quality_filter"`, etc.). The S3b handler bridges this with `.lower()` (main.py:1469). This works correctly but is a latent inconsistency. The root fix would be for S3a to publish the enum value (lowercase) rather than the enum name (uppercase), i.e. `rejection_stage=RejectionStage.QUALITY_FILTER.value` instead of `rejection_stage="QUALITY_FILTER"`. The `.lower()` bridge is acceptable for now but should be tracked for cleanup.

### 6.4 OBSERVATION: Factory uses `object` typing throughout

`build_counterfactual_tracker()` in startup.py accepts `config: object` and `candle_store: object | None` and returns `tuple[object, object] | None`. Similarly, `self._counterfactual_tracker` and `self._counterfactual_store` in main.py are typed as `object | None`. This is consistent with the duck-typing pattern used elsewhere in the codebase (e.g., `_latest_regime_vector: object | None`) and avoids circular imports. Not a concern, but noted for completeness. DEF-096 already tracks the Protocol type improvement pattern.

## 7. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| BacktestEngine regression | No — not touched |
| Fill priority disagreement | No — not touched |
| Event bus ordering violation | No — subscriptions only; no priority changes |
| Pre-existing test failure | No — 280/280 pass (scoped); close-out reports 3,466 full suite |
| `_process_signal()` behavioral change | No — rejection events publish after decision |

No escalation criteria triggered.

## 8. Verdict

**APPROVED_WITH_CONCERNS**

The implementation correctly fulfills all S3b requirements. The startup factory, event bus subscriptions, EOD close, shutdown cleanup, and YAML config are all properly wired. The handler is defensively wrapped in try/except. The CandleEvent hot path short-circuits efficiently. All 12 new tests pass and cover the critical wiring paths.

Three low-severity concerns are documented: (1) unrelated validation JSON files included in the commit, (2) `asyncio.get_event_loop()` deprecation path on Python 3.12+, and (3) RejectionStage case mismatch between S3a publishing and S3b consumption. None of these block progress to S4.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.7",
  "session": "S3b",
  "verdict": "CONCERNS",
  "verdict_display": "APPROVED_WITH_CONCERNS",
  "confidence": 0.93,
  "findings": [
    {
      "id": "F-01",
      "severity": "LOW",
      "category": "scope-hygiene",
      "summary": "Unrelated validation JSON files included in commit",
      "detail": "flat_top_breakout_validation.json and red_to_green_validation.json changes are backtest revalidation data unrelated to S3b scope.",
      "recommendation": "No action required for S3b. Future commits should use targeted git add.",
      "blocks_next_session": false
    },
    {
      "id": "F-02",
      "severity": "LOW",
      "category": "deprecation",
      "summary": "asyncio.get_event_loop().create_task() deprecation path",
      "detail": "Python 3.12+ deprecates get_event_loop() when no running loop exists. Current code handles RuntimeError but may emit DeprecationWarning first.",
      "recommendation": "Track for cleanup when upgrading to Python 3.12+. Matches existing EvaluationEventStore pattern.",
      "blocks_next_session": false
    },
    {
      "id": "F-03",
      "severity": "LOW",
      "category": "consistency",
      "summary": "RejectionStage case mismatch bridged with .lower()",
      "detail": "S3a publishes uppercase enum names, S3b consumes with .lower() bridge. Root fix: publish lowercase enum values in S3a code.",
      "recommendation": "Track for cleanup. The .lower() bridge is correct and defensive.",
      "blocks_next_session": false
    }
  ],
  "tests": {
    "command": "python -m pytest tests/intelligence/ tests/test_signal_rejected.py -x -q",
    "passed": 280,
    "failed": 0,
    "skipped": 0,
    "new_tests": 12
  },
  "do_not_modify_check": "PASS",
  "escalation_criteria_triggered": [],
  "next_session_ready": true
}
```
