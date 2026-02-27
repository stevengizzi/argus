"""Journal entry routes for The Debrief page.

Provides endpoints for creating, listing, and managing trading journal entries.
Supports observations, trade annotations, pattern notes, and system notes.
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

JournalEntryType = Literal["observation", "trade_annotation", "pattern_note", "system_note"]


class CreateJournalEntryRequest(BaseModel):
    """Request body for creating a new journal entry."""

    entry_type: JournalEntryType
    title: str
    content: str
    linked_strategy_id: str | None = None
    linked_trade_ids: list[str] | None = None
    tags: list[str] | None = None


class UpdateJournalEntryRequest(BaseModel):
    """Request body for updating a journal entry."""

    entry_type: JournalEntryType | None = None
    title: str | None = None
    content: str | None = None
    linked_strategy_id: str | None = None
    linked_trade_ids: list[str] | None = None
    tags: list[str] | None = None


class JournalEntryResponse(BaseModel):
    """Response model for a single journal entry."""

    id: str
    entry_type: str
    title: str
    content: str
    author: str
    linked_strategy_id: str | None = None
    linked_trade_ids: list[str]
    tags: list[str]
    created_at: str
    updated_at: str


class JournalEntriesListResponse(BaseModel):
    """Response model for listing journal entries."""

    entries: list[JournalEntryResponse]
    total: int


class JournalTagsResponse(BaseModel):
    """Response model for listing unique journal tags."""

    tags: list[str]


def _dict_to_entry_response(entry: dict) -> JournalEntryResponse:
    """Convert a journal entry dict to JournalEntryResponse."""
    return JournalEntryResponse(
        id=entry["id"],
        entry_type=entry["entry_type"],
        title=entry["title"],
        content=entry["content"],
        author=entry.get("author", "operator"),
        linked_strategy_id=entry.get("linked_strategy_id"),
        linked_trade_ids=entry.get("linked_trade_ids", []),
        tags=entry.get("tags", []),
        created_at=entry["created_at"],
        updated_at=entry["updated_at"],
    )


@router.post("", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(
    body: CreateJournalEntryRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> JournalEntryResponse:
    """Create a new journal entry.

    Args:
        body: The journal entry creation request.

    Returns:
        The created journal entry.
    """
    entry = await service.create_journal_entry(
        entry_type=body.entry_type,
        title=body.title,
        content=body.content,
        linked_strategy_id=body.linked_strategy_id,
        linked_trade_ids=body.linked_trade_ids,
        tags=body.tags,
    )

    return _dict_to_entry_response(entry)


@router.get("", response_model=JournalEntriesListResponse)
async def list_journal_entries(
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
    entry_type: JournalEntryType | None = Query(  # noqa: B008
        None, description="Filter by entry type"
    ),
    strategy_id: str | None = Query(None, description="Filter by linked strategy ID"),  # noqa: B008
    tag: str | None = Query(None, description="Filter by tag"),  # noqa: B008
    search: str | None = Query(None, description="Search in title and content"),  # noqa: B008
    date_from: str | None = Query(None, description="Start date filter (YYYY-MM-DD)"),  # noqa: B008
    date_to: str | None = Query(None, description="End date filter (YYYY-MM-DD)"),  # noqa: B008
    limit: int = Query(50, ge=1, le=250, description="Max results per page"),  # noqa: B008
    offset: int = Query(0, ge=0, description="Number of results to skip"),  # noqa: B008
) -> JournalEntriesListResponse:
    """List journal entries with optional filtering and pagination.

    Args:
        entry_type: Optional entry type filter.
        strategy_id: Optional linked strategy filter.
        tag: Optional tag filter.
        search: Optional search term for title and content.
        date_from: Optional start date.
        date_to: Optional end date.
        limit: Maximum results per page.
        offset: Number of results to skip.

    Returns:
        Paginated list of journal entries with total count.
    """
    entries, total = await service.list_journal_entries(
        entry_type=entry_type,
        strategy_id=strategy_id,
        tag=tag,
        search=search,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )

    return JournalEntriesListResponse(
        entries=[_dict_to_entry_response(e) for e in entries],
        total=total,
    )


@router.get("/tags", response_model=JournalTagsResponse)
async def get_journal_tags(
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> JournalTagsResponse:
    """Get all unique tags from journal entries.

    Returns:
        List of unique tags sorted alphabetically.
    """
    tags = await service.get_journal_tags()

    return JournalTagsResponse(tags=tags)


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    entry_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> JournalEntryResponse:
    """Get a single journal entry by ID.

    Args:
        entry_id: The journal entry ID.

    Returns:
        The journal entry.

    Raises:
        HTTPException 404: If the entry is not found.
    """
    entry = await service.get_journal_entry(entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Journal entry {entry_id} not found",
        )

    return _dict_to_entry_response(entry)


@router.put("/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    entry_id: str,
    body: UpdateJournalEntryRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> JournalEntryResponse:
    """Update a journal entry.

    Args:
        entry_id: The journal entry ID.
        body: The update request.

    Returns:
        The updated journal entry.

    Raises:
        HTTPException 404: If the entry is not found.
    """
    # Build kwargs from explicitly provided fields (allows setting to null)
    update_kwargs: dict[str, Any] = {}
    if "entry_type" in body.model_fields_set:
        update_kwargs["entry_type"] = body.entry_type
    if "title" in body.model_fields_set:
        update_kwargs["title"] = body.title
    if "content" in body.model_fields_set:
        update_kwargs["content"] = body.content
    if "linked_strategy_id" in body.model_fields_set:
        update_kwargs["linked_strategy_id"] = body.linked_strategy_id
    if "linked_trade_ids" in body.model_fields_set:
        update_kwargs["linked_trade_ids"] = body.linked_trade_ids
    if "tags" in body.model_fields_set:
        update_kwargs["tags"] = body.tags

    entry = await service.update_journal_entry(entry_id, **update_kwargs)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Journal entry {entry_id} not found",
        )

    return _dict_to_entry_response(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_journal_entry(
    entry_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> None:
    """Delete a journal entry.

    Args:
        entry_id: The journal entry ID.

    Raises:
        HTTPException 404: If the entry is not found.
    """
    deleted = await service.delete_journal_entry(entry_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Journal entry {entry_id} not found",
        )
