# ARGUS — Sprint 2 Implementation Spec

> **Date:** February 15, 2026
> **Scope:** Broker Abstraction + SimulatedBroker + Risk Manager (Account Level)
> **Prerequisite:** Sprint 1 complete (52 tests passing, ruff clean)
> **Deliverable:** Hand this to Claude Code. Build in order. Do not skip ahead.

---

## Overview

Sprint 2 builds two major components:

1. **Broker Abstraction Layer** — The `Broker` ABC, `SimulatedBroker` (deterministic test double), and `BrokerRouter` (order routing).
2. **Risk Manager (Account Level)** — The three-level gate (Phase 1 implements account-level only). Evaluates every signal before it reaches the broker.

At the end of Sprint 2, the following end-to-end flow works:

```
SignalEvent → RiskManager.evaluate_signal() → OrderApprovedEvent/OrderRejectedEvent
  → SimulatedBroker.place_order() → OrderFilledEvent
  → TradeLogger.log_trade()
```

---

## Micro-Decisions (Settled — Do Not Relitigate)

These were discussed and approved before this spec was written:

| ID | Decision |
|----|----------|
| MD-1 | Weekly loss limit uses **calendar week** (Monday–Friday), not rolling 5-day. Resets each Monday. |
| MD-2 | Circuit breaker is **internally enforced** by Risk Manager. Sets `_circuit_breaker_active` flag, auto-rejects all subsequent signals until `reset_daily_state()`. |
| MD-3 | SimulatedBroker has a **`simulate_price_update(symbol, price)`** method for testing bracket order fills (stop/target triggers). Testing infrastructure only. |
| MD-4 | PDT $25K threshold goes in **config** (`risk_limits.yaml` → `pdt.threshold_balance: 25000`). Regulatory value, but respects the no-hardcode rule. |
| MD-5 | Risk Manager **queries the Broker** for account state and positions (source of truth). Maintains in-memory tracking only for daily/weekly realized P&L and PDT day-trade counts, updated via EventBus subscriptions to `PositionClosedEvent`. Reconstructs from TradeLogger on startup. |

---

## File Creation Order

Build these files in this exact sequence. Each file may depend on the ones before it.

```
1. config/risk_limits.yaml              (UPDATE — add pdt.threshold_balance)
2. argus/models/trading.py              (UPDATE — add OrderResult, BracketOrderResult, AccountInfo, OrderStatus)
3. argus/execution/__init__.py          (NEW — empty)
4. argus/execution/broker.py            (NEW — Broker ABC)
5. argus/execution/simulated_broker.py  (NEW — SimulatedBroker)
6. argus/execution/broker_router.py     (NEW — BrokerRouter)
7. argus/core/risk_manager.py           (NEW — RiskManager)
8. tests/execution/__init__.py          (NEW — empty)
9. tests/execution/test_broker.py       (NEW — SimulatedBroker tests)
10. tests/execution/test_broker_router.py (NEW — BrokerRouter tests)
11. tests/core/test_risk_manager.py      (NEW — Risk Manager tests)
12. tests/test_integration_sprint2.py    (NEW — end-to-end flow test)
```

---

## Step 1: Config Update

### File: `config/risk_limits.yaml`

Add `threshold_balance` to the `pdt` section:

```yaml
account:
  daily_loss_limit_pct: 0.03
  weekly_loss_limit_pct: 0.05
  cash_reserve_pct: 0.20
  max_concurrent_positions: 10
  emergency_shutdown_enabled: true

cross_strategy:
  max_single_stock_pct: 0.05
  max_single_sector_pct: 0.15
  duplicate_stock_policy: "priority_by_win_rate"

pdt:
  enabled: true
  account_type: "margin"
  threshold_balance: 25000  # FINRA regulatory minimum for unlimited day trading
```

### File: `argus/core/config.py`

Add `threshold_balance` to the existing `PDTConfig` model:

```python
class PDTConfig(BaseModel):
    enabled: bool = True
    account_type: str = "margin"  # "margin" or "cash"
    threshold_balance: float = 25000.0  # FINRA PDT threshold
```

No other config changes needed.

---

## Step 2: Model Updates

### File: `argus/models/trading.py`

Add these new models alongside the existing ones. Do NOT modify existing models — only add new ones.

```python
from enum import Enum

class OrderStatus(str, Enum):
    """Status of an order in its lifecycle."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass(frozen=True)
class OrderResult:
    """Result of a single order submission.

    Attributes:
        order_id: ULID assigned to this order.
        status: Current status after submission.
        filled_qty: Number of shares filled (0 if pending/rejected).
        filled_avg_price: Average fill price (0.0 if not filled).
        message: Human-readable status message or rejection reason.
    """
    order_id: str
    status: OrderStatus
    filled_qty: int
    filled_avg_price: float
    message: str = ""


@dataclass(frozen=True)
class BracketOrderResult:
    """Result of a bracket order submission (entry + stop + targets).

    Attributes:
        entry: Result for the entry order.
        stop: Result for the stop-loss order.
        targets: Results for each profit target order.
    """
    entry: OrderResult
    stop: OrderResult
    targets: list[OrderResult]


@dataclass(frozen=True)
class AccountInfo:
    """Snapshot of the brokerage account state.

    Attributes:
        equity: Total account equity (cash + positions value).
        cash: Available cash balance.
        buying_power: Available buying power for new orders.
        positions_value: Total value of open positions.
        daily_pnl: Realized P&L for today.
    """
    equity: float
    cash: float
    buying_power: float
    positions_value: float = 0.0
    daily_pnl: float = 0.0
```

**Important:** `OrderStatus` is an enum used by the broker layer. This is distinct from trade status tracked by the TradeLogger. The broker reports `OrderStatus`; the TradeLogger records the final outcome. Keep them separate.

---

## Step 3: Broker ABC

### File: `argus/execution/__init__.py`

Empty file.

### File: `argus/execution/broker.py`

