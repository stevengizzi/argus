#!/usr/bin/env python3
"""Interactive DuckDB query tool for the ARGUS Parquet cache.

Provides a REPL for running SQL queries and built-in dot-commands against
the Databento historical cache. Also supports one-shot non-interactive mode
via --query.

Usage examples:
    python scripts/query_cache.py
    python scripts/query_cache.py --cache-dir /Volumes/LaCie/argus-cache
    python scripts/query_cache.py --query "SELECT COUNT(DISTINCT symbol) FROM historical"
    python scripts/query_cache.py --memory 4096 --threads 8
"""

from __future__ import annotations

import argparse
import os
import readline  # noqa: F401 — enables readline history in input()
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_view(conn: object, cache_dir: str) -> bool:
    """Create the ``historical`` VIEW over all Parquet files.

    Args:
        conn: DuckDB connection.
        cache_dir: Path to the Parquet cache root.

    Returns:
        True if the VIEW was created and is queryable, False otherwise.
    """
    import duckdb  # type: ignore[import-untyped]

    cache_path = Path(cache_dir)
    parquet_files = list(cache_path.glob("**/*.parquet"))
    if not parquet_files:
        print(f"[warn] No Parquet files found in '{cache_dir}'")
        return False

    glob_pattern = str(cache_path.resolve()) + "/**/*.parquet"
    view_sql = f"""
    CREATE OR REPLACE VIEW historical AS
    SELECT
        regexp_extract(filename, '.*/([^/]+)/[^/]+\\.parquet$', 1) AS symbol,
        "timestamp" AS ts_event,
        CAST("timestamp" AS DATE) AS date,
        "open",
        "high",
        "low",
        "close",
        "volume"
    FROM read_parquet('{glob_pattern}', filename=true, union_by_name=true)
    """
    try:
        conn.execute(view_sql)  # type: ignore[union-attr]
        conn.execute("SELECT * FROM historical LIMIT 1").fetchdf()  # type: ignore[union-attr]
        return True
    except duckdb.Error as exc:
        print(f"[error] Failed to create VIEW: {exc}")
        return False


def _print_summary(conn: object, cache_dir: str) -> None:
    """Print schema and basic stats on startup.

    Args:
        conn: DuckDB connection with ``historical`` VIEW created.
        cache_dir: Path to the Parquet cache root.
    """
    try:
        schema_df = conn.execute("DESCRIBE SELECT * FROM historical").fetchdf()  # type: ignore[union-attr]
        print("\nView 'historical' schema:")
        print(schema_df.to_string(index=False))
    except Exception as exc:
        print(f"[warn] Could not describe schema: {exc}")

    try:
        stats = conn.execute(  # type: ignore[union-attr]
            "SELECT COUNT(DISTINCT symbol) AS symbols, COUNT(*) AS total_bars, "
            "MIN(ts_event) AS min_ts, MAX(ts_event) AS max_ts FROM historical"
        ).fetchdf()
        row = stats.iloc[0]
        print(
            f"\nCache: {int(row['symbols'])} symbols, "
            f"{int(row['total_bars']):,} bars, "
            f"{str(row['min_ts'])[:10]} → {str(row['max_ts'])[:10]}"
        )
    except Exception as exc:
        print(f"[warn] Could not compute stats: {exc}")

    # Filesystem size
    total_bytes = sum(
        os.path.getsize(os.path.join(root, f))
        for root, _, files in os.walk(cache_dir)
        for f in files
        if f.endswith(".parquet")
    )
    print(f"Cache size: {total_bytes / 1_048_576:.1f} MB ({cache_dir})")


