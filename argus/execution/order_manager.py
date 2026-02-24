"""Order Manager — manages the full lifecycle of trades from approval to exit.

Subscribes to OrderApprovedEvent, OrderFilledEvent, OrderCancelledEvent,
and TickEvent via the Event Bus. Runs a fallback poll loop for time-based
exits and a scheduled EOD flatten.

Key design decisions:
- T1/T2 split: Separate orders, not Alpaca brackets (DEC-039/MD-4a-6)
- Stop management: Cancel and resubmit, not modify-in-place (MD-4b-1)
- EOD flatten: Checked in fallback poll, not APScheduler (MD-4b-2)
- Trade logging: Called directly, not via event listener (MD-4b-3)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    CircuitBreakerEvent,
    ExitReason,
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderSubmittedEvent,
    OrderType,
    PositionClosedEvent,
    PositionOpenedEvent,
    Side,
    TickEvent,
)
from argus.core.ids import generate_id
from argus.execution.broker import Broker
from argus.models.trading import Order, OrderSide, OrderStatus
from argus.models.trading import OrderType as TradingOrderType

if TYPE_CHECKING:
    from argus.core.clock import Clock

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class ManagedPosition:
    """Tracks a position being actively managed by the Order Manager.

    Mutable — fields update as the position progresses through its lifecycle.
    """

    symbol: str
    strategy_id: str
    entry_price: float  # Actual fill price
    entry_time: datetime  # When entry filled
    shares_total: int  # Original total shares
    shares_remaining: int  # Shares still open
    stop_price: float  # Current stop price (may move to breakeven)
    original_stop_price: float  # Original stop from signal (never changes)
    stop_order_id: str | None  # Broker-side stop order ID
    t1_price: float  # T1 target price (target_prices[0])
    t1_order_id: str | None  # Broker-side T1 limit order ID
    t1_shares: int  # Shares allocated to T1 (50%)
    t1_filled: bool  # Whether T1 has been hit
    t2_price: float  # T2 target price (target_prices[1])
    high_watermark: float  # Highest price since entry (for trailing stop)

    # Optional fields with defaults (must come after required fields)
    t2_order_id: str | None = None  # Broker-side T2 limit order ID (IBKR native brackets)
    realized_pnl: float = 0.0  # Accumulated P&L from partial exits
    time_stop_seconds: int | None = None  # Per-position time stop from signal (DEC-122)

    @property
    def is_fully_closed(self) -> bool:
        """Return True if no shares remain."""
        return self.shares_remaining <= 0


@dataclass
class PendingManagedOrder:
    """Tracks an order awaiting fill confirmation from the broker.

    Keyed by order_id in Order Manager's _pending_orders dict.
    """

    order_id: str
    symbol: str
    strategy_id: str
    order_type: str  # "entry", "stop", "t1_target", "t2", "flatten"
    shares: int = 0  # Expected fill quantity
    signal: Any = field(default=None)  # OrderApprovedEvent (for reference)
    # Bracket order IDs (set when entry is part of a bracket, DEC-117)
    bracket_stop_order_id: str | None = None
    bracket_t1_order_id: str | None = None
    bracket_t2_order_id: str | None = None


# ---------------------------------------------------------------------------
# Order Manager
# ---------------------------------------------------------------------------


class OrderManager:
    """Manages the full lifecycle of trades from approval to exit.

    Subscribes to:
    - OrderApprovedEvent: Convert approved signals to broker orders
    - OrderFilledEvent: Handle fills, manage T1/T2 and stops
    - OrderCancelledEvent: Handle cancelled orders
    - TickEvent: Real-time price monitoring for trailing stops and T2
    - CircuitBreakerEvent: Emergency flatten

    Runs a fallback poll loop for time-based exits (time stops, EOD flatten).
    """

    def __init__(
        self,
        event_bus: EventBus,
        broker: Broker,
        clock: Clock,
        config: OrderManagerConfig,
        trade_logger: Any | None = None,
    ) -> None:
        """Initialize the Order Manager.

        Args:
            event_bus: The event bus for pub/sub.
            broker: The broker implementation.
            clock: Clock protocol for time operations.
            config: Order Manager configuration.
            trade_logger: Optional TradeLogger for persistence.
        """
        self._event_bus = event_bus
        self._broker = broker
        self._clock = clock
        self._config = config
        self._trade_logger = trade_logger

        # Active positions: keyed by symbol (list to support multiple positions)
        self._managed_positions: dict[str, list[ManagedPosition]] = {}

        # Orders awaiting fill confirmation: keyed by order_id
        self._pending_orders: dict[str, PendingManagedOrder] = {}

        # Async tasks
        self._poll_task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._flattened_today: bool = False

    async def start(self) -> None:
        """Start the Order Manager.

        Subscribes to events on the Event Bus and starts the fallback poll loop.
        """
        self._event_bus.subscribe(OrderApprovedEvent, self.on_approved)
        self._event_bus.subscribe(OrderFilledEvent, self.on_fill)
        self._event_bus.subscribe(OrderCancelledEvent, self.on_cancel)
        self._event_bus.subscribe(TickEvent, self.on_tick)
        self._event_bus.subscribe(CircuitBreakerEvent, self._on_circuit_breaker)

        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("OrderManager started")

    async def stop(self) -> None:
        """Stop the Order Manager. Cancel the poll task."""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task
        logger.info("OrderManager stopped")

    # ---------------------------------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------------------------------

    async def on_approved(self, event: OrderApprovedEvent) -> None:
        """Handle an approved signal from the Risk Manager.

        Extracts signal data (possibly with modifications applied),
        constructs entry + stop + target orders, and submits as atomic
        bracket order (DEC-117). All component order IDs are tracked
        for fill routing.
        """
        signal = event.signal
        if signal is None:
            logger.warning("OrderApprovedEvent with no signal, ignoring")
            return

        # Apply modifications if any (e.g., reduced share count)
        share_count = signal.share_count
        target_prices = signal.target_prices
        if event.modifications:
            if "share_count" in event.modifications:
                share_count = event.modifications["share_count"]
            if "target_prices" in event.modifications:
                target_prices = event.modifications["target_prices"]

        # Validate we have at least T1 target
        if len(target_prices) < 1:
            logger.error(
                "Signal for %s has no target prices, cannot manage. Ignoring.",
                signal.symbol,
            )
            return

        # Calculate T1/T2 share split
        # Single-target signals: 100% exit at T1 (ORB Scalp pattern — DEC-122)
        if len(target_prices) == 1:
            t1_shares = share_count
            t2_shares = 0
        else:
            t1_shares = int(share_count * self._config.t1_position_pct)
            if t1_shares == 0 and share_count > 0:
                t1_shares = 1
            t2_shares = share_count - t1_shares

        # Construct entry order
        entry_order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.BUY,  # Long only V1 (DEC-011)
            order_type=TradingOrderType.MARKET,
            quantity=share_count,
        )

        # Construct stop order (covers full position)
        stop_order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.SELL,
            order_type=TradingOrderType.STOP,
            quantity=share_count,
            stop_price=signal.stop_price,
        )

        # Construct target orders
        targets: list[Order] = []
        t1_price = target_prices[0] if len(target_prices) >= 1 else 0.0
        if t1_price > 0 and t1_shares > 0:
            t1_order = Order(
                strategy_id=signal.strategy_id,
                symbol=signal.symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.LIMIT,
                quantity=t1_shares,
                limit_price=t1_price,
            )
            targets.append(t1_order)

        t2_price = target_prices[1] if len(target_prices) >= 2 else 0.0
        if t2_price > 0 and t2_shares > 0:
            t2_order = Order(
                strategy_id=signal.strategy_id,
                symbol=signal.symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.LIMIT,
                quantity=t2_shares,
                limit_price=t2_price,
            )
            targets.append(t2_order)

        # Submit bracket order atomically (DEC-117)
        try:
            bracket_result = await self._broker.place_bracket_order(
                entry_order, stop_order, targets
            )
            entry_order_id = bracket_result.entry.order_id
        except Exception:
            logger.exception("Failed to submit bracket order for %s", signal.symbol)
            return

        # Track entry as pending with bracket IDs
        pending = PendingManagedOrder(
            order_id=entry_order_id,
            symbol=signal.symbol,
            strategy_id=signal.strategy_id,
            order_type="entry",
            shares=share_count,
            signal=event,
            bracket_stop_order_id=bracket_result.stop.order_id,
            bracket_t1_order_id=(
                bracket_result.targets[0].order_id if bracket_result.targets else None
            ),
            bracket_t2_order_id=(
                bracket_result.targets[1].order_id if len(bracket_result.targets) > 1 else None
            ),
        )
        self._pending_orders[entry_order_id] = pending

        # Track stop and target orders as pending (so fill events route correctly)
        if bracket_result.stop.order_id:
            self._pending_orders[bracket_result.stop.order_id] = PendingManagedOrder(
                order_id=bracket_result.stop.order_id,
                symbol=signal.symbol,
                strategy_id=signal.strategy_id,
                order_type="stop",
            )
        for i, target_result in enumerate(bracket_result.targets):
            order_type = "t1_target" if i == 0 else "t2"
            self._pending_orders[target_result.order_id] = PendingManagedOrder(
                order_id=target_result.order_id,
                symbol=signal.symbol,
                strategy_id=signal.strategy_id,
                order_type=order_type,
            )

        # Publish submission event
        await self._event_bus.publish(
            OrderSubmittedEvent(
                order_id=entry_order_id,
                strategy_id=signal.strategy_id,
                symbol=signal.symbol,
                side=Side.LONG,
                quantity=share_count,
                order_type=OrderType.MARKET,
            )
        )

        logger.info(
            "Bracket order submitted: BUY %d shares of %s (entry=%s, stop=%s, T1=%s, T2=%s)",
            share_count,
            signal.symbol,
            entry_order_id,
            bracket_result.stop.order_id,
            bracket_result.targets[0].order_id if bracket_result.targets else None,
            bracket_result.targets[1].order_id if len(bracket_result.targets) > 1 else None,
        )

        # Handle immediate fill (SimulatedBroker fills entry synchronously)
        if bracket_result.entry.status == OrderStatus.FILLED:
            fill_event = OrderFilledEvent(
                order_id=entry_order_id,
                fill_price=bracket_result.entry.filled_avg_price,
                fill_quantity=bracket_result.entry.filled_quantity,
            )
            await self.on_fill(fill_event)

    async def on_fill(self, event: OrderFilledEvent) -> None:
        """Route fill events to the appropriate handler.

        Cases:
        a) Entry fill → create ManagedPosition, submit stop + T1
        b) T1 fill → move stop to breakeven, update position
        c) Stop fill → position closed (full or partial)
        d) Flatten fill → position closed
        """
        pending = self._pending_orders.pop(event.order_id, None)
        if pending is None:
            logger.debug("Fill for unknown order_id %s, ignoring", event.order_id)
            return

        if pending.order_type == "entry":
            await self._handle_entry_fill(pending, event)
        elif pending.order_type == "t1_target":
            await self._handle_t1_fill(pending, event)
        elif pending.order_type == "t2":
            await self._handle_t2_fill(pending, event)
        elif pending.order_type == "stop":
            await self._handle_stop_fill(pending, event)
        elif pending.order_type == "flatten":
            await self._handle_flatten_fill(pending, event)
        else:
            logger.warning("Unknown pending order type: %s", pending.order_type)

    async def on_cancel(self, event: OrderCancelledEvent) -> None:
        """Handle order cancellation from broker.

        Remove from pending orders. If it was a stop order, ensure
        the position still has protection.
        """
        pending = self._pending_orders.pop(event.order_id, None)
        if pending is None:
            return  # Not our order

        logger.warning(
            "Order cancelled: %s (type=%s, symbol=%s, reason=%s)",
            event.order_id,
            pending.order_type,
            pending.symbol,
            event.reason,
        )

        if pending.order_type == "stop":
            # Critical: position may be unprotected
            positions = self._managed_positions.get(pending.symbol, [])
            for pos in positions:
                if pos.stop_order_id == event.order_id:
                    pos.stop_order_id = None
                    # Try to resubmit stop
                    logger.warning(
                        "Stop order cancelled for %s. Resubmitting.",
                        pending.symbol,
                    )
                    await self._submit_stop_order(pos, pos.shares_remaining, pos.stop_price)
                    break

    async def on_tick(self, event: TickEvent) -> None:
        """Primary position management — evaluate exit conditions on every tick.

        Only processes ticks for symbols with open managed positions.
        """
        positions = self._managed_positions.get(event.symbol)
        if not positions:
            return  # No managed positions for this symbol

        for position in positions:
            if position.is_fully_closed:
                continue

            # Update high watermark
            if event.price > position.high_watermark:
                position.high_watermark = event.price

            # Check trailing stop (if enabled)
            if self._config.enable_trailing_stop and position.t1_filled:
                trail_distance = (
                    position.high_watermark
                    * self._config.trailing_stop_atr_multiplier
                    * 0.01  # Simplified: use % instead of ATR for V1
                )
                trailing_stop_price = position.high_watermark - trail_distance
                if event.price <= trailing_stop_price:
                    await self._flatten_position(position, reason="trailing_stop")
                    continue

            # Check T2 target (market order, don't wait for limit fill)
            # Skip if broker has a T2 order (IBKR native brackets — DEC-093)
            if (
                position.t1_filled
                and position.t2_price > 0
                and position.t2_order_id is None  # No broker-side T2 order
                and event.price >= position.t2_price
            ):
                await self._flatten_position(position, reason="t2_target")
                continue

    async def _on_circuit_breaker(self, event: CircuitBreakerEvent) -> None:
        """Handle circuit breaker event — trigger emergency flatten."""
        logger.warning("Circuit breaker triggered: %s", event.reason)
        await self.emergency_flatten()

    # ---------------------------------------------------------------------------
    # Fill Handlers
    # ---------------------------------------------------------------------------

    async def _handle_entry_fill(
        self, pending: PendingManagedOrder, event: OrderFilledEvent
    ) -> None:
        """Entry order filled. Create ManagedPosition with bracket order IDs.

        DEC-117: Stop and target orders are already placed as part of the
        atomic bracket order in on_approved(). We just need to link the
        pre-assigned order IDs to the ManagedPosition.
        """
        approved_event = pending.signal  # OrderApprovedEvent
        signal = approved_event.signal

        filled_shares = event.fill_quantity

        # Extract target prices - handle both tuple and list
        target_prices = signal.target_prices
        if approved_event.modifications and "target_prices" in approved_event.modifications:
            target_prices = approved_event.modifications["target_prices"]

        # Calculate T1 shares — single-target = 100% exit at T1 (DEC-122)
        if len(target_prices) == 1:
            t1_shares = filled_shares
        else:
            t1_shares = int(filled_shares * self._config.t1_position_pct)
            # Ensure at least 1 share for T1 if we have shares
            if t1_shares == 0 and filled_shares > 0:
                t1_shares = 1

        t1_price = target_prices[0] if len(target_prices) >= 1 else 0.0
        t2_price = target_prices[1] if len(target_prices) >= 2 else 0.0

        # Use bracket order IDs from pending (DEC-117)
        position = ManagedPosition(
            symbol=pending.symbol,
            strategy_id=pending.strategy_id,
            entry_price=event.fill_price,
            entry_time=self._clock.now(),
            shares_total=filled_shares,
            shares_remaining=filled_shares,
            stop_price=signal.stop_price,
            original_stop_price=signal.stop_price,  # Never changes
            stop_order_id=pending.bracket_stop_order_id,  # FROM BRACKET
            t1_price=t1_price,
            t1_order_id=pending.bracket_t1_order_id,  # FROM BRACKET
            t1_shares=t1_shares,
            t1_filled=False,
            t2_price=t2_price,
            t2_order_id=pending.bracket_t2_order_id,  # FROM BRACKET (DEC-093)
            high_watermark=event.fill_price,
            time_stop_seconds=signal.time_stop_seconds,  # Per-position time stop (DEC-122)
        )

        # Add to managed positions
        if pending.symbol not in self._managed_positions:
            self._managed_positions[pending.symbol] = []
        self._managed_positions[pending.symbol].append(position)

        # NOTE: No _submit_stop_order, _submit_t1_order, _submit_t2_order calls.
        # Orders are already placed atomically in on_approved() via place_bracket_order().

        # Publish PositionOpenedEvent
        await self._event_bus.publish(
            PositionOpenedEvent(
                position_id=generate_id(),
                strategy_id=pending.strategy_id,
                symbol=pending.symbol,
                entry_price=event.fill_price,
                shares=filled_shares,
                stop_price=signal.stop_price,
                target_prices=tuple(target_prices),
            )
        )

        logger.info(
            "Position opened: %s %d shares @ %.2f (stop=%.2f, T1=%.2f, T2=%.2f)",
            pending.symbol,
            filled_shares,
            event.fill_price,
            signal.stop_price,
            t1_price,
            t2_price,
        )

    async def _handle_t1_fill(self, pending: PendingManagedOrder, event: OrderFilledEvent) -> None:
        """T1 target hit. Move stop to breakeven for remaining shares."""
        positions = self._managed_positions.get(pending.symbol, [])
        position = self._find_position_by_t1_order(positions, event.order_id)
        if position is None:
            logger.warning("T1 fill for %s but no matching position", pending.symbol)
            return

        # Record T1 partial exit
        t1_pnl = (event.fill_price - position.entry_price) * event.fill_quantity
        position.realized_pnl += t1_pnl
        position.shares_remaining -= event.fill_quantity
        position.t1_filled = True
        position.t1_order_id = None

        # If position fully closed by T1 (single-target — DEC-122), cancel stop and close
        if position.is_fully_closed:
            # Cancel stop order (no longer needed)
            if position.stop_order_id:
                try:
                    await self._broker.cancel_order(position.stop_order_id)
                except Exception:
                    logger.debug("Could not cancel stop %s", position.stop_order_id)
                self._pending_orders.pop(position.stop_order_id, None)
                position.stop_order_id = None

            logger.info(
                "T1 hit for %s: %d shares @ %.2f (PnL: +%.2f). Position fully closed.",
                pending.symbol,
                event.fill_quantity,
                event.fill_price,
                t1_pnl,
            )
            await self._close_position(position, event.fill_price, ExitReason.TARGET_1)
            return

        # Cancel old stop (was for full position size)
        if position.stop_order_id:
            old_stop_id = position.stop_order_id
            try:
                await self._broker.cancel_order(old_stop_id)
            except Exception:
                logger.exception("Failed to cancel old stop %s", old_stop_id)
            # Remove from pending since we cancelled it
            self._pending_orders.pop(old_stop_id, None)
            position.stop_order_id = None

        # Submit new stop at breakeven for remaining shares
        if self._config.enable_stop_to_breakeven:
            breakeven_price = position.entry_price * (1 + self._config.breakeven_buffer_pct)
            position.stop_price = breakeven_price
        else:
            breakeven_price = position.stop_price

        await self._submit_stop_order(position, position.shares_remaining, breakeven_price)

        logger.info(
            "T1 hit for %s: %d shares @ %.2f (PnL: +%.2f). "
            "Stop moved to breakeven %.2f for %d remaining shares.",
            pending.symbol,
            event.fill_quantity,
            event.fill_price,
            t1_pnl,
            breakeven_price,
            position.shares_remaining,
        )

    async def _handle_t2_fill(self, pending: PendingManagedOrder, event: OrderFilledEvent) -> None:
        """T2 target hit via broker-side limit order (IBKR native brackets — DEC-093).

        Cancel stop order and close position.
        """
        positions = self._managed_positions.get(pending.symbol, [])
        position = self._find_position_by_t2_order(positions, event.order_id)
        if position is None:
            logger.warning("T2 fill for %s but no matching position", pending.symbol)
            return

        # Record T2 exit
        t2_pnl = (event.fill_price - position.entry_price) * event.fill_quantity
        position.realized_pnl += t2_pnl
        position.shares_remaining -= event.fill_quantity
        position.t2_order_id = None

        # Cancel stop order
        if position.stop_order_id:
            try:
                await self._broker.cancel_order(position.stop_order_id)
            except Exception:
                logger.exception("Failed to cancel stop order %s", position.stop_order_id)
            self._pending_orders.pop(position.stop_order_id, None)
            position.stop_order_id = None

        await self._close_position(position, event.fill_price, ExitReason.TARGET_2)

        logger.info(
            "T2 hit for %s: %d shares @ %.2f (PnL: +%.2f). Position closed.",
            pending.symbol,
            event.fill_quantity,
            event.fill_price,
            t2_pnl,
        )

    async def _handle_stop_fill(
        self, pending: PendingManagedOrder, event: OrderFilledEvent
    ) -> None:
        """Stop loss triggered. Close position (or remaining shares)."""
        positions = self._managed_positions.get(pending.symbol, [])
        position = self._find_position_by_stop_order(positions, event.order_id)
        if position is None:
            logger.warning("Stop fill for %s but no matching position", pending.symbol)
            return

        # Record stop exit
        stop_pnl = (event.fill_price - position.entry_price) * event.fill_quantity
        position.realized_pnl += stop_pnl
        position.shares_remaining -= event.fill_quantity
        position.stop_order_id = None

        # Cancel T1 limit if still open
        if position.t1_order_id and not position.t1_filled:
            try:
                await self._broker.cancel_order(position.t1_order_id)
            except Exception:
                logger.exception("Failed to cancel T1 order %s", position.t1_order_id)
            self._pending_orders.pop(position.t1_order_id, None)
            position.t1_order_id = None

        # Cancel T2 limit if still open (IBKR native brackets — DEC-093)
        if position.t2_order_id:
            try:
                await self._broker.cancel_order(position.t2_order_id)
            except Exception:
                logger.exception("Failed to cancel T2 order %s", position.t2_order_id)
            self._pending_orders.pop(position.t2_order_id, None)
            position.t2_order_id = None

        await self._close_position(position, event.fill_price, ExitReason.STOP_LOSS)

        logger.info(
            "Stop hit for %s: %d shares @ %.2f (PnL: %.2f). Position closed.",
            pending.symbol,
            event.fill_quantity,
            event.fill_price,
            stop_pnl,
        )

    async def _handle_flatten_fill(
        self, pending: PendingManagedOrder, event: OrderFilledEvent
    ) -> None:
        """Market order to flatten position has filled."""
        positions = self._managed_positions.get(pending.symbol, [])
        # Find the position that was being flattened
        position = next(
            (p for p in positions if p.shares_remaining > 0),
            None,
        )
        if position is None:
            logger.warning("Flatten fill for %s but no open position", pending.symbol)
            return

        flatten_pnl = (event.fill_price - position.entry_price) * event.fill_quantity
        position.realized_pnl += flatten_pnl
        position.shares_remaining -= event.fill_quantity

        # Determine exit reason based on context
        exit_reason = ExitReason.TIME_STOP
        if self._flattened_today:
            exit_reason = ExitReason.EOD_FLATTEN

        await self._close_position(position, event.fill_price, exit_reason)

    # ---------------------------------------------------------------------------
    # Fallback Poll Loop
    # ---------------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Runs every N seconds. Handles time-based exits and EOD flatten."""
        while self._running:
            try:
                await asyncio.sleep(self._config.fallback_poll_interval_seconds)
                if not self._running:
                    break

                now = self._clock.now()

                # Check EOD flatten (MD-4b-2)
                if not self._flattened_today:
                    et_tz = ZoneInfo(self._config.eod_flatten_timezone)
                    # Convert to ET for comparison
                    if now.tzinfo is not None:
                        now_et = now.astimezone(et_tz)
                    else:
                        now_et = now.replace(tzinfo=et_tz)
                    flatten_time = time.fromisoformat(self._config.eod_flatten_time)
                    if now_et.time() >= flatten_time:
                        await self.eod_flatten()
                        self._flattened_today = True
                        continue

                # Check time stops on all positions
                for symbol, positions in list(self._managed_positions.items()):
                    for position in positions:
                        if position.is_fully_closed:
                            continue

                        elapsed_seconds = (now - position.entry_time).total_seconds()

                        # Per-position time stop from signal (DEC-122)
                        if (
                            position.time_stop_seconds is not None
                            and elapsed_seconds >= position.time_stop_seconds
                        ):
                            logger.info(
                                "Time stop for %s: open %.0f sec (limit=%d sec)",
                                symbol,
                                elapsed_seconds,
                                position.time_stop_seconds,
                            )
                            await self._flatten_position(position, reason="time_stop")
                            continue

                        # Fallback: global max_position_duration_minutes
                        elapsed_minutes = elapsed_seconds / 60
                        if elapsed_minutes >= self._config.max_position_duration_minutes:
                            logger.info(
                                "Time stop for %s: open %.1f min (limit=%d min)",
                                symbol,
                                elapsed_minutes,
                                self._config.max_position_duration_minutes,
                            )
                            await self._flatten_position(position, reason="time_stop")

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in fallback poll loop")

    # ---------------------------------------------------------------------------
    # EOD Flatten and Emergency Flatten
    # ---------------------------------------------------------------------------

    async def eod_flatten(self) -> None:
        """Close all positions at market. Scheduled at eod_flatten_time.

        1. Cancel all open orders (stops, targets)
        2. Close all remaining positions at market
        """
        logger.info("EOD flatten triggered — closing all positions")
        self._flattened_today = True

        for _symbol, positions in list(self._managed_positions.items()):
            for position in positions:
                if not position.is_fully_closed:
                    await self._flatten_position(position, reason="eod_flatten")

    async def emergency_flatten(self) -> None:
        """Close everything immediately. Used by circuit breakers.

        Same as eod_flatten but callable at any time.
        """
        logger.warning("EMERGENCY FLATTEN — closing all positions immediately")
        await self.eod_flatten()

    async def reconstruct_from_broker(self) -> None:
        """Reconstruct managed positions from broker state.

        Called at startup to recover any open positions that existed
        before a restart.

        1. Query broker for all open positions.
        2. Query broker for all open orders.
        3. For each position, create a ManagedPosition with:
           - Entry price from broker position data.
           - Stop price from any matching stop order.
           - T1/T2 inferred from stop orders and limit orders.
        4. Subscribe to TickEvents for these symbols.

        Limitations:
        - Cannot reconstruct exact entry_time (not available from broker).
        - Cannot reconstruct original strategy_id (uses "reconstructed").
        - T1/T2 status is inferred from order types, not exact.

        These limitations are acceptable because:
        - Time stops use conservative defaults.
        - The position will still be managed (stops moved, EOD flattened).
        - Full accuracy requires the system to not crash, which is the goal.
        """
        try:
            positions = await self._broker.get_positions()

            if not positions:
                logger.info("Order Manager reconstruction: No open positions at broker.")
                return

            orders = await self._broker.get_open_orders()

            logger.info(
                "Reconstructing %d positions and %d open orders from broker",
                len(positions),
                len(orders),
            )

            # Build order lookup by symbol
            orders_by_symbol: dict[str, list] = {}
            for order in orders:
                symbol = getattr(order, "symbol", "")
                if symbol:
                    if symbol not in orders_by_symbol:
                        orders_by_symbol[symbol] = []
                    orders_by_symbol[symbol].append(order)

            for pos in positions:
                symbol = getattr(pos, "symbol", str(pos))
                qty = int(getattr(pos, "qty", 0))
                avg_entry = float(getattr(pos, "avg_entry_price", 0.0))

                # Find matching stop order
                stop_price = 0.0
                stop_order_id = None
                symbol_orders = orders_by_symbol.get(symbol, [])
                for order in symbol_orders:
                    order_type = str(getattr(order, "order_type", "")).lower()
                    if "stop" in order_type:
                        stop_price = float(getattr(order, "stop_price", 0) or 0)
                        stop_order_id = str(getattr(order, "id", ""))
                        break

                # Find matching limit order (T1)
                t1_price = 0.0
                t1_order_id = None
                t1_shares = 0
                for order in symbol_orders:
                    order_type = str(getattr(order, "order_type", "")).lower()
                    if "limit" in order_type:
                        t1_price = float(getattr(order, "limit_price", 0) or 0)
                        t1_order_id = str(getattr(order, "id", ""))
                        t1_shares = int(getattr(order, "qty", 0) or 0)
                        break

                managed = ManagedPosition(
                    symbol=symbol,
                    strategy_id="reconstructed",
                    entry_price=avg_entry,
                    entry_time=self._clock.now(),  # Approximation
                    shares_total=qty,
                    shares_remaining=qty,
                    stop_price=stop_price,
                    original_stop_price=stop_price,  # Best approximation on reconstruct
                    stop_order_id=stop_order_id,
                    t1_price=t1_price,
                    t1_order_id=t1_order_id,
                    t1_shares=t1_shares,
                    t1_filled=(t1_order_id is None and t1_shares == 0),
                    t2_price=0.0,  # Unknown — position rides to stop or EOD
                    high_watermark=avg_entry,
                )

                if symbol not in self._managed_positions:
                    self._managed_positions[symbol] = []
                self._managed_positions[symbol].append(managed)

                # Track the stop and T1 orders in pending orders
                if stop_order_id:
                    self._pending_orders[stop_order_id] = PendingManagedOrder(
                        order_id=stop_order_id,
                        symbol=symbol,
                        strategy_id="reconstructed",
                        order_type="stop",
                        shares=qty,
                    )
                if t1_order_id:
                    self._pending_orders[t1_order_id] = PendingManagedOrder(
                        order_id=t1_order_id,
                        symbol=symbol,
                        strategy_id="reconstructed",
                        order_type="t1_target",
                        shares=t1_shares,
                    )

                logger.info(
                    "Reconstructed position: %s %d shares @ %.2f (stop=%.2f)",
                    symbol,
                    qty,
                    avg_entry,
                    stop_price,
                )

            logger.info(
                "Order Manager reconstruction complete: %d positions recovered",
                len(positions),
            )

        except Exception as e:
            logger.error("Order Manager reconstruction failed: %s", e)
            # Don't crash — system can still manage new positions

    # ---------------------------------------------------------------------------
    # Helper Methods
    # ---------------------------------------------------------------------------

    async def _submit_stop_order(
        self, position: ManagedPosition, shares: int, stop_price: float
    ) -> None:
        """Submit a stop-loss order and track it."""
        retry_count = 0
        order: Order | None = None

        while retry_count <= self._config.stop_retry_max:
            try:
                order = Order(
                    strategy_id=position.strategy_id,
                    symbol=position.symbol,
                    side=OrderSide.SELL,
                    order_type=TradingOrderType.STOP,
                    quantity=shares,
                    stop_price=stop_price,
                )
                result = await self._broker.place_order(order)
                position.stop_order_id = result.order_id

                self._pending_orders[result.order_id] = PendingManagedOrder(
                    order_id=result.order_id,
                    symbol=position.symbol,
                    strategy_id=position.strategy_id,
                    order_type="stop",
                    shares=shares,
                )
                return

            except Exception:
                retry_count += 1
                if retry_count <= self._config.stop_retry_max:
                    logger.warning(
                        "Stop order failed for %s, retry %d/%d",
                        position.symbol,
                        retry_count,
                        self._config.stop_retry_max,
                    )
                else:
                    logger.exception(
                        "Stop retry failed for %s. Emergency flattening.",
                        position.symbol,
                    )
                    await self._flatten_position(position, reason="stop_order_failure")

    async def _submit_t1_order(
        self, position: ManagedPosition, shares: int, limit_price: float
    ) -> None:
        """Submit a T1 limit sell order and track it."""
        try:
            order = Order(
                strategy_id=position.strategy_id,
                symbol=position.symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.LIMIT,
                quantity=shares,
                limit_price=limit_price,
            )
            result = await self._broker.place_order(order)
            position.t1_order_id = result.order_id

            self._pending_orders[result.order_id] = PendingManagedOrder(
                order_id=result.order_id,
                symbol=position.symbol,
                strategy_id=position.strategy_id,
                order_type="t1_target",
                shares=shares,
            )
        except Exception:
            logger.exception("Failed to submit T1 order for %s", position.symbol)

    async def _submit_t2_order(
        self, position: ManagedPosition, shares: int, limit_price: float
    ) -> None:
        """Submit a T2 limit sell order and track it.

        This enables broker-side T2 execution for IBKR native brackets (DEC-093).
        When T2 order ID is set, on_tick() skips client-side T2 monitoring.
        """
        try:
            order = Order(
                strategy_id=position.strategy_id,
                symbol=position.symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.LIMIT,
                quantity=shares,
                limit_price=limit_price,
            )
            result = await self._broker.place_order(order)
            position.t2_order_id = result.order_id

            self._pending_orders[result.order_id] = PendingManagedOrder(
                order_id=result.order_id,
                symbol=position.symbol,
                strategy_id=position.strategy_id,
                order_type="t2",
                shares=shares,
            )
        except Exception:
            logger.exception("Failed to submit T2 order for %s", position.symbol)

    async def _flatten_position(self, position: ManagedPosition, reason: str) -> None:
        """Cancel all open orders for this position and submit market sell."""
        # Cancel stop order
        if position.stop_order_id:
            try:
                await self._broker.cancel_order(position.stop_order_id)
            except Exception:
                logger.debug("Could not cancel stop %s", position.stop_order_id)
            self._pending_orders.pop(position.stop_order_id, None)
            position.stop_order_id = None

        # Cancel T1 if still open
        if position.t1_order_id and not position.t1_filled:
            try:
                await self._broker.cancel_order(position.t1_order_id)
            except Exception:
                logger.debug("Could not cancel T1 %s", position.t1_order_id)
            self._pending_orders.pop(position.t1_order_id, None)
            position.t1_order_id = None

        # Cancel T2 if still open (IBKR native brackets — DEC-093)
        if position.t2_order_id:
            try:
                await self._broker.cancel_order(position.t2_order_id)
            except Exception:
                logger.debug("Could not cancel T2 %s", position.t2_order_id)
            self._pending_orders.pop(position.t2_order_id, None)
            position.t2_order_id = None

        # Submit market sell for remaining shares
        if position.shares_remaining > 0:
            try:
                order = Order(
                    strategy_id=position.strategy_id,
                    symbol=position.symbol,
                    side=OrderSide.SELL,
                    order_type=TradingOrderType.MARKET,
                    quantity=position.shares_remaining,
                )
                result = await self._broker.place_order(order)
                pending = PendingManagedOrder(
                    order_id=result.order_id,
                    symbol=position.symbol,
                    strategy_id=position.strategy_id,
                    order_type="flatten",
                    shares=position.shares_remaining,
                )
                self._pending_orders[result.order_id] = pending

                # Handle immediate fill (SimulatedBroker fills market orders synchronously)
                if result.status == OrderStatus.FILLED:
                    fill_event = OrderFilledEvent(
                        order_id=result.order_id,
                        fill_price=result.filled_avg_price,
                        fill_quantity=result.filled_quantity,
                    )
                    await self.on_fill(fill_event)
            except Exception:
                logger.exception(
                    "CRITICAL: Failed to flatten %s (%d shares remain unprotected)",
                    position.symbol,
                    position.shares_remaining,
                )

    async def _close_position(
        self,
        position: ManagedPosition,
        exit_price: float,
        exit_reason: ExitReason,
    ) -> None:
        """Finalize a fully closed position. Log trade, publish event, clean up."""
        hold_seconds = int((self._clock.now() - position.entry_time).total_seconds())

        # Calculate weighted average exit price from realized P&L.
        # This ensures exit_price is consistent with gross_pnl when T1 hit
        # before the final exit (stop/flatten/etc).
        # Formula: weighted_exit = (realized_pnl / shares_total) + entry_price
        if position.shares_total > 0:
            weighted_exit_price = (
                position.realized_pnl / position.shares_total
            ) + position.entry_price
        else:
            weighted_exit_price = exit_price

        # Publish PositionClosedEvent
        await self._event_bus.publish(
            PositionClosedEvent(
                position_id=generate_id(),
                strategy_id=position.strategy_id,
                exit_price=weighted_exit_price,
                realized_pnl=position.realized_pnl,
                exit_reason=exit_reason,
                hold_duration_seconds=hold_seconds,
                entry_time=position.entry_time,
                exit_time=self._clock.now(),
            )
        )

        # Log trade via TradeLogger if available
        if self._trade_logger:
            try:
                from argus.models.trading import OrderSide, Trade

                trade = Trade(
                    strategy_id=position.strategy_id,
                    symbol=position.symbol,
                    side=OrderSide.BUY,
                    entry_price=position.entry_price,
                    entry_time=position.entry_time,
                    exit_price=weighted_exit_price,
                    exit_time=self._clock.now(),
                    shares=position.shares_total,
                    stop_price=position.original_stop_price,  # Use original, not moved
                    target_prices=[position.t1_price, position.t2_price],
                    exit_reason=exit_reason,
                    gross_pnl=position.realized_pnl,
                )
                await self._trade_logger.log_trade(trade)
            except Exception:
                logger.exception("Failed to log trade for %s", position.symbol)

        # Remove from managed positions
        positions = self._managed_positions.get(position.symbol, [])
        if position in positions:
            positions.remove(position)
        if not positions:
            self._managed_positions.pop(position.symbol, None)

        logger.info(
            "Position closed: %s | PnL: %.2f | Reason: %s | Hold: %ds",
            position.symbol,
            position.realized_pnl,
            exit_reason.value,
            hold_seconds,
        )

    def _find_position_by_t1_order(
        self, positions: list[ManagedPosition], order_id: str
    ) -> ManagedPosition | None:
        """Find position whose T1 order matches the given order_id."""
        return next(
            (p for p in positions if p.t1_order_id == order_id),
            None,
        )

    def _find_position_by_stop_order(
        self, positions: list[ManagedPosition], order_id: str
    ) -> ManagedPosition | None:
        """Find position whose stop order matches the given order_id."""
        return next(
            (p for p in positions if p.stop_order_id == order_id),
            None,
        )

    def _find_position_by_t2_order(
        self, positions: list[ManagedPosition], order_id: str
    ) -> ManagedPosition | None:
        """Find position whose T2 order matches the given order_id."""
        return next(
            (p for p in positions if p.t2_order_id == order_id),
            None,
        )

    def reset_daily_state(self) -> None:
        """Reset for new trading day. Called by orchestrator pre-market."""
        self._flattened_today = False
        # Positions should be empty after EOD flatten, but clear just in case
        self._managed_positions.clear()
        self._pending_orders.clear()

    @property
    def has_open_positions(self) -> bool:
        """True if any managed positions are still open."""
        return any(
            any(not p.is_fully_closed for p in positions)
            for positions in self._managed_positions.values()
        )

    @property
    def open_position_count(self) -> int:
        """Number of currently open managed positions."""
        return sum(
            sum(1 for p in positions if not p.is_fully_closed)
            for positions in self._managed_positions.values()
        )

    def get_managed_positions(self) -> dict[str, list[ManagedPosition]]:
        """Return a copy of managed positions for cross-strategy queries.

        Returns:
            Dict mapping symbol to list of ManagedPosition objects.
            Returns copies to prevent external mutation.
        """
        return {k: list(v) for k, v in self._managed_positions.items()}

    def get_all_positions_flat(self) -> list[ManagedPosition]:
        """Return all managed positions as a flat list (for API/UI).

        Returns:
            List of all ManagedPosition objects currently being tracked,
            including partially closed positions.
        """
        result: list[ManagedPosition] = []
        for positions in self._managed_positions.values():
            result.extend(positions)
        return result
