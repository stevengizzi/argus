#!/usr/bin/env python3
"""CLI entry point for running parameterized pattern experiment sweeps.

Usage:
    python scripts/run_experiment.py --pattern bull_flag
    python scripts/run_experiment.py --pattern bull_flag --params pole_min_move_pct,flag_max_bars
    python scripts/run_experiment.py --pattern bull_flag --dry-run
    python scripts/run_experiment.py --pattern bull_flag --date-range 2025-01-01,2025-12-31
    python scripts/run_experiment.py --pattern bull_flag --cache-dir data/databento_cache
    python scripts/run_experiment.py --pattern narrow_range_breakout --universe-filter
    python scripts/run_experiment.py --pattern bull_flag --symbols AAPL,NVDA,TSLA

Sprint 32, Session 8. Universe-aware sweep flags added Sprint 31A.75, Session 1.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

from argus.core.config import UniverseFilterConfig
from argus.data.historical_query_config import HistoricalQueryConfig
from argus.data.historical_query_service import HistoricalQueryService
from argus.intelligence.experiments.config import ExperimentConfig
from argus.intelligence.experiments.runner import ExperimentRunner
from argus.intelligence.experiments.store import ExperimentStore

logger = logging.getLogger(__name__)

_EXPERIMENTS_YAML = "config/experiments.yaml"
_UNIVERSE_FILTERS_DIR = Path("config/universe_filters")

# Dynamic filter fields in UniverseFilterConfig that cannot be evaluated
# against historical OHLCV data alone (require real-time or reference data).
_DYNAMIC_FILTER_FIELDS = (
    "min_relative_volume",
    "min_gap_percent",
    "min_premarket_volume",
    "min_market_cap",
    "max_market_cap",
    "min_float",
    "sectors",
    "exclude_sectors",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Run an ARGUS pattern parameter sweep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sweep all bull_flag params with default config
  python scripts/run_experiment.py --pattern bull_flag

  # Sweep only two params (faster)
  python scripts/run_experiment.py --pattern bull_flag --params pole_min_move_pct,flag_max_bars

  # Print grid without running backtests
  python scripts/run_experiment.py --pattern bull_flag --dry-run

  # Restrict date range
  python scripts/run_experiment.py --pattern bull_flag --date-range 2025-06-01,2025-12-31

  # Sweep using pattern's production universe filter
  python scripts/run_experiment.py --pattern narrow_range_breakout --universe-filter

  # Sweep with a specific universe filter
  python scripts/run_experiment.py --pattern bull_flag --universe-filter hod_break

  # Sweep a specific symbol list
  python scripts/run_experiment.py --pattern bull_flag --symbols AAPL,NVDA,TSLA

  # Sweep from a file (one symbol per line)
  python scripts/run_experiment.py --pattern bull_flag --symbols @symbols.txt

  # Combine: filter from file, then validate coverage
  python scripts/run_experiment.py --pattern bull_flag --symbols @symbols.txt --date-range 2025-01-01,2025-12-31
""",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        required=True,
        help="Pattern name to sweep (e.g. bull_flag, flat_top_breakout)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Override Parquet cache directory (default: from config/experiments.yaml)",
    )
    parser.add_argument(
        "--params",
        type=str,
        default=None,
        help="Comma-separated list of param names to vary (others use defaults)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print grid without running backtests",
    )
    parser.add_argument(
        "--date-range",
        type=str,
        default=None,
        help="start,end ISO dates (e.g. 2025-01-01,2025-12-31)",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated symbol list OR @filepath (one symbol per line)",
    )
    parser.add_argument(
        "--universe-filter",
        type=str,
        default=None,
        nargs="?",
        const="__from_pattern__",
        help=(
            "Pattern name to load universe filter from "
            "config/universe_filters/{name}.yaml. "
            "If flag used without value, defaults to --pattern value."
        ),
    )
    return parser.parse_args(argv)


def load_config() -> ExperimentConfig:
    """Load ExperimentConfig from YAML or return defaults.

    Returns:
        ExperimentConfig instance.
    """
    path = Path(_EXPERIMENTS_YAML)
    if path.exists():
        raw = yaml.safe_load(path.read_text())
        if isinstance(raw, dict):
            return ExperimentConfig(**raw)
    return ExperimentConfig()


def _parse_symbols(raw: str) -> list[str]:
    """Parse a symbol list from a comma-separated string or @filepath.

    Args:
        raw: Either a comma-separated list (e.g. ``"AAPL,NVDA,TSLA"``) or a
            file path prefixed with ``@`` (e.g. ``"@symbols.txt"``).

    Returns:
        Deduplicated, uppercased list of ticker symbols (order preserved).
    """
    if raw.startswith("@"):
        file_path = Path(raw[1:])
        lines = file_path.read_text().splitlines()
        raw_symbols = [line.strip() for line in lines if line.strip()]
    else:
        raw_symbols = [s.strip() for s in raw.split(",") if s.strip()]

    return list(dict.fromkeys(sym.upper() for sym in raw_symbols))


