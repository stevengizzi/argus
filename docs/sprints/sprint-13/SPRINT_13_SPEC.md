# ARGUS — Sprint 13 Spec: IBKRBroker Adapter + IB Gateway Integration

> **Version:** 1.0 | February 21, 2026
> **Status:** Approved — ready for implementation
> **Author:** Steven + Claude (strategic design)
> **Target:** ~80 new tests → ~765 total
> **Estimated duration:** 3–5 days
> **Prerequisite reads:** `03_ARCHITECTURE.md` §3.3/3.7, `argus_execution_broker_research_report.md` §11, `CLAUDE.md`

---

## 1. Sprint Goal

Implement `IBKRBroker` — the production execution broker adapter — implementing the existing `Broker` ABC via the `ib_async` library. After this sprint, ARGUS can submit orders, receive fills, query account state, and manage positions through Interactive Brokers with **native multi-leg bracket orders**, enabling paper trading migration from Alpaca to IBKR.

**IBKR Account Status:** Application submitted Feb 21 (Account ID: U24619949). Awaiting approval (1–3 business days typical). All development uses mocked `ib_async.IB` instances. Integration testing requires the approved paper trading account.

---

## 2. Key Decisions (Approved)

### DEC-093 — Native IBKR Bracket Orders (Option B)

| Field | Value |
|-------|-------|
| **Date** | 2026-02-21 |
| **Decision** | IBKRBroker uses IBKR's native multi-leg bracket orders. All bracket legs (entry + stop + T1 + T2) are submitted atomically. The Order Manager is updated to handle broker-side T2 limit orders (not tick-monitored) when the broker supports it. |
| **Rationale** | IBKR supports full multi-leg brackets with parentId linkage. Atomic submission means all-or-nothing — no partial bracket states. Broker-side T2 orders survive ARGUS crashes. Parent cancellation auto-cascades to all children. Since IBKR is the production target, building native bracket support now avoids a future migration sprint. |
| **Impact on Order Manager** | (1) New `t2_order_id` field on `ManagedPosition`. (2) New `"t2"` order type in `PendingManagedOrder`. (3) T2 fill handling in `on_fill()` — cancel remaining stop, close position. (4) Skip tick-based T2 monitoring when `t2_order_id` is set. (5) `place_bracket_order()` passes full `targets` list (T1 + T2) to broker. |
| **Backward compatibility** | AlpacaBroker continues to receive only `targets[0]` (T1). Order Manager branches on whether `t2_order_id` is set to decide T2 handling path. |
| **Status** | Active |

### DEC-094 — BrokerSource Enum for Provider Selection

| Field | Value |
|-------|-------|
| **Date** | 2026-02-21 |
| **Decision** | `BrokerSource` enum in `SystemConfig` with `alpaca`/`ibkr`/`simulated` variants. Mirrors the `DataSource` enum pattern from Sprint 12 (DEC-090). `main.py` Phase 3 (broker initialization) branches on this to select the Broker implementation. |
| **Rationale** | Consistent with existing DataSource pattern. Config-driven, extensible. |
| **Status** | Active |

---

## 3. Architecture Context

### 3.1 Broker ABC Interface (from `argus/execution/broker.py`)

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

IBKRBroker implements this interface exactly. The existing AlpacaBroker implementation (Sprint 4a) is the structural template.

### 3.2 Order Manager T1/T2 Flow (Current — Alpaca)

1. `on_approved()`: calls `broker.place_bracket_order(entry, stop, [T1])` — Alpaca receives single target
2. `on_fill(entry)`: creates `ManagedPosition`, records `stop_order_id` and `t1_order_id`
3. `on_fill(T1)`: cancel old stop, submit new stop at breakeven for remaining shares. `t1_filled = True`
4. `on_tick()`: if `t1_filled` and `price >= t2_price` → submit market flatten for remaining shares
5. `on_fill(flatten)`: close position, publish `PositionClosedEvent`

### 3.3 Order Manager T1/T2 Flow (New — IBKR with Native Brackets)

1. `on_approved()`: calls `broker.place_bracket_order(entry, stop, [T1, T2])` — IBKR receives both targets
2. `on_fill(entry)`: creates `ManagedPosition`, records `stop_order_id`, `t1_order_id`, AND `t2_order_id`
3. `on_fill(T1)`: cancel old stop, submit new stop at breakeven for remaining shares. `t1_filled = True`
4. `on_fill(T2)`: cancel remaining stop, close position. Publish `PositionClosedEvent`
5. `on_tick()`: if `t2_order_id is None` (Alpaca path) → tick-monitor T2. If `t2_order_id is set` (IBKR path) → skip T2 tick check
6. `on_fill(stop)`: broker auto-cancels remaining children (T1/T2) via parentId cascade. Close position.

**Key differences from Alpaca path:**
- T2 is a broker-side limit order, not tick-monitored
- Stop fill auto-cancels T1 and T2 children (bracket behavior)
- T2 fill triggers stop cancellation (not tick-based flatten)
- No market flatten order needed for T2 — it's already a limit order at the broker

### 3.4 ib_async Library Overview

- **Package:** `ib_async>=2.1.0` (PyPI). Successor to `ib_insync`. GitHub: `ib-api-reloaded/ib_async`.
- **Dependencies:** `aeventkit>=2.1.0` (event framework), `nest_asyncio` (notebook support, optional for us)
- **Architecture:** asyncio-native. The `IB` class maintains an event loop, auto-syncs with TWS/Gateway. No separate reader thread — events fire on the same event loop as ARGUS.
- **Key types:** `IB` (main client), `Stock`/`Contract` (instruments), `Order` (order specification), `Trade` (order + status + fills), `Position` (portfolio position), `AccountValue` (account data)
- **Event system:** `ib.orderStatusEvent`, `ib.newOrderEvent`, `ib.errorEvent`, `ib.disconnectedEvent`, `ib.connectedEvent` — subscribe via `+=` operator
- **Auto-sync on connect:** `StartupFetch` fetches positions, open orders, completed orders, account updates, and executions automatically. Subsequent reads from `ib.positions()`, `ib.openTrades()`, etc. are cached in-memory.
- **Ports:** 4001 (Gateway live), 4002 (Gateway paper), 7496 (TWS live), 7497 (TWS paper)
- **Order IDs:** Sequential integers, unique per clientId. `ib_async` manages the next valid ID automatically.
- **bracketOrder helper:** `ib.bracketOrder(action, quantity, limitPrice, takeProfitPrice, stopLossPrice)` returns `(parent, takeProfit, stopLoss)` — three pre-linked Order objects with parentId set and transmit flags configured.

### 3.5 Critical: No Thread Bridging Needed

