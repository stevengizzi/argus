"""Migration registry for ``data/vix_landscape.db`` (Sprint 31.91 Impromptu C).

The ``vix_landscape`` schema stores daily VIX/SPX OHLC data plus derived
metrics (vol-of-vol ratio, VIX percentile, term structure proxy,
realized vol, variance risk premium). Owned by ``VIXDataService`` in
``argus/data/vix_data_service.py`` (DEC-345 separate-DB pattern).

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C. Pre-existing tables created via
``CREATE TABLE IF NOT EXISTS`` are no-ops on re-run.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "vix_landscape"


_VIX_DAILY_DDL = """
CREATE TABLE IF NOT EXISTS vix_daily (
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
);
"""


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing vix_landscape schema."""
    await db.execute(_VIX_DAILY_DDL)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP TABLE IF EXISTS vix_daily")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: vix_landscape schema (vix_daily "
            "OHLC + derived metrics table)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
