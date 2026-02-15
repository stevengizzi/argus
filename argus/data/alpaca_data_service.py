"""Alpaca live data service implementation using WebSocket and REST APIs.

This module provides real-time market data streaming from Alpaca via WebSocket,
with historical data fetching for indicator warm-up via REST API.
"""

import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar, Trade
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from argus.core.clock import Clock, SystemClock
from argus.core.config import AlpacaConfig, DataServiceConfig
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent, TickEvent
from argus.data.service import DataService

logger = logging.getLogger(__name__)


@dataclass
class IndicatorState:
    """Internal state for computing indicators for a single symbol.

    Matches ReplayDataService's indicator computation logic exactly.
    """

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


class AlpacaDataService(DataService):
    """Live market data service using Alpaca's WebSocket and REST APIs.

    Subscribes to Alpaca's 1m bar stream for CandleEvents and trade stream
    for TickEvents and real-time price cache. Computes indicators inline
    (VWAP, ATR, SMA, RVOL) matching ReplayDataService's behavior exactly.

    Attributes:
        _event_bus: Event bus for publishing market data events.
        _alpaca_config: Alpaca-specific configuration (API keys, feed, reconnection).
        _data_config: Data service configuration (warm-up periods, etc.).
        _clock: Injectable clock for time-based operations.
        _data_stream: Alpaca WebSocket stream for bars and trades.
        _historical_client: Alpaca REST client for historical data.
        _price_cache: Latest trade price per symbol.
        _indicator_state: IndicatorState instances per symbol.
        _last_data_time: Last data received timestamp per symbol.
        _is_stale: Flag indicating if data is stale.
        _stream_task: Asyncio task running the WebSocket stream.
        _monitor_task: Asyncio task monitoring for stale data.
        _subscribed_symbols: Set of currently subscribed symbols.
        _running: Flag indicating if the service is running.
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: AlpacaConfig,
        data_config: DataServiceConfig,
        clock: Clock | None = None,
    ):
        """Initialize AlpacaDataService.

        Args:
            event_bus: Event bus for publishing market data events.
            config: Alpaca-specific configuration.
            data_config: Data service configuration.
            clock: Injectable clock (defaults to SystemClock).
        """
        self._event_bus = event_bus
        self._alpaca_config = config
        self._data_config = data_config
        self._clock = clock if clock is not None else SystemClock()

        # WebSocket and REST clients (initialized in start())
        self._data_stream: StockDataStream | None = None
        self._historical_client: StockHistoricalDataClient | None = None

        # State
        self._price_cache: dict[str, float] = {}
        self._indicator_state: dict[str, IndicatorState] = {}
        self._last_data_time: dict[str, datetime] = {}
        self._is_stale = False
        self._stream_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._subscribed_symbols: set[str] = set()
        self._running = False
        self._consecutive_failures = 0

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Start streaming live data for the given symbols.

        Args:
            symbols: List of ticker symbols to stream.
            timeframes: List of timeframes (only "1m" supported currently).

        Raises:
            ValueError: If API keys not found in environment.
            ValueError: If unsupported timeframe requested.
        """
        if "1m" not in timeframes:
            raise ValueError(f"Only 1m timeframe supported, got: {timeframes}")

        logger.info(f"Starting AlpacaDataService for symbols: {symbols}")

        # Initialize clients
        api_key = os.getenv(self._alpaca_config.api_key_env)
        secret_key = os.getenv(self._alpaca_config.secret_key_env)

        if not api_key or not secret_key:
            raise ValueError(
                f"Alpaca API keys not found in environment. "
                f"Expected: {self._alpaca_config.api_key_env}, "
                f"{self._alpaca_config.secret_key_env}"
            )

        # Initialize historical client (REST)
        self._historical_client = StockHistoricalDataClient(api_key, secret_key)

        # Initialize data stream (WebSocket)
        self._data_stream = StockDataStream(
            api_key=api_key,
            secret_key=secret_key,
            feed=self._alpaca_config.data_feed,
        )

        # Subscribe to bars and trades
        if self._alpaca_config.subscribe_bars:
            self._data_stream.subscribe_bars(self._on_bar, *symbols)
        if self._alpaca_config.subscribe_trades:
            self._data_stream.subscribe_trades(self._on_trade, *symbols)

        self._subscribed_symbols = set(symbols)

        # Warm up indicators with historical data
        await self._warm_up_indicators(symbols)

        # Start WebSocket stream as asyncio task (use _run_forever directly)
        self._stream_task = asyncio.create_task(self._run_stream_with_reconnect())

        # Start stale data monitor
        self._monitor_task = asyncio.create_task(self._stale_data_monitor())

        self._running = True
        logger.info(f"AlpacaDataService started for {len(symbols)} symbols")

    async def stop(self) -> None:
        """Stop streaming, close WebSocket connections, cancel tasks."""
        logger.info("Stopping AlpacaDataService")
        self._running = False

        # Stop WebSocket stream
        if self._data_stream:
            await self._data_stream.stop_ws()

        # Cancel tasks
        if self._stream_task:
            self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket connection
        if self._data_stream:
            await self._data_stream.close()

        logger.info("AlpacaDataService stopped")

    async def get_current_price(self, symbol: str) -> float:
        """Return the latest trade price from the in-memory cache.

        Args:
            symbol: Ticker symbol.

        Returns:
            Latest trade price.

        Raises:
            ValueError: If no price available for symbol.
        """
        if symbol not in self._price_cache:
            raise ValueError(f"No price data available for {symbol}")
        return self._price_cache[symbol]

    async def get_indicator(self, symbol: str, indicator: str) -> float:
        """Return latest computed indicator value from cache.

        Args:
            symbol: Ticker symbol.
            indicator: Indicator key (e.g., "vwap", "atr_14", "sma_9").

        Returns:
            Latest indicator value.

        Raises:
            ValueError: If indicator not available for symbol.
        """
        state = self._indicator_state.get(symbol)
        if state is None:
            raise ValueError(f"No indicator state for {symbol}")

        indicator_map = {
            "vwap": state.vwap,
            "atr_14": state.atr_14,
            "sma_9": state.sma_9,
            "sma_20": state.sma_20,
            "sma_50": state.sma_50,
            "rvol": state.rvol,
        }

        value = indicator_map.get(indicator)
        if value is None:
            raise ValueError(f"Indicator {indicator} not available for {symbol}")

        return value

    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fetch historical candles via Alpaca REST API.

        Args:
            symbol: Ticker symbol.
            timeframe: Timeframe string (e.g., "1m").
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.

        Raises:
            ValueError: If historical client not initialized.
        """
        if not self._historical_client:
            raise ValueError("Historical client not initialized")

        logger.debug(f"Fetching historical candles for {symbol} from {start} to {end}")

        # Map timeframe string to Alpaca TimeFrame
        timeframe_map = {
            "1m": TimeFrame.Minute,
            "5m": TimeFrame(5, "Min"),
            "15m": TimeFrame(15, "Min"),
            "1h": TimeFrame.Hour,
            "1d": TimeFrame.Day,
        }

        if timeframe not in timeframe_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe_map[timeframe],
            start=start,
            end=end,
        )

        bars = self._historical_client.get_stock_bars(request)

        # Convert to DataFrame
        if symbol not in bars:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        data = []
        for bar in bars[symbol]:
            data.append(
                {
                    "timestamp": bar.timestamp,
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume),
                }
            )

        return pd.DataFrame(data)

    async def get_watchlist_data(self, symbols: list[str]) -> dict[str, Any]:
        """Fetch current data summary for a list of symbols.

        Args:
            symbols: List of ticker symbols.

        Returns:
            Dict keyed by symbol with latest price, volume, indicators.
        """
        result = {}
        for symbol in symbols:
            try:
                price = await self.get_current_price(symbol)
                state = self._indicator_state.get(symbol)
                result[symbol] = {
                    "price": price,
                    "vwap": state.vwap if state else None,
                    "atr_14": state.atr_14 if state else None,
                    "rvol": state.rvol if state else None,
                }
            except ValueError:
                # Symbol not in cache yet
                result[symbol] = None

        return result

    @property
    def is_stale(self) -> bool:
        """Check if data is currently stale (no recent updates)."""
        return self._is_stale

    # --- Internal methods ---

    async def _warm_up_indicators(self, symbols: list[str]) -> None:
        """Fetch historical candles and warm up indicator state.

        Args:
            symbols: List of ticker symbols to warm up.
        """
        logger.info(f"Warming up indicators for {len(symbols)} symbols")

        # Fetch last 60 1m candles for each symbol
        end = self._clock.now()
        start = end - timedelta(minutes=60)

        for symbol in symbols:
            try:
                df = await self.get_historical_candles(symbol, "1m", start, end)

                if df.empty:
                    logger.warning(f"No historical data for {symbol}, skipping warm-up")
                    continue

                # Initialize indicator state
                state = IndicatorState()
                self._indicator_state[symbol] = state

                # Feed historical candles (do NOT publish events during warm-up)
                for _, row in df.iterrows():
                    timestamp = row["timestamp"]
                    candle_date = timestamp.strftime("%Y-%m-%d")

                    # Reset VWAP on new day
                    if state.vwap_date != candle_date:
                        state.vwap_cumulative_tp_volume = 0.0
                        state.vwap_cumulative_volume = 0
                        state.vwap_date = candle_date
                        state.rvol_volume_samples = []
                        state.rvol_baseline_volume = None

                    # Update indicators (same logic as _update_indicators but without publishing)
                    high = row["high"]
                    low = row["low"]
                    close = row["close"]
                    volume = row["volume"]

                    # VWAP
                    typical_price = (high + low + close) / 3
                    state.vwap_cumulative_tp_volume += typical_price * volume
                    state.vwap_cumulative_volume += volume
                    if state.vwap_cumulative_volume > 0:
                        state.vwap = state.vwap_cumulative_tp_volume / state.vwap_cumulative_volume

                    # ATR
                    if state.atr_prev_close is not None:
                        true_range = max(
                            high - low,
                            abs(high - state.atr_prev_close),
                            abs(low - state.atr_prev_close),
                        )
                        state.atr_true_ranges.append(true_range)
                        if len(state.atr_true_ranges) >= 14:
                            if state.atr_14 is None:
                                state.atr_14 = sum(state.atr_true_ranges[-14:]) / 14
                            else:
                                state.atr_14 = (state.atr_14 * 13 + true_range) / 14
                    state.atr_prev_close = close

                    # SMA
                    state.sma_closes.append(close)
                    if len(state.sma_closes) >= 9:
                        state.sma_9 = sum(state.sma_closes[-9:]) / 9
                    if len(state.sma_closes) >= 20:
                        state.sma_20 = sum(state.sma_closes[-20:]) / 20
                    if len(state.sma_closes) >= 50:
                        state.sma_50 = sum(state.sma_closes[-50:]) / 50

                    # RVOL
                    state.rvol_volume_samples.append(volume)
                    if len(state.rvol_volume_samples) >= 20:
                        if state.rvol_baseline_volume is None:
                            state.rvol_baseline_volume = sum(state.rvol_volume_samples[:20]) / 20
                        if state.rvol_baseline_volume > 0:
                            cumulative_volume = sum(state.rvol_volume_samples)
                            num_samples = len(state.rvol_volume_samples)
                            expected_volume = state.rvol_baseline_volume * num_samples
                            state.rvol = cumulative_volume / expected_volume

                logger.debug(
                    f"Warmed up {symbol} with {len(df)} candles. "
                    f"VWAP: {state.vwap:.2f if state.vwap else 'N/A'}, "
                    f"ATR: {state.atr_14:.2f if state.atr_14 else 'N/A'}"
                )

            except Exception as e:
                logger.error(f"Failed to warm up {symbol}: {e}")

        logger.info("Indicator warm-up complete")

    async def _on_bar(self, bar: Bar) -> None:
        """Handler for Alpaca bar stream.

        Called when a completed 1m bar arrives from Alpaca.

        Args:
            bar: Alpaca Bar object.
        """
        symbol = bar.symbol
        timestamp = bar.timestamp

        # Ensure indicator state exists
        if symbol not in self._indicator_state:
            # Create state if not exists (shouldn't happen if warm-up worked)
            self._indicator_state[symbol] = IndicatorState()

        # Update last data time (for stale detection)
        self._last_data_time[symbol] = self._clock.now()

        # Publish CandleEvent
        candle_event = CandleEvent(
            symbol=symbol,
            timeframe="1m",
            timestamp=timestamp,
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=int(bar.volume),
        )
        await self._event_bus.publish(candle_event)

        # Update indicators and publish IndicatorEvents
        await self._update_indicators(symbol, candle_event)

        logger.debug(
            f"Published CandleEvent for {symbol} at {timestamp}, close={bar.close:.2f}"
        )

    async def _on_trade(self, trade: Trade) -> None:
        """Handler for Alpaca trade stream.

        Called on each individual trade from Alpaca.

        Args:
            trade: Alpaca Trade object.
        """
        symbol = trade.symbol
        price = float(trade.price)
        size = int(trade.size)
        timestamp = trade.timestamp

        # Update price cache
        self._price_cache[symbol] = price

        # Update last data time (for stale detection)
        self._last_data_time[symbol] = self._clock.now()

        # Publish TickEvent
        tick_event = TickEvent(
            symbol=symbol,
            timestamp=timestamp,
            price=price,
            volume=size,
        )
        await self._event_bus.publish(tick_event)

    async def _run_stream_with_reconnect(self) -> None:
        """Wrapper around StockDataStream that handles reconnections.

        Implements exponential backoff with jitter on disconnection.
        Publishes system alerts after consecutive failures.
        """
        logger.info("Starting WebSocket stream with reconnection support")

        while self._running:
            try:
                # Run the stream's internal event loop
                await self._data_stream._run_forever()

                # If we get here, stream stopped gracefully
                logger.info("WebSocket stream stopped")
                break

            except Exception as e:
                self._consecutive_failures += 1
                logger.error(
                    f"WebSocket stream error (failure {self._consecutive_failures}): {e}"
                )

                # Alert after max consecutive failures
                if (
                    self._consecutive_failures
                    >= self._alpaca_config.ws_reconnect_max_failures_before_alert
                ):
                    # TODO: Publish SystemAlertEvent when implemented in Sprint 5
                    logger.critical(
                        f"WebSocket reconnection failed {self._consecutive_failures} "
                        f"times consecutively. System alert needed."
                    )

                # Exponential backoff with jitter
                base_delay = self._alpaca_config.ws_reconnect_base_seconds
                max_delay = self._alpaca_config.ws_reconnect_max_seconds
                delay = min(base_delay * (2 ** (self._consecutive_failures - 1)), max_delay)

                # Add jitter (±20%)
                jitter = delay * 0.2 * (random.random() * 2 - 1)
                delay = delay + jitter

                logger.info(f"Reconnecting in {delay:.2f} seconds...")
                await asyncio.sleep(delay)

        logger.info("WebSocket reconnection loop exited")

    async def _stale_data_monitor(self) -> None:
        """Background task that runs every 5 seconds during operation.

        Checks if any subscribed symbol has not received data
        within stale_data_timeout_seconds (default 30s).

        Sets _is_stale flag and publishes alerts as needed.
        """
        logger.info("Starting stale data monitor")

        while self._running:
            await asyncio.sleep(5)

            # TODO: Add market hours check - only monitor during trading hours
            # For now, always monitor

            now = self._clock.now()
            timeout = timedelta(seconds=self._alpaca_config.stale_data_timeout_seconds)

            stale_symbols = []
            for symbol in self._subscribed_symbols:
                last_time = self._last_data_time.get(symbol)
                if last_time is None:
                    # No data received yet (warm-up phase)
                    continue
                if now - last_time > timeout:
                    stale_symbols.append(symbol)

            if stale_symbols and not self._is_stale:
                # Transition to stale
                self._is_stale = True
                logger.warning(f"Data stale for symbols: {stale_symbols}")
                # TODO: Publish SystemAlertEvent when implemented in Sprint 5

            elif not stale_symbols and self._is_stale:
                # Transition to fresh
                self._is_stale = False
                logger.info("Data feed recovered, no longer stale")
                # TODO: Publish recovery event when implemented in Sprint 5

        logger.info("Stale data monitor stopped")

    async def _update_indicators(self, symbol: str, candle: CandleEvent) -> None:
        """Compute indicators and publish IndicatorEvents.

        Uses the same logic as ReplayDataService for consistency.

        Args:
            symbol: Ticker symbol.
            candle: CandleEvent with OHLCV data.
        """
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
            await self._publish_indicator(symbol, "vwap", state.vwap, candle.timestamp)

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

                await self._publish_indicator(symbol, "atr_14", state.atr_14, candle.timestamp)

        state.atr_prev_close = candle.close

        # --- SMA (9, 20, 50) ---
        state.sma_closes.append(candle.close)

        if len(state.sma_closes) >= 9:
            state.sma_9 = sum(state.sma_closes[-9:]) / 9
            await self._publish_indicator(symbol, "sma_9", state.sma_9, candle.timestamp)

        if len(state.sma_closes) >= 20:
            state.sma_20 = sum(state.sma_closes[-20:]) / 20
            await self._publish_indicator(symbol, "sma_20", state.sma_20, candle.timestamp)

        if len(state.sma_closes) >= 50:
            state.sma_50 = sum(state.sma_closes[-50:]) / 50
            await self._publish_indicator(symbol, "sma_50", state.sma_50, candle.timestamp)

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
                expected_volume = state.rvol_baseline_volume * len(state.rvol_volume_samples)
                state.rvol = cumulative_volume / expected_volume
                await self._publish_indicator(symbol, "rvol", state.rvol, candle.timestamp)

    async def _publish_indicator(
        self, symbol: str, indicator: str, value: float, timestamp: datetime
    ) -> None:
        """Publish an IndicatorEvent to the Event Bus.

        Args:
            symbol: Ticker symbol.
            indicator: Indicator name (e.g., "vwap", "atr_14").
            value: Indicator value.
            timestamp: Timestamp of the indicator calculation (unused in event, for logging).
        """
        event = IndicatorEvent(
            symbol=symbol,
            indicator_name=indicator,
            value=value,
        )
        await self._event_bus.publish(event)
