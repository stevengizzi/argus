"""Simulated broker for testing and backtesting.

Fills orders deterministically. Tracks positions and account state internally.
Supports configurable slippage and bracket order simulation.

Usage:
    broker = SimulatedBroker(initial_cash=50000.0)
    await broker.connect()
    result = await broker.place_order(order)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import UTC, datetime

from argus.core.ids import generate_id
from argus.execution.broker import Broker
from argus.models.trading import (
    AccountInfo,
    BracketOrderResult,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class SimulatedSlippage:
    """Slippage configuration for the simulated broker.

    Attributes:
        mode: "none", "fixed", or "random".
        fixed_amount: Fixed slippage per share (used when mode="fixed").
        random_max: Maximum random slippage per share (used when mode="random").
    """

    mode: str = "none"  # "none", "fixed", "random"
    fixed_amount: float = 0.0
    random_max: float = 0.0


@dataclass
class PendingBracketOrder:
    """A stop or target order waiting to be triggered by price movement.

    Attributes:
        order_id: ULID for this pending order.
        symbol: The stock symbol.
        side: "buy" or "sell".
        quantity: Number of shares.
        trigger_price: Price at which this order triggers.
        order_type: "stop" or "limit" (determines trigger direction).
        parent_position_symbol: Symbol of the associated position.
        strategy_id: ID of the strategy that created this bracket.
    """

    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    trigger_price: float
    order_type: str  # "stop" or "limit"
    parent_position_symbol: str
    strategy_id: str


class SimulatedBroker(Broker):
    """Deterministic broker simulation for testing and backtesting.

    Fills orders immediately at specified prices with optional slippage.
    Tracks positions and account state internally. Supports bracket order
    simulation via simulate_price_update().

    Args:
        initial_cash: Starting cash balance.
        slippage: Slippage configuration.
    """

    def __init__(
        self,
        initial_cash: float = 100_000.0,
        slippage: SimulatedSlippage | None = None,
    ) -> None:
        self._initial_cash = initial_cash
        self._slippage = slippage or SimulatedSlippage()
        self._cash: float = initial_cash
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, OrderResult] = {}
        self._pending_brackets: list[PendingBracketOrder] = []
        self._connected: bool = False
        # Current prices cache for market order fills in backtest mode
        self._current_prices: dict[str, float] = {}

    async def connect(self) -> None:
        """Establish connection to the simulated broker."""
        self._connected = True
        logger.info("SimulatedBroker connected (initial_cash=%.2f)", self._initial_cash)

    async def disconnect(self) -> None:
        """Disconnect from the simulated broker."""
        self._connected = False
        logger.info("SimulatedBroker disconnected")

    def _check_connected(self) -> None:
        """Raise if not connected."""
        if not self._connected:
            raise RuntimeError("SimulatedBroker is not connected. Call connect() first.")

    def _apply_slippage(self, price: float, side: OrderSide) -> float:
        """Apply slippage to a fill price.

        For buy orders, slippage makes the price worse (higher).
        For sell orders, slippage makes the price worse (lower).
        """
        if self._slippage.mode == "none":
            return price

        if self._slippage.mode == "fixed":
            slip = self._slippage.fixed_amount
        elif self._slippage.mode == "random":
            slip = random.uniform(0, self._slippage.random_max)
        else:
            return price

        if side == OrderSide.BUY:
            return price + slip
        else:
            return price - slip

    async def _register_pending_order(self, order: Order, order_id: str) -> OrderResult:
        """Register a STOP or LIMIT order as pending (waits for price trigger).

        The order will be filled when simulate_price_update() detects
        the trigger condition is met.

        Args:
            order: The stop or limit order.
            order_id: Pre-generated order ID.

        Returns:
            OrderResult with PENDING status.
        """
        # Determine trigger price and order type
        if order.order_type == OrderType.STOP:
            trigger_price = order.stop_price or 0.0
            bracket_type = "stop"
        elif order.order_type == OrderType.LIMIT:
            trigger_price = order.limit_price or 0.0
            bracket_type = "limit"
        else:  # STOP_LIMIT
            trigger_price = order.stop_price or 0.0
            bracket_type = "stop"

        # Register as pending bracket
        self._pending_brackets.append(
            PendingBracketOrder(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                trigger_price=trigger_price,
                order_type=bracket_type,
                parent_position_symbol=order.symbol,
                strategy_id=order.strategy_id,
            )
        )

        result = OrderResult(
            order_id=order_id,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            filled_avg_price=0.0,
            message=f"{order.order_type.value} order pending at {trigger_price}",
        )
        self._orders[order_id] = result

        logger.debug(
            "Registered pending %s order: %s %d %s @ %.2f",
            bracket_type,
            order.side.value,
            order.quantity,
            order.symbol,
            trigger_price,
        )

        return result

    async def place_order(self, order: Order) -> OrderResult:
        """Submit a single order to the simulated broker.

        MARKET orders are filled immediately at the current price (plus slippage).
        STOP and LIMIT orders are registered as pending and trigger via
        simulate_price_update().

        For market orders without a limit_price, uses the current price from
        the _current_prices cache (set by simulate_price_update or set_price).

        Args:
            order: The order to place.

        Returns:
            OrderResult with fill information or rejection reason.
        """
        self._check_connected()

        order_id = generate_id()

        # Handle STOP and LIMIT orders as pending (they wait for price trigger)
        if order.order_type in (OrderType.STOP, OrderType.LIMIT, OrderType.STOP_LIMIT):
            return await self._register_pending_order(order, order_id)

        # For MARKET orders, fill immediately
        # Use: limit_price > current_price cache > 0.0
        base_price = order.limit_price or self._current_prices.get(order.symbol, 0.0)
        fill_price = self._apply_slippage(base_price, order.side)
        cost = fill_price * order.quantity

        if order.side == OrderSide.BUY:
            # Check buying power
            if cost > self._cash:
                result = OrderResult(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    filled_quantity=0,
                    filled_avg_price=0.0,
                    message="Insufficient buying power",
                )
                self._orders[order_id] = result
                logger.warning(
                    "Order rejected: insufficient buying power (need=%.2f, have=%.2f)",
                    cost,
                    self._cash,
                )
                return result

            # Deduct cash
            self._cash -= cost

            # Create or update position
            if order.symbol in self._positions:
                pos = self._positions[order.symbol]
                # Average up/down
                total_shares = pos.shares + order.quantity
                total_cost = (pos.entry_price * pos.shares) + cost
                new_avg_price = total_cost / total_shares
                self._positions[order.symbol] = Position(
                    id=pos.id,
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    side=pos.side,
                    status=PositionStatus.OPEN,
                    entry_price=new_avg_price,
                    entry_time=pos.entry_time,
                    shares=total_shares,
                    stop_price=pos.stop_price,
                    target_prices=pos.target_prices,
                    current_price=fill_price,
                )
            else:
                self._positions[order.symbol] = Position(
                    id=generate_id(),
                    strategy_id=order.strategy_id,
                    symbol=order.symbol,
                    side=OrderSide.BUY,
                    status=PositionStatus.OPEN,
                    entry_price=fill_price,
                    entry_time=datetime.now(UTC),
                    shares=order.quantity,
                    stop_price=order.stop_price or 0.0,
                    target_prices=[],
                    current_price=fill_price,
                )

            result = OrderResult(
                order_id=order_id,
                status=OrderStatus.FILLED,
                filled_quantity=order.quantity,
                filled_avg_price=fill_price,
                message="",
            )

        else:  # SELL
            # Check position exists
            if order.symbol not in self._positions:
                result = OrderResult(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    filled_quantity=0,
                    filled_avg_price=0.0,
                    message="No position to sell",
                )
                self._orders[order_id] = result
                logger.warning("Order rejected: no position for %s", order.symbol)
                return result

            pos = self._positions[order.symbol]
            if pos.shares < order.quantity:
                result = OrderResult(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    filled_quantity=0,
                    filled_avg_price=0.0,
                    message=f"Insufficient shares (have={pos.shares}, want={order.quantity})",
                )
                self._orders[order_id] = result
                logger.warning(
                    "Order rejected: insufficient shares for %s (have=%d, want=%d)",
                    order.symbol,
                    pos.shares,
                    order.quantity,
                )
                return result

            # Add proceeds to cash
            proceeds = fill_price * order.quantity
            self._cash += proceeds

            # Reduce or close position
            remaining = pos.shares - order.quantity
            if remaining == 0:
                del self._positions[order.symbol]
            else:
                self._positions[order.symbol] = Position(
                    id=pos.id,
                    strategy_id=pos.strategy_id,
                    symbol=pos.symbol,
                    side=pos.side,
                    status=PositionStatus.OPEN,
                    entry_price=pos.entry_price,
                    entry_time=pos.entry_time,
                    shares=remaining,
                    stop_price=pos.stop_price,
                    target_prices=pos.target_prices,
                    current_price=fill_price,
                )

            result = OrderResult(
                order_id=order_id,
                status=OrderStatus.FILLED,
                filled_quantity=order.quantity,
                filled_avg_price=fill_price,
                message="",
            )

        self._orders[order_id] = result
        logger.info(
            "Order filled: %s %d %s @ %.2f",
            order.side.value,
            order.quantity,
            order.symbol,
            fill_price,
        )
        return result

    async def place_bracket_order(
        self,
        entry: Order,
        stop: Order,
        targets: list[Order],
    ) -> BracketOrderResult:
        """Submit a bracket order (entry + stop + targets).

        The entry order is executed immediately. If it fills, the stop and
        target orders are registered as pending bracket orders, to be
        triggered by simulate_price_update().

        Args:
            entry: The entry order.
            stop: The stop-loss order.
            targets: Profit target orders.

        Returns:
            BracketOrderResult with results for all orders.
        """
        self._check_connected()

        # Place entry
        entry_result = await self.place_order(entry)

        if entry_result.status != OrderStatus.FILLED:
            # Entry rejected — don't submit stop/targets
            rejected_result = OrderResult(
                order_id=generate_id(),
                status=OrderStatus.REJECTED,
                filled_quantity=0,
                filled_avg_price=0.0,
                message="Entry order rejected",
            )
            return BracketOrderResult(
                entry=entry_result,
                stop=rejected_result,
                targets=[rejected_result for _ in targets],
            )

        # Register stop as pending
        stop_id = generate_id()
        self._pending_brackets.append(
            PendingBracketOrder(
                order_id=stop_id,
                symbol=stop.symbol,
                side=stop.side,
                quantity=stop.quantity,
                trigger_price=stop.stop_price or 0.0,
                order_type="stop",
                parent_position_symbol=entry.symbol,
                strategy_id=entry.strategy_id,
            )
        )
        stop_result = OrderResult(
            order_id=stop_id,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            filled_avg_price=0.0,
            message="Stop order pending",
        )
        self._orders[stop_id] = stop_result

        # Register targets as pending
        target_results = []
        for target in targets:
            target_id = generate_id()
            self._pending_brackets.append(
                PendingBracketOrder(
                    order_id=target_id,
                    symbol=target.symbol,
                    side=target.side,
                    quantity=target.quantity,
                    trigger_price=target.limit_price or 0.0,
                    order_type="limit",
                    parent_position_symbol=entry.symbol,
                    strategy_id=entry.strategy_id,
                )
            )
            target_result = OrderResult(
                order_id=target_id,
                status=OrderStatus.PENDING,
                filled_quantity=0,
                filled_avg_price=0.0,
                message="Target order pending",
            )
            self._orders[target_id] = target_result
            target_results.append(target_result)

        logger.info(
            "Bracket order placed: entry filled, %d stop(s), %d target(s) pending",
            1,
            len(targets),
        )
        return BracketOrderResult(
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order.

        Args:
            order_id: The ID of the order to cancel.

        Returns:
            True if cancelled, False if not found or already filled.
        """
        self._check_connected()

        # Check pending brackets
        for i, bracket in enumerate(self._pending_brackets):
            if bracket.order_id == order_id:
                self._pending_brackets.pop(i)
                if order_id in self._orders:
                    old = self._orders[order_id]
                    self._orders[order_id] = OrderResult(
                        order_id=old.order_id,
                        status=OrderStatus.CANCELLED,
                        filled_quantity=old.filled_quantity,
                        filled_avg_price=old.filled_avg_price,
                        message="Cancelled",
                    )
                logger.info("Order %s cancelled", order_id)
                return True

        # Check regular orders
        if order_id in self._orders:
            old = self._orders[order_id]
            if old.status == OrderStatus.PENDING:
                self._orders[order_id] = OrderResult(
                    order_id=old.order_id,
                    status=OrderStatus.CANCELLED,
                    filled_quantity=old.filled_quantity,
                    filled_avg_price=old.filled_avg_price,
                    message="Cancelled",
                )
                logger.info("Order %s cancelled", order_id)
                return True

        return False

    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify a pending bracket order.

        Args:
            order_id: The ID of the order to modify.
            modifications: Dict with new values (e.g., trigger_price, quantity).

        Returns:
            Updated OrderResult.

        Raises:
            KeyError: If order not found.
        """
        self._check_connected()

        for bracket in self._pending_brackets:
            if bracket.order_id == order_id:
                if "trigger_price" in modifications:
                    bracket.trigger_price = modifications["trigger_price"]
                if "quantity" in modifications:
                    bracket.quantity = modifications["quantity"]
                return OrderResult(
                    order_id=order_id,
                    status=OrderStatus.PENDING,
                    filled_quantity=0,
                    filled_avg_price=0.0,
                    message="Modified",
                )

        raise KeyError(f"Order {order_id} not found in pending brackets")

    async def get_positions(self) -> list[Position]:
        """Get all open positions.

        Returns:
            List of open Position objects.
        """
        self._check_connected()
        return list(self._positions.values())

    async def get_account(self) -> AccountInfo:
        """Get current account information.

        Returns:
            AccountInfo with equity, cash, buying power.
        """
        self._check_connected()

        positions_value = sum(pos.current_price * pos.shares for pos in self._positions.values())
        equity = self._cash + positions_value

        return AccountInfo(
            equity=equity,
            cash=self._cash,
            # V1: buying_power = cash (no margin). When AlpacaBroker is added (Sprint 4),
            # buying_power will differ from cash for margin accounts. The Risk Manager's
            # cash reserve (step 5) and buying power (step 6) checks will then diverge.
            buying_power=self._cash,
            positions_value=positions_value,
            daily_pnl=0.0,  # Not tracked in V1
        )

    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get the status of a specific order.

        Args:
            order_id: The ID of the order.

        Returns:
            Current OrderStatus.

        Raises:
            KeyError: If order not found.
        """
        self._check_connected()

        # Check regular orders
        if order_id in self._orders:
            return self._orders[order_id].status

        # Check pending brackets
        for bracket in self._pending_brackets:
            if bracket.order_id == order_id:
                return OrderStatus.PENDING

        raise KeyError(f"Order {order_id} not found")

    async def get_open_orders(self) -> list[Order]:
        """Get all open (pending) orders.

        Returns:
            List of Order objects for pending bracket orders.
        """
        self._check_connected()

        orders = []
        for bracket in self._pending_brackets:
            # Map bracket order type to OrderType enum
            if bracket.order_type == "stop":
                order_type = OrderType.STOP
                stop_price = bracket.trigger_price
                limit_price = None
            else:  # limit
                order_type = OrderType.LIMIT
                stop_price = None
                limit_price = bracket.trigger_price

            order = Order(
                id=bracket.order_id,
                strategy_id=bracket.strategy_id,
                symbol=bracket.symbol,
                side=bracket.side,
                order_type=order_type,
                quantity=bracket.quantity,
                stop_price=stop_price,
                limit_price=limit_price,
            )
            orders.append(order)

        logger.info("Retrieved %d open orders from SimulatedBroker", len(orders))
        return orders

    async def flatten_all(self) -> list[OrderResult]:
        """Close all positions and cancel all pending orders.

        Returns:
            List of OrderResults for each closing order.
        """
        self._check_connected()

        # Cancel all pending bracket orders
        self._pending_brackets.clear()
        logger.info("All pending bracket orders cancelled")

        # Close all positions
        results = []
        symbols = list(self._positions.keys())
        for symbol in symbols:
            pos = self._positions[symbol]
            sell_order = Order(
                strategy_id=pos.strategy_id,
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=pos.shares,
                limit_price=pos.current_price,
            )
            result = await self.place_order(sell_order)
            results.append(result)

        logger.info("Flattened %d positions", len(results))
        return results

    # -------------------------------------------------------------------------
    # Testing Infrastructure (not on ABC)
    # -------------------------------------------------------------------------

    def set_price(self, symbol: str, price: float) -> None:
        """Set the current price for a symbol (for market order fills).

        This is used in backtest mode to ensure market orders fill at
        realistic prices rather than zero.

        Args:
            symbol: The symbol.
            price: The current market price.
        """
        self._current_prices[symbol] = price

    async def simulate_price_update(self, symbol: str, price: float) -> list[OrderResult]:
        """Simulate a price update and trigger any matching bracket orders.

        This is testing infrastructure. It updates position current_price,
        updates the current price cache, and checks if any stop or target
        orders should trigger.

        Args:
            symbol: The symbol to update.
            price: The new price.

        Returns:
            List of OrderResults for any triggered orders.
        """
        self._check_connected()

        # Update current price cache (for future market orders)
        self._current_prices[symbol] = price

        # Update position price
        if symbol in self._positions:
            pos = self._positions[symbol]
            self._positions[symbol] = Position(
                id=pos.id,
                strategy_id=pos.strategy_id,
                symbol=pos.symbol,
                side=pos.side,
                status=pos.status,
                entry_price=pos.entry_price,
                entry_time=pos.entry_time,
                shares=pos.shares,
                stop_price=pos.stop_price,
                target_prices=pos.target_prices,
                current_price=price,
            )

        # Check for triggered bracket orders
        triggered_results = []
        triggered_ids = []

        for bracket in self._pending_brackets:
            if bracket.symbol != symbol:
                continue

            # Stop triggers when price <= trigger; limit triggers when price >= trigger
            triggered = (bracket.order_type == "stop" and price <= bracket.trigger_price) or (
                bracket.order_type == "limit" and price >= bracket.trigger_price
            )

            if triggered:
                # Execute the bracket order
                sell_order = Order(
                    strategy_id=bracket.strategy_id,
                    symbol=symbol,
                    side=bracket.side,
                    quantity=bracket.quantity,
                    limit_price=price,
                )
                result = await self.place_order(sell_order)

                # Update the stored order result
                self._orders[bracket.order_id] = OrderResult(
                    order_id=bracket.order_id,
                    status=result.status,
                    filled_quantity=result.filled_quantity,
                    filled_avg_price=result.filled_avg_price,
                    message=f"Triggered at {price}",
                )
                triggered_results.append(self._orders[bracket.order_id])
                triggered_ids.append(bracket.order_id)

                logger.info(
                    "Bracket order %s triggered at %.2f (%s)",
                    bracket.order_id,
                    price,
                    bracket.order_type,
                )

        # Remove triggered brackets
        self._pending_brackets = [
            b for b in self._pending_brackets if b.order_id not in triggered_ids
        ]

        # If position is fully closed, cancel remaining brackets for that symbol
        if symbol not in self._positions:
            remaining_brackets = [
                b for b in self._pending_brackets if b.parent_position_symbol == symbol
            ]
            for b in remaining_brackets:
                if b.order_id in self._orders:
                    old = self._orders[b.order_id]
                    self._orders[b.order_id] = OrderResult(
                        order_id=old.order_id,
                        status=OrderStatus.CANCELLED,
                        filled_quantity=0,
                        filled_avg_price=0.0,
                        message="Position closed, order cancelled",
                    )
            self._pending_brackets = [
                b for b in self._pending_brackets if b.parent_position_symbol != symbol
            ]

        return triggered_results

    def reset(self) -> None:
        """Reset broker to initial state. For testing only."""
        self._cash = self._initial_cash
        self._positions.clear()
        self._orders.clear()
        self._pending_brackets.clear()
        self._current_prices.clear()
        self._connected = False
