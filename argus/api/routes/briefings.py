"""Briefing routes for The Debrief page.

Provides endpoints for creating, listing, and managing pre-market and EOD briefings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import get_debrief_service

if TYPE_CHECKING:
    from argus.analytics.debrief_service import DebriefService

router = APIRouter()


class CreateBriefingRequest(BaseModel):
    """Request body for creating a new briefing."""

    date: str
    briefing_type: Literal["pre_market", "eod"]
    title: str | None = None


class UpdateBriefingRequest(BaseModel):
    """Request body for updating a briefing."""

    title: str | None = None
    content: str | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class BriefingResponse(BaseModel):
    """Response model for a single briefing."""

    id: str
    date: str
    briefing_type: str
    status: str
    title: str
    content: str
    metadata: dict[str, Any] | None = None
    author: str
    created_at: str
    updated_at: str
    word_count: int
    reading_time_min: int


class BriefingsListResponse(BaseModel):
    """Response model for listing briefings."""

    briefings: list[BriefingResponse]
    total: int


@router.post("", response_model=BriefingResponse, status_code=status.HTTP_201_CREATED)
async def create_briefing(
    body: CreateBriefingRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> BriefingResponse:
    """Create a new briefing.

    Creates a pre-market or EOD briefing for the specified date.
    If no title is provided, one is auto-generated.
    If no content is provided, a template is used.

    Args:
        body: The briefing creation request.

    Returns:
        The created briefing.

    Raises:
        HTTPException 409: If a briefing already exists for the date and type.
    """
    try:
        briefing = await service.create_briefing(
            date=body.date,
            briefing_type=body.briefing_type,
            title=body.title,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    return BriefingResponse(**briefing)


@router.get("", response_model=BriefingsListResponse)
async def list_briefings(
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
    briefing_type: Literal["pre_market", "eod"] | None = Query(
        None, description="Filter by briefing type"
    ),
    briefing_status: str | None = Query(
        None, alias="status", description="Filter by status (draft, final, ai_generated)"
    ),
    date_from: str | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=250, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> BriefingsListResponse:
    """List briefings with optional filtering and pagination.

    Args:
        briefing_type: Optional type filter.
        briefing_status: Optional status filter.
        date_from: Optional start date.
        date_to: Optional end date.
        limit: Maximum results per page.
        offset: Number of results to skip.

    Returns:
        Paginated list of briefings with total count.
    """
    briefings, total = await service.list_briefings(
        briefing_type=briefing_type,
        status=briefing_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    return BriefingsListResponse(
        briefings=[BriefingResponse(**b) for b in briefings],
        total=total,
    )


@router.get("/{briefing_id}", response_model=BriefingResponse)
async def get_briefing(
    briefing_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> BriefingResponse:
    """Get a single briefing by ID.

    Args:
        briefing_id: The briefing ID.

    Returns:
        The briefing.

    Raises:
        HTTPException 404: If the briefing is not found.
    """
    briefing = await service.get_briefing(briefing_id)
    if briefing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Briefing {briefing_id} not found",
        )

    return BriefingResponse(**briefing)


@router.put("/{briefing_id}", response_model=BriefingResponse)
async def update_briefing(
    briefing_id: str,
    body: UpdateBriefingRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> BriefingResponse:
    """Update a briefing.

    Args:
        briefing_id: The briefing ID.
        body: The update request.

    Returns:
        The updated briefing.

    Raises:
        HTTPException 404: If the briefing is not found.
    """
    # Build kwargs from explicitly provided fields (allows setting to null)
    update_kwargs: dict[str, Any] = {}
    if "title" in body.model_fields_set:
        update_kwargs["title"] = body.title
    if "content" in body.model_fields_set:
        update_kwargs["content"] = body.content
    if "status" in body.model_fields_set:
        update_kwargs["status"] = body.status
    if "metadata" in body.model_fields_set:
        update_kwargs["metadata"] = body.metadata

    briefing = await service.update_briefing(briefing_id, **update_kwargs)
    if briefing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Briefing {briefing_id} not found",
        )

    return BriefingResponse(**briefing)


@router.delete("/{briefing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_briefing(
    briefing_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> None:
    """Delete a briefing.

    Args:
        briefing_id: The briefing ID.

    Raises:
        HTTPException 404: If the briefing is not found.
    """
    deleted = await service.delete_briefing(briefing_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Briefing {briefing_id} not found",
        )
