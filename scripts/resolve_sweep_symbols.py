#!/usr/bin/env python3
"""Pre-resolve symbol lists for overnight pattern sweeps.

Separates the slow DuckDB symbol resolution step (this script) from the fast
parallel backtest step (run_experiment.py).  Output files written to
``data/sweep_logs/symbols_{pattern}.txt`` can be fed directly to
``run_experiment.py`` via ``--symbols @filepath``.

Usage:
    # Single pattern
    python scripts/resolve_sweep_symbols.py --pattern bull_flag --date-range 2025-01-01,2025-12-31

    # All 10 patterns in one invocation (reuses a single DuckDB connection)
    python scripts/resolve_sweep_symbols.py --all-patterns --date-range 2025-01-01,2025-12-31

Sprint 31.75, Session 3b.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

# Allow importing from the project root (for run_experiment helpers).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from argus.core.config import UniverseFilterConfig
from argus.data.historical_query_config import HistoricalQueryConfig
from argus.data.historical_query_service import HistoricalQueryService

# Re-use the canonical set of dynamic filter field names from run_experiment so
# both scripts stay in sync if the list ever changes.
from scripts.run_experiment import _DYNAMIC_FILTER_FIELDS  # noqa: E402

_UNIVERSE_FILTERS_DIR = Path("config/universe_filters")
_DEFAULT_CACHE_DIR = "data/databento_cache"
_DEFAULT_OUTPUT_DIR = "data/sweep_logs"
_DEFAULT_PERSIST_DB = "data/historical_query.duckdb"

logger = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Pre-resolve universe symbols for ARGUS sweep runs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resolve symbols for one pattern
  python scripts/resolve_sweep_symbols.py --pattern bull_flag --date-range 2025-01-01,2025-12-31

  # Resolve all 10 patterns (single DuckDB connection)
  python scripts/resolve_sweep_symbols.py --all-patterns --date-range 2025-01-01,2025-12-31

  # Custom cache dir and output
  python scripts/resolve_sweep_symbols.py --all-patterns --date-range 2025-01-01,2025-12-31 \\
      --cache-dir data/databento_cache --output-dir data/sweep_logs
""",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--pattern",
        type=str,
        help="Pattern name to resolve (e.g. bull_flag, flat_top_breakout)",
    )
    group.add_argument(
        "--all-patterns",
        action="store_true",
        help="Resolve all patterns found in config/universe_filters/",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=_DEFAULT_CACHE_DIR,
        help=f"Parquet cache directory (default: {_DEFAULT_CACHE_DIR})",
    )
    parser.add_argument(
        "--date-range",
        type=str,
        required=True,
        help="start,end ISO dates (e.g. 2025-01-01,2025-12-31)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Directory for output symbol files (default: {_DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--persist-db",
        type=str,
        default=_DEFAULT_PERSIST_DB,
        help=f"Persistent DuckDB path (default: {_DEFAULT_PERSIST_DB})",
    )
    parser.add_argument(
        "--min-bars",
        type=int,
        default=100,
        help="Minimum bar count for coverage validation (default: 100)",
    )
    return parser.parse_args(argv)


def _parse_date_range(raw: str) -> tuple[str, str]:
    """Parse a ``start,end`` date range string.

    Args:
        raw: Comma-separated ISO dates.

    Returns:
        Tuple of (start_date, end_date).

    Raises:
        SystemExit: If the format is invalid.
    """
    parts = raw.split(",")
    if len(parts) != 2:  # noqa: PLR2004
        print(f"ERROR: --date-range must be 'start,end' ISO dates, got: {raw}")
        sys.exit(1)
    return parts[0].strip(), parts[1].strip()


def _load_filter_config(pattern_name: str) -> UniverseFilterConfig | None:
    """Load a UniverseFilterConfig for the given pattern name.

    Args:
        pattern_name: Pattern name (without .yaml extension).

    Returns:
        Parsed UniverseFilterConfig, or None if the file does not exist.
    """
    filter_path = _UNIVERSE_FILTERS_DIR / f"{pattern_name}.yaml"
    if not filter_path.exists():
        logger.warning("No universe filter YAML for pattern '%s' at %s", pattern_name, filter_path)
        return None
    raw = yaml.safe_load(filter_path.read_text()) or {}
    return UniverseFilterConfig(**raw)


def _discover_patterns() -> list[str]:
    """Discover all pattern names from config/universe_filters/*.yaml.

    Returns:
        Sorted list of pattern names (without .yaml extension).
    """
    return sorted(p.stem for p in _UNIVERSE_FILTERS_DIR.glob("*.yaml"))


def _count_cache_symbols(service: HistoricalQueryService) -> int:
    """Count distinct symbols present in the historical VIEW.

    Args:
        service: Initialized HistoricalQueryService.

    Returns:
        Number of distinct symbols, or 0 if the query fails.
    """
    try:
        df = service.query("SELECT COUNT(DISTINCT symbol) AS n FROM historical", [])
        if df.empty:
            return 0
        return int(df.iloc[0]["n"])
    except Exception:
        logger.debug("Could not count cache symbols", exc_info=True)
        return 0


