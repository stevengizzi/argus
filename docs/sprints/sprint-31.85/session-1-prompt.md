# Sprint 31.85, Session 1: Parquet Cache Consolidation (DEF-161)

## Pre-Flight Checks

Before making any changes:

1. Read these files to load context:
   - `docs/sprints/sprint-31.85/triage-notes.md` (triage summary + cache separation table + design decisions)
   - `docs/sprints/sprint-31.85/review-context.md` (sprint spec, specification by contradiction, regression checklist)
   - `scripts/resolve_symbols_fast.py` (for ProcessPoolExecutor conventions, cache layout, pyarrow usage)
   - `argus/data/historical_query_service.py` (to understand exactly which query shapes the consolidated cache must support — `regexp_extract` path regex, `timestamp` column, `symbol` extraction, batch `validate_symbol_coverage()`)
   - `argus/data/historical_query_config.py` (config model — do not modify)
   - `config/historical_query.yaml` (do not modify)
   - `argus/backtest/historical_data_feed.py` lines 30–250 (to understand what BacktestEngine expects from the ORIGINAL cache — we must not break it)

2. Confirm two caches remain distinct:
   - Original: `data/databento_cache/{SYMBOL}/{YYYY-MM}.parquet` — BacktestEngine consumes. NEVER written by this script.
   - Consolidated: `data/databento_cache_consolidated/{SYMBOL}/{SYMBOL}.parquet` — HistoricalQueryService consumes. This script's sole output target.

3. Run the test baseline (DEC-328, Session 1 of sprint):
   Full suite: `python -m pytest --ignore=tests/test_main.py -n auto -q`
   Expected: 4,919 tests, all passing.
   Note: In autonomous mode, the expected test count is dynamically adjusted by the runner based on the previous session's actual results. The count above is the planning-time estimate.

4. Verify you are on the correct branch: `main` (or a `sprint-31.85` working branch if created).

5. The script itself includes a 60 GB free-disk preflight at runtime (`--min-free-gb` default 60). This is a runtime check, not a build-time check — the Claude Code session only needs to build and test the script, not run it against the real cache.

## Objective

Build a one-time consolidation script that merges the Databento Parquet cache's 983K per-month-per-symbol files into ~24K per-symbol files, with embedded `symbol` column and non-bypassable row-count validation. Verify DuckDB queries against the consolidated cache complete in under 10 seconds (vs hours against the original cache). Resolves DEF-161.

## Requirements

### R1. Create `scripts/consolidate_parquet_cache.py`

CLI interface (use `argparse`, match conventions from `scripts/resolve_symbols_fast.py`):

```
python scripts/consolidate_parquet_cache.py [flags]

--source-dir PATH         Default: data/databento_cache
--dest-dir PATH           Default: data/databento_cache_consolidated
--workers N               Default: 8
--symbols COMMA_OR_FILE   Optional: restrict to a subset for testing
                          (comma-separated list, or "@path/to/file.txt" with one symbol per line)
--limit N                 Optional: process only the first N symbols (for smoke tests)
--resume / --force        Default: --resume (skip symbols whose output exists AND passes row-count re-validation).
                          --force re-consolidates everything.
--verify                  After consolidation, run the DuckDB benchmark suite and print a report.
                          Can also be used standalone (skip consolidation, just benchmark existing consolidated cache).
--dry-run                 Print what would be done (symbol count, estimated size, worker count) without writing anything.
--min-free-gb N           Default: 60. Refuse to start if less than N GB free on --dest-dir's filesystem.
--force-no-disk-check     Skip the free-disk preflight (for test harnesses).
```

### R2. Per-symbol consolidation function

For each symbol, in a worker process:

1. List all files matching `{source_dir}/{SYMBOL}/*.parquet` (sorted lexicographically — alphabetical YYYY-MM ordering is also chronological).
2. If zero files: skip, report as empty.
3. For each monthly file:
   - Read with `pyarrow.parquet.read_table(path)` — keep all original columns.
   - Record row count.
