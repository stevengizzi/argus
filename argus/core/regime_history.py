"""Regime history persistence for the regime intelligence subsystem.

Stores RegimeVector snapshots in a separate SQLite database
(data/regime_history.db) following the evaluation.db separation pattern
(DEC-345). Writes one row per reclassify_regime() call (~78 rows/day).

Sprint 27.6, Session 6.
"""

from __future__ import annotations

import json
import logging
import time as time_mod
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import aiosqlite

from argus.core.regime import RegimeVector

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS regime_snapshots (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    trading_date TEXT NOT NULL,
    primary_regime TEXT NOT NULL,
    regime_confidence REAL NOT NULL,
    trend_score REAL NOT NULL,
    trend_conviction REAL NOT NULL,
    volatility_level REAL NOT NULL,
    volatility_direction REAL NOT NULL,
    universe_breadth_score REAL,
    breadth_thrust INTEGER,
    avg_correlation REAL,
    correlation_regime TEXT,
    sector_rotation_phase TEXT,
    intraday_character TEXT,
    regime_vector_json TEXT NOT NULL
)
"""

_CREATE_IDX_DATE = """
CREATE INDEX IF NOT EXISTS idx_regime_trading_date
ON regime_snapshots (trading_date)
"""

_CREATE_IDX_REGIME_DATE = """
CREATE INDEX IF NOT EXISTS idx_regime_primary_date
ON regime_snapshots (primary_regime, trading_date)
"""

_RETENTION_DAYS = 7


class RegimeHistoryStore:
    """SQLite persistence for RegimeVector snapshots.

    Separate DB file (data/regime_history.db) to avoid write contention
    with argus.db or evaluation.db. Fire-and-forget writes with rate-limited
    warning on failure.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str = "data/regime_history.db") -> None:
        """Initialize the store.

        Args:
            db_path: Filesystem path for the SQLite database.
        """
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._last_warning_time: float = 0.0

    async def initialize(self) -> None:
        """Create table, indexes, migrate schema, and run retention cleanup.

        Safe to call multiple times (CREATE IF NOT EXISTS + idempotent migration).
        """
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.execute(_CREATE_TABLE_SQL)
        await self._db.execute(_CREATE_IDX_DATE)
        await self._db.execute(_CREATE_IDX_REGIME_DATE)
        await self._db.commit()

        # Schema migration: add vix_close column if missing (Sprint 27.9)
        await self._migrate_add_vix_close()

        # 7-day retention cleanup
        await self._cleanup_old_records()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def record(
        self,
        regime_vector: RegimeVector,
        vix_close: float | None = None,
    ) -> None:
        """Write a RegimeVector snapshot. Fire-and-forget with rate-limited warning.

        Args:
            regime_vector: The RegimeVector to persist.
            vix_close: Optional VIX closing price to store alongside the snapshot.
                Falls back to regime_vector.vix_close if not provided explicitly.
        """
        try:
            if self._db is None:
                return

            from ulid import ULID

            row_id = str(ULID())
            now_et = regime_vector.computed_at.astimezone(_ET)
            timestamp_str = now_et.isoformat()
            trading_date = now_et.strftime("%Y-%m-%d")
            vector_json = json.dumps(regime_vector.to_dict())

            breadth_thrust_int: int | None = None
            if regime_vector.breadth_thrust is not None:
                breadth_thrust_int = 1 if regime_vector.breadth_thrust else 0

            # Use explicit vix_close if provided, else fall back to vector field
            effective_vix_close = vix_close if vix_close is not None else regime_vector.vix_close

            await self._db.execute(
                """
                INSERT INTO regime_snapshots (
                    id, timestamp, trading_date, primary_regime,
                    regime_confidence, trend_score, trend_conviction,
                    volatility_level, volatility_direction,
                    universe_breadth_score, breadth_thrust,
                    avg_correlation, correlation_regime,
                    sector_rotation_phase, intraday_character,
                    regime_vector_json, vix_close
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    timestamp_str,
                    trading_date,
                    regime_vector.primary_regime.value,
                    regime_vector.regime_confidence,
                    regime_vector.trend_score,
                    regime_vector.trend_conviction,
                    regime_vector.volatility_level,
                    regime_vector.volatility_direction,
                    regime_vector.universe_breadth_score,
                    breadth_thrust_int,
                    regime_vector.average_correlation,
                    regime_vector.correlation_regime,
                    regime_vector.sector_rotation_phase,
                    regime_vector.intraday_character,
                    vector_json,
                    effective_vix_close,
                ),
            )
            await self._db.commit()

        except Exception as exc:
            now = time_mod.monotonic()
            if now - self._last_warning_time >= 60.0:
                logger.warning("RegimeHistoryStore write failed: %s", exc)
                self._last_warning_time = now

    async def get_regime_history(self, trading_date: str) -> list[dict]:
        """Get all regime snapshots for a trading date, chronological.

        Args:
            trading_date: Date string in YYYY-MM-DD format.

        Returns:
            List of dicts with all snapshot columns.
        """
        if self._db is None:
            return []

        cursor = await self._db.execute(
            """
            SELECT * FROM regime_snapshots
            WHERE trading_date = ?
            ORDER BY timestamp ASC
            """,
            (trading_date,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_regime_at_time(self, timestamp: datetime) -> dict | None:
        """Get the most recent regime snapshot at or before a timestamp.

        Args:
            timestamp: The point in time to query.

        Returns:
            Dict with snapshot columns, or None if no data.
        """
        if self._db is None:
            return None

        ts_et = timestamp.astimezone(_ET)
        ts_str = ts_et.isoformat()

        cursor = await self._db.execute(
            """
            SELECT * FROM regime_snapshots
            WHERE timestamp <= ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (ts_str,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def get_regime_summary(self, trading_date: str) -> dict:
        """Get summary statistics for a trading date.

        Args:
            trading_date: Date string in YYYY-MM-DD format.

        Returns:
            Dict with dominant_regime, transition_count, avg_confidence.
            Empty dict if no data for the date.
        """
        if self._db is None:
            return {}

        rows = await self.get_regime_history(trading_date)
        if not rows:
            return {}

        # Dominant regime: most frequent primary_regime
        regime_counts: Counter[str] = Counter()
        for row in rows:
            regime_counts[row["primary_regime"]] += 1
        dominant_regime = regime_counts.most_common(1)[0][0]

        # Transition count: number of regime changes
        transitions = 0
        for i in range(1, len(rows)):
            if rows[i]["primary_regime"] != rows[i - 1]["primary_regime"]:
                transitions += 1

        # Average confidence
        confidences = [row["regime_confidence"] for row in rows]
        avg_confidence = sum(confidences) / len(confidences)

        return {
            "dominant_regime": dominant_regime,
            "transition_count": transitions,
            "avg_confidence": round(avg_confidence, 4),
            "snapshot_count": len(rows),
        }

    async def _migrate_add_vix_close(self) -> None:
        """Add vix_close column if it doesn't exist (Sprint 27.9 migration).

        Idempotent: safe to call multiple times. Uses PRAGMA table_info
        to check for the column before running ALTER TABLE.
        """
        if self._db is None:
            return

        cursor = await self._db.execute("PRAGMA table_info(regime_snapshots)")
        columns = await cursor.fetchall()
        column_names = {row[1] for row in columns}

        if "vix_close" not in column_names:
            await self._db.execute(
                "ALTER TABLE regime_snapshots ADD COLUMN vix_close REAL"
            )
            await self._db.commit()
            logger.info("RegimeHistoryStore: migrated schema — added vix_close column")

    async def _cleanup_old_records(self) -> None:
        """Delete records older than 7 days."""
        if self._db is None:
            return

        cutoff_et = datetime.now(_ET)
        from datetime import timedelta

        cutoff_date = (cutoff_et - timedelta(days=_RETENTION_DAYS)).strftime("%Y-%m-%d")

        result = await self._db.execute(
            "DELETE FROM regime_snapshots WHERE trading_date < ?",
            (cutoff_date,),
        )
        await self._db.commit()
        deleted = result.rowcount
        if deleted > 0:
            logger.info(
                "RegimeHistoryStore: cleaned up %d records older than %s",
                deleted,
                cutoff_date,
            )
