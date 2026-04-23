"""Sprint 4a Integration Test.

Simplified integration test verifying the core signal→risk→broker flow
with Sprint 4a components (AlpacaBroker). AlpacaDataService is tested
separately in its unit tests.

All alpaca-py clients are mocked. No network calls.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    AccountRiskConfig,
    AlpacaConfig,
    RiskConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import OrderApprovedEvent, OrderFilledEvent, SignalEvent
from argus.core.risk_manager import RiskManager
from argus.execution.alpaca_broker import AlpacaBroker
from argus.execution.simulated_broker import SimulatedBroker
from argus.models.trading import Order, OrderSide, OrderType


@pytest.fixture
def mock_trading_client() -> Mock:
    """Create a mock TradingClient for testing."""
    client = Mock()

    # Mock submit_order to return an order with ID
    mock_order = Mock()
    mock_order.id = "alpaca-order-123"
    client.submit_order = Mock(return_value=mock_order)

    client.cancel_order_by_id = Mock()
    client.replace_order_by_id = Mock()
    client.get_all_positions = Mock(return_value=[])

    # Mock account
    mock_account = Mock()
    mock_account.equity = "100000.0"
    mock_account.cash = "100000.0"
    mock_account.buying_power = "200000.0"
    mock_account.last_equity = "100000.0"
    client.get_account = Mock(return_value=mock_account)

    client.get_order_by_id = Mock()
    client.close_all_positions = Mock(return_value=[])
    client.cancel_orders = Mock()
    return client


@pytest.fixture
def mock_trading_stream() -> Mock:
    """Create a mock TradingStream for testing."""
    stream = Mock()
    stream.subscribe_trade_updates = Mock()
    stream.close = AsyncMock()
    stream._run_forever = AsyncMock()
    return stream


class TestSprint4aIntegration:
    """Integration tests for Sprint 4a components."""

    @pytest.mark.asyncio
    async def test_signal_to_broker_pipeline(
        self,
        mock_trading_client: Mock,
        mock_trading_stream: Mock,
    ) -> None:
        """Test signal→risk→broker flow with AlpacaBroker.

        Verifies:
        1. SignalEvent created manually
        2. RiskManager evaluates and approves signal
        3. AlpacaBroker receives approved order and calls TradingClient.submit_order()
        4. Trade update from TradingStream triggers OrderFilledEvent
        """
        # Set up environment variables
        os.environ["TEST_ALPACA_API_KEY"] = "test_key"
        os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

        try:
            # Create components
            event_bus = EventBus()
            clock = FixedClock(datetime(2026, 2, 15, 10, 0, tzinfo=UTC))

            # SimulatedBroker for RiskManager account queries
            simulated_broker = SimulatedBroker(initial_cash=100_000)
            await simulated_broker.connect()

            # AlpacaBroker with mocked clients
            alpaca_config = AlpacaConfig(
                enabled=True,
                api_key_env="TEST_ALPACA_API_KEY",
                secret_key_env="TEST_ALPACA_SECRET_KEY",
                paper=True,
            )

            with (
                patch(
                    "argus.execution.alpaca_broker.TradingClient",
                    return_value=mock_trading_client,
                ),
                patch(
                    "argus.execution.alpaca_broker.TradingStream",
                    return_value=mock_trading_stream,
                ),
            ):
                alpaca_broker = AlpacaBroker(event_bus=event_bus, config=alpaca_config)
                await alpaca_broker.connect()

            # RiskManager
            risk_config = RiskConfig(
                account=AccountRiskConfig(
                    daily_loss_limit_pct=0.03,
                    weekly_loss_limit_pct=0.05,
                    cash_reserve_pct=0.20,
                    max_concurrent_positions=10,
                ),
            )
            risk_manager = RiskManager(
                config=risk_config,
                broker=simulated_broker,
                event_bus=event_bus,
                clock=clock,
            )
            await risk_manager.initialize()
            await risk_manager.reset_daily_state()

            # Create a test signal
            signal = SignalEvent(
                timestamp=clock.now(),
                strategy_id="test_strategy",
                symbol="AAPL",
                entry_price=150.0,
                stop_price=148.0,
                target_prices=(154.0, 156.0),
                share_count=100,
                rationale="Test breakout signal",
            )

            # Track fills
            fills: list[OrderFilledEvent] = []

            async def handle_fill(fill: OrderFilledEvent) -> None:
                fills.append(fill)

            event_bus.subscribe(OrderFilledEvent, handle_fill)

            # Evaluate signal through RiskManager
            result = await risk_manager.evaluate_signal(signal)

            # Verify signal was approved
            assert isinstance(result, OrderApprovedEvent)
            assert result.signal is not None
            assert result.signal.symbol == "AAPL"

            # Create order from approved signal
            order = Order(
                strategy_id=result.signal.strategy_id,
                symbol=result.signal.symbol,
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=result.signal.share_count,
            )

            # Place order through AlpacaBroker
            order_result = await alpaca_broker.place_order(order)

            # Verify order was submitted to TradingClient
            assert mock_trading_client.submit_order.called
            assert order_result.broker_order_id == "alpaca-order-123"

            # Verify order ID mapping stored
            assert len(alpaca_broker._order_id_map) == 1
            our_order_id = order.id
            assert alpaca_broker._order_id_map[our_order_id] == "alpaca-order-123"

            # Simulate fill event from TradingStream
            mock_update = Mock()
            mock_update.event = "fill"
            mock_update.order = Mock()
            mock_update.order.id = "alpaca-order-123"
            mock_update.order.symbol = "AAPL"
            mock_update.order.filled_qty = "100"
            mock_update.order.filled_avg_price = "150.0"

            await alpaca_broker._on_trade_update(mock_update)
            await event_bus.drain()
            await asyncio.sleep(0.01)

            # Verify fill event was published
            assert len(fills) == 1
            fill = fills[0]
            assert fill.order_id == our_order_id
            assert fill.fill_price == pytest.approx(150.0)
            assert fill.fill_quantity == 100

            # Cleanup
            await alpaca_broker.disconnect()
            await simulated_broker.disconnect()

        finally:
            # Clean up environment variables
            if "TEST_ALPACA_API_KEY" in os.environ:
                del os.environ["TEST_ALPACA_API_KEY"]
            if "TEST_ALPACA_SECRET_KEY" in os.environ:
                del os.environ["TEST_ALPACA_SECRET_KEY"]

    @pytest.mark.asyncio
    async def test_bracket_order_through_alpaca_broker(
        self,
        mock_trading_client: Mock,
        mock_trading_stream: Mock,
    ) -> None:
        """Test that bracket orders can be placed through AlpacaBroker."""
        os.environ["TEST_ALPACA_API_KEY"] = "test_key"
        os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

        try:
            event_bus = EventBus()

            alpaca_config = AlpacaConfig(
                enabled=True,
                api_key_env="TEST_ALPACA_API_KEY",
                secret_key_env="TEST_ALPACA_SECRET_KEY",
                paper=True,
            )

            # Mock bracket order response
            mock_order = Mock()
            mock_order.id = "alpaca-bracket-456"
            mock_trading_client.submit_order.return_value = mock_order

            with (
                patch(
                    "argus.execution.alpaca_broker.TradingClient",
                    return_value=mock_trading_client,
                ),
                patch(
                    "argus.execution.alpaca_broker.TradingStream",
                    return_value=mock_trading_stream,
                ),
            ):
                alpaca_broker = AlpacaBroker(event_bus=event_bus, config=alpaca_config)
                await alpaca_broker.connect()

            # Create bracket order components
            entry = Order(
                strategy_id="test_strategy",
                symbol="TSLA",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=50,
            )
            stop = Order(
                strategy_id="test_strategy",
                symbol="TSLA",
                side=OrderSide.SELL,
                order_type=OrderType.STOP,
                quantity=50,
                stop_price=245.0,
            )
            targets = [
                Order(
                    strategy_id="test_strategy",
                    symbol="TSLA",
                    side=OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    quantity=25,
                    limit_price=255.0,
                )
            ]

            # Place bracket order
            result = await alpaca_broker.place_bracket_order(entry, stop, targets)

            # Verify bracket order submitted
            assert mock_trading_client.submit_order.called
            assert result.entry.broker_order_id == "alpaca-bracket-456"
            assert result.stop.status.value == "submitted"
            assert result.targets[0].status.value == "submitted"

            await alpaca_broker.disconnect()

        finally:
            if "TEST_ALPACA_API_KEY" in os.environ:
                del os.environ["TEST_ALPACA_API_KEY"]
            if "TEST_ALPACA_SECRET_KEY" in os.environ:
                del os.environ["TEST_ALPACA_SECRET_KEY"]
