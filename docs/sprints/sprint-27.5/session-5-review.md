---BEGIN-REVIEW---

# Sprint 27.5 Session 5 — Tier 2 Review
**Reviewer:** Automated (Tier 2)
**Date:** 2026-03-24
**Session:** S5 — Slippage Model Calibration

## Verdict: CONCERNS

## Summary

Session S5 implements the slippage model calibration module (`argus/analytics/slippage_model.py`) and its test suite (8 tests). The implementation matches the spec precisely: `SlippageConfidence` enum, `StrategySlippageModel` dataclass with serialization, `calibrate_slippage_model()` async function, atomic file save/load, and pure-Python linear regression. No existing files were modified. All 8 new tests pass. Full suite shows 3,136 passing + 1 pre-existing failure (sprint_runner notification test, confirmed pre-existing on clean HEAD).

One medium-severity data integrity concern was identified regarding time-of-day bucketing.

## Session-Specific Review Focus Results

### 1. DB query matches actual `execution_records` table column names
**PASS.** The SQL query in `calibrate_slippage_model()` selects `actual_slippage_bps`, `time_of_day`, `order_size_shares` filtered by `strategy_id`. All four column names match the schema in `argus/db/schema.sql` (lines 353-370) and the `ExecutionRecord` dataclass in `argus/execution/execution_record.py`.

### 2. Time-of-day bucketing uses ET (Eastern Time), not UTC
**CONCERN.** The slippage model's `_time_bucket()` function correctly documents and treats the `time_of_day` column as Eastern Time (per DEC-061). However, the upstream data producer (`create_execution_record()` in `execution_record.py`, line 86) computes `time_of_day = fill_timestamp.strftime("%H:%M:%S")` where `fill_timestamp` comes from `self._clock.now()` in `order_manager.py` (line 578), which returns UTC. This means the stored `time_of_day` values are actually UTC, not ET.

This is a **pre-existing data integrity issue** in `execution_record.py`, not in the slippage model itself. The slippage model's assumption is architecturally correct per DEC-061, but the data it consumes is stored in the wrong timezone. When real execution records accumulate and calibration runs, morning trades (9:30-10:00 ET) would appear as afternoon trades (14:30-15:00 UTC), causing incorrect time-of-day adjustments.

**Impact:** The slippage model code is correct in its assumptions. The upstream bug is outside session scope (execution_record.py is a "do not modify" file). This should be logged as a deferred item for correction before live slippage calibration is relied upon.

### 3. Linear regression is correct
**PASS.** The `_linear_regression_slope()` function (lines 84-109) correctly implements the least-squares formula: `slope = sum((xi - x_mean) * (yi - y_mean)) / sum((xi - x_mean)^2)`. Guards against `n < 2` and zero denominator are present. The test `test_size_adjustment_slope` validates slope accuracy to within 0.01.

### 4. Atomic file write (temp file then rename)
**PASS.** `save_slippage_model()` (lines 301-324) uses `tempfile.NamedTemporaryFile` with `delete=False` in the same directory as the target, writes the JSON, then uses `Path.rename()` for an atomic move. This is the correct pattern for POSIX atomic writes.

### 5. <5 records returns a valid (zeroed) model, not an error
**PASS.** The `_zeroed_model()` helper (lines 213-232) returns a complete `StrategySlippageModel` with all-zero values and `INSUFFICIENT` confidence. Called at line 259 when `sample_count < 5`. Verified by `test_calibrate_insufficient_records`.

### 6. No numpy dependency added
**PASS.** No numpy import in the module. All math uses pure Python (`sum()`, list comprehensions, `** 0.5` for square root).

## Sprint-Level Regression Checklist
- [x] Full pytest suite passes (3,136 passed; 1 failure is pre-existing in `test_notifications.py`, confirmed by running on clean HEAD)
- [x] No existing file modifications (git diff HEAD shows no changes; all S5 work is committed)

## Scope Creep Check
- No calibration scheduling or auto-refresh added. No scope creep detected.

## Findings

### F-001: Pre-existing UTC/ET mismatch in execution_record.py (MEDIUM)
- **Location:** `argus/execution/execution_record.py`, line 86
- **Issue:** `time_of_day` stored as UTC, but slippage model (and DEC-061) assumes ET
- **Impact:** Time-of-day adjustments will be incorrect when calibration runs against real data
- **Recommendation:** Log as deferred item. Before S6 integration wiring or before live calibration, `execution_record.py` should convert `fill_timestamp` to ET before `strftime`. This is outside S5 scope (protected file).

### F-002: Population vs sample std dev (INFORMATIONAL)
- **Location:** `argus/analytics/slippage_model.py`, line 80
- **Detail:** Uses population std dev (divides by N, not N-1). Close-out correctly documents this as intentional for calibration purposes. Acceptable for a descriptive model of observed spread.

### F-003: Pre-existing test failure (INFORMATIONAL)
- **Test:** `tests/sprint_runner/test_notifications.py::TestReminderEscalation::test_check_reminder_sends_after_interval`
- **Status:** Pre-existing. Fails on clean HEAD (no stash needed, no uncommitted changes). Not introduced by this session.

## Code Quality Assessment
The implementation is clean, well-structured, and follows project conventions:
- Complete type hints on all functions
- Google-style docstrings on all public interfaces
- Proper use of `__all__` exports
- No circular imports (only imports `argus.db.manager`)
- Pathlib for file operations
- Logging via `logging.getLogger(__name__)`

## Conclusion
Implementation matches spec exactly. The only concern (F-001) is a pre-existing upstream data issue that the slippage model correctly handles per architectural rules but that will produce incorrect results when fed real data. This should be tracked as a deferred item before live calibration is relied upon.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.5",
  "session": "S5",
  "verdict": "CONCERNS",
  "findings": [
    {
      "id": "F-001",
      "severity": "MEDIUM",
      "category": "data_integrity",
      "summary": "Pre-existing UTC/ET mismatch: execution_record.py stores time_of_day in UTC but slippage model assumes ET per DEC-061",
      "recommendation": "Log as deferred item. Fix in execution_record.py before live calibration is relied upon.",
      "blocked_by_scope": true
    },
    {
      "id": "F-002",
      "severity": "INFORMATIONAL",
      "category": "design_choice",
      "summary": "Population std dev (N divisor) used instead of sample std dev (N-1). Documented as intentional."
    },
    {
      "id": "F-003",
      "severity": "INFORMATIONAL",
      "category": "pre_existing",
      "summary": "test_notifications.py reminder escalation test fails on clean HEAD. Not introduced by this session."
    }
  ],
  "tests": {
    "scoped_pass": true,
    "scoped_count": 8,
    "full_suite_pass": false,
    "full_suite_total": 3137,
    "full_suite_passed": 3136,
    "full_suite_failed": 1,
    "full_suite_failure_preexisting": true
  },
  "regression_checklist": {
    "all_pass": true,
    "no_existing_file_modifications": true
  },
  "escalation_criteria_triggered": false,
  "scope_creep_detected": false
}
```
