"""Market data routes for the Command Center API."""

from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.execution.simulated_broker import SimulatedBroker

router = APIRouter()
ET_TZ = ZoneInfo("America/New_York")
logger = logging.getLogger(__name__)


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
    limit: int = Query(390, ge=1, le=1000),
    start_time: str | None = Query(None, description="Start time (ISO-8601)"),
    end_time: str | None = Query(None, description="End time (ISO-8601)"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> BarsResponse:
    """Get intraday bars for a symbol.

    In dev mode, returns synthetic data. In production, queries DataService
    (Databento Historical API with Parquet caching).

    Args:
        symbol: Stock symbol (e.g., "AAPL", "TSLA").
        timeframe: Bar timeframe (default "1m"). Only 1m supported currently.
        limit: Number of bars to return (max 1000).
        start_time: Optional start time (ISO-8601 datetime). Defaults to today's market open.
        end_time: Optional end time (ISO-8601 datetime). Defaults to current time or market close.

    Returns:
        BarsResponse with OHLCV data.
    """
    upper_symbol = symbol.upper()
    is_dev_mode = isinstance(state.broker, SimulatedBroker)

    if not is_dev_mode and state.data_service is not None:
        # Production: fetch real bars from Databento via DataService
        try:
            # Parse time range
            if start_time and end_time:
                start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            else:
                # Default: today's trading session
                now_et = datetime.now(ET_TZ)
                start = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                end = min(now_et, now_et.replace(hour=16, minute=0, second=0, microsecond=0))

            df = await state.data_service.get_historical_candles(
                upper_symbol, timeframe, start, end
            )

            if df.empty:
                logger.warning(
                    "No bars returned for %s from DataService, falling back to synthetic",
                    upper_symbol,
                )
                bars = _generate_synthetic_bars(upper_symbol, min(limit, 390))
            else:
                bars = []
                for _, row in df.iterrows():
                    # Handle timestamp: could be datetime or pandas Timestamp
                    ts = row["timestamp"]
                    if hasattr(ts, "isoformat"):
                        ts_str = ts.isoformat()
                    else:
                        ts_str = str(ts)

                    bars.append(
                        BarData(
                            timestamp=ts_str,
                            open=round(float(row["open"]), 2),
                            high=round(float(row["high"]), 2),
                            low=round(float(row["low"]), 2),
                            close=round(float(row["close"]), 2),
                            volume=int(row["volume"]),
                        )
                    )
                # Return most recent N bars if limit specified
                if limit and len(bars) > limit:
                    bars = bars[-limit:]

        except Exception as e:
            logger.warning(
                "Failed to fetch real bars for %s: %s, falling back to synthetic",
                upper_symbol,
                e,
            )
            bars = _generate_synthetic_bars(upper_symbol, min(limit, 390))
    else:
        # Dev mode: synthetic data
        bars = _generate_synthetic_bars(upper_symbol, min(limit, 390))

    return BarsResponse(
        symbol=upper_symbol,
        timeframe=timeframe,
        bars=bars,
        count=len(bars),
    )