Unlike Databento (DEC-088) which uses a reader thread requiring `call_soon_threadsafe()`, `ib_async` is asyncio-native. Event handlers fire on the same event loop. **Do NOT use `call_soon_threadsafe()`.** This makes integration simpler than Sprint 12.

### 3.6 Critical: No Market Data from IBKR

ARGUS uses Databento for all market data (DEC-082). The IBKR connection is **execution-only**. Do not call `reqMktData()`, `reqRealTimeBars()`, or any market data methods. This avoids IBKR's market data subscription fees and their 5-second bar delay.

---

## 4. Component Breakdown

### Component 1: IBKRConfig + BrokerSource Enum

**File:** `argus/core/config.py` (modify existing)

```python
class BrokerSource(str, Enum):
    """Broker provider selection (mirrors DataSource pattern from DEC-090)."""
    ALPACA = "alpaca"
    IBKR = "ibkr"
    SIMULATED = "simulated"

class IBKRConfig(BaseModel):
    """Interactive Brokers connection configuration."""
    host: str = "127.0.0.1"
    port: int = 4002              # 4001=live, 4002=paper. Default to paper for safety.
    client_id: int = 1
    account: str = ""             # IBKR account ID (e.g., "U24619949")
    timeout_seconds: float = 30.0
    readonly: bool = False
    # Reconnection
    reconnect_max_retries: int = 10
    reconnect_base_delay_seconds: float = 1.0
    reconnect_max_delay_seconds: float = 60.0
    # Operational safety
    max_order_rate_per_second: float = 45.0  # IBKR limit is 50/sec, leave headroom
```

**File:** `argus/core/config.py` — add to `SystemConfig`:
```python
class SystemConfig(BaseModel):
    # ... existing fields ...
    broker_source: BrokerSource = BrokerSource.SIMULATED
    ibkr: IBKRConfig = IBKRConfig()
```

**File:** `config/brokers.yaml` — add ibkr section:
```yaml
broker_source: "simulated"  # "alpaca", "ibkr", or "simulated"

ibkr:
  host: "127.0.0.1"
  port: 4002  # 4001=live, 4002=paper
  client_id: 1
  account: ""  # Set via environment variable or override
  timeout_seconds: 30.0
  readonly: false
  reconnect_max_retries: 10
  reconnect_base_delay_seconds: 1.0
  reconnect_max_delay_seconds: 60.0
```

**Tests:** 3 (config loading from YAML, default values, validation of port/client_id)

### Component 2: Contract Resolution

**File:** `argus/execution/ibkr_contracts.py` (new, ~60 lines)

Converts ARGUS symbol strings to `ib_async` Contract objects. V1 handles US equities only.

```python
from ib_async import Stock, Contract, IB

class IBKRContractResolver:
    """Resolves ARGUS symbols to qualified IBKR Contract objects."""
    
    def __init__(self) -> None:
        self._cache: dict[str, Contract] = {}
    
    def get_stock_contract(self, symbol: str, exchange: str = "SMART",
                           currency: str = "USD") -> Stock:
        """Create a Stock contract for the given symbol.
        Uses SMART routing by default (IBKR SmartRouting across 20+ venues)."""
        if symbol not in self._cache:
            self._cache[symbol] = Stock(symbol, exchange, currency)
        return self._cache[symbol]
    
    async def qualify_contracts(self, ib: IB, symbols: list[str]) -> dict[str, Contract]:
        """Qualify contracts with IBKR to get full conId resolution.
        Call once at startup for the watchlist. Caches results."""
        contracts = [self.get_stock_contract(s) for s in symbols]
        qualified = await ib.qualifyContractsAsync(*contracts)
        for c in qualified:
            self._cache[c.symbol] = c
        return self._cache
    
    def clear_cache(self) -> None:
        self._cache.clear()
```

**Extension point:** When options/futures/forex are added, this module gets new methods (`get_option_contract()`, `get_futures_contract()`, etc.) without changing the IBKRBroker code.

**Tests:** 4 (stock creation, cache behavior, qualification mock, SMART exchange default)

### Component 3: Error Handling

**File:** `argus/execution/ibkr_errors.py` (new, ~120 lines)

IBKR error codes are extensive and cryptic. This module provides classification and human-readable mapping.

```python
from dataclasses import dataclass
from enum import Enum

class IBKRErrorSeverity(str, Enum):
    CRITICAL = "critical"    # Connection lost, no trading permission
    WARNING = "warning"      # Order rejected, cannot modify
    INFO = "info"            # Market data not subscribed (irrelevant for us)

@dataclass
class IBKRErrorInfo:
    code: int
    severity: IBKRErrorSeverity
    category: str            # "connection", "order", "account", "data", "system"
    description: str
    action: str              # What ARGUS should do: "reconnect", "log", "reject_order", "circuit_break"

# Comprehensive error map — key errors that IBKRBroker must handle
IBKR_ERROR_MAP: dict[int, IBKRErrorInfo] = {
    # Connection errors
    1100: IBKRErrorInfo(1100, IBKRErrorSeverity.CRITICAL, "connection",
        "Connectivity between IB and TWS has been lost", "reconnect"),
    1101: IBKRErrorInfo(1101, IBKRErrorSeverity.WARNING, "connection",
        "Connectivity restored — data may have been lost during disconnect", "verify_state"),
    1102: IBKRErrorInfo(1102, IBKRErrorSeverity.INFO, "connection",
        "Connectivity restored — data maintained", "log"),
    502: IBKRErrorInfo(502, IBKRErrorSeverity.CRITICAL, "connection",
        "Couldn't connect to TWS/Gateway", "reconnect"),
    504: IBKRErrorInfo(504, IBKRErrorSeverity.CRITICAL, "connection",
        "Not connected", "reconnect"),
    
    # Order errors
    103: IBKRErrorInfo(103, IBKRErrorSeverity.WARNING, "order",
        "Duplicate order ID", "generate_new_id"),
    104: IBKRErrorInfo(104, IBKRErrorSeverity.WARNING, "order",
        "Can't modify a filled order", "log"),
    105: IBKRErrorInfo(105, IBKRErrorSeverity.WARNING, "order",
        "Order being modified does not match original", "log"),
    110: IBKRErrorInfo(110, IBKRErrorSeverity.WARNING, "order",
        "The price does not conform to the minimum price variation", "reject_order"),
    135: IBKRErrorInfo(135, IBKRErrorSeverity.CRITICAL, "account",
        "Can't find order with ID", "log"),
    161: IBKRErrorInfo(161, IBKRErrorSeverity.INFO, "order",
        "Cancel attempted", "log"),
    200: IBKRErrorInfo(200, IBKRErrorSeverity.WARNING, "order",
        "No security definition has been found (ambiguous contract)", "reject_order"),
    201: IBKRErrorInfo(201, IBKRErrorSeverity.WARNING, "order",
        "Order rejected — reason in error message", "reject_order"),
    202: IBKRErrorInfo(202, IBKRErrorSeverity.INFO, "order",
        "Order cancelled", "log"),
    203: IBKRErrorInfo(203, IBKRErrorSeverity.CRITICAL, "account",
        "The security is not available or allowed for this account", "reject_order"),
    
    # Account errors
    321: IBKRErrorInfo(321, IBKRErrorSeverity.CRITICAL, "account",
        "Server error validating API client request", "log"),
    
    # Market data (informational — we use Databento, not IBKR data)
    354: IBKRErrorInfo(354, IBKRErrorSeverity.INFO, "data",
        "Requested market data is not subscribed", "log"),
    10167: IBKRErrorInfo(10167, IBKRErrorSeverity.INFO, "data",
        "Requested market data is not subscribed (delayed data available)", "log"),
    
    # System
    2103: IBKRErrorInfo(2103, IBKRErrorSeverity.INFO, "system",
        "A market data farm is connecting", "log"),
    2104: IBKRErrorInfo(2104, IBKRErrorSeverity.INFO, "system",
        "Market data farm connection is OK", "log"),
    2105: IBKRErrorInfo(2105, IBKRErrorSeverity.WARNING, "system",
        "A historical data farm is connecting", "log"),
    2106: IBKRErrorInfo(2106, IBKRErrorSeverity.INFO, "system",
        "A historical data farm connection is OK", "log"),
    2158: IBKRErrorInfo(2158, IBKRErrorSeverity.INFO, "system",
        "Sec-def data farm connection is OK", "log"),
}

def classify_error(error_code: int, error_string: str) -> IBKRErrorInfo:
    """Classify an IBKR error code. Returns info with severity and recommended action.
    Unknown codes default to WARNING severity with 'log' action."""
    if error_code in IBKR_ERROR_MAP:
        return IBKR_ERROR_MAP[error_code]
    # Unknown error — default to warning
    return IBKRErrorInfo(
        code=error_code,
        severity=IBKRErrorSeverity.WARNING,
        category="unknown",
        description=error_string,
        action="log",
    )

def is_order_rejection(error_code: int) -> bool:
    """Returns True if this error code means an order was rejected."""
    return error_code in {110, 200, 201, 203}

def is_connection_error(error_code: int) -> bool:
    """Returns True if this error code indicates a connection problem."""
    return error_code in {502, 504, 1100}
```

