# Sprint 12 — DatabentoDataService Adapter (Prompt 1 of 2)

> **For Claude Code.** This is the implementation spec for Sprint 12, Components 1–3.
> After completing this prompt, pause for review. The user will provide a second prompt for Components 4–6.

---

## Sprint Context

**Previous sprint:** Sprint 11 (Extended Backtest) — ✅ COMPLETE. 542 tests. 35 months of data, 15 walk-forward windows, WFE=0.56.

**This sprint:** Build the DatabentoDataService adapter — ARGUS's primary production market data service. This replaces the Alpaca IEX feed (which only captures 2–3% of market volume) with institutional-grade exchange-direct data.

**Key decisions already made:**
- DEC-082: Databento US Equities Standard ($199/mo) as primary data backbone
- DEC-085: Historical data from Databento, cached as Parquet. Existing Alpaca Parquet retained.
- DEC-087: Databento subscription activated at end of sprint for integration testing, not before. All dev/tests use mocks.
- DEC-029: Event Bus is the sole streaming delivery mechanism. No callback subscription on DataService.

**Target:** ~110 new tests across 6 components. This prompt covers Components 1–3 (~65 tests).

**Databento Python client:** `databento` (official, pip install). Current version ~0.71.0. Uses `DATABENTO_API_KEY` environment variable automatically.

---

## Dependency Setup

**Add to requirements/dependencies:**
```
databento>=0.40.0
```

**Add to `.env` template (but NOT `.env` itself — that has real keys):**
```
DATABENTO_API_KEY=db-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Verify `.env` is in `.gitignore`.** This should already be the case from Sprint 4a.

---

## Component 1: DatabentoConfig (`argus/config/databento_config.py`)

**Purpose:** Pydantic configuration model for Databento connectivity. Follows the existing pattern established by `AlpacaConfig` — stores env var names, not actual keys.

```python
"""Configuration for Databento market data service."""

from pydantic import BaseModel, field_validator


class DatabentoConfig(BaseModel):
    """Configuration for Databento market data connectivity.

    API key is read from environment variable at runtime, never stored in config.
    Follows the same pattern as AlpacaConfig (DEC-032).
    """

    # API key — name of the environment variable containing the key
    api_key_env_var: str = "DATABENTO_API_KEY"

    # Dataset selection — determines which exchange feeds are included
    # XNAS.ITCH = Nasdaq TotalView-ITCH (recommended for trading firms)
    # Full universe, L2/L3 available, deepest historical data
    dataset: str = "XNAS.ITCH"

    # Schema subscriptions for live streaming
    bar_schema: str = "ohlcv-1m"     # Completed 1-minute OHLCV bars → CandleEvents
    trade_schema: str = "trades"      # Individual trades → TickEvents + price cache
    depth_schema: str = "mbp-10"      # L2 10-level depth (when enabled)
    enable_depth: bool = False         # L2 depth subscription off by default

    # Symbol configuration
    # Either a list of specific symbols ["AAPL", "TSLA", ...]
    # or the string "ALL_SYMBOLS" for full universe subscription
    symbols: list[str] | str = "ALL_SYMBOLS"

    # Symbology type for input symbols
    # "raw_symbol" = exchange-native ticker (e.g., "AAPL")
    # "instrument_id" = Databento internal numeric ID
    stype_in: str = "raw_symbol"

    # Session management
    reconnect_max_retries: int = 10
    reconnect_base_delay_seconds: float = 1.0
    reconnect_max_delay_seconds: float = 60.0

    # Circuit breaker — halt new trades if no data received within this window
    # Mitigates RSK-021 (data feed failure during live trading)
    stale_data_timeout_seconds: float = 30.0

    # Historical data cache directory (DEC-085)
    historical_cache_dir: str = "data/databento_cache"

    @field_validator("dataset")
    @classmethod
    def validate_dataset(cls, v: str) -> str:
        """Validate dataset is a known Databento US equities dataset."""
        known_datasets = {
            "XNAS.ITCH",      # Nasdaq TotalView-ITCH (primary recommendation)
            "XNAS.BASIC",     # Nasdaq Basic with NLS Plus
            "XNYS.PILLAR",    # NYSE Integrated
            "ARCX.PILLAR",    # NYSE Arca Integrated
            "XASE.PILLAR",    # NYSE American Integrated
            "DBEQ.BASIC",     # Databento Equities Basic (free tier)
            "XBOS.ITCH",      # Nasdaq BX TotalView-ITCH
            "XPSX.ITCH",      # Nasdaq PSX TotalView-ITCH
            "XCHI.PILLAR",    # NYSE Chicago Integrated
            "XCIS.TRADESBBO", # NYSE National Trades and BBO
            "EQUS.SUMMARY",   # Consolidated summary (delayed)
        }
        if v not in known_datasets:
            raise ValueError(
                f"Unknown dataset '{v}'. Known datasets: {sorted(known_datasets)}"
            )
        return v

    @field_validator("bar_schema")
    @classmethod
    def validate_bar_schema(cls, v: str) -> str:
        valid = {"ohlcv-1s", "ohlcv-1m", "ohlcv-1h", "ohlcv-1d"}
        if v not in valid:
            raise ValueError(f"Invalid bar_schema '{v}'. Valid: {sorted(valid)}")
        return v

    @field_validator("stype_in")
    @classmethod
    def validate_stype_in(cls, v: str) -> str:
        valid = {"raw_symbol", "instrument_id", "smart"}
        if v not in valid:
            raise ValueError(f"Invalid stype_in '{v}'. Valid: {sorted(valid)}")
        return v
