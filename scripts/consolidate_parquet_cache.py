#!/usr/bin/env python3
"""One-time consolidation of the Databento Parquet cache.

Merges `data/databento_cache/{SYMBOL}/{YYYY-MM}.parquet` (983K files) into
`data/databento_cache_consolidated/{SYMBOL}/{SYMBOL}.parquet` (~24K files).

The consolidated cache is consumed exclusively by HistoricalQueryService
(DuckDB). The original cache remains read-only and is still consumed by
BacktestEngine via HistoricalDataFeed. This script NEVER mutates the
original cache.

Row-count validation (`consolidated_row_count == sum(monthly_row_counts)`)
is non-bypassable — there is no flag, env var, or code path that disables
it. On mismatch, no output is written for that symbol and the script exits
non-zero.

Sprint 31.85, Session 1 — resolves DEF-161.
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq


_DEFAULT_SOURCE_DIR = "data/databento_cache"
_DEFAULT_DEST_DIR = "data/databento_cache_consolidated"
_DEFAULT_WORKERS = 8
_DEFAULT_MIN_FREE_GB = 60
_BENCHMARK_SAMPLE_COUNT = 100
_PROGRESS_EVERY = 500

logger = logging.getLogger("consolidate_parquet_cache")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Consolidate Databento Parquet cache into per-symbol files",
    )
    parser.add_argument("--source-dir", type=str, default=_DEFAULT_SOURCE_DIR)
    parser.add_argument("--dest-dir", type=str, default=_DEFAULT_DEST_DIR)
    parser.add_argument("--workers", type=int, default=_DEFAULT_WORKERS)
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbol list, or '@/path/to/file.txt'",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N symbols (after filtering)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        help="Skip symbols whose output exists and row count matches source (default)",
    )
    mode.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help="Re-consolidate every symbol even if output exists",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help=(
            "Run DuckDB benchmark queries against the consolidated cache. "
            "May be used standalone (no consolidation) or after consolidation."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without writing anything",
    )
    parser.add_argument(
        "--min-free-gb",
        type=int,
        default=_DEFAULT_MIN_FREE_GB,
        help="Refuse to start with less than N GB free on dest filesystem",
    )
    parser.add_argument(
        "--force-no-disk-check",
        action="store_true",
        help="Skip the free-disk preflight (test-only)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Run verification suite only; skip consolidation entirely",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Result record
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SymbolResult:
    """Per-symbol consolidation outcome.

    Attributes:
        symbol: Ticker symbol.
        monthly_files: Count of source monthly Parquet files.
        source_rows: Sum of rows across all source monthly files.
        dest_rows: Row count in the consolidated output (0 if not written).
        dest_bytes: Size of the consolidated output file in bytes.
        status: One of "written", "skipped_resume", "skipped_empty",
                "skipped_dry_run", "failed_row_count", "failed_io".
        error: Error message when status is a failure, otherwise "".
    """

    symbol: str
    monthly_files: int
    source_rows: int
    dest_rows: int
    dest_bytes: int
    status: str
    error: str


# ---------------------------------------------------------------------------
# Symbol discovery
# ---------------------------------------------------------------------------


def _list_symbol_dirs(source_dir: Path) -> list[str]:
    """Return sorted list of symbol directory names under source_dir."""
    if not source_dir.exists():
        return []
    return sorted(
        d.name
        for d in source_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def _parse_symbols_filter(raw: str | None) -> set[str] | None:
    """Parse --symbols into a set.

    Args:
        raw: Either None, a comma-separated string, or '@path/to/file.txt'
            (one symbol per line; blanks and '#' comments ignored).

    Returns:
        Set of upper-cased symbols, or None if no filter was provided.
    """
    if raw is None:
        return None
    if raw.startswith("@"):
        path = Path(raw[1:])
        contents = path.read_text()
        symbols = {
            line.strip().upper()
            for line in contents.splitlines()
            if line.strip() and not line.strip().startswith("#")
        }
        return symbols
    return {s.strip().upper() for s in raw.split(",") if s.strip()}


# ---------------------------------------------------------------------------
# Per-symbol worker
# ---------------------------------------------------------------------------


def _count_rows(path: Path) -> int:
    """Return row count for a single Parquet file without loading data."""
    # Use metadata for speed; fall back to read_table if metadata absent.
    try:
        return pq.ParquetFile(path).metadata.num_rows
    except Exception:
        return pq.read_table(path).num_rows


def _sum_source_rows(source_files: list[Path]) -> int:
    """Sum row counts across all source monthly Parquet files."""
    return sum(_count_rows(p) for p in source_files)


def consolidate_one_symbol(
    symbol: str,
    source_dir: str,
    dest_dir: str,
    resume: bool,
    force: bool,
    dry_run: bool,
) -> dict:
    """Consolidate one symbol's monthly Parquet files into a single file.

    This function is the worker entry point for ProcessPoolExecutor; it
    must accept only picklable arguments and return a picklable dict.

    Args:
        symbol: Ticker symbol (must match a directory under source_dir).
        source_dir: Root of the original cache.
        dest_dir: Root of the consolidated cache.
        resume: If True, skip when output exists and row counts match.
        force: If True, always re-consolidate (overrides resume).
        dry_run: If True, compute what would be done but write nothing.

    Returns:
        Dict form of SymbolResult.
    """
    source_symbol_dir = Path(source_dir) / symbol
    dest_symbol_dir = Path(dest_dir) / symbol
    dest_final = dest_symbol_dir / f"{symbol}.parquet"
    dest_tmp = dest_symbol_dir / f"{symbol}.parquet.tmp"

    source_files = sorted(source_symbol_dir.glob("*.parquet"))
    if not source_files:
        return asdict(
            SymbolResult(
                symbol=symbol,
                monthly_files=0,
                source_rows=0,
                dest_rows=0,
                dest_bytes=0,
                status="skipped_empty",
                error="",
            )
        )

    source_row_count = _sum_source_rows(source_files)

    if resume and not force and dest_final.exists():
        try:
            existing_rows = _count_rows(dest_final)
        except Exception as exc:
            existing_rows = -1
            logger.warning(
                "%s: failed to read existing output, will re-consolidate: %s",
                symbol,
                exc,
            )
        if existing_rows == source_row_count:
            return asdict(
                SymbolResult(
                    symbol=symbol,
                    monthly_files=len(source_files),
                    source_rows=source_row_count,
                    dest_rows=existing_rows,
                    dest_bytes=dest_final.stat().st_size,
                    status="skipped_resume",
                    error="",
                )
            )
        logger.warning(
            "%s: row-count mismatch on existing output "
            "(existing=%d source=%d) — re-consolidating",
            symbol,
            existing_rows,
            source_row_count,
        )

    if dry_run:
        return asdict(
            SymbolResult(
                symbol=symbol,
                monthly_files=len(source_files),
                source_rows=source_row_count,
                dest_rows=0,
                dest_bytes=0,
                status="skipped_dry_run",
                error="",
            )
        )

    try:
        per_file_counts: list[tuple[str, int]] = []
        tables: list[pa.Table] = []
        for p in source_files:
            tbl = pq.read_table(p)
            per_file_counts.append((p.name, tbl.num_rows))
            tables.append(tbl)

        concatenated = pa.concat_tables(tables, promote_options="default")

        if "timestamp" in concatenated.column_names:
            sort_indices = pc.sort_indices(
                concatenated, sort_keys=[("timestamp", "ascending")]
            )
            concatenated = concatenated.take(sort_indices)

        if "symbol" in concatenated.column_names:
            concatenated = concatenated.drop(["symbol"])
        symbol_col = pa.array([symbol] * concatenated.num_rows, type=pa.string())
        concatenated = concatenated.append_column("symbol", symbol_col)

        expected = sum(c for _, c in per_file_counts)
        actual = concatenated.num_rows
        if actual != expected:
            logger.error(
                "%s: ROW COUNT MISMATCH — expected=%d actual=%d per_file=%s",
                symbol,
                expected,
                actual,
                per_file_counts,
            )
            if dest_tmp.exists():
                try:
                    dest_tmp.unlink()
                except OSError:
                    pass
            return asdict(
                SymbolResult(
                    symbol=symbol,
                    monthly_files=len(source_files),
                    source_rows=expected,
                    dest_rows=actual,
                    dest_bytes=0,
                    status="failed_row_count",
                    error=(
                        f"expected={expected} actual={actual} "
                        f"per_file={per_file_counts}"
                    ),
                )
            )

        dest_symbol_dir.mkdir(parents=True, exist_ok=True)
        if dest_tmp.exists():
            try:
                dest_tmp.unlink()
            except OSError:
                pass

        pq.write_table(concatenated, dest_tmp, compression="zstd")

        os.rename(dest_tmp, dest_final)

        return asdict(
            SymbolResult(
                symbol=symbol,
                monthly_files=len(source_files),
                source_rows=expected,
                dest_rows=actual,
                dest_bytes=dest_final.stat().st_size,
                status="written",
                error="",
            )
        )
    except Exception as exc:
        logger.exception("%s: unexpected error during consolidation", symbol)
        if dest_tmp.exists():
            try:
                dest_tmp.unlink()
            except OSError:
                pass
        return asdict(
            SymbolResult(
                symbol=symbol,
                monthly_files=len(source_files),
                source_rows=source_row_count,
                dest_rows=0,
                dest_bytes=0,
                status="failed_io",
                error=str(exc),
            )
        )


# ---------------------------------------------------------------------------
# Disk preflight
# ---------------------------------------------------------------------------


def check_disk_space(dest_dir: Path, min_free_gb: int) -> tuple[bool, float]:
    """Return (ok, free_gb) for the filesystem containing dest_dir."""
    probe = dest_dir
    while not probe.exists():
        if probe.parent == probe:
            break
        probe = probe.parent
    usage = shutil.disk_usage(probe)
    free_gb = usage.free / (1024 ** 3)
    return (free_gb >= min_free_gb, free_gb)


# ---------------------------------------------------------------------------
# DuckDB verification suite
# ---------------------------------------------------------------------------


def run_verification(dest_dir: Path, benchmark_out_path: Path) -> int:
    """Run the three DuckDB benchmark queries and write a Markdown report.

    Args:
        dest_dir: Consolidated cache directory.
        benchmark_out_path: Destination file for the Markdown report.

    Returns:
        Exit code contribution (0 always — thresholds are informational).
    """
    import duckdb

    files = sorted(dest_dir.glob("*/*.parquet"))
    if not files:
        logger.error("Verify: no consolidated Parquet files under %s", dest_dir)
        return 1

    glob_pattern = f"{dest_dir.resolve()}/**/*.parquet"

    sample_symbols: list[str] = []
    step = max(1, len(files) // _BENCHMARK_SAMPLE_COUNT)
    for idx in range(0, len(files), step):
        if len(sample_symbols) >= _BENCHMARK_SAMPLE_COUNT:
            break
        sample_symbols.append(files[idx].parent.name)

    # Q2 needs a real single symbol file. Use the first available.
    single_symbol = files[0].parent.name
    single_symbol_path = files[0]

    conn = duckdb.connect(":memory:")
    conn.execute("SET memory_limit='2048MB'")
    conn.execute("SET threads TO 4")

    results: list[dict] = []

    # Q1: COUNT(DISTINCT symbol)
    sql1 = (
        f"SELECT COUNT(DISTINCT symbol) "
        f"FROM read_parquet('{glob_pattern}', union_by_name=true)"
    )
    t0 = time.perf_counter()
    q1_value = conn.execute(sql1).fetchone()[0]
    q1_elapsed = time.perf_counter() - t0
    q1_pass = q1_elapsed < 60.0
    results.append(
        {
            "name": "Q1 COUNT(DISTINCT symbol)",
            "value": q1_value,
            "elapsed_s": q1_elapsed,
            "threshold_s": 60.0,
            "pass": q1_pass,
        }
    )

    # Q2: single-symbol range
    sql2 = (
        f"SELECT COUNT(*) FROM read_parquet('{single_symbol_path}') "
        f"WHERE timestamp >= '2025-01-01' AND timestamp < '2025-02-01'"
    )
    t0 = time.perf_counter()
    q2_value = conn.execute(sql2).fetchone()[0]
    q2_elapsed = time.perf_counter() - t0
    q2_pass = q2_elapsed < 5.0
    results.append(
        {
            "name": f"Q2 single-symbol range ({single_symbol})",
            "value": q2_value,
            "elapsed_s": q2_elapsed,
            "threshold_s": 5.0,
            "pass": q2_pass,
        }
    )

    # Q3: batch coverage check over sampled symbols
    placeholders = ",".join(f"'{s}'" for s in sample_symbols)
    sql3 = (
        f"SELECT symbol, COUNT(*) AS bars "
        f"FROM read_parquet('{glob_pattern}', union_by_name=true) "
        f"WHERE symbol IN ({placeholders}) "
        f"AND timestamp >= '2025-01-01' AND timestamp < '2025-02-01' "
        f"GROUP BY symbol"
    )
    t0 = time.perf_counter()
    q3_rows = conn.execute(sql3).fetchall()
    q3_elapsed = time.perf_counter() - t0
    q3_pass = q3_elapsed < 30.0
    results.append(
        {
            "name": f"Q3 batch coverage ({len(sample_symbols)} sampled symbols)",
            "value": len(q3_rows),
            "elapsed_s": q3_elapsed,
            "threshold_s": 30.0,
            "pass": q3_pass,
        }
    )

    conn.close()

    lines: list[str] = []
    lines.append(
        f"# Consolidated Cache Benchmark — "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    lines.append("")
    lines.append(f"Cache dir: `{dest_dir}`")
    lines.append(f"Consolidated files: {len(files)}")
    lines.append(
        "Sampling rule for Q3: every (total // 100)th file after sorted "
        "directory listing."
    )
    lines.append("")
    any_miss = any(not r["pass"] for r in results)
    if any_miss:
        lines.append(
            "> **WARNING:** One or more queries exceeded their informational "
            "threshold. Thresholds are advisory; the hard pass/fail is "
            "row-count validation during consolidation itself."
        )
        lines.append("")
    lines.append("| Query | Value | Elapsed | Threshold | Pass |")
    lines.append("|-------|-------|---------|-----------|------|")
    for r in results:
        lines.append(
            f"| {r['name']} | {r['value']} | "
            f"{r['elapsed_s']:.3f} s | < {r['threshold_s']:.1f} s | "
            f"{'YES' if r['pass'] else 'NO'} |"
        )
    report = "\n".join(lines) + "\n"

    print(report)
    benchmark_out_path.parent.mkdir(parents=True, exist_ok=True)
    benchmark_out_path.write_text(report)
    logger.info("Verify: benchmark report written to %s", benchmark_out_path)
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _configure_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on full success or pure skip, 1 if any symbol failed
        row-count validation, disk preflight failed, or the verify suite
        could not run.
    """
    _configure_logging()
    args = parse_args(argv)

    source_dir = Path(args.source_dir)
    dest_dir = Path(args.dest_dir)
    resume = not args.force  # --resume is the default
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.verify_only:
        dest_dir.mkdir(parents=True, exist_ok=True)
        benchmark_path = Path("data") / f"consolidation_benchmark_{ts}.md"
        return run_verification(dest_dir, benchmark_path)

    if not args.force_no_disk_check:
        ok, free_gb = check_disk_space(dest_dir, args.min_free_gb)
        logger.info(
            "Preflight: %.1f GB free on %s (minimum %d GB)",
            free_gb,
            dest_dir,
            args.min_free_gb,
        )
        if not ok:
            logger.error(
                "Insufficient disk space: %.1f GB free, %d GB required. "
                "Use --force-no-disk-check to override (test-only).",
                free_gb,
                args.min_free_gb,
            )
            return 1

    all_symbols = _list_symbol_dirs(source_dir)
    if not all_symbols:
        logger.error("No symbol directories found under %s", source_dir)
        return 1

    filter_set = _parse_symbols_filter(args.symbols)
    if filter_set is not None:
        all_symbols = [s for s in all_symbols if s.upper() in filter_set]

    if args.limit is not None:
        all_symbols = all_symbols[: args.limit]

    total = len(all_symbols)
    if total == 0:
        logger.error("Symbol filter eliminated all candidates — nothing to do")
        return 1

    logger.info(
        "Starting: symbols=%d workers=%d source=%s dest=%s resume=%s "
        "force=%s dry_run=%s",
        total,
        args.workers,
        source_dir,
        dest_dir,
        resume,
        args.force,
        args.dry_run,
    )

    if args.dry_run:
        for sym in all_symbols:
            files = list((source_dir / sym).glob("*.parquet"))
            logger.info(
                "[dry-run] %s: %d monthly files would be consolidated",
                sym,
                len(files),
            )
        logger.info("[dry-run] complete — nothing written")
        return 0

    dest_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    start_time = time.perf_counter()
    written_bytes = 0
    succeeded = 0
    skipped = 0
    failed = 0

    if args.workers <= 1:
        for sym in all_symbols:
            res = consolidate_one_symbol(
                sym,
                str(source_dir),
                str(dest_dir),
                resume=resume,
                force=args.force,
                dry_run=False,
            )
            results.append(res)
            succeeded, skipped, failed, written_bytes = _tally(
                res, succeeded, skipped, failed, written_bytes
            )
            _maybe_progress(
                len(results), total, written_bytes, start_time
            )
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(
                    consolidate_one_symbol,
                    sym,
                    str(source_dir),
                    str(dest_dir),
                    resume,
                    args.force,
                    False,
                ): sym
                for sym in all_symbols
            }
            for future in as_completed(futures):
                res = future.result()
                results.append(res)
                succeeded, skipped, failed, written_bytes = _tally(
                    res, succeeded, skipped, failed, written_bytes
                )
                _maybe_progress(
                    len(results), total, written_bytes, start_time
                )

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Done: succeeded=%d skipped=%d failed=%d bytes=%.2f GB elapsed=%.1fs",
        succeeded,
        skipped,
        failed,
        written_bytes / (1024 ** 3),
        elapsed,
    )

    exit_code = 1 if failed > 0 else 0

    if args.verify:
        benchmark_path = Path("data") / f"consolidation_benchmark_{ts}.md"
        verify_rc = run_verification(dest_dir, benchmark_path)
        if verify_rc != 0 and exit_code == 0:
            exit_code = verify_rc

    return exit_code


def _tally(
    res: dict,
    succeeded: int,
    skipped: int,
    failed: int,
    written_bytes: int,
) -> tuple[int, int, int, int]:
    status = res["status"]
    if status == "written":
        succeeded += 1
        written_bytes += res["dest_bytes"]
    elif status.startswith("skipped"):
        skipped += 1
    elif status.startswith("failed"):
        failed += 1
    return succeeded, skipped, failed, written_bytes


def _maybe_progress(
    done: int, total: int, written_bytes: int, start_time: float
) -> None:
    if done % _PROGRESS_EVERY != 0:
        return
    elapsed = time.perf_counter() - start_time
    rate = done / elapsed if elapsed > 0 else 0.0
    remaining = (total - done) / rate if rate > 0 else 0.0
    logger.info(
        "Progress: %d/%d symbols consolidated (%.2f GB written, %.1fs "
        "elapsed, ~%.0fs ETA)",
        done,
        total,
        written_bytes / (1024 ** 3),
        elapsed,
        remaining,
    )


if __name__ == "__main__":
    sys.exit(main())
