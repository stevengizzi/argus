"""Migration registry for ``data/catalyst.db`` (Sprint 31.91 Impromptu C).

The ``catalyst`` schema collects ARGUS's NLP catalyst pipeline tables:
classified catalyst events, classification cache (keyed by headline hash),
and generated intelligence briefs.

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C, including the ``fetched_at`` column previously
added via in-place ALTER TABLE in ``CatalystStorage.initialize()``.
Pre-existing tables created via ``CREATE TABLE IF NOT EXISTS`` are no-ops
on re-run, so applying v1 to a DB that pre-dates the framework is safe.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "catalyst"


_CATALYST_EVENTS_DDL = """
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
    created_at TEXT NOT NULL,
    fetched_at TEXT
);
"""

_CATALYST_EVENTS_IDX_SYMBOL = (
    "CREATE INDEX IF NOT EXISTS idx_catalyst_symbol "
    "ON catalyst_events(symbol);"
)
_CATALYST_EVENTS_IDX_TYPE = (
    "CREATE INDEX IF NOT EXISTS idx_catalyst_type "
    "ON catalyst_events(catalyst_type);"
)
_CATALYST_EVENTS_IDX_HASH = (
    "CREATE INDEX IF NOT EXISTS idx_catalyst_headline_hash "
    "ON catalyst_events(headline_hash);"
)
_CATALYST_EVENTS_IDX_CREATED = (
    "CREATE INDEX IF NOT EXISTS idx_catalyst_created_at "
    "ON catalyst_events(created_at);"
)


_CATALYST_CACHE_DDL = """
CREATE TABLE IF NOT EXISTS catalyst_classifications_cache (
    headline_hash TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    quality_score REAL NOT NULL,
    summary TEXT NOT NULL,
    trading_relevance TEXT NOT NULL,
    classified_by TEXT NOT NULL,
    cached_at TEXT NOT NULL
);
"""

_CATALYST_CACHE_IDX_CACHED_AT = (
    "CREATE INDEX IF NOT EXISTS idx_cache_cached_at "
    "ON catalyst_classifications_cache(cached_at);"
)


_INTELLIGENCE_BRIEFS_DDL = """
CREATE TABLE IF NOT EXISTS intelligence_briefs (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    brief_type TEXT NOT NULL,
    content TEXT NOT NULL,
    symbols_json TEXT NOT NULL,
    catalyst_count INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    generation_cost_usd REAL NOT NULL
);
"""

_INTELLIGENCE_BRIEFS_IDX_DATE = (
    "CREATE INDEX IF NOT EXISTS idx_briefs_date "
    "ON intelligence_briefs(date);"
)
_INTELLIGENCE_BRIEFS_IDX_TYPE = (
    "CREATE INDEX IF NOT EXISTS idx_briefs_type "
    "ON intelligence_briefs(brief_type);"
)


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing catalyst schema."""
    await db.execute(_CATALYST_EVENTS_DDL)
    await db.execute(_CATALYST_EVENTS_IDX_SYMBOL)
    await db.execute(_CATALYST_EVENTS_IDX_TYPE)
    await db.execute(_CATALYST_EVENTS_IDX_HASH)
    await db.execute(_CATALYST_EVENTS_IDX_CREATED)
    await db.execute(_CATALYST_CACHE_DDL)
    await db.execute(_CATALYST_CACHE_IDX_CACHED_AT)
    await db.execute(_INTELLIGENCE_BRIEFS_DDL)
    await db.execute(_INTELLIGENCE_BRIEFS_IDX_DATE)
    await db.execute(_INTELLIGENCE_BRIEFS_IDX_TYPE)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP INDEX IF EXISTS idx_briefs_type")
    await db.execute("DROP INDEX IF EXISTS idx_briefs_date")
    await db.execute("DROP TABLE IF EXISTS intelligence_briefs")
    await db.execute("DROP INDEX IF EXISTS idx_cache_cached_at")
    await db.execute("DROP TABLE IF EXISTS catalyst_classifications_cache")
    await db.execute("DROP INDEX IF EXISTS idx_catalyst_created_at")
    await db.execute("DROP INDEX IF EXISTS idx_catalyst_headline_hash")
    await db.execute("DROP INDEX IF EXISTS idx_catalyst_type")
    await db.execute("DROP INDEX IF EXISTS idx_catalyst_symbol")
    await db.execute("DROP TABLE IF EXISTS catalyst_events")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: catalyst schema (catalyst_events + "
            "catalyst_classifications_cache + intelligence_briefs, "
            "including fetched_at column from prior in-place migration)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
