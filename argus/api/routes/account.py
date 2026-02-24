"""Account routes for the Command Center API.

Provides the account overview endpoint with equity, P&L, and market status.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.execution.simulated_broker import SimulatedBroker

router = APIRouter()


class AccountResponse(BaseModel):
    """Account overview response."""

    equity: float
    cash: float
    buying_power: float
    daily_pnl: float
    daily_pnl_pct: float
    open_positions_count: int
    daily_trades_count: int
    market_status: str
    broker_source: str
    data_source: str
    timestamp: str


def get_market_status(clock_now: datetime | None = None) -> str:
    """Determine current market status based on ET time.

    Args:
        clock_now: Optional datetime to use instead of current time.
                   Should be timezone-aware. If None, uses system time.

    Returns:
        One of: "pre_market", "open", "closed", "after_hours"
    """
    et_tz = ZoneInfo("America/New_York")

    if clock_now is not None:
        # Convert to ET if needed
        if clock_now.tzinfo is not None:
            now_et = clock_now.astimezone(et_tz)
        else:
            now_et = clock_now.replace(tzinfo=et_tz)
    else:
        now_et = datetime.now(et_tz)

    # Weekend check
    if now_et.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return "closed"

    current_time = now_et.time()

    # Market hours (ET):
    # Pre-market: 4:00 - 9:30
    # Market open: 9:30 - 16:00
    # After hours: 16:00 - 20:00
    # Closed: 20:00 - 4:00

    pre_market_start = time(4, 0)
    market_open = time(9, 30)
    market_close = time(16, 0)
    after_hours_end = time(20, 0)

    if pre_market_start <= current_time < market_open:
        return "pre_market"
    elif market_open <= current_time < market_close:
        return "open"
    elif market_close <= current_time < after_hours_end:
        return "after_hours"
    else:
        return "closed"


@router.get("/account", response_model=AccountResponse)
async def get_account(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> AccountResponse:
    """Get account overview with equity, P&L, and market status.

    Returns current account information including:
    - Equity, cash, buying power from broker
    - Today's P&L from trade logger
    - Open position count from order manager
    - Market status (pre_market, open, closed, after_hours)
    - Configured broker and data sources
    """
    # Get account info from broker
    account_info = await state.broker.get_account()

    equity = account_info.equity
    cash = account_info.cash
    buying_power = account_info.buying_power

    # In dev mode (SimulatedBroker), add small random variations
    # to test AnimatedNumber component
    is_dev_mode = isinstance(state.broker, SimulatedBroker)
    if is_dev_mode:
        # Add ±0.5% variation to equity and cash
        equity_variation = equity * random.uniform(-0.005, 0.005)
        cash_variation = cash * random.uniform(-0.003, 0.003)
        equity += equity_variation
        cash += cash_variation
        buying_power = cash * 2  # Margin account

    # Get today's P&L and trade count from trade logger
    daily_pnl = await state.trade_logger.get_todays_pnl()
    if is_dev_mode:
        # Add variation to P&L for testing flash animation
        daily_pnl += random.uniform(-50, 50)
    daily_trades_count = await state.trade_logger.get_todays_trade_count()

    # Calculate daily P&L percentage
    daily_pnl_pct = (daily_pnl / equity * 100) if equity > 0 else 0.0

    # Get open positions count from order manager
    open_positions_count = len(state.order_manager.get_all_positions_flat())

    # Get market status using clock if available
    clock_now = state.clock.now() if state.clock else None
    market_status = get_market_status(clock_now)

    # Get broker and data source from config
    broker_source = "unknown"
    data_source = "unknown"
    if state.config:
        broker_source = state.config.broker_source.value
        data_source = state.config.data_source.value

    return AccountResponse(
        equity=equity,
        cash=cash,
        buying_power=buying_power,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        open_positions_count=open_positions_count,
        daily_trades_count=daily_trades_count,
        market_status=market_status,
        broker_source=broker_source,
        data_source=data_source,
        timestamp=datetime.now(UTC).isoformat(),
    )
