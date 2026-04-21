# Sprint 31.85, Session 1 — Tier 2 Review

**Reviewer:** Claude Opus 4.7 (Tier 2 automated review)
**Date:** 2026-04-20
**Scope:** Sprint 31.85, Session 1 — Parquet cache consolidation (DEF-161)
**Diff range:** `9f5482a` (single commit, 4 files added, 1509 insertions, 0 deletions)
**Mode:** Read-only. No source files were modified during review.

---BEGIN-REVIEW---

## Summary

The session delivers exactly the spec: a one-time consolidation script
(`scripts/consolidate_parquet_cache.py`, 758 lines), 15 new pytest tests
(`tests/scripts/test_consolidate_parquet_cache.py`, 489 lines), and an
operator-facing reference (`docs/operations/parquet-cache-layout.md`, 130
lines). No out-of-scope files were touched. Row-count validation is provably
non-bypassable, the original cache is byte-read-only, the `symbol` column is
sourced from the worker's known-symbol directory context, and the DuckDB
benchmark suite targets only the consolidated cache. Implementation is clean
and the review found no findings requiring escalation or remediation.

## Per-Focus-Item Findings

### 1. Row-count validation non-bypassable — PASS

- Greps for `--skip-validation`, `--no-validate`, `SKIP_VALIDATION`,
  `skip_validation`, `no_validate`: **no matches in script.**
- Greps for `except AssertionError` or `except ValueError` that could swallow a
  row-count failure: **no matches.** The only broad `except Exception` in
  `consolidate_one_symbol()` wraps the entire concat/sort/write block; on
  exception it returns `status="failed_io"` and unlinks any `.tmp` — it does
  not swallow validation.
- Write ordering at `scripts/consolidate_parquet_cache.py:321–360` is:
  compute `expected = sum(per_file_counts)`, compare to `actual = concatenated.num_rows`,
  return `failed_row_count` on mismatch (no write), then
  `pq.write_table(..., dest_tmp, ...)` → `os.rename(dest_tmp, dest_final)`.
  The rename is unreachable when validation fails.
- The regression test `test_no_bypass_flag_exists` (test file lines 480–489)
  hard-codes the three forbidden tokens and asserts absence.
- The operator documentation (`docs/operations/parquet-cache-layout.md`
  lines 123–131) states the non-bypassable nature explicitly.

### 2. Original cache is read-only — PASS

- Every filesystem-mutating call was located and audited. Targets:
  - `dest_tmp.unlink()` — three sites (lines 333, 354, 377), all operate on
    `{dest_dir}/{symbol}/{symbol}.parquet.tmp`.
  - `dest_symbol_dir.mkdir(...)` (line 351) — under `dest_dir`.
  - `pq.write_table(concatenated, dest_tmp, ...)` (line 358) — writes to
    `dest_tmp`.
  - `os.rename(dest_tmp, dest_final)` (line 360) — both paths under `dest_dir`.
  - `benchmark_out_path.parent.mkdir(...)` and `.write_text(report)` (lines
    546–547) — under `data/` (benchmark output).
  - `dest_dir.mkdir(...)` (lines 588, 649) — dest only.
- No `write_*`, `rename`, `unlink`, `rmtree`, or `touch` call resolves to a
  path under `source_dir`. Every `source_dir` usage is a read operation
  (`exists`, `iterdir`, `glob`, `Path(...)` construction).
- `test_original_cache_is_unmodified` (test file lines 127–144) uses
  `_snapshot_tree()` which captures `(st_size, st_mtime_ns, st_ino)` per file
  before and after the run. This is the full mtime+size+inode invariant the
  prompt required.

### 3. `symbol` column source — PASS

- `pa.array([symbol] * concatenated.num_rows, type=pa.string())` is at
  `scripts/consolidate_parquet_cache.py:318`. The `symbol` local variable is
  the first argument to `consolidate_one_symbol(symbol, source_dir, ...)` at
  line 213.
- The caller provides that symbol from `_list_symbol_dirs(source_dir)`
  (line 609), which returns directory names — not file content, not regex
  parsing.
- No `re.match`, `re.search`, `regexp_extract`, `stem`, or filename→symbol
  extraction appears in the script (grep clean).
- The regression test `test_symbol_column_populated_correctly` (test file
  lines 433–450) reads every consolidated file and asserts
  `values == [symbol] * tbl.num_rows` — a per-row equality check, not just
  a presence check.
- Defensive behavior on pre-existing `symbol` column in source: lines 316–317
  drop it before appending the canonical one. Correct: the worker's known
  context is authoritative.

### 4. Atomic write — PASS

- `pq.write_table(concatenated, dest_tmp, compression="zstd")` at line 358,
  followed by `os.rename(dest_tmp, dest_final)` at line 360. Both reach only
  after validation passes (lines 321–349 short-circuit on mismatch).
- `test_atomic_write_cleanup` (lines 453–477) monkeypatches `pq.write_table`
  to raise, asserts rc=1, and asserts no `.parquet` AND no `.parquet.tmp`
  remain — the broad `except Exception` block at line 373 catches the IOError
  and the inner `dest_tmp.unlink()` call (line 377) cleans the partial tmp
  file.