**Tests:** 6 (classify known error, classify unknown error, is_order_rejection, is_connection_error, critical severity check, info severity suppression)

### Component 4: IBKRBroker Core

**File:** `argus/execution/ibkr_broker.py` (new, ~450 lines)

This is the main adapter. Implements the `Broker` ABC.

#### 4a: Constructor and Connection

```python
import asyncio
import logging
from datetime import datetime, timezone
from ib_async import IB, Stock, Contract, Order as IBOrder, MarketOrder, LimitOrder, \
    StopOrder, Trade, OrderStatus as IBOrderStatus

from argus.core.config import IBKRConfig
from argus.core.events import (
    EventBus, OrderFilledEvent, OrderCancelledEvent, OrderSubmittedEvent,
)
from argus.core.models import Order, OrderResult, BracketOrderResult, Position, AccountInfo, OrderStatus
from argus.execution.broker import Broker
from argus.execution.ibkr_contracts import IBKRContractResolver
from argus.execution.ibkr_errors import classify_error, is_connection_error, is_order_rejection
from argus.utils.ulid import generate_ulid

logger = logging.getLogger(__name__)


class IBKRBroker(Broker):
    """Production execution broker using Interactive Brokers via ib_async.
    
    Implements the Broker ABC for order submission, fill streaming, account queries,
    and position management. Uses native IBKR multi-leg bracket orders (DEC-093).
    
    All market data comes from Databento (DEC-082) — this adapter is execution-only.
    """

    def __init__(self, config: IBKRConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._ib = IB()
        self._connected = False
        self._reconnecting = False
        
        # Order ID mapping: ARGUS ULID ↔ IBKR integer orderId
        self._ulid_to_ibkr: dict[str, int] = {}
        self._ibkr_to_ulid: dict[int, str] = {}
        
        # Contract resolver
        self._contracts = IBKRContractResolver()
        
        # Last known positions (for reconnection verification)
        self._last_known_positions: list = []
        
        # Wire up ib_async events
        self._ib.orderStatusEvent += self._on_order_status
        self._ib.errorEvent += self._on_error
        self._ib.disconnectedEvent += self._on_disconnected
    
    # --- Connection Management ---
    
    async def connect(self) -> None:
        """Connect to IB Gateway. Blocks until connected and synced."""
        try:
            await self._ib.connectAsync(
                host=self._config.host,
                port=self._config.port,
                clientId=self._config.client_id,
                timeout=self._config.timeout_seconds,
                readonly=self._config.readonly,
                account=self._config.account or "",
            )
            self._connected = True
            self._last_known_positions = list(self._ib.positions())
            logger.info(
                f"Connected to IB Gateway at {self._config.host}:{self._config.port} "
                f"(clientId={self._config.client_id}, account={self._config.account})"
            )
        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect to IB Gateway: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Graceful disconnect from IB Gateway."""
        if self._ib.isConnected():
            self._ib.disconnect()
        self._connected = False
        logger.info("Disconnected from IB Gateway")
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._ib.isConnected()
```

**Tests (connection):** 8 (connect success, connect failure/timeout, disconnect, is_connected property, connection state tracking, reconnect on disconnect event, account parameter passthrough, clientId uniqueness)

#### 4b: Order Submission — `place_order()`

