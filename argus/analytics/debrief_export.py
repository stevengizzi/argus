"""Automated debrief data export for post-session analysis.

Queries all three databases (argus.db, evaluation.db, catalyst.db) and
the broker to produce a single JSON file containing everything the
market session debrief protocol needs.

Sprint 25.7 — DEF-079.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiosqlite

if TYPE_CHECKING:
    from argus.core.orchestrator import Orchestrator
    from argus.db.manager import DatabaseManager
    from argus.execution.broker import Broker
    from argus.strategies.telemetry_store import EvaluationEventStore

logger = logging.getLogger(__name__)


async def export_debrief_data(
    session_date: str,
    db: DatabaseManager,
    eval_store: EvaluationEventStore | None,
    catalyst_db_path: str | None,
    broker: Broker | None,
    orchestrator: Orchestrator | None,
    output_dir: str = "logs",
) -> str | None:
    """Export debrief data to a JSON file for post-session analysis.

    Each section is independently try/excepted so that one failure
    does not prevent other sections from being exported.

    Args:
        session_date: Trading date in "YYYY-MM-DD" format (ET).
        db: Open DatabaseManager for argus.db.
        eval_store: EvaluationEventStore for evaluation.db (may be None).
        catalyst_db_path: Path to catalyst.db (separate connection).
        broker: Broker instance for account state.
        orchestrator: Orchestrator for regime/allocation state.
        output_dir: Directory to write the output file.

    Returns:
        File path on success, None on failure.
    """
    try:
        result: dict[str, Any] = {
            "session_date": session_date,
            "exported_at": datetime.now(UTC).isoformat(),
        }

        # --- Orchestrator Decisions ---
        result["orchestrator_decisions"] = await _export_orchestrator_decisions(
            db, session_date
        )

        # --- Evaluation Summary ---
        result["evaluation_summary"] = await _export_evaluation_summary(
            eval_store, session_date
        )

        # --- Quality History ---
        result["quality_history"] = await _export_quality_history(db, session_date)

        # --- Trades ---
        result["trades"] = await _export_trades(db, session_date)

        # --- Catalyst Summary ---
        result["catalyst_summary"] = await _export_catalyst_summary(
            catalyst_db_path, session_date
        )

        # --- Account State ---
        result["account_state"] = await _export_account_state(broker)

        # --- Regime ---
        result["regime"] = _export_regime(orchestrator)

        # Write to file
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        file_path = output_path / f"debrief_{session_date}.json"

        file_path.write_text(
            json.dumps(result, default=str, indent=2),
            encoding="utf-8",
        )

        logger.info("Debrief data exported to %s", file_path)
        return str(file_path)

    except Exception as e:
        logger.warning("Debrief export failed: %s", e)
        return None


async def _export_orchestrator_decisions(
    db: DatabaseManager, session_date: str
) -> list[dict[str, Any]] | dict[str, str]:
    """Query orchestrator_decisions table for today."""
    try:
        rows = await db.fetch_all(
            "SELECT decision_type, strategy_id, details, rationale, created_at "
            "FROM orchestrator_decisions WHERE date = ?",
            (session_date,),
        )
        return [
            {
                "decision_type": r[0],
                "strategy_id": r[1],
                "details": r[2],
                "rationale": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Debrief export: orchestrator_decisions failed: %s", e)
        return {"error": str(e)}


async def _export_evaluation_summary(
    eval_store: EvaluationEventStore | None, session_date: str
) -> dict[str, Any]:
    """Query evaluation_events table in evaluation.db."""
    if eval_store is None:
        return {"error": "eval_store not available"}

    try:
        summary: dict[str, Any] = {}

        # Total count
        rows = await eval_store.execute_query(
            "SELECT COUNT(*) FROM evaluation_events WHERE trading_date = ?",
            (session_date,),
        )
        summary["total_events"] = rows[0][0] if rows else 0

        # Per-strategy counts
        rows = await eval_store.execute_query(
            "SELECT strategy_id, COUNT(*), COUNT(DISTINCT symbol) "
            "FROM evaluation_events WHERE trading_date = ? "
            "GROUP BY strategy_id",
            (session_date,),
        )
        summary["by_strategy"] = {
            r[0]: {"count": r[1], "distinct_symbols": r[2]} for r in rows
        }

        # Event type × result distribution
        rows = await eval_store.execute_query(
            "SELECT event_type, result, COUNT(*) "
            "FROM evaluation_events WHERE trading_date = ? "
            "GROUP BY event_type, result ORDER BY COUNT(*) DESC LIMIT 20",
            (session_date,),
        )
        summary["by_event_type_result"] = [
            {"event_type": r[0], "result": r[1], "count": r[2]} for r in rows
        ]

        # Last 50 ENTRY_EVALUATION events
        rows = await eval_store.execute_query(
            "SELECT symbol, strategy_id, result, reason, metadata_json "
            "FROM evaluation_events WHERE trading_date = ? "
            "AND event_type = 'ENTRY_EVALUATION' "
            "ORDER BY rowid DESC LIMIT 50",
            (session_date,),
        )
        summary["entry_evaluations"] = [
            {
                "symbol": r[0],
                "strategy_id": r[1],
                "result": r[2],
                "reason": r[3],
                "metadata_json": r[4],
            }
            for r in rows
        ]

        return summary

    except Exception as e:
        logger.warning("Debrief export: evaluation_summary failed: %s", e)
        return {"error": str(e)}


async def _export_quality_history(
    db: DatabaseManager, session_date: str
) -> list[dict[str, Any]] | dict[str, str]:
    """Query quality_history table for today."""
    try:
        rows = await db.fetch_all(
            "SELECT symbol, strategy_id, composite_score, grade, "
            "calculated_shares, scored_at "
            "FROM quality_history WHERE created_at >= ?",
            (session_date,),
        )
        return [
            {
                "symbol": r[0],
                "strategy_id": r[1],
                "composite_score": r[2],
                "grade": r[3],
                "calculated_shares": r[4],
                "scored_at": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Debrief export: quality_history failed: %s", e)
        return {"error": str(e)}


async def _export_trades(
    db: DatabaseManager, session_date: str
) -> list[dict[str, Any]] | dict[str, str]:
    """Query trades table for today using dynamic column discovery."""
    try:
        # Get column names dynamically
        col_rows = await db.fetch_all("PRAGMA table_info(trades)")
        col_names = [r[1] for r in col_rows]

        # Fetch today's trades
        rows = await db.fetch_all(
            "SELECT * FROM trades WHERE date(created_at) = ?",
            (session_date,),
        )
        return [dict(zip(col_names, r)) for r in rows]
    except Exception as e:
        logger.warning("Debrief export: trades failed: %s", e)
        return {"error": str(e)}


async def _export_catalyst_summary(
    catalyst_db_path: str | None, session_date: str
) -> dict[str, Any]:
    """Query catalyst_events from catalyst.db (separate connection)."""
    if catalyst_db_path is None:
        return {"error": "catalyst_db_path not provided"}

    try:
        db_path = Path(catalyst_db_path)
        if not db_path.exists():
            return {"error": f"catalyst.db not found at {catalyst_db_path}"}

        async with aiosqlite.connect(str(db_path)) as conn:
            # Total events today
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM catalyst_events "
                "WHERE date(created_at) = ?",
                (session_date,),
            )
            row = await cursor.fetchone()
            total = row[0] if row else 0

            # By source
            cursor = await conn.execute(
                "SELECT source, COUNT(*) FROM catalyst_events "
                "WHERE date(created_at) = ? GROUP BY source",
                (session_date,),
            )
            by_source = {r[0]: r[1] for r in await cursor.fetchall()}

            # Sample events (first 20)
            cursor = await conn.execute(
                "SELECT symbol, headline, source, created_at "
                "FROM catalyst_events WHERE date(created_at) = ? "
                "ORDER BY created_at LIMIT 20",
                (session_date,),
            )
            sample_events = [
                {
                    "symbol": r[0],
                    "headline": r[1],
                    "source": r[2],
                    "created_at": r[3],
                }
                for r in await cursor.fetchall()
            ]

            return {
                "total_events_today": total,
                "by_source": by_source,
                "sample_events": sample_events,
            }

    except Exception as e:
        logger.warning("Debrief export: catalyst_summary failed: %s", e)
        return {"error": str(e)}


async def _export_account_state(
    broker: Broker | None,
) -> dict[str, Any]:
    """Fetch account state from broker."""
    if broker is None:
        return {"error": "broker not available"}

    try:
        account = await broker.get_account()
        positions = await broker.get_positions()

        account_data: dict[str, Any] = {}
        if account is not None:
            account_data["equity"] = account.equity
            account_data["buying_power"] = account.buying_power
            account_data["cash"] = account.cash
        else:
            account_data["error"] = "get_account() returned None"

        position_list = []
        if positions:
            for pos in positions:
                position_list.append({
                    "symbol": pos.symbol,
                    "shares": pos.shares,
                    "entry_price": pos.entry_price,
                    "current_price": pos.current_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                })
        account_data["positions"] = position_list

        return account_data

    except Exception as e:
        logger.warning("Debrief export: account_state failed: %s", e)
        return {"error": str(e)}


def _export_regime(orchestrator: Orchestrator | None) -> dict[str, Any]:
    """Read regime and allocation state from Orchestrator."""
    if orchestrator is None:
        return {"error": "orchestrator not available"}

    try:
        regime_data: dict[str, Any] = {
            "current": orchestrator.current_regime.value,
            "spy_data_available": orchestrator.spy_data_available
        }

        allocations = orchestrator.current_allocations
        alloc_data: dict[str, Any] = {}
        for sid, alloc in allocations.items():
            alloc_data[sid] = {
                "eligible": alloc.eligible,
                "allocation_dollars": alloc.allocation_dollars,
                "allocation_pct": alloc.allocation_pct,
                "throttle_action": alloc.throttle_action.value,
            }
        regime_data["allocations"] = alloc_data

        return regime_data

    except Exception as e:
        logger.warning("Debrief export: regime failed: %s", e)
        return {"error": str(e)}