```

**Add DatabentoConfig to the main config loader.** The existing YAML → Pydantic flow (DEC-032) should gain a `databento:` section. Add it alongside the existing `alpaca:` section — both can coexist since AlpacaDataService is retained for the incubator pipeline (DEC-086).

**Tests (~10):**
1. Default config creates successfully
2. Custom dataset validates
3. Invalid dataset raises ValueError
4. Invalid bar_schema raises ValueError
5. Invalid stype_in raises ValueError
6. Symbols as list works
7. Symbols as "ALL_SYMBOLS" string works
8. Reconnection defaults are sane
9. Config serialization round-trip (dict → model → dict)
10. Config integrates into main YAML config structure

---

## Component 2: DatabentoSymbolMap (`argus/data/databento_symbol_map.py`)

**Purpose:** Bidirectional mapping between Databento's integer `instrument_id` and human-readable ticker symbols. This is critical because every Databento message uses `instrument_id` in its header — we need to resolve these to ticker symbols for the rest of ARGUS.

**Why this is needed:** Alpaca sends string symbols directly on every message. Databento sends a numeric `instrument_id` for efficiency. At session start, Databento sends `SymbolMappingMsg` events that establish the mapping. We must process these before we can interpret any bar or trade data.

```python
"""Bidirectional symbol mapping for Databento instrument_id ↔ ticker symbol."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import databento as db

logger = logging.getLogger(__name__)


class DatabentoSymbolMap:
    """Bidirectional mapping between Databento instrument_ids and ticker symbols.

    Populated by SymbolMappingMsg events during live session startup.
    Also supports manual population for testing and historical data.

    Thread-safe: The Databento Live client fires callbacks on its internal
    reader thread, so updates to this map must be safe for concurrent access.
    In practice, SymbolMappingMsg events arrive before any data messages,
    so race conditions are unlikely, but we use a simple dict (GIL-protected
    for single-word operations) as the backing store.
    """

    def __init__(self) -> None:
        self._id_to_symbol: dict[int, str] = {}
        self._symbol_to_id: dict[str, int] = {}

    def on_symbol_mapping(self, msg: db.SymbolMappingMsg) -> None:
        """Process a SymbolMappingMsg to update the mapping.

        Args:
            msg: Databento SymbolMappingMsg with instrument_id and
                 stype_in_symbol (the human-readable ticker).
        """
        instrument_id = msg.instrument_id
        # stype_in_symbol is the ticker in the input symbology type
        symbol = msg.stype_in_symbol

        if not symbol or symbol == "":
            logger.warning(
                "Empty symbol in SymbolMappingMsg for instrument_id=%d", instrument_id
            )
            return

        # Handle remapping (instrument_id can change for a symbol during session)
        old_symbol = self._id_to_symbol.get(instrument_id)
        if old_symbol and old_symbol != symbol:
            logger.info(
                "Remapping instrument_id=%d: %s → %s", instrument_id, old_symbol, symbol
            )
            del self._symbol_to_id[old_symbol]

        self._id_to_symbol[instrument_id] = symbol
        self._symbol_to_id[symbol] = instrument_id
        logger.debug("Mapped %s → instrument_id=%d", symbol, instrument_id)

    def add_mapping(self, instrument_id: int, symbol: str) -> None:
        """Manually add a mapping (for testing or historical data).

        Args:
            instrument_id: Databento numeric instrument identifier.
            symbol: Human-readable ticker symbol.
        """
        self._id_to_symbol[instrument_id] = symbol
        self._symbol_to_id[symbol] = instrument_id

    def get_symbol(self, instrument_id: int) -> str | None:
        """Resolve instrument_id → ticker symbol.

        Returns None if the instrument_id hasn't been mapped yet.
        """
        return self._id_to_symbol.get(instrument_id)

    def get_instrument_id(self, symbol: str) -> int | None:
        """Resolve ticker symbol → instrument_id.

        Returns None if the symbol hasn't been mapped yet.
        """
        return self._symbol_to_id.get(symbol)

    def has_symbol(self, symbol: str) -> bool:
        """Check if a ticker symbol is in the map."""
        return symbol in self._symbol_to_id

    def has_instrument_id(self, instrument_id: int) -> bool:
        """Check if an instrument_id is in the map."""
        return instrument_id in self._id_to_symbol

    @property
    def symbol_count(self) -> int:
        """Number of mapped symbols."""
        return len(self._id_to_symbol)

    def all_symbols(self) -> list[str]:
        """Return all mapped ticker symbols."""
        return list(self._symbol_to_id.keys())

    def clear(self) -> None:
        """Clear all mappings (for session reset)."""
        self._id_to_symbol.clear()
        self._symbol_to_id.clear()
```

**Tests (~15):**
1. Empty map returns None for lookups
2. `add_mapping()` creates bidirectional mapping
3. `get_symbol()` returns correct symbol
4. `get_instrument_id()` returns correct id
5. `has_symbol()` returns True/False correctly
6. `has_instrument_id()` returns True/False correctly
7. `symbol_count` reflects current state
8. `all_symbols()` returns list of all symbols
9. `on_symbol_mapping()` processes SymbolMappingMsg correctly
10. Remapping logs and updates correctly (same instrument_id, different symbol)
11. Empty symbol in mapping message is ignored with warning
12. Multiple symbols can be mapped simultaneously
13. `clear()` removes all mappings
14. Large number of mappings (1000+) works correctly
15. `on_symbol_mapping()` with mock SymbolMappingMsg object

**Mock for SymbolMappingMsg:** Create a simple dataclass or namedtuple that mimics the fields Claude Code needs:
```python
@dataclass
class MockSymbolMappingMsg:
    instrument_id: int
    stype_in_symbol: str
```
This avoids importing the real `databento` library in unit tests (which may not be installed in CI).

---

## Component 3: DatabentoDataService — Core Live Streaming (`argus/data/databento_data_service.py`)

**Purpose:** Implements the `DataService` ABC using Databento's Live client for streaming and Historical client for on-demand queries. This is ARGUS's primary production data service.

**Architecture:**

```
Databento Live Client (TCP, internal reader thread)
    │
    ├── SymbolMappingMsg  → DatabentoSymbolMap (populate)
    ├── OHLCVMsg          → _on_ohlcv() → CandleEvent + IndicatorEvents → Event Bus
    ├── TradeMsg          → _on_trade() → TickEvent → Event Bus
    └── ErrorMsg          → _on_error() → log + alert
    
    Note: Callbacks fire on Databento's internal reader thread.
    Bridge to asyncio via loop.call_soon_threadsafe().
```

### Threading Model (Critical Design Detail)

The Databento Python `Live` client runs an internal reader thread that fires callbacks. ARGUS's Event Bus is asyncio-based. We bridge with `loop.call_soon_threadsafe()`:

```python
# In callback (runs on Databento's reader thread):
def _on_ohlcv(self, msg: db.OHLCVMsg) -> None:
    # Build CandleEvent synchronously (fast, no I/O)
    event = self._build_candle_event(msg)
    if event is not None:
        # Schedule async publish on the event loop
        self._loop.call_soon_threadsafe(
            self._schedule_publish, event
        )

def _schedule_publish(self, event):
    """Schedule an event publish as an asyncio task."""
    asyncio.ensure_future(self._event_bus.publish(event), loop=self._loop)
```

### Databento Price Format

The Python `databento` library automatically converts fixed-point prices to Python floats. `OHLCVMsg.open`, `.high`, `.low`, `.close` are all `float`. `TradeMsg.price` is `float`. `TradeMsg.size` is `int`. No manual conversion needed in Python (unlike the C/Rust clients).

### Full Class Structure

```python
"""DatabentoDataService — Primary production market data service.

