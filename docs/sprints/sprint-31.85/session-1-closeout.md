# Sprint 31.85, Session 1 — Close-Out

**Date:** 2026-04-20
**Sprint:** 31.85 (Sweep Infrastructure — Parquet Consolidation)
**Session:** 1 (final and only session)
**Resolves:** DEF-161
**Branch:** main
**Context state:** GREEN — session completed well within context limits

---

## Objective

Build a one-time consolidation script that merges `data/databento_cache/{SYMBOL}/{YYYY-MM}.parquet` (≈983K files) into `data/databento_cache_consolidated/{SYMBOL}/{SYMBOL}.parquet` (~24K files) with an embedded `symbol` column and non-bypassable row-count validation, unblocking DuckDB-based analytical queries for Sprint 31B.

## Change Manifest

| File | Status | Notes |
|------|--------|-------|
| [scripts/consolidate_parquet_cache.py](scripts/consolidate_parquet_cache.py) | **Added** | 758 lines. One-time per-symbol consolidation with `ProcessPoolExecutor`, atomic `.tmp → rename` write, non-bypassable row-count validation, and DuckDB `--verify` benchmark suite. |
| [tests/scripts/test_consolidate_parquet_cache.py](tests/scripts/test_consolidate_parquet_cache.py) | **Added** | 15 new pytest tests exercising happy path, resume, force, symbol filters, dry-run, disk preflight, symbol-column correctness, atomic-write cleanup, and a grep-style bypass-token check. |
| [docs/operations/parquet-cache-layout.md](docs/operations/parquet-cache-layout.md) | **Added** | Canonical cache-separation table, script synopsis, repointing instructions, known limitations, and explicit statement that row-count validation is non-bypassable. |

Nothing else was modified.

## Scope Verification

- `argus/data/historical_query_service.py` — **unchanged** (untracked-only diff).
- `argus/data/historical_query_config.py` — **unchanged**.
- `config/historical_query.yaml` — **unchanged** (repointing is an operator action after this sprint).
- Anything under `argus/backtest/` — **unchanged**.
- Anything under `data/databento_cache/` — **unchanged** (runtime-only directory; script is read-only against it).
- `scripts/resolve_symbols_fast.py`, `scripts/populate_historical_cache.py`, `scripts/run_experiment.py` — **unchanged**.
- `requirements*.txt` / `pyproject.toml` — **unchanged** (no new runtime dependencies).

Confirmed via `git status --short`: only three untracked additions under `scripts/`, `tests/scripts/`, and `docs/operations/`.

## Non-Bypassable Row-Count Validation

The contract `consolidated_row_count == sum(monthly_row_counts)` is enforced in `consolidate_one_symbol()`. On mismatch:

1. An `ERROR` log is emitted with per-file counts.
2. Any existing `.parquet.tmp` is deleted.
3. No file is ever promoted to `{SYMBOL}.parquet` — `os.rename` is only reached after validation passes.
4. A `failed_row_count` status is returned to the orchestrator.
5. The script exits with code 1 if any symbol reported `failed_*` status.

There is no flag or environment variable that disables this check. The regression test `test_no_bypass_flag_exists` greps the script source for `--skip-validation`, `--no-validate`, and `SKIP_VALIDATION` and asserts none are present.

## Judgment Calls During Implementation

1. **Sequential fallback when `--workers <= 1`.** Added an in-process branch so monkeypatched unit tests can exercise the worker without needing `ProcessPoolExecutor`. The production path (default `--workers 8`) is unchanged; the sequential branch is gated only on `args.workers <= 1`. No new flag.
2. **`failed_io` status.** The spec explicitly names row-count failures as a hard exit-1 trigger. I extended this to any IO-level failure in the worker (e.g., disk full mid-write, pyarrow write error). This keeps the script honest about partial failure. The atomic-write regression test exercises this path and asserts rc == 1 plus no leftover `.tmp` file.
3. **Q2 single-symbol benchmark uses the first consolidated file, not a hard-coded `AAPL`.** The prompt's benchmark table used `AAPL` as an illustrative symbol; since the real cache may or may not contain it, I read the first file from the sorted listing instead. The sampling rule is documented in the Markdown benchmark output.
4. **Separate `--verify-only` alias.** The prompt allowed `--verify` to run standalone "just benchmark existing consolidated cache". I added an explicit `--verify-only` mode alongside the post-consolidation `--verify`, both wired into `run_verification()`. Keeps the intent unambiguous in operator-facing usage.