- The implementation extends spec intent by also unlinking stale `.tmp` files
  *before* writing (lines 352–356), which protects against crashed prior runs.

### 5. DuckDB benchmark targets consolidated cache — PASS

- `run_verification(dest_dir, benchmark_out_path)` (line 415) receives only
  `dest_dir`. No `source_dir` is imported into the function.
- Line 427: `files = sorted(dest_dir.glob("*/*.parquet"))`.
- Line 432: `glob_pattern = f"{dest_dir.resolve()}/**/*.parquet"`.
- Q1 SQL (line 452), Q2 SQL (line 471), Q3 SQL (line 491) all reference
  `glob_pattern` or `single_symbol_path` (which is `files[0]`, also from
  `dest_dir`).
- Real DuckDB: `conn = duckdb.connect(":memory:")` (line 445), with
  `memory_limit='2048MB'` and `threads=4` (matches `HistoricalQueryConfig`
  defaults per review context).
- Timing: `time.perf_counter()` bracketed around each SQL `execute` call
  (lines 456/458, 475/477, 498/500).

### 6. No modifications to HistoricalQueryService or config — PASS

- `git diff HEAD~1 -- argus/data/historical_query_service.py argus/data/historical_query_config.py config/historical_query.yaml argus/backtest/ scripts/resolve_symbols_fast.py scripts/populate_historical_cache.py scripts/run_experiment.py pyproject.toml requirements.txt` — **empty output.**
- `git diff HEAD~1 --name-only` shows exactly four files: the three new files
  and the closeout. (The review file being written now is not in HEAD~1 yet.)
- `git diff HEAD~1 -- data/` — **empty output.** (`data/databento_cache/`
  unchanged.)

### 7. Documentation accuracy — PASS

- `docs/operations/parquet-cache-layout.md` lines 9–15 contain the Cache
  Separation table matching the review context exactly.
- Line 14: "`BacktestEngine` must never be pointed at the consolidated cache."
- Line 16: "Conversely, `HistoricalQueryService` should be pointed at the
  consolidated cache" with an accurate description of the performance
  characteristics.
- Line 11 lists the original cache's consumers: `BacktestEngine` via
  `HistoricalDataFeed`; `scripts/resolve_symbols_fast.py`;
  `scripts/populate_historical_cache.py`; `scripts/run_experiment.py
  --cache-dir`; `argus/backtest/data_fetcher.py` — matches review context.
- Repointing instructions at lines 94–109 correctly instruct the operator to
  edit `config/historical_query.yaml` only, leaving `BacktestEngine`
  untouched.

### 8. Exit code on failure — PASS

- `main()` computes `exit_code = 1 if failed > 0 else 0` at line 709. The
  `_tally()` helper (lines 720–735) increments `failed` when
  `status.startswith("failed")`, which covers both `failed_row_count` and
  `failed_io`.
- Disk preflight failure → `return 1` (line 607).
- Empty symbol list (filter eliminated everything) → `return 1` (line 624).
- Missing source directory → `return 1` (line 612).
- `test_row_count_validation_detects_corruption` asserts `rc == 1` on forced
  row-count mismatch (line 173). `test_atomic_write_cleanup` asserts `rc == 1`
  on IO failure (line 475). `test_disk_space_preflight_blocks` asserts
  `rc == 1` (line 429).

### 9. Disk-space preflight — PASS

- `_DEFAULT_MIN_FREE_GB = 60` (line 40). `argparse` default
  `default=_DEFAULT_MIN_FREE_GB` at line 108.
- Preflight runs at lines 592–607 of `main()`, well before
  `_list_symbol_dirs(source_dir)` at line 609 — i.e., before any
  consolidation work.
- `--force-no-disk-check` exists (line 111–115) with help text "Skip the
  free-disk preflight (test-only)" — correctly flagged as test-only at
  declaration.
- `grep --force-no-disk-check docs/operations/parquet-cache-layout.md` —
  **no matches.** The flag is not advertised in operator documentation.

### 10. Resume validation is by row count, not existence — PASS

- Resume path at lines 257–285: `dest_final.exists()` is the trigger, but the
  skip decision at line 267 requires `existing_rows == source_row_count`.
  `_count_rows()` reads the existing consolidated file's Parquet metadata
  (line 202).
- On mismatch, a WARNING is logged (lines 279–285) and execution falls
  through to the concat+validate+write path.
- `test_resume_reconsolidates_on_row_count_mismatch` (lines 215–241) writes a
  1-row bogus file, runs with default `--resume`, and asserts the output
  file has been re-consolidated to the correct 10-row count.
- `--force` short-circuits the resume check entirely via `if resume and not
  force and dest_final.exists()` (line 257).

## Sprint-Level Regression Checklist