```python
"""Broker abstraction layer.

All broker implementations must implement the Broker ABC. Orders are routed
through this interface — no component should ever call a broker SDK directly.
"""

from abc import ABC, abstractmethod

from argus.models.trading import (
    Order,
    Position,
    OrderResult,
    BracketOrderResult,
    AccountInfo,
    OrderStatus,
)


class Broker(ABC):
    """Abstract base class for all broker implementations.

    Implementations:
        - SimulatedBroker: Deterministic test double for backtesting and testing.
        - AlpacaBroker: Live/paper trading via Alpaca API (Sprint 4).
        - IBKRBroker: Interactive Brokers adapter (Phase 3+).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the broker.

        Called once at system startup. Implementations should verify
        credentials and connectivity.

        Raises:
            ConnectionError: If the broker cannot be reached.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Cleanly disconnect from the broker.

        Called at system shutdown. Implementations should close WebSocket
        connections, cancel pending heartbeats, etc.
        """

    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """Submit a single order to the broker.

        Args:
            order: The order to place (market, limit, stop, etc.).

        Returns:
            OrderResult with fill information or rejection reason.
        """

    @abstractmethod
    async def place_bracket_order(
        self,
        entry: Order,
        stop: Order,
        targets: list[Order],
    ) -> BracketOrderResult:
        """Submit a bracket order (entry + stop-loss + profit targets).

        The stop and target orders become active only after the entry fills.
        If the entry is rejected, stop and targets are not submitted.

        Args:
            entry: The entry order.
            stop: The stop-loss order (activated on entry fill).
            targets: Profit target orders (activated on entry fill).

        Returns:
            BracketOrderResult with results for all component orders.
        """

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending or partially filled order.

        Args:
            order_id: The ID of the order to cancel.

        Returns:
            True if the order was successfully cancelled, False otherwise.
        """

    @abstractmethod
    async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:
        """Modify a pending order (price, quantity, etc.).

        Args:
            order_id: The ID of the order to modify.
            modifications: Dict of field names to new values.

        Returns:
            OrderResult reflecting the modified order state.
        """

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Get all currently open positions.

        Returns:
            List of open Position objects. Empty list if no positions.
        """

    @abstractmethod
    async def get_account(self) -> AccountInfo:
        """Get current account information.

        Returns:
            AccountInfo snapshot with equity, cash, buying power.
        """

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus:
        """Get the current status of a specific order.

        Args:
            order_id: The ID of the order to check.

        Returns:
            Current OrderStatus.

        Raises:
            KeyError: If the order_id is not found.
        """

    @abstractmethod
    async def flatten_all(self) -> list[OrderResult]:
        """Emergency: close all open positions at market price.

        This is the nuclear option. Used by circuit breakers and manual
        emergency shutdown. Cancels all pending orders first, then
        submits market orders to close every open position.

        Returns:
            List of OrderResults for each closing order.
        """
```

---

## Step 4: SimulatedBroker

### File: `argus/execution/simulated_broker.py`

This is a deterministic test double. It fills orders immediately at specified prices, tracks positions and account state internally, and supports bracket order simulation.

```python
"""Simulated broker for testing and backtesting.

Fills orders deterministically. Tracks positions and account state internally.
Supports configurable slippage and bracket order simulation.

Usage:
    broker = SimulatedBroker(initial_cash=50000.0)
    await broker.connect()
    result = await broker.place_order(order)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from argus.core.ids import generate_ulid
from argus.execution.broker import Broker
from argus.models.trading import (
    AccountInfo,
    BracketOrderResult,
    Order,
    OrderResult,
    OrderStatus,
    Position,
)

logger = logging.getLogger(__name__)


@dataclass
class SimulatedSlippage:
    """Slippage configuration for the simulated broker.

    Attributes:
        mode: "none", "fixed", or "random".
        fixed_amount: Fixed slippage per share (used when mode="fixed").
        random_max: Maximum random slippage per share (used when mode="random").
    """
    mode: str = "none"  # "none", "fixed", "random"
    fixed_amount: float = 0.0
    random_max: float = 0.0


@dataclass
class PendingBracketOrder:
    """A stop or target order waiting to be triggered by price movement.

    Attributes:
        order_id: ULID for this pending order.
        symbol: The stock symbol.
        side: "buy" or "sell".
        quantity: Number of shares.
        trigger_price: Price at which this order triggers.
        order_type: "stop" or "limit" (determines trigger direction).
        parent_position_symbol: Symbol of the associated position.
    """
    order_id: str
    symbol: str
    side: str
    quantity: int
    trigger_price: float
    order_type: str  # "stop" or "limit"
    parent_position_symbol: str
```

**Class: `SimulatedBroker(Broker)`**

Constructor parameters:
- `initial_cash: float = 100_000.0` — Starting cash balance.
- `slippage: SimulatedSlippage = SimulatedSlippage()` — Slippage config.

Internal state (private attributes, not constructor params):
- `_cash: float` — Current cash balance. Initialized from `initial_cash`.
- `_positions: dict[str, Position]` — Open positions keyed by symbol.
- `_orders: dict[str, OrderResult]` — All submitted orders keyed by order_id.
- `_pending_brackets: list[PendingBracketOrder]` — Stop/target orders waiting for price triggers.
- `_connected: bool` — Whether `connect()` has been called.

**Method implementations:**

`async def connect(self) -> None:`
- Set `_connected = True`. Log connection.

`async def disconnect(self) -> None:`
- Set `_connected = False`. Log disconnection.

`async def place_order(self, order: Order) -> OrderResult:`
- Validate `_connected` is True (raise `RuntimeError` if not).
- Generate order_id via `generate_ulid()`.
- Calculate fill price: `order.price` + slippage (if configured).
  - For slippage: buy orders get WORSE price (add slippage), sell orders get BETTER price (subtract slippage). If `mode == "fixed"`, add/subtract `fixed_amount`. If `mode == "random"`, add/subtract `random.uniform(0, random_max)`.
- Calculate cost: `fill_price * order.quantity`.
- **Buying power check:** If buy order and `cost > _cash`, return `OrderResult(status=REJECTED, message="Insufficient buying power")`.
- If buy order: deduct `cost` from `_cash`. Create or update `Position` in `_positions`. Store `OrderResult(status=FILLED)`.
- If sell order: verify position exists and has sufficient shares. Add `fill_price * order.quantity` to `_cash`. Reduce position shares. If position shares reach 0, remove from `_positions`. Store `OrderResult(status=FILLED)`.
- Return the `OrderResult`.

`async def place_bracket_order(self, entry: Order, stop: Order, targets: list[Order]) -> BracketOrderResult:`
- Place the entry order via `self.place_order(entry)`.
- If entry is rejected, return `BracketOrderResult` with rejected entry and no stop/targets submitted.
- If entry fills: register stop as a `PendingBracketOrder` with `order_type="stop"`. Register each target as a `PendingBracketOrder` with `order_type="limit"`. Assign ULIDs to each. Return `BracketOrderResult` with entry filled, stop/targets as PENDING.

`async def cancel_order(self, order_id: str) -> bool:`
- Check if `order_id` is in `_pending_brackets`. If yes, remove it and return `True`.
- Check if `order_id` is in `_orders`. If found and status is PENDING, mark as CANCELLED and return `True`.
- Return `False` otherwise.

`async def modify_order(self, order_id: str, modifications: dict) -> OrderResult:`
- Find the order in `_pending_brackets`. Apply modifications (e.g., `trigger_price`, `quantity`).
- Return updated `OrderResult(status=PENDING)`.
- Raise `KeyError` if order_id not found.

`async def get_positions(self) -> list[Position]:`
- Return `list(self._positions.values())`.

`async def get_account(self) -> AccountInfo:`
- Calculate `positions_value`: sum of `position.current_price * position.shares` for all positions.
- `equity = _cash + positions_value`.
- `buying_power = _cash` (simplified for V1 — no margin).
- Return `AccountInfo(equity=equity, cash=_cash, buying_power=_cash, positions_value=positions_value)`.

`async def get_order_status(self, order_id: str) -> OrderStatus:`
- Look up in `_orders`. If found, return its status.
- Look up in `_pending_brackets`. If found, return `OrderStatus.PENDING`.
- Raise `KeyError` if not found.

`async def flatten_all(self) -> list[OrderResult]:`
- Cancel all pending bracket orders.
- For each open position: create a market sell order for the full quantity. Use the position's `current_price` as the fill price.
- Place each sell order via `self.place_order()`.
- Return list of `OrderResult` for each closing order.

**Testing infrastructure method (not on the ABC):**

