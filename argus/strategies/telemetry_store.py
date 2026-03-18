"""SQLite persistence for strategy evaluation events.

Provides durable storage with historical query support and automatic
retention cleanup, so evaluation data survives restarts and enables
after-close diagnostic review.

Sprint 24.5, Session 3.5.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiosqlite

from argus.strategies.telemetry import EvaluationEvent

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_CREATE_TABLE = """\
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
)
"""

_CREATE_IDX_DATE_STRATEGY = (
    "CREATE INDEX IF NOT EXISTS idx_eval_date_strategy "
    "ON evaluation_events(trading_date, strategy_id)"
)

_CREATE_IDX_DATE_SYMBOL = (
    "CREATE INDEX IF NOT EXISTS idx_eval_date_symbol "
    "ON evaluation_events(trading_date, symbol)"
)

_INSERT_EVENT = """\
INSERT INTO evaluation_events
    (trading_date, timestamp, symbol, strategy_id, event_type, result, reason, metadata_json)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


class EvaluationEventStore:
    """SQLite-backed store for evaluation events with retention cleanup.

    Attributes:
        RETENTION_DAYS: Number of days of history to keep.
    """

    RETENTION_DAYS: int = 7

    def __init__(self, db_path: str) -> None:
        """Initialize the store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create the evaluation_events table and indexes if they don't exist."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute(_CREATE_TABLE)
        await self._conn.execute(_CREATE_IDX_DATE_STRATEGY)
        await self._conn.execute(_CREATE_IDX_DATE_SYMBOL)
        await self._conn.commit()
        logger.info("EvaluationEventStore initialized: %s", self._db_path)

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
            logger.warning("Failed to write evaluation event", exc_info=True)

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
        """Delete events older than RETENTION_DAYS.

        Uses ET date for the retention boundary.
        """
        if self._conn is None:
            return
        cutoff = (datetime.now(_ET) - timedelta(days=self.RETENTION_DAYS)).strftime(
            "%Y-%m-%d"
        )
        cursor = await self._conn.execute(
            "DELETE FROM evaluation_events WHERE trading_date < ?",
            (cutoff,),
        )
        await self._conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Cleaned up %d old evaluation events (before %s)", deleted, cutoff)

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
