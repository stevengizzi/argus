"""Migration registry for ``data/regime_history.db`` (Sprint 31.91 Impromptu C).

The ``regime_history`` schema collects RegimeVector snapshots emitted by
the regime intelligence subsystem (~78 rows/day). Owned by
``RegimeHistoryStore`` in ``argus/core/regime_history.py`` (DEC-345
separate-DB pattern).

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C, including the ``vix_close`` column previously
added via in-place ALTER TABLE in ``RegimeHistoryStore._migrate_add_vix_close``.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "regime_history"


_REGIME_SNAPSHOTS_DDL = """
CREATE TABLE IF NOT EXISTS regime_snapshots (
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
);
"""

_REGIME_IDX_DATE = (
    "CREATE INDEX IF NOT EXISTS idx_regime_trading_date "
    "ON regime_snapshots(trading_date);"
)
_REGIME_IDX_PRIMARY_DATE = (
    "CREATE INDEX IF NOT EXISTS idx_regime_primary_date "
    "ON regime_snapshots(primary_regime, trading_date);"
)


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing regime_history schema."""
    await db.execute(_REGIME_SNAPSHOTS_DDL)
    await db.execute(_REGIME_IDX_DATE)
    await db.execute(_REGIME_IDX_PRIMARY_DATE)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP INDEX IF EXISTS idx_regime_primary_date")
    await db.execute("DROP INDEX IF EXISTS idx_regime_trading_date")
    await db.execute("DROP TABLE IF EXISTS regime_snapshots")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: regime_history schema "
            "(regime_snapshots table including vix_close column from "
            "Sprint 27.9 in-place migration)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