Implements the DataService ABC using Databento's Live and Historical clients.
Single TCP session with Event Bus fan-out to all consumers (DEC-082).
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from functools import singledispatch
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import databento as db

from argus.config.databento_config import DatabentoConfig
from argus.config.models import DataServiceConfig
from argus.core.events import CandleEvent, IndicatorEvent, TickEvent
from argus.data.base import DataService
from argus.data.databento_symbol_map import DatabentoSymbolMap

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
        event_bus,  # EventBus
        config: DatabentoConfig,
        data_config: DataServiceConfig,
        clock=None,  # Clock protocol
    ) -> None:
        self._event_bus = event_bus
        self._config = config
        self._data_config = data_config
        self._clock = clock

        # Databento clients — created in start(), destroyed in stop()
        self._live_client = None   # db.Live
        self._hist_client = None   # db.Historical

        # Symbol mapping
        self._symbol_map = DatabentoSymbolMap()

        # Price and indicator caches (same pattern as AlpacaDataService)
        self._price_cache: dict[str, float] = {}
        self._indicator_cache: dict[tuple[str, str], float] = {}

        # Indicator computation engines — reuse the EXACT same logic
        # as AlpacaDataService / BacktestDataService.
        # Claude Code: Extract/import the indicator computation from
        # the existing codebase. The indicators must compute identically
        # across all DataService implementations.
        self._indicator_engines: dict[str, object] = {}  # symbol → IndicatorEngine

        # State
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stream_task: asyncio.Task | None = None
        self._stale_monitor_task: asyncio.Task | None = None
        self._last_message_time: float = 0.0
        self._stale_published = False

        # Symbols we're tracking (populated during start())
        self._active_symbols: set[str] = set()

    # ──────────────────────────────────────────────
    # DataService ABC Implementation
    # ──────────────────────────────────────────────

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Start streaming live data from Databento.

        1. Resolve API key from environment variable
        2. Store reference to the running event loop (for thread bridging)
        3. Create db.Live() client
        4. Subscribe to ohlcv-1m and trades schemas
        5. Register singledispatch callback handler
        6. Fetch historical candles for indicator warm-up
        7. Start the live stream (non-blocking — runs on internal thread)
        8. Start stale data monitor task

        Args:
            symbols: List of ticker symbols to stream. If the config has
                     "ALL_SYMBOLS", this parameter is ignored and the full
                     universe is streamed.
            timeframes: Timeframes to stream (currently only "1m" used).
        """
        import databento as db

        if self._running:
            logger.warning("DatabentoDataService already running")
            return

        # 1. Resolve API key
        api_key = os.getenv(self._config.api_key_env_var)
        if not api_key:
            raise RuntimeError(
                f"Databento API key not found in environment variable "
                f"'{self._config.api_key_env_var}'. Set it in your .env file."
            )

        # 2. Store event loop reference for thread bridging
        self._loop = asyncio.get_running_loop()
        self._running = True

        # 3. Determine symbols to subscribe
        subscribe_symbols = self._config.symbols
        if isinstance(subscribe_symbols, list):
            # Use configured symbols, but also accept the passed-in list
            # if config says ALL_SYMBOLS
            pass
        elif subscribe_symbols == "ALL_SYMBOLS":
            subscribe_symbols = "ALL_SYMBOLS"
        else:
            subscribe_symbols = symbols

        self._active_symbols = set(symbols)

        # 4. Create Live client
        self._live_client = db.Live(key=api_key)

        # 5. Subscribe to bar stream
        self._live_client.subscribe(
            dataset=self._config.dataset,
            schema=self._config.bar_schema,
            symbols=subscribe_symbols,
            stype_in=self._config.stype_in,
        )

        # 6. Subscribe to trades stream
        self._live_client.subscribe(
            dataset=self._config.dataset,
            schema=self._config.trade_schema,
            symbols=subscribe_symbols,
            stype_in=self._config.stype_in,
        )

        # 7. (Optional) Subscribe to L2 depth
        if self._config.enable_depth:
            self._live_client.subscribe(
                dataset=self._config.dataset,
                schema=self._config.depth_schema,
                symbols=subscribe_symbols,
                stype_in=self._config.stype_in,
            )

        # 8. Register callback using singledispatch pattern
        self._live_client.add_callback(self._dispatch_record)

        # 9. Indicator warm-up — fetch recent historical bars
        # Claude Code: Replicate the warm-up pattern from AlpacaDataService.
        # Fetch the last N bars (enough for ATR(14) + SMA(50)) for each
        # symbol from the Historical API or from local Parquet cache.
        await self._warm_up_indicators(symbols)

        # 10. Start live stream (non-blocking — Databento manages its own thread)
        self._live_client.start()
        self._last_message_time = time.monotonic()

        # 11. Start stale data monitor
        self._stale_monitor_task = asyncio.create_task(
            self._stale_data_monitor()
        )

        logger.info(
            "DatabentoDataService started: dataset=%s, symbols=%s, schemas=[%s, %s]",
            self._config.dataset,
            subscribe_symbols if isinstance(subscribe_symbols, str)
            else f"{len(subscribe_symbols)} symbols",
            self._config.bar_schema,
            self._config.trade_schema,
        )

    async def stop(self) -> None:
        """Stop streaming and clean up.

        1. Set running flag to False
        2. Stop stale monitor task
        3. Stop the Databento Live client (closes TCP connection)
        4. Clean up state
        """
        if not self._running:
            return

        self._running = False

        # Cancel stale monitor
        if self._stale_monitor_task and not self._stale_monitor_task.done():
            self._stale_monitor_task.cancel()
            try:
                await self._stale_monitor_task
            except asyncio.CancelledError:
                pass

        # Stop Databento client
        if self._live_client is not None:
            try:
                self._live_client.stop()
            except Exception as e:
                logger.warning("Error stopping Databento live client: %s", e)
            self._live_client = None

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
            self._hist_client = db.Historical(key=api_key)

        data = self._hist_client.timeseries.get_range(
            dataset=self._config.dataset,
            symbols=symbol,
            schema=f"ohlcv-{timeframe}" if not timeframe.startswith("ohlcv") else timeframe,
            start=start.isoformat(),
            end=end.isoformat(),
            stype_in=self._config.stype_in,
        )

        df = data.to_df()

        if df.empty:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        # Normalize to our standard schema
        result = self._normalize_historical_df(df)

        # Cache as Parquet
        self._save_parquet_cache(symbol, timeframe, start, end, result)

        return result

    async def get_watchlist_data(self, symbols: list[str]) -> dict:
        """Fetch current data summary for a list of symbols.

        Returns dict keyed by symbol with latest price and indicators.
        """
        result = {}
        for symbol in symbols:
            price = self._price_cache.get(symbol)
            indicators = {
                k[1]: v
                for k, v in self._indicator_cache.items()
                if k[0] == symbol
            }
            result[symbol] = {
                "price": price,
                "indicators": indicators,
            }
        return result

    # ──────────────────────────────────────────────
    # Callback Dispatch (runs on Databento's reader thread)
    # ──────────────────────────────────────────────

    def _dispatch_record(self, record) -> None:
        """Main callback registered with Databento Live client.

        Dispatches based on record type. Runs on Databento's internal
        reader thread — must bridge to asyncio for Event Bus publishing.

        Uses isinstance checks rather than functools.singledispatch because
        singledispatch doesn't work well with method callbacks. The pattern
        is equivalent.
        """
        import databento as db

        self._last_message_time = time.monotonic()

        if isinstance(record, db.OHLCVMsg):
            self._on_ohlcv(record)
        elif isinstance(record, db.TradeMsg):
            self._on_trade(record)
        elif isinstance(record, db.SymbolMappingMsg):
            self._on_symbol_mapping(record)
        elif isinstance(record, db.ErrorMsg):
            self._on_error(record)
        # Other record types (SystemMsg, etc.) are silently ignored

    def _on_symbol_mapping(self, msg) -> None:
        """Process SymbolMappingMsg — populate the symbol map.

        These arrive at session start before any data messages.
        Runs on Databento's reader thread.
        """
        self._symbol_map.on_symbol_mapping(msg)

    def _on_ohlcv(self, msg) -> None:
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
        ts = datetime.fromtimestamp(msg.ts_event / 1e9, tz=timezone.utc)

        # Build CandleEvent
        candle_event = CandleEvent(
            symbol=symbol,
            timestamp=ts,
            open=msg.open,
            high=msg.high,
            low=msg.low,
            close=msg.close,
            volume=msg.volume,
            timeframe="1m",
        )

        # Update price cache
        self._price_cache[symbol] = msg.close

        # Update indicators
        # Claude Code: Call the indicator engine for this symbol.
        # This must use the EXACT same indicator computation as
        # AlpacaDataService and BacktestDataService.
        indicator_events = self._update_indicators(symbol, candle_event)

        # Bridge to asyncio — schedule publishes on the event loop
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                self._schedule_candle_publish, candle_event, indicator_events
            )

    def _on_trade(self, msg) -> None:
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

        ts = datetime.fromtimestamp(msg.ts_event / 1e9, tz=timezone.utc)

        tick_event = TickEvent(
            symbol=symbol,
            timestamp=ts,
            price=msg.price,
            size=msg.size,
        )

        # Update price cache
        self._price_cache[symbol] = msg.price

        # Bridge to asyncio
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                self._schedule_tick_publish, tick_event
            )

    def _on_error(self, msg) -> None:
        """Process ErrorMsg — log and potentially trigger alerts.

        Runs on Databento's reader thread.
        """
        logger.error("Databento ErrorMsg: %s", msg.err)

    # ──────────────────────────────────────────────
    # Asyncio Bridge Methods (called via call_soon_threadsafe)
    # ──────────────────────────────────────────────

    def _schedule_candle_publish(self, candle_event, indicator_events):
        """Schedule CandleEvent and IndicatorEvent publishes as asyncio tasks."""
        asyncio.ensure_future(self._event_bus.publish(candle_event))
        for ind_event in indicator_events:
            asyncio.ensure_future(self._event_bus.publish(ind_event))

    def _schedule_tick_publish(self, tick_event):
        """Schedule TickEvent publish as an asyncio task."""
        asyncio.ensure_future(self._event_bus.publish(tick_event))

    # ──────────────────────────────────────────────
    # Indicator Computation
    # ──────────────────────────────────────────────

    def _update_indicators(self, symbol: str, candle: CandleEvent) -> list:
        """Update indicators for a symbol after receiving a new candle.

        Claude Code: This method MUST use the exact same indicator
        computation logic as AlpacaDataService._update_indicators()
        and BacktestDataService.feed_bar(). Extract the shared logic
        into a common module if not already done, or import it.

        Indicators to compute: VWAP, ATR(14), SMA(9), SMA(20), SMA(50), RVOL.

        Updates self._indicator_cache and returns a list of IndicatorEvent
        objects to publish.
        """
        # Claude Code implements this by reusing existing indicator logic
        indicator_events = []
        # ... indicator computation ...
        # ... update self._indicator_cache[(symbol, indicator_name)] = value ...
        # ... build IndicatorEvent for each updated indicator ...
        return indicator_events

    async def _warm_up_indicators(self, symbols: list[str]) -> None:
        """Fetch recent historical bars to warm up indicator engines.

        Claude Code: Replicate the warm-up pattern from AlpacaDataService.
        Fetch enough historical bars (at least 50 for SMA(50)) for each
        symbol and feed them through the indicator engines.

        Use get_historical_candles() or query Databento Historical directly.
        This runs once at startup before live streaming begins.
        """
        logger.info("Warming up indicators for %d symbols", len(symbols))
        # Claude Code implements this
        pass

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
                    # Claude Code: Define DataStaleEvent/DataResumedEvent
                    # or use a DataHealthEvent with status enum
                    self._stale_published = True
            elif self._stale_published:
                logger.info("Data feed resumed after stale period")
                self._stale_published = False

    # ──────────────────────────────────────────────
    # Historical Data / Parquet Cache (DEC-085)
    # ──────────────────────────────────────────────

    def _check_parquet_cache(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame | None:
        """Check if requested data exists in local Parquet cache.

        Claude Code: Implement file-based cache lookup.
        Cache key: {cache_dir}/{symbol}/{timeframe}/{YYYY-MM}.parquet
        Return None if not cached.
        """
        return None  # Claude Code implements

    def _save_parquet_cache(
        self, symbol: str, timeframe: str, start: datetime, end: datetime,
        df: pd.DataFrame
    ) -> None:
        """Save historical data to local Parquet cache."""
        pass  # Claude Code implements

    @staticmethod
    def _normalize_historical_df(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Databento historical DataFrame to ARGUS standard schema.

        Databento's to_df() returns columns like:
            ts_event, open, high, low, close, volume, ...

        ARGUS standard schema:
            timestamp, open, high, low, close, volume

        Ensures timestamps are UTC-aware. Same output as Alpaca historical
        data for full compatibility with VectorBT and Replay Harness.
        """
        result = df[["ts_event", "open", "high", "low", "close", "volume"]].copy()
        result = result.rename(columns={"ts_event": "timestamp"})

        # Ensure UTC-aware timestamps
        if result["timestamp"].dt.tz is None:
            result["timestamp"] = result["timestamp"].dt.tz_localize("UTC")
        elif str(result["timestamp"].dt.tz) != "UTC":
            result["timestamp"] = result["timestamp"].dt.tz_convert("UTC")

        return result.sort_values("timestamp").reset_index(drop=True)