```python
    async def place_order(self, order: Order) -> OrderResult:
        """Submit a single order to IBKR. Maps ARGUS Order to ib_async Order."""
        if not self.is_connected:
            return OrderResult(order_id="", status="error", message="Not connected to IB Gateway")
        
        # Resolve contract
        contract = self._contracts.get_stock_contract(order.symbol)
        
        # Build ib_async order
        ib_order = self._build_ib_order(order)
        
        # Generate ULID, store orderRef for reconstruction
        ulid = generate_ulid()
        ib_order.orderRef = ulid  # Stored on IBKR side — enables reconstruction
        
        # Store mapping
        self._ulid_to_ibkr[ulid] = ib_order.orderId if ib_order.orderId else 0
        
        # Place order
        trade = self._ib.placeOrder(contract, ib_order)
        
        # Update mapping with actual orderId (assigned by ib_async)
        actual_id = trade.order.orderId
        self._ulid_to_ibkr[ulid] = actual_id
        self._ibkr_to_ulid[actual_id] = ulid
        
        logger.info(f"Order placed: {ulid} → IBKR #{actual_id} "
                     f"{order.side} {order.quantity} {order.symbol} {order.order_type}")
        
        return OrderResult(order_id=ulid, status="submitted", 
                          broker_order_id=str(actual_id))
    
    def _build_ib_order(self, order: Order) -> IBOrder:
        """Convert ARGUS Order model to ib_async Order object."""
        action = "BUY" if order.side.lower() == "buy" else "SELL"
        
        if order.order_type.lower() == "market":
            ib_order = MarketOrder(action, order.quantity)
        elif order.order_type.lower() == "limit":
            ib_order = LimitOrder(action, order.quantity, order.price)
        elif order.order_type.lower() == "stop":
            ib_order = StopOrder(action, order.quantity, order.price)
        elif order.order_type.lower() == "stop_limit":
            ib_order = IBOrder(
                action=action,
                totalQuantity=order.quantity,
                orderType="STP LMT",
                auxPrice=order.stop_price,    # trigger price
                lmtPrice=order.price,          # limit price
            )
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")
        
        # Common settings
        ib_order.tif = "DAY"          # Intraday strategies — DAY orders only
        ib_order.outsideRth = False   # No pre/post-market trading
        
        return ib_order
```

**Tests (order submission):** 10 (market order, limit order, stop order, stop-limit order, order type mapping, ULID↔IBKR ID mapping, orderRef set, not-connected error, invalid order type, buy/sell action mapping)

#### 4c: Bracket Order Submission — `place_bracket_order()` (Native IBKR — DEC-093)

```python
    async def place_bracket_order(self, entry: Order, stop: Order,
                                   targets: list[Order]) -> BracketOrderResult:
        """Submit a full bracket order to IBKR with native multi-leg support.
        
        IBKR brackets: parent (entry) + children (stop + targets) linked via parentId.
        All children are submitted atomically. If parent is cancelled, all children
        are auto-cancelled by IBKR.
        
        Args:
            entry: Entry order (market or limit)
            stop: Stop-loss order for total shares
            targets: List of take-profit orders [T1] or [T1, T2]
        
        Returns:
            BracketOrderResult with all order IDs (entry, stop, t1, optionally t2)
        """
        if not self.is_connected:
            return BracketOrderResult(status="error", message="Not connected")
        
        contract = self._contracts.get_stock_contract(entry.symbol)
        action = "BUY" if entry.side.lower() == "buy" else "SELL"
        exit_action = "SELL" if action == "BUY" else "BUY"
        
        # --- Build parent order (entry) ---
        parent = self._build_ib_order(entry)
        parent.transmit = False  # Don't transmit until last child
        
        # Generate ULIDs for all legs
        entry_ulid = generate_ulid()
        stop_ulid = generate_ulid()
        parent.orderRef = entry_ulid
        
        # Place parent first to get orderId
        parent_trade = self._ib.placeOrder(contract, parent)
        parent_id = parent_trade.order.orderId
        self._ulid_to_ibkr[entry_ulid] = parent_id
        self._ibkr_to_ulid[parent_id] = entry_ulid
        
        # --- Build stop-loss child ---
        stop_ib = StopOrder(exit_action, stop.quantity, stop.price)
        stop_ib.parentId = parent_id
        stop_ib.tif = "DAY"
        stop_ib.outsideRth = False
        stop_ib.orderRef = stop_ulid
        
        # Determine if stop is the last order (transmit=True) or not
        has_targets = len(targets) > 0
        stop_ib.transmit = not has_targets  # Transmit only if no targets follow
        
        stop_trade = self._ib.placeOrder(contract, stop_ib)
        stop_actual_id = stop_trade.order.orderId
        self._ulid_to_ibkr[stop_ulid] = stop_actual_id
        self._ibkr_to_ulid[stop_actual_id] = stop_ulid
        
        # --- Build target children (T1, optionally T2) ---
        target_ulids = []
        for i, target in enumerate(targets):
            t_ulid = generate_ulid()
            target_ulids.append(t_ulid)
            
            is_last = (i == len(targets) - 1)
            
            t_ib = LimitOrder(exit_action, target.quantity, target.price)
            t_ib.parentId = parent_id
            t_ib.tif = "DAY"
            t_ib.outsideRth = False
            t_ib.orderRef = t_ulid
            t_ib.transmit = is_last  # Last child transmits the entire bracket
            
            t_trade = self._ib.placeOrder(contract, t_ib)
            t_actual_id = t_trade.order.orderId
            self._ulid_to_ibkr[t_ulid] = t_actual_id
            self._ibkr_to_ulid[t_actual_id] = t_ulid
        
        logger.info(
            f"Bracket placed: entry={entry_ulid} (IBKR #{parent_id}), "
            f"stop={stop_ulid}, targets={target_ulids} — "
            f"{action} {entry.quantity} {entry.symbol}"
        )
        
        result = BracketOrderResult(
            status="submitted",
            entry_order_id=entry_ulid,
            stop_order_id=stop_ulid,
            target_order_ids=target_ulids,
        )
        return result
```

**Key implementation notes:**
- `transmit=False` on parent and intermediate children prevents partial submission
- `transmit=True` on the last child triggers atomic submission of the entire group
- `parentId` on all children links them — parent cancel cascades to all
- ULIDs stored in `orderRef` on every leg for reconstruction
- T1 gets `targets[0].quantity` shares, T2 gets `targets[1].quantity` shares
- Stop gets `stop.quantity` (total shares) — will need modification when T1 fills

**Tests (bracket orders):** 10 (bracket with T1 only, bracket with T1+T2, market entry bracket, limit entry bracket, parentId linkage verified, transmit flags correct, all ULIDs mapped, bracket cancel cascades, partial target list, empty targets list)

#### 4d: Fill Streaming — Event Handlers

