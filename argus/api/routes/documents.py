"""Document routes for The Debrief page.

Provides endpoints for managing research documents, strategy specs, and other
markdown content. Supports both database-stored documents and filesystem discovery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import get_debrief_service

if TYPE_CHECKING:
    from argus.analytics.debrief_service import DebriefService

router = APIRouter()


class CreateDocumentRequest(BaseModel):
    """Request body for creating a new document."""

    category: str
    title: str
    content: str
    tags: list[str] | None = None


class UpdateDocumentRequest(BaseModel):
    """Request body for updating a document."""

    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None


class DocumentResponse(BaseModel):
    """Response model for a single document."""

    id: str
    category: str
    title: str
    content: str
    author: str
    tags: list[str]
    metadata: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    word_count: int
    reading_time_min: int
    source: str
    is_editable: bool
    last_modified: str | None = None


class DocumentsListResponse(BaseModel):
    """Response model for listing documents."""

    documents: list[DocumentResponse]
    total: int


class TagsResponse(BaseModel):
    """Response model for listing unique tags."""

    tags: list[str]


def _dict_to_document_response(doc: dict) -> DocumentResponse:
    """Convert a document dict to DocumentResponse, handling both DB and filesystem docs."""
    return DocumentResponse(
        id=doc["id"],
        category=doc["category"],
        title=doc["title"],
        content=doc["content"],
        author=doc.get("author", "system"),
        tags=doc.get("tags", []),
        metadata=doc.get("metadata"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
        word_count=doc["word_count"],
        reading_time_min=doc["reading_time_min"],
        source=doc.get("source", "database"),
        is_editable=doc.get("is_editable", True),
        last_modified=doc.get("last_modified"),
    )


@router.get("", response_model=DocumentsListResponse)
async def list_documents(
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
    category: str | None = Query(None, description="Filter by category"),
) -> DocumentsListResponse:
    """List all documents, merging filesystem and database sources.

    Documents are sorted by category, then by title.

    Args:
        category: Optional category filter.

    Returns:
        List of all documents with total count.
    """
    # Get filesystem documents
    fs_docs = service.discover_filesystem_documents()

    # Get database documents
    db_docs = await service.list_documents(category=category)

    # Filter filesystem docs by category if specified
    if category is not None:
        fs_docs = [d for d in fs_docs if d["category"] == category]

    # Merge and sort
    all_docs = fs_docs + db_docs
    all_docs.sort(key=lambda d: (d["category"], d["title"]))

    documents = [_dict_to_document_response(d) for d in all_docs]

    return DocumentsListResponse(
        documents=documents,
        total=len(documents),
    )


@router.get("/tags", response_model=TagsResponse)
async def get_document_tags(
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> TagsResponse:
    """Get all unique tags from database documents.

    Returns:
        List of unique tags sorted alphabetically.
    """
    # Get all database documents and extract unique tags
    db_docs = await service.list_documents()
    all_tags: set[str] = set()
    for doc in db_docs:
        tags = doc.get("tags", [])
        if isinstance(tags, list):
            all_tags.update(tags)

    return TagsResponse(tags=sorted(all_tags))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> DocumentResponse:
    """Get a single document by ID.

    Filesystem documents have IDs starting with 'fs_'.

    Args:
        document_id: The document ID.

    Returns:
        The document.

    Raises:
        HTTPException 404: If the document is not found.
    """
    # Check if this is a filesystem document
    if document_id.startswith("fs_"):
        fs_docs = service.discover_filesystem_documents()
        for doc in fs_docs:
            if doc["id"] == document_id:
                return _dict_to_document_response(doc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Otherwise, query database
    doc = await service.get_document(document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return _dict_to_document_response(doc)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    body: CreateDocumentRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> DocumentResponse:
    """Create a new document in the database.

    Args:
        body: The document creation request.

    Returns:
        The created document.
    """
    doc = await service.create_document(
        category=body.category,
        title=body.title,
        content=body.content,
        tags=body.tags,
    )

    return _dict_to_document_response(doc)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    body: UpdateDocumentRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> DocumentResponse:
    """Update a document.

    Only database documents can be updated. Filesystem documents are read-only.

    Args:
        document_id: The document ID.
        body: The update request.

    Returns:
        The updated document.

    Raises:
        HTTPException 400: If attempting to edit a filesystem document.
        HTTPException 404: If the document is not found.
    """
    # Reject filesystem document edits
    if document_id.startswith("fs_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit filesystem documents",
        )

    # Build kwargs from explicitly provided fields (allows setting to null)
    update_kwargs: dict[str, Any] = {}
    if "title" in body.model_fields_set:
        update_kwargs["title"] = body.title
    if "content" in body.model_fields_set:
        update_kwargs["content"] = body.content
    if "category" in body.model_fields_set:
        update_kwargs["category"] = body.category
    if "tags" in body.model_fields_set:
        update_kwargs["tags"] = body.tags

    doc = await service.update_document(document_id, **update_kwargs)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return _dict_to_document_response(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    service: DebriefService = Depends(get_debrief_service),  # noqa: B008
) -> None:
    """Delete a document.

    Only database documents can be deleted. Filesystem documents are read-only.

    Args:
        document_id: The document ID.

    Raises:
        HTTPException 400: If attempting to delete a filesystem document.
        HTTPException 404: If the document is not found.
    """
    # Reject filesystem document deletes
    if document_id.startswith("fs_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete filesystem documents",
        )

    deleted = await service.delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
