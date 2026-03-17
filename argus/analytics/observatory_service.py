"""Observatory service: analytics and aggregation layer for pipeline visualization.

Provides read-only queries over evaluation telemetry, universe manager state,
and quality engine data to power The Observatory page.

Sprint 25, Session 1.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from argus.data.universe_manager import UniverseManager
    from argus.intelligence.quality_engine import SetupQualityEngine
    from argus.strategies.base_strategy import BaseStrategy
    from argus.strategies.telemetry_store import EvaluationEventStore

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


def _today_et() -> str:
    """Return today's date in ET as YYYY-MM-DD."""
    return datetime.now(_ET).strftime("%Y-%m-%d")


class ObservatoryService:
    """Analytics layer for The Observatory pipeline visualization page.

    Reads from EvaluationEventStore, UniverseManager, SetupQualityEngine,
    and the strategy registry. Never writes or modifies data.

    Args:
        telemetry_store: SQLite-backed evaluation event persistence.
        universe_manager: Viable universe and routing table provider.
        quality_engine: Quality scorer for near-trigger symbol display.
        strategies: Dictionary mapping strategy_id to BaseStrategy instances.
    """

    def __init__(
        self,
        telemetry_store: EvaluationEventStore | None,
        universe_manager: UniverseManager | None,
        quality_engine: SetupQualityEngine | None,
        strategies: dict[str, BaseStrategy],
    ) -> None:
        self._store = telemetry_store
        self._universe = universe_manager
        self._quality = quality_engine
        self._strategies = strategies

    async def get_pipeline_stages(self, date: str | None = None) -> dict:
        """Return counts for each pipeline tier.

        Args:
            date: Date filter (YYYY-MM-DD). Defaults to today (ET).

        Returns:
            Dict with keys: universe, viable, routed, evaluating,
            near_trigger, signal, traded.
        """
        target_date = date or _today_et()

        # Static counts from UniverseManager
        universe_count = 0
        viable_count = 0
        routed_count = 0

        if self._universe is not None:
            # Total symbols in reference cache = universe feed size
            universe_count = len(self._universe.reference_cache)
            viable_count = self._universe.viable_count
            # Routed = symbols that appear in the routing table with ≥1 strategy
            stats = self._universe.get_universe_stats()
            per_strategy = stats.get("per_strategy_counts", {})
            # Count distinct symbols that route to at least one strategy
            routed_count = stats.get("total_viable", 0) if per_strategy else 0

        # Dynamic counts from evaluation telemetry
        evaluating_count = 0
        near_trigger_count = 0
        signal_count = 0
        traded_count = 0

        if self._store is not None and self._store._conn is not None:
            conn = self._store._conn

            # Evaluating: distinct symbols with any event today
            row = await conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM evaluation_events "
                "WHERE trading_date = ?",
                (target_date,),
            )
            result = await row.fetchone()
            evaluating_count = result[0] if result else 0

            # Near-trigger: symbols passing ≥50% conditions in most recent
            # ENTRY_EVALUATION event
            near_trigger_count = await self._count_near_triggers(
                conn, target_date
            )

            # Signal: distinct symbols with SIGNAL_GENERATED event today
            row = await conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM evaluation_events "
                "WHERE trading_date = ? AND event_type = ?",
                (target_date, "SIGNAL_GENERATED"),
            )
            result = await row.fetchone()
            signal_count = result[0] if result else 0

            # Traded: distinct symbols with QUALITY_SCORED event (indicates
            # the signal went through the quality pipeline toward execution)
            row = await conn.execute(
                "SELECT COUNT(DISTINCT symbol) FROM evaluation_events "
                "WHERE trading_date = ? AND event_type = ?",
                (target_date, "QUALITY_SCORED"),
            )
            result = await row.fetchone()
            traded_count = result[0] if result else 0

        return {
            "universe": universe_count,
            "viable": viable_count,
            "routed": routed_count,
            "evaluating": evaluating_count,
            "near_trigger": near_trigger_count,
            "signal": signal_count,
            "traded": traded_count,
            "date": target_date,
        }

    async def get_closest_misses(
        self,
        tier: str,
        limit: int = 20,
        date: str | None = None,
    ) -> list[dict]:
        """Return symbols sorted by how many conditions they passed.

        Args:
            tier: Pipeline tier to query (e.g. "evaluating", "near_trigger").
            limit: Maximum entries to return.
            date: Date filter (YYYY-MM-DD). Defaults to today (ET).

        Returns:
            List of dicts with symbol, strategy, conditions_passed,
            conditions_total, conditions_detail.
        """
        target_date = date or _today_et()

        if self._store is None or self._store._conn is None:
            return []

        conn = self._store._conn

        # Get the most recent ENTRY_EVALUATION event per (symbol, strategy)
        rows = await conn.execute(
            """
            SELECT e.symbol, e.strategy_id, e.metadata_json, e.timestamp
            FROM evaluation_events e
            INNER JOIN (
                SELECT symbol, strategy_id, MAX(timestamp) as max_ts
                FROM evaluation_events
                WHERE trading_date = ? AND event_type = ?
                GROUP BY symbol, strategy_id
            ) latest
            ON e.symbol = latest.symbol
                AND e.strategy_id = latest.strategy_id
                AND e.timestamp = latest.max_ts
            WHERE e.trading_date = ? AND e.event_type = ?
            """,
            (target_date, "ENTRY_EVALUATION", target_date, "ENTRY_EVALUATION"),
        )
        results = await rows.fetchall()

        entries = []
        for row in results:
            metadata = _safe_json_loads(row[2])
            conditions_detail = _extract_conditions(metadata)
            passed = sum(1 for c in conditions_detail if c["passed"])
            total = len(conditions_detail)

            entries.append({
                "symbol": row[0],
                "strategy": row[1],
                "conditions_passed": passed,
                "conditions_total": total,
                "conditions_detail": conditions_detail,
                "timestamp": row[3],
            })

        # Sort by conditions_passed descending
        entries.sort(key=lambda e: e["conditions_passed"], reverse=True)

        return entries[:limit]

    async def get_symbol_journey(
        self,
        symbol: str,
        date: str | None = None,
    ) -> list[dict]:
        """Return chronological evaluation events for a symbol.

        Args:
            symbol: Ticker symbol to query.
            date: Date filter (YYYY-MM-DD). Defaults to today (ET).

        Returns:
            List of event dicts sorted by timestamp ascending.
        """
        target_date = date or _today_et()

        if self._store is None or self._store._conn is None:
            return []

        conn = self._store._conn

        rows = await conn.execute(
            "SELECT timestamp, strategy_id, event_type, result, reason, "
            "metadata_json FROM evaluation_events "
            "WHERE trading_date = ? AND symbol = ? "
            "ORDER BY timestamp ASC",
            (target_date, symbol.upper()),
        )
        results = await rows.fetchall()

        return [
            {
                "timestamp": row[0],
                "strategy": row[1],
                "event_type": row[2],
                "result": row[3],
                "metadata": _safe_json_loads(row[5]),
            }
            for row in results
        ]

    async def get_symbol_tiers(self, date: str | None = None) -> dict[str, str]:
        """Return current tier assignment for each symbol.

        Tier is determined by the most advanced pipeline stage reached today.
        Used by the WebSocket handler to diff between intervals and detect
        tier transitions.

        Args:
            date: Date filter (YYYY-MM-DD). Defaults to today (ET).

        Returns:
            Dict mapping symbol -> tier name (e.g. {"AAPL": "signal", "NVDA": "evaluating"}).
        """
        target_date = date or _today_et()

        if self._store is None or self._store._conn is None:
            return {}

        conn = self._store._conn

        # Build symbol -> highest tier from evaluation events
        # Tier priority: traded > signal > near_trigger > evaluating
        tier_priority = {
            "QUALITY_SCORED": "traded",
            "SIGNAL_GENERATED": "signal",
        }

        # Get all distinct (symbol, event_type) pairs for today
        rows = await conn.execute(
            "SELECT DISTINCT symbol, event_type FROM evaluation_events "
            "WHERE trading_date = ?",
            (target_date,),
        )
        results = await rows.fetchall()

        symbol_tiers: dict[str, str] = {}
        tier_rank = {"evaluating": 0, "near_trigger": 1, "signal": 2, "traded": 3}

        for row in results:
            symbol = row[0]
            event_type = row[1]
            tier = tier_priority.get(event_type, "evaluating")
            current_rank = tier_rank.get(symbol_tiers.get(symbol, ""), -1)
            new_rank = tier_rank.get(tier, 0)
            if new_rank > current_rank:
                symbol_tiers[symbol] = tier

        # Check near-trigger status for symbols still at "evaluating"
        if symbol_tiers:
            near_trigger_symbols = await self._get_near_trigger_symbols(
                conn, target_date
            )
            for sym in near_trigger_symbols:
                if symbol_tiers.get(sym) == "evaluating":
                    symbol_tiers[sym] = "near_trigger"

        return symbol_tiers

    async def _get_near_trigger_symbols(
        self,
        conn: object,
        target_date: str,
    ) -> set[str]:
        """Get symbols that pass ≥50% conditions in latest ENTRY_EVALUATION.

        Args:
            conn: aiosqlite connection.
            target_date: Date string (YYYY-MM-DD).

        Returns:
            Set of symbol names meeting near-trigger threshold.
        """
        rows = await conn.execute(  # type: ignore[union-attr]
            """
            SELECT e.symbol, e.metadata_json
            FROM evaluation_events e
            INNER JOIN (
                SELECT symbol, strategy_id, MAX(timestamp) as max_ts
                FROM evaluation_events
                WHERE trading_date = ? AND event_type = ?
                GROUP BY symbol, strategy_id
            ) latest
            ON e.symbol = latest.symbol
                AND e.strategy_id = latest.strategy_id
                AND e.timestamp = latest.max_ts
            WHERE e.trading_date = ? AND e.event_type = ?
            """,
            (target_date, "ENTRY_EVALUATION", target_date, "ENTRY_EVALUATION"),
        )
        results = await rows.fetchall()

        near_symbols: set[str] = set()
        for row in results:
            metadata = _safe_json_loads(row[1])
            conditions = _extract_conditions(metadata)
            if not conditions:
                continue
            passed = sum(1 for c in conditions if c["passed"])
            if passed >= len(conditions) / 2:
                near_symbols.add(row[0])

        return near_symbols

    async def get_session_summary(self, date: str | None = None) -> dict:
        """Return aggregate metrics for a trading session.

        Args:
            date: Date filter (YYYY-MM-DD). Defaults to today (ET).

        Returns:
            Dict with total_evaluations, total_signals, total_trades,
            symbols_evaluated, top_blockers, closest_miss.
        """
        target_date = date or _today_et()

        if self._store is None or self._store._conn is None:
            return {
                "total_evaluations": 0,
                "total_signals": 0,
                "total_trades": 0,
                "symbols_evaluated": 0,
                "top_blockers": [],
                "closest_miss": None,
                "date": target_date,
            }

        conn = self._store._conn

        # Total evaluations (ENTRY_EVALUATION events)
        row = await conn.execute(
            "SELECT COUNT(*) FROM evaluation_events "
            "WHERE trading_date = ? AND event_type = ?",
            (target_date, "ENTRY_EVALUATION"),
        )
        result = await row.fetchone()
        total_evaluations = result[0] if result else 0

        # Total signals
        row = await conn.execute(
            "SELECT COUNT(*) FROM evaluation_events "
            "WHERE trading_date = ? AND event_type = ?",
            (target_date, "SIGNAL_GENERATED"),
        )
        result = await row.fetchone()
        total_signals = result[0] if result else 0

        # Total trades (QUALITY_SCORED as proxy)
        row = await conn.execute(
            "SELECT COUNT(*) FROM evaluation_events "
            "WHERE trading_date = ? AND event_type = ?",
            (target_date, "QUALITY_SCORED"),
        )
        result = await row.fetchone()
        total_trades = result[0] if result else 0

        # Distinct symbols evaluated
        row = await conn.execute(
            "SELECT COUNT(DISTINCT symbol) FROM evaluation_events "
            "WHERE trading_date = ?",
            (target_date,),
        )
        result = await row.fetchone()
        symbols_evaluated = result[0] if result else 0

        # Top blockers: most frequent rejection reasons from ENTRY_EVALUATION
        # events with FAIL result
        top_blockers = await self._get_top_blockers(conn, target_date)

        # Closest miss: the single symbol+strategy with most conditions passed
        closest_misses = await self.get_closest_misses(
            tier="evaluating", limit=1, date=target_date
        )
        closest_miss = closest_misses[0] if closest_misses else None

        return {
            "total_evaluations": total_evaluations,
            "total_signals": total_signals,
            "total_trades": total_trades,
            "symbols_evaluated": symbols_evaluated,
            "top_blockers": top_blockers,
            "closest_miss": closest_miss,
            "date": target_date,
        }

    async def _count_near_triggers(
        self,
        conn: object,
        target_date: str,
    ) -> int:
        """Count symbols passing ≥50% conditions in latest ENTRY_EVALUATION.

        Args:
            conn: aiosqlite connection.
            target_date: Date string (YYYY-MM-DD).

        Returns:
            Count of near-trigger symbols.
        """
        # Get latest ENTRY_EVALUATION per (symbol, strategy)
        rows = await conn.execute(  # type: ignore[union-attr]
            """
            SELECT e.metadata_json
            FROM evaluation_events e
            INNER JOIN (
                SELECT symbol, strategy_id, MAX(timestamp) as max_ts
                FROM evaluation_events
                WHERE trading_date = ? AND event_type = ?
                GROUP BY symbol, strategy_id
            ) latest
            ON e.symbol = latest.symbol
                AND e.strategy_id = latest.strategy_id
                AND e.timestamp = latest.max_ts
            WHERE e.trading_date = ? AND e.event_type = ?
            """,
            (target_date, "ENTRY_EVALUATION", target_date, "ENTRY_EVALUATION"),
        )
        results = await rows.fetchall()

        count = 0
        for row in results:
            metadata = _safe_json_loads(row[0])
            conditions = _extract_conditions(metadata)
            if not conditions:
                continue
            passed = sum(1 for c in conditions if c["passed"])
            if passed >= len(conditions) / 2:
                count += 1

        return count

    async def _get_top_blockers(
        self,
        conn: object,
        target_date: str,
        top_n: int = 5,
    ) -> list[dict]:
        """Get the most frequent rejection reasons.

        Parses ENTRY_EVALUATION metadata for failed conditions, counts
        occurrences, and returns the top N.

        Args:
            conn: aiosqlite connection.
            target_date: Date string (YYYY-MM-DD).
            top_n: Number of top blockers to return.

        Returns:
            List of {condition_name, rejection_count, percentage} dicts.
        """
        rows = await conn.execute(  # type: ignore[union-attr]
            "SELECT metadata_json FROM evaluation_events "
            "WHERE trading_date = ? AND event_type = ?",
            (target_date, "ENTRY_EVALUATION"),
        )
        results = await rows.fetchall()

        blocker_counts: dict[str, int] = {}
        total_checks = 0

        for row in results:
            metadata = _safe_json_loads(row[0])
            conditions = _extract_conditions(metadata)
            for cond in conditions:
                if not cond["passed"]:
                    name = cond["name"]
                    blocker_counts[name] = blocker_counts.get(name, 0) + 1
                    total_checks += 1

        if total_checks == 0:
            return []

        # Sort by count descending, take top N
        sorted_blockers = sorted(
            blocker_counts.items(), key=lambda x: x[1], reverse=True
        )[:top_n]

        return [
            {
                "condition_name": name,
                "rejection_count": count,
                "percentage": round(count / total_checks * 100, 1),
            }
            for name, count in sorted_blockers
        ]


