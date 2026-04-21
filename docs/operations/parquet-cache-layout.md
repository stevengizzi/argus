# Parquet Cache Layout — Operator Reference

> Sprint 31.85. Resolves DEF-161.
> ARGUS maintains two Parquet caches after this sprint. Confusing them is a latent
> data-integrity risk. This document is the canonical reference.

## Cache Separation

| Cache | Path | Layout | Consumers | Writable? |
|-------|------|--------|-----------|-----------|
| **Original** | `data/databento_cache/` | `{SYMBOL}/{YYYY-MM}.parquet` (~983K files) | `BacktestEngine` via `HistoricalDataFeed`; `scripts/resolve_symbols_fast.py`; `scripts/populate_historical_cache.py`; `scripts/run_experiment.py --cache-dir`; `argus/backtest/data_fetcher.py` | **NO — read-only. Source of truth.** |
| **Consolidated** | `data/databento_cache_consolidated/` | `{SYMBOL}/{SYMBOL}.parquet` (~24K files) with embedded `symbol` column | `HistoricalQueryService` (DuckDB) via `config/historical_query.yaml` | Rebuilt by `scripts/consolidate_parquet_cache.py`. Derived artifact. |

**Invariant:** `BacktestEngine` must never be pointed at the consolidated cache — it
expects per-month files and will silently miss data if pointed elsewhere.
Conversely, `HistoricalQueryService` should be pointed at the consolidated cache
for query performance; pointing it at the original cache is functionally correct
but impractically slow (VIEW scans take hours, TABLE materialization takes 16+
hours).

## Consolidation Script

`scripts/consolidate_parquet_cache.py` merges the original cache's per-month files
into one file per symbol with an embedded `symbol` column. The original cache is
never modified.

### Synopsis

```bash
# Full consolidation (default: --resume, 8 workers, zstd compression):
python scripts/consolidate_parquet_cache.py

# Dry run — report symbol count without writing:
python scripts/consolidate_parquet_cache.py --dry-run

# Consolidate then run DuckDB benchmark suite:
python scripts/consolidate_parquet_cache.py --verify

# Benchmark an existing consolidated cache (no consolidation):
python scripts/consolidate_parquet_cache.py --verify-only

# Force re-consolidation of a specific subset for diagnostics:
python scripts/consolidate_parquet_cache.py --force --symbols AAPL,SPY,QQQ
```

### Common Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--source-dir` | `data/databento_cache` | Original cache (read-only input). |
| `--dest-dir` | `data/databento_cache_consolidated` | Consolidated cache (output). |
| `--workers` | 8 | `ProcessPoolExecutor` pool size. |
| `--symbols` | (all) | Restrict to comma-separated symbols or `@path/to/file.txt`. |
| `--limit` | (none) | Process only the first N symbols after sort+filter. |
| `--resume` | on | Skip symbols whose output exists and row count matches source. |
| `--force` | off | Re-consolidate every symbol regardless of existing output. |
| `--verify` | off | After consolidation, run three DuckDB benchmark queries. |
| `--verify-only` | off | Run the benchmark suite without any consolidation. |
| `--dry-run` | off | Enumerate work without writing anything. |
| `--min-free-gb` | 60 | Refuse to start with less than N GB free on `--dest-dir`. |

### When to Re-Run

Re-run after any operation that adds data to the original cache, in particular
after `scripts/populate_historical_cache.py --update` has pulled new months. The
default `--resume` behavior makes re-runs cheap: only symbols whose source row
count grew are re-consolidated.

## Verifying Cache Health

Run the benchmark suite against an already-consolidated cache:

```bash
python scripts/consolidate_parquet_cache.py --verify-only
```

The suite writes a Markdown report to `data/consolidation_benchmark_{YYYYMMDD_HHMMSS}.md`
and prints it to stdout. The three queries are:

| # | Query | Informational threshold |
|---|-------|-------------------------|
| Q1 | `COUNT(DISTINCT symbol)` over the full glob | < 60 s |
| Q2 | Single-symbol one-month range scan | < 5 s |
| Q3 | Batch coverage check across 100 sampled symbols, one-month range | < 30 s |

**Thresholds are informational.** The hard data-integrity gate is the non-
bypassable row-count validation that runs during consolidation itself — any
symbol whose `consolidated_row_count != sum(monthly_row_counts)` fails, no
output is written for that symbol, and the script exits non-zero.

The 100 sample symbols in Q3 are chosen deterministically: every
`(total // 100)`th entry in the sorted consolidated-file list.

## Activating the Consolidated Cache

> **This is an operator action, not part of Sprint 31.85.**

After a successful consolidation run and acceptable benchmark results:

1. **Confirm the benchmark report** at `data/consolidation_benchmark_*.md` is
   reasonable (sub-10s single-symbol queries, sub-60s COUNT DISTINCT).
2. **Edit `config/historical_query.yaml`** and change `cache_dir` from
   `data/databento_cache` to `data/databento_cache_consolidated`. Leave every
   other field unchanged.
3. **Restart ARGUS** (`./scripts/stop_live.sh && ./scripts/start_live.sh`).
4. **Verify the startup log** contains an entry like:
   `HistoricalQueryService: VIEW 'historical' created over data/databento_cache_consolidated (~24000 Parquet files found)`
5. **Leave `BacktestEngine` configuration untouched** — it continues to consume
   the original cache at `data/databento_cache`.

## Known Limitations

- `os.rename` is not guaranteed atomic across filesystems. Keep `--source-dir`
  and `--dest-dir` on the same filesystem. If you need them on different
  filesystems, invoke the script on each filesystem independently.
- The per-symbol worker concatenates every month of data for a symbol in
  memory. For unusually large symbols (e.g., several years of 1-min bars), this
  can peak at ~1–2 GB of resident memory per worker. Reduce `--workers` if your
  host is memory-constrained.
- `HistoricalQueryService`, its config model, and `config/historical_query.yaml`
  are NOT modified by this sprint. Repointing is an operator step.

## Row-Count Validation Is Non-Bypassable

By design, there is no `--skip-validation` flag, no environment variable, and
no code path that disables the
`consolidated_row_count == sum(monthly_row_counts)` assertion. Silent data
loss is the failure mode this sprint was designed to prevent; bypassing the
check would re-introduce it. If you believe a validated mismatch is a false
positive, file a DEF entry rather than patching the script.
