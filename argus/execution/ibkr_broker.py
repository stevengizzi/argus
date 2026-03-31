"""IBKR Broker adapter.

Production execution broker using Interactive Brokers via ib_async.

Implements the Broker ABC for order submission, fill streaming, account queries,
and position management. Uses native IBKR multi-leg bracket orders (DEC-093).

All market data comes from Databento (DEC-082) — this adapter is execution-only.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

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
    OVERNIGHT_MAINTENANCE_CODES,
    classify_error,
    is_connection_error,
    is_order_rejection,
)
from argus.utils.log_throttle import ThrottledLogger
from argus.models.trading import (
    AccountInfo,
    BracketOrderResult,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    Position,
)
from argus.models.trading import OrderType as TradingOrderType

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

        # Rate-limited logger for high-volume IBKR errors
        self._throttled = ThrottledLogger(logger)

        # Symbols that received IBKR error 404 (qty mismatch on SELL).
        # Order Manager queries this to re-check broker qty before retry.
        self.error_404_symbols: set[str] = set()

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
                "Connected to IB Gateway at %s:%d (clientId=%d, account=%s, positions=%d)",
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
            logger.debug("Ignoring status update for unknown IBKR order #%d", ib_order_id)
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
            logger.info("Order filled: %s — %d @ $%.2f", ulid, filled_qty, avg_fill_price)

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

        Outside market hours (9:30 AM – 4:00 PM ET), overnight maintenance error codes
        (1100, 1102, 2107, 2157) are downgraded to INFO level since connectivity issues
        during IB Gateway nightly maintenance are expected.

        Args:
            req_id: Request ID associated with the error (often IBKR order ID).
            error_code: IBKR error code.
            error_string: Human-readable error message.
            contract: Optional contract associated with the error.
        """
        error_info = classify_error(error_code, error_string)

        # Downgrade overnight maintenance codes outside market hours
        if error_code in OVERNIGHT_MAINTENANCE_CODES and not self._is_market_hours():
            logger.info("IBKR maintenance %d (outside market hours): %s", error_code, error_string)
            return

        # Rate-limit high-volume error codes before general classification
        if error_code == 399:
            symbol = contract.symbol if contract else "unknown"
            self._throttled.warn_throttled(
                f"ibkr_399_{symbol}",
                f"IBKR error 399 ({symbol}): {error_string}",
                interval_seconds=60.0,
            )
            return

        if error_code == 202:
            self._throttled.warn_throttled(
                f"ibkr_202_{req_id}",
                f"IBKR error 202 (orderId={req_id}): {error_string}",
                interval_seconds=86400.0,  # effectively once per orderId
            )
            return

        if error_code == 10148:
            self._throttled.warn_throttled(
                f"ibkr_10148_{req_id}",
                f"IBKR error 10148 (orderId={req_id}): {error_string}",
                interval_seconds=86400.0,  # effectively once per orderId
            )
            return

        # Error 404: qty mismatch on SELL order (Sprint 29.5 R1).
        # Track the symbol so Order Manager can re-query broker qty on next retry.
        if error_code == 404:
            symbol = contract.symbol if contract else "unknown"
            self.error_404_symbols.add(symbol)
            logger.warning(
                "IBKR error 404 (qty mismatch) for %s (orderId=%d): %s",
                symbol,
                req_id,
                error_string,
            )
            return

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

    def _is_market_hours(self) -> bool:
        """Check if current time is within US market hours (9:30 AM – 4:00 PM ET).

        Returns:
            True if currently within market hours, False otherwise.
        """
        et_tz = ZoneInfo("America/New_York")
        now_et = datetime.now(et_tz)
        market_open = time(9, 30)
        market_close = time(16, 0)
        return market_open <= now_et.time() <= market_close

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
        Sets connected flag to False and schedules reconnection if not already
        reconnecting (double-reconnect guard).
        """
        self._connected = False
        logger.warning("IB Gateway disconnected")

        # Double-reconnect guard: only schedule if not already reconnecting
        if not self._reconnecting:
            logger.info("Scheduling reconnection attempt")
            asyncio.ensure_future(self._reconnect())

    async def _reconnect(self) -> None:
        """Reconnect to IB Gateway with exponential backoff.

        Attempts to reconnect up to reconnect_max_retries times using
        exponential backoff with a cap at reconnect_max_delay_seconds.
        After successful reconnection, verifies position consistency.

        If all retries are exhausted, logs CRITICAL error.
        SystemAlertEvent deferred to DEF-014.
        """
        self._reconnecting = True

        # Snapshot pre-disconnect positions for verification
        pre_positions = [(p.contract.symbol, int(p.position)) for p in self._last_known_positions]

        for attempt in range(self._config.reconnect_max_retries):
            # Calculate delay with exponential backoff and cap
            delay = min(
                self._config.reconnect_base_delay_seconds * (2**attempt),
                self._config.reconnect_max_delay_seconds,
            )
            logger.info(
                "Reconnection attempt %d/%d in %.1fs",
                attempt + 1,
                self._config.reconnect_max_retries,
                delay,
            )

            await asyncio.sleep(delay)

            try:
                await self.connect()

                # Verify positions match after reconnection
                post_positions = [
                    (p.contract.symbol, int(p.position)) for p in self._ib.positions()
                ]

                if set(pre_positions) != set(post_positions):
                    logger.warning(
                        "Position mismatch after reconnect! Before: %s, After: %s",
                        pre_positions,
                        post_positions,
                    )
                    # Continue anyway — HealthMonitor will reconcile

                self._reconnecting = False
                logger.info(
                    "Reconnected to IB Gateway (attempt %d)",
                    attempt + 1,
                )
                return

            except Exception as e:
                logger.warning(
                    "Reconnection attempt %d failed: %s",
                    attempt + 1,
                    e,
                )

        # All retries exhausted
        self._reconnecting = False
        logger.critical(
            "Failed to reconnect after %d attempts. "
            "IB Gateway unreachable. Manual intervention required.",
            self._config.reconnect_max_retries,
        )
        # TODO: Publish SystemAlertEvent when available (DEF-014)

    # --- Order Building Helpers ---

    def _round_price(self, price: float, tick_size: float = 0.01) -> float:
        """Round price to minimum tick size for IBKR submission.

        IBKR rejects orders with prices that don't conform to the minimum
        price variation for the contract (Error 110). US equities use $0.01.

        Args:
            price: The raw price to round.
            tick_size: Minimum tick size (default $0.01 for US equities).

        Returns:
            Price rounded to the nearest tick.
        """
        return round(round(price / tick_size) * tick_size, 2)

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
            ib_order = LimitOrder(action, order.quantity, self._round_price(order.limit_price))
        elif order_type == "stop":
            if order.stop_price is None:
                raise ValueError("Stop order requires stop_price")
            ib_order = StopOrder(action, order.quantity, self._round_price(order.stop_price))
        elif order_type == "stop_limit":
            if order.stop_price is None or order.limit_price is None:
                raise ValueError("Stop-limit order requires both stop_price and limit_price")
            ib_order = IBOrder(
                action=action,
                totalQuantity=order.quantity,
                orderType="STP LMT",
                auxPrice=self._round_price(order.stop_price),  # trigger price
                lmtPrice=self._round_price(order.limit_price),  # limit price
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
        stop_ib = StopOrder(exit_action, stop.quantity, self._round_price(stop.stop_price))
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
            t_ib = LimitOrder(exit_action, target.quantity, self._round_price(target.limit_price))
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
        """Cancel an open order by ARGUS ULID.

        Looks up the IBKR order ID from the mapping, finds the Trade
        in ib_async's cache, and submits a cancel request.

        Args:
            order_id: The ARGUS ULID of the order to cancel.

        Returns:
            True if cancellation was submitted, False if order not found.
        """
        ib_order_id = self._ulid_to_ibkr.get(order_id)
        if ib_order_id is None:
            logger.warning("Cannot cancel unknown order: %s", order_id)
            return False

        trade = self._find_trade_by_order_id(ib_order_id)
        if trade is None:
            logger.warning("Cannot find trade for IBKR order #%d", ib_order_id)
            return False

        self._ib.cancelOrder(trade.order)
        logger.info("Cancel requested: %s (IBKR #%d)", order_id, ib_order_id)
        return True

    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify an existing order (price, quantity).

        ib_async pattern: modify the Trade.order object in-place, then re-place it.
        For stop orders, price modifications use auxPrice. For limit orders, lmtPrice.

        Args:
            order_id: The ARGUS ULID of the order to modify.
            modifications: Dict of field names to new values. Supported keys:
                - "price": New price (auxPrice for STP, lmtPrice for others)
                - "quantity": New total quantity

        Returns:
            OrderResult reflecting the modified order state.
        """
        ib_order_id = self._ulid_to_ibkr.get(order_id)
        if ib_order_id is None:
            return OrderResult(
                order_id=order_id,
                status="rejected",
                message="Unknown order",
            )

        trade = self._find_trade_by_order_id(ib_order_id)
        if trade is None:
            return OrderResult(
                order_id=order_id,
                status="rejected",
                message="Trade not found",
            )

        # Apply modifications
        if "price" in modifications:
            # Stop orders use auxPrice, limit orders use lmtPrice
            rounded_price = self._round_price(modifications["price"])
            if trade.order.orderType == "STP":
                trade.order.auxPrice = rounded_price
            else:
                trade.order.lmtPrice = rounded_price

        if "quantity" in modifications:
            trade.order.totalQuantity = modifications["quantity"]

        # Re-place to transmit modification
        self._ib.placeOrder(trade.contract, trade.order)

        logger.info("Order modified: %s — %s", order_id, modifications)
        return OrderResult(
            order_id=order_id,
            status="submitted",
            message="Order modification submitted",
        )

    async def get_positions(self) -> list[Position]:
        """Get current positions from IBKR (auto-synced cache).

        ib_async keeps positions updated automatically after connection.
        Filters out zero-quantity positions (closed positions may remain
        in cache briefly).

        Returns:
            List of Position objects for all non-zero positions.
        """
        from datetime import UTC, datetime

        from argus.models.trading import (
            AssetClass,
            PositionStatus,
        )
        from argus.models.trading import (
            OrderSide as ModelOrderSide,
        )

        ib_positions = self._ib.positions()
        positions = []

        for ib_pos in ib_positions:
            # Filter out zero-quantity positions
            if ib_pos.position == 0:
                continue

            # Determine side from position quantity
            side = ModelOrderSide.BUY if ib_pos.position > 0 else ModelOrderSide.SELL
            shares = abs(int(ib_pos.position))

            position = Position(
                id=generate_id(),
                strategy_id="",  # Unknown at broker level
                symbol=ib_pos.contract.symbol,
                asset_class=AssetClass.US_STOCKS,
                side=side,
                status=PositionStatus.OPEN,
                entry_price=ib_pos.avgCost,
                entry_time=datetime.now(UTC),  # Not available from IBKR position
                shares=shares,
                stop_price=0.0,  # Not available from position object
                target_prices=[],
                current_price=ib_pos.avgCost,  # Approximate, real price via market data
                unrealized_pnl=0.0,  # Available via reqPnLSingle if needed
            )
            positions.append(position)

        logger.info("Retrieved %d positions from IBKR", len(positions))
        return positions

    async def get_account(self) -> AccountInfo:
        """Get account info from IBKR (auto-synced cache).

        ib_async keeps accountValues() updated automatically after connection.
        Filters for USD values and extracts key account metrics.

        Returns:
            AccountInfo snapshot with equity, cash, buying power.
        """
        # Build a dict of USD account values
        values: dict[str, float] = {}
        for av in self._ib.accountValues():
            if av.currency == "USD" and self._is_numeric(av.value):
                values[av.tag] = float(av.value)

        equity = values.get("NetLiquidation", 0.0)
        cash = values.get("TotalCashValue", 0.0)
        buying_power = values.get("BuyingPower", 0.0)

        # Positions value = equity - cash
        positions_value = equity - cash

        logger.debug(
            "Account: equity=$%.2f, cash=$%.2f, buying_power=$%.2f",
            equity,
            cash,
            buying_power,
        )

        return AccountInfo(
            equity=equity,
            cash=cash,
            buying_power=buying_power,
            positions_value=positions_value,
            daily_pnl=0.0,  # Available via reqPnL if needed
        )

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get the current status of a specific order.

        Looks up the Trade in ib_async's cache and maps the IBKR status
        to our OrderStatus enum.

        Args:
            order_id: The ARGUS ULID of the order to check.

        Returns:
            Current OrderStatus enum value.

        Raises:
            KeyError: If the order_id is not found.
        """
        ib_order_id = self._ulid_to_ibkr.get(order_id)
        if ib_order_id is None:
            raise KeyError(f"Order {order_id} not found in ID map")

        trade = self._find_trade_by_order_id(ib_order_id)
        if trade is None:
            raise KeyError(f"Order {order_id} not found at IBKR")

        return self._map_ibkr_status_to_model(trade.orderStatus.status)

    async def get_open_orders(self) -> list[Order]:
        """Get all open (unfilled, not cancelled) orders from IBKR.

        Uses ib_async's openTrades() cache which is auto-updated after connection.

        Returns:
            List of Order objects for all open orders at IBKR.
        """
        open_trades = self._ib.openTrades()
        orders = []

        for trade in open_trades:
            ib_id = trade.order.orderId
            ulid = self._ibkr_to_ulid.get(ib_id)

            # Recover ULID from orderRef if not in mapping
            if ulid is None and trade.order.orderRef:
                ulid = trade.order.orderRef
                self._ulid_to_ibkr[ulid] = ib_id
                self._ibkr_to_ulid[ib_id] = ulid

            # If still no ULID, assign unknown prefix
            if ulid is None:
                ulid = f"unknown_{ib_id}"

            # Map IBKR order type to trading model OrderType
            ib_type = trade.order.orderType
            if ib_type == "MKT":
                order_type = TradingOrderType.MARKET
            elif ib_type == "LMT":
                order_type = TradingOrderType.LIMIT
            elif ib_type == "STP":
                order_type = TradingOrderType.STOP
            elif ib_type == "STP LMT":
                order_type = TradingOrderType.STOP_LIMIT
            else:
                order_type = TradingOrderType.MARKET

            # Map side
            side = OrderSide.BUY if trade.order.action.lower() == "buy" else OrderSide.SELL

            # Extract prices
            stop_price = None
            limit_price = None
            if ib_type == "STP":
                stop_price = trade.order.auxPrice
            elif ib_type == "LMT":
                limit_price = trade.order.lmtPrice
            elif ib_type == "STP LMT":
                stop_price = trade.order.auxPrice
                limit_price = trade.order.lmtPrice

            order = Order(
                id=ulid,
                strategy_id="",  # Unknown at broker level
                symbol=trade.contract.symbol if trade.contract else "",
                side=side,
                order_type=order_type,
                quantity=int(trade.order.totalQuantity),
                stop_price=stop_price,
                limit_price=limit_price,
            )
            orders.append(order)

        logger.info("Retrieved %d open orders from IBKR", len(orders))
        return orders

    async def cancel_all_orders(self) -> int:
        """Cancel all open orders at IBKR via reqGlobalCancel.

        Used during graceful shutdown to prevent orphaned orders.

        Returns:
            Number of open orders that were present before cancellation.
        """
        if not self.is_connected:
            logger.warning("cancel_all_orders: not connected to IB Gateway")
            return 0

        open_trades = self._ib.openTrades()
        count = len(open_trades)
        if count > 0:
            self._ib.reqGlobalCancel()
            # Wait briefly for cancellation confirmations
            await asyncio.sleep(min(5.0, max(1.0, count * 0.5)))
            logger.info("Shutdown: cancelled %d open orders at IBKR", count)
        else:
            logger.info("Shutdown: no open orders to cancel at IBKR")
        return count

    async def flatten_all(self) -> list[OrderResult]:
        """Emergency: cancel all open orders, then close all positions.

        This is the nuclear option. Used by circuit breakers and manual
        emergency shutdown.

        Order of operations:
        1. Cancel all open orders (prevents stops from interfering)
        2. Brief pause for cancellations to process
        3. Submit market orders to close all positions (both long and short)

        Returns:
            List of OrderResults for each closing order.
        """
        results: list[OrderResult] = []

        # Step 1: Cancel all open orders
        self._ib.reqGlobalCancel()
        logger.warning("Emergency flatten: all open orders cancelled")

        # Brief pause for cancellations to process
        await asyncio.sleep(0.5)

        # Step 2: Close all positions
        for ib_pos in self._ib.positions():
            if ib_pos.position == 0:
                continue

            # Determine action: SELL to close long, BUY to close short
            action = "SELL" if ib_pos.position > 0 else "BUY"
            quantity = abs(int(ib_pos.position))

            close_order = MarketOrder(action, quantity)
            close_order.tif = "DAY"
            ulid = generate_id()
            close_order.orderRef = ulid

            # Use SMART routing for close orders to avoid direct routing restrictions
            # (ib_pos.contract may retain fill exchange like ARCA, which triggers error 10311)
            close_contract = self._contracts.get_stock_contract(ib_pos.contract.symbol)

            trade = self._ib.placeOrder(close_contract, close_order)

            # Store mappings
            self._ulid_to_ibkr[ulid] = trade.order.orderId
            self._ibkr_to_ulid[trade.order.orderId] = ulid

            results.append(
                OrderResult(
                    order_id=ulid,
                    broker_order_id=str(trade.order.orderId),
                    status="submitted",
                    message=f"Emergency close: {action} {quantity} {ib_pos.contract.symbol}",
                )
            )
            logger.warning(
                "Emergency close: %s %d %s",
                action,
                quantity,
                ib_pos.contract.symbol,
            )

        return results

    async def reconstruct_state(self) -> dict:
        """Rebuild internal state from IBKR after restart or reconnection.

        Reads positions and open trades from ib_async's cache, recovers
        ULID mappings from the orderRef field on each order, and returns
        a snapshot of broker state for Order Manager reconstruction.

        This method is called during mid-day restart to recover position
        state without requiring a database query.

        Returns:
            Dict with:
                - "positions": List of ARGUS Position objects for open positions
                - "open_orders": List of order dicts with order_id, symbol, side,
                  quantity, order_type, status
        """
        positions = self._ib.positions()
        open_trades = self._ib.openTrades()

        # Recover ULID mappings from orderRef
        recovered = 0
        for trade in open_trades:
            order_ref = trade.order.orderRef
            if order_ref and order_ref not in self._ulid_to_ibkr:
                ib_id = trade.order.orderId
                self._ulid_to_ibkr[order_ref] = ib_id
                self._ibkr_to_ulid[ib_id] = order_ref
                recovered += 1

        if recovered > 0:
            logger.info("Recovered %d ULID mappings from orderRef", recovered)

        # Build open_orders list
        open_orders = []
        for trade in open_trades:
            ib_id = trade.order.orderId
            ulid = self._ibkr_to_ulid.get(ib_id)

            # If no ULID found, assign an unknown_ prefix for tracking
            if ulid is None:
                ulid = f"unknown_{ib_id}"

            open_orders.append(
                {
                    "order_id": ulid,
                    "symbol": trade.contract.symbol if trade.contract else "",
                    "side": trade.order.action.lower(),
                    "quantity": int(trade.order.totalQuantity),
                    "order_type": self._map_ib_order_type(trade.order.orderType).value,
                    "status": trade.orderStatus.status.lower(),
                }
            )

        # Build positions list (filter out zero-quantity)
        converted_positions = [self._convert_position(p) for p in positions if p.position != 0]

        logger.info(
            "Reconstructed state: %d positions, %d open orders",
            len(converted_positions),
            len(open_orders),
        )

        return {
            "positions": converted_positions,
            "open_orders": open_orders,
        }

    def _convert_position(self, ib_pos) -> Position:
        """Convert ib_async position to ARGUS Position model.

        Creates a minimal Position object from IBKR position data.
        Strategy-level fields (strategy_id, stop_price, target_prices)
        are filled in by Order Manager during reconstruction.

        Args:
            ib_pos: An ib_async Position object (from self._ib.positions()).

        Returns:
            ARGUS Position model with broker-available fields populated.
        """
        from datetime import UTC, datetime

        from argus.models.trading import (
            AssetClass,
            PositionStatus,
        )
        from argus.models.trading import (
            OrderSide as ModelOrderSide,
        )

        # Determine side from position quantity
        side = ModelOrderSide.BUY if ib_pos.position > 0 else ModelOrderSide.SELL
        shares = abs(int(ib_pos.position))

        return Position(
            id=generate_id(),
            strategy_id="",  # Unknown at broker level — filled by Order Manager
            symbol=ib_pos.contract.symbol,
            asset_class=AssetClass.US_STOCKS,
            side=side,
            status=PositionStatus.OPEN,
            entry_price=ib_pos.avgCost,
            entry_time=datetime.now(UTC),  # Actual entry time not available from IBKR
            shares=shares,
            stop_price=0.0,  # Not available from position — filled by Order Manager
            target_prices=[],  # Not available from position — filled by Order Manager
            current_price=ib_pos.avgCost,  # Approximate until market data updates
            unrealized_pnl=0.0,  # Available via reqPnLSingle if needed
        )

    # --- Helper Methods ---

    def _find_trade_by_order_id(self, ib_order_id: int) -> Trade | None:
        """Find a Trade object by IBKR order ID from ib_async's cache.

        Scans all trades in ib_async's cache to find the one matching
        the given IBKR order ID.

        Args:
            ib_order_id: The IBKR integer order ID.

        Returns:
            The Trade object if found, None otherwise.
        """
        for trade in self._ib.trades():
            if trade.order.orderId == ib_order_id:
                return trade
        return None

    @staticmethod
    def _is_numeric(value: str) -> bool:
        """Check if a string value can be converted to float.

        Used for filtering accountValues which may contain non-numeric entries.

        Args:
            value: The string value to check.

        Returns:
            True if the value can be converted to float, False otherwise.
        """
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _map_ibkr_status_to_model(ibkr_status: str) -> OrderStatus:
        """Map IBKR order status string to our OrderStatus enum.

        Args:
            ibkr_status: IBKR status string (Submitted, Filled, Cancelled, etc.)

        Returns:
            Corresponding OrderStatus enum value.
        """
        status_lower = ibkr_status.lower()
        if status_lower in ("submitted", "presubmitted", "pendingsubmit"):
            return OrderStatus.SUBMITTED
        elif status_lower in ("filled",):
            return OrderStatus.FILLED
        elif status_lower in ("cancelled", "pendingcancel"):
            return OrderStatus.CANCELLED
        elif status_lower in ("inactive",):
            return OrderStatus.REJECTED
        else:
            # Default to submitted for unknown statuses
            return OrderStatus.SUBMITTED
