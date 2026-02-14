"""Sprint 2 Integration Tests.

End-to-end flow test:
SignalEvent → RiskManager.evaluate_signal() → OrderApprovedEvent/OrderRejectedEvent
  → SimulatedBroker.place_order() → OrderFilledEvent
  → TradeLogger.log_trade()
"""

from datetime import datetime
from pathlib import Path

import pytest

from argus.analytics.trade_logger import TradeLogger
from argus.core.config import (
    AccountRiskConfig,
    AccountType,
    CrossStrategyRiskConfig,
    PDTConfig,
    RiskConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    Side,
    SignalEvent,
)
from argus.core.risk_manager import RiskManager
from argus.db.manager import DatabaseManager
from argus.execution.simulated_broker import SimulatedBroker
from argus.models.trading import (
    ExitReason,
    Order,
    OrderSide,
    OrderStatus,
    Trade,
)


def make_signal(
    symbol: str = "AAPL",
    side: Side = Side.LONG,
    entry_price: float = 150.0,
    stop_price: float = 147.0,
    share_count: int = 100,
    strategy_id: str = "strat_orb_breakout",
    target_prices: tuple[float, ...] | None = None,
) -> SignalEvent:
    """Create a SignalEvent for testing."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices or (153.0, 156.0),
        share_count=share_count,
        rationale="Test signal",
    )


def make_risk_config(
    daily_loss_limit_pct: float = 0.03,
    weekly_loss_limit_pct: float = 0.05,
    cash_reserve_pct: float = 0.20,
    max_concurrent_positions: int = 10,
) -> RiskConfig:
    """Create a RiskConfig for testing."""
    return RiskConfig(
        account=AccountRiskConfig(
            daily_loss_limit_pct=daily_loss_limit_pct,
            weekly_loss_limit_pct=weekly_loss_limit_pct,
            cash_reserve_pct=cash_reserve_pct,
            max_concurrent_positions=max_concurrent_positions,
        ),
        cross_strategy=CrossStrategyRiskConfig(),
        pdt=PDTConfig(
            enabled=True,
            account_type=AccountType.MARGIN,
            threshold_balance=25000.0,
        ),
    )


class TestEndToEndFlow:
    """Integration tests for the full signal-to-trade flow."""

    @pytest.mark.asyncio
    async def test_signal_to_fill_happy_path(self, tmp_path: Path) -> None:
        """Complete flow: signal → approval → order → fill."""
        # Setup components
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Create signal
        signal = make_signal(
            symbol="AAPL",
            share_count=100,
            entry_price=150.0,
            stop_price=147.0,
        )

        # Evaluate signal
        result = await rm.evaluate_signal(signal)
        assert isinstance(result, OrderApprovedEvent)
        assert result.modifications is None

        # Place order based on approval
        order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.BUY,
            quantity=signal.share_count,
            limit_price=signal.entry_price,
        )
        fill_result = await broker.place_order(order)

        assert fill_result.status == OrderStatus.FILLED
        assert fill_result.filled_quantity == 100
        assert fill_result.filled_avg_price == 150.0

        # Verify position exists
        positions = await broker.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_signal_to_fill_with_modification(self) -> None:
        """Flow with share count modification due to cash reserve."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Signal wants too many shares
        signal = make_signal(
            symbol="AAPL",
            share_count=600,  # 600 * 150 = 90K, but only 80K available after reserve
            entry_price=150.0,
            stop_price=147.0,
        )

        result = await rm.evaluate_signal(signal)
        assert isinstance(result, OrderApprovedEvent)
        assert result.modifications is not None
        modified_shares = result.modifications["share_count"]
        assert modified_shares == 533  # int(80000/150)

        # Place order with modified shares
        order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.BUY,
            quantity=modified_shares,
            limit_price=signal.entry_price,
        )
        fill_result = await broker.place_order(order)

        assert fill_result.status == OrderStatus.FILLED
        assert fill_result.filled_quantity == 533

    @pytest.mark.asyncio
    async def test_signal_rejection_stops_flow(self) -> None:
        """Rejected signal should not result in any order."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Trigger circuit breaker
        rm._circuit_breaker_active = True

        signal = make_signal()
        result = await rm.evaluate_signal(signal)

        assert isinstance(result, OrderRejectedEvent)
        assert "circuit breaker" in result.reason.lower()

        # No orders should be placed
        positions = await broker.get_positions()
        assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_full_trade_cycle_with_trade_logger(self, tmp_path: Path) -> None:
        """Complete trade cycle: entry → exit → logged."""
        # Setup database and trade logger
        db = DatabaseManager(tmp_path / "test.db")
        await db.initialize()
        trade_logger = TradeLogger(db)

        # Setup broker and risk manager
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Entry
        signal = make_signal(
            symbol="AAPL",
            share_count=100,
            entry_price=150.0,
            stop_price=147.0,
        )
        approval = await rm.evaluate_signal(signal)
        assert isinstance(approval, OrderApprovedEvent)

        entry_order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.BUY,
            quantity=signal.share_count,
            limit_price=signal.entry_price,
        )
        entry_time = datetime.utcnow()
        entry_fill = await broker.place_order(entry_order)
        assert entry_fill.status == OrderStatus.FILLED

        # Exit (profit)
        exit_order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.SELL,
            quantity=signal.share_count,
            limit_price=155.0,
        )
        exit_fill = await broker.place_order(exit_order)
        assert exit_fill.status == OrderStatus.FILLED

        # Log the trade
        trade = Trade(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.BUY,
            entry_price=entry_fill.filled_avg_price,
            entry_time=entry_time,
            exit_price=exit_fill.filled_avg_price,
            exit_time=datetime.utcnow(),
            shares=signal.share_count,
            stop_price=signal.stop_price,
            target_prices=list(signal.target_prices),
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=500.0,  # (155 - 150) * 100
        )
        trade_id = await trade_logger.log_trade(trade)

        # Verify trade was logged
        retrieved = await trade_logger.get_trade(trade_id)
        assert retrieved is not None
        assert retrieved.symbol == "AAPL"
        assert retrieved.gross_pnl == 500.0

        # Publish position closed event to update risk manager
        event = PositionClosedEvent(
            position_id="test",
            exit_price=155.0,
            realized_pnl=500.0,
            entry_time=entry_time,
            exit_time=datetime.utcnow(),
        )
        await bus.publish(event)
        await bus.drain()

        # Verify risk manager tracked the P&L
        assert rm.daily_realized_pnl == 500.0

        await db.close()

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_subsequent_signals(self) -> None:
        """After circuit breaker triggers, all signals should be rejected."""
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config(daily_loss_limit_pct=0.03)

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Set daily loss at limit
        rm._daily_realized_pnl = -3000.0  # 3% of 100K

        # First signal triggers circuit breaker
        signal1 = make_signal(symbol="AAPL")
        result1 = await rm.evaluate_signal(signal1)
        assert isinstance(result1, OrderRejectedEvent)
        assert rm.circuit_breaker_active is True

        # Second signal should also be rejected
        signal2 = make_signal(symbol="TSLA")
        result2 = await rm.evaluate_signal(signal2)
        assert isinstance(result2, OrderRejectedEvent)
        assert "circuit breaker" in result2.reason.lower()

    @pytest.mark.asyncio
    async def test_multiple_positions_concurrent_limit(self) -> None:
        """Should reject new signals when at max concurrent positions."""
        broker = SimulatedBroker(initial_cash=500_000)
        await broker.connect()
        bus = EventBus()
        config = make_risk_config()

        rm = RiskManager(config=config, broker=broker, event_bus=bus)
        await rm.initialize()

        # Fill up to max positions
        symbols = ["AAPL", "TSLA", "GOOG", "META", "AMZN", "MSFT", "NVDA", "AMD", "INTC", "CRM"]
        for symbol in symbols:
            signal = make_signal(symbol=symbol, share_count=10, entry_price=100.0)
            result = await rm.evaluate_signal(signal)
            assert isinstance(result, OrderApprovedEvent)

            order = Order(
                strategy_id=signal.strategy_id,
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=10,
                limit_price=100.0,
            )
            await broker.place_order(order)

        # Now at max positions (10)
        positions = await broker.get_positions()
        assert len(positions) == 10

        # Next signal should be rejected
        signal = make_signal(symbol="ORCL", share_count=10)
        result = await rm.evaluate_signal(signal)
        assert isinstance(result, OrderRejectedEvent)
        assert "concurrent positions" in result.reason.lower()