`async def simulate_price_update(self, symbol: str, price: float) -> list[OrderResult]:`
- Update `current_price` on any position for this symbol.
- Check all `_pending_brackets` for this symbol:
  - **Stop orders** (`order_type == "stop"`): If the position is long and `price <= trigger_price`, trigger the stop. Create and execute a sell market order at `price`.
  - **Limit/target orders** (`order_type == "limit"`): If the position is long and `price >= trigger_price`, trigger the target. Create and execute a sell market order at `price`.
- When a bracket leg triggers: remove it from `_pending_brackets`. Also cancel any remaining bracket orders for the same `parent_position_symbol` if the entire position is now closed (i.e., if stop triggers, cancel targets; if final target triggers, cancel stop).
- Return list of `OrderResult` for any orders that triggered.

---

## Step 5: BrokerRouter

### File: `argus/execution/broker_router.py`

```python
"""Routes orders to the correct broker based on asset class configuration.

V1: Everything routes to the single configured broker. The router exists
to establish the pattern for multi-broker routing when IBKR is added.
"""

from __future__ import annotations

import logging

from argus.core.config import BrokerConfig
from argus.execution.broker import Broker

logger = logging.getLogger(__name__)


class BrokerRouter:
    """Routes orders to the appropriate broker based on asset class.

    In V1, all orders route to the primary broker. The routing logic
    exists to make multi-broker support a config change, not a code change.

    Args:
        config: Broker configuration from YAML.
        brokers: Dict mapping broker name to Broker instance.
    """

    def __init__(self, config: BrokerConfig, brokers: dict[str, Broker]) -> None:
        self._config = config
        self._brokers = brokers
        self._primary = config.primary

        if self._primary not in self._brokers:
            raise ValueError(
                f"Primary broker '{self._primary}' not found in registered brokers: "
                f"{list(self._brokers.keys())}"
            )

    def route(self, asset_class: str = "us_stocks") -> Broker:
        """Return the broker instance for the given asset class.

        Args:
            asset_class: The asset class of the order (e.g., "us_stocks", "crypto").

        Returns:
            The Broker instance that should handle this order.

        Raises:
            ValueError: If no broker is configured for the asset class.
        """
        # V1: everything routes to primary. Log for future routing visibility.
        broker = self._brokers.get(self._primary)
        if broker is None:
            raise ValueError(f"No broker registered for primary '{self._primary}'")

        logger.debug(
            "Routing %s order to broker '%s'",
            asset_class,
            self._primary,
        )
        return broker

    @property
    def primary_broker(self) -> Broker:
        """Direct access to the primary broker instance."""
        return self._brokers[self._primary]
```

---

## Step 6: Risk Manager (Account Level)

### File: `argus/core/risk_manager.py`

This is the most complex component in Sprint 2. Read carefully.

```python
"""Risk Manager — Three-level gate for all trade signals.

Phase 1 implements account-level checks only. Strategy-level checks are
handled inside strategies (Sprint 3). Cross-strategy checks require
multiple strategies (Phase 4).

Every SignalEvent must pass through evaluate_signal() before reaching
the broker. No exceptions. No shortcuts.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from argus.core.config import RiskConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    CircuitBreakerEvent,
    OrderApprovedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    SignalEvent,
)
from argus.execution.broker import Broker

logger = logging.getLogger(__name__)
```

**Data structures:**

```python
@dataclass
class PDTTracker:
    """Tracks Pattern Day Trading rule compliance.

    Maintains a rolling window of day trade timestamps. A day trade is
    any round-trip (buy + sell) in the same stock on the same day.

    Attributes:
        day_trades: Deque of dates when day trades occurred.
        account_type: "margin" or "cash".
        threshold_balance: FINRA PDT threshold (default $25,000).
    """
    day_trades: deque[date] = field(default_factory=deque)
    account_type: str = "margin"
    threshold_balance: float = 25000.0

    def record_day_trade(self, trade_date: date) -> None:
        """Record a day trade on the given date."""
        self.day_trades.append(trade_date)
        self._prune(trade_date)

    def day_trades_remaining(self, current_date: date, account_equity: float) -> int:
        """Return how many day trades are available.

        Args:
            current_date: Today's date.
            account_equity: Current account equity.

        Returns:
            Number of day trades remaining. Returns 999 if PDT doesn't apply
            (cash account or equity >= threshold).
        """
        if self.account_type == "cash":
            return 999  # PDT doesn't apply to cash accounts
        if account_equity >= self.threshold_balance:
            return 999  # Above threshold, unlimited day trades

        self._prune(current_date)
        used = len(self.day_trades)
        return max(0, 3 - used)

    def _prune(self, current_date: date) -> None:
        """Remove day trades older than 5 business days."""
        cutoff = self._business_days_ago(current_date, 5)
        while self.day_trades and self.day_trades[0] < cutoff:
            self.day_trades.popleft()

    @staticmethod
    def _business_days_ago(from_date: date, n: int) -> date:
        """Calculate the date N business days before from_date."""
        current = from_date
        days_counted = 0
        while days_counted < n:
            current -= timedelta(days=1)
            if current.weekday() < 5:  # Monday=0, Friday=4
                days_counted += 1
        return current


@dataclass
class IntegrityReport:
    """Result of a daily integrity check.

    Attributes:
        timestamp: When the check was performed.
        positions_checked: Number of positions verified.
        issues: List of issue descriptions. Empty if all checks pass.
        passed: Whether all checks passed.
    """
    timestamp: datetime
    positions_checked: int
    issues: list[str]
    passed: bool
```

**Class: `RiskManager`**

Constructor parameters:
- `config: RiskConfig` — The full risk configuration.
- `broker: Broker` — The broker to query for account state and positions.
- `event_bus: EventBus` — For publishing CircuitBreakerEvent and subscribing to PositionClosedEvent.

Internal state:
- `_config: RiskConfig`
- `_broker: Broker`
- `_event_bus: EventBus`
- `_daily_realized_pnl: float` — Accumulated realized P&L for today. Updated via PositionClosedEvent subscription.
- `_weekly_realized_pnl: float` — Accumulated realized P&L for the calendar week.
- `_current_week_start: date` — Monday of the current week. Used to detect week rollover.
- `_circuit_breaker_active: bool` — Once True, all signals rejected until `reset_daily_state()`.
- `_pdt_tracker: PDTTracker` — Tracks day trade count.
- `_trades_today: int` — Count of trades executed today (for informational/logging purposes).

**Initialization:**

```python
async def initialize(self) -> None:
    """Initialize the Risk Manager.

    Subscribes to PositionClosedEvent on the EventBus to track realized P&L.
    Must be called after EventBus is available.
    """
    await self._event_bus.subscribe(PositionClosedEvent, self._on_position_closed)
    logger.info("Risk Manager initialized. Config: daily_limit=%.1f%%, weekly_limit=%.1f%%",
                self._config.account.daily_loss_limit_pct * 100,
                self._config.account.weekly_loss_limit_pct * 100)
```

**Core method — `evaluate_signal`:**

