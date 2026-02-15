"""Tests for AlpacaBroker.

All tests use mocked alpaca-py clients. No network calls are made.
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from argus.core.config import AlpacaConfig
from argus.core.event_bus import EventBus
from argus.core.events import OrderCancelledEvent, OrderFilledEvent
from argus.execution.alpaca_broker import AlpacaBroker
from argus.models.trading import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)


@pytest.fixture
def event_bus() -> EventBus:
    """Create an Event Bus for testing."""
    return EventBus()


@pytest.fixture
def alpaca_config() -> AlpacaConfig:
    """Create test Alpaca config."""
    return AlpacaConfig(
        enabled=True,
        api_key_env="TEST_ALPACA_API_KEY",
        secret_key_env="TEST_ALPACA_SECRET_KEY",
        paper=True,
    )


@pytest.fixture
def mock_trading_client() -> Mock:
    """Create a mock TradingClient."""
    client = Mock()
    client.submit_order = Mock()
    client.cancel_order_by_id = Mock()
    client.replace_order_by_id = Mock()
    client.get_all_positions = Mock(return_value=[])
    client.get_account = Mock()
    client.get_order_by_id = Mock()
    client.close_all_positions = Mock(return_value=[])
    client.cancel_orders = Mock()
    return client


@pytest.fixture
def mock_trading_stream() -> Mock:
    """Create a mock TradingStream."""
    stream = Mock()
    stream.subscribe_trade_updates = Mock()
    stream.close = AsyncMock()
    stream._run_forever = AsyncMock()
    return stream


@pytest.fixture
async def broker(
    event_bus: EventBus,
    alpaca_config: AlpacaConfig,
    mock_trading_client: Mock,
    mock_trading_stream: Mock,
) -> AlpacaBroker:
    """Create AlpacaBroker with mocked clients."""
    broker = AlpacaBroker(event_bus, alpaca_config)

    # Set environment variables for API keys
    os.environ["TEST_ALPACA_API_KEY"] = "test_api_key"
    os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret_key"

    # Inject mocked clients
    with (
        patch("argus.execution.alpaca_broker.TradingClient", return_value=mock_trading_client),
        patch("argus.execution.alpaca_broker.TradingStream", return_value=mock_trading_stream),
    ):
        await broker.connect()

    yield broker

    # Cleanup
    await broker.disconnect()
    del os.environ["TEST_ALPACA_API_KEY"]
    del os.environ["TEST_ALPACA_SECRET_KEY"]


# ---------------------------------------------------------------------------
# Connection Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_initializes_clients(
    event_bus: EventBus,
    alpaca_config: AlpacaConfig,
    mock_trading_client: Mock,
    mock_trading_stream: Mock,
) -> None:
    """Test that connect() initializes TradingClient and TradingStream."""
    broker = AlpacaBroker(event_bus, alpaca_config)
    os.environ["TEST_ALPACA_API_KEY"] = "test_api_key"
    os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret_key"

    with (
        patch(
            "argus.execution.alpaca_broker.TradingClient", return_value=mock_trading_client
        ) as client_cls,
        patch(
            "argus.execution.alpaca_broker.TradingStream", return_value=mock_trading_stream
        ) as stream_cls,
    ):
        await broker.connect()

        # Verify TradingClient initialized with correct params
        client_cls.assert_called_once_with(
            api_key="test_api_key",
            secret_key="test_secret_key",
            paper=True,
        )

        # Verify TradingStream initialized with correct params
        stream_cls.assert_called_once_with(
            api_key="test_api_key",
            secret_key="test_secret_key",
            paper=True,
        )

        # Verify trade updates subscription
        mock_trading_stream.subscribe_trade_updates.assert_called_once()

    await broker.disconnect()
    del os.environ["TEST_ALPACA_API_KEY"]
    del os.environ["TEST_ALPACA_SECRET_KEY"]


@pytest.mark.asyncio
async def test_connect_fails_without_api_keys(
    event_bus: EventBus,
    alpaca_config: AlpacaConfig,
) -> None:
    """Test that connect() raises ConnectionError if API keys are missing."""
    broker = AlpacaBroker(event_bus, alpaca_config)

    # Ensure env vars are not set
    if "TEST_ALPACA_API_KEY" in os.environ:
        del os.environ["TEST_ALPACA_API_KEY"]
    if "TEST_ALPACA_SECRET_KEY" in os.environ:
        del os.environ["TEST_ALPACA_SECRET_KEY"]

    with pytest.raises(ConnectionError, match="API keys not found"):
        await broker.connect()


@pytest.mark.asyncio
async def test_disconnect_closes_stream(
    event_bus: EventBus,
    alpaca_config: AlpacaConfig,
    mock_trading_client: Mock,
    mock_trading_stream: Mock,
) -> None:
    """Test that disconnect() closes the WebSocket stream."""
    broker = AlpacaBroker(event_bus, alpaca_config)
    os.environ["TEST_ALPACA_API_KEY"] = "test_api_key"
    os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret_key"

    with (
        patch("argus.execution.alpaca_broker.TradingClient", return_value=mock_trading_client),
        patch("argus.execution.alpaca_broker.TradingStream", return_value=mock_trading_stream),
    ):
        await broker.connect()
        await asyncio.sleep(0.1)  # Let stream task start
        await broker.disconnect()

        # Verify stream closed
        mock_trading_stream.close.assert_called_once()

    del os.environ["TEST_ALPACA_API_KEY"]
    del os.environ["TEST_ALPACA_SECRET_KEY"]


# ---------------------------------------------------------------------------
# Place Order Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_market_order(broker: AlpacaBroker) -> None:
    """Test placing a market order."""
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )

    # Mock Alpaca response
    mock_order = Mock()
    mock_order.id = "alpaca-order-123"
    broker._trading_client.submit_order.return_value = mock_order

    result = await broker.place_order(order)

    # Verify order submitted to Alpaca
    broker._trading_client.submit_order.assert_called_once()
    call_args = broker._trading_client.submit_order.call_args[0][0]
    assert call_args.symbol == "AAPL"
    assert call_args.qty == 100
    assert str(call_args.side) == "OrderSide.BUY"
    assert str(call_args.time_in_force) == "TimeInForce.DAY"

    # Verify result
    assert result.order_id == order.id
    assert result.broker_order_id == "alpaca-order-123"
    assert result.status == OrderStatus.SUBMITTED

    # Verify order ID mapping stored
    assert broker._order_id_map[order.id] == "alpaca-order-123"
    assert broker._reverse_id_map["alpaca-order-123"] == order.id


@pytest.mark.asyncio
async def test_place_limit_order(broker: AlpacaBroker) -> None:
    """Test placing a limit order."""
    order = Order(
        strategy_id="test_strategy",
        symbol="TSLA",
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity=50,
        limit_price=250.0,
    )

    # Mock Alpaca response
    mock_order = Mock()
    mock_order.id = "alpaca-order-456"
    broker._trading_client.submit_order.return_value = mock_order

    result = await broker.place_order(order)

    # Verify limit order submitted
    broker._trading_client.submit_order.assert_called_once()
    call_args = broker._trading_client.submit_order.call_args[0][0]
    assert call_args.symbol == "TSLA"
    assert call_args.qty == 50
    assert str(call_args.side) == "OrderSide.SELL"
    assert call_args.limit_price == 250.0

    assert result.status == OrderStatus.SUBMITTED


@pytest.mark.asyncio
async def test_place_stop_order(broker: AlpacaBroker) -> None:
    """Test placing a stop order."""
    order = Order(
        strategy_id="test_strategy",
        symbol="SPY",
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        quantity=100,
        stop_price=450.0,
    )

    # Mock Alpaca response
    mock_order = Mock()
    mock_order.id = "alpaca-order-789"
    broker._trading_client.submit_order.return_value = mock_order

    result = await broker.place_order(order)

    # Verify stop order submitted
    broker._trading_client.submit_order.assert_called_once()
    call_args = broker._trading_client.submit_order.call_args[0][0]
    assert call_args.symbol == "SPY"
    assert call_args.qty == 100
    assert call_args.stop_price == 450.0

    assert result.status == OrderStatus.SUBMITTED


@pytest.mark.asyncio
async def test_place_bracket_order(broker: AlpacaBroker) -> None:
    """Test placing a bracket order (entry + stop + target)."""
    entry = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )
    stop = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        quantity=100,
        stop_price=145.0,
    )
    targets = [
        Order(
            strategy_id="test_strategy",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            limit_price=155.0,
        ),
        Order(
            strategy_id="test_strategy",
            symbol="AAPL",
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=50,
            limit_price=160.0,
        ),
    ]

    # Mock Alpaca response
    mock_order = Mock()
    mock_order.id = "alpaca-bracket-123"
    broker._trading_client.submit_order.return_value = mock_order

    result = await broker.place_bracket_order(entry, stop, targets)

    # Verify bracket order submitted
    broker._trading_client.submit_order.assert_called_once()
    call_args = broker._trading_client.submit_order.call_args[0][0]
    assert call_args.symbol == "AAPL"
    assert call_args.qty == 100
    assert str(call_args.order_class) == "OrderClass.BRACKET"
    # take_profit and stop_loss are converted to Request objects by alpaca-py
    # Check the dict values we passed in
    assert hasattr(call_args, "take_profit")
    assert hasattr(call_args, "stop_loss")

    # Verify results
    assert result.entry.status == OrderStatus.SUBMITTED
    assert result.stop.status == OrderStatus.SUBMITTED
    assert result.targets[0].status == OrderStatus.SUBMITTED
    assert result.targets[1].status == OrderStatus.REJECTED  # T2 ignored


@pytest.mark.asyncio
async def test_place_order_rejects_on_exception(broker: AlpacaBroker) -> None:
    """Test that place_order returns rejection on Alpaca API error."""
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )

    # Mock Alpaca API error
    broker._trading_client.submit_order.side_effect = Exception("API error")

    result = await broker.place_order(order)

    assert result.status == OrderStatus.REJECTED
    assert "API error" in result.message


# ---------------------------------------------------------------------------
# Cancel/Modify Order Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_order(broker: AlpacaBroker) -> None:
    """Test cancelling an order."""
    # First place an order to get it in the ID map
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )
    mock_order = Mock()
    mock_order.id = "alpaca-order-999"
    broker._trading_client.submit_order.return_value = mock_order
    await broker.place_order(order)

    # Now cancel it
    success = await broker.cancel_order(order.id)

    # Verify cancel called with Alpaca order ID
    broker._trading_client.cancel_order_by_id.assert_called_once_with("alpaca-order-999")
    assert success is True


@pytest.mark.asyncio
async def test_cancel_unknown_order_fails(broker: AlpacaBroker) -> None:
    """Test that cancelling an unknown order fails."""
    success = await broker.cancel_order("unknown-order-id")
    assert success is False


@pytest.mark.asyncio
async def test_modify_order(broker: AlpacaBroker) -> None:
    """Test modifying an order."""
    # First place an order
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=100,
        limit_price=150.0,
    )
    mock_order = Mock()
    mock_order.id = "alpaca-order-111"
    broker._trading_client.submit_order.return_value = mock_order
    await broker.place_order(order)

    # Mock replace response
    new_mock_order = Mock()
    new_mock_order.id = "alpaca-order-222"
    broker._trading_client.replace_order_by_id.return_value = new_mock_order

    # Modify it
    modifications = {"limit_price": 155.0}
    result = await broker.modify_order(order.id, modifications)

    # Verify replace called
    broker._trading_client.replace_order_by_id.assert_called_once()
    assert result.status == OrderStatus.SUBMITTED
    assert result.broker_order_id == "alpaca-order-222"

    # Verify ID mapping updated
    assert broker._order_id_map[order.id] == "alpaca-order-222"
    assert broker._reverse_id_map["alpaca-order-222"] == order.id
    assert "alpaca-order-111" not in broker._reverse_id_map


# ---------------------------------------------------------------------------
# Get Positions/Account Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_positions(broker: AlpacaBroker) -> None:
    """Test getting positions."""
    # Mock Alpaca positions
    mock_pos1 = Mock()
    mock_pos1.symbol = "AAPL"
    mock_pos1.qty = "100"
    mock_pos1.avg_entry_price = "150.0"
    mock_pos1.current_price = "155.0"
    mock_pos1.unrealized_pl = "500.0"

    mock_pos2 = Mock()
    mock_pos2.symbol = "TSLA"
    mock_pos2.qty = "-50"
    mock_pos2.avg_entry_price = "250.0"
    mock_pos2.current_price = "245.0"
    mock_pos2.unrealized_pl = "250.0"

    broker._trading_client.get_all_positions.return_value = [mock_pos1, mock_pos2]

    positions = await broker.get_positions()

    assert len(positions) == 2
    assert positions[0].symbol == "AAPL"
    assert positions[0].shares == 100
    assert positions[0].side == OrderSide.BUY
    assert positions[0].entry_price == 150.0
    assert positions[0].current_price == 155.0
    assert positions[0].unrealized_pnl == 500.0

    assert positions[1].symbol == "TSLA"
    assert positions[1].shares == 50
    assert positions[1].side == OrderSide.SELL
    assert positions[1].entry_price == 250.0


@pytest.mark.asyncio
async def test_get_account(broker: AlpacaBroker) -> None:
    """Test getting account info."""
    # Mock Alpaca account
    mock_account = Mock()
    mock_account.equity = "100000.0"
    mock_account.cash = "50000.0"
    mock_account.buying_power = "200000.0"
    mock_account.last_equity = "99000.0"

    broker._trading_client.get_account.return_value = mock_account

    account = await broker.get_account()

    assert account.equity == 100000.0
    assert account.cash == 50000.0
    assert account.buying_power == 200000.0
    assert account.positions_value == 50000.0  # equity - cash
    assert account.daily_pnl == 1000.0  # 100000 - 99000


# ---------------------------------------------------------------------------
# Get Order Status Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_order_status(broker: AlpacaBroker) -> None:
    """Test getting order status."""
    # First place an order
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )
    mock_order = Mock()
    mock_order.id = "alpaca-order-333"
    broker._trading_client.submit_order.return_value = mock_order
    await broker.place_order(order)

    # Mock get order status
    mock_order.status = "filled"
    broker._trading_client.get_order_by_id.return_value = mock_order

    status = await broker.get_order_status(order.id)

    broker._trading_client.get_order_by_id.assert_called_once_with("alpaca-order-333")
    assert status == OrderStatus.FILLED


@pytest.mark.asyncio
async def test_get_order_status_raises_on_unknown_order(broker: AlpacaBroker) -> None:
    """Test that get_order_status raises KeyError for unknown order."""
    with pytest.raises(KeyError, match="not found in ID map"):
        await broker.get_order_status("unknown-order-id")


# ---------------------------------------------------------------------------
# Flatten All Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flatten_all(broker: AlpacaBroker) -> None:
    """Test emergency flatten."""
    # Mock close responses
    mock_close1 = Mock()
    mock_close1.symbol = "AAPL"
    mock_close1.id = "close-order-1"

    mock_close2 = Mock()
    mock_close2.symbol = "TSLA"
    mock_close2.id = "close-order-2"

    broker._trading_client.close_all_positions.return_value = [mock_close1, mock_close2]

    results = await broker.flatten_all()

    # Verify cancel orders called first
    broker._trading_client.cancel_orders.assert_called_once()

    # Verify close all positions called
    broker._trading_client.close_all_positions.assert_called_once_with(cancel_orders=True)

    # Verify results
    assert len(results) == 2
    assert all(r.status == OrderStatus.SUBMITTED for r in results)
    assert "Emergency flatten" in results[0].message


# ---------------------------------------------------------------------------
# Trade Update Handler Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_trade_update_fill_event(broker: AlpacaBroker) -> None:
    """Test that trade update handler publishes OrderFilledEvent on fill."""
    # Place an order first
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )
    mock_order = Mock()
    mock_order.id = "alpaca-order-444"
    broker._trading_client.submit_order.return_value = mock_order
    await broker.place_order(order)

    # Mock fill trade update
    mock_update = Mock()
    mock_update.event = "fill"
    mock_update.order = Mock()
    mock_update.order.id = "alpaca-order-444"
    mock_update.order.symbol = "AAPL"
    mock_update.order.side = "buy"
    mock_update.order.order_type = "market"
    mock_update.order.filled_qty = "100"
    mock_update.order.filled_avg_price = "150.5"

    # Subscribe to OrderFilledEvent
    received_events = []

    async def handler(event: OrderFilledEvent) -> None:
        received_events.append(event)

    broker._event_bus.subscribe(OrderFilledEvent, handler)

    # Trigger trade update
    await broker._on_trade_update(mock_update)
    await asyncio.sleep(0.1)  # Let event propagate

    # Verify event published
    assert len(received_events) == 1
    event = received_events[0]
    assert event.order_id == order.id
    assert event.fill_price == 150.5
    assert event.fill_quantity == 100


@pytest.mark.asyncio
async def test_on_trade_update_cancel_event(broker: AlpacaBroker) -> None:
    """Test that trade update handler publishes OrderCancelledEvent on cancel."""
    # Place an order first
    order = Order(
        strategy_id="test_strategy",
        symbol="AAPL",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )
    mock_order = Mock()
    mock_order.id = "alpaca-order-555"
    broker._trading_client.submit_order.return_value = mock_order
    await broker.place_order(order)

    # Mock cancel trade update
    mock_update = Mock()
    mock_update.event = "canceled"
    mock_update.order = Mock()
    mock_update.order.id = "alpaca-order-555"
    mock_update.order.symbol = "AAPL"

    # Subscribe to OrderCancelledEvent
    received_events = []

    async def handler(event: OrderCancelledEvent) -> None:
        received_events.append(event)

    broker._event_bus.subscribe(OrderCancelledEvent, handler)

    # Trigger trade update
    await broker._on_trade_update(mock_update)
    await asyncio.sleep(0.1)  # Let event propagate

    # Verify event published
    assert len(received_events) == 1
    event = received_events[0]
    assert event.order_id == order.id
    assert event.reason == "canceled"


@pytest.mark.asyncio
async def test_on_trade_update_ignores_unknown_order(broker: AlpacaBroker) -> None:
    """Test that trade update for unknown order is ignored."""
    # Mock trade update for unknown order
    mock_update = Mock()
    mock_update.event = "fill"
    mock_update.order = Mock()
    mock_update.order.id = "unknown-alpaca-order"
    mock_update.order.symbol = "AAPL"

    # Should not raise, just log warning
    await broker._on_trade_update(mock_update)
