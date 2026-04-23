"""Tests for the trade logger."""

from datetime import datetime

from argus.analytics.trade_logger import TradeLogger
from argus.db.manager import DatabaseManager
from argus.models.trading import ExitReason, OrderSide, Trade


def make_trade(
    strategy_id: str = "strat_orb",
    symbol: str = "AAPL",
    gross_pnl: float = 100.0,
    exit_time: datetime | None = None,
) -> Trade:
    """Helper to create a test trade."""
    entry_time = datetime(2026, 2, 15, 10, 0, 0)
    if exit_time is None:
        exit_time = datetime(2026, 2, 15, 10, 30, 0)

    return Trade(
        strategy_id=strategy_id,
        symbol=symbol,
        side=OrderSide.BUY,
        entry_price=150.0,
        entry_time=entry_time,
        exit_price=151.0 if gross_pnl > 0 else 149.0,
        exit_time=exit_time,
        shares=100,
        stop_price=148.0,
        exit_reason=ExitReason.TARGET_1 if gross_pnl > 0 else ExitReason.STOP_LOSS,
        gross_pnl=gross_pnl,
        commission=1.0,
    )


class TestTradeLogger:
    """Tests for TradeLogger."""

    async def test_log_trade(self, trade_logger: TradeLogger) -> None:
        """log_trade saves a trade to the database."""
        trade = make_trade()
        trade_id = await trade_logger.log_trade(trade)

        assert trade_id == trade.id

        # Verify it was saved
        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.strategy_id == "strat_orb"

    async def test_get_trade_not_found(self, trade_logger: TradeLogger) -> None:
        """get_trade returns None for missing trade."""
        result = await trade_logger.get_trade("nonexistent_id")
        assert result is None

    async def test_get_trades_by_strategy(self, trade_logger: TradeLogger) -> None:
        """get_trades_by_strategy filters by strategy ID."""
        # Create trades for different strategies
        await trade_logger.log_trade(make_trade(strategy_id="strat_orb"))
        await trade_logger.log_trade(make_trade(strategy_id="strat_orb"))
        await trade_logger.log_trade(make_trade(strategy_id="strat_other"))

        orb_trades = await trade_logger.get_trades_by_strategy("strat_orb")
        assert len(orb_trades) == 2

        other_trades = await trade_logger.get_trades_by_strategy("strat_other")
        assert len(other_trades) == 1

    async def test_get_trades_by_symbol(self, trade_logger: TradeLogger) -> None:
        """get_trades_by_symbol filters by symbol."""
        await trade_logger.log_trade(make_trade(symbol="AAPL"))
        await trade_logger.log_trade(make_trade(symbol="AAPL"))
        await trade_logger.log_trade(make_trade(symbol="MSFT"))

        aapl_trades = await trade_logger.get_trades_by_symbol("AAPL")
        assert len(aapl_trades) == 2

    async def test_get_trades_by_date(self, trade_logger: TradeLogger) -> None:
        """get_trades_by_date filters by date."""
        await trade_logger.log_trade(make_trade(exit_time=datetime(2026, 2, 15, 10, 30, 0)))
        await trade_logger.log_trade(make_trade(exit_time=datetime(2026, 2, 15, 11, 0, 0)))
        await trade_logger.log_trade(make_trade(exit_time=datetime(2026, 2, 16, 10, 0, 0)))

        feb15_trades = await trade_logger.get_trades_by_date("2026-02-15")
        assert len(feb15_trades) == 2

        feb16_trades = await trade_logger.get_trades_by_date("2026-02-16")
        assert len(feb16_trades) == 1

    async def test_get_daily_summary(self, trade_logger: TradeLogger) -> None:
        """get_daily_summary calculates correct metrics."""
        # Create 3 winning trades and 1 losing trade
        await trade_logger.log_trade(make_trade(gross_pnl=100.0))
        await trade_logger.log_trade(make_trade(gross_pnl=200.0))
        await trade_logger.log_trade(make_trade(gross_pnl=50.0))
        await trade_logger.log_trade(make_trade(gross_pnl=-100.0))

        summary = await trade_logger.get_daily_summary("2026-02-15")

        assert summary.total_trades == 4
        assert summary.winning_trades == 3
        assert summary.losing_trades == 1
        assert summary.win_rate == 0.75

        # Gross P&L: 100 + 200 + 50 - 100 = 250
        assert summary.gross_pnl == 250.0

        # Commissions: 4 * $1 = $4
        assert summary.commissions == 4.0

        # Net P&L: 250 - 4 = 246
        assert summary.net_pnl == 246.0

    async def test_get_daily_summary_empty(self, trade_logger: TradeLogger) -> None:
        """get_daily_summary returns zeros for empty day."""
        summary = await trade_logger.get_daily_summary("2026-02-20")

        assert summary.total_trades == 0
        assert summary.net_pnl == 0.0
        assert summary.win_rate == 0.0

    async def test_save_daily_summary(self, trade_logger: TradeLogger, db: DatabaseManager) -> None:
        """save_daily_summary persists the summary."""
        # Create some trades first
        await trade_logger.log_trade(make_trade(gross_pnl=100.0))
        await trade_logger.log_trade(make_trade(gross_pnl=-50.0))

        summary = await trade_logger.get_daily_summary("2026-02-15")
        summary_id = await trade_logger.save_daily_summary(summary)

        assert len(summary_id) == 26  # ULID

        # Verify it was saved
        row = await db.fetch_one("SELECT * FROM daily_summaries WHERE date = ?", ("2026-02-15",))
        assert row is not None
        assert row["total_trades"] == 2

    async def test_get_daily_pnl_account_wide(self, trade_logger: TradeLogger) -> None:
        """get_daily_pnl without strategy_id returns account-wide P&L."""
        # Create trades for different strategies
        await trade_logger.log_trade(make_trade(strategy_id="strat_orb", gross_pnl=100.0))
        await trade_logger.log_trade(make_trade(strategy_id="strat_orb", gross_pnl=50.0))
        await trade_logger.log_trade(make_trade(strategy_id="strat_scalp", gross_pnl=-30.0))

        daily_pnl = await trade_logger.get_daily_pnl()

        # Should return one record with combined P&L from all strategies
        assert len(daily_pnl) == 1
        # Net P&L = (100-1) + (50-1) + (-30-1) = 99 + 49 - 31 = 117
        assert daily_pnl[0]["pnl"] == 117.0
        assert daily_pnl[0]["trades"] == 3

    async def test_get_daily_pnl_per_strategy(self, trade_logger: TradeLogger) -> None:
        """get_daily_pnl with strategy_id filters to that strategy only."""
        # Create trades for different strategies
        await trade_logger.log_trade(make_trade(strategy_id="strat_orb", gross_pnl=100.0))
        await trade_logger.log_trade(make_trade(strategy_id="strat_orb", gross_pnl=50.0))
        await trade_logger.log_trade(make_trade(strategy_id="strat_scalp", gross_pnl=-30.0))

        # Get P&L for strat_orb only
        orb_pnl = await trade_logger.get_daily_pnl(strategy_id="strat_orb")

        assert len(orb_pnl) == 1
        # Net P&L = (100-1) + (50-1) = 99 + 49 = 148
        assert orb_pnl[0]["pnl"] == 148.0
        assert orb_pnl[0]["trades"] == 2

        # Get P&L for strat_scalp only
        scalp_pnl = await trade_logger.get_daily_pnl(strategy_id="strat_scalp")

        assert len(scalp_pnl) == 1
        # Net P&L = -30 - 1 = -31
        assert scalp_pnl[0]["pnl"] == -31.0
        assert scalp_pnl[0]["trades"] == 1

    async def test_log_orchestrator_decision(
        self, trade_logger: TradeLogger, db: DatabaseManager
    ) -> None:
        """log_orchestrator_decision saves decision to database."""
        decision_id = await trade_logger.log_orchestrator_decision(
            date="2026-02-24",
            decision_type="allocation",
            strategy_id="strat_orb",
            details={"allocation_pct": 0.4, "reason": "equal weight"},
            rationale="Pre-market allocation",
        )

        assert len(decision_id) == 26  # ULID

        # Verify it was saved
        row = await db.fetch_one(
            "SELECT * FROM orchestrator_decisions WHERE id = ?", (decision_id,)
        )
        assert row is not None
        assert row["decision_type"] == "allocation"
        assert row["strategy_id"] == "strat_orb"
        assert row["date"] == "2026-02-24"
        assert row["rationale"] == "Pre-market allocation"

    async def test_log_orchestrator_decision_system_wide(
        self, trade_logger: TradeLogger, db: DatabaseManager
    ) -> None:
        """log_orchestrator_decision works with None strategy_id for system-wide decisions."""
        decision_id = await trade_logger.log_orchestrator_decision(
            date="2026-02-24",
            decision_type="eod_review",
            strategy_id=None,
            details={"regime": "bullish_trending"},
            rationale="End of day review",
        )

        assert len(decision_id) == 26  # ULID

        # Verify it was saved
        row = await db.fetch_one(
            "SELECT * FROM orchestrator_decisions WHERE id = ?", (decision_id,)
        )
        assert row is not None
        assert row["decision_type"] == "eod_review"
        assert row["strategy_id"] is None


