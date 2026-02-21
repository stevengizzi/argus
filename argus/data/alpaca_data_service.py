"""Alpaca live data service implementation using WebSocket and REST APIs.

This module provides real-time market data streaming from Alpaca via WebSocket,
with historical data fetching for indicator warm-up via REST API.

Indicator computation delegated to IndicatorEngine (DEF-013).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import random
from datetime import datetime, timedelta
from datetime import time as dt_time
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import pandas as pd
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.live import StockDataStream
from alpaca.data.models import Bar, Trade
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from argus.core.clock import Clock, SystemClock
from argus.core.config import AlpacaConfig, DataServiceConfig
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent, TickEvent
from argus.data.indicator_engine import IndicatorEngine
from argus.data.service import DataService

if TYPE_CHECKING:
    from argus.core.health import HealthMonitor

logger = logging.getLogger(__name__)


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
        _indicator_engines: IndicatorEngine instances per symbol (DEF-013).
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
        health_monitor: HealthMonitor | None = None,
    ):
        """Initialize AlpacaDataService.

        Args:
            event_bus: Event bus for publishing market data events.
            config: Alpaca-specific configuration.
            data_config: Data service configuration.
            clock: Injectable clock (defaults to SystemClock).
            health_monitor: Optional health monitor for status updates.
        """
        self._event_bus = event_bus
        self._alpaca_config = config
        self._data_config = data_config
        self._clock = clock if clock is not None else SystemClock()
        self._health_monitor = health_monitor

        # WebSocket and REST clients (initialized in start())
        self._data_stream: StockDataStream | None = None
        self._historical_client: StockHistoricalDataClient | None = None

        # State
        self._price_cache: dict[str, float] = {}
        self._indicator_engines: dict[str, IndicatorEngine] = {}
        self._last_data_time: dict[str, datetime] = {}
        self._is_stale = False
        self._stream_task: asyncio.Task | None = None
        self._monitor_task: asyncio.Task | None = None
        self._subscribed_symbols: set[str] = set()
        self._running = False
        self._consecutive_failures = 0
        self._first_bar_logged = False
        self._first_trade_logged = False

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

        # Map config data_feed string to DataFeed enum
        feed_map = {"iex": DataFeed.IEX, "sip": DataFeed.SIP}
        data_feed_enum = feed_map.get(self._alpaca_config.data_feed.lower(), DataFeed.IEX)

        # Initialize data stream (WebSocket)
        self._data_stream = StockDataStream(
            api_key=api_key,
            secret_key=secret_key,
            feed=data_feed_enum,
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
        self._stream_task.add_done_callback(self._task_done_callback)

        # Start stale data monitor
        self._monitor_task = asyncio.create_task(self._stale_data_monitor())
        self._monitor_task.add_done_callback(self._task_done_callback)

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
            with contextlib.suppress(asyncio.CancelledError):
                await self._stream_task

        if self._monitor_task:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task

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
        engine = self._indicator_engines.get(symbol)
        if engine is None:
            raise ValueError(f"No indicator state for {symbol}")

        indicator_map = {
            "vwap": engine.vwap,
            "atr_14": engine.atr_14,
            "sma_9": engine.sma_9,
            "sma_20": engine.sma_20,
            "sma_50": engine.sma_50,
            "rvol": engine.rvol,
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

        # Map config data_feed string to DataFeed enum
        feed_map = {
            "iex": DataFeed.IEX,
            "sip": DataFeed.SIP,
        }
        feed = feed_map.get(self._alpaca_config.data_feed.lower(), DataFeed.IEX)

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=timeframe_map[timeframe],
            start=start,
            end=end,
            feed=feed,
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
                engine = self._indicator_engines.get(symbol)
                result[symbol] = {
                    "price": price,
                    "vwap": engine.vwap if engine else None,
                    "atr_14": engine.atr_14 if engine else None,
                    "rvol": engine.rvol if engine else None,
                }
            except ValueError:
                # Symbol not in cache yet
                result[symbol] = None

        return result

    @property
    def is_stale(self) -> bool:
        """Check if data is currently stale (no recent updates)."""
        return self._is_stale

    async def fetch_todays_bars(self, symbols: list[str]) -> list[CandleEvent]:
        """Fetch today's 1m bars from Alpaca REST API for reconstruction.

        Returns CandleEvent objects in chronological order, suitable for
        replaying through strategies during mid-day restart reconstruction.

        Uses StockHistoricalDataClient.get_stock_bars() with:
        - timeframe: 1Min
        - start: today at 9:30 AM ET
        - end: now

        Args:
            symbols: List of ticker symbols to fetch.

        Returns:
            List of CandleEvent objects sorted by timestamp.
        """
        et_tz = ZoneInfo("America/New_York")
        now = self._clock.now()
        now_et = now.replace(tzinfo=et_tz) if now.tzinfo is None else now.astimezone(et_tz)

        today_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)

        events: list[CandleEvent] = []

        if not self._historical_client:
            # Initialize client if not already done
            api_key = os.getenv(self._alpaca_config.api_key_env)
            secret_key = os.getenv(self._alpaca_config.secret_key_env)
            if not api_key or not secret_key:
                logger.error("Cannot fetch today's bars: API keys not configured")
                return events
            self._historical_client = StockHistoricalDataClient(api_key, secret_key)

        for symbol in symbols:
            try:
                df = await self.get_historical_candles(
                    symbol=symbol,
                    timeframe="1m",
                    start=today_open,
                    end=now_et,
                )

                for _, row in df.iterrows():
                    events.append(CandleEvent(
                        symbol=symbol,
                        timeframe="1m",
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                        timestamp=row["timestamp"],
                    ))

            except Exception as e:
                logger.error("Failed to fetch today's bars for %s: %s", symbol, e)

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        logger.info("Fetched %d bars for reconstruction from %d symbols", len(events), len(symbols))
        return events

    # --- Internal methods ---

    def _task_done_callback(self, task: asyncio.Task) -> None:
        """Log any exceptions from background tasks that would otherwise be silent.

        Args:
            task: The completed asyncio Task.
        """
        try:
            exc = task.exception()
            if exc is not None:
                logger.critical(
                    f"Background task '{task.get_name()}' died with exception: {exc!r}",
                    exc_info=exc,
                )
        except asyncio.CancelledError:
            # Task was cancelled, not an error
            logger.debug(f"Background task '{task.get_name()}' was cancelled")

    async def _warm_up_indicators(self, symbols: list[str]) -> None:
        """Fetch historical candles and warm up indicator state.

        Delegates to IndicatorEngine for computation (DEF-013).

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

                # Initialize indicator engine
                engine = IndicatorEngine(symbol)
                self._indicator_engines[symbol] = engine

                # Feed historical candles through engine (do NOT publish events during warm-up)
                for _, row in df.iterrows():
                    timestamp = row["timestamp"]
                    candle_date = timestamp.strftime("%Y-%m-%d")

                    engine.update(
                        open_=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=int(row["volume"]),
                        timestamp_date=candle_date,
                    )

                vwap_str = f"{engine.vwap:.2f}" if engine.vwap else "N/A"
                atr_str = f"{engine.atr_14:.2f}" if engine.atr_14 else "N/A"
                logger.debug(
                    f"Warmed up {symbol} with {len(df)} candles. "
                    f"VWAP: {vwap_str}, ATR: {atr_str}"
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

        # Log first bar received to confirm stream is working
        if not self._first_bar_logged:
            self._first_bar_logged = True
            logger.info(
                f"First bar received from WebSocket: {symbol} @ {timestamp}, "
                f"close={bar.close:.2f}, volume={bar.volume}"
            )

        # Ensure indicator engine exists
        if symbol not in self._indicator_engines:
            # Create engine if not exists (shouldn't happen if warm-up worked)
            self._indicator_engines[symbol] = IndicatorEngine(symbol)

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

        # Log first trade received to confirm stream is working
        if not self._first_trade_logged:
            self._first_trade_logged = True
            logger.info(
                f"First trade received from WebSocket: {symbol} @ ${price:.2f}, "
                f"size={size}, timestamp={timestamp}"
            )

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
        logger.info(
            f"WebSocket config: feed={self._alpaca_config.data_feed}, "
            f"bars={self._alpaca_config.subscribe_bars}, "
            f"trades={self._alpaca_config.subscribe_trades}, "
            f"symbols={list(self._subscribed_symbols)}"
        )

        while self._running:
            try:
                logger.info("Connecting to Alpaca WebSocket stream...")
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

        Only checks during market hours on weekdays (RSK-015 fix).
        Sets _is_stale flag and updates health status as needed.
        """
        logger.info("Starting stale data monitor")

        et_tz = ZoneInfo("America/New_York")
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        no_data_warning_logged = False

        while self._running:
            try:
                await asyncio.sleep(5)

                now = self._clock.now()

                # Convert to ET for market hours check
                now_et = (now.replace(tzinfo=et_tz) if now.tzinfo is None
                          else now.astimezone(et_tz))

                # Only check for stale data during market hours on weekdays
                if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
                    continue
                if not (market_open <= now_et.time() <= market_close):
                    continue

                timeout = timedelta(seconds=self._alpaca_config.stale_data_timeout_seconds)

                stale_symbols = []
                never_received = []
                for symbol in self._subscribed_symbols:
                    last_time = self._last_data_time.get(symbol)
                    if last_time is None:
                        # No data ever received for this symbol
                        never_received.append(symbol)
                    elif now - last_time > timeout:
                        stale_symbols.append(symbol)

                # If no data ever received for ALL symbols, that's a problem worth logging
                # Only log once to avoid spamming
                if never_received and len(never_received) == len(self._subscribed_symbols):
                    if not no_data_warning_logged:
                        no_data_warning_logged = True
                        logger.warning(
                            f"No data received from WebSocket for any symbol during "
                            f"market hours. Symbols: {never_received}. "
                            f"Check WebSocket connection and feed subscription."
                        )
                elif never_received:
                    # Some symbols have data, some don't — reset the flag if we recover
                    no_data_warning_logged = False

                if stale_symbols and not self._is_stale:
                    # Transition to stale
                    self._is_stale = True
                    logger.warning(f"Data stale for symbols: {stale_symbols}")
                    # Update health status if monitor available
                    if self._health_monitor:
                        from argus.core.health import ComponentStatus
                        self._health_monitor.update_component(
                            "data_service",
                            ComponentStatus.DEGRADED,
                            message=f"Stale data for: {', '.join(stale_symbols)}",
                        )

                elif not stale_symbols and self._is_stale:
                    # Transition to fresh
                    self._is_stale = False
                    logger.info("Data feed recovered, no longer stale")
                    # Update health status if monitor available
                    if self._health_monitor:
                        from argus.core.health import ComponentStatus
                        self._health_monitor.update_component(
                            "data_service",
                            ComponentStatus.HEALTHY,
                            message="Data feed active",
                        )

            except Exception as e:
                logger.error(f"Error in stale data monitor loop: {e}", exc_info=True)
                # Don't crash the monitor, continue checking
                await asyncio.sleep(5)

        logger.info("Stale data monitor stopped")

    async def _update_indicators(self, symbol: str, candle: CandleEvent) -> None:
        """Compute indicators and publish IndicatorEvents.

        Delegates to IndicatorEngine for computation (DEF-013).

        Args:
            symbol: Ticker symbol.
            candle: CandleEvent with OHLCV data.
        """
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
            await self._publish_indicator(symbol, "vwap", values.vwap, candle.timestamp)

        if values.atr_14 is not None:
            await self._publish_indicator(symbol, "atr_14", values.atr_14, candle.timestamp)

        if values.sma_9 is not None:
            await self._publish_indicator(symbol, "sma_9", values.sma_9, candle.timestamp)

        if values.sma_20 is not None:
            await self._publish_indicator(symbol, "sma_20", values.sma_20, candle.timestamp)

        if values.sma_50 is not None:
            await self._publish_indicator(symbol, "sma_50", values.sma_50, candle.timestamp)

        if values.rvol is not None:
            await self._publish_indicator(symbol, "rvol", values.rvol, candle.timestamp)

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
