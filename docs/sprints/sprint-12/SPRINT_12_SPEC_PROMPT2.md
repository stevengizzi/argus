# Sprint 12 — DatabentoDataService Adapter (Prompt 2 of 2)

> **For Claude Code.** This is the continuation spec for Sprint 12, Components 4–6.
> Prompt 1 covered Components 1–3 (Config, SymbolMap, Core DatabentoDataService).

---

## Sprint Context (Reminder)

Sprint 12 builds the DatabentoDataService adapter — ARGUS's primary production market data service. Prompt 1 established:
- `DatabentoConfig` — Pydantic config model
- `DatabentoSymbolMap` — instrument_id ↔ ticker symbol mapping
- `DatabentoDataService` — core live streaming with callback dispatch, Event Bus bridge, indicator computation, and basic stale data monitoring
- Mock classes for testing (`tests/mocks/mock_databento.py`)

This prompt adds: robust reconnection logic, the DataFetcher Databento backend for historical data, and scanner + system integration.

**Current test count after Prompt 1:** 609 (608 from Prompt 1 + 1 from cleanup)

---

## Component 4: Reconnection Logic + Circuit Breaker Enhancement

**Purpose:** Production-grade reconnection with exponential backoff, and enhanced circuit breaker that integrates with the Risk Manager to halt new entries when data is stale.

### 4a: Reconnection Wrapper

The basic `DatabentoDataService.start()` from Prompt 1 creates a single live session. If the TCP connection drops (network issue, Databento maintenance, etc.), we need automatic reconnection.

**Modify `DatabentoDataService` to add a reconnection wrapper around the live session:**

**Important:** The cleanup pass (post-Prompt 1) moved `import databento` out of the 
hot-path `_dispatch_record()` and stored record class references as instance variables 
(DEC-088). When refactoring `start()` → `_connect_live_session()`, ensure these 
references are set inside `_connect_live_session()` since that's where `import databento 
as db` now lives. `_dispatch_record()` uses `isinstance(record, self._OHLCVMsg)` etc. 
— it does NOT import databento itself.

```python
# In DatabentoDataService

async def start(self, symbols: list[str], timeframes: list[str]) -> None:
    """Start streaming with reconnection support.
    
    The actual connection logic moves to _connect_and_stream().
    start() launches a reconnection-aware wrapper task.
    """
    # ... (existing validation, API key check, loop capture) ...
    
    self._running = True
    self._active_symbols = set(symbols)
    self._symbols_list = symbols
    self._timeframes_list = timeframes
    
    # Launch reconnection wrapper as a task
    self._stream_task = asyncio.create_task(
        self._run_with_reconnection()
    )
    
    # Start stale data monitor
    self._stale_monitor_task = asyncio.create_task(
        self._stale_data_monitor()
    )

async def _run_with_reconnection(self) -> None:
    """Main streaming loop with exponential backoff reconnection.
    
    Manages the lifecycle of the Databento Live client:
    1. Connect and subscribe
    2. Wait for close (normal operation)
    3. If unexpected disconnect, reconnect with backoff
    4. If max retries exceeded, publish critical alert and stop
    """
    import databento as db
    
    retries = 0
    
    while self._running:
        try:
            # Connect and subscribe
            await self._connect_live_session()
            
            # Reset retry counter on successful connection
            retries = 0
            
            # Wait for the session to end
            # Use wait_for_close() in a thread since it's blocking
            await asyncio.to_thread(self._live_client.block_for_close)
            
            if not self._running:
                break  # Clean shutdown via stop()
            
            # Unexpected disconnect — reconnect
            logger.warning("Databento session ended unexpectedly")
            
        except Exception as e:
            logger.error("Databento stream error: %s", e)
        
        # Reconnection logic
        retries += 1
        if retries > self._config.reconnect_max_retries:
            logger.critical(
                "Databento max reconnection retries (%d) exceeded. "
                "Data feed is DEAD. Manual intervention required.",
                self._config.reconnect_max_retries,
            )
            # Publish critical system event
            # Claude Code: Publish a SystemAlertEvent or similar
            break
        
        delay = min(
            self._config.reconnect_base_delay_seconds * (2 ** (retries - 1)),
            self._config.reconnect_max_delay_seconds,
        )
        logger.warning(
            "Reconnecting to Databento in %.1fs (attempt %d/%d)",
            delay, retries, self._config.reconnect_max_retries,
        )
        await asyncio.sleep(delay)
    
    logger.info("Reconnection loop exited (running=%s, retries=%d)", 
                self._running, retries)

