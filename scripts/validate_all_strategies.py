"""Validation orchestrator: run revalidate_strategy.py for all strategies,
then perform Pareto comparison, regime robustness, and optional ensemble analysis.

Chains BacktestEngine -> walk-forward -> MultiObjectiveResult -> Pareto comparison
into a single CLI invocation for the 6-strategy re-validation push.

Usage:
    python scripts/validate_all_strategies.py --cache-dir /Volumes/LaCie/argus-cache
    python scripts/validate_all_strategies.py --cache-dir /Volumes/LaCie/argus-cache --strategies orb vwap
    python scripts/validate_all_strategies.py --cache-dir /Volumes/LaCie/argus-cache --output results.json
    python scripts/validate_all_strategies.py --cache-dir /Volumes/LaCie/argus-cache --ensemble
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

# Ensure project root is importable when running as a script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from argus.analytics.comparison import (
    compare,
    is_regime_robust,
    pareto_frontier,
)
from argus.analytics.ensemble_evaluation import (
    build_ensemble_result,
)
from argus.analytics.evaluation import (
    ConfidenceTier,
    MultiObjectiveResult,
    RegimeMetrics,
    compute_confidence_tier,
    parameter_hash,
)

# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: dict[str, dict[str, Any]] = {
    "orb": {
        "start": "2023-03-01",
        "end": "2025-03-01",
        "description": "ORB Breakout",
    },
    "orb_scalp": {
        "start": "2023-03-01",
        "end": "2025-03-01",
        "description": "ORB Scalp",
    },
    "vwap_reclaim": {
        "start": "2023-03-01",
        "end": "2025-03-01",
        "description": "VWAP Reclaim",
    },
    "afternoon_momentum": {
        "start": "2023-03-01",
        "end": "2025-03-01",
        "description": "Afternoon Momentum",
    },
    "red_to_green": {
        "start": "2023-06-01",
        "end": "2025-03-01",
        "description": "Red-to-Green",
    },
    "bull_flag": {
        "start": "2023-06-01",
        "end": "2025-03-01",
        "description": "Bull Flag",
    },
    "flat_top_breakout": {
        "start": "2023-06-01",
        "end": "2025-03-01",
        "description": "Flat-Top Breakout",
    },
}


# ---------------------------------------------------------------------------
# Subprocess execution
# ---------------------------------------------------------------------------


def run_revalidation(
    strategy_key: str,
    cache_dir: str,
    start: str,
    end: str,
    output_dir: str,
) -> dict[str, Any]:
    """Run revalidate_strategy.py as a subprocess and capture JSON output.

    Args:
        strategy_key: Strategy key (e.g. "orb", "vwap_reclaim").
        cache_dir: Path to Databento Parquet cache directory.
        start: Start date (YYYY-MM-DD).
        end: End date (YYYY-MM-DD).
        output_dir: Output directory for per-strategy results.

    Returns:
        Parsed JSON result dict from the validation script.

    Raises:
        RuntimeError: If subprocess fails or JSON output cannot be parsed.
    """
    script_path = PROJECT_ROOT / "scripts" / "revalidate_strategy.py"
    strategy_output_dir = str(Path(output_dir) / strategy_key)

    cmd = [
        sys.executable,
        str(script_path),
        "--strategy", strategy_key,
        "--start", start,
        "--end", end,
        "--cache-dir", cache_dir,
        "--output-dir", strategy_output_dir,
        "--log-level", "WARNING",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=1800,  # 30 min max per strategy
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"revalidate_strategy.py failed for {strategy_key} "
            f"(exit code {result.returncode}):\n{result.stderr}"
        )

    # Find the JSON output file
    json_path = _find_validation_json(strategy_output_dir, strategy_key)
    if json_path is None:
        raise RuntimeError(
            f"No validation JSON found for {strategy_key} "
            f"in {strategy_output_dir}"
        )

    return json.loads(json_path.read_text())


def _find_validation_json(
    output_dir: str,
    strategy_key: str,
) -> Path | None:
    """Locate the validation JSON file produced by revalidate_strategy.py.

    Args:
        output_dir: Directory where the script writes output.
        strategy_key: Strategy key for filename matching.

    Returns:
        Path to the JSON file, or None if not found.
    """
    output_path = Path(output_dir)
    if not output_path.exists():
        return None

    # revalidate_strategy.py writes {yaml_name}_validation.json
    for json_file in output_path.glob("*_validation.json"):
        return json_file

    return None


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------


def parse_validation_result(
    strategy_key: str,
    raw: dict[str, Any],
) -> MultiObjectiveResult:
    """Parse revalidate_strategy.py JSON output into a MultiObjectiveResult.

    Args:
        strategy_key: Strategy key for identification.
        raw: Raw JSON dict from revalidate_strategy.py.

    Returns:
        MultiObjectiveResult constructed from the validation data.
    """
    new_results = raw.get("new_results", {})
    date_range = raw.get("date_range", {})

    sharpe = float(new_results.get("oos_sharpe", 0.0) or 0.0)
    win_rate = float(new_results.get("avg_win_rate", 0.0) or 0.0)
    profit_factor = float(new_results.get("avg_profit_factor", 0.0) or 0.0)
    total_trades = int(new_results.get("total_oos_trades", 0) or 0)
    wfe = float(new_results.get("wfe_pnl", 0.0) or 0.0)

    # Estimate expectancy from available metrics
    # expectancy ~ (win_rate * avg_win - (1-win_rate) * avg_loss)
    # Approximate from profit_factor: E[R] = (PF * WR - (1-WR)) / 1
    if profit_factor > 0 and win_rate > 0:
        expectancy = (profit_factor * win_rate) - (1.0 - win_rate)
    else:
        expectancy = 0.0

    # Parse date range
    start_str = date_range.get("start", "2023-01-01")
    end_str = date_range.get("end", "2025-01-01")
    start_date = date.fromisoformat(start_str)
    end_date = date.fromisoformat(end_str)

    # Build regime results dict (empty — not available from revalidation output)
    regime_results: dict[str, RegimeMetrics] = {}

    # Compute confidence tier
    confidence = compute_confidence_tier(total_trades, {})

    # Build parameter hash from strategy key (deterministic)
    param_hash = parameter_hash({"strategy": strategy_key})

    return MultiObjectiveResult(
        strategy_id=strategy_key,
        parameter_hash=param_hash,
        evaluation_date=datetime.now(UTC),
        data_range=(start_date, end_date),
        sharpe_ratio=sharpe,
        max_drawdown_pct=0.0,  # Not available from revalidation JSON
        profit_factor=profit_factor,
        win_rate=win_rate,
        total_trades=total_trades,
        expectancy_per_trade=expectancy,
        regime_results=regime_results,
        confidence_tier=confidence,
        wfe=wfe,
        is_oos=True,
    )


# ---------------------------------------------------------------------------
# Comparison and analysis
# ---------------------------------------------------------------------------


def run_comparison_phase(
    results: dict[str, MultiObjectiveResult],
) -> dict[str, Any]:
    """Run Pareto frontier, pairwise comparison, and regime robustness.

    Args:
        results: Dict of strategy_key -> MultiObjectiveResult.

    Returns:
        Analysis dict with pareto, comparisons, and robustness results.
    """
    mor_list = list(results.values())

    # Pareto frontier (HIGH/MODERATE confidence only)
    frontier = pareto_frontier(mor_list)
    pareto_members = {r.strategy_id for r in frontier}

    # Pairwise comparison matrix
    keys = sorted(results.keys())
    comparisons: dict[str, dict[str, str]] = {}
    for i, key_a in enumerate(keys):
        comparisons[key_a] = {}
        for key_b in keys[i + 1:]:
            verdict = compare(results[key_a], results[key_b])
            comparisons[key_a][key_b] = verdict.value

    # Regime robustness
    robustness: dict[str, bool] = {}
    for key, mor in results.items():
        robustness[key] = is_regime_robust(mor)

    return {
        "pareto_members": sorted(pareto_members),
        "comparisons": comparisons,
        "robustness": robustness,
    }


def run_ensemble_phase(
    results: dict[str, MultiObjectiveResult],
) -> dict[str, Any]:
    """Run ensemble evaluation on all collected results.

    Args:
        results: Dict of strategy_key -> MultiObjectiveResult.

    Returns:
        Ensemble analysis dict.
    """
    mor_list = list(results.values())
    if len(mor_list) < 2:
        return {"note": "Need at least 2 strategies for ensemble analysis"}

    ensemble = build_ensemble_result(mor_list, cohort_id="validation_cohort")
    return ensemble.to_dict()


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def print_summary_table(
    results: dict[str, MultiObjectiveResult],
    raw_results: dict[str, dict[str, Any]],
    analysis: dict[str, Any],
    failures: dict[str, str],
) -> None:
    """Print the summary table to stdout.

    Args:
        results: Dict of strategy_key -> MultiObjectiveResult.
        raw_results: Dict of strategy_key -> raw JSON from revalidation.
        analysis: Comparison analysis dict.
        failures: Dict of strategy_key -> error message for failed strategies.
    """
    pareto_members = set(analysis.get("pareto_members", []))
    robustness = analysis.get("robustness", {})

    header = (
        f"{'Strategy':<20} | {'Sharpe':>6} | {'WinRate':>7} | {'PF':>5} "
        f"| {'MaxDD':>7} | {'WFE':>5} | {'Trades':>6} "
        f"| {'Confidence':<10} | {'Pareto':>6} | {'Robust':>6}"
    )
    separator = "-" * len(header)

    print("\n" + "=" * len(header))
    print("VALIDATION SUMMARY")
    print("=" * len(header))
    print(header)
    print(separator)

    all_keys = sorted(
        set(list(results.keys()) + list(failures.keys()))
    )

    for key in all_keys:
        if key in failures:
            print(f"{key:<20} | {'FAILED':>6} | {'-':>7} | {'-':>5} "
                  f"| {'-':>7} | {'-':>5} | {'-':>6} "
                  f"| {'-':<10} | {'-':>6} | {'-':>6}")
            continue

        mor = results[key]
        raw = raw_results.get(key, {})
        new_r = raw.get("new_results", {})

        sharpe_str = f"{mor.sharpe_ratio:.2f}"
        wr_str = f"{mor.win_rate:.1%}"
        pf_str = f"{mor.profit_factor:.2f}"
        dd_str = f"{mor.max_drawdown_pct:.1%}" if mor.max_drawdown_pct != 0.0 else "N/A"
        wfe_val = new_r.get("wfe_pnl")
        wfe_str = f"{wfe_val:.2f}" if wfe_val is not None else "N/A"
        trades_str = str(mor.total_trades)
        conf_str = mor.confidence_tier.value
        pareto_str = "Y" if key in pareto_members else "-"
        robust_str = "Y" if robustness.get(key, False) else "-"

        print(f"{key:<20} | {sharpe_str:>6} | {wr_str:>7} | {pf_str:>5} "
              f"| {dd_str:>7} | {wfe_str:>5} | {trades_str:>6} "
              f"| {conf_str:<10} | {pareto_str:>6} | {robust_str:>6}")

    print(separator)

    if failures:
        print(f"\nFAILED STRATEGIES ({len(failures)}):")
        for key, error in failures.items():
            print(f"  {key}: {error[:100]}")

    succeeded = len(results)
    total = succeeded + len(failures)
    print(f"\n{succeeded}/{total} strategies validated successfully.")
    print("=" * len(header))


def build_output_json(
    results: dict[str, MultiObjectiveResult],
    raw_results: dict[str, dict[str, Any]],
    analysis: dict[str, Any],
    failures: dict[str, str],
    ensemble: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the full JSON output structure.

    Args:
        results: Dict of strategy_key -> MultiObjectiveResult.
        raw_results: Dict of strategy_key -> raw JSON from revalidation.
        analysis: Comparison analysis dict.
        failures: Dict of strategy_key -> error message.
        ensemble: Optional ensemble analysis dict.

    Returns:
        Complete output dict for JSON serialization.
    """
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "strategies": {
            key: {
                "multi_objective_result": mor.to_dict(),
                "raw_validation": raw_results.get(key, {}),
            }
            for key, mor in results.items()
        },
        "failures": failures,
        "analysis": analysis,
        "ensemble": ensemble,
        "summary": {
            "total": len(results) + len(failures),
            "succeeded": len(results),
            "failed": len(failures),
            "pareto_members": analysis.get("pareto_members", []),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Validation orchestrator: run all strategies through "
            "BacktestEngine walk-forward, then Pareto + ensemble analysis."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/validate_all_strategies.py "
            "--cache-dir /Volumes/LaCie/argus-cache\n"
            "  python scripts/validate_all_strategies.py "
            "--cache-dir /Volumes/LaCie/argus-cache --strategies orb vwap\n"
            "  python scripts/validate_all_strategies.py "
            "--cache-dir /Volumes/LaCie/argus-cache --output results.json\n"
        ),
    )
    parser.add_argument(
        "--cache-dir",
        required=True,
        help="Databento Parquet cache directory (required).",
    )
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=list(STRATEGY_REGISTRY.keys()),
        default=None,
        help="Strategies to validate (default: all 7).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write full JSON results.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/backtest_runs/validation_all",
        help="Output directory for per-strategy results "
        "(default: data/backtest_runs/validation_all).",
    )
    parser.add_argument(
        "--ensemble",
        action="store_true",
        default=False,
        help="Run ensemble cohort analysis after individual validation.",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the validation orchestrator.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Exit code: 0 if all succeed, 1 if any fail.
    """
    args = parse_args(argv)

    strategies = args.strategies or list(STRATEGY_REGISTRY.keys())
    cache_dir = args.cache_dir
    output_dir = args.output_dir

    results: dict[str, MultiObjectiveResult] = {}
    raw_results: dict[str, dict[str, Any]] = {}
    failures: dict[str, str] = {}

    print(f"Validating {len(strategies)} strategies...")
    print(f"Cache directory: {cache_dir}")
    print()

    # Execution loop
    for i, strategy_key in enumerate(strategies, 1):
        config = STRATEGY_REGISTRY[strategy_key]
        description = config["description"]
        start = config["start"]
        end = config["end"]

        print(f"[{i}/{len(strategies)}] {description} ({strategy_key})...",
              end=" ", flush=True)

        try:
            raw = run_revalidation(
                strategy_key=strategy_key,
                cache_dir=cache_dir,
                start=start,
                end=end,
                output_dir=output_dir,
            )
            raw_results[strategy_key] = raw
            mor = parse_validation_result(strategy_key, raw)
            results[strategy_key] = mor

            status = raw.get("status", "UNKNOWN")
            print(f"DONE (status={status}, trades={mor.total_trades})")

        except Exception as exc:
            error_msg = str(exc)
            failures[strategy_key] = error_msg
            print(f"FAILED ({error_msg[:80]})")

    print()

    # Comparison phase
    if results:
        print("Running comparison analysis...")
        analysis = run_comparison_phase(results)
    else:
        analysis = {
            "pareto_members": [],
            "comparisons": {},
            "robustness": {},
        }

    # Optional ensemble phase
    ensemble: dict[str, Any] | None = None
    if args.ensemble and len(results) >= 2:
        print("Running ensemble analysis...")
        ensemble = run_ensemble_phase(results)

    # Print summary table
    print_summary_table(results, raw_results, analysis, failures)

    # Write JSON output if requested
    if args.output:
        output_json = build_output_json(
            results, raw_results, analysis, failures, ensemble
        )
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_json, indent=2, default=str))
        print(f"\nFull results written to {args.output}")

    has_failures = len(failures) > 0
    return 1 if has_failures else 0


if __name__ == "__main__":
    sys.exit(main())
