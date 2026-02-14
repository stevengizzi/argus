"""Trade logging service for Argus.

All completed trades are logged through this service. Provides
read/write access to trade records in the database.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime

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
                hold_duration_seconds, outcome, rationale, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        trades = await self.get_trades_by_date(date, strategy_id)

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

    def _row_to_trade(self, row: object) -> Trade:
        """Convert a database row to a Trade model.

        Args:
            row: The database row (aiosqlite.Row).

        Returns:
            The Trade model.
        """
        from argus.models.trading import AssetClass, ExitReason, OrderSide, TradeOutcome

        # Access row as dict-like object
        r = dict(row)  # type: ignore[arg-type]

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
        )
