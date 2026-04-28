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
import threading
import time
from datetime import UTC, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import pandas as pd

from argus.core.clock import Clock, SystemClock
from argus.core.config import DatabentoConfig, DataServiceConfig
from argus.core.events import (
    CandleEvent,
    DataResumedEvent,
    DataStaleEvent,
    IndicatorEvent,
    SystemAlertEvent,
    TickEvent,
)
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

        # Last data update timestamp for health endpoint (DEF-076)
        self.last_update: datetime | None = None

        # Symbols we're tracking (populated during start())
        self._active_symbols: set[str] = set()
        self._symbols_list: list[str] = []
        self._timeframes_list: list[str] = []

        # Viable universe for fast-path discard (Sprint 23)
        # When set, only symbols in this set are processed
        # When None, all symbols are processed (backward compatibility)
        self._viable_universe: set[str] | None = None

        # Databento record class references — stored here (not imported at
        # module top) so the ``import databento`` call only runs once when
        # ``_connect_live_session()`` fires. Callback registration in that
        # method is the ONLY site that should invoke ``_dispatch_record``,
        # so the None → type ordering is safe in practice. If a future change
        # registers the callback before the record classes are populated,
        # ``isinstance(record, None)`` will raise ``TypeError`` — treat that
        # as an invariant violation, not a bug-in-isinstance (see
        # FIX-06 audit 2026-04-21, P1-C2-13).
        self._OHLCVMsg: type | None = None
        self._TradeMsg: type | None = None
        self._SymbolMappingMsg: type | None = None
        self._ErrorMsg: type | None = None

        # Data heartbeat tracking (periodic INFO log for visibility)
        self._heartbeat_task: asyncio.Task | None = None
        self._heartbeat_interval_seconds: float = 300.0  # 5 minutes
        self._candles_since_heartbeat: int = 0
        self._symbols_seen_since_heartbeat: set[str] = set()

        # Per-gate drop counters — reset each heartbeat cycle
        self._ohlcv_unmapped_since_heartbeat: int = 0
        self._ohlcv_filtered_universe_since_heartbeat: int = 0
        self._ohlcv_filtered_active_since_heartbeat: int = 0
        self._trades_unmapped_since_heartbeat: int = 0
        self._trades_received_since_heartbeat: int = 0

        # First-event sentinel flags — fire once per session
        self._ohlcv_unmapped_warned: bool = False
        self._first_ohlcv_resolved: bool = False
        self._first_trade_resolved: bool = False

        # Symbol mapping observability
        self._symbol_mappings_received: int = 0

        # Zero-candle escalation: count heartbeat cycles that fell inside market hours
        self._market_hours_heartbeat_count: int = 0

        # Time-aware warm-up state (Sprint 23.7)
        # Mid-session mode: lazy per-symbol backfill on first candle
        # Pre-market mode: no backfill (indicators build from live stream)
        self._mid_session_mode: bool = False
        self._symbols_needing_warmup: set[str] = set()
        self._warmup_lock = threading.Lock()  # Thread-safe access from reader thread

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

        # 7. Start data heartbeat (periodic INFO log for visibility)
        self._heartbeat_task = asyncio.create_task(self._data_heartbeat())

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
                message = (
                    f"Databento max reconnection retries "
                    f"({self._config.reconnect_max_retries}) exceeded. "
                    f"Data feed is DEAD. Manual intervention required."
                )
                logger.critical(message)
                # FIX-06 audit 2026-04-21 (P1-C2 F5 / DEF-014) — publish a
                # SystemAlertEvent so HealthMonitor (and any future Command
                # Center subscriber) can react to the dead feed. Published
                # via the asyncio loop directly since this coroutine already
                # runs on the asyncio thread.
                try:
                    await self._event_bus.publish(
                        SystemAlertEvent(
                            source="databento_feed",
                            alert_type="databento_dead_feed",
                            message=message,
                            severity="critical",
                            # Sprint 31.91 Session 5a.1 (DEF-213): structured
                            # metadata for HealthMonitor consumer + Command
                            # Center alert pane. ``message`` remains the
                            # human-readable form.
                            metadata={
                                "max_retries": self._config.reconnect_max_retries,
                                "detection_source": "databento_data_service.reconnect_loop",
                            },
                        )
                    )
                except Exception:
                    logger.exception(
                        "Failed to publish SystemAlertEvent for "
                        "Databento feed exhaustion"
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

        # Schedule a post-start symbology_map size log (mappings arrive asynchronously)
        asyncio.ensure_future(self._log_post_start_symbology_size())

        logger.info(
            "Connected to Databento: dataset=%s, symbols=%s",
            self._config.dataset,
            subscribe_symbols
            if isinstance(subscribe_symbols, str)
            else f"{len(subscribe_symbols)} symbols",
        )

    async def _log_post_start_symbology_size(self) -> None:
        """Log symbology_map size 2 seconds after session start.

        Databento populates symbology_map asynchronously as SymbolMappingMsg
        records arrive. A brief delay gives the map time to fill before logging.
        Informational only — does not block startup.
        """
        await asyncio.sleep(2.0)
        if self._live_client is not None:
            map_size = len(self._live_client.symbology_map)
            logger.info(
                "Databento session started: symbology_map contains %d instrument IDs",
                map_size,
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

        # Cancel heartbeat task
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task

        logger.info("DatabentoDataService stopped")

    def set_viable_universe(self, symbols: set[str]) -> None:
        """Set the viable symbol universe for fast-path discard.

        When set, only symbols in this set will be processed. Candles and
        ticks for non-viable symbols are discarded before any processing
        or IndicatorEngine creation.

        When set to None (or never called), all symbols are processed
        as before (backward compatibility).

        Args:
            symbols: Set of symbols that are viable for trading.
        """
        self._viable_universe = symbols
        logger.info("Viable universe set: %d symbols", len(symbols))

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
        self.last_update = datetime.now(UTC)

        if isinstance(record, self._OHLCVMsg):
            self._on_ohlcv(record)
        elif isinstance(record, self._TradeMsg):
            self._on_trade(record)
        elif isinstance(record, self._SymbolMappingMsg):
            self._on_symbol_mapping(record)
        elif isinstance(record, self._ErrorMsg):
            self._on_error(record)
        # Other record types (SystemMsg, etc.) are silently ignored

    def _resolve_symbol(self, instrument_id: int) -> str | None:
        """Resolve instrument_id to symbol using Databento's symbology_map.

        The Databento library maintains symbology_map as instrument_id → symbol.
        Direct lookup is O(1).
        """
        if self._live_client:
            # Direct lookup: symbology_map is {instrument_id: symbol}
            return self._live_client.symbology_map.get(instrument_id)

    def _on_symbol_mapping(self, msg: Any) -> None:
        """Handle SymbolMappingMsg — count arrivals and log progress.

        The Databento library populates symbology_map automatically from these
        messages. This callback adds observability on top of that (DEC-242).
        """
        self._symbol_mappings_received += 1
        if self._symbol_mappings_received == 1:
            raw_symbol = getattr(msg, "stype_in_symbol", "?")
            logger.info(
                "First SymbolMappingMsg received (instrument_id=%d → %s)",
                msg.instrument_id,
                raw_symbol,
            )
        elif self._symbol_mappings_received % 2000 == 0:
            logger.info(
                "SymbolMappingMsg progress: %d mappings received",
                self._symbol_mappings_received,
            )

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
            msg.instrument_id — int, Databento instrument identifier
        """
        # Resolve instrument_id → symbol using Databento's symbology_map
        symbol = self._resolve_symbol(msg.instrument_id)
        if symbol is None:
            self._ohlcv_unmapped_since_heartbeat += 1
            if not self._ohlcv_unmapped_warned:
                self._ohlcv_unmapped_warned = True
                map_size = len(self._live_client.symbology_map) if self._live_client else 0
                logger.warning(
                    "OHLCV-1m record dropped — instrument_id=%d not in symbology_map "
                    "(%d IDs mapped). This warning logs once; check heartbeat for counts.",
                    msg.instrument_id,
                    map_size,
                )
            return

        # Fast-path discard for non-viable symbols (Sprint 23)
        # This must be the FIRST check - before any allocation or computation
        if self._viable_universe is not None and symbol not in self._viable_universe:
            self._ohlcv_filtered_universe_since_heartbeat += 1
            return

        # Skip if we're not tracking this symbol
        # (relevant when subscribing to ALL_SYMBOLS but only trading a subset)
        if self._active_symbols and symbol not in self._active_symbols:
            self._ohlcv_filtered_active_since_heartbeat += 1
            return

        # Log first successfully resolved OHLCV symbol (once per session)
        if not self._first_ohlcv_resolved:
            self._first_ohlcv_resolved = True
            map_size = len(self._live_client.symbology_map) if self._live_client else 0
            logger.info(
                "First OHLCV-1m candle resolved: %s (instrument_id=%d, symbology_map size: %d)",
                symbol,
                msg.instrument_id,
                map_size,
            )

        # Lazy warm-up for mid-session boot (Sprint 23.7)
        # On first candle per symbol, fetch today's historical data before processing
        if self._mid_session_mode:
            needs_warmup = False
            with self._warmup_lock:
                if symbol in self._symbols_needing_warmup:
                    needs_warmup = True
                    self._symbols_needing_warmup.discard(symbol)

            if needs_warmup:
                self._lazy_warmup_symbol(symbol)

        # Track for periodic heartbeat logging
        self._candles_since_heartbeat += 1
        self._symbols_seen_since_heartbeat.add(symbol)

        # Convert nanosecond timestamp to datetime
        ts = datetime.fromtimestamp(msg.ts_event / 1e9, tz=UTC)

        # Databento prices are in fixed-point format (scaled by 1e9)
        # Convert to standard floating-point prices
        price_scale = 1e-9

        # Build CandleEvent
        candle_event = CandleEvent(
            symbol=symbol,
            timestamp=ts,
            open=msg.open * price_scale,
            high=msg.high * price_scale,
            low=msg.low * price_scale,
            close=msg.close * price_scale,
            volume=int(msg.volume),
            timeframe="1m",
        )

        # Update price cache (use scaled price)
        self._price_cache[symbol] = msg.close * price_scale

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
            msg.instrument_id — int
        """
        symbol = self._resolve_symbol(msg.instrument_id)
        if symbol is None:
            self._trades_unmapped_since_heartbeat += 1
            return

        # Fast-path discard for non-viable symbols (Sprint 23)
        if self._viable_universe is not None and symbol not in self._viable_universe:
            return

        if self._active_symbols and symbol not in self._active_symbols:
            return

        self._trades_received_since_heartbeat += 1

        # Log first successfully resolved trade (once per session)
        if not self._first_trade_resolved:
            self._first_trade_resolved = True
            map_size = len(self._live_client.symbology_map) if self._live_client else 0
            logger.info(
                "First trade resolved: %s (instrument_id=%d, symbology_map size: %d)",
                symbol,
                msg.instrument_id,
                map_size,
            )

        ts = datetime.fromtimestamp(msg.ts_event / 1e9, tz=UTC)

        # Databento prices are in fixed-point format (scaled by 1e9)
        price = msg.price * 1e-9

        tick_event = TickEvent(
            symbol=symbol,
            timestamp=ts,
            price=price,
            volume=int(msg.size),
        )

        # Update price cache
        self._price_cache[symbol] = price

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
        # FIX-06 audit 2026-04-21 (P1-C2-15): use the stored loop reference
        # rather than ``asyncio.ensure_future`` (which resolves the loop via
        # ``get_event_loop()`` — deprecated outside a running loop in 3.12+).
        # Called via ``call_soon_threadsafe`` so ``self._loop`` is guaranteed
        # non-None by the time these fire.
        assert self._loop is not None  # set in start()
        self._loop.create_task(self._event_bus.publish(candle_event))
        for ind_event in indicator_events:
            self._loop.create_task(self._event_bus.publish(ind_event))

    def _schedule_tick_publish(self, tick_event: TickEvent) -> None:
        """Schedule TickEvent publish as an asyncio task."""
        assert self._loop is not None  # set in start()
        self._loop.create_task(self._event_bus.publish(tick_event))

    def _schedule_stale_event_publish(self, event: DataStaleEvent | DataResumedEvent) -> None:
        """Schedule stale/resumed event publish as an asyncio task."""
        assert self._loop is not None  # set in start()
        self._loop.create_task(self._event_bus.publish(event))

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
        # When viable_universe is set, only create for viable symbols (defense-in-depth)
        if symbol not in self._indicator_engines:
            if self._viable_universe is not None and symbol not in self._viable_universe:
                return []  # Non-viable symbol, no indicator processing
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

        Time-aware behavior (Sprint 23.7):
        - Pre-market (current time <= 9:30 AM ET): Skip warm-up entirely.
          Indicators will build naturally from the live stream.
        - Mid-session (current time > 9:30 AM ET): Enable lazy per-symbol
          backfill mode. On first candle per symbol, fetch today's historical
          data from 9:30 AM to now before processing.

        This replaces the blocking per-symbol warm-up loop, enabling ARGUS
        to start in seconds with a 6,000+ symbol universe.
        """
        # Determine current time in ET for warm-up decision
        et_tz = ZoneInfo("America/New_York")
        now_et = self._clock.now().astimezone(et_tz)
        market_open = dt_time(9, 30, 0)

        if now_et.time() <= market_open:
            # Pre-market boot: skip warm-up, indicators build from live stream
            logger.info(
                "Pre-market boot — skipping indicator warm-up "
                "(indicators will build from live stream)"
            )
            return

        # Mid-session boot: enable lazy per-symbol backfill
        logger.info(
            "Mid-session boot — enabling lazy per-symbol warm-up for %d symbols",
            len(symbols),
        )
        with self._warmup_lock:
            self._mid_session_mode = True
            self._symbols_needing_warmup = set(symbols)

    def _lazy_warmup_symbol(self, symbol: str) -> None:
        """Lazy warm-up for a single symbol during mid-session boot.

        Fetches historical 1m OHLCV from 9:30 AM ET today to now and feeds
        through the IndicatorEngine. Called from the reader thread on first
        candle received for an un-warmed symbol.

        This is a blocking synchronous call. Thread-safe with respect to the
        warm-up tracking state via self._warmup_lock.

        On failure: logs warning, marks symbol as warmed anyway (no retry).
        """
        import databento as db

        start_time = time.monotonic()
        et_tz = ZoneInfo("America/New_York")

        try:
            # Ensure historical client exists
            if self._hist_client is None:
                api_key = os.getenv(self._config.api_key_env_var)
                if not api_key:
                    logger.warning(
                        "Lazy warm-up for %s failed: API key not found", symbol
                    )
                    return
                self._hist_client = db.Historical(key=api_key)

            # Calculate time range: 9:30 AM ET today to now
            now_et = self._clock.now().astimezone(et_tz)
            today = now_et.date()
            market_open_et = datetime.combine(
                today, dt_time(9, 30, 0), tzinfo=et_tz
            )

            # Databento historical API lags ~10min behind live stream (DEC-326)
            _HISTORICAL_LAG_BUFFER = timedelta(seconds=600)
            end_et = now_et - _HISTORICAL_LAG_BUFFER

            if end_et <= market_open_et:
                logger.debug(
                    "Lazy warm-up for %s: clamped end (%s) <= start (%s), "
                    "skipping — indicators will build from live stream",
                    symbol,
                    end_et.strftime("%H:%M:%S"),
                    market_open_et.strftime("%H:%M:%S"),
                )
                return

            # Fetch historical 1m candles
            data = self._hist_client.timeseries.get_range(
                dataset=self._config.dataset,
                symbols=symbol,
                schema="ohlcv-1m",
                start=market_open_et.isoformat(),
                end=end_et.isoformat(),
                stype_in=self._config.stype_in,
            )

            df = data.to_df()

            if df.empty:
                logger.warning(
                    "Lazy warm-up for %s: no historical data available", symbol
                )
                return

            # Normalize and feed through indicator engine
            df = self._normalize_historical_df(df)

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
                # Update indicators — discard returned events during warm-up
                self._update_indicators(symbol, candle)

            elapsed = time.monotonic() - start_time
            logger.info(
                "Lazy warm-up for %s: fetched %d historical candles (%.2fs)",
                symbol,
                len(df),
                elapsed,
            )

        except Exception as e:
            elapsed = time.monotonic() - start_time
            logger.warning(
                "Lazy warm-up for %s failed: %s (%.2fs)", symbol, e, elapsed
            )

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

    async def _data_heartbeat(self) -> None:
        """Periodic log showing data flow activity, including drop counts.

        Logs every 5 minutes. Escalates to WARNING when 0 candles are received
        during market hours after at least 2 market-hours cycles — the April 3
        failure mode that was previously invisible at INFO level.
        """
        _ET = ZoneInfo("America/New_York")
        _MARKET_OPEN = dt_time(9, 30)
        _MARKET_CLOSE = dt_time(16, 0)

        while self._running:
            await asyncio.sleep(self._heartbeat_interval_seconds)

            # Capture and reset all counters atomically
            candle_count = self._candles_since_heartbeat
            symbols_seen = len(self._symbols_seen_since_heartbeat)
            ohlcv_unmapped = self._ohlcv_unmapped_since_heartbeat
            ohlcv_universe = self._ohlcv_filtered_universe_since_heartbeat
            ohlcv_active = self._ohlcv_filtered_active_since_heartbeat
            trades_received = self._trades_received_since_heartbeat
            trades_unmapped = self._trades_unmapped_since_heartbeat

            self._candles_since_heartbeat = 0
            self._symbols_seen_since_heartbeat.clear()
            self._ohlcv_unmapped_since_heartbeat = 0
            self._ohlcv_filtered_universe_since_heartbeat = 0
            self._ohlcv_filtered_active_since_heartbeat = 0
            self._trades_received_since_heartbeat = 0
            self._trades_unmapped_since_heartbeat = 0

            interval_mins = int(self._heartbeat_interval_seconds / 60)

            # Build drop suffix — only when any OHLCV record was silently dropped
            any_ohlcv_drop = ohlcv_unmapped or ohlcv_universe or ohlcv_active
            drop_suffix = (
                f" | dropped: {ohlcv_unmapped} unmapped, "
                f"{ohlcv_universe} universe, {ohlcv_active} active"
                if any_ohlcv_drop
                else ""
            )

            # Build trades suffix — only when trades activity is non-zero
            trades_suffix = (
                f" | trades: {trades_received} received, {trades_unmapped} unmapped"
                if trades_received or trades_unmapped
                else ""
            )

            heartbeat_msg = (
                f"Data heartbeat: {candle_count} candles in last {interval_mins}m "
                f"({symbols_seen} symbols active){drop_suffix}{trades_suffix}"
            )

            # Escalate to WARNING for zero candles during market hours after 2 cycles
            # (suppressed on market holidays — zero candles are expected)
            from argus.core.market_calendar import is_market_holiday

            now_et = datetime.now(tz=_ET).time()
            in_market_hours = _MARKET_OPEN <= now_et < _MARKET_CLOSE

            _today_is_holiday, _holiday_name = is_market_holiday()

            if in_market_hours and not _today_is_holiday:
                self._market_hours_heartbeat_count += 1

            if candle_count == 0 and in_market_hours and _today_is_holiday:
                logger.info(
                    "Data heartbeat: 0 candles in last %dm (market holiday: %s — no data expected)",
                    interval_mins,
                    _holiday_name,
                )
            elif candle_count == 0 and in_market_hours and self._market_hours_heartbeat_count >= 2:
                logger.warning(
                    "%s during market hours — possible data feed failure",
                    heartbeat_msg,
                )
            else:
                logger.info(heartbeat_msg)

    # ──────────────────────────────────────────────
    # Historical Data / Parquet Cache (DEC-085)
    # ──────────────────────────────────────────────

    def _check_parquet_cache(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame | None:
        """Check if requested data exists in local Parquet cache.

        Cache structure: {cache_dir}/{symbol}/{timeframe}/{YYYY-MM}.parquet

        Returns None if any required month file is missing — partial
        coverage is treated as a miss so callers re-fetch the whole range
        rather than receive a silently-truncated frame.

        FIX-06 audit 2026-04-21 (P1-C2-12): was previously single-month only;
        now walks every month in [start, end], concatenates, and returns None
        on any missing month (fail-closed on incomplete coverage).
        """
        cache_dir = Path(self._config.historical_cache_dir)
        if not cache_dir.exists():
            return None

        symbol_dir = cache_dir / symbol / timeframe
        if not symbol_dir.exists():
            return None

        # Enumerate every month covered by [start, end] in chronological order.
        months: list[str] = []
        cursor = datetime(start.year, start.month, 1, tzinfo=start.tzinfo)
        last_month = datetime(end.year, end.month, 1, tzinfo=end.tzinfo)
        while cursor <= last_month:
            months.append(cursor.strftime("%Y-%m"))
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1)

        frames: list[pd.DataFrame] = []
        for month_key in months:
            cache_file = symbol_dir / f"{month_key}.parquet"
            if not cache_file.exists():
                # Partial coverage — force caller to re-fetch the range.
                return None
            try:
                frames.append(pd.read_parquet(cache_file))
            except Exception as e:
                logger.warning("Error reading cache file %s: %s", cache_file, e)
                return None

        if not frames:
            return None

        df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        if "timestamp" not in df.columns:
            return None

        df = df[(df["timestamp"] >= start) & (df["timestamp"] <= end)]
        if df.empty:
            return None

        logger.debug(
            "Cache hit for %s %s across %d month(s)",
            symbol,
            timeframe,
            len(months),
        )
        return df.sort_values("timestamp").reset_index(drop=True)

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
        """Fetch daily OHLCV bars for regime classification via FMP API.

        Uses the FMP stable historical-price-eod endpoint (available on Starter
        plan). Called once at startup and periodically (~every 5 min) for regime
        reclassification — not hot path.

        Args:
            symbol: Ticker symbol (e.g., "SPY").
            lookback_days: Number of trading days to return.

        Returns:
            DataFrame with columns [date, open, high, low, close, volume],
            sorted ascending by date, limited to lookback_days rows.
            Returns None on any error (graceful degradation).
        """
        import aiohttp

        api_key = os.getenv("FMP_API_KEY")
        if not api_key:
            logger.warning("fetch_daily_bars: FMP_API_KEY not set, returning None")
            return None

        url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
        # WARNING (FIX-06 audit 2026-04-21, P1-C2-11 / DEF-037): ``params``
        # carries the FMP API key. The error handlers below intentionally
        # log ONLY ``symbol`` and ``response.status`` / ``str(e)`` — never
        # ``response.url`` or ``params``. Adding URL/params to any error
        # log here would leak the key into logs. Mirror-safe redaction
        # now lives in argus/data/fmp_reference.py::_safe_error_context.
        params = {"symbol": symbol, "apikey": api_key}

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.info(
                            "fetch_daily_bars: FMP returned HTTP %d for %s",
                            response.status,
                            symbol,
                        )
                        return None

                    data = await response.json()

            if not isinstance(data, list) or not data:
                logger.info("fetch_daily_bars: empty or invalid response for %s", symbol)
                return None

            df = pd.DataFrame(data)

            # Ensure required columns exist
            required_cols = {"date", "open", "high", "low", "close", "volume"}
            if not required_cols.issubset(df.columns):
                logger.info(
                    "fetch_daily_bars: missing columns for %s (got %s)",
                    symbol,
                    list(df.columns),
                )
                return None

            # Keep only required columns
            df = df[["date", "open", "high", "low", "close", "volume"]].copy()

            # Sort ascending by date (FMP returns newest first)
            df = df.sort_values("date", ascending=True).reset_index(drop=True)

            # Limit to lookback_days most recent rows
            if len(df) > lookback_days:
                df = df.tail(lookback_days).reset_index(drop=True)

            logger.info(
                "fetch_daily_bars: fetched %d daily bars for %s via FMP",
                len(df),
                symbol,
            )
            return df

        except asyncio.TimeoutError:
            logger.info("fetch_daily_bars: timeout fetching %s from FMP", symbol)
            return None
        except Exception as e:
            logger.info("fetch_daily_bars: error fetching %s from FMP: %s", symbol, e)
            return None