```

### New Events Needed

Define `DataStaleEvent` and `DataResumedEvent` (or a combined `DataHealthEvent`):

```python
# In argus/core/events.py (or wherever events are defined)

@dataclass
class DataStaleEvent:
    """Published when the data feed has not received messages for too long.
    Strategies should halt new entries. Order Manager should NOT close existing positions.
    """
    timestamp: datetime
    provider: str  # "databento", "alpaca", etc.
    seconds_since_last: float

@dataclass
class DataResumedEvent:
    """Published when a previously stale data feed resumes."""
    timestamp: datetime
    provider: str
```

### Mocking Strategy for Tests

**Do NOT import `databento` at module level.** Use `TYPE_CHECKING` guard and lazy imports inside methods. This allows tests to run without the `databento` package installed.

Create mock classes for testing:

```python
# tests/mocks/mock_databento.py

from dataclasses import dataclass, field


@dataclass
class MockRecordHeader:
    instrument_id: int = 0
    length: int = 0
    rtype: int = 0
    publisher_id: int = 0
    ts_event: int = 0


@dataclass
class MockOHLCVMsg:
    """Mock Databento OHLCVMsg for unit tests."""
    hd: MockRecordHeader = field(default_factory=MockRecordHeader)
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    ts_event: int = 0  # Nanosecond Unix timestamp


