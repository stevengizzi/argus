"""Position routes for the Command Center API.

Provides endpoints for viewing and managing open positions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class PositionResponse(BaseModel):
    """Single position with computed fields."""

    position_id: str
    strategy_id: str
    symbol: str
    side: str
    entry_price: float
    entry_time: str
    shares_total: int
    shares_remaining: int
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_price: float
    t1_price: float
    t2_price: float
    t1_filled: bool
    hold_duration_seconds: int
    r_multiple_current: float


class PositionsResponse(BaseModel):
    """Response for GET /positions."""

    positions: list[PositionResponse]
    count: int
    timestamp: str


class ReconciliationResponse(BaseModel):
    """Response for GET /positions/reconciliation."""

    status: str
    discrepancies: list[dict[str, object]]
    timestamp: str


@router.get("", response_model=PositionsResponse)
async def get_positions(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    strategy_id: str | None = Query(None, description="Filter by strategy ID"),
) -> PositionsResponse:
    """Get all open positions with computed unrealized P&L.

    Returns current positions from the Order Manager, enriched with:
    - Current price (from data service or entry price fallback)
    - Unrealized P&L (dollars and percentage)
    - Current R-multiple based on live price
    - Hold duration in seconds

    Args:
        strategy_id: Optional filter to show positions from a specific strategy.

    Returns:
        List of open positions with computed fields.
    """
    managed_positions = state.order_manager.get_all_positions_flat()

    # Filter by strategy if specified
    if strategy_id is not None:
        managed_positions = [p for p in managed_positions if p.strategy_id == strategy_id]

    positions: list[PositionResponse] = []
    clock_now = state.clock.now() if state.clock else datetime.now(UTC)

    for pos in managed_positions:
        # Try to get current price from data service, fallback to entry price
        current_price = pos.entry_price
        if state.data_service is not None:
            try:
                price = await state.data_service.get_current_price(pos.symbol)
                if price is not None:
                    current_price = price
            except (ValueError, KeyError):
                # Use entry price if current price unavailable
                pass

        # Compute unrealized P&L (long only for now)
        unrealized_pnl = (current_price - pos.entry_price) * pos.shares_remaining

        # Compute unrealized P&L percentage
        cost_basis = pos.entry_price * pos.shares_remaining
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0

        # Compute hold duration
        hold_duration = (clock_now - pos.entry_time).total_seconds()

        # Compute current R-multiple
        # R = (current_price - entry_price) / (entry_price - stop_price)
        risk_per_share = pos.entry_price - pos.original_stop_price
        if abs(risk_per_share) > 0.0001:  # Guard against division by zero
            r_multiple_current = (current_price - pos.entry_price) / risk_per_share
        else:
            r_multiple_current = 0.0

        # Generate position_id from symbol + strategy + entry_time
        position_id = f"{pos.symbol}_{pos.strategy_id}_{pos.entry_time.strftime('%Y%m%d%H%M%S')}"

        positions.append(
            PositionResponse(
                position_id=position_id,
                strategy_id=pos.strategy_id,
                symbol=pos.symbol,
                side="long",  # V1 is long only
                entry_price=pos.entry_price,
                entry_time=pos.entry_time.isoformat(),
                shares_total=pos.shares_total,
                shares_remaining=pos.shares_remaining,
                current_price=current_price,
                unrealized_pnl=round(unrealized_pnl, 2),
                unrealized_pnl_pct=round(unrealized_pnl_pct, 2),
                stop_price=pos.stop_price,
                t1_price=pos.t1_price,
                t2_price=pos.t2_price,
                t1_filled=pos.t1_filled,
                hold_duration_seconds=int(hold_duration),
                r_multiple_current=round(r_multiple_current, 2),
            )
        )

    return PositionsResponse(
        positions=positions,
        count=len(positions),
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/reconciliation", response_model=ReconciliationResponse)
async def get_reconciliation(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ReconciliationResponse:
    """Get the latest position reconciliation result.

    Returns the most recent comparison of internal positions against
    broker-reported positions. If no discrepancies: status is "synced".

    Returns:
        Latest reconciliation result with timestamp and discrepancies.
    """
    result = state.order_manager.last_reconciliation
    if result is None:
        return ReconciliationResponse(
            status="synced",
            discrepancies=[],
            timestamp=datetime.now(UTC).isoformat(),
        )
    return ReconciliationResponse(
        status=result.status,
        discrepancies=list(result.discrepancies),
        timestamp=result.timestamp,
    )
