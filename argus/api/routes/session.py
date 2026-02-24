"""Session summary routes for the Command Center API.

Provides endpoints for retrieving end-of-day session summaries including
trade statistics, best/worst trades, and active strategies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class TradeHighlight(BaseModel):
    """Highlighted trade (best or worst)."""

    symbol: str
    r_multiple: float
    pnl_dollars: float
    strategy_id: str


class SessionSummaryResponse(BaseModel):
    """Session summary response for a trading day."""

    date: str
    trade_count: int
    wins: int
    losses: int
    breakeven: int
    net_pnl: float
    win_rate: float
    best_trade: TradeHighlight | None
    worst_trade: TradeHighlight | None
    fill_rate: float
    regime: str | None
    active_strategies: list[str]
    timestamp: str


@router.get("/session-summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    date_param: str | None = Query(
        None,
        alias="date",
        description="Date in YYYY-MM-DD format. Defaults to today (ET).",
    ),
) -> SessionSummaryResponse:
    """Get session summary for a trading day.

    Returns trade statistics, best/worst trades, regime, and active strategies
    for the specified date (or today if not specified).

    Args:
        date_param: Optional date in YYYY-MM-DD format. Defaults to today (ET).

    Returns:
        SessionSummaryResponse with day's trading statistics.
    """
    # Determine the date to query (default to today in ET)
    if date_param is not None:
        query_date = date_param
    else:
        et_tz = ZoneInfo("America/New_York")
        query_date = datetime.now(et_tz).date().isoformat()

    # Query trades for the date
    trades = await state.trade_logger.get_trades_by_date(query_date)

    # Calculate statistics
    trade_count = len(trades)
    wins = sum(1 for t in trades if t.net_pnl > 0)
    losses = sum(1 for t in trades if t.net_pnl < 0)
    breakeven = sum(1 for t in trades if t.net_pnl == 0)
    net_pnl = sum(t.net_pnl for t in trades)
    win_rate = wins / trade_count if trade_count > 0 else 0.0

    # Find best and worst trades by R-multiple
    best_trade: TradeHighlight | None = None
    worst_trade: TradeHighlight | None = None

    if trades:
        best = max(trades, key=lambda t: t.r_multiple)
        worst = min(trades, key=lambda t: t.r_multiple)

        best_trade = TradeHighlight(
            symbol=best.symbol,
            r_multiple=best.r_multiple,
            pnl_dollars=best.net_pnl,
            strategy_id=best.strategy_id,
        )
        worst_trade = TradeHighlight(
            symbol=worst.symbol,
            r_multiple=worst.r_multiple,
            pnl_dollars=worst.net_pnl,
            strategy_id=worst.strategy_id,
        )

    # Fill rate: For now, estimate as 100% since we don't track unfilled signals
    # In the future, this could compare SignalEvents emitted vs trades logged
    fill_rate = 1.0

    # Get regime from orchestrator (if available)
    regime: str | None = None
    if state.orchestrator is not None:
        regime = state.orchestrator.current_regime.value

    # Get active strategies
    active_strategies = list(state.strategies.keys())

    return SessionSummaryResponse(
        date=query_date,
        trade_count=trade_count,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        net_pnl=net_pnl,
        win_rate=win_rate,
        best_trade=best_trade,
        worst_trade=worst_trade,
        fill_rate=fill_rate,
        regime=regime,
        active_strategies=active_strategies,
        timestamp=datetime.now(UTC).isoformat(),
    )
