# ARGUS — Sprint 4a Implementation Spec

> **Date:** February 15, 2026
> **Sprint:** 4a — Live Connections (Alpaca Data Service + Alpaca Broker + Clock Injection)
> **Handoff to:** Claude Code
> **Prerequisite:** Sprint 3 complete (222 tests passing). All code committed.
> **Target tests after Sprint 4a:** ~280+

---

## Sprint 4a Goal

Real market data flowing into the system and paper orders placed on Alpaca, end-to-end:

```
AlpacaDataService (live WebSocket) → OrbBreakout → RiskManager → AlpacaBroker (paper)
```

After this sprint, the system can receive live data, detect ORB breakouts on real stocks, and submit paper orders. There is **no dynamic position management** yet (that's Sprint 4b) — broker-side bracket orders (stop + targets submitted with entry) provide basic exit coverage.

---

## Decisions in Effect (Sprint 4a Specific)

These are new decisions made for Sprint 4a. All prior decisions (DEC-001 through DEC-038) remain active.

| ID | Decision | Rationale |
|----|----------|-----------|
| **MD-4a-1** | AlpacaDataService subscribes to **both** Alpaca's 1m bar stream and trade stream. Bars drive `CandleEvent` publishing; trades drive `get_current_price()` cache and `TickEvent` publishing. | Bar stream provides reliable pre-aggregated candles (no aggregation bugs). Trade stream provides sub-second price awareness for `get_current_price()` and future scalp strategy support. Best of both worlds. |
| **MD-4a-2** | WebSocket reconnection: exponential backoff starting at 1s, max 30s, with jitter. Stale data mode (pause strategies) after 30s of disconnection. Unlimited retries during market hours. System alert after 3 consecutive reconnection failures. | Matches the Architecture doc's 30-second stale data timeout. Exponential backoff with jitter prevents thundering herd on Alpaca's servers. |
| **MD-4a-3** | **Switch from `alpaca-trade-api` to `alpaca-py`** as the Alpaca SDK. | `alpaca-trade-api` has been deprecated since end of 2022 — no new features, no active maintenance. `alpaca-py` is the current official SDK with native Pydantic models (aligns with DEC-032), proper async support, separate client classes per concern (`StockDataStream`, `TradingClient`, `TradingStream`, `StockHistoricalDataClient`). All Alpaca documentation and examples now use `alpaca-py`. |
| **MD-4a-4** | Run alpaca-py's WebSocket streams as asyncio tasks within Argus's main event loop. Handlers translate Alpaca events into Event Bus events. If `.run()` blocks, wrap in `asyncio.to_thread()`. | Single event loop keeps the architecture simple and consistent with DEC-025. Alpaca's `StockDataStream` and `TradingStream` use asyncio internally and should integrate cleanly. |
| **MD-4a-5** | Clock injection scope: Risk Manager + BaseStrategy. A `Clock` protocol with `now()` and `today()` methods, defaulting to real time. Injected via constructor. | Risk Manager and strategies are the two components where date boundaries matter for testing (daily reset, weekly P&L, PDT tracking). System-wide injection is overkill for now. Resolves DEF-001. |
| **MD-4a-6** | Testing: Mock alpaca-py client classes for unit tests. Optional recorded-fixture integration test (not in main test suite, requires API keys). | Unit tests must be fast, deterministic, and not require API keys. Recorded fixtures provide one realistic end-to-end validation but shouldn't gate CI. |

---

## Components to Implement

### Component 1: Clock Protocol (`argus/core/clock.py`)

**Purpose:** Injectable time provider for date-boundary testing. Resolves DEF-001.

```python
from datetime import datetime, date
from typing import Protocol

class Clock(Protocol):
    """Protocol for injectable time provider.
    
    Components that need current time should accept a Clock parameter
    instead of calling datetime.now() or date.today() directly.
    """
    def now(self) -> datetime:
        """Return current datetime (timezone-aware, UTC)."""
        ...
    
    def today(self) -> date:
        """Return current date in the system's configured timezone."""
        ...

class SystemClock:
    """Production clock using real system time."""
    
    def __init__(self, timezone: str = "America/New_York"):
        """
        Args:
            timezone: IANA timezone string. Used for today() to determine
                      the correct date boundary for trading days.
        """
        ...
    
    def now(self) -> datetime:
        """Return current UTC datetime."""
        # return datetime.now(UTC)
    
    def today(self) -> date:
        """Return today's date in the configured timezone."""
        # Convert UTC now to configured timezone, return .date()

class FixedClock:
    """Test clock with manually controllable time."""
    
    def __init__(self, fixed_time: datetime):
        self._time = fixed_time
    
    def now(self) -> datetime:
        return self._time
    
    def today(self) -> date:
        return self._time.date()
    
    def advance(self, **kwargs) -> None:
        """Advance time by timedelta kwargs (hours=1, minutes=30, etc.)."""
        self._time += timedelta(**kwargs)
    
    def set(self, new_time: datetime) -> None:
        """Set time to a specific datetime."""
        self._time = new_time
```

**Integration points:**

1. **Risk Manager constructor:** Add `clock: Clock = None` parameter. Default to `SystemClock()` if not provided. Replace all `datetime.now(UTC)` calls with `self._clock.now()` and all `date.today()` calls with `self._clock.today()`.

2. **BaseStrategy constructor:** Add `clock: Clock = None` parameter. Same replacement pattern. Strategies that extend BaseStrategy inherit the clock.

3. **Backward compatibility:** Existing tests that don't pass a clock should continue to work (default to SystemClock). New tests that need date control pass FixedClock.

**Files to create:**
- `argus/core/clock.py`
- `tests/core/test_clock.py`

**Files to modify:**
- `argus/core/risk_manager.py` — inject Clock, replace datetime calls
- `argus/strategies/base_strategy.py` — inject Clock, replace datetime calls
- Affected tests — update constructors where needed (existing tests should still pass with defaults)

---

### Component 2: Alpaca Configuration (`argus/core/config.py` additions)

**New Pydantic config models:**

```python
class AlpacaConfig(BaseModel):
    """Configuration for Alpaca API connections."""
    api_key_env: str = "ALPACA_API_KEY"          # Env var name (not the key itself!)
    secret_key_env: str = "ALPACA_SECRET_KEY"     # Env var name (not the key itself!)
    paper: bool = True                             # Paper trading mode
    data_feed: str = "iex"                         # "iex" (free) or "sip" (paid)
    
    # WebSocket reconnection
    ws_reconnect_base_seconds: float = 1.0
    ws_reconnect_max_seconds: float = 30.0
    ws_reconnect_max_failures_before_alert: int = 3
    
    # Stale data
    stale_data_timeout_seconds: float = 30.0
    
    # Data streams
    subscribe_bars: bool = True       # 1m bar stream
    subscribe_trades: bool = True     # Individual trade stream
```

**Update `config/brokers.yaml`:**

```yaml
primary: "alpaca"
alpaca:
  enabled: true
  paper: true
  data_feed: "iex"
  api_key_env: "ALPACA_API_KEY"
  secret_key_env: "ALPACA_SECRET_KEY"
  ws_reconnect_base_seconds: 1.0
  ws_reconnect_max_seconds: 30.0
  ws_reconnect_max_failures_before_alert: 3
  stale_data_timeout_seconds: 30.0
  subscribe_bars: true
  subscribe_trades: true
```

**CRITICAL: API keys are NEVER in config files or code.** The config stores the *names* of environment variables. At runtime, the AlpacaBroker and AlpacaDataService read keys from the environment using these names. This follows our existing architectural rule.

**`.env` Loading:** The project root contains a `.env` file (already in `.gitignore`) with `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`. Use `python-dotenv` to load this at system startup:

```python
# In argus/main.py (or wherever the system entry point is), at the very top:
from dotenv import load_dotenv
load_dotenv()  # Reads .env file from project root into os.environ
```

This must happen before any component tries to read API keys via `os.getenv()`. The `.env` file format is standard:
```
ALPACA_API_KEY=PKXXXXXXXXXXXXXXXXXX
ALPACA_SECRET_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Verify `.env` is in `.gitignore`.** If it's not, add it immediately — this is a security-critical check.

---

### Component 3: AlpacaDataService (`argus/data/alpaca_data_service.py`)

**Purpose:** Implements the `DataService` ABC using alpaca-py's `StockDataStream` (WebSocket) and `StockHistoricalDataClient` (REST). This is the live equivalent of `ReplayDataService`.

**Dependencies (pip install):**
```
alpaca-py
python-dotenv
```

**Architecture:**

```
                ┌─────────────────────────────────┐
                │       AlpacaDataService          │
                │                                  │
                │  StockDataStream (WebSocket)      │
                │    ├── subscribe_bars → _on_bar   │
                │    └── subscribe_trades → _on_trade│
                │                                  │
                │  StockHistoricalDataClient (REST)  │
                │    └── get_stock_bars (historical) │
                │                                  │
                │  Internal State:                  │
                │    ├── _price_cache: {symbol: float}│
                │    ├── _indicator_cache: {key: float}│
                │    ├── _candle_builders: {symbol: CandleBuilder}│
                │    └── _indicator_engines: {symbol: IndicatorEngine}│
                │                                  │
                │  Publishes to Event Bus:          │
                │    ├── CandleEvent (from bar stream)│
                │    ├── TickEvent (from trade stream)│
                │    └── IndicatorEvent (computed)   │
                └─────────────────────────────────┘
```

**Interface (implements DataService ABC):**

```python
class AlpacaDataService(DataService):
    """Live market data service using Alpaca's WebSocket and REST APIs.
    
    Subscribes to Alpaca's 1m bar stream for CandleEvents and trade stream
    for TickEvents and real-time price cache. Computes indicators inline
    (VWAP, ATR, SMA, RVOL) matching ReplayDataService's behavior exactly.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        config: AlpacaConfig,
        data_config: DataServiceConfig,
        clock: Clock = None,
    ):
        ...
    
    # --- DataService ABC implementation ---
    
    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Start streaming live data for the given symbols.
        
        1. Initialize alpaca-py clients (StockDataStream, StockHistoricalDataClient)
        2. Fetch historical candles for indicator warm-up (see Indicator Warm-Up below)
        3. Subscribe to bar stream for all symbols
        4. Subscribe to trade stream for all symbols
        5. Start the WebSocket event loop as an asyncio task
        6. Start the stale data monitor as an asyncio task
        """
    
    async def stop(self) -> None:
        """Stop streaming, close WebSocket connections, cancel tasks."""
    
    async def get_current_price(self, symbol: str) -> float:
        """Return the latest trade price from the in-memory cache.
        Updated on every trade received via the trade stream.
        Raises ValueError if no price available for symbol."""
    
    async def get_indicator(self, symbol: str, indicator: str) -> float:
        """Return latest computed indicator value from cache.
        Key format: 'vwap', 'atr_14', 'sma_9', 'sma_20', 'sma_50', 'rvol'.
        Raises ValueError if indicator not available."""
    
    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Fetch historical candles via Alpaca REST API.
        Uses StockHistoricalDataClient.get_stock_bars().
        Returns DataFrame with columns: open, high, low, close, volume, timestamp."""
    
    async def get_watchlist_data(self, symbols: list[str]) -> dict:
        """Fetch current data summary for a list of symbols.
        Returns dict keyed by symbol with latest price, volume, indicators."""
```

**Internal Handlers (translate Alpaca events → Argus events):**

```python
async def _on_bar(self, bar) -> None:
    """Handler for Alpaca bar stream.
    
    Called when a completed 1m bar arrives from Alpaca.
    1. Extract OHLCV data from Alpaca's Bar object
    2. Update indicator engine for this symbol (VWAP, ATR, SMA, RVOL)
    3. Publish CandleEvent to Event Bus
    4. Publish IndicatorEvents for all updated indicators
    """

async def _on_trade(self, trade) -> None:
    """Handler for Alpaca trade stream.
    
    Called on each individual trade from Alpaca.
    1. Update _price_cache[symbol] = trade.price
    2. Publish TickEvent to Event Bus
    """
```

**Indicator Warm-Up:**

When `start()` is called, the AlpacaDataService must fetch recent historical data to "warm up" indicators before the live stream begins. Without warm-up, VWAP would start at zero, ATR would have no history, and SMAs would be incomplete.

```
Warm-up procedure:
1. Fetch the last 60 1m candles for each symbol via REST API
   (covers pre-market / previous day data for indicator seeding)
2. Feed these candles through the indicator engine sequentially
3. Do NOT publish CandleEvents or IndicatorEvents during warm-up
   (these are historical — strategies should not trade on them)
4. After warm-up, the indicator cache is populated and the live stream begins
```

Note: The 60-candle window is a starting point. ATR(14) needs 14 candles minimum. SMA(50) needs 50 candles minimum. 60 provides enough for all current indicators. If more indicators are added later that need deeper history, increase this number.

**VWAP Daily Reset:** VWAP must reset at market open (9:30 AM EST) each day, same as ReplayDataService. Use the injected Clock to determine when a new trading day starts.

**Stale Data Monitor:**

```python
async def _stale_data_monitor(self) -> None:
    """Background task that runs every 5 seconds during market hours.
    
    Checks if any subscribed symbol has not received a bar or trade
    within stale_data_timeout_seconds (default 30s).
    
    If stale:
    1. Set self._is_stale = True
    2. Publish a system alert event to the Event Bus
    3. Strategies should check DataService.is_stale before acting
    
    When data resumes:
    1. Set self._is_stale = False
    2. Publish a recovery event
    """
```

**WebSocket Reconnection:**

```python
async def _run_stream_with_reconnect(self) -> None:
    """Wrapper around StockDataStream that handles disconnections.
    
    On disconnect:
    1. Log the disconnection
    2. Increment consecutive_failures counter
    3. If consecutive_failures >= max_failures_before_alert: publish system alert
    4. Wait: min(base * 2^failures + jitter, max_seconds)
    5. Reconnect and re-subscribe to all symbols
    6. On successful reconnect: reset consecutive_failures to 0
    
    Runs indefinitely during market hours. Stops when stop() is called.
    """
```

**Important: alpaca-py integration pattern.**

alpaca-py's `StockDataStream` has a `.run()` method that starts its own event loop. To integrate with our existing asyncio loop:

```python
# Pattern 1 (preferred): Use the stream's internal coroutine
# alpaca-py's StockDataStream._run_forever() is an awaitable coroutine
# We can create a task from it:
self._stream_task = asyncio.create_task(self._run_stream_with_reconnect())

# Inside _run_stream_with_reconnect, instead of calling stream.run(),
# we call the internal async method or manage the connection ourselves.

# Pattern 2 (fallback): If Pattern 1 doesn't work due to SDK internals,
# run stream.run() in a thread:
self._stream_task = asyncio.create_task(
    asyncio.to_thread(self._data_stream.run)
)
```

**Claude Code should investigate alpaca-py's source to determine which pattern works.** The key requirement is: Alpaca's handlers (`_on_bar`, `_on_trade`) must be able to publish events to our Event Bus, which runs on the main asyncio loop. If the handlers run on a different thread, they'll need `loop.call_soon_threadsafe()` or similar to bridge.

**Files to create:**
- `argus/data/alpaca_data_service.py`
- `tests/data/test_alpaca_data_service.py`

---

### Component 4: AlpacaBroker (`argus/execution/alpaca_broker.py`)

**Purpose:** Implements the `Broker` ABC using alpaca-py's `TradingClient` (REST) and `TradingStream` (WebSocket for order updates).

**Architecture:**

```
                ┌──────────────────────────────────┐
                │          AlpacaBroker             │
                │                                   │
                │  TradingClient (REST)              │
                │    ├── submit_order()              │
                │    ├── cancel_order_by_id()        │
                │    ├── replace_order_by_id()        │
                │    ├── get_all_positions()          │
                │    ├── get_account()                │
                │    ├── get_order_by_id()            │
                │    └── close_all_positions()        │
                │                                   │
                │  TradingStream (WebSocket)          │
                │    └── subscribe_trade_updates()    │
                │        → _on_trade_update()         │
                │                                   │
                │  Publishes to Event Bus:            │
                │    ├── OrderSubmittedEvent           │
                │    ├── OrderFilledEvent              │
                │    └── OrderCancelledEvent           │
                └──────────────────────────────────┘
```

**Interface (implements Broker ABC):**

```python
class AlpacaBroker(Broker):
    """Live broker adapter using Alpaca's Trading API (paper or live).
    
    Uses alpaca-py's TradingClient for REST operations and TradingStream
    for real-time order status updates via WebSocket.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        config: AlpacaConfig,
    ):
        ...
    
    async def connect(self) -> None:
        """Initialize TradingClient and TradingStream.
        
        1. Read API keys from environment variables
        2. Initialize TradingClient(api_key, secret_key, paper=config.paper)
        3. Initialize TradingStream(api_key, secret_key, paper=config.paper)
        4. Subscribe to trade_updates
        5. Start TradingStream as asyncio task
        """
    
    async def disconnect(self) -> None:
        """Close WebSocket connection and clean up."""
    
    # --- Broker ABC implementation ---
    
    async def place_order(self, order: Order) -> OrderResult:
        """Submit a single order to Alpaca.
        
        Maps our Order model to Alpaca's MarketOrderRequest/LimitOrderRequest/
        StopOrderRequest based on order.order_type.
        
        Returns OrderResult with Alpaca's order ID mapped to our order_id.
        Publishes OrderSubmittedEvent to Event Bus.
        """
    
    async def place_bracket_order(
        self, entry: Order, stop: Order, targets: list[Order]
    ) -> BracketOrderResult:
        """Submit a bracket order (entry + stop + take-profit) to Alpaca.
        
        Alpaca supports bracket orders natively via OrderClass.BRACKET or
        OrderClass.OTO (one-triggers-other).
        
        For ORB's tiered exit (50% at T1, 50% at T2), this requires:
        - Option A: Single bracket order with one take-profit and one stop-loss.
          Limitation: Alpaca bracket orders support exactly ONE take-profit price.
        - Option B: Submit entry as a market order, then on fill submit two
          separate OTO orders (each for half the shares) with different targets
          and the same stop.
        
        IMPORTANT DECISION POINT: Alpaca's native bracket order only supports
        a single take-profit level. Since ORB has T1 and T2 targets at different
        prices, we have two implementation paths:
        
        Path A (Simpler, Sprint 4a): Submit a single bracket order using T1 as
        the take-profit for the full position. The Order Manager (Sprint 4b)
        will later handle the T1/T2 split by modifying the order after T1 hits.
        
        Path B (Complete, Sprint 4a): Submit entry as market order. On fill event,
        submit two separate stop + take-profit OCO order pairs for half the shares
        each, with different target prices.
        
        Recommendation: Use Path A for Sprint 4a. It provides bracket protection
        (entry + stop + at least T1 target) without the complexity of managing
        multiple child orders. Sprint 4b's Order Manager supersedes this with
        full position management anyway.
        
        Publishes OrderSubmittedEvent to Event Bus.
        """
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID. Returns True if successfully cancelled."""
    
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify an existing order (e.g., change limit price, qty).
        Uses Alpaca's replace_order_by_id()."""
    
    async def get_positions(self) -> list[Position]:
        """Get all open positions. Maps Alpaca Position objects to our Position model."""
    
    async def get_account(self) -> AccountInfo:
        """Get account info. Maps Alpaca Account to our AccountInfo model.
        
        IMPORTANT: Alpaca's paper account returns real margin/buying power values.
        This is where SimulatedBroker's buying_power=cash (DEC-036) diverges from
        reality. AlpacaBroker returns Alpaca's actual buying_power which includes
        margin.
        """
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get status of a specific order."""
    
    async def flatten_all(self) -> list[OrderResult]:
        """Emergency: close all positions at market.
        Uses Alpaca's close_all_positions(cancel_orders=True)."""
