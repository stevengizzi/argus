"""IBKR Broker adapter.

Production execution broker using Interactive Brokers via ib_async.

Implements the Broker ABC for order submission, fill streaming, account queries,
and position management. Uses native IBKR multi-leg bracket orders (DEC-093).

All market data comes from Databento (DEC-082) — this adapter is execution-only.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from ib_async import IB, LimitOrder, MarketOrder, StopOrder
from ib_async import Order as IBOrder

from argus.core.config import IBKRConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderSubmittedEvent,
    OrderType,
    Side,
)
from argus.core.ids import generate_id
from argus.execution.broker import Broker
from argus.execution.ibkr_contracts import IBKRContractResolver
from argus.execution.ibkr_errors import (
    IBKRErrorSeverity,
    classify_error,
    is_connection_error,
    is_order_rejection,
)
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
        Schedules async handler as a task to allow async Event Bus publishing.

        Note: ib_async is asyncio-native (not threaded), so we can use
        ensure_future directly without call_soon_threadsafe.

        Args:
            trade: The Trade object with updated status.
        """
        asyncio.ensure_future(self._handle_order_status(trade))

    async def _handle_order_status(self, trade: Trade) -> None:
        """Process order status update and publish to Event Bus.

        Maps IBKR order statuses to ARGUS events:
        - "Filled" → OrderFilledEvent (with avg fill price and filled quantity)
        - "Cancelled" → OrderCancelledEvent
        - "Inactive" → OrderCancelledEvent (IBKR uses Inactive for rejections)
        - "Submitted" → OrderSubmittedEvent
        - "PreSubmitted" → debug log only (bracket children before parent fills)
        - Other → debug log

        Args:
            trade: The Trade object with updated status.
        """
        ib_order_id = trade.order.orderId
        ulid = self._ibkr_to_ulid.get(ib_order_id)

        if not ulid:
            # Not our order — could be pre-existing from TWS, or external
            logger.debug(
                "Ignoring status update for unknown IBKR order #%d", ib_order_id
            )
            return

        status = trade.orderStatus.status

        if status == "Filled":
            avg_fill_price = trade.orderStatus.avgFillPrice
            filled_qty = int(trade.orderStatus.filled)

            await self._event_bus.publish(
                OrderFilledEvent(
                    order_id=ulid,
                    fill_price=avg_fill_price,
                    fill_quantity=filled_qty,
                )
            )
            logger.info(
                "Order filled: %s — %d @ $%.2f", ulid, filled_qty, avg_fill_price
            )

        elif status == "Cancelled":
            await self._event_bus.publish(
                OrderCancelledEvent(
                    order_id=ulid,
                    reason=f"Cancelled (IBKR status: {status})",
                )
            )
            logger.info("Order cancelled: %s", ulid)

        elif status == "Inactive":
            # Inactive = rejected by IBKR (insufficient margin, invalid price, etc.)
            why_held = trade.orderStatus.whyHeld or "unknown reason"
            reason = f"Order rejected by IBKR: {why_held}"
            await self._event_bus.publish(
                OrderCancelledEvent(
                    order_id=ulid,
                    reason=reason,
                )
            )
            logger.warning("Order rejected: %s — %s", ulid, reason)

        elif status == "Submitted":
            # Map IBKR order type and side
            side_str = trade.order.action.lower()
            side = Side.LONG if side_str == "buy" else Side.SHORT
            order_type = self._map_ib_order_type(trade.order.orderType)

            await self._event_bus.publish(
                OrderSubmittedEvent(
                    order_id=ulid,
                    strategy_id="",  # Filled by Order Manager from context
                    symbol=trade.contract.symbol if trade.contract else "",
                    side=side,
                    quantity=int(trade.order.totalQuantity),
                    order_type=order_type,
                )
            )
            logger.debug("Order submitted: %s (IBKR #%d)", ulid, ib_order_id)

        elif status == "PreSubmitted":
            # Bracket children before parent fills — normal, just log
            logger.debug("Order pre-submitted: %s (IBKR #%d)", ulid, ib_order_id)

        else:
            # PendingSubmit, PendingCancel — transient states, log only
            logger.debug("Order status: %s → %s", ulid, status)

    def _on_error(
        self,
        req_id: int,
        error_code: int,
        error_string: str,
        contract: Contract | None = None,
    ) -> None:
        """Handle error events from ib_async.

        Classifies errors by severity and routes appropriately:
        - CRITICAL: Log at critical level. Connection errors handled by _on_disconnected.
        - WARNING: Log at warning level. Order rejections publish OrderCancelledEvent.
        - INFO: Log at debug level (suppress noise from market data messages).

        Args:
            req_id: Request ID associated with the error (often IBKR order ID).
            error_code: IBKR error code.
            error_string: Human-readable error message.
            contract: Optional contract associated with the error.
        """
        error_info = classify_error(error_code, error_string)

        if error_info.severity == IBKRErrorSeverity.CRITICAL:
            logger.critical("IBKR error %d: %s", error_code, error_string)
            if is_connection_error(error_code):
                # Connection errors trigger reconnection (handled by _on_disconnected)
                pass

        elif error_info.severity == IBKRErrorSeverity.WARNING:
            logger.warning("IBKR error %d: %s", error_code, error_string)
            if is_order_rejection(error_code) and req_id in self._ibkr_to_ulid:
                ulid = self._ibkr_to_ulid[req_id]
                asyncio.ensure_future(
                    self._event_bus.publish(
                        OrderCancelledEvent(
                            order_id=ulid,
                            reason=f"IBKR rejected: {error_string}",
                        )
                    )
                )

        else:
            # INFO severity — debug log only (e.g., market data not subscribed)
            logger.debug("IBKR info %d: %s", error_code, error_string)

    @staticmethod
    def _map_ib_order_type(ib_type: str) -> OrderType:
        """Map IBKR order type string to ARGUS OrderType enum.

        Args:
            ib_type: IBKR order type string (MKT, LMT, STP, STP LMT).

        Returns:
            Corresponding ARGUS OrderType enum value.
        """
        mapping = {
            "MKT": OrderType.MARKET,
            "LMT": OrderType.LIMIT,
            "STP": OrderType.STOP,
            "STP LMT": OrderType.STOP_LIMIT,
        }
        return mapping.get(ib_type, OrderType.MARKET)

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
        """Submit a bracket order to IBKR with native multi-leg support (DEC-093).

        IBKR brackets: parent (entry) + children (stop + targets) linked via parentId.
        All children are submitted atomically. If parent is cancelled, all children
        are auto-cancelled by IBKR.

        The transmit flag pattern ensures atomic submission:
        - parent.transmit = False
        - stop.transmit = False (if targets exist) or True (if no targets)
        - targets[:-1].transmit = False
        - targets[-1].transmit = True (triggers atomic submission of entire group)

        Args:
            entry: Entry order (market or limit).
            stop: Stop-loss order for total shares.
            targets: List of take-profit orders [T1] or [T1, T2]. Can be empty.

        Returns:
            BracketOrderResult with all order IDs (entry, stop, targets).
        """
        if not self.is_connected:
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

        contract = self._contracts.get_stock_contract(entry.symbol)
        action = "BUY" if entry.side.lower() == "buy" else "SELL"
        exit_action = "SELL" if action == "BUY" else "BUY"

        # --- Build parent order (entry) ---
        parent = self._build_ib_order(entry)
        parent.transmit = False  # Don't transmit until last child

        # Generate ULID for entry
        entry_ulid = generate_id()
        parent.orderRef = entry_ulid

        # Place parent first to get orderId
        parent_trade = self._ib.placeOrder(contract, parent)
        parent_id = parent_trade.order.orderId
        self._ulid_to_ibkr[entry_ulid] = parent_id
        self._ibkr_to_ulid[parent_id] = entry_ulid

        entry_result = OrderResult(
            order_id=entry_ulid,
            broker_order_id=str(parent_id),
            status="submitted",
        )

        # --- Build stop-loss child ---
        stop_ulid = generate_id()
        if stop.stop_price is None:
            raise ValueError("Stop order requires stop_price")
        stop_ib = StopOrder(exit_action, stop.quantity, stop.stop_price)
        stop_ib.parentId = parent_id
        stop_ib.tif = "DAY"
        stop_ib.outsideRth = False
        stop_ib.orderRef = stop_ulid

        # Determine if stop is the last order (transmit=True) or not
        has_targets = len(targets) > 0
        stop_ib.transmit = not has_targets  # Transmit only if no targets follow

        stop_trade = self._ib.placeOrder(contract, stop_ib)
        stop_actual_id = stop_trade.order.orderId
        self._ulid_to_ibkr[stop_ulid] = stop_actual_id
        self._ibkr_to_ulid[stop_actual_id] = stop_ulid

        stop_result = OrderResult(
            order_id=stop_ulid,
            broker_order_id=str(stop_actual_id),
            status="submitted",
        )

        # --- Build target children (T1, optionally T2) ---
        target_results: list[OrderResult] = []
        for i, target in enumerate(targets):
            t_ulid = generate_id()
            is_last = i == len(targets) - 1

            if target.limit_price is None:
                raise ValueError("Target order requires limit_price")
            t_ib = LimitOrder(exit_action, target.quantity, target.limit_price)
            t_ib.parentId = parent_id
            t_ib.tif = "DAY"
            t_ib.outsideRth = False
            t_ib.orderRef = t_ulid
            t_ib.transmit = is_last  # Last child transmits the entire bracket

            t_trade = self._ib.placeOrder(contract, t_ib)
            t_actual_id = t_trade.order.orderId
            self._ulid_to_ibkr[t_ulid] = t_actual_id
            self._ibkr_to_ulid[t_actual_id] = t_ulid

            target_results.append(
                OrderResult(
                    order_id=t_ulid,
                    broker_order_id=str(t_actual_id),
                    status="submitted",
                )
            )

        # Build log message
        target_ulids = [r.order_id for r in target_results]
        logger.info(
            "Bracket placed: entry=%s (IBKR #%d), stop=%s, targets=%s — %s %d %s",
            entry_ulid,
            parent_id,
            stop_ulid,
            target_ulids,
            action,
            entry.quantity,
            entry.symbol,
        )

        return BracketOrderResult(
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

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