@dataclass
class MockTradeMsg:
    """Mock Databento TradeMsg for unit tests."""
    hd: MockRecordHeader = field(default_factory=MockRecordHeader)
    price: float = 0.0
    size: int = 0
    ts_event: int = 0


@dataclass
class MockSymbolMappingMsg:
    """Mock Databento SymbolMappingMsg for unit tests."""
    instrument_id: int = 0
    stype_in_symbol: str = ""


@dataclass
class MockErrorMsg:
    """Mock Databento ErrorMsg for unit tests."""
    err: str = ""


class MockLiveClient:
    """Mock Databento Live client for unit tests.

    Records subscribe/start/stop calls. Allows injecting
    messages via fire_callback().
    """

    def __init__(self, key: str = ""):
        self.subscriptions: list[dict] = []
        self.callbacks: list = []
        self.started = False
        self.stopped = False

    def subscribe(self, **kwargs) -> None:
        self.subscriptions.append(kwargs)

    def add_callback(self, callback) -> None:
        self.callbacks.append(callback)

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def fire_callback(self, record) -> None:
        """Simulate a record arriving from Databento.
        Calls all registered callbacks (on the current thread).
        """
        for cb in self.callbacks:
            cb(record)


class MockHistoricalClient:
    """Mock Databento Historical client for unit tests."""

    def __init__(self, key: str = ""):
        self.timeseries = MockTimeseries()