```python
async def evaluate_signal(self, signal: SignalEvent) -> OrderApprovedEvent | OrderRejectedEvent:
    """Evaluate a trade signal against account-level risk limits.

    Checks performed in order (fail-fast):
    1. Circuit breaker active? → Reject
    2. Daily loss limit breached? → Reject
    3. Weekly loss limit breached? → Reject
    4. Max concurrent positions exceeded? → Reject
    5. Cash reserve enforcement → Reject or modify share count
    6. Buying power check → Reject or modify share count
    7. PDT check (margin accounts under threshold) → Reject

    If share count must be reduced (steps 5-6), check the 0.25R floor:
    if reduced position potential profit < 0.25R, reject entirely.

    Args:
        signal: The SignalEvent to evaluate.

    Returns:
        OrderApprovedEvent (possibly with modifications) or OrderRejectedEvent.
    """
```

**Implementation logic for `evaluate_signal`:**

1. **Circuit breaker check:**
   - If `_circuit_breaker_active` is True, reject with reason `"Circuit breaker active — all trading halted for the day"`.

2. **Daily loss limit check:**
   - Get account info from broker: `account = await self._broker.get_account()`.
   - Calculate limit: `daily_limit = account.equity * self._config.account.daily_loss_limit_pct`.
   - If `abs(self._daily_realized_pnl) >= daily_limit` AND `_daily_realized_pnl < 0`, reject with reason `"Daily loss limit reached ({pnl:.2f} of {limit:.2f})"`.
   - Also trigger circuit breaker: set `_circuit_breaker_active = True`, publish `CircuitBreakerEvent(level="account", reason="Daily loss limit reached", strategies_affected=[signal.strategy_id])` to the EventBus.

3. **Weekly loss limit check:**
   - Calculate limit: `weekly_limit = account.equity * self._config.account.weekly_loss_limit_pct`.
   - If `abs(self._weekly_realized_pnl) >= weekly_limit` AND `_weekly_realized_pnl < 0`, reject with reason `"Weekly loss limit reached"`.

4. **Max concurrent positions check:**
   - Get positions from broker: `positions = await self._broker.get_positions()`.
   - If `len(positions) >= self._config.account.max_concurrent_positions`, reject with reason `"Max concurrent positions ({max}) reached"`.

5. **Cash reserve enforcement:**
   - Calculate required reserve: `reserve = account.equity * self._config.account.cash_reserve_pct`.
   - Calculate available for trading: `available = account.cash - reserve`.
   - Calculate order cost: `cost = signal.entry_price * signal.share_count`.
   - If `cost > available` AND `available > 0`:
     - Calculate reduced shares: `reduced = int(available / signal.entry_price)`.
     - Check 0.25R floor (see step below).
   - If `available <= 0`, reject with reason `"Cash reserve would be violated"`.

6. **Buying power check:**
   - If `cost > account.buying_power` (and not already reduced in step 5):
     - Calculate reduced shares: `reduced = int(account.buying_power / signal.entry_price)`.
     - Check 0.25R floor.

7. **0.25R floor check** (applied whenever share count is reduced):
   - Calculate R (risk per share): `r_per_share = abs(signal.entry_price - signal.stop_price)`.
   - Calculate original R amount: `original_r = r_per_share * signal.share_count`.
   - Calculate reduced position potential profit at T1: `potential = reduced * r_per_share * signal.target_prices[0]` (or estimate using entry-stop distance as 1R).
     - Simpler formulation: If `reduced * r_per_share < 0.25 * original_r`, reject.
     - Even simpler: If `reduced < max(1, int(signal.share_count * 0.25))`, reject.
   - Actually, the cleanest interpretation of "0.25R potential profit" from DEC-027: the reduced position must risk at least 0.25R where R is the risk-per-share times the ORIGINAL share count. So: `reduced_risk = reduced * r_per_share`. If `reduced_risk < 0.25 * (signal.share_count * r_per_share)`, the trade is too small to matter. Reject with reason `"Position reduced below 0.25R minimum — not worth taking"`.

   **Clarification on 0.25R floor:** R = `signal.share_count * abs(signal.entry_price - signal.stop_price)`. This is the total dollar risk of the original signal. If reducing shares causes the new total dollar risk to fall below 25% of the original R, reject. This prevents taking tiny positions that won't move the needle.

8. **PDT check:**
   - If `self._pdt_tracker.day_trades_remaining(today, account.equity) <= 0`:
     - Reject with reason `"PDT limit reached — no day trades remaining in rolling 5-day window"`.
   - Note: The PDT check determines whether the trader CAN take a new intraday trade. The actual day trade is recorded when the position CLOSES (same-day round-trip), handled by `_on_position_closed`.

9. **Approve (with or without modifications):**
   - If share count was reduced in steps 5/6 and passed the 0.25R floor:
     - Return `OrderApprovedEvent(signal_event=signal, modifications={"share_count": reduced, "reason": "Reduced from {original} to {reduced} shares — [cash reserve/buying power] constraint"})`.
   - If no modifications needed:
     - Return `OrderApprovedEvent(signal_event=signal, modifications=None)`.

**EventBus handler:**

```python
async def _on_position_closed(self, event: PositionClosedEvent) -> None:
    """Track realized P&L and PDT day trades from position close events.

    Args:
        event: The PositionClosedEvent from the EventBus.
    """
    self._daily_realized_pnl += event.realized_pnl
    self._weekly_realized_pnl += event.realized_pnl
    self._trades_today += 1

    # Check if this was a day trade (opened and closed same day)
    # A day trade = position opened and closed on the same calendar day
    if event.entry_time and event.exit_time:
        entry_date = event.entry_time.date() if isinstance(event.entry_time, datetime) else event.entry_time
        exit_date = event.exit_time.date() if isinstance(event.exit_time, datetime) else event.exit_time
        if entry_date == exit_date:
            self._pdt_tracker.record_day_trade(exit_date)

    # Check if daily loss limit is now breached (circuit breaker)
    await self._check_circuit_breaker_after_close()


async def _check_circuit_breaker_after_close(self) -> None:
    """Check if daily loss limit is breached after a position closes."""
    if self._circuit_breaker_active:
        return  # Already triggered

    account = await self._broker.get_account()
    daily_limit = account.equity * self._config.account.daily_loss_limit_pct

    if self._daily_realized_pnl < 0 and abs(self._daily_realized_pnl) >= daily_limit:
        self._circuit_breaker_active = True
        event = CircuitBreakerEvent(
            level="account",
            reason=f"Daily loss limit reached: ${self._daily_realized_pnl:.2f}",
            strategies_affected=[],  # Affects all strategies
        )
        await self._event_bus.publish(event)
        logger.critical(
            "CIRCUIT BREAKER TRIGGERED: Daily loss $%.2f exceeds limit $%.2f",
            abs(self._daily_realized_pnl),
            daily_limit,
        )
```

**State management methods:**

