"""Trade history routes for the Command Center API.

Provides endpoints for querying trade history and details.
"""

from __future__ import annotations

import csv
import io
import json
import random
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class TradeResponse(BaseModel):
    """Single trade record."""

    id: str
    strategy_id: str
    symbol: str
    side: str
    entry_price: float
    entry_time: str
    exit_price: float | None
    exit_time: str | None
    shares: int
    pnl_dollars: float | None
    pnl_r_multiple: float | None
    exit_reason: str | None
    hold_duration_seconds: int | None
    commission: float
    market_regime: str | None
    stop_price: float | None = None
    target_prices: list[float] | None = None
    quality_grade: str | None = None
    quality_score: float | None = None


class TradesResponse(BaseModel):
    """Response for GET /trades with pagination."""

    trades: list[TradeResponse]
    total_count: int
    limit: int
    offset: int
    timestamp: str


class TradesBatchResponse(BaseModel):
    """Response for GET /trades/batch."""

    trades: list[TradeResponse]
    count: int
    timestamp: str


class TradeStatsResponse(BaseModel):
    """Aggregate stats for filtered trades."""

    total_trades: int
    wins: int
    losses: int
    win_rate: float
    net_pnl: float
    avg_r: float | None
    timestamp: str


@router.get("/stats", response_model=TradeStatsResponse)
async def get_trade_stats(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    strategy_id: str | None = Query(None, description="Filter by strategy ID"),
    date_from: str | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    outcome: Literal["win", "loss", "breakeven"] | None = Query(
        None, description="Filter by trade outcome"
    ),
) -> TradeStatsResponse:
    """Get aggregate statistics for filtered trades.

    Computes stats from the full filtered dataset server-side,
    avoiding the pagination limit that affects client-side computation.

    Args:
        strategy_id: Optional strategy filter.
        date_from: Optional start date (ISO YYYY-MM-DD).
        date_to: Optional end date (ISO YYYY-MM-DD).
        outcome: Optional outcome filter ("win", "loss", "breakeven").

    Returns:
        Aggregate trade statistics.
    """
    from argus.analytics.performance import compute_metrics

    # Query ALL matching trades — use count_trades() to get true total,
    # then fetch that exact count so metrics cover the full dataset.
    total_count = await state.trade_logger.count_trades(
        strategy_id=strategy_id,
        date_from=date_from,
        date_to=date_to,
        outcome=outcome,
    )

    trades_data = await state.trade_logger.query_trades(
        strategy_id=strategy_id,
        date_from=date_from,
        date_to=date_to,
        outcome=outcome,
        limit=max(total_count, 1),
        offset=0,
    )

    metrics = compute_metrics(trades_data)

    return TradeStatsResponse(
        total_trades=metrics.total_trades,
        wins=metrics.wins,
        losses=metrics.losses,
        win_rate=metrics.win_rate,
        net_pnl=metrics.net_pnl,
        avg_r=metrics.avg_r_multiple if metrics.total_trades > 0 else None,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("", response_model=TradesResponse)
async def get_trades(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    strategy_id: str | None = Query(None, description="Filter by strategy ID"),
    symbol: str | None = Query(None, description="Filter by symbol"),
    date_from: str | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date filter (YYYY-MM-DD)"),
    outcome: Literal["win", "loss", "breakeven"] | None = Query(
        None, description="Filter by trade outcome"
    ),
    limit: int = Query(50, ge=1, le=250, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> TradesResponse:
    """Get trade history with filtering and pagination.

    Query closed trades with optional filters:
    - strategy_id: Filter by specific strategy
    - symbol: Filter by symbol (e.g., AAPL)
    - date_from/date_to: Filter by entry date range
    - outcome: Filter by win/loss/breakeven

    Results are ordered by entry_time descending (most recent first).

    Args:
        strategy_id: Optional strategy filter.
        symbol: Optional symbol filter.
        date_from: Optional start date (ISO YYYY-MM-DD).
        date_to: Optional end date (ISO YYYY-MM-DD).
        outcome: Optional outcome filter ("win", "loss", "breakeven").
        limit: Maximum results per page (1-250, default 50).
        offset: Number of results to skip for pagination.

    Returns:
        Paginated list of trades with total count.
    """
    # Query trades with filters
    trades_data = await state.trade_logger.query_trades(
        strategy_id=strategy_id,
        symbol=symbol,
        date_from=date_from,
        date_to=date_to,
        outcome=outcome,
        limit=limit,
        offset=offset,
    )

    # Get total count for pagination
    total_count = await state.trade_logger.count_trades(
        strategy_id=strategy_id,
        symbol=symbol,
        date_from=date_from,
        date_to=date_to,
        outcome=outcome,
    )

    # Transform database rows to response format
    trades: list[TradeResponse] = []
    for row in trades_data:
        # Parse target_prices from JSON string
        target_prices_raw = row.get("target_prices")
        target_prices = (
            json.loads(target_prices_raw) if target_prices_raw else None
        )

        trades.append(
            TradeResponse(
                id=row["id"],
                strategy_id=row["strategy_id"],
                symbol=row["symbol"],
                side=row["side"],
                entry_price=row["entry_price"],
                entry_time=row["entry_time"],
                exit_price=row.get("exit_price"),
                exit_time=row.get("exit_time"),
                shares=row["shares"],
                pnl_dollars=row.get("net_pnl"),
                pnl_r_multiple=row.get("r_multiple"),
                exit_reason=row.get("exit_reason"),
                hold_duration_seconds=row.get("hold_duration_seconds"),
                commission=row.get("commission", 0.0),
                market_regime=row.get("market_regime"),
                stop_price=row.get("stop_price"),
                target_prices=target_prices,
                quality_grade=row.get("quality_grade") or None,
                quality_score=row.get("quality_score"),
            )
        )

    return TradesResponse(
        trades=trades,
        total_count=total_count,
        limit=limit,
        offset=offset,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/batch", response_model=TradesBatchResponse)
async def get_trades_batch(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    ids: str = Query(..., description="Comma-separated trade IDs"),
) -> TradesBatchResponse:
    """Get multiple trades by their IDs in a single request.

    Useful for fetching linked trades in journal entries without
    fetching the entire trade history.

    Args:
        ids: Comma-separated list of trade IDs (ULIDs).

    Returns:
        List of trades matching the provided IDs.
        Missing IDs are silently omitted from results.

    Raises:
        HTTPException: 400 if more than 50 IDs are requested.
    """
    # Parse comma-separated IDs
    trade_ids = [tid.strip() for tid in ids.split(",") if tid.strip()]

    if not trade_ids:
        return TradesBatchResponse(
            trades=[],
            count=0,
            timestamp=datetime.now(UTC).isoformat(),
        )

    if len(trade_ids) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 trade IDs per request",
        )

    # Fetch trades by IDs
    trades_data = await state.trade_logger.get_trades_by_ids(trade_ids)

    # Transform to response format
    trades: list[TradeResponse] = []
    for row in trades_data:
        # Parse target_prices from JSON string
        target_prices_raw = row.get("target_prices")
        target_prices = (
            json.loads(target_prices_raw) if target_prices_raw else None
        )

        trades.append(
            TradeResponse(
                id=row["id"],
                strategy_id=row["strategy_id"],
                symbol=row["symbol"],
                side=row["side"],
                entry_price=row["entry_price"],
                entry_time=row["entry_time"],
                exit_price=row.get("exit_price"),
                exit_time=row.get("exit_time"),
                shares=row["shares"],
                pnl_dollars=row.get("net_pnl"),
                pnl_r_multiple=row.get("r_multiple"),
                exit_reason=row.get("exit_reason"),
                hold_duration_seconds=row.get("hold_duration_seconds"),
                commission=row.get("commission", 0.0),
                market_regime=row.get("market_regime"),
                stop_price=row.get("stop_price"),
                target_prices=target_prices,
                quality_grade=row.get("quality_grade") or None,
                quality_score=row.get("quality_score"),
            )
        )

    return TradesBatchResponse(
        trades=trades,
        count=len(trades),
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/export/csv")
async def export_trades_csv(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    strategy_id: str | None = Query(None, description="Filter by strategy ID"),
    date_from: str | None = Query(None, description="Start date filter (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date filter (YYYY-MM-DD)"),
) -> StreamingResponse:
    """Export trades as a CSV file.

    Exports all trades matching the filters (no pagination limit).

    Args:
        strategy_id: Optional strategy filter.
        date_from: Optional start date (ISO YYYY-MM-DD).
        date_to: Optional end date (ISO YYYY-MM-DD).

    Returns:
        StreamingResponse with CSV content and download headers.
    """
    # Query ALL trades with filters (no limit/offset for export)
    trades_data = await state.trade_logger.query_trades(
        strategy_id=strategy_id,
        date_from=date_from,
        date_to=date_to,
        limit=10000,  # High limit for export
        offset=0,
    )

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow(
        [
            "id",
            "strategy_id",
            "symbol",
            "side",
            "entry_price",
            "entry_time",
            "exit_price",
            "exit_time",
            "shares",
            "pnl_dollars",
            "pnl_r_multiple",
            "exit_reason",
            "hold_duration_seconds",
            "commission",
        ]
    )

    # Write data rows
    for row in trades_data:
        writer.writerow(
            [
                row["id"],
                row["strategy_id"],
                row["symbol"],
                row["side"],
                row["entry_price"],
                row["entry_time"],
                row.get("exit_price", ""),
                row.get("exit_time", ""),
                row["shares"],
                row.get("net_pnl", ""),
                row.get("r_multiple", ""),
                row.get("exit_reason", ""),
                row.get("hold_duration_seconds", ""),
                row.get("commission", 0.0),
            ]
        )

    # Generate filename with date
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"argus_trades_{date_str}.csv"

    # Return as streaming response
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ---------------------------------------------------------------------------
# Trade Replay
# ---------------------------------------------------------------------------


class ReplayBar(BaseModel):
    """Single OHLCV bar for trade replay."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class TradeReplayResponse(BaseModel):
    """Response for trade replay with historical bars."""

    trade: TradeResponse
    bars: list[ReplayBar]
    entry_bar_index: int
    exit_bar_index: int | None
    vwap: list[float] | None
    timestamp: str


def _generate_synthetic_replay_bars(
    trade: dict,
    bar_count: int = 50,
) -> tuple[list[ReplayBar], int, int | None, list[float] | None]:
    """Generate synthetic 1-minute bars for a plausible trade scenario.

    Creates a realistic trade pattern:
    - Gap up at open
    - Consolidation in opening range (first 5 bars)
    - Breakout with volume surge (bar 15)
    - Run to target (bar 25-30)
    - Pullback/continuation

    Args:
        trade: Trade data dict with entry_price, stop_price, etc.
        bar_count: Number of bars to generate.

    Returns:
        Tuple of (bars, entry_bar_index, exit_bar_index, vwap_values).
    """
    entry_price = trade["entry_price"]
    stop_price = trade.get("stop_price") or entry_price * 0.99
    exit_price = trade.get("exit_price") or entry_price * 1.01
    entry_time_str = trade["entry_time"]
    exit_time_str = trade.get("exit_time")

    # Parse entry time
    entry_time = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
    # Start 15 bars before entry
    start_time = entry_time - timedelta(minutes=15)

    # Calculate price levels
    risk = entry_price - stop_price
    or_high = entry_price - risk * 0.1  # OR high just below entry
    or_low = stop_price + risk * 0.3  # OR low above stop
    pre_open_price = or_low - risk * 0.5  # Previous close

    bars: list[ReplayBar] = []
    vwap_values: list[float] = []
    entry_bar_idx = 15  # Bar 15 is entry
    exit_bar_idx: int | None = None

    # Track VWAP computation
    cum_volume = 0.0
    cum_pv = 0.0  # price * volume

    for i in range(bar_count):
        bar_time = start_time + timedelta(minutes=i)

        # Generate price based on phase
        if i < 5:
            # Pre-market / opening gap
            base = pre_open_price + (or_low - pre_open_price) * (i / 5)
            volatility = risk * 0.15
        elif i < 15:
            # Opening range consolidation
            base = or_low + (or_high - or_low) * (0.5 + 0.3 * random.random())
            volatility = risk * 0.1
        elif i == 15:
            # Breakout bar
            base = entry_price
            volatility = risk * 0.2
        elif i < 25:
            # Run towards target
            progress = (i - 15) / 10
            target_price = entry_price + risk * 2  # Assume 2R target
            base = entry_price + (target_price - entry_price) * progress
            volatility = risk * 0.08
        elif i < 30:
            # Near exit / target hit
            if exit_time_str and exit_bar_idx is None:
                exit_time = datetime.fromisoformat(exit_time_str.replace("Z", "+00:00"))
                if bar_time >= exit_time:
                    exit_bar_idx = i
            base = exit_price if exit_price else entry_price + risk * 1.5
            volatility = risk * 0.1
        else:
            # Post-trade continuation
            base = exit_price if exit_price else entry_price + risk * 1.2
            volatility = risk * 0.12

        # Generate OHLC
        noise = random.uniform(-volatility, volatility)
        open_price = base + noise
        close_price = base + random.uniform(-volatility, volatility)
        high_price = max(open_price, close_price) + random.uniform(0, volatility * 0.5)
        low_price = min(open_price, close_price) - random.uniform(0, volatility * 0.5)

        # Volume surge on breakout
        if i == 15 or i == 16:
            volume = random.randint(50000, 150000)
        elif i < 5:
            volume = random.randint(5000, 15000)
        else:
            volume = random.randint(15000, 50000)

        bars.append(
            ReplayBar(
                timestamp=bar_time.isoformat(),
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=float(volume),
            )
        )

        # Update VWAP
        typical_price = (high_price + low_price + close_price) / 3
        cum_volume += volume
        cum_pv += typical_price * volume
        vwap = cum_pv / cum_volume if cum_volume > 0 else typical_price
        vwap_values.append(round(vwap, 2))

    # Set exit bar if not found
    if exit_bar_idx is None and exit_time_str:
        exit_bar_idx = 25

    return bars, entry_bar_idx, exit_bar_idx, vwap_values


@router.get("/{trade_id}/replay", response_model=TradeReplayResponse)
async def get_trade_replay(
    trade_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> TradeReplayResponse:
    """Get historical bars for replaying a trade.

    Returns the trade data along with 1-minute bars for the time window
    around the trade (entry_time - 15 min to exit_time + 5 min).

    In dev mode, generates synthetic bars that create a plausible trade scenario.
    In live mode, queries the DataService for historical bars (stub for now).

    Args:
        trade_id: The ULID of the trade to replay.

    Returns:
        Trade data with historical bars, entry/exit bar indices, and VWAP values.

    Raises:
        HTTPException: 404 if trade not found.
    """
    # Fetch the trade
    trades_data = await state.trade_logger.get_trades_by_ids([trade_id])
    if not trades_data:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")

    trade_row = trades_data[0]

    # Parse target_prices from JSON string
    target_prices_raw = trade_row.get("target_prices")
    target_prices = (
        json.loads(target_prices_raw) if target_prices_raw else None
    )

    # Build trade response
    trade = TradeResponse(
        id=trade_row["id"],
        strategy_id=trade_row["strategy_id"],
        symbol=trade_row["symbol"],
        side=trade_row["side"],
        entry_price=trade_row["entry_price"],
        entry_time=trade_row["entry_time"],
        exit_price=trade_row.get("exit_price"),
        exit_time=trade_row.get("exit_time"),
        shares=trade_row["shares"],
        pnl_dollars=trade_row.get("net_pnl"),
        pnl_r_multiple=trade_row.get("r_multiple"),
        exit_reason=trade_row.get("exit_reason"),
        hold_duration_seconds=trade_row.get("hold_duration_seconds"),
        commission=trade_row.get("commission", 0.0),
        market_regime=trade_row.get("market_regime"),
        stop_price=trade_row.get("stop_price"),
        target_prices=target_prices,
        quality_grade=trade_row.get("quality_grade") or None,
        quality_score=trade_row.get("quality_score"),
    )

    # Check if we're in dev mode (has _mock_watchlist attribute)
    is_dev_mode = hasattr(state, "_mock_watchlist")

    if is_dev_mode:
        # Generate synthetic bars for dev mode
        bars, entry_idx, exit_idx, vwap = _generate_synthetic_replay_bars(trade_row)
    else:
        # Live mode: stub implementation
        # In the future, this would query DataService for historical bars
        bars = []
        entry_idx = 0
        exit_idx = None
        vwap = None

    return TradeReplayResponse(
        trade=trade,
        bars=bars,
        entry_bar_index=entry_idx,
        exit_bar_index=exit_idx,
        vwap=vwap,
        timestamp=datetime.now(UTC).isoformat(),
    )