```python
    def _on_order_status(self, trade: Trade) -> None:
        """Called by ib_async on order status changes. Bridges to ARGUS Event Bus.
        
        Note: This is called on the asyncio event loop (not a separate thread).
        We schedule the async event publishing as a task.
        """
        asyncio.ensure_future(self._handle_order_status(trade))
    
    async def _handle_order_status(self, trade: Trade) -> None:
        """Process order status update and publish to Event Bus."""
        ib_order_id = trade.order.orderId
        ulid = self._ibkr_to_ulid.get(ib_order_id)
        
        if not ulid:
            # Not our order — could be pre-existing from TWS, or external
            logger.debug(f"Ignoring status update for unknown IBKR order #{ib_order_id}")
            return
        
        status = trade.orderStatus.status
        
        if status == "Filled":
            # Get fill details
            avg_fill_price = trade.orderStatus.avgFillPrice
            filled_qty = trade.orderStatus.filled
            
            await self._event_bus.publish(OrderFilledEvent(
                order_id=ulid,
                fill_price=avg_fill_price,
                fill_quantity=int(filled_qty),
                timestamp=datetime.now(timezone.utc),
            ))
            logger.info(f"Order filled: {ulid} — {filled_qty} @ ${avg_fill_price:.2f}")
        
        elif status == "Cancelled":
            await self._event_bus.publish(OrderCancelledEvent(
                order_id=ulid,
                reason=f"Cancelled (IBKR status: {status})",
            ))
            logger.info(f"Order cancelled: {ulid}")
        
        elif status == "Inactive":
            # Inactive = rejected by IBKR (insufficient margin, invalid price, etc.)
            reason = f"Order rejected by IBKR: {trade.orderStatus.whyHeld or 'unknown reason'}"
            await self._event_bus.publish(OrderCancelledEvent(
                order_id=ulid,
                reason=reason,
            ))
            logger.warning(f"Order rejected: {ulid} — {reason}")
        
        elif status == "Submitted":
            await self._event_bus.publish(OrderSubmittedEvent(
                order_id=ulid,
                strategy_id="",  # Filled by Order Manager from context
                symbol=trade.contract.symbol,
                side=trade.order.action.lower(),
                quantity=int(trade.order.totalQuantity),
                order_type=self._map_ib_order_type(trade.order.orderType),
            ))
        
        elif status == "PreSubmitted":
            # Bracket children before parent fills — normal, just log
            logger.debug(f"Order pre-submitted: {ulid} (IBKR #{ib_order_id})")
        
        # PendingSubmit, PendingCancel — transient states, log only
        else:
            logger.debug(f"Order status: {ulid} → {status}")
    
    def _on_error(self, reqId: int, errorCode: int, errorString: str, 
                  contract: Contract = None) -> None:
        """Called by ib_async on error. Classify and handle."""
        error_info = classify_error(errorCode, errorString)
        
        if error_info.severity == IBKRErrorSeverity.CRITICAL:
            logger.critical(f"IBKR error {errorCode}: {errorString}")
            if is_connection_error(errorCode):
                # Connection errors trigger reconnection (handled by _on_disconnected)
                pass
        elif error_info.severity == IBKRErrorSeverity.WARNING:
            logger.warning(f"IBKR error {errorCode}: {errorString}")
            if is_order_rejection(errorCode) and reqId in self._ibkr_to_ulid:
                ulid = self._ibkr_to_ulid[reqId]
                asyncio.ensure_future(self._event_bus.publish(OrderCancelledEvent(
                    order_id=ulid,
                    reason=f"IBKR rejected: {errorString}",
                )))
        else:
            logger.debug(f"IBKR info {errorCode}: {errorString}")
    
    @staticmethod
    def _map_ib_order_type(ib_type: str) -> str:
        """Map IBKR order type string to ARGUS order type."""
        mapping = {
            "MKT": "market",
            "LMT": "limit",
            "STP": "stop",
            "STP LMT": "stop_limit",
        }
        return mapping.get(ib_type, ib_type.lower())
```

**Tests (fill streaming):** 12 (fill event published, partial fill handling, cancelled event, inactive/rejected event, submitted event, pre-submitted bracket child, unknown order ignored, error classification routing, critical error logging, order rejection via error event, multiple fills aggregation, fill price accuracy)

#### 4e: Cancel, Modify, Status

```python
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order by ARGUS ULID."""
        ib_order_id = self._ulid_to_ibkr.get(order_id)
        if ib_order_id is None:
            logger.warning(f"Cannot cancel unknown order: {order_id}")
            return False
        
        trade = self._find_trade_by_order_id(ib_order_id)
        if trade is None:
            logger.warning(f"Cannot find trade for IBKR order #{ib_order_id}")
            return False
        
        self._ib.cancelOrder(trade.order)
        logger.info(f"Cancel requested: {order_id} (IBKR #{ib_order_id})")
        return True
    
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify an existing order (price, quantity).
        
        ib_async pattern: modify the Trade.order object in-place, then re-place it.
        """
        ib_order_id = self._ulid_to_ibkr.get(order_id)
        if ib_order_id is None:
            return OrderResult(order_id=order_id, status="error", message="Unknown order")
        
        trade = self._find_trade_by_order_id(ib_order_id)
        if trade is None:
            return OrderResult(order_id=order_id, status="error", message="Trade not found")
        
        # Apply modifications
        if "price" in modifications:
            if trade.order.orderType == "STP":
                trade.order.auxPrice = modifications["price"]
            else:
                trade.order.lmtPrice = modifications["price"]
        
        if "quantity" in modifications:
            trade.order.totalQuantity = modifications["quantity"]
        
        # Re-place to transmit modification
        self._ib.placeOrder(trade.contract, trade.order)
        
        logger.info(f"Order modified: {order_id} — {modifications}")
        return OrderResult(order_id=order_id, status="modified")
    
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get current status of an order."""
        ib_order_id = self._ulid_to_ibkr.get(order_id)
        if ib_order_id is None:
            return OrderStatus(status="unknown")
        
        trade = self._find_trade_by_order_id(ib_order_id)
        if trade is None:
            return OrderStatus(status="unknown")
        
        return OrderStatus(
            status=trade.orderStatus.status.lower(),
            filled_quantity=int(trade.orderStatus.filled),
            remaining_quantity=int(trade.orderStatus.remaining),
            avg_fill_price=trade.orderStatus.avgFillPrice,
        )
    
    def _find_trade_by_order_id(self, ib_order_id: int) -> Trade | None:
        """Find a Trade object by IBKR order ID from ib_async's cache."""
        for trade in self._ib.trades():
            if trade.order.orderId == ib_order_id:
                return trade
        return None
```

**Tests (cancel/modify/status):** 6 (cancel existing order, cancel unknown, modify stop price, modify limit price, modify quantity, get order status)

#### 4f: Account Queries

```python
    async def get_positions(self) -> list[Position]:
        """Get current positions from IBKR (auto-synced cache)."""
        ib_positions = self._ib.positions()
        return [
            Position(
                symbol=p.contract.symbol,
                quantity=int(p.position),
                avg_cost=p.avgCost,
                market_value=p.position * p.avgCost,  # Approximate
                unrealized_pnl=0.0,  # Available via reqPnLSingle if needed
            )
            for p in ib_positions
            if p.position != 0
        ]
    
    async def get_account(self) -> AccountInfo:
        """Get account info from IBKR (auto-synced cache).
        
        ib_async keeps accountValues() updated automatically after connection.
        """
        values = {v.tag: float(v.value) for v in self._ib.accountValues()
                  if v.currency == "USD" and self._is_numeric(v.value)}
        
        return AccountInfo(
            equity=values.get("NetLiquidation", 0.0),
            cash=values.get("TotalCashValue", 0.0),
            buying_power=values.get("BuyingPower", 0.0),
            margin_used=values.get("MaintMarginReq", 0.0),
            day_trades_remaining=int(values.get("DayTradesRemaining", -1)),
        )
    
    @staticmethod
    def _is_numeric(value: str) -> bool:
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
```

