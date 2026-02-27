"""Performance analytics routes for the Command Center API.

Provides endpoints for performance metrics, statistics, and reports.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Literal
from zoneinfo import ZoneInfo

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
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


# --- Heatmap Models ---


class HeatmapCell(BaseModel):
    """Single cell in the trade activity heatmap."""

    hour: int  # 9-15 (ET hour)
    day_of_week: int  # 0=Mon, 4=Fri
    trade_count: int
    avg_r_multiple: float
    net_pnl: float


class HeatmapResponse(BaseModel):
    """Response for GET /performance/heatmap."""

    cells: list[HeatmapCell]
    period: str
    timestamp: str


# --- Distribution Models ---


class DistributionBin(BaseModel):
    """Single bin in the R-multiple distribution histogram."""

    range_min: float  # e.g., -1.0
    range_max: float  # e.g., -0.75
    count: int
    avg_pnl: float


class DistributionResponse(BaseModel):
    """Response for GET /performance/distribution."""

    bins: list[DistributionBin]
    total_trades: int
    mean_r: float
    median_r: float
    period: str
    timestamp: str


# --- Correlation Models ---


class CorrelationResponse(BaseModel):
    """Response for GET /performance/correlation."""

    strategy_ids: list[str]
    matrix: list[list[float]]  # NxN correlation matrix
    period: str
    data_days: int
    message: str | None = None  # Set if insufficient data
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


# --- Specific routes must come BEFORE the /{period} catch-all route ---


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    period: Literal["today", "week", "month", "all"] = Query(default="month"),
    strategy_id: str | None = Query(default=None, description="Filter by strategy ID"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> HeatmapResponse:
    """Get trade activity heatmap by hour of day and day of week.

    Returns a grid of cells where each cell represents trades in a specific
    (hour, day_of_week) bucket with average R-multiple and net P&L.

    Args:
        period: Time period to analyze (today, week, month, all).
        strategy_id: Optional filter to get heatmap for a specific strategy only.

    Returns:
        HeatmapResponse with cells grouped by hour (9-15 ET) and day (Mon-Fri).
    """
    # Get current time in ET for date calculations
    now_utc = state.clock.now() if state.clock is not None else datetime.now(UTC)
    now_et = now_utc.astimezone(ET_TZ)

    # Get date range
    try:
        date_from, date_to = _get_date_range(period, now_et)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Fetch all trades for the period
    trades = await state.trade_logger.query_trades(
        strategy_id=strategy_id,
        date_from=date_from,
        date_to=date_to,
        limit=10000,
        offset=0,
    )

    # Group trades by (hour, day_of_week)
    # Key: (hour, day_of_week), Value: list of {r_multiple, net_pnl}
    buckets: dict[tuple[int, int], list[dict]] = defaultdict(list)

    for trade in trades:
        entry_time_str = trade.get("entry_time")
        if not entry_time_str:
            continue

        # Parse entry time and convert to ET
        entry_time = datetime.fromisoformat(entry_time_str)
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=UTC)
        entry_et = entry_time.astimezone(ET_TZ)

        hour = entry_et.hour
        day_of_week = entry_et.weekday()  # 0=Mon, 4=Fri

        # Only include market hours (9-16) and weekdays (0-4)
        if 9 <= hour <= 15 and 0 <= day_of_week <= 4:
            r_multiple = trade.get("r_multiple", 0.0) or 0.0
            net_pnl = trade.get("net_pnl", 0.0) or 0.0
            buckets[(hour, day_of_week)].append({
                "r_multiple": r_multiple,
                "net_pnl": net_pnl,
            })

    # Build cells from buckets
    cells: list[HeatmapCell] = []
    for (hour, day_of_week), bucket_trades in buckets.items():
        trade_count = len(bucket_trades)
        avg_r = sum(t["r_multiple"] for t in bucket_trades) / trade_count if trade_count > 0 else 0.0
        total_pnl = sum(t["net_pnl"] for t in bucket_trades)

        cells.append(HeatmapCell(
            hour=hour,
            day_of_week=day_of_week,
            trade_count=trade_count,
            avg_r_multiple=round(avg_r, 2),
            net_pnl=round(total_pnl, 2),
        ))

    return HeatmapResponse(
        cells=cells,
        period=period,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/distribution", response_model=DistributionResponse)
async def get_distribution(
    period: Literal["today", "week", "month", "all"] = Query(default="month"),
    strategy_id: str | None = Query(default=None, description="Filter by strategy ID"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> DistributionResponse:
    """Get R-multiple distribution histogram.

    Returns trade outcomes binned by R-multiple in 0.25R increments from -3R to +4R.

    Args:
        period: Time period to analyze (today, week, month, all).
        strategy_id: Optional filter to get distribution for a specific strategy only.

    Returns:
        DistributionResponse with bins, total trades, mean R, and median R.
    """
    # Get current time in ET for date calculations
    now_utc = state.clock.now() if state.clock is not None else datetime.now(UTC)
    now_et = now_utc.astimezone(ET_TZ)

    # Get date range
    try:
        date_from, date_to = _get_date_range(period, now_et)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Fetch all trades for the period
    trades = await state.trade_logger.query_trades(
        strategy_id=strategy_id,
        date_from=date_from,
        date_to=date_to,
        limit=10000,
        offset=0,
    )

    # Extract R-multiples
    r_multiples: list[float] = []
    r_with_pnl: dict[float, list[float]] = defaultdict(list)  # bin -> list of pnls

    # Define bins: -3R to +4R in 0.25R increments (28 bins)
    bin_edges = [round(-3.0 + i * 0.25, 2) for i in range(29)]  # 29 edges = 28 bins

    for trade in trades:
        r = trade.get("r_multiple")
        pnl = trade.get("net_pnl", 0.0) or 0.0
        if r is not None:
            r_multiples.append(r)
            # Find bin for this R-multiple
            for i in range(len(bin_edges) - 1):
                if bin_edges[i] <= r < bin_edges[i + 1]:
                    r_with_pnl[i].append(pnl)
                    break
            else:
                # Handle values >= 4R (put in last bin)
                if r >= bin_edges[-1]:
                    r_with_pnl[len(bin_edges) - 2].append(pnl)

    # Build distribution bins
    bins: list[DistributionBin] = []
    for i in range(len(bin_edges) - 1):
        pnls = r_with_pnl.get(i, [])
        count = len(pnls)
        avg_pnl = sum(pnls) / count if count > 0 else 0.0

        bins.append(DistributionBin(
            range_min=bin_edges[i],
            range_max=bin_edges[i + 1],
            count=count,
            avg_pnl=round(avg_pnl, 2),
        ))

    # Compute summary statistics
    total_trades = len(r_multiples)
    mean_r = sum(r_multiples) / total_trades if total_trades > 0 else 0.0
    median_r = median(r_multiples) if r_multiples else 0.0

    return DistributionResponse(
        bins=bins,
        total_trades=total_trades,
        mean_r=round(mean_r, 2),
        median_r=round(median_r, 2),
        period=period,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/correlation", response_model=CorrelationResponse)
async def get_correlation(
    period: Literal["today", "week", "month", "all"] = Query(default="month"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> CorrelationResponse:
    """Get strategy return correlation matrix.

    Computes pairwise correlation between strategy daily returns using numpy.corrcoef.
    Requires at least 5 trading days with data to compute meaningful correlations.

    Args:
        period: Time period to analyze (today, week, month, all).

    Returns:
        CorrelationResponse with strategy IDs and NxN correlation matrix.
        If insufficient data (<5 days), returns empty matrix with message.
    """
    # Get current time in ET for date calculations
    now_utc = state.clock.now() if state.clock is not None else datetime.now(UTC)
    now_et = now_utc.astimezone(ET_TZ)

    # Get date range
    try:
        date_from, date_to = _get_date_range(period, now_et)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    # Fetch daily P&L by strategy
    daily_pnl_data = await state.trade_logger.get_daily_pnl_by_strategy(
        date_from=date_from,
        date_to=date_to,
    )

    # Pivot: {date: {strategy_id: pnl}}
    daily_returns: dict[str, dict[str, float]] = defaultdict(dict)
    strategy_ids_set: set[str] = set()

    for row in daily_pnl_data:
        date = row["date"]
        strategy_id = row["strategy_id"]
        pnl = row["pnl"]
        daily_returns[date][strategy_id] = pnl
        strategy_ids_set.add(strategy_id)

    # Sort strategy IDs for consistent ordering
    strategy_ids = sorted(strategy_ids_set)
    dates = sorted(daily_returns.keys())
    data_days = len(dates)

    # Need at least 5 days with data for meaningful correlation
    if data_days < 5 or len(strategy_ids) < 2:
        return CorrelationResponse(
            strategy_ids=strategy_ids,
            matrix=[],
            period=period,
            data_days=data_days,
            message="Insufficient data for correlation analysis (need at least 5 trading days with 2+ strategies)",
            timestamp=datetime.now(UTC).isoformat(),
        )

    # Build returns matrix: rows = strategies, cols = dates
    # Fill missing days with 0 (no trading that day for that strategy)
    returns_matrix: list[list[float]] = []
    for strat_id in strategy_ids:
        strat_returns = [daily_returns[date].get(strat_id, 0.0) for date in dates]
        returns_matrix.append(strat_returns)

    # Compute correlation matrix using numpy
    returns_array = np.array(returns_matrix)
    corr_matrix = np.corrcoef(returns_array)

    # Handle NaN values (can occur if a strategy has zero variance)
    corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)

    # Convert to list of lists with rounding
    matrix = [[round(float(v), 3) for v in row] for row in corr_matrix]

    return CorrelationResponse(
        strategy_ids=strategy_ids,
        matrix=matrix,
        period=period,
        data_days=data_days,
        message=None,
        timestamp=datetime.now(UTC).isoformat(),
    )


# --- Generic period route must come AFTER specific routes ---


@router.get("/{period}", response_model=PerformanceResponse)
async def get_performance(
    period: Literal["today", "week", "month", "all"],
    strategy_id: str | None = Query(default=None, description="Filter by strategy ID"),
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
        strategy_id: Optional filter to get metrics for a specific strategy only.

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
        strategy_id=strategy_id,
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
        strategy_id=strategy_id,
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
        strat_id = trade.get("strategy_id", "unknown")
        if strat_id not in strategy_trades:
            strategy_trades[strat_id] = []
        strategy_trades[strat_id].append(trade)

    by_strategy: dict[str, StrategyMetrics] = {}
    for strat_id, strat_trades in strategy_trades.items():
        strat_metrics = compute_metrics(strat_trades)
        by_strategy[strat_id] = StrategyMetrics(
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
