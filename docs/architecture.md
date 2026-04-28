# ARGUS — Architecture Document

> *Version 1.0 | February 2026*
> *This document defines the technical design of the Argus system. It translates the Project Bible's intent into implementation specifications. A developer should be able to read this document and know exactly how to build any component.*

---

## 1. System Tiers

Argus is built in three tiers. Tier 1 (Trading Engine) is the foundation. Tiers 2 and 3 are built incrementally in parallel with strategy validation, starting from MVP scope and expanding over time. See DEC-079.

### Tier 1: Trading Engine
The autonomous core. Runs headless (no UI). Communicates via internal event bus and exposes a REST/WebSocket API for Tier 2.

### Tier 2: Command Center
A Tauri desktop application (macOS/Windows/Linux) with a React frontend, served simultaneously as a mobile-responsive web app. Connects to Tier 1's API.

### Tier 3: AI Layer
Claude API integration for analysis, advisory, and approved actions. Connects to both Tier 1 (for data and action execution) and Tier 2 (for user-facing chat and approval UI).

All three tiers share a single database and configuration store.

---

## 2. High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                            │
│  Databento    IBKR API    Alpaca API    IQFeed (future)   Claude API│
└──────┬────────────┬────────────┬──────────────┬──────────────┬──────┘
       │            │            │              │              │
┌──────▼────────────▼────────────▼──────────────│──────────────│──────┐
│                   TIER 1: TRADING ENGINE                            │
│                                                                     │
│  ┌──────────┐   ┌──────────────┐   ┌────────────────┐              │
│  │  Broker  │   │ Data Service │   │    Scanner     │              │
│  │Abstraction│  │  (pub/sub)   │   │  (pre-market)  │              │
│  └────┬─────┘   └──────┬───────┘   └───────┬────────┘              │
│       │                │                     │                      │
│       │         ┌──────▼───────┐             │                      │
│       │         │  Event Bus   │◄────────────┘                      │
│       │         └──┬───┬───┬───┘                                    │
│       │            │   │   │                                        │
│  ┌────▼───┐  ┌─────▼┐ ▼  ┌▼──────────┐  ┌──────────┐             │
│  │ Order  │  │Strat │...│ Strat N   │  │Orchestrator│             │
│  │Manager │  │  1   │   │           │  │            │             │
│  └────┬───┘  └──┬───┘   └──┬────────┘  └─────┬──────┘             │
│       │         │           │                  │                    │
│       │    ┌────▼───────────▼──────────────────▼────┐              │
│       │    │           Risk Manager                  │              │
│       │    └────────────────┬────────────────────────┘              │
│       │                     │                                       │
│       ◄─────────────────────┘                                       │
│       │                                                             │
│  ┌────▼────────┐  ┌─────────────┐  ┌──────────────┐               │
│  │ Trade Logger│  │  Portfolio   │  │  Accounting  │               │
│  └─────────────┘  └─────────────┘  └──────────────┘               │
│                                                                     │
│  ┌──────────────────┐  ┌───────────────┐                           │
│  │  API Server      │  │ Notifications │                           │
│  │  (REST+WebSocket)│  │   Service     │                           │
│  └────────┬─────────┘  └───────────────┘                           │
└───────────┼─────────────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────────────┐
│                   TIER 2: COMMAND CENTER                            │
│  ┌─────────────────────────────────────────────────┐               │
│  │              React Frontend                      │               │
│  │  Dashboard | Strategy Lab | Controls | Reports  │               │
│  │  Approval Queue | Learning Journal | Settings   │               │
│  └─────────────────────────────────────────────────┘               │
│  Wrapped in Tauri (desktop) | Served as web app (mobile)           │
└─────────────────────────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────────────┐
│                   TIER 3: AI LAYER                                  │
│  Claude API ↔ System Context Builder ↔ Approval Workflow           │
│  Analysis Engine | Report Generator | Strategy Dev Assistant       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Specifications

### 3.1 Event Bus (`core/event_bus.py`)

The internal communication backbone. Components publish events and subscribe to event types. This decouples modules — strategies don't import the Risk Manager, they publish signals on the bus.

**Pattern:** In-process pub/sub using Python's `asyncio`. No external message broker needed for V1. FIFO delivery per subscriber. No global ordering guarantees or priority queues.

**Sequence Numbers:** Every event carries a monotonic sequence number assigned at publish time. This enables deterministic replay and post-hoc debugging — sort any event log by sequence number to reconstruct exact ordering.

**Event Types:**
```python
# Base event
@dataclass
class Event:
    sequence: int          # Monotonic, assigned by EventBus at publish time
    timestamp: datetime    # When the event was created

# Market data events
CandleEvent(symbol, timeframe, open, high, low, close, volume, timestamp)
TickEvent(symbol, price, volume, timestamp)
IndicatorEvent(symbol, indicator_name, value, timestamp)

# Scanner events
WatchlistEvent(date, symbols: list[WatchlistItem])
UniverseUpdateEvent(viable_count, total_fetched)

# Strategy events
SignalEvent(strategy_id, symbol, side, entry_price, stop_price, target_prices, share_count, rationale, atr_value)

# Risk events
OrderApprovedEvent(signal_event, modifications: dict | None)
OrderRejectedEvent(signal_event, reason: str)
SignalRejectedEvent(signal, rejection_reason, rejection_stage, quality_score, quality_grade, regime_vector_snapshot, metadata)

# Execution events
OrderSubmittedEvent(order_id, strategy_id, symbol, side, quantity, order_type)
OrderFilledEvent(order_id, fill_price, fill_quantity, timestamp)
OrderCancelledEvent(order_id, reason)

# Position events
PositionOpenedEvent(position_id, strategy_id, symbol, entry_price, shares, stop, targets)
PositionUpdatedEvent(position_id, current_price, unrealized_pnl, stop_updated_to)
PositionClosedEvent(position_id, exit_price, realized_pnl, exit_reason, hold_duration)

# System events
CircuitBreakerEvent(level, reason, strategies_affected)
HeartbeatEvent(timestamp, system_status)
RegimeChangeEvent(old_regime, new_regime, indicators, regime_vector_summary)
ShutdownRequestedEvent(reason)
DataStaleEvent(symbol, last_tick_age_seconds)
DataResumedEvent(symbol, stale_duration_seconds)
AccountUpdateEvent(equity, cash, buying_power, positions_value, daily_pnl)
SessionEndEvent(trading_day, trades_count, counterfactual_count)

# Orchestrator events
AllocationUpdateEvent(strategy_id, new_allocation_pct, reason)
StrategyActivatedEvent(strategy_id, reason)
StrategySuspendedEvent(strategy_id, reason)

# Approval events
ApprovalRequestedEvent(action_id, action_type, description, risk_level)
ApprovalGrantedEvent(action_id)
ApprovalDeniedEvent(action_id, reason)

# Intelligence events
CatalystEvent(symbol, category, quality_score, headline, source, timestamp)
OrderFlowEvent(symbol, imbalance_ratio, ask_thin_rate, tape_speed, bid_stack_score, composite_score, timestamp)
QualitySignalEvent(symbol, score, grade, risk_tier, components, rationale)
```

<!-- FIX-05 (P1-A2-M03): catalog previously listed a non-existent
`LearningInsightEvent`, omitted `ShutdownRequestedEvent` /
`DataStaleEvent` / `DataResumedEvent` / `AccountUpdateEvent` /
`SessionEndEvent`, and mis-described `UniverseUpdateEvent`
(actually two fields: `viable_count`, `total_fetched`). This block was
regenerated from `argus/core/events.py`; the broader API-catalog drift
was closed by IMPROMPTU-08 (2026-04-23, DEF-168) via
`scripts/generate_api_catalog.py` + the freshness gate at
`tests/docs/test_architecture_api_catalog_freshness.py`. -->


### 3.2 Data Service (`data/service.py`)

Single source of market data for the entire system.

**Responsibilities:**
- Subscribe to raw market data (WebSocket from broker) once per symbol
- Maintain in-memory current price state for all watched symbols
- Build candles at multiple timeframes in real-time (1s, 5s, 1m, 5m, 15m)
- Compute running indicators shared across strategies: VWAP, ATR(14), Relative Volume, Moving Averages (9, 20, 50)
- Expose subscription API: strategies register for specific data types per symbol
- Publish `CandleEvent`, `TickEvent`, `IndicatorEvent` to the Event Bus
- Abstract the data source: can be swapped between Alpaca, IBKR, Polygon, or the Replay Harness

**Interface:**
```python
class DataService(ABC):
    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """Start streaming data for these symbols. Publishes CandleEvent, TickEvent,
        and IndicatorEvent to the Event Bus. This is the sole streaming delivery
        mechanism — there is no callback-based subscription API."""

    async def stop(self) -> None:
        """Stop streaming and clean up connections."""

    async def get_current_price(self, symbol: str) -> float:
        """Synchronous lookup of last known price from in-memory cache."""

    async def get_indicator(self, symbol: str, indicator: str) -> float:
        """Synchronous lookup of current indicator value from in-memory cache."""

    async def get_historical_candles(self, symbol: str, timeframe: str,
                                      start: datetime, end: datetime) -> pd.DataFrame:
        """Fetch historical data via REST call or local cache."""

    async def get_watchlist_data(self, symbols: list[str]) -> dict:
        """Fetch current data summary for a list of symbols."""
```

**Data Delivery:** All streaming market data flows through the Event Bus. Strategies and other components subscribe to `CandleEvent`, `TickEvent`, and `IndicatorEvent` via the Event Bus. The synchronous query methods (`get_current_price`, `get_indicator`) serve a different purpose — point-in-time lookups for position sizing and indicator checks — and do not duplicate the streaming path.

**Implementations:**
- `DatabentoDataService` — **PRIMARY (DEC-082).** Databento US Equities Standard. Live TCP streaming via `databento` Python client (official, async). Subscribes to OHLCV-1m bars and trades streams, publishes CandleEvents and TickEvents through Event Bus. Full universe (no symbol limits). L2 depth (MBP-10) designed from Sprint 12, activated when strategies require it. Single live session with Event Bus fan-out. Session reconnection with exponential backoff.
- `VIXDataService` — **SUPPLEMENTAL (Sprint 27.9).** Ingests VIX (^VIX) + SPX (^GSPC) daily OHLC from Yahoo Finance (yfinance). Computes 5 derived metrics: vol-of-vol ratio, VIX percentile rank, term structure proxy, realized vol, variance risk premium. Persists to SQLite (`data/vix_landscape.db`). Trust-cache-on-startup pattern (DEC-362). Daily update task during market hours. Self-disables when data exceeds `max_staleness_days` (3 trading days). Config-gated via `vix_regime.enabled` in `config/vix_regime.yaml`. VixRegimeConfig Pydantic model with 3 boundary sub-models (VolRegimeBoundaries, TermStructureBoundaries, VRPBoundaries) and 4 string enums (VolRegimePhase, VolRegimeMomentum, TermStructureRegime, VRPTier). Not a DataService ABC implementation — standalone service wired into server lifespan.
- `IQFeedDataService` — **SUPPLEMENTAL (future).** IQFeed via Wine/Docker gateway. Forex ticks, Benzinga news, breadth indicators (TICK, TRIN, A/D). Added when forex strategies or Tier 2 news are built.
- `AlpacaDataService` — **INCUBATOR ONLY (DEC-086).** Live WebSocket via `alpaca-py`. Retained for strategy incubator paper testing. Not used for production data (IEX feed unreliable — DEC-081).
- `ReplayDataService` — reads historical Parquet files, drips into the system at configurable speed
- `BacktestDataService` — step-driven DataService controlled by ReplayHarness

**IndicatorEngine (DEF-013 / DEC-092):**

All DataService implementations delegate indicator computation to a shared `IndicatorEngine` class (`argus/data/indicator_engine.py`). This eliminates code duplication across the four services.

```python
@dataclass
class IndicatorValues:
    """Return type for IndicatorEngine.update() — all computed indicators."""
    vwap: float | None = None
    atr_14: float | None = None
    sma_9: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    rvol: float | None = None

class IndicatorEngine:
    """Stateful indicator computation engine, one per symbol."""
    def __init__(self, symbol: str) -> None: ...
    def update(self, open_, high, low, close, volume, timestamp_date=None) -> IndicatorValues: ...
    def reset_daily(self) -> None: ...
    def get_current_values(self) -> IndicatorValues: ...
    def warm_up(self, bars: list[dict]) -> None: ...
```

**Indicator behaviors:**
- **VWAP**: Resets daily. Cumulative typical_price × volume ÷ cumulative volume.
- **ATR(14)**: Carries across days. Wilder's smoothing: `(prev × 13 + TR) / 14`.
- **SMA(9/20/50)**: Carry across days. Simple moving averages of close prices.
- **RVOL**: Resets daily. Uses first 20 bars of day as baseline volume.
- **Auto-reset**: Engine detects day boundary via `timestamp_date` parameter.

**Full-universe computation (DEC-263, Sprint 23+):** The IndicatorEngine maintains full indicator state (VWAP, ATR, EMAs) for every symbol in the broad Databento subscription (3,000–5,000 symbols) from market open. Processing budget analysis confirms pure Python handles this at ~2–4% CPU utilization.

**Time-aware indicator warm-up (DEC-316, Sprint 23.7):** Pre-market boot (at or before 9:30 AM ET) skips warm-up entirely — the live Databento stream delivers candles from market open and the IndicatorEngine builds indicators naturally from the first candle. Mid-session boot (after 9:30 AM ET, crash recovery) enables lazy mode: on each symbol's first live candle arrival, a synchronous historical backfill fetches 1-min OHLCV data from 9:30 AM ET to current time via the Databento historical API. The backfill runs on the reader thread (per DEC-088) and completes before the candle is dispatched to strategies (preserving DEC-025 FIFO ordering). Thread safety for the warm-up tracking set is via `threading.Lock`. If the historical fetch fails, the symbol is marked as warmed (no retry loop) and the live candle is processed normally — strategies will not fire signals without valid indicator state (fail-closed).

### 3.2b Data Flow Architecture

```
Live Trading (Universe Manager enabled):
  FMP REST API ──────> FMPReferenceClient ──> UniverseManager (system filters, routing table)
                                                      │
  Databento US Equities ──TCP──> DatabentoDataService ─┤─ fast-path discard (non-viable)
                                        │              │
                                        │         EventBus (viable symbols only)
                                        │              │
                                        ├── CandleEvents (1m bars)     ├── Strategy 1 (via routing table)
                                        ├── TickEvents (every trade)   ├── Strategy 2 (via routing table)
                                        ├── IndicatorEvents (VWAP,ATR) ├── ...
                                        └── L2 Depth (post-revenue)    └── Strategy 30+

Live Trading (Universe Manager disabled / legacy):
  Databento US Equities ──TCP──> DatabentoDataService ──EventBus──> All Strategies
                                        │                              │
                                        ├── CandleEvents (1m bars)     ├── Strategy 1
                                        ├── TickEvents (every trade)   ├── Strategy 2
                                        ├── IndicatorEvents (VWAP,ATR) ├── ...
                                        └── L2 Depth (post-revenue)    └── Strategy 30+

Historical / Backtesting:
  Databento Historical API ──REST──> DataFetcher ──> Parquet files ──> VectorBT / Replay Harness
  (Existing Alpaca Parquet files also valid for backtesting)

Order Execution:
  Strategy → Risk Manager → Order Manager → BrokerAbstraction
                                              ├── IBKRBroker    → IB Gateway  [live + IBKR paper]
                                              ├── AlpacaBroker  → Alpaca API  [incubator paper]
                                              └── SimulatedBroker             [backtesting/shadow]

Future (when needed):
  IQFeed ──TCP/Wine──> IQFeedDataService ──EventBus──> Forex Strategies
                                        │                         News Classifier
                                        ├── Forex ticks            Breadth Monitor
                                        └── Benzinga news
```

**DatabentoDataService Configuration (DatabentoConfig):**
- `api_key`: Databento API key (from environment variable, never in code)
- `dataset`: "EQUS.MINI" (consolidated US equities — all exchanges in single feed, DEC-248)
- `schema`: ["ohlcv-1m", "trades"] (default). L2 ["mbp-10"] requires Plus tier (DEC-237), deferred post-revenue (DEC-238).
- `symbols`: list or "ALL_SYMBOLS" for full universe
- `reconnect_max_retries`: 10
- `reconnect_base_delay_seconds`: 1.0

**Implementation Status:** Sprint 12 ✅ COMPLETE (Feb 21), updated Sprint 21.5 (Mar 2–3). DatabentoConfig, DatabentoDataService (live streaming, reconnection with exponential backoff, indicators, stale data monitor, historical/Parquet cache). DataFetcher Databento backend with manifest tracking. DatabentoScanner (V1 watchlist with historical data lag resilience, DEC-247). DataSource enum for config-driven provider selection. Shared normalization via `argus/data/databento_utils.py` (DEC-091). Threading model: Databento reader thread → `call_soon_threadsafe()` → asyncio Event Bus (DEC-088). Production dataset: EQUS.MINI (DEC-248, supersedes XNAS.ITCH DEC-089) — consolidated US equities covering all exchanges in single feed. Symbol resolution uses Databento library's built-in `symbology_map` (DEC-242). Prices in fixed-point format ×1e9 (DEC-243). DatabentoSymbolMap removed (replaced by built-in mapping). Live streaming + all required schemas (ohlcv-1m, ohlcv-1d, trades, tbbo) verified on Standard plan. See `argus_market_data_research_report.md` Section 14. **Scanning data source (Sprint 21.7):** FMP Starter ($22/mo, DEC-258) provides pre-market daily bars and screener endpoints for gap/volume scanning, replacing the broken Databento historical daily bar path (DEC-247). Hybrid architecture: Databento for live streaming + backtesting, FMP for scanning (DEC-257). **Universe Manager integration (Sprint 23):** DatabentoDataService gains `set_viable_universe()` method and fast-path discard in `_on_ohlcv` and `_on_trade` — non-viable symbols are dropped before `_active_symbols` check and before IndicatorEngine processing. Backward compatible: when viable_universe is None (UM disabled), all symbols pass. **Indicator warm-up scaling (Sprint 23.7):** Time-aware warm-up (DEC-316) — pre-market boot skips warm-up; mid-session boot uses lazy per-symbol backfill. Replaced blocking per-symbol warm-up that took 12+ hours for 6,000+ symbols.

**Daily bars for regime classification (Sprint 25.7, DEC-347):** `fetch_daily_bars()` implemented via FMP stable API (`GET /stable/historical-price-eod/full`). Uses `aiohttp` GET with 10s timeout, returns DataFrame or None on any error. Called at startup (pre-market routine) and every 5 min (regime reclassification). Previously a stub returning `None` since Sprint 12.

**Data freshness tracking (Sprint 25.7):** `last_update` attribute set in `_dispatch_record()` on every incoming record. Exposed via health endpoint's `last_data_received` field.


### 3.3 Broker Abstraction (`execution/broker.py`)

Routes orders to the correct broker and asset class handler.

**Interface:**
```python
class Broker(ABC):
    async def place_order(self, order: Order) -> OrderResult
    async def place_bracket_order(self, entry: Order, stop: Order, targets: list[Order]) -> BracketOrderResult
    async def cancel_order(self, order_id: str) -> bool
    async def cancel_all_orders(
        self,
        symbol: str | None = None,
        *,
        await_propagation: bool = False,
    ) -> int  # DEC-364 no-args contract preserved; symbol/await_propagation added Sprint 31.91 S0 (DEC-386)
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult
    async def get_positions(self) -> list[Position]
    async def get_account(self) -> AccountInfo
    async def get_order_status(self, order_id: str) -> OrderStatus
    async def get_open_orders(self) -> list[Order]  # For state reconstruction (DEC-246)
    async def flatten_all(self) -> list[OrderResult]  # Emergency: close everything (uses SMART routing DEC-245)
```

**`cancel_all_orders` semantics (DEC-386, Sprint 31.91 Session 0):**
- No-args call (`cancel_all_orders()`): preserves DEC-364 contract — cancel ALL working orders. `IBKRBroker` invokes `reqGlobalCancel`; `SimulatedBroker` clears the in-memory pending list; `AlpacaBroker` emits `DeprecationWarning` and delegates to its legacy implementation (queued for Sprint 31.94 retirement).
- Per-symbol filter (`cancel_all_orders(symbol="AAPL")`): cancels only working orders for that symbol. Used by Session 1c's broker-only safety paths to clear stale yesterday OCA-group siblings before placing a follow-up flatten SELL.
- Propagation-await (`cancel_all_orders(symbol="AAPL", await_propagation=True)`): after issuing cancellations, polls broker open-orders for the filtered scope every 100ms until empty. 2-second timeout. Raises `CancelPropagationTimeout` (defined in `argus/execution/broker.py`) on timeout. The leaked-long failure mode on timeout is the intended trade-off vs. an unbounded phantom-short risk — see §3.7's OCA architecture block and DEC-386 for the asymmetric-risk rationale.

**Implementations:**
- `IBKRBroker` — **PRIMARY for live trading (DEC-083).** Wraps `ib_async` library (asyncio-native successor to `ib_insync`). Connects to IB Gateway (headless Java process, Docker containerized). SmartRouting across 20+ venues, no PFOF. 100+ order types including full bracket orders with multi-leg take-profit. Covers entire asset class roadmap (stocks, options, futures, forex, crypto) through single account.
- `AlpacaBroker` — **INCUBATOR paper testing only (DEC-086).** Wraps `alpaca-py` SDK. Excellent developer experience for rapid strategy prototyping. No real capital flows through Alpaca.
- `SimulatedBroker` — fills orders at historical prices (for Replay Harness and Shadow System)

**Order Routing:**
```python
class BrokerRouter:
    """Routes orders to the correct broker based on asset class and configuration."""
    def route(self, order: Order) -> Broker:
        asset_class = order.symbol.asset_class
        # Configurable routing rules in config/brokers.yaml
        return self.broker_map[asset_class]
```

**Implementation Status:** `SimulatedBroker`, `AlpacaBroker`, and `IBKRBroker` all implemented. `IBKRBroker` completed Sprint 13 (Feb 22, DEC-083/093/094) — 126 new tests, full Broker abstraction via `ib_async`. Config-driven broker selection via `BrokerSource` enum in `SystemConfig`. `DatabentoDataService` completed Sprint 12 (Feb 21, DEC-082). The comprehensive test suite against the `Broker` ABC and `DataService` ABC ensures all adapters are drop-in compatible.

### 3.3b Clock Protocol (`core/clock.py`)

Injectable time provider for components where date boundaries matter for logic or testing.
```python
class Clock(Protocol):
    def now(self) -> datetime:    # UTC, timezone-aware
    def today(self) -> date:      # In configured timezone (default America/New_York)
```

**Implementations:**
- `SystemClock` — production clock using real system time. Configurable timezone for `today()`.
- `FixedClock` — test clock with `advance(**kwargs)` and `set(new_time)` for controllable time.

**Injected into:** Risk Manager, BaseStrategy. Passed via constructor, defaults to `SystemClock` for backward compatibility.

### 3.3c IBKRBroker (`execution/ibkr_broker.py`)

Production execution broker using Interactive Brokers via `ib_async` library (DEC-083).

**Architecture:**
```
ARGUS ──ib_async──> IB Gateway (Java) ──> IBKR Servers ──> Exchanges
                         │
                    Docker container (recommended)
                    Nightly reset at ~11:45 PM ET
                    Auto-reconnect on restart
```

**Configuration (IBKRConfig):**
- `host`: "127.0.0.1" (IB Gateway on same machine)
- `port`: 4001 (live) or 4002 (paper)
- `client_id`: unique per connection (default 1)
- `account`: IBKR account ID
- `timeout_seconds`: 30

