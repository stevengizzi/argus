"""Market data routes for the Command Center API."""

from __future__ import annotations

import hashlib
import logging
import random
from datetime import datetime, timedelta, UTC
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.core.market_calendar import get_next_trading_day, is_market_holiday

router = APIRouter()
ET_TZ = ZoneInfo("America/New_York")
logger = logging.getLogger(__name__)


class MarketStatusResponse(BaseModel):
    """Response for GET /api/v1/market/status."""

    is_holiday: bool
    holiday_name: str | None
    is_market_hours: bool
    next_trading_day: str


@router.get("/status", response_model=MarketStatusResponse)
async def get_market_status() -> MarketStatusResponse:
    """Get current market status including holiday information.

    No authentication required — useful for health checks and frontend context.

    Returns:
        MarketStatusResponse with holiday, market hours, and next trading day info.
    """
    holiday_flag, holiday_name = is_market_holiday()
    next_day = get_next_trading_day()

    now_et = datetime.now(ET_TZ)
    in_market_hours = (
        not holiday_flag
        and now_et.weekday() < 5
        and datetime(now_et.year, now_et.month, now_et.day, 9, 30, tzinfo=ET_TZ)
        <= now_et
        < datetime(now_et.year, now_et.month, now_et.day, 16, 0, tzinfo=ET_TZ)
    )

    return MarketStatusResponse(
        is_holiday=holiday_flag,
        holiday_name=holiday_name,
        is_market_hours=in_market_hours,
        next_trading_day=next_day.isoformat(),
    )


class BarData(BaseModel):
    """Single OHLCV bar."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class BarsResponse(BaseModel):
    """Response containing intraday bars for a symbol.

    The ``source`` field discloses provenance so the frontend can gate
    real-trading UI behind ``live``/``historical`` data:

    * ``live`` — served from the in-memory IntradayCandleStore (current session).
    * ``historical`` — served from the DataService historical Parquet cache.
    * ``synthetic`` — generated deterministically from the symbol name.
      Only returned when no real data is available for the requested window
      (e.g., pre-market, data-feed outage). Treat as illustrative only.
    """

    symbol: str
    timeframe: str
    bars: list[BarData]
    count: int
    source: Literal["live", "historical", "synthetic"]


def _generate_synthetic_bars(symbol: str, limit: int) -> list[BarData]:
    """Generate deterministic synthetic OHLCV data for dev mode.

    Uses the symbol name as a seed to produce consistent data across requests.

    Args:
        symbol: The stock symbol (used for seeding).
        limit: Number of bars to generate. Capped at 390 (a full RTH
            trading day) — real-data paths may return up to the full
            route ``limit`` query param, but synthetic is session-bounded.

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

    Attempts to fetch real data from DataService first. Falls back to synthetic
    data if DataService is unavailable or returns no data.

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

    # --- Priority 1: IntradayCandleStore (live session bars) ---
    if state.candle_store is not None and state.candle_store.has_bars(upper_symbol):
        # Parse optional time range
        start: datetime | None = None
        end: datetime | None = None
        if start_time and end_time:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        candle_bars = state.candle_store.get_bars(upper_symbol, start, end)

        # Apply limit (most recent N bars)
        if len(candle_bars) > limit:
            candle_bars = candle_bars[-limit:]

        bars = [
            BarData(
                timestamp=bar.timestamp.isoformat(),
                open=round(bar.open, 2),
                high=round(bar.high, 2),
                low=round(bar.low, 2),
                close=round(bar.close, 2),
                volume=int(bar.volume),
            )
            for bar in candle_bars
        ]

        logger.info(
            "Bars for %s from candle store: %d bars",
            upper_symbol,
            len(bars),
        )

        return BarsResponse(
            symbol=upper_symbol,
            timeframe=timeframe,
            bars=bars,
            count=len(bars),
            source="live",
        )

    # --- Priority 2: DataService historical candles ---
    if state.data_service is not None and hasattr(state.data_service, "get_historical_candles"):
        try:
            # Parse time range
            if start_time and end_time:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            else:
                # Default: today's trading session
                now_et = datetime.now(ET_TZ)
                start_dt = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                end_dt = min(now_et, now_et.replace(hour=16, minute=0, second=0, microsecond=0))

            df = await state.data_service.get_historical_candles(
                upper_symbol, timeframe, start_dt, end_dt
            )

            if df is not None and not df.empty:
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

                logger.info(
                    "Bars for %s: %d bars, price range %.2f-%.2f",
                    upper_symbol,
                    len(bars),
                    min(b.low for b in bars) if bars else 0,
                    max(b.high for b in bars) if bars else 0,
                )

                return BarsResponse(
                    symbol=upper_symbol,
                    timeframe=timeframe,
                    bars=bars,
                    count=len(bars),
                    source="historical",
                )
            else:
                logger.debug(
                    "No bars returned for %s from DataService, falling back to synthetic",
                    upper_symbol,
                )

        except Exception:
            logger.debug(
                "Failed to fetch real bars for %s, falling back to synthetic",
                upper_symbol,
                exc_info=True,
            )

    # --- Priority 3: Synthetic fallback ---
    # Synthetic is capped at 390 (one RTH session) regardless of the
    # route `limit` query param. The `source="synthetic"` flag on the
    # response lets the frontend gate real-trading UI away from fake bars.
    synthetic_limit = min(limit, 390)
    bars = _generate_synthetic_bars(upper_symbol, synthetic_limit)
    logger.warning(
        "Returning %d SYNTHETIC bars for %s (no real data available)",
        len(bars),
        upper_symbol,
    )
    return BarsResponse(
        symbol=upper_symbol,
        timeframe=timeframe,
        bars=bars,
        count=len(bars),
        source="synthetic",
    )
