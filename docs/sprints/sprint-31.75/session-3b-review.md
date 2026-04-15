# Sprint 31.75, Session 3b — Tier 2 Review Report

**Reviewer:** Tier 2 Automated Review (Opus 4.6)
**Date:** 2026-04-14
**Session:** Sprint 31.75, Session 3b — Sweep Tooling Scripts
**Commits reviewed:** `85e9854` (implementation), `71771c0` (close-out)
**Close-out self-assessment:** CLEAN

---BEGIN-REVIEW---

## 1. Spec Compliance

### Deliverables

| Deliverable | Status | Notes |
|-------------|--------|-------|
| `scripts/resolve_sweep_symbols.py` | DELIVERED | Full CLI with `--pattern`, `--all-patterns`, `--date-range`, `--output-dir`, `--persist-db`, `--min-bars` |
| `scripts/run_sweep_batch.sh` | DELIVERED | Three-phase orchestrator with error isolation |
| `config/universe_filters/bull_flag_trend.yaml` | DELIVERED | Distinct criteria from `bull_flag.yaml` |
| `scripts/analyze_sweeps.py` relocation | DELIVERED | Shebang + docstring added, content preserved |
| 15 new tests | DELIVERED | Minimum was 4; 15 provided covering all deliverables |

### Constraints

| Constraint | Honored? |
|-----------|----------|
| `runner.py` unmodified | YES |
| `store.py` unmodified | YES |
| `historical_query_service.py` unmodified | YES |
| Pattern files unmodified | YES |
| `ui/` unmodified | YES |
| `config/universe_filters/bull_flag.yaml` unmodified | YES |

All six protected files confirmed unmodified via `git diff HEAD~2`.

## 2. Session-Specific Review Focus

### F1: Single HistoricalQueryService in `--all-patterns` mode

**PASS.** `main()` at line 309 creates exactly one `HistoricalQueryService` instance before the pattern loop (line 334). The same `service` object is passed to `_resolve_one_pattern()` for each pattern. `service.close()` is called once at line 357 after the loop completes. Test `test_resolve_sweep_symbols_all_patterns_main_single_service` explicitly asserts the constructor is called exactly once across multiple patterns.

### F2: `run_sweep_batch.sh` uses `> logfile 2>&1` (not `| tee`)

**PASS.** Line 106 of the batch script: `> "$logfile" 2>&1`. No `| tee` anywhere in the script. Test `test_run_sweep_batch_no_tee_in_sweep_phase` asserts this.

### F3: Error isolation with `|| { ... continue }` block form

**PASS.** Lines 106-110 of the batch script use the block form:
```bash
> "$logfile" 2>&1 || {
    echo "FAILED: $pattern (see $logfile)"
    echo "{\"status\": \"failed\", \"pattern\": \"$pattern\"}" > "$progress_file"
    continue
}
```
One pattern's failure writes a progress sentinel and continues to the next pattern. No `|| exit` appears in the script. Test `test_run_sweep_batch_uses_continue_not_exit` asserts this.

### F4: `bull_flag_trend.yaml` differs from `bull_flag.yaml`

**PASS.** Three criteria differ:
- `min_price`: 20.0 (trend) vs 10.0 (momentum)
- `max_price`: 300.0 (trend) vs 500.0 (momentum)
- `min_avg_volume`: 300000 (trend) vs 500000 (momentum)

Test `test_bull_flag_trend_differs_from_bull_flag` asserts at least one criterion differs.

### F5: No frontend imports or modifications

**PASS.** No files under `argus/ui/` in the diff. No imports from `ui/` in any new file.

### F6: macOS bash 3.2 compatibility

**PASS.** Script syntax-checks cleanly with `bash -n`. No bash 4+ bashisms found (no `declare -A`, `readarray`, `mapfile`, regex matching `=~`, or case modification operators). Uses only `set -euo pipefail`, arrays via `PATTERNS=(...)`, `[[ ]]` conditionals, and `$()` command substitution -- all bash 3.2 compatible. Note: `date -Iseconds` verified working on this macOS system.

## 3. Test Results

