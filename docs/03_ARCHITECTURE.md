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

### 3.2b Data Flow Architecture

```
Live Trading:
  Databento US Equities ──TCP──> DatabentoDataService ──EventBus──> All Strategies
                                        │                              │
                                        ├── CandleEvents (1m bars)     ├── Strategy 1
                                        ├── TickEvents (every trade)   ├── Strategy 2
                                        ├── IndicatorEvents (VWAP,ATR) ├── ...
                                        └── L2 Depth (when needed)     └── Strategy 30+

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
- `dataset`: "XNAS.ITCH" (NASDAQ) + "XNYS.PILLAR" (NYSE) or equivalent composite
- `schema`: ["ohlcv-1m", "trades"] (default), ["mbp-10"] (optional L2)
- `symbols`: list or "ALL_SYMBOLS" for full universe
- `reconnect_max_retries`: 10
- `reconnect_base_delay_seconds`: 1.0

Sprint 12 scope. See DEC-082 and `argus_market_data_research_report.md` Section 14.

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
    async def flatten_all(self) -> list[OrderResult]  # Emergency: close everything
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

**Implementation Status:** `SimulatedBroker` and `AlpacaBroker` implemented (Phase 1, Sprints 1–5). `IBKRBroker` is Sprint 13 (DEC-083/084) — uses `ib_async` (asyncio-native, `ib-api-reloaded` GitHub org). IB Gateway runs as a local Java process (Docker containerized for deployment). `DatabentoDataService` is Sprint 12 (DEC-082). The existing comprehensive test suite against the `Broker` ABC and `DataService` ABC ensures all adapters are drop-in compatible.

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

Sprint 13 scope. See DEC-083 and `argus_execution_broker_research_report.md` Section 11.

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

    def reset_daily_state(self) -> None:
        """Called at start of each trading day. Wipes all intraday state."""

    async def reconstruct_state(self, trade_logger: TradeLogger) -> None:
        """Reconstruct intraday state from database after mid-day restart.
        Queries today's trades and open positions from the Trade Logger."""
```

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
| Reduce share count | Reduce to fit buying power or position limits. Reject if reduced position yields < 0.25R potential profit. |
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

```python
class Orchestrator:
    async def pre_market_routine(self) -> None:
        """
        Runs daily before market open:
        1. Classify current market regime
        2. Determine which strategies are eligible (regime filter)
        3. Calculate capital allocation per strategy
        4. Activate/deactivate strategies
        5. Publish AllocationUpdateEvents
        """

    async def evaluate_regime(self) -> MarketRegime:
        """Assess current market conditions using V1 indicator set."""

    async def calculate_allocations(self, active_strategies: list[BaseStrategy]) -> dict[str, float]:
        """Determine capital allocation percentages based on performance and regime."""

    async def check_throttling(self, strategy: BaseStrategy) -> ThrottleAction:
        """Check if strategy should be throttled or suspended based on performance."""

    async def end_of_day_review(self) -> None:
        """Review day's performance, update rolling metrics, log orchestrator decisions."""
```

### 3.7 Order Manager (`execution/order_manager.py`)

Manages the lifecycle of every order from submission to fill/cancel. Position management is event-driven.

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

Wires all components together with a 10-phase startup sequence:

1. Config + Clock + EventBus
2. Database + TradeLogger
3. Broker connection
4. HealthMonitor
5. RiskManager (with state reconstruction)
6. AlpacaDataService
7. AlpacaScanner (pre-market scan)
8. OrbBreakoutStrategy (with mid-day reconstruction if applicable)
9. OrderManager (with broker position reconstruction)
10. Start data streaming

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

