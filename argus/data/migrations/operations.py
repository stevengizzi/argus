"""Migration registry for ``data/operations.db`` (Sprint 31.91 5a.2).

The ``operations`` schema collects ARGUS's operator-facing
infrastructure tables: alert state, acknowledgment audit, and Session
2c.1's phantom-short entry-gate.

Version 1 codifies everything that landed up to and including Session
5a.2: the Session 2c.1 ``phantom_short_gated_symbols`` table, the
Session 5a.1 ``alert_acknowledgment_audit`` table, and the Session 5a.2
``alert_state`` table + indexes. Pre-existing tables created via
``CREATE TABLE IF NOT EXISTS`` are no-ops on re-run, so applying v1 to a
DB that pre-dates the migration framework is safe.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "operations"


_PHANTOM_SHORT_GATED_DDL = """
CREATE TABLE IF NOT EXISTS phantom_short_gated_symbols (
    symbol TEXT PRIMARY KEY,
    engaged_at_utc TEXT NOT NULL,
    engaged_at_et TEXT NOT NULL,
    engagement_source TEXT NOT NULL,
    last_observed_short_shares INTEGER
);
"""


_ALERT_ACK_AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS alert_acknowledgment_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TEXT NOT NULL,
    alert_id TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    audit_kind TEXT NOT NULL
);
"""

_ALERT_ACK_AUDIT_IDX_ALERT_ID = (
    "CREATE INDEX IF NOT EXISTS idx_aaa_alert_id "
    "ON alert_acknowledgment_audit(alert_id);"
)
_ALERT_ACK_AUDIT_IDX_TIMESTAMP = (
    "CREATE INDEX IF NOT EXISTS idx_aaa_timestamp "
    "ON alert_acknowledgment_audit(timestamp_utc);"
)


_ALERT_STATE_DDL = """
CREATE TABLE IF NOT EXISTS alert_state (
    alert_id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    emitted_at_utc TEXT NOT NULL,
    emitted_at_et TEXT NOT NULL,
    status TEXT NOT NULL,
    acknowledged_by TEXT,
    acknowledged_at_utc TEXT,
    acknowledgment_reason TEXT,
    auto_resolved_at_utc TEXT,
    archived_at_utc TEXT
);
"""

_ALERT_STATE_IDX_STATUS = (
    "CREATE INDEX IF NOT EXISTS idx_alert_state_status "
    "ON alert_state(status);"
)
_ALERT_STATE_IDX_EMITTED = (
    "CREATE INDEX IF NOT EXISTS idx_alert_state_emitted_at "
    "ON alert_state(emitted_at_utc);"
)
_ALERT_STATE_IDX_TYPE = (
    "CREATE INDEX IF NOT EXISTS idx_alert_state_alert_type "
    "ON alert_state(alert_type);"
)


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by Sprints 31.91 5a.1 + 5a.2."""
    await db.execute(_PHANTOM_SHORT_GATED_DDL)
    await db.execute(_ALERT_ACK_AUDIT_DDL)
    await db.execute(_ALERT_ACK_AUDIT_IDX_ALERT_ID)
    await db.execute(_ALERT_ACK_AUDIT_IDX_TIMESTAMP)
    await db.execute(_ALERT_STATE_DDL)
    await db.execute(_ALERT_STATE_IDX_STATUS)
    await db.execute(_ALERT_STATE_IDX_EMITTED)
    await db.execute(_ALERT_STATE_IDX_TYPE)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP INDEX IF EXISTS idx_alert_state_alert_type")
    await db.execute("DROP INDEX IF EXISTS idx_alert_state_emitted_at")
    await db.execute("DROP INDEX IF EXISTS idx_alert_state_status")
    await db.execute("DROP TABLE IF EXISTS alert_state")
    await db.execute("DROP INDEX IF EXISTS idx_aaa_timestamp")
    await db.execute("DROP INDEX IF EXISTS idx_aaa_alert_id")
    await db.execute("DROP TABLE IF EXISTS alert_acknowledgment_audit")
    await db.execute("DROP TABLE IF EXISTS phantom_short_gated_symbols")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 5a.1+5a.2: alert_state + alert_acknowledgment_audit "
            "+ phantom_short_gated_symbols"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
