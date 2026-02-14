# ARGUS — Architecture Document

> *Version 1.0 | February 2026*
> *This document defines the technical design of the Argus system. It translates the Project Bible's intent into implementation specifications. A developer should be able to read this document and know exactly how to build any component.*

---

## 1. System Tiers

Argus is built in three tiers, each depending on the one before it.

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
│  Alpaca API    IBKR API    Polygon.io    Banks (Plaid)    Claude API│
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

**Pattern:** In-process pub/sub using Python's `asyncio`. No external message broker needed for V1.

**Event Types:**
```python
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
    async def subscribe_candles(self, symbol: str, timeframe: str, callback: Callable)
    async def subscribe_ticks(self, symbol: str, callback: Callable)
    async def get_indicator(self, symbol: str, indicator: str) -> float
    async def get_current_price(self, symbol: str) -> float
    async def get_historical_candles(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> pd.DataFrame
    async def get_watchlist_data(self, symbols: list[str]) -> dict
```

**Implementations:**
- `AlpacaDataService` — live WebSocket + REST historical
- `IBKRDataService` — TWS API data feed
- `ReplayDataService` — reads historical data files, drips into the system at configurable speed

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
- `AlpacaBroker` — wraps `alpaca-trade-api` SDK
- `IBKRBroker` — wraps `ib_insync` / `ib_api`
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

### 3.4 Base Strategy (`strategies/base_strategy.py`)

Every strategy implements this interface.

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

    # State
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
        """Called at start of each trading day."""
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

Manages the lifecycle of every order from submission to fill/cancel.

```python
class OrderManager:
    async def submit_signal(self, approved_signal: OrderApprovedEvent) -> None:
        """Convert approved signal to broker order(s). Submit via BrokerRouter."""

    async def on_fill(self, event: OrderFilledEvent) -> None:
        """Handle partial and full fills. Update position tracking."""

    async def manage_open_positions(self) -> None:
        """
        Continuous loop:
        - Move stops to breakeven when T1 hits
        - Execute time stops
        - Execute end-of-day flattening at 3:50 PM
        - Execute trailing stops if configured
        """

    async def emergency_flatten(self) -> None:
        """Close all positions at market. Used by circuit breakers and manual override."""
```

### 3.8 Trade Logger (`analytics/trade_log.py`)

Every trade is recorded with comprehensive metadata.

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

### 5.1 VectorBT Layer (`backtest/vectorbt/`)

Used for rapid parameter exploration. Strategies are expressed in simplified vectorized form.

```python
# Example: ORB parameter sweep
import vectorbt as vbt

# Load historical 1-minute data
data = load_historical_data("2025-06-01", "2025-12-31", symbols=scanner_results)

# Define parameter ranges
orb_windows = [5, 10, 15, 20, 30]
stop_ratios = [0.3, 0.4, 0.5, 0.6]  # Stop at X of range from high
target_ratios = [1.0, 1.5, 2.0, 2.5]
volume_filters = [1.5, 2.0, 2.5, 3.0]

# Run combinatorial sweep (all parameter combinations)
results = sweep_orb_parameters(data, orb_windows, stop_ratios, target_ratios, volume_filters)

# Output: DataFrame of metrics per parameter combination
# Sort by Sharpe ratio, profit factor, or custom scoring function
```

### 5.2 Backtrader Layer (`backtest/backtrader/`)

Used for full-fidelity single-strategy validation at specific parameters.

```python
# Example: Validate ORB-15 with selected parameters
import backtrader as bt

cerebro = bt.Cerebro()
cerebro.addstrategy(OrbBacktraderStrategy, 
    orb_window=15, stop_ratio=0.5, target_1=1.0, target_2=2.0, volume_filter=2.0)
cerebro.adddata(historical_minute_data)
cerebro.broker.setcash(25000)
cerebro.broker.setcommission(commission=0.0)
results = cerebro.run()
# Analyze: win rate, profit factor, max drawdown, equity curve
```

### 5.3 Replay Harness (`backtest/replay/`)

Feeds historical data through the production system.

**Architecture:**
```
ReplayDataService (implements DataService interface)
  → reads historical data from Parquet/CSV files
  → emits CandleEvents and TickEvents at configurable speed
  → supports: real-time speed, accelerated (e.g., 100x), or instant (as fast as possible)

SimulatedBroker (implements Broker interface)
  → fills orders at historical prices
  → simulates slippage (configurable: none, fixed, random within range)
  → simulates partial fills (configurable)
  → enforces buying power and margin rules

ReplayHarness (orchestration)
  → initializes production system with ReplayDataService + SimulatedBroker
  → runs the full stack: all strategies, Orchestrator, Risk Manager
  → records all events and trades
  → produces comparison report: expected vs actual behavior
```

---

## 6. Command Center (Tier 2)

### 6.1 Technology Stack
- **Framework:** Tauri v2 (Rust backend, web frontend)
- **Frontend:** React 18+ with TypeScript
- **Styling:** Tailwind CSS
- **State Management:** Zustand or Jotai (lightweight, performant)
- **Charts:** Lightweight Charts (TradingView's open-source library) for price charts; Recharts for performance metrics
- **Data Fetching:** TanStack Query for REST; native WebSocket for real-time
- **Mobile:** Same React app served as responsive web app accessible via browser

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
| Broker SDKs | alpaca-trade-api, ib_insync |
| Data Manipulation | pandas, numpy |
| Technical Indicators | pandas-ta or ta-lib |
| Backtesting (fast) | VectorBT |
| Backtesting (full) | Backtrader |
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

---

*End of Architecture Document v1.0*
