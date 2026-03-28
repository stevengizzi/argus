"""Unified outcome data reader for the Learning Loop.

Pulls closed trades from argus.db, closed counterfactual positions from
counterfactual.db, and quality history dimension scores from argus.db.
All queries are read-only — no writes to any database.

Sprint 28, Session 1.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import aiosqlite

from argus.intelligence.learning.models import DataQualityPreamble, OutcomeRecord

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_DEFAULT_ARGUS_DB = "data/argus.db"
_DEFAULT_COUNTERFACTUAL_DB = "data/counterfactual.db"


class OutcomeCollector:
    """Collects outcome records from trades + counterfactual databases.

    Read-only collector that produces unified OutcomeRecord lists for
    analysis by the Learning Loop analyzers.

    Args:
        argus_db_path: Path to the argus.db (trades + quality_history).
        counterfactual_db_path: Path to the counterfactual.db.
    """

    def __init__(
        self,
        argus_db_path: str = _DEFAULT_ARGUS_DB,
        counterfactual_db_path: str = _DEFAULT_COUNTERFACTUAL_DB,
    ) -> None:
        self._argus_db_path = argus_db_path
        self._counterfactual_db_path = counterfactual_db_path

    async def collect(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy_id: str | None = None,
    ) -> list[OutcomeRecord]:
        """Collect outcome records from trades and counterfactual sources.

        Args:
            start_date: Start of the analysis window (inclusive).
            end_date: End of the analysis window (inclusive).
            strategy_id: Optional strategy filter.

        Returns:
            List of OutcomeRecord from both sources, sorted by timestamp.
        """
        trade_records = await self._collect_trades(
            start_date, end_date, strategy_id
        )
        counterfactual_records = await self._collect_counterfactual(
            start_date, end_date, strategy_id
        )

        all_records = trade_records + counterfactual_records
        all_records.sort(key=lambda r: r.timestamp)
        return all_records

    async def build_data_quality_preamble(
        self, records: list[OutcomeRecord]
    ) -> DataQualityPreamble:
        """Build a data quality summary from collected records.

        Args:
            records: List of OutcomeRecord to summarize.

        Returns:
            DataQualityPreamble with counts and quality flags.
        """
        if not records:
            return DataQualityPreamble(
                trading_days_count=0,
                total_trades=0,
                total_counterfactual=0,
                effective_sample_size=0,
                known_data_gaps=[],
                earliest_date=None,
                latest_date=None,
            )

        trades = [r for r in records if r.source == "trade"]
        counterfactual = [r for r in records if r.source == "counterfactual"]

        trading_days = {r.timestamp.date() for r in records}

        known_gaps: list[str] = []

        # Flag pre-Sprint-27.95 reconciliation artifacts
        reco_trades = [
            r for r in trades
            if r.rejection_reason is not None
            and "reconciliation" in r.rejection_reason.lower()
        ]
        if reco_trades:
            known_gaps.append(
                f"{len(reco_trades)} reconciliation-sourced trades "
                "may have synthetic close prices"
            )

        # Flag if no counterfactual data available
        if not counterfactual and trades:
            known_gaps.append(
                "No counterfactual data — analysis limited to executed trades"
            )

        # Flag zero-quality-score records (legacy pre-Quality Engine)
        zero_quality = [r for r in records if r.quality_score == 0.0]
        if zero_quality:
            known_gaps.append(
                f"{len(zero_quality)} records with zero quality score "
                "(legacy or pre-Quality Engine)"
            )

        return DataQualityPreamble(
            trading_days_count=len(trading_days),
            total_trades=len(trades),
            total_counterfactual=len(counterfactual),
            effective_sample_size=len(records),
            known_data_gaps=known_gaps,
            earliest_date=min(r.timestamp for r in records),
            latest_date=max(r.timestamp for r in records),
        )

    # --- Internal query methods ---

    async def _collect_trades(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy_id: str | None,
    ) -> list[OutcomeRecord]:
        """Query trades table and join with quality_history for dimensions.

        Args:
            start_date: Start of the analysis window.
            end_date: End of the analysis window.
            strategy_id: Optional strategy filter.

        Returns:
            List of OutcomeRecord with source="trade".
        """
        if not Path(self._argus_db_path).exists():
            return []

        records: list[OutcomeRecord] = []
        try:
            async with aiosqlite.connect(self._argus_db_path) as conn:
                conn.row_factory = aiosqlite.Row

                conditions = [
                    "t.exit_time >= ?",
                    "t.exit_time <= ?",
                ]
                params: list[object] = [
                    start_date.isoformat(),
                    end_date.isoformat(),
                ]

                if strategy_id is not None:
                    conditions.append("t.strategy_id = ?")
                    params.append(strategy_id)

                where = " AND ".join(conditions)

                # Left join quality_history to get per-dimension scores.
                # Match by symbol + strategy_id + closest scored_at to entry_time.
                sql = f"""
                    SELECT
                        t.symbol,
                        t.strategy_id,
                        t.quality_score,
                        t.quality_grade,
                        t.net_pnl,
                        t.r_multiple,
                        t.exit_time,
                        qh.pattern_strength,
                        qh.catalyst_quality,
                        qh.volume_profile,
                        qh.historical_match,
                        qh.regime_alignment
                    FROM trades t
                    LEFT JOIN quality_history qh ON (
                        qh.id = (
                            SELECT qh2.id
                            FROM quality_history qh2
                            WHERE qh2.symbol = t.symbol
                              AND qh2.strategy_id = t.strategy_id
                              AND qh2.scored_at <= t.exit_time
                            ORDER BY qh2.scored_at DESC
                            LIMIT 1
                        )
                    )
                    WHERE {where}
                    ORDER BY t.exit_time
                """  # noqa: S608

                cursor = await conn.execute(sql, tuple(params))
                rows = await cursor.fetchall()

                for row in rows:
                    r = dict(row)  # type: ignore[arg-type]
                    dimension_scores = self._extract_dimension_scores(r)
                    exit_time_str = r["exit_time"]
                    assert isinstance(exit_time_str, str)

                    records.append(OutcomeRecord(
                        symbol=str(r["symbol"]),
                        strategy_id=str(r["strategy_id"]),
                        quality_score=float(r["quality_score"] or 0.0),
                        quality_grade=str(r["quality_grade"] or ""),
                        dimension_scores=dimension_scores,
                        regime_context={},
                        pnl=float(r["net_pnl"]),
                        r_multiple=(
                            float(r["r_multiple"])
                            if r["r_multiple"] is not None
                            else None
                        ),
                        source="trade",
                        timestamp=datetime.fromisoformat(exit_time_str),
                    ))

        except Exception:
            logger.warning(
                "Failed to collect trades from %s",
                self._argus_db_path,
                exc_info=True,
            )

        return records

    async def _collect_counterfactual(
        self,
        start_date: datetime,
        end_date: datetime,
        strategy_id: str | None,
    ) -> list[OutcomeRecord]:
        """Query counterfactual_positions for closed positions.

        Args:
            start_date: Start of the analysis window.
            end_date: End of the analysis window.
            strategy_id: Optional strategy filter.

        Returns:
            List of OutcomeRecord with source="counterfactual".
        """
        if not Path(self._counterfactual_db_path).exists():
            return []

        records: list[OutcomeRecord] = []
        try:
            async with aiosqlite.connect(self._counterfactual_db_path) as conn:
                conn.row_factory = aiosqlite.Row

                conditions = [
                    "opened_at >= ?",
                    "opened_at <= ?",
                    "closed_at IS NOT NULL",
                ]
                params: list[object] = [
                    start_date.isoformat(),
                    end_date.isoformat(),
                ]

                if strategy_id is not None:
                    conditions.append("strategy_id = ?")
                    params.append(strategy_id)

                where = " AND ".join(conditions)

                sql = f"""
                    SELECT
                        symbol,
                        strategy_id,
                        quality_score,
                        quality_grade,
                        theoretical_pnl,
                        theoretical_r_multiple,
                        rejection_stage,
                        rejection_reason,
                        regime_vector_snapshot,
                        closed_at
                    FROM counterfactual_positions
                    WHERE {where}
                    ORDER BY closed_at
                """  # noqa: S608

                cursor = await conn.execute(sql, tuple(params))
                rows = await cursor.fetchall()

                for row in rows:
                    r = dict(row)  # type: ignore[arg-type]
                    regime_context = self._parse_regime_snapshot(
                        r.get("regime_vector_snapshot")
                    )
                    closed_at_str = r["closed_at"]
                    assert isinstance(closed_at_str, str)

                    records.append(OutcomeRecord(
                        symbol=str(r["symbol"]),
                        strategy_id=str(r["strategy_id"]),
                        quality_score=float(r["quality_score"] or 0.0),
                        quality_grade=str(r["quality_grade"] or ""),
                        dimension_scores={},
                        regime_context=regime_context,
                        pnl=float(r["theoretical_pnl"] or 0.0),
                        r_multiple=(
                            float(r["theoretical_r_multiple"])
                            if r.get("theoretical_r_multiple") is not None
                            else None
                        ),
                        source="counterfactual",
                        timestamp=datetime.fromisoformat(closed_at_str),
                        rejection_stage=str(r["rejection_stage"]) if r.get("rejection_stage") else None,
                        rejection_reason=str(r["rejection_reason"]) if r.get("rejection_reason") else None,
                    ))

        except Exception:
            logger.warning(
                "Failed to collect counterfactual from %s",
                self._counterfactual_db_path,
                exc_info=True,
            )

        return records

    # --- Helpers ---

    @staticmethod
    def _extract_dimension_scores(row: dict[str, object]) -> dict[str, float]:
        """Extract per-dimension quality scores from a joined row.

        Returns an empty dict if dimension columns are NULL (no match).

        Args:
            row: Dict from the trades LEFT JOIN quality_history query.

        Returns:
            Dict of dimension name → score value.
        """
        dimensions = [
            "pattern_strength",
            "catalyst_quality",
            "volume_profile",
            "historical_match",
            "regime_alignment",
        ]
        scores: dict[str, float] = {}
        for dim in dimensions:
            val = row.get(dim)
            if val is not None:
                scores[dim] = float(val)
        return scores

    @staticmethod
    def _parse_regime_snapshot(raw: object) -> dict[str, object]:
        """Parse a regime_vector_snapshot JSON string.

        Args:
            raw: JSON string or None.

        Returns:
            Parsed dict or empty dict.
        """
        if raw is None:
            return {}
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(raw, dict):
            return raw
        return {}