class TestF05LogTruncationWidth:
    """Apr 21 debrief F-05 (IMPROMPTU-07 regression): widen ULID log-
    truncation from 8 chars to 12 chars.

    Context: every trade ULID emitted by ``log_trade`` and every decision
    ULID emitted by ``log_orchestrator_decision`` was truncated to 8
    chars in the log line. ULIDs encode the timestamp in the first ~10
    chars of Crockford base32, so 8-char prefixes collide routinely on
    trades from the same second — producing spurious "duplicate
    trade_id" confusion during session debugging. 12 chars includes the
    full timestamp half plus ~2 random chars and is collision-free in
    practice.
    """

    async def test_log_trade_emits_12_char_ulid_prefix(
        self, trade_logger: TradeLogger, caplog
    ) -> None:
        """The 'Logged trade X' INFO line contains the first 12 chars of
        the trade ULID (not 8). Revert-proof: trade.id[:8] would fail
        this assertion on any ULID whose first 12 chars contain a char
        absent from the first 8 — which is ~every ULID."""
        import logging

        caplog.set_level(logging.INFO, logger="argus.analytics.trade_logger")
        trade = make_trade()
        await trade_logger.log_trade(trade)

        log_lines = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == "argus.analytics.trade_logger"
            and "Logged trade" in rec.getMessage()
        ]
        assert len(log_lines) == 1, f"Expected 1 'Logged trade' log, got {log_lines}"
        logged = log_lines[0]

        # The 12-char prefix must appear; 8-char prefix alone without the
        # extra 4 chars would indicate regression back to the F-05 bug.
        prefix_12 = trade.id[:12]
        assert prefix_12 in logged, (
            f"F-05 regression: log line should contain trade.id[:12]="
            f"{prefix_12!r}; got: {logged!r}"
        )

    async def test_log_orchestrator_decision_emits_12_char_ulid_prefix(
        self, trade_logger: TradeLogger, caplog
    ) -> None:
        """Same 12-char prefix width for orchestrator-decision logs."""
        import logging

        caplog.set_level(logging.DEBUG, logger="argus.analytics.trade_logger")
        decision_id = await trade_logger.log_orchestrator_decision(
            date="2026-04-23",
            decision_type="allocation",
            strategy_id="strat_orb",
            details={"reason": "pre-market"},
            rationale="Test",
        )

        log_lines = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == "argus.analytics.trade_logger"
            and "orchestrator decision" in rec.getMessage()
        ]
        assert len(log_lines) == 1, f"Expected 1 decision log, got {log_lines}"
        logged = log_lines[0]

        prefix_12 = decision_id[:12]
        assert prefix_12 in logged, (
            f"F-05 regression: log line should contain decision_id[:12]="
            f"{prefix_12!r}; got: {logged!r}"
        )
