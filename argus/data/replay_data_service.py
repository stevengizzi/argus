"""Replay Data Service for backtesting and development.

Reads historical data from Parquet files and replays it through the Event Bus
as if it were live data. Supports configurable replay speed.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent
from argus.data.service import DataService

logger = logging.getLogger(__name__)


@dataclass
class IndicatorState:
    """Internal state for computing indicators for a single symbol."""

    # VWAP state (resets daily)
    vwap_cumulative_tp_volume: float = 0.0
    vwap_cumulative_volume: int = 0
    vwap_date: str = ""  # Track which date we're on for reset

    # ATR state
    atr_true_ranges: list[float] = field(default_factory=list)
    atr_prev_close: float | None = None

    # SMA state (rolling windows)
    sma_closes: list[float] = field(default_factory=list)

    # RVOL state (relative volume)
    rvol_baseline_volume: float | None = None  # Average volume from first N candles
    rvol_volume_samples: list[int] = field(default_factory=list)

    # Cached indicator values
    vwap: float | None = None
    atr_14: float | None = None
    sma_9: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    rvol: float | None = None


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

        # Indicator state per symbol
        self._indicator_state: dict[str, IndicatorState] = defaultdict(IndicatorState)

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
        """Compute indicators and publish IndicatorEvents."""
        state = self._indicator_state[symbol]

        # Get date string for VWAP reset
        candle_date = candle.timestamp.strftime("%Y-%m-%d")

        # Reset VWAP on new day
        if state.vwap_date != candle_date:
            state.vwap_cumulative_tp_volume = 0.0
            state.vwap_cumulative_volume = 0
            state.vwap_date = candle_date
            # Reset RVOL baseline on new day too
            state.rvol_volume_samples = []
            state.rvol_baseline_volume = None

        # --- VWAP ---
        typical_price = (candle.high + candle.low + candle.close) / 3
        state.vwap_cumulative_tp_volume += typical_price * candle.volume
        state.vwap_cumulative_volume += candle.volume

        if state.vwap_cumulative_volume > 0:
            state.vwap = state.vwap_cumulative_tp_volume / state.vwap_cumulative_volume
            await self._publish_indicator(symbol, "vwap", state.vwap)

        # --- ATR(14) ---
        if state.atr_prev_close is not None:
            true_range = max(
                candle.high - candle.low,
                abs(candle.high - state.atr_prev_close),
                abs(candle.low - state.atr_prev_close),
            )
            state.atr_true_ranges.append(true_range)

            if len(state.atr_true_ranges) >= 14:
                # Use Wilder's smoothing (exponential moving average)
                if state.atr_14 is None:
                    # Initial ATR is simple average
                    state.atr_14 = sum(state.atr_true_ranges[-14:]) / 14
                else:
                    # Subsequent ATR uses smoothing: ATR = ((ATR_prev * 13) + TR) / 14
                    state.atr_14 = (state.atr_14 * 13 + true_range) / 14

                await self._publish_indicator(symbol, "atr_14", state.atr_14)

        state.atr_prev_close = candle.close

        # --- SMA (9, 20, 50) ---
        state.sma_closes.append(candle.close)

        if len(state.sma_closes) >= 9:
            state.sma_9 = sum(state.sma_closes[-9:]) / 9
            await self._publish_indicator(symbol, "sma_9", state.sma_9)

        if len(state.sma_closes) >= 20:
            state.sma_20 = sum(state.sma_closes[-20:]) / 20
            await self._publish_indicator(symbol, "sma_20", state.sma_20)

        if len(state.sma_closes) >= 50:
            state.sma_50 = sum(state.sma_closes[-50:]) / 50
            await self._publish_indicator(symbol, "sma_50", state.sma_50)

        # --- RVOL (relative volume) ---
        # Use first 20 candles as baseline
        state.rvol_volume_samples.append(candle.volume)
        if len(state.rvol_volume_samples) >= 20:
            if state.rvol_baseline_volume is None:
                # Set baseline from first 20 candles
                state.rvol_baseline_volume = sum(state.rvol_volume_samples[:20]) / 20

            if state.rvol_baseline_volume > 0:
                # RVOL = current cumulative volume / expected cumulative volume
                cumulative_volume = sum(state.rvol_volume_samples)
                expected_volume = state.rvol_baseline_volume * len(
                    state.rvol_volume_samples
                )
                state.rvol = cumulative_volume / expected_volume
                await self._publish_indicator(symbol, "rvol", state.rvol)

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
        self._indicator_state.clear()
        logger.info("ReplayDataService stopped")

    async def get_current_price(self, symbol: str) -> float | None:
        """Return the close price of the most recent candle for the symbol."""
        return self._current_prices.get(symbol.upper())

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Return the most recent computed indicator value."""
        state = self._indicator_state.get(symbol.upper())
        if state is None:
            return None

        indicator_map = {
            "vwap": state.vwap,
            "atr_14": state.atr_14,
            "sma_9": state.sma_9,
            "sma_20": state.sma_20,
            "sma_50": state.sma_50,
            "rvol": state.rvol,
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
