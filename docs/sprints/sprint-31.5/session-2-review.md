---BEGIN-REVIEW---

# Sprint 31.5, Session 2 — Tier 2 Review

**Reviewer:** Tier 2 Automated Review (Opus 4.6)
**Date:** 2026-04-03
**Session objective:** DEF-146 — Move universe filtering into ExperimentRunner
**Close-out self-assessment:** CLEAN
**Close-out context state:** GREEN

---

## Verdict: CLEAR

The session correctly implements DEF-146. Universe filtering logic is moved from
the CLI script into `ExperimentRunner._resolve_universe_symbols()`, the CLI
delegates to the runner via the new `universe_filter` parameter, the
HistoricalQueryService connection is closed in a `try/finally` block, and all
backward compatibility is preserved. Six well-structured tests cover the new
functionality. All 4,837 pytest tests pass. No forbidden files were modified.

---

## Escalation Criteria Check

| # | Criterion | Result |
|---|-----------|--------|
| 1 | HistoricalQueryService connection leaked (no close() in finally) | **NOT TRIGGERED** -- `service.close()` is in a `finally` block (runner.py L784-785). Test 5 asserts `service.close.assert_called_once()`. |
| 2 | `_apply_universe_filter()` or `_validate_coverage()` removed from `scripts/run_experiment.py` | **NOT TRIGGERED** -- Both functions remain at lines 203 and 284. Only the inline *calls* in `run()` were removed; the standalone functions are preserved. |
| 3 | Any DO NOT MODIFY files changed | **NOT TRIGGERED** -- `git diff HEAD~2 HEAD` shows zero changes to `argus/data/historical_query_service.py`, `argus/intelligence/experiments/store.py`, `argus/backtest/engine.py`, `argus/core/config.py`, any frontend files, or any strategy files. |
| 4 | Test count delta exceeds +10 or -5 from expected +6 | **NOT TRIGGERED** -- Delta is exactly +6 (scoped: 115 to 121; full: 4,831 to 4,837). |
| 5 | `run_sweep()` signature no longer backward-compatible | **NOT TRIGGERED** -- New parameter `universe_filter` has default `None`. All existing parameters retain their positions and defaults. |

---

## Session-Specific Review Focus

### Focus 1: HistoricalQueryService closed after use (try/finally)

**PASS.** `_resolve_universe_symbols()` constructs the service at L707-709,
checks availability at L711-714 (raises ValueError if unavailable -- note the
service is NOT closed in this early-return path, but `HistoricalQueryService`
with `is_available=False` means no DuckDB connection was opened, so no resource
leak), then enters `try` at L716 with `finally: service.close()` at L784-785.
All filter logic, query execution, and coverage validation occur inside the
`try` block. Test 5 explicitly asserts `service.close.assert_called_once()`.

### Focus 2: Dynamic filter fields logged as skipped

**PASS.** Lines 718-725 iterate over `_DYNAMIC_FILTER_FIELDS` (8 fields) and
log a WARNING for each non-empty value. The `getattr(universe_filter,
field_name, None)` safely handles fields that might not exist on the config
model (though all 8 are valid fields today). The logic matches the CLI pattern
exactly.

### Focus 3: CLI works identically when --universe-filter is NOT passed

**PASS.** When `args.universe_filter` is `None`, `filter_name` remains `None`,
the `if filter_name is not None` block at L429 is skipped, `filter_config`
stays `None`, and `run_sweep()` receives `universe_filter=None`. The
`if universe_filter is not None` guard in `run_sweep()` (L373) skips the
filtering path entirely. The `symbols` variable passes through unchanged
(either `None` for auto-detect or the user-supplied list from `--symbols`).

### Focus 4: Intersection logic (both symbols and universe_filter)

**PASS.** In `run_sweep()` at L374, when `universe_filter is not None`, the
existing `symbols` value (which may be a user-supplied list) is passed as
`candidate_symbols` to `_resolve_universe_symbols()`. Inside that method
(L728-731), when `candidate_symbols is not None`, it is used as `all_symbols`
directly (restricting the SQL query via `IN (?)` clause). When
`candidate_symbols is None`, `get_available_symbols()` provides all cache
symbols. Test 2 verifies the `candidate_symbols` argument is passed correctly.

### Focus 5: No circular imports from UniverseFilterConfig

**PASS.** `UniverseFilterConfig` is imported under `TYPE_CHECKING` (L32-33),
and `from __future__ import annotations` (L11) ensures the string annotation
`UniverseFilterConfig | None` works at runtime without the actual import. The
lazy import of `HistoricalQueryService` and `HistoricalQueryConfig` inside
`_resolve_universe_symbols()` (L704-705) avoids loading DuckDB at module
import time.

### Focus 6: run_sweep() signature backward compatibility

**PASS.** The new `universe_filter` parameter is the last keyword argument with
default `None`. All 8 preceding parameters retain their names, positions, and
defaults. Any caller using the pre-session signature will work identically.

---

## Regression Checklist

