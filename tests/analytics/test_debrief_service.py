"""Tests for the debrief service."""

from __future__ import annotations

from pathlib import Path

import pytest

from argus.analytics.debrief_service import DebriefService
from argus.db.manager import DatabaseManager


@pytest.fixture
def debrief_service(db: DatabaseManager) -> DebriefService:
    """Provide a DebriefService backed by a temp database."""
    return DebriefService(db)


class TestBriefings:
    """Tests for briefing CRUD operations."""

    async def test_create_briefing_with_template_pre_market(
        self, debrief_service: DebriefService
    ) -> None:
        """create_briefing generates pre-market template when no content provided."""
        briefing = await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
        )

        assert briefing["id"] is not None
        assert briefing["date"] == "2026-02-27"
        assert briefing["briefing_type"] == "pre_market"
        assert briefing["status"] == "draft"
        assert "Pre-Market Briefing" in briefing["title"]
        assert "## Market Overview" in briefing["content"]
        assert "## Watchlist" in briefing["content"]
        assert "## Game Plan" in briefing["content"]
        assert briefing["word_count"] > 0
        assert briefing["reading_time_min"] >= 1

    async def test_create_briefing_with_template_eod(
        self, debrief_service: DebriefService
    ) -> None:
        """create_briefing generates EOD template when no content provided."""
        briefing = await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="eod",
        )

        assert briefing["briefing_type"] == "eod"
        assert "EOD Briefing" in briefing["title"]
        assert "## Session Summary" in briefing["content"]
        assert "## What Worked" in briefing["content"]
        assert "## Key Lessons" in briefing["content"]

    async def test_create_briefing_custom_content(
        self, debrief_service: DebriefService
    ) -> None:
        """create_briefing accepts custom title and content."""
        briefing = await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
            title="Custom Title",
            content="Custom content here.",
        )

        assert briefing["title"] == "Custom Title"
        assert briefing["content"] == "Custom content here."

    async def test_get_briefing(self, debrief_service: DebriefService) -> None:
        """get_briefing retrieves by ID."""
        created = await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
        )

        retrieved = await debrief_service.get_briefing(created["id"])

        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["date"] == "2026-02-27"

    async def test_get_briefing_not_found(self, debrief_service: DebriefService) -> None:
        """get_briefing returns None for non-existent ID."""
        result = await debrief_service.get_briefing("nonexistent_id")
        assert result is None

    async def test_list_briefings_all(self, debrief_service: DebriefService) -> None:
        """list_briefings returns all briefings."""
        await debrief_service.create_briefing(date="2026-02-27", briefing_type="pre_market")
        await debrief_service.create_briefing(date="2026-02-27", briefing_type="eod")
        await debrief_service.create_briefing(date="2026-02-26", briefing_type="pre_market")

        briefings, total = await debrief_service.list_briefings()

        assert len(briefings) == 3
        assert total == 3

    async def test_list_briefings_filter_type(self, debrief_service: DebriefService) -> None:
        """list_briefings filters by type."""
        await debrief_service.create_briefing(date="2026-02-27", briefing_type="pre_market")
        await debrief_service.create_briefing(date="2026-02-27", briefing_type="eod")
        await debrief_service.create_briefing(date="2026-02-26", briefing_type="pre_market")

        briefings, total = await debrief_service.list_briefings(briefing_type="pre_market")

        assert len(briefings) == 2
        assert total == 2
        assert all(b["briefing_type"] == "pre_market" for b in briefings)

    async def test_list_briefings_filter_date_range(
        self, debrief_service: DebriefService
    ) -> None:
        """list_briefings filters by date range."""
        await debrief_service.create_briefing(date="2026-02-25", briefing_type="pre_market")
        await debrief_service.create_briefing(date="2026-02-26", briefing_type="pre_market")
        await debrief_service.create_briefing(date="2026-02-27", briefing_type="pre_market")

        briefings, total = await debrief_service.list_briefings(
            date_from="2026-02-26",
            date_to="2026-02-27",
        )

        assert len(briefings) == 2
        assert total == 2

    async def test_list_briefings_pagination(self, debrief_service: DebriefService) -> None:
        """list_briefings respects limit and offset."""
        for i in range(5):
            await debrief_service.create_briefing(
                date=f"2026-02-{20 + i:02d}",
                briefing_type="pre_market",
            )

        briefings, total = await debrief_service.list_briefings(limit=2, offset=0)
        assert len(briefings) == 2
        assert total == 5

        briefings, total = await debrief_service.list_briefings(limit=2, offset=2)
        assert len(briefings) == 2
        assert total == 5

    async def test_update_briefing(self, debrief_service: DebriefService) -> None:
        """update_briefing updates fields."""
        created = await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
        )

        updated = await debrief_service.update_briefing(
            created["id"],
            title="Updated Title",
            content="Updated content",
            status="final",
        )

        assert updated is not None
        assert updated["title"] == "Updated Title"
        assert updated["content"] == "Updated content"
        assert updated["status"] == "final"

    async def test_delete_briefing(self, debrief_service: DebriefService) -> None:
        """delete_briefing removes the briefing."""
        created = await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
        )

        result = await debrief_service.delete_briefing(created["id"])
        assert result is True

        retrieved = await debrief_service.get_briefing(created["id"])
        assert retrieved is None

    async def test_delete_briefing_not_found(self, debrief_service: DebriefService) -> None:
        """delete_briefing returns False for non-existent ID."""
        result = await debrief_service.delete_briefing("nonexistent_id")
        assert result is False


