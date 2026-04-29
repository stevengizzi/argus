"""SQLite persistence for strategy evaluation events.

Provides durable storage with historical query support and automatic
retention cleanup, so evaluation data survives restarts and enables
after-close diagnostic review.

Sprint 24.5, Session 3.5.
Sprint 31.91 Impromptu C: schema managed by the migration framework.
Sprint 31.915 (DEC-389): retention + observability policy is config-driven
via EvaluationStoreConfig; success-path INFO logged before VACUUM so a
vacuum failure does not eat the deletion record (Phase A H3 finding);
zero-deletion path always logged; pre-VACUUM disk-headroom check refuses
to proceed under disk pressure.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite

from argus.core.config import EvaluationStoreConfig
from argus.data.migrations import apply_migrations
from argus.data.migrations.evaluation import MIGRATIONS, SCHEMA_NAME
from argus.strategies.telemetry import EvaluationEvent

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_INSERT_EVENT = """\
INSERT INTO evaluation_events
    (trading_date, timestamp, symbol, strategy_id, event_type, result, reason, metadata_json)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


class EvaluationEventStore:
    """SQLite-backed store for evaluation events with retention cleanup.

    Retention/observability policy is supplied via :class:`EvaluationStoreConfig`
    (DEC-389). ``VACUUM_AFTER_CLEANUP`` remains a class constant — it is a
    behavioral toggle, not an operator-tunable value.

    Sprint 31.915 (DEC-389): the legacy ``RETENTION_DAYS`` /
    ``STARTUP_RECLAIM_*`` / ``SIZE_WARNING_THRESHOLD_MB`` /
    ``RETENTION_INTERVAL_SECONDS`` class constants are retained as
    deprecated aliases — ``__init__`` synchronizes them from the
    ``EvaluationStoreConfig`` so the runtime values come from config.
    Pre-existing tests (tests/strategies/test_telemetry_store_vacuum.py
    Sprint 31.8 regression suite) monkeypatch these as instance attributes
    after construction; production reads ``self.<NAME>`` so an instance-
    level override takes precedence over the config-derived default.
    Operators MUST configure via ``config/evaluation_store.yaml`` →
    ``EvaluationStoreConfig`` — the class constants are NOT a public
    operator surface.

    Attributes:
        VACUUM_AFTER_CLEANUP: Whether to VACUUM after retention DELETE.
        RETENTION_DAYS: Deprecated alias of ``_config.retention_days``;
            synced in ``__init__``.
        STARTUP_RECLAIM_FREELIST_RATIO: Deprecated alias of
            ``_config.startup_reclaim_freelist_ratio``.
        STARTUP_RECLAIM_MIN_SIZE_MB: Deprecated alias of
            ``_config.startup_reclaim_min_size_mb``.
        SIZE_WARNING_THRESHOLD_MB: Deprecated alias of
            ``_config.size_warning_threshold_mb``.
        RETENTION_INTERVAL_SECONDS: Deprecated alias of
            ``_config.retention_interval_seconds``.
    """

    VACUUM_AFTER_CLEANUP: bool = True
    _WARNING_INTERVAL_SECONDS: float = 60.0

    # Deprecated class-constant defaults — production reads ``self.<NAME>``,
    # which is synchronized from ``self._config`` in ``__init__``. The class
    # values exist solely to support the Sprint 31.8 VACUUM regression tests'
    # instance-attribute monkeypatch pattern. Do NOT add new reads against
    # these class attributes — read ``self._config.<field>`` directly.
    RETENTION_DAYS: int = 2
    STARTUP_RECLAIM_FREELIST_RATIO: float = 0.5
    STARTUP_RECLAIM_MIN_SIZE_MB: int = 500
    SIZE_WARNING_THRESHOLD_MB: int = 2000
    RETENTION_INTERVAL_SECONDS: int = 4 * 60 * 60

    def __init__(
        self,
        db_path: str,
        config: EvaluationStoreConfig | None = None,
    ) -> None:
        """Initialize the store.

        Args:
            db_path: Path to the SQLite database file.
            config: Retention + observability policy (DEC-389). If ``None``,
                defaults to ``EvaluationStoreConfig()`` (retention_days=2,
                retention_interval_seconds=14400, etc.).
        """
        self._db_path = db_path
        self._config = config or EvaluationStoreConfig()
        # Sync config values into instance attributes for backward-compat
        # with Sprint 31.8 VACUUM regression tests that monkeypatch via
        # instance-attribute assignment. Production code paths below read
        # ``self.<NAME>`` so instance-level overrides take precedence.
        self.RETENTION_DAYS = self._config.retention_days
        self.STARTUP_RECLAIM_FREELIST_RATIO = self._config.startup_reclaim_freelist_ratio
        self.STARTUP_RECLAIM_MIN_SIZE_MB = self._config.startup_reclaim_min_size_mb
        self.SIZE_WARNING_THRESHOLD_MB = self._config.size_warning_threshold_mb
        self.RETENTION_INTERVAL_SECONDS = self._config.retention_interval_seconds
        self._conn: aiosqlite.Connection | None = None
        self._last_warning_time: float = 0.0
        self._retention_task: asyncio.Task[None] | None = None
        # G5 (DEF-233): observability state for /health endpoint subfield.
        # Updated on every cleanup_old_events() invocation regardless of
        # which branch fires (success / zero-deletion).
        self._last_retention_run_at_et: datetime | None = None
        self._last_retention_deleted_count: int | None = None

    async def initialize(self) -> None:
        """Create the evaluation_events table and indexes if they don't exist.

        Also logs DB size/freelist stats at startup and triggers a VACUUM
        if the DB is bloated (freelist ratio exceeds threshold).
        """
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL")
        # Sprint 31.91 Impromptu C: schema managed by the migration framework.
        await apply_migrations(
            self._conn, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
        )

        # Observability: log DB size and freelist ratio at startup
        size_mb = self._get_db_size_mb()
        freelist_ratio = await self._get_freelist_ratio()
        logger.info(
            "EvaluationEventStore initialized: %s (size=%.1f MB, freelist=%.1f%%)",
            self._db_path,
            size_mb,
            freelist_ratio * 100,
        )

        # Startup reclaim: VACUUM if DB is bloated. Reads ``self.<NAME>``
        # (synced from ``self._config`` in ``__init__``) so legacy tests
        # that monkeypatch instance attributes still drive the gate.
        if (
            size_mb >= self.STARTUP_RECLAIM_MIN_SIZE_MB
            and freelist_ratio >= self.STARTUP_RECLAIM_FREELIST_RATIO
        ):
            logger.warning(
                "EvaluationEventStore: DB bloated (%.1f MB, %.1f%% freelist) "
                "— running startup VACUUM to reclaim space",
                size_mb,
                freelist_ratio * 100,
            )
            await self._vacuum()
            new_size_mb = self._get_db_size_mb()
            logger.info(
                "EvaluationEventStore: startup VACUUM complete "
                "(%.1f MB -> %.1f MB, freed %.1f MB)",
                size_mb,
                new_size_mb,
                size_mb - new_size_mb,
            )

        # Post-init size warning. Reads ``self.SIZE_WARNING_THRESHOLD_MB``
        # so legacy instance-attribute overrides are honored.
        final_size_mb = self._get_db_size_mb()
        if final_size_mb >= self.SIZE_WARNING_THRESHOLD_MB:
            logger.warning(
                "EvaluationEventStore: DB size %.1f MB exceeds %d MB threshold "
                "— investigate write volume",
                final_size_mb,
                self.SIZE_WARNING_THRESHOLD_MB,
            )

        # IMPROMPTU-10 (DEF-197): the single startup cleanup_old_events() call
        # cannot keep up with multi-day sessions — once a session crosses the
        # retention boundary, day-N+1 rows accumulate until the next boot.
        # Spawn a periodic retention task so cleanup fires every
        # retention_interval_seconds regardless of how long the process runs.
        # Cancelled in close().
        self._retention_task = asyncio.create_task(self._run_periodic_retention())

    async def write_event(self, event: EvaluationEvent) -> None:
        """Persist a single evaluation event.

        Extracts trading_date from event.timestamp as YYYY-MM-DD.
        Failures are logged but never raised — persistence must not
        disrupt the evaluation pipeline.

        Args:
            event: The evaluation event to persist.
        """
        try:
            if self._conn is None:
                logger.warning("EvaluationEventStore not initialized — skipping write")
                return
            trading_date = event.timestamp.strftime("%Y-%m-%d")
            await self._conn.execute(
                _INSERT_EVENT,
                (
                    trading_date,
                    event.timestamp.isoformat(),
                    event.symbol,
                    event.strategy_id,
                    str(event.event_type),
                    str(event.result),
                    event.reason,
                    json.dumps(event.metadata, default=str),
                ),
            )
            await self._conn.commit()
        except Exception:
            now = time.monotonic()
            if now - self._last_warning_time >= self._WARNING_INTERVAL_SECONDS:
                logger.warning("Failed to write evaluation event", exc_info=True)
                self._last_warning_time = now

    async def query_events(
        self,
        *,
        strategy_id: str,
        symbol: str | None = None,
        date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, object]]:
        """Query persisted evaluation events with filters.

        Args:
            strategy_id: Required strategy filter.
            symbol: Optional ticker filter.
            date: Optional date filter (YYYY-MM-DD). Defaults to today (ET).
            limit: Maximum rows to return.

        Returns:
            List of event dicts, newest first.
        """
        if self._conn is None:
            return []

        if date is None:
            date = datetime.now(_ET).strftime("%Y-%m-%d")

        conditions = ["trading_date = ?", "strategy_id = ?"]
        params: list[object] = [date, strategy_id]

        if symbol is not None:
            conditions.append("symbol = ?")
            params.append(symbol)

        where = " AND ".join(conditions)
        params.append(limit)

        rows = await self._conn.execute(
            f"SELECT * FROM evaluation_events WHERE {where} "  # noqa: S608
            f"ORDER BY timestamp DESC LIMIT ?",
            tuple(params),
        )
        results = await rows.fetchall()
        return [
            {
                "id": row["id"],
                "trading_date": row["trading_date"],
                "timestamp": row["timestamp"],
                "symbol": row["symbol"],
                "strategy_id": row["strategy_id"],
                "event_type": row["event_type"],
                "result": row["result"],
                "reason": row["reason"],
                "metadata": json.loads(row["metadata_json"]),
            }
            for row in results
        ]

    @property
    def is_connected(self) -> bool:
        """Return True if the database connection is open."""
        return self._conn is not None

    async def execute_query(
        self, sql: str, params: tuple[object, ...] = ()
    ) -> list[aiosqlite.Row]:
        """Execute a read-only SQL query and return all rows.

        Provides public access to the underlying connection for
        read-only analytics queries (e.g. ObservatoryService).

        Args:
            sql: SQL query string.
            params: Query parameters.

        Returns:
            List of result rows.
        """
        if self._conn is None:
            return []
        cursor = await self._conn.execute(sql, params)
        return await cursor.fetchall()

    async def cleanup_old_events(self) -> None:
        """Delete events older than ``retention_days`` and optionally VACUUM.

        Sprint 31.915 / DEF-231: the success-path INFO log line is emitted
        BEFORE ``await self._vacuum()`` so a vacuum failure cannot eat the
        deletion record (Phase A H3 finding). The zero-deletion path now
        emits an INFO line of its own (G3 / DEF-231) so operators can
        confirm the periodic task is alive even when no rows aged out.
        ``_last_retention_run_at_et`` and ``_last_retention_deleted_count``
        are updated regardless of branch (G5 / DEF-233).
        """
        if self._conn is None:
            return
        # Reads ``self.RETENTION_DAYS`` (synced from config in __init__)
        # so legacy instance-attribute monkeypatches still drive the cutoff.
        cutoff = (
            datetime.now(_ET) - timedelta(days=self.RETENTION_DAYS)
        ).strftime("%Y-%m-%d")
        size_before_mb = self._get_db_size_mb()
        cursor = await self._conn.execute(
            "DELETE FROM evaluation_events WHERE trading_date < ?",
            (cutoff,),
        )
        await self._conn.commit()
        deleted = cursor.rowcount

        # G5 / DEF-233: record observability state BEFORE any VACUUM attempt
        # so /health reflects the DELETE outcome regardless of VACUUM success.
        self._last_retention_run_at_et = datetime.now(_ET)
        self._last_retention_deleted_count = deleted

        # G3 / DEF-231: log the DELETE outcome BEFORE attempting VACUUM. The
        # production silent-failure mode on Apr 27→28 (Phase A H3 finding)
        # was that VACUUM raised mid-cleanup, propagating up and skipping
        # the success-path INFO line that previously lived AFTER the VACUUM
        # call. Logging BEFORE VACUUM means a vacuum failure does not eat
        # the deletion record. The zero-deletion path also logs so the
        # operator can confirm the periodic task is alive.
        if deleted > 0:
            logger.info(
                "EvaluationEventStore: retention deleted %d rows (before %s, "
                "db size %.1f MB)",
                deleted,
                cutoff,
                size_before_mb,
            )
        else:
            logger.info(
                "EvaluationEventStore: retention scanned (cutoff %s, "
                "0 rows matched)",
                cutoff,
            )

        if deleted > 0 and self.VACUUM_AFTER_CLEANUP:
            await self._vacuum()
            size_after_mb = self._get_db_size_mb()
            logger.info(
                "EvaluationEventStore: post-retention VACUUM complete "
                "(db size %.1f MB -> %.1f MB, freed %.1f MB)",
                size_before_mb,
                size_after_mb,
                size_before_mb - size_after_mb,
            )

    async def _run_periodic_retention(self) -> None:
        """Run cleanup_old_events() on a fixed cadence until cancelled.

        Sleeps ``retention_interval_seconds`` between iterations. Failures
        inside cleanup_old_events() are logged and do not stop the loop.
        Exits cleanly on CancelledError.
        """
        while True:
            try:
                # Reads ``self.RETENTION_INTERVAL_SECONDS`` (synced from
                # config in __init__) so legacy instance-attribute
                # monkeypatches still drive the cadence.
                await asyncio.sleep(self.RETENTION_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                raise
            try:
                await self.cleanup_old_events()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning(
                    "EvaluationEventStore: periodic retention iteration failed",
                    exc_info=True,
                )

    def _get_db_size_mb(self) -> float:
        """Return the database file size in MB, or 0 if file does not exist."""
        path = Path(self._db_path)
        if path.exists():
            return path.stat().st_size / (1024 * 1024)
        return 0.0

    async def _get_freelist_ratio(self) -> float:
        """Return the ratio of freelist pages to total pages (0.0–1.0).

        Returns 0.0 if the connection is not open or page_count is 0.
        """
        if self._conn is None:
            return 0.0
        cursor = await self._conn.execute("PRAGMA freelist_count")
        row = await cursor.fetchone()
        freelist = row[0] if row else 0

        cursor = await self._conn.execute("PRAGMA page_count")
        row = await cursor.fetchone()
        page_count = row[0] if row else 0

        if page_count == 0:
            return 0.0
        return freelist / page_count

    async def get_freelist_pct(self) -> float:
        """Return the freelist ratio as a percentage (0.0–100.0). G5 helper.

        Async sibling of ``get_health_snapshot`` for /health endpoint
        consumers — the freelist read is async because PRAGMA goes through
        aiosqlite.
        """
        return (await self._get_freelist_ratio()) * 100.0

    def get_health_snapshot(self) -> dict[str, Any]:
        """Return current observability state for the /health endpoint (G5).

        Returns the synchronous slice of the evaluation_db health subfield.
        Caller is expected to combine with ``await get_freelist_pct()`` for
        the full payload at /health-render time.
        """
        size_mb = self._get_db_size_mb()
        last_run = self._last_retention_run_at_et
        return {
            "size_mb": round(size_mb, 1),
            "last_retention_run_at_et": last_run.isoformat() if last_run else None,
            "last_retention_deleted_count": self._last_retention_deleted_count,
        }

    async def _vacuum(self) -> None:
        """Run VACUUM to reclaim freed pages.

        VACUUM cannot run inside aiosqlite (raises "SQL statements in progress")
        and the file cannot be truncated while an aiosqlite WAL lock is held.
        Solution: close the aiosqlite connection, VACUUM via a synchronous
        sqlite3 connection with autocommit, then reopen aiosqlite.

        Sprint 31.915 (G4 / DEF-232): refuse to run VACUUM if the volume
        does not have ``pre_vacuum_headroom_multiplier`` × current_db_size
        free. VACUUM creates a temporary copy on the same volume and can
        silently ENOSPC under disk pressure; we abort the cycle loudly
        rather than letting that propagate as a generic exception.
        """
        if self._conn is None:
            return

        # G4 / DEF-232: pre-VACUUM disk-headroom check. Non-bypassable
        # (RULE-039) — there is no skip flag, no env var, and no broad
        # ``except`` swallowing the failure. The DELETE has already
        # committed at this point; aborting here means we lose the VACUUM
        # but keep the DELETE.
        db_path = Path(self._db_path)
        db_size = db_path.stat().st_size if db_path.exists() else 0
        free_bytes = shutil.disk_usage(db_path.parent).free
        required = int(db_size * self._config.pre_vacuum_headroom_multiplier)
        if free_bytes < required:
            logger.warning(
                "EvaluationEventStore: pre-VACUUM headroom check FAILED "
                "(free=%.1f MB, required=%.1f MB at %.1fx multiplier, "
                "db=%.1f MB) — aborting this VACUUM cycle. See "
                "docs/operations/evaluation-db-runbook.md.",
                free_bytes / (1024 * 1024),
                required / (1024 * 1024),
                self._config.pre_vacuum_headroom_multiplier,
                db_size / (1024 * 1024),
            )
            return

        # Close aiosqlite to release WAL locks
        await self._conn.close()
        self._conn = None

        def _sync_vacuum() -> None:
            conn = sqlite3.connect(self._db_path, isolation_level=None)
            try:
                conn.execute("VACUUM")
            finally:
                conn.close()

        await asyncio.to_thread(_sync_vacuum)

        # Reopen aiosqlite connection
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL")

    async def close(self) -> None:
        """Close the database connection and cancel the retention task."""
        if self._retention_task is not None:
            self._retention_task.cancel()
            try:
                await self._retention_task
            except asyncio.CancelledError:
                pass
            self._retention_task = None
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
