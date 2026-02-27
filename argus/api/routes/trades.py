"""Trade history routes for the Command Center API.

Provides endpoints for querying trade history and details.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
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
