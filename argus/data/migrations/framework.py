"""Schema migration framework (Sprint 31.91 Session 5a.2, MEDIUM #9).

Single-source-of-truth pattern for managed SQLite schemas in ARGUS. Each
managed database (currently only ``data/operations.db``) carries a
``schema_version`` row; ``apply_migrations`` reads the row, runs every
migration with ``version > current`` in order, and bumps the recorded
version inside the same transaction as the migration body.

Append-only by convention. Adding a new schema change is one edit:
register a new ``Migration`` in the appropriate per-DB module (e.g.
``operations.py``). The framework itself is unaware of which DB it is
operating against — both ``schema_name`` and the migration list are
caller-supplied.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import aiosqlite


_SCHEMA_VERSION_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    schema_name TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    applied_at_utc TEXT NOT NULL,
    description TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Migration:
    """One forward step on a schema's version timeline.

    ``up`` is the migration body — typically a sequence of ``CREATE
    TABLE`` / ``ALTER TABLE`` / ``CREATE INDEX`` statements executed
    inside the same transaction that bumps ``schema_version``.

    ``down`` is advisory: production does NOT auto-rollback. Documented
    for manual recovery procedures and so a future engineer reviewing
    the migration log can answer "what was the inverse?" without
    reverse-engineering the up step.
    """

    version: int
    description: str
    up: Callable[["aiosqlite.Connection"], Awaitable[None]]
    down: Callable[["aiosqlite.Connection"], Awaitable[None]] | None = None


async def current_version(
    db: "aiosqlite.Connection",
    *,
    schema_name: str,
) -> int:
    """Return the recorded version for ``schema_name`` (0 if absent)."""
    await db.execute(_SCHEMA_VERSION_DDL)
    cursor = await db.execute(
        "SELECT version FROM schema_version WHERE schema_name = ?",
        (schema_name,),
    )
    row = await cursor.fetchone()
    if row is None:
        return 0
    return int(row[0])


async def apply_migrations(
    db: "aiosqlite.Connection",
    *,
    schema_name: str,
    migrations: list[Migration],
) -> int:
    """Apply every migration with ``version > current``.

    Each migration runs inside a single transaction with the
    ``schema_version`` UPSERT, so a failed migration leaves the
    recorded version unchanged.

    Args:
        db: An open ``aiosqlite`` connection.
        schema_name: Logical name for this schema (e.g. ``"operations"``).
        migrations: Forward migrations sorted by ``version``. The
            framework re-sorts defensively but callers should keep the
            list ordered so the registry reads top-to-bottom.

    Returns:
        The new current version after all migrations applied.
    """
    current = await current_version(db, schema_name=schema_name)
    pending = sorted(
        (m for m in migrations if m.version > current),
        key=lambda m: m.version,
    )
    for migration in pending:
        await db.execute("BEGIN")
        try:
            await migration.up(db)
            await db.execute(
                """
                INSERT INTO schema_version
                    (schema_name, version, applied_at_utc, description)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(schema_name) DO UPDATE SET
                    version=excluded.version,
                    applied_at_utc=excluded.applied_at_utc,
                    description=excluded.description
                """,
                (
                    schema_name,
                    migration.version,
                    datetime.now(UTC).isoformat(),
                    migration.description,
                ),
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        current = migration.version
    return current