async def _connect_live_session(self) -> None:
    """Create a new Databento Live client and subscribe to streams.
    
    Extracted from start() so it can be called on each reconnection attempt.
    """
    import databento as db
    
    api_key = os.getenv(self._config.api_key_env_var)
    
    # Clean up previous client if exists
    if self._live_client is not None:
        try:
            self._live_client.stop()
        except Exception:
            pass
    
    # Create fresh client
    self._live_client = db.Live(key=api_key)
    
    # Clear symbol map — new session will send fresh mappings
    self._symbol_map.clear()
    
    subscribe_symbols = self._config.symbols
    
    # Subscribe to schemas
    self._live_client.subscribe(
        dataset=self._config.dataset,
        schema=self._config.bar_schema,
        symbols=subscribe_symbols,
        stype_in=self._config.stype_in,
    )
    self._live_client.subscribe(
        dataset=self._config.dataset,
        schema=self._config.trade_schema,
        symbols=subscribe_symbols,
        stype_in=self._config.stype_in,
    )
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
        "Connected to Databento: dataset=%s", self._config.dataset
    )
```

### 4b: Stale Data Monitor — ALREADY IMPLEMENTED (Prompt 1)

The stale data monitor with DataStaleEvent/DataResumedEvent, the _stale_published 
dedup flag, and 4 tests are already in place from Prompt 1. No changes needed unless 
the reconnection wrapper introduces new stale monitor requirements (e.g., resetting 
_last_message_time on reconnection — verify this happens in _connect_live_session()).

**Skip tests 11–15 from the test list.** They already exist and pass.

### Tests for Component 4 (~15):

**Reconnection logic:**
1. Clean shutdown exits reconnection loop (running=False)
2. First connection failure triggers reconnect with base delay
3. Exponential backoff doubles delay on each retry
4. Backoff caps at max_delay_seconds
5. Max retries exceeded logs critical and stops
6. Successful connection resets retry counter to 0
7. Symbol map is cleared on reconnection
8. Previous client is stopped before creating new one
9. Connection error triggers reconnect (not crash)
10. Multiple reconnections work (connect → disconnect → reconnect → disconnect → reconnect)

**Stale data monitor:**
11. No stale event before first message (last_message_time == 0)
12. Stale event published when timeout exceeded
13. Resumed event published when data returns
14. Stale event published only once (not repeatedly)
15. Resumed event published only once per recovery

---

## Component 5: DataFetcher Databento Backend

**Purpose:** Extend the existing `DataFetcher` class to support fetching historical 1-minute bars from Databento's Historical API, alongside the existing Alpaca backend.

**Location:** `argus/data/data_fetcher.py` (existing file — extend, don't replace)

**Note:** DatabentoDataService already has `_normalize_historical_df()` from Prompt 1 
that performs the same normalization (ts_event → timestamp, UTC, column selection, sort). 
Rather than duplicating, either:
(a) Extract it as a standalone utility function in a shared location (e.g., 
    `argus/data/databento_utils.py`) and have both DataFetcher and 
    DatabentoDataService call it, OR
(b) Copy it as `_normalize_databento_df()` in DataFetcher and flag as tech debt 
    (minor — it's a pure static method with no state).

Option (a) is preferred but (b) is acceptable for Sprint 12.

### Design

The DataFetcher currently fetches from Alpaca. We add a parallel code path for Databento. The data source is selected by a new config field or method parameter.

```python
# Add to DataFetcherConfig (or create DatabentoFetcherConfig)
class DataFetcherConfig(BaseModel):
    # ... existing fields ...
    
    # New field: data source selection
    source: str = "alpaca"  # "alpaca" or "databento"
    
    # Databento-specific settings
    databento_dataset: str = "XNAS.ITCH"

