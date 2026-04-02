"""Arena REST API routes for the real-time position visualization page.

Provides initial data load endpoints for the Arena page:
- Position list with levels (entry, stop, targets, trail)
- Candle history per symbol for chart initialization
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class ArenaPositionResponse(BaseModel):
    """Single position entry for the Arena page."""

    symbol: str
    strategy_id: str
    side: str
    shares: int
    entry_price: float
    current_price: float
    stop_price: float
    target_prices: list[float]
    trailing_stop_price: float | None
    unrealized_pnl: float
    r_multiple: float
    hold_duration_seconds: int
    quality_grade: str
    entry_time: str


class ArenaStatsResponse(BaseModel):
    """Aggregate stats across all open positions."""

    position_count: int
    total_pnl: float
    net_r: float


class ArenaPositionsResponse(BaseModel):
    """Response for GET /arena/positions."""

    positions: list[ArenaPositionResponse]
    stats: ArenaStatsResponse
    timestamp: str


class CandleBarResponse(BaseModel):
    """Single OHLCV bar in TradingView Lightweight Charts format."""

    time: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class ArenaCandlesResponse(BaseModel):
    """Response for GET /arena/candles/{symbol}."""

    symbol: str
    candles: list[CandleBarResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/positions", response_model=ArenaPositionsResponse)
async def get_arena_positions(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ArenaPositionsResponse:
    """Get all open managed positions for the Arena page.

    Returns each position's price levels (entry, stop, targets, trail),
    unrealized P&L, R-multiple, and hold duration. Designed for initial
    chart load — live updates arrive via /ws/v1/arena.

    Returns:
        All open positions with computed fields and aggregate stats.
    """
    managed_positions = state.order_manager.get_all_positions_flat()
    clock_now = state.clock.now() if state.clock else datetime.now(UTC)

    positions: list[ArenaPositionResponse] = []

    for pos in managed_positions:
        # Try live price from data service; fall back to entry price
        current_price = pos.entry_price
        if state.data_service is not None:
            try:
                price = await state.data_service.get_current_price(pos.symbol)
                if price is not None:
                    current_price = price
            except (ValueError, KeyError):
                pass

        unrealized_pnl = round((current_price - pos.entry_price) * pos.shares_remaining, 2)

        risk_per_share = pos.entry_price - pos.original_stop_price
        if abs(risk_per_share) > 0.0001:
            r_multiple = round((current_price - pos.entry_price) / risk_per_share, 2)
        else:
            r_multiple = 0.0

        hold_duration_seconds = int((clock_now - pos.entry_time).total_seconds())

        trailing_stop_price: float | None = pos.trail_stop_price if pos.trail_active else None

        entry_time_str = (
            pos.entry_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            if pos.entry_time.tzinfo is not None
            else pos.entry_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        positions.append(
            ArenaPositionResponse(
                symbol=pos.symbol,
                strategy_id=pos.strategy_id,
                side="long",
                shares=pos.shares_remaining,
                entry_price=pos.entry_price,
                current_price=current_price,
                stop_price=pos.stop_price,
                target_prices=[pos.t1_price, pos.t2_price],
                trailing_stop_price=trailing_stop_price,
                unrealized_pnl=unrealized_pnl,
                r_multiple=r_multiple,
                hold_duration_seconds=hold_duration_seconds,
                quality_grade=pos.quality_grade,
                entry_time=entry_time_str,
            )
        )

    total_pnl = round(sum(p.unrealized_pnl for p in positions), 2)
    net_r = round(sum(p.r_multiple for p in positions), 2)

    return ArenaPositionsResponse(
        positions=positions,
        stats=ArenaStatsResponse(
            position_count=len(positions),
            total_pnl=total_pnl,
            net_r=net_r,
        ),
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/candles/{symbol}", response_model=ArenaCandlesResponse)
async def get_arena_candles(
    symbol: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    minutes: int = Query(30, ge=1, le=390, description="Number of 1-min bars to return"),
) -> ArenaCandlesResponse:
    """Get recent 1-minute candles for a symbol.

    Returns the N most recent market-hours bars from the intraday candle
    store in TradingView Lightweight Charts format (Unix timestamps).

    Args:
        symbol: Stock symbol (e.g., "AAPL").
        minutes: Number of bars to return (default 30, max 390).

    Returns:
        Symbol and list of OHLCV bars with Unix timestamps.
    """
    if state.candle_store is None:
        return ArenaCandlesResponse(symbol=symbol, candles=[])

    bars = state.candle_store.get_latest(symbol, count=minutes)

    candles = [
        CandleBarResponse(
            time=int(bar.timestamp.timestamp()),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
        )
        for bar in bars
    ]

    return ArenaCandlesResponse(symbol=symbol, candles=candles)
