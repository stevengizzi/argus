"""Individual comparison API for multi-objective evaluation results.

Provides Pareto dominance, soft dominance, regime robustness checks, and
human-readable comparison reports. Used by Learning Loop and all downstream
optimization sprints.

Sprint 27.5 Session 3.
"""

from __future__ import annotations

import math

from argus.analytics.evaluation import (
    ComparisonVerdict,
    ConfidenceTier,
    MultiObjectiveResult,
)

__all__ = [
    "COMPARISON_METRICS",
    "compare",
    "pareto_frontier",
    "soft_dominance",
    "is_regime_robust",
    "format_comparison_report",
]

# The 5 metrics used for Pareto dominance comparison and their directions.
# "higher" means a larger value is better. For max_drawdown_pct, values are
# negative (e.g. -0.05), so less negative = higher = better.
COMPARISON_METRICS: tuple[tuple[str, str], ...] = (
    ("sharpe_ratio", "higher"),
    ("max_drawdown_pct", "higher"),
    ("profit_factor", "higher"),
    ("win_rate", "higher"),
    ("expectancy_per_trade", "higher"),
)

# Default tolerances for soft dominance. Each value is the minimum improvement
# needed on that metric, and the maximum degradation allowed.
_DEFAULT_TOLERANCE: dict[str, float] = {
    "sharpe_ratio": 0.1,
    "max_drawdown_pct": 0.02,
    "profit_factor": 0.1,
    "win_rate": 0.02,
    "expectancy_per_trade": 0.05,
}


def _get_metric(result: MultiObjectiveResult, metric_name: str) -> float:
    """Extract a metric value from a MultiObjectiveResult by name.

    Args:
        result: The evaluation result.
        metric_name: One of the COMPARISON_METRICS names.

    Returns:
        The metric value as a float.
    """
    return float(getattr(result, metric_name))


def _has_nan(result: MultiObjectiveResult) -> bool:
    """Check if any comparison metric is NaN.

    Args:
        result: The evaluation result.

    Returns:
        True if any comparison metric is NaN.
    """
    return any(
        math.isnan(_get_metric(result, name))
        for name, _ in COMPARISON_METRICS
    )


def compare(
    a: MultiObjectiveResult,
    b: MultiObjectiveResult,
) -> ComparisonVerdict:
    """Compare two MultiObjectiveResults using Pareto dominance.

    A dominates B if A >= B on all 5 comparison metrics AND A > B on at least 1.
    B dominates A if B >= A on all 5 AND B > A on at least 1.
    Otherwise INCOMPARABLE.

    Args:
        a: First evaluation result.
        b: Second evaluation result.

    Returns:
        ComparisonVerdict indicating the dominance relationship.
    """
    if (
        a.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY
        or b.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY
    ):
        return ComparisonVerdict.INSUFFICIENT_DATA

    if _has_nan(a) or _has_nan(b):
        return ComparisonVerdict.INSUFFICIENT_DATA

    a_ge_b_count = 0  # A >= B
    a_gt_b_count = 0  # A > B
    b_ge_a_count = 0  # B >= A
    b_gt_a_count = 0  # B > A

    for metric_name, _ in COMPARISON_METRICS:
        val_a = _get_metric(a, metric_name)
        val_b = _get_metric(b, metric_name)

        if val_a >= val_b:
            a_ge_b_count += 1
        if val_a > val_b:
            a_gt_b_count += 1
        if val_b >= val_a:
            b_ge_a_count += 1
        if val_b > val_a:
            b_gt_a_count += 1

    total = len(COMPARISON_METRICS)

    if a_ge_b_count == total and a_gt_b_count >= 1:
        return ComparisonVerdict.DOMINATES
    if b_ge_a_count == total and b_gt_a_count >= 1:
        return ComparisonVerdict.DOMINATED

    return ComparisonVerdict.INCOMPARABLE


def pareto_frontier(
    results: list[MultiObjectiveResult],
) -> list[MultiObjectiveResult]:
    """Compute the Pareto frontier from a list of evaluation results.

    Filters to HIGH and MODERATE confidence only, then returns the
    non-dominated subset. O(n²) pairwise comparison.

    Args:
        results: List of evaluation results.

    Returns:
        Non-dominated subset (may be empty).
    """
    eligible = [
        r for r in results
        if r.confidence_tier in (ConfidenceTier.HIGH, ConfidenceTier.MODERATE)
    ]

    if not eligible:
        return []

    frontier: list[MultiObjectiveResult] = []
    for candidate in eligible:
        dominated = False
        for other in eligible:
            if other is candidate:
                continue
            verdict = compare(other, candidate)
            if verdict == ComparisonVerdict.DOMINATES:
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)

    return frontier


