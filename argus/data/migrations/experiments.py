"""Migration registry for ``data/experiments.db`` (Sprint 31.91 Impromptu C).

The ``experiments`` schema collects ARGUS's experiment registry: variant
definitions, experiment records (with backtest results), and promotion
events. Owned by ``ExperimentStore`` in
``argus/intelligence/experiments/store.py`` (DEC-345 separate-DB pattern,
Sprint 32).

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C, including the ``exit_overrides`` column on
``variants`` added in Sprint 32.5 S1 via in-place ALTER TABLE.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "experiments"


_EXPERIMENTS_DDL = """
CREATE TABLE IF NOT EXISTS experiments (
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
);
"""

_VARIANTS_DDL = """
CREATE TABLE IF NOT EXISTS variants (
    variant_id TEXT PRIMARY KEY,
    base_pattern TEXT NOT NULL,
    parameter_fingerprint TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    mode TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    exit_overrides TEXT
);
"""

_PROMOTION_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS promotion_events (
    event_id TEXT PRIMARY KEY,
    variant_id TEXT NOT NULL,
    action TEXT NOT NULL,
    previous_mode TEXT NOT NULL,
    new_mode TEXT NOT NULL,
    reason TEXT NOT NULL,
    comparison_verdict_json TEXT,
    shadow_trades INTEGER NOT NULL DEFAULT 0,
    shadow_expectancy REAL,
    timestamp TEXT NOT NULL
);
"""

_IDX_EXP_PATTERN = (
    "CREATE INDEX IF NOT EXISTS idx_exp_pattern_name "
    "ON experiments(pattern_name);"
)
_IDX_EXP_STATUS = (
    "CREATE INDEX IF NOT EXISTS idx_exp_status "
    "ON experiments(status);"
)
_IDX_EXP_CREATED = (
    "CREATE INDEX IF NOT EXISTS idx_exp_created_at "
    "ON experiments(created_at);"
)
_IDX_EXP_FINGERPRINT = (
    "CREATE INDEX IF NOT EXISTS idx_exp_pattern_fingerprint "
    "ON experiments(pattern_name, parameter_fingerprint);"
)
_IDX_VAR_PATTERN = (
    "CREATE INDEX IF NOT EXISTS idx_var_base_pattern "
    "ON variants(base_pattern);"
)
_IDX_VAR_CREATED = (
    "CREATE INDEX IF NOT EXISTS idx_var_created_at "
    "ON variants(created_at);"
)
_IDX_PROMO_VARIANT = (
    "CREATE INDEX IF NOT EXISTS idx_promo_variant_id "
    "ON promotion_events(variant_id);"
)
_IDX_PROMO_TS = (
    "CREATE INDEX IF NOT EXISTS idx_promo_timestamp "
    "ON promotion_events(timestamp);"
)


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing experiments schema."""
    await db.execute(_EXPERIMENTS_DDL)
    await db.execute(_VARIANTS_DDL)
    await db.execute(_PROMOTION_EVENTS_DDL)
    await db.execute(_IDX_EXP_PATTERN)
    await db.execute(_IDX_EXP_STATUS)
    await db.execute(_IDX_EXP_CREATED)
    await db.execute(_IDX_EXP_FINGERPRINT)
    await db.execute(_IDX_VAR_PATTERN)
    await db.execute(_IDX_VAR_CREATED)
    await db.execute(_IDX_PROMO_VARIANT)
    await db.execute(_IDX_PROMO_TS)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP INDEX IF EXISTS idx_promo_timestamp")
    await db.execute("DROP INDEX IF EXISTS idx_promo_variant_id")
    await db.execute("DROP INDEX IF EXISTS idx_var_created_at")
    await db.execute("DROP INDEX IF EXISTS idx_var_base_pattern")
    await db.execute("DROP INDEX IF EXISTS idx_exp_pattern_fingerprint")
    await db.execute("DROP INDEX IF EXISTS idx_exp_created_at")
    await db.execute("DROP INDEX IF EXISTS idx_exp_status")
    await db.execute("DROP INDEX IF EXISTS idx_exp_pattern_name")
    await db.execute("DROP TABLE IF EXISTS promotion_events")
    await db.execute("DROP TABLE IF EXISTS variants")
    await db.execute("DROP TABLE IF EXISTS experiments")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: experiments schema (experiments + "
            "variants + promotion_events; variants includes exit_overrides "
            "from Sprint 32.5 S1 in-place migration)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
