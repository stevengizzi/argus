"""Intelligence routes for the Command Center API.

Provides endpoints for catalyst data access and pre-market intelligence
brief generation. All endpoints are JWT-protected.

Sprint 23.5 Session 4 — DEC-164
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter()

_ET = ZoneInfo("America/New_York")


# --- Request/Response Models ---


class CatalystResponse(BaseModel):
    """A classified catalyst item."""

    headline: str
    symbol: str
    source: str
    source_url: str | None
    filing_type: str | None
    published_at: str
    category: str
    quality_score: float
    summary: str
    trading_relevance: str
    classified_by: str
    classified_at: str


class CatalystsBySymbolResponse(BaseModel):
    """Response body for GET /catalysts/{symbol}."""

    catalysts: list[CatalystResponse]
    count: int
    symbol: str


class RecentCatalystsResponse(BaseModel):
    """Response body for GET /catalysts/recent."""

    catalysts: list[CatalystResponse]
    count: int
    total: int


class BriefingResponse(BaseModel):
    """Response body for GET /premarket/briefing."""

    date: str
    brief_type: str
    content: str
    symbols_covered: list[str]
    catalyst_count: int
    generated_at: str
    generation_cost_usd: float


class BriefingHistoryResponse(BaseModel):
    """Response body for GET /premarket/briefing/history."""

    briefings: list[BriefingResponse]
    count: int


class GenerateBriefingRequest(BaseModel):
    """Request body for POST /premarket/briefing/generate."""

    symbols: list[str] | None = Field(
        default=None,
        description="Symbols to include. If null, uses cached watchlist.",
    )


# --- Helper Functions ---


def _ensure_catalyst_storage(state: AppState) -> None:
    """Raise 503 if CatalystStorage is not available.

    Args:
        state: The application state.

    Raises:
        HTTPException 503: If CatalystStorage is not initialized.
    """
    if state.catalyst_storage is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalyst storage not available",
        )


def _ensure_briefing_generator(state: AppState) -> None:
    """Raise 503 if BriefingGenerator is not available.

    Args:
        state: The application state.

    Raises:
        HTTPException 503: If BriefingGenerator is not initialized.
    """
    if state.briefing_generator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Briefing generator not available",
        )


def _catalyst_to_response(catalyst: Any) -> CatalystResponse:
    """Convert a ClassifiedCatalyst to response model.

    Args:
        catalyst: The ClassifiedCatalyst instance.

    Returns:
        CatalystResponse model.
    """
    return CatalystResponse(
        headline=catalyst.headline,
        symbol=catalyst.symbol,
        source=catalyst.source,
        source_url=catalyst.source_url,
        filing_type=catalyst.filing_type,
        published_at=catalyst.published_at.isoformat(),
        category=catalyst.category,
        quality_score=catalyst.quality_score,
        summary=catalyst.summary,
        trading_relevance=catalyst.trading_relevance,
        classified_by=catalyst.classified_by,
        classified_at=catalyst.classified_at.isoformat(),
    )


def _brief_to_response(brief: Any) -> BriefingResponse:
    """Convert an IntelligenceBrief to response model.

    Args:
        brief: The IntelligenceBrief instance.

    Returns:
        BriefingResponse model.
    """
    return BriefingResponse(
        date=brief.date,
        brief_type=brief.brief_type,
        content=brief.content,
        symbols_covered=brief.symbols_covered,
        catalyst_count=brief.catalyst_count,
        generated_at=brief.generated_at.isoformat(),
        generation_cost_usd=brief.generation_cost_usd,
    )


# --- Catalyst Endpoints ---


@router.get("/catalysts/recent", response_model=RecentCatalystsResponse)
async def get_recent_catalysts(
    limit: int = 50,
    offset: int = 0,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> RecentCatalystsResponse:
    """Get recent catalysts across all symbols.

    Query params:
        limit: Maximum number of results (default 50).
        offset: Number of results to skip for pagination (default 0).

    Returns:
        List of recent catalysts ordered by creation time DESC.
    """
    _ensure_catalyst_storage(state)

    catalysts = await state.catalyst_storage.get_recent_catalysts(  # type: ignore
        limit=limit, offset=offset
    )

    total = await state.catalyst_storage.get_total_count()  # type: ignore

    return RecentCatalystsResponse(
        catalysts=[_catalyst_to_response(c) for c in catalysts],
        count=len(catalysts),
        total=total,
    )


@router.get("/catalysts/{symbol}", response_model=CatalystsBySymbolResponse)
async def get_catalysts_by_symbol(
    symbol: str,
    limit: int = 50,
    since: str | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> CatalystsBySymbolResponse:
    """Get catalysts for a specific symbol.

    Path params:
        symbol: Stock ticker symbol.

    Query params:
        limit: Maximum number of results (default 50).
        since: Optional ISO datetime filter for published_at.

    Returns:
        List of catalysts for the symbol (200 even if empty).
    """
    _ensure_catalyst_storage(state)

    # Parse since datetime if provided
    since_dt: datetime | None = None
    if since is not None:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            # Ensure timezone aware
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=_ET)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid datetime format for 'since': {since}",
            ) from e

    catalysts = await state.catalyst_storage.get_catalysts_by_symbol(  # type: ignore
        symbol.upper(), limit=limit, since=since_dt
    )

    return CatalystsBySymbolResponse(
        catalysts=[_catalyst_to_response(c) for c in catalysts],
        count=len(catalysts),
        symbol=symbol.upper(),
    )


def _make_aware(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware.

    Args:
        dt: The datetime to check.

    Returns:
        Timezone-aware datetime (assumes ET if naive).
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_ET)
    return dt


# --- Briefing Endpoints ---


@router.get("/premarket/briefing", response_model=BriefingResponse)
async def get_premarket_briefing(
    date: str | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> BriefingResponse:
    """Get the most recent pre-market briefing for a date.

    Query params:
        date: Date in YYYY-MM-DD format. Defaults to today ET.

    Returns:
        The briefing for the specified date.

    Raises:
        404: If no briefing exists for the date.
    """
    _ensure_catalyst_storage(state)

    # Default to today ET
    if date is None:
        date = datetime.now(_ET).date().isoformat()

    brief = await state.catalyst_storage.get_brief(date, "premarket")  # type: ignore

    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No briefing found for {date}",
        )

    return _brief_to_response(brief)


@router.get("/premarket/briefing/history", response_model=BriefingHistoryResponse)
async def get_briefing_history(
    limit: int = 30,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> BriefingHistoryResponse:
    """Get historical pre-market briefings.

    Query params:
        limit: Maximum number of briefings to return (default 30).

    Returns:
        List of briefings ordered by date DESC.
    """
    _ensure_catalyst_storage(state)

    briefs = await state.catalyst_storage.get_brief_history(limit=limit)  # type: ignore

    return BriefingHistoryResponse(
        briefings=[_brief_to_response(b) for b in briefs],
        count=len(briefs),
    )


@router.post("/premarket/briefing/generate", response_model=BriefingResponse)
async def generate_premarket_briefing(
    request: GenerateBriefingRequest | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> BriefingResponse:
    """Generate a new pre-market briefing.

    Request body:
        symbols: Optional list of symbols. If null, uses cached watchlist.

    Returns:
        The newly generated briefing.

    Raises:
        500: If generation fails.
    """
    _ensure_briefing_generator(state)

    # Determine symbols to use
    if request is not None and request.symbols is not None:
        symbols = request.symbols
    elif state.cached_watchlist:
        # Use cached watchlist symbols
        symbols = [item.symbol for item in state.cached_watchlist]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No symbols provided and no cached watchlist available",
        )

    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No symbols provided for briefing generation",
        )

    try:
        brief = await state.briefing_generator.generate_brief(symbols)  # type: ignore
        return _brief_to_response(brief)
    except Exception as e:
        logger.error("Failed to generate briefing: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Briefing generation failed: {type(e).__name__}: {e}",
        ) from e