class MockTimeseries:
    """Mock timeseries endpoint."""

    def __init__(self):
        self._data = None  # Set in test to control return

    def get_range(self, **kwargs) -> "MockDBNStore":
        return MockDBNStore(self._data)


class MockDBNStore:
    """Mock DBNStore returned by get_range()."""

    def __init__(self, df=None):
        self._df = df

    def to_df(self):
        import pandas as pd
        if self._df is not None:
            return self._df
        return pd.DataFrame(
            columns=["ts_event", "open", "high", "low", "close", "volume"]
        )
```

### Tests for Component 3 (~40)

**Config and initialization:**
1. Constructor sets up all internal state correctly
2. Constructor with custom config
3. Constructor with clock injection

**start() method:**
4. Missing API key raises RuntimeError
5. Start creates Live client and subscribes (mock)
6. Start subscribes to bar_schema
7. Start subscribes to trade_schema
8. Start subscribes to depth_schema when enable_depth=True
9. Start does NOT subscribe to depth when enable_depth=False
10. Start registers callback
11. Start sets running flag
12. Start warns if already running
13. Start stores event loop reference

**stop() method:**
14. Stop calls live_client.stop()
15. Stop cancels stale monitor task
16. Stop clears symbol map
17. Stop sets running=False
18. Stop is idempotent (calling twice is safe)

**Symbol mapping flow:**
19. _on_symbol_mapping updates symbol map
20. _on_ohlcv skips unknown instrument_id
21. _on_trade skips unknown instrument_id
22. Full flow: mapping → ohlcv → candle event published

**OHLCVMsg → CandleEvent conversion:**
23. Correct symbol resolution
24. Correct timestamp conversion (nanoseconds → datetime)
25. Correct OHLCV field mapping
26. Price cache updated with close price
27. CandleEvent published to Event Bus
28. Symbols not in active_symbols are skipped

**TradeMsg → TickEvent conversion:**
29. Correct symbol resolution
30. Correct timestamp conversion
31. Correct price and size mapping
32. Price cache updated
33. TickEvent published to Event Bus
34. Symbols not in active_symbols are skipped

**ErrorMsg handling:**
35. Error message logged

**get_current_price():**
36. Returns cached price
37. Returns None for unknown symbol

**get_indicator():**
38. Returns cached indicator
39. Returns None for unknown indicator

**get_watchlist_data():**
40. Returns correct structure for multiple symbols

**Stale data monitor (basic):**
41. Monitor publishes stale event after timeout
42. Monitor publishes resumed event when data returns

---

## Implementation Order for Claude Code

1. **Install `databento` dependency** — add to pyproject.toml or requirements
2. **Create mock classes** — `tests/mocks/mock_databento.py`
3. **Implement DatabentoConfig** — `argus/config/databento_config.py` + tests
4. **Integrate config into YAML loader** — add `databento:` section
5. **Implement DatabentoSymbolMap** — `argus/data/databento_symbol_map.py` + tests
6. **Define new events** — `DataStaleEvent`, `DataResumedEvent`
7. **Implement DatabentoDataService** — `argus/data/databento_data_service.py`
   - Start with the callback dispatch and event conversion (testable with mocks)
   - Then indicator integration (reuse existing code)
   - Then historical data / Parquet cache
   - Then stale data monitor
8. **Tests for DatabentoDataService** — comprehensive test suite

**Run `ruff` and `pytest` after each component.** Incremental testing is mandatory.

---

## After Completing This Prompt

**Pause and report:**
- Total test count
- Any deviations from spec
- Any issues discovered
- Any decisions that needed to be made during implementation

The user will review, then provide Prompt 2 (Components 4–6: Reconnection/Circuit Breaker, DataFetcher Databento Backend, Scanner + Integration).
