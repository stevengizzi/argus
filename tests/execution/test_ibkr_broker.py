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
