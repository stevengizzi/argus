"""Live broker adapter using Alpaca's Trading API.

Implements the Broker ABC using alpaca-py's TradingClient (REST) and
TradingStream (WebSocket for order updates). Supports paper and live trading.

Usage:
    config = AlpacaConfig(paper=True)
    broker = AlpacaBroker(event_bus, config)
    await broker.connect()
    result = await broker.place_order(order)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce
from alpaca.trading.requests import (
    LimitOrderRequest,
    MarketOrderRequest,
    ReplaceOrderRequest,
    StopLimitOrderRequest,
    StopOrderRequest,
)
from alpaca.trading.stream import TradingStream

from argus.core.config import AlpacaConfig
from argus.core.event_bus import EventBus
from argus.core.events import OrderCancelledEvent, OrderFilledEvent, OrderSubmittedEvent
from argus.core.ids import generate_id
from argus.execution.broker import Broker
from argus.models.trading import (
    AccountInfo,
    AssetClass,
    BracketOrderResult,
    Order,
    OrderResult,
    OrderType,
    Position,
    PositionStatus,
)
from argus.models.trading import (
    OrderSide as ModelOrderSide,
)
from argus.models.trading import (
    OrderStatus as ModelOrderStatus,
)

logger = logging.getLogger(__name__)


class AlpacaBroker(Broker):
    """Live broker adapter using Alpaca's Trading API (paper or live).

    Uses alpaca-py's TradingClient for REST operations and TradingStream
    for real-time order status updates via WebSocket.

    Args:
        event_bus: Event Bus for publishing order/position events.
        config: Alpaca configuration (API keys, paper mode, etc.).
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: AlpacaConfig,
    ) -> None:
        self._event_bus = event_bus
        self._config = config
        self._trading_client: TradingClient | None = None
        self._trading_stream: TradingStream | None = None
        self._stream_task: asyncio.Task | None = None
        self._connected: bool = False
        self._order_id_map: dict[str, str] = {}  # our_ulid → alpaca_uuid
        self._reverse_id_map: dict[str, str] = {}  # alpaca_uuid → our_ulid

    async def connect(self) -> None:
        """Initialize TradingClient and TradingStream.

        Reads API keys from environment variables, initializes both clients,
        subscribes to trade updates, and starts the WebSocket stream.

        Raises:
            ConnectionError: If API keys are missing or connection fails.
        """
        if self._connected:
            logger.warning("AlpacaBroker already connected. Skipping reconnect.")
            return

        # Read API keys from environment
        api_key = os.getenv(self._config.api_key_env)
        secret_key = os.getenv(self._config.secret_key_env)

        if not api_key or not secret_key:
            msg = (
                f"Alpaca API keys not found. Set {self._config.api_key_env} "
                f"and {self._config.secret_key_env} environment variables."
            )
            logger.error(msg)
            raise ConnectionError(msg)

        # Initialize REST client
        self._trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=self._config.paper,
        )
        logger.info(f"AlpacaBroker TradingClient initialized (paper={self._config.paper})")

        # Initialize WebSocket stream
        self._trading_stream = TradingStream(
            api_key=api_key,
            secret_key=secret_key,
            paper=self._config.paper,
        )
        self._trading_stream.subscribe_trade_updates(self._on_trade_update)
        logger.info("AlpacaBroker TradingStream subscribed to trade_updates")

        # Start WebSocket stream as background task
        self._stream_task = asyncio.create_task(self._run_stream())
        self._connected = True
        logger.info("AlpacaBroker connected successfully")

    async def disconnect(self) -> None:
        """Close WebSocket connection and clean up."""
        if not self._connected:
            logger.warning("AlpacaBroker not connected. Skipping disconnect.")
            return

        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                logger.info("AlpacaBroker stream task cancelled")

        if self._trading_stream:
            await self._trading_stream.close()
            logger.info("AlpacaBroker TradingStream closed")

        self._connected = False
        self._trading_client = None
        self._trading_stream = None
        self._stream_task = None
        logger.info("AlpacaBroker disconnected")

    async def _run_stream(self) -> None:
        """Run the TradingStream WebSocket connection.

        This coroutine runs until cancelled. It calls TradingStream.run()
        which blocks until the connection is closed.
        """
        if not self._trading_stream:
            return

        try:
            logger.info("AlpacaBroker starting WebSocket stream")
            await self._trading_stream._run_forever()  # Runs until cancelled
        except asyncio.CancelledError:
            logger.info("AlpacaBroker WebSocket stream cancelled")
        except Exception as e:
            logger.error(f"AlpacaBroker WebSocket stream error: {e}", exc_info=True)

    async def _on_trade_update(self, data: object) -> None:
        """Handler for Alpaca's trade_updates WebSocket stream.

        Alpaca sends events: new, fill, partial_fill, canceled, expired,
        replaced, rejected, pending_cancel, etc.

        Mapping to our events:
        - 'new' → OrderSubmittedEvent
        - 'fill' → OrderFilledEvent
        - 'partial_fill' → OrderFilledEvent
        - 'canceled' → OrderCancelledEvent
        - 'expired' → OrderCancelledEvent
        - 'rejected' → OrderCancelledEvent

        Args:
            data: Alpaca TradeUpdate object from WebSocket.
        """
        if not hasattr(data, "event") or not hasattr(data, "order"):
            logger.warning(f"AlpacaBroker received invalid trade update: {data}")
            return

        event_type = data.event
        order = data.order
        alpaca_order_id = str(order.id)
        our_order_id = self._reverse_id_map.get(alpaca_order_id)

        if not our_order_id:
            logger.warning(
                f"AlpacaBroker received trade update for unknown order: {alpaca_order_id}"
            )
            return

        timestamp = datetime.now(UTC)

        # Handle different event types
        if event_type == "new":
            # Order submitted to broker
            event = OrderSubmittedEvent(
                timestamp=timestamp,
                order_id=our_order_id,
                strategy_id="",  # Unknown at this level
                symbol=order.symbol,
                side=self._map_side_to_model(order.side),
                quantity=int(order.qty) if order.qty else 0,
                order_type=self._map_order_type_to_model(order.order_type),
            )
            await self._event_bus.publish(event)
            logger.debug(f"OrderSubmittedEvent published: {our_order_id}")

        elif event_type in ("fill", "partial_fill"):
            # Order filled (fully or partially)
            filled_qty = int(order.filled_qty) if order.filled_qty else 0
            filled_price = float(order.filled_avg_price) if order.filled_avg_price else 0.0

            event = OrderFilledEvent(
                timestamp=timestamp,
                order_id=our_order_id,
                fill_price=filled_price,
                fill_quantity=filled_qty,
            )
            await self._event_bus.publish(event)
            logger.info(
                f"OrderFilledEvent published: {our_order_id} ({filled_qty} @ ${filled_price:.2f})"
            )

        elif event_type in ("canceled", "expired", "rejected"):
            # Order cancelled or rejected
            reason = event_type
            if event_type == "rejected" and hasattr(order, "reject_reason"):
                reason = f"rejected: {order.reject_reason}"

            event = OrderCancelledEvent(
                timestamp=timestamp,
                order_id=our_order_id,
                reason=reason,
            )
            await self._event_bus.publish(event)
            logger.info(f"OrderCancelledEvent published: {our_order_id} ({reason})")

        elif event_type == "replaced":
            # Order modification confirmed
            logger.debug(f"Order {our_order_id} replaced successfully")

        else:
            logger.warning(f"AlpacaBroker unhandled trade event: {event_type}")

    async def place_order(self, order: Order) -> OrderResult:
        """Submit a single order to Alpaca.

        Maps our Order model to Alpaca's MarketOrderRequest/LimitOrderRequest/
        StopOrderRequest based on order.order_type.

        Args:
            order: The order to place.

        Returns:
            OrderResult with Alpaca's order ID mapped to our order_id.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        # Map side
        alpaca_side = self._map_side_to_alpaca(order.side)

        # Map time in force
        tif = self._map_time_in_force(order.time_in_force)

        # Build request based on order type
        if order.order_type == OrderType.MARKET:
            request = MarketOrderRequest(
                symbol=order.symbol,
                qty=order.quantity,
                side=alpaca_side,
                time_in_force=tif,
            )
        elif order.order_type == OrderType.LIMIT:
            if not order.limit_price:
                raise ValueError("Limit order requires limit_price")
            request = LimitOrderRequest(
                symbol=order.symbol,
                qty=order.quantity,
                side=alpaca_side,
                time_in_force=tif,
                limit_price=order.limit_price,
            )
        elif order.order_type == OrderType.STOP:
            if not order.stop_price:
                raise ValueError("Stop order requires stop_price")
            request = StopOrderRequest(
                symbol=order.symbol,
                qty=order.quantity,
                side=alpaca_side,
                time_in_force=tif,
                stop_price=order.stop_price,
            )
        elif order.order_type == OrderType.STOP_LIMIT:
            if not order.stop_price or not order.limit_price:
                raise ValueError("Stop-limit order requires stop_price and limit_price")
            request = StopLimitOrderRequest(
                symbol=order.symbol,
                qty=order.quantity,
                side=alpaca_side,
                time_in_force=tif,
                stop_price=order.stop_price,
                limit_price=order.limit_price,
            )
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        # Submit order to Alpaca
        try:
            alpaca_order = self._trading_client.submit_order(request)
            alpaca_order_id = str(alpaca_order.id)

            # Store order ID mapping
            self._order_id_map[order.id] = alpaca_order_id
            self._reverse_id_map[alpaca_order_id] = order.id

            logger.info(
                f"Order submitted to Alpaca: {order.symbol} {order.side} "
                f"{order.quantity} @ {order.order_type} "
                f"(our_id={order.id}, alpaca_id={alpaca_order_id})"
            )

            return OrderResult(
                order_id=order.id,
                broker_order_id=alpaca_order_id,
                status=ModelOrderStatus.SUBMITTED,
                message="Order submitted to Alpaca",
            )
        except Exception as e:
            logger.error(f"Failed to submit order to Alpaca: {e}", exc_info=True)
            return OrderResult(
                order_id=order.id,
                status=ModelOrderStatus.REJECTED,
                message=f"Alpaca order submission failed: {e}",
            )

    async def place_bracket_order(
        self,
        entry: Order,
        stop: Order,
        targets: list[Order],
    ) -> BracketOrderResult:
        """Submit a bracket order (entry + stop + take-profit) to Alpaca.

        Path A (Sprint 4a): Submit a single bracket order using T1 as
        the take-profit for the full position. The Order Manager (Sprint 4b)
        will later handle the T1/T2 split by modifying the order after T1 hits.

        Alpaca's native bracket order only supports a single take-profit level.

        Args:
            entry: The entry order.
            stop: The stop-loss order.
            targets: Profit target orders (only first target is used).

        Returns:
            BracketOrderResult with results for entry, stop, and targets.

        Raises:
            ConnectionError: If not connected.
            ValueError: If entry is not market order or targets is empty.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        if entry.order_type != OrderType.MARKET:
            raise ValueError("Alpaca bracket orders require market entry order")

        if not targets:
            raise ValueError("Bracket order requires at least one target")

        if not stop.stop_price:
            raise ValueError("Bracket order requires stop_price on stop order")

        if not targets[0].limit_price:
            raise ValueError("Bracket order requires limit_price on target order")

        # Map side
        alpaca_side = self._map_side_to_alpaca(entry.side)

        # Map time in force
        tif = self._map_time_in_force(entry.time_in_force)

        # Build bracket order request (using first target only)
        request = MarketOrderRequest(
            symbol=entry.symbol,
            qty=entry.quantity,
            side=alpaca_side,
            time_in_force=tif,
            order_class=OrderClass.BRACKET,
            take_profit={"limit_price": targets[0].limit_price},
            stop_loss={"stop_price": stop.stop_price},
        )

        # Submit bracket order to Alpaca
        try:
            alpaca_order = self._trading_client.submit_order(request)
            alpaca_order_id = str(alpaca_order.id)

            # Store order ID mapping for entry
            self._order_id_map[entry.id] = alpaca_order_id
            self._reverse_id_map[alpaca_order_id] = entry.id

            # Alpaca creates child orders for stop and target, but we don't
            # have their IDs immediately. We'll track them via trade updates.

            logger.info(
                f"Bracket order submitted to Alpaca: {entry.symbol} {entry.side} "
                f"{entry.quantity} @ market, stop=${stop.stop_price:.2f}, "
                f"target=${targets[0].limit_price:.2f} "
                f"(our_id={entry.id}, alpaca_id={alpaca_order_id})"
            )

            entry_result = OrderResult(
                order_id=entry.id,
                broker_order_id=alpaca_order_id,
                status=ModelOrderStatus.SUBMITTED,
                message="Bracket order submitted to Alpaca",
            )

            stop_result = OrderResult(
                order_id=stop.id,
                broker_order_id="",  # Child order ID not available yet
                status=ModelOrderStatus.SUBMITTED,
                message="Stop-loss submitted as part of bracket",
            )

            target_results = [
                OrderResult(
                    order_id=targets[0].id,
                    broker_order_id="",  # Child order ID not available yet
                    status=ModelOrderStatus.SUBMITTED,
                    message="Take-profit submitted as part of bracket",
                )
            ]

            # Additional targets (if any) are ignored in Sprint 4a
            for i in range(1, len(targets)):
                logger.warning(
                    f"AlpacaBroker ignoring target {i + 1} (Alpaca limitation). "
                    f"Sprint 4b Order Manager will handle multiple targets."
                )
                target_results.append(
                    OrderResult(
                        order_id=targets[i].id,
                        status=ModelOrderStatus.REJECTED,
                        message="Alpaca bracket orders support only one target",
                    )
                )

            return BracketOrderResult(
                entry=entry_result,
                stop=stop_result,
                targets=target_results,
            )

        except Exception as e:
            logger.error(f"Failed to submit bracket order to Alpaca: {e}", exc_info=True)

            entry_result = OrderResult(
                order_id=entry.id,
                status=ModelOrderStatus.REJECTED,
                message=f"Alpaca bracket order submission failed: {e}",
            )
            stop_result = OrderResult(
                order_id=stop.id,
                status=ModelOrderStatus.REJECTED,
                message="Bracket order entry failed",
            )
            target_results = [
                OrderResult(
                    order_id=t.id,
                    status=ModelOrderStatus.REJECTED,
                    message="Bracket order entry failed",
                )
                for t in targets
            ]

            return BracketOrderResult(
                entry=entry_result,
                stop=stop_result,
                targets=target_results,
            )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID.

        Args:
            order_id: Our ULID for the order.

        Returns:
            True if successfully cancelled, False otherwise.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        alpaca_order_id = self._order_id_map.get(order_id)
        if not alpaca_order_id:
            logger.error(f"Cannot cancel order {order_id}: not found in ID map")
            return False

        try:
            self._trading_client.cancel_order_by_id(alpaca_order_id)
            logger.info(f"Order cancelled: {order_id} (alpaca_id={alpaca_order_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}", exc_info=True)
            return False

    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify an existing order (e.g., change limit price, qty).

        Uses Alpaca's replace_order_by_id().

        Args:
            order_id: Our ULID for the order.
            modifications: Dict of field names to new values.

        Returns:
            OrderResult reflecting the modified order state.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        alpaca_order_id = self._order_id_map.get(order_id)
        if not alpaca_order_id:
            logger.error(f"Cannot modify order {order_id}: not found in ID map")
            return OrderResult(
                order_id=order_id,
                status=ModelOrderStatus.REJECTED,
                message="Order not found in ID map",
            )

        # Build ReplaceOrderRequest from modifications
        request = ReplaceOrderRequest(
            qty=modifications.get("quantity"),
            limit_price=modifications.get("limit_price"),
            stop_price=modifications.get("stop_price"),
            time_in_force=self._map_time_in_force(modifications.get("time_in_force", "day")),
        )

        try:
            alpaca_order = self._trading_client.replace_order_by_id(alpaca_order_id, request)
            new_alpaca_order_id = str(alpaca_order.id)

            # Update ID mapping (Alpaca assigns new order ID on replace)
            del self._order_id_map[order_id]
            del self._reverse_id_map[alpaca_order_id]
            self._order_id_map[order_id] = new_alpaca_order_id
            self._reverse_id_map[new_alpaca_order_id] = order_id

            logger.info(
                f"Order modified: {order_id} (old={alpaca_order_id}, new={new_alpaca_order_id})"
            )

            return OrderResult(
                order_id=order_id,
                broker_order_id=new_alpaca_order_id,
                status=ModelOrderStatus.SUBMITTED,
                message="Order modification submitted",
            )
        except Exception as e:
            logger.error(f"Failed to modify order {order_id}: {e}", exc_info=True)
            return OrderResult(
                order_id=order_id,
                status=ModelOrderStatus.REJECTED,
                message=f"Order modification failed: {e}",
            )

    async def get_positions(self) -> list[Position]:
        """Get all open positions.

        Maps Alpaca Position objects to our Position model.

        Returns:
            List of Position objects. Empty list if no positions.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        try:
            alpaca_positions = self._trading_client.get_all_positions()
            positions = []

            for pos in alpaca_positions:
                # Map Alpaca position to our Position model
                side = ModelOrderSide.BUY if float(pos.qty) > 0 else ModelOrderSide.SELL
                shares = abs(int(pos.qty)) if pos.qty else 0
                entry_price = float(pos.avg_entry_price) if pos.avg_entry_price else 0.0
                current_price = float(pos.current_price) if pos.current_price else 0.0
                unrealized_pnl = float(pos.unrealized_pl) if pos.unrealized_pl else 0.0

                position = Position(
                    id=generate_id(),
                    strategy_id="",  # Unknown at broker level
                    symbol=pos.symbol,
                    asset_class=AssetClass.US_STOCKS,
                    side=side,
                    status=PositionStatus.OPEN,
                    entry_price=entry_price,
                    entry_time=datetime.now(UTC),  # Not available from Alpaca
                    shares=shares,
                    stop_price=0.0,  # Not available from position object
                    target_prices=[],
                    current_price=current_price,
                    unrealized_pnl=unrealized_pnl,
                )
                positions.append(position)

            logger.info(f"Retrieved {len(positions)} positions from Alpaca")
            return positions

        except Exception as e:
            logger.error(f"Failed to get positions from Alpaca: {e}", exc_info=True)
            return []

    async def get_account(self) -> AccountInfo:
        """Get account info.

        Maps Alpaca Account to our AccountInfo model. Alpaca's paper account
        returns real margin/buying power values.

        Returns:
            AccountInfo snapshot.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        try:
            account = self._trading_client.get_account()

            equity = float(account.equity) if account.equity else 0.0
            cash = float(account.cash) if account.cash else 0.0
            buying_power = float(account.buying_power) if account.buying_power else 0.0

            # Calculate positions value
            positions_value = equity - cash

            # Daily P&L is the change from yesterday's equity
            daily_pnl = 0.0
            if (
                hasattr(account, "equity")
                and hasattr(account, "last_equity")
                and account.last_equity
            ):
                daily_pnl = equity - float(account.last_equity)

            logger.debug(
                f"Account: equity=${equity:.2f}, cash=${cash:.2f}, buying_power=${buying_power:.2f}"
            )

            return AccountInfo(
                equity=equity,
                cash=cash,
                buying_power=buying_power,
                positions_value=positions_value,
                daily_pnl=daily_pnl,
            )

        except Exception as e:
            logger.error(f"Failed to get account from Alpaca: {e}", exc_info=True)
            raise

    async def get_order_status(self, order_id: str) -> ModelOrderStatus:
        """Get the current status of a specific order.

        Args:
            order_id: Our ULID for the order.

        Returns:
            Current OrderStatus.

        Raises:
            ConnectionError: If not connected.
            KeyError: If the order_id is not found.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        alpaca_order_id = self._order_id_map.get(order_id)
        if not alpaca_order_id:
            raise KeyError(f"Order {order_id} not found in ID map")

        try:
            order = self._trading_client.get_order_by_id(alpaca_order_id)
            return self._map_order_status_to_model(order.status)
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}", exc_info=True)
            raise KeyError(f"Order {order_id} not found at Alpaca") from e

    async def get_open_orders(self) -> list[Order]:
        """Get all open (unfilled, not cancelled) orders from Alpaca.

        Returns:
            List of Order objects for all open orders at Alpaca.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        try:
            from alpaca.trading.requests import GetOrdersRequest

            request = GetOrdersRequest(status="open")
            alpaca_orders = self._trading_client.get_orders(request)
            orders = []

            for alpaca_order in alpaca_orders:
                alpaca_order_id = str(alpaca_order.id)
                our_id = self._reverse_id_map.get(alpaca_order_id)

                # If not in mapping, use alpaca ID as unknown
                if our_id is None:
                    our_id = f"unknown_{alpaca_order_id}"

                order = Order(
                    id=our_id,
                    strategy_id="",  # Unknown at broker level
                    symbol=alpaca_order.symbol,
                    side=self._map_side_to_model(alpaca_order.side),
                    order_type=self._map_order_type_to_model(alpaca_order.order_type),
                    quantity=int(alpaca_order.qty) if alpaca_order.qty else 0,
                    stop_price=float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
                    limit_price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
                )
                orders.append(order)

            logger.info(f"Retrieved {len(orders)} open orders from Alpaca")
            return orders

        except Exception as e:
            logger.error(f"Failed to get open orders from Alpaca: {e}", exc_info=True)
            return []

    async def cancel_all_orders(self) -> int:
        """Cancel all open orders at Alpaca.

        Returns:
            Number of orders cancelled.
        """
        self._check_connected()
        try:
            cancelled = self._trading_client.cancel_orders()
            count = len(cancelled) if cancelled else 0
            logger.info("Shutdown: cancelled %d open orders at Alpaca", count)
            return count
        except Exception as e:
            logger.error("Failed to cancel all orders at Alpaca: %s", e)
            return 0

    async def flatten_all(self) -> list[OrderResult]:
        """Emergency: close all open positions at market price.

        Uses Alpaca's close_all_positions(cancel_orders=True).

        Returns:
            List of OrderResults for each closing order.

        Raises:
            ConnectionError: If not connected.
        """
        if not self._connected or not self._trading_client:
            raise ConnectionError("AlpacaBroker not connected. Call connect() first.")

        try:
            # Cancel all pending orders first
            self._trading_client.cancel_orders()
            logger.info("All pending orders cancelled")

            # Close all positions at market
            close_responses = self._trading_client.close_all_positions(cancel_orders=True)

            results = []
            for response in close_responses:
                if hasattr(response, "symbol"):
                    our_order_id = generate_id()
                    alpaca_order_id = str(response.id) if hasattr(response, "id") else ""

                    # Store mapping
                    if alpaca_order_id:
                        self._order_id_map[our_order_id] = alpaca_order_id
                        self._reverse_id_map[alpaca_order_id] = our_order_id

                    results.append(
                        OrderResult(
                            order_id=our_order_id,
                            broker_order_id=alpaca_order_id,
                            status=ModelOrderStatus.SUBMITTED,
                            message=f"Emergency flatten: {response.symbol}",
                        )
                    )

            logger.warning(f"Emergency flatten executed: {len(results)} positions closed")
            return results

        except Exception as e:
            logger.error(f"Failed to flatten all positions: {e}", exc_info=True)
            return []

    # ---------------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------------

    def _map_side_to_alpaca(self, side: ModelOrderSide) -> OrderSide:
        """Map our OrderSide to Alpaca's OrderSide."""
        return OrderSide.BUY if side == ModelOrderSide.BUY else OrderSide.SELL

    def _map_side_to_model(self, alpaca_side: OrderSide) -> ModelOrderSide:
        """Map Alpaca's OrderSide to our OrderSide."""
        return ModelOrderSide.BUY if alpaca_side == OrderSide.BUY else ModelOrderSide.SELL

    def _map_time_in_force(self, tif: str) -> TimeInForce:
        """Map our time_in_force string to Alpaca's TimeInForce enum."""
        tif_lower = tif.lower()
        if tif_lower == "day":
            return TimeInForce.DAY
        elif tif_lower == "gtc":
            return TimeInForce.GTC
        elif tif_lower == "ioc":
            return TimeInForce.IOC
        elif tif_lower == "fok":
            return TimeInForce.FOK
        else:
            logger.warning(f"Unknown time_in_force '{tif}', defaulting to DAY")
            return TimeInForce.DAY

    def _map_order_type_to_model(self, alpaca_order_type: str) -> OrderType:
        """Map Alpaca's order type string to our OrderType."""
        alpaca_type_lower = alpaca_order_type.lower()
        if alpaca_type_lower == "market":
            return OrderType.MARKET
        elif alpaca_type_lower == "limit":
            return OrderType.LIMIT
        elif alpaca_type_lower == "stop":
            return OrderType.STOP
        elif alpaca_type_lower == "stop_limit":
            return OrderType.STOP_LIMIT
        else:
            logger.warning(f"Unknown Alpaca order type '{alpaca_order_type}', defaulting to MARKET")
            return OrderType.MARKET

    def _map_order_status_to_model(self, alpaca_status: str) -> ModelOrderStatus:
        """Map Alpaca's order status string to our OrderStatus."""
        alpaca_status_lower = alpaca_status.lower()
        if alpaca_status_lower in ("new", "accepted", "pending_new"):
            return ModelOrderStatus.SUBMITTED
        elif alpaca_status_lower == "partially_filled":
            return ModelOrderStatus.PARTIAL_FILL
        elif alpaca_status_lower == "filled":
            return ModelOrderStatus.FILLED
        elif alpaca_status_lower in ("canceled", "pending_cancel"):
            return ModelOrderStatus.CANCELLED
        elif alpaca_status_lower == "rejected":
            return ModelOrderStatus.REJECTED
        elif alpaca_status_lower == "expired":
            return ModelOrderStatus.EXPIRED
        else:
            logger.warning(f"Unknown Alpaca status '{alpaca_status}', defaulting to PENDING")
            return ModelOrderStatus.PENDING
