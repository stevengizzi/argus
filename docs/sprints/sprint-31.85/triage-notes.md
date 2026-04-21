# Sprint 31.85 — Impromptu Triage Notes

**Date:** April 20, 2026
**Classification:** Impromptu (between-sprints, standalone)
**Resolves:** DEF-161 (DuckDB Parquet consolidation — 983K file problem)
**Blocks unblocked:** Sprint 31B (Research Console SQL features), analytical-query layer in `docs/architecture/allocation-intelligence-vision.md`
**Protocol:** `workflow/protocols/impromptu-triage.md`

---

## 1. Scope

One-time consolidation of the Databento Parquet cache from per-month-per-symbol files (983K files, unusable by DuckDB) to per-symbol files (~24K files, fast DuckDB queries). The original cache is untouched; the consolidated cache is a derived, reproducible artifact.

## 2. Numbering

| Item | Value |
|------|-------|
| Sprint sub-number | **31.85** |
| New DECs | None (mechanical work — no architectural decision) |
| New RSKs | None |
| DEF resolved | **DEF-161** |
| Sessions | 1 (single-session sprint) |

## 3. Cache Separation (Canonical Reference)

After this sprint, ARGUS has **two Parquet caches**, each serving a specific purpose. Confusing them causes silent failures. This table is the source of truth and is mirrored into `docs/operations/parquet-cache-layout.md`.

| Cache | Path | Layout | Consumers | Writable? |
|-------|------|--------|-----------|-----------|
| **Original** | `data/databento_cache/` | `{SYMBOL}/{YYYY-MM}.parquet` (983K files) | `BacktestEngine` via `HistoricalDataFeed`; `scripts/resolve_symbols_fast.py`; `scripts/populate_historical_cache.py`; `scripts/run_experiment.py --cache-dir`; `argus/backtest/data_fetcher.py` | **NO — read-only. Source of truth.** |
| **Consolidated** | `data/databento_cache_consolidated/` | `{SYMBOL}/{SYMBOL}.parquet` (~24K files) with embedded `symbol` column | `HistoricalQueryService` (DuckDB) via `historical_query.yaml` | Rebuilt by `scripts/consolidate_parquet_cache.py`. Derived artifact. |

**Invariant:** BacktestEngine must never be pointed at the consolidated cache (it expects monthly files). HistoricalQueryService should be repointed from original → consolidated after first consolidation run.

## 4. Impact Assessment

| Question | Answer |
|----------|--------|
| What files will this touch? | New: `scripts/consolidate_parquet_cache.py`, `tests/scripts/test_consolidate_parquet_cache.py`, `docs/operations/parquet-cache-layout.md`. Modified: none. |
| What could this break? | Nothing at runtime — standalone script. Worst case at operator time: consolidation produces bad output, caught by row-count validation and benchmark verification. Original cache is read-only. |
| Does this conflict with in-progress sprint work? | No (between sprints). |
| Does this change any existing decisions? | No. Follows DEC-345 storage separation pattern and DEC-328 test discipline. |
| Should any planned sprint work be deferred? | No. Resolving DEF-161 de-risks Sprint 31B (Research Console) and the analytical query work in `allocation-intelligence-vision.md`. |
| Regression risk | **LOW.** No runtime code paths changed. Script only writes to new directory (`data/databento_cache_consolidated/`). |

## 5. Design Choices (Confirmed)

1. **Output layout:** `{SYMBOL}/{SYMBOL}.parquet`. Zero changes to `HistoricalQueryService` — the existing `regexp_extract(filename, ...)` continues to work unchanged when the service is repointed.
2. **Embed `symbol` column** in each consolidated Parquet file. Eliminates `regexp_extract` overhead on every DuckDB query. Self-describing files are better for debugging.
3. **Row-count validation** (`consolidated_row_count == sum(monthly_row_counts)`) is **non-bypassable**. No `--skip-validation` flag. Silent data loss was flagged as catastrophic.
4. **Compression:** zstd. Matches typical Databento compression; good size/speed balance.
5. **Sort semantics:** sort by `timestamp` ascending; no dedup. Original cache is authoritative — preserve duplicates if present rather than silently drop rows.
6. **Atomic write:** `.parquet.tmp` + `os.rename` *after* row-count validation passes. Corrupted files cannot land on disk.
7. **Resume mode** (default): re-reads existing consolidated files and validates row counts. Not just existence check.
8. **Parallelism:** per-symbol `ProcessPoolExecutor`, default 8 workers. Matches `resolve_symbols_fast.py` convention.
9. **Disk preflight:** refuses to start with less than 60 GB free unless `--force-no-disk-check` (test-only, not advertised).
10. **Benchmark thresholds** (60s/5s/30s for the three DuckDB queries) are informational, not pass/fail. Hard gate is row-count validation during consolidation itself.

## 6. Out of Scope (Explicit Deferrals)

- Modifying `config/historical_query.yaml` to repoint `cache_dir` — this is an **operator action** after first consolidation run, not a code change in this sprint.
- Monthly re-consolidation cron scheduling — log as a new DEF at next doc sync, paired with the existing open DEF for `populate_historical_cache.py --update` cron scheduling. Both crons chain together and should be scheduled as a pair.
- Any modifications to `HistoricalQueryService`, `HistoricalQueryConfig`, `BacktestEngine`, or existing scripts.

## 7. Handoff Checklist (Claude.ai → Claude Code)

Before running `session-1-prompt.md` in Claude Code:

- [ ] Confirm you are between sprints (no active sprint work in progress).
- [ ] Confirm branch is clean: `git status` shows no uncommitted work.
- [ ] Confirm at least 60 GB free on the cache volume.
- [ ] Confirm the sprint directory exists: `ls docs/sprints/sprint-31.85/` (should show these three planning files).
- [ ] Open Claude Code in the ARGUS repo.
- [ ] Paste the entire contents of `session-1-prompt.md` as the first message.
- [ ] Let the session run through implementation + @reviewer invocation.

## 8. Post-Session Operator Steps (NOT in sprint scope)

After a CLEAR or CONCERNS_RESOLVED verdict, manually:

1. Run `python scripts/consolidate_parquet_cache.py --verify` once (30–60 min wall clock).
2. Review benchmark report at `data/consolidation_benchmark_YYYYMMDD_HHMMSS.md`. Confirm sub-10s on single-symbol query, sub-60s on COUNT DISTINCT.
3. Edit `config/historical_query.yaml`: change `cache_dir` from `data/databento_cache` to `data/databento_cache_consolidated`.
4. Restart ARGUS. Watch startup log for `HistoricalQueryService: VIEW 'historical' created over data/databento_cache_consolidated (~24000 Parquet files found)`.
5. Log new DEF at next doc sync: "Monthly re-consolidation cron (chains with `populate_historical_cache.py --update`)".
