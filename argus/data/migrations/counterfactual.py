"""Migration registry for ``data/counterfactual.db`` (Sprint 31.91 Impromptu C).

The ``counterfactual`` schema stores shadow positions tracked by the
``CounterfactualTracker``. Owned by ``CounterfactualStore`` in
``argus/intelligence/counterfactual_store.py`` (DEC-345 separate-DB
pattern, Sprint 27.7).

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C, including the ``variant_id`` column added in
Sprint 32.5 S5 and the ``scoring_fingerprint`` column added in FIX-01
(audit 2026-04-21) — both previously applied via in-place ALTER TABLE.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "counterfactual"


_COUNTERFACTUAL_POSITIONS_DDL = """
CREATE TABLE IF NOT EXISTS counterfactual_positions (
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
);
"""

_CF_IDX_OPENED_AT = (
    "CREATE INDEX IF NOT EXISTS idx_cf_opened_at "
    "ON counterfactual_positions(opened_at);"
)
_CF_IDX_STRATEGY = (
    "CREATE INDEX IF NOT EXISTS idx_cf_strategy "
    "ON counterfactual_positions(strategy_id);"
)
_CF_IDX_STAGE = (
    "CREATE INDEX IF NOT EXISTS idx_cf_stage "
    "ON counterfactual_positions(rejection_stage);"
)
_CF_IDX_SYMBOL = (
    "CREATE INDEX IF NOT EXISTS idx_cf_symbol "
    "ON counterfactual_positions(symbol);"
)


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing counterfactual schema."""
    await db.execute(_COUNTERFACTUAL_POSITIONS_DDL)
    await db.execute(_CF_IDX_OPENED_AT)
    await db.execute(_CF_IDX_STRATEGY)
    await db.execute(_CF_IDX_STAGE)
    await db.execute(_CF_IDX_SYMBOL)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP INDEX IF EXISTS idx_cf_symbol")
    await db.execute("DROP INDEX IF EXISTS idx_cf_stage")
    await db.execute("DROP INDEX IF EXISTS idx_cf_strategy")
    await db.execute("DROP INDEX IF EXISTS idx_cf_opened_at")
    await db.execute("DROP TABLE IF EXISTS counterfactual_positions")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: counterfactual schema "
            "(counterfactual_positions including variant_id from Sprint 32.5 "
            "S5 and scoring_fingerprint from FIX-01)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
