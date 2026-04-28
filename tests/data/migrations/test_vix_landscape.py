"""Sprint 31.91 Impromptu C — vix_landscape.db migration framework adoption."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from argus.data.migrations import apply_migrations, current_version
from argus.data.migrations.vix_landscape import MIGRATIONS, SCHEMA_NAME

EXPECTED_TABLES = {"vix_daily"}


@pytest.mark.asyncio
async def test_vix_landscape_v1_creates_expected_tables(tmp_path: Path) -> None:
    """Apply v1; every expected table is registered in ``sqlite_master``."""
    db_path = str(tmp_path / "vix_landscape.db")
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
async def test_vix_landscape_v1_is_idempotent(tmp_path: Path) -> None:
    """Re-applying v1 is a no-op; current_version stays at 1."""
    db_path = str(tmp_path / "vix_landscape.db")
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
async def test_vix_landscape_v1_preserves_existing_data(tmp_path: Path) -> None:
    """Pre-existing rows in vix_daily survive framework adoption."""
    db_path = str(tmp_path / "vix_landscape.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE vix_daily (
                date TEXT PRIMARY KEY,
                vix_open REAL,
                vix_high REAL,
                vix_low REAL,
                vix_close REAL,
                spx_open REAL,
                spx_high REAL,
                spx_low REAL,
                spx_close REAL,
                vol_of_vol_ratio REAL,
                vix_percentile REAL,
                term_structure_proxy REAL,
                realized_vol_20d REAL,
                variance_risk_premium REAL
            )
            """
        )
        await db.execute(
            "INSERT INTO vix_daily (date, vix_close, spx_close) VALUES (?, ?, ?)",
            ("2026-04-28", 17.5, 5500.0),
        )
        await db.commit()

    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT date, vix_close, spx_close FROM vix_daily"
        )
        rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "2026-04-28"
    assert rows[0][1] == 17.5
    assert rows[0][2] == 5500.0


@pytest.mark.asyncio
async def test_vix_landscape_schema_version_recorded(tmp_path: Path) -> None:
    """schema_version table records vix_landscape@v1."""
    db_path = str(tmp_path / "vix_landscape.db")
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