# New methods in DataFetcher:

class DataFetcher:
    """Extended to support both Alpaca and Databento data sources."""
    
    def __init__(
        self,
        config: DataFetcherConfig,
        api_key: str | None = None,
        api_secret: str | None = None,
        databento_key: str | None = None,  # NEW
    ) -> None:
        self._config = config
        # Existing Alpaca client setup ...
        
        # Databento client (lazy init)
        self._databento_key = databento_key
        self._databento_client = None  # Created on first use

    @property
    def _db_client(self):
        """Lazy-init Databento Historical client."""
        if self._databento_client is None:
            import databento as db
            key = self._databento_key or os.getenv("DATABENTO_API_KEY")
            if not key:
                raise RuntimeError("Databento API key not available")
            self._databento_client = db.Historical(key=key)
        return self._databento_client

    async def fetch_symbol_month_databento(
        self,
        symbol: str,
        year: int,
        month: int,
    ) -> pd.DataFrame:
        """Fetch one month of 1-minute bars from Databento Historical API.

        Checks Parquet cache first. If not cached, fetches from Databento,
        normalizes to standard schema, and caches as Parquet.

        Args:
            symbol: Ticker symbol (e.g., "AAPL")
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
            Same schema as fetch_symbol_month() (Alpaca version).
        """
        import calendar
        from datetime import date

        # Check cache
        cache_path = self._get_parquet_path(symbol, year, month)
        if cache_path.exists():
            logger.debug("Cache hit: %s", cache_path)
            return pd.read_parquet(cache_path)

        # Calculate date range
        start_date = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = date(year, month, last_day)

        # Rate limit
        await self._rate_limit()

        # Fetch from Databento
        logger.info("Fetching %s %d-%02d from Databento", symbol, year, month)
        data = self._db_client.timeseries.get_range(
            dataset=self._config.databento_dataset,
            symbols=symbol,
            schema="ohlcv-1m",
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),  # Exclusive end
            stype_in="raw_symbol",
        )

        df = data.to_df()

        if df.empty:
            logger.warning("No data returned for %s %d-%02d", symbol, year, month)
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        # Normalize to standard schema
        result = self._normalize_databento_df(df)

        # Filter to market hours only (9:30 AM - 4:00 PM ET)
        # Claude Code: Apply the same market hours filter as the existing
        # Alpaca fetch path, if one exists.

        # Save to cache
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(cache_path, index=False)
        logger.info("Cached %d bars for %s %d-%02d", len(result), symbol, year, month)

        # Update manifest
        # Claude Code: Update the manifest the same way as Alpaca fetches

        return result

    @staticmethod
    def _normalize_databento_df(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Databento DataFrame to ARGUS standard schema.

        Input (Databento to_df() output):
            ts_event, rtype, publisher_id, instrument_id, open, high, low, close, volume

        Output (ARGUS standard):
            timestamp, open, high, low, close, volume
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

### Integration Notes

- The existing `fetch_symbol_month()` (Alpaca version) remains unchanged
- A new `fetch_symbol_month_databento()` provides the Databento path
- Both produce the **exact same output schema** — downstream consumers (VectorBT, Replay Harness) can't tell the difference
- The `_normalize_databento_df()` static method can also be used by `DatabentoDataService.get_historical_candles()`
- Parquet files use the same directory structure as Alpaca: `data/{symbol}/{YYYY-MM}.parquet`
- A separate cache dir (`data/databento_cache/`) is used to avoid mixing providers

### Tests for Component 5 (~15):

1. DataFetcher constructor accepts databento_key parameter
2. Lazy Databento client creation (not created until first use)
3. Missing Databento key raises RuntimeError on first use
4. `fetch_symbol_month_databento()` — cache hit returns cached data
5. `fetch_symbol_month_databento()` — cache miss fetches from API (mocked)
6. `fetch_symbol_month_databento()` — empty response returns empty DataFrame
7. `fetch_symbol_month_databento()` — result saved to Parquet cache
8. `fetch_symbol_month_databento()` — correct date range calculation (month boundaries)
9. `_normalize_databento_df()` — correct column rename (ts_event → timestamp)
10. `_normalize_databento_df()` — timestamps converted to UTC
11. `_normalize_databento_df()` — sorted by timestamp
12. `_normalize_databento_df()` — extra columns dropped (rtype, publisher_id, etc.)
13. Output schema matches Alpaca fetch output exactly (column names, dtypes)
14. Rate limiting is called before Databento fetch
15. Parquet cache directory created if missing

---

## Component 6: Scanner Integration + System Wiring

### 6a: DatabentoScanner

**Purpose:** Scanner implementation that uses Databento data for pre-market gap scanning. With Databento's full-universe access, we can scan all ~8,000 stocks instead of being limited by Alpaca's symbol constraints.

**Location:** `argus/data/databento_scanner.py`

**Note:** `.env.example` already includes DATABENTO_API_KEY (added in Prompt 1). 
No additional changes needed.

**Design:** For V1, the scanner follows the same ABC as existing scanners. The DatabentoScanner scans for gap candidates by querying yesterday's closing prices and today's opening prices from Databento.

```python
"""Scanner using Databento data for gap-based candidate selection."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import databento as db

from argus.data.scanner import Scanner, ScannerCandidate

logger = logging.getLogger(__name__)


class DatabentoScanner(Scanner):
    """Scanner using Databento for full-universe pre-market gap scanning.

    Can scan all ~8,000 US equity symbols since Databento has no symbol limits.
    Uses historical API to compute gap from previous day's close to today's open.

    For ORB strategy: identifies stocks with significant pre-market gaps
    (configurable min_gap_pct) that meet price and volume filters.
    """

    def __init__(
        self,
        config,  # ScannerConfig (existing)
        databento_config=None,  # DatabentoConfig (optional, uses env vars if None)
    ) -> None:
        self._config = config
        self._databento_config = databento_config
        self._hist_client = None

    @property
    def _client(self):
        """Lazy-init Databento Historical client."""
        if self._hist_client is None:
            import databento as db
            key = os.getenv(
                self._databento_config.api_key_env_var
                if self._databento_config
                else "DATABENTO_API_KEY"
            )
            self._hist_client = db.Historical(key=key)
        return self._hist_client

    async def scan(self) -> list[ScannerCandidate]:
        """Scan for ORB candidates based on pre-market gap.

        Strategy:
        1. Query Databento for yesterday's OHLCV-1d bars (closing prices)
        2. Query Databento for today's opening print (first trade or OHLCV-1m first bar)
        3. Compute gap_pct = (today_open - yesterday_close) / yesterday_close
        4. Filter by min_gap_pct, min_price, min_volume from config
        5. Sort by gap_pct descending, return top N candidates

        This runs ONCE per day, before market open.
        
        NOTE: For V1, this may use a pre-configured symbol universe
        rather than scanning ALL_SYMBOLS (to control costs and latency).
        The architecture supports full-universe scanning.
        """
        # Claude Code: Implement the scanning logic.
        # 
        # For initial implementation, a simpler approach is acceptable:
        # - Use a configurable watchlist of symbols (e.g., S&P 500 + high-volume stocks)
        # - Query their previous close and current day open
        # - Filter and sort
        #
        # Full-universe scanning can be added later when we understand
        # the latency and cost implications of querying 8,000 symbols.
        
        logger.info("DatabentoScanner starting scan")
        candidates = []
        
        # Implementation here...
        # Use self._client.timeseries.get_range() for historical data
        
        logger.info("DatabentoScanner found %d candidates", len(candidates))
        return candidates
```

**Note to Claude Code:** The DatabentoScanner implementation can be initially simpler than the Alpaca scanner — even a stub that returns a static list is fine for Sprint 12. The key value of this sprint is the DatabentoDataService (live streaming) and DataFetcher (historical data). The scanner can be enhanced in a future sprint when we're ready to do full-universe scanning.

### 6b: System Integration

**Wire DatabentoDataService into the system startup sequence.**

The existing `argus/main.py` has a 10-phase startup sequence (DEC-045/MD-5-6). Modify it to support selecting between Alpaca and Databento data services based on config.

**Changes needed:**

1. **Config file (`config/argus.yaml` or equivalent):**
```yaml
data_service:
  provider: "databento"  # or "alpaca" for incubator mode
  
databento:
  dataset: "XNAS.ITCH"
  symbols: "ALL_SYMBOLS"
  enable_depth: false
  # ... other DatabentoConfig fields ...

alpaca:
  # ... existing AlpacaConfig (retained for incubator) ...
```

2. **main.py data service creation:**
```python
# In the startup sequence, replace hardcoded AlpacaDataService with:
if config.data_service.provider == "databento":
    data_service = DatabentoDataService(
        event_bus=event_bus,
        config=config.databento,
        data_config=config.data_service_config,
        clock=clock,
    )
elif config.data_service.provider == "alpaca":
    data_service = AlpacaDataService(
        event_bus=event_bus,
        config=config.alpaca,
        data_config=config.data_service_config,
        clock=clock,
    )
else:
    raise ValueError(f"Unknown data service provider: {config.data_service.provider}")
```

3. **Scanner selection:** Similarly, wire `DatabentoScanner` as an option alongside `AlpacaScanner` and `StaticScanner`.

4. **Environment variable documentation:** Update `.env.example` (or wherever env vars are documented) to include `DATABENTO_API_KEY`.

### Tests for Component 6 (~15):

**DatabentoScanner:**
1. Constructor creates scanner with config
2. Lazy Historical client creation
3. Missing API key raises error on first scan
4. `scan()` returns list of ScannerCandidate
5. `scan()` with mock data returns filtered candidates
6. `scan()` respects min_gap_pct filter
7. `scan()` respects min_price filter
8. `scan()` returns empty list when no candidates match

**System integration:**
9. Config with provider="databento" creates DatabentoDataService
10. Config with provider="alpaca" creates AlpacaDataService
11. Config with unknown provider raises ValueError
12. DatabentoConfig is loadable from YAML
13. Full startup sequence works with Databento config (mocked client)
14. DatabentoDataService is registered with Event Bus correctly
15. DatabentoScanner is selectable in config

---

## Post-Sprint Checklist

After completing both Prompt 1 and Prompt 2:

### Verify

- [ ] `ruff check .` — clean
- [ ] `pytest` — all pass, including existing 542 tests
- [ ] New test count is ~110+ (Components 1–6)
- [ ] Total test count is ~650+
- [ ] No `databento` import at module level (all behind `TYPE_CHECKING` or lazy import)
- [ ] Tests run without `databento` package installed (using mocks)
- [ ] DatabentoDataService implements all DataService ABC methods
- [ ] Indicator computation uses the exact same logic as AlpacaDataService
- [ ] Historical data output matches Alpaca Parquet schema exactly
- [ ] Config is additive (existing Alpaca config unchanged)
- [ ] `.env` template updated with `DATABENTO_API_KEY`

### Report to User

Provide:
1. Final test count (new + total)
2. All deviations from spec (with rationale)
3. Any implementation decisions made during coding
4. Any issues or TODOs discovered
5. File list of all new/modified files

### Next Steps After Sprint 12

Sprint 13 (IBKRBroker adapter) is next in the Build Track queue. The user will provide the Sprint 13 spec separately.

The Validation Track can resume paper trading with Databento data quality once the subscription is activated (DEC-087) and integration testing passes.
