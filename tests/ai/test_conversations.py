"""Tests for ConversationManager."""

from __future__ import annotations

import pytest

from argus.ai.conversations import ConversationManager, VALID_TAGS
from argus.db.manager import DatabaseManager


@pytest.fixture
async def conv_manager(db: DatabaseManager) -> ConversationManager:
    """Provide an initialized ConversationManager with temp database."""
    manager = ConversationManager(db)
    await manager.initialize()
    return manager


class TestConversationManagerCreate:
    """Test conversation creation."""

    async def test_create_conversation_basic(self, conv_manager: ConversationManager) -> None:
        """create_conversation creates a conversation with correct fields."""
        conv = await conv_manager.create_conversation("2026-03-06", tag="session")

        assert conv["id"] is not None
        assert len(conv["id"]) == 26  # ULID length
        assert conv["date"] == "2026-03-06"
        assert conv["tag"] == "session"
        assert conv["title"] == ""
        assert conv["message_count"] == 0
        assert conv["created_at"] is not None
        assert conv["updated_at"] is not None

    async def test_create_conversation_default_tag(self, conv_manager: ConversationManager) -> None:
        """create_conversation uses 'general' as default tag."""
        conv = await conv_manager.create_conversation("2026-03-06")

        assert conv["tag"] == "general"

    async def test_create_conversation_invalid_tag(self, conv_manager: ConversationManager) -> None:
        """create_conversation raises ValueError for invalid tag."""
        with pytest.raises(ValueError, match="Invalid tag"):
            await conv_manager.create_conversation("2026-03-06", tag="invalid")

    async def test_create_conversation_all_valid_tags(self, conv_manager: ConversationManager) -> None:
        """create_conversation accepts all valid tags."""
        for tag in VALID_TAGS:
            conv = await conv_manager.create_conversation("2026-03-06", tag=tag)
            assert conv["tag"] == tag


class TestConversationManagerGet:
    """Test conversation retrieval."""

    async def test_get_conversation_exists(self, conv_manager: ConversationManager) -> None:
        """get_conversation returns conversation by ID."""
        created = await conv_manager.create_conversation("2026-03-06", tag="research")
        retrieved = await conv_manager.get_conversation(created["id"])

        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["date"] == "2026-03-06"
        assert retrieved["tag"] == "research"

    async def test_get_conversation_not_found(self, conv_manager: ConversationManager) -> None:
        """get_conversation returns None for missing ID."""
        result = await conv_manager.get_conversation("nonexistent_id")
        assert result is None


class TestConversationManagerList:
    """Test conversation listing with filters."""

    async def test_list_conversations_empty(self, conv_manager: ConversationManager) -> None:
        """list_conversations returns empty list when no conversations."""
        result = await conv_manager.list_conversations()
        assert result == []

    async def test_list_conversations_all(self, conv_manager: ConversationManager) -> None:
        """list_conversations returns all conversations."""
        await conv_manager.create_conversation("2026-03-06", tag="session")
        await conv_manager.create_conversation("2026-03-07", tag="research")

        result = await conv_manager.list_conversations()
        assert len(result) == 2

    async def test_list_conversations_filter_by_date_range(
        self, conv_manager: ConversationManager
    ) -> None:
        """list_conversations filters by date range."""
        await conv_manager.create_conversation("2026-03-05")
        await conv_manager.create_conversation("2026-03-06")
        await conv_manager.create_conversation("2026-03-07")
        await conv_manager.create_conversation("2026-03-08")

        # Filter to only 6th and 7th
        result = await conv_manager.list_conversations(
            date_from="2026-03-06", date_to="2026-03-07"
        )
        assert len(result) == 2

    async def test_list_conversations_filter_by_tag(
        self, conv_manager: ConversationManager
    ) -> None:
        """list_conversations filters by tag."""
        await conv_manager.create_conversation("2026-03-06", tag="session")
        await conv_manager.create_conversation("2026-03-06", tag="research")
        await conv_manager.create_conversation("2026-03-06", tag="session")

        result = await conv_manager.list_conversations(tag="session")
        assert len(result) == 2

    async def test_list_conversations_pagination(
        self, conv_manager: ConversationManager
    ) -> None:
        """list_conversations respects limit and offset."""
        for i in range(5):
            await conv_manager.create_conversation(f"2026-03-0{i+1}")

        # Get first 2
        page1 = await conv_manager.list_conversations(limit=2, offset=0)
        assert len(page1) == 2

        # Get next 2
        page2 = await conv_manager.list_conversations(limit=2, offset=2)
        assert len(page2) == 2

        # Get remaining 1
        page3 = await conv_manager.list_conversations(limit=2, offset=4)
        assert len(page3) == 1


