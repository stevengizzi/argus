"""Market data routes for the Command Center API."""

from __future__ import annotations

import hashlib
import random
from datetime import timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()
ET_TZ = ZoneInfo("America/New_York")


class BarData(BaseModel):
    """Single OHLCV bar."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class BarsResponse(BaseModel):
    """Response containing intraday bars for a symbol."""

    symbol: str
    timeframe: str
    bars: list[BarData]
    count: int


def _generate_synthetic_bars(symbol: str, limit: int) -> list[BarData]:
    """Generate deterministic synthetic OHLCV data for dev mode.

    Uses the symbol name as a seed to produce consistent data across requests.

    Args:
        symbol: The stock symbol (used for seeding).
        limit: Number of bars to generate (max 390 for a full trading day).

    Returns:
        List of BarData with synthetic OHLCV values.
    """
    # Seed from symbol name for deterministic output
    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    # Base price derived from symbol hash (range $10-$500)
    base_price = 10 + (seed % 490)
    volatility = base_price * 0.002  # 0.2% per bar

    # Start from today's market open in ET
    from datetime import datetime

    now_et = datetime.now(ET_TZ)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)

    bars = []
    price = float(base_price)

    for i in range(limit):
        timestamp = market_open + timedelta(minutes=i)

        # Random walk with slight mean reversion
        change = rng.gauss(0, volatility)
        mean_reversion = (base_price - price) * 0.01
        price += change + mean_reversion
        price = max(price, 1.0)  # Floor at $1

        open_price = price
        close_price = price + rng.gauss(0, volatility * 0.5)
        high_price = max(open_price, close_price) + abs(rng.gauss(0, volatility * 0.3))
        low_price = min(open_price, close_price) - abs(rng.gauss(0, volatility * 0.3))

        # Volume: higher at open/close, lower midday
        minutes_from_open = i
        volume_base = 50000 + seed % 200000
        if minutes_from_open < 30:  # First 30 min
            volume_mult = 2.0 + rng.random()
        elif minutes_from_open > 350:  # Last 40 min
            volume_mult = 1.5 + rng.random()
        else:
            volume_mult = 0.5 + rng.random()
        volume = int(volume_base * volume_mult)

        bars.append(
            BarData(
                timestamp=timestamp.isoformat(),
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=volume,
            )
        )

        price = close_price

    return bars


@router.get("/{symbol}/bars", response_model=BarsResponse)
async def get_symbol_bars(
    symbol: str,
    timeframe: str = "1m",
    limit: int = 390,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> BarsResponse:
    """Get intraday bars for a symbol.

    In dev mode, returns synthetic data. In production, queries DataService.

    Args:
        symbol: Stock symbol (e.g., "AAPL", "TSLA").
        timeframe: Bar timeframe (default "1m"). Only 1m supported currently.
        limit: Number of bars to return (max 390 for a full trading day).

    Returns:
        BarsResponse with OHLCV data.
    """
    # For now, always use synthetic data (production DataService integration
    # will be added when Databento is active)
    bars = _generate_synthetic_bars(symbol.upper(), min(limit, 390))

    return BarsResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        bars=bars,
        count=len(bars),
    )