**Tests (account queries):** 6 (get positions with holdings, get positions empty, get account info, buying power calculation, non-USD values filtered, day trades remaining)

#### 4g: Flatten All

```python
    async def flatten_all(self) -> list[OrderResult]:
        """Emergency: cancel all open orders, then close all positions.
        
        Order of operations:
        1. Cancel all open orders (prevents stops from interfering)
        2. Submit market orders to close all positions
        """
        results = []
        
        # Step 1: Cancel all open orders
        self._ib.reqGlobalCancel()
        logger.warning("Emergency flatten: all open orders cancelled")
        
        # Brief pause for cancellations to process
        await asyncio.sleep(0.5)
        
        # Step 2: Close all positions
        for pos in self._ib.positions():
            if pos.position == 0:
                continue
            
            action = "SELL" if pos.position > 0 else "BUY"
            quantity = abs(int(pos.position))
            
            close_order = MarketOrder(action, quantity)
            close_order.tif = "DAY"
            ulid = generate_ulid()
            close_order.orderRef = ulid
            
            trade = self._ib.placeOrder(pos.contract, close_order)
            
            self._ulid_to_ibkr[ulid] = trade.order.orderId
            self._ibkr_to_ulid[trade.order.orderId] = ulid
            
            results.append(OrderResult(
                order_id=ulid,
                status="submitted",
                message=f"Emergency close: {action} {quantity} {pos.contract.symbol}",
            ))
            logger.warning(f"Emergency close: {action} {quantity} {pos.contract.symbol}")
        
        return results
```

**Tests (flatten):** 4 (flatten with positions, flatten empty portfolio, flatten cancels pending first, flatten both long and short)

### Component 5: Reconnection Logic

```python
    def _on_disconnected(self) -> None:
        """Handle unexpected disconnection from IB Gateway."""
        self._connected = False
        if not self._reconnecting:
            logger.warning("IB Gateway disconnected — starting reconnection")
            asyncio.ensure_future(self._reconnect())
    
    async def _reconnect(self) -> None:
        """Reconnect to IB Gateway with exponential backoff.
        Verifies position consistency after reconnection."""
        self._reconnecting = True
        pre_positions = [
            (p.contract.symbol, int(p.position))
            for p in self._last_known_positions
        ]
        
        for attempt in range(self._config.reconnect_max_retries):
            delay = min(
                self._config.reconnect_base_delay_seconds * (2 ** attempt),
                self._config.reconnect_max_delay_seconds,
            )
            logger.info(f"Reconnection attempt {attempt + 1}/{self._config.reconnect_max_retries} "
                        f"in {delay:.1f}s")
            await asyncio.sleep(delay)
            
            try:
                await self.connect()
                
                # Verify positions match
                post_positions = [
                    (p.contract.symbol, int(p.position))
                    for p in self._ib.positions()
                ]
                if set(pre_positions) != set(post_positions):
                    logger.warning(
                        f"Position mismatch after reconnect! "
                        f"Before: {pre_positions}, After: {post_positions}"
                    )
                    # Continue anyway — HealthMonitor will reconcile
                
                self._reconnecting = False
                logger.info(f"Reconnected to IB Gateway (attempt {attempt + 1})")
                return
                
            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
        
        self._reconnecting = False
        logger.critical(
            f"Failed to reconnect after {self._config.reconnect_max_retries} attempts. "
            f"IB Gateway unreachable. Manual intervention required."
        )
        # TODO: Publish SystemAlertEvent when available (DEF-014)
```

**Tests (reconnection):** 6 (successful reconnect on first attempt, successful reconnect after failures, max retries exceeded, position verification pass, position mismatch warning, exponential backoff timing, no double-reconnect)

### Component 6: State Reconstruction

```python
    async def reconstruct_state(self) -> dict:
        """Rebuild internal state from IBKR after restart or reconnection.
        
        Recovery strategy:
        1. ib_async auto-fetches positions and orders on connectAsync()
        2. Scan open orders for orderRef field to recover ULID mappings
        3. Return positions and orders for Order Manager reconstruction
        """
        # ib_async has already fetched everything during connect()
        positions = self._ib.positions()
        open_trades = self._ib.openTrades()
        
        # Recover ULID mappings from orderRef
        recovered = 0
        for trade in open_trades:
            order_ref = trade.order.orderRef
            if order_ref and order_ref not in self._ulid_to_ibkr:
                ib_id = trade.order.orderId
                self._ulid_to_ibkr[order_ref] = ib_id
                self._ibkr_to_ulid[ib_id] = order_ref
                recovered += 1
        
        if recovered > 0:
            logger.info(f"Recovered {recovered} ULID mappings from IBKR orderRef")
        
        return {
            "positions": [self._convert_position(p) for p in positions if p.position != 0],
            "open_orders": [
                {
                    "order_id": self._ibkr_to_ulid.get(t.order.orderId, f"unknown_{t.order.orderId}"),
                    "symbol": t.contract.symbol,
                    "side": t.order.action.lower(),
                    "quantity": int(t.order.totalQuantity),
                    "order_type": self._map_ib_order_type(t.order.orderType),
                    "status": t.orderStatus.status.lower(),
                }
                for t in open_trades
            ],
        }
    
    def _convert_position(self, ib_pos) -> Position:
        """Convert ib_async position to ARGUS Position model."""
        return Position(
            symbol=ib_pos.contract.symbol,
            quantity=int(ib_pos.position),
            avg_cost=ib_pos.avgCost,
            market_value=abs(ib_pos.position * ib_pos.avgCost),
            unrealized_pnl=0.0,
        )
```

**Tests (reconstruction):** 5 (reconstruct with positions and orders, reconstruct empty state, ULID recovery from orderRef, unknown orders handled, reconstruction after reconnect)

### Component 7: Order Manager Changes (DEC-093)

**File:** `argus/execution/order_manager.py` (modify existing)

These changes enable the Order Manager to handle broker-side T2 limit orders from IBKR's native brackets. The Alpaca path (tick-monitored T2) is preserved.

#### 7a: ManagedPosition changes

```python
@dataclass
class ManagedPosition:
    # ... existing fields ...
    t2_order_id: str | None = None   # NEW: Set when broker supports native T2 (IBKR)
```

#### 7b: PendingManagedOrder changes

```python
@dataclass
class PendingManagedOrder:
    order_id: str
    symbol: str
    strategy_id: str
    order_type: str  # "entry", "stop", "t1", "t2", "flatten"  ← "t2" added
    signal: SignalEvent | None = None
```

