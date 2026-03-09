"""SQLite storage for catalyst events and classifications.

Provides async persistence for classified catalysts, classification cache,
and intelligence briefs. Uses aiosqlite with WAL mode for concurrent access.

Database: {data_dir}/catalyst.db (separate from main DB and ai.db)

Sprint 23.5 Session 3 — DEC-164
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from argus.core.ids import generate_id
from argus.intelligence.models import (
    CatalystClassification,
    ClassifiedCatalyst,
    IntelligenceBrief,
)

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


class CatalystStorage:
    """Async SQLite storage for the NLP Catalyst Pipeline.

    Manages three tables:
    - catalyst_events: Persisted classified catalysts
    - catalyst_classifications_cache: Cached classification results by headline hash
    - intelligence_briefs: Generated pre-market and intraday briefs

    Usage:
        storage = CatalystStorage("data/catalyst.db")
        await storage.initialize()

        await storage.store_catalyst(classified_catalyst)
        catalysts = await storage.get_catalysts_by_symbol("AAPL")

        await storage.close()
    """

    _CATALYST_EVENTS_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS catalyst_events (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            catalyst_type TEXT NOT NULL,
            quality_score REAL NOT NULL,
            headline TEXT NOT NULL,
            summary TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            filing_type TEXT,
            headline_hash TEXT NOT NULL,
            published_at TEXT NOT NULL,
            classified_at TEXT NOT NULL,
            classified_by TEXT NOT NULL,
            trading_relevance TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """

    _CATALYST_EVENTS_INDICES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_catalyst_symbol ON catalyst_events(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_catalyst_type ON catalyst_events(catalyst_type)",
        "CREATE INDEX IF NOT EXISTS idx_catalyst_headline_hash ON catalyst_events(headline_hash)",
        "CREATE INDEX IF NOT EXISTS idx_catalyst_created_at ON catalyst_events(created_at)",
    ]

    _CACHE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS catalyst_classifications_cache (
            headline_hash TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            quality_score REAL NOT NULL,
            summary TEXT NOT NULL,
            trading_relevance TEXT NOT NULL,
            classified_by TEXT NOT NULL,
            cached_at TEXT NOT NULL
        )
    """

    _CACHE_INDICES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_cache_cached_at "
        "ON catalyst_classifications_cache(cached_at)",
    ]

    _BRIEFS_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS intelligence_briefs (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            brief_type TEXT NOT NULL,
            content TEXT NOT NULL,
            symbols_json TEXT NOT NULL,
            catalyst_count INTEGER NOT NULL,
            generated_at TEXT NOT NULL,
            generation_cost_usd REAL NOT NULL
        )
    """

    _BRIEFS_INDICES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_briefs_date ON intelligence_briefs(date)",
        "CREATE INDEX IF NOT EXISTS idx_briefs_type ON intelligence_briefs(brief_type)",
    ]

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the catalyst storage.

        Args:
            db_path: Path to the SQLite database file.
                Use ":memory:" for an in-memory database (testing).
        """
        self._db_path = str(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize the database connection and schema.

        Creates the database file if it doesn't exist, enables WAL mode,
        and creates all required tables.

        Safe to call multiple times.
        """
        # Ensure parent directory exists for file-based databases
        if self._db_path != ":memory:":
            db_file = Path(self._db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row

        # Enable WAL mode for concurrent access
        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.execute("PRAGMA foreign_keys = ON")

        # Create tables
        await self._connection.execute(self._CATALYST_EVENTS_TABLE_SQL)
        for index_sql in self._CATALYST_EVENTS_INDICES_SQL:
            await self._connection.execute(index_sql)

        await self._connection.execute(self._CACHE_TABLE_SQL)
        for index_sql in self._CACHE_INDICES_SQL:
            await self._connection.execute(index_sql)

        await self._connection.execute(self._BRIEFS_TABLE_SQL)
        for index_sql in self._BRIEFS_INDICES_SQL:
            await self._connection.execute(index_sql)

        await self._connection.commit()
        logger.info("Catalyst storage initialized: %s", self._db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            logger.info("Catalyst storage connection closed")

    def _ensure_connected(self) -> aiosqlite.Connection:
        """Ensure the database is connected.

        Returns:
            The active database connection.

        Raises:
            RuntimeError: If the database is not initialized.
        """
        if self._connection is None:
            raise RuntimeError("Storage not initialized. Call initialize() first.")
        return self._connection

    # -------------------------------------------------------------------------
    # Catalyst Events
    # -------------------------------------------------------------------------

    async def store_catalyst(self, catalyst: ClassifiedCatalyst) -> str:
        """Store a classified catalyst.

        Args:
            catalyst: The classified catalyst to store.

        Returns:
            The generated ULID for the stored catalyst.
        """
        conn = self._ensure_connected()
        catalyst_id = generate_id()
        now = datetime.now(_ET).isoformat()

        sql = """
            INSERT INTO catalyst_events (
                id, symbol, catalyst_type, quality_score, headline, summary,
                source, source_url, filing_type, headline_hash, published_at,
                classified_at, classified_by, trading_relevance, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await conn.execute(
            sql,
            (
                catalyst_id,
                catalyst.symbol,
                catalyst.category,
                catalyst.quality_score,
                catalyst.headline,
                catalyst.summary,
                catalyst.source,
                catalyst.source_url,
                catalyst.filing_type,
                catalyst.headline_hash,
                catalyst.published_at.isoformat(),
                catalyst.classified_at.isoformat(),
                catalyst.classified_by,
                catalyst.trading_relevance,
                now,
            ),
        )
        await conn.commit()

        logger.debug("Stored catalyst %s for %s", catalyst_id[:8], catalyst.symbol)
        return catalyst_id

    async def get_catalysts_by_symbol(
        self, symbol: str, limit: int = 50
    ) -> list[ClassifiedCatalyst]:
        """Get catalysts for a specific symbol.

        Args:
            symbol: Stock ticker symbol.
            limit: Maximum number of results.

        Returns:
            List of classified catalysts, ordered by created_at DESC.
        """
        conn = self._ensure_connected()
        sql = """
            SELECT * FROM catalyst_events
            WHERE symbol = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        cursor = await conn.execute(sql, (symbol, limit))
        rows = await cursor.fetchall()
        return [self._row_to_catalyst(row) for row in rows]

    async def get_recent_catalysts(
        self, limit: int = 50, offset: int = 0
    ) -> list[ClassifiedCatalyst]:
        """Get recent catalysts across all symbols.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip for pagination.

        Returns:
            List of classified catalysts, ordered by created_at DESC.
        """
        conn = self._ensure_connected()
        sql = """
            SELECT * FROM catalyst_events
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor = await conn.execute(sql, (limit, offset))
        rows = await cursor.fetchall()
        return [self._row_to_catalyst(row) for row in rows]

    def _row_to_catalyst(self, row: aiosqlite.Row) -> ClassifiedCatalyst:
        """Convert a database row to a ClassifiedCatalyst.

        Args:
            row: The database row.

        Returns:
            A ClassifiedCatalyst instance.
        """
        r: dict[str, Any] = dict(row)
        return ClassifiedCatalyst(
            headline=r["headline"],
            symbol=r["symbol"],
            source=r["source"],
            published_at=datetime.fromisoformat(r["published_at"]),
            fetched_at=datetime.fromisoformat(r["created_at"]),  # Use created_at as fetched_at
            category=r["catalyst_type"],
            quality_score=float(r["quality_score"]),
            summary=r["summary"],
            trading_relevance=r["trading_relevance"],
            classified_by=r["classified_by"],
            classified_at=datetime.fromisoformat(r["classified_at"]),
            headline_hash=r["headline_hash"],
            source_url=r["source_url"],
            filing_type=r["filing_type"],
        )

    # -------------------------------------------------------------------------
    # Classification Cache
    # -------------------------------------------------------------------------

    async def cache_classification(
        self, headline_hash: str, classification: CatalystClassification
    ) -> None:
        """Cache a classification result.

        Uses INSERT OR REPLACE to update existing cache entries.

        Args:
            headline_hash: The headline hash to cache under.
            classification: The classification to cache.
        """
        conn = self._ensure_connected()
        now = datetime.now(_ET).isoformat()

        sql = """
            INSERT OR REPLACE INTO catalyst_classifications_cache (
                headline_hash, category, quality_score, summary,
                trading_relevance, classified_by, cached_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await conn.execute(
            sql,
            (
                headline_hash,
                classification.category,
                classification.quality_score,
                classification.summary,
                classification.trading_relevance,
                classification.classified_by,
                now,
            ),
        )
        await conn.commit()
        logger.debug("Cached classification for hash %s", headline_hash[:8])

    async def get_cached_classification(
        self, headline_hash: str
    ) -> CatalystClassification | None:
        """Get a cached classification by headline hash.

        Args:
            headline_hash: The headline hash to look up.

        Returns:
            The cached classification, or None if not found.
        """
        conn = self._ensure_connected()
        sql = """
            SELECT * FROM catalyst_classifications_cache
            WHERE headline_hash = ?
        """
        cursor = await conn.execute(sql, (headline_hash,))
        row = await cursor.fetchone()

        if row is None:
            return None

        r: dict[str, Any] = dict(row)
        return CatalystClassification(
            category=r["category"],
            quality_score=float(r["quality_score"]),
            summary=r["summary"],
            trading_relevance=r["trading_relevance"],
            classified_by=r["classified_by"],
            classified_at=datetime.fromisoformat(r["cached_at"]),
        )

    async def is_cache_valid(self, headline_hash: str, ttl_hours: int) -> bool:
        """Check if a cache entry exists and is not expired.

        Args:
            headline_hash: The headline hash to check.
            ttl_hours: Cache TTL in hours.

        Returns:
            True if cache exists and is valid, False otherwise.
        """
        conn = self._ensure_connected()
        sql = """
            SELECT cached_at FROM catalyst_classifications_cache
            WHERE headline_hash = ?
        """
        cursor = await conn.execute(sql, (headline_hash,))
        row = await cursor.fetchone()

        if row is None:
            return False

        cached_at = datetime.fromisoformat(row["cached_at"])
        now = datetime.now(_ET)

        # Handle timezone-naive cached_at (legacy data)
        if cached_at.tzinfo is None:
            cached_at = cached_at.replace(tzinfo=_ET)

        age_hours = (now - cached_at).total_seconds() / 3600
        return age_hours < ttl_hours

    # -------------------------------------------------------------------------
    # Intelligence Briefs
    # -------------------------------------------------------------------------

    async def store_brief(self, brief: IntelligenceBrief) -> str:
        """Store an intelligence brief.

        Args:
            brief: The brief to store.

        Returns:
            The generated ULID for the stored brief.
        """
        conn = self._ensure_connected()
        brief_id = generate_id()

        sql = """
            INSERT INTO intelligence_briefs (
                id, date, brief_type, content, symbols_json,
                catalyst_count, generated_at, generation_cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await conn.execute(
            sql,
            (
                brief_id,
                brief.date,
                brief.brief_type,
                brief.content,
                json.dumps(brief.symbols_covered),
                brief.catalyst_count,
                brief.generated_at.isoformat(),
                brief.generation_cost_usd,
            ),
        )
        await conn.commit()

        logger.debug("Stored brief %s for %s", brief_id[:8], brief.date)
        return brief_id

    async def get_brief(
        self, date: str, brief_type: str = "premarket"
    ) -> IntelligenceBrief | None:
        """Get a brief by date and type.

        Args:
            date: The date in YYYY-MM-DD format.
            brief_type: The brief type (default: "premarket").

        Returns:
            The brief if found, None otherwise.
        """
        conn = self._ensure_connected()
        sql = """
            SELECT * FROM intelligence_briefs
            WHERE date = ? AND brief_type = ?
            ORDER BY generated_at DESC
            LIMIT 1
        """
        cursor = await conn.execute(sql, (date, brief_type))
        row = await cursor.fetchone()

        if row is None:
            return None

        return self._row_to_brief(row)

    async def get_brief_history(self, limit: int = 30) -> list[IntelligenceBrief]:
        """Get recent briefs.

        Args:
            limit: Maximum number of briefs to return.

        Returns:
            List of briefs, ordered by date DESC.
        """
        conn = self._ensure_connected()
        sql = """
            SELECT * FROM intelligence_briefs
            ORDER BY date DESC, generated_at DESC
            LIMIT ?
        """
        cursor = await conn.execute(sql, (limit,))
        rows = await cursor.fetchall()
        return [self._row_to_brief(row) for row in rows]

    def _row_to_brief(self, row: aiosqlite.Row) -> IntelligenceBrief:
        """Convert a database row to an IntelligenceBrief.

        Args:
            row: The database row.

        Returns:
            An IntelligenceBrief instance.
        """
        r: dict[str, Any] = dict(row)
        return IntelligenceBrief(
            date=r["date"],
            brief_type=r["brief_type"],
            content=r["content"],
            symbols_covered=json.loads(r["symbols_json"]),
            catalyst_count=r["catalyst_count"],
            generated_at=datetime.fromisoformat(r["generated_at"]),
            generation_cost_usd=float(r["generation_cost_usd"]),
        )
