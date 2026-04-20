#!/usr/bin/env python3
"""Fast symbol resolution via direct Parquet reads — no DuckDB.

Reads 3 sample months per symbol (early/mid/late in date range) to estimate
avg price and volume, then applies universe filter criteria. Produces the
same symbols_{pattern}.txt output as resolve_sweep_symbols.py.

Usage:
    python scripts/resolve_symbols_fast.py --all-patterns
    python scripts/resolve_symbols_fast.py --pattern bull_flag
    python scripts/resolve_symbols_fast.py --all-patterns --date-range 2018-05-01,2026-02-28

Sprint 31.75, Session 4 — pragmatic replacement for DuckDB-based resolver.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import yaml


_DEFAULT_CACHE_DIR = "data/databento_cache"
_DEFAULT_OUTPUT_DIR = "data/sweep_logs"
_FILTERS_DIR = Path("config/universe_filters")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Fast symbol resolution via Parquet sampling",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pattern", type=str, help="Single pattern to resolve")
    group.add_argument(
        "--all-patterns", action="store_true", help="Resolve all patterns",
    )
    parser.add_argument(
        "--cache-dir", type=str, default=_DEFAULT_CACHE_DIR,
    )
    parser.add_argument(
        "--output-dir", type=str, default=_DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--date-range",
        type=str,
        default="2018-05-01,2026-02-28",
        help="Start,end ISO dates for Parquet file selection",
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="Parallel workers",
    )
    parser.add_argument(
        "--min-bars", type=int, default=100, help="Min total bars for coverage",
    )
    return parser.parse_args(argv)


def _get_symbol_dirs(cache_dir: str) -> list[str]:
    """List all symbol directories in cache.

    Args:
        cache_dir: Path to the Parquet cache root.

    Returns:
        Sorted list of symbol directory names.
    """
    cache_path = Path(cache_dir)
    return sorted(
        d.name
        for d in cache_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def _months_in_range(start: str, end: str) -> list[str]:
    """Generate YYYY-MM strings within a date range.

    Args:
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).

    Returns:
        List of YYYY-MM strings covering the range.
    """
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    months: list[str] = []
    y, m = s.year, s.month
    while (y, m) <= (e.year, e.month):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _sample_symbol(
    args: tuple[str, str, list[str]],
) -> tuple[str, float, float, int] | None:
    """Read sample Parquet files for one symbol.

    Reads 3 representative files (early/mid/late) to estimate avg close
    and avg volume without scanning the entire symbol's data.

    Args:
        args: Tuple of (symbol, cache_dir, valid_months).

    Returns:
        (symbol, avg_close, avg_volume, estimated_total_bars) or None
        if the symbol has no data in the date range.
    """
    symbol, cache_dir, valid_months = args
    symbol_dir = Path(cache_dir) / symbol

    available: list[Path] = []
    for m in valid_months:
        f = symbol_dir / f"{m}.parquet"
        if f.exists():
            available.append(f)

    if not available:
        return None

    # Sample 3 files: early, middle, late
    if len(available) >= 3:
        indices = [0, len(available) // 2, -1]
        sample_files = [available[i] for i in indices]
    else:
        sample_files = available

    # Read sample files and aggregate to daily level for volume
    daily_closes: list[float] = []
    daily_volumes: list[float] = []
    total_bars = 0

    for f in sample_files:
        try:
            table = pq.read_table(f, columns=["timestamp", "close", "volume"])
            df = table.to_pandas()
            if df.empty:
                continue
            total_bars += len(df)
            df["_date"] = pd.to_datetime(df["timestamp"]).dt.date
            daily = df.groupby("_date").agg(
                {"close": "last", "volume": "sum"},
            )
            daily_closes.extend(daily["close"].tolist())
            daily_volumes.extend(daily["volume"].tolist())
        except Exception:
            continue

    if not daily_closes:
        return None

    avg_close = sum(daily_closes) / len(daily_closes)
    avg_volume = sum(daily_volumes) / len(daily_volumes)
    est_total_bars = int(total_bars / len(sample_files) * len(available))

    return (symbol, avg_close, avg_volume, est_total_bars)


def _resolve_pattern(
    pattern_name: str,
    filter_config: dict,
    symbols_with_stats: list[tuple[str, float, float, int]],
    min_bars: int,
    output_dir: str,
) -> int:
    """Apply a pattern's filter criteria and write symbol file.

    Args:
        pattern_name: Pattern name for the output filename.
        filter_config: Raw YAML dict with filter criteria.
        symbols_with_stats: Pre-computed (symbol, avg_close, avg_vol, bars).
        min_bars: Minimum estimated bar count for coverage.
        output_dir: Directory for output files.

    Returns:
        Number of symbols that passed the filter.
    """
    min_price = filter_config.get("min_price", 0)
    max_price = filter_config.get("max_price", float("inf"))
    min_avg_volume = filter_config.get("min_avg_volume", 0)

    passed: list[str] = []
    for symbol, avg_close, avg_volume, est_bars in symbols_with_stats:
        if avg_close < min_price:
            continue
        if avg_close > max_price:
            continue
        if avg_volume < min_avg_volume:
            continue
        if est_bars < min_bars:
            continue
        passed.append(symbol)

    out_path = Path(output_dir) / f"symbols_{pattern_name}.txt"
    out_path.write_text("\n".join(sorted(passed)) + "\n")
    return len(passed)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the fast symbol resolver.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 success, 1 error).
    """
    args = parse_args(argv)

    start, end = [s.strip() for s in args.date_range.split(",")]
    valid_months = _months_in_range(start, end)
    print(f"Date range: {start} to {end} ({len(valid_months)} months)")

    t0 = time.time()
    all_symbols = _get_symbol_dirs(args.cache_dir)
    print(f"Cache contains {len(all_symbols)} symbol directories")

    # Parallel Parquet sampling
    print(f"Sampling Parquet files with {args.workers} workers...")
    work_items = [(sym, args.cache_dir, valid_months) for sym in all_symbols]

    symbols_with_stats: list[tuple[str, float, float, int]] = []
    failed = 0

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_sample_symbol, item): item[0]
            for item in work_items
        }
        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            if done_count % 5000 == 0:
                elapsed = time.time() - t0
                print(
                    f"  ... sampled {done_count}/{len(all_symbols)} "
                    f"symbols ({elapsed:.0f}s)",
                )
            result = future.result()
            if result is not None:
                symbols_with_stats.append(result)
            else:
                failed += 1

    elapsed = time.time() - t0
    print(
        f"Sampled {len(symbols_with_stats)} symbols "
        f"({failed} empty/failed) in {elapsed:.1f}s",
    )

    # Discover patterns
    os.makedirs(args.output_dir, exist_ok=True)

    if args.all_patterns:
        pattern_files = sorted(_FILTERS_DIR.glob("*.yaml"))
        patterns = [
            (f.stem, yaml.safe_load(f.read_text()) or {})
            for f in pattern_files
        ]
    else:
        filter_path = _FILTERS_DIR / f"{args.pattern}.yaml"
        if not filter_path.exists():
            print(f"ERROR: {filter_path} not found")
            return 1
        patterns = [
            (args.pattern, yaml.safe_load(filter_path.read_text()) or {}),
        ]

    # Apply filters per pattern
    print(f"\nResolving {len(patterns)} patterns:")
    for pattern_name, filter_config in patterns:
        count = _resolve_pattern(
            pattern_name,
            filter_config,
            symbols_with_stats,
            args.min_bars,
            args.output_dir,
        )
        print(f"  {pattern_name}: {count} symbols")

    total_elapsed = time.time() - t0
    print(f"\nDone in {total_elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