```python
def reset_daily_state(self) -> None:
    """Reset daily state at the start of each trading day.

    Called by the Orchestrator before market open. Clears daily P&L,
    trade count, and circuit breaker flag. Weekly P&L rolls over
    on Monday.
    """
    self._daily_realized_pnl = 0.0
    self._trades_today = 0
    self._circuit_breaker_active = False

    # Check for week rollover (Monday)
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    if monday != self._current_week_start:
        self._weekly_realized_pnl = 0.0
        self._current_week_start = monday
        logger.info("Weekly P&L reset (new week starting %s)", monday)

    logger.info("Risk Manager daily state reset")


async def reconstruct_state(self, trade_logger) -> None:
    """Reconstruct intraday state from the database after a mid-day restart.

    Queries today's closed trades from the TradeLogger to rebuild:
    - Daily realized P&L
    - Weekly realized P&L
    - PDT day trade count
    - Trade count

    Args:
        trade_logger: The TradeLogger instance for database queries.
    """
    today = date.today()
    trades_today = await trade_logger.get_trades_by_date(today)

    self._daily_realized_pnl = sum(t.pnl_dollars for t in trades_today if t.pnl_dollars)
    self._trades_today = len(trades_today)

    # Reconstruct weekly P&L
    monday = today - timedelta(days=today.weekday())
    self._current_week_start = monday
    # Note: For full weekly reconstruction, we'd need trades from Monday–today.
    # For V1, we reconstruct daily only. Weekly is an approximation after restart.
    # This is acceptable because weekly limit is a soft backstop.

    # Reconstruct PDT tracker from this week's trades
    # (would need TradeLogger.get_trades_by_date_range — defer to integration)

    logger.info(
        "Risk Manager state reconstructed: daily_pnl=$%.2f, trades=%d",
        self._daily_realized_pnl,
        self._trades_today,
    )
```

**Integrity check:**

```python
async def daily_integrity_check(self) -> IntegrityReport:
    """Verify all open positions have associated stop orders at the broker.

    V1 implementation: verify that the broker reports positions and that
    the system's internal state is consistent with the broker's state.
    Full stop-order verification requires Order Manager (Sprint 4).

    Returns:
        IntegrityReport with check results.
    """
    issues = []
    positions = await self._broker.get_positions()

    # Basic checks for V1
    account = await self._broker.get_account()
    if account.equity <= 0:
        issues.append("Account equity is zero or negative")

    return IntegrityReport(
        timestamp=datetime.now(),
        positions_checked=len(positions),
        issues=issues,
        passed=len(issues) == 0,
    )
```

**Properties (read-only access for testing and monitoring):**

```python
@property
def daily_realized_pnl(self) -> float:
    """Current daily realized P&L."""
    return self._daily_realized_pnl

@property
def weekly_realized_pnl(self) -> float:
    """Current weekly realized P&L."""
    return self._weekly_realized_pnl

@property
def circuit_breaker_active(self) -> bool:
    """Whether the circuit breaker is currently active."""
    return self._circuit_breaker_active

@property
def pdt_tracker(self) -> PDTTracker:
    """Access to PDT tracker for monitoring."""
    return self._pdt_tracker
```

---

## Step 7: Tests

### General Testing Notes

- All tests use `pytest` + `pytest-asyncio`.
- Use the existing `conftest.py` fixtures where applicable (config, event_bus, db, trade_logger).
- Add new fixtures for `SimulatedBroker` and `RiskManager` to `conftest.py`.
- Follow existing naming convention: `test_<what>_<expected_result>`.
- Mock nothing in unit tests for SimulatedBroker (it IS the mock). Mock the Broker in Risk Manager tests using SimulatedBroker.

### New fixtures to add to `tests/conftest.py`:

```python
from argus.execution.simulated_broker import SimulatedBroker
from argus.core.risk_manager import RiskManager

@pytest.fixture
def simulated_broker():
    """SimulatedBroker with default settings."""
    broker = SimulatedBroker(initial_cash=100_000.0)
    return broker

@pytest.fixture
def risk_manager(config, simulated_broker, event_bus):
    """RiskManager with default config, simulated broker, and event bus."""
    return RiskManager(
        config=config.risk,
        broker=simulated_broker,
        event_bus=event_bus,
    )
```

### File: `tests/execution/__init__.py`

Empty file.

### File: `tests/execution/test_broker.py`

Test the `SimulatedBroker` directly. No mocking needed — it IS the test double.

**Tests to implement:**

