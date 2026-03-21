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
UniverseUpdateEvent(viable_count, routing_table_size, cache_age_minutes, per_strategy_counts)

# Strategy events
SignalEvent(strategy_id, symbol, side, entry_price, stop_price, target_prices, share_count, rationale)

# Risk events
OrderApprovedEvent(signal_event, modifications: dict | None)
OrderRejectedEvent(signal_event, reason: str)

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
RegimeChangeEvent(old_regime, new_regime, indicators)

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
LearningInsightEvent(insight_type, finding, confidence, period)
```

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
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult
    async def get_positions(self) -> list[Position]
    async def get_account(self) -> AccountInfo
    async def get_order_status(self, order_id: str) -> OrderStatus
    async def get_open_orders(self) -> list[Order]  # For state reconstruction (DEC-246)
    async def flatten_all(self) -> list[OrderResult]  # Emergency: close everything (uses SMART routing DEC-245)
```

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

### 3.4.4 Strategy Evaluation Telemetry — Sprint 24.5 ✅

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

**Instrumentation Coverage:** All 4 strategies emit evaluation events at every decision point (OR accumulation, finalization, exclusion checks, entry conditions, signal generation, quality scoring). AfMo `_check_breakout_entry()` restructured from sequential early-return to evaluate-all-then-check pattern to support 8 individual `CONDITION_CHECK` events.

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
- `RegimeClassifier` (`core/regime.py`): Rules-based SPY regime classification. Computes SMA-20/50, 5-day ROC, 20-day realized vol (VIX proxy, DEC-113). Classifies into 5 regimes: BULLISH_TRENDING, BEARISH_TRENDING, RANGE_BOUND, HIGH_VOLATILITY, CRISIS.
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
        - Trailing stop updates (if configured)
        """

    async def on_cancel(self, event: OrderCancelledEvent) -> None:
        """Handle order cancellation from broker."""

    async def on_circuit_breaker(self, event: CircuitBreakerEvent) -> None:
        """Circuit breaker triggered. Emergency flatten all positions."""

    async def eod_flatten(self) -> None:
        """Close all positions at market. Called from poll loop when
        clock.now() >= eod_flatten_time. Sets _flattened_today flag."""

    async def emergency_flatten(self) -> None:
        """Close all positions at market. Used by circuit breakers."""

    async def close_position(self, symbol: str) -> None:
        """Close specific position by symbol. Cancels child orders (stops,
        targets) and submits market sell. Routes through OrderManager for
        proper position tracking (DEC-352, Sprint 25.8)."""
```

**Position Management Architecture:**
- **Primary:** Event-driven via `TickEvent` subscription. On each tick, evaluates T2 price exit conditions for open positions.
- **Fallback:** 5-second polling loop handles time-based exits (time stops, EOD flatten). Checked via `clock.now()` against configured thresholds.
- **EOD Flatten:** Checked in the fallback poll loop (not APScheduler per DEC-041). Default 3:50 PM ET, configurable via `eod_flatten_time` and `eod_flatten_timezone`.
- **Stop Management:** Cancel-and-resubmit pattern (not modify-in-place) per DEC-040. When T1 fills, old stop is cancelled and new stop at breakeven is submitted.
- **T1/T2 Split:** Entry uses market order, then separate limit orders for T1 target and stop. T2 exit is via tick monitoring + market flatten order.

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
- **Zero-evaluation health warning (DEC-344, Sprint 25.5):** `check_strategy_evaluations()` detects active strategies with populated watchlists but zero evaluation events after their operating window + 5 min grace period. Sets component status to DEGRADED. Self-corrects to HEALTHY when evaluations resume (idempotent). Periodic 60s asyncio task in main.py during market hours only (9:30–16:00 ET). Opens/closes its own `EvaluationEventStore` per check cycle to avoid coupling with server.py-managed store lifecycle.

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

### 3.9 System Entry Point (`main.py`)

Wires all components together with a 12-phase startup sequence:

1. Config + Clock + EventBus
2. Database + TradeLogger
3. Broker connection
4. HealthMonitor
5. RiskManager (with state reconstruction)
6. DataService (Databento or Alpaca)
7. Scanner (pre-market scan)
7.5. FMPReferenceClient start (if Universe Manager enabled)
8. Build viable universe (if UM enabled, using scanner symbols)
9. Strategies (with mid-day reconstruction if applicable)
9.5. Build routing table (if UM enabled, from strategy configs); populate each strategy's watchlist from UM routing via `strategy.set_watchlist(symbols, source="universe_manager")` (DEC-343, Sprint 25.5)
10. OrderManager (with broker position reconstruction)
10.5. Set viable universe on DataService (if UM enabled)
11. Start data streaming
12. API server (in-process FastAPI)

Shutdown runs in reverse order. SIGINT/SIGTERM trigger graceful shutdown.

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

#### CatalystPipeline (`intelligence/catalyst/pipeline.py`) — Sprint 23.5 ✅

Orchestrates catalyst ingestion, classification, and storage from three data sources (DEC-164, DEC-304).

**Data Sources:**
- `SECEdgarSource` (`intelligence/catalyst/sources/sec_edgar.py`): 8-K filings, Form 4 insider transactions
- `FMPNewsSource` (`intelligence/catalyst/sources/fmp_news.py`): Stock news, press releases
- `FinnhubSource` (`intelligence/catalyst/sources/finnhub.py`): Company news, analyst recommendations (DEC-306). Finnhub 403 responses downgraded from ERROR to WARNING with per-cycle request/403 counters and cycle summary log (Sprint 24.5 S6).

**Core Components:**
- `CatalystClassifier` (`intelligence/catalyst/classifier.py`): Claude API classification with rule-based fallback (DEC-301). Categories: earnings, insider, guidance, analyst, regulatory, partnership, product, restructuring, other.
- `CatalystStorage` (`intelligence/catalyst/storage.py`): SQLite persistence with headline hash (SHA-256) deduplication (DEC-302).
- `BriefingGenerator` (`intelligence/catalyst/briefing.py`): Pre-market intelligence brief generation with $5/day cost ceiling via UsageTracker (DEC-303).

Interface:
- `async run(symbols: list[str]) -> list[Catalyst]`
- `async classify(headline: str, symbol: str) -> CatalystClassification`
- `async generate_briefing(symbols: list[str]) -> IntelligenceBrief`

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

**Note on SQLite databases:** ARGUS uses three separate SQLite database files to avoid write contention:
- `data/argus.db` — trades, quality history, orchestrator decisions, conversation history, AI usage
- `data/catalyst.db` — catalyst events and classifications (DEC-309, Sprint 23.6)
- `data/evaluation.db` — strategy evaluation telemetry events (DEC-345, Sprint 25.6)

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

#### LearningLoop (`intelligence/learning_loop.py`)
Post-trade analysis and model refinement.

Interface:
- `record_outcome(trade_id, quality, outcome) -> None`
- `retrain() -> ModelUpdate` — weekly batch
- `get_calibration() -> CalibrationReport`
- `get_insights(period_days) -> list[Insight]`

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

**Not yet implemented (future sprints):**
- PUT strategies (config updates)
- POST strategies pause/resume
- Orchestrator status
- Risk status details
- Emergency controls (flatten, pause, resume)
- Approval workflow endpoints
- Learning journal
- Claude API integration endpoints

### REST Endpoints (Implemented)
```
POST   /api/v1/auth/login              — Password login, returns JWT
POST   /api/v1/auth/refresh            — Refresh valid token
GET    /api/v1/auth/me                 — Verify token, return user info
GET    /api/v1/account                 — Account info, P&L, market status
GET    /api/v1/positions               — Open positions with computed fields
GET    /api/v1/trades                  — Trade history (filterable, paginated)
GET    /api/v1/performance/{period}    — Metrics for today/week/month/all
GET    /api/v1/strategies              — Strategy list with status
GET    /api/v1/health                  — System health + component status
GET    /api/v1/orchestrator/status     — Regime, allocations, throttle state, per-strategy deployment (DEC-135)
GET    /api/v1/orchestrator/decisions  — Decision history (paginated)
POST   /api/v1/orchestrator/rebalance  — Trigger manual rebalance
GET    /api/v1/session-summary         — Session recap (P&L, wins/losses, best/worst trade, regime, strategies). Query: ?date=YYYY-MM-DD
GET    /api/v1/dashboard/summary       — Aggregate endpoint returning all Dashboard card data (account, today_stats, goals, market, regime, deployment, orchestrator) in single response. Sprint 21d (DEC-222).

# Intelligence endpoints — Sprint 23.5 ✅ (Catalyst), Sprint 24+ (remaining)
GET  /api/v1/catalysts                   # List all catalysts (with filters: symbol, category, since) — Sprint 23.5 ✅
GET  /api/v1/catalysts/{symbol}          # Catalysts for a symbol — Sprint 23.5 ✅
POST /api/v1/catalysts/refresh           # Trigger catalyst pipeline refresh — Sprint 23.5 ✅
GET  /api/v1/intelligence/briefings      # List intelligence briefings — Sprint 23.5 ✅
GET  /api/v1/intelligence/briefings/{id} # Get specific briefing — Sprint 23.5 ✅
POST /api/v1/intelligence/briefings/generate  # Generate new briefing — Sprint 23.5 ✅
GET  /api/v1/premarket/briefing          # Current pre-market briefing (planned Sprint 24+)
GET  /api/v1/premarket/watchlist         # Ranked pre-market watchlist (planned Sprint 24+)
GET  /api/v1/orderflow/{symbol}          # Current order flow state + 1-min history (post-revenue)
GET  /api/v1/quality/{symbol}            # Current quality score (Sprint 24)
GET  /api/v1/quality/history             # Quality score history (Sprint 24)
GET  /api/v1/quality/distribution        # Today's grade distribution (Sprint 24)
GET  /api/v1/learning/calibration        # Predicted vs actual by grade (Sprint 28+)
GET  /api/v1/learning/insights           # Top recent findings (Sprint 28+)

# AI Copilot endpoints (Sprint 22)
WS   /api/v1/ai/chat                    # Copilot chat (WebSocket)
POST /api/v1/ai/briefing/generate       # Generate pre-market briefing
POST /api/v1/ai/report/generate         # Generate analysis report
POST /api/v1/ai/analyze/trade/{id}      # Analyze specific trade

# Universe Manager endpoints (Sprint 23)
GET  /api/v1/universe/status              # Viable count, routing table size, per-strategy counts, data age
GET  /api/v1/universe/symbols             # Paginated symbol list with strategy filter

# Debrief endpoints (Sprint 21c)
GET/POST         /api/v1/debrief/briefings           # List / create briefings
GET/PUT/DELETE   /api/v1/debrief/briefings/{id}      # Get / update / delete briefing
GET/POST         /api/v1/debrief/documents           # List / create documents (DB + filesystem)
GET/PUT/DELETE   /api/v1/debrief/documents/{id}      # Get / update / delete document
GET              /api/v1/debrief/documents/tags      # List all document tags
GET/POST         /api/v1/debrief/journal             # List / create journal entries
GET/PUT/DELETE   /api/v1/debrief/journal/{id}        # Get / update / delete entry
GET              /api/v1/debrief/journal/tags        # List all journal tags
GET              /api/v1/debrief/search              # Unified search across all 3 types

# Trade batch endpoint (Sprint 21c, DEC-203)
GET  /api/v1/trades/batch?ids=<ULIDs>           # Batch fetch trades by ID (max 50)

# Performance analytics endpoints (Sprint 21d)
GET  /api/v1/performance/heatmap                # Trade activity heatmap data (hour×DOW grid)
GET  /api/v1/performance/distribution           # R-multiple histogram + risk waterfall data
GET  /api/v1/performance/correlation            # Strategy pairwise correlation matrix
GET  /api/v1/performance/replay/{trade_id}      # Trade replay bar data for Lightweight Charts
GET  /api/v1/goals                              # GoalsConfig (monthly target, read/update)

# Market data endpoint (Sprint 21a)
GET  /api/v1/market/{symbol}/bars               # Synthetic OHLCV for dev mode symbol charts

```

### WebSocket
```
ws://host/ws/v1/live?token={jwt}
  → Streams: position.opened/closed/updated, order.submitted/filled/cancelled/approved/rejected,
    price.update (throttled, positions only), system.heartbeat, system.circuit_breaker,
    scanner.watchlist, strategy.signal
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

Seven pages delivered with responsive design across four breakpoints (DEC-169). Single React codebase targeting web, Tauri desktop (v2), and PWA mobile (DEC-080). Full animation system (Framer Motion), skeleton loading, emergency controls, trade detail panel, CSV export. Desktop icon sidebar with group dividers. Mobile 5-tab + More bottom sheet (DEC-211, DEC-216). AI Copilot shell panel (DEC-212). 1712 pytest + 257 Vitest tests.

### Pages

**Dashboard** (`/`): Ambient awareness surface (DEC-204). OrchestratorStatusStrip (clickable → Orchestrator page). StrategyDeploymentBar (per-strategy capital deployment with accent colors, click → Pattern Library or Orchestrator, DEC-219). GoalTracker (2-column pace dashboard with avg daily P&L and need/day metrics, color-coded pace indicator, DEC-220). Three-card row: MarketStatus (merged Market + Market Regime, DEC-221), TodayStats (2×2 metrics grid), SessionTimeline (SVG strategy windows with "now" marker, click → Orchestrator). Positions panel with table/timeline toggle and three-way filter All/Open/Closed (DEC-128). Recent trades list. SessionSummaryCard after hours (DEC-131). PreMarketLayout with placeholder cards (DEC-213, time-gated, data wired Sprint 23). Dashboard aggregate endpoint for single-request data loading (DEC-222). useSummaryData hook disabling pattern (DEC-223).

**Trade Log** (`/trades`): Filter bar (strategy, outcome, date range), stats summary row (total trades, win rate, net P&L), paginated trade table with color-coded exit reason badges. Row click opens TradeDetailPanel.

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
| Desktop (≥1024px) | Icon sidebar with group dividers | All 8 pages visible |
| Tablet (640–1023px) | Icon sidebar | All 8 pages visible |
| Mobile (<640px) | Bottom tab bar (5 tabs) + More sheet | Dash, Trades, Orch, Patterns, More → (Performance, Debrief, System) |

Global keyboard shortcuts: `1`–`7` page navigation, `w` watchlist toggle, `c` copilot toggle (DEC-199).

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

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/controls/strategies/{id}/pause` | POST | Pause strategy signal generation |
| `/controls/strategies/{id}/resume` | POST | Resume paused strategy |
| `/controls/positions/{id}/close` | POST | Close specific position via `OrderManager.close_position(symbol)` (DEC-352) |
| `/controls/emergency/flatten` | POST | Emergency close all positions |
| `/controls/emergency/pause` | POST | Emergency pause all strategies |
| `/trades/export/csv` | GET | Export trades as CSV (with filters) |

### Orchestrator Endpoints (Sprint 17)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/orchestrator/status` | GET | Current regime, indicators, allocations, next regime check time |
| `/orchestrator/decisions` | GET | Paginated decision history (allocation, regime, throttle, suspension) |
| `/orchestrator/rebalance` | POST | Trigger manual allocation rebalance |

## 5. Backtesting Toolkit

Two-layer approach: VectorBT for fast parameter exploration, Replay Harness for full-fidelity validation. Backtrader was dropped (DEC-046) — the Replay Harness runs actual production code, making Backtrader's intermediate-fidelity approach redundant.

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
```

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
├── data_fetcher.py       # Historical data download (Databento primary, Alpaca legacy) → Parquet cache
├── replay_harness.py     # Production code replay engine
├── vectorbt_orb.py       # VectorBT parameter sweeps
├── metrics.py            # Performance metric calculations
├── walk_forward.py       # Walk-forward analysis framework
└── report_generator.py   # HTML report generation
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

### Future Module: `argus/intelligence/`
Planned for Build Track near-term (Tier 1, Sprint 17) and Build Track later (Tiers 2–3). Will contain:
- `calendar.py` — Economic and earnings calendar ingestion
- `news_feed.py` — News API subscription and symbol matching
- `classifier.py` — Catalyst type classification (keyword → ML pipeline)
- `edgar.py` — SEC EDGAR filing crawler (8-K, Form 4, 13F)
- `sentiment.py` — Claude API sentiment analysis (Tier 3)

Not yet implemented. Interface will publish `CatalystEvent` to the Event Bus for consumption by Scanner, Risk Manager, and Learning Journal.

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

**Overview Dashboard:** Account equity, daily P&L, active strategies at a glance, open positions, recent trades, current market regime, system health indicator, approval queue badge

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

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ai/conversations` | GET | List conversations (date/tag filter) |
| `/api/v1/ai/conversations` | POST | Create conversation |
| `/api/v1/ai/conversations/{id}/messages` | GET | Get messages for conversation |
| `/api/v1/ai/actions/{id}/approve` | POST | Approve pending proposal |
| `/api/v1/ai/actions/{id}/reject` | POST | Reject pending proposal |
| `/api/v1/ai/actions/pending` | GET | List pending proposals |
| `/api/v1/ai/insight` | GET | Get dashboard AI insight (cached) |
| `/api/v1/ai/usage` | GET | Get usage/cost summary |
| `/api/v1/ai/status` | GET | AI service status + monthly spend |

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
- Dashboard protected by JWT authentication with 2FA
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

## 10. Notification Service (`notifications/service.py`)

```python
class NotificationService:
    async def send(self, alert: Alert) -> None:
        """Route alert to appropriate channels based on alert.category and config."""

    channels: list[NotificationChannel]  # Push, Email, Telegram, Discord

class Alert:
    category: str       # 'critical', 'informational', 'periodic'
    title: str
    body: str
    data: dict          # Structured data for rich notifications
    timestamp: datetime
```

**Channel Implementations:**
- `PushChannel` — via Firebase Cloud Messaging or similar (for Tauri/mobile)
- `EmailChannel` — via SendGrid, SES, or SMTP
- `TelegramChannel` — via Telegram Bot API
- `DiscordChannel` — via Discord webhook

---

## 11. Shadow System (`core/shadow.py`)

A parallel instance of the full trading engine running in paper mode. Uses the same live data feed but submits orders to `SimulatedBroker` instead of real broker.

**Purpose:** Continuous validation that the live system and shadow system produce identical signals. Divergence indicates execution issues (slippage, partial fills, timing) and is reported.

**Implementation:** Runs as a separate process on the same VPS. Shares the Data Service (read-only) but has its own strategy instances, Risk Manager, and Order Manager.

---

## 12. Configuration Files

All tunable parameters live in YAML files, not in code.

```
config/
├── system.yaml           # Global settings (timezone, market hours, logging level)
├── brokers.yaml          # Broker connections and routing rules
├── risk_limits.yaml      # All three levels of risk parameters
├── orchestrator.yaml     # Allocation rules, regime thresholds, throttling rules
├── notifications.yaml    # Channel configs, alert routing, schedule
├── strategies/
│   ├── orb_breakout.yaml
│   ├── orb_scalp.yaml
│   ├── vwap_reclaim.yaml
│   ├── afternoon_momentum.yaml
│   └── red_to_green.yaml
└── ui.yaml               # Dashboard preferences, default views
```

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

## 14. Technology Stack Summary

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Async Runtime | asyncio |
| Broker SDKs | alpaca-py>=0.30, ib_async>=1.0.0 |
| Environment | python-dotenv>=1.0 |
| Data Manipulation | pandas, numpy |
| Technical Indicators | pandas-ta or ta-lib |
| Backtesting (fast) | VectorBT |
| Backtesting (full) | Replay Harness (production code replay) |
| Database | SQLite (production: consider PostgreSQL for scale) |
| API Server | FastAPI (REST + WebSocket) |
| Desktop App | Tauri v2 |
| Frontend | React 18+ / TypeScript / Tailwind CSS |
| Charts (time-series) | Lightweight Charts (TradingView) |
| Charts (standard) | Recharts |
| Charts (custom viz) | D3 (sparingly — treemaps, heatmaps) |
| 3D Visualization | Three.js r128 (Observatory Funnel/Radar views, code-split) |
| Animation | Framer Motion + CSS transitions |
| AI Integration | Anthropic Claude API |
| Scheduling | APScheduler |
| Notifications | Firebase/Telegram Bot API/SendGrid/Discord Webhook |
| Deployment | AWS EC2 / systemd / Nginx |
| Version Control | Git |
| Secrets | age-encryption or SOPS (production: AWS Secrets Manager) |
| ID Generation | python-ulid (ULIDs) |

---

*End of Architecture Document v1.1 (updated Sprint 25 — Observatory subsystem)*
