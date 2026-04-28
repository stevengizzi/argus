"""SQLite persistence for the experiment registry.

Stores variants, experiment records, and promotion events in
data/experiments.db. Follows the DEC-345 pattern: separate DB per
subsystem, WAL mode, fire-and-forget writes with rate-limited warnings.

Sprint 32, Session 4.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta

import aiosqlite

from argus.data.migrations import apply_migrations
from argus.data.migrations.experiments import MIGRATIONS, SCHEMA_NAME
from argus.intelligence.experiments.models import (
    ExperimentRecord,
    ExperimentStatus,
    PromotionEvent,
    VariantDefinition,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/experiments.db"
_WARN_INTERVAL_SECONDS = 60.0

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

class ExperimentStore:
    """SQLite-backed store for variants, experiments, and promotion events.

    Follows the DEC-345 pattern: WAL mode, per-operation connections,
    fire-and-forget writes with rate-limited WARNING logs.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._last_warn_time: float = 0.0

    # ---------------------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create tables and indexes if they do not exist.

        Enables WAL journal mode for concurrent read access.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            # Sprint 31.91 Impromptu C: schema managed by the migration
            # framework. Migration v1 includes the exit_overrides column on
            # variants (Sprint 32.5 S1) previously added via in-place ALTER.
            # The legacy ALTER fallback below covers DBs that pre-date the
            # framework adoption AND have variants table without the column.
            await apply_migrations(
                conn, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
            )

            # Legacy compat: pre-Impromptu-C DBs whose variants table
            # pre-dates Sprint 32.5 S1. New DBs already include exit_overrides.
            try:
                await conn.execute(
                    "ALTER TABLE variants ADD COLUMN exit_overrides TEXT"
                )
                await conn.commit()
            except aiosqlite.OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

        logger.info("ExperimentStore initialized: %s", self._db_path)

    async def close(self) -> None:
        """No-op — this store uses per-operation connections."""

    # ---------------------------------------------------------------------------
    # Experiment methods
    # ---------------------------------------------------------------------------

    async def save_experiment(self, record: ExperimentRecord) -> None:
        """Persist an experiment record (insert or replace).

        Fire-and-forget: logs WARNING on failure, never raises.

        Args:
            record: The ExperimentRecord to persist.
        """
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO experiments
                    (experiment_id, pattern_name, parameter_fingerprint,
                     parameters_json, status, backtest_result_json,
                     shadow_trades, shadow_expectancy, is_baseline,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.experiment_id,
                        record.pattern_name,
                        record.parameter_fingerprint,
                        json.dumps(record.parameters),
                        str(record.status),
                        json.dumps(record.backtest_result, default=str)
                        if record.backtest_result is not None
                        else None,
                        record.shadow_trades,
                        record.shadow_expectancy,
                        1 if record.is_baseline else 0,
                        record.created_at.isoformat(),
                        record.updated_at.isoformat(),
                    ),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn(
                "Failed to save experiment %s", record.experiment_id
            )

    async def get_experiment(self, experiment_id: str) -> ExperimentRecord | None:
        """Retrieve a single experiment by ID.

        Args:
            experiment_id: ULID to look up.

        Returns:
            ExperimentRecord or None if not found.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM experiments WHERE experiment_id = ?",
                (experiment_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_experiment(dict(row))  # type: ignore[arg-type]

    async def list_experiments(
        self,
        pattern_name: str | None = None,
        limit: int = 50,
    ) -> list[ExperimentRecord]:
        """List experiments, optionally filtered by pattern name.

        Args:
            pattern_name: Optional pattern name filter.
            limit: Maximum records to return.

        Returns:
            List of ExperimentRecord ordered by created_at descending.
        """
        conditions: list[str] = []
        params: list[object] = []
        if pattern_name is not None:
            conditions.append("pattern_name = ?")
            params.append(pattern_name)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT * FROM experiments
            {where}
            ORDER BY created_at DESC
            LIMIT ?
        """  # noqa: S608
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            return [self._row_to_experiment(dict(r)) for r in rows]  # type: ignore[arg-type]

    async def get_baseline(self, pattern_name: str) -> ExperimentRecord | None:
        """Return the baseline experiment for a pattern, if one exists.

        Args:
            pattern_name: Pattern name to look up.

        Returns:
            ExperimentRecord marked is_baseline=True, or None.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM experiments
                WHERE pattern_name = ? AND is_baseline = 1
                LIMIT 1
                """,
                (pattern_name,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_experiment(dict(row))  # type: ignore[arg-type]

    async def get_by_fingerprint(
        self, pattern_name: str, fingerprint: str
    ) -> ExperimentRecord | None:
        """Retrieve an experiment by pattern name and parameter fingerprint.

        Uses the composite index on (pattern_name, parameter_fingerprint) for
        an O(log n) lookup instead of a full table scan.

        Args:
            pattern_name: Pattern name to scope the search.
            fingerprint: 16-character hex fingerprint to match.

        Returns:
            ExperimentRecord or None if not found.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM experiments
                WHERE pattern_name = ? AND parameter_fingerprint = ?
                LIMIT 1
                """,
                (pattern_name, fingerprint),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_experiment(dict(row))  # type: ignore[arg-type]

    async def set_baseline(self, experiment_id: str) -> None:
        """Mark an experiment as the baseline for its pattern.

        Atomically unmarks any previous baseline for the same pattern
        before marking the new one.

        Fire-and-forget: logs WARNING on failure, never raises.

        Args:
            experiment_id: ULID of the experiment to mark as baseline.
        """
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                # Fetch the pattern_name for this experiment
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(
                    "SELECT pattern_name FROM experiments WHERE experiment_id = ?",
                    (experiment_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    logger.warning(
                        "set_baseline: experiment %s not found", experiment_id
                    )
                    return
                pattern_name = dict(row)["pattern_name"]  # type: ignore[arg-type]

                # Unmark all previous baselines for this pattern
                await conn.execute(
                    """
                    UPDATE experiments
                    SET is_baseline = 0
                    WHERE pattern_name = ? AND is_baseline = 1
                    """,
                    (pattern_name,),
                )
                # Mark the new baseline
                now = datetime.now(UTC).isoformat()
                await conn.execute(
                    """
                    UPDATE experiments
                    SET is_baseline = 1, updated_at = ?
                    WHERE experiment_id = ?
                    """,
                    (now, experiment_id),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn(
                "Failed to set baseline for experiment %s", experiment_id
            )

    # ---------------------------------------------------------------------------
    # Variant methods
    # ---------------------------------------------------------------------------

    async def save_variant(self, variant: VariantDefinition) -> None:
        """Persist a variant definition (insert or replace).

        Fire-and-forget: logs WARNING on failure, never raises.

        Args:
            variant: The VariantDefinition to persist.
        """
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO variants
                    (variant_id, base_pattern, parameter_fingerprint,
                     parameters_json, mode, source, created_at, exit_overrides)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        variant.variant_id,
                        variant.base_pattern,
                        variant.parameter_fingerprint,
                        json.dumps(variant.parameters),
                        variant.mode,
                        variant.source,
                        variant.created_at.isoformat(),
                        json.dumps(variant.exit_overrides)
                        if variant.exit_overrides is not None
                        else None,
                    ),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn(
                "Failed to save variant %s", variant.variant_id
            )

    async def list_variants(
        self, pattern_name: str | None = None
    ) -> list[VariantDefinition]:
        """List variants, optionally filtered by base_pattern.

        Args:
            pattern_name: Optional base_pattern filter.

        Returns:
            List of VariantDefinition ordered by created_at descending.
        """
        conditions: list[str] = []
        params: list[object] = []
        if pattern_name is not None:
            conditions.append("base_pattern = ?")
            params.append(pattern_name)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT * FROM variants
            {where}
            ORDER BY created_at DESC
        """  # noqa: S608

        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            return [self._row_to_variant(dict(r)) for r in rows]  # type: ignore[arg-type]

    async def get_variant(self, variant_id: str) -> VariantDefinition | None:
        """Retrieve a single variant by ID.

        Args:
            variant_id: Variant ID to look up.

        Returns:
            VariantDefinition or None if not found.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM variants WHERE variant_id = ?",
                (variant_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._row_to_variant(dict(row))  # type: ignore[arg-type]

    async def update_variant_mode(self, variant_id: str, new_mode: str) -> None:
        """Update the mode of an existing variant.

        Fire-and-forget: logs WARNING on failure, never raises.

        Args:
            variant_id: ID of the variant to update.
            new_mode: New mode string ("live" or "shadow").
        """
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                await conn.execute(
                    "UPDATE variants SET mode = ? WHERE variant_id = ?",
                    (new_mode, variant_id),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn(
                "Failed to update mode for variant %s", variant_id
            )

    # ---------------------------------------------------------------------------
    # Promotion event methods
    # ---------------------------------------------------------------------------

    async def save_promotion_event(self, event: PromotionEvent) -> None:
        """Persist a promotion event (insert or replace).

        Fire-and-forget: logs WARNING on failure, never raises.

        Args:
            event: The PromotionEvent to persist.
        """
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO promotion_events
                    (event_id, variant_id, action, previous_mode, new_mode,
                     reason, comparison_verdict_json, shadow_trades,
                     shadow_expectancy, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.variant_id,
                        event.action,
                        event.previous_mode,
                        event.new_mode,
                        event.reason,
                        event.comparison_verdict,
                        event.shadow_trades,
                        event.shadow_expectancy,
                        event.timestamp.isoformat(),
                    ),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn(
                "Failed to save promotion event %s", event.event_id
            )

    async def list_promotion_events(
        self,
        variant_id: str | None = None,
        limit: int = 50,
    ) -> list[PromotionEvent]:
        """List promotion events, optionally filtered by variant_id.

        Args:
            variant_id: Optional variant ID filter.
            limit: Maximum records to return.

        Returns:
            List of PromotionEvent ordered by timestamp descending.
        """
        conditions: list[str] = []
        params: list[object] = []
        if variant_id is not None:
            conditions.append("variant_id = ?")
            params.append(variant_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT * FROM promotion_events
            {where}
            ORDER BY timestamp DESC
            LIMIT ?
        """  # noqa: S608
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            return [self._row_to_promotion_event(dict(r)) for r in rows]  # type: ignore[arg-type]

    async def query_variants_with_metrics(self) -> list[dict[str, object]]:
        """Return all variant definitions joined with available experiment metrics.

        Performs a LEFT JOIN between variants and experiments on
        (base_pattern, parameter_fingerprint) to attach status, shadow trade
        count, and key backtest metrics (win_rate, expectancy, sharpe) where
        a matching experiment record exists.

        Returns:
            List of variant dicts ordered by created_at DESC. Each dict
            contains: variant_id, pattern_name, detection_params,
            exit_overrides, config_fingerprint, mode, status,
            trade_count, shadow_trade_count, win_rate, expectancy, sharpe.
            Metrics fields are None when no experiment record matches.
        """
        import json as _json

        sql = """
            SELECT
                v.variant_id,
                v.base_pattern AS pattern_name,
                v.parameters_json AS detection_params_json,
                v.exit_overrides AS exit_overrides_json,
                v.parameter_fingerprint AS config_fingerprint,
                v.mode,
                v.source,
                v.created_at,
                e.status,
                e.shadow_trades,
                e.shadow_expectancy,
                e.backtest_result_json
            FROM variants v
            LEFT JOIN experiments e
                ON v.base_pattern = e.pattern_name
                AND v.parameter_fingerprint = e.parameter_fingerprint
            ORDER BY v.created_at DESC
        """  # noqa: S608
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql)
            rows = await cursor.fetchall()

        results: list[dict[str, object]] = []
        for row in rows:
            raw = dict(row)  # type: ignore[arg-type]
            backtest_raw = raw.get("backtest_result_json")
            backtest: dict[str, object] | None = (
                _json.loads(str(backtest_raw)) if backtest_raw is not None else None
            )
            results.append(
                {
                    "variant_id": raw["variant_id"],
                    "pattern_name": raw["pattern_name"],
                    "detection_params": _json.loads(str(raw["detection_params_json"])),
                    "exit_overrides": (
                        _json.loads(str(raw["exit_overrides_json"]))
                        if raw.get("exit_overrides_json") is not None
                        else None
                    ),
                    "config_fingerprint": raw["config_fingerprint"],
                    "mode": raw["mode"],
                    "status": raw.get("status"),
                    "trade_count": 0,
                    "shadow_trade_count": int(raw["shadow_trades"])  # type: ignore[arg-type]
                    if raw.get("shadow_trades") is not None
                    else 0,
                    "win_rate": float(backtest["win_rate"])  # type: ignore[index]
                    if backtest is not None and "win_rate" in backtest
                    else None,
                    "expectancy": float(backtest["expectancy_per_trade"])  # type: ignore[index]
                    if backtest is not None and "expectancy_per_trade" in backtest
                    else None,
                    "sharpe": float(backtest["sharpe_ratio"])  # type: ignore[index]
                    if backtest is not None and "sharpe_ratio" in backtest
                    else None,
                }
            )
        return results

    async def query_promotion_events(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, object]]:
        """Query promotion/demotion events with pagination.

        JOINs promotion_events with variants to include pattern_name.
        Returns events ordered by timestamp DESC.

        Args:
            limit: Maximum rows to return (default 100).
            offset: Number of rows to skip for pagination (default 0).

        Returns:
            List of event dicts, each with: event_id, variant_id,
            pattern_name, event_type, from_mode, to_mode, timestamp,
            trigger_reason, metrics_snapshot.
        """
        sql = """
            SELECT
                pe.event_id,
                pe.variant_id,
                v.base_pattern AS pattern_name,
                pe.action AS event_type,
                pe.previous_mode AS from_mode,
                pe.new_mode AS to_mode,
                pe.timestamp,
                pe.reason AS trigger_reason,
                pe.comparison_verdict_json AS metrics_snapshot,
                pe.shadow_trades,
                pe.shadow_expectancy
            FROM promotion_events pe
            LEFT JOIN variants v ON pe.variant_id = v.variant_id
            ORDER BY pe.timestamp DESC
            LIMIT ? OFFSET ?
        """  # noqa: S608
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, (limit, offset))
            rows = await cursor.fetchall()

        return [dict(row) for row in rows]  # type: ignore[arg-type]

    async def count_promotion_events(self) -> int:
        """Return total number of promotion events for pagination.

        Returns:
            Total row count in promotion_events table.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM promotion_events")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0  # type: ignore[index]

    # ---------------------------------------------------------------------------
    # Maintenance
    # ---------------------------------------------------------------------------

    async def enforce_retention(self, max_age_days: int = 90) -> int:
        """Delete records older than max_age_days across all three tables.

        Args:
            max_age_days: Number of days to retain records.

        Returns:
            Total number of records deleted.
        """
        cutoff = (
            datetime.now(UTC) - timedelta(days=max_age_days)
        ).isoformat()
        total_deleted = 0
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.execute(
                    "DELETE FROM experiments WHERE created_at < ?",
                    (cutoff,),
                )
                total_deleted += cursor.rowcount

                cursor = await conn.execute(
                    "DELETE FROM variants WHERE created_at < ?",
                    (cutoff,),
                )
                total_deleted += cursor.rowcount

                cursor = await conn.execute(
                    "DELETE FROM promotion_events WHERE timestamp < ?",
                    (cutoff,),
                )
                total_deleted += cursor.rowcount

                await conn.commit()
        except Exception:
            self._rate_limited_warn("Failed to enforce experiment retention")
            return 0
        if total_deleted > 0:
            logger.info(
                "ExperimentStore retention: deleted %d records older than %s",
                total_deleted,
                cutoff,
            )
        return total_deleted

    # ---------------------------------------------------------------------------
    # Row helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _row_to_experiment(row: dict[str, object]) -> ExperimentRecord:
        """Convert a DB row dict to an ExperimentRecord.

        Args:
            row: Dict from aiosqlite Row.

        Returns:
            ExperimentRecord instance.
        """
        backtest_raw = row.get("backtest_result_json")
        backtest_result: dict[str, object] | None = (
            json.loads(str(backtest_raw)) if backtest_raw is not None else None
        )
        return ExperimentRecord(
            experiment_id=str(row["experiment_id"]),
            pattern_name=str(row["pattern_name"]),
            parameter_fingerprint=str(row["parameter_fingerprint"]),
            parameters=json.loads(str(row["parameters_json"])),
            status=ExperimentStatus(str(row["status"])),
            backtest_result=backtest_result,
            shadow_trades=int(row["shadow_trades"]),  # type: ignore[arg-type]
            shadow_expectancy=float(row["shadow_expectancy"])  # type: ignore[arg-type]
            if row.get("shadow_expectancy") is not None
            else None,
            is_baseline=bool(int(row["is_baseline"])),  # type: ignore[arg-type]
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    @staticmethod
    def _row_to_variant(row: dict[str, object]) -> VariantDefinition:
        """Convert a DB row dict to a VariantDefinition.

        Args:
            row: Dict from aiosqlite Row.

        Returns:
            VariantDefinition instance.
        """
        exit_overrides_raw = row.get("exit_overrides")
        exit_overrides: dict[str, object] | None = (
            json.loads(str(exit_overrides_raw))
            if exit_overrides_raw is not None
            else None
        )
        return VariantDefinition(
            variant_id=str(row["variant_id"]),
            base_pattern=str(row["base_pattern"]),
            parameter_fingerprint=str(row["parameter_fingerprint"]),
            parameters=json.loads(str(row["parameters_json"])),
            mode=str(row["mode"]),
            source=str(row["source"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            exit_overrides=exit_overrides,
        )

    @staticmethod
    def _row_to_promotion_event(row: dict[str, object]) -> PromotionEvent:
        """Convert a DB row dict to a PromotionEvent.

        Args:
            row: Dict from aiosqlite Row.

        Returns:
            PromotionEvent instance.
        """
        verdict_raw = row.get("comparison_verdict_json")
        return PromotionEvent(
            event_id=str(row["event_id"]),
            variant_id=str(row["variant_id"]),
            action=str(row["action"]),
            previous_mode=str(row["previous_mode"]),
            new_mode=str(row["new_mode"]),
            reason=str(row["reason"]),
            comparison_verdict=str(verdict_raw) if verdict_raw is not None else None,
            shadow_trades=int(row["shadow_trades"]),  # type: ignore[arg-type]
            shadow_expectancy=float(row["shadow_expectancy"])  # type: ignore[arg-type]
            if row.get("shadow_expectancy") is not None
            else None,
            timestamp=datetime.fromisoformat(str(row["timestamp"])),
        )

    def _rate_limited_warn(self, msg: str, *args: object) -> None:
        """Log a warning at most once per _WARN_INTERVAL_SECONDS.

        Args:
            msg: Log message format string.
            *args: Format arguments.
        """
        now = time.monotonic()
        if now - self._last_warn_time >= _WARN_INTERVAL_SECONDS:
            logger.warning(msg, *args, exc_info=True)
            self._last_warn_time = now