class TestJournal:
    """Tests for journal entry CRUD operations."""

    async def test_create_journal_entry(self, debrief_service: DebriefService) -> None:
        """create_journal_entry creates an entry."""
        entry = await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Test Observation",
            content="Observing patterns.",
        )

        assert entry["id"] is not None
        assert entry["entry_type"] == "observation"
        assert entry["title"] == "Test Observation"
        assert entry["content"] == "Observing patterns."
        assert entry["author"] == "user"  # Default author from schema

    async def test_create_journal_entry_with_tags_and_trades(
        self, debrief_service: DebriefService
    ) -> None:
        """create_journal_entry accepts tags and linked trade IDs."""
        entry = await debrief_service.create_journal_entry(
            entry_type="trade_annotation",
            title="Trade Note",
            content="Notes about trade.",
            linked_strategy_id="orb_breakout",
            linked_trade_ids=["trade_001", "trade_002"],
            tags=["discipline", "early-exit"],
        )

        assert entry["linked_strategy_id"] == "orb_breakout"
        assert entry["linked_trade_ids"] == ["trade_001", "trade_002"]
        assert entry["tags"] == ["discipline", "early-exit"]

    async def test_list_journal_entries_filter_type(
        self, debrief_service: DebriefService
    ) -> None:
        """list_journal_entries filters by entry type."""
        await debrief_service.create_journal_entry(
            entry_type="observation", title="Obs 1", content="Content"
        )
        await debrief_service.create_journal_entry(
            entry_type="observation", title="Obs 2", content="Content"
        )
        await debrief_service.create_journal_entry(
            entry_type="pattern_note", title="Pattern", content="Content"
        )

        entries, total = await debrief_service.list_journal_entries(entry_type="observation")

        assert len(entries) == 2
        assert total == 2
        assert all(e["entry_type"] == "observation" for e in entries)

    async def test_list_journal_entries_filter_tag(
        self, debrief_service: DebriefService
    ) -> None:
        """list_journal_entries filters by tag."""
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Entry 1",
            content="Content",
            tags=["regime-change", "timing"],
        )
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Entry 2",
            content="Content",
            tags=["discipline"],
        )

        entries, total = await debrief_service.list_journal_entries(tag="regime-change")

        assert len(entries) == 1
        assert total == 1
        assert "regime-change" in entries[0]["tags"]

    async def test_list_journal_entries_search(self, debrief_service: DebriefService) -> None:
        """list_journal_entries searches title and content."""
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="VWAP patterns",
            content="Content about patterns",
        )
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Other entry",
            content="Something about VWAP strategy",
        )
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="No match",
            content="Nothing relevant",
        )

        entries, total = await debrief_service.list_journal_entries(search="VWAP")

        assert len(entries) == 2
        assert total == 2

    async def test_update_journal_entry(self, debrief_service: DebriefService) -> None:
        """update_journal_entry updates fields."""
        created = await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Original",
            content="Original content",
        )

        updated = await debrief_service.update_journal_entry(
            created["id"],
            title="Updated Title",
            tags=["new-tag"],
        )

        assert updated is not None
        assert updated["title"] == "Updated Title"
        assert updated["tags"] == ["new-tag"]
        # Content unchanged
        assert updated["content"] == "Original content"

    async def test_delete_journal_entry(self, debrief_service: DebriefService) -> None:
        """delete_journal_entry removes the entry."""
        created = await debrief_service.create_journal_entry(
            entry_type="observation",
            title="To Delete",
            content="Content",
        )

        result = await debrief_service.delete_journal_entry(created["id"])
        assert result is True

        retrieved = await debrief_service.get_journal_entry(created["id"])
        assert retrieved is None

    async def test_get_journal_tags(self, debrief_service: DebriefService) -> None:
        """get_journal_tags returns unique sorted tags."""
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Entry 1",
            content="Content",
            tags=["regime-change", "timing"],
        )
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Entry 2",
            content="Content",
            tags=["discipline", "timing"],
        )

        tags = await debrief_service.get_journal_tags()

        assert tags == ["discipline", "regime-change", "timing"]


