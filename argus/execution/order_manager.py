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
import time as _time
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from argus.core.config import (
    BrokerSource,
    ExitManagementConfig,
    OrderManagerConfig,
    ReconciliationConfig,
    StartupConfig,
    deep_update,
)
from argus.core.exit_math import (
    compute_effective_stop,
    compute_escalation_stop,
    compute_trailing_stop,
)
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
    PositionUpdatedEvent,
    ShutdownRequestedEvent,
    Side,
    SignalEvent,
    TickEvent,
)
from argus.core.ids import generate_id
from argus.execution.broker import Broker
from argus.models.trading import Order, OrderSide, OrderStatus
from argus.utils.log_throttle import ThrottledLogger
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
    quality_grade: str = ""     # From signal, set at entry fill
    quality_score: float = 0.0  # From signal, set at entry fill

    # Exit management fields (Sprint 28.5 S4a)
    trail_active: bool = False  # Whether trailing stop is currently active
    trail_stop_price: float = 0.0  # Current computed trail stop price
    escalation_phase_index: int = -1  # Index into phases list (-1 = no phase reached)
    exit_config: ExitManagementConfig | None = None  # Per-strategy resolved config
    atr_value: float | None = None  # Captured from signal at entry

    # MFE/MAE tracking (Sprint 29.5 S6)
    mfe_price: float = 0.0      # Highest price reached while position open
    mae_price: float = 0.0      # Lowest price reached while position open
    mfe_r: float = 0.0          # MFE in R-multiples
    mae_r: float = 0.0          # MAE in R-multiples (negative)
    mfe_time: datetime | None = None  # When MFE was reached
    mae_time: datetime | None = None  # When MAE was reached

    @property
    def is_fully_closed(self) -> bool:
        """Return True if no shares remain."""
        return self.shares_remaining <= 0


