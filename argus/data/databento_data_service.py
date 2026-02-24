"""DatabentoDataService — Primary production market data service.

Implements the DataService ABC using Databento's Live and Historical clients.
Single TCP session with Event Bus fan-out to all consumers (DEC-082).

Indicator computation delegated to IndicatorEngine (DEF-013).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from argus.core.clock import Clock, SystemClock
from argus.core.config import DatabentoConfig, DataServiceConfig
from argus.core.events import (
    CandleEvent,
    DataResumedEvent,
    DataStaleEvent,
    IndicatorEvent,
    TickEvent,
)
from argus.data.databento_symbol_map import DatabentoSymbolMap
from argus.data.databento_utils import normalize_databento_df
from argus.data.indicator_engine import IndicatorEngine
from argus.data.service import DataService

if TYPE_CHECKING:
    from argus.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class DatabentoDataService(DataService):
    """Primary production market data service using Databento.

    Connects to Databento's live TCP streaming service. Subscribes to
    OHLCV-1m bars and trades streams. Computes indicators (VWAP, ATR,
    SMA, RVOL) matching existing DataService behavior. Publishes
    CandleEvents, TickEvents, and IndicatorEvents through the Event Bus.

    Single live session with Event Bus fan-out — one Databento TCP
    connection serves all strategies and consumers (DEC-082).

    Args:
        event_bus: The system Event Bus for publishing market data events.
        config: DatabentoConfig with connection and subscription settings.
        data_config: Shared DataServiceConfig with indicator parameters.
        clock: Optional Clock for testability (DEC-039/MD-4a-5).
    """

    def __init__(
        self,
        event_bus: EventBus,
        config: DatabentoConfig,
        data_config: DataServiceConfig,
        clock: Clock | None = None,
    ) -> None:
        """Initialize DatabentoDataService.

        Args:
            event_bus: Event bus for publishing market data events.
            config: Databento-specific configuration.
            data_config: Data service configuration.
            clock: Injectable clock (defaults to SystemClock).
        """
        self._event_bus = event_bus
        self._config = config
        self._data_config = data_config
        self._clock = clock if clock is not None else SystemClock()

        # Databento clients — created in start(), destroyed in stop()
        self._live_client: Any = None  # db.Live
        self._hist_client: Any = None  # db.Historical

        # Symbol mapping
        self._symbol_map = DatabentoSymbolMap()

        # Price and indicator caches (same pattern as AlpacaDataService)
        self._price_cache: dict[str, float] = {}
        self._indicator_cache: dict[tuple[str, str], float] = {}

        # Indicator engines per symbol (DEF-013)
        self._indicator_engines: dict[str, IndicatorEngine] = {}

        # State
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stale_monitor_task: asyncio.Task | None = None
        self._stream_task: asyncio.Task | None = None
        self._last_message_time: float = 0.0
        self._stale_published = False

        # Symbols we're tracking (populated during start())
        self._active_symbols: set[str] = set()
        self._symbols_list: list[str] = []
        self._timeframes_list: list[str] = []

        # Databento record class references (stored in start() to avoid hot-path imports)
        self._OHLCVMsg: type | None = None
        self._TradeMsg: type | None = None
        self._SymbolMappingMsg: type | None = None
        self._ErrorMsg: type | None = None

    # ──────────────────────────────────────────────
    # DataService ABC Implementation
    # ──────────────────────────────────────────────

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Start streaming live data from Databento with reconnection support.

        1. Validate API key exists
        2. Store event loop reference for thread bridging
        3. Perform initial connection (synchronous for API compatibility)
        4. Perform indicator warm-up
        5. Launch reconnection wrapper task (handles subsequent reconnects)
        6. Launch stale data monitor task

        Args:
            symbols: List of ticker symbols to stream. If the config has
                     "ALL_SYMBOLS", this parameter is ignored and the full
                     universe is streamed.
            timeframes: Timeframes to stream (currently only "1m" used).
        """
        if self._running:
            logger.warning("DatabentoDataService already running")
            return

        # 1. Validate API key exists
        api_key = os.getenv(self._config.api_key_env_var)
        if not api_key:
            raise RuntimeError(
                f"Databento API key not found in environment variable "
                f"'{self._config.api_key_env_var}'. Set it in your .env file."
            )

        # 2. Store event loop reference for thread bridging
        self._loop = asyncio.get_running_loop()
        self._running = True
        self._active_symbols = set(symbols)
        self._symbols_list = symbols
        self._timeframes_list = timeframes

        # 3. Indicator warm-up — fetch recent historical bars
        await self._warm_up_indicators(symbols)

        # 4. Perform initial connection (synchronous for API compatibility)
        await self._connect_live_session()

        # 5. Launch reconnection wrapper as a task (handles subsequent reconnects)
        self._stream_task = asyncio.create_task(self._run_with_reconnection())

        # 6. Start stale data monitor
        self._stale_monitor_task = asyncio.create_task(self._stale_data_monitor())

        logger.info(
            "DatabentoDataService started: dataset=%s, symbols=%d, schemas=[%s, %s]",
            self._config.dataset,
            len(symbols),
            self._config.bar_schema,
            self._config.trade_schema,
        )

    async def _run_with_reconnection(self) -> None:
        """Main streaming loop with exponential backoff reconnection.

        Manages the lifecycle of the Databento Live client:
        1. Wait for close (initial connection made in start())
        2. If unexpected disconnect, reconnect with backoff
        3. If max retries exceeded, log critical and stop

        Note: The initial connection is made synchronously in start() before
        this task is launched. This task handles subsequent reconnections.
        """
        retries = 0
        first_iteration = True

        while self._running:
            try:
                # On first iteration, we're already connected (done in start())
                # On subsequent iterations, we need to reconnect
                if not first_iteration:
                    await self._connect_live_session()
                    # Reset retry counter on successful connection
                    retries = 0

                first_iteration = False

                # Wait for the session to end
                # Use block_for_close() in a thread since it's blocking
                if self._live_client is not None:
                    await asyncio.to_thread(self._live_client.block_for_close)

                if not self._running:
                    break  # Clean shutdown via stop()

                # Unexpected disconnect — reconnect
                logger.warning("Databento session ended unexpectedly")

            except Exception as e:
                logger.error("Databento stream error: %s", e)

            if not self._running:
                break

            # Reconnection logic
            retries += 1
            if retries > self._config.reconnect_max_retries:
                logger.critical(
                    "Databento max reconnection retries (%d) exceeded. "
                    "Data feed is DEAD. Manual intervention required.",
                    self._config.reconnect_max_retries,
                )
                break

            delay = min(
                self._config.reconnect_base_delay_seconds * (2 ** (retries - 1)),
                self._config.reconnect_max_delay_seconds,
            )
            logger.warning(
                "Reconnecting to Databento in %.1fs (attempt %d/%d)",
                delay,
                retries,
                self._config.reconnect_max_retries,
            )
            await asyncio.sleep(delay)

        logger.info("Reconnection loop exited (running=%s, retries=%d)", self._running, retries)

    async def _connect_live_session(self) -> None:
        """Create a new Databento Live client and subscribe to streams.

        Extracted from start() so it can be called on each reconnection attempt.
        Sets up record class references for _dispatch_record() (DEC-088).
        """
        import databento as db

        api_key = os.getenv(self._config.api_key_env_var)

        # Clean up previous client if exists
        if self._live_client is not None:
            with contextlib.suppress(Exception):
                self._live_client.stop()

        # Create fresh client
        self._live_client = db.Live(key=api_key)

        # Clear symbol map — new session will send fresh mappings
        self._symbol_map.clear()

        # Determine symbols to subscribe
        subscribe_symbols: str | list[str]
        if isinstance(self._config.symbols, list):
            subscribe_symbols = self._config.symbols
        elif self._config.symbols == "ALL_SYMBOLS":
            subscribe_symbols = "ALL_SYMBOLS"
        else:
            subscribe_symbols = self._symbols_list

        # Subscribe to bar stream
        self._live_client.subscribe(
            dataset=self._config.dataset,
            schema=self._config.bar_schema,
            symbols=subscribe_symbols,
            stype_in=self._config.stype_in,
        )

        # Subscribe to trades stream
        self._live_client.subscribe(
            dataset=self._config.dataset,
            schema=self._config.trade_schema,
            symbols=subscribe_symbols,
            stype_in=self._config.stype_in,
        )

        # (Optional) Subscribe to L2 depth
        if self._config.enable_depth:
            self._live_client.subscribe(
                dataset=self._config.dataset,
                schema=self._config.depth_schema,
                symbols=subscribe_symbols,
                stype_in=self._config.stype_in,
            )

        # Register callback
        self._live_client.add_callback(self._dispatch_record)

        # Store record class references for _dispatch_record() (DEC-088)
        self._OHLCVMsg = db.OHLCVMsg
        self._TradeMsg = db.TradeMsg
        self._SymbolMappingMsg = db.SymbolMappingMsg
        self._ErrorMsg = db.ErrorMsg

        # Start streaming
        self._live_client.start()
        self._last_message_time = time.monotonic()

        logger.info(
            "Connected to Databento: dataset=%s, symbols=%s",
            self._config.dataset,
            subscribe_symbols
            if isinstance(subscribe_symbols, str)
            else f"{len(subscribe_symbols)} symbols",
        )

    async def stop(self) -> None:
        """Stop streaming and clean up.

        1. Set running flag to False (signals reconnection loop to exit)
        2. Stop the Databento Live client (closes TCP connection)
        3. Cancel stream task
        4. Cancel stale monitor task
        5. Clean up state
        """
        if not self._running:
            return

        self._running = False

        # Stop Databento client (will cause block_for_close to return)
        if self._live_client is not None:
            try:
                self._live_client.stop()
            except Exception as e:
                logger.warning("Error stopping Databento live client: %s", e)
            self._live_client = None

        # Cancel stream task (reconnection loop)
        if self._stream_task and not self._stream_task.done():
            self._stream_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stream_task

        # Cancel stale monitor
        if self._stale_monitor_task and not self._stale_monitor_task.done():
            self._stale_monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stale_monitor_task

        self._symbol_map.clear()
        logger.info("DatabentoDataService stopped")

    async def get_current_price(self, symbol: str) -> float | None:
        """Return the latest trade price from the in-memory cache.

        Updated on every trade received via the trades stream.
        Returns None if no price available for symbol.
        """
        return self._price_cache.get(symbol)

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Return latest computed indicator value from cache.

        Key format: 'vwap', 'atr_14', 'sma_9', 'sma_20', 'sma_50', 'rvol'.
        Returns None if indicator not available.
        """
        return self._indicator_cache.get((symbol, indicator))

    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fetch historical candles via Databento Historical API.

        Checks local Parquet cache first (DEC-085). If not cached,
        queries Databento Historical API, caches result, returns DataFrame.

        Returns DataFrame with columns: timestamp, open, high, low, close, volume.
        Same schema as Alpaca historical data for compatibility.
        """
        import databento as db

        # Check Parquet cache first
        cached = self._check_parquet_cache(symbol, timeframe, start, end)
        if cached is not None:
            return cached

        # Query Databento Historical API
        if self._hist_client is None:
            api_key = os.getenv(self._config.api_key_env_var)
            if not api_key:
                raise RuntimeError(
                    f"Databento API key not found in environment variable "
                    f"'{self._config.api_key_env_var}'."
                )
            self._hist_client = db.Historical(key=api_key)

        # Map timeframe to Databento schema
        schema = f"ohlcv-{timeframe}" if not timeframe.startswith("ohlcv") else timeframe

        data = self._hist_client.timeseries.get_range(
            dataset=self._config.dataset,
            symbols=symbol,
            schema=schema,
            start=start.isoformat(),
            end=end.isoformat(),
            stype_in=self._config.stype_in,
        )

        df = data.to_df()

        if df.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        # Normalize to our standard schema
        result = self._normalize_historical_df(df)

        # Cache as Parquet
        self._save_parquet_cache(symbol, timeframe, start, end, result)

        return result

    async def get_watchlist_data(self, symbols: list[str]) -> dict[str, Any]:
        """Fetch current data summary for a list of symbols.

        Returns dict keyed by symbol with latest price and indicators.
        """
        result: dict[str, Any] = {}
        for symbol in symbols:
            price = self._price_cache.get(symbol)
            indicators = {k[1]: v for k, v in self._indicator_cache.items() if k[0] == symbol}
            result[symbol] = {
                "price": price,
                "indicators": indicators,
            }
        return result

    @property
    def is_stale(self) -> bool:
        """Check if data is currently stale (no recent updates)."""
        return self._stale_published

    @property
    def symbol_map(self) -> DatabentoSymbolMap:
        """Access the symbol map for testing and debugging."""
        return self._symbol_map

    # ──────────────────────────────────────────────
    # Callback Dispatch (runs on Databento's reader thread)
    # ──────────────────────────────────────────────

    def _dispatch_record(self, record: Any) -> None:
        """Main callback registered with Databento Live client.

        Dispatches based on record type. Runs on Databento's internal
        reader thread — must bridge to asyncio for Event Bus publishing.

        Uses isinstance checks with stored class references to avoid
        importing databento on every message (hot path optimization).
        """
        self._last_message_time = time.monotonic()

        if isinstance(record, self._OHLCVMsg):
            self._on_ohlcv(record)
        elif isinstance(record, self._TradeMsg):
            self._on_trade(record)
        elif isinstance(record, self._SymbolMappingMsg):
            self._on_symbol_mapping(record)
        elif isinstance(record, self._ErrorMsg):
            self._on_error(record)
        # Other record types (SystemMsg, etc.) are silently ignored

    def _on_symbol_mapping(self, msg: Any) -> None:
        """Process SymbolMappingMsg — populate the symbol map.

        These arrive at session start before any data messages.
        Runs on Databento's reader thread.
        """
        self._symbol_map.on_symbol_mapping(msg)

    def _on_ohlcv(self, msg: Any) -> None:
        """Process OHLCVMsg — convert to CandleEvent, update indicators.

        Runs on Databento's reader thread. Bridges to asyncio for Event Bus.

        Databento OHLCVMsg fields:
            msg.open     — float, bar open price
            msg.high     — float, bar high price
            msg.low      — float, bar low price
            msg.close    — float, bar close price
            msg.volume   — int, bar volume
            msg.ts_event — int, nanosecond Unix timestamp (bar OPEN time)
            msg.hd.instrument_id — int, Databento instrument identifier
        """
        # Resolve instrument_id → symbol
        symbol = self._symbol_map.get_symbol(msg.hd.instrument_id)
        if symbol is None:
            logger.debug(
                "Unknown instrument_id=%d in OHLCVMsg (mapping not yet received)",
                msg.hd.instrument_id,
            )
            return

        # Skip if we're not tracking this symbol
        # (relevant when subscribing to ALL_SYMBOLS but only trading a subset)
        if self._active_symbols and symbol not in self._active_symbols:
            return

        # Convert nanosecond timestamp to datetime
        ts = datetime.fromtimestamp(msg.ts_event / 1e9, tz=UTC)

        # Build CandleEvent
        candle_event = CandleEvent(
            symbol=symbol,
            timestamp=ts,
            open=msg.open,
            high=msg.high,
            low=msg.low,
            close=msg.close,
            volume=int(msg.volume),
            timeframe="1m",
        )

        # Update price cache
        self._price_cache[symbol] = msg.close

        # Update indicators
        indicator_events = self._update_indicators(symbol, candle_event)

        # Bridge to asyncio — schedule publishes on the event loop
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                self._schedule_candle_publish, candle_event, indicator_events
            )

    def _on_trade(self, msg: Any) -> None:
        """Process TradeMsg — convert to TickEvent, update price cache.

        Runs on Databento's reader thread.

        Databento TradeMsg fields:
            msg.price    — float, trade price
            msg.size     — int, trade size (shares)
            msg.ts_event — int, nanosecond Unix timestamp
            msg.hd.instrument_id — int
        """
        symbol = self._symbol_map.get_symbol(msg.hd.instrument_id)
        if symbol is None:
            return

        if self._active_symbols and symbol not in self._active_symbols:
            return

        ts = datetime.fromtimestamp(msg.ts_event / 1e9, tz=UTC)

        tick_event = TickEvent(
            symbol=symbol,
            timestamp=ts,
            price=msg.price,
            volume=int(msg.size),
        )

        # Update price cache
        self._price_cache[symbol] = msg.price

        # Bridge to asyncio
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._schedule_tick_publish, tick_event)

    def _on_error(self, msg: Any) -> None:
        """Process ErrorMsg — log and potentially trigger alerts.

        Runs on Databento's reader thread.
        """
        logger.error("Databento ErrorMsg: %s", msg.err)

    # ──────────────────────────────────────────────
    # Asyncio Bridge Methods (called via call_soon_threadsafe)
    # ──────────────────────────────────────────────

    def _schedule_candle_publish(
        self, candle_event: CandleEvent, indicator_events: list[IndicatorEvent]
    ) -> None:
        """Schedule CandleEvent and IndicatorEvent publishes as asyncio tasks."""
        asyncio.ensure_future(self._event_bus.publish(candle_event))
        for ind_event in indicator_events:
            asyncio.ensure_future(self._event_bus.publish(ind_event))

    def _schedule_tick_publish(self, tick_event: TickEvent) -> None:
        """Schedule TickEvent publish as an asyncio task."""
        asyncio.ensure_future(self._event_bus.publish(tick_event))

    def _schedule_stale_event_publish(self, event: DataStaleEvent | DataResumedEvent) -> None:
        """Schedule stale/resumed event publish as an asyncio task."""
        asyncio.ensure_future(self._event_bus.publish(event))

    # ──────────────────────────────────────────────
    # Indicator Computation
    # ──────────────────────────────────────────────

    def _update_indicators(self, symbol: str, candle: CandleEvent) -> list[IndicatorEvent]:
        """Update indicators for a symbol after receiving a new candle.

        Delegates to IndicatorEngine for computation (DEF-013).

        Updates self._indicator_cache and returns a list of IndicatorEvent
        objects to publish.
        """
        # Get or create indicator engine for this symbol
        if symbol not in self._indicator_engines:
            self._indicator_engines[symbol] = IndicatorEngine(symbol)

        engine = self._indicator_engines[symbol]
        events: list[IndicatorEvent] = []

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

        # Update cache and build events for non-None indicators
        if values.vwap is not None:
            self._indicator_cache[(symbol, "vwap")] = values.vwap
            events.append(
                IndicatorEvent(
                    symbol=symbol,
                    indicator_name="vwap",
                    value=values.vwap,
                )
            )

        if values.atr_14 is not None:
            self._indicator_cache[(symbol, "atr_14")] = values.atr_14
            events.append(
                IndicatorEvent(
                    symbol=symbol,
                    indicator_name="atr_14",
                    value=values.atr_14,
                )
            )

        if values.sma_9 is not None:
            self._indicator_cache[(symbol, "sma_9")] = values.sma_9
            events.append(
                IndicatorEvent(
                    symbol=symbol,
                    indicator_name="sma_9",
                    value=values.sma_9,
                )
            )

        if values.sma_20 is not None:
            self._indicator_cache[(symbol, "sma_20")] = values.sma_20
            events.append(
                IndicatorEvent(
                    symbol=symbol,
                    indicator_name="sma_20",
                    value=values.sma_20,
                )
            )

        if values.sma_50 is not None:
            self._indicator_cache[(symbol, "sma_50")] = values.sma_50
            events.append(
                IndicatorEvent(
                    symbol=symbol,
                    indicator_name="sma_50",
                    value=values.sma_50,
                )
            )

        if values.rvol is not None:
            self._indicator_cache[(symbol, "rvol")] = values.rvol
            events.append(
                IndicatorEvent(
                    symbol=symbol,
                    indicator_name="rvol",
                    value=values.rvol,
                )
            )

        return events

    async def _warm_up_indicators(self, symbols: list[str]) -> None:
        """Fetch recent historical bars to warm up indicator engines.

        Fetches enough historical bars (at least 50 for SMA(50)) for each
        symbol and feeds them through _update_indicators(). Events are
        discarded during warm-up (not published to Event Bus).

        Uses get_historical_candles() or queries Databento Historical directly.
        This runs once at startup before live streaming begins.
        """
        logger.info("Warming up indicators for %d symbols", len(symbols))

        # Fetch last 60 1m candles for each symbol
        end = self._clock.now()
        start = end - timedelta(minutes=60)

        for symbol in symbols:
            try:
                df = await self.get_historical_candles(symbol, "1m", start, end)

                if df.empty:
                    logger.warning("No historical data for %s, skipping warm-up", symbol)
                    continue

                # Feed historical candles through _update_indicators()
                # (reuses live indicator logic — events are discarded during warm-up)
                for _, row in df.iterrows():
                    candle = CandleEvent(
                        symbol=symbol,
                        timestamp=row["timestamp"],
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=int(row["volume"]),
                        timeframe="1m",
                    )
                    # Update indicators — ignore returned events during warm-up
                    self._update_indicators(symbol, candle)

                engine = self._indicator_engines.get(symbol)
                vwap_str = f"{engine.vwap:.2f}" if engine and engine.vwap else "N/A"
                atr_str = f"{engine.atr_14:.2f}" if engine and engine.atr_14 else "N/A"
                logger.debug(
                    "Warmed up %s with %d candles. VWAP: %s, ATR: %s",
                    symbol,
                    len(df),
                    vwap_str,
                    atr_str,
                )

            except Exception as e:
                logger.error("Failed to warm up %s: %s", symbol, e)

        logger.info("Indicator warm-up complete")

    # ──────────────────────────────────────────────
    # Stale Data Monitor (RSK-021 mitigation)
    # ──────────────────────────────────────────────

    async def _stale_data_monitor(self) -> None:
        """Monitor for data feed staleness.

        If no messages received within stale_data_timeout_seconds,
        publish a DataStaleEvent to halt new trade entries.
        When data resumes, publish DataResumedEvent.

        This is a critical safety feature — trading blind is unacceptable.
        """
        while self._running:
            await asyncio.sleep(5.0)  # Check every 5 seconds
            elapsed = time.monotonic() - self._last_message_time
            if elapsed > self._config.stale_data_timeout_seconds:
                if not self._stale_published:
                    logger.warning(
                        "Data feed stale for %.1fs (threshold: %.1fs)",
                        elapsed,
                        self._config.stale_data_timeout_seconds,
                    )
                    # Publish stale event
                    event = DataStaleEvent(
                        provider="databento",
                        seconds_since_last=elapsed,
                    )
                    await self._event_bus.publish(event)
                    self._stale_published = True
            elif self._stale_published:
                logger.info("Data feed resumed after stale period")
                # Publish resumed event
                event = DataResumedEvent(provider="databento")
                await self._event_bus.publish(event)
                self._stale_published = False

    # ──────────────────────────────────────────────
    # Historical Data / Parquet Cache (DEC-085)
    # ──────────────────────────────────────────────

    def _check_parquet_cache(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame | None:
        """Check if requested data exists in local Parquet cache.

        Cache structure: {cache_dir}/{symbol}/{timeframe}/{YYYY-MM}.parquet

        Returns None if not cached or partial coverage.
        """
        cache_dir = Path(self._config.historical_cache_dir)
        if not cache_dir.exists():
            return None

        symbol_dir = cache_dir / symbol / timeframe
        if not symbol_dir.exists():
            return None

        # For simplicity, check if we have a file covering the date range
        # Full implementation would merge multiple monthly files
        start_month = start.strftime("%Y-%m")
        cache_file = symbol_dir / f"{start_month}.parquet"

        if not cache_file.exists():
            return None

        try:
            df = pd.read_parquet(cache_file)
            # Filter to requested range
            if "timestamp" in df.columns:
                df = df[(df["timestamp"] >= start) & (df["timestamp"] <= end)]
                if not df.empty:
                    logger.debug("Cache hit for %s %s %s", symbol, timeframe, start_month)
                    return df
        except Exception as e:
            logger.warning("Error reading cache file %s: %s", cache_file, e)

        return None

    def _save_parquet_cache(
        self, symbol: str, timeframe: str, start: datetime, end: datetime, df: pd.DataFrame
    ) -> None:
        """Save historical data to local Parquet cache.

        Cache structure: {cache_dir}/{symbol}/{timeframe}/{YYYY-MM}.parquet
        """
        if df.empty:
            return

        cache_dir = Path(self._config.historical_cache_dir)
        symbol_dir = cache_dir / symbol / timeframe

        try:
            symbol_dir.mkdir(parents=True, exist_ok=True)

            # Save by month
            start_month = start.strftime("%Y-%m")
            cache_file = symbol_dir / f"{start_month}.parquet"

            df.to_parquet(cache_file, index=False)
            logger.debug("Cached %d rows to %s", len(df), cache_file)

        except Exception as e:
            logger.warning("Error saving cache file: %s", e)

    @staticmethod
    def _normalize_historical_df(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Databento historical DataFrame to ARGUS standard schema.

        Delegates to shared utility function for consistency with DataFetcher.
        """
        return normalize_databento_df(df)

    async def fetch_daily_bars(self, symbol: str, lookback_days: int = 60) -> pd.DataFrame | None:
        """Fetch daily OHLCV bars for regime classification.

        DatabentoDataService does not support daily bar fetching in V1.
        Returns None. The Orchestrator should handle None by using a fallback regime.

        Future: When Databento subscription is active, implement via Historical API.

        Args:
            symbol: Ticker symbol (e.g., "SPY").
            lookback_days: Number of trading days to fetch.

        Returns:
            None — daily bars not yet implemented for Databento.
        """
        return None
