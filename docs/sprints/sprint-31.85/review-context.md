# Sprint 31.85 — Sweep Infrastructure: Parquet Consolidation

## Review Context File

> Shared context for the Tier 2 review in Sprint 31.85.
> This file is referenced by each session's review prompt.

---

## Sprint Spec (Summary)

**Sprint 31.85** resolves DEF-161 by building a one-time consolidation script that merges the Databento Parquet cache's 983K per-month-per-symbol files into ~24K per-symbol files. This unblocks the DuckDB-based `HistoricalQueryService` (which currently cannot practically query the 983K-file cache — VIEW scans take hours, TABLE materialization takes 16+ hours) and in turn unblocks Sprint 31B Research Console SQL features.

### Sessions

| Session | Scope | Key Deliverables |
|---------|-------|-----------------|
| S1 | Consolidation script + tests + docs | `scripts/consolidate_parquet_cache.py`, `tests/scripts/test_consolidate_parquet_cache.py`, `docs/operations/parquet-cache-layout.md` |

### Invariants

1. All existing 4,919 pytest + 846 Vitest tests must pass after the session.
2. Original cache (`data/databento_cache/`) is byte-read-only. No writes, renames, unlinks, or mutations of any kind. BacktestEngine consumes this cache via `HistoricalDataFeed` and must continue to work unchanged.
3. `HistoricalQueryService`, `HistoricalQueryConfig`, and `config/historical_query.yaml` are NOT modified in this sprint. The service consumes the consolidated cache after operator-level repointing, which happens *after* this sprint.
4. Row-count validation (`consolidated_row_count == sum(monthly_row_counts)`) is non-bypassable. No flag, env var, or code path can disable it.
5. No runtime dependencies added — `pyarrow`, `pandas`, `duckdb`, `yaml` are already in the project.

### Cache Separation (Critical Reference)

| Cache | Path | Layout | Consumers | Writable? |
|-------|------|--------|-----------|-----------|
| **Original** | `data/databento_cache/` | `{SYMBOL}/{YYYY-MM}.parquet` (983K files) | `BacktestEngine`, `HistoricalDataFeed`, `resolve_symbols_fast.py`, `populate_historical_cache.py`, `run_experiment.py --cache-dir`, `data_fetcher.py` | **NO — read-only** |
| **Consolidated** | `data/databento_cache_consolidated/` | `{SYMBOL}/{SYMBOL}.parquet` (~24K files) with embedded `symbol` column | `HistoricalQueryService` (DuckDB) after operator repoints `historical_query.yaml` | Rebuilt by `scripts/consolidate_parquet_cache.py` |

### Key Design Decisions

1. **Output layout `{SYMBOL}/{SYMBOL}.parquet`** preserves the existing `regexp_extract(filename, '.*/([^/]+)/[^/]+\\.parquet$', 1)` pattern in `HistoricalQueryService._initialize_view()` and `_initialize_table()`. Zero service-code changes required.
2. **Embedded `symbol` column** — self-describing Parquet, no regex overhead on query.
3. **zstd compression** — matches typical Databento compression.
4. **Sort by `timestamp` ascending, no dedup.**
5. **Atomic write** — `.tmp` + `os.rename` after validation passes.
6. **Resume is row-count-validated**, not existence-only.

---

## Specification by Contradiction

Claims the implementation must falsify:

1. **"The script modifies files in the original cache."** → Test `test_original_cache_is_unmodified` uses `os.stat` comparisons (size + mtime) before and after the run. Any mutation fails the test.
2. **"Row-count validation can be bypassed."** → Grep the script for `--skip-validation`, `--no-validate`, `SKIP_VALIDATION`, or any `try/except` that catches `AssertionError` or `ValueError` from the row-count check. None should exist.
3. **"Consolidated file can land on disk with a row-count mismatch."** → Write order is validate → `os.rename(.tmp → final)`. If validation fails, the `.tmp` file is deleted, not promoted.
4. **"The `symbol` column might be missing or wrong."** → Test `test_symbol_column_populated_correctly` asserts for every symbol in the fixture (3 symbols) that every row's `symbol` value equals the expected symbol.
5. **"The script exits 0 even when symbols failed."** → Test asserts exit code 1 when any symbol fails row-count validation.
6. **"The DuckDB benchmark could be reading from the wrong cache."** → Review focus item confirms `--verify` SQL targets `{dest_dir}`, not `{source_dir}`.
7. **"HistoricalQueryService was modified."** → `git diff HEAD~1 -- argus/data/historical_query_service.py argus/data/historical_query_config.py config/historical_query.yaml` must produce no output.

---

## Sprint-Level Regression Checklist

| Check | How to Verify |
|-------|---------------|
| Full pytest suite passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` — expected ≥ 4,932 tests (baseline 4,919 + ≥ 13 new) |
| HistoricalQueryService tests still pass | `pytest tests/data/test_historical_query_config.py tests/api/test_historical_routes.py -n auto -q` |
| Only expected files changed | `git diff HEAD~1 --name-only` shows only: `scripts/consolidate_parquet_cache.py`, `tests/scripts/test_consolidate_parquet_cache.py`, `docs/operations/parquet-cache-layout.md`, plus the two sprint artifact files (`session-1-closeout.md`, `session-1-review.md`) |
| `historical_query.yaml` unchanged | `git diff HEAD~1 -- config/historical_query.yaml` produces no output |
| No runtime dependencies added | `git diff HEAD~1 -- requirements*.txt pyproject.toml` produces no output |
| `resolve_symbols_fast.py` still importable | `python -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('m', 'scripts/resolve_symbols_fast.py'); assert spec is not None; print('ok')"` |

---

## Sprint-Level Escalation Criteria

ESCALATE to Tier 3 if any of the following is observed:

1. **Any file under `data/databento_cache/` was modified** — data-integrity red line. Automatic escalation.
2. **Row-count validation can be bypassed** via any flag, environment variable, or code path.
3. **`HistoricalQueryService`, `HistoricalQueryConfig`, or `historical_query.yaml` was modified** — out of scope. A change there means the cache separation architecture was altered without design review.
4. **The script deletes or renames files in the original cache.**
5. **The `symbol` column is computed from filename via regex inside the Parquet write path** instead of being passed from the known-symbol worker context. This re-introduces the exact fragility we are eliminating.
6. **Per-symbol worker memory footprint exceeds ~2 GB** on a single large symbol (e.g., SPY with 8+ years of 1-min bars). If observed, the concat strategy needs a streaming rewrite — flag for Tier 3 rather than patch in-session.
7. **Any test was weakened or skipped** to make the suite pass (e.g., `@pytest.mark.skip`, `xfail` added to existing passing tests).