#### 7c: on_approved() changes

```python
async def on_approved(self, event: OrderApprovedEvent) -> None:
    # ... existing logic to extract signal, build orders ...
    
    # Pass ALL targets to broker (not just T1)
    # AlpacaBroker will use targets[0] only; IBKRBroker handles full list
    targets = [t1_order]
    if t2_order is not None:
        targets.append(t2_order)
    
    result = await self._broker.place_bracket_order(entry_order, stop_order, targets)
    
    # Track T2 order ID if broker returned it
    t2_order_id = None
    if len(result.target_order_ids) > 1:
        t2_order_id = result.target_order_ids[1]
        # Register T2 as pending managed order
        self._pending_orders[t2_order_id] = PendingManagedOrder(
            order_id=t2_order_id,
            symbol=signal.symbol,
            strategy_id=signal.strategy_id,
            order_type="t2",
            signal=signal,
        )
```

#### 7d: on_fill() changes

```python
async def on_fill(self, event: OrderFilledEvent) -> None:
    pending = self._pending_orders.get(event.order_id)
    if not pending:
        return
    
    if pending.order_type == "t2":
        # T2 filled at broker (IBKR native bracket path)
        position = self._find_position_by_symbol(pending.symbol)
        if position:
            # Cancel remaining stop
            if position.stop_order_id:
                await self._broker.cancel_order(position.stop_order_id)
            
            # Update realized P&L
            pnl = (event.fill_price - position.entry_price) * event.fill_quantity
            position.realized_pnl += pnl
            position.shares_remaining -= event.fill_quantity
            
            # Close position if no shares remaining
            if position.shares_remaining <= 0:
                await self._close_position(position, event.fill_price, "t2_target")
    
    # ... existing entry, t1, stop, flatten handling unchanged ...
```

#### 7e: on_tick() changes

```python
async def on_tick(self, event: TickEvent) -> None:
    # ... existing tick handling ...
    
    for position in positions:
        # T2 check: only tick-monitor if no broker-side T2 order exists
        if position.t1_filled and position.t2_order_id is None:
            # Alpaca path: tick-monitored T2
            if event.price >= position.t2_price:
                await self._flatten_remaining(position)
        # If t2_order_id is set (IBKR path): T2 is handled by broker-side limit order
        # No tick monitoring needed — fills come through on_fill()
```

**Tests (Order Manager changes):** 8 (T2 fill closes position, T2 fill cancels stop, Alpaca path unchanged (no t2_order_id), IBKR path skips tick T2, bracket with T1+T2 targets, t2 pending order registered, stop fills cascade to T2 cancel, ManagedPosition t2_order_id field)

### Component 8: System Integration

**File:** `argus/main.py` (modify existing)

```python
# Phase 3: Initialize broker
if config.broker_source == BrokerSource.IBKR:
    from argus.execution.ibkr_broker import IBKRBroker
    broker = IBKRBroker(config.ibkr, event_bus)
    await broker.connect()
elif config.broker_source == BrokerSource.ALPACA:
    from argus.execution.alpaca_broker import AlpacaBroker
    broker = AlpacaBroker(config.alpaca, event_bus)
    await broker.connect()
else:
    from argus.execution.simulated_broker import SimulatedBroker
    broker = SimulatedBroker(config.simulated_broker, event_bus)
```

**File:** `config/brokers.yaml` — updated with `broker_source` field

**Tests (integration):** 3 (IBKR broker selected from config, Alpaca broker selected from config, simulated broker as default)

---

## 5. File Structure

```
New files:
  argus/execution/ibkr_broker.py         # Main adapter (~450 lines)
  argus/execution/ibkr_contracts.py      # Contract resolution (~60 lines)
  argus/execution/ibkr_errors.py         # Error code mapping (~120 lines)
  tests/execution/test_ibkr_broker.py    # Core broker tests (~700 lines)
  tests/execution/test_ibkr_contracts.py # Contract tests (~80 lines)
  tests/execution/test_ibkr_errors.py    # Error handling tests (~100 lines)
  tests/execution/test_order_manager_t2.py  # T2 bracket changes (~200 lines)

Modified files:
  argus/core/config.py                   # Add IBKRConfig, BrokerSource enum
  argus/execution/order_manager.py       # T2 handling for native brackets (DEC-093)
  argus/main.py                          # Add IBKR broker selection path
  config/brokers.yaml                    # Add ibkr section, broker_source field
  requirements.txt / pyproject.toml      # Add ib_async>=2.1.0
```

---

## 6. Test Summary

| Category | File | Count | Description |
|----------|------|-------|-------------|
| Config | test_ibkr_broker.py | 3 | IBKRConfig loading, validation, defaults |
| Connection | test_ibkr_broker.py | 8 | Connect, disconnect, reconnect, timeout, state |
| Contracts | test_ibkr_contracts.py | 4 | Stock resolution, qualification, cache |
| Order placement | test_ibkr_broker.py | 10 | Market/limit/stop/stop-limit, mapping, orderRef |
| Bracket orders | test_ibkr_broker.py | 10 | Native T1+T2, parentId, transmit flags, cascade |
| Fill streaming | test_ibkr_broker.py | 12 | Fill/cancel/reject events, partial fills, status |
| Cancel/modify | test_ibkr_broker.py | 6 | Cancel, modify stop/limit/quantity, not-found |
| Account queries | test_ibkr_broker.py | 6 | Positions, account info, buying power |
| Flatten | test_ibkr_broker.py | 4 | Flatten positions, cancel-then-close |
| Error handling | test_ibkr_errors.py | 6 | Classification, severity, connection/rejection |
| Reconnection | test_ibkr_broker.py | 6 | Backoff, max retries, position verification |
| Reconstruction | test_ibkr_broker.py | 5 | Positions, orders, ULID recovery from orderRef |
| Order Manager T2 | test_order_manager_t2.py | 8 | T2 fills, tick skip, backward compat, cascade |
| System integration | test_ibkr_broker.py | 3 | Broker selection, startup sequence |
| **Total** | | **~91** | |

---

## 7. Mocking Strategy

All tests mock `ib_async.IB` — no live Gateway connection needed.

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from ib_async import IB, Trade, Order as IBOrder, OrderStatus as IBOrderStatus, \
    Stock, Position as IBPosition, AccountValue

