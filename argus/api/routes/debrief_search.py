"""Search routes for The Debrief page.

Provides a unified search endpoint across all debrief content types.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import get_debrief_service

if TYPE_CHECKING:
    from argus.analytics.debrief_service import DebriefService

router = APIRouter()


class SearchResultsResponse(BaseModel):
    """Response model for unified search results."""

    briefings: list[dict[str, Any]]
    journal: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    total_count: int


@router.get("/search", response_model=SearchResultsResponse)
async def search_debrief_content(
    query: str = Query(..., min_length=1, description="Search query"),
    scope: str = Query("all", description="Search scope: all, briefings, journal, documents"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> SearchResultsResponse:
    """Search across all debrief content types.

    Searches briefings, journal entries, and documents for the given query.
    Results can be scoped to specific content types.

    Args:
        query: The search query string.
        scope: Search scope ('all', 'briefings', 'journal', 'documents').

    Returns:
        Search results grouped by content type with total count.
    """
    results = await service.search_all(query=query, scope=scope)

    total_count = (
        len(results.get("briefings", []))
        + len(results.get("journal", []))
        + len(results.get("documents", []))
    )

    return SearchResultsResponse(
        briefings=results.get("briefings", []),
        journal=results.get("journal", []),
        documents=results.get("documents", []),
        total_count=total_count,
    )
