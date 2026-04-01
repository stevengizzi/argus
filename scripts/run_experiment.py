#!/usr/bin/env python3
"""CLI entry point for running parameterized pattern experiment sweeps.

Usage:
    python scripts/run_experiment.py --pattern bull_flag
    python scripts/run_experiment.py --pattern bull_flag --params pole_min_move_pct,flag_max_bars
    python scripts/run_experiment.py --pattern bull_flag --dry-run
    python scripts/run_experiment.py --pattern bull_flag --date-range 2025-01-01,2025-12-31
    python scripts/run_experiment.py --pattern bull_flag --cache-dir data/databento_cache

Sprint 32, Session 8.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

from argus.intelligence.experiments.config import ExperimentConfig
from argus.intelligence.experiments.runner import ExperimentRunner
from argus.intelligence.experiments.store import ExperimentStore

logger = logging.getLogger(__name__)

_EXPERIMENTS_YAML = "config/experiments.yaml"


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
    date_range: tuple[str, str] | None = None
    if args.date_range:
        parts = args.date_range.split(",")
        if len(parts) != 2:  # noqa: PLR2004
            print(f"ERROR: --date-range must be 'start,end' ISO dates, got: {args.date_range}")
            return 1
        date_range = (parts[0].strip(), parts[1].strip())

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

    records = await runner.run_sweep(
        pattern_name=args.pattern,
        cache_dir=cache_dir,
        param_subset=param_subset,
        date_range=date_range,
        dry_run=False,
    )

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
