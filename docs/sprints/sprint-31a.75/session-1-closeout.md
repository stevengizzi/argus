# Sprint 31A.75, Session 1 — Close-Out Report

**Sprint:** 31A.75 Sweep Tooling Impromptu
**Session:** 1 — Universe-Aware Sweep Flags
**Date:** 2026-04-03
**Status:** CLEAN

---

## Summary

Added `--symbols` and `--universe-filter` CLI flags to `scripts/run_experiment.py`,
resolving DEF-145. Parameter sweeps can now target specific symbol populations instead
of the full Parquet cache. `HistoricalQueryService.validate_symbol_coverage()` is wired
into the filtering pipeline to drop symbols without sufficient cache data.

---

## Change Manifest

### New / Modified Files

| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/run_experiment.py` | Modified | Added `--symbols`, `--universe-filter` args; `_parse_symbols()`, `_load_universe_filter()`, `_apply_universe_filter()`, `_validate_coverage()` helpers; symbol filtering pipeline in `run()`; updated epilog |
| `argus/intelligence/experiments/config.py` | Modified | Added `backtest_start_date: str | None = None` and `backtest_end_date: str | None = None` to `ExperimentConfig` so `run()` can access config-level dates |
| `tests/scripts/test_run_experiment_filters.py` | New | 12 tests covering `_parse_symbols`, `_load_universe_filter`, and `parse_args` behavior |

### No Other Files Modified

`argus/core/config.py`, `argus/data/historical_query_service.py`,
`argus/backtest/engine.py`, `argus/intelligence/experiments/runner.py` — all unchanged.
`runner.run_sweep()` already had `symbols` parameter passing through to `BacktestEngineConfig`.

---

## Requirements Checklist

| Req | Description | Status |
|-----|-------------|--------|
| 1 | `--symbols` arg + `_parse_symbols()` (comma-sep + @filepath, dedup, uppercase) | DONE |
| 2 | `--universe-filter` arg + `_load_universe_filter()` (load YAML, SystemExit on missing) | DONE |
| 3 | `_apply_universe_filter()` (DuckDB query, static HAVING clauses, dynamic filter warnings) | DONE |
| 4 | `_validate_coverage()` (batch coverage check, log drops) | DONE |
| 5 | Filtering pipeline in `run()` (Layer 1→2→3) | DONE |
| 6 | Pass `symbols` to `run_sweep()` | DONE |
| 7 | Dry-run output shows symbol count | DONE |
| 8 | Updated epilog with new examples | DONE |
| 9 | `backtest_start_date`/`backtest_end_date` on `ExperimentConfig` | DONE |

---

## Judgment Calls

1. **`ExperimentConfig` modification:** The spec said to add `backtest_start_date`/
   `backtest_end_date` if not present. `ExperimentConfig` has `extra="forbid"`, so
   adding optional fields with `None` defaults is a backward-compatible change. The
   YAML (`config/experiments.yaml`) does not currently use these fields, so no YAML
   changes were needed.

2. **Parameter ordering in `_apply_universe_filter()`:** The SQL `WHERE` clause is
   `date >= ? AND date <= ? AND symbol IN (...)`, so params are ordered
   `[start_date, end_date, sym1, sym2, ...]`. A dead `where_params` variable was
   introduced and then removed before finalizing, replaced by the correct `query_params`.

3. **`nargs='?'` with `const='__from_pattern__'`:** Used exactly as specified. When
   `--universe-filter` appears with no value, `args.universe_filter == "__from_pattern__"`.
   The `run()` function then substitutes `args.pattern` as the filter name.

4. **Coverage validation skipped when dates unavailable:** If no date range is available
   (neither `--date-range` nor config defaults), coverage validation is skipped and
   symbols pass through unvalidated — matches spec intent.

5. **Flaky pre-existing test:** `tests/sprint_runner/test_notifications.py::TestReminderEscalation::test_check_reminder_sends_after_interval` failed once under `-n auto` but passed immediately when run in isolation. This is a pre-existing race condition (DEF not yet assigned), completely unrelated to this session's changes.

---

## Test Results

**New tests:** 12 passing (spec required 11 minimum)

| Test | Status |
|------|--------|
| `test_parse_symbols_comma_separated` | PASS |
| `test_parse_symbols_with_whitespace` | PASS |
| `test_parse_symbols_from_file` | PASS |
| `test_parse_symbols_from_file_blank_lines` | PASS (bonus beyond spec) |
| `test_parse_symbols_deduplicates` | PASS |
| `test_parse_symbols_uppercase` | PASS |
| `test_load_universe_filter_valid` | PASS |
| `test_load_universe_filter_missing` | PASS |
| `test_parse_args_symbols_flag` | PASS |
| `test_parse_args_universe_filter_with_value` | PASS |
| `test_parse_args_universe_filter_no_value` | PASS |
| `test_parse_args_defaults_unchanged` | PASS |

**Full suite:** 4822 passed, 1 pre-existing flaky failure, 63 warnings
(4811 baseline + 12 new = 4823 total; flaky test counts in total but fails intermittently)

---

## Regression Checklist

| Check | Result |
|-------|--------|
| Default behavior unchanged | PASS — `--pattern bull_flag --dry-run` works, shows "Symbols: all (auto-detect from cache)" |
| `--symbols` comma parsing | PASS — `--symbols AAPL,NVDA --dry-run` shows "Symbols from --symbols: 2" + "Symbols: 2 (filtered)" |
| `--universe-filter` flag | PASS — `--universe-filter --dry-run` triggers DuckDB query (DuckDB view creation logged) |
| `--help` shows new examples | PASS — `--symbols`, `--universe-filter`, and all new epilog examples visible |
| No unexpected production files modified | PASS — only `argus/intelligence/experiments/config.py` (explicitly expected) |
| `ExperimentRunner.run_sweep()` symbols pass-through | CONFIRMED — `symbols` param already existed at line 199, passed to `BacktestEngineConfig` at line 312 |

---

## Deferred Items

None from this session. DEF-145 is resolved.

---

## Context State

GREEN — session completed within normal context bounds.

---

## Self-Assessment

**CLEAN** — All 9 requirements implemented. 12/11 required tests written and passing.
Default behavior verified unchanged. Only expected file (`experiments/config.py`) modified
in `argus/`. Pre-existing flaky test unrelated to changes.

---

```json:structured-closeout
{
  "sprint": "31A.75",
  "session": 1,
  "date": "2026-04-03",
  "verdict": "CLEAN",
  "files_changed": [
    "scripts/run_experiment.py",
    "argus/intelligence/experiments/config.py",
    "tests/scripts/test_run_experiment_filters.py"
  ],
  "tests_added": 12,
  "tests_baseline": 4811,
  "tests_final": 4823,
  "tests_passing": 4822,
  "tests_failing_preexisting": 1,
  "def_resolved": ["DEF-145"],
  "def_opened": [],
  "dec_added": [],
  "scope_deviations": [],
  "judgment_calls": [
    "ExperimentConfig backtest date fields added (explicitly expected by spec)",
    "query_params ordering: [start_date, end_date, *candidate_symbols] matches SQL WHERE clause order",
    "Coverage validation skipped gracefully when no date range available",
    "Bonus test: test_parse_symbols_from_file_blank_lines (beyond 11-test minimum)"
  ],
  "context_state": "GREEN"
}
```
