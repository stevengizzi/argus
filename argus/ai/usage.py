"""Usage tracking for the AI Copilot.

Tracks API token consumption, estimated costs, and usage patterns.
Provides daily and monthly aggregation for budgeting and monitoring.

NOTE: Shares SQLite write lock with Trade Logger. Monitor latency during
active trading + chat. See RSK-NEW-5.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.ids import generate_id

if TYPE_CHECKING:
    from argus.db.manager import DatabaseManager

logger = logging.getLogger(__name__)


class UsageTracker:
    """Tracks AI API usage and costs.

    Records token consumption per API call and provides aggregation
    methods for daily, monthly, and summary views.

    Usage:
        db = DatabaseManager("data/argus.db")
        await db.initialize()

        usage_tracker = UsageTracker(db)
        await usage_tracker.initialize()

        await usage_tracker.record_usage(
            conversation_id="01ABC...",
            input_tokens=500,
            output_tokens=200,
            model="claude-opus-4-5-20250514",
            estimated_cost_usd=0.025,
        )

        daily = await usage_tracker.get_daily_usage("2026-03-06")
    """

    # Table creation SQL
    _USAGE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS ai_usage (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            timestamp TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            model TEXT NOT NULL,
            estimated_cost_usd REAL NOT NULL,
            endpoint TEXT DEFAULT 'chat',
            FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id)
        )
    """

    _USAGE_INDICES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON ai_usage(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_usage_conversation ON ai_usage(conversation_id)",
    ]

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize the usage tracker.

        Args:
            db: The database manager instance.
        """
        self._db = db

    async def initialize(self) -> None:
        """Initialize database tables.

        Creates ai_usage table if it doesn't exist.
        Safe to call multiple times.
        """
        await self._db.execute(self._USAGE_TABLE_SQL)
        for index_sql in self._USAGE_INDICES_SQL:
            await self._db.execute(index_sql)

        await self._db.commit()
        logger.info("AI usage table initialized")

    async def record_usage(
        self,
        conversation_id: str | None,
        input_tokens: int,
        output_tokens: int,
        model: str,
        estimated_cost_usd: float,
        endpoint: str = "chat",
    ) -> str:
        """Record an API usage event.

        Args:
            conversation_id: The conversation ULID, or None for non-chat calls.
            input_tokens: Number of input tokens consumed.
            output_tokens: Number of output tokens generated.
            model: The model identifier used.
            estimated_cost_usd: Estimated cost in USD.
            endpoint: The endpoint type (chat, insight, summary).

        Returns:
            The usage record ID.
        """
        usage_id = generate_id()
        now = datetime.now(ZoneInfo("UTC")).isoformat()

        sql = """
            INSERT INTO ai_usage (id, conversation_id, timestamp, input_tokens, output_tokens, model, estimated_cost_usd, endpoint)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self._db.execute(
            sql,
            (
                usage_id,
                conversation_id,
                now,
                input_tokens,
                output_tokens,
                model,
                estimated_cost_usd,
                endpoint,
            ),
        )
        await self._db.commit()

        logger.debug(
            "Recorded usage: %d in / %d out tokens, $%.4f",
            input_tokens,
            output_tokens,
            estimated_cost_usd,
        )

        return usage_id

    async def get_daily_usage(self, date: str) -> dict:
        """Get aggregated usage for a specific date.

        Args:
            date: Date in YYYY-MM-DD format.

        Returns:
            Dict with input_tokens, output_tokens, estimated_cost_usd, call_count.
        """
        sql = """
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) as estimated_cost_usd,
                COUNT(*) as call_count
            FROM ai_usage
            WHERE date(timestamp) = ?
        """
        row = await self._db.fetch_one(sql, (date,))

        if row is None:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.0,
                "call_count": 0,
            }

        r = dict(row)  # type: ignore[arg-type]
        return {
            "input_tokens": int(r["input_tokens"]),
            "output_tokens": int(r["output_tokens"]),
            "estimated_cost_usd": float(r["estimated_cost_usd"]),
            "call_count": int(r["call_count"]),
        }

    async def get_monthly_usage(self, year: int, month: int) -> dict:
        """Get aggregated usage for a specific month.

        Args:
            year: The year (e.g., 2026).
            month: The month (1-12).

        Returns:
            Dict with input_tokens, output_tokens, estimated_cost_usd, call_count,
            and daily_breakdown (list of per-day dicts).
        """
        # Format month pattern for SQL LIKE
        month_pattern = f"{year:04d}-{month:02d}-%"

        # Get monthly totals
        total_sql = """
            SELECT
                COALESCE(SUM(input_tokens), 0) as input_tokens,
                COALESCE(SUM(output_tokens), 0) as output_tokens,
                COALESCE(SUM(estimated_cost_usd), 0) as estimated_cost_usd,
                COUNT(*) as call_count
            FROM ai_usage
            WHERE timestamp LIKE ?
        """
        total_row = await self._db.fetch_one(total_sql, (month_pattern,))

        if total_row is None:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.0,
                "call_count": 0,
                "daily_breakdown": [],
            }

        t = dict(total_row)  # type: ignore[arg-type]

        # Get daily breakdown
        daily_sql = """
            SELECT
                date(timestamp) as date,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(estimated_cost_usd) as estimated_cost_usd,
                COUNT(*) as call_count
            FROM ai_usage
            WHERE timestamp LIKE ?
            GROUP BY date(timestamp)
            ORDER BY date ASC
        """
        daily_rows = await self._db.fetch_all(daily_sql, (month_pattern,))

        daily_breakdown = []
        for row in daily_rows:
            d = dict(row)  # type: ignore[arg-type]
            daily_breakdown.append({
                "date": d["date"],
                "input_tokens": int(d["input_tokens"]),
                "output_tokens": int(d["output_tokens"]),
                "estimated_cost_usd": float(d["estimated_cost_usd"]),
                "call_count": int(d["call_count"]),
            })

        return {
            "input_tokens": int(t["input_tokens"]),
            "output_tokens": int(t["output_tokens"]),
            "estimated_cost_usd": float(t["estimated_cost_usd"]),
            "call_count": int(t["call_count"]),
            "daily_breakdown": daily_breakdown,
        }

    async def get_usage_summary(self) -> dict:
        """Get a usage summary with today, this month, and per-day average.

        Returns:
            Dict with today, this_month, and per_day_average dicts.
        """
        # Get today's date in ET timezone
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)
        today_str = now_et.date().isoformat()
        year = now_et.year
        month = now_et.month

        # Get today's usage
        today_usage = await self.get_daily_usage(today_str)

        # Get this month's usage
        monthly_usage = await self.get_monthly_usage(year, month)

        # Calculate per-day average from this month
        daily_breakdown = monthly_usage.get("daily_breakdown", [])
        num_days = len(daily_breakdown) if daily_breakdown else 1

        per_day_avg = {
            "input_tokens": monthly_usage["input_tokens"] / num_days,
            "output_tokens": monthly_usage["output_tokens"] / num_days,
            "estimated_cost_usd": monthly_usage["estimated_cost_usd"] / num_days,
            "call_count": monthly_usage["call_count"] / num_days,
        }

        return {
            "today": today_usage,
            "this_month": {
                "input_tokens": monthly_usage["input_tokens"],
                "output_tokens": monthly_usage["output_tokens"],
                "estimated_cost_usd": monthly_usage["estimated_cost_usd"],
                "call_count": monthly_usage["call_count"],
            },
            "per_day_average": per_day_avg,
        }