CREATE TABLE journal_entries (
    id TEXT PRIMARY KEY,
    entry_type TEXT NOT NULL,  -- 'observation', 'analysis', 'decision', 'insight'
    content TEXT NOT NULL,
    author TEXT NOT NULL,  -- 'user' or 'claude'
    linked_strategy_id TEXT,
    linked_trade_ids TEXT,  -- JSON array
    linked_date_range TEXT,  -- JSON: {start, end}
    tags TEXT,  -- JSON array
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

---

## 4. API Server (`core/api_server.py`)

Tier 1 exposes a REST + WebSocket API for the Command Center and AI Layer.

### REST Endpoints

```
GET    /api/v1/account              — Account info (equity, cash, buying power)
GET    /api/v1/positions             — All open positions across strategies
GET    /api/v1/positions/:strategy   — Open positions for a specific strategy
GET    /api/v1/strategies            — List all strategies with status and allocation
GET    /api/v1/strategies/:id        — Detailed strategy info + recent performance
PUT    /api/v1/strategies/:id        — Update strategy config (requires approval if configured)
POST   /api/v1/strategies/:id/pause  — Pause a strategy
POST   /api/v1/strategies/:id/resume — Resume a strategy
GET    /api/v1/orchestrator/status   — Current regime, allocations, decisions
GET    /api/v1/risk/status           — Risk utilization (daily loss used, positions open, etc.)
GET    /api/v1/trades                — Trade history (filterable by strategy, date, outcome)
GET    /api/v1/trades/:id            — Single trade detail
GET    /api/v1/performance/:period   — Performance metrics (daily/weekly/monthly/all-time)
GET    /api/v1/approvals/pending     — Pending approval requests
POST   /api/v1/approvals/:id/approve — Approve an action
POST   /api/v1/approvals/:id/reject  — Reject an action
GET    /api/v1/journal               — Learning journal entries (filterable)
POST   /api/v1/journal               — Add a journal entry
POST   /api/v1/emergency/shutdown    — Emergency flatten all positions
POST   /api/v1/emergency/pause       — Pause all trading (no new entries)
POST   /api/v1/emergency/resume      — Resume trading
GET    /api/v1/health                — System health status
POST   /api/v1/claude/chat           — Send a message to Claude (async response)
GET    /api/v1/claude/proposals       — Claude's pending action proposals
```

### WebSocket Streams

```
ws://host/ws/v1/live
  → Streams real-time events: position updates, trade executions, 
    price ticks for open positions, system alerts, approval requests
```

### Authentication
- JWT-based authentication
- Tokens issued on login with username + password + 2FA
- Tokens expire after configurable period (default: 24 hours)
- All API calls require valid token in Authorization header

---

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

### 7.1 Claude API Integration (`ai/claude_service.py`)

```python
class ClaudeService:
    async def chat(self, message: str, context: SystemContext) -> ClaudeResponse:
        """
        Send a message to Claude with current system context.
        Context includes: account state, open positions, today's trades, 
        recent performance, current regime, pending approvals.
        """

    async def generate_analysis(self, analysis_type: str, params: dict) -> str:
        """Generate analytical narrative (EOD report, strategy review, etc.)"""

    async def propose_action(self, action: ProposedAction) -> ApprovalRequest:
        """Submit a Claude-generated action proposal to the approval queue."""

    async def generate_report(self, report_type: str, date_range: DateRange) -> Report:
        """Generate a formatted report with charts and narrative."""
```

### 7.2 Context Builder (`ai/context_builder.py`)

Assembles relevant system state into a context payload for each Claude API call. Must be concise (fits within Claude's context window) while providing enough information for informed analysis.

```python
class SystemContextBuilder:
    def build_context(self, scope: str = "full") -> SystemContext:
        """
        Scopes:
        - "full": everything (for deep analysis)
        - "trading": positions, today's trades, regime (for trade-related questions)
        - "strategy": specific strategy's history and config (for strategy questions)
        - "minimal": just account state (for simple queries)
        """
```

### 7.3 Approval Workflow (`ai/approval_workflow.py`)

All Claude-proposed actions go through the same approval pipeline as other system actions. The approval queue is a first-class concept shared between the Orchestrator, Risk Manager, and Claude.

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

## 13. Technology Stack Summary

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Async Runtime | asyncio |
| Broker SDKs | alpaca-py>=0.30, ib_insync |
| Environment | python-dotenv>=1.0 |
| Data Manipulation | pandas, numpy |
| Technical Indicators | pandas-ta or ta-lib |
| Backtesting (fast) | VectorBT |
| Backtesting (full) | Replay Harness (production code replay) |
| Database | SQLite (production: consider PostgreSQL for scale) |
| API Server | FastAPI (REST + WebSocket) |
| Desktop App | Tauri v2 |
| Frontend | React 18+ / TypeScript / Tailwind CSS |
| Charts | Lightweight Charts, Recharts |
| AI Integration | Anthropic Claude API |
| Scheduling | APScheduler |
| Notifications | Firebase/Telegram Bot API/SendGrid/Discord Webhook |
| Deployment | AWS EC2 / systemd / Nginx |
| Version Control | Git |
| Secrets | age-encryption or SOPS (production: AWS Secrets Manager) |
| ID Generation | python-ulid (ULIDs) |

---

*End of Architecture Document v1.0*
