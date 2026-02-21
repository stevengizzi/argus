"""Replay Data Service for backtesting and development.

Reads historical data from Parquet files and replays it through the Event Bus
as if it were live data. Supports configurable replay speed.

Indicator computation delegated to IndicatorEngine (DEF-013).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent
from argus.data.indicator_engine import IndicatorEngine
from argus.data.service import DataService

logger = logging.getLogger(__name__)


class ReplayDataService(DataService):
    """Data service that replays historical data from Parquet files.

    Reads 1-minute candle data from Parquet files and publishes CandleEvents
    to the Event Bus. Supports configurable replay speed.

    Multi-timeframe framework (MD-2c): The interface accepts a list of timeframes,
    but Sprint 3 only implements 1m. Other timeframes will be built by aggregating
    1m candles when needed.

    Data format (MD-5a): Parquet only. Expected schema:
        - timestamp: datetime (UTC)
        - open: float
        - high: float
        - low: float
        - close: float
        - volume: int

    Each file represents one symbol's data. File naming: {SYMBOL}.parquet
    (e.g., AAPL.parquet)

    Indicator computation (MD-3a): After publishing each CandleEvent, the
    ReplayDataService computes indicators and publishes IndicatorEvents.
    Indicators computed: VWAP, ATR(14), RVOL, SMA(9), SMA(20), SMA(50).

    Args:
        event_bus: The Event Bus to publish events on.
        data_dir: Path to directory containing Parquet files.
        speed: Replay speed multiplier. 0 = instant (as fast as possible),
               1.0 = real-time, 100.0 = 100x speed.
    """

    def __init__(
        self,
        event_bus: EventBus,
        data_dir: Path,
        speed: float = 0,
    ) -> None:
        self._event_bus = event_bus
        self._data_dir = data_dir
        self._speed = speed

        # Loaded data per symbol
        self._data: dict[str, pd.DataFrame] = {}

        # Current prices (most recent close)
        self._current_prices: dict[str, float] = {}

        # Indicator engines per symbol (DEF-013)
        self._indicator_engines: dict[str, IndicatorEngine] = {}

        # Running state
        self._running: bool = False
        self._replay_task: asyncio.Task | None = None

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Load Parquet files for symbols and begin replay.

        For each symbol:
        1. Load the Parquet file from data_dir/{SYMBOL}.parquet
        2. Sort by timestamp
        3. Iterate through candles in chronological order
        4. For each candle: publish CandleEvent, compute & publish IndicatorEvents
        5. If speed > 0, sleep proportionally between candles

        If timeframes contains anything other than "1m", log a warning but continue
        (multi-timeframe not yet implemented).
        """
        # Warn about unsupported timeframes
        unsupported = [tf for tf in timeframes if tf != "1m"]
        if unsupported:
            logger.warning(
                "ReplayDataService only supports 1m timeframe. Ignoring: %s",
                unsupported,
            )

        # Load Parquet files
        for symbol in symbols:
            file_path = self._data_dir / f"{symbol.upper()}.parquet"
            if not file_path.exists():
                raise FileNotFoundError(
                    f"Parquet file not found for {symbol}: {file_path}"
                )

            df = pd.read_parquet(file_path)
            df = df.sort_values("timestamp").reset_index(drop=True)
            self._data[symbol.upper()] = df
            logger.info("Loaded %d candles for %s", len(df), symbol.upper())

        self._running = True
        self._replay_task = asyncio.create_task(self._run_replay())
        logger.info("ReplayDataService started for %d symbols", len(symbols))

    async def _run_replay(self) -> None:
        """Execute the replay loop."""
        # Merge all candles from all symbols and sort by timestamp
        all_candles: list[tuple[datetime, str, pd.Series]] = []

        for symbol, df in self._data.items():
            for _, row in df.iterrows():
                ts = row["timestamp"]
                if isinstance(ts, pd.Timestamp):
                    ts = ts.to_pydatetime()
                all_candles.append((ts, symbol, row))

        # Sort by timestamp
        all_candles.sort(key=lambda x: x[0])

        prev_timestamp: datetime | None = None

        for timestamp, symbol, row in all_candles:
            if not self._running:
                break

            # Sleep for replay speed if needed
            if self._speed > 0 and prev_timestamp is not None:
                delta_seconds = (timestamp - prev_timestamp).total_seconds()
                sleep_time = delta_seconds / self._speed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

            prev_timestamp = timestamp

            # Publish candle event
            candle = CandleEvent(
                symbol=symbol,
                timeframe="1m",
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
                timestamp=timestamp,
            )
            await self._event_bus.publish(candle)

            # Update current price
            self._current_prices[symbol] = candle.close

            # Compute and publish indicators
            await self._update_indicators(symbol, candle)

        logger.info("Replay complete")
        self._running = False

    async def _update_indicators(self, symbol: str, candle: CandleEvent) -> None:
        """Compute indicators and publish IndicatorEvents.

        Delegates to IndicatorEngine for computation (DEF-013).
        """
        # Get or create indicator engine for this symbol
        if symbol not in self._indicator_engines:
            self._indicator_engines[symbol] = IndicatorEngine(symbol)

        engine = self._indicator_engines[symbol]

        # Get date string for auto-reset detection
        candle_date = candle.timestamp.strftime("%Y-%m-%d")

        # Update indicators via engine
        values = engine.update(
            open_=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            timestamp_date=candle_date,
        )

        # Publish events for non-None indicators
        if values.vwap is not None:
            await self._publish_indicator(symbol, "vwap", values.vwap)

        if values.atr_14 is not None:
            await self._publish_indicator(symbol, "atr_14", values.atr_14)

        if values.sma_9 is not None:
            await self._publish_indicator(symbol, "sma_9", values.sma_9)

        if values.sma_20 is not None:
            await self._publish_indicator(symbol, "sma_20", values.sma_20)

        if values.sma_50 is not None:
            await self._publish_indicator(symbol, "sma_50", values.sma_50)

        if values.rvol is not None:
            await self._publish_indicator(symbol, "rvol", values.rvol)

    async def _publish_indicator(
        self, symbol: str, indicator: str, value: float
    ) -> None:
        """Publish an IndicatorEvent to the Event Bus."""
        event = IndicatorEvent(
            symbol=symbol,
            indicator_name=indicator,
            value=value,
        )
        await self._event_bus.publish(event)

    async def stop(self) -> None:
        """Stop replay and clean up."""
        self._running = False
        if self._replay_task is not None:
            self._replay_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._replay_task
            self._replay_task = None

        self._data.clear()
        self._current_prices.clear()
        self._indicator_engines.clear()
        logger.info("ReplayDataService stopped")

    async def get_current_price(self, symbol: str) -> float | None:
        """Return the close price of the most recent candle for the symbol."""
        return self._current_prices.get(symbol.upper())

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Return the most recent computed indicator value."""
        engine = self._indicator_engines.get(symbol.upper())
        if engine is None:
            return None

        indicator_map = {
            "vwap": engine.vwap,
            "atr_14": engine.atr_14,
            "sma_9": engine.sma_9,
            "sma_20": engine.sma_20,
            "sma_50": engine.sma_50,
            "rvol": engine.rvol,
        }
        return indicator_map.get(indicator.lower())

    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Return candles from the loaded Parquet data within the date range."""
        upper_symbol = symbol.upper()
        if upper_symbol not in self._data:
            return pd.DataFrame()

        df = self._data[upper_symbol]

        # Ensure timezone-aware comparison
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)

        # Filter by date range
        mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
        return df[mask].copy()

    async def wait_for_completion(self) -> None:
        """Wait for the replay to complete. Used in tests."""
        if self._replay_task is not None:
            await self._replay_task
