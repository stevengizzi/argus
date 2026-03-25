"""SQLite persistence for counterfactual positions.

Provides durable storage for shadow positions tracked by the
CounterfactualTracker. Separate database (data/counterfactual.db)
per the DEC-345 pattern of isolated DBs per subsystem.

Sprint 27.7, Session 2.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiosqlite

from argus.intelligence.counterfactual import CounterfactualPosition

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_CREATE_TABLE = """\
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
    bars_monitored INTEGER DEFAULT 0
)
"""

_CREATE_IDX_OPENED_AT = (
    "CREATE INDEX IF NOT EXISTS idx_cf_opened_at "
    "ON counterfactual_positions(opened_at)"
)
_CREATE_IDX_STRATEGY = (
    "CREATE INDEX IF NOT EXISTS idx_cf_strategy "
    "ON counterfactual_positions(strategy_id)"
)
_CREATE_IDX_STAGE = (
    "CREATE INDEX IF NOT EXISTS idx_cf_stage "
    "ON counterfactual_positions(rejection_stage)"
)
_CREATE_IDX_SYMBOL = (
    "CREATE INDEX IF NOT EXISTS idx_cf_symbol "
    "ON counterfactual_positions(symbol)"
)

_INSERT_OPEN = """\
INSERT INTO counterfactual_positions (
    position_id, symbol, strategy_id, entry_price, stop_price,
    target_price, time_stop_seconds, rejection_stage, rejection_reason,
    quality_score, quality_grade, regime_vector_snapshot, signal_metadata,
    opened_at, max_adverse_excursion, max_favorable_excursion, bars_monitored
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_UPDATE_CLOSE = """\
UPDATE counterfactual_positions SET
    closed_at = ?,
    exit_price = ?,
    exit_reason = ?,
    theoretical_pnl = ?,
    theoretical_r_multiple = ?,
    duration_seconds = ?,
    max_adverse_excursion = ?,
    max_favorable_excursion = ?,
    bars_monitored = ?
WHERE position_id = ?
"""


class CounterfactualStore:
    """SQLite-backed store for counterfactual position persistence.

    Follows the EvaluationEventStore pattern: separate DB file,
    WAL mode, fire-and-forget writes with rate-limited warnings.

    Args:
        db_path: Path to the SQLite database file.
    """

    _WARNING_INTERVAL_SECONDS: float = 60.0

    def __init__(self, db_path: str = "data/counterfactual.db") -> None:
        """Initialize the store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._last_warning_time: float = 0.0

    async def initialize(self) -> None:
        """Create the counterfactual_positions table and indexes if needed."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute(_CREATE_TABLE)
        await self._conn.execute(_CREATE_IDX_OPENED_AT)
        await self._conn.execute(_CREATE_IDX_STRATEGY)
        await self._conn.execute(_CREATE_IDX_STAGE)
        await self._conn.execute(_CREATE_IDX_SYMBOL)
        await self._conn.commit()
        logger.info("CounterfactualStore initialized: %s", self._db_path)

    async def write_open(self, position: CounterfactualPosition) -> None:
        """Persist a newly opened counterfactual position.

        Fire-and-forget: logs WARNING on failure, never raises.

        Args:
            position: The counterfactual position to persist.
        """
        try:
            if self._conn is None:
                logger.warning(
                    "CounterfactualStore not initialized — skipping write_open"
                )
                return
            await self._conn.execute(
                _INSERT_OPEN,
                (
                    position.position_id,
                    position.symbol,
                    position.strategy_id,
                    position.entry_price,
                    position.stop_price,
                    position.target_price,
                    position.time_stop_seconds,
                    str(position.rejection_stage),
                    position.rejection_reason,
                    position.quality_score,
                    position.quality_grade,
                    json.dumps(position.regime_vector_snapshot, default=str)
                    if position.regime_vector_snapshot is not None
                    else None,
                    json.dumps(position.signal_metadata, default=str),
                    position.opened_at.isoformat(),
                    position.max_adverse_excursion,
                    position.max_favorable_excursion,
                    position.bars_monitored,
                ),
            )
            await self._conn.commit()
        except Exception:
            self._warn("Failed to write_open counterfactual position")

    async def write_close(self, position: CounterfactualPosition) -> None:
        """Update a position's exit fields on close.

        Fire-and-forget: logs WARNING on failure, never raises.

        Args:
            position: The closed counterfactual position.
        """
        try:
            if self._conn is None:
                logger.warning(
                    "CounterfactualStore not initialized — skipping write_close"
                )
                return
            await self._conn.execute(
                _UPDATE_CLOSE,
                (
                    position.closed_at.isoformat()
                    if position.closed_at is not None
                    else None,
                    position.exit_price,
                    str(position.exit_reason) if position.exit_reason else None,
                    position.theoretical_pnl,
                    position.theoretical_r_multiple,
                    position.duration_seconds,
                    position.max_adverse_excursion,
                    position.max_favorable_excursion,
                    position.bars_monitored,
                    position.position_id,
                ),
            )
            await self._conn.commit()
        except Exception:
            self._warn("Failed to write_close counterfactual position")

    async def query(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        strategy_id: str | None = None,
        rejection_stage: str | None = None,
        quality_grade: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, object]]:
        """Query counterfactual positions with optional filters.

        Args:
            start_date: ISO date string lower bound on opened_at (inclusive).
            end_date: ISO date string upper bound on opened_at (inclusive).
            strategy_id: Filter by strategy_id.
            rejection_stage: Filter by rejection_stage.
            quality_grade: Filter by quality_grade.
            limit: Maximum rows to return.

        Returns:
            List of position dicts, newest first.
        """
        if self._conn is None:
            return []

        conditions: list[str] = []
        params: list[object] = []

        if start_date is not None:
            conditions.append("opened_at >= ?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("opened_at <= ?")
            params.append(end_date)
        if strategy_id is not None:
            conditions.append("strategy_id = ?")
            params.append(strategy_id)
        if rejection_stage is not None:
            conditions.append("rejection_stage = ?")
            params.append(rejection_stage)
        if quality_grade is not None:
            conditions.append("quality_grade = ?")
            params.append(quality_grade)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        cursor = await self._conn.execute(
            f"SELECT * FROM counterfactual_positions "  # noqa: S608
            f"WHERE {where} ORDER BY opened_at DESC LIMIT ?",
            tuple(params),
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    async def get_closed_positions(
        self,
        start_date: str,
        end_date: str,
        **filters: object,
    ) -> list[dict[str, object]]:
        """Convenience method for FilterAccuracy (Session 4).

        Returns only closed positions (closed_at IS NOT NULL) within
        the date range, with optional additional filters.

        Args:
            start_date: ISO date string lower bound on opened_at.
            end_date: ISO date string upper bound on opened_at.
            **filters: Additional keyword filters (strategy_id,
                rejection_stage, quality_grade).

        Returns:
            List of closed position dicts.
        """
        if self._conn is None:
            return []

        conditions = [
            "opened_at >= ?",
            "opened_at <= ?",
            "closed_at IS NOT NULL",
        ]
        params: list[object] = [start_date, end_date]

        for key, value in filters.items():
            if key in ("strategy_id", "rejection_stage", "quality_grade"):
                conditions.append(f"{key} = ?")
                params.append(value)

        where = " AND ".join(conditions)

        cursor = await self._conn.execute(
            f"SELECT * FROM counterfactual_positions "  # noqa: S608
            f"WHERE {where} ORDER BY opened_at DESC",
            tuple(params),
        )
        rows = await cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]

    async def enforce_retention(self, retention_days: int) -> None:
        """Delete positions older than retention_days.

        Uses opened_at for the retention boundary.

        Args:
            retention_days: Number of days of history to keep.
        """
        if self._conn is None:
            return
        cutoff = (
            datetime.now(_ET) - timedelta(days=retention_days)
        ).isoformat()
        cursor = await self._conn.execute(
            "DELETE FROM counterfactual_positions WHERE opened_at < ?",
            (cutoff,),
        )
        await self._conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(
                "Cleaned up %d old counterfactual positions (before %s)",
                deleted,
                cutoff,
            )

    async def count(self) -> int:
        """Return total record count for health monitoring.

        Returns:
            Number of rows in counterfactual_positions.
        """
        if self._conn is None:
            return 0
        cursor = await self._conn.execute(
            "SELECT COUNT(*) FROM counterfactual_positions"
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0  # type: ignore[index]

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # --- Internal helpers ---

    def _warn(self, message: str) -> None:
        """Log a warning with rate limiting (1 per 60 seconds).

        Args:
            message: Warning message to log.
        """
        now = time.monotonic()
        if now - self._last_warning_time >= self._WARNING_INTERVAL_SECONDS:
            logger.warning(message, exc_info=True)
            self._last_warning_time = now

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict[str, object]:
        """Convert an aiosqlite.Row to a plain dict.

        Args:
            row: Database row.

        Returns:
            Dict with column names as keys.
        """
        return dict(row)  # type: ignore[arg-type]