class TestConversationManagerMessages:
    """Test message operations."""

    async def test_add_message_user(self, conv_manager: ConversationManager) -> None:
        """add_message adds a user message correctly."""
        conv = await conv_manager.create_conversation("2026-03-06")
        msg = await conv_manager.add_message(conv["id"], "user", "Hello, Claude!")

        assert msg["id"] is not None
        assert msg["conversation_id"] == conv["id"]
        assert msg["role"] == "user"
        assert msg["content"] == "Hello, Claude!"
        assert msg["tool_use_data"] is None
        assert msg["is_complete"] is True

    async def test_add_message_assistant(self, conv_manager: ConversationManager) -> None:
        """add_message adds an assistant message correctly."""
        conv = await conv_manager.create_conversation("2026-03-06")
        msg = await conv_manager.add_message(conv["id"], "assistant", "Hello! How can I help?")

        assert msg["role"] == "assistant"
        assert msg["content"] == "Hello! How can I help?"

    async def test_add_message_with_tool_use_data(
        self, conv_manager: ConversationManager
    ) -> None:
        """add_message correctly stores and retrieves tool_use_data."""
        conv = await conv_manager.create_conversation("2026-03-06")
        tool_data = {"tool_name": "get_positions", "input": {}, "output": []}

        msg = await conv_manager.add_message(
            conv["id"], "assistant", "Checking positions...", tool_use_data=tool_data
        )

        assert msg["tool_use_data"] == tool_data

        # Verify it persists and deserializes correctly
        messages = await conv_manager.get_messages(conv["id"])
        assert messages[0]["tool_use_data"] == tool_data

    async def test_add_message_with_page_context(
        self, conv_manager: ConversationManager
    ) -> None:
        """add_message correctly stores and retrieves page_context."""
        conv = await conv_manager.create_conversation("2026-03-06")
        context = {"page": "dashboard", "active_positions": 3}

        msg = await conv_manager.add_message(
            conv["id"], "user", "What's my P&L?", page_context=context
        )

        assert msg["page_context"] == context

        # Verify it persists
        messages = await conv_manager.get_messages(conv["id"])
        assert messages[0]["page_context"] == context

    async def test_add_message_invalid_role(self, conv_manager: ConversationManager) -> None:
        """add_message raises ValueError for invalid role."""
        conv = await conv_manager.create_conversation("2026-03-06")

        with pytest.raises(ValueError, match="Invalid role"):
            await conv_manager.add_message(conv["id"], "system", "test")

    async def test_add_message_increments_count(
        self, conv_manager: ConversationManager
    ) -> None:
        """add_message increments conversation message_count."""
        conv = await conv_manager.create_conversation("2026-03-06")
        assert conv["message_count"] == 0

        await conv_manager.add_message(conv["id"], "user", "First message")
        await conv_manager.add_message(conv["id"], "assistant", "Response")

        updated = await conv_manager.get_conversation(conv["id"])
        assert updated is not None
        assert updated["message_count"] == 2

    async def test_get_messages_oldest_first(self, conv_manager: ConversationManager) -> None:
        """get_messages returns messages in oldest-first order."""
        conv = await conv_manager.create_conversation("2026-03-06")

        await conv_manager.add_message(conv["id"], "user", "First")
        await conv_manager.add_message(conv["id"], "assistant", "Second")
        await conv_manager.add_message(conv["id"], "user", "Third")

        messages = await conv_manager.get_messages(conv["id"])
        assert len(messages) == 3
        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"

    async def test_get_messages_pagination(self, conv_manager: ConversationManager) -> None:
        """get_messages respects limit and offset."""
        conv = await conv_manager.create_conversation("2026-03-06")

        for i in range(5):
            await conv_manager.add_message(conv["id"], "user", f"Message {i+1}")

        # Get first 2
        page1 = await conv_manager.get_messages(conv["id"], limit=2, offset=0)
        assert len(page1) == 2
        assert page1[0]["content"] == "Message 1"
        assert page1[1]["content"] == "Message 2"

        # Get next 2
        page2 = await conv_manager.get_messages(conv["id"], limit=2, offset=2)
        assert len(page2) == 2
        assert page2[0]["content"] == "Message 3"

    async def test_add_message_incomplete_then_complete(
        self, conv_manager: ConversationManager
    ) -> None:
        """add_message with is_complete=False, then mark_message_complete."""
        conv = await conv_manager.create_conversation("2026-03-06")

        # Add incomplete message (streaming)
        msg = await conv_manager.add_message(
            conv["id"], "assistant", "Starting...", is_complete=False
        )
        assert msg["is_complete"] is False

        # Mark as complete with final content
        await conv_manager.mark_message_complete(msg["id"], "Final complete response.")

        # Verify update
        messages = await conv_manager.get_messages(conv["id"])
        assert len(messages) == 1
        assert messages[0]["is_complete"] is True
        assert messages[0]["content"] == "Final complete response."


class TestConversationManagerTitle:
    """Test conversation title operations."""

    async def test_update_conversation_title(self, conv_manager: ConversationManager) -> None:
        """update_conversation_title sets the title."""
        conv = await conv_manager.create_conversation("2026-03-06")
        assert conv["title"] == ""

        await conv_manager.update_conversation_title(conv["id"], "ORB Strategy Discussion")

        updated = await conv_manager.get_conversation(conv["id"])
        assert updated is not None
        assert updated["title"] == "ORB Strategy Discussion"


class TestConversationManagerGetOrCreate:
    """Test get_or_create_today_conversation."""

    async def test_get_or_create_creates_new(
        self, conv_manager: ConversationManager
    ) -> None:
        """get_or_create_today_conversation creates new when none exists."""
        conv = await conv_manager.get_or_create_today_conversation(tag="session")

        assert conv["id"] is not None
        assert conv["tag"] == "session"
        assert conv["message_count"] == 0

    async def test_get_or_create_returns_existing(
        self, conv_manager: ConversationManager
    ) -> None:
        """get_or_create_today_conversation returns existing conversation."""
        # Create first conversation
        first = await conv_manager.get_or_create_today_conversation(tag="session")

        # Add a message to identify it
        await conv_manager.add_message(first["id"], "user", "Marker message")

        # Get or create again - should return same one
        second = await conv_manager.get_or_create_today_conversation(tag="session")

        assert second["id"] == first["id"]
        assert second["message_count"] == 1

    async def test_get_or_create_different_tags(
        self, conv_manager: ConversationManager
    ) -> None:
        """get_or_create_today_conversation creates separate for different tags."""
        session = await conv_manager.get_or_create_today_conversation(tag="session")
        research = await conv_manager.get_or_create_today_conversation(tag="research")

        assert session["id"] != research["id"]
        assert session["tag"] == "session"
        assert research["tag"] == "research"
