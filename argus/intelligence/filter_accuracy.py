"""Filter accuracy computation for counterfactual positions.

Answers "what percentage of rejected signals would have lost money?"
by analyzing closed counterfactual positions from the CounterfactualStore.

Read-only: queries the store but never modifies position data.

Sprint 27.7, Session 4.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from argus.intelligence.counterfactual_store import CounterfactualStore

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class FilterAccuracyBreakdown:
    """Accuracy metric for a single filter category.

    Attributes:
        category: The category value (e.g., "quality_filter", "B+", "orb_breakout").
        total_rejections: Total closed positions in this category.
        correct_rejections: Would have lost money (theoretical_pnl <= 0).
        incorrect_rejections: Would have made money (theoretical_pnl > 0).
        accuracy: correct / total (0.0-1.0).
        avg_theoretical_pnl: Average P&L of all rejected signals in this category.
        sample_sufficient: True if total >= min_sample_count.
    """

    category: str
    total_rejections: int
    correct_rejections: int
    incorrect_rejections: int
    accuracy: float
    avg_theoretical_pnl: float
    sample_sufficient: bool


@dataclass(frozen=True)
class FilterAccuracyReport:
    """Complete filter accuracy analysis.

    Attributes:
        computed_at: When this report was generated.
        date_range_start: Start of the analysis period.
        date_range_end: End of the analysis period.
        total_positions: Total closed positions analyzed.
        by_stage: Breakdown by rejection stage.
        by_reason: Breakdown by rejection reason.
        by_grade: Breakdown by quality grade.
        by_strategy: Breakdown by strategy_id.
        by_regime: Breakdown by primary_regime from regime_vector_snapshot.
    """

    computed_at: datetime
    date_range_start: datetime
    date_range_end: datetime
    total_positions: int
    by_stage: list[FilterAccuracyBreakdown]
    by_reason: list[FilterAccuracyBreakdown]
    by_grade: list[FilterAccuracyBreakdown]
    by_strategy: list[FilterAccuracyBreakdown]
    by_regime: list[FilterAccuracyBreakdown]


def _build_breakdown(
    positions: list[dict[str, object]],
    key_fn: callable,  # type: ignore[valid-type]
    min_sample_count: int,
) -> list[FilterAccuracyBreakdown]:
    """Group positions by a key function and compute accuracy for each group.

    Args:
        positions: List of closed position dicts from the store.
        key_fn: Function that extracts the grouping key from a position dict.
        min_sample_count: Minimum sample count for sample_sufficient flag.

    Returns:
        List of FilterAccuracyBreakdown sorted by total_rejections descending.
    """
    groups: dict[str, list[float]] = {}
    for pos in positions:
        category = key_fn(pos)
        pnl = pos.get("theoretical_pnl")
        if pnl is None:
            continue
        pnl_float = float(pnl)
        if category not in groups:
            groups[category] = []
        groups[category].append(pnl_float)

    breakdowns: list[FilterAccuracyBreakdown] = []
    for category, pnls in sorted(groups.items(), key=lambda x: -len(x[1])):
        total = len(pnls)
        correct = sum(1 for p in pnls if p <= 0)
        incorrect = total - correct
        accuracy = correct / total if total > 0 else 0.0
        avg_pnl = sum(pnls) / total if total > 0 else 0.0

        breakdowns.append(FilterAccuracyBreakdown(
            category=category,
            total_rejections=total,
            correct_rejections=correct,
            incorrect_rejections=incorrect,
            accuracy=accuracy,
            avg_theoretical_pnl=avg_pnl,
            sample_sufficient=total >= min_sample_count,
        ))

    return breakdowns


def _extract_primary_regime(pos: dict[str, object]) -> str:
    """Extract the primary_regime from a position's regime_vector_snapshot.

    Handles both JSON strings and dict values. Returns "unknown" if
    the snapshot is missing or has no primary_regime.

    Args:
        pos: Position dict from the store.

    Returns:
        The primary regime string or "unknown".
    """
    snapshot = pos.get("regime_vector_snapshot")
    if snapshot is None:
        return "unknown"

    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except (json.JSONDecodeError, TypeError):
            return "unknown"

    if isinstance(snapshot, dict):
        regime = snapshot.get("primary_regime")
        if regime is not None:
            return str(regime)

    return "unknown"


async def compute_filter_accuracy(
    store: CounterfactualStore,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    strategy_id: str | None = None,
    min_sample_count: int = 10,
) -> FilterAccuracyReport:
    """Compute filter accuracy from closed counterfactual positions.

    Queries the store for closed positions within the date range and
    computes accuracy breakdowns by stage, reason, grade, strategy,
    and regime.

    Args:
        store: CounterfactualStore to query.
        start_date: Start of analysis period (defaults to 30 days ago).
        end_date: End of analysis period (defaults to now).
        strategy_id: Optional strategy filter.
        min_sample_count: Minimum sample count for sample_sufficient flag.

    Returns:
        FilterAccuracyReport with all breakdowns.
    """
    now_et = datetime.now(_ET)

    if end_date is None:
        end_date = now_et
    if start_date is None:
        from datetime import timedelta
        start_date = end_date - timedelta(days=30)

    # Build filter kwargs
    filters: dict[str, object] = {}
    if strategy_id is not None:
        filters["strategy_id"] = strategy_id

    positions = await store.get_closed_positions(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        **filters,
    )

    if not positions:
        return FilterAccuracyReport(
            computed_at=now_et,
            date_range_start=start_date,
            date_range_end=end_date,
            total_positions=0,
            by_stage=[],
            by_reason=[],
            by_grade=[],
            by_strategy=[],
            by_regime=[],
        )

    by_stage = _build_breakdown(
        positions,
        lambda p: str(p.get("rejection_stage", "unknown")),
        min_sample_count,
    )
    by_reason = _build_breakdown(
        positions,
        lambda p: str(p.get("rejection_reason", "unknown")),
        min_sample_count,
    )
    by_grade = _build_breakdown(
        positions,
        lambda p: str(p.get("quality_grade") or "unknown"),
        min_sample_count,
    )
    by_strategy = _build_breakdown(
        positions,
        lambda p: str(p.get("strategy_id", "unknown")),
        min_sample_count,
    )
    by_regime = _build_breakdown(
        positions,
        _extract_primary_regime,
        min_sample_count,
    )

    return FilterAccuracyReport(
        computed_at=now_et,
        date_range_start=start_date,
        date_range_end=end_date,
        total_positions=len(positions),
        by_stage=by_stage,
        by_reason=by_reason,
        by_grade=by_grade,
        by_strategy=by_strategy,
        by_regime=by_regime,
    )