def _apply_static_filters(
    service: HistoricalQueryService,
    filter_config: UniverseFilterConfig,
    start_date: str,
    end_date: str,
) -> list[str]:
    """Apply static price and volume filters against the historical VIEW.

    Dynamic filters that require real-time or reference data are logged as
    skipped.  Applies ``min_price``, ``max_price``, and ``min_avg_volume``
    as HAVING clauses on period averages.

    Args:
        service: Initialized HistoricalQueryService (kept open by caller).
        filter_config: UniverseFilterConfig with filter criteria.
        start_date: Inclusive start date (YYYY-MM-DD).
        end_date: Inclusive end date (YYYY-MM-DD).

    Returns:
        Sorted list of symbols that pass all applicable static filters.
    """
    for field_name in _DYNAMIC_FILTER_FIELDS:
        value = getattr(filter_config, field_name)
        is_non_empty = value is not None and value != [] and value != ""
        if is_non_empty:
            logger.warning(
                "Skipping dynamic filter '%s' (not applicable to historical sweeps)",
                field_name,
            )

    having_clauses: list[str] = ["1=1"]
    if filter_config.min_price is not None:
        having_clauses.append(f"AVG(close) >= {filter_config.min_price}")
    if filter_config.max_price is not None:
        having_clauses.append(f"AVG(close) <= {filter_config.max_price}")
    if filter_config.min_avg_volume is not None:
        having_clauses.append(f"AVG(volume) >= {filter_config.min_avg_volume}")

    having_sql = " AND ".join(having_clauses)
    sql = (
        "SELECT symbol "
        "FROM historical "
        "WHERE date >= ? AND date <= ? "
        "GROUP BY symbol "
        f"HAVING {having_sql}"
    )

    df = service.query(sql, [start_date, end_date])
    if df.empty:
        return []
    return sorted(df["symbol"].tolist())


def _resolve_one_pattern(
    service: HistoricalQueryService,
    pattern_name: str,
    filter_config: UniverseFilterConfig,
    start_date: str,
    end_date: str,
    min_bars: int,
    output_dir: Path,
    cache_total: int,
) -> int:
    """Resolve and write the symbol file for a single pattern.

    Args:
        service: Initialized HistoricalQueryService (kept open by caller).
        pattern_name: Pattern name used for output filename.
        filter_config: Universe filter criteria.
        start_date: Inclusive start date.
        end_date: Inclusive end date.
        min_bars: Minimum bar count for coverage validation.
        output_dir: Directory to write symbol files.
        cache_total: Pre-computed total symbols in cache (for summary line).

    Returns:
        Number of symbols written to the output file.
    """
    # Apply static price/volume filters
    filtered = _apply_static_filters(service, filter_config, start_date, end_date)
    after_filter = len(filtered)

    # Coverage validation: drop symbols without sufficient bar data
    coverage = service.validate_symbol_coverage(filtered, start_date, end_date, min_bars)
    covered = sorted(sym for sym in filtered if coverage.get(sym, False))
    after_coverage = len(covered)

    # Write output file (one symbol per line, sorted)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"symbols_{pattern_name}.txt"
    output_file.write_text("\n".join(covered) + ("\n" if covered else ""))

    # Print summary line
    print(
        f"{pattern_name}: {cache_total} in cache → {after_filter} after filter "
        f"→ {after_coverage} after coverage → {output_file.name}"
    )

    return after_coverage


def main(argv: list[str] | None = None) -> int:
    """Entry point for the resolve_sweep_symbols CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 success, 1 error).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args(argv)

    start_date, end_date = _parse_date_range(args.date_range)
    output_dir = Path(args.output_dir)

    # Build the list of patterns to process
    if args.all_patterns:
        patterns = _discover_patterns()
        if not patterns:
            print(f"ERROR: No universe filter YAMLs found in {_UNIVERSE_FILTERS_DIR}")
            return 1
    else:
        patterns = [args.pattern]

    # Open ONE HistoricalQueryService instance for all patterns
    service = HistoricalQueryService(
        HistoricalQueryConfig(
            enabled=True,
            cache_dir=args.cache_dir,
            persist_path=args.persist_db,
        )
    )

    if not service.is_available:
        print(
            f"ERROR: HistoricalQueryService unavailable — "
            f"cache not found or empty at: {args.cache_dir}"
        )
        return 1

    # Count total symbols once (shared across all patterns)
    cache_total = _count_cache_symbols(service)

    total_written = 0
    failed_patterns: list[str] = []

    print(f"Resolving symbols for {len(patterns)} pattern(s) "
          f"({start_date} → {end_date}, min_bars={args.min_bars})")
    print()

    for pattern_name in patterns:
        filter_config = _load_filter_config(pattern_name)
        if filter_config is None:
            print(f"{pattern_name}: SKIPPED (no filter YAML)")
            failed_patterns.append(pattern_name)
            continue

        try:
            count = _resolve_one_pattern(
                service=service,
                pattern_name=pattern_name,
                filter_config=filter_config,
                start_date=start_date,
                end_date=end_date,
                min_bars=args.min_bars,
                output_dir=output_dir,
                cache_total=cache_total,
            )
            total_written += count
        except Exception:
            logger.exception("Failed to resolve symbols for pattern '%s'", pattern_name)
            failed_patterns.append(pattern_name)

    service.close()

    # Grand total summary (always printed for --all-patterns; also for single)
    print()
    print(f"Grand total: {total_written} symbols written across {len(patterns)} pattern(s)")
    if failed_patterns:
        print(f"Failed patterns: {', '.join(failed_patterns)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