def _handle_dot_command(conn: object, cmd: str, cache_dir: str) -> None:
    """Handle built-in dot-commands.

    Args:
        conn: DuckDB connection.
        cmd: The command string (e.g., ".symbols", ".coverage AAPL").
        cache_dir: Cache directory path for size calculations.
    """
    parts = cmd.strip().split()
    command = parts[0].lower()

    if command == ".help":
        print(
            "\nAvailable commands:\n"
            "  .schema              Show the historical VIEW column schema\n"
            "  .symbols             List all symbols with bar counts\n"
            "  .coverage [SYMBOL]   Show date range and bar count (all or one symbol)\n"
            "  .tables              List available views\n"
            "  .help                Show this help message\n"
            "  .quit / .exit        Exit the REPL\n"
            "  <SQL>                Execute any SQL query\n"
        )
    elif command == ".schema":
        try:
            df = conn.execute("DESCRIBE SELECT * FROM historical").fetchdf()  # type: ignore[union-attr]
            print(df.to_string(index=False))
        except Exception as exc:
            print(f"[error] {exc}")
    elif command == ".symbols":
        try:
            df = conn.execute(  # type: ignore[union-attr]
                "SELECT symbol, COUNT(*) AS bars FROM historical "
                "GROUP BY symbol ORDER BY symbol"
            ).fetchdf()
            print(df.to_string(index=False))
            print(f"\n{len(df)} symbols total")
        except Exception as exc:
            print(f"[error] {exc}")
    elif command == ".coverage":
        sym = parts[1] if len(parts) > 1 else None
        try:
            if sym:
                df = conn.execute(  # type: ignore[union-attr]
                    "SELECT MIN(ts_event) AS min_date, MAX(ts_event) AS max_date, "
                    "COUNT(*) AS bars FROM historical WHERE symbol = ?",
                    [sym],
                ).fetchdf()
                print(df.to_string(index=False))
            else:
                df = conn.execute(  # type: ignore[union-attr]
                    "SELECT COUNT(DISTINCT symbol) AS symbols, "
                    "MIN(ts_event) AS min_date, MAX(ts_event) AS max_date, "
                    "COUNT(*) AS bars FROM historical"
                ).fetchdf()
                print(df.to_string(index=False))
        except Exception as exc:
            print(f"[error] {exc}")
    elif command == ".tables":
        try:
            df = conn.execute("SHOW TABLES").fetchdf()  # type: ignore[union-attr]
            print(df.to_string(index=False))
        except Exception as exc:
            print(f"[error] {exc}")
    else:
        print(f"Unknown command '{command}'. Type .help for a list of commands.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments, initialize DuckDB, and start the REPL or run one query."""
    parser = argparse.ArgumentParser(
        description="Interactive DuckDB query tool for the ARGUS Parquet cache.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--cache-dir",
        default="data/databento_cache",
        help="Path to the Databento Parquet cache directory (default: data/databento_cache)",
    )
    parser.add_argument(
        "--memory",
        type=int,
        default=2048,
        help="DuckDB memory limit in MB (default: 2048)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="DuckDB worker thread count (default: 4)",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Non-interactive mode: execute this SQL and exit",
    )
    args = parser.parse_args()

    try:
        import duckdb  # type: ignore[import-untyped]
    except ImportError:
        print("[error] duckdb is not installed. Run: pip install duckdb")
        sys.exit(1)

    cache_dir = args.cache_dir
    if not Path(cache_dir).exists():
        print(f"[error] Cache directory not found: {cache_dir}")
        sys.exit(1)

    conn = duckdb.connect(database=":memory:")
    conn.execute(f"SET memory_limit='{args.memory}MB'")
    conn.execute(f"SET threads TO {args.threads}")

    print(f"DuckDB {duckdb.__version__} — cache: {cache_dir}")
    if not _build_view(conn, cache_dir):
        print("[error] Could not build historical VIEW. Check the cache directory.")
        sys.exit(1)

    # Non-interactive mode
    if args.query:
        try:
            df = conn.execute(args.query).fetchdf()
            print(df.to_string(index=False))
        except duckdb.Error as exc:
            print(f"[error] {exc}")
            sys.exit(1)
        conn.close()
        return

    # Interactive REPL
    _print_summary(conn, cache_dir)
    print('\nType SQL queries, dot-commands (.help, .symbols, .coverage, .tables), or .quit\n')

    while True:
        try:
            line = input("duckdb> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue

        if not line:
            continue

        if line.lower() in (".quit", ".exit"):
            break

        if line.startswith("."):
            _handle_dot_command(conn, line, cache_dir)
            continue

        # SQL query
        try:
            df = conn.execute(line).fetchdf()
            print(df.to_string(index=False))
            print(f"({len(df)} rows)")
        except duckdb.Error as exc:
            print(f"[error] {exc}")

    conn.close()
    print("Bye.")


if __name__ == "__main__":
    main()