- **Full suite:** 4,898 passed, 1 failed (pre-existing `test_history_store_migration`)
- **New tests:** 15 passed in 0.05s
- **Net change:** +41 tests from baseline 4,857 (session reports +15 new; the remaining +26 are likely from the previous session S3a combined with S3b in the same diff range)

The pre-existing failure (`test_history_store_migration`) is a known xdist race condition documented in the close-out report and confirmed in sprint context as pre-existing.

## 4. Code Quality Assessment

### Strengths
- Clean separation of concerns: symbol resolution (`resolve_sweep_symbols.py`) is decoupled from sweep execution (`run_sweep_batch.sh`).
- `_DYNAMIC_FILTER_FIELDS` imported from `run_experiment.py` rather than duplicated, keeping the two scripts in sync.
- Good defensive coding: `service.close()` called after the loop, `failed_patterns` tracking, non-zero exit on failures.
- Batch script's three-phase design (resolve, validate, sweep) with progress sentinels is operationally sound.

### Findings

**F1 (LOW): SQL construction uses f-strings for numeric filter values**

`_apply_static_filters()` (lines 211-216) interpolates `filter_config.min_price`, `max_price`, and `min_avg_volume` directly into SQL via f-strings rather than parameterized queries. These are Pydantic-validated `float | None` and `int | None` fields from YAML, so injection risk is negligible. This mirrors the existing pattern in `run_experiment.py`. Noting for consistency -- the `date` parameters on the same query correctly use parameterized `?` placeholders.

**F2 (LOW): `_count_cache_symbols` uses raw SQL on `historical` view**

`_count_cache_symbols()` calls `service.query("SELECT COUNT(DISTINCT symbol) AS n FROM historical", [])`. This assumes the view name is `historical`, which is an implementation detail of `HistoricalQueryService`. If the view name changes, this would break silently. The existing `validate_symbol_coverage()` method on the service abstracts this away. Minor coupling concern.

**F3 (INFO): Judgment call on `_apply_static_filters` duplication documented clearly**

The close-out report explains why `_apply_universe_filter` from `run_experiment.py` was not reused (it creates/destroys its own service per call). The alternative -- importing `_DYNAMIC_FILTER_FIELDS` and writing ~30 lines of SQL construction -- is a reasonable trade-off for the single-service requirement. This is well-documented in the judgment calls section.

**F4 (INFO): `test_cli_delegates_filter_to_runner` modification is legitimate**

The test was broken by S3a's move to inline filtering. The fix correctly updates assertions to match S3a's behavior (inline resolution, `universe_filter=None` to `run_sweep()`). This file is not in the protected list.

## 5. Regression Checklist

| # | Check | Result |
|---|-------|--------|
| 1 | Protected files unmodified | PASS |
| 2 | `test_cli_delegates_filter_to_runner` fix is legitimate | PASS (S3a broke assumptions; not in protected list) |
| 3 | Pre-existing `test_history_store_migration` confirmed pre-existing | PASS |
| 4 | New test count >= 4 | PASS (15 new tests) |
| 5 | No `| tee` in batch script | PASS |
| 6 | `|| { ... continue }` error isolation | PASS |
| 7 | `bull_flag_trend.yaml` differs from `bull_flag.yaml` | PASS |
| 8 | Single service instance in `--all-patterns` | PASS |

## 6. Verdict

All session-specific review focus items pass. All protected files are unmodified. No escalation criteria triggered. Test suite shows +41 net tests with only the pre-existing `test_history_store_migration` failure. Code quality is solid with well-documented judgment calls.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "id": "F1",
      "severity": "LOW",
      "description": "SQL f-string interpolation for numeric Pydantic fields in _apply_static_filters() — matches existing pattern in run_experiment.py, negligible injection risk",
      "file": "scripts/resolve_sweep_symbols.py",
      "lines": "211-216"
    },
    {
      "id": "F2",
      "severity": "LOW",
      "description": "_count_cache_symbols() hardcodes 'historical' view name, coupling to HistoricalQueryService internals",
      "file": "scripts/resolve_sweep_symbols.py",
      "lines": "171"
    }
  ],
  "tests": {
    "total_passed": 4898,
    "total_failed": 1,
    "new_tests": 15,
    "pre_existing_failures": ["tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration"]
  },
  "escalation_triggers": []
}
```