None of these deviate from a requirement; each clarifies behavior at edges the spec left to my judgment.

## Regression Verification

| Check | Result |
|-------|--------|
| Full suite (`python -m pytest --ignore=tests/test_main.py -n auto -q`) | 4,931 passed, 3 pre-existing failures, 117.21s |
| Scripts-only (`pytest tests/scripts/`) | 74 passed, 0.36s |
| New file tests (`pytest tests/scripts/test_consolidate_parquet_cache.py`) | 15 passed, 0.41s |
| HistoricalQueryService tests (`pytest tests/data/test_historical_query_config.py tests/api/test_historical_routes.py`) | Not affected — module untouched |
| `git diff HEAD -- config/historical_query.yaml` | Empty |
| `git diff HEAD -- requirements*.txt pyproject.toml` | Empty |

### Pre-Existing Failures (Not Caused by This Session)

All three were reproduced against code paths entirely outside the three new files:

1. `tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable` — date-decay failure (test seeded bogus trade via `datetime.now()`, expects `pnl == 100.0`, observed `0.0`). Related to DEF-159 retroactive migration; needs a time freeze.
2. `tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration` — similar date-decay. Related to DEF-137 pattern.
3. `tests/sprint_runner/test_notifications.py::TestReminderEscalation::test_check_reminder_sends_after_interval` — DEF-150 (flaky race under `-n auto`, pre-existing).

## Final Test Count

- **Baseline:** 4,919 pytest (CLAUDE.md "Current State")
- **After session:** 4,934 pytest total (4,931 passing + 3 pre-existing date-decay/flaky failures)
- **Net new tests:** 15 (target was ≥13)

## Self-Assessment

**CLEAN.** Scope matches spec; all Definition-of-Done items completed; row-count validation is non-bypassable; original cache never written; no out-of-scope files touched; ≥13 new tests delivered.

## Operator Handoff — 5-Step Checklist

After this session is merged and the reviewer verdict is CLEAR (or CONCERNS_RESOLVED):

1. **Consolidate** — `python scripts/consolidate_parquet_cache.py` (30–60 min wall clock on the real 983K-file cache; default `--resume` and 8 workers).
2. **Benchmark** — The run ends with a summary log; optionally re-run `python scripts/consolidate_parquet_cache.py --verify-only` to regenerate the markdown benchmark report. Review `data/consolidation_benchmark_YYYYMMDD_HHMMSS.md` — expect sub-5-second Q2 (single symbol) and sub-60-second Q1 (COUNT DISTINCT).
3. **Repoint** — Edit `config/historical_query.yaml` and change `cache_dir` from `data/databento_cache` to `data/databento_cache_consolidated`. Leave every other field unchanged.
4. **Restart ARGUS** — `./scripts/stop_live.sh && ./scripts/start_live.sh`.
5. **Verify startup log** — Look for `HistoricalQueryService: VIEW 'historical' created over data/databento_cache_consolidated (~24000 Parquet files found)`. If you still see the old count (~983K) the repoint did not take effect.

At no step should `BacktestEngine` or `HistoricalDataFeed` configuration be changed — they continue to consume the original per-month cache.

```json:structured-closeout
{
  "sprint": "31.85",
  "session": 1,
  "verdict_self": "CLEAN",
  "context_state": "GREEN",
  "files_added": [
    "scripts/consolidate_parquet_cache.py",
    "tests/scripts/test_consolidate_parquet_cache.py",
    "docs/operations/parquet-cache-layout.md"
  ],
  "files_modified": [],
  "files_deleted": [],
  "decisions_created": [],
  "defs_resolved": ["DEF-161"],
  "defs_opened": [],
  "script_line_count": 758,
  "tests_added": 15,
  "test_count_baseline": 4919,
  "test_count_after": 4934,
  "test_count_passing": 4931,
  "test_count_preexisting_failures": 3,
  "preexisting_failures": [
    "tests/analytics/test_def159_entry_price_known.py::test_get_todays_pnl_excludes_unrecoverable (DEF-159-adjacent date decay)",
    "tests/core/test_regime_vector_expansion.py::TestHistoryStoreMigration::test_history_store_migration (DEF-137-adjacent date decay)",
    "tests/sprint_runner/test_notifications.py::TestReminderEscalation::test_check_reminder_sends_after_interval (DEF-150 flaky race)"
  ],
  "row_count_validation_non_bypassable": true,
  "original_cache_unmodified": true,
  "historical_query_service_unmodified": true,
  "runtime_dependencies_added": []
}
```