def soft_dominance(
    a: MultiObjectiveResult,
    b: MultiObjectiveResult,
    tolerance: dict[str, float] | None = None,
) -> bool:
    """Check if A soft-dominates B within tolerance bands.

    A soft-dominates B if:
    1. A improves at least one metric by >= its tolerance
    2. A does NOT degrade any metric by > its tolerance

    Args:
        a: Candidate result (potential improvement).
        b: Baseline result.
        tolerance: Per-metric tolerance values. Defaults to _DEFAULT_TOLERANCE.

    Returns:
        True if A soft-dominates B.
    """
    if (
        a.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY
        or b.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY
    ):
        return False

    tol = tolerance if tolerance is not None else _DEFAULT_TOLERANCE

    has_meaningful_improvement = False

    for metric_name, _ in COMPARISON_METRICS:
        val_a = _get_metric(a, metric_name)
        val_b = _get_metric(b, metric_name)
        metric_tol = tol[metric_name]

        improvement = val_a - val_b
        degradation = val_b - val_a

        # Check for meaningful improvement
        if improvement >= metric_tol:
            has_meaningful_improvement = True

        # Check for unacceptable degradation
        if degradation > metric_tol:
            return False

    return has_meaningful_improvement


def is_regime_robust(
    result: MultiObjectiveResult,
    min_regimes: int = 3,
) -> bool:
    """Check if a result is robust across market regimes.

    Requires HIGH or MODERATE confidence. Counts regimes where
    expectancy_per_trade > 0.

    Args:
        result: The evaluation result.
        min_regimes: Minimum number of positive-expectancy regimes required.

    Returns:
        True if the result meets the regime robustness threshold.
    """
    if result.confidence_tier not in (ConfidenceTier.HIGH, ConfidenceTier.MODERATE):
        return False

    positive_regimes = sum(
        1 for rm in result.regime_results.values()
        if rm.expectancy_per_trade > 0
    )
    return positive_regimes >= min_regimes


def format_comparison_report(
    a: MultiObjectiveResult,
    b: MultiObjectiveResult,
) -> str:
    """Format a human-readable comparison report.

    Includes header with strategy IDs and confidence tiers, metric-by-metric
    table, verdict, and regime breakdown if available.

    Args:
        a: First evaluation result.
        b: Second evaluation result.

    Returns:
        Multi-line string suitable for CLI output and Copilot context injection.
    """
    lines: list[str] = []

    # Header
    lines.append("=" * 60)
    lines.append("COMPARISON REPORT")
    lines.append("=" * 60)
    lines.append(
        f"A: {a.strategy_id}  (hash: {a.parameter_hash[:8]})"
    )
    lines.append(
        f"   Date range: {a.data_range[0]} to {a.data_range[1]}"
    )
    lines.append(f"   Confidence: {a.confidence_tier.value}")
    lines.append(
        f"B: {b.strategy_id}  (hash: {b.parameter_hash[:8]})"
    )
    lines.append(
        f"   Date range: {b.data_range[0]} to {b.data_range[1]}"
    )
    lines.append(f"   Confidence: {b.confidence_tier.value}")
    lines.append("")

    # Metric table
    lines.append(f"{'Metric':<25} {'A':>12} {'B':>12} {'Winner':>8}")
    lines.append("-" * 60)

    for metric_name, _ in COMPARISON_METRICS:
        val_a = _get_metric(a, metric_name)
        val_b = _get_metric(b, metric_name)

        # Format values
        fmt_a = f"{val_a:.4f}" if not math.isinf(val_a) else "inf"
        fmt_b = f"{val_b:.4f}" if not math.isinf(val_b) else "inf"

        if math.isnan(val_a) or math.isnan(val_b):
            winner = "N/A"
        elif val_a > val_b:
            winner = "A"
        elif val_b > val_a:
            winner = "B"
        else:
            winner = "tie"

        lines.append(f"{metric_name:<25} {fmt_a:>12} {fmt_b:>12} {winner:>8}")

    lines.append("")

    # Verdict
    verdict = compare(a, b)
    lines.append(f"Verdict: {verdict.value}")
    lines.append("")

    # Regime breakdown
    if a.regime_results or b.regime_results:
        lines.append("REGIME BREAKDOWN")
        lines.append("-" * 60)

        all_regimes = sorted(
            set(list(a.regime_results.keys()) + list(b.regime_results.keys()))
        )
        for regime in all_regimes:
            lines.append(f"  {regime}:")
            rm_a = a.regime_results.get(regime)
            rm_b = b.regime_results.get(regime)
            if rm_a is not None:
                lines.append(
                    f"    A: Sharpe={rm_a.sharpe_ratio:.2f}  "
                    f"DD={rm_a.max_drawdown_pct:.2%}  "
                    f"WR={rm_a.win_rate:.1%}  "
                    f"E[R]={rm_a.expectancy_per_trade:.3f}  "
                    f"({rm_a.total_trades} trades)"
                )
            else:
                lines.append("    A: (no data)")
            if rm_b is not None:
                lines.append(
                    f"    B: Sharpe={rm_b.sharpe_ratio:.2f}  "
                    f"DD={rm_b.max_drawdown_pct:.2%}  "
                    f"WR={rm_b.win_rate:.1%}  "
                    f"E[R]={rm_b.expectancy_per_trade:.3f}  "
                    f"({rm_b.total_trades} trades)"
                )
            else:
                lines.append("    B: (no data)")

    lines.append("=" * 60)
    return "\n".join(lines)