```

**Order Update Handler:**

```python
async def _on_trade_update(self, data) -> None:
    """Handler for Alpaca's trade_updates WebSocket stream.
    
    Alpaca sends events: new, fill, partial_fill, canceled, expired,
    replaced, rejected, pending_cancel, etc.
    
    Mapping to our events:
    - 'new' → OrderSubmittedEvent (if we didn't already publish on REST response)
    - 'fill' → OrderFilledEvent(order_id, fill_price, fill_qty, timestamp)
    - 'partial_fill' → OrderFilledEvent(order_id, fill_price, partial_qty, timestamp)
    - 'canceled' → OrderCancelledEvent(order_id, reason='canceled')
    - 'expired' → OrderCancelledEvent(order_id, reason='expired')
    - 'rejected' → OrderCancelledEvent(order_id, reason='rejected: {msg}')
    - 'replaced' → Log only (order modification confirmed)
    
    All events published to Event Bus.
    """
```

**Order ID Mapping:**

Alpaca assigns its own order IDs (UUIDs). We use ULIDs internally. The AlpacaBroker must maintain a bidirectional mapping:

```python
self._order_id_map: dict[str, str] = {}      # our_ulid → alpaca_uuid
self._reverse_id_map: dict[str, str] = {}    # alpaca_uuid → our_ulid
```

When placing an order, we generate our ULID, submit to Alpaca, receive Alpaca's UUID, and store both mappings. When receiving order updates via WebSocket, we look up our ULID from Alpaca's UUID.

**Alpaca-py Client Usage Patterns:**

```python
# REST - Trading Client
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass

client = TradingClient(api_key, secret_key, paper=True)

# Market order
request = MarketOrderRequest(
    symbol="AAPL",
    qty=100,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
)
order = client.submit_order(request)

# Bracket order (single take-profit)
request = MarketOrderRequest(
    symbol="AAPL",
    qty=100,
    side=OrderSide.BUY,
    time_in_force=TimeInForce.DAY,
    order_class=OrderClass.BRACKET,
    take_profit={"limit_price": 155.0},
    stop_loss={"stop_price": 148.0},
)
order = client.submit_order(request)

# Get account
account = client.get_account()

# Get positions
positions = client.get_all_positions()

# Cancel all orders and close all positions
client.close_all_positions(cancel_orders=True)


# WebSocket - Trading Stream
from alpaca.trading.stream import TradingStream

stream = TradingStream(api_key, secret_key, paper=True)

async def handler(data):
    print(data)

stream.subscribe_trade_updates(handler)
stream.run()  # Blocks — needs asyncio integration (see MD-4a-4)
```

**Files to create:**
- `argus/execution/alpaca_broker.py`
- `tests/execution/test_alpaca_broker.py`

---

### Component 5: Alpaca Config in `brokers.yaml` + Dependency Wiring

**Update `config/brokers.yaml`** with the new AlpacaConfig fields (shown above in Component 2).

**Update `BrokerRouter`** to instantiate `AlpacaBroker` when `primary: "alpaca"` and `alpaca.enabled: true`.

**Update the main entry point** (`argus/main.py` or wherever the system is wired together) to:
1. Load AlpacaConfig from brokers.yaml
2. Instantiate SystemClock
3. Pass Clock to RiskManager and strategies
4. Instantiate AlpacaDataService with config + event_bus + clock
5. Instantiate AlpacaBroker with config + event_bus
6. Wire the pipeline: DataService → Strategy → RiskManager → Broker

---

### Component 6: Integration Test

**Purpose:** Verify the full pipeline end-to-end with live Alpaca connections.

**Two levels of integration tests:**

**Level 1: Mocked integration (in main test suite)**
```python
class TestAlpacaPipelineWithMocks:
    """Full pipeline test using mocked Alpaca clients.
    
    Tests:
    1. MockStockDataStream emits a bar → AlpacaDataService publishes CandleEvent
    2. CandleEvent triggers OrbBreakout → emits SignalEvent
    3. SignalEvent passes RiskManager → OrderApprovedEvent
    4. AlpacaBroker receives approved signal → calls MockTradingClient.submit_order()
    5. MockTradingStream sends fill event → AlpacaBroker publishes OrderFilledEvent
    
    All alpaca-py clients are mocked. No network calls. Runs in <1 second.
    """
