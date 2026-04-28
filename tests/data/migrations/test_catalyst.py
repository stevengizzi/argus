"""Sprint 31.91 Impromptu C — catalyst.db migration framework adoption.

Mirrors ``tests/api/test_alerts_5a2.py::TestMigrationFramework`` for the
catalyst schema. Confirms the v1 migration creates every expected table,
is idempotent, preserves pre-existing data, and records the v1 entry in
``schema_version``.
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from argus.data.migrations import apply_migrations, current_version
from argus.data.migrations.catalyst import MIGRATIONS, SCHEMA_NAME

EXPECTED_TABLES = {
    "catalyst_events",
    "catalyst_classifications_cache",
    "intelligence_briefs",
}


@pytest.mark.asyncio
async def test_catalyst_v1_creates_expected_tables(tmp_path: Path) -> None:
    """Apply v1; every expected table is registered in ``sqlite_master``."""
    db_path = str(tmp_path / "catalyst.db")
    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        rows = await cursor.fetchall()
    table_names = {row[0] for row in rows}
    for table in EXPECTED_TABLES:
        assert table in table_names, f"missing expected table: {table}"


@pytest.mark.asyncio
async def test_catalyst_v1_is_idempotent(tmp_path: Path) -> None:
    """Re-applying v1 is a no-op; current_version stays at 1."""
    db_path = str(tmp_path / "catalyst.db")
    async with aiosqlite.connect(db_path) as db:
        v1 = await apply_migrations(
            db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
        )
        v2 = await apply_migrations(
            db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
        )
        current = await current_version(db, schema_name=SCHEMA_NAME)
        cursor = await db.execute(
            "SELECT COUNT(*) FROM schema_version WHERE schema_name = ?",
            (SCHEMA_NAME,),
        )
        count_row = await cursor.fetchone()
    assert v1 == 1
    assert v2 == 1
    assert current == 1
    assert count_row is not None and count_row[0] == 1


@pytest.mark.asyncio
async def test_catalyst_v1_preserves_existing_data(tmp_path: Path) -> None:
    """Pre-existing rows in catalyst_events survive framework adoption.

    Models the production case: a DB built with the prior service-level DDL
    already contains rows; applying v1 must leave them in place.
    """
    db_path = str(tmp_path / "catalyst.db")
    # Pre-build the pre-framework schema and insert one row.
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE catalyst_events (
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
            )
            """
        )
        await db.execute(
            """
            INSERT INTO catalyst_events (
                id, symbol, catalyst_type, quality_score, headline, summary,
                source, source_url, filing_type, headline_hash, published_at,
                classified_at, classified_by, trading_relevance, created_at,
                fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "01ABC",
                "AAPL",
                "earnings",
                75.0,
                "AAPL beats EPS",
                "summary",
                "finnhub",
                None,
                None,
                "abc123",
                "2026-04-28T09:00:00",
                "2026-04-28T09:01:00",
                "claude",
                "high",
                "2026-04-28T09:02:00",
                "2026-04-28T09:00:30",
            ),
        )
        await db.commit()

    # Adopt the migration framework on the existing DB.
    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT id, symbol, headline FROM catalyst_events WHERE id = ?",
            ("01ABC",),
        )
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "01ABC"
    assert row[1] == "AAPL"
    assert row[2] == "AAPL beats EPS"


@pytest.mark.asyncio
async def test_catalyst_schema_version_recorded(tmp_path: Path) -> None:
    """schema_version table contains a row with schema_name=catalyst, version=1."""
    db_path = str(tmp_path / "catalyst.db")
    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT version, description FROM schema_version "
            "WHERE schema_name = ?",
            (SCHEMA_NAME,),
        )
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 1
    assert "Sprint 31.91" in row[1]
