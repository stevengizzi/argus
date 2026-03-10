"""Event definitions for the Argus event system.

All inter-component communication flows through typed events on the Event Bus.
Events are immutable dataclasses. The `sequence` field is assigned by the
Event Bus at publish time — never set it manually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

# ET timezone for intelligence layer (DEC-276)
_ET = ZoneInfo("America/New_York")

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Side(StrEnum):
    """Trade direction."""

    LONG = "long"
    SHORT = "short"


class OrderType(StrEnum):
    """Order type for broker submission."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class ExitReason(StrEnum):
    """Why a position was closed."""

    TARGET_1 = "target_1"
    TARGET_2 = "target_2"
    TARGET_3 = "target_3"
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TIME_STOP = "time_stop"
    EOD_FLATTEN = "eod"
    MANUAL = "manual"
    CIRCUIT_BREAKER = "circuit_breaker"
    EMERGENCY = "emergency"


class CircuitBreakerLevel(StrEnum):
    """Which level triggered the circuit breaker."""

    STRATEGY = "strategy"
    CROSS_STRATEGY = "cross_strategy"
    ACCOUNT = "account"


class SystemStatus(StrEnum):
    """Overall system health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    SAFE_MODE = "safe_mode"


# ---------------------------------------------------------------------------
# Base Event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """Base event class. All events inherit from this.

    Attributes:
        sequence: Monotonic sequence number assigned by EventBus at publish time.
            Do not set this manually — pass 0 and the EventBus will overwrite it.
        timestamp: When the event was created (UTC).
    """

    sequence: int = field(default=0)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Market Data Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandleEvent(Event):
    """A completed candle at a specific timeframe."""

    symbol: str = ""
    timeframe: str = ""  # "1s", "5s", "1m", "5m", "15m"
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0


@dataclass(frozen=True)
class TickEvent(Event):
    """A single price update (trade or quote)."""

    symbol: str = ""
    price: float = 0.0
    volume: int = 0


@dataclass(frozen=True)
class IndicatorEvent(Event):
    """A computed indicator value update."""

    symbol: str = ""
    indicator_name: str = ""  # "vwap", "atr_14", "rvol", "sma_20", etc.
    value: float = 0.0


# ---------------------------------------------------------------------------
# Scanner Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WatchlistItem:
    """A single stock on the scanner watchlist with metadata."""

    symbol: str = ""
    gap_pct: float = 0.0
    premarket_volume: int = 0
    float_shares: int = 0
    catalyst: str = ""
    scan_source: str = ""  # e.g., "fmp", "static", "fmp_fallback"
    selection_reason: str = ""  # e.g., "gap_up_3.2%", "gap_down_1.8%", "high_volume"


@dataclass(frozen=True)
class WatchlistEvent(Event):
    """Pre-market scanner results — the day's watchlist."""

    date: str = ""  # YYYY-MM-DD
    symbols: tuple[WatchlistItem, ...] = ()


# ---------------------------------------------------------------------------
# Strategy Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalEvent(Event):
    """A trade signal emitted by a strategy."""

    strategy_id: str = ""
    symbol: str = ""
    side: Side = Side.LONG
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_prices: tuple[float, ...] = ()
    share_count: int = 0
    rationale: str = ""
    time_stop_seconds: int | None = None


# ---------------------------------------------------------------------------
# Risk Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderApprovedEvent(Event):
    """Risk Manager approved a signal (possibly with modifications)."""

    signal: SignalEvent | None = None
    modifications: dict[str, Any] | None = None


@dataclass(frozen=True)
class OrderRejectedEvent(Event):
    """Risk Manager rejected a signal."""

    signal: SignalEvent | None = None
    reason: str = ""


# ---------------------------------------------------------------------------
# Execution Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderSubmittedEvent(Event):
    """An order has been submitted to the broker."""

    order_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    side: Side = Side.LONG
    quantity: int = 0
    order_type: OrderType = OrderType.MARKET


@dataclass(frozen=True)
class OrderFilledEvent(Event):
    """An order has been filled (partially or fully)."""

    order_id: str = ""
    fill_price: float = 0.0
    fill_quantity: int = 0


@dataclass(frozen=True)
class OrderCancelledEvent(Event):
    """An order has been cancelled."""

    order_id: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Position Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionOpenedEvent(Event):
    """A new position has been opened."""

    position_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    entry_price: float = 0.0
    shares: int = 0
    stop_price: float = 0.0
    target_prices: tuple[float, ...] = ()


@dataclass(frozen=True)
class PositionUpdatedEvent(Event):
    """An existing position's state has changed."""

    position_id: str = ""
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    stop_updated_to: float | None = None


