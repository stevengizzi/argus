"""Conversation persistence layer for the AI Copilot.

Manages conversation and message storage for chat history. Conversations are
keyed by calendar date with optional tags (pre-market, session, research, etc.).

NOTE: Shares SQLite write lock with Trade Logger. Monitor latency during
active trading + chat. See RSK-NEW-5.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.ids import generate_id

if TYPE_CHECKING:
    from argus.db.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Valid conversation tags
VALID_TAGS = {"pre-market", "session", "research", "debrief", "general"}


class ConversationManager:
    """Manages conversation and message persistence.

    Stores chat conversations and messages in SQLite. Conversations are
    organized by calendar date and tagged for context (e.g., session,
    research, debrief).

    Usage:
        db = DatabaseManager("data/argus.db")
        await db.initialize()

        conv_manager = ConversationManager(db)
        await conv_manager.initialize()

        conversation = await conv_manager.create_conversation("2026-03-06", tag="session")
        await conv_manager.add_message(conversation["id"], "user", "Hello")
    """

    # Table creation SQL
    _CONVERSATIONS_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS ai_conversations (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            tag TEXT DEFAULT 'general',
            title TEXT DEFAULT '',
            message_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """

    _CONVERSATIONS_INDICES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_conversations_date ON ai_conversations(date)",
        "CREATE INDEX IF NOT EXISTS idx_conversations_tag ON ai_conversations(tag)",
    ]

    _MESSAGES_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS ai_messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_use_data TEXT,
            page_context TEXT,
            is_complete BOOLEAN DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
        )
    """

    _MESSAGES_INDICES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON ai_messages(conversation_id)",
    ]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize the conversation manager.

        Args:
            db: The database manager instance.
        """
        self._db = db

    async def initialize(self) -> None:
        """Initialize database tables.

        Creates ai_conversations and ai_messages tables if they don't exist.
        Safe to call multiple times.
        """
        await self._db.execute(self._CONVERSATIONS_TABLE_SQL)
        for index_sql in self._CONVERSATIONS_INDICES_SQL:
            await self._db.execute(index_sql)

        await self._db.execute(self._MESSAGES_TABLE_SQL)
        for index_sql in self._MESSAGES_INDICES_SQL:
            await self._db.execute(index_sql)

        await self._db.commit()
        logger.info("AI conversation tables initialized")

    async def create_conversation(
        self,
        date: str,
        tag: str = "general",
    ) -> dict:
        """Create a new conversation.

        Args:
            date: Calendar date in YYYY-MM-DD format.
            tag: Conversation tag (pre-market, session, research, debrief, general).

        Returns:
            Dict with conversation data including id, date, tag, title,
            message_count, created_at, updated_at.

        Raises:
            ValueError: If tag is not a valid tag value.
        """
        if tag not in VALID_TAGS:
            raise ValueError(f"Invalid tag '{tag}'. Must be one of: {VALID_TAGS}")

        conversation_id = generate_id()
        now = datetime.now(ZoneInfo("UTC")).isoformat()

        sql = """
            INSERT INTO ai_conversations (id, date, tag, title, message_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """
        await self._db.execute(sql, (conversation_id, date, tag, "", now, now))
        await self._db.commit()

        logger.debug("Created conversation %s for date %s with tag %s", conversation_id[:8], date, tag)

        return {
            "id": conversation_id,
            "date": date,
            "tag": tag,
            "title": "",
            "message_count": 0,
            "created_at": now,
            "updated_at": now,
        }

    async def get_conversation(self, conversation_id: str) -> dict | None:
        """Retrieve a conversation by ID.

        Args:
            conversation_id: The conversation ULID.

        Returns:
            Dict with conversation data, or None if not found.
        """
        sql = "SELECT * FROM ai_conversations WHERE id = ?"
        row = await self._db.fetch_one(sql, (conversation_id,))

        if row is None:
            return None

        return self._row_to_conversation(row)

    async def list_conversations(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List conversations with optional filters.

        Args:
            date_from: Optional start date filter (YYYY-MM-DD).
            date_to: Optional end date filter (YYYY-MM-DD).
            tag: Optional tag filter.
            limit: Maximum number of conversations to return.
            offset: Number of conversations to skip for pagination.

        Returns:
            List of conversation dicts, ordered by updated_at DESC.
        """
        conditions: list[str] = []
        params: list[object] = []

        if date_from is not None:
            conditions.append("date >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("date <= ?")
            params.append(date_to)

        if tag is not None:
            conditions.append("tag = ?")
            params.append(tag)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT * FROM ai_conversations
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = await self._db.fetch_all(sql, tuple(params))
        return [self._row_to_conversation(row) for row in rows]

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_use_data: dict | None = None,
        page_context: dict | None = None,
        is_complete: bool = True,
    ) -> dict:
        """Add a message to a conversation.

        Args:
            conversation_id: The conversation ULID.
            role: Message role ('user' or 'assistant').
            content: Message text content.
            tool_use_data: Optional dict of tool_use blocks from assistant response.
            page_context: Optional dict of page context at time of message (for user msgs).
            is_complete: Whether the message is complete (False for partial streams).

        Returns:
            Dict with message data including id, conversation_id, role, content,
            tool_use_data, page_context, is_complete, created_at.

        Raises:
            ValueError: If role is not 'user' or 'assistant'.
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role '{role}'. Must be 'user' or 'assistant'.")

        message_id = generate_id()
        now = datetime.now(ZoneInfo("UTC")).isoformat()

        tool_use_json = json.dumps(tool_use_data) if tool_use_data else None
        page_context_json = json.dumps(page_context) if page_context else None

        sql = """
            INSERT INTO ai_messages (id, conversation_id, role, content, tool_use_data, page_context, is_complete, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self._db.execute(
            sql,
            (
                message_id,
                conversation_id,
                role,
                content,
                tool_use_json,
                page_context_json,
                is_complete,
                now,
            ),
        )

        # Update conversation message_count and updated_at
        update_sql = """
            UPDATE ai_conversations
            SET message_count = message_count + 1, updated_at = ?
            WHERE id = ?
        """
        await self._db.execute(update_sql, (now, conversation_id))
        await self._db.commit()

        logger.debug("Added %s message to conversation %s", role, conversation_id[:8])

        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "tool_use_data": tool_use_data,
            "page_context": page_context,
            "is_complete": is_complete,
            "created_at": now,
        }

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get messages for a conversation.

        Args:
            conversation_id: The conversation ULID.
            limit: Maximum number of messages to return.
            offset: Number of messages to skip for pagination.

        Returns:
            List of message dicts, ordered oldest-first (chronological).
        """
        sql = """
            SELECT * FROM ai_messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
        """
        rows = await self._db.fetch_all(sql, (conversation_id, limit, offset))
        return [self._row_to_message(row) for row in rows]

    async def mark_message_complete(
        self,
        message_id: str,
        final_content: str,
    ) -> None:
        """Mark a message as complete with final content.

        Used when a streaming message finishes.

        Args:
            message_id: The message ULID.
            final_content: The final complete message content.
        """
        sql = """
            UPDATE ai_messages
            SET content = ?, is_complete = 1
            WHERE id = ?
        """
        await self._db.execute(sql, (final_content, message_id))
        await self._db.commit()

        logger.debug("Marked message %s as complete", message_id[:8])

    async def update_conversation_title(
        self,
        conversation_id: str,
        title: str,
    ) -> None:
        """Update a conversation's title.

        Args:
            conversation_id: The conversation ULID.
            title: The new title.
        """
        now = datetime.now(ZoneInfo("UTC")).isoformat()
        sql = """
            UPDATE ai_conversations
            SET title = ?, updated_at = ?
            WHERE id = ?
        """
        await self._db.execute(sql, (title, now, conversation_id))
        await self._db.commit()

        logger.debug("Updated conversation %s title to '%s'", conversation_id[:8], title[:20])

    async def get_or_create_today_conversation(
        self,
        tag: str = "session",
    ) -> dict:
        """Get or create a conversation for today with the given tag.

        If a conversation exists for today's date with the specified tag,
        returns it. Otherwise creates a new one.

        Args:
            tag: Conversation tag (default: "session").

        Returns:
            Dict with conversation data.
        """
        # Use ET timezone for "today" to match trading hours
        et_tz = ZoneInfo("America/New_York")
        today = date.today()
        today_str = today.isoformat()

        # Try to find existing conversation
        sql = """
            SELECT * FROM ai_conversations
            WHERE date = ? AND tag = ?
            ORDER BY created_at DESC
            LIMIT 1
        """
        row = await self._db.fetch_one(sql, (today_str, tag))

        if row is not None:
            logger.debug("Found existing conversation for today with tag %s", tag)
            return self._row_to_conversation(row)

        # Create new conversation
        return await self.create_conversation(today_str, tag)

    def _row_to_conversation(self, row: object) -> dict:
        """Convert a database row to a conversation dict.

        Args:
            row: The database row (aiosqlite.Row).

        Returns:
            Dict with conversation data.
        """
        r = dict(row)  # type: ignore[arg-type]
        return {
            "id": r["id"],
            "date": r["date"],
            "tag": r["tag"],
            "title": r["title"],
            "message_count": r["message_count"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    def _row_to_message(self, row: object) -> dict:
        """Convert a database row to a message dict.

        Args:
            row: The database row (aiosqlite.Row).

        Returns:
            Dict with message data.
        """
        r = dict(row)  # type: ignore[arg-type]
        return {
            "id": r["id"],
            "conversation_id": r["conversation_id"],
            "role": r["role"],
            "content": r["content"],
            "tool_use_data": json.loads(r["tool_use_data"]) if r["tool_use_data"] else None,
            "page_context": json.loads(r["page_context"]) if r["page_context"] else None,
            "is_complete": bool(r["is_complete"]),
            "created_at": r["created_at"],
        }
