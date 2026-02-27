"""Tests for The Debrief API endpoints (briefings, documents, journal, search)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestBriefingsAPI:
    """Tests for /api/v1/debrief/briefings endpoints."""

    @pytest.mark.asyncio
    async def test_create_briefing(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /debrief/briefings creates a new briefing."""
        response = await client_with_debrief.post(
            "/api/v1/debrief/briefings",
            json={
                "date": "2026-02-28",
                "briefing_type": "pre_market",
                "title": "Test Pre-Market",
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["date"] == "2026-02-28"
        assert data["briefing_type"] == "pre_market"
        assert data["title"] == "Test Pre-Market"
        assert data["status"] == "draft"
        assert "## Market Overview" in data["content"]

    @pytest.mark.asyncio
    async def test_create_briefing_unauthenticated(
        self, client_with_debrief: AsyncClient
    ) -> None:
        """POST /debrief/briefings without auth returns 401."""
        response = await client_with_debrief.post(
            "/api/v1/debrief/briefings",
            json={
                "date": "2026-02-28",
                "briefing_type": "pre_market",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_duplicate_briefing_returns_409(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /debrief/briefings with duplicate date+type returns 409."""
        payload = {"date": "2026-03-15", "briefing_type": "eod"}
        await client_with_debrief.post(
            "/api/v1/debrief/briefings",
            json=payload,
            headers=auth_headers,
        )
        response = await client_with_debrief.post(
            "/api/v1/debrief/briefings",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_briefings(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/briefings returns list of briefings."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/briefings",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "briefings" in data
        assert "total" in data
        # seeded_debrief_service creates 3 briefings
        assert data["total"] == 3
        assert len(data["briefings"]) == 3

    @pytest.mark.asyncio
    async def test_list_briefings_with_type_filter(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/briefings with type filter returns filtered results."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/briefings",
            params={"briefing_type": "pre_market"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # seeded_debrief_service creates 2 pre_market briefings
        assert data["total"] == 2
        assert all(b["briefing_type"] == "pre_market" for b in data["briefings"])

    @pytest.mark.asyncio
    async def test_get_briefing(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/briefings/{id} returns a single briefing."""
        # First list to get an ID
        list_response = await client_with_debrief.get(
            "/api/v1/debrief/briefings",
            headers=auth_headers,
        )
        briefing_id = list_response.json()["briefings"][0]["id"]

        response = await client_with_debrief.get(
            f"/api/v1/debrief/briefings/{briefing_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == briefing_id

    @pytest.mark.asyncio
    async def test_get_briefing_not_found(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/briefings/{id} returns 404 for non-existent ID."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/briefings/nonexistent_id",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_briefing(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """PUT /debrief/briefings/{id} updates the briefing."""
        # First list to get an ID
        list_response = await client_with_debrief.get(
            "/api/v1/debrief/briefings",
            headers=auth_headers,
        )
        briefing_id = list_response.json()["briefings"][0]["id"]

        response = await client_with_debrief.put(
            f"/api/v1/debrief/briefings/{briefing_id}",
            json={
                "title": "Updated Title",
                "status": "final",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["status"] == "final"

    @pytest.mark.asyncio
    async def test_delete_briefing(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """DELETE /debrief/briefings/{id} removes the briefing."""
        # First create a briefing to delete
        create_response = await client_with_debrief.post(
            "/api/v1/debrief/briefings",
            json={"date": "2026-03-01", "briefing_type": "eod"},
            headers=auth_headers,
        )
        briefing_id = create_response.json()["id"]

        response = await client_with_debrief.delete(
            f"/api/v1/debrief/briefings/{briefing_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client_with_debrief.get(
            f"/api/v1/debrief/briefings/{briefing_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


class TestDocumentsAPI:
    """Tests for /api/v1/debrief/documents endpoints."""

    @pytest.mark.asyncio
    async def test_list_documents(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/documents returns both filesystem and database documents."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/documents",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
        # Should include at least the 2 seeded database documents
        assert data["total"] >= 2

    @pytest.mark.asyncio
    async def test_list_documents_with_category_filter(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/documents with category filter returns filtered results."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/documents",
            params={"category": "research"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # seeded_debrief_service creates 2 research documents
        assert len([d for d in data["documents"] if d["source"] == "database"]) == 2

    @pytest.mark.asyncio
    async def test_create_database_document(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /debrief/documents creates a new database document."""
        response = await client_with_debrief.post(
            "/api/v1/debrief/documents",
            json={
                "category": "research",
                "title": "New Research Doc",
                "content": "Research content here.",
                "tags": ["test", "new"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Research Doc"
        assert data["category"] == "research"
        assert data["source"] == "database"
        assert data["is_editable"] is True

    @pytest.mark.asyncio
    async def test_get_database_document(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/documents/{id} returns a database document."""
        # First list to get an ID
        list_response = await client_with_debrief.get(
            "/api/v1/debrief/documents",
            headers=auth_headers,
        )
        # Find a database document
        db_docs = [d for d in list_response.json()["documents"] if d["source"] == "database"]
        doc_id = db_docs[0]["id"]

        response = await client_with_debrief.get(
            f"/api/v1/debrief/documents/{doc_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id

    @pytest.mark.asyncio
    async def test_update_database_document(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """PUT /debrief/documents/{id} updates a database document."""
        # First list to get an ID
        list_response = await client_with_debrief.get(
            "/api/v1/debrief/documents",
            headers=auth_headers,
        )
        db_docs = [d for d in list_response.json()["documents"] if d["source"] == "database"]
        doc_id = db_docs[0]["id"]

        response = await client_with_debrief.put(
            f"/api/v1/debrief/documents/{doc_id}",
            json={
                "title": "Updated Document Title",
                "tags": ["updated"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Document Title"
        assert data["tags"] == ["updated"]

    @pytest.mark.asyncio
    async def test_reject_edit_filesystem_document(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """PUT /debrief/documents/{fs_id} rejects editing filesystem documents."""
        response = await client_with_debrief.put(
            "/api/v1/debrief/documents/fs_research_test",
            json={"title": "Attempted Edit"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Cannot edit filesystem" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_reject_delete_filesystem_document(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """DELETE /debrief/documents/{fs_id} rejects deleting filesystem documents."""
        response = await client_with_debrief.delete(
            "/api/v1/debrief/documents/fs_research_test",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Cannot delete filesystem" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_database_document(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """DELETE /debrief/documents/{id} removes a database document."""
        # First create a document to delete
        create_response = await client_with_debrief.post(
            "/api/v1/debrief/documents",
            json={
                "category": "research",
                "title": "To Delete",
                "content": "Will be deleted.",
            },
            headers=auth_headers,
        )
        doc_id = create_response.json()["id"]

        response = await client_with_debrief.delete(
            f"/api/v1/debrief/documents/{doc_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_document_tags(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/documents/tags returns unique tags from database documents."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/documents/tags",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        # seeded_debrief_service creates docs with 'test', 'research', 'search' tags
        assert "test" in data["tags"]


class TestJournalAPI:
    """Tests for /api/v1/debrief/journal endpoints."""

    @pytest.mark.asyncio
    async def test_create_journal_entry(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """POST /debrief/journal creates a new journal entry."""
        response = await client_with_debrief.post(
            "/api/v1/debrief/journal",
            json={
                "entry_type": "observation",
                "title": "New Observation",
                "content": "Observing patterns in the market.",
                "tags": ["pattern", "observation"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entry_type"] == "observation"
        assert data["title"] == "New Observation"
        assert data["tags"] == ["pattern", "observation"]

    @pytest.mark.asyncio
    async def test_list_journal_entries(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/journal returns list of journal entries."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/journal",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        # seeded_debrief_service creates 5 entries
        assert data["total"] == 5

    @pytest.mark.asyncio
    async def test_list_journal_entries_with_filters(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/journal with filters returns filtered results."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/journal",
            params={"entry_type": "observation"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # seeded_debrief_service creates 2 observations
        assert data["total"] == 2
        assert all(e["entry_type"] == "observation" for e in data["entries"])

    @pytest.mark.asyncio
    async def test_get_journal_entry(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/journal/{id} returns a single journal entry."""
        # First list to get an ID
        list_response = await client_with_debrief.get(
            "/api/v1/debrief/journal",
            headers=auth_headers,
        )
        entry_id = list_response.json()["entries"][0]["id"]

        response = await client_with_debrief.get(
            f"/api/v1/debrief/journal/{entry_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id

    @pytest.mark.asyncio
    async def test_update_journal_entry(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """PUT /debrief/journal/{id} updates the journal entry."""
        # First list to get an ID
        list_response = await client_with_debrief.get(
            "/api/v1/debrief/journal",
            headers=auth_headers,
        )
        entry_id = list_response.json()["entries"][0]["id"]

        response = await client_with_debrief.put(
            f"/api/v1/debrief/journal/{entry_id}",
            json={
                "title": "Updated Entry Title",
                "tags": ["updated", "test"],
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Entry Title"
        assert data["tags"] == ["updated", "test"]

    @pytest.mark.asyncio
    async def test_delete_journal_entry(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """DELETE /debrief/journal/{id} removes the journal entry."""
        # First create an entry to delete
        create_response = await client_with_debrief.post(
            "/api/v1/debrief/journal",
            json={
                "entry_type": "system_note",
                "title": "To Delete",
                "content": "Will be deleted.",
            },
            headers=auth_headers,
        )
        entry_id = create_response.json()["id"]

        response = await client_with_debrief.delete(
            f"/api/v1/debrief/journal/{entry_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_update_journal_entry_clear_strategy_link(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """PUT /debrief/journal/{id} with null linked_strategy_id clears it."""
        # Create entry with a strategy link
        create_resp = await client_with_debrief.post(
            "/api/v1/debrief/journal",
            json={
                "entry_type": "trade_annotation",
                "title": "Linked Entry",
                "content": "Content",
                "linked_strategy_id": "orb_breakout",
            },
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        # Clear the link
        response = await client_with_debrief.put(
            f"/api/v1/debrief/journal/{entry_id}",
            json={"linked_strategy_id": None},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["linked_strategy_id"] is None

    @pytest.mark.asyncio
    async def test_journal_tags(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/journal/tags returns unique tags from journal entries."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/journal/tags",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        # seeded_debrief_service creates entries with various tags
        assert len(data["tags"]) > 0


class TestSearchAPI:
    """Tests for /api/v1/debrief/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_briefings(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/search with briefings scope searches only briefings."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/search",
            params={"query": "Test", "scope": "briefings"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["briefings"]) > 0
        assert len(data["journal"]) == 0
        assert len(data["documents"]) == 0

    @pytest.mark.asyncio
    async def test_search_journal(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/search with journal scope searches only journal."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/search",
            params={"query": "Test", "scope": "journal"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["briefings"]) == 0
        assert len(data["journal"]) > 0
        assert len(data["documents"]) == 0

    @pytest.mark.asyncio
    async def test_search_all_scopes(
        self, client_with_debrief: AsyncClient, auth_headers: dict[str, str]
    ) -> None:
        """GET /debrief/search with all scope searches across all types."""
        response = await client_with_debrief.get(
            "/api/v1/debrief/search",
            params={"query": "FINDME", "scope": "all"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # seeded_debrief_service creates content with "FINDME" in journal and documents
        assert data["total_count"] >= 2
        assert len(data["journal"]) >= 1
        assert len(data["documents"]) >= 1
