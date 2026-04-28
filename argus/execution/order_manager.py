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
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import aiosqlite

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
    SignalRejectedEvent,
    SystemAlertEvent,
    TickEvent,
)
from argus.core.ids import generate_id
from argus.execution.broker import Broker, CancelPropagationTimeout
from argus.execution.ibkr_broker import _is_oca_already_filled_error
from argus.models.trading import Order, OrderSide, OrderStatus
from argus.utils.log_throttle import ThrottledLogger
from argus.models.trading import OrderType as TradingOrderType

if TYPE_CHECKING:
    from argus.core.clock import Clock

logger = logging.getLogger(__name__)


def _log_persist_task_exception(task: "asyncio.Task[None]", symbol: str) -> None:
    """Done-callback for fire-and-forget gate-state persistence tasks.

    Sprint 31.91 Session 2c.1: persistence of ``phantom_short_gated_symbols``
    is fire-and-forget so the reconciliation cycle is not blocked. We still
    surface failures via WARNING — DEC-345 fire-and-forget pattern requires
    the failure to be visible. A broken DB cannot silently swallow.
    """
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.warning(
            "Phantom-short gate persistence write failed for %s: %s",
            symbol,
            exc,
            exc_info=exc,
        )


# Sprint 31.91 Session 1b: OCA type for standalone-SELL threading on
# ManagedPosition-bound paths. Mirrors ``IBKRConfig.bracket_oca_type``
# (default 1, constrained ``[0, 1]``); matches the value Session 1a uses
# at ``IBKRBroker.place_bracket_order`` (line 764, ``oca_type =
# self._config.bracket_oca_type``). OrderManager does not have access to
# ``IBKRConfig`` (different config tree, and the do-not-modify list
# forbids extending the OrderManager constructor at the
# ``argus/main.py`` call site this session). A module constant is the
# surgical choice — if the operator ever flips
# ``IBKRConfig.bracket_oca_type`` to 0 (no OCA), this constant must be
# updated in lock-step. The ``RESTART-REQUIRED`` note in the IBKRConfig
# docstring already governs that flip; we add a paired pointer here.
_OCA_TYPE_BRACKET: int = 1


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

    # OCA grouping (Sprint 31.91 Session 1a, DEC-386 reserved). Set at
    # bracket-confirmation time to ``f"oca_{parent_ulid}"`` so subsequent
    # standalone-SELL paths (Session 1b) can thread the same group.
    # ``None`` for ``reconstruct_from_broker``-derived positions (no
    # parent ULID is recoverable from broker state).
    oca_group_id: str | None = None

    # Sprint 31.91 Session 1b: marker that an OCA-grouped SELL placement
    # raised IBKR Error 201 "OCA group is already filled" — meaning
    # another OCA member (typically the bracket stop) already filled and
    # the position is exiting via that member's fill callback. Used by
    # the four standalone-SELL paths (``_trail_flatten``,
    # ``_escalation_update_stop``, ``_submit_stop_order`` /
    # ``_resubmit_stop_with_retry``, ``_flatten_position``) to
    # short-circuit duplicate exits and DEF-158 retry, and to surface
    # the SAFE outcome in post-mortem analysis.
    redundant_exit_observed: bool = False

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


