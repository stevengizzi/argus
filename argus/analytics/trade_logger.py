"""Trade logging service for Argus.

All completed trades are logged through this service. Provides
read/write access to trade records in the database.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any

import aiosqlite

from argus.core.ids import generate_id
from argus.db.manager import DatabaseManager
from argus.models.trading import DailySummary, Trade

logger = logging.getLogger(__name__)


class TradeLogger:
    """Service for logging and retrieving trades.

    Usage:
        db = DatabaseManager("data/argus.db")
        await db.initialize()

        trade_logger = TradeLogger(db)

        trade = Trade(
            strategy_id="strat_orb",
            symbol="AAPL",
            side=OrderSide.BUY,
            ...
        )
        await trade_logger.log_trade(trade)

        trades = await trade_logger.get_trades_by_strategy("strat_orb")
    """

    def __init__(self, db: DatabaseManager) -> None:
        """Initialize the trade logger.

        Args:
            db: The database manager instance.
        """
        self._db = db

    async def log_trade(self, trade: Trade) -> str:
        """Log a completed trade to the database.

        Args:
            trade: The trade to log.

        Returns:
            The trade ID.

        Raises:
            RuntimeError: If database is not initialized.
        """
        sql = """
            INSERT INTO trades (
                id, strategy_id, symbol, asset_class, side,
                entry_price, entry_time, exit_price, exit_time,
                shares, stop_price, target_prices, exit_reason,
                gross_pnl, commission, net_pnl, r_multiple,
                hold_duration_seconds, outcome, rationale, notes,
                quality_grade, quality_score,
                mfe_r, mae_r, mfe_price, mae_price,
                config_fingerprint, entry_price_known
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            trade.id,
            trade.strategy_id,
            trade.symbol,
            trade.asset_class.value,
            trade.side.value,
            trade.entry_price,
            trade.entry_time.isoformat(),
            trade.exit_price,
            trade.exit_time.isoformat(),
            trade.shares,
            trade.stop_price,
            json.dumps(trade.target_prices),
            trade.exit_reason.value,
            trade.gross_pnl,
            trade.commission,
            trade.net_pnl,
            trade.r_multiple,
            trade.hold_duration_seconds,
            trade.outcome.value,
            trade.rationale,
            trade.notes,
            trade.quality_grade,
            trade.quality_score if trade.quality_score is not None else None,
            trade.mfe_r,
            trade.mae_r,
            trade.mfe_price,
            trade.mae_price,
            trade.config_fingerprint,
            1 if trade.entry_price_known else 0,
        )

        await self._db.execute(sql, params)
        await self._db.commit()

        logger.info(
            "Logged trade %s: %s %s %s %.2f -> %.2f (%s)",
            trade.id[:8],
            trade.strategy_id,
            trade.side.value,
            trade.symbol,
            trade.entry_price,
            trade.exit_price,
            trade.outcome.value,
        )

        return trade.id

    async def get_trade(self, trade_id: str) -> Trade | None:
        """Retrieve a trade by ID.

        Args:
            trade_id: The trade ID.

        Returns:
            The trade, or None if not found.
        """
        sql = "SELECT * FROM trades WHERE id = ?"
        row = await self._db.fetch_one(sql, (trade_id,))

        if row is None:
            return None

        return self._row_to_trade(row)

    async def get_trades_by_strategy(
        self,
        strategy_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
    ) -> list[Trade]:
        """Retrieve trades for a specific strategy.

        Args:
            strategy_id: The strategy ID.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            limit: Maximum number of trades to return.

        Returns:
            List of trades, ordered by exit_time descending.
        """
        sql = "SELECT * FROM trades WHERE strategy_id = ?"
        params: list[object] = [strategy_id]

        if start_date is not None:
            sql += " AND exit_time >= ?"
            params.append(start_date.isoformat())

        if end_date is not None:
            sql += " AND exit_time <= ?"
            params.append(end_date.isoformat())

        sql += " ORDER BY exit_time DESC LIMIT ?"
        params.append(limit)

        rows = await self._db.fetch_all(sql, tuple(params))
        return [self._row_to_trade(row) for row in rows]

    async def get_trades_by_symbol(
        self,
        symbol: str,
        limit: int = 100,
    ) -> list[Trade]:
        """Retrieve trades for a specific symbol.

        Args:
            symbol: The stock symbol.
            limit: Maximum number of trades to return.

        Returns:
            List of trades, ordered by exit_time descending.
        """
        sql = """
            SELECT * FROM trades
            WHERE symbol = ?
            ORDER BY exit_time DESC
            LIMIT ?
        """
        rows = await self._db.fetch_all(sql, (symbol, limit))
        return [self._row_to_trade(row) for row in rows]

    async def get_trades_by_date(
        self,
        trade_date: str | date,
        strategy_id: str | None = None,
    ) -> list[Trade]:
        """Retrieve trades for a specific date.

        Args:
            trade_date: Date string in YYYY-MM-DD format or date object.
            strategy_id: Optional strategy filter.

        Returns:
            List of trades, ordered by exit_time.
        """
        date_str = trade_date.isoformat() if isinstance(trade_date, date) else trade_date
        sql = "SELECT * FROM trades WHERE date(exit_time) = ?"
        params: list[object] = [date_str]

        if strategy_id is not None:
            sql += " AND strategy_id = ?"
            params.append(strategy_id)

        sql += " ORDER BY exit_time"

        rows = await self._db.fetch_all(sql, tuple(params))
        return [self._row_to_trade(row) for row in rows]

    async def get_trades_by_date_range(
        self,
        start_date: str | date,
        end_date: str | date,
        strategy_id: str | None = None,
    ) -> list[Trade]:
        """Retrieve trades within a date range (inclusive).

        Args:
            start_date: Start date (YYYY-MM-DD format or date object).
            end_date: End date (YYYY-MM-DD format or date object).
            strategy_id: Optional strategy filter.

        Returns:
            List of trades, ordered by exit_time.
        """
        start_str = start_date.isoformat() if isinstance(start_date, date) else start_date
        end_str = end_date.isoformat() if isinstance(end_date, date) else end_date

        sql = "SELECT * FROM trades WHERE date(exit_time) >= ? AND date(exit_time) <= ?"
        params: list[object] = [start_str, end_str]

        if strategy_id is not None:
            sql += " AND strategy_id = ?"
            params.append(strategy_id)

        sql += " ORDER BY exit_time"

        rows = await self._db.fetch_all(sql, tuple(params))
        return [self._row_to_trade(row) for row in rows]

    async def get_daily_summary(
        self,
        date: str,
        strategy_id: str | None = None,
    ) -> DailySummary:
        """Calculate or retrieve the daily summary for a date.

        Args:
            date: Date string in YYYY-MM-DD format.
            strategy_id: Optional strategy filter.

        Returns:
            The daily summary.
        """
        all_trades = await self.get_trades_by_date(date, strategy_id)
        # Exclude trades with unrecoverable entry prices (DEF-159)
        trades = [t for t in all_trades if t.entry_price_known]

        if not trades:
            return DailySummary(date=date, strategy_id=strategy_id)

        winning = [t for t in trades if t.net_pnl > 0]
        losing = [t for t in trades if t.net_pnl < 0]

        gross_pnl = sum(t.gross_pnl for t in trades)
        commissions = sum(t.commission for t in trades)
        net_pnl = sum(t.net_pnl for t in trades)

        total_wins = sum(t.net_pnl for t in winning)
        total_losses = abs(sum(t.net_pnl for t in losing))

        return DailySummary(
            date=date,
            strategy_id=strategy_id,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(trades) if trades else 0,
            gross_pnl=gross_pnl,
            commissions=commissions,
            net_pnl=net_pnl,
            avg_winner=total_wins / len(winning) if winning else 0,
            avg_loser=total_losses / len(losing) if losing else 0,
            largest_winner=max((t.net_pnl for t in winning), default=0),
            largest_loser=min((t.net_pnl for t in losing), default=0),
            avg_r_multiple=sum(t.r_multiple for t in trades) / len(trades) if trades else 0,
            profit_factor=total_wins / total_losses if total_losses > 0 else float("inf"),
        )

    async def get_todays_pnl(self) -> float:
        """Get total net P&L for today's closed trades.

        Uses ET timezone for date comparison to match trading hours.

        Returns:
            Sum of net_pnl for all trades exited today.
        """
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        today_et = datetime.now(et_tz).date().isoformat()

        sql = (
            "SELECT COALESCE(SUM(net_pnl), 0) as total FROM trades "
            "WHERE date(exit_time) = ? AND entry_price_known = 1"
        )
        row = await self._db.fetch_one(sql, (today_et,))

        if row is None:
            return 0.0
        return float(row[0])

    async def get_todays_trade_count(self) -> int:
        """Get the count of trades closed today.

        Uses ET timezone for date comparison to match trading hours.

        Returns:
            Number of trades exited today.
        """
        from zoneinfo import ZoneInfo

        et_tz = ZoneInfo("America/New_York")
        today_et = datetime.now(et_tz).date().isoformat()

        sql = "SELECT COUNT(*) as count FROM trades WHERE date(exit_time) = ? AND entry_price_known = 1"
        row = await self._db.fetch_one(sql, (today_et,))

        if row is None:
            return 0
        return int(row[0])

    async def query_trades(
        self,
        strategy_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        outcome: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query trades with filtering and pagination.

        Args:
            strategy_id: Optional strategy ID filter.
            date_from: Optional start date filter (ISO YYYY-MM-DD).
            date_to: Optional end date filter (ISO YYYY-MM-DD).
            outcome: Optional outcome filter ("win", "loss", "breakeven").
            symbol: Optional symbol filter (e.g., "AAPL").
            limit: Maximum number of trades to return (default 50).
            offset: Number of trades to skip for pagination.

        Returns:
            List of trade dicts, ordered by entry_time DESC.
        """
        conditions: list[str] = []
        params: list[object] = []

        if strategy_id is not None:
            conditions.append("strategy_id = ?")
            params.append(strategy_id)

        if symbol is not None:
            conditions.append("symbol = ?")
            params.append(symbol)

        if date_from is not None:
            conditions.append("date(entry_time) >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("date(entry_time) <= ?")
            params.append(date_to)

        if outcome is not None:
            if outcome == "win":
                conditions.append("net_pnl > 0")
            elif outcome == "loss":
                conditions.append("net_pnl < 0")
            elif outcome == "breakeven":
                conditions.append("net_pnl = 0")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT * FROM trades
            WHERE {where_clause}
            ORDER BY entry_time DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = await self._db.fetch_all(sql, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    async def get_trades_by_ids(self, trade_ids: list[str]) -> list[dict[str, Any]]:
        """Retrieve trades by their IDs.

        Args:
            trade_ids: List of trade IDs to fetch.

        Returns:
            List of trade dicts for IDs that exist. Missing IDs are silently skipped.
        """
        if not trade_ids:
            return []

        # Build parameterized IN clause
        placeholders = ",".join("?" * len(trade_ids))
        sql = f"""
            SELECT * FROM trades
            WHERE id IN ({placeholders})
            ORDER BY entry_time DESC
        """

        rows = await self._db.fetch_all(sql, tuple(trade_ids))
        return [self._row_to_dict(row) for row in rows]

    async def count_trades(
        self,
        strategy_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        outcome: str | None = None,
        symbol: str | None = None,
    ) -> int:
        """Count trades matching filters for pagination total.

        Args:
            strategy_id: Optional strategy ID filter.
            date_from: Optional start date filter (ISO YYYY-MM-DD).
            date_to: Optional end date filter (ISO YYYY-MM-DD).
            outcome: Optional outcome filter ("win", "loss", "breakeven").
            symbol: Optional symbol filter (e.g., "AAPL").

        Returns:
            Total number of matching trades.
        """
        conditions: list[str] = []
        params: list[object] = []

        if strategy_id is not None:
            conditions.append("strategy_id = ?")
            params.append(strategy_id)

        if symbol is not None:
            conditions.append("symbol = ?")
            params.append(symbol)

        if date_from is not None:
            conditions.append("date(entry_time) >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("date(entry_time) <= ?")
            params.append(date_to)

        if outcome is not None:
            if outcome == "win":
                conditions.append("net_pnl > 0")
            elif outcome == "loss":
                conditions.append("net_pnl < 0")
            elif outcome == "breakeven":
                conditions.append("net_pnl = 0")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT COUNT(*) FROM trades WHERE {where_clause}"

        row = await self._db.fetch_one(sql, tuple(params))
        if row is None:
            return 0
        return int(row[0])

    async def get_daily_pnl(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        strategy_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily P&L aggregation.

        Args:
            date_from: Optional start date filter (ISO YYYY-MM-DD).
            date_to: Optional end date filter (ISO YYYY-MM-DD).
            strategy_id: Optional strategy ID filter. If provided, returns P&L
                        for that strategy only. If None, returns account-wide P&L.

        Returns:
            List of dicts with date, pnl, and trades count per day.
        """
        conditions: list[str] = []
        params: list[object] = []

        if date_from is not None:
            conditions.append("date(entry_time) >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("date(entry_time) <= ?")
            params.append(date_to)

        if strategy_id is not None:
            conditions.append("strategy_id = ?")
            params.append(strategy_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"""
            SELECT
                date(entry_time) as date,
                SUM(net_pnl) as pnl,
                COUNT(*) as trades
            FROM trades
            WHERE {where_clause}
            GROUP BY date(entry_time)
            ORDER BY date DESC
        """

        rows = await self._db.fetch_all(sql, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    async def get_daily_pnl_by_strategy(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily P&L broken out by strategy.

        Used for computing strategy correlation matrices and other
        cross-strategy analytics.

        Args:
            date_from: Optional start date filter (ISO YYYY-MM-DD).
            date_to: Optional end date filter (ISO YYYY-MM-DD).

        Returns:
            List of dicts with {date, strategy_id, pnl} rows.
            Each row represents one strategy's P&L for one day.
        """
        conditions: list[str] = ["exit_time IS NOT NULL"]
        params: list[object] = []

        if date_from is not None:
            conditions.append("date(exit_time) >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("date(exit_time) <= ?")
            params.append(date_to)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT
                date(exit_time) as date,
                strategy_id,
                SUM(net_pnl) as pnl
            FROM trades
            WHERE {where_clause}
            GROUP BY date(exit_time), strategy_id
            ORDER BY date DESC, strategy_id
        """

        rows = await self._db.fetch_all(sql, tuple(params))
        return [self._row_to_dict(row) for row in rows]

    async def log_orchestrator_decision(
        self,
        date: str,
        decision_type: str,
        strategy_id: str | None,
        details: dict[str, Any],
        rationale: str,
        created_at: str | None = None,
    ) -> str:
        """Log an orchestrator decision to the database.

        Args:
            date: Date of the decision (ISO YYYY-MM-DD format).
            decision_type: Type of decision (allocation, activation, etc.).
            strategy_id: Strategy ID if applicable, None for system-wide decisions.
            details: Dict with decision details (will be JSON-serialized).
            rationale: Human-readable explanation.
            created_at: Optional ISO timestamp (for dev mode mock data).
                If not provided, uses database default (current time).

        Returns:
            The generated decision ID.
        """
        decision_id = generate_id()

        if created_at is not None:
            sql = """INSERT INTO orchestrator_decisions
                     (id, date, decision_type, strategy_id, details, rationale, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?)"""
            await self._db.execute(
                sql,
                (
                    decision_id,
                    date,
                    decision_type,
                    strategy_id,
                    json.dumps(details),
                    rationale,
                    created_at,
                ),
            )
        else:
            sql = """INSERT INTO orchestrator_decisions
                     (id, date, decision_type, strategy_id, details, rationale)
                     VALUES (?, ?, ?, ?, ?, ?)"""
            await self._db.execute(
                sql,
                (decision_id, date, decision_type, strategy_id, json.dumps(details), rationale),
            )

        await self._db.commit()

        logger.debug(
            "Logged orchestrator decision %s: %s for %s",
            decision_id[:8],
            decision_type,
            strategy_id or "system",
        )

        return decision_id

    async def get_orchestrator_decisions(
        self,
        limit: int = 50,
        offset: int = 0,
        strategy_id: str | None = None,
        decision_type: str | None = None,
        date: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Query orchestrator decisions with pagination.

        Args:
            limit: Maximum number of decisions to return (default 50).
            offset: Number of decisions to skip for pagination.
            strategy_id: Optional strategy ID filter.
            decision_type: Optional decision type filter.
            date: Optional date filter (ISO YYYY-MM-DD format).

        Returns:
            Tuple of (list of decision dicts, total count).
        """
        conditions: list[str] = []
        params: list[object] = []

        if strategy_id is not None:
            conditions.append("strategy_id = ?")
            params.append(strategy_id)

        if decision_type is not None:
            conditions.append("decision_type = ?")
            params.append(decision_type)

        if date is not None:
            conditions.append("date = ?")
            params.append(date)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_sql = f"SELECT COUNT(*) FROM orchestrator_decisions WHERE {where_clause}"
        count_row = await self._db.fetch_one(count_sql, tuple(params))
        total = int(count_row[0]) if count_row else 0

        # Get paginated results
        # Returns newest-first. Frontend DecisionTimeline reverses for chronological display.
        sql = f"""
            SELECT id, date, decision_type, strategy_id, details, rationale, created_at
            FROM orchestrator_decisions
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = await self._db.fetch_all(sql, tuple(params))

        decisions = []
        for row in rows:
            r = self._row_to_dict(row)
            decisions.append(
                {
                    "id": r["id"],
                    "date": r["date"],
                    "decision_type": r["decision_type"],
                    "strategy_id": r.get("strategy_id"),
                    "details": json.loads(r["details"]) if r.get("details") else None,
                    "rationale": r.get("rationale"),
                    "created_at": r["created_at"],
                }
            )

        return decisions, total

    async def save_daily_summary(self, summary: DailySummary) -> str:
        """Save a daily summary to the database.

        Args:
            summary: The daily summary to save.

        Returns:
            The summary ID.
        """
        summary_id = generate_id()

        sql = """
            INSERT OR REPLACE INTO daily_summaries (
                id, date, strategy_id, total_trades, winning_trades,
                losing_trades, win_rate, gross_pnl, commissions, net_pnl,
                avg_winner, avg_loser, largest_winner, largest_loser,
                avg_r_multiple, profit_factor
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            summary_id,
            summary.date,
            summary.strategy_id,
            summary.total_trades,
            summary.winning_trades,
            summary.losing_trades,
            summary.win_rate,
            summary.gross_pnl,
            summary.commissions,
            summary.net_pnl,
            summary.avg_winner,
            summary.avg_loser,
            summary.largest_winner,
            summary.largest_loser,
            summary.avg_r_multiple,
            summary.profit_factor,
        )

        await self._db.execute(sql, params)
        await self._db.commit()

        return summary_id

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        """Convert an aiosqlite.Row to a plain dict.

        Args:
            row: The database row.

        Returns:
            Dict with column names as keys.
        """
        return dict(row)  # type: ignore[arg-type]

    def _row_to_trade(self, row: aiosqlite.Row) -> Trade:
        """Convert a database row to a Trade model.

        Args:
            row: The database row (aiosqlite.Row).

        Returns:
            The Trade model.
        """
        from argus.models.trading import AssetClass, ExitReason, OrderSide, TradeOutcome

        r = self._row_to_dict(row)

        return Trade(
            id=r["id"],
            strategy_id=r["strategy_id"],
            symbol=r["symbol"],
            asset_class=AssetClass(r["asset_class"]),
            side=OrderSide(r["side"]),
            entry_price=r["entry_price"],
            entry_time=datetime.fromisoformat(r["entry_time"]),
            exit_price=r["exit_price"],
            exit_time=datetime.fromisoformat(r["exit_time"]),
            shares=r["shares"],
            stop_price=r["stop_price"],
            target_prices=json.loads(r["target_prices"]) if r["target_prices"] else [],
            exit_reason=ExitReason(r["exit_reason"]),
            gross_pnl=r["gross_pnl"],
            commission=r["commission"],
            net_pnl=r["net_pnl"],
            r_multiple=r["r_multiple"],
            hold_duration_seconds=r["hold_duration_seconds"],
            outcome=TradeOutcome(r["outcome"]),
            rationale=r["rationale"] or "",
            notes=r["notes"] or "",
            quality_grade=r.get("quality_grade", "") or "",
            quality_score=float(r["quality_score"]) if r.get("quality_score") is not None else 0.0,
            mfe_r=float(r["mfe_r"]) if r.get("mfe_r") is not None else None,
            mae_r=float(r["mae_r"]) if r.get("mae_r") is not None else None,
            mfe_price=float(r["mfe_price"]) if r.get("mfe_price") is not None else None,
            mae_price=float(r["mae_price"]) if r.get("mae_price") is not None else None,
            config_fingerprint=r.get("config_fingerprint"),
            entry_price_known=bool(r.get("entry_price_known", 1)),
        )
