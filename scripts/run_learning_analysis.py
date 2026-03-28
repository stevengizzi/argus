#!/usr/bin/env python3
"""CLI entry point for running learning loop analysis.

Usage:
    python scripts/run_learning_analysis.py
    python scripts/run_learning_analysis.py --window-days 60
    python scripts/run_learning_analysis.py --strategy-id orb_breakout
    python scripts/run_learning_analysis.py --dry-run

Sprint 28, Session 3b.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import yaml

from argus.intelligence.learning.correlation_analyzer import CorrelationAnalyzer
from argus.intelligence.learning.learning_service import LearningService
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import LearningLoopConfig, LearningReport
from argus.intelligence.learning.outcome_collector import OutcomeCollector
from argus.intelligence.learning.threshold_analyzer import ThresholdAnalyzer
from argus.intelligence.learning.weight_analyzer import WeightAnalyzer

logger = logging.getLogger(__name__)

_LEARNING_LOOP_YAML = "config/learning_loop.yaml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Run ARGUS learning loop analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=None,
        help="Override analysis window (days)",
    )
    parser.add_argument(
        "--strategy-id",
        type=str,
        default=None,
        help="Filter to a single strategy",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report to stdout without persisting",
    )
    return parser.parse_args(argv)


def load_config() -> LearningLoopConfig:
    """Load LearningLoopConfig from YAML or return defaults.

    Returns:
        LearningLoopConfig instance.
    """
    path = Path(_LEARNING_LOOP_YAML)
    if path.exists():
        raw = yaml.safe_load(path.read_text())
        if isinstance(raw, dict):
            return LearningLoopConfig(**raw)
    return LearningLoopConfig()


def print_report_summary(report: LearningReport) -> None:
    """Print a human-readable report summary to stdout.

    Args:
        report: The LearningReport to summarize.
    """
    dq = report.data_quality
    print(f"\n{'=' * 60}")
    print("ARGUS Learning Loop Analysis Report")
    print(f"{'=' * 60}")
    print(f"Report ID:    {report.report_id}")
    print(f"Generated:    {report.generated_at.isoformat()}")
    print(f"Window:       {report.analysis_window_start.date()} → "
          f"{report.analysis_window_end.date()}")
    print(f"Version:      {report.version}")

    print(f"\n--- Data Quality ---")
    print(f"Trading days: {dq.trading_days_count}")
    print(f"Trades:       {dq.total_trades}")
    print(f"Counterfact:  {dq.total_counterfactual}")
    print(f"Sample size:  {dq.effective_sample_size}")
    if dq.known_data_gaps:
        print(f"Data gaps:")
        for gap in dq.known_data_gaps:
            print(f"  - {gap}")

    if report.weight_recommendations:
        print(f"\n--- Weight Recommendations ({len(report.weight_recommendations)}) ---")
        for rec in report.weight_recommendations:
            print(
                f"  {rec.dimension}: {rec.current_weight:.3f} → "
                f"{rec.recommended_weight:.3f} "
                f"(Δ{rec.delta:+.4f}, {rec.confidence.value})"
            )

    if report.threshold_recommendations:
        print(f"\n--- Threshold Recommendations ({len(report.threshold_recommendations)}) ---")
        for rec in report.threshold_recommendations:
            print(
                f"  {rec.grade}: {rec.recommended_direction} "
                f"(missed_opp={rec.missed_opportunity_rate:.2f}, "
                f"correct_rej={rec.correct_rejection_rate:.2f}, "
                f"{rec.confidence.value})"
            )

    cr = report.correlation_result
    if cr is not None and cr.flagged_pairs:
        print(f"\n--- Flagged Correlation Pairs ---")
        for pair in cr.flagged_pairs:
            corr = cr.correlation_matrix.get(pair, 0.0)
            print(f"  {pair[0]} ↔ {pair[1]}: {corr:.3f}")

    print(f"\n{'=' * 60}")


async def run(args: argparse.Namespace) -> int:
    """Execute the learning analysis.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code (0 success, 1 error).
    """
    config = load_config()

    collector = OutcomeCollector()
    weight_analyzer = WeightAnalyzer()
    threshold_analyzer = ThresholdAnalyzer()
    correlation_analyzer = CorrelationAnalyzer()
    store = LearningStore()

    if not args.dry_run:
        await store.initialize()

    service = LearningService(
        config=config,
        outcome_collector=collector,
        weight_analyzer=weight_analyzer,
        threshold_analyzer=threshold_analyzer,
        correlation_analyzer=correlation_analyzer,
        store=store,
    )

    # For dry-run, temporarily override to always-enabled
    if args.dry_run:
        service._config = LearningLoopConfig(
            **{
                **config.model_dump(),
                "enabled": True,
            }
        )

    report = await service.run_analysis(
        window_days=args.window_days,
        strategy_id=args.strategy_id,
    )

    if report is None:
        print("Learning loop is disabled. Use --dry-run to force.")
        return 0

    print_report_summary(report)

    if args.dry_run:
        print("\n[DRY RUN] Report NOT persisted to database.")
        print(json.dumps(report.to_dict(), indent=2, default=str))

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
        logger.exception("Learning analysis failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
