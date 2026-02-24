"""Abstract Data Service for market data access.

The Data Service is the single source of market data for the Argus system.
Streaming data is delivered exclusively via the Event Bus (DEC-029).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class DataService(ABC):
    """Abstract base class for market data services.

    The Data Service is the single source of market data for the system.
    Streaming data is delivered exclusively via the Event Bus (DEC-029):
    - CandleEvent for completed candles
    - TickEvent for price updates
    - IndicatorEvent for computed indicators

    Synchronous query methods are for point-in-time lookups only.
    """

    @abstractmethod
    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Start streaming data for the given symbols and timeframes.

        Publishes CandleEvent, TickEvent, and IndicatorEvent to the Event Bus.

        Args:
            symbols: List of ticker symbols to stream.
            timeframes: List of timeframe strings (e.g., ["1m"]).
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop streaming and clean up connections."""

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float | None:
        """Get last known price from in-memory cache.

        Args:
            symbol: Ticker symbol.

        Returns:
            Last known price, or None if no data available.
        """

    @abstractmethod
    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Get current indicator value from in-memory cache.

        Args:
            symbol: Ticker symbol.
            indicator: Indicator name (e.g., "vwap", "atr_14", "sma_20").

        Returns:
            Current indicator value, or None if not yet computed.
        """

    @abstractmethod
    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fetch historical candle data.

        Args:
            symbol: Ticker symbol.
            timeframe: Candle timeframe (e.g., "1m").
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp.
        """

    @abstractmethod
    async def fetch_daily_bars(
        self, symbol: str, lookback_days: int = 60
    ) -> pd.DataFrame | None:
        """Fetch daily OHLCV bars for regime classification.

        Used by the Orchestrator to compute regime indicators (SPY daily bars).
        This is a REST fetch, not a streaming subscription.

        Args:
            symbol: Ticker symbol (e.g., "SPY").
            lookback_days: Number of trading days to fetch (default 60).

        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp.
            Sorted oldest-first. Returns None if data is unavailable.
        """
