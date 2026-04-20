"""Shared data models used across the Argus system.

These are the canonical representations of trading objects. They are
Pydantic models for validation and serialization. Components that
need to exchange trading data use these types.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from argus.core.ids import generate_id

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AssetClass(StrEnum):
    """Supported asset classes."""

    US_STOCKS = "us_stocks"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"


class OrderSide(StrEnum):
    """Order direction."""

    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    """Order type for broker submission."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(StrEnum):
    """Current state of an order."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PositionStatus(StrEnum):
    """Current state of a position."""

    OPEN = "open"
    CLOSED = "closed"


class TradeOutcome(StrEnum):
    """Outcome of a completed trade."""

    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


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
    RECONCILIATION = "reconciliation"


# ---------------------------------------------------------------------------
# Order Models
# ---------------------------------------------------------------------------


class Order(BaseModel):
    """An order to be submitted to a broker."""

    id: str = Field(default_factory=generate_id)
    strategy_id: str
    symbol: str
    asset_class: AssetClass = AssetClass.US_STOCKS
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    quantity: int = Field(ge=1)
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: str = "day"  # 'day', 'gtc', 'ioc', 'fok'
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OrderResult(BaseModel):
    """Result from submitting an order to the broker."""

    order_id: str
    broker_order_id: str = ""
    status: OrderStatus = OrderStatus.SUBMITTED
    filled_quantity: int = 0
    filled_avg_price: float = 0.0
    message: str = ""


class BracketOrderResult(BaseModel):
    """Result from submitting a bracket order (entry + stop + targets)."""

    entry: OrderResult
    stop: OrderResult
    targets: list[OrderResult] = Field(default_factory=list)


class AccountInfo(BaseModel):
    """Snapshot of the brokerage account state.

    Attributes:
        equity: Total account equity (cash + positions value).
        cash: Available cash balance.
        buying_power: Available buying power for new orders.
        positions_value: Total value of open positions.
        daily_pnl: Realized P&L for today.
    """

    equity: float
    cash: float
    buying_power: float
    positions_value: float = 0.0
    daily_pnl: float = 0.0


# ---------------------------------------------------------------------------
# Position Model
# ---------------------------------------------------------------------------


class Position(BaseModel):
    """A tracked trading position."""

    id: str = Field(default_factory=generate_id)
    strategy_id: str
    symbol: str
    asset_class: AssetClass = AssetClass.US_STOCKS
    side: OrderSide
    status: PositionStatus = PositionStatus.OPEN
    entry_price: float
    entry_time: datetime
    shares: int = Field(ge=1)
    stop_price: float
    target_prices: list[float] = Field(default_factory=list)
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    exit_price: float | None = None
    exit_time: datetime | None = None
    exit_reason: ExitReason | None = None
    realized_pnl: float = 0.0


# ---------------------------------------------------------------------------
# Trade Model (completed trade for logging/analysis)
# ---------------------------------------------------------------------------


class Trade(BaseModel):
    """A completed trade record for logging and analysis."""

    id: str = Field(default_factory=generate_id)
    strategy_id: str
    symbol: str
    asset_class: AssetClass = AssetClass.US_STOCKS
    side: OrderSide
    entry_price: float
    entry_time: datetime
    exit_price: float
    exit_time: datetime
    shares: int = Field(ge=1)
    stop_price: float
    target_prices: list[float] = Field(default_factory=list)
    exit_reason: ExitReason
    gross_pnl: float
    commission: float = 0.0
    net_pnl: float = 0.0
    r_multiple: float = 0.0
    hold_duration_seconds: int = 0
    outcome: TradeOutcome = TradeOutcome.BREAKEVEN
    rationale: str = ""
    notes: str = ""
    quality_grade: str = ""
    quality_score: float = 0.0
    mfe_r: float | None = None
    mae_r: float | None = None
    mfe_price: float | None = None
    mae_price: float | None = None
    config_fingerprint: str | None = None
    entry_price_known: bool = True  # False when entry price unrecoverable (DEF-159)

    def model_post_init(self, __context: object) -> None:
        """Calculate derived fields after initialization."""
        # Calculate net P&L
        if self.net_pnl == 0.0:
            self.net_pnl = self.gross_pnl - self.commission

        # Calculate hold duration
        if self.hold_duration_seconds == 0:
            delta = self.exit_time - self.entry_time
            self.hold_duration_seconds = int(delta.total_seconds())

        # Calculate R-multiple
        if self.r_multiple == 0.0 and self.stop_price != self.entry_price:
            risk_per_share = abs(self.entry_price - self.stop_price)
            pnl_per_share = self.net_pnl / self.shares if self.shares > 0 else 0
            self.r_multiple = pnl_per_share / risk_per_share if risk_per_share > 0 else 0

        # Determine outcome
        if self.net_pnl > 0:
            self.outcome = TradeOutcome.WIN
        elif self.net_pnl < 0:
            self.outcome = TradeOutcome.LOSS
        else:
            self.outcome = TradeOutcome.BREAKEVEN


# ---------------------------------------------------------------------------
# Daily Summary Model
# ---------------------------------------------------------------------------


class DailySummary(BaseModel):
    """Daily trading summary for a strategy or the entire account."""

    date: str  # YYYY-MM-DD
    strategy_id: str | None = None  # None for account-wide summary
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    gross_pnl: float = 0.0
    commissions: float = 0.0
    net_pnl: float = 0.0
    avg_winner: float = 0.0
    avg_loser: float = 0.0
    largest_winner: float = 0.0
    largest_loser: float = 0.0
    avg_r_multiple: float = 0.0
    profit_factor: float = 0.0