| # | Check | Result |
|---|-------|--------|
| 1 | Sequential identical to current | **PASS** -- `run_sweep(workers=1)` tests pass; no changes to sequential path when `universe_filter=None`. |
| 4 | CLI unchanged without new flags | **PASS** -- `--pattern X --dry-run` path is unmodified when `filter_config is None`. |
| 8 | DEF-146 filtering matches CLI filtering | **PASS** -- Same SQL HAVING clauses (AVG(close)/AVG(volume)), same `validate_symbol_coverage()` call with `min_bars=100`, same `_DYNAMIC_FILTER_FIELDS` tuple (8 fields, identical ordering). |
| 9 | 4,831+ pytest pass | **PASS** -- 4,837 passed, 0 failures. |
| 11 | Existing experiment tests pass | **PASS** -- 121 scoped tests pass (115 pre-existing + 6 new). |
| 12 | Existing CLI flags work | **PASS** -- `--symbols`, `--universe-filter`, `--date-range`, `--pattern`, `--dry-run`, `--params` all preserved. `_apply_universe_filter` and `_validate_coverage` remain as standalone utilities. |

---

## Findings

### F1 (MINOR): Service not closed on early ValueError for unavailable service

In `_resolve_universe_symbols()`, when `service.is_available` is `False`
(L711-714), the method raises `ValueError` before entering the `try/finally`
block. This means `service.close()` is not called. In practice, a service with
`is_available=False` has not opened a DuckDB connection, so there is no resource
to leak. However, defensively moving the `is_available` check inside the `try`
block would be marginally safer if the service constructor ever acquires
resources before the `is_available` check.

**Severity:** MINOR
**Impact:** None in practice. DuckDB connection is not opened when cache is
missing.

### F2 (MINOR): SQL injection surface in HAVING clause uses operator-controlled config values

The HAVING clause at L743-748 interpolates `universe_filter.min_price`,
`.max_price`, and `.min_avg_volume` directly into SQL strings (e.g.,
`f"AVG(close) >= {universe_filter.min_price}"`). These values come from
Pydantic-validated `float | None` fields in `UniverseFilterConfig`, loaded from
operator-controlled YAML files (not user input). The Pydantic validation
ensures these are always floats, eliminating injection risk. The `WHERE` clause
correctly uses parameterized queries for date and symbol values. This is
acceptable given the trust boundary (operator config), but using parameterized
queries for the HAVING values would be more defensively consistent.

**Severity:** MINOR
**Impact:** None. Values are Pydantic-validated floats from operator YAML.

### F3 (MINOR): Test 4 patches at module level, not at import site

`test_run_sweep_universe_filter_service_unavailable_raises` patches
`argus.data.historical_query_service.HistoricalQueryService` rather than the
import site within the runner module. Because the runner uses a lazy import
(`from argus.data.historical_query_service import HistoricalQueryService`), and
the patch replaces the class on the source module before the import executes,
this works correctly. However, it relies on the import not being cached from a
previous test. The test passes reliably (121/121), but the pattern is fragile
if test ordering changes. Test 5 (`test_resolve_universe_symbols_static_filters`)
uses the same pattern and also works. Both tests pass consistently, so this is
informational.

**Severity:** MINOR
**Impact:** None currently. Tests pass consistently.

---

## Test Results

```
Scoped:  121 passed in 0.50s
Full:    4837 passed, 63 warnings in 177.79s
```

---

## Summary

Session 2 delivers a clean implementation of DEF-146. The universe filtering
logic is correctly moved into `ExperimentRunner._resolve_universe_symbols()`
with proper resource cleanup, dynamic filter logging, backward-compatible API
design, and the TYPE_CHECKING guard for the import. The CLI correctly delegates
to the runner while preserving its standalone utility functions. All three
minor findings are informational with no practical impact.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "Sprint 31.5, Session 2",
  "reviewer": "Tier 2 Automated Review (Opus 4.6)",
  "date": "2026-04-03",
  "escalation_triggered": false,
  "findings": [
    {
      "id": "F1",
      "severity": "MINOR",
      "title": "Service not closed on early ValueError for unavailable service",
      "description": "ValueError raised before try/finally when is_available=False. No actual resource leak since DuckDB connection is not opened."
    },
    {
      "id": "F2",
      "severity": "MINOR",
      "title": "SQL HAVING clause uses string interpolation for operator-controlled floats",
      "description": "min_price/max_price/min_avg_volume interpolated into SQL. Safe because values are Pydantic-validated floats from operator YAML, not user input."
    },
    {
      "id": "F3",
      "severity": "MINOR",
      "title": "Test patches at module level rather than import site",
      "description": "Tests 4 and 5 patch HistoricalQueryService on the source module. Works due to lazy import pattern but is fragile if import caching changes."
    }
  ],
  "test_results": {
    "scoped": "121 passed",
    "full_suite": "4837 passed",
    "failures": 0
  },
  "regression_checklist": {
    "items_checked": 6,
    "items_passed": 6,
    "items_failed": 0
  },
  "files_modified_correctly": [
    "argus/intelligence/experiments/runner.py",
    "scripts/run_experiment.py",
    "tests/intelligence/experiments/test_runner.py"
  ],
  "forbidden_files_clean": true
}
```