4. Concat via `pyarrow.concat_tables(tables)`.
5. Sort by `timestamp` ascending using `pyarrow.compute.sort_indices` + `Table.take`. Do not drop duplicates — the original cache is authoritative; if it has them, the consolidated file keeps them.
6. Append a `symbol` column (`pyarrow.array` of the symbol string, length == table.num_rows) — the symbol value comes from the worker's known context (the directory name it was passed), NOT from parsing the Parquet content. This is important: we are eliminating the `regexp_extract` fragility, not relocating it.
7. **VALIDATE:** `consolidated_row_count == sum(monthly_row_counts)`. On mismatch:
   - Log an ERROR with symbol, expected count, actual count, per-file counts.
   - Do NOT write the output file.
   - Delete any existing `.tmp` file for this symbol.
   - Return a failure record so the main process can tally failures.
   - The script's exit code must be non-zero if any symbol failed this check.
8. Write atomically: write to `{dest_dir}/{SYMBOL}/{SYMBOL}.parquet.tmp`, then `os.rename` to final path. This prevents half-written files on interruption.
9. Use `pyarrow.parquet.write_table(table, path, compression='zstd')` — zstd matches typical Databento compression and is a good balance of size/speed.
10. Return per-symbol result dict: `{symbol, monthly_files, source_rows, dest_rows, dest_bytes, status, error}`.

### R3. Resume logic

Default `--resume` behavior for each symbol:
1. If `{dest_dir}/{SYMBOL}/{SYMBOL}.parquet` does not exist → consolidate.
2. If it exists, re-read it and count rows. Count rows in the original `{source_dir}/{SYMBOL}/*.parquet` files. If they match → skip (log DEBUG). If they mismatch → log WARNING and re-consolidate (the source grew or the output is corrupt).

`--force` skips the re-validation and always re-consolidates.

### R4. Verification mode (`--verify`)

After consolidation (or standalone), run these three DuckDB benchmarks against the consolidated cache and report wall-clock time for each:

| # | Query | Target | Pass threshold |
|---|-------|--------|----------------|
| 1 | `SELECT COUNT(DISTINCT symbol) FROM read_parquet('{dest_dir}/**/*.parquet', union_by_name=true)` | Distinct symbol count equal to number of consolidated files | < 60 s |
| 2 | Single-symbol range: `SELECT COUNT(*) FROM read_parquet('{dest_dir}/AAPL/AAPL.parquet') WHERE timestamp >= '2025-01-01' AND timestamp < '2025-02-01'` | Non-zero row count | < 5 s |
| 3 | Batch coverage check (mimics `validate_symbol_coverage()`): `SELECT symbol, COUNT(*) AS bars FROM read_parquet('{dest_dir}/**/*.parquet', union_by_name=true) WHERE symbol IN (<100 symbols>) AND timestamp >= '2025-01-01' AND timestamp < '2025-02-01' GROUP BY symbol` | 100 rows (one per symbol) | < 30 s |