def _load_universe_filter(filter_name: str) -> UniverseFilterConfig:
    """Load a UniverseFilterConfig from config/universe_filters/{name}.yaml.

    Args:
        filter_name: Name of the filter file (without extension).

    Returns:
        Parsed UniverseFilterConfig.

    Raises:
        SystemExit: If the filter file does not exist.
    """
    filter_path = _UNIVERSE_FILTERS_DIR / f"{filter_name}.yaml"
    if not filter_path.exists():
        available = sorted(p.stem for p in _UNIVERSE_FILTERS_DIR.glob("*.yaml"))
        print(
            f"ERROR: Universe filter '{filter_name}' not found at {filter_path}\n"
            f"Available filters: {', '.join(available) if available else '(none)'}"
        )
        raise SystemExit(1)

    raw = yaml.safe_load(filter_path.read_text()) or {}
    return UniverseFilterConfig(**raw)


def _apply_universe_filter(
    filter_config: UniverseFilterConfig,
    cache_dir: str,
    start_date: str,
    end_date: str,
    candidate_symbols: list[str] | None = None,
) -> list[str]:
    """Query the Parquet cache via DuckDB and apply static universe filters.

    Applies ``min_price``, ``max_price``, and ``min_avg_volume`` from
    *filter_config* against historical OHLCV averages.  Dynamic filters
    that require real-time or reference data are logged as skipped.

    Args:
        filter_config: UniverseFilterConfig with filter criteria.
        cache_dir: Path to the Databento Parquet cache directory.
        start_date: Inclusive start date (YYYY-MM-DD) for price/volume averages.
        end_date: Inclusive end date (YYYY-MM-DD) for price/volume averages.
        candidate_symbols: When provided, restrict results to this set
            (intersection with cache contents).

    Returns:
        Sorted list of symbols that pass all applicable static filters.
    """
    service = HistoricalQueryService(
        HistoricalQueryConfig(enabled=True, cache_dir=cache_dir)
    )

    if not service.is_available:
        print(
            f"ERROR: HistoricalQueryService unavailable — cache not found or empty at: {cache_dir}"
        )
        sys.exit(1)

    # Log dynamic filters that are present but cannot be evaluated historically.
    for field_name in _DYNAMIC_FILTER_FIELDS:
        value = getattr(filter_config, field_name)
        is_non_empty = value is not None and value != [] and value != ""
        if is_non_empty:
            logger.warning(
                "Skipping dynamic filter '%s' (not applicable to historical sweeps)",
                field_name,
            )

    # Build parameterized WHERE clause.
    # Date params come first; candidate symbols appended after.
    query_params: list = [start_date, end_date]
    symbol_clause = ""
    if candidate_symbols is not None:
        placeholders = ", ".join("?" for _ in candidate_symbols)
        symbol_clause = f" AND symbol IN ({placeholders})"
        query_params = [start_date, end_date] + list(candidate_symbols)

    # Build static HAVING clauses from operator-controlled config values.
    having_clauses: list[str] = ["1=1"]
    if filter_config.min_price is not None:
        having_clauses.append(f"AVG(close) >= {filter_config.min_price}")
    if filter_config.max_price is not None:
        having_clauses.append(f"AVG(close) <= {filter_config.max_price}")
    if filter_config.min_avg_volume is not None:
        having_clauses.append(f"AVG(volume) >= {filter_config.min_avg_volume}")

    having_sql = " AND ".join(having_clauses)

    sql = (
        f"SELECT symbol, AVG(close) AS avg_price, AVG(volume) AS avg_volume "
        f"FROM historical "
        f"WHERE date >= ? AND date <= ?{symbol_clause} "
        f"GROUP BY symbol "
        f"HAVING {having_sql}"
    )

    df = service.query(sql, query_params)
    service.close()

    if df.empty:
        return []

    return sorted(df["symbol"].tolist())


def _validate_coverage(
    symbols: list[str],
    cache_dir: str,
    start_date: str,
    end_date: str,
    min_bars: int = 100,
) -> list[str]:
    """Drop symbols without sufficient historical bar coverage.

    Args:
        symbols: Candidate symbol list to validate.
        cache_dir: Path to the Databento Parquet cache directory.
        start_date: Inclusive start date (YYYY-MM-DD).
        end_date: Inclusive end date (YYYY-MM-DD).
        min_bars: Minimum bar count required to pass (default 100).

    Returns:
        Subset of *symbols* that meet the minimum bar threshold.
    """
    service = HistoricalQueryService(
        HistoricalQueryConfig(enabled=True, cache_dir=cache_dir)
    )

    if not service.is_available:
        logger.warning(
            "Coverage validation skipped — HistoricalQueryService unavailable at: %s",
            cache_dir,
        )
        return symbols

    coverage = service.validate_symbol_coverage(symbols, start_date, end_date, min_bars)
    service.close()

    passed = [sym for sym in symbols if coverage.get(sym, False)]
    failed = [sym for sym in symbols if not coverage.get(sym, False)]
    total = len(symbols)

    logger.info(
        "Coverage validation: %d/%d symbols have sufficient data (%d+ bars)",
        len(passed),
        total,
        min_bars,
    )

    if failed:
        sample = failed[:20]
        summary = ", ".join(sample)
        if len(failed) > 20:  # noqa: PLR2004
            summary += f" ... and {len(failed) - 20} more"
        logger.warning("Symbols dropped (insufficient coverage): %s", summary)

    return passed


