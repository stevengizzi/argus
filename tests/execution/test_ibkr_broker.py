"""Tests for IBKRBroker adapter.

Tests cover connection management, order submission, fill streaming,
cancel/modify, account queries, and flatten operations.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.config import IBKRConfig
from argus.core.event_bus import EventBus
from argus.execution.ibkr_broker import IBKRBroker

if TYPE_CHECKING:
    from ib_async import Order as IBOrder
    from ib_async import Stock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class MockEvent:
    """Mock event object that tracks += subscriptions."""

    def __init__(self) -> None:
        self.handlers: list = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


@pytest.fixture
def mock_ib() -> MagicMock:
    """Create a mock ib_async.IB instance with standard behavior.

    The mock simulates:
    - Connection methods (connectAsync, disconnect, isConnected)
    - Account data (managedAccounts, accountValues, positions)
    - Order management (placeOrder, cancelOrder, trades, openTrades)
    - Event subscriptions (orderStatusEvent, errorEvent, disconnectedEvent)

    Returns:
        MagicMock configured to behave like ib_async.IB.
    """
    ib = MagicMock()
    ib.isConnected.return_value = True
    ib.managedAccounts.return_value = ["U24619949"]
    ib.positions.return_value = []
    ib.openTrades.return_value = []
    ib.trades.return_value = []

    # Account values
    ib.accountValues.return_value = [
        _mock_account_value("NetLiquidation", "100000.0", "USD", "U24619949"),
        _mock_account_value("TotalCashValue", "50000.0", "USD", "U24619949"),
        _mock_account_value("BuyingPower", "200000.0", "USD", "U24619949"),
    ]

    # Event subscriptions (aeventkit uses += operator)
    # Use MockEvent to properly track += subscriptions
    ib.orderStatusEvent = MockEvent()
    ib.errorEvent = MockEvent()
    ib.disconnectedEvent = MockEvent()
    ib.connectedEvent = MockEvent()
    ib.newOrderEvent = MockEvent()

    # connectAsync returns a coroutine
    ib.connectAsync = AsyncMock()

    # placeOrder returns a Trade object
    def make_trade(contract: Stock, order: IBOrder) -> MagicMock:
        trade = MagicMock()
        trade.order = order
        trade.contract = contract
        trade.orderStatus = MagicMock()
        trade.orderStatus.status = "Submitted"
        trade.orderStatus.filled = 0
        trade.orderStatus.remaining = order.totalQuantity
        trade.orderStatus.avgFillPrice = 0.0
        trade.fills = []
        # Assign orderId if not set
        if not hasattr(order, "_mock_order_id"):
            order._mock_order_id = id(order) % 10000
            order.orderId = order._mock_order_id
        return trade

    ib.placeOrder = MagicMock(side_effect=make_trade)
    ib.cancelOrder = MagicMock()
    ib.reqGlobalCancel = MagicMock()

    return ib


def _mock_account_value(tag: str, value: str, currency: str, account: str) -> MagicMock:
    """Create a mock AccountValue object."""
    av = MagicMock()
    av.tag = tag
    av.value = value
    av.currency = currency
    av.account = account
    return av


def _mock_position(symbol: str, quantity: int, avg_cost: float) -> MagicMock:
    """Create a mock Position object."""
    pos = MagicMock()
    pos.contract = MagicMock()
    pos.contract.symbol = symbol
    pos.position = quantity
    pos.avgCost = avg_cost
    return pos


@pytest.fixture
def ibkr_config() -> IBKRConfig:
    """Create a standard IBKRConfig for testing."""
    return IBKRConfig(
        host="127.0.0.1",
        port=4002,
        client_id=1,
        account="U24619949",
        timeout_seconds=10.0,
        readonly=False,
    )


@pytest.fixture
def event_bus() -> EventBus:
    """Create an EventBus for testing."""
    return EventBus()


# ---------------------------------------------------------------------------
# Connection Tests
# ---------------------------------------------------------------------------


class TestIBKRBrokerConnection:
    """Tests for IBKRBroker connection management."""

    @pytest.mark.asyncio
    async def test_connect_success(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Successful connection sets _connected flag and calls connectAsync."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            assert broker._connected is True
            assert broker.is_connected is True
            mock_ib.connectAsync.assert_called_once_with(
                host="127.0.0.1",
                port=4002,
                clientId=1,
                timeout=10.0,
                readonly=False,
                account="U24619949",
            )

    @pytest.mark.asyncio
    async def test_connect_failure_raises(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Connection failure raises ConnectionError."""
        mock_ib.connectAsync = AsyncMock(side_effect=Exception("Connection refused"))

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)

            with pytest.raises(ConnectionError) as exc_info:
                await broker.connect()

            assert "Connection refused" in str(exc_info.value)
            assert broker._connected is False

    @pytest.mark.asyncio
    async def test_disconnect(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Disconnect calls ib.disconnect() and clears _connected flag."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()
            assert broker._connected is True

            await broker.disconnect()

            assert broker._connected is False
            mock_ib.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_connected_true(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """is_connected returns True when both flags are true."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            assert broker.is_connected is True

    @pytest.mark.asyncio
    async def test_is_connected_false_when_ib_disconnected(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """is_connected returns False when ib.isConnected() returns False."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Simulate IB Gateway disconnect
            mock_ib.isConnected.return_value = False

            assert broker.is_connected is False

    @pytest.mark.asyncio
    async def test_state_tracking_after_connect_disconnect(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Connection state is tracked correctly through connect/disconnect cycle."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)

            # Initially not connected
            assert broker._connected is False
            mock_ib.isConnected.return_value = False
            assert broker.is_connected is False

            # After connect
            mock_ib.isConnected.return_value = True
            await broker.connect()
            assert broker._connected is True
            assert broker.is_connected is True

            # After disconnect
            await broker.disconnect()
            assert broker._connected is False

    @pytest.mark.asyncio
    async def test_event_subscription_wiring(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Event subscriptions are wired in constructor."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)

            # Verify event handlers were registered via += operator
            assert len(mock_ib.orderStatusEvent.handlers) == 1
            assert len(mock_ib.errorEvent.handlers) == 1
            assert len(mock_ib.disconnectedEvent.handlers) == 1

            # Verify the handlers are the broker's methods
            assert mock_ib.orderStatusEvent.handlers[0] == broker._on_order_status
            assert mock_ib.errorEvent.handlers[0] == broker._on_error
            assert mock_ib.disconnectedEvent.handlers[0] == broker._on_disconnected

    @pytest.mark.asyncio
    async def test_account_parameter_passthrough(
        self, mock_ib: MagicMock, event_bus: EventBus
    ) -> None:
        """Account parameter from config is passed to connectAsync."""
        config = IBKRConfig(
            host="192.168.1.100",
            port=4001,
            client_id=5,
            account="DU12345",
            timeout_seconds=60.0,
            readonly=True,
        )

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(config, event_bus)
            await broker.connect()

            mock_ib.connectAsync.assert_called_once_with(
                host="192.168.1.100",
                port=4001,
                clientId=5,
                timeout=60.0,
                readonly=True,
                account="DU12345",
            )

    @pytest.mark.asyncio
    async def test_position_snapshot_on_connect(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Positions are snapshotted on connect for reconnection verification."""
        mock_positions = [
            _mock_position("AAPL", 100, 150.0),
            _mock_position("NVDA", 50, 800.0),
        ]
        mock_ib.positions.return_value = mock_positions

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            assert len(broker._last_known_positions) == 2
            assert broker._last_known_positions == mock_positions
            mock_ib.positions.assert_called()


class TestIBKRBrokerConstructor:
    """Tests for IBKRBroker constructor initialization."""

    def test_constructor_initializes_state(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Constructor initializes all internal state correctly."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)

            assert broker._config == ibkr_config
            assert broker._event_bus == event_bus
            assert broker._ib == mock_ib
            assert broker._connected is False
            assert broker._reconnecting is False
            assert broker._ulid_to_ibkr == {}
            assert broker._ibkr_to_ulid == {}
            assert broker._last_known_positions == []
            assert broker._contracts is not None

    def test_constructor_creates_contract_resolver(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Constructor creates an IBKRContractResolver instance."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)

            from argus.execution.ibkr_contracts import IBKRContractResolver

            assert isinstance(broker._contracts, IBKRContractResolver)


class TestIBKRBrokerDisconnectEvent:
    """Tests for handling disconnection events."""

    @pytest.mark.asyncio
    async def test_on_disconnected_clears_connected_flag(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """_on_disconnected handler clears the connected flag."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()
            assert broker._connected is True

            # Simulate disconnect event
            broker._on_disconnected()

            assert broker._connected is False


# ---------------------------------------------------------------------------
# Order Submission Tests
# ---------------------------------------------------------------------------


def _create_order(
    symbol: str = "AAPL",
    side: str = "buy",
    order_type: str = "market",
    quantity: int = 100,
    limit_price: float | None = None,
    stop_price: float | None = None,
):
    """Create an ARGUS Order for testing.

    Returns:
        Order: An ARGUS Order instance for testing.
    """
    from argus.models.trading import Order

    return Order(
        strategy_id="test_strategy",
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        limit_price=limit_price,
        stop_price=stop_price,
    )


class TestIBKRBrokerOrderSubmission:
    """Tests for IBKRBroker order submission (place_order)."""

    @pytest.mark.asyncio
    async def test_market_order_placed(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Market order is placed correctly with MarketOrder type."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order(order_type="market", quantity=100)
            result = await broker.place_order(order)

            assert result.status == "submitted"
            assert result.order_id != ""
            assert result.broker_order_id != ""
            mock_ib.placeOrder.assert_called_once()

            # Verify the order type
            call_args = mock_ib.placeOrder.call_args
            ib_order = call_args[0][1]
            assert ib_order.action == "BUY"
            assert ib_order.totalQuantity == 100
            assert ib_order.tif == "DAY"
            assert ib_order.outsideRth is False

    @pytest.mark.asyncio
    async def test_limit_order_with_price(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Limit order is placed with correct limit price."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order(order_type="limit", quantity=50, limit_price=150.50)
            result = await broker.place_order(order)

            assert result.status == "submitted"
            call_args = mock_ib.placeOrder.call_args
            ib_order = call_args[0][1]
            assert ib_order.lmtPrice == 150.50
            assert ib_order.totalQuantity == 50

    @pytest.mark.asyncio
    async def test_stop_order_with_price(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Stop order is placed with correct stop price."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order(side="sell", order_type="stop", quantity=75, stop_price=145.00)
            result = await broker.place_order(order)

            assert result.status == "submitted"
            call_args = mock_ib.placeOrder.call_args
            ib_order = call_args[0][1]
            assert ib_order.auxPrice == 145.00
            assert ib_order.action == "SELL"

    @pytest.mark.asyncio
    async def test_stop_limit_order_with_both_prices(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Stop-limit order is placed with both stop and limit prices."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order(
                order_type="stop_limit",
                quantity=100,
                stop_price=148.00,
                limit_price=147.50,
            )
            result = await broker.place_order(order)

            assert result.status == "submitted"
            call_args = mock_ib.placeOrder.call_args
            ib_order = call_args[0][1]
            assert ib_order.orderType == "STP LMT"
            assert ib_order.auxPrice == 148.00  # trigger price
            assert ib_order.lmtPrice == 147.50  # limit price

    @pytest.mark.asyncio
    async def test_ulid_generated_and_mapped(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """ULID is generated for each order and stored in mapping."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)

            # ULID should be 26 characters
            assert len(result.order_id) == 26
            # Should be in the mapping
            assert result.order_id in broker._ulid_to_ibkr

    @pytest.mark.asyncio
    async def test_order_ref_set_on_ib_order(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """orderRef is set on the ib_async order for reconstruction."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)

            # Get the order that was passed to placeOrder
            call_args = mock_ib.placeOrder.call_args
            ib_order = call_args[0][1]

            # orderRef should be set to the ULID
            assert ib_order.orderRef == result.order_id

    @pytest.mark.asyncio
    async def test_ibkr_id_mapped_bidirectionally(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """IBKR order ID is mapped bidirectionally with ULID."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)

            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            # Check both directions
            assert broker._ulid_to_ibkr[ulid] == ibkr_id
            assert broker._ibkr_to_ulid[ibkr_id] == ulid

    @pytest.mark.asyncio
    async def test_not_connected_returns_rejected(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Order placement when not connected returns rejected status."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            # Don't connect

            order = _create_order()
            result = await broker.place_order(order)

            assert result.status == "rejected"
            assert "Not connected" in result.message
            mock_ib.placeOrder.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_order_type_raises_value_error(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Invalid order type raises ValueError."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Create order with invalid type by bypassing validation
            from argus.models.trading import Order

            # We need to test the _build_ib_order method directly with invalid type
            # since Pydantic would validate the Order model
            order = Order(
                strategy_id="test",
                symbol="AAPL",
                side="buy",
                order_type="market",  # Valid type for creation
                quantity=100,
            )
            # Manually set invalid type to bypass Pydantic
            object.__setattr__(order, "order_type", "invalid_type")

            with pytest.raises(ValueError) as exc_info:
                await broker.place_order(order)

            assert "Unsupported order type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_buy_sell_action_mapping(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Buy and sell sides are correctly mapped to BUY/SELL actions."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Test BUY
            buy_order = _create_order(side="buy")
            await broker.place_order(buy_order)

            call_args = mock_ib.placeOrder.call_args
            ib_order = call_args[0][1]
            assert ib_order.action == "BUY"

            # Reset mock
            mock_ib.placeOrder.reset_mock()

            # Test SELL
            sell_order = _create_order(side="sell")
            await broker.place_order(sell_order)

            call_args = mock_ib.placeOrder.call_args
            ib_order = call_args[0][1]
            assert ib_order.action == "SELL"


# ---------------------------------------------------------------------------
# Bracket Order Tests (DEC-093)
# ---------------------------------------------------------------------------


def _create_bracket_orders(
    symbol: str = "AAPL",
    entry_side: str = "buy",
    entry_type: str = "market",
    entry_quantity: int = 100,
    entry_limit_price: float | None = None,
    stop_price: float = 145.00,
    t1_price: float = 155.00,
    t1_quantity: int = 50,
    t2_price: float | None = None,
    t2_quantity: int | None = None,
) -> tuple:
    """Create entry, stop, and target orders for bracket testing.

    Returns:
        Tuple of (entry_order, stop_order, targets_list).
    """
    from argus.models.trading import Order

    entry = Order(
        strategy_id="test_strategy",
        symbol=symbol,
        side=entry_side,
        order_type=entry_type,
        quantity=entry_quantity,
        limit_price=entry_limit_price,
    )

    stop = Order(
        strategy_id="test_strategy",
        symbol=symbol,
        side="sell" if entry_side == "buy" else "buy",
        order_type="stop",
        quantity=entry_quantity,
        stop_price=stop_price,
    )

    targets: list[Order] = []
    if t1_price is not None:
        t1 = Order(
            strategy_id="test_strategy",
            symbol=symbol,
            side="sell" if entry_side == "buy" else "buy",
            order_type="limit",
            quantity=t1_quantity,
            limit_price=t1_price,
        )
        targets.append(t1)

    if t2_price is not None and t2_quantity is not None:
        t2 = Order(
            strategy_id="test_strategy",
            symbol=symbol,
            side="sell" if entry_side == "buy" else "buy",
            order_type="limit",
            quantity=t2_quantity,
            limit_price=t2_price,
        )
        targets.append(t2)

    return entry, stop, targets


class TestIBKRBrokerBracketOrders:
    """Tests for IBKRBroker native bracket order support (DEC-093)."""

    @pytest.mark.asyncio
    async def test_bracket_with_t1_only(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Bracket with T1 target creates 3 orders: entry + stop + T1."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(t1_price=155.00, t1_quantity=50)
            result = await broker.place_bracket_order(entry, stop, targets)

            # Should have called placeOrder 3 times: entry, stop, T1
            assert mock_ib.placeOrder.call_count == 3

            # Result structure
            assert result.entry.status == "submitted"
            assert result.stop.status == "submitted"
            assert len(result.targets) == 1
            assert result.targets[0].status == "submitted"

    @pytest.mark.asyncio
    async def test_bracket_with_t1_and_t2(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Bracket with T1 and T2 targets creates 4 orders: entry + stop + T1 + T2."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                t1_price=155.00,
                t1_quantity=50,
                t2_price=160.00,
                t2_quantity=50,
            )
            result = await broker.place_bracket_order(entry, stop, targets)

            # Should have called placeOrder 4 times: entry, stop, T1, T2
            assert mock_ib.placeOrder.call_count == 4

            # Result structure
            assert result.entry.status == "submitted"
            assert result.stop.status == "submitted"
            assert len(result.targets) == 2
            assert result.targets[0].status == "submitted"
            assert result.targets[1].status == "submitted"

    @pytest.mark.asyncio
    async def test_market_entry_bracket(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Market entry bracket order creates parent as MarketOrder."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                entry_type="market", t1_price=155.00, t1_quantity=50
            )
            await broker.place_bracket_order(entry, stop, targets)

            # First call should be the parent (entry) order
            first_call = mock_ib.placeOrder.call_args_list[0]
            parent_order = first_call[0][1]

            # Check it's a market order
            assert parent_order.action == "BUY"
            assert parent_order.totalQuantity == 100

    @pytest.mark.asyncio
    async def test_limit_entry_bracket(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Limit entry bracket order creates parent as LimitOrder."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                entry_type="limit",
                entry_limit_price=150.00,
                t1_price=155.00,
                t1_quantity=50,
            )
            await broker.place_bracket_order(entry, stop, targets)

            # First call should be the parent (entry) order
            first_call = mock_ib.placeOrder.call_args_list[0]
            parent_order = first_call[0][1]

            # Check it's a limit order with correct price
            assert parent_order.lmtPrice == 150.00
            assert parent_order.action == "BUY"

    @pytest.mark.asyncio
    async def test_parent_id_set_on_all_children(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """All child orders (stop, T1, T2) have parentId set to parent order ID."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                t1_price=155.00,
                t1_quantity=50,
                t2_price=160.00,
                t2_quantity=50,
            )
            await broker.place_bracket_order(entry, stop, targets)

            # Get parent order ID from first call
            first_call = mock_ib.placeOrder.call_args_list[0]
            parent_order = first_call[0][1]
            parent_id = parent_order.orderId

            # Check all children have parentId set
            for i, call in enumerate(mock_ib.placeOrder.call_args_list[1:], start=1):
                child_order = call[0][1]
                assert child_order.parentId == parent_id, (
                    f"Child order {i} parentId mismatch: "
                    f"expected {parent_id}, got {child_order.parentId}"
                )

    @pytest.mark.asyncio
    async def test_transmit_false_on_parent_and_intermediates(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Parent and intermediate children have transmit=False."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                t1_price=155.00,
                t1_quantity=50,
                t2_price=160.00,
                t2_quantity=50,
            )
            await broker.place_bracket_order(entry, stop, targets)

            # 4 orders: entry (0), stop (1), T1 (2), T2 (3)
            # Entry, stop, and T1 should have transmit=False
            calls = mock_ib.placeOrder.call_args_list

            # Entry (index 0)
            assert calls[0][0][1].transmit is False, "Entry should have transmit=False"
            # Stop (index 1)
            assert calls[1][0][1].transmit is False, "Stop should have transmit=False"
            # T1 (index 2) - not the last target
            assert calls[2][0][1].transmit is False, "T1 should have transmit=False"

    @pytest.mark.asyncio
    async def test_transmit_true_on_last_child_only(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Only the last child order has transmit=True."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                t1_price=155.00,
                t1_quantity=50,
                t2_price=160.00,
                t2_quantity=50,
            )
            await broker.place_bracket_order(entry, stop, targets)

            # Last order (T2) should have transmit=True
            calls = mock_ib.placeOrder.call_args_list
            last_order = calls[-1][0][1]
            assert last_order.transmit is True, "Last child should have transmit=True"

    @pytest.mark.asyncio
    async def test_all_ulids_mapped_bidirectionally(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """All ULIDs are registered in both _ulid_to_ibkr and _ibkr_to_ulid."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                t1_price=155.00,
                t1_quantity=50,
                t2_price=160.00,
                t2_quantity=50,
            )
            result = await broker.place_bracket_order(entry, stop, targets)

            # Collect all ULIDs from result
            all_ulids = [
                result.entry.order_id,
                result.stop.order_id,
                *[t.order_id for t in result.targets],
            ]

            # All should be in mappings
            for ulid in all_ulids:
                assert ulid in broker._ulid_to_ibkr, f"{ulid} not in _ulid_to_ibkr"
                ibkr_id = broker._ulid_to_ibkr[ulid]
                assert ibkr_id in broker._ibkr_to_ulid, f"{ibkr_id} not in _ibkr_to_ulid"
                assert broker._ibkr_to_ulid[ibkr_id] == ulid, "Bidirectional mapping mismatch"

    @pytest.mark.asyncio
    async def test_order_ref_set_on_every_leg(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """orderRef is set to ULID on every leg for reconstruction."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _create_bracket_orders(
                t1_price=155.00,
                t1_quantity=50,
                t2_price=160.00,
                t2_quantity=50,
            )
            result = await broker.place_bracket_order(entry, stop, targets)

            # Get all ULIDs from result
            expected_refs = [
                result.entry.order_id,
                result.stop.order_id,
                *[t.order_id for t in result.targets],
            ]

            # Check each order has orderRef set to its ULID
            calls = mock_ib.placeOrder.call_args_list
            for i, call in enumerate(calls):
                order = call[0][1]
                assert order.orderRef == expected_refs[i], (
                    f"Order {i} orderRef mismatch: "
                    f"expected {expected_refs[i]}, got {order.orderRef}"
                )

    @pytest.mark.asyncio
    async def test_empty_targets_list_entry_stop_only(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Bracket with empty targets list creates 2 orders: entry + stop."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Create bracket with no targets
            entry, stop, _ = _create_bracket_orders()
            targets: list = []  # Empty targets list

            result = await broker.place_bracket_order(entry, stop, targets)

            # Should have called placeOrder 2 times: entry + stop
            assert mock_ib.placeOrder.call_count == 2

            # Result structure
            assert result.entry.status == "submitted"
            assert result.stop.status == "submitted"
            assert len(result.targets) == 0

            # Stop should have transmit=True since it's the last order
            stop_call = mock_ib.placeOrder.call_args_list[1]
            stop_order = stop_call[0][1]
            assert stop_order.transmit is True, "Stop should have transmit=True when no targets"

            # Entry should still have transmit=False
            entry_call = mock_ib.placeOrder.call_args_list[0]
            entry_order = entry_call[0][1]
            assert entry_order.transmit is False


# ---------------------------------------------------------------------------
# Fill Streaming Tests (Prompt 6)
# ---------------------------------------------------------------------------


def _mock_trade(
    order_id: int = 12345,
    status: str = "Submitted",
    filled: int = 0,
    remaining: int = 100,
    avg_fill_price: float = 0.0,
    action: str = "BUY",
    order_type: str = "MKT",
    total_qty: int = 100,
    symbol: str = "AAPL",
    order_ref: str = "",
    why_held: str = "",
) -> MagicMock:
    """Create a mock Trade object for testing fill streaming."""
    trade = MagicMock()
    trade.order = MagicMock()
    trade.order.orderId = order_id
    trade.order.action = action
    trade.order.orderType = order_type
    trade.order.totalQuantity = total_qty
    trade.order.orderRef = order_ref

    trade.orderStatus = MagicMock()
    trade.orderStatus.status = status
    trade.orderStatus.filled = filled
    trade.orderStatus.remaining = remaining
    trade.orderStatus.avgFillPrice = avg_fill_price
    trade.orderStatus.whyHeld = why_held

    trade.contract = MagicMock()
    trade.contract.symbol = symbol

    return trade


class TestIBKRBrokerFillStreaming:
    """Tests for IBKRBroker fill streaming event handlers."""

    @pytest.mark.asyncio
    async def test_filled_event_published_with_correct_price_qty(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Filled status publishes OrderFilledEvent with correct price and quantity."""
        from argus.core.events import OrderFilledEvent

        # Track published events (use async handler for EventBus)
        published_events: list = []

        async def capture_event(e: OrderFilledEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderFilledEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Place an order to register the ULID mapping
            order = _create_order()
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            # Simulate a fill
            trade = _mock_trade(
                order_id=ibkr_id,
                status="Filled",
                filled=100,
                remaining=0,
                avg_fill_price=152.75,
            )

            await broker._handle_order_status(trade)
            await event_bus.drain()

        # Verify event was published
        assert len(published_events) == 1
        event = published_events[0]
        assert event.order_id == ulid
        assert event.fill_price == 152.75
        assert event.fill_quantity == 100

    @pytest.mark.asyncio
    async def test_cancelled_event_published(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Cancelled status publishes OrderCancelledEvent."""
        from argus.core.events import OrderCancelledEvent

        published_events: list = []

        async def capture_event(e: OrderCancelledEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderCancelledEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            trade = _mock_trade(order_id=ibkr_id, status="Cancelled")

            await broker._handle_order_status(trade)
            await event_bus.drain()

        assert len(published_events) == 1
        event = published_events[0]
        assert event.order_id == ulid
        assert "Cancelled" in event.reason

    @pytest.mark.asyncio
    async def test_inactive_rejected_event_published_with_reason(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Inactive status (IBKR rejection) publishes OrderCancelledEvent with reason."""
        from argus.core.events import OrderCancelledEvent

        published_events: list = []

        async def capture_event(e: OrderCancelledEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderCancelledEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            trade = _mock_trade(
                order_id=ibkr_id,
                status="Inactive",
                why_held="insufficient margin",
            )

            await broker._handle_order_status(trade)
            await event_bus.drain()

        assert len(published_events) == 1
        event = published_events[0]
        assert event.order_id == ulid
        assert "rejected" in event.reason.lower()
        assert "insufficient margin" in event.reason

    @pytest.mark.asyncio
    async def test_submitted_event_published(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Submitted status publishes OrderSubmittedEvent."""
        from argus.core.events import OrderSubmittedEvent, Side

        published_events: list = []

        async def capture_event(e: OrderSubmittedEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderSubmittedEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            trade = _mock_trade(
                order_id=ibkr_id,
                status="Submitted",
                action="BUY",
                order_type="MKT",
                total_qty=100,
                symbol="AAPL",
            )

            await broker._handle_order_status(trade)
            await event_bus.drain()

        assert len(published_events) == 1
        event = published_events[0]
        assert event.order_id == ulid
        assert event.symbol == "AAPL"
        assert event.side == Side.LONG
        assert event.quantity == 100

    @pytest.mark.asyncio
    async def test_presubmitted_logged_only_no_event(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """PreSubmitted status is logged only, no event published."""
        from argus.core.events import (
            OrderCancelledEvent,
            OrderFilledEvent,
            OrderSubmittedEvent,
        )

        filled_events: list = []
        cancelled_events: list = []
        submitted_events: list = []

        async def capture_filled(e: OrderFilledEvent) -> None:
            filled_events.append(e)

        async def capture_cancelled(e: OrderCancelledEvent) -> None:
            cancelled_events.append(e)

        async def capture_submitted(e: OrderSubmittedEvent) -> None:
            submitted_events.append(e)

        event_bus.subscribe(OrderFilledEvent, capture_filled)
        event_bus.subscribe(OrderCancelledEvent, capture_cancelled)
        event_bus.subscribe(OrderSubmittedEvent, capture_submitted)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)
            ibkr_id = int(result.broker_order_id)

            trade = _mock_trade(order_id=ibkr_id, status="PreSubmitted")

            await broker._handle_order_status(trade)
            await event_bus.drain()

        # No events should be published
        assert len(filled_events) == 0
        assert len(cancelled_events) == 0
        assert len(submitted_events) == 0

    @pytest.mark.asyncio
    async def test_unknown_order_id_ignored(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Unknown order IDs (not in mapping) are ignored with debug log."""
        from argus.core.events import OrderFilledEvent

        published_events: list = []

        async def capture_event(e: OrderFilledEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderFilledEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Don't place any order — ID 99999 is unknown
            trade = _mock_trade(
                order_id=99999,
                status="Filled",
                filled=100,
                avg_fill_price=150.0,
            )

            await broker._handle_order_status(trade)
            await event_bus.drain()

        # No event should be published
        assert len(published_events) == 0

    @pytest.mark.asyncio
    async def test_error_classification_routes_correctly(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Error handler classifies and routes errors by severity."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # INFO-level error (should be debug logged, no event)
            with patch("argus.execution.ibkr_broker.logger") as mock_logger:
                broker._on_error(0, 354, "Market data not subscribed")
                mock_logger.debug.assert_called()
                mock_logger.critical.assert_not_called()
                mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_critical_error_logged(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Critical errors are logged at critical level."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            with patch("argus.execution.ibkr_broker.logger") as mock_logger:
                broker._on_error(0, 502, "Couldn't connect to TWS")
                mock_logger.critical.assert_called()

    @pytest.mark.asyncio
    async def test_order_rejection_via_error_publishes_cancel(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Order rejection via error event (code 201) publishes OrderCancelledEvent."""
        from argus.core.events import OrderCancelledEvent

        published_events: list = []

        async def capture_event(e: OrderCancelledEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderCancelledEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            # Simulate order rejection error
            broker._on_error(ibkr_id, 201, "Order rejected - invalid price")

            # Give async task time to complete
            await asyncio.sleep(0.01)
            await event_bus.drain()

        assert len(published_events) == 1
        event = published_events[0]
        assert event.order_id == ulid
        assert "rejected" in event.reason.lower()

    def test_order_type_mapping_all_variants(self) -> None:
        """_map_ib_order_type correctly maps all order type variants."""
        from argus.core.events import OrderType

        assert IBKRBroker._map_ib_order_type("MKT") == OrderType.MARKET
        assert IBKRBroker._map_ib_order_type("LMT") == OrderType.LIMIT
        assert IBKRBroker._map_ib_order_type("STP") == OrderType.STOP
        assert IBKRBroker._map_ib_order_type("STP LMT") == OrderType.STOP_LIMIT
        # Unknown type defaults to MARKET
        assert IBKRBroker._map_ib_order_type("UNKNOWN") == OrderType.MARKET

    @pytest.mark.asyncio
    async def test_partial_fill_handling(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Partial fills (filled < total) publish OrderFilledEvent with partial qty."""
        from argus.core.events import OrderFilledEvent

        published_events: list = []

        async def capture_event(e: OrderFilledEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderFilledEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order(quantity=100)
            result = await broker.place_order(order)
            ibkr_id = int(result.broker_order_id)

            # Simulate partial fill (50 of 100)
            trade = _mock_trade(
                order_id=ibkr_id,
                status="Filled",
                filled=50,
                remaining=50,
                total_qty=100,
                avg_fill_price=151.25,
            )

            await broker._handle_order_status(trade)
            await event_bus.drain()

        assert len(published_events) == 1
        event = published_events[0]
        assert event.fill_quantity == 50
        assert event.fill_price == 151.25

    @pytest.mark.asyncio
    async def test_fill_with_zero_avg_price_edge_case(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Fill with zero average price (edge case) is handled without error."""
        from argus.core.events import OrderFilledEvent

        published_events: list = []

        async def capture_event(e: OrderFilledEvent) -> None:
            published_events.append(e)

        event_bus.subscribe(OrderFilledEvent, capture_event)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            order = _create_order()
            result = await broker.place_order(order)
            ibkr_id = int(result.broker_order_id)

            # Simulate fill with zero price (unusual but should not crash)
            trade = _mock_trade(
                order_id=ibkr_id,
                status="Filled",
                filled=100,
                remaining=0,
                avg_fill_price=0.0,
            )

            await broker._handle_order_status(trade)
            await event_bus.drain()

        # Event should still be published
        assert len(published_events) == 1
        event = published_events[0]
        assert event.fill_price == 0.0
        assert event.fill_quantity == 100


# ---------------------------------------------------------------------------
# Cancel Order Tests (Prompt 7)
# ---------------------------------------------------------------------------


class TestIBKRBrokerCancelOrder:
    """Tests for IBKRBroker cancel_order method."""

    @pytest.mark.asyncio
    async def test_cancel_existing_order_succeeds(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Cancel an existing order returns True and calls cancelOrder."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Place an order to get it registered
            order = _create_order()
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            # Create a mock trade for the find method
            mock_trade = _mock_trade(order_id=ibkr_id)
            mock_ib.trades.return_value = [mock_trade]

            # Cancel the order
            cancelled = await broker.cancel_order(ulid)

            assert cancelled is True
            mock_ib.cancelOrder.assert_called_once_with(mock_trade.order)

    @pytest.mark.asyncio
    async def test_cancel_unknown_order_returns_false(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Cancel an unknown order returns False without calling IBKR."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Try to cancel an order that was never placed
            cancelled = await broker.cancel_order("unknown_ulid_12345")

            assert cancelled is False
            mock_ib.cancelOrder.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_not_found_trade_returns_false(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Cancel returns False when order ID is known but trade not in cache."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Place an order
            order = _create_order()
            result = await broker.place_order(order)
            ulid = result.order_id

            # Simulate trade not being in the cache
            mock_ib.trades.return_value = []

            # Cancel should fail
            cancelled = await broker.cancel_order(ulid)

            assert cancelled is False
            mock_ib.cancelOrder.assert_not_called()


# ---------------------------------------------------------------------------
# Modify Order Tests (Prompt 7)
# ---------------------------------------------------------------------------


class TestIBKRBrokerModifyOrder:
    """Tests for IBKRBroker modify_order method."""

    @pytest.mark.asyncio
    async def test_modify_stop_price_uses_aux_price(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Modifying a stop order price sets auxPrice."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Place an order
            order = _create_order(order_type="stop", stop_price=145.00)
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            # Create a mock trade with STP order type
            mock_trade = _mock_trade(order_id=ibkr_id, order_type="STP")
            mock_ib.trades.return_value = [mock_trade]

            # Modify the stop price
            mod_result = await broker.modify_order(ulid, {"price": 143.00})

            assert mod_result.status == "submitted"
            assert mock_trade.order.auxPrice == 143.00
            # placeOrder should be called to submit the modification
            assert mock_ib.placeOrder.call_count >= 2  # Original + modification

    @pytest.mark.asyncio
    async def test_modify_limit_price_uses_lmt_price(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Modifying a limit order price sets lmtPrice."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Place an order
            order = _create_order(order_type="limit", limit_price=150.00)
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            # Create a mock trade with LMT order type
            mock_trade = _mock_trade(order_id=ibkr_id, order_type="LMT")
            mock_ib.trades.return_value = [mock_trade]

            # Modify the limit price
            mod_result = await broker.modify_order(ulid, {"price": 152.00})

            assert mod_result.status == "submitted"
            assert mock_trade.order.lmtPrice == 152.00

    @pytest.mark.asyncio
    async def test_modify_quantity(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Modifying order quantity sets totalQuantity."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Place an order
            order = _create_order(quantity=100)
            result = await broker.place_order(order)
            ulid = result.order_id
            ibkr_id = int(result.broker_order_id)

            # Create a mock trade
            mock_trade = _mock_trade(order_id=ibkr_id, total_qty=100)
            mock_ib.trades.return_value = [mock_trade]

            # Modify the quantity
            mod_result = await broker.modify_order(ulid, {"quantity": 50})

            assert mod_result.status == "submitted"
            assert mock_trade.order.totalQuantity == 50


# ---------------------------------------------------------------------------
# Account Query Tests (Prompt 7)
# ---------------------------------------------------------------------------


class TestIBKRBrokerPositions:
    """Tests for IBKRBroker get_positions method."""

    @pytest.mark.asyncio
    async def test_positions_with_holdings(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """get_positions returns Position objects for all holdings."""
        mock_positions = [
            _mock_position("AAPL", 100, 150.0),
            _mock_position("NVDA", 50, 800.0),
        ]
        mock_ib.positions.return_value = mock_positions

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            positions = await broker.get_positions()

            assert len(positions) == 2
            assert positions[0].symbol == "AAPL"
            assert positions[0].shares == 100
            assert positions[0].entry_price == 150.0
            assert positions[1].symbol == "NVDA"
            assert positions[1].shares == 50

    @pytest.mark.asyncio
    async def test_positions_empty(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """get_positions returns empty list when no positions."""
        mock_ib.positions.return_value = []

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            positions = await broker.get_positions()

            assert len(positions) == 0

    @pytest.mark.asyncio
    async def test_positions_filters_zero_quantity(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """get_positions filters out zero-quantity (closed) positions."""
        mock_positions = [
            _mock_position("AAPL", 100, 150.0),
            _mock_position("CLOSED", 0, 100.0),  # Zero qty should be filtered
            _mock_position("NVDA", 50, 800.0),
        ]
        mock_ib.positions.return_value = mock_positions

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            positions = await broker.get_positions()

            assert len(positions) == 2
            symbols = [p.symbol for p in positions]
            assert "CLOSED" not in symbols


class TestIBKRBrokerAccount:
    """Tests for IBKRBroker get_account method."""

    @pytest.mark.asyncio
    async def test_account_info_all_fields(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """get_account returns AccountInfo with all expected fields."""
        mock_ib.accountValues.return_value = [
            _mock_account_value("NetLiquidation", "100000.0", "USD", "U24619949"),
            _mock_account_value("TotalCashValue", "50000.0", "USD", "U24619949"),
            _mock_account_value("BuyingPower", "200000.0", "USD", "U24619949"),
        ]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            account = await broker.get_account()

            assert account.equity == 100000.0
            assert account.cash == 50000.0
            assert account.buying_power == 200000.0
            assert account.positions_value == 50000.0  # equity - cash

    @pytest.mark.asyncio
    async def test_account_buying_power_present(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """get_account extracts BuyingPower correctly."""
        mock_ib.accountValues.return_value = [
            _mock_account_value("NetLiquidation", "75000.0", "USD", "U24619949"),
            _mock_account_value("TotalCashValue", "25000.0", "USD", "U24619949"),
            _mock_account_value("BuyingPower", "150000.0", "USD", "U24619949"),
        ]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            account = await broker.get_account()

            assert account.buying_power == 150000.0

    @pytest.mark.asyncio
    async def test_account_filters_non_usd_values(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """get_account filters out non-USD account values."""
        mock_ib.accountValues.return_value = [
            _mock_account_value("NetLiquidation", "100000.0", "USD", "U24619949"),
            _mock_account_value("NetLiquidation", "85000.0", "EUR", "U24619949"),  # Ignored
            _mock_account_value("TotalCashValue", "50000.0", "USD", "U24619949"),
            _mock_account_value("BuyingPower", "200000.0", "USD", "U24619949"),
            _mock_account_value("BuyingPower", "170000.0", "EUR", "U24619949"),  # Ignored
        ]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            account = await broker.get_account()

            # Should use the USD values, not EUR
            assert account.equity == 100000.0
            assert account.buying_power == 200000.0


# ---------------------------------------------------------------------------
# Flatten Tests (Prompt 7)
# ---------------------------------------------------------------------------


class TestIBKRBrokerFlatten:
    """Tests for IBKRBroker flatten_all method."""

    @pytest.mark.asyncio
    async def test_flatten_with_long_positions(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """flatten_all closes long positions with SELL orders."""
        mock_positions = [
            _mock_position("AAPL", 100, 150.0),
        ]
        mock_ib.positions.return_value = mock_positions

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            results = await broker.flatten_all()

            assert len(results) == 1
            assert results[0].status == "submitted"
            assert "SELL" in results[0].message
            assert "100" in results[0].message
            assert "AAPL" in results[0].message
            mock_ib.reqGlobalCancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_flatten_with_short_positions(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """flatten_all closes short positions with BUY orders."""
        mock_positions = [
            _mock_position("TSLA", -50, 200.0),  # Short position
        ]
        mock_ib.positions.return_value = mock_positions

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            results = await broker.flatten_all()

            assert len(results) == 1
            assert results[0].status == "submitted"
            assert "BUY" in results[0].message
            assert "50" in results[0].message
            assert "TSLA" in results[0].message

    @pytest.mark.asyncio
    async def test_flatten_empty_portfolio(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """flatten_all with no positions returns empty list."""
        mock_ib.positions.return_value = []

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            results = await broker.flatten_all()

            assert len(results) == 0
            # Should still cancel pending orders
            mock_ib.reqGlobalCancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_flatten_cancels_pending_orders_first(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """flatten_all calls reqGlobalCancel before closing positions."""
        mock_positions = [
            _mock_position("AAPL", 100, 150.0),
        ]
        mock_ib.positions.return_value = mock_positions

        # Track call order
        call_order: list[str] = []
        original_cancel = mock_ib.reqGlobalCancel
        original_place = mock_ib.placeOrder

        def track_cancel() -> None:
            call_order.append("reqGlobalCancel")
            return original_cancel()

        def track_place(*args, **kwargs):
            call_order.append("placeOrder")
            return original_place(*args, **kwargs)

        mock_ib.reqGlobalCancel = MagicMock(side_effect=track_cancel)
        mock_ib.placeOrder = MagicMock(side_effect=track_place)

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            await broker.flatten_all()

            # reqGlobalCancel should be called before placeOrder
            assert "reqGlobalCancel" in call_order
            assert "placeOrder" in call_order
            req_global_idx = call_order.index("reqGlobalCancel")
            place_idx = call_order.index("placeOrder")
            assert req_global_idx < place_idx


# ---------------------------------------------------------------------------
# Helper Method Tests (Prompt 7)
# ---------------------------------------------------------------------------


class TestIBKRBrokerHelpers:
    """Tests for IBKRBroker helper methods."""

    def test_is_numeric_true_for_valid_numbers(self) -> None:
        """_is_numeric returns True for valid numeric strings."""
        assert IBKRBroker._is_numeric("100.0") is True
        assert IBKRBroker._is_numeric("0") is True
        assert IBKRBroker._is_numeric("-50.5") is True
        assert IBKRBroker._is_numeric("1e6") is True

    def test_is_numeric_false_for_non_numbers(self) -> None:
        """_is_numeric returns False for non-numeric strings."""
        assert IBKRBroker._is_numeric("not_a_number") is False
        assert IBKRBroker._is_numeric("") is False
        assert IBKRBroker._is_numeric("N/A") is False

    @pytest.mark.asyncio
    async def test_find_trade_by_order_id_found(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """_find_trade_by_order_id returns trade when found."""
        mock_trade = _mock_trade(order_id=12345)
        mock_ib.trades.return_value = [mock_trade]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)

            found = broker._find_trade_by_order_id(12345)

            assert found is mock_trade

    @pytest.mark.asyncio
    async def test_find_trade_by_order_id_not_found(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """_find_trade_by_order_id returns None when not found."""
        mock_ib.trades.return_value = []

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)

            found = broker._find_trade_by_order_id(99999)

            assert found is None


# ---------------------------------------------------------------------------
# Reconnection Tests (Prompt 8)
# ---------------------------------------------------------------------------


class TestIBKRBrokerReconnection:
    """Tests for IBKRBroker reconnection logic."""

    @pytest.mark.asyncio
    async def test_successful_reconnect_first_attempt(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Successful reconnection on first attempt sets flags correctly."""
        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock),
        ):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()
            assert broker._connected is True

            # Simulate disconnect and call _reconnect directly (not via _on_disconnected)
            # to avoid async timing issues with ensure_future
            broker._connected = False
            await broker._reconnect()

            # Should be reconnected
            assert broker._connected is True
            assert broker._reconnecting is False

    @pytest.mark.asyncio
    async def test_successful_reconnect_after_two_failures(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Successful reconnection after 2 failed attempts."""
        connect_attempts = [0]

        async def failing_connect(*args, **kwargs):
            connect_attempts[0] += 1
            if connect_attempts[0] <= 2:
                raise ConnectionError("Connection refused")
            # Third attempt succeeds (normal behavior from mock)

        mock_ib.connectAsync = AsyncMock(side_effect=failing_connect)

        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock),
        ):
            broker = IBKRBroker(ibkr_config, event_bus)
            # First connect succeeds (we're not using failing_connect yet)
            mock_ib.connectAsync.side_effect = None
            await broker.connect()

            # Now set up failing connect for reconnection
            connect_attempts[0] = 0
            mock_ib.connectAsync.side_effect = failing_connect

            # Simulate disconnect
            broker._connected = False
            await broker._reconnect()

            # Should have attempted 3 times (2 failures + 1 success)
            assert connect_attempts[0] == 3
            assert broker._connected is True
            assert broker._reconnecting is False

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_logs_critical(
        self, mock_ib: MagicMock, event_bus: EventBus
    ) -> None:
        """Max retries exceeded logs CRITICAL and sets reconnecting to False."""
        config = IBKRConfig(
            host="127.0.0.1",
            port=4002,
            client_id=1,
            account="U24619949",
            timeout_seconds=10.0,
            reconnect_max_retries=3,  # Only 3 retries for faster test
            reconnect_base_delay_seconds=0.1,
        )

        # Always fail to connect
        mock_ib.connectAsync = AsyncMock(side_effect=ConnectionError("Connection refused"))

        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock),
            patch("argus.execution.ibkr_broker.logger") as mock_logger,
        ):
            broker = IBKRBroker(config, event_bus)
            broker._connected = False  # Simulate disconnected state

            await broker._reconnect()

            # Should have logged critical
            mock_logger.critical.assert_called()
            critical_msg = mock_logger.critical.call_args[0][0]
            assert "Failed to reconnect" in critical_msg

            # Reconnecting flag should be cleared
            assert broker._reconnecting is False
            assert broker._connected is False

    @pytest.mark.asyncio
    async def test_position_verification_passes_same_positions(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Position verification passes when positions match before/after."""
        initial_positions = [
            _mock_position("AAPL", 100, 150.0),
            _mock_position("NVDA", 50, 800.0),
        ]
        mock_ib.positions.return_value = initial_positions

        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock),
            patch("argus.execution.ibkr_broker.logger") as mock_logger,
        ):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Simulate disconnect
            broker._connected = False

            # Reconnect with same positions
            await broker._reconnect()

            # Should NOT have logged position mismatch warning
            for call in mock_logger.warning.call_args_list:
                assert "Position mismatch" not in str(call)

    @pytest.mark.asyncio
    async def test_position_mismatch_logs_warning(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Position mismatch after reconnect logs warning."""
        initial_positions = [
            _mock_position("AAPL", 100, 150.0),
        ]

        # After reconnect, positions are different
        post_reconnect_positions = [
            _mock_position("AAPL", 50, 150.0),  # Quantity changed
        ]

        positions_call_count = [0]

        def get_positions():
            positions_call_count[0] += 1
            # First call during connect(), second during _reconnect verification
            if positions_call_count[0] <= 1:
                return initial_positions
            return post_reconnect_positions

        mock_ib.positions.side_effect = get_positions

        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.sleep", new_callable=AsyncMock),
            patch("argus.execution.ibkr_broker.logger") as mock_logger,
        ):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Simulate disconnect
            broker._connected = False

            # Reconnect with different positions
            await broker._reconnect()

            # Should have logged position mismatch warning
            warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
            mismatch_logged = any("Position mismatch" in call for call in warning_calls)
            assert mismatch_logged, f"Expected position mismatch warning. Calls: {warning_calls}"

    @pytest.mark.asyncio
    async def test_no_double_reconnect(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Second disconnect during reconnection is ignored (no double-reconnect)."""
        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.ensure_future") as mock_ensure,
        ):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # First disconnect triggers reconnection
            broker._on_disconnected()
            assert mock_ensure.call_count == 1

            # Manually set reconnecting flag (simulating _reconnect in progress)
            broker._reconnecting = True

            # Second disconnect while reconnecting should be ignored
            broker._on_disconnected()

            # ensure_future should have been called only once
            assert mock_ensure.call_count == 1

    @pytest.mark.asyncio
    async def test_backoff_delay_values_correct(
        self, mock_ib: MagicMock, event_bus: EventBus
    ) -> None:
        """Exponential backoff delays are calculated correctly with cap."""
        config = IBKRConfig(
            host="127.0.0.1",
            port=4002,
            client_id=1,
            account="U24619949",
            timeout_seconds=10.0,
            reconnect_max_retries=6,
            reconnect_base_delay_seconds=1.0,
            reconnect_max_delay_seconds=8.0,  # Cap at 8 seconds
        )

        # Always fail to connect so we can measure all delays
        mock_ib.connectAsync = AsyncMock(side_effect=ConnectionError("Connection refused"))

        recorded_delays: list[float] = []

        async def recording_sleep(delay: float) -> None:
            recorded_delays.append(delay)

        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch(
                "argus.execution.ibkr_broker.asyncio.sleep",
                side_effect=recording_sleep,
            ),
        ):
            broker = IBKRBroker(config, event_bus)
            broker._connected = False

            await broker._reconnect()

            # Expected delays: 1, 2, 4, 8, 8, 8 (capped at 8)
            expected_delays = [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]
            assert recorded_delays == expected_delays

    @pytest.mark.asyncio
    async def test_on_disconnected_schedules_reconnect(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """_on_disconnected schedules _reconnect via ensure_future."""
        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.ensure_future") as mock_ensure,
        ):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Trigger disconnect
            broker._on_disconnected()

            # ensure_future should have been called
            mock_ensure.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnecting_flag_prevents_duplicate_reconnect(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """_reconnecting flag prevents duplicate reconnection scheduling."""
        with (
            patch("argus.execution.ibkr_broker.IB", return_value=mock_ib),
            patch("argus.execution.ibkr_broker.asyncio.ensure_future") as mock_ensure,
        ):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Set reconnecting flag manually
            broker._reconnecting = True

            # Trigger disconnect
            broker._on_disconnected()

            # ensure_future should NOT have been called
            mock_ensure.assert_not_called()


# ---------------------------------------------------------------------------
# State Reconstruction Tests (Sprint 13.9)
# ---------------------------------------------------------------------------


class TestIBKRBrokerReconstruction:
    """Tests for IBKRBroker state reconstruction after restart/reconnect."""

    @pytest.mark.asyncio
    async def test_reconstruct_with_positions_and_orders(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """reconstruct_state returns positions and open orders from broker."""
        # Setup: 1 position and 2 open orders
        mock_ib.positions.return_value = [
            _mock_position("AAPL", 100, 150.25),
            _mock_position("NVDA", -50, 875.00),  # Short position
        ]
        mock_ib.openTrades.return_value = [
            _mock_trade(
                order_id=1001,
                symbol="AAPL",
                action="SELL",
                order_type="STP",
                total_qty=100,
                status="Submitted",
                order_ref="01ABC123",  # Has ULID
            ),
            _mock_trade(
                order_id=1002,
                symbol="AAPL",
                action="SELL",
                order_type="LMT",
                total_qty=50,
                status="PreSubmitted",
                order_ref="01DEF456",
            ),
        ]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            result = await broker.reconstruct_state()

            # Verify positions
            assert len(result["positions"]) == 2
            aapl_pos = next(p for p in result["positions"] if p.symbol == "AAPL")
            assert aapl_pos.shares == 100
            assert aapl_pos.entry_price == 150.25

            nvda_pos = next(p for p in result["positions"] if p.symbol == "NVDA")
            assert nvda_pos.shares == 50  # abs(position)
            assert nvda_pos.side.value == "sell"  # Short

            # Verify open orders
            assert len(result["open_orders"]) == 2
            stop_order = next(o for o in result["open_orders"] if o["order_type"] == "stop")
            assert stop_order["order_id"] == "01ABC123"
            assert stop_order["symbol"] == "AAPL"
            assert stop_order["side"] == "sell"

    @pytest.mark.asyncio
    async def test_reconstruct_empty_state(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """reconstruct_state handles empty broker state gracefully."""
        mock_ib.positions.return_value = []
        mock_ib.openTrades.return_value = []

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            result = await broker.reconstruct_state()

            assert result["positions"] == []
            assert result["open_orders"] == []

    @pytest.mark.asyncio
    async def test_ulid_recovery_from_order_ref(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """reconstruct_state recovers ULID mappings from orderRef field."""
        ulid = "01ABCDEF123456789"
        ib_order_id = 9999

        mock_ib.positions.return_value = []
        mock_ib.openTrades.return_value = [
            _mock_trade(
                order_id=ib_order_id,
                symbol="TSLA",
                action="BUY",
                order_type="LMT",
                total_qty=10,
                order_ref=ulid,
            ),
        ]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Before reconstruction, no mappings exist
            assert ulid not in broker._ulid_to_ibkr
            assert ib_order_id not in broker._ibkr_to_ulid

            result = await broker.reconstruct_state()

            # After reconstruction, mappings should exist
            assert broker._ulid_to_ibkr[ulid] == ib_order_id
            assert broker._ibkr_to_ulid[ib_order_id] == ulid
            assert result["open_orders"][0]["order_id"] == ulid

    @pytest.mark.asyncio
    async def test_unknown_orders_get_prefix(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Orders without orderRef get 'unknown_' prefix in reconstruction."""
        ib_order_id = 8888

        mock_ib.positions.return_value = []
        mock_ib.openTrades.return_value = [
            _mock_trade(
                order_id=ib_order_id,
                symbol="META",
                action="SELL",
                order_type="STP",
                total_qty=25,
                order_ref="",  # No ULID
            ),
        ]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            result = await broker.reconstruct_state()

            # Order should have unknown_ prefix
            assert result["open_orders"][0]["order_id"] == f"unknown_{ib_order_id}"

    @pytest.mark.asyncio
    async def test_reconstruction_after_reconnect(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """reconstruct_state works correctly after reconnection."""
        mock_ib.positions.return_value = [_mock_position("GOOG", 20, 175.50)]
        mock_ib.openTrades.return_value = [
            _mock_trade(
                order_id=5555,
                symbol="GOOG",
                action="SELL",
                order_type="STP",
                total_qty=20,
                order_ref="01RECONNECT123",
            ),
        ]

        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            # Simulate reconnection clearing internal state
            broker._ulid_to_ibkr.clear()
            broker._ibkr_to_ulid.clear()

            result = await broker.reconstruct_state()

            # ULID should be recovered from orderRef
            assert "01RECONNECT123" in broker._ulid_to_ibkr
            assert len(result["positions"]) == 1
            assert result["positions"][0].symbol == "GOOG"
            assert result["open_orders"][0]["order_id"] == "01RECONNECT123"
