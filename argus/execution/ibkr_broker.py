"""IBKR Broker adapter.

Production execution broker using Interactive Brokers via ib_async.

Implements the Broker ABC for order submission, fill streaming, account queries,
and position management. Uses native IBKR multi-leg bracket orders (DEC-093).

All market data comes from Databento (DEC-082) — this adapter is execution-only.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ib_async import IB, LimitOrder, MarketOrder, StopOrder
from ib_async import Order as IBOrder

from argus.core.config import IBKRConfig
from argus.core.event_bus import EventBus
from argus.core.ids import generate_id
from argus.execution.broker import Broker
from argus.execution.ibkr_contracts import IBKRContractResolver
from argus.models.trading import (
    AccountInfo,
    BracketOrderResult,
    Order,
    OrderResult,
    OrderStatus,
    Position,
)

if TYPE_CHECKING:
    from ib_async import Contract, Trade

logger = logging.getLogger(__name__)


class IBKRBroker(Broker):
    """Production execution broker using Interactive Brokers via ib_async.

    Implements the Broker ABC for order submission, fill streaming, account queries,
    and position management. Uses native IBKR multi-leg bracket orders (DEC-093).

    All market data comes from Databento (DEC-082) — this adapter is execution-only.

    Args:
        config: IBKRConfig with connection parameters.
        event_bus: EventBus for publishing fill/cancel events.

    Attributes:
        _config: IBKR connection configuration.
        _event_bus: Event bus for publishing events.
        _ib: ib_async IB client instance.
        _connected: Internal connection state flag.
        _reconnecting: Flag to prevent reconnection loops.
        _ulid_to_ibkr: Mapping from ARGUS ULID to IBKR order ID.
        _ibkr_to_ulid: Mapping from IBKR order ID to ARGUS ULID.
        _contracts: Contract resolver for symbol → Contract mapping.
        _last_known_positions: Snapshot of positions for reconnection verification.
    """

    def __init__(self, config: IBKRConfig, event_bus: EventBus) -> None:
        """Initialize IBKRBroker with configuration and event bus.

        Creates the IB client instance, wires up event subscriptions,
        and initializes order ID mapping dictionaries.

        Args:
            config: IBKRConfig with host, port, client_id, account, etc.
            event_bus: EventBus for publishing OrderFilledEvent, OrderCancelledEvent, etc.
        """
        self._config = config
        self._event_bus = event_bus
        self._ib = IB()
        self._connected = False
        self._reconnecting = False

        # Order ID mapping: ARGUS ULID ↔ IBKR integer orderId
        self._ulid_to_ibkr: dict[str, int] = {}
        self._ibkr_to_ulid: dict[int, str] = {}

        # Contract resolver
        self._contracts = IBKRContractResolver()

        # Last known positions (for reconnection verification)
        self._last_known_positions: list = []

        # Wire up ib_async events
        # Note: ib_async is asyncio-native — NO call_soon_threadsafe() needed
        # (unlike Databento Sprint 12). Event handlers fire on the same event loop.
        self._ib.orderStatusEvent += self._on_order_status
        self._ib.errorEvent += self._on_error
        self._ib.disconnectedEvent += self._on_disconnected

    # --- Connection Management ---

    async def connect(self) -> None:
        """Connect to IB Gateway/TWS.

        Establishes connection using ib_async's connectAsync() method.
        On successful connection, snapshots current positions for
        reconnection verification.

        Raises:
            ConnectionError: If connection cannot be established.
        """
        try:
            await self._ib.connectAsync(
                host=self._config.host,
                port=self._config.port,
                clientId=self._config.client_id,
                timeout=self._config.timeout_seconds,
                readonly=self._config.readonly,
                account=self._config.account or "",
            )
            self._connected = True
            # Snapshot positions for reconnection verification
            self._last_known_positions = list(self._ib.positions())
            logger.info(
                "Connected to IB Gateway at %s:%d "
                "(clientId=%d, account=%s, positions=%d)",
                self._config.host,
                self._config.port,
                self._config.client_id,
                self._config.account or "(default)",
                len(self._last_known_positions),
            )
        except Exception as e:
            self._connected = False
            logger.error("Failed to connect to IB Gateway: %s", e)
            raise ConnectionError(f"Failed to connect to IB Gateway: {e}") from e

    async def disconnect(self) -> None:
        """Gracefully disconnect from IB Gateway.

        Closes the connection and updates internal state.
        """
        if self._ib.isConnected():
            self._ib.disconnect()
        self._connected = False
        logger.info("Disconnected from IB Gateway")

    @property
    def is_connected(self) -> bool:
        """Check if broker is connected.

        Returns True only if both internal state flag AND ib_async
        report connected status.

        Returns:
            True if connected to IB Gateway.
        """
        return self._connected and self._ib.isConnected()

    # --- Event Handlers (wired in __init__) ---

    def _on_order_status(self, trade: Trade) -> None:
        """Handle order status updates from ib_async.

        Called by ib_async on the asyncio event loop when order status changes.
        This is a placeholder that will be fully implemented in Prompt 6.

        Args:
            trade: The Trade object with updated status.
        """
        # Placeholder - will be implemented in Prompt 6 (Fill Streaming)
        logger.debug("Order status update: %s", trade.order.orderId)

    def _on_error(
        self,
        req_id: int,
        error_code: int,
        error_string: str,
        contract: Contract | None = None,
    ) -> None:
        """Handle error events from ib_async.

        Called by ib_async on the asyncio event loop when errors occur.
        This is a placeholder that will be fully implemented in Prompt 8.

        Args:
            req_id: Request ID associated with the error.
            error_code: IBKR error code.
            error_string: Human-readable error message.
            contract: Optional contract associated with the error.
        """
        # Placeholder - will be implemented in Prompt 8 (Error Handling)
        logger.debug("IBKR error %d: %s", error_code, error_string)

    def _on_disconnected(self) -> None:
        """Handle disconnection event from ib_async.

        Called when the connection to IB Gateway is lost.
        This is a placeholder that will trigger reconnection in Prompt 8.
        """
        self._connected = False
        logger.warning("IB Gateway disconnected")

    # --- Order Building Helpers ---

    def _build_ib_order(self, order: Order) -> IBOrder:
        """Convert ARGUS Order model to ib_async Order object.

        Maps ARGUS order types to ib_async order classes:
        - market → MarketOrder
        - limit → LimitOrder
        - stop → StopOrder
        - stop_limit → IBOrder with orderType="STP LMT"

        All orders have tif="DAY" and outsideRth=False for intraday strategies.

        Args:
            order: The ARGUS Order to convert.

        Returns:
            An ib_async Order object ready for submission.

        Raises:
            ValueError: If the order type is not supported.
        """
        action = "BUY" if order.side.lower() == "buy" else "SELL"
        order_type = order.order_type.lower()

        if order_type == "market":
            ib_order = MarketOrder(action, order.quantity)
        elif order_type == "limit":
            if order.limit_price is None:
                raise ValueError("Limit order requires limit_price")
            ib_order = LimitOrder(action, order.quantity, order.limit_price)
        elif order_type == "stop":
            if order.stop_price is None:
                raise ValueError("Stop order requires stop_price")
            ib_order = StopOrder(action, order.quantity, order.stop_price)
        elif order_type == "stop_limit":
            if order.stop_price is None or order.limit_price is None:
                raise ValueError("Stop-limit order requires both stop_price and limit_price")
            ib_order = IBOrder(
                action=action,
                totalQuantity=order.quantity,
                orderType="STP LMT",
                auxPrice=order.stop_price,  # trigger price
                lmtPrice=order.limit_price,  # limit price
            )
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        # Common settings for all order types
        ib_order.tif = "DAY"  # Intraday strategies — DAY orders only
        ib_order.outsideRth = False  # No pre/post-market trading

        return ib_order

    # --- Broker ABC Implementation ---

    async def place_order(self, order: Order) -> OrderResult:
        """Submit a single order to IBKR.

        Maps ARGUS Order to ib_async Order, generates a ULID for tracking,
        stores the orderRef on the IBKR side for reconstruction, and
        maintains bidirectional ID mappings.

        Args:
            order: The ARGUS Order to place.

        Returns:
            OrderResult with submission status and order IDs.
        """
        if not self.is_connected:
            return OrderResult(
                order_id="",
                status="rejected",
                message="Not connected to IB Gateway",
            )

        # Resolve contract for the symbol
        contract = self._contracts.get_stock_contract(order.symbol)

        # Build ib_async order
        ib_order = self._build_ib_order(order)

        # Generate ULID and store in orderRef for reconstruction
        ulid = generate_id()
        ib_order.orderRef = ulid

        # Place order via ib_async
        trade = self._ib.placeOrder(contract, ib_order)

        # Store bidirectional mapping (ULID ↔ IBKR orderId)
        actual_id = trade.order.orderId
        self._ulid_to_ibkr[ulid] = actual_id
        self._ibkr_to_ulid[actual_id] = ulid

        logger.info(
            "Order placed: %s → IBKR #%d %s %d %s %s",
            ulid,
            actual_id,
            order.side.upper(),
            order.quantity,
            order.symbol,
            order.order_type.upper(),
        )

        return OrderResult(
            order_id=ulid,
            broker_order_id=str(actual_id),
            status="submitted",
        )

    async def place_bracket_order(
        self,
        entry: Order,
        stop: Order,
        targets: list[Order],
    ) -> BracketOrderResult:
        """Submit a bracket order to IBKR with native multi-leg support.

        Stub implementation — will be completed in Prompt 5.

        Args:
            entry: Entry order (market or limit).
            stop: Stop-loss order.
            targets: List of take-profit orders [T1] or [T1, T2].

        Returns:
            BracketOrderResult with all order IDs.
        """
        if not self.is_connected:
            # BracketOrderResult requires entry/stop/targets, can't return error directly
            # Return a rejected entry result to indicate connection error
            error_result = OrderResult(
                order_id="",
                status="rejected",
                message="Not connected to IB Gateway",
            )
            return BracketOrderResult(
                entry=error_result,
                stop=error_result,
                targets=[],
            )
        # Placeholder - will be implemented in Prompt 5
        raise NotImplementedError("place_bracket_order will be implemented in Prompt 5")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order.

        Stub implementation — will be completed in Prompt 7.

        Args:
            order_id: The ARGUS ULID of the order to cancel.

        Returns:
            True if cancellation was submitted.
        """
        # Placeholder - will be implemented in Prompt 7
        raise NotImplementedError("cancel_order will be implemented in Prompt 7")

    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify an existing order.

        Stub implementation — will be completed in Prompt 7.

        Args:
            order_id: The ARGUS ULID of the order to modify.
            modifications: Dict of field names to new values.

        Returns:
            OrderResult reflecting the modified order state.
        """
        # Placeholder - will be implemented in Prompt 7
        raise NotImplementedError("modify_order will be implemented in Prompt 7")

    async def get_positions(self) -> list[Position]:
        """Get all currently open positions.

        Stub implementation — will be completed in Prompt 7.

        Returns:
            List of open Position objects.
        """
        # Placeholder - will be implemented in Prompt 7
        raise NotImplementedError("get_positions will be implemented in Prompt 7")

    async def get_account(self) -> AccountInfo:
        """Get current account information.

        Stub implementation — will be completed in Prompt 7.

        Returns:
            AccountInfo snapshot with equity, cash, buying power.
        """
        # Placeholder - will be implemented in Prompt 7
        raise NotImplementedError("get_account will be implemented in Prompt 7")

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get the current status of a specific order.

        Stub implementation — will be completed in Prompt 7.

        Args:
            order_id: The ARGUS ULID of the order to check.

        Returns:
            Current OrderStatus.
        """
        # Placeholder - will be implemented in Prompt 7
        raise NotImplementedError("get_order_status will be implemented in Prompt 7")

    async def flatten_all(self) -> list[OrderResult]:
        """Emergency: close all open positions.

        Stub implementation — will be completed in Prompt 7.

        Returns:
            List of OrderResults for each closing order.
        """
        # Placeholder - will be implemented in Prompt 7
        raise NotImplementedError("flatten_all will be implemented in Prompt 7")
