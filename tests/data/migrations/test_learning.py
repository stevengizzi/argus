"""Sprint 31.91 Impromptu C — learning.db migration framework adoption."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from argus.data.migrations import apply_migrations, current_version
from argus.data.migrations.learning import MIGRATIONS, SCHEMA_NAME

EXPECTED_TABLES = {
    "learning_reports",
    "config_proposals",
    "config_change_history",
}


@pytest.mark.asyncio
async def test_learning_v1_creates_expected_tables(tmp_path: Path) -> None:
    """Apply v1; every expected table is registered in ``sqlite_master``."""
    db_path = str(tmp_path / "learning.db")
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
async def test_learning_v1_is_idempotent(tmp_path: Path) -> None:
    """Re-applying v1 is a no-op; current_version stays at 1."""
    db_path = str(tmp_path / "learning.db")
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
async def test_learning_v1_preserves_existing_data(tmp_path: Path) -> None:
    """Pre-existing rows in learning_reports survive framework adoption."""
    db_path = str(tmp_path / "learning.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE learning_reports (
                report_id TEXT PRIMARY KEY,
                generated_at TEXT NOT NULL,
                analysis_window_start TEXT NOT NULL,
                analysis_window_end TEXT NOT NULL,
                report_json TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        await db.execute(
            """
            INSERT INTO learning_reports
                (report_id, generated_at, analysis_window_start,
                 analysis_window_end, report_json, version)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "report-1",
                "2026-04-28T00:00:00",
                "2026-03-29T00:00:00",
                "2026-04-28T00:00:00",
                '{"weights": {}}',
                1,
            ),
        )
        await db.commit()

    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT report_id, report_json FROM learning_reports"
        )
        rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "report-1"
    assert rows[0][1] == '{"weights": {}}'


@pytest.mark.asyncio
async def test_learning_schema_version_recorded(tmp_path: Path) -> None:
    """schema_version table records learning@v1."""
    db_path = str(tmp_path / "learning.db")
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