def _print_summary_table(records: list[object]) -> None:
    """Print a summary table of experiment results.

    Args:
        records: List of ExperimentRecord instances.
    """
    if not records:
        print("\nNo experiments run.")
        return

    print(f"\n{'=' * 80}")
    print("Experiment Sweep Results")
    print(f"{'=' * 80}")
    header = (
        f"{'Fingerprint':<18} {'Status':<16} {'Trades':>7} "
        f"{'Expectancy':>11} {'Sharpe':>8}"
    )
    print(header)
    print("-" * 80)

    for record in records:
        fingerprint = getattr(record, "parameter_fingerprint", "")[:16]
        rec_status = str(getattr(record, "status", ""))
        backtest = getattr(record, "backtest_result", None) or {}
        trades = backtest.get("total_trades", "-")
        expectancy = backtest.get("expectancy_per_trade")
        sharpe = backtest.get("sharpe_ratio")

        exp_str = f"{expectancy:.4f}" if isinstance(expectancy, float) else "-"
        sharpe_str = f"{sharpe:.4f}" if isinstance(sharpe, float) else "-"

        print(
            f"{fingerprint:<18} {rec_status:<16} {str(trades):>7} "
            f"{exp_str:>11} {sharpe_str:>8}"
        )

    print(f"{'=' * 80}")
    print(f"Total: {len(records)} experiments processed")


async def run(args: argparse.Namespace) -> int:
    """Execute the experiment sweep.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 success, 1 error).
    """
    config = load_config()
    config_dict = config.model_dump()

    cache_dir = args.cache_dir or config.cache_dir
    param_subset = (
        [p.strip() for p in args.params.split(",") if p.strip()]
        if args.params
        else None
    )

    # Resolve date range (needed for symbol filtering and run_sweep).
    date_range: tuple[str, str] | None = None
    start_date_str: str | None = None
    end_date_str: str | None = None

    if args.date_range:
        parts = args.date_range.split(",")
        if len(parts) != 2:  # noqa: PLR2004
            print(f"ERROR: --date-range must be 'start,end' ISO dates, got: {args.date_range}")
            return 1
        start_date_str = parts[0].strip()
        end_date_str = parts[1].strip()
        date_range = (start_date_str, end_date_str)
    elif config.backtest_start_date and config.backtest_end_date:
        start_date_str = str(config.backtest_start_date)
        end_date_str = str(config.backtest_end_date)
        date_range = (start_date_str, end_date_str)

    # --- Symbol filtering pipeline ---
    symbols: list[str] | None = None
    filter_config: UniverseFilterConfig | None = None

    # Layer 1: --symbols flag
    if args.symbols:
        symbols = _parse_symbols(args.symbols)
        print(f"Symbols from --symbols: {len(symbols)}")

    # Layer 2: --universe-filter flag — load config; runner handles filtering
    filter_name = args.universe_filter
    if filter_name == "__from_pattern__":
        filter_name = args.pattern

    if filter_name is not None:
        if start_date_str is None or end_date_str is None:
            print(
                "ERROR: --universe-filter requires a date range. "
                "Provide --date-range or set backtest_start_date/backtest_end_date in config."
            )
            return 1
        filter_config = _load_universe_filter(filter_name)

    store = ExperimentStore()
    runner = ExperimentRunner(store=store, config=config_dict)

    # Generate grid for display / validation
    try:
        grid = runner.generate_parameter_grid(args.pattern, param_subset)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"\nPattern: {args.pattern}")
    print(f"Grid size: {len(grid)} configurations")
    print(f"Estimate: {runner.estimate_sweep_time(len(grid))}")
    if param_subset:
        print(f"Varying params: {', '.join(param_subset)}")

    if args.dry_run:
        if filter_config is not None:
            print(f"Symbols: universe filter '{filter_name}' (resolved at sweep time)")
        elif symbols is not None:
            print(f"Symbols: {len(symbols)} (from --symbols)")
        else:
            print("Symbols: all (auto-detect from cache)")
        sample = grid[:3] if len(grid) > 3 else grid
        print("\n[DRY RUN] Sample configurations:")
        for i, params in enumerate(sample, 1):
            print(f"  {i}. {params}")
        print(f"\n[DRY RUN] No backtests executed.")
        return 0

    # Initialize store for real run
    await store.initialize()

    print(f"\nStarting sweep against cache at: {cache_dir}")
    print("(This may take several minutes...)\n")

    try:
        records = await runner.run_sweep(
            pattern_name=args.pattern,
            cache_dir=cache_dir,
            param_subset=param_subset,
            date_range=date_range,
            symbols=symbols,
            dry_run=False,
            universe_filter=filter_config,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    _print_summary_table(records)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = parse_args(argv)
    try:
        return asyncio.run(run(args))
    except Exception:
        logger.exception("Experiment sweep failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
