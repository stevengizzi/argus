"""Counterfactual accuracy routes for the Command Center API.

Provides the filter accuracy endpoint that reports how often rejected
signals would have lost money, proving the rejection was correct.

Sprint 27.7, Session 4.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from zoneinfo import ZoneInfo

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter()

_ET = ZoneInfo("America/New_York")


# --- Response Models ---


class BreakdownResponse(BaseModel):
    """A single filter accuracy breakdown entry."""

    category: str
    total_rejections: int
    correct_rejections: int
    incorrect_rejections: int
    accuracy: float
    avg_theoretical_pnl: float
    sample_sufficient: bool


class FilterAccuracyResponse(BaseModel):
    """Complete filter accuracy report."""

    computed_at: str
    date_range_start: str
    date_range_end: str
    total_positions: int
    by_stage: list[BreakdownResponse]
    by_reason: list[BreakdownResponse]
    by_grade: list[BreakdownResponse]
    by_strategy: list[BreakdownResponse]
    by_regime: list[BreakdownResponse]


# --- Endpoints ---


@router.get("/positions")
async def get_counterfactual_positions(
    strategy_id: str | None = Query(default=None, description="Filter by strategy ID"),
    date_from: str | None = Query(default=None, description="ISO 8601 start date for opened_at"),
    date_to: str | None = Query(default=None, description="ISO 8601 end date for opened_at"),
    rejection_stage: str | None = Query(default=None, description="Filter by rejection stage"),
    limit: int = Query(default=500, ge=1, le=2000, description="Max results per page"),
    offset: int = Query(default=0, ge=0, description="Rows to skip for pagination"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Get shadow (counterfactual) positions with optional filters and pagination.

    Returns all positions (active and closed) matching the filters.
    Returns an empty list when the counterfactual store is not available.

    Query params:
        strategy_id: Optional strategy filter.
        date_from: ISO 8601 start date for opened_at (inclusive).
        date_to: ISO 8601 end date for opened_at (inclusive).
        rejection_stage: Optional rejection stage filter.
        limit: Maximum results (default 500).
        offset: Pagination offset (default 0).

    Returns:
        Dict with ``positions`` list, ``total_count``, ``limit``,
        ``offset``, and ``timestamp``.
    """
    if state.counterfactual_store is None:
        return {
            "positions": [],
            "total_count": 0,
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now(_ET).isoformat(),
        }

    try:
        positions = await state.counterfactual_store.query_positions(
            strategy_id=strategy_id,
            date_from=date_from,
            date_to=date_to,
            rejection_stage=rejection_stage,
            limit=limit,
            offset=offset,
        )
        total_count = await state.counterfactual_store.count_positions(
            strategy_id=strategy_id,
            date_from=date_from,
            date_to=date_to,
            rejection_stage=rejection_stage,
        )
    except Exception as exc:
        logger.error("Failed to query counterfactual positions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query positions: {exc}",
        ) from exc

    return {
        "positions": positions,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "timestamp": datetime.now(_ET).isoformat(),
    }


@router.get("/accuracy", response_model=FilterAccuracyResponse)
async def get_counterfactual_accuracy(
    start_date: str | None = Query(default=None, description="ISO 8601 start date"),
    end_date: str | None = Query(default=None, description="ISO 8601 end date"),
    strategy_id: str | None = Query(default=None, description="Filter by strategy"),
    min_sample_count: int = Query(default=10, ge=1, description="Min samples for sufficient flag"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> FilterAccuracyResponse:
    """Get filter accuracy report for counterfactual positions.

    Computes how often rejected signals would have lost money, grouped
    by rejection stage, reason, quality grade, strategy, and regime.

    Returns 200 with an empty report if the counterfactual store is
    not available (disabled) or no data exists.

    Query params:
        start_date: ISO 8601 start date (default: 30 days ago).
        end_date: ISO 8601 end date (default: now).
        strategy_id: Optional strategy filter.
        min_sample_count: Minimum samples for sample_sufficient flag (default: 10).

    Returns:
        FilterAccuracyResponse with breakdowns.
    """
    from argus.intelligence.filter_accuracy import compute_filter_accuracy

    # If store not available, return empty report
    if state.counterfactual_store is None:
        now_et = datetime.now(_ET)
        return FilterAccuracyResponse(
            computed_at=now_et.isoformat(),
            date_range_start=now_et.isoformat(),
            date_range_end=now_et.isoformat(),
            total_positions=0,
            by_stage=[],
            by_reason=[],
            by_grade=[],
            by_strategy=[],
            by_regime=[],
        )

    # Parse date strings
    parsed_start: datetime | None = None
    parsed_end: datetime | None = None

    if start_date is not None:
        try:
            parsed_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format: {start_date}",
            ) from e

    if end_date is not None:
        try:
            parsed_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_date format: {end_date}",
            ) from e

    report = await compute_filter_accuracy(
        store=state.counterfactual_store,
        start_date=parsed_start,
        end_date=parsed_end,
        strategy_id=strategy_id,
        min_sample_count=min_sample_count,
    )

    def _breakdown_to_response(b: object) -> BreakdownResponse:
        """Convert a FilterAccuracyBreakdown to response model."""
        from argus.intelligence.filter_accuracy import FilterAccuracyBreakdown
        assert isinstance(b, FilterAccuracyBreakdown)
        return BreakdownResponse(
            category=b.category,
            total_rejections=b.total_rejections,
            correct_rejections=b.correct_rejections,
            incorrect_rejections=b.incorrect_rejections,
            accuracy=b.accuracy,
            avg_theoretical_pnl=b.avg_theoretical_pnl,
            sample_sufficient=b.sample_sufficient,
        )

    return FilterAccuracyResponse(
        computed_at=report.computed_at.isoformat(),
        date_range_start=report.date_range_start.isoformat(),
        date_range_end=report.date_range_end.isoformat(),
        total_positions=report.total_positions,
        by_stage=[_breakdown_to_response(b) for b in report.by_stage],
        by_reason=[_breakdown_to_response(b) for b in report.by_reason],
        by_grade=[_breakdown_to_response(b) for b in report.by_grade],
        by_strategy=[_breakdown_to_response(b) for b in report.by_strategy],
        by_regime=[_breakdown_to_response(b) for b in report.by_regime],
    )