```
test_connect_sets_connected_state
    broker = SimulatedBroker(initial_cash=50000)
    await broker.connect()
    assert broker._connected is True

test_place_order_not_connected_raises
    broker = SimulatedBroker()
    # Don't call connect()
    with pytest.raises(RuntimeError):
        await broker.place_order(buy_order)

test_place_buy_order_fills_at_price
    await broker.connect()
    order = Order(symbol="AAPL", side="buy", quantity=100, price=150.0, order_type="market")
    result = await broker.place_order(order)
    assert result.status == OrderStatus.FILLED
    assert result.filled_qty == 100
    assert result.filled_avg_price == 150.0

test_place_buy_order_deducts_cash
    # Start with 50000, buy 100 shares at 150 = 15000 cost
    broker = SimulatedBroker(initial_cash=50000)
    await broker.connect()
    await broker.place_order(buy_order)
    account = await broker.get_account()
    assert account.cash == 35000.0

test_place_buy_order_creates_position
    await broker.connect()
    await broker.place_order(buy_order)
    positions = await broker.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].shares == 100

test_place_sell_order_closes_position
    await broker.connect()
    await broker.place_order(buy_order)
    sell_order = Order(symbol="AAPL", side="sell", quantity=100, price=155.0, order_type="market")
    result = await broker.place_order(sell_order)
    assert result.status == OrderStatus.FILLED
    positions = await broker.get_positions()
    assert len(positions) == 0

test_place_sell_order_adds_cash
    broker = SimulatedBroker(initial_cash=50000)
    await broker.connect()
    await broker.place_order(buy_100_at_150)  # -15000, cash=35000
    await broker.place_order(sell_100_at_155)  # +15500, cash=50500
    account = await broker.get_account()
    assert account.cash == 50500.0

test_place_buy_order_insufficient_funds_rejected
    broker = SimulatedBroker(initial_cash=1000)
    await broker.connect()
    order = Order(symbol="AAPL", side="buy", quantity=100, price=150.0, order_type="market")
    result = await broker.place_order(order)
    assert result.status == OrderStatus.REJECTED
    assert "buying power" in result.message.lower()

test_place_sell_order_no_position_rejected
    await broker.connect()
    sell_order = Order(symbol="AAPL", side="sell", quantity=100, price=155.0, order_type="market")
    result = await broker.place_order(sell_order)
    assert result.status == OrderStatus.REJECTED

test_place_bracket_order_registers_stop_and_targets
    await broker.connect()
    entry = Order(symbol="AAPL", side="buy", quantity=100, price=150.0, order_type="market")
    stop = Order(symbol="AAPL", side="sell", quantity=100, price=145.0, order_type="stop")
    targets = [Order(symbol="AAPL", side="sell", quantity=50, price=155.0, order_type="limit")]
    result = await broker.place_bracket_order(entry, stop, targets)
    assert result.entry.status == OrderStatus.FILLED
    assert result.stop.status == OrderStatus.PENDING
    assert result.targets[0].status == OrderStatus.PENDING

test_bracket_order_entry_rejected_no_stop_or_targets
    broker = SimulatedBroker(initial_cash=100)  # Not enough
    await broker.connect()
    entry = Order(symbol="AAPL", side="buy", quantity=100, price=150.0, order_type="market")
    stop = Order(...)
    targets = [...]
    result = await broker.place_bracket_order(entry, stop, targets)
    assert result.entry.status == OrderStatus.REJECTED
    assert result.stop.status == OrderStatus.REJECTED
    assert result.targets[0].status == OrderStatus.REJECTED

test_simulate_price_update_triggers_stop
    await broker.connect()
    # Buy 100 at 150, stop at 145
    await broker.place_bracket_order(entry, stop, targets)
    # Price drops to 144 → stop triggers
    results = await broker.simulate_price_update("AAPL", 144.0)
    assert len(results) == 1
    assert results[0].status == OrderStatus.FILLED
    positions = await broker.get_positions()
    assert len(positions) == 0  # Position closed by stop

test_simulate_price_update_triggers_target
    await broker.connect()
    await broker.place_bracket_order(entry, stop, [target_at_155])
    results = await broker.simulate_price_update("AAPL", 156.0)
    assert len(results) == 1
    assert results[0].filled_avg_price == 156.0

test_stop_trigger_cancels_remaining_targets
    await broker.connect()
    # Entry 100 shares, stop 100 shares, target 100 shares
    await broker.place_bracket_order(entry, stop, [target])
    await broker.simulate_price_update("AAPL", 144.0)  # Stop triggers
    # All bracket orders for this position should be gone
    assert len(broker._pending_brackets) == 0

test_target_trigger_cancels_stop_when_position_fully_closed
    await broker.connect()
    # Entry 100, target sells all 100
    await broker.place_bracket_order(entry, stop, [target_for_100_shares])
    await broker.simulate_price_update("AAPL", 160.0)  # Target triggers
    assert len(broker._pending_brackets) == 0
    assert len(await broker.get_positions()) == 0

test_cancel_pending_bracket_order
    await broker.connect()
    await broker.place_bracket_order(entry, stop, [target])
    stop_id = # get from bracket result
    cancelled = await broker.cancel_order(stop_id)
    assert cancelled is True

test_get_account_reflects_positions
    await broker.connect()
    await broker.place_order(buy_100_at_150)
    account = await broker.get_account()
    assert account.positions_value == 15000.0
    assert account.equity == 100000.0  # Cash decreased but position value equals cost

test_flatten_all_closes_everything
    await broker.connect()
    await broker.place_order(buy_aapl)
    await broker.place_order(buy_tsla)
    results = await broker.flatten_all()
    assert len(results) == 2
    positions = await broker.get_positions()
    assert len(positions) == 0

test_flatten_all_cancels_pending_brackets
    await broker.connect()
    await broker.place_bracket_order(entry, stop, [target])
    await broker.flatten_all()
    assert len(broker._pending_brackets) == 0

test_fixed_slippage_buy_order
    broker = SimulatedBroker(initial_cash=100000, slippage=SimulatedSlippage(mode="fixed", fixed_amount=0.05))
    await broker.connect()
    order = Order(symbol="AAPL", side="buy", quantity=100, price=150.0, order_type="market")
    result = await broker.place_order(order)
    assert result.filled_avg_price == 150.05  # Worse for buyer

test_fixed_slippage_sell_order
    broker = SimulatedBroker(initial_cash=100000, slippage=SimulatedSlippage(mode="fixed", fixed_amount=0.05))
    await broker.connect()
    # First buy, then sell
    await broker.place_order(buy_order)
    result = await broker.place_order(sell_order)
    assert result.filled_avg_price == sell_price - 0.05  # Worse for seller

test_partial_sell_reduces_position
    await broker.connect()
    await broker.place_order(buy_100)
    await broker.place_order(sell_50)
    positions = await broker.get_positions()
    assert positions[0].shares == 50

test_get_order_status_returns_correct_status
    await broker.connect()
    result = await broker.place_order(buy_order)
    status = await broker.get_order_status(result.order_id)
    assert status == OrderStatus.FILLED

test_get_order_status_unknown_id_raises
    await broker.connect()
    with pytest.raises(KeyError):
        await broker.get_order_status("nonexistent")
```

**Total: ~24 tests**

### File: `tests/execution/test_broker_router.py`

```
test_route_returns_primary_broker
    router = BrokerRouter(config, {"alpaca": mock_broker})
    broker = router.route("us_stocks")
    assert broker is mock_broker

test_route_different_asset_class_still_returns_primary_v1
    # V1: everything routes to primary regardless of asset class
    router = BrokerRouter(config, {"alpaca": mock_broker})
    broker = router.route("crypto")
    assert broker is mock_broker

test_primary_broker_property
    router = BrokerRouter(config, {"alpaca": mock_broker})
    assert router.primary_broker is mock_broker

test_invalid_primary_raises_on_construction
    config_with_bad_primary = ...  # primary="nonexistent"
    with pytest.raises(ValueError):
        BrokerRouter(config_with_bad_primary, {"alpaca": mock_broker})
```

**Total: ~4 tests**

### File: `tests/core/test_risk_manager.py`