@dataclass
class ReconciliationResult:
    """Typed result from position reconciliation.

    Replaces dict[str, object] for type safety at the API boundary.
    """

    timestamp: str
    status: str  # "synced" or "mismatch"
    discrepancies: list[dict[str, object]]


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
    # Execution quality tracking (DEC-358 §5.1)
    expected_fill_price: float = 0.0
    signal_timestamp: datetime | None = None


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
        db_manager: Any | None = None,
        broker_source: BrokerSource = BrokerSource.SIMULATED,
        auto_cleanup_orphans: bool = False,
        reconciliation_config: ReconciliationConfig | None = None,
        startup_config: StartupConfig | None = None,
        exit_config: ExitManagementConfig | None = None,
        strategy_exit_overrides: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the Order Manager.

        Args:
            event_bus: The event bus for pub/sub.
            broker: The broker implementation.
            clock: Clock protocol for time operations.
            config: Order Manager configuration.
            trade_logger: Optional TradeLogger for persistence.
            db_manager: Optional DatabaseManager for execution record persistence.
            broker_source: Broker type, used to skip amendment for SimulatedBroker.
            auto_cleanup_orphans: When True, reconciliation auto-closes orphaned
                positions (internal_qty > 0, broker_qty == 0). Deprecated — use
                reconciliation_config.auto_cleanup_orphans instead.
            reconciliation_config: Typed reconciliation settings (Sprint 27.95).
            startup_config: Startup behavior settings (Sprint 27.95 S4).
            exit_config: Exit management config (trailing stops, escalation). Sprint 28.5.
            strategy_exit_overrides: Per-strategy exit_management YAML overrides
                keyed by strategy_id. Deep-merged with global exit_config (AMD-1).
        """
        self._event_bus = event_bus
        self._broker = broker
        self._clock = clock
        self._config = config
        self._trade_logger = trade_logger
        self._db_manager = db_manager
        self._broker_source = broker_source
        # Reconciliation config: prefer typed config, fall back to legacy bool
        self._reconciliation_config = reconciliation_config or ReconciliationConfig(
            auto_cleanup_orphans=auto_cleanup_orphans,
        )
        # Startup config (Sprint 27.95 S4)
        self._startup_config = startup_config or StartupConfig()
        # Exit management config (trailing stops, escalation — Sprint 28.5)
        self._exit_config = exit_config
        # Per-strategy exit overrides: raw YAML dicts keyed by strategy_id
        self._strategy_exit_overrides = strategy_exit_overrides or {}
        # Cache for merged per-strategy ExitManagementConfig (computed once per strategy)
        self._exit_config_cache: dict[str, ExitManagementConfig] = {}

        # Active positions: keyed by symbol (list to support multiple positions)
        self._managed_positions: dict[str, list[ManagedPosition]] = {}

        # Orders awaiting fill confirmation: keyed by order_id
        self._pending_orders: dict[str, PendingManagedOrder] = {}

        # Flatten-pending guard: symbol → (order_id, monotonic_time, retry_count)
        # Prevents duplicate flatten orders; timeout resubmits stale ones (Sprint 28.75)
        self._flatten_pending: dict[str, tuple[str, float, int]] = {}

        # Throttled logger for high-frequency messages (Sprint 28.75)
        self._throttled = ThrottledLogger(logger)

        # Broker-confirmed entry fill tracking (Sprint 27.95)
        self._broker_confirmed: dict[str, bool] = {}

        # Consecutive reconciliation miss counter (Sprint 27.95)
        self._reconciliation_miss_count: dict[str, int] = {}

        # Latest reconciliation result
        self._last_reconciliation: ReconciliationResult | None = None

        # Async tasks
        self._poll_task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._flattened_today: bool = False

        # Stop resubmission retry counter: {symbol: count} (Sprint 27.95 S2)
        self._stop_retry_count: dict[str, int] = {}

        # Amended bracket prices: {symbol: (stop, t1, t2)} for revision-rejected
        self._amended_prices: dict[str, tuple[float, float, float]] = {}

        # Flatten circuit breaker: cycle count and abandoned set (Sprint 29.5 R2)
        self._flatten_cycle_count: dict[str, int] = {}
        self._flatten_abandoned: set[str] = set()

        # Startup flatten queue: (symbol, qty) tuples queued for market open (Sprint 29.5 R4)
        self._startup_flatten_queue: list[tuple[str, int]] = []

        # Fill deduplication: {order_id: last_cumulative_filled_qty}
        self._last_fill_state: dict[str, float] = {}
        # Reverse index: {symbol: set(order_ids)} for cleanup on position close
        self._fill_order_ids_by_symbol: dict[str, set[str]] = {}

        # P&L update throttle: {symbol: last_publish_monotonic} (Sprint 27.65 S4)
        self._pnl_last_published: dict[str, float] = {}
        self._pnl_throttle_seconds: float = 1.0

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
    # Exit Config Resolution
    # ---------------------------------------------------------------------------

    def _get_exit_config(self, strategy_id: str) -> ExitManagementConfig:
        """Return the resolved ExitManagementConfig for a strategy.

        If the strategy has a per-strategy override in its YAML
        (``exit_management:`` key), deep-merges the override into the global
        config using :func:`deep_update` (AMD-1 field-level merge).  The
        merged result is validated via Pydantic and cached per strategy_id.

        Args:
            strategy_id: The strategy identifier to look up.

        Returns:
            The resolved ExitManagementConfig (global or merged).
        """
        if strategy_id in self._exit_config_cache:
            return self._exit_config_cache[strategy_id]

        global_config = self._exit_config or ExitManagementConfig()

        override = self._strategy_exit_overrides.get(strategy_id)
        if override:
            base_dict = global_config.model_dump()
            merged_dict = deep_update(base_dict, override)
            resolved = ExitManagementConfig(**merged_dict)
        else:
            resolved = global_config

        self._exit_config_cache[strategy_id] = resolved
        return resolved

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

        # Signals with share_count=0 are pending Dynamic Sizer (Sprint 24 S6a).
        # Do not submit broker orders until the sizer fills in the share count.
        if share_count == 0:
            logger.debug(
                "Signal for %s has share_count=0 (Dynamic Sizer pending), skipping order.",
                signal.symbol,
            )
            return

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
            expected_fill_price=signal.entry_price,
            signal_timestamp=self._clock.now(),
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

        Includes duplicate fill deduplication: if the same order_id reports
        the same cumulative filled quantity twice, the second callback is ignored.
        """
        # Duplicate fill deduplication (Sprint 27.95 S2)
        order_id = event.order_id
        cumulative_qty = float(event.fill_quantity)
        last_qty = self._last_fill_state.get(order_id)
        if last_qty is not None and cumulative_qty == last_qty:
            logger.debug(
                "Duplicate fill callback ignored: order %s cumulative %s",
                order_id,
                cumulative_qty,
            )
            return
        self._last_fill_state[order_id] = cumulative_qty

        pending = self._pending_orders.pop(event.order_id, None)
        if pending is None:
            logger.debug("Fill for unknown order_id %s, ignoring", event.order_id)
            return

        # Track order→symbol mapping for fill dedup cleanup on position close
        if pending.symbol not in self._fill_order_ids_by_symbol:
            self._fill_order_ids_by_symbol[pending.symbol] = set()
        self._fill_order_ids_by_symbol[pending.symbol].add(order_id)

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
        the position still has protection. If it was a flatten order,
        clear the flatten-pending guard so re-flattening can proceed.
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

        # Clear flatten-pending guard if this was a flatten order
        if pending.order_type == "flatten":
            entry = self._flatten_pending.get(pending.symbol)
            if entry is not None and entry[0] == event.order_id:
                self._flatten_pending.pop(pending.symbol, None)
                logger.info(
                    "Flatten-pending cleared for %s (order %s cancelled)",
                    pending.symbol,
                    event.order_id,
                )

        # Revision-rejected detection: IBKR may reject bracket amendments
        is_revision_rejected = "Revision rejected" in (event.reason or "")

        if pending.order_type in ("stop", "t1_target", "t2") and is_revision_rejected:
            # Bracket amendment was rejected — resubmit as fresh order (not retry flow)
            await self._handle_revision_rejected(pending, event)
            return

        if pending.order_type == "stop":
            # Critical: position may be unprotected
            positions = self._managed_positions.get(pending.symbol, [])
            for pos in positions:
                if pos.stop_order_id == event.order_id:
                    pos.stop_order_id = None
                    await self._resubmit_stop_with_retry(pos)
                    break

        if pending.order_type == "t1_target":
            # Clear T1 order ID on the position
            positions = self._managed_positions.get(pending.symbol, [])
            for pos in positions:
                if pos.t1_order_id == event.order_id:
                    pos.t1_order_id = None
                    # Check bracket exhaustion: all bracket legs gone
                    if pos.stop_order_id is None and pos.t1_order_id is None:
                        logger.warning(
                            "All bracket legs cancelled for %s — "
                            "position unprotected, attempting flatten",
                            pending.symbol,
                        )
                        await self._flatten_position(pos, reason="bracket_exhausted")
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

            # Update MFE/MAE (Sprint 29.5 S6) — O(1) comparisons, no DB lookups
            if event.price > position.mfe_price:
                position.mfe_price = event.price
                position.mfe_time = self._clock.now()
                risk = position.entry_price - position.original_stop_price
                if risk > 0:
                    position.mfe_r = (event.price - position.entry_price) / risk
            if event.price < position.mae_price:
                position.mae_price = event.price
                position.mae_time = self._clock.now()
                risk = position.entry_price - position.original_stop_price
                if risk > 0:
                    position.mae_r = -((position.entry_price - event.price) / risk)

            # --- after_profit_pct trail activation (Sprint 28.5) ---
            if (
                not position.trail_active
                and position.exit_config is not None
                and position.exit_config.trailing_stop.enabled
                and position.exit_config.trailing_stop.activation == "after_profit_pct"
            ):
                unrealized_pct = (
                    (event.price - position.entry_price) / position.entry_price
                )
                if unrealized_pct >= position.exit_config.trailing_stop.activation_profit_pct:
                    position.trail_active = True

            # --- Trail stop check (Sprint 28.5) ---
            if position.trail_active and position.exit_config:
                trail_cfg = position.exit_config.trailing_stop
                new_trail = compute_trailing_stop(
                    position.high_watermark, position.atr_value,
                    trail_type=trail_cfg.type, atr_multiplier=trail_cfg.atr_multiplier,
                    trail_percent=trail_cfg.percent, fixed_distance=trail_cfg.fixed_distance,
                    min_trail_distance=trail_cfg.min_trail_distance, enabled=trail_cfg.enabled,
                )
                if new_trail is not None:
                    # Ratchet up only — trail price never decreases
                    position.trail_stop_price = max(position.trail_stop_price, new_trail)

                effective_stop = compute_effective_stop(
                    position.stop_price,
                    position.trail_stop_price or None,
                    None,  # escalation checked in poll loop
                )
                if event.price <= effective_stop:
                    await self._trail_flatten(position, event.price)
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

        # Publish throttled P&L updates for open positions (Sprint 27.65 S4)
        await self._publish_position_pnl(event.symbol, event.price)

    async def _resubmit_stop_with_retry(self, position: ManagedPosition) -> None:
        """Resubmit a cancelled stop order with retry tracking and backoff.

        Increments per-symbol retry counter. If max retries exceeded, triggers
        emergency flatten. Uses exponential backoff (1s, 2s, 4s) between retries.

        Args:
            position: The position whose stop was cancelled.
        """
        symbol = position.symbol
        count = self._stop_retry_count.get(symbol, 0) + 1
        self._stop_retry_count[symbol] = count

        if count > self._config.stop_cancel_retry_max:
            logger.error(
                "Stop resubmission exhausted for %s after %d attempts "
                "— triggering emergency flatten",
                symbol,
                count,
            )
            await self._flatten_position(position, reason="stop_retry_exhausted")
            return

        # Exponential backoff: 2^(count-1) seconds → 1s, 2s, 4s
        backoff = 2 ** (count - 1)
        logger.warning(
            "Stop order cancelled for %s. Retry %d/%d (backoff %ds).",
            symbol,
            count,
            self._config.stop_cancel_retry_max,
            backoff,
        )
        await asyncio.sleep(backoff)
        await self._submit_stop_order(position, position.shares_remaining, position.stop_price)

    async def _handle_revision_rejected(
        self, pending: PendingManagedOrder, event: OrderCancelledEvent
    ) -> None:
        """Handle IBKR 'Revision rejected' cancel by submitting a fresh order.

        When IBKR rejects a bracket amendment (modify-in-place), we resubmit
        the order as brand-new instead of entering the normal retry flow.
        If the fresh order also fails, it enters the stop retry flow.

        Args:
            pending: The cancelled pending order.
            event: The cancellation event with reason.
        """
        symbol = pending.symbol
        positions = self._managed_positions.get(symbol, [])

        logger.info(
            "Bracket amendment rejected for %s — resubmitting as fresh order",
            symbol,
        )

        if pending.order_type == "stop":
            for pos in positions:
                if pos.stop_order_id == event.order_id:
                    pos.stop_order_id = None
                    # Use amended prices if available, otherwise current position prices
                    amended = self._amended_prices.get(symbol)
                    stop_price = amended[0] if amended else pos.stop_price
                    try:
                        await self._submit_stop_order(
                            pos, pos.shares_remaining, stop_price,
                        )
                    except Exception:
                        logger.warning(
                            "Fresh stop order failed for %s after revision rejected "
                            "— entering retry flow",
                            symbol,
                        )
                        await self._resubmit_stop_with_retry(pos)
                    break

        elif pending.order_type == "t1_target":
            for pos in positions:
                if pos.t1_order_id == event.order_id:
                    pos.t1_order_id = None
                    amended = self._amended_prices.get(symbol)
                    t1_price = amended[1] if amended else pos.t1_price
                    await self._submit_t1_order(pos, pos.t1_shares, t1_price)
                    break

        elif pending.order_type == "t2":
            for pos in positions:
                if pos.t2_order_id == event.order_id:
                    pos.t2_order_id = None
                    amended = self._amended_prices.get(symbol)
                    t2_price = amended[2] if amended else pos.t2_price
                    t2_shares = pos.shares_remaining - pos.t1_shares
                    if t2_shares > 0:
                        await self._submit_t2_order(pos, t2_shares, t2_price)
                    break

    async def _publish_position_pnl(self, symbol: str, current_price: float) -> None:
        """Compute and publish unrealized P&L for open positions on a symbol.

        Throttled to at most once per second per symbol to avoid flooding.

        Args:
            symbol: The ticker symbol.
            current_price: Current market price.
        """
        now = _time.monotonic()
        last = self._pnl_last_published.get(symbol, 0.0)
        if now - last < self._pnl_throttle_seconds:
            return

        self._pnl_last_published[symbol] = now

        positions = self._managed_positions.get(symbol)
        if not positions:
            return

        for position in positions:
            if position.is_fully_closed:
                continue

            # Compute unrealized P&L (long only for V1)
            unrealized_pnl = (current_price - position.entry_price) * position.shares_remaining
            risk_per_share = abs(position.entry_price - position.original_stop_price)
            risk_amount = risk_per_share * position.shares_total
            r_multiple = unrealized_pnl / risk_amount if risk_amount > 0 else 0.0

            await self._event_bus.publish(
                PositionUpdatedEvent(
                    position_id=generate_id(),
                    symbol=symbol,
                    current_price=current_price,
                    unrealized_pnl=round(unrealized_pnl, 2),
                    r_multiple=round(r_multiple, 3),
                    entry_price=position.entry_price,
                    shares=position.shares_remaining,
                    strategy_id=position.strategy_id,
                )
            )

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
            quality_grade=signal.quality_grade,
            quality_score=signal.quality_score,
            exit_config=self._get_exit_config(pending.strategy_id),
            atr_value=signal.atr_value,
            mfe_price=event.fill_price,
            mae_price=event.fill_price,
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

        # Mark position as broker-confirmed (Sprint 27.95)
        self._broker_confirmed[pending.symbol] = True

        logger.info(
            "Position opened: %s %d shares @ %.2f (stop=%.2f, T1=%.2f, T2=%.2f)",
            pending.symbol,
            filled_shares,
            event.fill_price,
            signal.stop_price,
            t1_price,
            t2_price,
        )

        # --- Immediate trail activation (Sprint 28.5) ---
        if (
            position.exit_config is not None
            and position.exit_config.trailing_stop.enabled
            and position.exit_config.trailing_stop.activation == "immediate"
        ):
            position.trail_active = True
            trail_cfg = position.exit_config.trailing_stop
            initial_trail = compute_trailing_stop(
                position.high_watermark, position.atr_value,
                trail_type=trail_cfg.type, atr_multiplier=trail_cfg.atr_multiplier,
                trail_percent=trail_cfg.percent, fixed_distance=trail_cfg.fixed_distance,
                min_trail_distance=trail_cfg.min_trail_distance, enabled=trail_cfg.enabled,
            )
            position.trail_stop_price = initial_trail if initial_trail is not None else 0.0

        # --- Bracket amendment on fill slippage (Sprint 27.65 S2) ---
        await self._amend_bracket_on_slippage(position, signal, event.fill_price)

        # --- Execution Quality Logging (DEC-358 §5.1) ---
        try:
            from argus.execution.execution_record import (
                create_execution_record,
                save_execution_record,
            )
            record = create_execution_record(
                order_id=pending.order_id,
                symbol=pending.symbol,
                strategy_id=pending.strategy_id,
                side="BUY",  # Long-only V1 (DEC-011)
                expected_fill_price=pending.expected_fill_price,
                actual_fill_price=event.fill_price,
                order_size_shares=filled_shares,
                signal_timestamp=pending.signal_timestamp,
                fill_timestamp=self._clock.now(),
                avg_daily_volume=None,  # TODO: wire UM reference data when available
                bid_ask_spread_bps=None,  # Requires L1 data (Standard plan = None)
            )
            if self._db_manager is not None:
                await save_execution_record(self._db_manager, record)
                logger.debug("Execution record saved: %s", record.record_id)
            else:
                logger.debug("No DB manager — execution record not persisted")
        except Exception:
            logger.warning(
                "Failed to save execution record for %s (non-critical)",
                pending.symbol,
                exc_info=True,
            )

    async def _amend_bracket_on_slippage(
        self,
        position: ManagedPosition,
        signal: SignalEvent,
        actual_fill_price: float,
        tolerance: float = 0.01,
    ) -> None:
        """Amend bracket legs when entry fill differs from signal price.

        Shifts stop and target prices by the same delta as the slippage so
        risk/reward ratios are preserved relative to the actual cost basis.

        Skipped for SimulatedBroker (zero slippage by design).

        Args:
            position: The newly opened ManagedPosition.
            signal: The original SignalEvent with expected prices.
            actual_fill_price: The price the entry actually filled at.
            tolerance: Minimum price difference to trigger amendment (default $0.01).
        """
        # Skip for simulated broker — no slippage
        if self._broker_source == BrokerSource.SIMULATED:
            return

        delta = actual_fill_price - signal.entry_price
        if abs(delta) <= tolerance:
            return

        new_stop = position.original_stop_price + delta
        new_t1 = position.t1_price + delta if position.t1_price > 0 else 0.0
        new_t2 = position.t2_price + delta if position.t2_price > 0 else 0.0

        # Safety check: target must be above fill price for longs
        if new_t1 > 0 and new_t1 <= actual_fill_price:
            logger.error(
                "SAFETY: Amended T1 %.2f <= fill %.2f for %s. Cancelling position.",
                new_t1,
                actual_fill_price,
                position.symbol,
            )
            await self._flatten_position(position, reason="bracket_amendment_safety")
            return

        # Cancel existing bracket legs and resubmit with amended prices
        # Cancel stop
        if position.stop_order_id:
            try:
                await self._broker.cancel_order(position.stop_order_id)
            except Exception:
                logger.debug("Could not cancel stop %s for amendment", position.stop_order_id)
            self._pending_orders.pop(position.stop_order_id, None)
            position.stop_order_id = None

        # Cancel T1
        if position.t1_order_id:
            try:
                await self._broker.cancel_order(position.t1_order_id)
            except Exception:
                logger.debug("Could not cancel T1 %s for amendment", position.t1_order_id)
            self._pending_orders.pop(position.t1_order_id, None)
            position.t1_order_id = None

        # Cancel T2
        if position.t2_order_id:
            try:
                await self._broker.cancel_order(position.t2_order_id)
            except Exception:
                logger.debug("Could not cancel T2 %s for amendment", position.t2_order_id)
            self._pending_orders.pop(position.t2_order_id, None)
            position.t2_order_id = None

        # Resubmit with amended prices
        position.stop_price = new_stop
        position.t1_price = new_t1
        position.t2_price = new_t2

        # Store amended prices for revision-rejected resubmission (Sprint 27.95 S2)
        self._amended_prices[position.symbol] = (new_stop, new_t1, new_t2)

        await self._submit_stop_order(position, position.shares_remaining, new_stop)

        if new_t1 > 0 and position.t1_shares > 0:
            await self._submit_t1_order(position, position.t1_shares, new_t1)

        t2_shares = position.shares_remaining - position.t1_shares
        if new_t2 > 0 and t2_shares > 0:
            await self._submit_t2_order(position, t2_shares, new_t2)

        logger.info(
            "Bracket amended for %s: fill slippage %+.2f, new stop=%.2f, new T1=%.2f",
            position.symbol,
            delta,
            new_stop,
            new_t1,
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

        # --- Trail activation after T1 fill (Sprint 28.5) ---
        if (
            position.exit_config is not None
            and position.exit_config.trailing_stop.enabled
            and position.exit_config.trailing_stop.activation == "after_t1"
        ):
            position.trail_active = True
            trail_cfg = position.exit_config.trailing_stop
            initial_trail = compute_trailing_stop(
                position.high_watermark, position.atr_value,
                trail_type=trail_cfg.type, atr_multiplier=trail_cfg.atr_multiplier,
                trail_percent=trail_cfg.percent, fixed_distance=trail_cfg.fixed_distance,
                min_trail_distance=trail_cfg.min_trail_distance, enabled=trail_cfg.enabled,
            )
            position.trail_stop_price = initial_trail if initial_trail is not None else 0.0

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
        # Find the position that was being flattened, matching by strategy_id
        position = next(
            (
                p
                for p in positions
                if p.shares_remaining > 0 and p.strategy_id == pending.strategy_id
            ),
            None,
        )
        # Fallback: if no strategy_id match, use first open position (for backwards compat)
        if position is None:
            position = next(
                (p for p in positions if p.shares_remaining > 0),
                None,
            )
            if position is not None:
                logger.warning(
                    "Flatten fill for %s strategy_id mismatch: expected %s, "
                    "falling back to position from %s",
                    pending.symbol,
                    pending.strategy_id,
                    position.strategy_id,
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
        elif position.trail_active:
            exit_reason = ExitReason.TRAILING_STOP

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

                # Drain startup flatten queue at market open (Sprint 29.5 R4)
                if self._startup_flatten_queue:
                    # Separate ET time for startup queue drain — distinct from
                    # eod_flatten's et_tz/now_et which are inside a conditional
                    # guard and may not be in scope.
                    et_tz2 = ZoneInfo("America/New_York")
                    if now.tzinfo is not None:
                        now_et2 = now.astimezone(et_tz2)
                    else:
                        now_et2 = now.replace(tzinfo=et_tz2)
                    if now_et2.time() >= time(9, 30):
                        await self._drain_startup_flatten_queue()

                # Check time stops on all positions
                for symbol, positions in list(self._managed_positions.items()):
                    for position in positions:
                        if position.is_fully_closed:
                            continue

                        # Skip flatten for abandoned symbols (Sprint 29.5 R2)
                        if symbol in self._flatten_abandoned:
                            continue

                        elapsed_seconds = (now - position.entry_time).total_seconds()

                        # Determine if flatten is already pending/abandoned
                        # for log suppression (Sprint 29.5 R5)
                        _suppress_log = symbol in self._flatten_pending

                        # Per-position time stop from signal (DEC-122)
                        if (
                            position.time_stop_seconds is not None
                            and elapsed_seconds >= position.time_stop_seconds
                        ):
                            if _suppress_log:
                                self._throttled.warn_throttled(
                                    f"time_stop:{symbol}",
                                    f"Time stop for {symbol}: open "
                                    f"{elapsed_seconds:.0f} sec "
                                    f"(limit={position.time_stop_seconds} sec"
                                    f", flatten pending)",
                                    interval_seconds=60.0,
                                )
                            else:
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
                            if _suppress_log:
                                self._throttled.warn_throttled(
                                    f"time_stop:{symbol}",
                                    f"Time stop for {symbol}: open "
                                    f"{elapsed_minutes:.1f} min "
                                    f"(limit="
                                    f"{self._config.max_position_duration_minutes}"
                                    f" min, flatten pending)",
                                    interval_seconds=60.0,
                                )
                            else:
                                logger.info(
                                    "Time stop for %s: open %.1f min (limit=%d min)",
                                    symbol,
                                    elapsed_minutes,
                                    self._config.max_position_duration_minutes,
                                )
                            await self._flatten_position(position, reason="time_stop")
                            continue

                        # --- Escalation check (Sprint 28.5, AMD-3/6/8) ---
                        if (
                            position.exit_config is not None
                            and position.exit_config.escalation.enabled
                        ):
                            phases = [
                                (p.elapsed_pct, p.stop_to.value)
                                for p in position.exit_config.escalation.phases
                            ]
                            esc_stop = compute_escalation_stop(
                                position.entry_price,
                                position.high_watermark,
                                elapsed_seconds,
                                position.time_stop_seconds,
                                phases=phases,
                                enabled=True,
                            )
                            if esc_stop is not None:
                                effective = compute_effective_stop(
                                    position.stop_price,
                                    position.trail_stop_price or None,
                                    esc_stop,
                                )
                                if effective > position.stop_price:
                                    # AMD-8: skip if flatten already pending
                                    if symbol in self._flatten_pending:
                                        continue
                                    # AMD-6: does NOT count against stop_cancel_retry_max
                                    await self._escalation_update_stop(
                                        position, effective
                                    )

                # --- Flatten-pending timeout (Sprint 28.75, R2) ---
                await self._check_flatten_pending_timeouts()

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in fallback poll loop")

    # ---------------------------------------------------------------------------
    # EOD Flatten and Emergency Flatten
    # ---------------------------------------------------------------------------

    async def eod_flatten(self) -> None:
        """Close all positions at market. Scheduled at eod_flatten_time.

        1. Clear abandoned set (EOD gets one final attempt for everything)
        2. Cancel all open orders (stops, targets)
        3. Close all remaining positions at market
        4. Flatten broker-only positions not tracked by ARGUS
        5. If auto_shutdown_after_eod is enabled, request system shutdown
        """
        logger.info("EOD flatten triggered — closing all positions")
        self._flattened_today = True

        # Clear abandoned set — EOD is the last resort (Sprint 29.5 R2)
        if self._flatten_abandoned:
            logger.info(
                "EOD clearing %d abandoned flatten symbols: %s",
                len(self._flatten_abandoned),
                sorted(self._flatten_abandoned),
            )
            self._flatten_abandoned.clear()
            self._flatten_cycle_count.clear()

        for _symbol, positions in list(self._managed_positions.items()):
            for position in positions:
                if not position.is_fully_closed:
                    await self._flatten_position(position, reason="eod_flatten")

        # Pass 2: Flatten broker-only positions not tracked by ARGUS (Sprint 29.5 R3)
        try:
            broker_positions = await self._broker.get_positions()
            managed_symbols = set(self._managed_positions.keys())
            for pos in broker_positions:
                symbol = getattr(pos, "symbol", str(pos))
                qty = int(getattr(pos, "qty", 0))
                if symbol not in managed_symbols and qty > 0:
                    logger.warning(
                        "EOD flatten: closing untracked broker position "
                        "%s (%d shares)",
                        symbol,
                        qty,
                    )
                    await self._flatten_unknown_position(
                        symbol, qty, force_execute=True,
                    )
        except Exception as e:
            logger.error("EOD flatten: broker position query failed: %s", e)

        # Request auto-shutdown if enabled
        if self._config.auto_shutdown_after_eod:
            delay = self._config.auto_shutdown_delay_seconds
            logger.info(
                "EOD flatten complete. Auto-shutdown in %ds...",
                delay,
            )
            await self._event_bus.publish(
                ShutdownRequestedEvent(
                    reason="eod_flatten_complete",
                    delay_seconds=delay,
                )
            )

    async def emergency_flatten(self) -> None:
        """Close everything immediately. Used by circuit breakers.

        Same as eod_flatten but callable at any time.
        """
        logger.warning("EMERGENCY FLATTEN — closing all positions immediately")
        await self.eod_flatten()

    async def close_position(self, symbol: str, reason: str = "api_close") -> bool:
        """Close a specific position by symbol.

        Cancels all child orders (stop, T1, T2) and submits a market sell
        for remaining shares. Routes through _flatten_position() which handles
        the full teardown lifecycle.

        Args:
            symbol: The symbol to close.
            reason: The exit reason string for logging.

        Returns:
            True if position was found and close initiated, False if not found.
        """
        positions = self._managed_positions.get(symbol)
        if not positions:
            return False
        for position in list(positions):
            await self._flatten_position(position, reason)
        return True

    async def reconstruct_from_broker(self) -> None:
        """Reconstruct managed positions from broker state.

        Called at startup to recover any open positions that existed
        before a restart.

        1. Query broker for all open positions.
        2. For each position, check if it has associated broker orders.
           - Positions with orders: reconstruct as ManagedPosition.
           - Positions without orders (zombies): flatten (if configured) or warn.
        3. Query broker for all open orders (for known positions).
        4. For each known position, create a ManagedPosition with:
           - Entry price from broker position data.
           - Stop price from any matching stop order.
           - T1/T2 inferred from stop orders and limit orders.

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
        except Exception as e:
            logger.warning(
                "IBKR portfolio query failed at startup — skipping zombie cleanup: %s",
                e,
            )
            return

        if not positions:
            logger.info("Order Manager reconstruction: No open positions at broker.")
            return

        try:
            orders = await self._broker.get_open_orders()
        except Exception as e:
            logger.warning("Failed to query open orders during reconstruction: %s", e)
            orders = []

        logger.info(
            "Reconstructing from %d positions and %d open orders at broker",
            len(positions),
            len(orders),
        )

        # Build order lookup by symbol
        orders_by_symbol: dict[str, list[object]] = {}
        for order in orders:
            symbol = getattr(order, "symbol", "")
            if symbol:
                if symbol not in orders_by_symbol:
                    orders_by_symbol[symbol] = []
                orders_by_symbol[symbol].append(order)

        # Classify positions: "managed" (has bracket orders) vs "zombie" (no orders).
        # ARGUS always places bracket orders (stop + targets) for managed positions.
        # A position WITH associated orders was being actively managed before restart.
        # A position with NO orders is an orphan/zombie from a prior session.
        # Also check _managed_positions in case upstream phases pre-populated state.
        managed_count = 0
        zombie_count = 0
        for pos in positions:
            symbol = getattr(pos, "symbol", str(pos))
            qty = int(getattr(pos, "qty", 0))

            has_orders = bool(orders_by_symbol.get(symbol, []))
            already_known = symbol in self._managed_positions

            if has_orders or already_known:
                # Managed position — reconstruct it
                self._reconstruct_known_position(pos, orders_by_symbol)
                managed_count += 1
            elif self._startup_config.flatten_unknown_positions:
                # Zero-qty guard: skip flatten for ghost positions with no shares
                if abs(qty) <= 0:
                    logger.debug(
                        "Skipping flatten for zero-quantity position %s", symbol
                    )
                    zombie_count += 1
                    continue
                # Zombie position with no orders — flatten
                await self._flatten_unknown_position(symbol, qty)
                zombie_count += 1
            else:
                # Zombie but flatten disabled — warn and create RECO entry
                logger.warning(
                    "Unknown IBKR position at startup: %s (%d shares) "
                    "— manual cleanup required",
                    symbol,
                    qty,
                )
                self._create_reco_position(symbol, qty, pos)
                zombie_count += 1

        logger.info(
            "Order Manager reconstruction complete: %d positions recovered, "
            "%d zombies handled",
            managed_count,
            zombie_count,
        )

    async def _flatten_unknown_position(
        self, symbol: str, qty: int, *, force_execute: bool = False,
    ) -> None:
        """Submit a market SELL order to close an unknown broker position.

        If the market is not open (before 9:30 ET or after 16:00 ET),
        queues the flatten for execution at market open instead of
        submitting immediately (Sprint 29.5 R4).

        Args:
            symbol: The ticker symbol.
            qty: Number of shares to sell.
            force_execute: If True, skip the market-hours gate and execute
                immediately. Used by EOD Pass 2 where we must close
                positions regardless of clock time.
        """
        # Check if market is open (Sprint 29.5 R4)
        et_tz = ZoneInfo("America/New_York")
        now = self._clock.now()
        if now.tzinfo is not None:
            now_et = now.astimezone(et_tz)
        else:
            now_et = now.replace(tzinfo=et_tz)
        market_open = time(9, 30)
        market_close = time(16, 0)
        if not force_execute and not (market_open <= now_et.time() < market_close):
            self._startup_flatten_queue.append((symbol, abs(qty)))
            logger.info(
                "Queued startup flatten for %s (%d shares) "
                "— will execute at market open",
                symbol,
                abs(qty),
            )
            return

        try:
            sell_order = Order(
                strategy_id="startup_cleanup",
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.MARKET,
                quantity=abs(qty),
            )
            await self._broker.place_order(sell_order)
            logger.info(
                "Startup cleanup: flattened unknown position %s (%d shares)",
                symbol,
                abs(qty),
            )
        except Exception as e:
            logger.error(
                "Startup cleanup: failed to flatten %s (%d shares): %s",
                symbol,
                abs(qty),
                e,
            )

    async def _drain_startup_flatten_queue(self) -> None:
        """Execute queued startup zombie flattens (Sprint 29.5 R4).

        Called from the poll loop when market opens. Drains the entire
        queue and submits market sell orders for each entry.
        """
        if not self._startup_flatten_queue:
            return

        queue = list(self._startup_flatten_queue)
        self._startup_flatten_queue.clear()

        logger.info(
            "Draining startup flatten queue: %d positions", len(queue)
        )
        for symbol, qty in queue:
            try:
                sell_order = Order(
                    strategy_id="startup_cleanup",
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=TradingOrderType.MARKET,
                    quantity=abs(qty),
                )
                await self._broker.place_order(sell_order)
                logger.info(
                    "Startup queue: flattened %s (%d shares)", symbol, abs(qty)
                )
            except Exception as e:
                logger.error(
                    "Startup queue: failed to flatten %s (%d shares): %s",
                    symbol,
                    abs(qty),
                    e,
                )

    def _create_reco_position(
        self, symbol: str, qty: int, pos: object
    ) -> None:
        """Create a reconstructed ManagedPosition for UI visibility.

        Used when flatten_unknown_positions is disabled — preserves the
        existing RECO behavior so operators can see the position.

        Args:
            symbol: The ticker symbol.
            qty: Number of shares.
            pos: The broker position object.
        """
        avg_entry = float(getattr(pos, "avg_entry_price", 0.0))
        managed = ManagedPosition(
            symbol=symbol,
            strategy_id="reconstructed",
            entry_price=avg_entry,
            entry_time=self._clock.now(),
            shares_total=abs(qty),
            shares_remaining=abs(qty),
            stop_price=0.0,
            original_stop_price=0.0,
            stop_order_id=None,
            t1_price=0.0,
            t1_order_id=None,
            t1_shares=0,
            t1_filled=True,
            t2_price=0.0,
            high_watermark=avg_entry,
        )
        if symbol not in self._managed_positions:
            self._managed_positions[symbol] = []
        self._managed_positions[symbol].append(managed)

    def _reconstruct_known_position(
        self,
        pos: object,
        orders_by_symbol: dict[str, list[object]],
    ) -> None:
        """Reconstruct a single known position from broker state.

        Args:
            pos: The broker position object.
            orders_by_symbol: Lookup of open orders keyed by symbol.
        """
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

    async def _check_flatten_pending_timeouts(self) -> None:
        """Cancel and resubmit stale flatten orders (Sprint 28.75, R2).

        Iterates over _flatten_pending entries. If any entry has exceeded
        flatten_pending_timeout_seconds, cancel the stale order and resubmit
        a fresh market sell. Stops retrying after max_flatten_retries.
        """
        timeout = self._config.flatten_pending_timeout_seconds
        max_retries = self._config.max_flatten_retries
        now = _time.monotonic()

        for symbol, (order_id, placed_at, retry_count) in list(
            self._flatten_pending.items()
        ):
            elapsed = now - placed_at
            if elapsed < timeout:
                continue

            # Max retries exhausted — increment cycle count, possibly abandon
            if retry_count >= max_retries:
                self._flatten_pending.pop(symbol, None)
                cycle = self._flatten_cycle_count.get(symbol, 0) + 1
                self._flatten_cycle_count[symbol] = cycle
                max_cycles = self._config.max_flatten_cycles
                if cycle >= max_cycles:
                    self._flatten_abandoned.add(symbol)
                    total_attempts = cycle * max_retries
                    logger.error(
                        "Flatten for %s abandoned after %d cycles "
                        "(%d total attempts) — requires manual intervention "
                        "or EOD flatten",
                        symbol,
                        cycle,
                        total_attempts,
                    )
                else:
                    logger.error(
                        "Flatten for %s exhausted %d retries (cycle %d/%d) "
                        "— will retry on next flatten attempt",
                        symbol,
                        max_retries,
                        cycle,
                        max_cycles,
                    )
                continue

            logger.warning(
                "Flatten order for %s timed out after %ds. Resubmitting. "
                "(retry %d/%d, order %s)",
                symbol,
                int(elapsed),
                retry_count + 1,
                max_retries,
                order_id,
            )

            # Cancel stale order
            try:
                await self._broker.cancel_order(order_id)
            except Exception:
                logger.debug("Could not cancel stale flatten order %s", order_id)
            self._pending_orders.pop(order_id, None)

            # Find the position to get shares_remaining and strategy_id
            positions = self._managed_positions.get(symbol, [])
            position = next(
                (p for p in positions if not p.is_fully_closed), None
            )
            if position is None or position.shares_remaining <= 0:
                self._flatten_pending.pop(symbol, None)
                continue

            # Re-query broker qty if error 404 was flagged (Sprint 29.5 R1)
            sell_qty = position.shares_remaining
            broker_404_symbols = getattr(self._broker, "error_404_symbols", None)
            if broker_404_symbols is not None and symbol in broker_404_symbols:
                broker_404_symbols.discard(symbol)
                try:
                    broker_positions = await self._broker.get_positions()
                    broker_qty = 0
                    for bp in broker_positions:
                        if getattr(bp, "symbol", "") == symbol:
                            broker_qty = abs(int(getattr(bp, "qty", 0)))
                            break
                    if broker_qty == 0:
                        logger.info(
                            "IBKR position already closed for %s — "
                            "removing from flatten pending",
                            symbol,
                        )
                        self._flatten_pending.pop(symbol, None)
                        continue
                    if broker_qty != position.shares_remaining:
                        logger.warning(
                            "Flatten qty mismatch for %s: ARGUS=%d, IBKR=%d "
                            "— using IBKR qty",
                            symbol,
                            position.shares_remaining,
                            broker_qty,
                        )
                        sell_qty = broker_qty
                except Exception:
                    logger.warning(
                        "Broker re-query failed for %s — using ARGUS qty %d",
                        symbol,
                        position.shares_remaining,
                    )

            # Resubmit fresh market sell
            try:
                order = Order(
                    strategy_id=position.strategy_id,
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=TradingOrderType.MARKET,
                    quantity=sell_qty,
                )
                result = await self._broker.place_order(order)
                new_pending = PendingManagedOrder(
                    order_id=result.order_id,
                    symbol=symbol,
                    strategy_id=position.strategy_id,
                    order_type="flatten",
                    shares=sell_qty,
                )
                self._pending_orders[result.order_id] = new_pending
                self._flatten_pending[symbol] = (
                    result.order_id, _time.monotonic(), retry_count + 1,
                )

                # Handle immediate fill (SimulatedBroker)
                if result.status == OrderStatus.FILLED:
                    fill_event = OrderFilledEvent(
                        order_id=result.order_id,
                        fill_price=result.filled_avg_price,
                        fill_quantity=result.filled_quantity,
                    )
                    await self.on_fill(fill_event)
            except Exception:
                logger.exception(
                    "CRITICAL: Flatten resubmit failed for %s (%d shares unprotected)",
                    symbol,
                    sell_qty,
                )

    async def _trail_flatten(
        self, position: ManagedPosition, current_price: float
    ) -> None:
        """Flatten a position due to trail stop hit (AMD-2, AMD-4, AMD-8).

        Order of operations is safety-critical:
        1. AMD-8: Check _flatten_pending — complete no-op if already pending
        2. AMD-4: Check shares_remaining > 0 — no-op if zero
        3. Submit market sell FIRST (AMD-2: sell before cancel)
        4. Cancel broker safety stop SECOND

        If broker safety stop fills before cancel, DEC-374 dedup handles it.

        Args:
            position: The position to flatten.
            current_price: Current market price (for logging).
        """
        symbol = position.symbol

        # Step 1 (AMD-8): Complete no-op if flatten already pending
        if symbol in self._flatten_pending:
            return

        # Step 2 (AMD-4): No-op if no shares remain
        if position.shares_remaining <= 0:
            position.trail_active = False
            position.trail_stop_price = 0.0
            return

        logger.info(
            "Trail stop triggered for %s: trail=%.2f, price=%.2f",
            symbol,
            position.trail_stop_price,
            current_price,
        )

        # Step 3: Submit market sell FIRST (AMD-2)
        try:
            order = Order(
                strategy_id=position.strategy_id,
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.MARKET,
                quantity=position.shares_remaining,
            )
            result = await self._broker.place_order(order)
            flatten_order_id = result.order_id

            pending = PendingManagedOrder(
                order_id=flatten_order_id,
                symbol=symbol,
                strategy_id=position.strategy_id,
                order_type="flatten",
                shares=position.shares_remaining,
            )
            self._pending_orders[flatten_order_id] = pending
            self._flatten_pending[symbol] = (flatten_order_id, _time.monotonic(), 0)

            # Handle immediate fill (SimulatedBroker)
            if result.status == OrderStatus.FILLED:
                fill_event = OrderFilledEvent(
                    order_id=flatten_order_id,
                    fill_price=result.filled_avg_price,
                    fill_quantity=result.filled_quantity,
                )
                await self.on_fill(fill_event)
        except Exception:
            logger.exception(
                "CRITICAL: Trail flatten sell failed for %s (%d shares unprotected)",
                symbol,
                position.shares_remaining,
            )
            return

        # Step 4: Cancel broker safety stop SECOND (AMD-2)
        if position.stop_order_id:
            try:
                await self._broker.cancel_order(position.stop_order_id)
            except Exception:
                logger.debug("Could not cancel safety stop %s", position.stop_order_id)
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

        # Cancel T2 if still open
        if position.t2_order_id:
            try:
                await self._broker.cancel_order(position.t2_order_id)
            except Exception:
                logger.debug("Could not cancel T2 %s", position.t2_order_id)
            self._pending_orders.pop(position.t2_order_id, None)
            position.t2_order_id = None

    async def _escalation_update_stop(
        self, position: ManagedPosition, new_stop_price: float
    ) -> None:
        """Update broker stop to escalation price (AMD-3, AMD-6).

        Single-attempt submission — NOT through retry loop. If submission
        fails, immediately flattens position for safety.

        Does NOT increment _stop_retry_count (AMD-6).

        Args:
            position: The position to update.
            new_stop_price: The new escalation stop price.
        """
        symbol = position.symbol

        # AMD-8: Defense-in-depth — skip if flatten already pending
        if symbol in self._flatten_pending:
            return

        # Cancel current broker stop
        if position.stop_order_id:
            try:
                await self._broker.cancel_order(position.stop_order_id)
            except Exception:
                logger.debug(
                    "Could not cancel stop %s for escalation update", position.stop_order_id
                )
            self._pending_orders.pop(position.stop_order_id, None)
            position.stop_order_id = None

        # Submit new stop at escalation price (single attempt — AMD-3)
        try:
            order = Order(
                strategy_id=position.strategy_id,
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.STOP,
                quantity=position.shares_remaining,
                stop_price=new_stop_price,
            )
            result = await self._broker.place_order(order)
            position.stop_order_id = result.order_id

            self._pending_orders[result.order_id] = PendingManagedOrder(
                order_id=result.order_id,
                symbol=symbol,
                strategy_id=position.strategy_id,
                order_type="stop",
                shares=position.shares_remaining,
            )

            position.stop_price = new_stop_price
            logger.info(
                "Escalation stop updated for %s: new_stop=%.2f",
                symbol,
                new_stop_price,
            )
        except Exception:
            logger.error(
                "Escalation stop submission failed for %s (attempted=%.2f) "
                "— triggering flatten",
                symbol,
                new_stop_price,
                exc_info=True,
            )
            await self._flatten_position(position, reason="escalation_failure")

    async def _flatten_position(self, position: ManagedPosition, reason: str) -> None:
        """Cancel all open orders for this position and submit market sell.

        Includes a flatten-pending guard to prevent duplicate flatten orders
        (e.g., time-stop loop submitting a new flatten every 5 seconds).
        """
        # Clear P&L throttle so the close event isn't suppressed (Sprint 27.65 S4)
        self._pnl_last_published.pop(position.symbol, None)

        # Skip if flatten has been abandoned for this symbol (Sprint 29.5 R2)
        if position.symbol in self._flatten_abandoned:
            logger.debug(
                "Flatten skipped for %s — abandoned (awaiting EOD)",
                position.symbol,
            )
            return

        # Flatten-pending guard: skip if a flatten order is already pending
        existing_entry = self._flatten_pending.get(position.symbol)
        if existing_entry is not None:
            self._throttled.warn_throttled(
                f"flatten_pending:{position.symbol}",
                f"Flatten already pending for {position.symbol} "
                f"(order {existing_entry[0]})",
                interval_seconds=60.0,
            )
            return

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

                # Track flatten as pending (prevents duplicates)
                self._flatten_pending[position.symbol] = (
                    result.order_id, _time.monotonic(), 0,
                )

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
        # Clear flatten-pending guard for this symbol
        self._flatten_pending.pop(position.symbol, None)

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
                symbol=position.symbol,
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

                is_reconciliation = exit_reason == ExitReason.RECONCILIATION

                if is_reconciliation:
                    # Defensive getattr — reconciliation positions may have
                    # incomplete ManagedPosition state (e.g. RECO entries
                    # created for orphaned positions with no bracket data).
                    stop = getattr(position, "original_stop_price", 0.0) or 0.0
                    t1 = getattr(position, "t1_price", 0.0) or 0.0
                    t2 = getattr(position, "t2_price", 0.0) or 0.0
                else:
                    # Normal close — fields guaranteed on ManagedPosition
                    stop = position.original_stop_price or 0.0
                    t1 = position.t1_price or 0.0
                    t2 = position.t2_price or 0.0

                trade = Trade(
                    strategy_id=position.strategy_id,
                    symbol=position.symbol,
                    side=OrderSide.BUY,
                    entry_price=position.entry_price,
                    entry_time=position.entry_time,
                    exit_price=weighted_exit_price,
                    exit_time=self._clock.now(),
                    shares=position.shares_total,
                    stop_price=stop if not is_reconciliation else (stop or position.entry_price),
                    target_prices=[t1, t2],
                    exit_reason=exit_reason,
                    gross_pnl=position.realized_pnl if not is_reconciliation else 0.0,
                    quality_grade=position.quality_grade,
                    quality_score=position.quality_score,
                    # mfe_price/mae_price are initialized to entry_price (non-zero) for real trades.
                    # The 0.0 check catches reconciliation/synthetic positions that were never
                    # through _handle_entry_fill and should store NULL instead of misleading 0.0.
                    mfe_price=position.mfe_price if position.mfe_price != 0.0 else None,
                    mae_price=position.mae_price if position.mae_price != 0.0 else None,
                    # R-multiples: 0.0 means "no excursion" (valid data), distinct from NULL (legacy/no data).
                    # Only reconciliation positions have mfe_price=0.0; their R-multiples are also 0.0,
                    # but the price-level NULL (above) already signals "no real data" for those trades.
                    mfe_r=position.mfe_r if position.mfe_price != 0.0 else None,
                    mae_r=position.mae_r if position.mae_price != 0.0 else None,
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
            # Clean up reconciliation tracking when no positions remain for symbol
            self._broker_confirmed.pop(position.symbol, None)
            self._reconciliation_miss_count.pop(position.symbol, None)
            # Clean up stop retry, amended prices, and fill dedup state (Sprint 27.95 S2)
            self._stop_retry_count.pop(position.symbol, None)
            self._amended_prices.pop(position.symbol, None)
            # Clean fill dedup entries via reverse index
            for oid in self._fill_order_ids_by_symbol.pop(position.symbol, set()):
                self._last_fill_state.pop(oid, None)

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
        self._flatten_pending.clear()
        self._broker_confirmed.clear()
        self._reconciliation_miss_count.clear()
        self._last_reconciliation = None
        self._stop_retry_count.clear()
        self._amended_prices.clear()
        self._last_fill_state.clear()
        self._fill_order_ids_by_symbol.clear()

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

    def get_pending_entry_exposure(self, symbol: str) -> float:
        """Return total notional exposure from pending (unfilled) entry orders for a symbol.

        Used by Risk Manager to include pending entries in concentration checks.
        Prevents race conditions when multiple signals approve before fills arrive.

        Args:
            symbol: The symbol to query.

        Returns:
            Total notional exposure (shares × entry_price) from pending entry orders.
        """
        total_exposure = 0.0
        for pending in self._pending_orders.values():
            if pending.order_type == "entry" and pending.symbol == symbol:
                # pending.signal is OrderApprovedEvent, pending.signal.signal is SignalEvent
                if pending.signal is None:
                    logger.debug(
                        "Pending entry order %s has no signal, skipping exposure calc",
                        pending.order_id,
                    )
                    continue
                signal = pending.signal.signal
                if signal is None:
                    logger.debug(
                        "Pending entry order %s has no inner signal, skipping exposure calc",
                        pending.order_id,
                    )
                    continue
                # Use the potentially modified share count from the approved event
                share_count = pending.shares
                entry_price = signal.entry_price
                total_exposure += share_count * entry_price
        return total_exposure

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

    async def reconcile_positions(
        self, broker_positions: dict[str, float]
    ) -> list[dict[str, object]]:
        """Compare internal positions against broker-reported positions.

        Detects discrepancies and logs warnings. Broker-confirmed positions
        are never auto-closed (snapshot may be stale). Unconfirmed positions
        are cleaned up only after consecutive_miss_threshold consecutive
        snapshot misses when auto_cleanup_unconfirmed is True.

        Args:
            broker_positions: Dict of {symbol: quantity} from broker.

        Returns:
            List of discrepancy dicts with symbol, internal_qty, broker_qty.
        """
        discrepancies: list[dict[str, object]] = []
        recon = self._reconciliation_config

        # Build internal position totals by symbol
        internal_positions: dict[str, int] = {}
        for symbol, positions in self._managed_positions.items():
            total_qty = sum(p.shares_remaining for p in positions if not p.is_fully_closed)
            if total_qty > 0:
                internal_positions[symbol] = total_qty

        # Reset miss counters for symbols found in broker snapshot
        for symbol in internal_positions:
            if int(broker_positions.get(symbol, 0)) > 0:
                self._reconciliation_miss_count[symbol] = 0

        # Check all symbols in either set
        all_symbols = set(internal_positions.keys()) | set(broker_positions.keys())
        for symbol in sorted(all_symbols):
            internal_qty = internal_positions.get(symbol, 0)
            broker_qty = int(broker_positions.get(symbol, 0))
            if internal_qty != broker_qty:
                logger.debug(
                    "Position mismatch detail: %s — ARGUS=%d, IBKR=%d",
                    symbol,
                    internal_qty,
                    broker_qty,
                )
                discrepancies.append({
                    "symbol": symbol,
                    "internal_qty": internal_qty,
                    "broker_qty": broker_qty,
                })

        # Consolidated summary at WARNING level
        if discrepancies:
            symbols = [str(d["symbol"]) for d in discrepancies]
            preview = ", ".join(symbols[:3])
            suffix = "..." if len(symbols) > 3 else ""
            logger.warning(
                "Position reconciliation: %d mismatch(es) — %s%s (ARGUS vs IBKR)",
                len(discrepancies),
                preview,
                suffix,
            )

        # Process orphan discrepancies (internal > 0, broker == 0)
        for d in discrepancies:
            if int(d["internal_qty"]) <= 0 or int(d["broker_qty"]) != 0:  # type: ignore[arg-type]
                continue

            sym = str(d["symbol"])
            confirmed = self._broker_confirmed.get(sym, False)

            if confirmed:
                # Broker-confirmed position — NEVER auto-close. Snapshot may be stale.
                self._throttled.warn_throttled(
                    f"recon_missing:{sym}",
                    f"IBKR portfolio snapshot missing confirmed position {sym} "
                    f"— snapshot may be stale",
                    interval_seconds=600.0,  # 10 minutes per symbol
                )
                self._reconciliation_miss_count[sym] = 0
                continue

            # Unconfirmed position — apply miss counter logic
            if recon.auto_cleanup_unconfirmed:
                miss_count = self._reconciliation_miss_count.get(sym, 0) + 1
                self._reconciliation_miss_count[sym] = miss_count

                if miss_count >= recon.consecutive_miss_threshold:
                    # Threshold reached — clean up
                    for pos in list(self._managed_positions.get(sym, [])):
                        if not pos.is_fully_closed:
                            pos.shares_remaining = 0
                            pos.realized_pnl = 0.0
                            logger.warning(
                                "Reconciliation cleanup: closed unconfirmed position %s "
                                "after %d consecutive misses (%d shares, strategy=%s)",
                                pos.symbol,
                                miss_count,
                                pos.shares_total,
                                pos.strategy_id,
                            )
                            await self._close_position(
                                pos,
                                exit_price=pos.entry_price,
                                exit_reason=ExitReason.RECONCILIATION,
                            )
                else:
                    logger.info(
                        "Unconfirmed position %s missing from IBKR snapshot "
                        "(miss %d/%d)",
                        sym,
                        miss_count,
                        recon.consecutive_miss_threshold,
                    )
            elif recon.auto_cleanup_orphans:
                # Legacy behavior: immediate cleanup for any orphan
                for pos in list(self._managed_positions.get(sym, [])):
                    if not pos.is_fully_closed:
                        pos.shares_remaining = 0
                        pos.realized_pnl = 0.0
                        logger.warning(
                            "Reconciliation cleanup: closed orphaned position %s "
                            "(%d shares, strategy=%s)",
                            pos.symbol,
                            pos.shares_total,
                            pos.strategy_id,
                        )
                        await self._close_position(
                            pos,
                            exit_price=pos.entry_price,
                            exit_reason=ExitReason.RECONCILIATION,
                        )
            else:
                # Warn-only mode
                logger.warning(
                    "Unconfirmed orphaned position %s — auto-cleanup disabled",
                    sym,
                )

        self._last_reconciliation = ReconciliationResult(
            timestamp=self._clock.now().isoformat(),
            status="synced" if not discrepancies else "mismatch",
            discrepancies=discrepancies,
        )
        return discrepancies

    @property
    def last_reconciliation(self) -> ReconciliationResult | None:
        """Return the latest reconciliation result."""
        return self._last_reconciliation
