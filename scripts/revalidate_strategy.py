"""Re-validation harness: run BacktestEngine-based walk-forward for any strategy.

Compares results against YAML backtest_summary baselines and outputs structured
JSON with divergence flags.

Usage:
    python scripts/revalidate_strategy.py --strategy orb --start 2023-03-01 --end 2025-03-01
    python scripts/revalidate_strategy.py --strategy bull_flag --start 2023-06-01 --end 2025-03-01
    python scripts/revalidate_strategy.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Ensure project root is importable when running as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.walk_forward import (
    WalkForwardConfig,
    WalkForwardResult,
    run_fixed_params_walk_forward,
)
from argus.core.config import load_yaml_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Strategies that have VectorBT IS evaluation paths in walk_forward.py
_WALK_FORWARD_SUPPORTED = {"orb", "orb_scalp", "vwap_reclaim", "afternoon_momentum"}

# StrategyType enum value → YAML config filename (without .yaml)
_STRATEGY_YAML_MAP: dict[str, str] = {
    "orb": "orb_breakout",
    "orb_scalp": "orb_scalp",
    "vwap_reclaim": "vwap_reclaim",
    "afternoon_momentum": "afternoon_momentum",
    "red_to_green": "red_to_green",
    "bull_flag": "bull_flag",
    "flat_top_breakout": "flat_top_breakout",
}

# StrategyType enum value → BacktestEngine strategy_id
_STRATEGY_ID_MAP: dict[str, str] = {
    "orb": "strat_orb_breakout",
    "orb_scalp": "strat_orb_scalp",
    "vwap_reclaim": "strat_vwap_reclaim",
    "afternoon_momentum": "strat_afternoon_momentum",
    "red_to_green": "strat_red_to_green",
    "bull_flag": "strat_bull_flag",
    "flat_top_breakout": "strat_flat_top_breakout",
}

# Divergence thresholds
SHARPE_DIVERGENCE_THRESHOLD = 0.5
WIN_RATE_DIVERGENCE_THRESHOLD = 10.0  # percentage points
PROFIT_FACTOR_DIVERGENCE_THRESHOLD = 0.5

# WFE pass threshold (DEC-047)
WFE_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Config extraction helpers (importable for testing)
# ---------------------------------------------------------------------------


def extract_fixed_params(strategy_key: str, yaml_config: dict[str, Any]) -> dict[str, Any]:
    """Map strategy YAML config keys to walk-forward fixed-params naming.

    Args:
        strategy_key: Strategy key (e.g. "orb", "vwap_reclaim").
        yaml_config: Parsed YAML config dict.

    Returns:
        Dict of fixed params in VectorBT naming convention.

    Raises:
        ValueError: If strategy_key is not recognized.
    """
    if strategy_key == "orb":
        return {
            "or_minutes": yaml_config.get("orb_window_minutes", 5),
            "target_r": yaml_config.get("target_2_r", 2.0),
            "stop_buffer_pct": 0.0,
            "max_hold_minutes": yaml_config.get("time_stop_minutes", 15),
            "min_gap_pct": yaml_config.get("min_gap_pct", 2.0),
            "max_range_atr_ratio": yaml_config.get("max_range_atr_ratio", 999.0),
        }
    elif strategy_key == "orb_scalp":
        max_hold_seconds = yaml_config.get("max_hold_seconds", 120)
        return {
            "scalp_target_r": yaml_config.get("scalp_target_r", 0.3),
            "max_hold_bars": max(1, max_hold_seconds // 60),
        }
    elif strategy_key == "vwap_reclaim":
        return {
            "min_pullback_pct": yaml_config.get("min_pullback_pct", 0.002),
            "min_pullback_bars": yaml_config.get("min_pullback_bars", 3),
            "volume_multiplier": yaml_config.get(
                "volume_confirmation_multiplier", 1.2
            ),
            "target_r": yaml_config.get("target_2_r", 2.0),
            "time_stop_bars": yaml_config.get("time_stop_minutes", 30),
        }
    elif strategy_key == "afternoon_momentum":
        return {
            "consolidation_atr_ratio": yaml_config.get(
                "consolidation_atr_ratio", 0.75
            ),
            "min_consolidation_bars": yaml_config.get("min_consolidation_bars", 30),
            "volume_multiplier": yaml_config.get("volume_multiplier", 1.2),
            "target_r": yaml_config.get("target_2_r", 2.0),
            "time_stop_bars": yaml_config.get("max_hold_minutes", 60),
        }
    elif strategy_key == "red_to_green":
        return {
            "min_gap_down_pct": yaml_config.get("min_gap_down_pct", 0.02),
            "level_proximity_pct": yaml_config.get("level_proximity_pct", 0.003),
            "volume_confirmation_multiplier": yaml_config.get(
                "volume_confirmation_multiplier", 1.2
            ),
            "time_stop_minutes": yaml_config.get("time_stop_minutes", 20),
        }
    elif strategy_key in ("bull_flag", "flat_top_breakout"):
        # PatternModule strategies — extract all non-standard keys as params
        skip_keys = {
            "strategy_id",
            "name",
            "version",
            "enabled",
            "asset_class",
            "pipeline_stage",
            "family",
            "description_short",
            "time_window_display",
            "operating_window",
            "risk_limits",
            "benchmarks",
            "backtest_summary",
            "universe_filter",
        }
        return {
            k: v
            for k, v in yaml_config.items()
            if k not in skip_keys and not isinstance(v, dict)
        }
    else:
        raise ValueError(f"Unknown strategy key: {strategy_key}")


def extract_baseline(yaml_config: dict[str, Any]) -> dict[str, Any] | None:
    """Extract backtest_summary baseline from YAML config.

    Args:
        yaml_config: Parsed YAML config dict.

    Returns:
        Baseline dict with oos_sharpe, wfe_pnl, total_trades, data_months,
        or None if no backtest_summary section exists.
    """
    summary = yaml_config.get("backtest_summary")
    if summary is None:
        return None

    return {
        "source": summary.get("data_source", "alpaca_provisional"),
        "oos_sharpe": summary.get("oos_sharpe"),
        "wfe_pnl": summary.get("wfe_pnl"),
        "total_trades": summary.get("total_trades"),
        "data_months": summary.get("data_months"),
    }


def detect_divergence(
    baseline: dict[str, Any] | None,
    new_results: dict[str, Any],
) -> dict[str, Any]:
    """Compare new results against baseline and flag divergences.

    Args:
        baseline: Baseline dict from YAML (may be None or have null values).
        new_results: New walk-forward results.

    Returns:
        Divergence dict with flags and differences.
    """
    flags: list[str] = []

    if baseline is None:
        return {
            "sharpe_diff": None,
            "wfe_diff": None,
            "win_rate_diff": None,
            "profit_factor_diff": None,
            "flagged": False,
            "flags": [],
            "note": "N/A — no prior baseline",
        }

    sharpe_diff: float | None = None
    wfe_diff: float | None = None
    win_rate_diff: float | None = None
    profit_factor_diff: float | None = None

    baseline_sharpe = baseline.get("oos_sharpe")
    new_sharpe = new_results.get("oos_sharpe")
    if baseline_sharpe is not None and new_sharpe is not None:
        sharpe_diff = abs(float(new_sharpe) - float(baseline_sharpe))
        if sharpe_diff > SHARPE_DIVERGENCE_THRESHOLD:
            flags.append("sharpe_divergence")

    baseline_wfe = baseline.get("wfe_pnl")
    new_wfe = new_results.get("wfe_pnl")
    if baseline_wfe is not None and new_wfe is not None:
        wfe_diff = abs(float(new_wfe) - float(baseline_wfe))

    new_win_rate = new_results.get("avg_win_rate")
    if new_win_rate is not None and baseline_sharpe is not None:
        # Win rate comparison only possible if we have both values
        # Baseline YAML doesn't store win_rate, so this flag is only raised
        # when comparing two re-validation runs (future use)
        pass

    new_pf = new_results.get("avg_profit_factor")
    if new_pf is not None:
        # Similarly, baseline YAML doesn't store profit_factor
        pass

    return {
        "sharpe_diff": sharpe_diff,
        "wfe_diff": wfe_diff,
        "win_rate_diff": win_rate_diff,
        "profit_factor_diff": profit_factor_diff,
        "flagged": len(flags) > 0,
        "flags": flags,
    }


def determine_status(
    new_results: dict[str, Any],
    divergence: dict[str, Any],
    baseline: dict[str, Any] | None,
) -> str:
    """Determine validation status from results and divergence.

    Args:
        new_results: New walk-forward results.
        divergence: Divergence analysis.
        baseline: Baseline from YAML (may be None).

    Returns:
        One of: VALIDATED, DIVERGENT, WFE_BELOW_THRESHOLD, ZERO_TRADES, NEW_BASELINE.
    """
    total_trades = new_results.get("total_oos_trades", 0)
    if total_trades == 0:
        return "ZERO_TRADES"

    if baseline is None or all(
        baseline.get(k) is None for k in ("oos_sharpe", "wfe_pnl", "total_trades")
    ):
        return "NEW_BASELINE"

    wfe_pnl = new_results.get("wfe_pnl")
    if wfe_pnl is not None and wfe_pnl < WFE_THRESHOLD:
        return "WFE_BELOW_THRESHOLD"

    if divergence.get("flagged", False):
        return "DIVERGENT"

    return "VALIDATED"


def build_new_results_dict(result: WalkForwardResult) -> dict[str, Any]:
    """Extract structured results from WalkForwardResult.

    Args:
        result: Walk-forward result object.

    Returns:
        Dict with standardized result fields.
    """
    valid_windows = [w for w in result.windows if w.error is None]
    avg_win_rate = (
        sum(w.oos_win_rate for w in valid_windows) / len(valid_windows)
        if valid_windows
        else 0.0
    )
    avg_profit_factor = (
        sum(w.oos_profit_factor for w in valid_windows) / len(valid_windows)
        if valid_windows
        else 0.0
    )

    return {
        "oos_sharpe": result.overall_oos_sharpe,
        "wfe_pnl": result.avg_wfe_pnl,
        "wfe_sharpe": result.avg_wfe_sharpe,
        "total_oos_trades": result.total_oos_trades,
        "avg_win_rate": round(avg_win_rate, 4),
        "avg_profit_factor": round(avg_profit_factor, 4),
        "total_windows": len(result.windows),
        "valid_windows": len(valid_windows),
        "data_months": None,  # Populated by caller from date range
    }


def build_backtest_engine_results_dict(
    metrics: dict[str, float],
    total_windows: int,
) -> dict[str, Any]:
    """Build results dict from BacktestEngine-only run (no WFE).

    Args:
        metrics: Metrics dict from BacktestEngine run.
        total_windows: Number of windows processed.

    Returns:
        Dict with standardized result fields.
    """
    return {
        "oos_sharpe": metrics.get("sharpe", 0.0),
        "wfe_pnl": None,
        "wfe_sharpe": None,
        "total_oos_trades": int(metrics.get("total_trades", 0)),
        "avg_win_rate": round(metrics.get("win_rate", 0.0), 4),
        "avg_profit_factor": round(metrics.get("profit_factor", 0.0), 4),
        "total_windows": total_windows,
        "valid_windows": total_windows,
        "data_months": None,
    }


# ---------------------------------------------------------------------------
# BacktestEngine-only fallback for unsupported strategies
# ---------------------------------------------------------------------------


async def run_backtest_engine_fallback(
    strategy_key: str,
    start_date: date,
    end_date: date,
    cache_dir: Path,
    fixed_params: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    """Run BacktestEngine directly for strategies without VectorBT IS paths.

    Runs a single BacktestEngine pass over the full date range and returns
    aggregate metrics. No WFE is computed (single run, not windowed).

    Args:
        strategy_key: Strategy key from StrategyType enum.
        start_date: Backtest start date.
        end_date: Backtest end date.
        cache_dir: Databento Parquet cache directory.
        fixed_params: Strategy parameters for config_overrides.
        output_dir: Where to write BacktestEngine output.

    Returns:
        Metrics dict with sharpe, win_rate, profit_factor, total_trades, total_pnl.
    """
    from argus.backtest.engine import BacktestEngine

    strategy_type = StrategyType(strategy_key)
    strategy_id = _STRATEGY_ID_MAP[strategy_key]

    # Build config_overrides from fixed_params
    # Map param names to strategy config paths
    yaml_name = _STRATEGY_YAML_MAP[strategy_key]
    config_overrides = {f"{yaml_name}.{k}": v for k, v in fixed_params.items()}

    engine_config = BacktestEngineConfig(
        strategy_type=strategy_type,
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date,
        cache_dir=cache_dir,
        output_dir=output_dir,
        config_overrides=config_overrides,
        log_level="WARNING",
    )

    engine = BacktestEngine(engine_config)
    result = await engine.run()

    return {
        "total_trades": result.total_trades,
        "sharpe": result.sharpe_ratio,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "total_pnl": result.final_equity - result.initial_capital,
        "max_drawdown": result.max_drawdown_pct,
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


async def run_validation(args: argparse.Namespace) -> dict[str, Any]:
    """Run the full validation pipeline.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Structured validation result dict (written to JSON).
    """
    strategy_key = args.strategy
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    cache_dir = Path(args.cache_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load strategy YAML config
    yaml_name = _STRATEGY_YAML_MAP[strategy_key]
    config_path = PROJECT_ROOT / "config" / "strategies" / f"{yaml_name}.yaml"
    yaml_config = load_yaml_file(config_path)

    # Extract params and baseline
    fixed_params = extract_fixed_params(strategy_key, yaml_config)
    baseline = extract_baseline(yaml_config)

    logger.info("Strategy: %s", strategy_key)
    logger.info("Date range: %s to %s", start, end)
    logger.info("Fixed params: %s", fixed_params)
    logger.info("Baseline: %s", baseline)

    # Compute data months from date range
    data_months = (end.year - start.year) * 12 + (end.month - start.month)

    walk_forward_available = strategy_key in _WALK_FORWARD_SUPPORTED
    notes: list[str] = []

    if walk_forward_available:
        # Full walk-forward with VectorBT IS + BacktestEngine OOS
        config = WalkForwardConfig(
            strategy=strategy_key,
            data_dir=str(cache_dir),
            in_sample_months=args.is_months,
            out_of_sample_months=args.oos_months,
            step_months=args.step_months,
            min_trades=args.min_trades,
            output_dir=str(output_dir / strategy_key),
            oos_engine="backtest_engine",
        )
        result = await run_fixed_params_walk_forward(config, fixed_params)
        new_results = build_new_results_dict(result)
        new_results["data_months"] = data_months
    else:
        # BacktestEngine-only fallback
        notes.append(
            f"Walk-forward not available for {strategy_key} "
            f"(no VectorBT IS evaluation path). "
            f"Running BacktestEngine-only over full date range. "
            f"No WFE computed."
        )
        metrics = await run_backtest_engine_fallback(
            strategy_key=strategy_key,
            start_date=start,
            end_date=end,
            cache_dir=cache_dir,
            fixed_params=fixed_params,
            output_dir=output_dir / strategy_key,
        )
        new_results = build_backtest_engine_results_dict(metrics, total_windows=1)
        new_results["data_months"] = data_months

    # Compare against baseline
    divergence = detect_divergence(baseline, new_results)
    status = determine_status(new_results, divergence, baseline)

    output = {
        "strategy": yaml_name,
        "strategy_type": strategy_key,
        "date_range": {"start": str(start), "end": str(end)},
        "data_source": "databento_ohlcv_1m",
        "engine": "backtest_engine",
        "baseline": baseline,
        "new_results": new_results,
        "divergence": divergence,
        "status": status,
        "walk_forward_available": walk_forward_available,
        "notes": "; ".join(notes) if notes else "",
    }

    # Write JSON output
    json_path = output_dir / f"{yaml_name}_validation.json"
    json_path.write_text(json.dumps(output, indent=2, default=str))
    logger.info("Results written to %s", json_path)

    return output


def print_summary(output: dict[str, Any]) -> None:
    """Print human-readable validation summary to stdout.

    Args:
        output: Structured validation result dict.
    """
    strategy = output["strategy"]
    status = output["status"]
    new = output["new_results"]
    baseline = output.get("baseline")

    print("\n" + "=" * 60)
    print(f"RE-VALIDATION RESULTS: {strategy.upper()}")
    print("=" * 60)
    print(f"Date Range:       {output['date_range']['start']} to {output['date_range']['end']}")
    print(f"Engine:           {output['engine']}")
    print(f"Walk-Forward:     {'Yes' if output['walk_forward_available'] else 'No (BacktestEngine-only)'}")
    print("-" * 60)

    print(f"OOS Sharpe:       {new.get('oos_sharpe', 'N/A')}")
    if new.get("wfe_pnl") is not None:
        print(f"WFE (P&L):        {new['wfe_pnl']:.2f}")
    if new.get("wfe_sharpe") is not None:
        print(f"WFE (Sharpe):     {new['wfe_sharpe']:.2f}")
    print(f"Total OOS Trades: {new.get('total_oos_trades', 0)}")
    print(f"Avg Win Rate:     {new.get('avg_win_rate', 0.0):.1%}")
    print(f"Avg Profit Factor:{new.get('avg_profit_factor', 0.0):.2f}")
    print(f"Windows:          {new.get('valid_windows', 0)}/{new.get('total_windows', 0)}")
    print("-" * 60)

    if baseline:
        print("Baseline Comparison:")
        bl_sharpe = baseline.get("oos_sharpe")
        bl_wfe = baseline.get("wfe_pnl")
        bl_trades = baseline.get("total_trades")
        print(f"  Old OOS Sharpe:  {bl_sharpe if bl_sharpe is not None else 'N/A'}")
        print(f"  Old WFE (P&L):   {bl_wfe if bl_wfe is not None else 'N/A'}")
        print(f"  Old Total Trades:{bl_trades if bl_trades is not None else 'N/A'}")

        div = output["divergence"]
        if div.get("sharpe_diff") is not None:
            print(f"  Sharpe Diff:     {div['sharpe_diff']:.2f}")
        if div.get("flagged"):
            print(f"  FLAGS:           {', '.join(div['flags'])}")
    else:
        print("Baseline: N/A — no prior baseline in YAML")

    print("-" * 60)
    print(f"STATUS: {status}")

    if output.get("notes"):
        print(f"\nNotes: {output['notes']}")

    print("=" * 60)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="Re-validate a strategy using BacktestEngine-based walk-forward.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/revalidate_strategy.py "
            "--strategy orb --start 2023-03-01 --end 2025-03-01\n"
            "  python scripts/revalidate_strategy.py "
            "--strategy bull_flag --start 2023-06-01 --end 2025-03-01\n"
        ),
    )
    parser.add_argument(
        "--strategy",
        required=True,
        choices=[s.value for s in StrategyType],
        help="Strategy key (StrategyType enum value).",
    )
    parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--cache-dir",
        default="data/databento_cache",
        help="Databento Parquet cache directory (default: data/databento_cache).",
    )
    parser.add_argument(
        "--output-dir",
        default="data/backtest_runs/validation",
        help="Output directory for result JSONs (default: data/backtest_runs/validation).",
    )
    parser.add_argument(
        "--is-months",
        type=int,
        default=4,
        help="In-sample window months (default: 4).",
    )
    parser.add_argument(
        "--oos-months",
        type=int,
        default=2,
        help="Out-of-sample window months (default: 2).",
    )
    parser.add_argument(
        "--step-months",
        type=int,
        default=2,
        help="Window step size in months (default: 2).",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=20,
        help="Minimum trades per window to qualify (default: 20).",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: WARNING).",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the re-validation harness.

    Args:
        argv: Optional argument list for testing.
    """
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    output = asyncio.run(run_validation(args))
    print_summary(output)


if __name__ == "__main__":
    main()
