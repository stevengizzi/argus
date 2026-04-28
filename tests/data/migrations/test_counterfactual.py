"""Sprint 31.91 Impromptu C — counterfactual.db migration framework adoption."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from argus.data.migrations import apply_migrations, current_version
from argus.data.migrations.counterfactual import MIGRATIONS, SCHEMA_NAME

EXPECTED_TABLES = {"counterfactual_positions"}


@pytest.mark.asyncio
async def test_counterfactual_v1_creates_expected_tables(tmp_path: Path) -> None:
    """Apply v1; every expected table is registered in ``sqlite_master``."""
    db_path = str(tmp_path / "counterfactual.db")
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
async def test_counterfactual_v1_is_idempotent(tmp_path: Path) -> None:
    """Re-applying v1 is a no-op; current_version stays at 1."""
    db_path = str(tmp_path / "counterfactual.db")
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
async def test_counterfactual_v1_preserves_existing_data(tmp_path: Path) -> None:
    """Pre-existing rows in counterfactual_positions survive framework adoption."""
    db_path = str(tmp_path / "counterfactual.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE counterfactual_positions (
                position_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy_id TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_price REAL NOT NULL,
                target_price REAL NOT NULL,
                time_stop_seconds INTEGER,
                rejection_stage TEXT NOT NULL,
                rejection_reason TEXT NOT NULL,
                quality_score REAL,
                quality_grade TEXT,
                regime_vector_snapshot TEXT,
                signal_metadata TEXT,
                opened_at TEXT NOT NULL,
                closed_at TEXT,
                exit_price REAL,
                exit_reason TEXT,
                theoretical_pnl REAL,
                theoretical_r_multiple REAL,
                duration_seconds REAL,
                max_adverse_excursion REAL DEFAULT 0.0,
                max_favorable_excursion REAL DEFAULT 0.0,
                bars_monitored INTEGER DEFAULT 0,
                variant_id TEXT,
                scoring_fingerprint TEXT
            )
            """
        )
        await db.execute(
            """
            INSERT INTO counterfactual_positions (
                position_id, symbol, strategy_id, entry_price, stop_price,
                target_price, rejection_stage, rejection_reason, opened_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cf-1",
                "AAPL",
                "orb_breakout",
                150.0,
                149.5,
                151.0,
                "QUALITY_FILTER",
                "score below threshold",
                "2026-04-28T09:30:00",
            ),
        )
        await db.commit()

    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT position_id, symbol, rejection_stage "
            "FROM counterfactual_positions"
        )
        rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "cf-1"
    assert rows[0][1] == "AAPL"
    assert rows[0][2] == "QUALITY_FILTER"


@pytest.mark.asyncio
async def test_counterfactual_schema_version_recorded(tmp_path: Path) -> None:
    """schema_version table records counterfactual@v1."""
    db_path = str(tmp_path / "counterfactual.db")
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
