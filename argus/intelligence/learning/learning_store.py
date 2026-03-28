"""SQLite persistence for the Learning Loop.

Stores learning reports, config proposals, and config change history
in data/learning.db. Follows DEC-345 pattern: separate DB per subsystem,
WAL mode, fire-and-forget writes with rate-limited warnings.

Sprint 28, Session 3a/4 (parallelized).
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

import aiosqlite

from argus.intelligence.learning.models import (
    ConfigProposal,
    LearningReport,
)

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = "data/learning.db"

_WARN_INTERVAL_SECONDS = 60.0

_CREATE_REPORTS = """\
CREATE TABLE IF NOT EXISTS learning_reports (
    report_id TEXT PRIMARY KEY,
    generated_at TEXT NOT NULL,
    analysis_window_start TEXT NOT NULL,
    analysis_window_end TEXT NOT NULL,
    report_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
)
"""

_CREATE_PROPOSALS = """\
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
)
"""

_CREATE_CHANGE_HISTORY = """\
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
)
"""

_CREATE_IDX_REPORTS_GENERATED = (
    "CREATE INDEX IF NOT EXISTS idx_reports_generated_at "
    "ON learning_reports(generated_at)"
)
_CREATE_IDX_PROPOSALS_STATUS = (
    "CREATE INDEX IF NOT EXISTS idx_proposals_status "
    "ON config_proposals(status)"
)
_CREATE_IDX_PROPOSALS_REPORT = (
    "CREATE INDEX IF NOT EXISTS idx_proposals_report_id "
    "ON config_proposals(report_id)"
)
_CREATE_IDX_CHANGES_APPLIED = (
    "CREATE INDEX IF NOT EXISTS idx_changes_applied_at "
    "ON config_change_history(applied_at)"
)


class LearningStore:
    """SQLite store for learning reports, proposals, and change history.

    Args:
        db_path: Path to the SQLite database file.
    """

    def __init__(self, db_path: str = _DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._last_warn_time: float = 0.0

    async def initialize(self) -> None:
        """Create tables and indexes if they don't exist."""
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute(_CREATE_REPORTS)
            await conn.execute(_CREATE_PROPOSALS)
            await conn.execute(_CREATE_CHANGE_HISTORY)
            await conn.execute(_CREATE_IDX_REPORTS_GENERATED)
            await conn.execute(_CREATE_IDX_PROPOSALS_STATUS)
            await conn.execute(_CREATE_IDX_PROPOSALS_REPORT)
            await conn.execute(_CREATE_IDX_CHANGES_APPLIED)
            await conn.commit()

    # --- Report methods ---

    async def save_report(self, report: LearningReport) -> None:
        """Save a learning report.

        Args:
            report: The LearningReport to persist.
        """
        import json

        report_json = json.dumps(report.to_dict())
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO learning_reports
                    (report_id, generated_at, analysis_window_start,
                     analysis_window_end, report_json, version)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report.report_id,
                        report.generated_at.isoformat(),
                        report.analysis_window_start.isoformat(),
                        report.analysis_window_end.isoformat(),
                        report_json,
                        report.version,
                    ),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn("Failed to save report %s", report.report_id)

    async def get_report(self, report_id: str) -> LearningReport | None:
        """Retrieve a report by ID.

        Args:
            report_id: The report ID to look up.

        Returns:
            LearningReport or None if not found.
        """
        import json

        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT report_json FROM learning_reports WHERE report_id = ?",
                (report_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            raw = dict(row)  # type: ignore[arg-type]
            return LearningReport.from_dict(json.loads(raw["report_json"]))

    async def list_reports(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[LearningReport]:
        """List reports in a date range.

        Args:
            start_date: Optional start filter on generated_at.
            end_date: Optional end filter on generated_at.
            limit: Maximum reports to return.

        Returns:
            List of LearningReport ordered by generated_at descending.
        """
        import json

        conditions: list[str] = []
        params: list[object] = []
        if start_date is not None:
            conditions.append("generated_at >= ?")
            params.append(start_date.isoformat())
        if end_date is not None:
            conditions.append("generated_at <= ?")
            params.append(end_date.isoformat())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT report_json FROM learning_reports
            {where}
            ORDER BY generated_at DESC
            LIMIT ?
        """  # noqa: S608
        params.append(limit)

        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            return [
                LearningReport.from_dict(json.loads(dict(r)["report_json"]))  # type: ignore[arg-type]
                for r in rows
            ]

    async def enforce_retention(self, retention_days: int) -> int:
        """Delete reports older than retention_days.

        Amendment 11: Skip reports referenced by APPLIED/REVERTED proposals.

        Args:
            retention_days: Number of days to retain.

        Returns:
            Number of deleted reports.
        """
        cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.execute(
                    """
                    DELETE FROM learning_reports
                    WHERE generated_at < ?
                      AND report_id NOT IN (
                          SELECT DISTINCT report_id FROM config_proposals
                          WHERE status IN ('APPLIED', 'REVERTED')
                      )
                    """,
                    (cutoff,),
                )
                deleted = cursor.rowcount
                await conn.commit()
                return deleted
        except Exception:
            self._rate_limited_warn("Failed to enforce retention")
            return 0

    # --- Proposal methods ---

    async def save_proposal(self, proposal: ConfigProposal) -> None:
        """Save a config proposal.

        Args:
            proposal: The ConfigProposal to persist.
        """
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO config_proposals
                    (proposal_id, report_id, field_path, current_value,
                     proposed_value, rationale, status, created_at, updated_at,
                     human_notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        proposal.proposal_id,
                        proposal.report_id,
                        proposal.field_path,
                        proposal.current_value,
                        proposal.proposed_value,
                        proposal.rationale,
                        proposal.status,
                        proposal.created_at.isoformat(),
                        proposal.updated_at.isoformat(),
                        proposal.human_notes,
                    ),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn(
                "Failed to save proposal %s", proposal.proposal_id
            )

    async def update_proposal_status(
        self,
        proposal_id: str,
        status: str,
        notes: str | None = None,
    ) -> None:
        """Update a proposal's status and optionally add notes.

        Args:
            proposal_id: ID of the proposal to update.
            status: New status string.
            notes: Optional human notes to set.
        """
        now = datetime.now(UTC).isoformat()
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                if notes is not None:
                    await conn.execute(
                        """
                        UPDATE config_proposals
                        SET status = ?, updated_at = ?, human_notes = ?
                        WHERE proposal_id = ?
                        """,
                        (status, now, notes, proposal_id),
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE config_proposals
                        SET status = ?, updated_at = ?
                        WHERE proposal_id = ?
                        """,
                        (status, now, proposal_id),
                    )
                # Set applied_at/reverted_at timestamps
                if status == "APPLIED":
                    await conn.execute(
                        "UPDATE config_proposals SET applied_at = ? WHERE proposal_id = ?",
                        (now, proposal_id),
                    )
                elif status == "REVERTED":
                    await conn.execute(
                        "UPDATE config_proposals SET reverted_at = ? WHERE proposal_id = ?",
                        (now, proposal_id),
                    )
                await conn.commit()
        except Exception:
            self._rate_limited_warn(
                "Failed to update proposal %s status", proposal_id
            )

    async def list_proposals(
        self,
        status_filter: str | None = None,
        report_id_filter: str | None = None,
    ) -> list[ConfigProposal]:
        """List proposals with optional filters.

        Args:
            status_filter: Optional status to filter by.
            report_id_filter: Optional report_id to filter by.

        Returns:
            List of ConfigProposal ordered by created_at.
        """
        conditions: list[str] = []
        params: list[object] = []
        if status_filter is not None:
            conditions.append("status = ?")
            params.append(status_filter)
        if report_id_filter is not None:
            conditions.append("report_id = ?")
            params.append(report_id_filter)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT * FROM config_proposals
            {where}
            ORDER BY created_at
        """  # noqa: S608

        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            return [self._row_to_proposal(dict(r)) for r in rows]  # type: ignore[arg-type]

    async def get_pending_proposals(self) -> list[ConfigProposal]:
        """Get all PENDING proposals.

        Returns:
            List of ConfigProposal with status PENDING.
        """
        return await self.list_proposals(status_filter="PENDING")

    async def get_approved_proposals(self) -> list[ConfigProposal]:
        """Get all APPROVED proposals ordered by updated_at (approval time).

        Returns:
            List of ConfigProposal with status APPROVED.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM config_proposals
                WHERE status = 'APPROVED'
                ORDER BY updated_at
                """,
            )
            rows = await cursor.fetchall()
            return [self._row_to_proposal(dict(r)) for r in rows]  # type: ignore[arg-type]

    async def supersede_proposals(self, new_report_id: str) -> int:
        """Set all PENDING proposals from prior reports to SUPERSEDED.

        Amendment 6: Only affects PENDING proposals from reports other than
        the new report.

        Args:
            new_report_id: Report ID of the new analysis.

        Returns:
            Number of proposals superseded.
        """
        now = datetime.now(UTC).isoformat()
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                cursor = await conn.execute(
                    """
                    UPDATE config_proposals
                    SET status = 'SUPERSEDED', updated_at = ?
                    WHERE status = 'PENDING' AND report_id != ?
                    """,
                    (now, new_report_id),
                )
                count = cursor.rowcount
                await conn.commit()
                return count
        except Exception:
            self._rate_limited_warn("Failed to supersede proposals")
            return 0

    # --- Change history methods ---

    async def record_change(
        self,
        field_path: str,
        old_value: float,
        new_value: float,
        source: str = "learning_loop",
        proposal_id: str | None = None,
        report_id: str | None = None,
    ) -> None:
        """Record a config change in the history.

        Args:
            field_path: Config field path (e.g., "weights.pattern_strength").
            old_value: Previous value.
            new_value: New value.
            source: Change source ("learning_loop" or "revert").
            proposal_id: Associated proposal ID, if any.
            report_id: Associated report ID, if any.
        """
        now = datetime.now(UTC).isoformat()
        try:
            async with aiosqlite.connect(self._db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO config_change_history
                    (proposal_id, field_path, old_value, new_value, source,
                     applied_at, report_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (proposal_id, field_path, old_value, new_value, source,
                     now, report_id),
                )
                await conn.commit()
        except Exception:
            self._rate_limited_warn("Failed to record config change")

    async def get_change_history(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, object]]:
        """Get config change history in a date range.

        Args:
            start_date: Optional start filter.
            end_date: Optional end filter.

        Returns:
            List of change records as dicts.
        """
        conditions: list[str] = []
        params: list[object] = []
        if start_date is not None:
            conditions.append("applied_at >= ?")
            params.append(start_date.isoformat())
        if end_date is not None:
            conditions.append("applied_at <= ?")
            params.append(end_date.isoformat())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT * FROM config_change_history
            {where}
            ORDER BY applied_at
        """  # noqa: S608

        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(sql, tuple(params))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]  # type: ignore[arg-type]

    async def get_latest_change(self, field_path: str) -> dict[str, object] | None:
        """Get the most recent change for a field path.

        Args:
            field_path: Config field path to look up.

        Returns:
            Most recent change record or None.
        """
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM config_change_history
                WHERE field_path = ?
                ORDER BY applied_at DESC
                LIMIT 1
                """,
                (field_path,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)  # type: ignore[arg-type]

    # --- Helpers ---

    @staticmethod
    def _row_to_proposal(row: dict[str, object]) -> ConfigProposal:
        """Convert a DB row dict to a ConfigProposal.

        Args:
            row: Dict from aiosqlite Row.

        Returns:
            ConfigProposal instance.
        """
        created_str = str(row["created_at"])
        updated_str = str(row["updated_at"])
        return ConfigProposal(
            proposal_id=str(row["proposal_id"]),
            report_id=str(row["report_id"]),
            field_path=str(row["field_path"]),
            current_value=float(row["current_value"]),  # type: ignore[arg-type]
            proposed_value=float(row["proposed_value"]),  # type: ignore[arg-type]
            rationale=str(row["rationale"]),
            status=str(row["status"]),
            created_at=datetime.fromisoformat(created_str),
            updated_at=datetime.fromisoformat(updated_str),
            human_notes=str(row["human_notes"]) if row.get("human_notes") else None,
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
