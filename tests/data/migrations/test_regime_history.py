"""Sprint 31.91 Impromptu C — regime_history.db migration framework adoption."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from argus.data.migrations import apply_migrations, current_version
from argus.data.migrations.regime_history import MIGRATIONS, SCHEMA_NAME

EXPECTED_TABLES = {"regime_snapshots"}


@pytest.mark.asyncio
async def test_regime_history_v1_creates_expected_tables(tmp_path: Path) -> None:
    """Apply v1; every expected table is registered in ``sqlite_master``."""
    db_path = str(tmp_path / "regime_history.db")
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
async def test_regime_history_v1_is_idempotent(tmp_path: Path) -> None:
    """Re-applying v1 is a no-op; current_version stays at 1."""
    db_path = str(tmp_path / "regime_history.db")
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
async def test_regime_history_v1_preserves_existing_data(tmp_path: Path) -> None:
    """Pre-existing rows in regime_snapshots survive framework adoption."""
    db_path = str(tmp_path / "regime_history.db")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE regime_snapshots (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                trading_date TEXT NOT NULL,
                primary_regime TEXT NOT NULL,
                regime_confidence REAL NOT NULL,
                trend_score REAL NOT NULL,
                trend_conviction REAL NOT NULL,
                volatility_level REAL NOT NULL,
                volatility_direction REAL NOT NULL,
                universe_breadth_score REAL,
                breadth_thrust INTEGER,
                avg_correlation REAL,
                correlation_regime TEXT,
                sector_rotation_phase TEXT,
                intraday_character TEXT,
                regime_vector_json TEXT NOT NULL,
                vix_close REAL
            )
            """
        )
        await db.execute(
            """
            INSERT INTO regime_snapshots (
                id, timestamp, trading_date, primary_regime, regime_confidence,
                trend_score, trend_conviction, volatility_level, volatility_direction,
                regime_vector_json, vix_close
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "01ULID",
                "2026-04-28T09:30:00",
                "2026-04-28",
                "bullish_trending",
                0.75,
                0.6,
                0.8,
                0.3,
                0.1,
                "{}",
                17.5,
            ),
        )
        await db.commit()

    async with aiosqlite.connect(db_path) as db:
        await apply_migrations(db, schema_name=SCHEMA_NAME, migrations=MIGRATIONS)
        cursor = await db.execute(
            "SELECT id, primary_regime, vix_close FROM regime_snapshots"
        )
        rows = await cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "01ULID"
    assert rows[0][1] == "bullish_trending"
    assert rows[0][2] == 17.5


@pytest.mark.asyncio
async def test_regime_history_schema_version_recorded(tmp_path: Path) -> None:
    """schema_version table records regime_history@v1."""
    db_path = str(tmp_path / "regime_history.db")
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