@dataclass(frozen=True)
class PositionClosedEvent(Event):
    """A position has been fully closed."""

    position_id: str = ""
    strategy_id: str = ""
    symbol: str = ""
    exit_price: float = 0.0
    realized_pnl: float = 0.0
    exit_reason: ExitReason = ExitReason.MANUAL
    hold_duration_seconds: int = 0
    # Optional because not all PositionClosedEvent publishers have timing data
    # during early development. The Order Manager (Sprint 4) will always populate
    # these. PDT tracking silently skips events without timestamps.
    entry_time: datetime | None = None
    exit_time: datetime | None = None


# ---------------------------------------------------------------------------
# System Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CircuitBreakerEvent(Event):
    """A circuit breaker has been triggered."""

    level: CircuitBreakerLevel = CircuitBreakerLevel.ACCOUNT
    reason: str = ""
    strategies_affected: tuple[str, ...] = ()


@dataclass(frozen=True)
class HeartbeatEvent(Event):
    """Periodic system health signal."""

    system_status: SystemStatus = SystemStatus.HEALTHY


@dataclass(frozen=True)
class RegimeChangeEvent(Event):
    """Market regime has changed."""

    old_regime: str = ""
    new_regime: str = ""
    indicators: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class CatalystEvent(Event):
    """A classified catalyst event for a symbol.

    Published by the intelligence layer after classifying a raw
    news item or SEC filing. Subscribers (strategies, UI) receive
    this to incorporate catalyst context into decisions.
    """

    symbol: str = ""
    catalyst_type: str = ""  # category from classification
    quality_score: float = 0.0  # 0-100
    headline: str = ""
    summary: str = ""
    source: str = ""  # "sec_edgar", "fmp_news", "finnhub"
    source_url: str | None = None
    filing_type: str | None = None
    # ET per DEC-276 (intelligence layer convention)
    published_at: datetime = field(default_factory=lambda: datetime.now(_ET))
    classified_at: datetime = field(default_factory=lambda: datetime.now(_ET))


@dataclass(frozen=True)
class ShutdownRequestedEvent(Event):
    """Request graceful system shutdown.

    Published after EOD flatten completes when auto_shutdown_after_eod is enabled.
    The main run loop listens for this event and initiates graceful shutdown.
    """

    reason: str = "eod_flatten_complete"
    delay_seconds: int = 60  # Delay before shutdown to allow final operations


# ---------------------------------------------------------------------------
# Data Feed Events (Sprint 12)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DataStaleEvent(Event):
    """Published when a data feed has not received messages for too long.

    Strategies should halt new entries when this event is received.
    Order Manager should NOT close existing positions — stale data
    does not mean positions are at risk, just that we can't make
    informed decisions about new entries.

    RSK-021 mitigation: Data feed failure during live trading.
    """

    provider: str = ""  # "databento", "alpaca", etc.
    seconds_since_last: float = 0.0


@dataclass(frozen=True)
class DataResumedEvent(Event):
    """Published when a previously stale data feed resumes.

    Strategies may resume normal operation after receiving this event.
    """

    provider: str = ""  # "databento", "alpaca", etc.


# ---------------------------------------------------------------------------
# Orchestrator Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AllocationUpdateEvent(Event):
    """Strategy capital allocation has changed."""

    strategy_id: str = ""
    new_allocation_pct: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class StrategyActivatedEvent(Event):
    """A strategy has been activated by the Orchestrator."""

    strategy_id: str = ""
    reason: str = ""


@dataclass(frozen=True)
class StrategySuspendedEvent(Event):
    """A strategy has been suspended by the Orchestrator."""

    strategy_id: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Approval Events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ApprovalRequestedEvent(Event):
    """An action requires human approval."""

    action_id: str = ""
    action_type: str = ""
    description: str = ""
    risk_level: str = "medium"  # "low", "medium", "high"


@dataclass(frozen=True)
class ApprovalGrantedEvent(Event):
    """Human approved an action."""

    action_id: str = ""


@dataclass(frozen=True)
class ApprovalDeniedEvent(Event):
    """Human denied an action."""

    action_id: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Universe Events (Sprint 23)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UniverseUpdateEvent(Event):
    """Published when the viable trading universe is rebuilt.

    Provides visibility into universe changes for logging and UI.
    Emitted by UniverseManager after build_viable_universe() completes.

    Attributes:
        viable_count: Number of symbols in the viable universe.
        total_fetched: Total symbols fetched before filtering.
    """

    viable_count: int = 0
    total_fetched: int = 0