@pytest.fixture
def mock_ib():
    """Create a mock ib_async.IB instance with standard behavior."""
    ib = MagicMock(spec=IB)
    ib.isConnected.return_value = True
    ib.managedAccounts.return_value = ["U24619949"]
    ib.positions.return_value = []
    ib.openTrades.return_value = []
    ib.trades.return_value = []
    ib.accountValues.return_value = [
        AccountValue(tag="NetLiquidation", value="100000.0", currency="USD", account="U24619949"),
        AccountValue(tag="TotalCashValue", value="50000.0", currency="USD", account="U24619949"),
        AccountValue(tag="BuyingPower", value="200000.0", currency="USD", account="U24619949"),
    ]
    
    # Event subscriptions (aeventkit uses += operator)
    ib.orderStatusEvent = MagicMock()
    ib.errorEvent = MagicMock()
    ib.disconnectedEvent = MagicMock()
    ib.connectedEvent = MagicMock()
    ib.newOrderEvent = MagicMock()
    
    # connectAsync returns a coroutine
    ib.connectAsync = AsyncMock()
    
    # placeOrder returns a Trade object
    def make_trade(contract, order):
        trade = MagicMock(spec=Trade)
        trade.order = order
        trade.contract = contract
        trade.orderStatus = MagicMock(spec=IBOrderStatus)
        trade.orderStatus.status = "Submitted"
        trade.orderStatus.filled = 0
        trade.orderStatus.remaining = order.totalQuantity
        trade.orderStatus.avgFillPrice = 0.0
        trade.fills = []
        # Assign orderId if not set
        if not hasattr(order, '_mock_order_id'):
            order._mock_order_id = id(order) % 10000
            order.orderId = order._mock_order_id
        return trade
    
    ib.placeOrder = MagicMock(side_effect=make_trade)
    ib.cancelOrder = MagicMock()
    ib.reqGlobalCancel = MagicMock()
    
    return ib
```

---

## 8. Implementation Order (Claude Code Prompts)

### Prompt 1: Foundation
- Add `ib_async>=2.1.0` to dependencies
- Add `IBKRConfig` and `BrokerSource` enum to `argus/core/config.py`
- Add `ibkr` section to `config/brokers.yaml`
- Add `broker_source` and `ibkr` fields to `SystemConfig`
- Tests: config loading, defaults, validation
- Run tests, ruff clean

### Prompt 2: Contracts + Errors
- Create `argus/execution/ibkr_contracts.py` (IBKRContractResolver)
- Create `argus/execution/ibkr_errors.py` (error map + classification)
- Tests for both modules
- Run tests, ruff clean

### Prompt 3: IBKRBroker Core — Connection
- Create `argus/execution/ibkr_broker.py` with:
  - Constructor, ib_async event wiring
  - `connect()`, `disconnect()`, `is_connected`
  - Order ID mapping infrastructure
- Tests: connection lifecycle, state tracking
- Run tests, ruff clean

### Prompt 4: Order Submission
- Add `place_order()` with all order types (market, limit, stop, stop-limit)
- Add `_build_ib_order()` helper
- ULID generation and orderRef assignment
- Tests: all order types, mapping, orderRef
- Run tests, ruff clean

### Prompt 5: Native Bracket Orders (DEC-093)
- Add `place_bracket_order()` with native IBKR multi-leg support
- Parent + stop + T1 + T2 with parentId linkage
- Transmit flag management (False on all but last child)
- Tests: T1-only, T1+T2, market/limit entry, parentId verification, transmit flags
- Run tests, ruff clean

### Prompt 6: Fill Streaming
- Add `_on_order_status()` event handler
- Add `_handle_order_status()` async bridge
- Publish OrderFilledEvent, OrderCancelledEvent, OrderSubmittedEvent
- Handle all IBKR statuses: Filled, Cancelled, Inactive, Submitted, PreSubmitted
- Tests: all status transitions, partial fills, unknown orders
- Run tests, ruff clean

### Prompt 7: Cancel, Modify, Account, Flatten
- Add `cancel_order()`, `modify_order()`, `get_order_status()`
- Add `get_positions()`, `get_account()`
- Add `flatten_all()` (global cancel + position close)
- Tests for all
- Run tests, ruff clean

### Prompt 8: Error Handling + Reconnection
- Add `_on_error()` event handler with error classification
- Add `_on_disconnected()` and `_reconnect()` with exponential backoff
- Position verification after reconnect
- Tests: error routing, reconnection scenarios, position mismatch
- Run tests, ruff clean

### Prompt 9: State Reconstruction + Order Manager Changes
- Add `reconstruct_state()` with ULID recovery from orderRef
- Modify `ManagedPosition` (add `t2_order_id`)
- Modify `PendingManagedOrder` (add `"t2"` type)
- Modify `on_approved()` to pass full targets list
- Modify `on_fill()` to handle T2 fills
- Modify `on_tick()` to skip T2 monitoring when t2_order_id is set
- Tests: reconstruction, all Order Manager T2 scenarios
- Run tests, ruff clean

### Prompt 10: System Integration + Final Sweep
- Update `argus/main.py` broker selection (BrokerSource branching)
- Final test sweep — ensure all ~765+ tests pass
- Ruff clean
- Update `__init__.py` exports if needed
- Integration test: full startup with IBKR broker selected

---

## 9. Decisions to Record After Sprint

After Sprint 13 completes, these entries need to be added to the Decision Log:

- **DEC-093** — Native IBKR bracket orders (Option B). Full multi-leg brackets with T1+T2 submitted atomically.
- **DEC-094** — BrokerSource enum for provider selection. Mirrors DataSource pattern (DEC-090).
- Any additional decisions that arise during implementation.

## 10. Risk Items to Monitor

- **RSK-022 (IB Gateway nightly reset):** Validate reconnection logic handles the 11:45 PM – 12:45 AM ET window cleanly. This sprint builds the logic; paper trading validates it.
- **ASM (ib_async stability):** Confirm `ib_async>=2.1.0` works reliably for order management. Flag any issues during testing.
- **ASM (IBKR paper fill simulation):** Paper fills may differ from live SmartRouting. Acceptable for validation, noted for comparison once live.

---

## 11. What This Sprint Unblocks

1. **Paper trading migration to IBKR** — Validation Track advances from "system stability only" (Alpaca IEX) to "signal accuracy + execution quality" (Databento + IBKR)
2. **Path to live trading** — IBKRBroker is the production broker. No further adapter work needed.
3. **Native bracket safety** — Broker-side T2 orders survive ARGUS crashes. Parent cancel cascades.
4. **Multi-asset foundation** — IBKRContractResolver extends to options/futures/forex without IBKRBroker changes.

---

## 12. AlpacaBroker Backward Compatibility Notes

The AlpacaBroker continues to work unchanged:
- `place_bracket_order()` receives `targets` list but Alpaca only uses `targets[0]` (its existing behavior)
- `BracketOrderResult.target_order_ids` returns `[t1_ulid]` (single element) — Order Manager checks length
- Order Manager T2 tick-monitoring activates when `t2_order_id is None` (Alpaca path)
- No changes to AlpacaBroker code required

---

*End of Sprint 13 Spec v1.0*
