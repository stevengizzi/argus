"""Observatory routes for The Observatory pipeline visualization page.

Provides endpoints for pipeline stage counts, closest-miss ranking,
per-symbol pipeline journey, and session summary.

Sprint 25, Session 1.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter()

_ET = ZoneInfo("America/New_York")


# --- Response Models ---


class PipelineStagesResponse(BaseModel):
    """Pipeline stage counts across all tiers."""

    universe: int
    viable: int
    routed: int
    evaluating: int
    near_trigger: int
    signal: int
    traded: int
    date: str
    timestamp: str


class ConditionDetail(BaseModel):
    """Individual condition check result."""

    name: str
    passed: bool
    actual_value: float | str | bool | None = None
    required_value: float | str | bool | None = None


class ClosestMissEntry(BaseModel):
    """Single closest-miss entry."""

    symbol: str
    strategy: str
    conditions_passed: int
    conditions_total: int
    conditions_detail: list[ConditionDetail]
    timestamp: str | None = None


class ClosestMissesResponse(BaseModel):
    """Closest-miss ranking response."""

    tier: str
    items: list[ClosestMissEntry]
    count: int
    timestamp: str


class JourneyEvent(BaseModel):
    """Single event in a symbol's pipeline journey."""

    timestamp: str
    strategy: str
    event_type: str
    result: str
    metadata: dict


class SymbolJourneyResponse(BaseModel):
    """Chronological evaluation events for a symbol."""

    symbol: str
    events: list[JourneyEvent]
    count: int
    date: str
    timestamp: str


class BlockerEntry(BaseModel):
    """Top blocker condition with rejection stats."""

    condition_name: str
    rejection_count: int
    percentage: float


class ClosestMissSummary(BaseModel):
    """Summary of the single closest miss."""

    symbol: str
    strategy: str
    conditions_passed: int
    conditions_total: int


class SessionSummaryResponse(BaseModel):
    """Aggregated session metrics."""

    total_evaluations: int
    total_signals: int
    total_trades: int
    symbols_evaluated: int
    top_blockers: list[BlockerEntry]
    closest_miss: ClosestMissSummary | None
    regime_vector_summary: dict | None = None
    date: str
    timestamp: str


# --- Helpers ---


def _get_observatory_service(state: AppState):
    """Get ObservatoryService from AppState.

    Args:
        state: Application state.

    Returns:
        ObservatoryService instance.

    Raises:
        HTTPException 503: If Observatory service is not available.
    """
    from fastapi import HTTPException, status

    if state.observatory_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Observatory service not available",
        )
    return state.observatory_service


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    from datetime import UTC

    return datetime.now(UTC).isoformat()


# --- Endpoints ---


@router.get("/pipeline", response_model=PipelineStagesResponse)
async def get_pipeline_stages(
    date: str | None = Query(None, description="Date filter (YYYY-MM-DD)"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> PipelineStagesResponse:
    """Get pipeline stage counts for all tiers.

    Args:
        date: Optional date filter. Defaults to today (ET).

    Returns:
        Counts for each of the 7 pipeline tiers.
    """
    svc = _get_observatory_service(state)
    result = await svc.get_pipeline_stages(date=date)
    return PipelineStagesResponse(
        **result,
        timestamp=_now_iso(),
    )


@router.get("/closest-misses", response_model=ClosestMissesResponse)
async def get_closest_misses(
    tier: str = Query("evaluating", description="Pipeline tier to query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    date: str | None = Query(None, description="Date filter (YYYY-MM-DD)"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ClosestMissesResponse:
    """Get symbols sorted by conditions passed (descending).

    Args:
        tier: Pipeline tier to query.
        limit: Maximum entries to return.
        date: Optional date filter. Defaults to today (ET).

    Returns:
        Sorted list of closest-miss entries with condition details.
    """
    svc = _get_observatory_service(state)
    items = await svc.get_closest_misses(tier=tier, limit=limit, date=date)
    return ClosestMissesResponse(
        tier=tier,
        items=[ClosestMissEntry(**item) for item in items],
        count=len(items),
        timestamp=_now_iso(),
    )


@router.get(
    "/symbol/{symbol}/journey",
    response_model=SymbolJourneyResponse,
)
async def get_symbol_journey(
    symbol: str,
    date: str | None = Query(None, description="Date filter (YYYY-MM-DD)"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> SymbolJourneyResponse:
    """Get chronological evaluation events for a symbol.

    Args:
        symbol: Ticker symbol.
        date: Optional date filter. Defaults to today (ET).

    Returns:
        Chronological list of evaluation events across all strategies.
    """
    svc = _get_observatory_service(state)
    target_date = date or datetime.now(_ET).strftime("%Y-%m-%d")
    events = await svc.get_symbol_journey(symbol=symbol, date=date)
    return SymbolJourneyResponse(
        symbol=symbol.upper(),
        events=[JourneyEvent(**e) for e in events],
        count=len(events),
        date=target_date,
        timestamp=_now_iso(),
    )


@router.get("/session-summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    date: str | None = Query(None, description="Date filter (YYYY-MM-DD)"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> SessionSummaryResponse:
    """Get aggregated session metrics.

    Args:
        date: Optional date filter. Defaults to today (ET).

    Returns:
        Session totals, top blockers, and closest miss summary.
    """
    svc = _get_observatory_service(state)
    result = await svc.get_session_summary(date=date)

    closest_miss = None
    if result.get("closest_miss"):
        cm = result["closest_miss"]
        closest_miss = ClosestMissSummary(
            symbol=cm["symbol"],
            strategy=cm["strategy"],
            conditions_passed=cm["conditions_passed"],
            conditions_total=cm["conditions_total"],
        )

    # Read regime vector summary from orchestrator if available
    regime_vector_summary = None
    if (
        state.orchestrator is not None
        and hasattr(state.orchestrator, "latest_regime_vector_summary")
    ):
        regime_vector_summary = state.orchestrator.latest_regime_vector_summary

    return SessionSummaryResponse(
        total_evaluations=result["total_evaluations"],
        total_signals=result["total_signals"],
        total_trades=result["total_trades"],
        symbols_evaluated=result["symbols_evaluated"],
        top_blockers=[BlockerEntry(**b) for b in result["top_blockers"]],
        closest_miss=closest_miss,
        regime_vector_summary=regime_vector_summary,
        date=result["date"],
        timestamp=_now_iso(),
    )