```

**Level 2: Live Alpaca paper trading (optional, manual)**
```python
# File: tests/integration/test_alpaca_live.py
# Marked with: @pytest.mark.skipif(not os.getenv("ALPACA_API_KEY"), reason="No Alpaca keys")

class TestAlpacaLiveConnection:
    """Optional integration test with real Alpaca paper trading API.
    
    Requires ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables.
    Only run manually: pytest tests/integration/test_alpaca_live.py -v
    
    Tests:
    1. Connect AlpacaDataService, verify bars/trades arrive for SPY
    2. Connect AlpacaBroker, verify get_account() returns valid data
    3. Place a paper market order for 1 share of SPY, verify fill arrives
    4. Cancel the order or close the position
    5. Verify all events were published to Event Bus correctly
    """
```

**Files to create:**
- `tests/test_integration_sprint4a.py` (mocked pipeline)
- `tests/integration/test_alpaca_live.py` (live, optional)

---

## File Summary

### New Files
| File | Description |
|------|-------------|
| `argus/core/clock.py` | Clock protocol + SystemClock + FixedClock |
| `argus/data/alpaca_data_service.py` | Live data service (WebSocket + REST) |
| `argus/execution/alpaca_broker.py` | Live broker adapter (REST + WebSocket) |
| `tests/core/test_clock.py` | Clock tests |
| `tests/data/test_alpaca_data_service.py` | AlpacaDataService tests (mocked) |
| `tests/execution/test_alpaca_broker.py` | AlpacaBroker tests (mocked) |
| `tests/test_integration_sprint4a.py` | Full pipeline integration (mocked) |
| `tests/integration/test_alpaca_live.py` | Live Alpaca test (optional, manual) |

### Modified Files
| File | Changes |
|------|---------|
| `argus/core/config.py` | Add AlpacaConfig model |
| `argus/core/risk_manager.py` | Accept Clock parameter, replace datetime calls |
| `argus/strategies/base_strategy.py` | Accept Clock parameter, replace datetime calls |
| `argus/strategies/orb_breakout.py` | Pass Clock through from base |
| `config/brokers.yaml` | Updated with new AlpacaConfig fields |
| `requirements.txt` or `pyproject.toml` | Add `alpaca-py` and `python-dotenv` dependencies, remove `alpaca-trade-api` if present |
| `argus/main.py` (or entry point) | Add `load_dotenv()` call at top before any config loading |
| `.gitignore` | Verify `.env` is listed — add if missing |
| Existing tests | Update constructors to pass default Clock where needed |

---

## Testing Strategy

### Unit Tests (Mocked — in main test suite)

**test_clock.py (~8 tests):**
- SystemClock returns current time
- FixedClock returns fixed time
- FixedClock.advance() moves time forward
- FixedClock.set() changes time
- Today() respects timezone (e.g., 11 PM EST is still "today" even though UTC is "tomorrow")

**test_alpaca_data_service.py (~20 tests):**
- Mock `StockDataStream` — verify `subscribe_bars` and `subscribe_trades` called with correct symbols
- Simulate bar arriving → verify CandleEvent published to Event Bus with correct fields
- Simulate trade arriving → verify TickEvent published and price cache updated
- `get_current_price()` returns latest trade price
- `get_current_price()` raises ValueError for unknown symbol
- `get_indicator()` returns computed values after bar processing
- Indicator warm-up: verify historical candles fetched and fed through indicator engine
- VWAP resets at market open
- Stale data detection: no data for 30s → `is_stale` becomes True, alert published
- Stale data recovery: data resumes → `is_stale` becomes False
- Reconnection: simulate disconnect → verify backoff timing and re-subscribe
- `stop()` cleans up tasks and connections
- `get_historical_candles()` calls REST API with correct parameters

**test_alpaca_broker.py (~25 tests):**
- Mock `TradingClient` — verify `submit_order()` called with correct MarketOrderRequest
- Place market order → verify OrderResult returned with mapped IDs
- Place bracket order → verify correct OrderClass and stop/target prices
- Cancel order → verify `cancel_order_by_id()` called
- Modify order → verify `replace_order_by_id()` called
- Get positions → verify Alpaca Position mapped to our Position model correctly
- Get account → verify Alpaca Account mapped to our AccountInfo model correctly
- Flatten all → verify `close_all_positions(cancel_orders=True)` called
- Order ID mapping: our ULID ↔ Alpaca UUID bidirectional lookup
- Trade update handler: 'fill' event → OrderFilledEvent published
- Trade update handler: 'partial_fill' → OrderFilledEvent with partial qty
- Trade update handler: 'canceled' → OrderCancelledEvent published
- Trade update handler: 'rejected' → OrderCancelledEvent with reason
- Trade update handler: unknown Alpaca order ID → logged but no crash
- Error handling: Alpaca API returns error → appropriate exception raised
- Error handling: Network timeout → retry or exception (depending on operation)

**test_integration_sprint4a.py (~8 tests):**
- Full pipeline with all mocks: bar → strategy → risk → broker
- Signal that should be rejected by risk manager → no order placed
- Multiple symbols: bars for different symbols route to correct strategy state
- Account info flows correctly from AlpacaBroker to RiskManager

**Clock integration tests (~5 tests, added to existing test files):**
- Risk Manager with FixedClock: test daily reset at date boundary
- Risk Manager with FixedClock: test weekly P&L reset at Monday boundary
- Strategy with FixedClock: test `reset_daily_state()` at date boundary

**Estimated total new tests: ~66**
**Total after Sprint 4a: ~288** (222 existing + 66 new)

---

## Dependency Changes

**Add to requirements:**
```
alpaca-py>=0.30.0
python-dotenv>=1.0.0
```

**Remove (if present):**
```
alpaca-trade-api  # Deprecated, replaced by alpaca-py
```

**Verify no existing code imports from `alpaca_trade_api`.** If found, it's dead code — remove it.

---

## Implementation Order

Within this sprint, build in this sequence:

1. **Clock protocol** — smallest component, unblocks Risk Manager and Strategy modifications
2. **Clock injection into Risk Manager** — modify existing code, verify existing tests still pass
3. **Clock injection into BaseStrategy/OrbBreakout** — modify existing code, verify existing tests still pass
4. **AlpacaConfig** — add to config.py and update brokers.yaml
5. **AlpacaDataService** — the larger component; build and test with mocks
6. **AlpacaBroker** — build and test with mocks
7. **Integration test** (mocked pipeline)
8. **Final pass:** run all tests (`pytest tests/ -x`), verify 280+ passing, verify ruff clean

---

## Edge Cases and Gotchas

### alpaca-py Event Loop Integration
The biggest implementation risk in this sprint. alpaca-py's `StockDataStream.run()` and `TradingStream.run()` each want to own the event loop. Our system has its own asyncio loop. Claude Code should:
1. Read alpaca-py's source for `StockDataStream` and `TradingStream` to understand their internals
2. Look for `_run_forever()` or similar async methods that can be awaited directly
3. If they block, use `asyncio.to_thread()` and bridge events with `loop.call_soon_threadsafe()`
4. Test this integration early — don't save it for last

### Alpaca's One-Connection Limit
Most Alpaca subscriptions limit to 1 WebSocket connection per endpoint. This means:
- One `StockDataStream` connection (market data) — OK
- One `TradingStream` connection (order updates) — OK
- These are different endpoints, so both work simultaneously
- The Shadow System (future) cannot have its own `StockDataStream` — it must share the live one or use REST polling

### IEX vs SIP Data Feed
Free Alpaca accounts use IEX data feed, which is a subset of all trades (~10% of volume). This means:
- Bars may differ slightly from SIP (the full consolidated feed)
- Trade stream will have fewer ticks
- For paper trading and development, IEX is sufficient
- When going live, evaluate upgrading to SIP ($49/month) for better data quality

### Market Hours
AlpacaDataService should be aware of market hours:
- Regular hours: 9:30 AM – 4:00 PM EST
- The stale data monitor should only flag stale data during market hours
- Before market open and after close, lack of data is expected
- Use the Clock + system.yaml market_open/market_close for this check

### Bracket Order Limitations
As noted in Component 4, Alpaca's native bracket order supports only one take-profit level. For Sprint 4a, use T1 as the single target. Sprint 4b's Order Manager will handle the T1/T2 split by modifying orders dynamically after T1 hits.

### Error Handling for API Calls
All Alpaca REST API calls should be wrapped in try/except:
- `alpaca.common.exceptions.APIError` — Alpaca-specific errors (insufficient funds, invalid order, etc.)
- `requests.exceptions.ConnectionError` — Network issues
- `requests.exceptions.Timeout` — Timeout
- Log the error, publish appropriate event (OrderCancelledEvent with reason for order failures), and do not crash

### Paper Trading Account State
Alpaca paper accounts persist state between sessions. If tests place orders, they may affect future test runs. The live integration test should always clean up after itself (cancel orders, close positions).

### `.env` and Tests
Mocked unit tests must **never** depend on `.env` being present or API keys being set. Only the optional live integration test (marked with `skipif`) requires real keys. If any component fails to find API keys at init time, it should raise a clear error — not silently use empty strings.

---

## What This Sprint Does NOT Include

These are explicitly out of scope for Sprint 4a (deferred to later sprints):

- **Order Manager / Position Management** (Sprint 4b) — no stop-to-breakeven, no time stops, no trailing stops, no dynamic T1/T2 management
- **AlpacaScanner** (Sprint 4b) — still using StaticScanner for symbol selection
- **EOD Flatten** (Sprint 4b) — no scheduled end-of-day position closing
- **Health monitoring / heartbeat** (Sprint 5) — no external health checks yet
- **Multi-timeframe candle building** — only 1m, same as Sprint 3
- **Historical data backfill** — only 60-candle warm-up for indicators

---

## Post-Sprint Verification

After implementation, verify:

1. `pytest tests/ -x` — all tests pass (target 280+)
2. `ruff check argus/ tests/` — clean
3. Clock injection didn't break any existing Sprint 1-3 tests
4. AlpacaDataService mocked tests demonstrate correct event translation
5. AlpacaBroker mocked tests demonstrate correct order lifecycle
6. Integration test shows full pipeline with mocks
7. (Optional, manual) Live test with Alpaca paper API connects and places an order

---

## Docs Status After Sprint 4a

After this sprint completes, the following docs need updating:

- **CLAUDE.md:** Update Current State to "Sprint 4a complete". Add `alpaca-py` to Tech Stack. Remove `alpaca-trade-api` reference. Add Clock to components list.
- **07_PHASE1_SPRINT_PLAN.md:** Mark Sprint 4a ✅ Complete with test count.
- **05_DECISION_LOG.md:** Add DEC-039 (Sprint 4a micro-decisions: MD-4a-1 through MD-4a-6).
- **03_ARCHITECTURE.md:** Update Technology Stack table to show `alpaca-py` instead of `alpaca-trade-api`. Document Clock protocol in Module Specifications.
- **02_PROJECT_KNOWLEDGE.md:** Update current state, add new key decisions (alpaca-py switch, clock injection).

---

*End of Sprint 4a Implementation Spec*
