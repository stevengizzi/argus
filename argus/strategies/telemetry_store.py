"""SQLite persistence for strategy evaluation events.

Provides durable storage with historical query support and automatic
retention cleanup, so evaluation data survives restarts and enables
after-close diagnostic review.

Sprint 24.5, Session 3.5.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import aiosqlite

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

    Attributes:
        RETENTION_DAYS: Number of days of history to keep.
        VACUUM_AFTER_CLEANUP: Whether to VACUUM after retention DELETE.
        STARTUP_RECLAIM_FREELIST_RATIO: Trigger startup VACUUM when freelist
            exceeds this fraction of total pages.
        STARTUP_RECLAIM_MIN_SIZE_MB: Only consider startup VACUUM when file
            exceeds this size in MB.
        SIZE_WARNING_THRESHOLD_MB: Log WARNING if DB exceeds this size after
            maintenance.
        RETENTION_INTERVAL_SECONDS: Cadence for the periodic retention task.
            Defaults to 4 hours so a long-running session triggers cleanup
            without waiting for the next boot.
    """

    RETENTION_DAYS: int = 7
    VACUUM_AFTER_CLEANUP: bool = True
    STARTUP_RECLAIM_FREELIST_RATIO: float = 0.5
    STARTUP_RECLAIM_MIN_SIZE_MB: int = 500
    SIZE_WARNING_THRESHOLD_MB: int = 2000
    RETENTION_INTERVAL_SECONDS: int = 4 * 60 * 60
    _WARNING_INTERVAL_SECONDS: float = 60.0

    def __init__(self, db_path: str) -> None:
        """Initialize the store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._last_warning_time: float = 0.0
        self._retention_task: asyncio.Task[None] | None = None

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

        # Startup reclaim: VACUUM if DB is bloated
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

        # Post-init size warning
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
        # retention boundary, day-8 rows accumulate until the next boot. Spawn
        # a periodic retention task so cleanup fires every 4 hours regardless
        # of how long the process runs. Cancelled in close().
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
        """Delete events older than RETENTION_DAYS and optionally VACUUM.

        Uses ET date for the retention boundary. When VACUUM_AFTER_CLEANUP is
        True (default), runs VACUUM after DELETE to reclaim disk space.
        """
        if self._conn is None:
            return
        cutoff = (datetime.now(_ET) - timedelta(days=self.RETENTION_DAYS)).strftime(
            "%Y-%m-%d"
        )
        size_before_mb = self._get_db_size_mb()
        cursor = await self._conn.execute(
            "DELETE FROM evaluation_events WHERE trading_date < ?",
            (cutoff,),
        )
        await self._conn.commit()
        deleted = cursor.rowcount

        if deleted > 0 and self.VACUUM_AFTER_CLEANUP:
            await self._vacuum()
            size_after_mb = self._get_db_size_mb()
            logger.info(
                "EvaluationEventStore: retention deleted %d rows (before %s), "
                "db size %.1f MB -> %.1f MB (freed %.1f MB)",
                deleted,
                cutoff,
                size_before_mb,
                size_after_mb,
                size_before_mb - size_after_mb,
            )
        elif deleted > 0:
            logger.info(
                "Cleaned up %d old evaluation events (before %s)", deleted, cutoff
            )

    async def _run_periodic_retention(self) -> None:
        """Run cleanup_old_events() on a fixed cadence until cancelled.

        Sleeps RETENTION_INTERVAL_SECONDS between iterations. Failures inside
        cleanup_old_events() are logged and do not stop the loop. Exits
        cleanly on CancelledError.
        """
        while True:
            try:
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

    async def _vacuum(self) -> None:
        """Run VACUUM to reclaim freed pages.

        VACUUM cannot run inside aiosqlite (raises "SQL statements in progress")
        and the file cannot be truncated while an aiosqlite WAL lock is held.
        Solution: close the aiosqlite connection, VACUUM via a synchronous
        sqlite3 connection with autocommit, then reopen aiosqlite.
        """
        if self._conn is None:
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
