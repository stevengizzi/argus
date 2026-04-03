"""Automated debrief data export for post-session analysis.

Queries all three databases (argus.db, evaluation.db, catalyst.db) and
the broker to produce a single JSON file containing everything the
market session debrief protocol needs.

Sprint 25.7 — DEF-079.
Sprint 32.9+ — Added counterfactual_summary, experiment_summary, safety_summary,
quality_distribution sections (Phase 4b/4c protocol additions).
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
    counterfactual_db_path: str | None = None,
    experiment_db_path: str | None = None,
    order_manager: object | None = None,
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
        counterfactual_db_path: Path to counterfactual.db (Sprint 32.9+).
        experiment_db_path: Path to experiments.db (Sprint 32.9+).
        order_manager: OrderManager instance for margin circuit state (Sprint 32.9+).

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

        # --- Quality Distribution (Sprint 32.9+) ---
        result["quality_distribution"] = await _export_quality_distribution(
            db, session_date
        )

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

        # --- Counterfactual Summary (Sprint 32.9+) ---
        result["counterfactual_summary"] = await _export_counterfactual_summary(
            counterfactual_db_path, session_date
        )

        # --- Experiment Summary (Sprint 32.9+) ---
        result["experiment_summary"] = await _export_experiment_summary(
            experiment_db_path, session_date
        )

        # --- Safety Summary (Sprint 32.9+) ---
        result["safety_summary"] = _export_safety_summary(order_manager, orchestrator)

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


async def _export_quality_distribution(
    db: DatabaseManager, session_date: str
) -> dict[str, Any]:
    """Query quality_history for grade distribution and dimension averages."""
    try:
        summary: dict[str, Any] = {}

        # Grade counts
        rows = await db.fetch_all(
            "SELECT grade, COUNT(*) FROM quality_history "
            "WHERE created_at >= ? GROUP BY grade ORDER BY grade",
            (session_date,),
        )
        summary["grade_counts"] = {r[0]: r[1] for r in rows}

        # Grade-outcome correlation (only for trades that completed)
        rows = await db.fetch_all(
            "SELECT grade, COUNT(*) as signals, "
            "SUM(CASE WHEN outcome_r_multiple > 0 THEN 1 ELSE 0 END) as wins, "
            "AVG(outcome_r_multiple) as avg_r "
            "FROM quality_history "
            "WHERE created_at >= ? AND outcome_trade_id IS NOT NULL "
            "GROUP BY grade ORDER BY grade",
            (session_date,),
        )
        summary["grade_outcomes"] = {
            r[0]: {
                "trades": r[1],
                "win_rate": round(r[2] / r[1], 3) if r[1] > 0 else 0.0,
                "avg_r": round(r[3], 3) if r[3] is not None else None,
            }
            for r in rows
        }

        # Dimension averages
        rows = await db.fetch_all(
            "SELECT AVG(pattern_strength), AVG(catalyst_quality), "
            "AVG(volume_profile), AVG(historical_match), AVG(regime_alignment), "
            "AVG(composite_score) "
            "FROM quality_history WHERE created_at >= ?",
            (session_date,),
        )
        if rows and rows[0][0] is not None:
            r = rows[0]
            summary["dimension_averages"] = {
                "pattern_strength": round(r[0], 1) if r[0] is not None else None,
                "catalyst_quality": round(r[1], 1) if r[1] is not None else None,
                "volume_profile": round(r[2], 1) if r[2] is not None else None,
                "historical_match": round(r[3], 1) if r[3] is not None else None,
                "regime_alignment": round(r[4], 1) if r[4] is not None else None,
                "composite_score": round(r[5], 1) if r[5] is not None else None,
            }
        else:
            summary["dimension_averages"] = None

        return summary

    except Exception as e:
        logger.warning("Debrief export: quality_distribution failed: %s", e)
        return {"error": str(e)}


async def _export_counterfactual_summary(
    counterfactual_db_path: str | None, session_date: str
) -> dict[str, Any]:
    """Query counterfactual.db for shadow/rejected position performance."""
    if counterfactual_db_path is None:
        return {"error": "counterfactual_db_path not provided"}

    try:
        db_path = Path(counterfactual_db_path)
        if not db_path.exists():
            return {"error": f"counterfactual.db not found at {counterfactual_db_path}"}

        async with aiosqlite.connect(str(db_path)) as conn:
            conn.row_factory = aiosqlite.Row

            # Total volume
            cursor = await conn.execute(
                "SELECT COUNT(*), "
                "SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END) "
                "FROM counterfactual_positions WHERE date(opened_at) = ?",
                (session_date,),
            )
            row = await cursor.fetchone()
            total_opened = row[0] if row else 0
            total_closed = row[1] if row else 0

            # Per-strategy stats
            cursor = await conn.execute(
                "SELECT strategy_id, "
                "COUNT(*) as total, "
                "SUM(CASE WHEN closed_at IS NOT NULL THEN 1 ELSE 0 END) as closed, "
                "SUM(CASE WHEN theoretical_r_multiple > 0 AND closed_at IS NOT NULL "
                "    THEN 1 ELSE 0 END) as wins, "
                "AVG(CASE WHEN closed_at IS NOT NULL THEN theoretical_r_multiple ELSE NULL END) as avg_r, "
                "AVG(CASE WHEN closed_at IS NOT NULL THEN theoretical_pnl ELSE NULL END) as avg_pnl "
                "FROM counterfactual_positions WHERE date(opened_at) = ? "
                "GROUP BY strategy_id",
                (session_date,),
            )
            by_strategy: dict[str, Any] = {}
            for r in await cursor.fetchall():
                closed = r["closed"] or 0
                by_strategy[r["strategy_id"]] = {
                    "positions_opened": r["total"],
                    "positions_closed": closed,
                    "wins": r["wins"] or 0,
                    "losses": closed - (r["wins"] or 0),
                    "avg_r": round(r["avg_r"], 3) if r["avg_r"] is not None else None,
                    "avg_pnl": round(r["avg_pnl"], 2) if r["avg_pnl"] is not None else None,
                }

            # By rejection stage
            cursor = await conn.execute(
                "SELECT rejection_stage, COUNT(*) "
                "FROM counterfactual_positions WHERE date(opened_at) = ? "
                "GROUP BY rejection_stage ORDER BY COUNT(*) DESC",
                (session_date,),
            )
            by_rejection_stage = {r[0]: r[1] for r in await cursor.fetchall()}

            # By exit reason (closed positions only)
            cursor = await conn.execute(
                "SELECT exit_reason, COUNT(*) "
                "FROM counterfactual_positions "
                "WHERE date(opened_at) = ? AND closed_at IS NOT NULL "
                "GROUP BY exit_reason ORDER BY COUNT(*) DESC",
                (session_date,),
            )
            by_exit_reason = {str(r[0]): r[1] for r in await cursor.fetchall()}

            return {
                "total_positions_opened": total_opened,
                "total_positions_closed": total_closed,
                "by_strategy": by_strategy,
                "by_rejection_stage": by_rejection_stage,
                "by_exit_reason": by_exit_reason,
            }

    except Exception as e:
        logger.warning("Debrief export: counterfactual_summary failed: %s", e)
        return {"error": str(e)}


async def _export_experiment_summary(
    experiment_db_path: str | None, session_date: str
) -> dict[str, Any]:
    """Query experiments.db for variant and promotion activity."""
    if experiment_db_path is None:
        return {"error": "experiment_db_path not provided"}

    try:
        db_path = Path(experiment_db_path)
        if not db_path.exists():
            return {"error": f"experiments.db not found at {experiment_db_path}"}

        async with aiosqlite.connect(str(db_path)) as conn:
            conn.row_factory = aiosqlite.Row

            # Total spawned variants
            cursor = await conn.execute("SELECT COUNT(*) FROM variants")
            row = await cursor.fetchone()
            variants_spawned = row[0] if row else 0

            # Variants by pattern
            cursor = await conn.execute(
                "SELECT base_pattern, GROUP_CONCAT(variant_id, ',') "
                "FROM variants GROUP BY base_pattern"
            )
            variants_by_pattern: dict[str, list[str]] = {}
            for r in await cursor.fetchall():
                variants_by_pattern[r[0]] = r[1].split(",") if r[1] else []

            # Variant shadow trade stats from experiments table
            cursor = await conn.execute(
                "SELECT experiment_id, pattern_name, shadow_trades, "
                "shadow_expectancy, status "
                "FROM experiments WHERE is_baseline = 0 "
                "ORDER BY shadow_trades DESC"
            )
            variant_shadow_trades: dict[str, Any] = {}
            for r in await cursor.fetchall():
                variant_shadow_trades[r["experiment_id"]] = {
                    "pattern_name": r["pattern_name"],
                    "trades": r["shadow_trades"],
                    "expectancy": round(r["shadow_expectancy"], 3)
                    if r["shadow_expectancy"] is not None
                    else None,
                    "status": r["status"],
                }

            # Promotion events today
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM promotion_events WHERE date(timestamp) = ?",
                (session_date,),
            )
            row = await cursor.fetchone()
            promotion_events_today = row[0] if row else 0

            return {
                "variants_spawned": variants_spawned,
                "variants_by_pattern": variants_by_pattern,
                "variant_shadow_trades": variant_shadow_trades,
                "promotion_events_today": promotion_events_today,
            }

    except Exception as e:
        logger.warning("Debrief export: experiment_summary failed: %s", e)
        return {"error": str(e)}


def _export_safety_summary(
    order_manager: object | None,
    orchestrator: object | None,
) -> dict[str, Any]:
    """Read safety-critical state from OrderManager and Orchestrator config.

    Margin circuit fields are read via getattr from the OrderManager instance.
    Fields not tracked in-memory (EOD flatten pass counts, signal skip count,
    peak concurrent positions) are reported as null — derive them from the JSONL
    log using the Phase 6 queries in the debrief protocol.
    """
    try:
        # Margin circuit breaker state
        circuit_open = bool(getattr(order_manager, "_margin_circuit_open", False))
        rejection_count = int(getattr(order_manager, "_margin_rejection_count", 0))

        # Signal cutoff config (duck-typed from orchestrator config)
        orchestrator_cfg = getattr(orchestrator, "_config", None) if orchestrator is not None else None
        cutoff_enabled = bool(getattr(orchestrator_cfg, "signal_cutoff_enabled", False))
        cutoff_time = str(getattr(orchestrator_cfg, "signal_cutoff_time", "15:30"))

        # Risk limits config (duck-typed for max_concurrent_positions)
        om_config = getattr(order_manager, "_config", None) if order_manager is not None else None
        eod_timeout = getattr(om_config, "eod_flatten_timeout_seconds", None)
        margin_threshold = getattr(om_config, "margin_rejection_threshold", None)

        return {
            "margin_circuit_breaker": {
                "triggered": circuit_open,
                "rejection_count": rejection_count,
                "rejection_threshold": int(margin_threshold) if margin_threshold is not None else None,
                # open_time/reset_time/entries_blocked: not tracked in-memory — derive from JSONL log
                "open_time": None,
                "reset_time": None,
                "entries_blocked": None,
            },
            "eod_flatten": {
                # Pass counts not tracked in-memory — derive from JSONL log (Phase 6)
                "timeout_seconds": int(eod_timeout) if eod_timeout is not None else None,
                "pass1_filled": None,
                "pass1_rejected": None,
                "pass1_timed_out": None,
                "pass2_orphans_found": None,
                "pass2_filled": None,
                "positions_remaining_after": None,
            },
            "signal_cutoff": {
                "active": cutoff_enabled,
                "cutoff_time": cutoff_time,
                # signals_skipped: not counted in-memory — derive from JSONL log
                "signals_skipped": None,
            },
        }

    except Exception as e:
        logger.warning("Debrief export: safety_summary failed: %s", e)
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
