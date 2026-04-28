"""Migration registry for ``data/learning.db`` (Sprint 31.91 Impromptu C).

The ``learning`` schema collects ARGUS's Learning Loop V1 records:
analysis reports, config proposals, and the change history. Owned by
``LearningStore`` in ``argus/intelligence/learning/learning_store.py``
(DEC-345 separate-DB pattern).

Version 1 codifies the existing schema as it stood at the start of
Sprint 31.91 Impromptu C. Pre-existing tables created via
``CREATE TABLE IF NOT EXISTS`` are no-ops on re-run.
"""

from __future__ import annotations

import aiosqlite

from argus.data.migrations.framework import Migration

SCHEMA_NAME = "learning"


_LEARNING_REPORTS_DDL = """
CREATE TABLE IF NOT EXISTS learning_reports (
    report_id TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    analysis_window_start TEXT NOT NULL,
    analysis_window_end TEXT NOT NULL,
    report_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
"""

_CONFIG_PROPOSALS_DDL = """
CREATE TABLE IF NOT EXISTS config_proposals (
    proposal_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    field_path TEXT NOT NULL,
    current_value REAL NOT NULL,
    proposed_value REAL NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    human_notes TEXT,
    applied_at TEXT,
    reverted_at TEXT,
    FOREIGN KEY (report_id) REFERENCES learning_reports(report_id)
);
"""

_CONFIG_CHANGE_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS config_change_history (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    proposal_id TEXT,
    field_path TEXT NOT NULL,
    old_value REAL NOT NULL,
    new_value REAL NOT NULL,
    source TEXT NOT NULL DEFAULT 'learning_loop',
    applied_at TEXT NOT NULL,
    report_id TEXT,
    FOREIGN KEY (proposal_id) REFERENCES config_proposals(proposal_id)
);
"""

_IDX_REPORTS_GENERATED = (
    "CREATE INDEX IF NOT EXISTS idx_reports_generated_at "
    "ON learning_reports(generated_at);"
)
_IDX_PROPOSALS_STATUS = (
    "CREATE INDEX IF NOT EXISTS idx_proposals_status "
    "ON config_proposals(status);"
)
_IDX_PROPOSALS_REPORT = (
    "CREATE INDEX IF NOT EXISTS idx_proposals_report_id "
    "ON config_proposals(report_id);"
)
_IDX_CHANGES_APPLIED = (
    "CREATE INDEX IF NOT EXISTS idx_changes_applied_at "
    "ON config_change_history(applied_at);"
)


async def _migration_001_up(db: aiosqlite.Connection) -> None:
    """Create all tables required by the existing learning schema."""
    await db.execute(_LEARNING_REPORTS_DDL)
    await db.execute(_CONFIG_PROPOSALS_DDL)
    await db.execute(_CONFIG_CHANGE_HISTORY_DDL)
    await db.execute(_IDX_REPORTS_GENERATED)
    await db.execute(_IDX_PROPOSALS_STATUS)
    await db.execute(_IDX_PROPOSALS_REPORT)
    await db.execute(_IDX_CHANGES_APPLIED)


async def _migration_001_down(db: aiosqlite.Connection) -> None:
    """Advisory inverse for migration 001 (manual rollback only)."""
    await db.execute("DROP INDEX IF EXISTS idx_changes_applied_at")
    await db.execute("DROP INDEX IF EXISTS idx_proposals_report_id")
    await db.execute("DROP INDEX IF EXISTS idx_proposals_status")
    await db.execute("DROP INDEX IF EXISTS idx_reports_generated_at")
    await db.execute("DROP TABLE IF EXISTS config_change_history")
    await db.execute("DROP TABLE IF EXISTS config_proposals")
    await db.execute("DROP TABLE IF EXISTS learning_reports")


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        description=(
            "Sprint 31.91 Impromptu C: learning schema (learning_reports + "
            "config_proposals + config_change_history)"
        ),
        up=_migration_001_up,
        down=_migration_001_down,
    ),
]
