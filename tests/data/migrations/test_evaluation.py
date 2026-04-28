"""Sprint 31.91 Impromptu C — evaluation.db migration framework adoption."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from argus.data.migrations import apply_migrations, current_version
from argus.data.migrations.evaluation import MIGRATIONS, SCHEMA_NAME

EXPECTED_TABLES = {"evaluation_events"}


@pytest.mark.asyncio
async def test_evaluation_v1_creates_expected_tables(tmp_path: Path) -> None:
    """Apply v1; every expected table is registered in ``sqlite_master``."""
    db_path = str(tmp_path / "evaluation.db")
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
async def test_evaluation_v1_is_idempotent(tmp_path: Path) -> None:
    """Re-applying v1 is a no-op; current_version stays at 1."""
    db_path = str(tmp_path / "evaluation.db")
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
async def test_evaluation_v1_preserves_existing_data(tmp_path: Path) -> None:
    """Pre-existing rows in evaluation_events survive framework adoption."""
    db_path = str(tmp_path / "evaluation.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE evaluation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trading_date TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                result TEXT NOT NULL,
                reason TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}'
            )
            """
        )
        await db.execute(
            """
            INSERT INTO evaluation_events
                (trading_date, timestamp, symbol, strategy_id, event_type,
                 result, reason, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2026-04-28",
                "2026-04-28T09:30:00",
                "TSLA",
                "orb_breakout",
                "ENTRY_EVALUATION",
                "ACCEPT",
                "all conditions met",
                "{}",
            ),
        )
        await db.commit()

    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT symbol, strategy_id, result FROM evaluation_events"
        )
        rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "TSLA"
    assert rows[0][1] == "orb_breakout"
    assert rows[0][2] == "ACCEPT"


@pytest.mark.asyncio
async def test_evaluation_schema_version_recorded(tmp_path: Path) -> None:
    """schema_version table records evaluation@v1."""
    db_path = str(tmp_path / "evaluation.db")
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
