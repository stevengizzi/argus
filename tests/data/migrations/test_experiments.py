"""Sprint 31.91 Impromptu C — experiments.db migration framework adoption."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from argus.data.migrations import apply_migrations, current_version
from argus.data.migrations.experiments import MIGRATIONS, SCHEMA_NAME

EXPECTED_TABLES = {"experiments", "variants", "promotion_events"}


@pytest.mark.asyncio
async def test_experiments_v1_creates_expected_tables(tmp_path: Path) -> None:
    """Apply v1; every expected table is registered in ``sqlite_master``."""
    db_path = str(tmp_path / "experiments.db")
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
async def test_experiments_v1_is_idempotent(tmp_path: Path) -> None:
    """Re-applying v1 is a no-op; current_version stays at 1."""
    db_path = str(tmp_path / "experiments.db")
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
async def test_experiments_v1_preserves_existing_data(tmp_path: Path) -> None:
    """Pre-existing rows in experiments survive framework adoption."""
    db_path = str(tmp_path / "experiments.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE experiments (
                experiment_id TEXT PRIMARY KEY,
                pattern_name TEXT NOT NULL,
                parameter_fingerprint TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                status TEXT NOT NULL,
                backtest_result_json TEXT,
                shadow_trades INTEGER NOT NULL DEFAULT 0,
                shadow_expectancy REAL,
                is_baseline INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            INSERT INTO experiments (
                experiment_id, pattern_name, parameter_fingerprint,
                parameters_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "exp-1",
                "bull_flag",
                "abc123def4567890",
                '{"min_consolidation_bars": 4}',
                "BACKTEST_COMPLETE",
                "2026-04-28T09:00:00",
                "2026-04-28T09:30:00",
            ),
        )
        await db.commit()

    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT experiment_id, pattern_name, status FROM experiments"
        )
        rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "exp-1"
    assert rows[0][1] == "bull_flag"
    assert rows[0][2] == "BACKTEST_COMPLETE"


@pytest.mark.asyncio
async def test_experiments_schema_version_recorded(tmp_path: Path) -> None:
    """schema_version table records experiments@v1."""
    db_path = str(tmp_path / "experiments.db")
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