These tests use `SimulatedBroker` as the real broker (it's deterministic) and a real `EventBus`. No mocking needed.

**Helper: Create a valid `SignalEvent` for testing:**

```python
def make_signal(
    symbol: str = "AAPL",
    side: str = "buy",
    entry_price: float = 150.0,
    stop_price: float = 147.0,
    share_count: int = 100,
    strategy_id: str = "strat_orb_breakout",
    target_prices: list[float] | None = None,
) -> SignalEvent:
    """Create a SignalEvent for testing."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices or [153.0, 156.0],
        share_count=share_count,
        rationale="Test signal",
    )
```

**Tests to implement:**

```
test_valid_signal_approved_no_modifications
    # Default broker has 100K, signal buys 100 shares at 150 = 15K. Well within limits.
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    signal = make_signal()
    result = await rm.evaluate_signal(signal)
    assert isinstance(result, OrderApprovedEvent)
    assert result.modifications is None

test_signal_rejected_when_circuit_breaker_active
    rm = RiskManager(config.risk, broker, event_bus)
    rm._circuit_breaker_active = True
    result = await rm.evaluate_signal(make_signal())
    assert isinstance(result, OrderRejectedEvent)
    assert "circuit breaker" in result.reason.lower()

test_signal_rejected_daily_loss_limit
    # Simulate broker account with 100K equity. Daily limit = 3% = $3000.
    # Set daily P&L to -$3000 (at limit).
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    rm._daily_realized_pnl = -3000.0
    result = await rm.evaluate_signal(make_signal())
    assert isinstance(result, OrderRejectedEvent)
    assert "daily loss limit" in result.reason.lower()

test_daily_loss_limit_triggers_circuit_breaker
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    rm._daily_realized_pnl = -3000.0

    # Track published events
    breaker_events = []
    await event_bus.subscribe(CircuitBreakerEvent, lambda e: breaker_events.append(e))

    await rm.evaluate_signal(make_signal())
    await event_bus.drain()

    assert rm.circuit_breaker_active is True
    assert len(breaker_events) == 1
    assert breaker_events[0].level == "account"

test_signal_rejected_weekly_loss_limit
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    rm._weekly_realized_pnl = -5000.0  # 5% of 100K
    result = await rm.evaluate_signal(make_signal())
    assert isinstance(result, OrderRejectedEvent)
    assert "weekly loss limit" in result.reason.lower()

test_signal_rejected_max_concurrent_positions
    # Fill the broker with max_concurrent_positions (10) positions first
    broker = SimulatedBroker(initial_cash=500_000)
    await broker.connect()
    for i in range(10):
        await broker.place_order(Order(symbol=f"SYM{i}", side="buy", quantity=10, price=100.0, order_type="market"))

    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    result = await rm.evaluate_signal(make_signal(symbol="NEWSTOCK"))
    assert isinstance(result, OrderRejectedEvent)
    assert "concurrent positions" in result.reason.lower()

test_signal_approved_with_reduced_shares_cash_reserve
    # Broker has 100K. Cash reserve = 20% = 20K. Available = 80K.
    # Signal wants to buy 600 shares at 150 = 90K (exceeds 80K available).
    # Should reduce to int(80000/150) = 533 shares.
    # Check 0.25R: 533 >= 0.25 * 600 = 150. 533 >= 150 ✓
    broker = SimulatedBroker(initial_cash=100_000)
    await broker.connect()
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    signal = make_signal(share_count=600, entry_price=150.0, stop_price=147.0)
    result = await rm.evaluate_signal(signal)
    assert isinstance(result, OrderApprovedEvent)
    assert result.modifications is not None
    assert result.modifications["share_count"] < 600
    assert result.modifications["share_count"] == 533

test_signal_rejected_below_025r_floor
    # Broker has very little available cash. Reduced shares would be tiny.
    # 100K equity, 80K already deployed in positions. Cash = 20K. Reserve = 20K.
    # Available = 0. Should reject entirely (not reduce to 0).
    broker = SimulatedBroker(initial_cash=20_000)
    await broker.connect()
    # Deploy most cash so available-after-reserve is tiny
    await broker.place_order(Order(symbol="SPY", side="buy", quantity=190, price=100.0, order_type="market"))
    # Cash now = 1000, equity ~= 20000, reserve = 4000. available = 1000 - 4000 < 0.
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    signal = make_signal(share_count=100, entry_price=150.0)
    result = await rm.evaluate_signal(signal)
    assert isinstance(result, OrderRejectedEvent)

test_signal_approved_with_reduced_shares_buying_power
    # Similar to cash reserve test but hitting buying power limit
    broker = SimulatedBroker(initial_cash=50_000)
    await broker.connect()
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    # Want 400 shares at 150 = 60K, but buying power = 50K (no reserve issue because
    # buying power < available-after-reserve)
    # Actually need to think about this more carefully:
    # equity = 50K, reserve = 10K, available = 40K
    # 400 * 150 = 60K > 40K (cash reserve constraint fires first)
    # reduced = int(40000/150) = 266
    signal = make_signal(share_count=400, entry_price=150.0)
    result = await rm.evaluate_signal(signal)
    assert isinstance(result, OrderApprovedEvent)
    assert result.modifications is not None
    assert result.modifications["share_count"] == 266

test_pdt_margin_account_under_threshold_limits_trades
    # Account under 25K, margin account, PDT enabled.
    # After 3 day trades in the rolling window, 4th should be rejected.
    broker = SimulatedBroker(initial_cash=20_000)
    await broker.connect()
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()

    today = date.today()
    rm._pdt_tracker.record_day_trade(today)
    rm._pdt_tracker.record_day_trade(today)
    rm._pdt_tracker.record_day_trade(today)

    result = await rm.evaluate_signal(make_signal(share_count=10, entry_price=50.0))
    assert isinstance(result, OrderRejectedEvent)
    assert "pdt" in result.reason.lower()

test_pdt_margin_account_above_threshold_unlimited
    # Account above 25K, margin account. PDT should not restrict.
    broker = SimulatedBroker(initial_cash=30_000)
    await broker.connect()
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()

    today = date.today()
    for _ in range(5):
        rm._pdt_tracker.record_day_trade(today)

    # Signal is small enough to pass other checks
    signal = make_signal(share_count=10, entry_price=50.0, stop_price=48.0)
    result = await rm.evaluate_signal(signal)
    assert isinstance(result, OrderApprovedEvent)

test_pdt_cash_account_unlimited
    # Cash account — PDT doesn't apply regardless of balance.
    risk_config = ...  # Clone config but set pdt.account_type = "cash"
    broker = SimulatedBroker(initial_cash=10_000)
    await broker.connect()
    rm = RiskManager(risk_config, broker, event_bus)
    await rm.initialize()

    today = date.today()
    for _ in range(10):
        rm._pdt_tracker.record_day_trade(today)

    signal = make_signal(share_count=10, entry_price=50.0, stop_price=48.0)
    result = await rm.evaluate_signal(signal)
    assert isinstance(result, OrderApprovedEvent)

test_pdt_rolling_window_expires_old_trades
    broker = SimulatedBroker(initial_cash=20_000)
    await broker.connect()
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()

    # Record 3 trades 6 business days ago (should be expired)
    today = date.today()
    old_date = PDTTracker._business_days_ago(today, 6)
    rm._pdt_tracker.record_day_trade(old_date)
    rm._pdt_tracker.record_day_trade(old_date)
    rm._pdt_tracker.record_day_trade(old_date)

    remaining = rm._pdt_tracker.day_trades_remaining(today, 20_000)
    assert remaining == 3  # Old trades expired, all 3 available

test_circuit_breaker_after_position_close_event
    # Simulate a PositionClosedEvent that pushes daily P&L past the limit
    broker = SimulatedBroker(initial_cash=100_000)
    await broker.connect()
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()

    rm._daily_realized_pnl = -2500.0  # Just under 3% of 100K = 3000

    # Publish a PositionClosedEvent with -$600 loss (total = -3100, over limit)
    close_event = PositionClosedEvent(
        position_id="test",
        exit_price=144.0,
        realized_pnl=-600.0,
        exit_reason="stop_loss",
        hold_duration=300,
        entry_time=datetime.now(),
        exit_time=datetime.now(),
    )
    await event_bus.publish(close_event)
    await event_bus.drain()

    assert rm.circuit_breaker_active is True
    assert rm._daily_realized_pnl == -3100.0

test_reset_daily_state_clears_everything
    rm = RiskManager(config.risk, broker, event_bus)
    rm._daily_realized_pnl = -2000.0
    rm._trades_today = 5
    rm._circuit_breaker_active = True

    rm.reset_daily_state()

    assert rm._daily_realized_pnl == 0.0
    assert rm._trades_today == 0
    assert rm._circuit_breaker_active is False

test_reset_daily_state_resets_weekly_on_monday
    rm = RiskManager(config.risk, broker, event_bus)
    rm._weekly_realized_pnl = -4000.0
    # Force a week change by setting current_week_start to last week
    rm._current_week_start = date.today() - timedelta(days=7)

    rm.reset_daily_state()

    assert rm._weekly_realized_pnl == 0.0

test_positive_pnl_does_not_trigger_daily_limit
    # Daily P&L of +$5000 should NOT trigger the daily loss limit
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()
    rm._daily_realized_pnl = 5000.0  # Positive
    result = await rm.evaluate_signal(make_signal())
    assert isinstance(result, OrderApprovedEvent)

test_on_position_closed_updates_daily_and_weekly_pnl
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()

    close_event = PositionClosedEvent(
        position_id="test",
        exit_price=155.0,
        realized_pnl=500.0,
        exit_reason="target_1",
        hold_duration=600,
        entry_time=datetime.now(),
        exit_time=datetime.now(),
    )
    await event_bus.publish(close_event)
    await event_bus.drain()

    assert rm.daily_realized_pnl == 500.0
    assert rm.weekly_realized_pnl == 500.0

test_on_position_closed_same_day_records_day_trade
    rm = RiskManager(config.risk, broker, event_bus)
    await rm.initialize()

    now = datetime.now()
    close_event = PositionClosedEvent(
        position_id="test",
        exit_price=155.0,
        realized_pnl=500.0,
        exit_reason="target_1",
        hold_duration=600,
        entry_time=now,
        exit_time=now,  # Same day
    )
    await event_bus.publish(close_event)
    await event_bus.drain()

    assert len(rm.pdt_tracker.day_trades) == 1

test_integrity_check_passes_with_no_issues
    broker = SimulatedBroker(initial_cash=100_000)
    await broker.connect()
    rm = RiskManager(config.risk, broker, event_bus)
    report = await rm.daily_integrity_check()
    assert report.passed is True
```

**Total: ~20 tests**

### File: `tests/test_integration_sprint2.py`

End-to-end integration test — the most important test in this sprint.

```
test_full_pipeline_signal_to_fill_to_log
    """Complete pipeline: SignalEvent → Risk Manager → SimulatedBroker → TradeLogger.

    This test validates that all Sprint 2 components work together:
    1. Create a valid SignalEvent
    2. Risk Manager evaluates and approves it
    3. Use approval to place an order on SimulatedBroker
    4. Get the fill result
    5. Log the trade via TradeLogger
    6. Query the trade back from TradeLogger and verify all fields
    """
    # Setup
    broker = SimulatedBroker(initial_cash=100_000)
    await broker.connect()
    event_bus = EventBus()
    risk_manager = RiskManager(config.risk, broker, event_bus)
    await risk_manager.initialize()
    trade_logger = TradeLogger(db_manager)

    # Step 1: Create signal
    signal = SignalEvent(
        strategy_id="strat_orb_breakout",
        symbol="AAPL",
        side="buy",
        entry_price=150.0,
        stop_price=147.0,
        target_prices=[153.0, 156.0],
        share_count=100,
        rationale="ORB breakout confirmed",
    )

    # Step 2: Risk Manager approves
    result = await risk_manager.evaluate_signal(signal)
    assert isinstance(result, OrderApprovedEvent)

    # Step 3: Place order on broker
    effective_shares = result.modifications["share_count"] if result.modifications else signal.share_count
    order = Order(
        symbol=signal.symbol,
        side=signal.side,
        quantity=effective_shares,
        price=signal.entry_price,
        order_type="market",
    )
    fill = await broker.place_order(order)
    assert fill.status == OrderStatus.FILLED

    # Step 4: Log the trade (entry)
    trade_id = await trade_logger.log_trade(
        strategy_id=signal.strategy_id,
        strategy_version="1.0.0",
        symbol=signal.symbol,
        asset_class="us_stocks",
        side=signal.side,
        entry_price=fill.filled_avg_price,
        shares=fill.filled_qty,
        stop_price=signal.stop_price,
        target_prices=signal.target_prices,
    )

    # Step 5: Query it back
    trade = await trade_logger.get_trade(trade_id)
    assert trade is not None
    assert trade.symbol == "AAPL"
    assert trade.entry_price == 150.0
    assert trade.shares == 100
    assert trade.strategy_id == "strat_orb_breakout"


test_pipeline_with_modification_reduced_shares
    """Pipeline where Risk Manager reduces share count due to cash reserve."""
    broker = SimulatedBroker(initial_cash=50_000)
    await broker.connect()
    # ... (signal that exceeds available-after-reserve, gets reduced, still fills)


test_pipeline_with_rejection
    """Pipeline where Risk Manager rejects the signal."""
    broker = SimulatedBroker(initial_cash=100_000)
    await broker.connect()
    risk_manager = RiskManager(config.risk, broker, event_bus)
    await risk_manager.initialize()
    risk_manager._circuit_breaker_active = True

    signal = make_signal()
    result = await risk_manager.evaluate_signal(signal)
    assert isinstance(result, OrderRejectedEvent)
    # No order placed, no trade logged. Pipeline stops here.


test_pipeline_bracket_order_with_stop_trigger
    """Full bracket order lifecycle with stop loss trigger."""
    broker = SimulatedBroker(initial_cash=100_000)
    await broker.connect()
    # ... (place bracket, simulate price drop, stop triggers, position closed)
```

**Total: ~4 integration tests**

---

## Summary of Test Counts

| File | Tests |
|------|-------|
| `tests/execution/test_broker.py` | ~24 |
| `tests/execution/test_broker_router.py` | ~4 |
| `tests/core/test_risk_manager.py` | ~20 |
| `tests/test_integration_sprint2.py` | ~4 |
| **Sprint 2 Total** | **~52** |
| Sprint 1 (existing) | 52 |
| **Grand Total** | **~104** |

---

## Sprint 2 Definition of Done

1. `ruff check argus/ tests/` — clean
2. `pytest tests/ -v` — all tests pass (Sprint 1 + Sprint 2)
3. SimulatedBroker fills orders deterministically
4. Risk Manager correctly rejects, approves, or modifies signals at account level
5. PDT tracking works for both margin and cash account modes
6. Circuit breaker fires and publishes event when triggered
7. End-to-end flow works: Signal → Risk Manager → SimulatedBroker → TradeLogger
8. All public methods have type hints and docstrings (Google style)
9. No hardcoded config values — everything from YAML/Pydantic

---

## Implementation Notes for Claude Code

**Pattern matching:** Follow the exact code style from Sprint 1. Specifically:
- Import grouping: stdlib → third-party → local
- Type hints on ALL parameters and return types
- Google-style docstrings on all public methods and classes
- `logger = logging.getLogger(__name__)` at module level
- Use `generate_ulid()` from `argus.core.ids` for all IDs
- Frozen dataclasses for immutable data (events, results)
- Regular dataclasses for mutable state (SimulatedBroker internals)

**Event field names:** Check the actual field names on `SignalEvent`, `PositionClosedEvent`, etc. in `argus/core/events.py` before using them. The spec uses field names from the Architecture doc, but the implementation may have minor naming differences from Sprint 1. The implementation is authoritative.

**Order model:** Check the actual fields on `Order` and `Position` in `argus/models/trading.py`. The spec uses simplified field names. Match the actual implementation.

**Config model update:** When adding `threshold_balance` to `PDTConfig`, ensure backward compatibility — existing tests that create `PDTConfig` without this field should still pass via the default value.

**Circular import prevention:** `RiskManager` imports from `execution.broker` (the ABC). This is fine — it depends on the abstraction, not the implementation. `SimulatedBroker` imports from `models.trading` and `execution.broker`. No circular dependencies.

---

## What NOT to Build

- No AlpacaBroker (Sprint 4)
- No IBKRBroker (Phase 3+)
- No Order Manager (Sprint 4)
- No cross-strategy risk checks (Phase 4)
- No strategy-level risk checks in Risk Manager (handled by strategies in Sprint 3)
- No Data Service (Sprint 3)
- No API server endpoints
- No UI components

---

*End of Sprint 2 Implementation Spec*
