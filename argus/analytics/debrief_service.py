"""Debrief service for Argus.

Manages briefings, journal entries, and documents for The Debrief page.
Provides read/write access to debrief-related content in the database
and discovery of filesystem-based documents.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from argus.core.ids import generate_id
from argus.db.manager import DatabaseManager

logger = logging.getLogger(__name__)


class DebriefService:
    """Service for managing debrief content (briefings, journal entries, documents).

    Usage:
        db = DatabaseManager("data/argus.db")
        await db.initialize()

        debrief = DebriefService(db)

        briefing = await debrief.create_briefing("2026-02-27", "pre_market")
        entries, total = await debrief.list_journal_entries(entry_type="observation")
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize the debrief service.

        Args:
            db: The database manager instance.
        """
        self._db = db

    # -------------------------------------------------------------------------
    # Briefing Methods
    # -------------------------------------------------------------------------

    async def create_briefing(
        self,
        date: str,
        briefing_type: str,
        title: str | None = None,
        content: str | None = None,
    ) -> dict:
        """Create a new briefing.

        Args:
            date: Date in YYYY-MM-DD format.
            briefing_type: Either 'pre_market' or 'eod'.
            title: Optional title. Auto-generated from type+date if not provided.
            content: Optional content. Template generated if not provided or empty.

        Returns:
            The created briefing as a dict.
        """
        briefing_id = generate_id()

        if title is None:
            type_label = "Pre-Market" if briefing_type == "pre_market" else "EOD"
            title = f"{type_label} Briefing — {date}"

        if content is None or content.strip() == "":
            if briefing_type == "pre_market":
                content = self._generate_pre_market_template()
            else:
                content = self._generate_eod_template()

        sql = """
            INSERT INTO briefings (id, date, briefing_type, title, content)
            VALUES (?, ?, ?, ?, ?)
        """
        await self._db.execute(sql, (briefing_id, date, briefing_type, title, content))
        await self._db.commit()

        logger.info("Created briefing %s: %s %s", briefing_id[:8], briefing_type, date)

        return await self.get_briefing(briefing_id)  # type: ignore[return-value]

    async def get_briefing(self, briefing_id: str) -> dict | None:
        """Retrieve a briefing by ID.

        Args:
            briefing_id: The briefing ID.

        Returns:
            The briefing as a dict, or None if not found.
        """
        sql = "SELECT * FROM briefings WHERE id = ?"
        row = await self._db.fetch_one(sql, (briefing_id,))

        if row is None:
            return None

        return self._row_to_briefing_dict(row)

    async def list_briefings(
        self,
        briefing_type: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List briefings with optional filtering and pagination.

        Args:
            briefing_type: Optional type filter ('pre_market' or 'eod').
            status: Optional status filter ('draft', 'final', 'ai_generated').
            date_from: Optional start date filter (YYYY-MM-DD).
            date_to: Optional end date filter (YYYY-MM-DD).
            limit: Maximum number of briefings to return.
            offset: Number of briefings to skip for pagination.

        Returns:
            Tuple of (list of briefing dicts with word_count and reading_time_min,
            total count).
        """
        conditions: list[str] = []
        params: list[object] = []

        if briefing_type is not None:
            conditions.append("briefing_type = ?")
            params.append(briefing_type)

        if status is not None:
            conditions.append("status = ?")
            params.append(status)

        if date_from is not None:
            conditions.append("date >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("date <= ?")
            params.append(date_to)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_sql = f"SELECT COUNT(*) as count FROM briefings WHERE {where_clause}"
        count_row = await self._db.fetch_one(count_sql, tuple(params))
        total = int(dict(count_row).get("count", 0)) if count_row else 0  # type: ignore[arg-type]

        # Get paginated results
        sql = f"""
            SELECT * FROM briefings
            WHERE {where_clause}
            ORDER BY date DESC, briefing_type ASC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = await self._db.fetch_all(sql, tuple(params))

        briefings = []
        for row in rows:
            briefing = self._row_to_briefing_dict(row)
            briefings.append(briefing)

        return briefings, total

    async def update_briefing(self, briefing_id: str, **kwargs: object) -> dict | None:
        """Update a briefing.

        Args:
            briefing_id: The briefing ID.
            **kwargs: Fields to update (title, content, status, metadata).

        Returns:
            The updated briefing, or None if not found.
        """
        existing = await self.get_briefing(briefing_id)
        if existing is None:
            return None

        allowed_fields = {"title", "content", "status", "metadata"}
        updates: list[str] = []
        params: list[object] = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == "metadata" and value is not None:
                    value = json.dumps(value)
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            return existing

        updates.append("updated_at = datetime('now')")
        params.append(briefing_id)

        sql = f"UPDATE briefings SET {', '.join(updates)} WHERE id = ?"
        await self._db.execute(sql, tuple(params))
        await self._db.commit()

        logger.debug("Updated briefing %s", briefing_id[:8])

        return await self.get_briefing(briefing_id)

    async def delete_briefing(self, briefing_id: str) -> bool:
        """Delete a briefing.

        Args:
            briefing_id: The briefing ID.

        Returns:
            True if deleted, False if not found.
        """
        existing = await self.get_briefing(briefing_id)
        if existing is None:
            return False

        sql = "DELETE FROM briefings WHERE id = ?"
        await self._db.execute(sql, (briefing_id,))
        await self._db.commit()

        logger.info("Deleted briefing %s", briefing_id[:8])

        return True

    # -------------------------------------------------------------------------
    # Journal Entry Methods
    # -------------------------------------------------------------------------

    async def create_journal_entry(
        self,
        entry_type: str,
        title: str,
        content: str,
        linked_strategy_id: str | None = None,
        linked_trade_ids: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Create a new journal entry.

        Args:
            entry_type: Type of entry ('observation', 'trade_annotation',
                'pattern_note', 'system_note').
            title: Entry title.
            content: Entry content (markdown).
            linked_strategy_id: Optional strategy ID to link.
            linked_trade_ids: Optional list of trade IDs to link.
            tags: Optional list of tags.

        Returns:
            The created journal entry as a dict.
        """
        entry_id = generate_id()

        linked_trade_ids_json = json.dumps(linked_trade_ids) if linked_trade_ids else None
        tags_json = json.dumps(tags) if tags else None

        sql = """
            INSERT INTO journal_entries
            (id, entry_type, title, content, linked_strategy_id, linked_trade_ids, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await self._db.execute(
            sql,
            (
                entry_id,
                entry_type,
                title,
                content,
                linked_strategy_id,
                linked_trade_ids_json,
                tags_json,
            ),
        )
        await self._db.commit()

        logger.info("Created journal entry %s: %s", entry_id[:8], entry_type)

        return await self.get_journal_entry(entry_id)  # type: ignore[return-value]

    async def get_journal_entry(self, entry_id: str) -> dict | None:
        """Retrieve a journal entry by ID.

        Args:
            entry_id: The entry ID.

        Returns:
            The entry as a dict with parsed JSON fields, or None if not found.
        """
        sql = "SELECT * FROM journal_entries WHERE id = ?"
        row = await self._db.fetch_one(sql, (entry_id,))

        if row is None:
            return None

        return self._row_to_journal_dict(row)

    async def list_journal_entries(
        self,
        entry_type: str | None = None,
        strategy_id: str | None = None,
        tag: str | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """List journal entries with optional filtering and pagination.

        Args:
            entry_type: Optional entry type filter.
            strategy_id: Optional linked strategy ID filter.
            tag: Optional tag filter (searches within JSON array).
            search: Optional search term for title and content.
            date_from: Optional start date filter (YYYY-MM-DD).
            date_to: Optional end date filter (YYYY-MM-DD).
            limit: Maximum number of entries to return.
            offset: Number of entries to skip for pagination.

        Returns:
            Tuple of (list of entry dicts, total count).
        """
        conditions: list[str] = []
        params: list[object] = []

        if entry_type is not None:
            conditions.append("entry_type = ?")
            params.append(entry_type)

        if strategy_id is not None:
            conditions.append("linked_strategy_id = ?")
            params.append(strategy_id)

        if tag is not None:
            conditions.append("tags LIKE ?")
            params.append(f"%{tag}%")

        if search is not None:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            search_pattern = f"%{search}%"
            params.append(search_pattern)
            params.append(search_pattern)

        if date_from is not None:
            conditions.append("date(created_at) >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("date(created_at) <= ?")
            params.append(date_to)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_sql = f"SELECT COUNT(*) as count FROM journal_entries WHERE {where_clause}"
        count_row = await self._db.fetch_one(count_sql, tuple(params))
        total = int(dict(count_row).get("count", 0)) if count_row else 0  # type: ignore[arg-type]

        # Get paginated results
        sql = f"""
            SELECT * FROM journal_entries
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = await self._db.fetch_all(sql, tuple(params))

        entries = [self._row_to_journal_dict(row) for row in rows]

        return entries, total

    async def update_journal_entry(self, entry_id: str, **kwargs: object) -> dict | None:
        """Update a journal entry.

        Args:
            entry_id: The entry ID.
            **kwargs: Fields to update (title, content, entry_type,
                linked_strategy_id, linked_trade_ids, tags).

        Returns:
            The updated entry, or None if not found.
        """
        existing = await self.get_journal_entry(entry_id)
        if existing is None:
            return None

        allowed_fields = {
            "title",
            "content",
            "entry_type",
            "linked_strategy_id",
            "linked_trade_ids",
            "tags",
        }
        updates: list[str] = []
        params: list[object] = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                if field in ("linked_trade_ids", "tags") and value is not None:
                    value = json.dumps(value)
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            return existing

        updates.append("updated_at = datetime('now')")
        params.append(entry_id)

        sql = f"UPDATE journal_entries SET {', '.join(updates)} WHERE id = ?"
        await self._db.execute(sql, tuple(params))
        await self._db.commit()

        logger.debug("Updated journal entry %s", entry_id[:8])

        return await self.get_journal_entry(entry_id)

    async def delete_journal_entry(self, entry_id: str) -> bool:
        """Delete a journal entry.

        Args:
            entry_id: The entry ID.

        Returns:
            True if deleted, False if not found.
        """
        existing = await self.get_journal_entry(entry_id)
        if existing is None:
            return False

        sql = "DELETE FROM journal_entries WHERE id = ?"
        await self._db.execute(sql, (entry_id,))
        await self._db.commit()

        logger.info("Deleted journal entry %s", entry_id[:8])

        return True

    async def get_journal_tags(self) -> list[str]:
        """Get all unique tags from journal entries.

        Returns:
            Sorted list of unique tags.
        """
        sql = "SELECT DISTINCT tags FROM journal_entries WHERE tags IS NOT NULL"
        rows = await self._db.fetch_all(sql)

        all_tags: set[str] = set()
        for row in rows:
            r = dict(row)  # type: ignore[arg-type]
            tags = self._parse_json_field(r.get("tags"))
            all_tags.update(tags)

        return sorted(all_tags)

    # -------------------------------------------------------------------------
    # Document Methods (Database)
    # -------------------------------------------------------------------------

    async def create_document(
        self,
        category: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """Create a new document in the database.

        Args:
            category: Document category ('research', 'strategy', 'backtest', 'ai_report').
            title: Document title.
            content: Document content (markdown).
            tags: Optional list of tags.
            metadata: Optional metadata dict.

        Returns:
            The created document as a dict.
        """
        document_id = generate_id()

        tags_json = json.dumps(tags) if tags else None
        metadata_json = json.dumps(metadata) if metadata else None

        sql = """
            INSERT INTO documents (id, category, title, content, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        await self._db.execute(
            sql, (document_id, category, title, content, tags_json, metadata_json)
        )
        await self._db.commit()

        logger.info("Created document %s: %s", document_id[:8], category)

        return await self.get_document(document_id)  # type: ignore[return-value]

    async def get_document(self, document_id: str) -> dict | None:
        """Retrieve a document by ID.

        Args:
            document_id: The document ID.

        Returns:
            The document as a dict, or None if not found.
        """
        sql = "SELECT * FROM documents WHERE id = ?"
        row = await self._db.fetch_one(sql, (document_id,))

        if row is None:
            return None

        return self._row_to_document_dict(row)

    async def list_documents(self, category: str | None = None) -> list[dict]:
        """List documents with optional category filter.

        Args:
            category: Optional category filter.

        Returns:
            List of document dicts with word_count and reading_time_min.
        """
        if category is not None:
            sql = "SELECT * FROM documents WHERE category = ? ORDER BY created_at DESC"
            rows = await self._db.fetch_all(sql, (category,))
        else:
            sql = "SELECT * FROM documents ORDER BY created_at DESC"
            rows = await self._db.fetch_all(sql)

        return [self._row_to_document_dict(row) for row in rows]

    async def update_document(self, document_id: str, **kwargs: object) -> dict | None:
        """Update a document.

        Args:
            document_id: The document ID.
            **kwargs: Fields to update (title, content, category, tags, metadata).

        Returns:
            The updated document, or None if not found.
        """
        existing = await self.get_document(document_id)
        if existing is None:
            return None

        allowed_fields = {"title", "content", "category", "tags", "metadata"}
        updates: list[str] = []
        params: list[object] = []

        for field, value in kwargs.items():
            if field in allowed_fields:
                if field in ("tags", "metadata") and value is not None:
                    value = json.dumps(value)
                updates.append(f"{field} = ?")
                params.append(value)

        if not updates:
            return existing

        updates.append("updated_at = datetime('now')")
        params.append(document_id)

        sql = f"UPDATE documents SET {', '.join(updates)} WHERE id = ?"
        await self._db.execute(sql, tuple(params))
        await self._db.commit()

        logger.debug("Updated document %s", document_id[:8])

        return await self.get_document(document_id)

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document.

        Args:
            document_id: The document ID.

        Returns:
            True if deleted, False if not found.
        """
        existing = await self.get_document(document_id)
        if existing is None:
            return False

        sql = "DELETE FROM documents WHERE id = ?"
        await self._db.execute(sql, (document_id,))
        await self._db.commit()

        logger.info("Deleted document %s", document_id[:8])

        return True

    # -------------------------------------------------------------------------
    # Filesystem Document Discovery
    # -------------------------------------------------------------------------

    def discover_filesystem_documents(self, base_dir: str | Path | None = None) -> list[dict]:
        """Discover markdown documents from the filesystem.

        Scans:
        - docs/research/*.md
        - docs/strategies/STRATEGY_*.md
        - docs/backtesting/*.md

        Args:
            base_dir: Base directory (project root). Defaults to auto-detected.

        Returns:
            List of document dicts with filesystem metadata.
        """
        base_dir = Path(__file__).parent.parent.parent if base_dir is None else Path(base_dir)

        documents: list[dict] = []
        scan_patterns = [
            ("research", "docs/research/*.md"),
            ("strategy", "docs/strategies/STRATEGY_*.md"),
            ("backtest", "docs/backtesting/*.md"),
        ]

        for category, pattern in scan_patterns:
            search_path = base_dir / pattern.rsplit("/", 1)[0]
            if not search_path.exists():
                continue

            glob_pattern = pattern.rsplit("/", 1)[1]
            for filepath in search_path.glob(glob_pattern):
                try:
                    doc = self._parse_filesystem_document(filepath, category)
                    documents.append(doc)
                except OSError as e:
                    logger.warning("Failed to read document %s: %s", filepath, e)

        return documents

    def _parse_filesystem_document(self, filepath: Path, category: str) -> dict:
        """Parse a filesystem document into a dict.

        Args:
            filepath: Path to the markdown file.
            category: Document category.

        Returns:
            Document dict with metadata.
        """
        content = filepath.read_text(encoding="utf-8")
        stat = filepath.stat()

        # Extract title from first # heading or use filename
        title = filepath.stem
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        word_count = self._compute_word_count(content)

        return {
            "id": f"fs_{category}_{filepath.stem}",
            "category": category,
            "title": title,
            "content": content,
            "word_count": word_count,
            "reading_time_min": self._compute_reading_time(word_count),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "source": "filesystem",
            "is_editable": False,
            "author": "system",
        }

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    async def search_all(
        self, query: str, scope: str = "all"
    ) -> dict[str, list[dict]]:
        """Search across all content types.

        Args:
            query: Search query string.
            scope: Search scope ('all', 'briefings', 'journal', 'documents').

        Returns:
            Dict with keys 'briefings', 'journal', 'documents', each containing
            a list of matching items.
        """
        results: dict[str, list[dict]] = {
            "briefings": [],
            "journal": [],
            "documents": [],
        }

        pattern = f"%{query}%"

        if scope in ("all", "briefings"):
            sql = """
                SELECT * FROM briefings
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY date DESC
                LIMIT 50
            """
            rows = await self._db.fetch_all(sql, (pattern, pattern))
            results["briefings"] = [self._row_to_briefing_dict(row) for row in rows]

        if scope in ("all", "journal"):
            sql = """
                SELECT * FROM journal_entries
                WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                LIMIT 50
            """
            rows = await self._db.fetch_all(sql, (pattern, pattern, pattern))
            results["journal"] = [self._row_to_journal_dict(row) for row in rows]

        if scope in ("all", "documents"):
            sql = """
                SELECT * FROM documents
                WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                LIMIT 50
            """
            rows = await self._db.fetch_all(sql, (pattern, pattern, pattern))
            results["documents"] = [self._row_to_document_dict(row) for row in rows]

        return results

    # -------------------------------------------------------------------------
    # Template Methods
    # -------------------------------------------------------------------------

    def _generate_pre_market_template(self) -> str:
        """Generate a pre-market briefing template.

        Returns:
            Markdown template with section headers and placeholders.
        """
        return """## Market Overview

Describe overnight futures action, key economic data, and overall market sentiment.

## Key Levels (SPY, QQQ)

| Index | Support | Resistance | VWAP | Notes |
|-------|---------|------------|------|-------|
| SPY   |         |            |      |       |
| QQQ   |         |            |      |       |

## Watchlist

List top 5-10 symbols from the scanner with gap %, relative volume, and setup notes.

## Catalysts

Note any earnings, economic releases, Fed speakers, or news affecting today's session.

## Game Plan

Outline your trading approach for the session: aggressive/defensive, focus sectors, risk limits.
"""

    def _generate_eod_template(self) -> str:
        """Generate an end-of-day briefing template.

        Returns:
            Markdown template with section headers and placeholders.
        """
        return """## Session Summary

Describe overall session: market direction, volatility, volume, notable moves.

## Trades Review

| Symbol | Strategy | Entry | Exit | P&L | Notes |
|--------|----------|-------|------|-----|-------|
|        |          |       |      |     |       |

## What Worked

List successful patterns, good entries, proper risk management.

## What Didn't Work

List mistakes, missed opportunities, areas for improvement.

## Key Lessons

1.
2.
3.

## Tomorrow's Focus

Note any overnight catalysts, watchlist candidates, or adjustments to strategy.
"""

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _compute_word_count(self, text: str) -> int:
        """Compute word count for text.

        Args:
            text: The text content.

        Returns:
            Number of words.
        """
        if not text:
            return 0
        return len(text.split())

    def _compute_reading_time(self, word_count: int) -> int:
        """Compute reading time in minutes.

        Args:
            word_count: Number of words.

        Returns:
            Reading time in minutes (minimum 1).
        """
        return max(1, word_count // 200)

    def _parse_json_field(self, value: str | None) -> list:
        """Safely parse a JSON field.

        Args:
            value: JSON string or None.

        Returns:
            Parsed list, or empty list on error/None.
        """
        if value is None:
            return []
        try:
            result = json.loads(value)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []

    def _row_to_briefing_dict(self, row: object) -> dict:
        """Convert a database row to a briefing dict.

        Args:
            row: The database row.

        Returns:
            Briefing dict with computed fields.
        """
        r = dict(row)  # type: ignore[arg-type]
        content = r.get("content", "") or ""
        word_count = self._compute_word_count(content)

        return {
            "id": r["id"],
            "date": r["date"],
            "briefing_type": r["briefing_type"],
            "status": r["status"],
            "title": r["title"],
            "content": content,
            "metadata": self._parse_json_field(r.get("metadata")) if r.get("metadata") else None,
            "author": r["author"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "word_count": word_count,
            "reading_time_min": self._compute_reading_time(word_count),
        }

    def _row_to_journal_dict(self, row: object) -> dict:
        """Convert a database row to a journal entry dict.

        Args:
            row: The database row.

        Returns:
            Journal entry dict with parsed JSON fields.
        """
        r = dict(row)  # type: ignore[arg-type]

        return {
            "id": r["id"],
            "entry_type": r["entry_type"],
            "title": r["title"],
            "content": r["content"],
            "author": r["author"],
            "linked_strategy_id": r.get("linked_strategy_id"),
            "linked_trade_ids": self._parse_json_field(r.get("linked_trade_ids")),
            "tags": self._parse_json_field(r.get("tags")),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    def _row_to_document_dict(self, row: object) -> dict:
        """Convert a database row to a document dict.

        Args:
            row: The database row.

        Returns:
            Document dict with computed fields.
        """
        r = dict(row)  # type: ignore[arg-type]
        content = r.get("content", "") or ""
        word_count = self._compute_word_count(content)

        return {
            "id": r["id"],
            "category": r["category"],
            "title": r["title"],
            "content": content,
            "author": r["author"],
            "tags": self._parse_json_field(r.get("tags")),
            "metadata": self._parse_json_field(r.get("metadata")) if r.get("metadata") else None,
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "word_count": word_count,
            "reading_time_min": self._compute_reading_time(word_count),
            "source": "database",
            "is_editable": True,
        }
