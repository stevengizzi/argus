"""Tests for IBKRBroker adapter.

Tests cover connection management, order submission, fill streaming,
cancel/modify, account queries, and flatten operations.
"""

from __future__ import annotations

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


def _mock_account_value(
    tag: str, value: str, currency: str, account: str
) -> MagicMock:
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

            order = _create_order(
                order_type="limit", quantity=50, limit_price=150.50
            )
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

            order = _create_order(
                side="sell", order_type="stop", quantity=75, stop_price=145.00
            )
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

            entry, stop, targets = _create_bracket_orders(
                t1_price=155.00, t1_quantity=50
            )
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
            assert stop_order.transmit is True, (
                "Stop should have transmit=True when no targets"
            )

            # Entry should still have transmit=False
            entry_call = mock_ib.placeOrder.call_args_list[0]
            entry_order = entry_call[0][1]
            assert entry_order.transmit is False