**Operational notes:**
- IB Gateway requires initial credential setup via browser. Session persists until manual logout or nightly reset.
- Nightly reset (~11:45 PM ET): Gateway disconnects briefly. IBKRBroker must implement reconnection with position verification.
- All stops placed broker-side — survive gateway disconnections.
- Paper trading uses separate paper account linked to live account. Same API, different port.

Implemented in Sprint 13 (Feb 22), updated Sprint 21.5 (Mar 2–3). 78 IBKRBroker tests + 13 Order Manager T2 tests + 8 integration tests. Sprint 21.5 additions: `flatten_all()` SMART routing fix (DEC-245 — uses `get_stock_contract()` instead of fill contract), `get_open_orders()` implementation with ULID recovery from `orderRef` (DEC-246). Live IBKR paper trading validated (Sessions 7–9). See DEC-083, DEC-093, DEC-094, and `argus_execution_broker_research_report.md` Section 11.

### 3.4 Base Strategy (`strategies/base_strategy.py`)

Every strategy implements this interface. Strategies follow a **daily-stateful, session-stateless** model:
- **Within a trading day:** Strategies accumulate state (opening range, trade count, daily P&L, active watchlist).
- **Between trading days:** All state is wiped by `reset_daily_state()`. No information carries over except what's in the database and config.
- **On mid-day restart:** Strategies reconstruct intraday state from the database (open positions, today's trades via the Trade Logger). The database is the durable source of truth; in-memory state is a performance cache.

```python
class BaseStrategy(ABC):
    # Identity
    strategy_id: str
    name: str
    version: str
    asset_class: AssetClass
    description: str

    # Configuration (loaded from YAML)
    config: StrategyConfig

    # State (daily-stateful: accumulates during market hours, reset between days)
    pipeline_stage: PipelineStage  # concept, exploration, validation, paper, live, etc.
    is_active: bool
    allocated_capital: float  # set by Orchestrator
    daily_pnl: float
    open_positions: list[Position]
    trade_count_today: int

    @abstractmethod
    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Called on each new candle. Return a signal if entry criteria are met, else None."""

    @abstractmethod
    async def on_tick(self, event: TickEvent) -> None:
        """Called on each tick. Used for fast strategies (scalp) and position management."""

    @abstractmethod
    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return the pre-market scanner filters for this strategy."""

    @abstractmethod
    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Return share count based on allocated capital and risk rules."""

    @abstractmethod
    def get_exit_rules(self) -> ExitRules:
        """Return stop loss, profit targets, time stop, trailing stop configuration."""

    @abstractmethod
    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return the market regime conditions under which this strategy may activate."""

    def check_internal_risk_limits(self) -> bool:
        """Check strategy-level risk limits (max daily loss, max positions, etc.)."""

    def set_watchlist(self, symbols: list[str], source: str = "scanner") -> None:
        """Set the strategy's watchlist. `_watchlist` is `set[str]` internally
        for O(1) membership checks. `watchlist` property returns `list[str]`
        — external API unchanged. `source` param logged for provenance
        (e.g., "scanner" or "universe_manager"). (DEC-343, Sprint 25.5)"""

    def reset_daily_state(self) -> None:
        """Called at start of each trading day. Wipes all intraday state.
        Clears `_watchlist` to `set()`."""

    async def reconstruct_state(self, trade_logger: TradeLogger) -> None:
        """Reconstruct intraday state from database after mid-day restart.
        Queries today's trades and open positions from the Trade Logger."""
```

### 3.4.1 ORB Strategy Family

The ORB strategy family uses a shared abstract base class for common logic:
```
OrbBaseStrategy (ABC)          ← shared: scanner criteria, gap filtering, OR tracking, breakout detection
├── OrbBreakoutStrategy        ← 2.0R target, 15min hold, T1/T2 split
└── OrbScalpStrategy           ← 0.3R single target, 120s hold, no T2
```

**OrbBaseStrategy** (`strategies/orb_base.py`): Provides shared opening range formation tracking, breakout detection with volume/VWAP confirmation, and scanner criteria. Subclasses override `_build_signal()` for target construction and `_get_time_stop_seconds()` for hold duration.

**Same-symbol mutual exclusion (DEC-261):** `_orb_family_triggered_symbols: ClassVar[set[str]]` shared across all OrbBaseStrategy subclasses. When either ORB Breakout or ORB Scalp fires a signal, the symbol is added to this set. Phase 2 breakout detection checks the set before evaluating — if the symbol is present, the strategy skips it. The set is cleared by `reset_daily_state()` each morning. Prevents dual-fire incidents where both ORB strategies open positions on the same symbol simultaneously.

**OrbScalpStrategy** (`strategies/orb_scalp.py`): Fast ORB variant. Single T1 target at 0.3R, 120-second max hold via per-signal `time_stop_seconds` field (DEC-122). No T2 split — trades too fast for partial exits (DEC-123). Uses same entry criteria as OrbBreakout but diverges entirely on exit management.

### 3.4.2 VWAP Reclaim Strategy (`strategies/vwap_reclaim.py`)

Mean-reversion strategy entering long when a stock reclaims VWAP after a pullback. Standalone from BaseStrategy (DEC-136).

**State Machine (DEC-138):** 5 states — WATCHING → ABOVE_VWAP → BELOW_VWAP → ENTERED (terminal) or REJECTED (terminal). Tracks pullback swing-low for stop placement (DEC-139).

**Key parameters:** `min_pullback_pct` (0.2%), `max_pullback_pct` (2%), `min_pullback_bars` (3), `volume_confirmation_multiplier` (1.2×), `max_chase_above_vwap_pct` (0.3%), `target_1_r` (1.0), `target_2_r` (2.0), `time_stop_minutes` (30).

**Operating window:** 10:00 AM – 12:00 PM ET. Position sizing with minimum risk floor (DEC-140) prevents oversizing on tight pullbacks. Cross-strategy ALLOW_ALL (DEC-141).

### 3.4.3 Afternoon Momentum Strategy (`strategies/afternoon_momentum.py`)

Consolidation breakout strategy entering on breakouts from midday tight ranges during afternoon session. Standalone from BaseStrategy (DEC-152).

**State Machine (DEC-155):** 5 states — WATCHING → ACCUMULATING → CONSOLIDATED → ENTERED (terminal) or REJECTED (terminal). Consolidation detected via high/low channel with ATR filter (DEC-153). Range updates continuously through CONSOLIDATED state — can still reject if range widens.

**Key parameters:** `consolidation_start_time` (12:00), `consolidation_atr_ratio` (0.75), `max_consolidation_atr_ratio` (2.0), `min_consolidation_bars` (30), `volume_multiplier` (1.2×), `max_chase_pct` (0.5%), `target_1_r` (1.0), `target_2_r` (2.0), `max_hold_minutes` (60), `stop_buffer_pct` (0.1%), `force_close_time` (15:45).

**Operating window:** Consolidation tracking from 12:00 PM, entries 2:00–3:30 PM, force close 3:45 PM ET. 8 simultaneous entry conditions (DEC-156). Dynamic time stop = min(max_hold_minutes, seconds until force_close) (DEC-157). Scanner reuses ORB gap watchlist (DEC-154).

### 3.4.4 PatternModule Subsystem — Sprint 26 ✅

Standardized pattern detection framework for composable, testable pattern modules.

**PatternModule ABC (`strategies/patterns/base.py`):**
```python
@dataclass(frozen=True)
class CandleBar:
    """Lightweight candle representation independent of events.py."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class PatternDetection:
    """Result of pattern detection."""
    detected: bool
    confidence: float       # 0–100
    entry_price: float
    stop_price: float
    target_prices: list[float]
    metadata: dict[str, Any]

class PatternModule(ABC):
    """Abstract base class for all pattern detection modules."""
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def lookback_bars(self) -> int: ...

    @abstractmethod
    def detect(self, bars: deque[CandleBar], indicators: dict, params: dict) -> PatternDetection | None: ...

    @abstractmethod
    def score(self, detection: PatternDetection, bars: deque[CandleBar], indicators: dict) -> float: ...

    @abstractmethod
    def get_default_params(self) -> dict[str, Any]: ...
```

**PatternBasedStrategy (`strategies/pattern_strategy.py`):**
Generic wrapper that turns any `PatternModule` into a full `BaseStrategy`. Handles operating window enforcement, per-symbol candle deque management (via `CandleBar` conversion from `CandleEvent`), watchlist gating, signal generation with T1/T2 targets from detection, pattern strength calculation via `score()`, and evaluation telemetry. Configured via strategy YAML with `pattern_name` field. One `PatternBasedStrategy` instance per pattern module.

### 3.4.5 Red-to-Green Strategy (`strategies/red_to_green.py`) — Sprint 26 ✅

Gap-down reversal strategy entering long when a gapped-down stock reclaims a key level. Standalone from BaseStrategy (not PatternModule — uses traditional state machine approach).

**State Machine:** 5 states — WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED (terminal) or EXHAUSTED (terminal).

**Key levels:** VWAP, premarket_low, prior_close. Strategy identifies the nearest key level and monitors for reclaim. `max_level_attempts=2` — if price tests and fails a level twice, state transitions to EXHAUSTED.

**Key parameters:** `min_gap_down_pct` (1.0%), `max_gap_down_pct` (8.0%), `level_proximity_pct` (0.3%), `reclaim_confirmation_bars` (2), `volume_confirmation_multiplier` (1.5×), `target_1_r` (1.0), `target_2_r` (2.0), `time_stop_minutes` (15).

**Operating window:** 9:35–11:30 AM ET.

### 3.4.6 Bull Flag Pattern (`strategies/patterns/bull_flag.py`) — Sprint 26 ✅

Continuation pattern detecting pole+flag+breakout formations. Implements PatternModule ABC, deployed via PatternBasedStrategy wrapper.

**Detection:** Pole detection (strong upward move), flag validation (orderly pullback with declining volume), breakout confirmation above flag high. Measured move target based on pole length.

**Score weighting:** Pattern quality 30%, breakout strength 30%, volume confirmation 25%, flag tightness 15%.

**Operating window:** 10:00 AM – 3:00 PM ET. Config: `config/strategies/bull_flag.yaml`.

### 3.4.7 Flat-Top Breakout Pattern (`strategies/patterns/flat_top_breakout.py`) — Sprint 26 ✅

Resistance cluster breakout pattern. Implements PatternModule ABC, deployed via PatternBasedStrategy wrapper.

**Detection:** Resistance clustering (multiple touches of similar price level), consolidation validation with range narrowing, breakout confirmation above resistance with volume.

**Score weighting:** Resistance strength 30%, consolidation quality 30%, breakout conviction 25%, volume surge 15%.

**Operating window:** 10:00 AM – 3:00 PM ET. Config: `config/strategies/flat_top_breakout.yaml`.

### 3.4.8 Strategy Evaluation Telemetry — Sprint 24.5 ✅

Real-time and historical visibility into what every strategy evaluates on every candle. Diagnostic-only — does NOT flow through the EventBus (DEC-342).

**In-Memory Ring Buffer (`strategies/evaluation_buffer.py`):**
- `StrategyEvaluationBuffer(maxlen=1000)` attached to `BaseStrategy`
- `record_evaluation()` logs decision-point events at every strategy decision (time window checks, condition evaluations, signal generation, quality scoring)
- Entire method body wrapped in try/except — never raises, never affects trading logic
- 9 event types in `EvaluationEventType` (StrEnum): `TIME_WINDOW_CHECK`, `OPENING_RANGE_UPDATE`, `STATE_TRANSITION`, `INDICATOR_STATUS`, `CONDITION_CHECK`, `ENTRY_EVALUATION`, `SIGNAL_GENERATED`, `SIGNAL_REJECTED`, `QUALITY_SCORED`
- `ENTRY_EVALUATION` events in ORB family include `conditions_passed` (0–4) and `conditions_total` (4) in metadata for closest-miss analysis (DEC-350, Sprint 25.7)
- 3 result types: `PASS`, `FAIL`, `INFO`
- Timestamps use ET naive datetimes per DEC-276

**SQLite Persistence (`strategies/telemetry_store.py`):**
- `EvaluationEventStore` persists events to `data/evaluation.db` (separated from argus.db in Sprint 25.6, DEC-345)
- 7-day retention with ET-date-based cleanup
- Fire-and-forget async forwarding from buffer to store via `loop.create_task()`
- **Periodic retention task (DEF-197, IMPROMPTU-10, Sprint 31.9):** the store now spawns `_run_periodic_retention()` from `EvaluationEventStore.initialize()` on a 4-hour cadence (`RETENTION_INTERVAL_SECONDS = 4 * 60 * 60` in `argus/strategies/telemetry_store.py`). Each iteration calls `cleanup_old_events()` and survives per-iteration exceptions; `close()` cancels and awaits the task. This handles the multi-day session case where the previous startup-only `cleanup_old_events()` call couldn't keep up with ~5 GB/day ingestion — a session running >24 h would cross the 7-day retention boundary and accumulate day-8+ rows until next reboot. `RETENTION_DAYS=7` unchanged; the operator one-shot to reclaim the existing 14.5 GB DB is documented in IMPROMPTU-10's closeout (not committed code).

**REST Endpoint:**
- `GET /api/v1/strategies/{id}/decisions` — JWT-protected
- Returns buffer contents for today; supports `?date=YYYY-MM-DD` param for historical queries (routes to store for non-today dates, buffer for today)
- `AppState.telemetry_store` wired in server lifespan

**Frontend (`features/orchestrator/StrategyDecisionStream`):**
- TanStack Query hook (`useStrategyDecisions`) with 3-second polling
- Color-coded two-line event rows (PASS=green, FAIL=red, INFO=amber, signals=blue)
- Symbol filter dropdown, summary stats, expandable metadata
- Slide-out panel on Orchestrator page with AnimatePresence animation + Esc key close
- "View Decisions" button on strategy cards opens panel; optional `onViewDecisions` callback prop on `StrategyOperationsCard` and `StrategyOperationsGrid`

**Instrumentation Coverage:** All 7 strategies emit evaluation events at every decision point (OR accumulation, finalization, exclusion checks, entry conditions, signal generation, quality scoring). AfMo `_check_breakout_entry()` restructured from sequential early-return to evaluate-all-then-check pattern to support 8 individual `CONDITION_CHECK` events.

### 3.5 Risk Manager (`core/risk_manager.py`)

Every order passes through the Risk Manager before reaching the broker.

```python
class RiskManager:
    async def evaluate_signal(self, signal: SignalEvent) -> OrderApprovedEvent | OrderRejectedEvent:
        """
        Three-level gate:
        1. Strategy level: Check strategy's internal limits
        2. Cross-strategy level: Check aggregate exposure
        3. Account level: Check daily/weekly loss limits, cash reserve
        Returns approved (possibly with modifications) or rejected with reason.
        """

    async def on_position_update(self, event: PositionUpdatedEvent) -> None:
        """Monitor running positions for stop adjustments, time stops, etc."""

    async def check_circuit_breakers(self) -> CircuitBreakerEvent | None:
        """Check if any circuit breaker conditions are met."""

    async def daily_integrity_check(self) -> IntegrityReport:
        """Verify all open positions have broker-side stops. Reconcile with broker records."""
```

**Modification Rules:**

When a signal is partially valid, the Risk Manager may approve with modifications rather than rejecting outright:

| Permitted Modifications | Rules |
|------------------------|-------|
| Reduce share count | Reduce to fit concentration limit (DEC-249), buying power, or cash reserve. Multiple reductions cascade and accumulate. Includes pending entry exposure in concentration check to prevent race conditions. Reject if reduced position risk < `min_position_risk_dollars` ($100 absolute floor, DEC-251). Concentration check includes pending entry order exposure via `OrderManager.get_pending_entry_exposure()` to prevent race conditions when multiple signals approve before fills arrive. |
| Tighten profit targets | If cross-strategy exposure limits require faster exit. |

| Prohibited Modifications | Reason |
|-------------------------|--------|
| Widen stop loss | Strategy set the stop for a reason. Reduced shares is the correct response to excess risk. |
| Change entry price | Risk Manager gates execution; it does not alter the signal's thesis. |
| Change side (long/short) | Signal's direction is inviolable. |

All modifications are recorded in `OrderApprovedEvent.modifications` with a reason string. The Trade Logger records both the original `SignalEvent` and the modified execution parameters to enable analysis of modification frequency and impact.

**Configuration (from `config/risk_limits.yaml`):**
```yaml
account:
  daily_loss_limit_pct: 0.03       # 3% of account
  weekly_loss_limit_pct: 0.05      # 5% of account
  cash_reserve_pct: 0.20           # 20% always held
  max_concurrent_positions: 10
  emergency_shutdown_enabled: true

cross_strategy:
  max_single_stock_pct: 0.05       # 5% of account in any one stock
  max_single_sector_pct: 0.15      # 15% in any one sector
  duplicate_stock_policy: "priority_by_win_rate"

pdt:
  enabled: true                     # Track PDT limits
  account_type: "margin"            # or "cash"
  day_trades_remaining: 3           # Auto-tracked
```

### 3.6 Orchestrator (`core/orchestrator.py`)

Central coordinator for strategy lifecycle, capital allocation, and market regime classification. V1 is rules-based; designed for AI enhancement in V2+ (Sprint 22).

**Constructor:**
```python
class Orchestrator:
    def __init__(
        self,
        config: OrchestratorConfig,
        event_bus: EventBus,
        clock: Clock,
        trade_logger: TradeLogger,
        broker: Broker,
        data_service: DataService,
    ) -> None
```

**Supporting Components:**
- `RegimeClassifier` (`core/regime.py`): Rules-based SPY regime classification (V1). Computes SMA-20/50, 5-day ROC, 20-day realized vol (VIX proxy, DEC-113). Classifies into 5 regimes: BULLISH_TRENDING, BEARISH_TRENDING, RANGE_BOUND, HIGH_VOLATILITY, CRISIS. V2 (`RegimeClassifierV2`, Sprint 27.6) wraps V1 with 4 additional dimension calculators producing a multi-dimensional `RegimeVector` — see §3.6.1.
- `PerformanceThrottler` (`core/throttle.py`): Evaluates per-strategy performance using per-strategy daily P&L from `TradeLogger.get_daily_pnl(strategy_id=...)`. Three rules: 5 consecutive losses → REDUCE, negative 20-day Sharpe → SUSPEND, >15% drawdown → SUSPEND. Worst action wins. Zero-trade-history guard (DEC-349, Sprint 25.7): returns `ThrottleAction.NONE` immediately when both `trades` and `daily_pnl` are empty — prevents false suspension of strategies with no history.
- `CorrelationTracker` (`core/correlation.py`): Records daily P&L per strategy, computes pairwise Pearson correlation. Infrastructure for V2 correlation-adjusted allocation (DEC-116). Not yet wired into allocation math.

**Lifecycle:**
```python
class Orchestrator:
    async def start(self) -> None:
        """Subscribe to PositionClosedEvent, launch background poll loop."""

    async def stop(self) -> None:
        """Cancel poll loop, unsubscribe from events."""

    async def run_pre_market(self) -> None:
        """Full pre-market sequence:
        1. Reconstruct strategy state from trade log
        2. Fetch SPY daily bars, classify regime
        3. Get account equity from broker
        4. Calculate per-strategy allocations (equal-weight V1, DEC-114)
        5. Apply allocations, activate/deactivate strategies
        6. Log decisions to orchestrator_decisions table
        """

    async def run_end_of_day(self) -> None:
        """Post-close: record daily P&L per strategy to CorrelationTracker, log EOD decision."""

    @property
    def spy_data_available(self) -> bool:
        """Whether SPY daily bars have been loaded for regime classification (Sprint 25.7)."""
```

**Background Poll Loop (DEC-118):** Self-contained asyncio loop (no APScheduler). Triggers pre-market at configured time (default 09:25 ET), regime recheck every 30 minutes during market hours (DEC-115), EOD review at 16:05 ET. Daily flags reset at midnight.

**Periodic Regime Reclassification (DEC-346, Sprint 25.6):** Public `reclassify_regime()` method returns `tuple[MarketRegime, MarketRegime]` (old, new). Independent 300s asyncio task in `main.py._run_regime_reclassification()` with market hours guard (9:30–16:00 ET). Sleep-first pattern avoids redundant reclassification after pre-market routine. SPY unavailability retains current regime. Note: Orchestrator's own poll loop also calls `reclassify_regime()` via `_run_regime_recheck()` — both paths are idempotent (DEF-074 tracks consolidation).

**Intraday Monitoring:** Subscribes to `PositionClosedEvent`. Tracks per-strategy consecutive losses in-memory. Suspends strategy if intraday consecutive losses exceed threshold. Independent from pre-market throttle checks (which use full historical trade log).

**Allocation Math (V1):** Equal-weight across eligible active strategies. Deployable = equity × (1 - cash_reserve_pct). Per-strategy = min(1/N, max_allocation_pct) × deployable. REDUCE strategies get min_allocation_pct. Single-strategy cap at 40% accepted (DEC-119).

**Event Subscriptions:** PositionClosedEvent

**Events Published:** RegimeChangeEvent, AllocationUpdateEvent, StrategyActivatedEvent, StrategySuspendedEvent

**Decision Logging:** All allocation decisions persisted via `TradeLogger.log_orchestrator_decision()` to `orchestrator_decisions` table.

### 3.6.1 Regime Intelligence (Sprint 27.6)

Multi-dimensional regime classification replacing the single `MarketRegime` enum with a continuous `RegimeVector` across 10 dimensions (6 original + 4 VIX-based from Sprint 27.9). Config-gated via `regime_intelligence.enabled` in `config/regime.yaml` + `vix_calculators_enabled` flag.

**RegimeVector** (`core/regime.py`): Frozen dataclass capturing market environment across 11 fields:
1. **Trend** — `trend_score` (-1.0 bearish to +1.0 bullish) + `trend_conviction` (0.0–1.0). Derived from V1 RegimeClassifier's SPY SMA/ROC indicators.
2. **Volatility** — `volatility_level` (annualized realized vol, continuous) + `volatility_direction` (-1.0 falling to +1.0 rising). From V1's SPY 20-day realized vol.
3. **Breadth** — `universe_breadth_score` (fraction of universe above 20-day MA, 0.0–1.0) + `breadth_thrust` (bool, crossed threshold rapidly). Computed from live Databento candle stream.
4. **Correlation** — `average_correlation` (mean pairwise correlation of top N symbols) + `correlation_regime` ("dispersed"/"normal"/"concentrated"). Computed from cached daily returns.
5. **Sector Rotation** — `sector_rotation_phase` ("risk_on"/"risk_off"/"mixed"/"transitioning") + `leading_sectors`/`lagging_sectors`. Via FMP sector performance endpoint (graceful degradation on 403).
6. **Intraday Character** — `opening_drive_strength`, `first_30min_range_ratio`, `vwap_slope`, `direction_change_count` + `intraday_character` ("trending"/"choppy"/"reversal"/"breakout"). From SPY candle analysis at configurable times (default: 9:35/10:00/10:30 ET).
7. **Vol Regime Phase** (Sprint 27.9) — `vol_regime_phase` (Optional[VolRegimePhase]: CALM/TRANSITION/VOL_EXPANSION/CRISIS). VIX threshold-based classification. None when VIX data unavailable or stale.
8. **Vol Regime Momentum** (Sprint 27.9) — `vol_regime_momentum` (Optional[VolRegimeMomentum]: STABILIZING/NEUTRAL/DETERIORATING). VIX rate-of-change classification. None when unavailable.
9. **Term Structure Regime** (Sprint 27.9) — `term_structure_regime` (Optional[TermStructureRegime]: CONTANGO_LOW/CONTANGO_HIGH/BACKWARDATION_LOW/BACKWARDATION_HIGH). VIX term structure proxy classification. None when unavailable.
10. **Variance Risk Premium** (Sprint 27.9) — `variance_risk_premium` (Optional[VRPTier]: COMPRESSED/NORMAL/ELEVATED/EXTREME) + continuous value. VIX minus realized vol. None when unavailable.
11. **VIX Close** (Sprint 27.9) — `vix_close` (Optional[float]). Latest VIX closing price for reference. None when unavailable.

Backward-compatible: `primary_regime` field provides the same `MarketRegime` enum for existing consumers. `regime_confidence` (0.0–1.0) provides overall assessment confidence. `matches_conditions()` treats None as match-any for VIX dimensions (Sprint 27.9). `to_dict()` includes all 11 fields. `from_dict()` backward-compatible with pre-27.9 serialized vectors.

**RegimeOperatingConditions** (`core/regime.py`): Frozen dataclass defining acceptable regime ranges for strategy activation. Float dimensions use `(min, max)` inclusive ranges. String dimensions use list-of-allowed-values. 4 new Optional VIX enum fields (Sprint 27.9): `vol_regime_phase`, `vol_regime_momentum`, `term_structure_regime`, `variance_risk_premium`. `RegimeVector.matches_conditions()` checks all non-None constraints (AND logic). Empty conditions → always matches (vacuously true). Strategy YAMLs use match-any (no `operating_conditions` block = None defaults).

**RegimeClassifierV2** (`core/regime.py`): Composes V1 `RegimeClassifier` with 8 dimension calculators (4 original + 4 VIX from Sprint 27.9). Delegates trend + volatility to V1, adds breadth/correlation/sector/intraday + VIX phase/momentum/term structure/VRP. Constructor takes `OrchestratorConfig`, `RegimeIntelligenceConfig`, original 4 calculator instances, and optional VIXDataService reference. VIX calculators return None gracefully when VIX data unavailable or stale. `classify_regime_v2()` async method returns `RegimeVector`.

**Calculators (Original 4 — Sprint 27.6):**
- `BreadthCalculator` (`core/breadth.py`): Maintains per-symbol state (latest close, MA buffer). `update(symbol, close)` for streaming updates. `compute()` returns `(breadth_score, breadth_thrust)`. Configurable `ma_period`, `thrust_threshold`, `min_symbols`, `min_bars_for_valid`.
- `MarketCorrelationTracker` (`core/market_correlation.py`): Computes pairwise correlation of top N symbols over lookback window. `compute()` returns `(average_correlation, correlation_regime)`. Uses cached daily returns data (FMP daily bars or computed from Databento). Configurable `lookback_days`, `top_n_symbols`, `dispersed_threshold`, `concentrated_threshold`.
- `SectorRotationAnalyzer` (`core/sector_rotation.py`): Fetches sector performance from FMP. `compute()` returns `(sector_rotation_phase, leading_sectors, lagging_sectors)`. Graceful degradation on HTTP 403 (FMP Starter plan limitation). Uses `aiohttp` with timeout.
- `IntradayCharacterDetector` (`core/intraday_character.py`): Analyzes SPY intraday price action. `update(candle)` for streaming bar updates. `classify()` returns `(opening_drive_strength, first_30min_range_ratio, vwap_slope, direction_change_count, intraday_character)`. Configurable `first_bar_minutes`, `classification_times`, `min_spy_bars`, threshold parameters.

**VIX Calculators (4 new — Sprint 27.9, `core/vix_calculators.py`):**
- `VolRegimePhaseCalculator`: Classifies VIX level into CALM/TRANSITION/VOL_EXPANSION/CRISIS phases using configurable thresholds from VolRegimeBoundaries. Returns None when VIX data unavailable or stale.
- `VolRegimeMomentumCalculator`: Classifies VIX rate-of-change as STABILIZING/NEUTRAL/DETERIORATING using vol-of-vol ratio and configurable momentum threshold. Returns None when unavailable.
- `TermStructureRegimeCalculator`: Classifies VIX term structure proxy into CONTANGO_LOW/CONTANGO_HIGH/BACKWARDATION_LOW/BACKWARDATION_HIGH using configurable thresholds from TermStructureBoundaries. Returns None when unavailable.
- `VarianceRiskPremiumCalculator`: Classifies VIX minus realized vol as COMPRESSED/NORMAL/ELEVATED/EXTREME using VRPBoundaries thresholds, also provides continuous VRP value. Returns None when unavailable.

**RegimeHistoryStore** (`core/regime_history.py`): SQLite persistence in `data/regime_history.db`. Fire-and-forget writes — exceptions logged, never disrupt trading. 7-day retention with automatic pruning. Stores serialized `RegimeVector` with computed_at timestamp. Schema: `regime_snapshots` table (`id` TEXT PK, `timestamp` TEXT ISO8601 UTC, `trading_date` TEXT ET YYYY-MM-DD, `primary_regime`, `regime_confidence`, `trend_score`, `trend_conviction`, `volatility_level`, `volatility_direction`, `universe_breadth_score`, `breadth_thrust`, `avg_correlation`, `correlation_regime`, `sector_rotation_phase`, `intraday_character`, `regime_vector_json` full `RegimeVector.to_dict()`, `vix_close REAL` nullable added Sprint 27.9 via idempotent ALTER TABLE). Indexes: `idx_regime_trading_date` on `trading_date`, `idx_regime_primary_date` on `(primary_regime, trading_date)`. FIX-05 (P1-A2-M08): schema block previously listed a non-existent `regime_history` table with ~6 columns.

**BacktestEngine Integration:** `use_regime_v2: bool` flag on `BacktestEngineConfig`. When enabled, BacktestEngine uses `RegimeClassifierV2` for regime tagging in `to_multi_objective_result()`.

**Observatory Integration (Sprint 27.6.1):** Orchestrator exposes `latest_regime_vector_summary` property (duck-typed `to_dict()`, no `RegimeVector` import). Observatory REST `/session-summary` and WebSocket push include `regime_vector_summary` field. Frontend `RegimeVitals` component in `SessionVitalsBar` renders regime dimensions.

**Config (`config/regime.yaml`):**
```yaml
enabled: true
persist_history: true
vix_calculators_enabled: true  # Enable VIX calculators in V2 classifier (Sprint 27.9)
breadth: { enabled: true, ma_period: 20, thrust_threshold: 0.80, min_symbols: 50 }
correlation: { enabled: true, lookback_days: 20, top_n_symbols: 50, dispersed_threshold: 0.30, concentrated_threshold: 0.60 }
sector_rotation: { enabled: true }
intraday: { enabled: true, first_bar_minutes: 5, classification_times: ["09:35","10:00","10:30"], min_spy_bars: 3 }
```

**VIX Config (`config/vix_regime.yaml`, Sprint 27.9; runtime config wired through `system.yaml`/`system_live.yaml` under `vix_regime:` key):**
```yaml
enabled: true
max_staleness_days: 3
fmp_fallback_enabled: false
vol_regime_boundaries: { calm_upper: 15.0, transition_upper: 20.0, expansion_upper: 30.0 }
term_structure_boundaries: { contango_threshold: 0.0, high_contango_threshold: 0.05 }
vrp_boundaries: { compressed_upper: -2.0, normal_upper: 3.0, elevated_upper: 8.0 }
momentum_threshold: 2.0
```

### 3.7 Order Manager (`execution/order_manager.py`)

Manages the lifecycle of every order from submission to fill/cancel. Position management is event-driven.

**Sprint 21.5.1 additions:** `_handle_flatten_fill()` matches positions by `strategy_id` (with fallback to first-open position + warning log) to correctly route flatten fills when multiple strategies hold positions in the same symbol. `get_pending_entry_exposure(symbol)` returns total notional from pending (unfilled) entry orders for use in Risk Manager concentration checks.

**Constructor:**
```python
class OrderManager:
    def __init__(
        self,
        event_bus: EventBus,
        broker: Broker,
        clock: Clock,
        config: OrderManagerConfig,
        trade_logger: TradeLogger | None = None,  # Optional, None in tests
    ) -> None
```

**Internal State:**
- `_managed_positions: dict[str, list[ManagedPosition]]` — Supports multiple positions per symbol
- `_pending_orders: dict[str, PendingManagedOrder]` — Keyed by order_id, tracks order type and context

**Event Subscriptions:** OrderApprovedEvent, OrderFilledEvent, OrderCancelledEvent, TickEvent, CircuitBreakerEvent

**Events Published:** OrderSubmittedEvent, PositionOpenedEvent, PositionClosedEvent

```python
class OrderManager:
    async def start(self) -> None:
        """Start the Order Manager. Launches fallback poll task."""

    async def stop(self) -> None:
        """Stop the Order Manager. Cancel the poll task."""

    async def on_approved(self, event: OrderApprovedEvent) -> None:
        """Convert approved signal to broker order(s). Submit entry order."""

    async def on_fill(self, event: OrderFilledEvent) -> None:
        """Handle fills by order type (entry, T1, stop, flatten).
        Entry fill: create ManagedPosition, submit stop + T1 orders.
        T1 fill: move stop to breakeven (cancel old, submit new).
        Stop/flatten fill: close position, publish PositionClosedEvent."""

    async def on_tick(self, event: TickEvent) -> None:
        """Primary position management trigger. On each tick:
        - Check T2 price reached → flatten remaining shares
        - Trailing stop: update trail_high watermark, compute trail stop via
          exit_math.compute_trail_stop_price(), flatten if price ≤ trail stop
          (belt-and-suspenders with broker stop as safety net)
        """

    async def on_cancel(self, event: OrderCancelledEvent) -> None:
        """Handle order cancellation from broker."""

    async def on_circuit_breaker(self, event: CircuitBreakerEvent) -> None:
        """Circuit breaker triggered. Emergency flatten all positions."""

    async def eod_flatten(self) -> None:
        """Close all positions at market. Called from poll loop when
        clock.now() >= eod_flatten_time. Sets _flattened_today flag."""
```

**Sprint 28.75 flatten-pending timeout (DEF-112):** `flatten_pending_timeout_seconds` (default 120s) + `max_flatten_retries` (default 3) on OrderManagerConfig. Stale flatten orders cancelled and resubmitted. Exhausted retries removed from `_flatten_pending` (caught by EOD flatten). `_flatten_pending` type changed from `dict[str, str]` to `dict[str, tuple[str, float, int]]` (order_id, monotonic_time, retry_count). ThrottledLogger rate-limiting on "flatten already pending" (60s/symbol) and "IBKR portfolio snapshot missing" (600s/symbol).

> **Active fix in flight (DEF-204, identified Apr 24, 2026 — IMPROMPTU-11 mechanism diagnostic; Sprint 31.91 in progress).** DEF-204's mechanism is a fill-side race: bracket children placed via `parentId` only without explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group with bracket children, produced ~98% of the unexpected-short blast radius observed during Apr 22–24 paper trading (44 symbols / 14,249 unintended short shares on Apr 24 alone, accumulated through gradual reconciliation-mismatch drift over a 6-hour session). ARGUS's exit-side accounting was also side-blind in three surfaces (reconcile orphan-loop one-direction-only; reconcile call site strips side info via `Position.shares = abs(int(ib_pos.position))`; DEF-158 retry path side-blind via `abs(int(getattr(bp, "shares", 0)))`). DEF-199's IMPROMPTU-04 fix correctly refuses to amplify these at EOD (1.00× signature, zero doubling) and escalates to operator with CRITICAL alert; the upstream mechanism is now being closed in Sprint 31.91. **Status as of 2026-04-27:** Sessions 0+1a+1b+1c have landed (DEC-386, Tier 3 architectural review #1 PROCEED) — the OCA architecture closes the ~98% mechanism. Sessions 2a–2d (side-aware reconciliation contract; DEC-385 reserved), Session 3 (DEF-158 retry side-check), and Session 4 (mass-balance + IMSR replay validation) remain in flight to close the secondary detection-blindness mechanism. Sessions 5a.1–5e (alert observability; DEC-388 reserved) remain in flight to make the new `phantom_short`/`cancel_propagation_timeout` alerts visible in the Command Center. **Operator mitigation in effect** (daily `scripts/ibkr_close_all_positions.py` at session close) until Sprint 31.91 sprint close + ≥3 paper sessions of zero `unaccounted_leak` mass-balance rows. See `docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md` for the original forensic analysis, `docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md` for the Sprint 31.91 deliverables, and DEC-386 for the OCA architecture rationale.

#### OCA Architecture (Sprint 31.91 Sessions 0+1a+1b+1c, DEC-386 — PROCEED 2026-04-27)

The OCA architecture is a 4-layer stack closing the bracket-internal fill race that produced ~98% of DEF-204's blast radius. Each layer is a strict superset of the prior layer's safety property (per Sprint 31.91 regression-checklist invariant 14 monotonic-safety matrix):

1. **API contract (Session 0).** `Broker.cancel_all_orders(symbol, *, await_propagation)` ABC extension + `CancelPropagationTimeout` exception class. See §3.3 for the interface; DEC-364 no-args contract preserved verbatim.

2. **Bracket OCA (Session 1a).** `IBKRBroker.place_bracket_order` sets `ocaGroup = f"oca_{parent_ulid}"` and `ocaType = config.ibkr.bracket_oca_type` (default 1) on each bracket child (stop, T1, T2). The parent (entry) Order is intentionally NOT in the OCA group, so an entry-fill does not OCA-cancel its own protection legs. `ManagedPosition.oca_group_id` persists at bracket-confirmation time. New Pydantic-validated `IBKRConfig.bracket_oca_type` field constrained to `[0, 1]`; ocaType=2 is architecturally wrong for ARGUS's bracket model; ocaType=0 is the RESTART-REQUIRED rollback escape hatch. Defensive `_is_oca_already_filled_error` helper distinguishes IBKR Error 201 / "OCA group is already filled" (SAFE — the bracket stop fired in the placement micro-window and the OCA group bought us out) from generic Error 201 (margin, price-protection); the rollback (DEC-117 invariant) STILL fires on both branches, only log severity differs. Phase A spike (`scripts/spike_ibkr_oca_late_add.py`) confirmed `PATH_1_SAFE` 2026-04-25 — IBKR enforces ocaType=1 atomic cancellation pre-submit. Spike result file freshness (≤30 days) is regression invariant 22.

3. **Standalone-SELL OCA (Session 1b).** Four paths thread `ManagedPosition.oca_group_id` onto the placed SELL Order: `_trail_flatten`, `_escalation_update_stop`, `_submit_stop_order` (which covers `_resubmit_stop_with_retry` per DEC-372), and `_flatten_position` (the central exit path used by EOD Pass 1, `close_position()`, `emergency_flatten()`, and time-stop). `oca_group_id is None` (covers `reconstruct_from_broker`-derived positions) falls through to legacy no-OCA behavior. Graceful Error 201 / OCA-filled handling: sets `ManagedPosition.redundant_exit_observed = True`, logs INFO, and short-circuits the DEF-158 retry path by deliberately NOT seeding `_flatten_pending`. The grep regression guard `tests/_regression_guards/test_oca_threading_completeness.py::test_no_sell_without_oca_when_managed_position_has_oca` enforces threading discipline; legitimate broker-only paths are exempted via the canonical `# OCA-EXEMPT: <reason>` comment.

4. **Broker-only safety (Session 1c).** Three broker-only SELL paths that have no `ManagedPosition` to thread (`_flatten_unknown_position`, `_drain_startup_flatten_queue`, `reconstruct_from_broker`) invoke `cancel_all_orders(symbol=X, await_propagation=True)` BEFORE placing the SELL (or BEFORE wiring the position into `_managed_positions`, for `reconstruct_from_broker`). On `CancelPropagationTimeout` (2-second budget exceeded), the SELL/wire is aborted, a critical `SystemAlertEvent(alert_type="cancel_propagation_timeout")` is emitted, and the position remains at the broker as a phantom long with no working stop. **The leaked-long failure mode is the intended trade-off** — phantom long is bounded exposure (the long position size; price floor of 0); an incorrect SELL placed without cancellation propagation could create an unbounded phantom short on a runaway upside. Operator response is manual flatten via `scripts/ibkr_close_all_positions.py`. **Critical caveat:** until Sprint 31.91 Session 5a.1 lands (HealthMonitor consumer for `SystemAlertEvent`), the alert is visible only in logs — not in the Command Center. Live-trading transition MUST NOT proceed before 5a.1 lands; see `docs/pre-live-transition-checklist.md`.

`reconstruct_from_broker()` carries a contractual STARTUP-ONLY docstring documenting that future RECONNECT_MID_SESSION callers MUST add a `ReconstructContext` parameter — the unconditional cancel-orders invocation is correct ONLY at startup (clears yesterday's stale OCA siblings); a mid-session reconnect would WIPE OUT today's working bracket children. The docstring is a time-bounded contract — Sprint 31.93 (DEF-194/195/196 reconnect-recovery) will replace the docstring with a runtime gate (DEF-211, sprint-gating). Until then, ARGUS does not support mid-session reconnect.

**Two follow-on sprint commitments inherited from DEC-386:**
- **Sprint 31.92** (component-ownership refactor; DEF-175/182/201/202): wire `IBKRConfig.bracket_oca_type` into `OrderManager.__init__` and replace the `_OCA_TYPE_BRACKET = 1` module constant in `argus/execution/order_manager.py` (DEF-212); also relocate `_is_oca_already_filled_error` from `ibkr_broker.py` to `broker.py` and rename to `is_oca_already_filled_error` (Tier 3 Concern A — sibling cleanup).
- **Sprint 31.93** (reconnect-recovery; DEF-194/195/196): add `ReconstructContext` parameter to `reconstruct_from_broker()` (DEF-211).

**Tier 3 architectural review #1 (PROCEED, 2026-04-27)** verdict artifact: `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md`.

#### ExecutionRecord Logging (`execution/execution_record.py`) — Sprint 21.6 ✅

ExecutionRecord logging (DEC-358 §5.1) captures expected vs actual fill price on every entry fill for slippage model calibration. Fire-and-forget — exceptions logged at WARNING, never disrupt order management. Data persisted to `execution_records` table.

```python
@dataclass
class ExecutionRecord:
    order_id: str
    symbol: str
    strategy_id: str
    expected_price: float        # From SignalEvent entry_price
    actual_price: float          # From OrderFilledEvent fill_price
    slippage_bps: float          # (actual - expected) / expected * 10000
    shares: int
    side: str
    timestamp: datetime
    market_cap_bucket: str | None
    avg_daily_volume: float | None   # Placeholder until UM reference data wired
    bid_ask_spread_bps: float | None # Requires L1 data (Standard plan limitation)
    venue: str | None
    order_type: str
    time_to_fill_ms: float | None
    fill_condition: str | None

    async def emergency_flatten(self) -> None:
        """Close all positions at market. Used by circuit breakers."""

    async def close_position(self, symbol: str) -> None:
        """Close specific position by symbol. Cancels child orders (stops,
        targets) and submits market sell. Routes through OrderManager for
        proper position tracking (DEC-352, Sprint 25.8)."""
```

**Position Management Architecture:**
- **Primary:** Event-driven via `TickEvent` subscription. On each tick, evaluates T2 price exit conditions and trailing stop conditions for open positions.
- **Fallback:** 5-second polling loop handles time-based exits (time stops, EOD flatten) and exit escalation (progressive stop tightening). Checked via `clock.now()` against configured thresholds.
- **EOD Flatten:** Checked in the fallback poll loop (not APScheduler per DEC-041). Default 3:50 PM ET, configurable via `eod_flatten_time` and `eod_flatten_timezone`.
- **Stop Management:** Cancel-and-resubmit pattern (not modify-in-place) per DEC-040. When T1 fills, old stop is cancelled and new stop at breakeven is submitted.
- **T1/T2 Split:** Entry uses market order, then separate limit orders for T1 target and stop. T2 exit is via tick monitoring + market flatten order.
- **Trailing Stops (Sprint 28.5):** After T1 fill, trail activates on remainder. `on_tick` updates `trail_high` watermark and computes trail stop via `exit_math.compute_trail_stop_price()` (ATR/percent/fixed modes). Belt-and-suspenders: broker stop order updated via AMD (approve-modify-delete) pattern, plus client-side flatten if price ≤ trail stop. Config: `config/exit_management.yaml` with per-strategy overrides merged via `deep_update()`.
- **Exit Escalation (Sprint 28.5):** Progressive stop tightening in poll loop based on hold time. Phases defined in `ExitEscalationConfig` (e.g., after 5min tighten to 0.5×, after 10min to 0.25×). Uses `exit_math.compute_escalation_stop()`. Escalation only tightens — never widens stop (AMD-8 guard).

**Data Models:**
```python
@dataclass
class ManagedPosition:
    position_id: str
    strategy_id: str
    symbol: str
    entry_price: float
    entry_time: datetime
    shares_total: int
    shares_remaining: int
    stop_price: float
    t1_price: float
    t2_price: float
    t1_shares: int
    t1_filled: bool = False
    stop_order_id: str | None = None
    t1_order_id: str | None = None
    realized_pnl: float = 0.0
    # Exit Management fields (Sprint 28.5)
    trail_active: bool = False
    trail_high: float | None = None
    trail_stop_price: float | None = None
    escalation_level: int = 0
    escalation_last_update: datetime | None = None

@dataclass
class PendingManagedOrder:
    order_id: str
    symbol: str
    strategy_id: str
    order_type: str  # "entry", "stop", "t1", "flatten"
    signal: SignalEvent | None = None
```

### 3.7b AlpacaScanner (`data/alpaca_scanner.py`)

Live pre-market scanner using Alpaca's snapshot API.

**Constructor:**
```python
class AlpacaScanner(Scanner):
    def __init__(
        self,
        config: AlpacaScannerConfig,
        alpaca_config: AlpacaConfig,
    ) -> None
```

**Interface (implements Scanner ABC):**
```python
class AlpacaScanner(Scanner):
    async def start(self) -> None:
        """Initialize StockHistoricalDataClient from alpaca-py."""

    async def stop(self) -> None:
        """Clean up client resources."""

    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Scan universe using Alpaca snapshots.
        1. Merge criteria from all active strategies (widest ranges)
        2. Fetch snapshots via get_stock_snapshot()
        3. Filter by gap%, price range, volume
        4. Sort by gap_pct descending
        5. Return top max_symbols_returned as WatchlistItems
        """
```

**Configuration (AlpacaScannerConfig):**
- `universe_symbols: list[str]` — Static list from config (DEC-043)
- `min_price`, `max_price` — Price range filter
- `min_volume_yesterday` — Volume filter
- `max_symbols_returned` — Cap on results

**Data Source:** Uses `StockHistoricalDataClient.get_stock_snapshot()` for batch snapshot retrieval. Gap calculated as `(open_price - prev_close) / prev_close`.

### 3.7c FMPScannerSource (`data/fmp_scanner.py`)

Pre-market scanner using Financial Modeling Prep (FMP) REST API. Primary scanner for production (DEC-258, Sprint 21.7).

**Constructor:**
```python
class FMPScannerSource(Scanner):
    def __init__(
        self,
        config: FMPScannerConfig,
    ) -> None
```

**Interface (implements Scanner ABC):**
```python
class FMPScannerSource(Scanner):
    async def start(self) -> None:
        """Read FMP_API_KEY from environment. Raises if missing."""

    async def stop(self) -> None:
        """Clear API key from memory."""

    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Scan using FMP gainers/losers/actives endpoints.
        1. Fetch from /stable/biggest-gainers, /stable/biggest-losers, /stable/most-actives (concurrent)
        2. Deduplicate (gainers/losers win over actives)
        3. Filter by price range, volume
        4. Sort by absolute gap_pct descending
        5. Return top max_symbols_returned as WatchlistItems
        Falls back to static symbols if API fails.
        """
```

**Configuration (FMPScannerConfig):**
- `min_price`, `max_price` — Price range filter (default 10–500)
- `min_volume` — Volume filter (default 500,000)
- `max_symbols_returned` — Cap on results (default 15)
- `fallback_symbols: list[str]` — Static fallback if API fails

**Data Source:** FMP REST API. Gap = `changesPercentage / 100`. Selection reason populated from endpoint source (`gap_up_X.X%`, `gap_down_X.X%`, `high_volume`).

**WatchlistItem Fields (Sprint 21.7):**
- `scan_source: str` — "fmp", "fmp_fallback", or "static"
- `selection_reason: str` — Human-readable selection rationale

### 3.7d Universe Manager (`data/universe_manager.py`, `data/fmp_reference.py`) — Sprint 23 ✅

Replaces the static pre-market watchlist with broad-universe monitoring. Config-gated: `universe_manager.enabled` in system.yaml. When disabled, existing scanner flow is unchanged.

**FMPReferenceClient** (`data/fmp_reference.py`):
```python
class FMPReferenceClient:
    def __init__(self, config: FMPReferenceConfig) -> None
    async def start(self) -> None          # Validate API key
    async def stop(self) -> None
    async def fetch_reference_data(self, symbols: list[str]) -> dict[str, SymbolReferenceData]
    async def fetch_float_data(self, symbols: list[str]) -> dict[str, float]
    async def build_reference_cache(self, symbols: list[str]) -> dict[str, SymbolReferenceData]
    def get_cached(self, symbol: str) -> SymbolReferenceData | None
    def is_cache_fresh(self) -> bool
    async def fetch_reference_data_incremental(self, symbols: list[str]) -> dict[str, SymbolReferenceData]
    def save_cache(self) -> None          # Atomic write: JSON temp file + os.replace()
    def load_cache(self) -> dict[str, SymbolReferenceData]
    def get_stale_symbols(self, symbols: list[str]) -> list[str]
```

Fetches Company Profile + Share Float in batches for ~3,000–5,000 viable symbols. OTC exchange detection via frozenset lookup. Graceful degradation when float data unavailable.

**Reference Data File Cache (DEC-314, updated DEC-317):** JSON file (`fmp_reference_cache.json`) with per-symbol `cached_at` timestamps. Incremental warm-up: `fetch_reference_data_incremental()` loads cache → diffs stale/missing symbols → fetches only delta → merges → saves. Reduces ~27-minute warm-up to ~2–5 minutes on subsequent runs. Atomic write via temp file + `os.replace()`. Corrupt file fallback returns empty dict. Configurable max age via `cache_max_age_hours` (default 24). **Periodic saves (DEC-317, Sprint 23.7):** Cache saved to disk every 1,000 successfully fetched symbols during fetch and on shutdown signal. Prevents data loss on interrupted cold-starts (previously lost all progress on Ctrl+C). FMP canary test at startup (`_run_canary_test()`) validates expected response keys — non-blocking WARNING on failure (DEC-313).

**SymbolReferenceData** dataclass: `symbol, name, sector, industry, market_cap, avg_volume, prev_close, float_shares, exchange, is_otc, is_etf, last_updated`.

**UniverseManager** (`data/universe_manager.py`):
```python
class UniverseManager:
    def __init__(self, config: UniverseManagerConfig, fmp_client: FMPReferenceClient) -> None
    async def build_viable_universe(self, symbols: list[str]) -> set[str]
    async def build_viable_universe_fallback(self, scanner_symbols: list[str]) -> set[str]
    def build_routing_table(self, strategy_configs: dict[str, Any]) -> None
    def route_candle(self, symbol: str) -> set[str]    # O(1) dict.get
    def get_strategy_symbols(self, strategy_id: str) -> set[str]
    def get_strategy_universe_size(self, strategy_id: str) -> int
    def get_universe_stats(self) -> dict
```

**System-level filters** (in `_apply_system_filters`): OTC exclusion, min/max price, min average volume. **Fail-closed on missing data (DEC-277):** symbols with None `prev_close` or `avg_volume` are excluded. Symbols with no cached reference data are excluded from routing.

**Routing table:** Pre-computed dict mapping each symbol to qualifying strategy IDs based on declarative `universe_filter` YAML configs per strategy. Each strategy declares: `min_price`, `max_price`, `min_market_cap`, `max_market_cap`, `min_float`, `max_float`, `min_avg_volume`, `sectors` (inclusion list), `exclude_sectors`. O(1) `route_candle()` lookup via `dict.get()`.

**Config:**
```yaml
# system.yaml
universe_manager:
  enabled: false          # Config gate — disabled by default
  min_price: 5.0
  max_price: 500.0
  min_avg_volume: 500000
  exclude_otc: true
  reference_cache_ttl_hours: 24
  fmp_batch_size: 100

# Per-strategy (e.g., config/strategies/orb_breakout.yaml)
universe_filter:
  min_price: 10.0
  max_price: 200.0
  min_avg_volume: 1000000
```

**Startup wiring (main.py):** Phase 7.5 (FMPReferenceClient start), Phase 8 (build viable universe after scanner), Phase 9.5 (build routing table after strategies loaded), Phase 10.5 (set viable universe on DatabentoDataService), Phase 11 (start streaming).

**Processing budget:** ~8,000–12,000 ticks/sec across full universe. Per-tick fast-path discard ~O(1) set lookup. Per-candle routing ~O(1) dict lookup. Total: ~2–4% of one CPU core in pure Python with ~97% headroom.

**Implementation Status:** Sprint 23 ✅ COMPLETE (Mar 7–8, 2026), updated Sprint 23.6 (Mar 10), Sprint 23.7 (Mar 11). FMPReferenceClient gains reference data file cache (DEC-314), canary test (DEC-313), incremental warm-up, and periodic cache saves (DEC-317). DEC-277 (fail-closed on missing reference data). Indicator warm-up scaled to full universe via time-aware approach (DEC-316).

### 3.8 Health Monitor (`core/health.py`)

Tracks system health, sends heartbeat pings, and dispatches critical alerts.

**Constructor:**
```python
class HealthMonitor:
    def __init__(
        self,
        event_bus: EventBus,
        clock: Clock,
        config: HealthConfig,
        broker: Broker | None = None,       # For integrity checks
        trade_logger: TradeLogger | None = None,  # For reconciliation
    ) -> None
```

**Responsibilities:**
- Component health registry (each component reports status via `update_component()`)
- Periodic heartbeat HTTP POST to configured URL (default: Healthchecks.io)
- Critical alert dispatch via webhook (Discord, Slack, or generic JSON)
- Daily integrity check (verify all open positions have broker-side stop orders)
- Weekly reconciliation (compare trade log with broker records)
- **Zero-evaluation health warning (DEC-344, Sprint 25.5):** `check_strategy_evaluations()` detects active strategies with populated watchlists but zero evaluation events after their operating window + 5 min grace period. Sets component status to DEGRADED. Self-corrects to HEALTHY when evaluations resume (idempotent). **Holiday suppression (Apr 3 hotfix):** check skips DEGRADED status on NYSE holidays — calls `is_market_holiday()` from `core/market_calendar.py` before raising DEGRADED. Periodic 60s asyncio task in main.py during market hours only (9:30–16:00 ET). Opens/closes its own `EvaluationEventStore` per check cycle to avoid coupling with server.py-managed store lifecycle.

**Status Model:** STARTING → HEALTHY → DEGRADED → UNHEALTHY → STOPPED

**Overall system status:** UNHEALTHY if any component is UNHEALTHY, DEGRADED if any DEGRADED, STARTING if any STARTING and none UNHEALTHY, HEALTHY otherwise.

**Configuration (from `config/system.yaml`):**
```yaml
health:
  heartbeat_interval_seconds: 60
  heartbeat_url: ""           # Healthchecks.io or similar
  alert_webhook_url: ""       # Discord webhook or similar
  daily_check_enabled: true
  weekly_reconciliation_enabled: true
```

### 3.8.1 NYSE Holiday Calendar (`core/market_calendar.py`) — Apr 3 hotfix

Pure algorithmic NYSE holiday detection. No external dependencies. Cached per-year computation.

**Functions:**
- `get_nyse_holidays(year: int) -> dict[date, str]` — returns all 10 NYSE holidays for the year with their names, applying observed-day shift rules (e.g., Saturday holiday → Friday, Sunday → Monday). Includes Easter via the Anonymous Gregorian algorithm (cross-validated against frontend `ui/src/utils/marketTime.ts`).
- `is_market_holiday(check_date: date) -> tuple[bool, str | None]` — returns `(True, holiday_name)` or `(False, None)`. Used as a guard in health monitor, orchestrator, and data service.
- `get_next_trading_day(from_date: date) -> date` — advances past weekends and holidays to find the next valid trading day.

**Integration points:**
1. `main.py` — startup logs holiday name + next trading day when current date is a holiday
2. `core/health.py` — `check_strategy_evaluations()` skips DEGRADED status on holidays
3. `data/databento_data_service.py` — heartbeat logs holiday context instead of zero-candle WARNING
4. `core/orchestrator.py` — `_is_market_hours()` returns False on NYSE holidays
5. `api/routes/market.py` — `GET /api/v1/market/status` endpoint (no JWT required)

**Limitation:** Early market close days (e.g., day before Thanksgiving, 1 PM close) are NOT detected — only full-day closures. ARGUS will operate normally on early-close days until this is extended.

---

### 3.8.2 Historical Query Service (`data/historical_query_service.py`) — Sprint 31A.5 ✅

Read-only analytical query layer over the Databento Parquet cache using DuckDB. Config-gated via `historical_query.enabled`. Provides SQL access to the 44.73 GB cache without any data import or ETL.

#### Cache Separation (Sprint 31.85)

ARGUS maintains **two Parquet caches** after Sprint 31.85. Confusing them is a latent data-integrity risk; this table is the canonical reference (full operator guide: `docs/operations/parquet-cache-layout.md`).

| Cache | Path | Layout | Consumers | Writable? |
|-------|------|--------|-----------|-----------|
| **Original** | `data/databento_cache/` | `{SYMBOL}/{YYYY-MM}.parquet` (~983K files) | `BacktestEngine` via `HistoricalDataFeed`; `scripts/resolve_symbols_fast.py`; `scripts/populate_historical_cache.py`; `scripts/run_experiment.py --cache-dir`; `argus/backtest/data_fetcher.py` | **NO — read-only. Source of truth.** |
| **Consolidated** | `data/databento_cache_consolidated/` | `{SYMBOL}/{SYMBOL}.parquet` (~24K files) with embedded `symbol` column | `HistoricalQueryService` (DuckDB) via `config/historical_query.yaml` | Rebuilt by `scripts/consolidate_parquet_cache.py`. Derived artifact. |

**Invariant:** `BacktestEngine` must never be pointed at the consolidated cache — it expects per-month files and will silently miss data if pointed elsewhere. Conversely, `HistoricalQueryService` should be pointed at the consolidated cache for query performance; pointing it at the original cache is functionally correct but impractically slow (VIEW scans take hours, TABLE materialization takes 16+ hours — the DEF-161 motivating observation).

**Consolidation tooling:** `scripts/consolidate_parquet_cache.py` merges the original cache's per-month files into one file per symbol with an embedded `symbol` column. Runs per-symbol under `ProcessPoolExecutor`, validates `consolidated_row_count == sum(monthly_row_counts)` (non-bypassable — no `--skip-validation` flag exists, and the `.tmp → rename` sequence is unreachable without passing validation), and optionally runs a three-query DuckDB benchmark suite via `--verify`/`--verify-only`. The original cache is read-only throughout (enforced by `test_original_cache_is_unmodified` snapshotting `st_size`/`st_mtime_ns`/`st_ino` per file). Repointing `config/historical_query.yaml` from `data/databento_cache` to `data/databento_cache_consolidated` is an operator action after first consolidation run.

#### Service Design

**Design:**
- In-memory DuckDB connection (`:memory:`) — no persistent DuckDB file. The Parquet cache IS the persistent store.
- Lazy initialization: DuckDB is imported and connected only on first query call.
- `CREATE VIEW` over Parquet directories using `regexp_extract` on file paths to extract symbol names from Databento path conventions (e.g., `TSLA_2025-06.parquet` → `TSLA`). The consolidated layout `{SYMBOL}/{SYMBOL}.parquet` preserves this pattern unchanged.
- **Databento schema note:** Parquet files use `timestamp` column (not `ts_event`). The VIEW aliases appropriately.

**6 query methods:**
- `get_available_symbols(min_bars: int = 0) -> list[str]`
- `get_coverage_summary() -> dict[str, Any]` — total symbols, total bars, date range, size on disk
- `get_bars(symbol: str, start: datetime, end: datetime) -> pd.DataFrame`
- `validate_symbol_coverage(symbols: list[str], start: str, end: str) -> dict[str, bool]` — key integration point for sweep tooling; returns per-symbol coverage status
- `get_cache_health() -> dict[str, Any]` — directory stats, file count, total size
- `execute_raw_query(sql: str) -> pd.DataFrame` — passthrough for ad-hoc analysis

**REST API** (`api/routes/historical.py`) — 4 JWT-protected endpoints:
- `GET /api/v1/historical/symbols` — list available symbols (optional `?min_bars=` filter)
- `GET /api/v1/historical/coverage` — summary statistics
- `GET /api/v1/historical/bars/{symbol}` — OHLCV bars for date range
- `POST /api/v1/historical/validate-coverage` — bulk symbol coverage check

**CLI:** `scripts/query_cache.py` — interactive SQL REPL with readline history, dot-commands (`.tables`, `.schema`, `.help`, `.quit`), formatted output.

**Dependency:** `duckdb>=1.0,<2` (added to `pyproject.toml`).

**Phase 2 integration roadmap:**
- **Sweep Tooling Impromptu:** `validate_symbol_coverage()` pre-filters symbols before parameter sweep
- **Sprint 31.5:** ExperimentRunner wires DuckDB validation for batch pre-validation + intelligent parallel worker partitioning (DEF-146)
- **Sprint 31B:** Research Console DuckDB backend for sweep heatmaps and SQL-based visualization (DEF-147)
- **Sprint 33:** Bootstrap confidence intervals and distributional analysis
- **Sprint 33.5:** Historical stress scenario queries against full 96-month dataset
- **Sprint 36+:** Hypothesis-to-SQL pattern mining and full-universe anomaly scanning

---

### 3.9 System Entry Point (`main.py`)

Wires all components together. The live sequence today has 19 phases (12 primary + 7 sub-phases: 7.5, 8.5, 9.5, 10.25, 10.3, 10.4, 10.7). Sub-phases were bolted on as features landed (Universe Manager, Regime V2, Quality Pipeline, Telemetry, Event Routing, Counterfactual) without renumbering the spine; this drift is cosmetic but worth the full enumeration below so the doc actually matches `argus/main.py` (FIX-03 P1-A1-M01 reconciliation, audit 2026-04-21; phase count corrected IMPROMPTU-07, DEF-198, 2026-04-23).

1. Config + Clock + EventBus
2. Database + TradeLogger (+ AI persistence tables: ConversationManager, UsageTracker, optional ActionManager)
3. Broker connection (IBKR / Alpaca / Simulated — lazy-imported per selection). **Startup position invariant (DEF-199, IMPROMPTU-04, Sprint 31.9):** immediately after `broker.connect()`, `check_startup_position_invariant()` (defined in `argus/main.py`) audits `broker.get_positions()` and sets `ArgusSystem._startup_flatten_disabled` to `True` on any non-BUY broker side (or on exception — fails closed). When the flag is True, the Phase 10 `OrderManager.reconstruct_from_broker()` call is gated off and the operator is required to clear the unexpected short manually via `scripts/ibkr_close_all_positions.py`. ARGUS is long-only by design (DEC-166); a short on the broker side at boot indicates either prior-session DEF-199 doubling (now closed) or DEF-204 upstream cascade (mechanism identified, fix scoped to `post-31.9-reconciliation-drift`).
4. HealthMonitor
5. RiskManager (with state reconstruction)
6. DataService (Databento or Alpaca)
7. Scanner (pre-market scan)
7.5. Universe Manager (if `universe_manager.enabled` and non-simulated broker): FMPReferenceClient start + viable-universe build
8. Strategy instantiation (ORB, ORB Scalp, VWAP Reclaim, Afternoon Momentum, Red-to-Green, plus PatternBasedStrategy roster built from declarative table at top of phase — FIX-03 P1-A1-M05)
8.5. Regime Intelligence V2 (if `regime_intelligence.enabled`): breadth / correlation / sector / intraday calculators + optional RegimeHistoryStore
9. Orchestrator construction + strategy registration + experiment-variant spawning (if `experiments.enabled`); then `orchestrator.start()`, telemetry-store wiring (moved earlier per FIX-03 P1-A1-M08 so ENTRY_EVALUATION events emitted during mid-day replay are not lost), regime V2 pre-market, and `orchestrator.run_pre_market()` (mid-day strategy-state reconstruction happens here via `PatternBasedStrategy.backfill_candles()` from IntradayCandleStore + `strategy.reconstruct_state(trade_logger)` — no separate mid-day replay path; the prior `_reconstruct_strategy_state` was orphaned and has been removed per FIX-03 P1-A1-C01)
9.5. Build routing table (if UM enabled, from strategy configs); populate each strategy's watchlist from UM routing via `strategy.set_watchlist(symbols, source="universe_manager")` (DEC-343, Sprint 25.5)
10. OrderManager (+ broker position reconstruction, strategy fingerprint registration, per-strategy `strategy_exit_overrides` including any experiment-variant overrides collected during spawning — FIX-03 P1-D2-M01)
10.25. Quality Pipeline (if `quality_engine.enabled` and non-simulated broker): SetupQualityEngine + DynamicPositionSizer + CatalystStorage against `data/catalyst.db`
10.3. Telemetry Store — actually initialized in phase 9 (above), retained as a numbering anchor for this doc; see P1-A1-M08
10.4. Event Routing (renumbered from 10.5 per FIX-03 P1-A1-L07 to free the 10.5 slot): IntradayCandleStore subscribes to CandleEvent; wire candle store into PatternBasedStrategy instances; subscribe the routing dispatcher + PositionClosedEvent + ShutdownRequestedEvent; regime V2 calculators subscribe to CandleEvent
10.7. Counterfactual Engine (if `counterfactual.enabled`): CounterfactualTracker + CounterfactualStore + 90-day retention enforcement
11. Start data streaming (set viable universe on DataService if UM enabled, warm up symbols, register background loops: evaluation health check, position reconciliation, counterfactual maintenance, optional background cache refresh). Regime reclassification cadence is owned by `Orchestrator._poll_loop` — the prior main.py-side 300s duplicate task was removed per FIX-03 P1-A1-M10 / DEF-074.
12. API server (in-process FastAPI)

Shutdown runs in reverse order. SIGINT/SIGTERM trigger graceful shutdown. Before the DB close, shutdown now closes `CatalystStorage` and `RegimeHistoryStore` symmetrically with the counterfactual and evaluation stores (FIX-03 P1-A1-M03 / P1-D1-M01). `ExperimentStore.enforce_retention(90d)` runs at boot alongside the counterfactual enforcement (FIX-03 P1-D2-M03); `LearningStore` retention is tracked in DEF-173.

**CLI:**
```
python -m argus.main                    # Default config
python -m argus.main --config /path/to  # Custom config
python -m argus.main --dry-run          # Connect but don't trade
```

### 3.10 Trade Logger (`analytics/trade_log.py`)

Every trade is recorded with comprehensive metadata.

**ID Format:** All `id TEXT PRIMARY KEY` columns use ULIDs (Universally Unique Lexicographically Sortable Identifiers) generated via the `python-ulid` library. ULIDs are globally unique, time-sortable, and 26 characters long. `ORDER BY id` returns records in chronological order.

**Database Schema (SQLite):**
```sql
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    strategy_version TEXT NOT NULL,
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    side TEXT NOT NULL,  -- 'long' or 'short'
    entry_price REAL NOT NULL,
    entry_time TEXT NOT NULL,
    exit_price REAL,
    exit_time TEXT,
    shares INTEGER NOT NULL,
    stop_price REAL NOT NULL,
    target_prices TEXT,  -- JSON array
    exit_reason TEXT,  -- 'target_1', 'target_2', 'stop_loss', 'time_stop', 'eod', 'manual', 'circuit_breaker'
    pnl_dollars REAL,
    pnl_r_multiple REAL,
    commission REAL DEFAULT 0,
    slippage REAL DEFAULT 0,  -- difference between intended and actual fill
    hold_duration_seconds INTEGER,
    market_regime TEXT,
    spy_price_at_entry REAL,
    vix_at_entry REAL,
    rvol_at_entry REAL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE strategy_daily_performance (
    date TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    trades_taken INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    gross_pnl REAL DEFAULT 0,
    net_pnl REAL DEFAULT 0,
    largest_win REAL DEFAULT 0,
    largest_loss REAL DEFAULT 0,
    avg_r_multiple REAL,
    allocated_capital REAL,
    market_regime TEXT,
    circuit_breaker_triggered BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (date, strategy_id)
);

CREATE TABLE account_daily_snapshot (
    date TEXT PRIMARY KEY,
    total_equity REAL NOT NULL,
    cash_balance REAL NOT NULL,
    deployed_capital REAL NOT NULL,
    total_pnl REAL NOT NULL,
    active_strategies INTEGER,
    total_trades INTEGER,
    market_regime TEXT,
    base_capital REAL,
    growth_pool REAL
);

CREATE TABLE orchestrator_decisions (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    decision_type TEXT NOT NULL,  -- 'allocation', 'activation', 'suspension', 'throttle'
    strategy_id TEXT,
    details TEXT,  -- JSON
    rationale TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE approval_log (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL,  -- 'low', 'medium', 'high'
    proposed_by TEXT NOT NULL,  -- 'orchestrator', 'risk_manager', 'claude', 'system'
    status TEXT NOT NULL,  -- 'pending', 'approved', 'rejected', 'expired'
    proposed_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,  -- 'user' or 'timeout'
    notes TEXT
);

-- Briefings (Sprint 21c, DEC-197)
CREATE TABLE IF NOT EXISTS briefings (
    id TEXT PRIMARY KEY,                    -- ULID
    date TEXT NOT NULL,                     -- YYYY-MM-DD
    briefing_type TEXT NOT NULL,            -- 'pre_market' or 'eod'
    status TEXT NOT NULL DEFAULT 'draft',   -- 'draft', 'final', 'ai_generated'
    title TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    metadata TEXT,                          -- JSON
    author TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(date, briefing_type)
);

-- Journal Entries (Sprint 21c, DEC-196 — updated types)
CREATE TABLE IF NOT EXISTS journal_entries (
    id TEXT PRIMARY KEY,                    -- ULID
    entry_type TEXT NOT NULL,               -- 'observation', 'trade_annotation', 'pattern_note', 'system_note'
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'user',
    linked_strategy_id TEXT,
    linked_trade_ids TEXT,                  -- JSON array
    tags TEXT,                              -- JSON array
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Documents (Sprint 21c, DEC-198)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,                    -- ULID
    category TEXT NOT NULL,                 -- 'research', 'strategy', 'backtest', 'ai_report'
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT 'user',
    tags TEXT,                              -- JSON array
    metadata TEXT,                          -- JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    component TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'healthy', 'degraded', 'down'
    latency_ms REAL,
    details TEXT
);

CREATE TABLE execution_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    expected_price REAL NOT NULL,
    actual_price REAL NOT NULL,
    slippage_bps REAL NOT NULL,
    shares INTEGER NOT NULL,
    side TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    market_cap_bucket TEXT,
    avg_daily_volume REAL,
    bid_ask_spread_bps REAL,
    venue TEXT,
    order_type TEXT NOT NULL,
    time_to_fill_ms REAL,
    fill_condition TEXT
);
CREATE INDEX idx_exec_records_symbol ON execution_records(symbol);
CREATE INDEX idx_exec_records_strategy ON execution_records(strategy_id);
CREATE INDEX idx_exec_records_timestamp ON execution_records(timestamp);
CREATE INDEX idx_exec_records_order ON execution_records(order_id);
-- Sprint 21.6: ExecutionRecord logging for slippage model calibration (DEC-358 §5.1)
```

### 3.10b Debrief Export (`analytics/debrief_export.py`) — Sprint 25.7 ✅

Automated export of debrief data during graceful shutdown (DEC-348). Produces `logs/debrief_YYYYMMDD.json` with 7 sections: session boundaries, positions, trades, signals, evaluations, catalysts, and errors. Each section independently try/excepted — cannot prevent shutdown. Lazy-imported in `shutdown()` to avoid import overhead during normal operation. Queries `argus.db`, `catalyst.db`, and `evaluation.db`. JSON artifact designed for paste into Claude.ai debrief protocol.

### 3.11 Intelligence Layer (`argus/intelligence/`)

New module directory housing all AI-enhanced trading intelligence components. These are distinct from core trading engine modules — they enrich the trading pipeline with quality signals but the engine functions without them (graceful degradation).

#### SetupQualityEngine (`intelligence/quality_engine.py`)
Composite scorer grading every potential trade 0–100 on six weighted dimensions.

Interface:
- `score_setup(symbol, pattern_type, pattern_strength, catalyst, volume_profile, regime, order_flow=None) -> SetupQuality`
  - V1: 5 dimensions (DEC-239). `order_flow` param reserved for post-revenue activation.
- `get_historical_match(pattern_type, catalyst_category, regime) -> HistoricalPerformance`

Events published: `QualitySignalEvent(symbol, score, grade, risk_tier, components, rationale)`
Config: `config/quality_engine.yaml` (weights, thresholds, tier mappings)

#### OrderFlowAnalyzer (`intelligence/order_flow.py`) — POST-REVENUE (DEC-238)
Processes Databento L2/L3 depth data into actionable signals. Requires Databento Plus tier ($1,399/mo, DEC-237). Historical L2 available on Standard for backtesting.

Interface:
- `start(symbols: list[str]) -> None` — begin L2 analysis
- `get_snapshot(symbol) -> OrderFlowSnapshot` — current state
- `stop() -> None`

Events published: `OrderFlowEvent(symbol, imbalance_ratio, ask_thin_rate, tape_speed, bid_stack_score, composite_score, timestamp)`
Throttling: configurable interval (default 100ms)
**Status:** Deferred to post-revenue. Historical backtesting can proceed on Standard plan.

#### CatalystPipeline (`intelligence/__init__.py`) — Sprint 23.5 ✅

Orchestrates catalyst ingestion, classification, and storage from three data sources (DEC-164, DEC-304). The `intelligence/` directory is flat (there is no nested `intelligence/catalyst/` subdirectory); `CatalystPipeline` itself lives in the package `__init__.py`. Path references in earlier drafts of this section pointed at `intelligence/catalyst/...` paths that do not exist; corrected FIX-07 P1-D1-M08 (audit 2026-04-21).

**Data Sources:**
- `SECEdgarClient` (`intelligence/sources/sec_edgar.py`): 8-K filings, Form 4 insider transactions
- `FMPNewsClient` (`intelligence/sources/fmp_news.py`): Stock news, press releases
- `FinnhubClient` (`intelligence/sources/finnhub.py`): Company news, analyst recommendations (DEC-306). Finnhub 403 responses downgraded from ERROR to WARNING with per-cycle request/403 counters and cycle summary log (Sprint 24.5 S6).

**Core Components:**
- `CatalystClassifier` (`intelligence/classifier.py`): Claude API classification with rule-based fallback (DEC-301). Categories: earnings, insider_trade, sec_filing, analyst_action, corporate_event, news_sentiment, regulatory, other (source of truth: `CatalystClassification.VALID_CATEGORIES` in `intelligence/models.py`).
- `CatalystStorage` (`intelligence/storage.py`): SQLite persistence with headline hash (SHA-256) deduplication (DEC-302).
- `BriefingGenerator` (`intelligence/briefing.py`): Pre-market intelligence brief generation with per-day cost ceiling via UsageTracker (DEC-303).

Interface (on `CatalystPipeline`):
- `async start()` / `async stop()` — lifecycle for all sources.
- `async run_poll(symbols: list[str], firehose: bool = False) -> list[ClassifiedCatalyst]` — single poll cycle (source fetch → headline-dedup → classify → semantic-dedup → batch-store → publish). Wraps source fetches in a single 120s safety-net `asyncio.wait_for(...)` (DEC-319); the caller in `intelligence/startup.py::run_polling_loop()` no longer double-wraps (FIX-07 P1-D1-M09).

`BriefingGenerator.generate_brief(symbols, date=None) -> IntelligenceBrief` is the separate pre-market brief entrypoint (distinct from `CatalystPipeline`).

Config: `catalyst.enabled` in system.yaml (default: false). Config-gated (DEC-300).

Events published: `CatalystEvent(symbol, category, quality_score, headline, source, timestamp)`

#### Intelligence Startup & Runtime (Sprint 23.6) ✅

**Startup Factory** (`intelligence/startup.py`, DEC-308):
- `IntelligenceComponents` dataclass: pipeline, storage, classifier, briefing_generator, sources
- `create_intelligence_components(config, event_bus, ai_client, usage_tracker, data_dir)` → builds all components from CatalystConfig; returns None when disabled
- `shutdown_intelligence(components)` → calls `pipeline.stop()` + `storage.close()`

**App Lifecycle Wiring** (DEC-310):
- `CatalystConfig` added to `SystemConfig` with `Field(default_factory=CatalystConfig)`
- Intelligence initialized in FastAPI lifespan handler after AI services, before WebSocket bridge
- AppState gains `catalyst_storage` and `briefing_generator` fields
- Graceful shutdown calls `shutdown_intelligence()` in reverse order

**Polling Loop** (`intelligence/startup.py`, DEC-315):
- `run_polling_loop(pipeline, config, get_symbols)` — asyncio task
- Market-hours interval: `poll_interval_seconds` (default 300) during 9:30–16:00 ET
- Off-hours interval: `poll_interval_off_hours_seconds` (default 1800)
- Symbols from Universe Manager viable_symbols (preferred) or cached_watchlist (fallback)
- Overlap protection: `asyncio.Lock()` prevents concurrent polls
- Graceful shutdown: `CancelledError` caught and re-raised

**Pipeline Enhancements** (Sprint 23.6):
- Semantic dedup: `_semantic_dedup()` groups by (symbol, category) within configurable time window (DEC-311)
- Batch-then-publish: `store_catalysts_batch()` single transaction, then per-item Event Bus publish (DEC-312)
- `fetched_at` column in catalyst_events table (ALTER TABLE migration for existing DBs)
- `get_total_count()` via `SELECT COUNT(*)` (replaces N-row fetch for pagination)
- SEC EDGAR `start()` validates `user_agent_email` config — raises ValueError if empty

Storage: separate `catalyst.db` SQLite file (DEC-309), path: `{data_dir}/catalyst.db`.

**Note on SQLite databases:** ARGUS uses five separate SQLite database files to avoid write contention:
- `data/argus.db` — trades, quality history, orchestrator decisions, conversation history, AI usage
- `data/catalyst.db` — catalyst events and classifications (DEC-309, Sprint 23.6)
- `data/evaluation.db` — strategy evaluation telemetry events (DEC-345, Sprint 25.6)
- `data/counterfactual.db` — counterfactual position tracking (DEC-345 pattern, Sprint 27.7)
- `data/learning.db` — learning reports, config proposals, config change history (DEC-345 pattern, Sprint 28)

#### Counterfactual Engine (`intelligence/counterfactual.py`, `counterfactual_store.py`, `filter_accuracy.py`) — Sprint 27.7 ✅

Tracks theoretical outcomes of rejected signals to measure filter accuracy for the Learning Loop.

**Shared Fill Model** (`core/fill_model.py`):
- `FillExitReason` enum: STOPPED_OUT, TARGET_HIT, TIME_STOPPED, EOD_CLOSED, EXPIRED
- `ExitResult` frozen dataclass: exit_reason + exit_price
- `evaluate_bar_exit()` pure function: worst-case-for-longs priority (stop > target > time_stop > EOD)
- Used by both BacktestEngine and CounterfactualTracker (single source of truth)

**CounterfactualTracker** (`intelligence/counterfactual.py`):
- Subscribes to `SignalRejectedEvent` via event bus handler in main.py
- On position open: backfills from IntradayCandleStore (may close immediately if stop breached)
- Forward monitoring via `CandleEvent` subscription using `evaluate_bar_exit()`
- MAE/MFE tracking per bar, time stop via elapsed seconds, EOD close via scheduled task
- No-data timeout (default 300s) expires stale positions
- Multiple positions per symbol tracked independently via `_symbols_to_positions` dict
- Zero-R guard: skips signals where entry_price == stop_price

Interface:
- `track(signal, rejection_reason, rejection_stage, metadata) -> str | None` — returns position_id (ULID)
- `async on_candle(event: CandleEvent) -> None` — O(1) short-circuit for untracked symbols
- `async close_all_eod() -> None` — idempotent EOD close
- `check_timeouts() -> list[str]` — returns expired position_ids

**CounterfactualStore** (`intelligence/counterfactual_store.py`):
- SQLite in `data/counterfactual.db` (DEC-345 isolated DB pattern)
- WAL mode, fire-and-forget writes with rate-limited warnings (60s)
- `write_open()`, `write_close()`, `query()`, `get_closed_positions()`, `enforce_retention()`
- 90-day default retention, enforced once per boot

**SignalRejectedEvent** (`core/events.py`):
- Frozen dataclass: signal (SignalEvent), rejection_reason (str), rejection_stage (str), quality_score, quality_grade, regime_vector_snapshot, metadata
- Published from 3 points in `_process_signal()`: quality filter, position sizer, risk manager
- Gated by `_counterfactual_enabled` flag (set True after tracker init)

**FilterAccuracy** (`intelligence/filter_accuracy.py`):
- `compute_filter_accuracy(store, date_range, strategy_filter, min_sample_count)` → `FilterAccuracyReport`
- Breakdowns by stage, reason, grade, regime, strategy
- "Correct rejection" = theoretical P&L ≤ 0; min sample threshold (default 10)
- Read-only (never modifies store data)

**Shadow Strategy Mode:**
- `StrategyMode` StrEnum (LIVE, SHADOW) in `base_strategy.py`
- Per-strategy `mode` field on `StrategyConfig` (default "live")
- Shadow routing at top of `_process_signal()`: bypasses quality pipeline and risk manager
- Shadow signals published as `SignalRejectedEvent` with `rejection_stage="shadow"`
- Strategy itself is unaware of its mode

Config: `counterfactual.enabled` in `config/counterfactual.yaml` (DEC-300 pattern). Fields: `enabled`, `retention_days`, `no_data_timeout_seconds`, `eod_close_time`.

REST: `GET /api/v1/counterfactual/accuracy` — JWT-protected, query params: start_date, end_date, strategy_id, min_sample_count.

#### Exit Management (`core/exit_math.py`, `config/exit_management.yaml`) — Sprint 28.5 ✅

Configurable per-strategy trailing stops, partial profit-taking with trail on T1 remainder, and time-based exit escalation (progressive stop tightening). Integrated into Order Manager, BacktestEngine, and CounterfactualTracker.

**Pure Functions** (`core/exit_math.py`):
- `compute_trail_stop_price(trail_high, mode, distance, entry_price, atr_value)` → `float` — ATR/percent/fixed modes via `StopToLevel` enum
- `compute_escalation_stop(entry_price, current_stop, initial_risk, phases, elapsed_seconds)` → `float | None` — phase-based progressive tightening, returns None if no escalation applies
- `validate_time_stop(time_stop_seconds)` → `int` — guards ≤ 0 values

**Config Models** (`core/config.py`):
- `TrailingStopConfig`: enabled, mode (atr/percent/fixed), atr_multiplier, percent_distance, fixed_distance, activation (on_t1/immediate)
- `ExitEscalationConfig`: enabled, phases list (sorted ascending by after_seconds)
- `ExitEscalationPhase`: after_seconds, stop_to_level (StopToLevel enum), stop_distance (fraction of initial risk)
- `ExitManagementConfig`: trailing_stop + escalation sub-configs
- `deep_update(base, override)` utility for per-strategy override merging

**Config** (`config/exit_management.yaml`):
- Global defaults (trailing stop disabled, escalation disabled)
- Per-strategy overrides via `strategy_exit_overrides` in system config
- Order Manager loads via `_get_exit_config(strategy_id)` with deep merge + LRU cache

**Integration Points:**
- **Order Manager** (`on_tick`): Trail activation after T1 fill, watermark tracking, belt-and-suspenders flatten. Poll loop: escalation check with phase progression.
- **BacktestEngine** (`_BacktestPosition` dataclass): Trail/escalation state per position, AMD-7 bar-processing order (escalation → trail → fill model).
- **CounterfactualTracker**: Trail/escalation state backfilled on position open, same AMD-7 processing order.
- **SignalEvent**: `atr_value: float | None` field emitted by all 7 strategies for ATR-based trail distance computation. R2G emits None (sync `_build_signal`, uses percent fallback — DEF-108).

**Belt-and-suspenders pattern:** Broker stop order is always maintained as a safety net (server-side protection). Client-side trail check in `on_tick` fires flatten if price breaches trail stop before broker stop triggers. Ensures protection even if broker stop update fails.

#### PreMarketEngine (`intelligence/premarket_engine.py`) — NOT YET IMPLEMENTED

Automated 4:00 AM → 9:25 AM pipeline. **Status:** Planned for Sprint 24+. CatalystPipeline (Sprint 23.5) provides the briefing generation component.

Interface (planned):
- `start() -> None` — begin pre-market scanning
- `generate_briefing() -> PreMarketBriefing`
- `lock_watchlist() -> Watchlist` — lock at 9:25 AM

#### DynamicPositionSizer (`intelligence/position_sizer.py`)
Maps quality grades to risk allocations. Replaces fixed risk_per_trade_pct.

Interface:
- `calculate_shares(quality, entry_price, stop_price, allocated_capital, buying_power) -> int`

#### Learning Loop V1 (`intelligence/learning/`) — Sprint 28 ✅

Closes the feedback loop between Quality Engine predictions and actual trading outcomes. Advisory-only ConfigProposal workflow — all recommendations require human approval before application. Config-gated via `learning_loop.enabled` in `config/learning_loop.yaml`.

**OutcomeCollector** (`intelligence/learning/outcome_collector.py`):
- Read-only queries across trades, counterfactual, and quality_history databases
- Collects `OutcomeRecord` dataclasses with source separation (trade vs counterfactual)
- `DataQualityPreamble` builder — summarizes data volume and completeness for reports
- No database writes — pure read layer

**WeightAnalyzer** (`intelligence/learning/weight_analyzer.py`):
- Source-separated Spearman rank correlations per quality dimension vs P&L outcomes
- P-value significance check (configurable threshold)
- Normalized positive correlation weight formula with `max_weight_change_per_cycle` guard (default ±0.10)
- Per-regime breakdown when sample size meets minimum
- Zero-variance guards for edge cases (all same scores, all same outcomes)

**ThresholdAnalyzer** (`intelligence/learning/threshold_analyzer.py`):
- Counterfactual-only analysis — compares rejected signals' theoretical outcomes
- Missed opportunity rate > 0.40 → recommend lowering grade threshold
- Correct rejection rate < 0.50 → recommend raising grade threshold
- Both can fire simultaneously; delta hardcoded at ±5 points for V1

**CorrelationAnalyzer** (`intelligence/learning/correlation_analyzer.py`):
- Pairwise Pearson daily P&L correlations over trailing window
- Trade-source preference (falls back to combined if insufficient trade data)
- Flagged pairs at |correlation| ≥ configurable threshold
- Overlap count per pair (concurrent positions on same day)
- Excluded strategies tracking (insufficient data)

**LearningService** (`intelligence/learning/learning_service.py`):
- Pipeline orchestrator: collect → analyze → report → persist → supersede → propose
- Concurrent execution guard (prevents parallel analysis runs)
- Auto-trigger via `SessionEndEvent` subscription after EOD flatten
- Zero-trade guard: skips analysis if no trades and no counterfactual positions in window
- Per-strategy `StrategyMetricsSummary` computation: trailing Sharpe (annualized, ddof=1, ≥5 trading days), win rate, expectancy (R-multiple preferred if ≥50% available, else raw P&L)
- Source preference for metrics: ≥5 trade → trade, ≥5 combined → combined, else insufficient

**ConfigProposalManager** (`intelligence/learning/config_proposal_manager.py`):
- Startup-only config application via `apply_pending()` — never writes mid-session
- Atomic YAML writes via tempfile + `os.rename()` on same filesystem
- Cumulative drift guard: max 20% total weight change over 30-day rolling window
- Weight redistribution maintains sum-to-1.0 invariant after clamping
- Proposal supersession: new proposals for same parameter supersede PENDING predecessors
- Writes to `quality_engine.yaml` (Quality Engine weights and thresholds)
- Config change history persisted for audit trail and revert capability

**LearningStore** (`intelligence/learning/learning_store.py`):
- SQLite persistence in `data/learning.db` (DEC-345 isolated DB pattern)
- WAL mode, fire-and-forget writes with rate-limited warnings
- 3 tables: `learning_reports`, `config_proposals`, `config_change_history`
- Retention enforcement protects reports referenced by APPLIED or REVERTED proposals

**SessionEndEvent** (`core/events.py`):
- Published after EOD flatten in shutdown sequence
- Carries `trades_count`, `counterfactual_count`, `trading_day`
- LearningService subscribes via Event Bus for auto-trigger

**REST API** (`api/routes/learning.py`) — 8 JWT-protected endpoints:
- `POST /api/v1/learning/trigger` — trigger analysis manually
- `GET /api/v1/learning/reports` — list reports (paginated)
- `GET /api/v1/learning/reports/{id}` — get specific report
- `GET /api/v1/learning/proposals` — list config proposals (filterable by status)
- `POST /api/v1/learning/proposals/{id}/approve` — approve proposal (with optional notes)
- `POST /api/v1/learning/proposals/{id}/dismiss` — dismiss proposal (with optional notes)
- `POST /api/v1/learning/proposals/{id}/revert` — revert applied proposal
- `GET /api/v1/learning/config-history` — config change audit trail

**CLI** (`scripts/run_learning_analysis.py`):
- `--window-days` (default from config), `--strategy-id` (optional filter), `--dry-run` (skip persistence)

**Frontend:**
- Performance page "Learning" tab (6th tab, lazy-loaded, keyboard shortcut 'l')
- `LearningInsightsPanel`: weight + threshold recommendation cards with approve/dismiss UX, conflicting signal detection and merged display
- `StrategyHealthBands`: real per-strategy metrics (Sharpe, win rate, expectancy) with green/amber/red bands
- `CorrelationMatrix`: custom SVG heatmap with tooltip including overlap count
- Dashboard `LearningDashboardCard`: pending count, last analysis timestamp, data quality indicator, "View Insights" link
- Responsive 3-column grid on desktop

### 3.Y AI Copilot (`argus/ai/`)

#### ClaudeService (`ai/claude_service.py`)
Anthropic API integration. All calls use Claude Opus (DEC-098). Prompt caching for system context.

#### ContextBuilder (`ai/context_builder.py`)
Assembles system state for Claude. Page-specific context payloads for Copilot. Insight data includes `session_status` (pre_market/open/closed), `session_elapsed_minutes` (from 9:30 ET), and `minutes_until_open` — replaces previous binary open/closed market status (Sprint 24.5 S6).

Interface:
- `build_context(page: str, selected_entity: dict | None) -> SystemContext`
- `build_trade_context(trade_id: str) -> TradeContext`
- `build_strategy_context(strategy_id: str) -> StrategyContext`

#### CopilotRouter (`ai/copilot_router.py`)
Handles chat messages with context injection. Manages conversation history. Routes action proposals through approval workflow.

### 3.Z Sprint Runner (Autonomous Execution Layer)
- **Location:** `scripts/sprint-runner.py`
- **Purpose:** Orchestrates sprint execution by invoking Claude Code CLI
- **Dependencies:** Claude Code CLI, git, ntfy.sh (optional)
- **State:** `docs/sprints/sprint-{N}/run-log/run-state.json`
- **Config:** `config/runner.yaml`
- **Mode:** Autonomous (full loop) or human-in-the-loop (logging only)
- **Key protocols:** Tier 2.5 triage, spec conformance check, notification

---

## 4. Command Center API (`argus/api/`)

Tier 1 exposes a REST + WebSocket API for the Command Center. In-process with the trading engine (Phase 11 of startup). Also runnable standalone in dev mode.

> **Catalog freshness (DEF-168, IMPROMPTU-08 — 2026-04-23).** The endpoint
> listings in §4, §7.8–7.9, §13.5.1, §14.2, and §15.8 are regenerated from
> the FastAPI `app.openapi()` schema via
> [`scripts/generate_api_catalog.py`](../scripts/generate_api_catalog.py).
> The WebSocket sub-section falls back to scanning
> `argus/api/websocket/*.py` for `@<router>.websocket(...)` decorators
> (FastAPI does not expose WebSocket routes in the OpenAPI schema).
> Run `python scripts/generate_api_catalog.py --verify` before editing to
> confirm docs are still in sync; `tests/docs/test_architecture_api_catalog_freshness.py`
> is the CI gate.

### Implementation Status (Sprint 14)

**Implemented:**
- JWT authentication (bcrypt hash, HS256 tokens, 24h expiry)
- Account overview endpoint
- Open positions with computed unrealized P&L and R-multiple
- Trade history with filtering and pagination
- Performance metrics (17 metrics, per-strategy breakdown, daily P&L)
- Strategy listing with config summaries
- System health with per-component status
- WebSocket bridge (EventBus → client streaming)
- Dev mode with mock data

### REST Endpoints (Implemented)

_Auto-generated from `app.openapi()` via `scripts/generate_api_catalog.py`.
All routes mount under the `/api/v1` prefix (see [argus/api/server.py](../argus/api/server.py))._

**account**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/account` | Get account overview with equity, P&L, and market status. |

**ai**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/ai/actions/pending` | Get all pending action proposals. |
| `POST   /api/v1/ai/actions/{proposal_id}/approve` | Approve a pending action proposal. |
| `POST   /api/v1/ai/actions/{proposal_id}/reject` | Reject a pending action proposal. |
| `POST   /api/v1/ai/chat` | Non-streaming chat endpoint. |
| `GET    /api/v1/ai/context/{page}` | Debug endpoint: inspect the context payload for a given page. |
| `GET    /api/v1/ai/conversations` | List conversations with optional filters. |
| `GET    /api/v1/ai/conversations/{conversation_id}` | Get a conversation with its messages. |
| `GET    /api/v1/ai/insight` | Get a brief AI-generated insight for the Dashboard. |
| `GET    /api/v1/ai/status` | Get AI service status and usage summary. |
| `GET    /api/v1/ai/usage` | Get detailed usage statistics. |

**arena**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/arena/candles/{symbol}` | Get recent 1-minute candles for a symbol. |
| `GET    /api/v1/arena/positions` | Get all open managed positions for the Arena page. |

**auth**

| Endpoint | Summary |
|----------|---------|
| `POST   /api/v1/auth/login` | Authenticate with password and receive a JWT token. |
| `GET    /api/v1/auth/me` | Get current authenticated user info. |
| `POST   /api/v1/auth/refresh` | Refresh an existing valid token with a new one. |

**config**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/config/goals` | Get goal tracking configuration. |

**controls**

| Endpoint | Summary |
|----------|---------|
| `POST   /api/v1/controls/emergency/flatten` | Emergency flatten all positions across all strategies. |
| `POST   /api/v1/controls/emergency/pause` | Emergency pause all strategies. |
| `POST   /api/v1/controls/positions/{position_id}/close` | Emergency close a specific position at market. |
| `POST   /api/v1/controls/strategies/{strategy_id}/pause` | Pause a strategy — stops generating new signals. |
| `POST   /api/v1/controls/strategies/{strategy_id}/resume` | Resume a paused strategy. |

**counterfactual**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/counterfactual/accuracy` | Get filter accuracy report for counterfactual positions. |
| `GET    /api/v1/counterfactual/positions` | Get shadow (counterfactual) positions with optional filters and pagination. |

**dashboard**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/dashboard/summary` | Get aggregated dashboard data in a single response. |

**debrief**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/debrief/briefings` | List briefings with optional filtering and pagination. |
| `POST   /api/v1/debrief/briefings` | Create a new briefing. |
| `DELETE /api/v1/debrief/briefings/{briefing_id}` | Delete a briefing. |
| `GET    /api/v1/debrief/briefings/{briefing_id}` | Get a single briefing by ID. |
| `PUT    /api/v1/debrief/briefings/{briefing_id}` | Update a briefing. |
| `GET    /api/v1/debrief/documents` | List all documents, merging filesystem and database sources. |
| `POST   /api/v1/debrief/documents` | Create a new document in the database. |
| `GET    /api/v1/debrief/documents/tags` | Get all unique tags from database documents. |
| `DELETE /api/v1/debrief/documents/{document_id}` | Delete a document. |
| `GET    /api/v1/debrief/documents/{document_id}` | Get a single document by ID. |
| `PUT    /api/v1/debrief/documents/{document_id}` | Update a document. |
| `GET    /api/v1/debrief/journal` | List journal entries with optional filtering and pagination. |
| `POST   /api/v1/debrief/journal` | Create a new journal entry. |
| `GET    /api/v1/debrief/journal/tags` | Get all unique tags from journal entries. |
| `DELETE /api/v1/debrief/journal/{entry_id}` | Delete a journal entry. |
| `GET    /api/v1/debrief/journal/{entry_id}` | Get a single journal entry by ID. |
| `PUT    /api/v1/debrief/journal/{entry_id}` | Update a journal entry. |
| `GET    /api/v1/debrief/search` | Search across all debrief content types. |

**experiments**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/experiments` | List experiments, optionally filtered by pattern name. |
| `GET    /api/v1/experiments/baseline/{pattern_name}` | Return the baseline experiment for a pattern. |
| `GET    /api/v1/experiments/promotions` | List promotion and demotion events with pagination. |
| `POST   /api/v1/experiments/run` | Trigger a parameter sweep for a pattern. |
| `GET    /api/v1/experiments/variants` | List all variants with experiment metrics where available. |
| `GET    /api/v1/experiments/{experiment_id}` | Return a single experiment by ID. |

**health**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/health` | Get system health status and diagnostics. |

**historical**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/historical/bars/{symbol}` | Return OHLCV bars for a symbol within a date range. |
| `GET    /api/v1/historical/coverage` | Return date coverage and bar count for the entire cache or one symbol. |
| `GET    /api/v1/historical/symbols` | Return all symbols present in the Parquet cache. |
| `POST   /api/v1/historical/validate-coverage` | Check whether each symbol has enough bars in the date range. |

**intelligence**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/catalysts/recent` | Get recent catalysts across all symbols. |
| `GET    /api/v1/catalysts/{symbol}` | Get catalysts for a specific symbol. |
| `GET    /api/v1/premarket/briefing` | Get the most recent pre-market briefing for a date. |
| `POST   /api/v1/premarket/briefing/generate` | Generate a new pre-market briefing. |
| `GET    /api/v1/premarket/briefing/history` | Get historical pre-market briefings. |

**learning**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/learning/config-history` | Get config change audit trail. |
| `GET    /api/v1/learning/proposals` | List config proposals with optional filters. |
| `POST   /api/v1/learning/proposals/{proposal_id}/approve` | Approve a PENDING proposal. 400 for illegal transitions. |
| `POST   /api/v1/learning/proposals/{proposal_id}/dismiss` | Dismiss a PENDING proposal. |
| `POST   /api/v1/learning/proposals/{proposal_id}/revert` | Revert an APPLIED proposal. 400 if not APPLIED or already REVERTED. |
| `GET    /api/v1/learning/reports` | List learning reports with optional date filters. |
| `GET    /api/v1/learning/reports/{report_id}` | Get a single learning report by ID. |
| `POST   /api/v1/learning/trigger` | Run the learning loop analysis pipeline. |

**market**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/market/status` | Get current market status including holiday information. |
| `GET    /api/v1/market/{symbol}/bars` | Get intraday bars for a symbol. |

**observatory**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/observatory/closest-misses` | Get symbols sorted by conditions passed (descending). |
| `GET    /api/v1/observatory/pipeline` | Get pipeline stage counts for all tiers with per-tier symbol lists. |
| `GET    /api/v1/observatory/session-summary` | Get aggregated session metrics. |
| `GET    /api/v1/observatory/symbol/{symbol}/journey` | Get chronological evaluation events for a symbol. |

**orchestrator**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/orchestrator/decisions` | Get paginated orchestrator decision history. |
| `POST   /api/v1/orchestrator/rebalance` | Trigger manual rebalance of strategy allocations. |
| `GET    /api/v1/orchestrator/status` | Get current orchestrator status including regime, indicators, and allocations. |
| `POST   /api/v1/orchestrator/strategies/{strategy_id}/override-throttle` | Temporarily override throttle for a strategy. |

**performance**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/performance/correlation` | Get strategy return correlation matrix. |
| `GET    /api/v1/performance/distribution` | Get R-multiple distribution histogram. |
| `GET    /api/v1/performance/heatmap` | Get trade activity heatmap by hour of day and day of week. |
| `GET    /api/v1/performance/{period}` | Get performance metrics for a time period. |

**positions**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/positions` | Get all open positions with computed unrealized P&L. |
| `GET    /api/v1/positions/reconciliation` | Get the latest position reconciliation result. |

**quality**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/quality/distribution` | Get today's quality grade distribution. |
| `GET    /api/v1/quality/history` | Get paginated quality history with optional filters. |
| `GET    /api/v1/quality/{symbol}` | Get the most recent quality score for a symbol. |

**session**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/session-summary` | Get session summary for a trading day. |

**strategies**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/strategies` | List all registered strategies with their status. |
| `GET    /api/v1/strategies/{strategy_id}/decisions` | Get recent evaluation events from a strategy's decision buffer. |
| `GET    /api/v1/strategies/{strategy_id}/spec` | Get strategy documents with metadata. |

**trades**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/trades` | Get trade history with filtering and pagination. |
| `GET    /api/v1/trades/batch` | Get multiple trades by their IDs in a single request. |
| `GET    /api/v1/trades/export/csv` | Export trades as a CSV file. |
| `GET    /api/v1/trades/stats` | Get aggregate statistics for filtered trades. |
| `GET    /api/v1/trades/{trade_id}/replay` | Get historical bars for replaying a trade. |

**universe**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/universe/status` | Get universe manager status and statistics. |
| `GET    /api/v1/universe/symbols` | Get paginated list of universe symbols with reference data. |

**vix**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/vix/current` | Get the latest VIX landscape data with regime classifications. |
| `GET    /api/v1/vix/history` | Get historical VIX data with derived metrics. |

**watchlist**

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/watchlist` | Get the current scanner watchlist with strategy status. |

### WebSocket

_Scanned from `@<router>.websocket(...)` decorators in
[argus/api/websocket/](../argus/api/websocket/) — FastAPI does not include
WebSocket routes in the OpenAPI schema._

| Endpoint | Module | Description |
|----------|--------|-------------|
| `WS /ws/v1/ai/chat` | `ai_chat` | AI Copilot chat streaming (token auth in first message) — detailed schema in §7.8 |
| `WS /ws/v1/arena` | `arena_ws` | Real-time Arena position/candle stream — detailed schema in §13.5.2 |
| `WS /ws/v1/live` | `live` | Event Bus bridge (positions, orders, prices, system, scanner, signals) |
| `WS /ws/v1/observatory` | `observatory_ws` | Pipeline stage counts + tier transitions (config-gated) |

Stream payloads for `/ws/v1/live`:

```
position.opened / position.closed / position.updated
order.submitted / order.filled / order.cancelled / order.approved / order.rejected
price.update       (throttled 1 Hz per symbol for generic clients)
system.heartbeat / system.circuit_breaker
scanner.watchlist
strategy.signal
```

Stream payloads for `/ws/v1/arena` (authentication via `?token={jwt}`):

```
arena_tick_price   (raw TickEvent, bypasses 1 Hz throttle — Sprint 32.8)
arena_tick         (price / pnl / r_multiple / trail_stop per open position, 1/sec/symbol)
arena_candle       (live + forming 1-min OHLCV bars)
arena_position_opened    (new position snapshot)
arena_position_closed    (symbol, exit_price, exit_reason, final_pnl)
arena_stats              (aggregate: open_count, total_unrealized_pnl, win/loss counts)
```

### Authentication
- Single-user system: password-only login (no username)
- JWT tokens (HS256) with configurable expiry (default 24h)
- All REST endpoints require `Authorization: Bearer {token}`
- Unauthenticated requests return HTTP 401 with `WWW-Authenticate: Bearer` header (DEC-351, Sprint 25.8). Uses `HTTPBearer(auto_error=False)` with explicit 401 response.
- WebSocket authenticates via `?token={jwt}` query parameter
- Password stored as bcrypt hash in config

## 4.1 Command Center Frontend (`argus/ui/`)

### Implementation Status (Sprint 21d)

Ten pages delivered with responsive design across four breakpoints (DEC-169 expanded in Sprint 25, 32.5, 32.75). Single React codebase targeting web and PWA mobile (Tauri desktop was scoped but never integrated — see DEF-174). Full animation system (Framer Motion), skeleton loading, emergency controls, trade detail panel, CSV export. Desktop icon sidebar with group dividers. Mobile 5-tab + More bottom sheet (DEC-211, DEC-216). AI Copilot shell panel (DEC-212). Test counts live in `CLAUDE.md` § Current State; pages enumerated in the next subsection.

### Pages

**Dashboard** (`/`): Ambient awareness surface (DEC-204). OrchestratorStatusStrip (clickable → Orchestrator page). StrategyDeploymentBar (per-strategy capital deployment with accent colors, click → Pattern Library or Orchestrator, DEC-219). GoalTracker (2-column pace dashboard with avg daily P&L and need/day metrics, color-coded pace indicator, DEC-220). Three-card row: MarketStatus (merged Market + Market Regime, DEC-221), TodayStats (2×2 metrics grid), SessionTimeline (SVG strategy windows with "now" marker, click → Orchestrator). Positions panel with table/timeline toggle and three-way filter All/Open/Closed (DEC-128). Recent trades list. SessionSummaryCard after hours (DEC-131). PreMarketLayout with placeholder cards (DEC-213, time-gated, data wired Sprint 23). Dashboard aggregate endpoint for single-request data loading (DEC-222). useSummaryData hook disabling pattern (DEC-223).

**Trade Log** (`/trades`): Filter bar (strategy, outcome, date range), stats summary row (total trades, win rate, net P&L), paginated trade table with color-coded exit reason badges. Row click opens TradeDetailPanel.

**The Arena** (`/arena`): Real-time multi-position visualization — 10th Command Center page (Sprint 32.75). Responsive grid of ArenaCard components (1–3 columns). Each card shows a MiniChart (live 1-min Lightweight Charts seeded from `GET /arena/candles/{symbol}` and updated via WS), position P&L badge (green/red), R-multiple, strategy badge (unique color + letter), and trail stop indicator. Cards with `pattern_score > 0.7` span 2 grid columns (priority sizing). Framer Motion AnimatePresence for card entry/exit with flash animation on position open. ArenaControls filter bar (strategy filter, sort by age/pnl/r). ArenaStatsBar aggregate row (open count, total P&L, net R — neutral color when netR=0). Disconnection overlay on WS loss. Keyboard shortcut: `4`.

**Performance** (`/performance`): Five-tab layout (DEC-218, DEC-228). Overview: MetricsGrid, EquityCurve (Lightweight Charts), DailyPnlChart, StrategyBreakdown, comparison toggle. Heatmaps: TradeActivityHeatmap (D3, DEC-206), CalendarPnlView. Distribution: RMultipleHistogram (Recharts), RiskWaterfall — side-by-side on desktop (DEC-227). Portfolio: PortfolioTreemap (D3, DEC-207), CorrelationMatrix — side-by-side 60/40 on desktop (DEC-227). Replay: TradeReplay (DEC-209) with trade selector and Lightweight Charts playback. Unified diverging color scale across all P&L charts (DEC-224). Dynamic WCAG text contrast (DEC-225). Strategy-level single-letter labels (DEC-226). Tab keyboard shortcuts: o/h/d/p/r (DEC-228). Performance Workbench customizable layout deferred (DEC-229).

**Orchestrator** (`/orchestrator`): Hero row — SessionOverview + RegimePanel stacked left, CapitalAllocation donut right (DEC-192). RegimePanel with visual gauge bars for Trend/Vol/Momentum (DEC-195). StrategyCoverageTimeline (custom SVG with "now" marker). StrategyOperationsGrid (2-col cards with allocation bars, throttle status, pause/resume). DecisionTimeline (newest-first, DEC-194). GlobalControls (force rebalance, emergency flatten/pause with ConfirmModal). ThrottleOverrideDialog (duration + mandatory reason). Emergency controls migrated from Dashboard.

**Pattern Library** (`/patterns`): IncubatorPipeline (10-stage horizontal pipeline with counts and click-to-filter). PatternCardGrid (filterable by family/time window, sortable). PatternCard (badges, stats, accent styling). PatternDetail (5 tabs: Overview, Performance, Backtest, Trades, Intelligence). OverviewTab (parameter table + document index with DocumentModal). PerformanceTab (strategy-filtered charts, DEC-183). BacktestTab (structured placeholder from config YAML, DEC-176). TradesTab (reuses TradeTable). IntelligenceTab (placeholder). Master-detail responsive layout (desktop 35%/65%, mobile drill-down). Arrow key navigation (DEC-185).

**The Debrief** (`/debrief`): Three-section SegmentedTab. Briefings (Pre-Market/EOD creation, editor with side-by-side markdown preview). Research Library (hybrid filesystem + database documents, DEC-198). Journal (4-filter dimensions, typed entry cards, inline editing, TradeSearchInput with linked trade chips). LIKE search (DEC-200). Batch trade fetch (DEC-203). Keyboard: b/r/j tabs, n new entry.

**System** (`/system`): SystemOverview (uptime, mode, broker/data sources). ComponentStatusList (infrastructure health). IntelligencePlaceholders (6 AI component cards with sprint target badges, DEC-210). EventsLog (WebSocket event stream).

**AI Copilot** (global panel, DEC-212): CopilotPanel slide-out (desktop 35% right, mobile 90vh bottom sheet). CopilotButton floating action (desktop bottom-right 24px, mobile above tab bar, DEC-217). Page context indicator. Placeholder content — activated Sprint 22. Keyboard: `c` toggle.

**Global panels:** SlideInPanel shared shell (DEC-177). SymbolDetailPanel (global, mounted in AppShell, click any symbol anywhere). TradeDetailPanel (slide-in from trade rows). WatchlistSidebar (desktop inline 280px / tablet slide-out / mobile overlay, DEC-147).

**TradeChart** (`components/TradeChart.tsx`, Sprint 21.5.1): TradingView Lightweight Charts v5 candlestick chart with price level overlays (entry blue, stop red, T1/T2 green, exit orange, current cyan) and entry/exit markers. Zoom padding scales with hold duration: max(50% of hold, 5 minutes). Embedded in both TradeDetailPanel (closed trades) and PositionDetailPanel (open positions). Data from `fetchSymbolBars()` via bars API endpoint with start_time/end_time parameters.

**PositionDetailPanel** (`features/dashboard/PositionDetailPanel.tsx`, Sprint 21.5.1): Live position detail view with P&L, price levels, and embedded TradeChart. Opened by clicking on a row in OpenPositions table.

### Responsive Breakpoints

| Breakpoint | Target Device | Navigation | Layout |
|-----------|--------------|------------|--------|
| 393px | iPhone SE/mini | Bottom tab bar | Stacked cards, compact tables |
| 834px | iPad portrait | Icon sidebar | Adapted grid, medium tables |
| 1194px | iPad landscape | Full sidebar | Full tables, side-by-side panels |
| 1512px | MacBook Pro | Full sidebar | Maximum information density |

### Navigation (Sprint 21d, DEC-211, DEC-216)

| Surface | Navigation | Pages |
|---------|-----------|-------|
| Desktop (≥1024px) | Icon sidebar with group dividers | All 10 pages visible |
| Tablet (640–1023px) | Icon sidebar | All 10 pages visible |
| Mobile (<640px) | Bottom tab bar (5 tabs) + More sheet | Dash, Trades, Orch, Patterns, More → (Performance, Arena, Debrief, System, Observatory, Experiments) |

Global keyboard shortcuts: `1`–`9` + `0` page navigation (0 = Experiments, 4 = The Arena), `w` watchlist toggle, `c` copilot toggle (DEC-199). All 10 pages accessible via keyboard.

### Tech Stack (Frontend)

| Component | Technology |
|-----------|-----------|
| Framework | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS v4 |
| State Management | Zustand |
| Navigation | React Router |
| Charts (time-series) | Lightweight Charts (TradingView) |
| Charts (standard) | Recharts (Sprint 17+, DEC-104) |
| Charts (custom viz) | D3 (Sprint 21+, DEC-108) |
| Animation | Framer Motion (DEC-110) |
| Server State | TanStack Query |
| Desktop | Tauri v2 |
| Testing | Vitest (DEC-130) |

### Planned Enhancements

See `docs/ui/ux-feature-backlog.md` for the complete prioritized inventory (35 features, Sprints 16–23+). Key upcoming:
- Sprint 16: ✅ Motion/animation, sparklines, skeleton loading, controls, trade detail panel, PWA, Tauri
- Sprint 17: ✅ Strategy allocation donut, risk utilization gauges, orchestrator interaction panel
- Sprint 18: ✅ SessionSummaryCard (after-hours recap), PositionTimeline (Gantt), three-way position filter, Zustand UI state persistence
- Sprint 21: ✅ Stock detail panel, Dashboard V2, 8 performance visualizations, Pattern Library, Orchestrator page, The Debrief, System cleanup, nav restructure, Copilot shell
- Sprint 22: AI insight cards, strategy optimization landscape

### Control Endpoints (Sprint 16, DEC-111)

_Auto-regenerated (DEF-168). `close_position` routes through
`OrderManager.close_position(symbol)` (DEC-352). `/trades/export/csv` is
owned by the trades router and appears in §4 above._

| Endpoint | Summary |
|----------|---------|
| `POST   /api/v1/controls/emergency/flatten` | Emergency flatten all positions across all strategies. |
| `POST   /api/v1/controls/emergency/pause` | Emergency pause all strategies. |
| `POST   /api/v1/controls/positions/{position_id}/close` | Emergency close a specific position at market. |
| `POST   /api/v1/controls/strategies/{strategy_id}/pause` | Pause a strategy — stops generating new signals. |
| `POST   /api/v1/controls/strategies/{strategy_id}/resume` | Resume a paused strategy. |

### Orchestrator Endpoints (Sprint 17)

_Auto-regenerated (DEF-168). Regime, indicators, allocations, throttle
state and per-strategy deployment are all served by `/orchestrator/status`
(DEC-135). `override-throttle` was added Sprint 29.5 S3._

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/orchestrator/decisions` | Get paginated orchestrator decision history. |
| `POST   /api/v1/orchestrator/rebalance` | Trigger manual rebalance of strategy allocations. |
| `GET    /api/v1/orchestrator/status` | Get current orchestrator status including regime, indicators, and allocations. |
| `POST   /api/v1/orchestrator/strategies/{strategy_id}/override-throttle` | Temporarily override throttle for a strategy. |

## 5. Backtesting Toolkit

Three-layer approach: VectorBT for fast parameter exploration, Replay Harness for tick-level fidelity validation, and BacktestEngine (Sprint 27) for production-code speed backtesting. Backtrader was dropped (DEC-046) — the Replay Harness runs actual production code, making Backtrader's intermediate-fidelity approach redundant.

### 5.1 VectorBT Layer (`backtest/vectorbt_orb.py`)

Used for rapid parameter exploration. Strategies are expressed in simplified vectorized form. Not a full simulation — an approximation for directional guidance on parameter sensitivity.
```python
# Example: ORB parameter sweep
import vectorbt as vbt

# Load historical 1-minute data
data = load_historical_data("2025-06-01", "2025-12-31", symbols=universe)

# Define parameter ranges
orb_windows = [5, 10, 15, 20, 30]
target_r = [1.0, 1.5, 2.0, 2.5, 3.0]
stop_buffers = [0.0, 0.1, 0.2, 0.5]
max_hold = [15, 30, 45, 60, 90, 120]
min_gaps = [1.0, 1.5, 2.0, 3.0, 5.0]

# Run combinatorial sweep (3,000 combinations per symbol)
results = sweep_orb_parameters(data, orb_windows, target_r, stop_buffers, max_hold, min_gaps)

# Output: DataFrame of metrics per parameter combination
# Visualize as 2D heatmaps to identify stable vs fragile regions
```

### 5.1.1 VectorBT ORB Scalp Layer (`backtest/vectorbt_orb_scalp.py`)

Scalp-specific sweep with a reduced 2-parameter grid: `scalp_target_r` (0.2, 0.3, 0.4, 0.5) × `max_hold_bars` (1, 2, 3, 5). Entry parameters inherited from ORB Breakout (DEC-076), not re-swept. Results are directional guidance only due to 1-minute bar resolution (DEC-127, RSK-026).

### 5.1.2 VectorBT VWAP Reclaim Layer (`backtest/vectorbt_vwap_reclaim.py`)

Precompute+vectorize architecture (DEC-144, ~500x speedup). Precomputes per-day entries from VWAP crossover patterns, vectorized exit detection for T1/T2/time-stop. Walk-forward dispatch: IS=VectorBT sweep, OOS=Replay Harness (DEC-145). Results provisional per DEC-132.

### 5.1.3 VectorBT Afternoon Momentum Layer (`backtest/vectorbt_afternoon_momentum.py`)

Precompute+vectorize architecture (DEC-162). Consolidation detection from midday bars (12:00–2:00 PM), breakout simulation during 2:00–3:30 PM window. ATR method divergence documented: VectorBT uses SMA(14), production uses Wilder's EMA — thresholds may not transfer exactly. Single entry per day (conservative vs live retry). Walk-forward pipeline dispatch. Results provisional per DEC-132.

### 5.1.4 VectorBT Red-to-Green Layer (`backtest/vectorbt_red_to_green.py`) — Sprint 26 ✅

Dedicated R2G backtester with gap-down detection, key level identification (VWAP, prior close), and reclaim entry simulation. Precompute+vectorize architecture. Walk-forward dispatch via `walk_forward.py`. WFE not evaluated (no historical data available at time of implementation) — Option 1 accepted (proceed to paper).

### 5.1.5 Generic PatternBacktester (`backtest/vectorbt_pattern.py`) — Sprint 26 ✅

Generic sliding-window backtester for any `PatternModule` implementation. Takes a PatternModule instance and runs backtests using the module's `detect()` and `score()` methods against historical OHLCV data. Parameter grid generation produces ±20% and ±40% variations of each default parameter. Self-contained walk-forward loop. Used for Bull Flag and Flat-Top Breakout backtesting.
```

### 5.1.6 BacktestEngine (`backtest/engine.py`) — Sprint 27 ✅

Production-code backtesting engine that runs real ARGUS strategy code against Databento OHLCV-1m historical data via synchronous event dispatch. Bridges the gap between VectorBT (fast but approximate) and Replay Harness (high-fidelity but slow) — BacktestEngine runs actual strategy code at ≥5x Replay Harness speed by using bar-level fills instead of synthetic tick generation.

**Key Components:**

- **SynchronousEventBus** (`core/sync_event_bus.py`): Sequential event dispatch with the same interface as the async EventBus. Subscribers receive events synchronously in subscription order. Enables deterministic, single-threaded backtesting without asyncio overhead.

- **HistoricalDataFeed** (`backtest/historical_data_feed.py`): Downloads Databento OHLCV-1m data via `timeseries.get_range()` with `metadata.get_cost()` pre-validation. Parquet cache layer: `{cache_dir}/{SYMBOL}/{YYYY-MM}.parquet`. Full-universe cache populated March 2026: 24,321 symbols × 153 months across 3 datasets — EQUS.MINI (Apr 2023 – present), XNAS.ITCH (May 2018 – Mar 2023), XNYS.PILLAR (May 2018 – Mar 2023). 44.73 GB in local cache (`data/databento_cache`). Population script: `scripts/populate_historical_cache.py` (ALL_SYMBOLS per-month, $0 cost, resumable, manifest-tracked, `--update` mode for monthly maintenance).

- **BacktestEngine** (`backtest/engine.py`): Assembles production components (strategies, Risk Manager, Order Manager, SimulatedBroker, IndicatorEngine) wired through SynchronousEventBus. Mirrors ReplayHarness component assembly pattern. Features:
  - **Bar-level fill model** with worst-case-for-longs exit priority: stop > target > time_stop > EOD (same priority as VectorBT sweeps per `.claude/rules/backtesting.md`). Exit priority logic extracted to shared `TheoreticalFillModel` (`core/fill_model.py`) in Sprint 27.7 — BacktestEngine calls `evaluate_bar_exit()`.
  - **Exit Management (Sprint 28.5):** `_BacktestPosition` dataclass with trail/escalation state fields. Per-bar processing follows AMD-7 ordering: escalation check → trail watermark update + trail stop check → fill model. Exit config loaded per strategy via `_get_exit_config()` with deep merge. Trail activates after T1 fill. Escalation progresses through phases based on elapsed seconds.
  - **Multi-day orchestration**: Iterates trading days, resets daily state, runs scanner simulation per day
  - **Scanner simulation**: Computes gap from prev_close → day_open, applies scanner filters (same approach as VectorBT backtests)
  - **Strategy factory**: Creates strategy instances from `StrategyType` enum with config overrides
  - **CLI entry point**: `python -m argus.backtest.engine --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31 --strategy orb_breakout`
  - **Results persistence**: Per-run SQLite database in `data/backtest_runs/`

- **Walk-forward integration**: `walk_forward.py` gains `oos_engine` parameter (`"replay"` default, `"backtest_engine"` selects BacktestEngine for OOS evaluation). Enables walk-forward validation using production-code execution at speed.
  - **Risk overrides** (Sprint 21.6, DEC-359): `risk_overrides` dict on `BacktestEngineConfig` with permissive defaults for single-strategy backtesting (min_position_risk_dollars: 1.0, cash_reserve_pct: 0.05, max_single_stock_pct: 0.50). Applied via `setattr` in `_load_risk_config()`. Empty dict opts back into production constraints. Production paths unaffected.
  - **VectorBT dual file naming** (Sprint 21.6): All 5 `vectorbt_*.py` files support both `{YYYY-MM}.parquet` (HistoricalDataFeed format) and `{SYMBOL}_{YYYY-MM}.parquet` (legacy format) via dual-glob fallback.
  - **Symbol auto-detection** (Sprint 21.6): `_load_data()` auto-detects available symbols from cache directory when `symbols=None`.
  - **Revalidation script** (Sprint 21.6): `scripts/revalidate_strategy.py` — CLI running BacktestEngine + walk-forward per strategy, producing JSON results in `data/backtest_runs/validation/`.
  - **Regime tagging** (Sprint 27.5): `to_multi_objective_result()` async method loads SPY 1-min Parquet, resamples to daily OHLCV, instantiates `RegimeClassifier` per day, partitions trades by exit_date regime, produces `MultiObjectiveResult` with populated `regime_results`. Falls back to single `RANGE_BOUND` regime when SPY not in Parquet cache.
  - **Slippage model integration** (Sprint 27.5): Optional `slippage_model_path: str | None` on `BacktestEngineConfig` loads calibrated slippage model, populating `execution_quality_adjustment` on the output `MultiObjectiveResult`.

**Relationship between backtesting layers:**

| Layer | Speed | Fidelity | Use Case |
|-------|-------|----------|----------|
| VectorBT | Fastest (~30s for full sweep) | Approximate (vectorized logic) | Parameter exploration, sensitivity analysis |
| BacktestEngine | Fast (≥5x Replay Harness) | High (real strategy code, bar-level fills) | Production-code validation, walk-forward OOS |
| Replay Harness | Slowest (tick-level replay) | Highest (synthetic ticks from OHLC) | Final validation, tick-level fidelity checks |

**Change C — Update directory structure in section 5.6 (replace the backtest file list):**

Replace:
```
├── vectorbt_orb.py       # VectorBT parameter sweeps
```
With:
```
├── vectorbt_orb.py                # VectorBT ORB parameter sweeps
├── vectorbt_orb_scalp.py          # VectorBT ORB Scalp sweeps
├── vectorbt_vwap_reclaim.py       # VectorBT VWAP Reclaim sweeps (DEC-144)
├── vectorbt_afternoon_momentum.py # VectorBT Afternoon Momentum sweeps (DEC-162)
├── vectorbt_red_to_green.py       # VectorBT R2G sweeps (Sprint 26)
├── vectorbt_pattern.py            # Generic PatternModule backtester (Sprint 26)

### 5.2 Replay Harness (`backtest/replay_harness.py`)

The highest-fidelity backtest. Feeds historical data through the production system using real components with injected time.

**Architecture:**
FixedClock (advancing with each bar)
→ provides simulated time to all components
ReplayDataService (from Sprint 3)
→ reads historical data from Parquet files
→ publishes CandleEvents on the Event Bus
OrbBreakoutStrategy (production code, unmodified)
→ receives CandleEvents, generates SignalEvents
RiskManager (production code)
→ evaluates signals with SimulatedBroker
OrderManager (production code)
→ manages positions using synthetic TickEvents from bar OHLC
→ handles T1/T2 exits, stop-to-breakeven, time stops, EOD flatten
SimulatedBroker (from Sprint 2)
→ fills orders at historical prices with configurable slippage
TradeLogger (production code)
→ writes to a separate backtest SQLite database
ReplayHarness (orchestration)
→ initializes all components with FixedClock + SimulatedBroker
→ runs one trading day at a time: reset state, feed bars, EOD flatten
→ produces a complete trade log in the same schema as production

**Key design decisions:**
- Uses FixedClock injection (DEF-001) so all time-dependent logic sees simulated time
- OrderManager receives synthetic TickEvents derived from bar OHLC data
- Each backtest run writes to its own SQLite database (`data/backtest_runs/run_YYYYMMDD_HHMMSS.db`)
- Same database schema as production — all existing SQL queries work on backtest output
- Config overrides allow running the same harness with different parameters without modifying YAML files

### 5.3 Walk-Forward Analysis (`backtest/walk_forward.py`)

Mandatory overfitting defense (DEC-047). Splits historical data into rolling windows:

1. **In-sample:** Optimize parameters using VectorBT (default: 4 months)
2. **Out-of-sample:** Test those parameters using Replay Harness (default: 2 months)
3. **Roll forward:** Slide the window and repeat (default: 2-month steps)

Key metric: **Walk-Forward Efficiency** = OOS return / IS return. Values > 0.5 indicate robust parameters. Values < 0.3 indicate overfitting.

### 5.4 Performance Metrics (`backtest/metrics.py`)

Standard backtest metrics computed from trade logs:
- Win rate, loss rate, profit factor
- Average R-multiple, max consecutive wins/losses
- Maximum drawdown (peak-to-trough equity decline)
- Sharpe ratio (annualized from daily returns)
- Recovery factor (net profit / max drawdown)
- Performance by time-of-day and day-of-week

### 5.5 Report Generator (`backtest/report_generator.py`)

Generates self-contained HTML reports with:
- Equity curve, monthly P&L table, R-multiple distribution
- Parameter sensitivity heatmaps
- Walk-forward in-sample vs out-of-sample comparison
- Best/worst trade tables for manual spot-checking

### 5.6 Directory Structure
argus/backtest/
├── init.py
├── config.py             # BacktestConfig Pydantic model (Sprint 27)
├── data_fetcher.py       # Historical data download (Databento primary, Alpaca legacy) → Parquet cache
├── engine.py             # BacktestEngine — production-code backtesting (Sprint 27)
├── historical_data_feed.py  # Databento OHLCV-1m download + Parquet cache (Sprint 27)
├── replay_harness.py     # Production code replay engine
├── vectorbt_orb.py       # VectorBT parameter sweeps
├── metrics.py            # Performance metric calculations
├── walk_forward.py       # Walk-forward analysis framework
└── report_generator.py   # HTML report generation
argus/core/
├── exit_math.py          # Pure functions: trailing stop, escalation, time stop validation (Sprint 28.5)
├── sync_event_bus.py     # SynchronousEventBus for deterministic backtesting (Sprint 27)
data/
├── historical/           # Downloaded Parquet files (gitignored)
│   ├── manifest.json     # Download tracking
│   └── 1m/               # 1-minute bars per symbol
└── backtest_runs/        # Output databases per run (gitignored)
docs/backtesting/
├── DATA_INVENTORY.md
├── BACKTEST_RUN_LOG.md
└── PARAMETER_VALIDATION_REPORT.md
docs/sprints/sprint-{N}/
└── run-log/                       # Autonomous runner output (see run-log-spec)
scripts/
├── sprint-runner.py              # Autonomous sprint orchestrator
└── launch_monitor.sh             # Unattended launch + monitoring (5 checkpoints, ntfy.sh notifications, Sprint 25.7)
config/
└── runner.yaml                   # Runner configuration

---

## 6. Command Center (Tier 2)

### 6.1 Technology Stack
- **Frontend:** React 18+ with TypeScript (single codebase for all surfaces — DEC-080)
- **Styling:** Tailwind CSS (responsive/mobile-first)
- **State Management:** Zustand or Jotai (lightweight, performant)
- **Charts:** Lightweight Charts (TradingView's open-source library) for price charts; Recharts for performance metrics
- **Data Fetching:** TanStack Query for REST; native WebSocket for real-time
- **Desktop:** Tauri v2 (Rust shell wrapping the React frontend — system tray, native notifications, auto-launch)
- **Mobile:** PWA (Progressive Web App) — home-screen install on iOS/iPad/Android, push notifications, no App Store required (DEC-080)
- **Backend:** FastAPI (REST + WebSocket) — serves both the React frontend and the Tauri app

### 6.2 Dashboard Pages

**Overview Dashboard:** Account equity, daily P&L, active strategies at a glance, open positions, recent trades, current market regime, system health indicator, approval queue badge, VixRegimeCard widget (VIX close, VRP tier badge, vol regime phase label, momentum direction arrow — hidden when `vix_regime.enabled: false` or data unavailable, TanStack Query 60s polling, Sprint 27.9)

**Strategy Lab:** All strategies in the Incubator Pipeline, filterable by stage. Drill into any strategy for full performance metrics, parameter configuration, and history.

**Live Monitor:** Real-time view of all open positions with streaming P&L. Per-strategy view. Price charts with entry/stop/target levels drawn. Time-in-trade counters.

**Performance:** Historical performance analytics — equity curve, drawdown chart, per-strategy breakdown, win rate over time, R-multiple distribution, performance by day of week / time of day / regime.

**Risk Dashboard:** Current risk utilization at all three levels. Visual indicators of how close each limit is to being hit. Heat map of sector exposure.

**Controls:** Autonomy settings per action type. Strategy pause/resume. Manual position close. Emergency buttons (shutdown, flatten, pause).

**Reports:** Generate and view daily/weekly/monthly reports. Claude-narrated analysis. Export to PDF.

**Accounting:** P&L statements, tax liability estimates, wash sale tracking, cost basis reports. Export for CPA.

**Learning Journal:** Searchable, taggable knowledge base. Linked to trades and strategies. Entries from both user and Claude.

**Settings:** Notification preferences, API key management, appearance, autonomy configuration, broker connection status, bank connection status.

**Claude Chat:** Conversational interface with Claude. Context-aware (Claude can see current system state). Action proposals appear inline with approve/reject buttons.

### 6.3 Mobile Access (DEC-080)

The Command Center is a Progressive Web App (PWA) installable on iOS, iPad, and Android devices.

**PWA Configuration:**
- `manifest.json` with app name, icons (multiple sizes), theme color, display mode (`standalone`)
- Service worker for offline shell caching (not offline data — trading data requires live connection)
- Apple-specific meta tags for iOS home screen appearance (`apple-mobile-web-app-capable`, status bar style)

**Responsive Design:**
- Mobile-first CSS via Tailwind breakpoints (`sm:`, `md:`, `lg:`)
- Dashboard cards stack vertically on mobile, grid on desktop
- Charts resize responsively (Recharts handles this natively)
- Touch-friendly controls (larger tap targets, swipe gestures where appropriate)
- Critical actions (emergency shutdown, position close) accessible within 2 taps from any screen

**Limitations vs Desktop:**
- No background execution (PWA suspends when not in foreground)
- Push notifications via web push API (requires HTTPS, service worker)
- No system tray — relies on push notifications for alerts
- Smaller screen real estate — some advanced views (multi-chart layouts, heatmaps) may be desktop-only

---

## 7. AI Layer (Tier 3)

*Implemented in Sprint 22 (March 2026). See DEC-264 through DEC-274.*

### 7.1 Architecture Overview

The AI Layer provides Claude-powered analysis, advisory, and action proposals through a structured approval workflow. Key design principles:

- **Graceful degradation:** All AI features are disabled when `ANTHROPIC_API_KEY` is unset. Trading engine operates identically.
- **tool_use over parsing:** Claude's native `tool_use` API for structured outputs (DEC-271), not JSON-in-text parsing.
- **Closed action enumeration:** 5 defined tools, each with validation and executor (DEC-272).
- **DB persistence:** All conversations, messages, proposals, and usage tracked in SQLite.
- **Safety guardrails:** System prompt enforces advisory-only role; never recommends specific entries/exits.

### 7.2 Module Structure (`ai/`)

```
argus/ai/
├── client.py        # ClaudeClient — API wrapper with rate limiting, tool_use
├── config.py        # AIConfig — Pydantic model, token budgets, TTLs
├── prompts.py       # PromptManager — system prompt template, guardrails
├── context.py       # SystemContextBuilder — per-page context assembly
├── conversations.py # ConversationManager — SQLite persistence, calendar-date keying
├── usage.py         # UsageTracker — per-call cost tracking
├── actions.py       # ActionManager — proposal lifecycle, TTL, 4-condition re-check
├── executors.py     # 5 ActionExecutors + ExecutorRegistry
├── summary.py       # DailySummaryGenerator
├── cache.py         # ResponseCache — TTL-based caching
└── tools.py         # 5 tool_use definitions with JSON schemas
```

### 7.3 Claude Client (`ai/client.py`)

```python
class ClaudeClient:
    async def stream_response(
        self,
        messages: list[dict],
        system_prompt: str,
        tools: list[dict] | None = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream response from Claude API with tool_use support.
        Yields: TextDelta, ToolUse, ToolResult, MessageComplete events.
        Rate limited per AIConfig.rate_limit_requests_per_minute.
        """
```

When Claude emits a `tool_use` content block, the client yields a `ToolUse` event. The caller creates an `ActionProposal`, stores it in DB, returns a `tool_result` to Claude, and Claude continues its response.

### 7.4 System Context Builder (`ai/context.py`)

Assembles trading context for each Claude API call. Per-page hooks provide contextual data.

```python
class SystemContextBuilder:
    def build_system_prompt(
        self,
        page_context: dict | None = None,
        include_strategies: bool = True
    ) -> str:
        """
        Builds system prompt with:
        - ARGUS description and behavioral guardrails
        - Active strategy summaries (allocations, states)
        - Current positions and today's P&L
        - Page-specific context (selected trade, viewed strategy, etc.)
        - Mandatory tool_use directive

        Token budgets (DEC-273):
        - System prompt: ≤1,500 tokens
        - Page context: ≤2,000 tokens
        - History: ≤8,000 tokens
        - Response: ≤4,096 tokens
        """
```

### 7.5 Conversation Manager (`ai/conversations.py`)

Manages persistent chat history with calendar-date keying (DEC-266).

**Tables:**
- `ai_conversations` — id, date, tag, title, created_at
- `ai_messages` — id, conversation_id, role, content, tool_use_data, timestamp
- `ai_usage` — id, conversation_id, timestamp, input_tokens, output_tokens, model, estimated_cost_usd

**Tags:** `pre-market`, `session`, `research`, `debrief`, `general` (default). Auto-assigned by page context.

### 7.6 Action Manager (`ai/actions.py`)

Manages the proposal lifecycle with DB persistence and 4-condition pre-execution re-check.

```python
class ActionManager:
    async def create_proposal(self, tool_name: str, tool_input: dict) -> ActionProposal:
        """Create pending proposal with 5-min TTL (DEC-267)."""

    async def approve_proposal(self, proposal_id: str) -> dict:
        """
        Re-check 4 conditions before execution:
        1. Target entity (strategy, risk param) still exists
        2. Regime hasn't changed to unfavorable
        3. Equity within ±5% of proposal time
        4. No circuit breaker active
        """

    async def reject_proposal(self, proposal_id: str, reason: str) -> None:
        """Mark proposal rejected with reason."""
```

**Proposal States:** `pending` → `approved` → `executing` → `executed` | `rejected` | `expired`

### 7.7 Action Executors (`ai/executors.py`)

Five closed-enumeration tools (DEC-272):

| Tool | Requires Approval | Executor |
|------|-------------------|----------|
| `propose_allocation_change` | Yes | Updates strategy allocation in config |
| `propose_risk_param_change` | Yes | Updates risk parameter in config |
| `propose_strategy_suspend` | Yes | Suspends strategy via Orchestrator |
| `propose_strategy_resume` | Yes | Resumes strategy via Orchestrator |
| `generate_report` | No | Immediately generates analytical report |

Each executor validates inputs against schema bounds (e.g., allocation 0–100%, risk params within defined ranges).

### 7.8 WebSocket Streaming (`api/websocket/ai_chat.py`)

`WS /ws/v1/ai/chat` — bidirectional streaming with JWT auth (DEC-265).

**Client → Server:**
```json
{"type": "auth", "token": "<JWT>"}
{"type": "message", "content": "...", "conversation_id": "..."}
{"type": "cancel"}
```

**Server → Client:**
```json
{"type": "token", "content": "..."}
{"type": "tool_use", "tool_name": "...", "tool_input": {...}, "proposal_id": "..."}
{"type": "stream_end", "message": {...}}
{"type": "error", "message": "..."}
```

### 7.9 REST Endpoints

_Auto-regenerated (DEF-168). All endpoints live under `/api/v1/ai` and
require JWT auth. `POST /ai/chat` is the non-streaming fallback; live
streaming uses the `/ws/v1/ai/chat` WebSocket in §7.8._

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/ai/actions/pending` | Get all pending action proposals. |
| `POST   /api/v1/ai/actions/{proposal_id}/approve` | Approve a pending action proposal. |
| `POST   /api/v1/ai/actions/{proposal_id}/reject` | Reject a pending action proposal. |
| `POST   /api/v1/ai/chat` | Non-streaming chat endpoint. |
| `GET    /api/v1/ai/context/{page}` | Debug endpoint: inspect the context payload for a given page. |
| `GET    /api/v1/ai/conversations` | List conversations with optional filters. |
| `GET    /api/v1/ai/conversations/{conversation_id}` | Get a conversation with its messages. |
| `GET    /api/v1/ai/insight` | Get a brief AI-generated insight for the Dashboard. |
| `GET    /api/v1/ai/status` | Get AI service status and usage summary. |
| `GET    /api/v1/ai/usage` | Get detailed usage statistics. |

### 7.10 Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `CopilotPanel` | `features/copilot/` | Slide-out chat panel, Cmd/K toggle |
| `ChatMessage` | `features/copilot/` | Rendered message with markdown |
| `StreamingMessage` | `features/copilot/` | Token-by-token streaming display |
| `ActionCard` | `features/copilot/` | Proposal display, approve/reject UI |
| `AIInsightCard` | `features/dashboard/` | Dashboard insight with auto-refresh |
| `ConversationBrowser` | `features/debrief/` | Learning Journal integration |

**Markdown rendering:** `react-markdown` + `remark-gfm` + `rehype-sanitize` (DEC-270).

**Context hooks:** Each of 8 pages provides context via `useCopilotContext` (DEC-268).

---

## 8. Security Architecture

### 8.1 Secrets Management
- All API keys, tokens, and credentials stored in encrypted file (age-encrypted or SOPS)
- Loaded into environment variables at runtime
- Never committed to git (`.env` in `.gitignore`)
- Production: consider AWS Secrets Manager or HashiCorp Vault

### 8.2 Authentication
- Dashboard protected by single-factor JWT authentication (bcrypt-hashed password + `HTTPBearer`, DEC-102 / DEC-351). 2FA is not implemented.
- API server validates JWT on every request
- Mobile access uses same authentication
- Session timeout configurable (default: 24h, re-auth required)

### 8.3 Network Security
- All connections over HTTPS/WSS
- VPS firewall: only allow inbound on HTTPS port (443) and SSH
- Consider VPN (WireGuard) for additional layer between devices and VPS
- Broker API connections are already encrypted (TLS)

### 8.4 Audit Trail
- Every action is logged immutably: trades, config changes, approvals, Claude interactions
- Logs include timestamp, actor (user/system/claude/orchestrator), action, details
- Audit log is append-only (no deletions)
- Backed up daily with database

---

## 9. Deployment Architecture

### Development
- Local machine (macOS/Linux/Windows)
- Python virtual environment (`venv` or `conda`)
- SQLite database in project directory
- Alpaca paper trading API
- Hot reload for UI development

### Production
- **Trading Engine:** AWS EC2 instance in `us-east-1` (Virginia)
  - Instance type: t3.medium (2 vCPU, 4GB RAM) — sufficient for V1
  - Ubuntu 24 LTS
  - Managed via `systemd` (auto-restart on crash)
  - Heartbeat monitoring via external service (UptimeRobot or custom)
- **Command Center:** Served from the same VPS (Nginx reverse proxy)
- **Desktop App:** Tauri binary installed on user's machine, connects to VPS API
- **Database:** SQLite on VPS (backed up daily to S3)
- **Monitoring:** External health check pings every 60 seconds

### CI/CD
- Git repository (GitHub or similar)
- Automated tests run on push
- Deployment via SSH + systemd restart (simple for single-user system)
- Database migrations tracked in code

---

## 10. Deferred Components (post-revenue or never-built)

- **NotificationService** (scoped but never built) — `argus/notifications/` contains `__init__.py` only. Alerts today flow through `HealthMonitor` webhook fields and logging. If reinstated, the abstraction lives here. See `.claude/rules/architecture.md` § Abstraction Layers.
- **OrderFlowAnalyzer** — post-revenue (DEC-238). Requires L2/L3 data (Databento Plus, $1,399/mo).
- **§11 "Shadow System" as a parallel process** — superseded by `StrategyMode.SHADOW` + `CounterfactualTracker` (Sprint 27.7). Individual strategies now run in shadow mode within the single ARGUS process; the separate-process design was never built.

---

## 12. Configuration Files

All tunable parameters live in YAML files under `config/` — read the directory directly for the current set. Major standalone overlays are registered in `_STANDALONE_SYSTEM_OVERLAYS` in `argus/core/config.py` (DEC-384): `quality_engine.yaml`, `overflow.yaml`. Per-strategy configs live under `config/strategies/`; per-pattern universe filters under `config/universe_filters/`. See `.claude/rules/architecture.md` § Config-Gating for the overlay pattern.

---

## 13. Observatory Subsystem (Sprint 25)

The Observatory is an immersive pipeline visualization page (Command Center page 8) providing real-time and post-session visibility into the entire ARGUS trading pipeline — from universe filtering through strategy evaluation to trade execution.

### 13.1 ObservatoryService (`analytics/observatory_service.py`)

Read-only analytics service querying EvaluationEventStore and UniverseManager. Does not write data or affect the trading pipeline.

**Methods:**
- `get_pipeline_stages()` — Aggregated counts per pipeline tier (universe → viable → monitored → evaluated → quality_scored → traded)
- `get_closest_misses()` — Symbols closest to triggering a strategy signal (most conditions passed)
- `get_symbol_journey(symbol)` — Full evaluation history for a single symbol across all strategies
- `get_session_summary()` — High-level session metrics (evaluation count, signal count, trade count, unique symbols)

**Data access:** Uses `EvaluationEventStore.execute_query()` public method (added Sprint 25 S10) for SQL queries over the evaluation telemetry SQLite database. The `is_connected` property gates queries when the store is not initialized.

### 13.2 Observatory WebSocket (`/ws/v1/observatory`)

Push-based pipeline updates, independent from the AI chat WebSocket (`/ws/v1/ai/chat`).

**Message types:**
- Tier transition events (symbol moves between pipeline stages)
- Evaluation summaries (periodic aggregated counts)

**Authentication:** JWT token required on connection (same as other WS endpoints).

**Config-gated:** Only active when `observatory.enabled: true` in system config.

### 13.3 Observatory Frontend

**Page structure:** Full-bleed immersive layout with 4 switchable views, persistent detail panel, and session vitals bar.

**Views (keyboard: f/m/r/t):**
1. **Funnel (Three.js 3D):** Translucent cone with tier discs, symbol particles via InstancedMesh (up to 5,000), CSS2DRenderer for labels with LOD behavior, OrbitControls for camera manipulation.
2. **Radar (Three.js 3D):** Bottom-up camera perspective of the same scene — concentric rings with trigger point at center. Thin wrapper passing `mode="radar"` to FunnelView. Smooth camera animation transition.
3. **Matrix (heatmap):** Condition heatmap sorted by proximity to trigger. Green/red/gray cells for pass/fail/unknown. Virtual scrolling for large symbol lists. Tab key navigation.
4. **Timeline (SVG):** Strategy lane timeline (9:30 AM–4:00 PM ET) with event marks at 4 severity levels (pass/fail/skip/trigger).

**Shared-scene pattern:** Funnel and Radar share a single Three.js scene with camera presets. This avoids duplicate WebGL contexts and enables smooth camera transitions between views.

**Three.js integration:**
- Three.js r128, loaded via React.lazy code-splitting (separate chunk, does not impact initial bundle)
- InstancedMesh for symbol particles — O(1) draw calls regardless of symbol count
- CSS2DRenderer for HTML labels overlaid on the 3D scene
- Monotonic instance slot allocation (no reclamation within session)

**Detail panel (right slide-out):**
- Per-symbol condition grid (which conditions passed/failed for each strategy)
- Quality score and catalyst summary
- Live candlestick chart (Lightweight Charts)
- Chronological strategy evaluation history
- Persists across view switches

**Session vitals bar:**
- Connection status, evaluation counts, closest miss, top blocking condition
- Live data via WS + REST polling

**Debrief mode:**
- Date picker switches all views to historical data
- 7-day retention (matches EvaluationEventStore retention)

**Keyboard navigation:**
- `f`/`m`/`r`/`t` — switch views (Funnel/Matrix/Radar/Timeline)
- `[`/`]` — navigate tiers
- `Tab` — cycle through symbols
- `Shift+R` — reset camera
- `Shift+F` — fit camera to scene

### 13.4 ObservatoryConfig (`analytics/config.py`)

Pydantic BaseModel wired into SystemConfig. Config-gated feature with `observatory.enabled` (default: true). YAML section: `observatory:` in system.yaml / system_live.yaml.

---

## 13.5 The Arena (Sprint 32.75)

Real-time multi-position visualization — 10th Command Center page. Shows all open managed positions simultaneously, each in its own card with live price chart and P&L data.

### 13.5.1 Arena REST API (`api/routes/arena.py`)

_Verified against `app.openapi()` on 2026-04-23 (DEF-168, IMPROMPTU-08).
Both endpoints are JWT-protected._

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/arena/candles/{symbol}` | Get recent 1-minute candles for a symbol. |
| `GET    /api/v1/arena/positions` | Get all open managed positions for the Arena page. |

**Implementation notes:**
- `GET /api/v1/arena/positions` sources from `OrderManager.get_managed_positions()`. No pagination — the cap is `overflow.broker_capacity` (50 as of Sprint 32.9, aligned with `max_concurrent_positions`). Payload per position: entry_price, current_price, unrealized_pnl, r_multiple, trail_stop_price (if active), strategy_id, symbol, share_count.
- `GET /api/v1/arena/candles/{symbol}` returns OHLCV bars from `IntradayCandleStore` (up to 720 bars post-Sprint 32.8 — full trading day including pre-market from 4:00 AM ET). Used to seed `MiniChart` on card mount.

### 13.5.2 Arena WebSocket (`/ws/v1/arena`)

**Channel:** `ws://host/ws/v1/arena` (`api/websocket/arena_ws.py`)

**Authentication:** JWT token required via `?token={jwt}` query parameter.

**Message types (server → client):**

| Type | Payload | Frequency |
|------|---------|-----------|
| `arena_tick` | symbol, price, unrealized_pnl, r_multiple, trail_stop_price | Per tick per open position (throttled 1/sec/symbol) |
| `arena_candle` | symbol, OHLCV, timestamp, is_forming | Per completed + forming bar per symbol |
| `arena_position_opened` | Full position snapshot | On new position open |
| `arena_position_closed` | symbol, exit_price, exit_reason, final_pnl | On position close |
| `arena_stats` | open_count, total_unrealized_pnl, win_count, loss_count | On position open/close |

**Single active position per symbol:** V1 simplification — `arena_tick` trail_stop from first symbol match; `arena_position_closed` discards on first symbol close. Multi-position same-symbol overlay deferred (DEF-138 backend protocol change needed, S7 F1).

### 13.5.3 Arena Frontend (`ui/src/features/arena/`)

**Components:**
- `ArenaPage.tsx` — Root page. Responsive grid (1/2/3 columns based on viewport). Framer Motion AnimatePresence for card entry/exit.
- `ArenaCard.tsx` — Per-position card. Contains MiniChart + P&L badge + R-multiple + strategy badge. Priority sizing: cards with `pattern_score > 0.7` span 2 grid columns. Flash animation on position open. Disconnection overlay renders over card on WS loss.
- `MiniChart.tsx` — Lightweight Charts mini instance seeded from `GET /arena/candles/{symbol}` on mount, updated via `arena_candle` WS messages. Live candle formation (partial bar updated in place).
- `ArenaControls.tsx` — Filter bar: strategy filter (normalizeStrategyId for case-insensitive match), sort by age/pnl/r-multiple. Persists to session state via Zustand.
- `ArenaStatsBar.tsx` — Aggregate bar: open positions count, total unrealized P&L, win/loss counts, net R. NetR colored green/red/neutral; neutral when netR = 0.

**Hooks:**
- `useArenaWebSocket.ts` — WS connection management, message dispatch, reconnect backoff. rAF batching for 60fps rendering.
- `useArenaData.ts` — REST polling for initial positions load + refresh on reconnect.

**Keyboard shortcut:** `4` (global nav, same as all Command Center pages).

---

## 14. Evaluation Framework (Sprint 27.5)

Universal evaluation infrastructure that becomes the shared currency for all downstream optimization and experiment sprints (28, 32.5, 33, 34, 38, 40, 41). Pure backend — no frontend, no API endpoints, no new YAML config.

### 14.1 MultiObjectiveResult (`analytics/evaluation.py`)

Core evaluation dataclass capturing:
- **Primary metrics:** Sharpe ratio, max drawdown %, profit factor, win rate, trade count, expectancy
- **Per-regime breakdown:** `regime_results: dict[str, RegimeMetrics]` — string-keyed for forward-compatibility with Sprint 27.6 `RegimeVector` (replaces enum-keyed approach)
- **RegimeMetrics** (frozen dataclass): per-regime Sharpe, max drawdown %, profit factor, win rate, expectancy, trade count
- **ConfidenceTier** enum: HIGH (≥50 trades + 3 regimes at ≥15 trades), MODERATE (≥30 trades + 2 regimes at ≥10, or ≥50 with insufficient regime coverage), LOW (10–29 trades), ENSEMBLE_ONLY (<10 trades)
- **ComparisonVerdict** enum: DOMINATES, DOMINATED, INCOMPARABLE, INSUFFICIENT_DATA
- Walk-forward efficiency, optional `execution_quality_adjustment`, placeholder p-value/CI fields
- `parameter_hash()`: deterministic SHA-256 of sorted JSON config
- `from_backtest_result()` factory: bridges `BacktestResult` → `MultiObjectiveResult`
- JSON serialization roundtrip (`to_dict()`/`from_dict()`) with infinity and None handling

### 14.2 Comparison Module API (`analytics/comparison.py`)

_This section documents a **Python module**, not an HTTP API — `comparison.py`
is not route-exposed. Regeneration from `app.openapi()` is not applicable
(DEF-168, IMPROMPTU-08 ambiguous-section decision). Function signatures
introspected via `inspect.signature()`._

Pairwise and set-level comparison using Pareto dominance:
- **5 comparison metrics:** Sharpe↑, max_drawdown_pct↑, profit_factor↑, win_rate↑, expectancy↑
- `compare(a: MultiObjectiveResult, b: MultiObjectiveResult) -> ComparisonVerdict` — Pareto dominance (all metrics must be ≥, at least one >)
- `pareto_frontier(results: list[MultiObjectiveResult]) -> list[MultiObjectiveResult]` — O(n²) pairwise filtering, excludes LOW/ENSEMBLE_ONLY confidence
- `soft_dominance(a, b, tolerance: dict[str, float] | None = None) -> bool` — configurable per-metric tolerance bands
- `is_regime_robust(result, min_regimes: int = 3) -> bool` — positive expectancy across the minimum regime count
- `format_comparison_report(a, b) -> str` — human-readable diff of two MultiObjectiveResults
- NaN → INSUFFICIENT_DATA, `float('inf')` handled natively

### 14.3 Ensemble Evaluation (`analytics/ensemble_evaluation.py`)

First-class evaluation for strategy cohorts:
- **EnsembleResult:** aggregate portfolio-level `MultiObjectiveResult` + `diversification_ratio` + `tail_correlation` + `capital_utilization` + `turnover_rate` + per-strategy `MarginalContribution`
- **MarginalContribution:** leave-one-out recomputation — measures each strategy's impact on ensemble Sharpe, drawdown, and profit factor
- `build_ensemble_result()`: constructs from list of strategy `MultiObjectiveResult`s
- `evaluate_cohort_addition()`: tests whether adding a strategy improves ensemble, returns `improvement_verdict`
- `identify_deadweight()`: finds strategies with negative marginal contribution
- **Metric-level approximation** documented (aggregate metrics computed from per-strategy metrics, not trade-level). Trade-level upgrade deferred to Sprint 32.5.

### 14.4 Slippage Model (`analytics/slippage_model.py`)

Calibration from live execution data:
- **StrategySlippageModel** dataclass: per-strategy slippage calibration
- `calibrate_slippage_model()` async: queries `execution_records` table filtered by strategy_id
- **Time-of-day buckets** (ET): pre_10am, 10am_2pm, post_2pm — captures intraday liquidity patterns
- **Size adjustment:** linear regression slope of slippage vs order size
- **Confidence tiers:** HIGH (≥50 records), MODERATE (≥20), LOW (≥5), INSUFFICIENT (<5)
- Atomic JSON persistence (`save_slippage_model()` / `load_slippage_model()`) via tempfile + rename
- Pure Python math (no numpy dependency)

### 14.5 Directory Structure

```
analytics/
├── evaluation.py          # MultiObjectiveResult, RegimeMetrics, ConfidenceTier (Sprint 27.5)
├── comparison.py          # Pareto comparison API (Sprint 27.5)
├── ensemble_evaluation.py # EnsembleResult, cohort evaluation (Sprint 27.5)
├── slippage_model.py      # Slippage calibration from execution records (Sprint 27.5)
```

---

## 15. Experiment Pipeline (Sprints 32 + 32.5)

Complete variant lifecycle infrastructure for autonomous parameter optimization. Config-gated via `experiments.enabled` (default: false). All existing strategies are unaffected when disabled.

### 15.1 Pattern Factory (`strategies/patterns/factory.py`)

Generic pattern instantiation with PatternParam introspection:
- **`build_pattern_from_config(pattern_name, config_dict)`** — maps config dict keys to PatternParam-declared detection params. No hardcoded switch statements. Unknown keys are silently ignored; missing required params fall back to PatternParam defaults.
- **`get_pattern_class(pattern_name)`** — returns the pattern class with lazy import + module-level caching. Fails fast with a clear error for unknown patterns.
- **`compute_parameter_fingerprint(pattern_name, config_dict)`** — SHA-256 of canonical JSON (sorted keys, `separators=(',', ':')`) of detection params only. Returns first 16 hex characters. Non-detection fields (strategy_id, name, enabled, operating_window) are excluded so variants with the same parameters get the same fingerprint regardless of identity.
- **`extract_detection_params(pattern_name)`** — introspects `get_default_params()` to return the set of valid detection param names for a pattern. Used by factory and spawner to filter config dicts.

All 7 PatternModule patterns in `main.py` now construct via `build_pattern_from_config()`. PatternBacktester `_create_pattern_by_name()` also delegates to factory (DEF-121 resolved).

### 15.2 Experiment Models (`intelligence/experiments/models.py`)

Core dataclasses for the experiment lifecycle:
- **`ExperimentRecord`** — frozen dataclass: experiment_id (ULID), pattern_name, fingerprint, config_dict, status (ExperimentStatus enum), backtest_result (MultiObjectiveResult | None), shadow_days, shadow_trades, promotion_events.
- **`VariantDefinition`** — frozen dataclass: strategy_id, pattern_name, fingerprint, config_dict, registered_at. Identifies a specific parameter combination instantiated as a shadow strategy.
- **`PromotionEvent`** — frozen dataclass: event_id (ULID), strategy_id, event_type (PROMOTED/DEMOTED/KILLED), reason, timestamp, metrics_snapshot.
- **`ExperimentStatus`** enum: PENDING → BACKTESTING → SHADOW → LIVE → DEMOTED → KILLED.

### 15.3 ExperimentStore (`intelligence/experiments/store.py`)

SQLite persistence following the DEC-345 pattern:
- Database: `data/experiments.db`
- WAL mode, fire-and-forget writes via asyncio tasks
- 3 tables: `experiment_records`, `variant_definitions`, `promotion_events`
- 90-day retention enforcement at startup and daily
- Methods: `save_experiment()`, `update_experiment_status()`, `get_experiment()`, `list_experiments()`, `save_variant()`, `get_variant_by_fingerprint()`, `save_promotion_event()`, `get_promotion_history()`

### 15.4 VariantSpawner (`intelligence/experiments/spawner.py`)

Shadow strategy instantiation from `config/experiments.yaml`:
- Reads `variants` list from experiments YAML config
- For each variant: computes fingerprint, checks ExperimentStore for duplicates, builds PatternBasedStrategy via factory with `mode: shadow`
- Skips duplicates by fingerprint (idempotent on restart)
- Registers each new variant with Orchestrator via `register_strategy()`
- Shadow variants are identical to live strategies except: signals bypass quality pipeline and risk manager, routed directly to CounterfactualTracker
- Max variants per pattern enforced by `max_variants_per_pattern` config field

### 15.5 ExperimentRunner (`intelligence/experiments/runner.py`)

Backtest pre-filter for candidate parameter combinations:
- Grid generation from PatternParam metadata (`min_value`, `max_value`, `step`) × optional `exit_sweep_params` cross-product (Sprint 32.5)
- For each grid point: runs BacktestEngine, evaluates MultiObjectiveResult, stores result in ExperimentStore
- Supports **all 7 PatternModule patterns** via `_PATTERN_TO_STRATEGY_TYPE` mapping (DEF-134 resolved Sprint 32.5)
- Config-gated pre-filter thresholds: `min_sharpe`, `min_trade_count`, `min_win_rate`
- CLI: `scripts/run_experiment.py --pattern bull_flag --dry-run` for standalone sweep execution

### 15.6 PromotionEvaluator (`intelligence/experiments/promotion.py`)

Autonomous promote/demote based on accumulated shadow evidence:
- Wired to `SessionEndEvent` (fires after EOD flatten)
- For each shadow variant: queries CounterfactualTracker results, computes MultiObjectiveResult, runs `compare()` against current live results for same pattern
- **Promotion logic:** `ComparisonVerdict.DOMINATES` + minimum shadow days + minimum shadow trades → `register_strategy_fingerprint()` + promote variant to live mode
- **Demotion logic:** Live variant `DOMINATED` by its own replacement + hysteresis guard (must be demoted for N consecutive sessions) → demote to shadow mode, promote replacement
- **Hysteresis guard:** Prevents oscillation (RSK-050). Configurable `promotion_hysteresis_sessions` threshold.
- Writes PromotionEvent to ExperimentStore on every state change
- `counterfactual_store=None` guard: gracefully skips if counterfactual tracking is disabled

### 15.7 Variant Lifecycle

```
PENDING (config/experiments.yaml entry)
  ↓ ExperimentRunner (BacktestEngine pre-filter)
BACKTESTING
  ↓ pre-filter pass (Sharpe/trades/win_rate thresholds)
SHADOW (VariantSpawner registers with Orchestrator)
  ↓ CounterfactualTracker accumulates live market evidence
  ↓ PromotionEvaluator checks after each SessionEndEvent
LIVE (Pareto dominance + min shadow days/trades threshold)
  ↓ (if performance degrades below promotion threshold)
DEMOTED → SHADOW (hysteresis guard, re-evaluate)
  ↓ (if KILLED via manual kill switch or catastrophic performance)
KILLED
```

Variants are never deleted from ExperimentStore — only status transitions occur. A DEMOTED variant remains eligible for re-promotion when market conditions change.

### 15.8 REST API

_Auto-regenerated (DEF-168, IMPROMPTU-08). JWT-protected endpoints under
`/api/v1/experiments` (Sprint 32) and `/api/v1/counterfactual` (Sprint 32.5)._

| Endpoint | Summary |
|----------|---------|
| `GET    /api/v1/experiments` | List experiments, optionally filtered by pattern name. |
| `GET    /api/v1/experiments/baseline/{pattern_name}` | Return the baseline experiment for a pattern. |
| `GET    /api/v1/experiments/promotions` | List promotion and demotion events with pagination. |
| `POST   /api/v1/experiments/run` | Trigger a parameter sweep for a pattern. |
| `GET    /api/v1/experiments/variants` | List all variants with experiment metrics where available. |
| `GET    /api/v1/experiments/{experiment_id}` | Return a single experiment by ID. |
| `GET    /api/v1/counterfactual/accuracy` | Get filter accuracy report for counterfactual positions. |
| `GET    /api/v1/counterfactual/positions` | Get shadow (counterfactual) positions with optional filters and pagination. |

**Behaviour notes:**
- `GET /api/v1/experiments` accepts a `?status=` filter; all `/experiments/*` routes return **503** when `experiments.enabled: false`.
- `POST /api/v1/experiments/run` dispatches a sweep via FastAPI `BackgroundTasks` and returns immediately (non-blocking).
- `GET /api/v1/counterfactual/positions` supports strategy / date / rejection-stage filters + pagination; R-multiple fields (`mfe_r`, `mae_r`) are serialized alongside preserved dollar excursions (IMPROMPTU-07, 2026-04-23).
- `GET /api/v1/counterfactual/accuracy` returns the `FilterAccuracyReport` breakdown (per-stage / per-reason / per-grade / per-regime / per-strategy).

### 15.9 UI (Sprint 32.5)

Two new surfaces added to the Command Center:
- **Shadow Trades tab** — second tab on the Trade Log page (keyboard shortcut `2` or tab click). Filter bar (strategy, rejection stage, date range), summary stats (total shadow trades, win rate, avg P&L), 13-column table (symbol, stage badge, grade badge, entry, stop, target, result P&L, MFE/MAE, duration, exit reason, strategy), pagination, empty state.
- **Experiments page** — 9th Command Center page (route `/experiments`, keyboard shortcut `9`, FlaskConical icon). Variant status table grouped by pattern (sortable by Win Rate, Expectancy, Sharpe), promotion event log, pattern comparison on group-header click (best Sharpe + best win rate highlighted), disabled state (503 → instructions to enable in `config/experiments.yaml`), empty state (0 variants → instructions to run `scripts/run_experiment.py`).

### 15.10 Allocation Intelligence Vision

The long-range architectural direction for capital allocation is documented in `docs/architecture/allocation-intelligence-vision.md`. Key points:
- **Problem:** Stacked guardrail chain asks "does this violate limits?" instead of "what is optimal capital?"
- **Vision:** Single `AllocationIntelligence` service replacing stacked chain with continuous sizing output
- **6 dimensions:** Edge estimation with uncertainty (Kelly), portfolio correlation penalty, opportunity cost, time-of-day weighting, drawdown response curve, variant track record
- **Phase 1** (~Sprint 34–35): Kelly-inspired sizing within existing Risk Manager boundary
- **Phase 2** (~Sprint 38+): Full AllocationIntelligence unification, Hard Floor as separate non-bypassable layer
- **Hard Floor** (non-overridable in all phases): circuit breakers, position size floor (0.25R), concentration limits, buying power check

### 15.11 Config

`config/experiments.yaml`:
```yaml
enabled: false
max_variants_per_pattern: 5
auto_promote: true
promotion_min_shadow_days: 5
promotion_min_shadow_trades: 30
promotion_hysteresis_sessions: 3
runner:
  min_sharpe: 0.5
  min_trade_count: 20
  min_win_rate: 0.35
variants: []  # List of {pattern_name, params} to spawn as shadow strategies
```

### 15.12 Directory Structure

```
intelligence/experiments/
├── __init__.py
├── models.py       # ExperimentRecord, VariantDefinition, PromotionEvent, ExperimentStatus (Sprint 32)
├── store.py        # ExperimentStore — SQLite data/experiments.db (Sprint 32)
├── spawner.py      # VariantSpawner — reads config, registers shadow variants (Sprint 32)
├── runner.py       # ExperimentRunner — grid generation + BacktestEngine pre-filter (Sprint 32)
├── promotion.py    # PromotionEvaluator — autonomous promote/demote (Sprint 32)
└── config.py       # ExperimentConfig Pydantic model (Sprint 32)

strategies/patterns/
└── factory.py      # build_pattern_from_config(), compute_parameter_fingerprint() (Sprint 32)

scripts/
└── run_experiment.py  # Standalone sweep CLI (Sprint 32)
```

---

## 16. Technology Stack Summary

See `docs/project-knowledge.md` § Tech Stack — authoritative. This section previously duplicated that content with drift (Deployment + Notifications rows were aspirational, not shipped) and is retained as a pointer.

---

*End of Architecture Document. Version marker retired (Sprint 28 tag was ~18 sprints stale). Major updates are tracked in `docs/sprint-history.md`; architectural decisions in `docs/decision-log.md`.*