class TestDocuments:
    """Tests for document CRUD operations."""

    async def test_create_document(self, debrief_service: DebriefService) -> None:
        """create_document creates a document."""
        doc = await debrief_service.create_document(
            category="research",
            title="Test Research",
            content="Research content here.",
            tags=["test", "research"],
        )

        assert doc["id"] is not None
        assert doc["category"] == "research"
        assert doc["title"] == "Test Research"
        assert doc["content"] == "Research content here."
        assert doc["tags"] == ["test", "research"]
        assert doc["source"] == "database"
        assert doc["is_editable"] is True
        assert doc["word_count"] == 3
        assert doc["reading_time_min"] >= 1

    async def test_list_documents_by_category(self, debrief_service: DebriefService) -> None:
        """list_documents filters by category."""
        await debrief_service.create_document(
            category="research", title="Research 1", content="Content"
        )
        await debrief_service.create_document(
            category="research", title="Research 2", content="Content"
        )
        await debrief_service.create_document(
            category="ai_report", title="AI Report", content="Content"
        )

        docs = await debrief_service.list_documents(category="research")

        assert len(docs) == 2
        assert all(d["category"] == "research" for d in docs)

    async def test_update_document(self, debrief_service: DebriefService) -> None:
        """update_document updates fields."""
        created = await debrief_service.create_document(
            category="research",
            title="Original",
            content="Original content",
        )

        updated = await debrief_service.update_document(
            created["id"],
            title="Updated Title",
            content="Updated content with more words.",
        )

        assert updated is not None
        assert updated["title"] == "Updated Title"
        assert updated["content"] == "Updated content with more words."
        assert updated["word_count"] == 5

    async def test_delete_document(self, debrief_service: DebriefService) -> None:
        """delete_document removes the document."""
        created = await debrief_service.create_document(
            category="research",
            title="To Delete",
            content="Content",
        )

        result = await debrief_service.delete_document(created["id"])
        assert result is True

        retrieved = await debrief_service.get_document(created["id"])
        assert retrieved is None

    async def test_discover_filesystem_documents(
        self, debrief_service: DebriefService, tmp_path: Path
    ) -> None:
        """discover_filesystem_documents finds markdown files."""
        # Create temp directory structure
        research_dir = tmp_path / "docs" / "research"
        research_dir.mkdir(parents=True)

        # Create a test markdown file
        test_file = research_dir / "test_doc.md"
        test_file.write_text("# Test Document\n\nThis is test content.", encoding="utf-8")

        # Discover documents from temp path
        docs = debrief_service.discover_filesystem_documents(tmp_path)

        assert len(docs) == 1
        assert docs[0]["id"] == "fs_research_test_doc"
        assert docs[0]["title"] == "Test Document"
        assert docs[0]["category"] == "research"
        assert docs[0]["source"] == "filesystem"
        assert docs[0]["is_editable"] is False
        # Word count: "# Test Document This is test content." = 7 words
        assert docs[0]["word_count"] == 7


class TestSearch:
    """Tests for unified search functionality."""

    async def test_search_all_finds_across_types(
        self, debrief_service: DebriefService
    ) -> None:
        """search_all finds matching items across all content types."""
        # Create content with searchable keyword
        await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
            title="Pre-Market with NVDA analysis",
            content="Looking at NVDA momentum.",
        )
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="NVDA observation",
            content="NVDA patterns observed.",
        )
        await debrief_service.create_document(
            category="research",
            title="NVDA Research",
            content="Deep dive into NVDA.",
        )

        results = await debrief_service.search_all(query="NVDA", scope="all")

        assert len(results["briefings"]) == 1
        assert len(results["journal"]) == 1
        assert len(results["documents"]) == 1

    async def test_search_scoped_to_briefings(self, debrief_service: DebriefService) -> None:
        """search_all with briefings scope only searches briefings."""
        await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
            title="Test Briefing",
            content="Contains searchterm here.",
        )
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Journal with searchterm",
            content="Content",
        )

        results = await debrief_service.search_all(query="searchterm", scope="briefings")

        assert len(results["briefings"]) == 1
        assert len(results["journal"]) == 0
        assert len(results["documents"]) == 0

    async def test_search_scoped_to_journal(self, debrief_service: DebriefService) -> None:
        """search_all with journal scope only searches journal."""
        await debrief_service.create_briefing(
            date="2026-02-27",
            briefing_type="pre_market",
            title="Briefing with keyword",
            content="Content",
        )
        await debrief_service.create_journal_entry(
            entry_type="observation",
            title="Journal with keyword",
            content="Content",
        )

        results = await debrief_service.search_all(query="keyword", scope="journal")

        assert len(results["briefings"]) == 0
        assert len(results["journal"]) == 1
        assert len(results["documents"]) == 0
