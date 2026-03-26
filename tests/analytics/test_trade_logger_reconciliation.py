"""Tests for reconciliation close trade logging.

Verifies that reconciliation closes produce valid trade records with
graceful defaults, and that normal close paths remain unchanged.
"""

from datetime import datetime

from argus.analytics.trade_logger import TradeLogger
from argus.models.trading import ExitReason, OrderSide, Trade, TradeOutcome


def _make_reconciliation_trade(
    strategy_id: str = "strat_orb",
    symbol: str = "AAPL",
    entry_price: float = 150.0,
    shares: int = 100,
) -> Trade:
    """Create a reconciliation trade with minimal data (mirrors _close_position defaults)."""
    entry_time = datetime(2026, 3, 26, 10, 0, 0)
    exit_time = datetime(2026, 3, 26, 14, 30, 0)
    return Trade(
        strategy_id=strategy_id,
        symbol=symbol,
        side=OrderSide.BUY,
        entry_price=entry_price,
        entry_time=entry_time,
        exit_price=entry_price,  # reconciliation uses entry_price as exit
        exit_time=exit_time,
        shares=shares,
        stop_price=entry_price,  # defensive default for reconciliation
        target_prices=[0.0, 0.0],
        exit_reason=ExitReason.RECONCILIATION,
        gross_pnl=0.0,
    )


class TestReconciliationTradeLogging:
    """Tests for reconciliation close trade logging."""

    async def test_reconciliation_close_produces_valid_trade_record(
        self, trade_logger: TradeLogger
    ) -> None:
        """Reconciliation close produces a valid trade record (no ERROR log)."""
        trade = _make_reconciliation_trade()
        trade_id = await trade_logger.log_trade(trade)

        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.strategy_id == "strat_orb"
        assert retrieved.exit_reason == ExitReason.RECONCILIATION

    async def test_reconciliation_trade_has_zero_pnl(
        self, trade_logger: TradeLogger
    ) -> None:
        """Reconciliation trade record has PnL=0.0 and exit_reason='reconciliation'."""
        trade = _make_reconciliation_trade()
        trade_id = await trade_logger.log_trade(trade)

        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.gross_pnl == 0.0
        assert retrieved.net_pnl == 0.0
        assert retrieved.exit_reason == ExitReason.RECONCILIATION
        assert retrieved.outcome == TradeOutcome.BREAKEVEN

    async def test_reconciliation_close_with_minimal_position_data(
        self, trade_logger: TradeLogger
    ) -> None:
        """Reconciliation close with minimal position data (only symbol + shares) succeeds."""
        trade = _make_reconciliation_trade(
            symbol="TSLA",
            shares=10,
            entry_price=200.0,
        )
        trade_id = await trade_logger.log_trade(trade)

        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.symbol == "TSLA"
        assert retrieved.shares == 10
        assert retrieved.exit_reason == ExitReason.RECONCILIATION
        assert retrieved.gross_pnl == 0.0

    async def test_normal_stop_loss_close_produces_correct_trade(
        self, trade_logger: TradeLogger
    ) -> None:
        """Normal stop_loss close still produces correct trade record with real prices."""
        trade = Trade(
            strategy_id="strat_orb",
            symbol="NVDA",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=datetime(2026, 3, 26, 10, 0, 0),
            exit_price=148.0,
            exit_time=datetime(2026, 3, 26, 10, 45, 0),
            shares=50,
            stop_price=148.0,
            target_prices=[153.0, 156.0],
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-100.0,
            commission=1.0,
        )
        trade_id = await trade_logger.log_trade(trade)

        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.exit_reason == ExitReason.STOP_LOSS
        assert retrieved.exit_price == 148.0
        assert retrieved.gross_pnl == -100.0
        assert retrieved.net_pnl == -101.0  # gross - commission
        assert retrieved.outcome == TradeOutcome.LOSS

    async def test_normal_target_1_close_produces_correct_trade(
        self, trade_logger: TradeLogger
    ) -> None:
        """Normal target_1 close still produces correct trade record."""
        trade = Trade(
            strategy_id="strat_vwap",
            symbol="MSFT",
            side=OrderSide.BUY,
            entry_price=400.0,
            entry_time=datetime(2026, 3, 26, 10, 0, 0),
            exit_price=404.0,
            exit_time=datetime(2026, 3, 26, 11, 0, 0),
            shares=25,
            stop_price=398.0,
            target_prices=[404.0, 408.0],
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=100.0,
            commission=0.50,
        )
        trade_id = await trade_logger.log_trade(trade)

        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.exit_reason == ExitReason.TARGET_1
        assert retrieved.exit_price == 404.0
        assert retrieved.gross_pnl == 100.0
        assert retrieved.net_pnl == 99.50
        assert retrieved.outcome == TradeOutcome.WIN

    async def test_reconciliation_trade_not_counted_in_daily_pnl(
        self, trade_logger: TradeLogger
    ) -> None:
        """Reconciliation trades with PnL=0 contribute nothing to daily summaries."""
        # Log a real winning trade
        real_trade = Trade(
            strategy_id="strat_orb",
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=datetime(2026, 3, 26, 10, 0, 0),
            exit_price=152.0,
            exit_time=datetime(2026, 3, 26, 10, 30, 0),
            shares=100,
            stop_price=148.0,
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=200.0,
        )
        await trade_logger.log_trade(real_trade)

        # Log a reconciliation trade (PnL=0)
        recon_trade = _make_reconciliation_trade(symbol="TSLA")
        await trade_logger.log_trade(recon_trade)

        # Daily summary should show the real trade's PnL, not polluted
        summary = await trade_logger.get_daily_summary("2026-03-26")
        assert summary.net_pnl == 200.0
        assert summary.total_trades == 2  # both counted as trades
        # Reconciliation trade is breakeven, so it goes into neither win nor loss
        assert summary.winning_trades == 1
        assert summary.losing_trades == 0

    async def test_exit_reason_reconciliation_enum_value(self) -> None:
        """ExitReason.RECONCILIATION is a valid enum member with value 'reconciliation'."""
        assert ExitReason.RECONCILIATION == "reconciliation"
        assert ExitReason.RECONCILIATION in ExitReason