| Check | Result |
|-------|--------|
| Full pytest suite passes (accounting for 3 pre-existing failures) | **PASS** (closeout: 4,931 passed, 3 pre-existing failures) |
| HistoricalQueryService tests still pass | **PASS** (reviewer ran `pytest tests/scripts/test_consolidate_parquet_cache.py tests/data/test_historical_query_config.py tests/api/test_historical_routes.py -q` → 39/39 passed in 4.09s) |
| Only expected files changed | **PASS** (`git diff HEAD~1 --name-only` shows exactly 4 files: the 3 new files + the closeout artifact) |
| `historical_query.yaml` unchanged | **PASS** (`git diff HEAD~1 -- config/historical_query.yaml` empty) |
| No runtime dependencies added | **PASS** (`git diff HEAD~1 -- requirements*.txt pyproject.toml` empty) |
| `resolve_symbols_fast.py` still importable | **PASS** (reviewer verified) |

## Escalation Criteria

| Criterion | Status |
|-----------|--------|
| Any file under `data/databento_cache/` modified | **CLEAR** (no data diff) |
| Row-count validation bypassable | **CLEAR** (no bypass flags, validate-then-rename ordering, grep regression test exists) |
| `HistoricalQueryService`, `HistoricalQueryConfig`, or `historical_query.yaml` modified | **CLEAR** |
| Script deletes or renames files in original cache | **CLEAR** (no mutation call resolves under `source_dir`) |
| `symbol` column computed via filename regex | **CLEAR** (sourced from worker function argument, which is directory name) |
| Per-worker memory footprint could exceed ~2 GB | **CLEAR** (worst realistic case SPY with 8y 1-min bars ≈ 1M rows × ~80 B × ~3x peak = ~240 MB; docs document 1–2 GB ceiling and `--workers` tuning; no streaming rewrite required) |
| Any test weakened or skipped | **CLEAR** (no `@pytest.mark.skip`, no `xfail`, no existing tests modified) |

## Observations (Informational, Non-Blocking)

1. **Closeout judgment call #4 (separate `--verify-only` alias) is a helpful
   operator ergonomic.** The prompt allowed `--verify` to run standalone; the
   implementation provides both `--verify` (post-consolidation) and
   `--verify-only` (skip consolidation entirely). Both are exercised in tests
   and documented. Good call.

2. **Closeout judgment call #1 (sequential branch when `--workers <= 1`) is
   load-bearing for the test suite.** Monkeypatches in
   `test_row_count_validation_detects_corruption` and `test_atomic_write_cleanup`
   would not reach `ProcessPoolExecutor` workers. The sequential branch at
   lines 658–674 permits in-process execution. The production path
   (`--workers 8` default) is unchanged. Reasonable.

3. **Closeout judgment call #2 (`failed_io` status) extends hard exit-1
   semantics to IO failures.** The prompt required row-count mismatches to
   exit 1; the implementation also exits 1 on pyarrow write errors. This is a
   strict improvement: an unwritten consolidated file due to disk-full
   silently exiting 0 would be worse. The corresponding regression test
   (`test_atomic_write_cleanup`) exercises this explicitly.

4. **Minor: `promote_options="default"` on `pa.concat_tables`.** The script
   passes `promote_options="default"` at line 308. This preserves behavior on
   potential schema mismatches across monthly files (e.g., column reorderings
   between Databento historical imports). No issue, documenting for future
   diagnostics.

5. **Minor: existing `symbol` column handled defensively.** Lines 316–317
   drop any pre-existing `symbol` column from the source Parquets before
   appending the canonical one. This guards against double-columns if the
   source cache ever evolves. Not required by spec; harmless and defensive.

## Pre-Existing Failures

The closeout identifies 3 pre-existing failures; all are confirmed unrelated
to this session's changes:

1. `tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable`
   — DEF-159-adjacent date decay.
2. `tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration`
   — DEF-137-adjacent date decay.
3. `tests/sprint_runner/test_notifications.py::TestReminderEscalation::test_check_reminder_sends_after_interval`
   — DEF-150 flaky race under `-n auto`.

None touch any file in this sprint's scope. No action required.

## Verdict

**CLEAR.** All 10 session-specific focus items pass. No escalation criterion
is triggered. No regression checklist item fails. No weakened or skipped
tests. The implementation matches the spec exactly, judgment calls are
tasteful and well-documented, and the operator handoff path is well-defined.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "findings": [],
  "regression_checklist": {
    "full_pytest_suite_passes": "pass",
    "historical_query_service_tests_pass": "pass",
    "only_expected_files_changed": "pass",
    "historical_query_yaml_unchanged": "pass",
    "no_runtime_dependencies_added": "pass",
    "resolve_symbols_fast_py_importable": "pass",
    "original_cache_unmodified": "pass",
    "row_count_validation_non_bypassable": "pass",
    "symbol_column_sourced_from_directory_context": "pass",
    "atomic_write_validate_before_rename": "pass",
    "duckdb_benchmark_targets_consolidated_cache": "pass",
    "exit_code_one_on_failure": "pass",
    "disk_preflight_default_60gb_test_only_bypass": "pass",
    "resume_validates_by_row_count": "pass",
    "no_tests_weakened_or_skipped": "pass"
  },
  "pre_existing_failures_acknowledged": true
}
```
