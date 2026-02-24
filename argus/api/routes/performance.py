"""Performance analytics routes for the Command Center API.

Provides endpoints for performance metrics, statistics, and reports.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from argus.analytics.performance import PerformanceMetrics, compute_metrics
from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()

ET_TZ = ZoneInfo("America/New_York")


class MetricsData(BaseModel):
    """Performance metrics for a period."""

    total_trades: int
    win_rate: float
    profit_factor: float
    net_pnl: float
    gross_pnl: float
    total_commissions: float
    avg_r_multiple: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_hold_seconds: float
    largest_win: float
    largest_loss: float
    consecutive_wins_max: int
    consecutive_losses_max: int


class StrategyMetrics(BaseModel):
    """Abbreviated metrics for per-strategy breakdown."""

    total_trades: int
    win_rate: float
    net_pnl: float
    profit_factor: float


class DailyPnlEntry(BaseModel):
    """Single day's P&L entry."""

    date: str
    pnl: float
    trades: int


class PerformanceResponse(BaseModel):
    """Response for GET /performance/{period}."""

    period: str
    date_from: str
    date_to: str
    metrics: MetricsData
    daily_pnl: list[DailyPnlEntry]
    by_strategy: dict[str, StrategyMetrics]
    timestamp: str


def _metrics_to_data(metrics: PerformanceMetrics) -> MetricsData:
    """Convert PerformanceMetrics to MetricsData response model."""
    return MetricsData(
        total_trades=metrics.total_trades,
        win_rate=metrics.win_rate,
        profit_factor=metrics.profit_factor if metrics.profit_factor != float("inf") else 0.0,
        net_pnl=metrics.net_pnl,
        gross_pnl=metrics.gross_pnl,
        total_commissions=metrics.total_commissions,
        avg_r_multiple=metrics.avg_r_multiple,
        sharpe_ratio=metrics.sharpe_ratio,
        max_drawdown_pct=metrics.max_drawdown_pct,
        avg_hold_seconds=metrics.avg_hold_seconds,
        largest_win=metrics.largest_win,
        largest_loss=metrics.largest_loss,
        consecutive_wins_max=metrics.consecutive_wins_max,
        consecutive_losses_max=metrics.consecutive_losses_max,
    )


def _get_date_range(
    period: str,
    now_et: datetime,
) -> tuple[str | None, str | None]:
    """Get date range for a period.

    Args:
        period: One of "today", "week", "month", "all".
        now_et: Current time in ET timezone.

    Returns:
        Tuple of (date_from, date_to) as ISO date strings, or (None, None) for "all".
    """
    today = now_et.date()

    if period == "today":
        date_str = today.isoformat()
        return date_str, date_str
    elif period == "week":
        # Monday of current week
        monday = today - timedelta(days=today.weekday())
        return monday.isoformat(), today.isoformat()
    elif period == "month":
        # First of current month
        first_of_month = today.replace(day=1)
        return first_of_month.isoformat(), today.isoformat()
    elif period == "all":
        return None, None
    else:
        raise ValueError(f"Invalid period: {period}")


@router.get("/{period}", response_model=PerformanceResponse)
async def get_performance(
    period: Literal["today", "week", "month", "all"],
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> PerformanceResponse:
    """Get performance metrics for a time period.

    Computes trading performance statistics for the specified period.

    Args:
        period: Time period to analyze:
            - "today": Current trading day
            - "week": Monday to today
            - "month": 1st of month to today
            - "all": All-time (no date filter)

    Returns:
        PerformanceResponse with metrics, daily P&L, and per-strategy breakdown.

    Raises:
        HTTPException 422: If period is invalid.
    """
    # Get current time in ET for date calculations
    now_utc = state.clock.now() if state.clock is not None else datetime.now(UTC)
    now_et = now_utc.astimezone(ET_TZ)

    # Get date range
    try:
        date_from, date_to = _get_date_range(period, now_et)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Fetch trades for the period (use high limit to get all)
    trades = await state.trade_logger.query_trades(
        date_from=date_from,
        date_to=date_to,
        limit=10000,
        offset=0,
    )

    # Compute overall metrics
    overall_metrics = compute_metrics(trades)

    # Fetch daily P&L
    daily_pnl_data = await state.trade_logger.get_daily_pnl(
        date_from=date_from,
        date_to=date_to,
    )
    daily_pnl = [
        DailyPnlEntry(
            date=row["date"],
            pnl=row["pnl"],
            trades=row["trades"],
        )
        for row in daily_pnl_data
    ]

    # Build per-strategy breakdown
    strategy_trades: dict[str, list[dict]] = {}
    for trade in trades:
        strategy_id = trade.get("strategy_id", "unknown")
        if strategy_id not in strategy_trades:
            strategy_trades[strategy_id] = []
        strategy_trades[strategy_id].append(trade)

    by_strategy: dict[str, StrategyMetrics] = {}
    for strategy_id, strat_trades in strategy_trades.items():
        strat_metrics = compute_metrics(strat_trades)
        by_strategy[strategy_id] = StrategyMetrics(
            total_trades=strat_metrics.total_trades,
            win_rate=strat_metrics.win_rate,
            net_pnl=strat_metrics.net_pnl,
            profit_factor=(
                strat_metrics.profit_factor if strat_metrics.profit_factor != float("inf") else 0.0
            ),
        )

    # Build response
    return PerformanceResponse(
        period=period,
        date_from=date_from or "",
        date_to=date_to or "",
        metrics=_metrics_to_data(overall_metrics),
        daily_pnl=daily_pnl,
        by_strategy=by_strategy,
        timestamp=datetime.now(UTC).isoformat(),
    )