def _safe_json_loads(raw: str | None) -> dict:
    """Parse JSON string, returning empty dict on failure.

    Args:
        raw: JSON string or None.

    Returns:
        Parsed dict, or empty dict if parsing fails.
    """
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _extract_conditions(metadata: dict) -> list[dict]:
    """Extract condition details from evaluation event metadata.

    Handles multiple metadata formats gracefully:
    - {"conditions": [{"name": ..., "passed": ..., ...}, ...]}
    - {"checks": {"condition_name": true/false, ...}}
    - Flat metadata with individual condition keys

    Args:
        metadata: Parsed metadata dict from an evaluation event.

    Returns:
        List of {name, passed, actual_value, required_value} dicts.
    """
    # Format 1: explicit conditions array
    if "conditions" in metadata and isinstance(metadata["conditions"], list):
        conditions = []
        for c in metadata["conditions"]:
            if isinstance(c, dict):
                conditions.append({
                    "name": c.get("name", "unknown"),
                    "passed": bool(c.get("passed", False)),
                    "actual_value": c.get("actual_value"),
                    "required_value": c.get("required_value"),
                })
        return conditions

    # Format 2: checks dict {name: bool}
    if "checks" in metadata and isinstance(metadata["checks"], dict):
        return [
            {
                "name": name,
                "passed": bool(passed),
                "actual_value": None,
                "required_value": None,
            }
            for name, passed in metadata["checks"].items()
        ]

    # Format 3: look for common condition keys at top level
    known_conditions = [
        "volume_check", "price_check", "range_check", "trend_check",
        "time_check", "atr_check", "vwap_check", "gap_check",
        "consolidation_check", "breakout_check",
    ]
    found = []
    for key in known_conditions:
        if key in metadata:
            found.append({
                "name": key,
                "passed": bool(metadata[key]),
                "actual_value": None,
                "required_value": None,
            })

    return found
