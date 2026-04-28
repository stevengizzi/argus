"""Migration registry for ``data/evaluation.db`` (Sprint 31.91 Impromptu C).

The ``evaluation`` schema collects ARGUS's strategy evaluation telemetry:
ENTRY_EVALUATION events emitted by every BaseStrategy through the
``StrategyEvaluationBuffer`` ring buffer (DEC-345 separate-DB pattern).
Owned by ``EvaluationEventStore`` in ``argus/strategies/telemetry_store.py``.

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C. Pre-existing tables created via
``CREATE TABLE IF NOT EXISTS`` are no-ops on re-run.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "evaluation"


_EVALUATION_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS evaluation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trading_date TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    result TEXT NOT NULL,
    reason TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}'
);
"""

_EVALUATION_IDX_DATE_STRATEGY = (
    "CREATE INDEX IF NOT EXISTS idx_eval_date_strategy "
    "ON evaluation_events(trading_date, strategy_id);"
)
_EVALUATION_IDX_DATE_SYMBOL = (
    "CREATE INDEX IF NOT EXISTS idx_eval_date_symbol "
    "ON evaluation_events(trading_date, symbol);"
)


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing evaluation schema."""
    await db.execute(_EVALUATION_EVENTS_DDL)
    await db.execute(_EVALUATION_IDX_DATE_STRATEGY)
    await db.execute(_EVALUATION_IDX_DATE_SYMBOL)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP INDEX IF EXISTS idx_eval_date_symbol")
    await db.execute("DROP INDEX IF EXISTS idx_eval_date_strategy")
    await db.execute("DROP TABLE IF EXISTS evaluation_events")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: evaluation schema (evaluation_events "
            "ring-buffer telemetry table + indexes)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