- The 100 symbols in Q3 are sampled deterministically (e.g., every (total // 100)th symbol after sorting). Document the sampling rule in the script.
- Use an in-memory DuckDB connection: `duckdb.connect(':memory:')`.
- Set `SET memory_limit='2048MB'; SET threads TO 4;` to match `HistoricalQueryConfig` defaults.
- Print a Markdown-formatted benchmark table to stdout AND write it to `data/consolidation_benchmark_{YYYYMMDD_HHMMSS}.md` for the operator's record.
- If any query exceeds its pass threshold, print a WARNING at the top of the report — but do not fail the script. Thresholds are informational; the hard pass/fail is row-count validation during consolidation itself.

### R5. Structured progress logging

- Use Python `logging` with INFO-level stdout handler.
- Every 500 symbols completed, log: `Progress: N/M symbols consolidated (X GB written, Y.Ys elapsed, ~Zs ETA)`.
- On start, log: total symbol count, worker count, source/dest dirs, free disk.
- On each worker failure (row-count mismatch), log ERROR immediately with full details.
- On completion, log a summary: symbols succeeded, symbols failed, symbols skipped (resume), total bytes written, wall-clock time.
- Exit code: 0 if all symbols succeeded or skipped; 1 if any failed row-count validation or disk-space preflight.

### R6. Documentation file

Create `docs/operations/parquet-cache-layout.md` with:

- A copy of the Cache Separation table from `docs/sprints/sprint-31.85/triage-notes.md`.
- How to run the consolidation script (synopsis + common flags).
- When to re-run (after `populate_historical_cache.py --update` adds new months).
- How to verify the consolidated cache is healthy (`--verify` without consolidation).
- The operator steps for repointing `config/historical_query.yaml` (but do NOT modify `config/historical_query.yaml` itself in this sprint — that's an operator action, not a code change).
- Known limitation: `os.rename` is not cross-filesystem atomic; keep `--source-dir` and `--dest-dir` on the same filesystem.

## Constraints

- Do NOT modify: `argus/data/historical_query_service.py`, `argus/data/historical_query_config.py`, `config/historical_query.yaml`, anything under `argus/backtest/`, anything under `data/databento_cache/`.
- Do NOT change: the Parquet file format, column names, or types in the original cache. Read-only access only.
- Do NOT add: runtime dependencies. `pyarrow`, `pandas`, `duckdb`, `yaml` are all already in the project.
- Do NOT: introduce a `--skip-validation` flag or any other way to bypass row-count validation. Silent data loss was explicitly flagged as catastrophic.
- Do NOT: delete the original cache or offer a flag to do so. The original cache remains the source of truth forever.
- Do NOT: modify `scripts/resolve_symbols_fast.py`, `scripts/populate_historical_cache.py`, or any existing script.

## Canary Tests (run before making changes)

Create `tests/scripts/test_consolidate_parquet_cache.py` with a canary fixture that builds a tiny fake cache under `tmp_path`:

- 3 symbols: `AAA`, `BBB`, `CCC`.
- 2 months each: `2025-01.parquet`, `2025-02.parquet`.
- Each file: 5 rows with `timestamp`, `open`, `high`, `low`, `close`, `volume`.
- Distinct deterministic values per (symbol, month) so that concat is verifiable.

Assert these invariants BEFORE implementing the main logic (they should fail until the script is written, then pass):

1. Running the script produces `{dest}/AAA/AAA.parquet`, `{dest}/BBB/BBB.parquet`, `{dest}/CCC/CCC.parquet` and no other files.
2. Each consolidated file has `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume` columns — all present (order not asserted).
3. Each consolidated file has exactly 10 rows (2 months × 5 rows).
4. Rows are sorted by `timestamp` ascending.
5. The `symbol` column contains only the correct symbol per file.
6. The original cache under `tmp_path / "source"` is byte-identical before and after (file count, file sizes, and mtimes unchanged — use `os.stat` before and after).

## Test Targets

After implementation, `tests/scripts/test_consolidate_parquet_cache.py` must include:

- `test_consolidation_happy_path` — the 3-symbol canary above.
- `test_original_cache_is_unmodified` — explicit mtime + size comparison before/after.
- `test_row_count_validation_detects_corruption` — monkeypatch pyarrow concat to drop a row, assert the symbol is marked failed and no output file is written for it.
- `test_resume_skips_valid_existing` — run consolidation twice; second run should skip all symbols (assert via logging capture or a returned counter).
- `test_resume_reconsolidates_on_row_count_mismatch` — write a bogus output file with fewer rows than the source, run with `--resume`, confirm it re-consolidates and the row count matches.
- `test_force_reconsolidates_always` — run twice with `--force`; both runs should re-write.
- `test_symbols_filter_comma_separated` — `--symbols AAA,CCC` processes only those two.
- `test_symbols_filter_file` — `--symbols @path/to/symbols.txt` reads from file.
- `test_limit_flag` — `--limit 2` processes only the first two symbols.
- `test_dry_run_writes_nothing` — `--dry-run` produces no files in dest dir.
- `test_verify_benchmark_runs` — build a small consolidated cache by hand, run `--verify` only, confirm it produces the benchmark markdown file and returns exit code 0.
- `test_disk_space_preflight_blocks` — patch `shutil.disk_usage` to report insufficient space, assert the script refuses to start (exit code 1) without `--force-no-disk-check`.
- `test_symbol_column_populated_correctly` — for each consolidated file, assert all values in `symbol` column equal the expected symbol.
- `test_atomic_write_cleanup` — simulate an interruption mid-write (raise inside `write_table`), assert no `.parquet.tmp` files are left behind OR that they don't shadow the valid file on re-run.

Minimum new pytest count: **13**.

Test command for pre-flight (Session 1): `python -m pytest --ignore=tests/test_main.py -n auto -q`
Test command for close-out (Session 1 = final and only session of sprint 31.85): same full suite with `-n auto`.

## Config Validation

Not applicable — this sprint adds no YAML config fields. `historical_query.yaml` is explicitly not modified.

## Definition of Done

- [ ] `scripts/consolidate_parquet_cache.py` created and executable.
- [ ] `tests/scripts/test_consolidate_parquet_cache.py` with ≥13 new tests, all passing.
- [ ] `docs/operations/parquet-cache-layout.md` created with the cache-separation table, run instructions, and repoint instructions.
- [ ] Full pytest suite passes: expected ≥ 4,932 tests (baseline 4,919 + at least 13 new).
- [ ] Row-count validation is non-bypassable (grep the script to confirm no `--skip-validation` flag and no `try: ... except` that swallows row-count mismatches silently).
- [ ] Original cache unmodified: a test asserts byte-identical file states before/after.
- [ ] Script runs end-to-end on a 3-symbol synthetic cache within the test suite (integration test).
- [ ] Script's `--dry-run` mode works without writing anything.
- [ ] Close-out report written to `docs/sprints/sprint-31.85/session-1-closeout.md` with a structured JSON appendix fenced with ```json:structured-closeout.
- [ ] Tier 2 review completed via @reviewer subagent and written to `docs/sprints/sprint-31.85/session-1-review.md`.

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| HistoricalQueryService tests still pass | `pytest tests/data/test_historical_query_config.py tests/api/test_historical_routes.py -n auto -q` |
| No source files modified outside scope | `git diff HEAD~1 --name-only` should show only: `scripts/consolidate_parquet_cache.py`, `tests/scripts/test_consolidate_parquet_cache.py`, `docs/operations/parquet-cache-layout.md`, plus the two sprint artifact files. |
| `resolve_symbols_fast.py` still importable | `python -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('m', 'scripts/resolve_symbols_fast.py'); assert spec is not None; print('ok')"` |
| `historical_query.yaml` unchanged | `git diff HEAD~1 -- config/historical_query.yaml` produces no output. |
| No runtime dependencies added | `git diff HEAD~1 -- requirements*.txt pyproject.toml` produces no output. |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-31.85/session-1-closeout.md`

Include in the close-out:
- Line count of the new script.
- Final test count.
- Summary of any design decisions made during implementation (e.g., any deviations from the triage-notes design choices).
- Explicit confirmation that no files outside scope were modified.
- Explicit confirmation that row-count validation is non-bypassable.
- **Operator handoff section**: the 5-step checklist the operator runs to activate the consolidated cache (consolidate → benchmark → repoint `config/historical_query.yaml` → restart ARGUS → verify startup log).

Do NOT just print the report in the terminal. Create the file, write the full report, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written and committed, invoke the @reviewer subagent within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.85/review-context.md`.
2. The close-out report path: `docs/sprints/sprint-31.85/session-1-closeout.md`.
3. The diff range: `git diff HEAD~1`.
4. The test command (final and only session of sprint — full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`.
5. Files that should NOT have been modified:
   - `argus/data/historical_query_service.py`
   - `argus/data/historical_query_config.py`
   - `config/historical_query.yaml`
   - Anything under `argus/backtest/`
   - Anything under `data/databento_cache/`
   - `scripts/resolve_symbols_fast.py`, `scripts/populate_historical_cache.py`, `scripts/run_experiment.py`

The @reviewer writes its review (with `json:structured-verdict`) to:
`docs/sprints/sprint-31.85/session-1-review.md`

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session, you MUST update the artifact trail so it reflects reality:

1. **Append a "Post-Review Fixes" section to the close-out report file** at `docs/sprints/sprint-31.85/session-1-closeout.md` with the table of Finding / Fix / Commit hash. Commit the updated close-out file.

2. **Append a "Post-Review Resolution" annotation to the review report file** at `docs/sprints/sprint-31.85/session-1-review.md`. Update the structured verdict JSON: change `"verdict": "CONCERNS"` to `"verdict": "CONCERNS_RESOLVED"` and add a `"post_review_fixes"` array. Commit the updated review file.

If the reviewer reports CLEAR or ESCALATE, skip this section entirely. ESCALATE findings must NOT be fixed without human review.

## Session-Specific Review Focus (for @reviewer)

1. **Row-count validation non-bypassable.** Search the script for any flag or code path that skips the `consolidated_row_count == sum(monthly_row_counts)` assertion. There must be none. Also confirm that on mismatch, the output file is NOT written (check the write order — validation before `os.rename`, not after).
2. **Original cache is read-only.** Search the script for any `write`, `rename`, `unlink`, `rmtree`, `touch`, or any filesystem mutation whose target path resolves under `args.source_dir`. There must be none. The test `test_original_cache_is_unmodified` must exist and must use `os.stat` comparisons, not just existence checks.
3. **`symbol` column correctness and source.** Verify the script adds a `symbol` column to every consolidated file, populated from the worker's known-symbol context (directory name it was passed), NOT from parsing the Parquet content or filename regex. Verify the test `test_symbol_column_populated_correctly` asserts this for every symbol in the fixture.
4. **Atomic write.** Confirm `write_table` targets `*.parquet.tmp` and `os.rename` promotes to `*.parquet` only after row-count validation passes. Simulated interruption test must exist.
5. **DuckDB benchmark actually runs against consolidated cache.** Confirm the `--verify` mode's SQL references `{dest_dir}` (the consolidated cache), not `{source_dir}`. Confirm it actually instantiates a real DuckDB connection and measures wall-clock via `time.perf_counter`.
6. **No modifications to HistoricalQueryService or its config.** Confirm via `git diff` that `argus/data/historical_query_service.py`, `argus/data/historical_query_config.py`, and `config/historical_query.yaml` are byte-identical to `HEAD~1`.
7. **Documentation accuracy.** Verify `docs/operations/parquet-cache-layout.md` correctly identifies which tools use which cache — especially that BacktestEngine uses the original cache, not the consolidated one. A confused doc here leads to silent production bugs later.
8. **Exit code on failure.** Confirm that any symbol-level row-count failure causes the script's exit code to be 1, not 0. A silent exit-0 on corruption is a regression.
9. **Disk-space preflight.** Confirm `--min-free-gb` default is 60 and the preflight runs before any consolidation work begins. Confirm `--force-no-disk-check` is test-only and not advertised in the operator documentation.
10. **No bypass of resume validation.** Confirm `--resume` (default) re-reads existing consolidated files and validates row counts — it does not simply check file existence.

## Sprint-Level Regression Checklist (for @reviewer)

See `docs/sprints/sprint-31.85/review-context.md` under "Sprint-Level Regression Checklist".

## Sprint-Level Escalation Criteria (for @reviewer)

See `docs/sprints/sprint-31.85/review-context.md` under "Sprint-Level Escalation Criteria".