@dataclass(frozen=True)
class ReconciliationPosition:
    """Typed broker-position contract for reconciliation.

    Frozen to prevent mutation in transit between the ``main.py`` call
    site and ``OrderManager.reconcile_positions``.

    Sprint 31.91 Session 2a (DEC-385 reserved): replaces the side-stripped
    ``dict[str, float]`` contract that was the structural cause of DEF-204
    (phantom-short blindness). The broker reports the absolute position
    size in ``shares`` and the direction in ``side``; this dataclass
    preserves both end-to-end through the reconciliation path.
    """

    symbol: str
    side: OrderSide
    shares: int

    def __post_init__(self) -> None:
        # Defensive: shares must be positive (the broker reports the
        # absolute size; direction is in `side`). A zero or negative
        # shares value indicates a caller-side bug; fail closed so it
        # cannot silently drift through the reconciliation pipeline.
        if self.shares <= 0:
            raise ValueError(
                f"ReconciliationPosition.shares must be positive; "
                f"got {self.shares} for {self.symbol}"
            )
        if self.side is None:
            raise ValueError(
                f"ReconciliationPosition.side must be set; got None for {self.symbol}"
            )


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
        reconciliation_config: ReconciliationConfig | None = None,
        startup_config: StartupConfig | None = None,
        exit_config: ExitManagementConfig | None = None,
        strategy_exit_overrides: dict[str, dict[str, Any]] | None = None,
        operations_db_path: str | None = None,
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
            reconciliation_config: Typed reconciliation settings (Sprint 27.95).
            startup_config: Startup behavior settings (Sprint 27.95 S4).
            exit_config: Exit management config (trailing stops, escalation). Sprint 28.5.
            strategy_exit_overrides: Per-strategy exit_management YAML overrides
                keyed by strategy_id. Deep-merged with global exit_config (AMD-1).
            operations_db_path: Path to ``data/operations.db`` (Sprint 31.91
                Session 2c.1). Used to persist + rehydrate the per-symbol
                phantom-short entry gate. Defaults to ``"data/operations.db"``
                — main.py may override based on ``config.system.data_dir``.
        """
        self._event_bus = event_bus
        self._broker = broker
        self._clock = clock
        self._config = config
        self._trade_logger = trade_logger
        self._db_manager = db_manager
        self._broker_source = broker_source
        self._reconciliation_config = reconciliation_config or ReconciliationConfig()
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

        # Strategy fingerprint registry: strategy_id → config_fingerprint (Sprint 32 scope gap fix)
        # Populated via register_strategy_fingerprint() after strategies are created.
        # Non-pattern strategies are absent from the registry; their trades get None.
        self._fingerprint_registry: dict[str, str | None] = {}

        # EOD flatten fill-verification events: symbol → asyncio.Event (Sprint 32.9)
        # Set in _close_position and on_cancel when a flatten order resolves.
        self._eod_flatten_events: dict[str, asyncio.Event] = {}

        # Margin circuit breaker (Sprint 32.9 S2)
        # Counts IBKR Error 201 "insufficient margin" rejections this session.
        self._margin_rejection_count: int = 0
        # When True, new entry orders are blocked until positions clear.
        self._margin_circuit_open: bool = False

        # Safety tracking attributes for debrief export (Sprint 31A S1)
        self.margin_circuit_breaker_open_time: datetime | None = None
        self.margin_circuit_breaker_reset_time: datetime | None = None
        self.margin_entries_blocked_count: int = 0
        self.eod_flatten_pass1_count: int = 0
        self.eod_flatten_pass2_count: int = 0
        self.signal_cutoff_skipped_count: int = 0

        # Sprint 31.91 Session 2b.1 (D5): per-symbol consecutive-cycle counter
        # for broker-orphan LONG positions. Used for cycle-3+ stranded_broker_long
        # alert escalation with M2 exponential backoff. NOT persisted in 2b.1
        # (Session 2c.1 adds SQLite persistence for the gate state, not this
        # counter — counter is session-scoped per M2 disposition). Cleared on
        # session reset (``reset_daily_state``) and per-symbol on broker-zero
        # observation in ``reconcile_positions``.
        self._broker_orphan_long_cycles: dict[str, int] = {}

        # Sprint 31.91 Session 2b.1 (D5): tracks the last alert-cycle count for
        # exponential-backoff re-alerting (3 → 6 → 12 → 24 → 48, then every 60
        # cycles which is roughly hourly if reconciliation runs once per minute).
        # Cleared alongside ``_broker_orphan_long_cycles``.
        self._broker_orphan_last_alerted_cycle: dict[str, int] = {}

        # Sprint 31.91 Session 2c.1: per-symbol entry gate. Symbols in this
        # set are blocked at the OrderApprovedEvent handler. Engagement:
        # Session 2b.1's ``_handle_broker_orphan_short`` adds the symbol;
        # auto-clear (5-cycle) lands in Session 2c.2; operator override
        # lands in Session 2d. SQLite-persisted to ``data/operations.db``
        # (M5 rehydration ordering).
        self._phantom_short_gated_symbols: set[str] = set()

        # Sprint 31.91 Session 2c.2: per-symbol consecutive-cycle counter for
        # auto-clearing the phantom_short gate. Increments on each reconciliation
        # cycle observing broker-non-short for a gated symbol; reaches the
        # configured threshold (default 5 per M4) -> gate clears. Counter
        # resets on re-detection of phantom short (preventing stuttering).
        #
        # M4 cost-of-error asymmetry: 5 cycles (~5 min) > 3 cycles (~3 min) because
        # false-clear (gate releases while short persists) is more dangerous than
        # false-hold (gate stays engaged a few extra cycles).
        self._phantom_short_clear_cycles: dict[str, int] = {}

        # Sprint 31.91 Session 2c.1: path to the operations.db file that
        # backs the phantom-short entry-gate state. Default is
        # ``data/operations.db``; main.py may override based on
        # ``config.system.data_dir``. The file/parent dir is created
        # lazily on first write (aiosqlite.connect creates the file).
        self._operations_db_path: str = operations_db_path or "data/operations.db"

        # Sprint 31.91 Session 2c.1: tracks fire-and-forget gate-state
        # persistence tasks so they can be awaited (tests, future
        # graceful shutdown) and so the GC doesn't reap a still-pending
        # task before its done-callback runs. Task removes itself from
        # this set in its done-callback.
        self._pending_gate_persist_tasks: set[asyncio.Task[None]] = set()

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

    def register_strategy_fingerprint(
        self, strategy_id: str, fingerprint: str | None
    ) -> None:
        """Register a config fingerprint for a strategy.

        Called once per PatternBasedStrategy after startup. Non-pattern
        strategies need not be registered — absent entries resolve to None.

        Args:
            strategy_id: The strategy's identifier string.
            fingerprint: 16-char hex fingerprint from compute_parameter_fingerprint(),
                or None if the strategy has no fingerprint.
        """
        self._fingerprint_registry[strategy_id] = fingerprint

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

        # Sprint 31.91 Session 2c.1: per-symbol phantom-short entry gate.
        # If this symbol was previously detected as a broker-orphan SHORT
        # (DEF-204 signature) and the entry gate is engaged, reject the
        # OrderApprovedEvent before any broker submission. This is the
        # first check — mirrors DEC-367 margin-circuit ordering. Operator
        # must clear via Session 2d operator override or wait for
        # Session 2c.2's 5-cycle auto-clear.
        if signal.symbol in self._phantom_short_gated_symbols:
            logger.critical(
                "OrderApprovedEvent REJECTED for %s: symbol is in "
                "phantom_short_gated_symbols. Operator must clear via "
                "POST /api/v1/reconciliation/phantom-short-gate/clear "
                "(Session 2d) or wait for 5-cycle auto-clear (Session 2c.2).",
                signal.symbol,
            )
            await self._event_bus.publish(
                SignalRejectedEvent(
                    signal=signal,
                    rejection_stage="risk_manager",
                    rejection_reason="phantom_short_gate",
                    metadata={
                        "reason_detail": (
                            f"Symbol {signal.symbol} is gated due to "
                            f"phantom-short detection (DEF-204 signature). "
                            f"Operator action required to clear."
                        ),
                        "gate": "phantom_short_gate",
                        "symbol": signal.symbol,
                    },
                )
            )
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

        # Margin circuit breaker gate: block new entries when margin is exhausted (Sprint 32.9 S2)
        if self._margin_circuit_open:
            self.margin_entries_blocked_count += 1
            logger.info(
                "Entry blocked by margin circuit breaker: %s for %s",
                signal.symbol,
                signal.strategy_id,
            )
            await self._event_bus.publish(
                SignalRejectedEvent(
                    signal=signal,
                    rejection_stage="risk_manager",
                    rejection_reason=(
                        f"Margin circuit breaker open — "
                        f"{self._margin_rejection_count} rejections this session"
                    ),
                )
            )
            return

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
                # Signal EOD flatten verification event if waiting (Sprint 32.9)
                eod_event = self._eod_flatten_events.get(pending.symbol)
                if eod_event is not None:
                    eod_event.set()

        # Margin circuit breaker: detect IBKR Error 201 margin rejections (Sprint 32.9 S2)
        # Only track entry orders — bracket legs and flattens don't consume buying power.
        if pending.order_type == "entry":
            reason_text = (event.reason or "").lower()
            is_margin_rejection = "available funds" in reason_text or "insufficient" in reason_text
            if is_margin_rejection:
                self._margin_rejection_count += 1
                if not self._margin_circuit_open and (
                    self._margin_rejection_count >= self._config.margin_rejection_threshold
                ):
                    self._margin_circuit_open = True
                    self.margin_circuit_breaker_open_time = datetime.now(UTC)
                    logger.warning(
                        "Margin circuit breaker OPEN — %d margin rejections this session. "
                        "New entries blocked until positions clear.",
                        self._margin_rejection_count,
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
        entry_fill_time = self._clock.now()
        # Sprint 31.91 Session 1a: derive the bracket's OCA group ID from
        # the entry ULID using the same deterministic formula
        # ``IBKRBroker.place_bracket_order`` uses (``f"oca_{parent_ulid}"``).
        # ``pending.order_id`` is the entry ULID (the dict was keyed by it
        # in ``on_approved``). Persisting this on ``ManagedPosition`` lets
        # Session 1b's standalone-SELL paths thread the same OCA group.
        # Re-entry on the same symbol generates a new ULID and therefore a
        # new ``oca_group_id``.
        oca_group_id = f"oca_{pending.order_id}" if pending.order_id else None
        position = ManagedPosition(
            symbol=pending.symbol,
            strategy_id=pending.strategy_id,
            entry_price=event.fill_price,
            entry_time=entry_fill_time,
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
            # FIX-04 P1-C1-L09: initialize mfe_time/mae_time at entry
            # (mirroring mfe_price/mae_price). Previously these stayed
            # None until the first tick with a price-change; an instant
            # reversal left mfe_time=None forever and surfaced as "null"
            # in analytics.
            mfe_time=entry_fill_time,
            mae_time=entry_fill_time,
            oca_group_id=oca_group_id,
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
        """Stop loss triggered. Close position (or remaining shares).

        DEF-158 fix: Also cancels any pending flatten orders for this symbol.
        If a time-stop or trail flatten was placed concurrently with the stop
        triggering, the flatten order must be cancelled to prevent a short.
        """
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

        # DEF-158: Cancel any pending flatten orders for this symbol.
        # A concurrent time-stop or trail flatten may have placed a SELL that
        # would create a short now that the stop has closed the position.
        flatten_entry = self._flatten_pending.get(pending.symbol)
        if flatten_entry is not None:
            flatten_oid = flatten_entry[0]
            try:
                await self._broker.cancel_order(flatten_oid)
            except Exception:
                logger.debug(
                    "Could not cancel concurrent flatten %s after stop fill for %s",
                    flatten_oid,
                    pending.symbol,
                )
            self._pending_orders.pop(flatten_oid, None)
            self._flatten_pending.pop(pending.symbol, None)

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
        """Market order to flatten position has filled.

        DEF-158 fix: After closing the position, cancels any OTHER pending
        flatten orders for the same symbol that may still be at the broker
        (e.g., from timeout resubmission). This prevents duplicate SELLs
        from creating a short position.
        """
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
        # FIX-04 P1-C1-L08: tighten the strategy_id-mismatch path from a
        # silent fallback to a hard error. The fallback existed for
        # positions opened before PendingManagedOrder tracked strategy_id;
        # after 89 sprints that legacy shape should no longer exist. An
        # ERROR here surfaces routing bugs instead of letting the fill
        # accrue silently to the wrong position's P&L.
        if position is None:
            logger.error(
                "Flatten fill for %s strategy_id=%s has no matching open "
                "position (tightened from fallback in FIX-04 P1-C1-L08).",
                pending.symbol,
                pending.strategy_id,
            )
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

        # DEF-158: Cancel any OTHER pending flatten orders for this symbol
        # that may still be live at the broker (from timeout resubmission).
        # The position is now closed — any additional SELL would go short.
        stale_flatten_ids = [
            oid for oid, p in self._pending_orders.items()
            if p.symbol == pending.symbol and p.order_type == "flatten"
            and oid != event.order_id
        ]
        for stale_id in stale_flatten_ids:
            try:
                await self._broker.cancel_order(stale_id)
            except Exception:
                logger.debug(
                    "Could not cancel stale flatten order %s for %s",
                    stale_id,
                    pending.symbol,
                )
            self._pending_orders.pop(stale_id, None)

    # ---------------------------------------------------------------------------
    # Fallback Poll Loop
    # ---------------------------------------------------------------------------

    def _now_et(self, now: datetime) -> datetime:
        """Convert the current clock time to the configured EOD timezone (ET).

        Tolerant of naive datetimes from test clocks — an unaware value is
        assumed to already be in the configured timezone, consistent with
        pre-existing behavior in both the EOD and startup-drain blocks.
        Introduced in FIX-04 P1-C1-L06 to collapse the duplicate ET
        conversion that previously lived in both poll-loop branches.
        """
        et_tz = ZoneInfo(self._config.eod_flatten_timezone)
        if now.tzinfo is not None:
            return now.astimezone(et_tz)
        return now.replace(tzinfo=et_tz)

    async def _poll_loop(self) -> None:
        """Runs every N seconds. Handles time-based exits and EOD flatten."""
        while self._running:
            try:
                await asyncio.sleep(self._config.fallback_poll_interval_seconds)
                if not self._running:
                    break

                now = self._clock.now()
                now_et = self._now_et(now)

                # Check EOD flatten (MD-4b-2)
                if not self._flattened_today:
                    flatten_time = time.fromisoformat(self._config.eod_flatten_time)
                    if now_et.time() >= flatten_time:
                        # FIX-04 P1-C1-L05: _flattened_today is set inside
                        # eod_flatten() itself; the post-call assignment
                        # here was a redundant double-write.
                        await self.eod_flatten()
                        continue

                # Drain startup flatten queue at market open (Sprint 29.5 R4)
                if self._startup_flatten_queue:
                    if now_et.time() >= time(9, 30):
                        await self._drain_startup_flatten_queue()

                # Margin circuit breaker auto-reset: check broker position count (Sprint 32.9 S2)
                # Sprint 31.91 S2b.2 (Pattern A.1): side-aware count filter.
                # Phantom shorts (DEF-204) must not inflate the count and block reset.
                if self._margin_circuit_open:
                    try:
                        broker_positions = await self._broker.get_positions()
                        long_positions = [
                            p for p in broker_positions if getattr(p, "side", None) == OrderSide.BUY
                        ]
                        short_positions = [
                            p for p in broker_positions if getattr(p, "side", None) == OrderSide.SELL
                        ]
                        position_count = len(long_positions)
                        reset_threshold = self._config.margin_circuit_reset_positions
                        will_reset = position_count < reset_threshold
                        logger.info(
                            "Margin circuit reset check: longs=%d, shorts=%d, "
                            "reset_threshold=%d, will_reset=%s",
                            len(long_positions),
                            len(short_positions),
                            reset_threshold,
                            will_reset,
                        )
                        if will_reset:
                            self._margin_circuit_open = False
                            self._margin_rejection_count = 0
                            self.margin_circuit_breaker_reset_time = datetime.now(UTC)
                            logger.info(
                                "Margin circuit breaker RESET — long position count %d below "
                                "threshold %d",
                                position_count,
                                reset_threshold,
                            )
                    except Exception:
                        logger.warning(
                            "Failed to query broker positions for margin circuit reset check"
                        )

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
        2. Close all managed positions at market (Pass 1) with fill verification
        3. Wait for fill callbacks with eod_flatten_timeout_seconds timeout
        4. Flatten broker-only positions not tracked by ARGUS (Pass 2)
        5. Post-flatten verification query; log CRITICAL if positions remain
        6. If auto_shutdown_after_eod is enabled, request system shutdown
        """
        logger.info("EOD flatten triggered — closing all positions")
        self._flattened_today = True
        eod_timeout = float(self._config.eod_flatten_timeout_seconds)

        # Clear abandoned set — EOD is the last resort (Sprint 29.5 R2)
        if self._flatten_abandoned:
            logger.info(
                "EOD clearing %d abandoned flatten symbols: %s",
                len(self._flatten_abandoned),
                sorted(self._flatten_abandoned),
            )
            self._flatten_abandoned.clear()
            self._flatten_cycle_count.clear()

        # --- Pass 1: Managed positions with fill verification (Sprint 32.9) ---
        self._eod_flatten_events = {}
        for _symbol, positions in list(self._managed_positions.items()):
            for position in positions:
                if not position.is_fully_closed and position.shares_remaining > 0:
                    if position.symbol not in self._eod_flatten_events:
                        self._eod_flatten_events[position.symbol] = asyncio.Event()
                    await self._flatten_position(position, reason="eod_flatten")

        filled: list[str] = []
        timed_out: list[str] = []
        if self._eod_flatten_events:
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        *[e.wait() for e in self._eod_flatten_events.values()]
                    ),
                    timeout=eod_timeout,
                )
                filled = list(self._eod_flatten_events.keys())
            except asyncio.TimeoutError:
                for sym, event in self._eod_flatten_events.items():
                    if event.is_set():
                        filled.append(sym)
                    else:
                        timed_out.append(sym)

            self.eod_flatten_pass1_count = len(filled)
            logger.info(
                "EOD flatten Pass 1: %d filled, %d timed out",
                len(filled),
                len(timed_out),
            )

            # Retry timed-out positions once with re-queried broker qty
            # (Sprint 32.9 + IMPROMPTU-04 DEF-199 side-check)
            if timed_out and self._config.eod_flatten_retry_rejected:
                try:
                    retry_positions = await self._broker.get_positions()
                    broker_qty_map: dict[str, int] = {
                        getattr(p, "symbol", ""): int(getattr(p, "shares", 0))
                        for p in retry_positions
                    }
                    broker_side_map: dict[str, Any] = {
                        getattr(p, "symbol", ""): getattr(p, "side", None)
                        for p in retry_positions
                    }
                    for sym in timed_out:
                        retry_qty = broker_qty_map.get(sym, 0)
                        retry_side = broker_side_map.get(sym, None)
                        if retry_qty > 0:
                            # DEF-199: branch on side. A re-queried short must
                            # NOT be flattened — that doubles the position.
                            if retry_side == OrderSide.BUY:
                                logger.warning(
                                    "EOD flatten: retrying long %s "
                                    "(%d shares from broker)",
                                    sym,
                                    retry_qty,
                                )
                                await self._flatten_unknown_position(
                                    sym, retry_qty, force_execute=True
                                )
                            elif retry_side == OrderSide.SELL:
                                logger.error(
                                    "EOD flatten (Pass 1 retry): DETECTED "
                                    "UNEXPECTED SHORT POSITION %s "
                                    "(%d shares). NOT auto-covering. "
                                    "Investigate and cover manually via "
                                    "scripts/ibkr_close_all_positions.py.",
                                    sym,
                                    retry_qty,
                                )
                            else:
                                logger.error(
                                    "EOD flatten (Pass 1 retry): position %s "
                                    "has unknown side (%r, qty=%d). "
                                    "Skipping auto-flatten.",
                                    sym, retry_side, retry_qty,
                                )
                except Exception as e:
                    logger.error("EOD flatten: retry pass failed: %s", e)

        self._eod_flatten_events = {}
        pass1_filled_set = set(filled)

        # --- Pass 2: Broker-only positions (Sprint 29.5 R3 + Sprint 32.9 shares fix
        # + IMPROMPTU-04 DEF-199 side-check) ---
        try:
            broker_positions = await self._broker.get_positions()
            managed_symbols = set(self._managed_positions.keys())
            p2_submitted = 0
            for pos in broker_positions:
                symbol = getattr(pos, "symbol", str(pos))
                qty = int(getattr(pos, "shares", 0))
                side = getattr(pos, "side", None)
                if symbol not in managed_symbols and symbol not in pass1_filled_set and qty > 0:
                    # DEF-199: IBKRBroker.get_positions() returns shares =
                    # abs(int(pos.position)); long/short lives on side. A blind
                    # SELL of a short doubles it. Branch on side.
                    if side == OrderSide.BUY:
                        p2_submitted += 1
                        logger.warning(
                            "EOD flatten: closing untracked long broker "
                            "position %s (%d shares)",
                            symbol,
                            qty,
                        )
                        await self._flatten_unknown_position(
                            symbol, qty, force_execute=True,
                        )
                    elif side == OrderSide.SELL:
                        # ARGUS is long-only. An untracked short MUST NOT be
                        # auto-flattened — a SELL would double it (DEF-199).
                        # Operator must cover manually.
                        logger.error(
                            "EOD flatten: DETECTED UNEXPECTED SHORT POSITION "
                            "%s (%d shares). NOT auto-covering. Investigate "
                            "and cover manually via "
                            "scripts/ibkr_close_all_positions.py.",
                            symbol,
                            qty,
                        )
                        # Sprint 31.91 S2b.2 (Pattern B): emit phantom_short
                        # SystemAlertEvent alongside the existing logger.error
                        # so the alert taxonomy is consistent with 2b.1's
                        # reconciliation broker-orphan branch and 2b.2's
                        # Health integrity check. Detection logic (DEF-199 A1
                        # fix) is unchanged — only observability is added.
                        try:
                            await self._event_bus.publish(
                                SystemAlertEvent(
                                    source="eod_flatten",
                                    alert_type="phantom_short",
                                    severity="critical",
                                    message=(
                                        f"EOD Pass 2 detected unexpected short "
                                        f"position for {symbol}: shares={qty}. "
                                        f"Will not place flatten SELL "
                                        f"(DEF-199 A1 protected)."
                                    ),
                                    metadata={
                                        "symbol": symbol,
                                        "shares": qty,
                                        "side": "SELL",
                                        "detection_source": "eod_flatten.pass2",
                                    },
                                )
                            )
                        except Exception:  # pragma: no cover - defensive
                            logger.exception(
                                "Failed to publish phantom_short "
                                "SystemAlertEvent for %s from EOD Pass 2",
                                symbol,
                            )
                    else:
                        logger.error(
                            "EOD flatten: position %s has unknown side "
                            "(%r, qty=%d). Skipping auto-flatten.",
                            symbol, side, qty,
                        )
            self.eod_flatten_pass2_count = p2_submitted
            if p2_submitted > 0:
                logger.info(
                    "EOD flatten Pass 2: %d broker-only positions submitted",
                    p2_submitted,
                )
        except Exception as e:
            logger.error("EOD flatten: broker position query failed: %s", e)

        # Post-flatten verification (Sprint 32.9)
        try:
            remaining = await self._broker.get_positions()
            if remaining:
                remaining_syms = [getattr(p, "symbol", str(p)) for p in remaining]
                logger.critical(
                    "EOD flatten: %d positions remain after both passes: %s",
                    len(remaining),
                    remaining_syms,
                )
        except Exception as e:
            logger.error("EOD flatten: post-verification query failed: %s", e)

        # Request auto-shutdown AFTER verification (Sprint 32.9: moved after verify)
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

        STARTUP-ONLY CONTRACT (added Sprint 31.91 Session 1c):

        This function is currently STARTUP-ONLY and is called exactly once at
        ARGUS boot via ``argus/main.py:1081`` (gated by
        ``_startup_flatten_disabled``). The unconditional
        ``cancel_all_orders(symbol)`` invocation is correct ONLY in this
        startup context — it clears stale yesterday's OCA siblings before
        today's session begins.

        Future callers MUST add a context parameter (e.g.,
        ``ReconstructContext``) distinguishing ``STARTUP_FRESH`` from
        ``RECONNECT_MID_SESSION``. The ``RECONNECT_MID_SESSION`` path MUST
        NOT invoke ``cancel_all_orders`` — yesterday's working bracket
        children are LIVE this-session orders that must be preserved.

        Sprint 31.93 (DEF-194/195/196 reconnect-recovery) is the natural
        sprint to add this differentiation. Until then, ARGUS does not
        support mid-session reconnect; operator daily-flatten remains the
        safety net.

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
            qty = int(getattr(pos, "shares", 0))

            # SAFETY: cancel stale yesterday OCA siblings BEFORE wiring this
            # broker-confirmed position into _managed_positions. Sprint 31.91
            # Session 1c (D4). See docstring re: STARTUP_ONLY contract — a
            # mid-session reconnect would WIPE OUT today's working bracket
            # children that must be preserved. On CancelPropagationTimeout,
            # skip this symbol entirely (no wiring, no flatten, no RECO) and
            # emit a critical alert; remaining symbols continue to be
            # reconstructed.
            try:
                await self._broker.cancel_all_orders(
                    symbol=symbol, await_propagation=True
                )
            except CancelPropagationTimeout:
                logger.error(
                    "Reconstruct ABORTED for %s: cancel propagation "
                    "timeout — skipping reconstruction. Position remains "
                    "at broker untouched. Operator should investigate "
                    "before next session.",
                    symbol,
                )
                await self._emit_cancel_propagation_timeout_alert(
                    source="order_manager.reconstruct_from_broker",
                    stage="reconstruct_from_broker",
                    symbol=symbol,
                    shares=abs(qty),
                )
                continue  # skip wiring this symbol; keep reconstructing rest

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

        DEF-158 fix: Cancels any open orders for the symbol before placing
        the flatten SELL to prevent bracket legs from firing after the
        flatten and creating a short position.

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

        # DEF-158: Cancel any open orders for this symbol before placing
        # the flatten SELL. Without this, residual bracket orders (stop/T1/T2)
        # from a prior session can trigger additional SELLs after the flatten,
        # creating a short position.
        await self._cancel_open_orders_for_symbol(symbol)

        # Sprint 31.91 Session 1c (D4): broker-only safety. Cancel stale
        # yesterday OCA-group siblings BEFORE the flatten SELL with explicit
        # propagation-await. Without propagation, a stale child could fill
        # against the SELL and produce a phantom short (DEF-204 mechanism).
        # On CancelPropagationTimeout, abort the SELL and emit a critical
        # SystemAlertEvent — the leaked-long failure mode is the intended
        # trade-off (bounded exposure preferable to an unbounded phantom
        # short). See PHASE-D-OPEN-ITEMS Item 2 for the disposition.
        try:
            await self._broker.cancel_all_orders(
                symbol=symbol, await_propagation=True
            )
        except CancelPropagationTimeout:
            logger.error(
                "EOD Pass 2 flatten ABORTED for %s: cancel propagation "
                "timeout — phantom long remains at broker with no working "
                "stop. Operator must run scripts/ibkr_close_all_positions.py "
                "before next session.",
                symbol,
            )
            await self._emit_cancel_propagation_timeout_alert(
                source="order_manager._flatten_unknown_position",
                stage="eod_pass2",
                symbol=symbol,
                shares=abs(qty),
            )
            return  # do NOT place SELL; abort cleanly

        try:
            sell_order = Order(
                strategy_id="startup_cleanup",
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=TradingOrderType.MARKET,
                quantity=abs(qty),
            )
            # OCA-EXEMPT: broker-only path (no ManagedPosition exists for
            # the unknown/zombie symbol). Safety comes from the
            # ``cancel_all_orders(symbol, await_propagation=True)`` call
            # immediately above (Sprint 31.91 Session 1c) which clears
            # stale yesterday's OCA-group siblings before this SELL; a
            # per-Order ocaGroup decoration is not the right mechanism here.
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

    async def _emit_cancel_propagation_timeout_alert(
        self,
        *,
        source: str,
        stage: str,
        symbol: str,
        shares: int,
    ) -> None:
        """Emit a critical SystemAlertEvent for a cancel-propagation timeout.

        Sprint 31.91 Session 1c (D4) — shared emission helper for the three
        broker-only safety paths (`_flatten_unknown_position`,
        `_drain_startup_flatten_queue`, `reconstruct_from_broker`). The
        operator response when this alert fires is to manually flatten via
        ``scripts/ibkr_close_all_positions.py`` before the next session;
        the leaked-long failure mode is the intended trade-off vs. an
        incorrect SELL that would create an unbounded phantom short.
        """
        message = (
            f"cancel_all_orders did not propagate within timeout for "
            f"{symbol} (shares={shares}, stage={stage}). Position "
            f"remains at broker untouched. Manual flatten required: "
            f"scripts/ibkr_close_all_positions.py."
        )
        try:
            await self._event_bus.publish(
                SystemAlertEvent(
                    source=source,
                    alert_type="cancel_propagation_timeout",
                    message=message,
                    severity="critical",
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "Failed to publish cancel_propagation_timeout "
                "SystemAlertEvent for %s",
                symbol,
            )

    async def _handle_broker_orphan_short(
        self, symbol: str, recon_pos: ReconciliationPosition
    ) -> None:
        """Emit a CRITICAL ``phantom_short`` alert.

        Sprint 31.91 Session 2b.1 (D5) — DEF-204 detection signal. The
        broker reports a SHORT position for which ARGUS has no
        ``_managed_positions`` entry. ARGUS is long-only (DEC-011), so a
        broker-side short is an OCA-leak signature or external/manual
        intervention. The alert is the operator-page; the per-symbol
        entry gate (preventing new entries on the gated symbol) is wired
        in Session 2c.1 — 2b.1 is detection-only.
        """
        if not self._reconciliation_config.broker_orphan_alert_enabled:
            return  # config-gated; allow operator to disable for testing

        logger.critical(
            "BROKER ORPHAN SHORT DETECTED: %s shares=%d. Broker reports short "
            "position ARGUS has no managed_positions entry for. This is the "
            "DEF-204 signature — investigate via "
            "scripts/ibkr_close_all_positions.py and check Sprint 31.91 "
            "runbook (live-operations.md Phantom-Short Gate Diagnosis).",
            symbol,
            recon_pos.shares,
        )

        message = (
            f"Broker reports short position for {symbol} that ARGUS has "
            f"no managed_positions entry for. Shares: {recon_pos.shares}."
        )
        try:
            await self._event_bus.publish(
                SystemAlertEvent(
                    source="reconciliation",
                    alert_type="phantom_short",
                    message=message,
                    severity="critical",
                    metadata={
                        "symbol": symbol,
                        "shares": recon_pos.shares,
                        "side": "SELL",
                        "detection_source": "reconciliation.broker_orphan_branch",
                    },
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "Failed to publish phantom_short SystemAlertEvent for %s",
                symbol,
            )

        # Sprint 31.91 Session 2c.1: engage per-symbol entry gate. The
        # ``not in`` guard makes engagement idempotent — re-detection of a
        # still-active phantom short does NOT produce duplicate persistence
        # writes (INSERT OR REPLACE would also be idempotent on the SQL
        # side, but skipping the write entirely avoids unnecessary I/O).
        if (
            self._reconciliation_config.broker_orphan_entry_gate_enabled
            and symbol not in self._phantom_short_gated_symbols
        ):
            self._phantom_short_gated_symbols.add(symbol)
            # Persist immediately. Fire-and-forget: if ARGUS crashes before
            # the write completes, the next reconciliation cycle (~1 minute
            # later) re-detects the phantom short and re-engages the gate.
            # Making persistence synchronous would block reconciliation.
            persist_task = asyncio.create_task(
                self._persist_gated_symbol(
                    symbol, "engaged", last_observed_short_shares=recon_pos.shares
                )
            )
            self._pending_gate_persist_tasks.add(persist_task)

            def _on_persist_done(t: "asyncio.Task[None]", _sym: str = symbol) -> None:
                self._pending_gate_persist_tasks.discard(t)
                _log_persist_task_exception(t, _sym)

            persist_task.add_done_callback(_on_persist_done)
            logger.critical(
                "Phantom-short gate ENGAGED for %s. Future "
                "OrderApprovedEvents for this symbol will be rejected "
                "until gate clears (5 consecutive zero-shares cycles per "
                "Session 2c.2 OR operator override per Session 2d).",
                symbol,
            )

    async def _handle_broker_orphan_long(
        self, symbol: str, recon_pos: ReconciliationPosition, cycle: int
    ) -> None:
        """Long-orphan handler with M2 exponential-backoff re-alert schedule.

        Sprint 31.91 Session 2b.1 (D5, M2 lifecycle):
        - cycle 1–2: WARNING log only (likely transient — eventual-consistency
          lag from a recent fill ARGUS hasn't yet processed).
        - cycle ≥ 3: emit ``stranded_broker_long`` alert (severity=warning)
          on schedule [3, 6, 12, 24, 48], then every 60 cycles thereafter
          (~hourly cap if reconciliation runs ~once per minute).

        Counter cleanup on broker-zero observation and session reset is
        handled by ``reconcile_positions`` and ``reset_daily_state``
        respectively.
        """
        if not self._reconciliation_config.broker_orphan_alert_enabled:
            return

        if cycle < 3:
            logger.warning(
                "Broker-orphan LONG cycle %d for %s shares=%d. Likely "
                "transient (eventual-consistency lag from a recent fill "
                "ARGUS has not yet processed). Will alert at cycle 3.",
                cycle,
                symbol,
                recon_pos.shares,
            )
            return

        # Cycle >= 3: check exp-backoff schedule
        last_alerted = self._broker_orphan_last_alerted_cycle.get(symbol, 0)
        # M2 exponential backoff: alert at cycles 3, 6, 12, 24, 48, then every
        # 60 cycles thereafter (60 ≈ hourly if recon runs ~once per minute).
        schedule = [3, 6, 12, 24, 48]
        if last_alerted == 0:
            should_alert = cycle == 3
        else:
            next_in_schedule = next(
                (c for c in schedule if c > last_alerted), None
            )
            if next_in_schedule is not None:
                should_alert = cycle >= next_in_schedule
            else:
                # Past the schedule: hourly cap (every 60 cycles after last).
                should_alert = (cycle - last_alerted) >= 60

        if not should_alert:
            return

        self._broker_orphan_last_alerted_cycle[symbol] = cycle

        message = (
            f"Broker reports long position for {symbol} that ARGUS has "
            f"no managed_positions entry for, persisting across {cycle} "
            f"reconciliation cycles. Shares: {recon_pos.shares}. Operator "
            f"should investigate (eventual-consistency window has elapsed)."
        )
        try:
            await self._event_bus.publish(
                SystemAlertEvent(
                    source="reconciliation",
                    alert_type="stranded_broker_long",
                    message=message,
                    severity="warning",
                    metadata={
                        "symbol": symbol,
                        "shares": recon_pos.shares,
                        "side": "BUY",
                        "consecutive_cycles": cycle,
                        "detection_source": "reconciliation.broker_orphan_branch",
                    },
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "Failed to publish stranded_broker_long "
                "SystemAlertEvent for %s",
                symbol,
            )

    # ------------------------------------------------------------------
    # Phantom-short entry-gate persistence (Sprint 31.91 Session 2c.1)
    # ------------------------------------------------------------------
    #
    # State backing the per-symbol entry gate
    # (``_phantom_short_gated_symbols``). The DDL is created idempotently
    # on first read/write so the table exists in fresh and existing
    # ``data/operations.db`` files. Per-write connection lifecycle
    # mirrors ``argus.intelligence.experiments.store`` (the dominant
    # aiosqlite pattern in the codebase).
    #
    # Schema:
    #   CREATE TABLE phantom_short_gated_symbols (
    #     symbol TEXT PRIMARY KEY,
    #     engaged_at_utc TEXT NOT NULL,
    #     engaged_at_et TEXT NOT NULL,
    #     engagement_source TEXT NOT NULL,
    #     last_observed_short_shares INTEGER
    #   )
    #
    # M5 rehydration ordering: ``_rehydrate_gated_symbols_from_db()`` is
    # called from ``argus/main.py`` BEFORE ``order_manager.start()``
    # subscribes to ``OrderApprovedEvent``. Without this ordering a ~60s
    # window of unsafe entries on restart could land before the next
    # reconciliation re-detects the phantom short and re-engages the gate.

    _PHANTOM_SHORT_GATED_SYMBOLS_DDL: str = (
        "CREATE TABLE IF NOT EXISTS phantom_short_gated_symbols (\n"
        "    symbol TEXT PRIMARY KEY,\n"
        "    engaged_at_utc TEXT NOT NULL,\n"
        "    engaged_at_et TEXT NOT NULL,\n"
        "    engagement_source TEXT NOT NULL,\n"
        "    last_observed_short_shares INTEGER\n"
        ")"
    )

    # Sprint 31.91 Session 2d (D5, M3): operator-override audit log.
    # Captures forensic detail for each manual phantom-short gate
    # clearance via ``POST /api/v1/reconciliation/phantom-short-gate/clear``.
    # Append-only; rows persist across restarts (no retention policy on
    # this table per Sprint 31.91 retention spec — full audit forever).
    # ``prior_engagement_alert_id`` is None pre-Session-5a.1 (HealthMonitor
    # consumer not yet wired); 5a.1 will populate it via cross-reference.
    _PHANTOM_SHORT_OVERRIDE_AUDIT_DDL: str = (
        "CREATE TABLE IF NOT EXISTS phantom_short_override_audit (\n"
        "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "    timestamp_utc TEXT NOT NULL,\n"
        "    timestamp_et TEXT NOT NULL,\n"
        "    symbol TEXT NOT NULL,\n"
        "    prior_engagement_source TEXT,\n"
        "    prior_engagement_alert_id TEXT,\n"
        "    reason_text TEXT NOT NULL,\n"
        "    override_payload_json TEXT NOT NULL\n"
        ")"
    )
    _PHANTOM_SHORT_OVERRIDE_AUDIT_INDEX_SYMBOL: str = (
        "CREATE INDEX IF NOT EXISTS idx_psoa_symbol "
        "ON phantom_short_override_audit(symbol)"
    )
    _PHANTOM_SHORT_OVERRIDE_AUDIT_INDEX_TIMESTAMP: str = (
        "CREATE INDEX IF NOT EXISTS idx_psoa_timestamp "
        "ON phantom_short_override_audit(timestamp_utc)"
    )

    def _ensure_operations_db_parent(self) -> None:
        """Ensure the parent directory of ``operations.db`` exists.

        ``aiosqlite.connect`` will create the DB file itself, but the
        parent directory must already exist. Tests use ``tmp_path``;
        production uses ``data/`` which is committed.
        """
        parent = Path(self._operations_db_path).parent
        if str(parent) and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

    async def _persist_gated_symbol(
        self,
        symbol: str,
        source: str,
        last_observed_short_shares: int | None = None,
    ) -> None:
        """Write/upsert a gated-symbol row to ``operations.db``.

        Sprint 31.91 Session 2c.1. Uses ``INSERT OR REPLACE`` so
        re-detection of an already-gated symbol updates the row in place
        rather than producing a constraint error. Writes are atomic by
        SQLite default; ``commit()`` runs on the success path.
        """
        self._ensure_operations_db_parent()
        utcnow = datetime.now(UTC)
        et_now = utcnow.astimezone(ZoneInfo("America/New_York"))
        async with aiosqlite.connect(self._operations_db_path) as db:
            await db.execute(self._PHANTOM_SHORT_GATED_SYMBOLS_DDL)
            await db.execute(
                "INSERT OR REPLACE INTO phantom_short_gated_symbols "
                "(symbol, engaged_at_utc, engaged_at_et, engagement_source, "
                "last_observed_short_shares) VALUES (?, ?, ?, ?, ?)",
                (
                    symbol,
                    utcnow.isoformat(),
                    et_now.isoformat(),
                    source,
                    last_observed_short_shares,
                ),
            )
            await db.commit()

    async def _remove_gated_symbol_from_db(self, symbol: str) -> None:
        """Delete a gated-symbol row from ``operations.db``.

        Sprint 31.91 Session 2c.1 stub; Session 2c.2 (5-cycle auto-clear)
        and Session 2d (operator override) are the call sites. Implemented
        in 2c.1 so the SQL surface is complete and 2c.2/2d don't need to
        re-touch this region.
        """
        self._ensure_operations_db_parent()
        async with aiosqlite.connect(self._operations_db_path) as db:
            await db.execute(self._PHANTOM_SHORT_GATED_SYMBOLS_DDL)
            await db.execute(
                "DELETE FROM phantom_short_gated_symbols WHERE symbol = ?",
                (symbol,),
            )
            await db.commit()

    async def clear_phantom_short_gate_with_audit(
        self,
        symbol: str,
        reason: str,
        override_payload_json: str,
    ) -> tuple[int, str | None, str | None]:
        """Manually clear the phantom-short gate for ``symbol`` with full
        forensic audit-log persistence (Sprint 31.91 Session 2d, M3).

        Persistence-first ordering — both writes (audit INSERT + gated
        DELETE) happen inside the same ``aiosqlite`` connection's
        ``commit()`` so a failure between them rolls back atomically.
        In-memory state is mutated by the caller AFTER this method
        returns successfully; if the SQLite write fails, in-memory state
        is unchanged and the gate remains engaged (fail-closed).

        Args:
            symbol: Symbol to clear (caller has already normalized to
                uppercase).
            reason: Operator's ≥10-char justification (validated upstream
                by Pydantic).
            override_payload_json: Full request-body JSON for forensic
                replay.

        Returns:
            Tuple of ``(audit_id, prior_engagement_source,
            prior_engagement_alert_id)``. ``prior_engagement_source`` is
            ``"reconciliation.broker_orphan_branch"`` pre-5a.1 (the only
            engagement source). ``prior_engagement_alert_id`` is ``None``
            until Session 5a.1 wires HealthMonitor cross-reference.
        """
        self._ensure_operations_db_parent()
        utcnow = datetime.now(UTC)
        et_now = utcnow.astimezone(ZoneInfo("America/New_York"))
        # Pre-Session-5a.1: only engagement source is the reconciliation
        # broker-orphan branch. Once HealthMonitor exposes alert IDs,
        # this becomes a cross-reference lookup.
        prior_source = "reconciliation.broker_orphan_branch"
        prior_alert_id: str | None = None

        async with aiosqlite.connect(self._operations_db_path) as db:
            # Idempotent DDL — both tables, both audit-log indexes.
            await db.execute(self._PHANTOM_SHORT_GATED_SYMBOLS_DDL)
            await db.execute(self._PHANTOM_SHORT_OVERRIDE_AUDIT_DDL)
            await db.execute(self._PHANTOM_SHORT_OVERRIDE_AUDIT_INDEX_SYMBOL)
            await db.execute(self._PHANTOM_SHORT_OVERRIDE_AUDIT_INDEX_TIMESTAMP)
            cursor = await db.execute(
                "INSERT INTO phantom_short_override_audit "
                "(timestamp_utc, timestamp_et, symbol, "
                "prior_engagement_source, prior_engagement_alert_id, "
                "reason_text, override_payload_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    utcnow.isoformat(),
                    et_now.isoformat(),
                    symbol,
                    prior_source,
                    prior_alert_id,
                    reason,
                    override_payload_json,
                ),
            )
            audit_id = cursor.lastrowid
            await db.execute(
                "DELETE FROM phantom_short_gated_symbols WHERE symbol = ?",
                (symbol,),
            )
            # Single transaction: audit INSERT + gated DELETE both
            # commit together or both roll back.
            await db.commit()

        if audit_id is None:  # pragma: no cover - aiosqlite always sets lastrowid
            raise RuntimeError(
                "phantom_short_override_audit INSERT did not return a "
                "lastrowid"
            )
        return audit_id, prior_source, prior_alert_id

    async def _rehydrate_gated_symbols_from_db(self) -> None:
        """M5 rehydration: load gated symbols from ``operations.db`` into
        the in-memory ``_phantom_short_gated_symbols`` set.

        Sprint 31.91 Session 2c.1. Called from ``argus/main.py`` BEFORE
        ``order_manager.start()`` subscribes to ``OrderApprovedEvent``.
        On a fresh boot with no operations.db, the table is created
        idempotently and zero rows are loaded — gate state is empty,
        which is correct.

        Logs CRITICAL when symbols are rehydrated so the operator sees
        the persisted gate state on every restart and can investigate.
        """
        self._ensure_operations_db_parent()
        async with aiosqlite.connect(self._operations_db_path) as db:
            await db.execute(self._PHANTOM_SHORT_GATED_SYMBOLS_DDL)
            await db.commit()
            async with db.execute(
                "SELECT symbol FROM phantom_short_gated_symbols"
            ) as cursor:
                rows = await cursor.fetchall()
        for (symbol,) in rows:
            self._phantom_short_gated_symbols.add(symbol)
        if self._phantom_short_gated_symbols:
            logger.critical(
                "Phantom-short gate REHYDRATED on startup. Gated symbols: "
                "%s. Operator must investigate (Sprint 31.91 runbook).",
                sorted(self._phantom_short_gated_symbols),
            )

    async def _cancel_open_orders_for_symbol(self, symbol: str) -> None:
        """Cancel any open broker-side orders for a given symbol.

        Shared helper used before flattening an unknown/zombie position so
        residual bracket orders (stop/T1/T2) from a prior session cannot
        fire after the flatten SELL and produce a short (DEF-158). Called
        from the direct flatten path and from the startup-queue drain
        (FIX-04 P1-C1-M02).
        """
        try:
            open_orders = await self._broker.get_open_orders()
        except Exception:
            logger.warning(
                "Startup cleanup: could not query open orders for %s",
                symbol,
            )
            return
        for order in open_orders:
            if getattr(order, "symbol", "") != symbol:
                continue
            order_id = getattr(order, "order_id", None) or getattr(
                order, "orderId", None
            ) or getattr(order, "id", None)
            if not order_id:
                continue
            try:
                await self._broker.cancel_order(str(order_id))
            except Exception:
                logger.debug(
                    "Could not cancel pre-existing order %s for %s",
                    order_id,
                    symbol,
                )

    async def _drain_startup_flatten_queue(self) -> None:
        """Execute queued startup zombie flattens (Sprint 29.5 R4).

        Called from the poll loop when market opens. Drains the entire
        queue and submits market sell orders for each entry. Before each
        SELL, cancels any pre-existing bracket orders for the symbol
        (FIX-04 P1-C1-M02) to prevent residual stop/T1/T2 from firing
        between market-open and the queued SELL.
        """
        if not self._startup_flatten_queue:
            return

        queue = list(self._startup_flatten_queue)
        self._startup_flatten_queue.clear()

        logger.info(
            "Draining startup flatten queue: %d positions", len(queue)
        )
        for symbol, qty in queue:
            await self._cancel_open_orders_for_symbol(symbol)

            # Sprint 31.91 Session 1c (D4): broker-only safety. Cancel stale
            # yesterday OCA-group siblings BEFORE the flatten SELL with
            # explicit propagation-await. On timeout, log + emit alert and
            # CONTINUE draining the queue for remaining symbols — do NOT
            # halt the whole drain on one symbol's timeout.
            try:
                await self._broker.cancel_all_orders(
                    symbol=symbol, await_propagation=True
                )
            except CancelPropagationTimeout:
                logger.error(
                    "Startup zombie flatten ABORTED for %s: cancel "
                    "propagation timeout — phantom long remains at broker "
                    "with no working stop. Operator must run "
                    "scripts/ibkr_close_all_positions.py before next session.",
                    symbol,
                )
                await self._emit_cancel_propagation_timeout_alert(
                    source="order_manager._drain_startup_flatten_queue",
                    stage="startup_zombie_flatten",
                    symbol=symbol,
                    shares=abs(qty),
                )
                continue  # skip this symbol; keep draining

            try:
                sell_order = Order(
                    strategy_id="startup_cleanup",
                    symbol=symbol,
                    side=OrderSide.SELL,
                    order_type=TradingOrderType.MARKET,
                    quantity=abs(qty),
                )
                # OCA-EXEMPT: broker-only path (no ManagedPosition exists for
                # queued startup zombies). Safety comes from the
                # ``cancel_all_orders(symbol, await_propagation=True)`` call
                # immediately above (Sprint 31.91 Session 1c) which clears
                # stale OCA-group siblings before placement; a per-Order
                # ocaGroup decoration is not the right mechanism here.
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
        avg_entry = float(getattr(pos, "entry_price", 0.0))
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
        qty = int(getattr(pos, "shares", 0))
        avg_entry = float(getattr(pos, "entry_price", 0.0))

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
                t1_shares = int(getattr(order, "quantity", 0) or 0)
                break

        # FIX-04 P1-C1-M06: true entry_time is not recoverable from broker
        # state. Bias reconstructed entry_time earlier by half the global
        # max_position_duration so the fallback time-stop fires at roughly
        # the expected point post-restart rather than granting a fresh
        # full-duration lease. Per-signal time_stop_seconds is not
        # reconstructed (unavailable from broker state); EOD flatten
        # provides a hard upper bound regardless. A durable fix (persist
        # entry_time in the trades-DB sidecar and restore it here) is out
        # of scope for this session.
        reconstructed_entry_time = self._clock.now() - timedelta(
            minutes=self._config.max_position_duration_minutes // 2
        )
        managed = ManagedPosition(
            symbol=symbol,
            strategy_id="reconstructed",
            entry_price=avg_entry,
            entry_time=reconstructed_entry_time,
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

    def _handle_oca_already_filled(
        self, position: ManagedPosition, *, where: str
    ) -> None:
        """Mark a position as a redundant exit and log INFO when an
        OCA-grouped SELL placement raises IBKR Error 201 "OCA group is
        already filled".

        Used by all four standalone-SELL paths (``_trail_flatten``,
        ``_escalation_update_stop``, ``_submit_stop_order`` /
        ``_resubmit_stop_with_retry``, ``_flatten_position``). The
        signature means another OCA member (typically the bracket stop)
        already filled and the position is exiting via that member's
        fill callback — so the redundant fresh-SELL is SAFE to skip.

        Importantly, the caller MUST NOT add the order_id to
        ``_flatten_pending``; this function deliberately leaves that
        dict untouched to short-circuit the DEF-158 retry path. Session
        3's side-aware ``_check_flatten_pending_timeouts`` would catch
        the resulting zero-broker-position anyway, but the
        short-circuit here is cleaner.

        Args:
            position: The ManagedPosition whose SELL placement was
                rejected with the OCA-filled signature.
            where: Caller name (for log clarity).
        """
        position.redundant_exit_observed = True
        logger.info(
            "OCA group already filled for %s in %s; redundant SELL skipped "
            "— position is exiting via an already-filled OCA member "
            "(oca_group=%s)",
            position.symbol,
            where,
            position.oca_group_id,
        )

    async def _submit_stop_order(
        self, position: ManagedPosition, shares: int, stop_price: float
    ) -> None:
        """Submit a stop-loss order and track it.

        Sprint 31.91 Session 1b: threads ``ManagedPosition.oca_group_id``
        onto the placed Order so the new stop joins the bracket's OCA
        group. Covers ``_resubmit_stop_with_retry`` (DEC-372 retry-cap
        path), stop-to-breakeven, MFE/MAE trail, and the
        revision-rejected fresh-stop path. ``oca_group_id is None`` for
        ``reconstruct_from_broker``-derived positions falls through to
        legacy no-OCA behavior.

        Sprint 31.91 Session 1b: also handles IBKR Error 201 "OCA group
        is already filled" gracefully — that signature means the
        original bracket stop already filled (the position is exiting
        via that fill callback). The redundant fresh-stop submission is
        logged INFO and the retry loop short-circuits to
        ``_handle_oca_already_filled``; DEF-158 retry path is not
        engaged.
        """
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
                # Sprint 31.91 Session 1b: thread bracket OCA group when
                # present. ``oca_group_id`` is None for
                # ``reconstruct_from_broker``-derived positions; legacy
                # no-OCA behavior preserved by the conditional below.
                if position.oca_group_id is not None:
                    order.ocaGroup = position.oca_group_id
                    order.ocaType = _OCA_TYPE_BRACKET
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

            except Exception as exc:
                if _is_oca_already_filled_error(exc):
                    # SAFE outcome — original bracket stop already filled.
                    # Position is exiting via that OCA member's callback.
                    # Do NOT retry, do NOT emergency flatten.
                    self._handle_oca_already_filled(
                        position, where="_submit_stop_order"
                    )
                    return
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
            # OCA-EXEMPT: T1 limit replacement (called from
            # ``_handle_revision_rejected`` and ``_amend_bracket_on_slippage``).
            # The original T1 leg is a bracket child whose OCA membership is
            # set in ``IBKRBroker.place_bracket_order`` (Session 1a). A
            # revision-rejected fresh T1 resubmission was outside Sprint
            # 31.91 Session 1b's spec §6 4-path scope; threading the
            # replacement into the bracket OCA group is a follow-on (logged
            # via the staged-flow report).
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
            # OCA-EXEMPT: T2 limit replacement. Same reasoning as
            # ``_submit_t1_order``: the original T2 leg is a bracket child
            # whose OCA membership is set in
            # ``IBKRBroker.place_bracket_order`` (Sprint 31.91 Session 1a).
            # A revision-rejected fresh T2 resubmission was outside Session
            # 1b's 4-path scope.
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

        DEF-158 fix: Before resubmitting, queries broker position to confirm
        shares still exist. If broker position is 0, the original order filled
        (fill callback may be delayed) — clears pending without resubmitting.
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

            # DEF-158: Always verify broker position before resubmitting.
            # The original order may have filled at IBKR even though the fill
            # callback hasn't arrived yet. Resubmitting would create a short.
            sell_qty = position.shares_remaining
            # Clear error_404 flag if set (Sprint 29.5 R1 compat)
            broker_404_symbols = getattr(self._broker, "error_404_symbols", None)
            if broker_404_symbols is not None:
                broker_404_symbols.discard(symbol)
            try:
                broker_positions = await self._broker.get_positions()
                broker_qty = 0
                broker_side: Any = None
                for bp in broker_positions:
                    if getattr(bp, "symbol", "") == symbol:
                        broker_qty = abs(int(getattr(bp, "shares", 0)))
                        # Sprint 31.91 Session 3 (DEF-158 retry side-check):
                        # mirror IMPROMPTU-04 EOD A1 idiom at :1888-1904. ARGUS
                        # is long-only; a broker-side SHORT must NOT be auto-
                        # flattened — issuing SELL doubles the short (DEF-204).
                        broker_side = getattr(bp, "side", None)
                        break
                if broker_qty == 0:
                    logger.info(
                        "Flatten timeout: IBKR position already closed for %s "
                        "— original order likely filled (DEF-158 guard)",
                        symbol,
                    )
                    self._flatten_pending.pop(symbol, None)
                    continue
                # Sprint 31.91 Session 3 (DEF-158 retry side-check): 3-branch
                # gate before resubmission. Mirror of IMPROMPTU-04 EOD A1 at
                # :1875-1904 — same cost-of-error asymmetry (unbounded short
                # vs. bounded leaked long), same taxonomy (CRITICAL alert on
                # phantom-short detection, ERROR log on unknown side, refuse
                # the SELL in both cases). Branch 1 (BUY) falls through to
                # the existing flatten-resubmit path below.
                if broker_side == OrderSide.SELL:
                    logger.critical(
                        "Flatten retry refused for %s: broker reports SHORT "
                        "position (shares=%d) but ARGUS expected long. Will "
                        "NOT issue SELL (would double the short, DEF-204). "
                        "Investigate via scripts/ibkr_close_all_positions.py.",
                        symbol,
                        broker_qty,
                    )
                    try:
                        await self._event_bus.publish(
                            SystemAlertEvent(
                                source="order_manager._check_flatten_pending_timeouts",
                                alert_type="phantom_short_retry_blocked",
                                severity="critical",
                                message=(
                                    f"DEF-158 retry refused for {symbol}: "
                                    f"broker reports SHORT position "
                                    f"(shares={broker_qty}) but ARGUS "
                                    f"expected long. SELL was NOT issued. "
                                    f"Operator must investigate via "
                                    f"scripts/ibkr_close_all_positions.py."
                                ),
                                metadata={
                                    "symbol": symbol,
                                    "broker_shares": broker_qty,
                                    "broker_side": "SELL",
                                    "expected_side": "BUY",
                                    "detection_source": "def158_retry",
                                },
                            )
                        )
                    except Exception:  # pragma: no cover - defensive
                        logger.exception(
                            "Failed to publish phantom_short_retry_blocked "
                            "SystemAlertEvent for %s",
                            symbol,
                        )
                    # Clear pending so the next timeout cycle does not
                    # re-emit the alert in an infinite loop.
                    self._flatten_pending.pop(symbol, None)
                    continue
                if broker_side != OrderSide.BUY:
                    logger.error(
                        "Flatten retry refused for %s: broker side is %r "
                        "(expected OrderSide.BUY or OrderSide.SELL); "
                        "broker_qty=%d. Will NOT issue SELL. Investigate "
                        "broker integration; check Position model for "
                        "malformed `side` field.",
                        symbol,
                        broker_side,
                        broker_qty,
                    )
                    # Defensive code path — structural bug in the broker
                    # adapter or Position model. ERROR log is sufficient
                    # observability; alert flooding on a structural defect
                    # would not be useful. Clear pending to avoid loop.
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
                    "Broker position query failed for %s — using ARGUS qty %d",
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
                # OCA-EXEMPT: DEF-158 retry path. Sprint 31.91 Session 3
                # added the upstream 3-branch side gate (BUY=resubmit /
                # SELL=alert+halt / unknown=halt) so SELL-of-short is
                # structurally prevented before this placement. OCA group
                # threading on the retry SELL is not added here — the
                # original flatten's OCA siblings were already drained at
                # first dispatch by ``_flatten_position``; the retry is a
                # fresh standalone SELL with no live OCA peers to bind to.
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
            # Sprint 31.91 Session 1b: thread bracket OCA group when present.
            # ``oca_group_id`` is None for ``reconstruct_from_broker``-derived
            # positions; legacy no-OCA behavior preserved.
            if position.oca_group_id is not None:
                order.ocaGroup = position.oca_group_id
                order.ocaType = _OCA_TYPE_BRACKET
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
        except Exception as exc:
            if _is_oca_already_filled_error(exc):
                # Sprint 31.91 Session 1b: SAFE outcome — bracket stop or
                # other OCA member already filled. Position is exiting via
                # that member's fill callback. Do NOT add to
                # ``_flatten_pending`` (DEF-158 retry path is short-
                # circuited). Continue to Step 4 (sibling cancellation)
                # since IBKR's OCA atomically cancelled them already, but
                # ARGUS-side bookkeeping should still drop the order_ids.
                self._handle_oca_already_filled(position, where="_trail_flatten")
            else:
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
            # Sprint 31.91 Session 1b: thread bracket OCA group when present.
            # ``oca_group_id`` is None for ``reconstruct_from_broker``-derived
            # positions; legacy no-OCA behavior preserved.
            if position.oca_group_id is not None:
                order.ocaGroup = position.oca_group_id
                order.ocaType = _OCA_TYPE_BRACKET
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
        except Exception as exc:
            if _is_oca_already_filled_error(exc):
                # Sprint 31.91 Session 1b: SAFE outcome — bracket stop or
                # other OCA member already filled. Position is exiting via
                # that member's fill callback. Do NOT flatten or escalate
                # further; do NOT add to ``_flatten_pending``.
                self._handle_oca_already_filled(
                    position, where="_escalation_update_stop"
                )
                return
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
                # Sprint 31.91 Session 1b: thread bracket OCA group when
                # present. ``oca_group_id`` is None for
                # ``reconstruct_from_broker``-derived positions; legacy
                # no-OCA behavior preserved.
                if position.oca_group_id is not None:
                    order.ocaGroup = position.oca_group_id
                    order.ocaType = _OCA_TYPE_BRACKET
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
            except Exception as exc:
                if _is_oca_already_filled_error(exc):
                    # Sprint 31.91 Session 1b: SAFE outcome — bracket stop
                    # or other OCA member already filled. Position is
                    # exiting via that member's fill callback. Do NOT add
                    # to ``_flatten_pending`` (DEF-158 retry path is
                    # short-circuited).
                    self._handle_oca_already_filled(
                        position, where="_flatten_position"
                    )
                    return
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

        # Signal EOD flatten verification event if waiting (Sprint 32.9)
        eod_event = self._eod_flatten_events.get(position.symbol)
        if eod_event is not None:
            eod_event.set()

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

                config_fingerprint = self._fingerprint_registry.get(position.strategy_id)

                # DEF-159: Mark trades with unrecoverable entry prices
                entry_known = position.entry_price != 0.0

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
                    config_fingerprint=config_fingerprint,
                    entry_price_known=entry_known,
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
            # Clean up reconciliation tracking when no positions remain for symbol.
            # FIX-04 P1-C1-L07: these per-symbol maps are ALSO cleared wholesale
            # in reset_daily_state(); the per-close pop() here is intentional
            # defense-in-depth so state is not carried across an intraday
            # close-reopen of the same symbol (ALLOW_ALL duplicate stock
            # policy, DEC-121/160).
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
        # Reset margin circuit breaker for new session (Sprint 32.9 S2)
        self._margin_rejection_count = 0
        self._margin_circuit_open = False
        # Reset safety tracking counters for new session (Sprint 31A S1)
        self.margin_circuit_breaker_open_time = None
        self.margin_circuit_breaker_reset_time = None
        self.margin_entries_blocked_count = 0
        self.eod_flatten_pass1_count = 0
        self.eod_flatten_pass2_count = 0
        self.signal_cutoff_skipped_count = 0
        # Sprint 31.91 Session 2b.1 (D5, M2): broker-orphan LONG cycle counters
        # are session-scoped — clear on each session start. Restart-preservation
        # of phantom-short gate state lands in Session 2c.1 (SQLite); the
        # cycle counter itself is intentionally NOT persisted across restarts.
        self._broker_orphan_long_cycles.clear()
        self._broker_orphan_last_alerted_cycle.clear()

    def increment_signal_cutoff(self) -> None:
        """Increment the signal cutoff skip counter.

        Called by the signal processing pipeline in main.py each time a signal
        is discarded due to the pre-EOD signal cutoff being active.
        """
        self.signal_cutoff_skipped_count += 1

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
        self, broker_positions: dict[str, ReconciliationPosition]
    ) -> list[dict[str, object]]:
        """Compare internal positions against broker-reported positions.

        Detects discrepancies and logs warnings. Broker-confirmed positions
        are never auto-closed (snapshot may be stale). Unconfirmed positions
        are cleaned up only after consecutive_miss_threshold consecutive
        snapshot misses when auto_cleanup_unconfirmed is True.

        Sprint 31.91 Session 2a (DEC-385 reserved): the ``broker_positions``
        contract is now ``dict[str, ReconciliationPosition]``. Both the
        absolute share count and the side travel end-to-end. Session 2a
        does NOT add side-aware orphan-detection branches — that lands in
        Session 2b.1; this session is the typed-contract refactor only.
        The existing ARGUS-orphan branch (internal > 0, broker == 0)
        behavior is preserved.

        Args:
            broker_positions: Dict of {symbol: ReconciliationPosition} from
                the broker (built at the call site in ``main.py``).

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
            broker_pos = broker_positions.get(symbol)
            if broker_pos is not None and broker_pos.shares > 0:
                self._reconciliation_miss_count[symbol] = 0

        # Check all symbols in either set
        all_symbols = set(internal_positions.keys()) | set(broker_positions.keys())
        for symbol in sorted(all_symbols):
            internal_qty = internal_positions.get(symbol, 0)
            broker_pos = broker_positions.get(symbol)
            broker_qty = broker_pos.shares if broker_pos is not None else 0
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

        # Sprint 31.91 Session 2b.1 (D5): broker-orphan branch.
        # Dispatch by side: SHORT → CRITICAL phantom_short alert (DEF-204
        # detection signal); LONG → cycle-counter increment + cycle-1/2
        # WARNING / cycle ≥3 stranded_broker_long alert with M2 exp-backoff.
        # Branch-ordering note: SHORT branch fires before any state-pruning
        # logic so the unbounded-risk path takes the alert-emission path
        # regardless of counter state. Broker-confirmed positions are never
        # in this branch by construction (they live in ``_managed_positions``,
        # which the ``symbol in self._managed_positions: continue`` guard
        # filters first), preserving DEC-369 / DEC-370 immunity.
        for symbol, recon_pos in broker_positions.items():
            if symbol in self._managed_positions:
                continue  # not an orphan — managed position exists
            if recon_pos.side == OrderSide.SELL:
                await self._handle_broker_orphan_short(symbol, recon_pos)
                # Reset the long counter for safety (symbol could flip in
                # pathological cases).
                self._broker_orphan_long_cycles.pop(symbol, None)
                self._broker_orphan_last_alerted_cycle.pop(symbol, None)
            elif recon_pos.side == OrderSide.BUY:
                cycle = self._broker_orphan_long_cycles.get(symbol, 0) + 1
                self._broker_orphan_long_cycles[symbol] = cycle
                await self._handle_broker_orphan_long(symbol, recon_pos, cycle)
            else:
                # Defensive: ReconciliationPosition.__post_init__ rejects
                # None, so this branch is unreachable in practice.
                logger.error(
                    "Broker-orphan with unrecognized side for %s: side=%r. "
                    "ReconciliationPosition __post_init__ should have "
                    "rejected this.",
                    symbol,
                    recon_pos.side,
                )

        # Cleanup on broker-zero (M2): clear long-cycle counters for
        # symbols that are no longer in ``broker_positions`` (orphan
        # resolved at broker side). This runs every reconciliation cycle.
        resolved_symbols = (
            set(self._broker_orphan_long_cycles.keys())
            - set(broker_positions.keys())
        )
        for symbol in resolved_symbols:
            self._broker_orphan_long_cycles.pop(symbol, None)
            self._broker_orphan_last_alerted_cycle.pop(symbol, None)
            logger.info(
                "Broker-orphan LONG resolved (broker reports zero): %s",
                symbol,
            )

        # Sprint 31.91 Session 2c.2 (D5, M4): auto-clear logic for the
        # phantom_short entry gate. For each gated symbol, observe broker
        # state this cycle:
        #   - broker reports SHORT  -> reset clear-counter (re-detection;
        #     prevents stuttering near-clear/re-engage cycles).
        #   - broker reports zero   -> increment clear-counter; clear gate
        #     if counter reaches the configured threshold.
        #   - broker reports LONG   -> increment clear-counter (original
        #     phantom-short condition has resolved); clear gate at threshold.
        # Snapshot the gated set before iterating so the clear-path mutation
        # below cannot raise RuntimeError on set-changed-during-iteration.
        clear_threshold = (
            self._reconciliation_config.broker_orphan_consecutive_clear_threshold
        )
        gated_to_clear: list[str] = []
        for symbol in list(self._phantom_short_gated_symbols):
            broker_pos = broker_positions.get(symbol)
            broker_is_short = (
                broker_pos is not None and broker_pos.side == OrderSide.SELL
            )
            if broker_is_short:
                # Re-detection — RESET the clear counter so a transient
                # broker-zero observation cannot count toward auto-clear
                # while the phantom short is still active at the broker.
                if symbol in self._phantom_short_clear_cycles:
                    self._phantom_short_clear_cycles.pop(symbol)
                    logger.info(
                        "Phantom-short gate clear-counter RESET for %s "
                        "(broker still reports short; counter back to 0).",
                        symbol,
                    )
                continue  # gate stays engaged
            current = self._phantom_short_clear_cycles.get(symbol, 0) + 1
            self._phantom_short_clear_cycles[symbol] = current
            if broker_pos is None:
                logger.info(
                    "Phantom-short gate clear-counter for %s: cycle %d/%d "
                    "(broker reports zero shares).",
                    symbol,
                    current,
                    clear_threshold,
                )
            else:
                # broker_pos.side == OrderSide.BUY — LONG. Original phantom
                # short has resolved (operator may have flattened then a
                # legitimate long entered, or another path created it).
                logger.info(
                    "Phantom-short gate clear-counter for %s: cycle %d/%d "
                    "(broker reports LONG shares=%d, not short).",
                    symbol,
                    current,
                    clear_threshold,
                    broker_pos.shares,
                )
            if current >= clear_threshold:
                gated_to_clear.append(symbol)

        for symbol in gated_to_clear:
            self._phantom_short_gated_symbols.discard(symbol)
            self._phantom_short_clear_cycles.pop(symbol, None)
            # Persist the removal. Fire-and-forget so reconciliation isn't
            # blocked; if the write fails, the next reconciliation cycle
            # would re-detect any still-active phantom short and re-engage.
            persist_task = asyncio.create_task(
                self._remove_gated_symbol_from_db(symbol)
            )
            self._pending_gate_persist_tasks.add(persist_task)

            def _on_persist_done(t: "asyncio.Task[None]", _sym: str = symbol) -> None:
                self._pending_gate_persist_tasks.discard(t)
                _log_persist_task_exception(t, _sym)

            persist_task.add_done_callback(_on_persist_done)
            logger.warning(
                "Phantom-short gate AUTO-CLEARED for %s after %d consecutive "
                "broker-non-short cycles. Symbol may now receive new entries. "
                "If this clearance is in error, re-detection via reconciliation "
                "will re-engage the gate automatically once the phantom short "
                "reappears at the broker.",
                symbol,
                clear_threshold,
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
