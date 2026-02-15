# ARGUS — Sprint 4b Implementation Spec

> **Date:** February 15, 2026
> **Author:** Claude (claude.ai strategic session)
> **Purpose:** Complete implementation guide for Claude Code. Everything needed to build Sprint 4b without ambiguity.
> **Starting state:** 282 tests, 0 flaky, ruff clean. Sprint 4a complete.

---

## Sprint 4b Objective

Deliver active position management and live scanning. After this sprint, the full ORB trading pipeline works end-to-end:

```
AlpacaScanner → OrbBreakout → RiskManager → OrderManager → AlpacaBroker
```

The Order Manager is the critical new component — it bridges the gap between "risk approved this signal" and "positions are actively managed through their full lifecycle."

---

## Micro-Decisions (Resolved)

### MD-4b-1: T1/T2 Stop Management — Cancel and Resubmit ✅

**Decision:** Cancel old stop, submit new stop (option a).

**Rationale:** `modify_order` on Alpaca replaces the entire order. If the replace fails mid-flight, we could briefly have no stop protection with no way to detect it. Cancel-then-submit is explicit: if the cancel succeeds but the new submit fails, we detect the failure immediately and can emergency flatten. The brief window between cancel and resubmit is acceptable because the Order Manager is also monitoring ticks and will catch any adverse moves.

**Implementation note:** After cancelling the old stop, always verify the cancel was acknowledged before submitting the new stop. If cancel fails (order already filled), handle that as a stop-out — don't submit a new stop for shares we no longer own.

### MD-4b-2: EOD Flatten Scheduling — Piggyback on Fallback Poll ✅

**Decision:** Check `clock.now()` against flatten time inside the fallback poll loop (option a).

**Rationale:** We don't have APScheduler integrated yet. The fallback poll already runs every 5 seconds — adding an EOD time check there is trivial and introduces no new dependencies. APScheduler can be introduced in Sprint 5 for more sophisticated scheduling needs.

**Implementation note:** The check should be: if `clock.now()` (in ET) >= `eod_flatten_time` AND we haven't already flattened today, trigger `eod_flatten()`. Set a `_flattened_today: bool` flag to prevent re-triggering on subsequent poll cycles.

### MD-4b-3: TradeLogger Integration — Order Manager Calls Directly ✅

**Decision:** Order Manager calls `TradeLogger.log_trade()` directly when a position fully closes (option a).

**Rationale:** The Order Manager has the complete trade data at close time — entry price, exit price(s), shares, P&L, hold duration, exit reason. Publishing a `PositionClosedEvent` is still done (for other subscribers like the UI), but the Order Manager owns the persistence call.

**Implementation note:** The Order Manager constructor takes an optional `TradeLogger` dependency. For unit tests, pass `None` and skip the `log_trade()` call. For integration tests and production, inject a real TradeLogger.

### MD-4b-4: AlpacaScanner Universe — Static Config ✅

**Decision:** Universe is a fixed list in config (option a).

**Rationale:** A curated list of 20-50 liquid stocks is more than enough for ORB scanning. Dynamic universe adds complexity (API failures at startup, rate limits, "what if the list changes mid-day?") for no V1 benefit. The list is easy to expand manually.

### MD-4b-5: Exit Rules Delivery — Embedded in Signal ✅

**Decision:** Exit rules travel with the signal (option a).

**Analysis of existing models:** The current `SignalEvent` already carries `stop_price` and `target_prices` (as a tuple of floats). These cover the price-based exit rules. However, the full `ExitRules` dataclass from `argus/models/strategy.py` contains additional fields (`time_stop_minutes`, `trailing_stop_atr_multiplier`, `stop_type`) that are NOT on `SignalEvent`.

**Resolution:** The Order Manager extracts what it can from `SignalEvent` (stop_price, target_prices) and uses its own config (`OrderManagerConfig`) for time-based rules and trailing stop settings. This avoids modifying the frozen `SignalEvent` dataclass.

Here's the mapping:
- `stop_price` → from `SignalEvent.stop_price` (via `OrderApprovedEvent.signal`)
- `target_prices[0]` → T1 price (1R target)
- `target_prices[1]` → T2 price (2R target)
- `time_stop_minutes` → from `OrderManagerConfig.max_position_duration_minutes`
- `trailing_stop` → from `OrderManagerConfig.enable_trailing_stop` + `trailing_stop_atr_multiplier`
- `stop_to_breakeven` → from `OrderManagerConfig.enable_stop_to_breakeven` + `breakeven_buffer_pct`

This means all positions managed by the Order Manager share the same time-stop and trailing-stop config. Per-strategy exit rule customization is a future enhancement (Phase 2+).

---

## Issue Found During Review: Event Model Gaps

The current `OrderFilledEvent` is minimal:
```python
@dataclass(frozen=True)
class OrderFilledEvent(Event):
    order_id: str = ""
    fill_price: float = 0.0
    fill_quantity: int = 0
```

The Order Manager needs to correlate fills back to managed positions. It can do this via `order_id` → `PendingManagedOrder` lookup (the Order Manager tracks which order_ids it submitted). This works without modifying the event model.

However, the `OrderFilledEvent` is missing a `symbol` field. The Order Manager can infer symbol from its `_pending_orders` dict, but other subscribers (like a future Trade Logger listener) would need to know which order_id maps to which symbol. **For now, we'll work around this by using the Order Manager's internal tracking. Add `symbol` to `OrderFilledEvent` as a Sprint 5 cleanup item.**

Similarly, `OrderCancelledEvent` is just `order_id` + `reason`. Same workaround applies.

---

## Component 1: Config Models

### File: `argus/core/config.py` (append)

```python
class OrderManagerConfig(BaseModel):
    """Configuration for the Order Manager."""
    eod_flatten_time: str = "15:50"  # HH:MM in ET
    eod_flatten_timezone: str = "America/New_York"
    fallback_poll_interval_seconds: int = 5
    enable_stop_to_breakeven: bool = True
    breakeven_buffer_pct: float = 0.001  # Move stop to entry + 0.1%
    enable_trailing_stop: bool = False  # V1: disabled by default
    trailing_stop_atr_multiplier: float = 2.0
    max_position_duration_minutes: int = 120  # Hard time stop
    entry_timeout_seconds: int = 30  # Cancel entry if not filled within this
    t1_position_pct: float = 0.5  # 50% of shares at T1
    stop_retry_max: int = 1  # Retry stop order submission once on failure


class AlpacaScannerConfig(BaseModel):
    """Configuration for the Alpaca live scanner."""
    universe_source: str = "config"  # "config" = use universe_symbols list
    universe_symbols: list[str] = []
    min_price: float = 5.0
    max_price: float = 500.0
    min_volume_yesterday: int = 1_000_000
    max_symbols_returned: int = 10
```

### File: `config/order_manager.yaml`

```yaml
eod_flatten_time: "15:50"
eod_flatten_timezone: "America/New_York"
fallback_poll_interval_seconds: 5
enable_stop_to_breakeven: true
breakeven_buffer_pct: 0.001
enable_trailing_stop: false
trailing_stop_atr_multiplier: 2.0
max_position_duration_minutes: 120
entry_timeout_seconds: 30
t1_position_pct: 0.5
stop_retry_max: 1
```

### File: `config/scanner.yaml` (update)

Add alongside existing static scanner config:

```yaml
scanner_type: "alpaca"
alpaca_scanner:
  universe_source: "config"
  universe_symbols:
    - "AAPL"
    - "MSFT"
    - "NVDA"
    - "TSLA"
    - "AMD"
    - "AMZN"
    - "META"
    - "GOOGL"
    - "NFLX"
    - "SPY"
  min_price: 5.0
  max_price: 500.0
  min_volume_yesterday: 1000000
  max_symbols_returned: 10
```

---

## Component 2: Data Models

### File: `argus/execution/order_manager.py` (top section)

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ManagedPosition:
    """Tracks a position being actively managed by the Order Manager.
    
    Mutable — fields update as the position progresses through its lifecycle.
    """
    symbol: str
    strategy_id: str
    entry_price: float             # Actual fill price
    entry_time: datetime           # When entry filled
    shares_total: int              # Original total shares
    shares_remaining: int          # Shares still open
    stop_price: float              # Current stop price (may move to breakeven)
    stop_order_id: str | None      # Broker-side stop order ID
    t1_price: float                # T1 target price (target_prices[0])
    t1_order_id: str | None        # Broker-side T1 limit order ID
    t1_shares: int                 # Shares allocated to T1 (50%)
    t1_filled: bool                # Whether T1 has been hit
    t2_price: float                # T2 target price (target_prices[1])
    high_watermark: float          # Highest price since entry (for trailing stop)
    
    # Tracking for partial exit P&L
    realized_pnl: float = 0.0     # Accumulated P&L from partial exits
    
    @property
    def is_fully_closed(self) -> bool:
        return self.shares_remaining <= 0


@dataclass
class PendingManagedOrder:
    """Tracks an order awaiting fill confirmation from the broker.
    
    Keyed by order_id in Order Manager's _pending_orders dict.
    """
    order_id: str
    symbol: str
    strategy_id: str
    order_type: str                # "entry", "stop", "t1_target", "flatten"
    shares: int                    # Expected fill quantity
    signal: object                 # OrderApprovedEvent (for reference)
```

---

## Component 3: Order Manager

### File: `argus/execution/order_manager.py`

```python
"""Order Manager — manages the full lifecycle of trades from approval to exit.

Subscribes to OrderApprovedEvent, OrderFilledEvent, OrderCancelledEvent,
and TickEvent via the Event Bus. Runs a fallback poll loop for time-based
exits and a scheduled EOD flatten.

Key design decisions:
- T1/T2 split: Separate orders, not Alpaca brackets (DEC-039/MD-4a-6)
- Stop management: Cancel and resubmit, not modify-in-place (MD-4b-1)
- EOD flatten: Checked in fallback poll, not APScheduler (MD-4b-2)
- Trade logging: Called directly, not via event listener (MD-4b-3)
"""

import asyncio
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo

from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    CircuitBreakerEvent,
    ExitReason,
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderSubmittedEvent,
    OrderType,
    PositionClosedEvent,
    PositionOpenedEvent,
    Side,
    TickEvent,
)
from argus.core.ids import generate_ulid
from argus.execution.broker import Broker, Order

logger = logging.getLogger(__name__)
```

### Constructor

```python
class OrderManager:
    def __init__(
        self,
        event_bus: EventBus,
        broker: Broker,
        clock,               # Clock protocol (SystemClock or FixedClock)
        config: OrderManagerConfig,
        trade_logger=None,    # Optional TradeLogger for persistence
    ) -> None:
        self._event_bus = event_bus
        self._broker = broker
        self._clock = clock
        self._config = config
        self._trade_logger = trade_logger
        
        # Active positions: keyed by symbol
        # Note: supports multiple positions per symbol (list)
        self._managed_positions: dict[str, list[ManagedPosition]] = {}
        
        # Orders awaiting fill confirmation: keyed by order_id
        self._pending_orders: dict[str, PendingManagedOrder] = {}
        
        # Async tasks
        self._poll_task: asyncio.Task | None = None
        self._running: bool = False
        self._flattened_today: bool = False
```

### Lifecycle Methods

```python
    async def start(self) -> None:
        """Start the Order Manager.
        
        1. Subscribe to events on the Event Bus
        2. Start the fallback poll loop
        """
        await self._event_bus.subscribe(OrderApprovedEvent, self.on_approved)
        await self._event_bus.subscribe(OrderFilledEvent, self.on_fill)
        await self._event_bus.subscribe(OrderCancelledEvent, self.on_cancel)
        await self._event_bus.subscribe(TickEvent, self.on_tick)
        await self._event_bus.subscribe(CircuitBreakerEvent, self._on_circuit_breaker)
        
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("OrderManager started")
    
    async def stop(self) -> None:
        """Stop the Order Manager. Cancel the poll task."""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("OrderManager stopped")
```

### on_approved — Signal → Entry Order

```python
    async def on_approved(self, event: OrderApprovedEvent) -> None:
        """Handle an approved signal from the Risk Manager.
        
        1. Extract signal data (possibly with modifications applied)
        2. Submit market entry order to broker
        3. Store as PendingManagedOrder awaiting fill
        4. Publish OrderSubmittedEvent
        """
        signal = event.signal
        if signal is None:
            logger.warning("OrderApprovedEvent with no signal, ignoring")
            return
        
        # Apply modifications if any (e.g., reduced share count)
        share_count = signal.share_count
        target_prices = signal.target_prices
        if event.modifications:
            if "share_count" in event.modifications:
                share_count = event.modifications["share_count"]
            if "target_prices" in event.modifications:
                target_prices = event.modifications["target_prices"]
        
        # Validate we have at least T1 target
        if len(target_prices) < 1:
            logger.error(
                "Signal for %s has no target prices, cannot manage. Ignoring.",
                signal.symbol,
            )
            return
        
        # Submit market entry order
        try:
            entry_order = Order(
                symbol=signal.symbol,
                side="buy",  # Long only V1 (DEC-011)
                quantity=share_count,
                order_type="market",
            )
            order_result = await self._broker.place_order(entry_order)
            entry_order_id = order_result.order_id  # Broker-assigned ID
        except Exception:
            logger.exception("Failed to submit entry order for %s", signal.symbol)
            return
        
        # Track as pending
        self._pending_orders[entry_order_id] = PendingManagedOrder(
            order_id=entry_order_id,
            symbol=signal.symbol,
            strategy_id=signal.strategy_id,
            order_type="entry",
            shares=share_count,
            signal=event,
        )
        
        # Publish submission event
        await self._event_bus.publish(OrderSubmittedEvent(
            order_id=entry_order_id,
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=Side.LONG,
            quantity=share_count,
            order_type=OrderType.MARKET,
        ))
        
        logger.info(
            "Entry order submitted: %s %d shares of %s (order_id=%s)",
            "BUY", share_count, signal.symbol, entry_order_id,
        )
```

### on_fill — Fill Routing

```python
    async def on_fill(self, event: OrderFilledEvent) -> None:
        """Route fill events to the appropriate handler.
        
        Cases:
        a) Entry fill → create ManagedPosition, submit stop + T1
        b) T1 fill → move stop to breakeven, update position
        c) Stop fill → position closed (full or partial)
        d) Flatten fill → position closed
        """
        pending = self._pending_orders.pop(event.order_id, None)
        if pending is None:
            logger.debug("Fill for unknown order_id %s, ignoring", event.order_id)
            return
        
        if pending.order_type == "entry":
            await self._handle_entry_fill(pending, event)
        elif pending.order_type == "t1_target":
            await self._handle_t1_fill(pending, event)
        elif pending.order_type == "stop":
            await self._handle_stop_fill(pending, event)
        elif pending.order_type == "flatten":
            await self._handle_flatten_fill(pending, event)
        else:
            logger.warning("Unknown pending order type: %s", pending.order_type)
```

### Entry Fill Handler

```python
    async def _handle_entry_fill(
        self, pending: PendingManagedOrder, event: OrderFilledEvent
    ) -> None:
        """Entry order filled. Create ManagedPosition, submit stop + T1."""
        approved_event = pending.signal  # OrderApprovedEvent
        signal = approved_event.signal
        
        filled_shares = event.fill_quantity
        t1_shares = int(filled_shares * self._config.t1_position_pct)
        # Ensure at least 1 share for T1 if we have shares
        if t1_shares == 0 and filled_shares > 0:
            t1_shares = 1
        
        t1_price = signal.target_prices[0] if len(signal.target_prices) >= 1 else 0.0
        t2_price = signal.target_prices[1] if len(signal.target_prices) >= 2 else 0.0
        
        position = ManagedPosition(
            symbol=pending.symbol,
            strategy_id=pending.strategy_id,
            entry_price=event.fill_price,
            entry_time=self._clock.now(),
            shares_total=filled_shares,
            shares_remaining=filled_shares,
            stop_price=signal.stop_price,
            stop_order_id=None,
            t1_price=t1_price,
            t1_order_id=None,
            t1_shares=t1_shares,
            t1_filled=False,
            t2_price=t2_price,
            high_watermark=event.fill_price,
        )
        
        # Add to managed positions
        if pending.symbol not in self._managed_positions:
            self._managed_positions[pending.symbol] = []
        self._managed_positions[pending.symbol].append(position)
        
        # Submit stop order (covers full position)
        await self._submit_stop_order(position, filled_shares, signal.stop_price)
        
        # Submit T1 limit order (partial position)
        if t1_price > 0 and t1_shares > 0:
            await self._submit_t1_order(position, t1_shares, t1_price)
        
        # Publish PositionOpenedEvent
        await self._event_bus.publish(PositionOpenedEvent(
            position_id=generate_ulid(),
            strategy_id=pending.strategy_id,
            symbol=pending.symbol,
            entry_price=event.fill_price,
            shares=filled_shares,
            stop_price=signal.stop_price,
            target_prices=signal.target_prices,
        ))
        
        logger.info(
            "Position opened: %s %d shares @ %.2f (stop=%.2f, T1=%.2f, T2=%.2f)",
            pending.symbol, filled_shares, event.fill_price,
            signal.stop_price, t1_price, t2_price,
        )
```

### T1 Fill Handler

```python
    async def _handle_t1_fill(
        self, pending: PendingManagedOrder, event: OrderFilledEvent
    ) -> None:
        """T1 target hit. Move stop to breakeven for remaining shares."""
        positions = self._managed_positions.get(pending.symbol, [])
        position = self._find_position_by_t1_order(positions, event.order_id)
        if position is None:
            logger.warning("T1 fill for %s but no matching position", pending.symbol)
            return
        
        # Record T1 partial exit
        t1_pnl = (event.fill_price - position.entry_price) * event.fill_quantity
        position.realized_pnl += t1_pnl
        position.shares_remaining -= event.fill_quantity
        position.t1_filled = True
        position.t1_order_id = None
        
        # If position fully closed by T1 (all shares were T1), we're done
        if position.is_fully_closed:
            await self._close_position(position, event.fill_price, ExitReason.TARGET)
            return
        
        # Cancel old stop (was for full position size)
        if position.stop_order_id:
            old_stop_id = position.stop_order_id
            try:
                await self._broker.cancel_order(old_stop_id)
            except Exception:
                logger.exception("Failed to cancel old stop %s", old_stop_id)
                # If cancel fails, the old stop may have already filled
                # The on_fill for the stop will handle that case
            position.stop_order_id = None
        
        # Submit new stop at breakeven for remaining shares
        breakeven_price = position.entry_price * (1 + self._config.breakeven_buffer_pct)
        position.stop_price = breakeven_price
        await self._submit_stop_order(
            position, position.shares_remaining, breakeven_price
        )
        
        logger.info(
            "T1 hit for %s: %d shares @ %.2f (PnL: +%.2f). "
            "Stop moved to breakeven %.2f for %d remaining shares.",
            pending.symbol, event.fill_quantity, event.fill_price,
            t1_pnl, breakeven_price, position.shares_remaining,
        )
        
        # Log partial exit if TradeLogger available
        if self._trade_logger:
            await self._trade_logger.log_partial_exit(
                symbol=pending.symbol,
                strategy_id=position.strategy_id,
                shares=event.fill_quantity,
                exit_price=event.fill_price,
                pnl=t1_pnl,
                reason="t1_target",
            )
```

### Stop Fill Handler

```python
    async def _handle_stop_fill(
        self, pending: PendingManagedOrder, event: OrderFilledEvent
    ) -> None:
        """Stop loss triggered. Close position (or remaining shares)."""
        positions = self._managed_positions.get(pending.symbol, [])
        position = self._find_position_by_stop_order(positions, event.order_id)
        if position is None:
            logger.warning("Stop fill for %s but no matching position", pending.symbol)
            return
        
        # Record stop exit
        stop_pnl = (event.fill_price - position.entry_price) * event.fill_quantity
        position.realized_pnl += stop_pnl
        position.shares_remaining -= event.fill_quantity
        position.stop_order_id = None
        
        # Cancel T1 limit if still open
        if position.t1_order_id and not position.t1_filled:
            try:
                await self._broker.cancel_order(position.t1_order_id)
            except Exception:
                logger.exception("Failed to cancel T1 order %s", position.t1_order_id)
            position.t1_order_id = None
        
        exit_reason = (
            ExitReason.STOP_LOSS if not position.t1_filled
            else ExitReason.STOP_LOSS  # Breakeven stop is still a "stop_loss" exit
        )
        await self._close_position(position, event.fill_price, exit_reason)
        
        logger.info(
            "Stop hit for %s: %d shares @ %.2f (PnL: %.2f). Position closed.",
            pending.symbol, event.fill_quantity, event.fill_price, stop_pnl,
        )
```

### Flatten Fill Handler

```python
    async def _handle_flatten_fill(
        self, pending: PendingManagedOrder, event: OrderFilledEvent
    ) -> None:
        """Market order to flatten position has filled."""
        positions = self._managed_positions.get(pending.symbol, [])
        # Find the position that was being flattened
        position = next(
            (p for p in positions if p.shares_remaining > 0),
            None,
        )
        if position is None:
            logger.warning("Flatten fill for %s but no open position", pending.symbol)
            return
        
        flatten_pnl = (event.fill_price - position.entry_price) * event.fill_quantity
        position.realized_pnl += flatten_pnl
        position.shares_remaining -= event.fill_quantity
        
        exit_reason = ExitReason.TIME_STOP  # Could also be EOD or circuit breaker
        # The caller sets a more specific reason via metadata if needed
        await self._close_position(position, event.fill_price, exit_reason)
```

### on_tick — Real-time Position Management

```python
    async def on_tick(self, event: TickEvent) -> None:
        """Primary position management — evaluate exit conditions on every tick.
        
        Only processes ticks for symbols with open managed positions.
        """
        positions = self._managed_positions.get(event.symbol)
        if not positions:
            return  # No managed positions for this symbol
        
        for position in positions:
            if position.is_fully_closed:
                continue
            
            # Update high watermark
            if event.price > position.high_watermark:
                position.high_watermark = event.price
            
            # Check trailing stop (if enabled)
            if self._config.enable_trailing_stop and position.t1_filled:
                trail_distance = (
                    position.high_watermark
                    * self._config.trailing_stop_atr_multiplier
                    * 0.01  # Simplified: use % instead of ATR for V1
                )
                trailing_stop_price = position.high_watermark - trail_distance
                if event.price <= trailing_stop_price:
                    await self._flatten_position(
                        position, reason="trailing_stop"
                    )
                    continue
            
            # Check T2 target (market order, don't wait for limit fill)
            if (
                position.t1_filled
                and position.t2_price > 0
                and event.price >= position.t2_price
            ):
                await self._flatten_position(position, reason="t2_target")
                continue
```

### on_cancel Handler

```python
    async def on_cancel(self, event: OrderCancelledEvent) -> None:
        """Handle order cancellation from broker.
        
        Remove from pending orders. If it was a stop order, we need to
        ensure the position still has protection.
        """
        pending = self._pending_orders.pop(event.order_id, None)
        if pending is None:
            return  # Not our order
        
        logger.warning(
            "Order cancelled: %s (type=%s, symbol=%s, reason=%s)",
            event.order_id, pending.order_type, pending.symbol, event.reason,
        )
        
        if pending.order_type == "stop":
            # Critical: position may be unprotected
            positions = self._managed_positions.get(pending.symbol, [])
            for pos in positions:
                if pos.stop_order_id == event.order_id:
                    pos.stop_order_id = None
                    # Try to resubmit stop
                    logger.warning(
                        "Stop order cancelled for %s. Resubmitting.",
                        pending.symbol,
                    )
                    await self._submit_stop_order(
                        pos, pos.shares_remaining, pos.stop_price
                    )
                    break
```

### Fallback Poll Loop

```python
    async def _poll_loop(self) -> None:
        """Runs every N seconds. Handles time-based exits and EOD flatten."""
        while self._running:
            try:
                await asyncio.sleep(self._config.fallback_poll_interval_seconds)
                if not self._running:
                    break
                
                now = self._clock.now()
                
                # Check EOD flatten (MD-4b-2)
                if not self._flattened_today:
                    et_tz = ZoneInfo(self._config.eod_flatten_timezone)
                    now_et = now.astimezone(et_tz) if now.tzinfo else now
                    flatten_time = time.fromisoformat(self._config.eod_flatten_time)
                    if now_et.time() >= flatten_time:
                        await self.eod_flatten()
                        self._flattened_today = True
                        continue
                
                # Check time stops on all positions
                for symbol, positions in list(self._managed_positions.items()):
                    for position in positions:
                        if position.is_fully_closed:
                            continue
                        
                        # Time stop: position open too long
                        elapsed_minutes = (
                            now - position.entry_time
                        ).total_seconds() / 60
                        if elapsed_minutes >= self._config.max_position_duration_minutes:
                            logger.info(
                                "Time stop for %s: open %.1f min (limit=%d)",
                                symbol, elapsed_minutes,
                                self._config.max_position_duration_minutes,
                            )
                            await self._flatten_position(
                                position, reason="time_stop"
                            )
                
                # Check entry timeouts
                now_ts = now.timestamp() if hasattr(now, 'timestamp') else 0
                for order_id, pending in list(self._pending_orders.items()):
                    if pending.order_type == "entry":
                        # Entry timeout check would need order submission time
                        # For V1, we rely on market orders filling immediately
                        pass
                
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in fallback poll loop")
```

### EOD Flatten and Emergency Flatten

```python
    async def eod_flatten(self) -> None:
        """Close all positions at market. Scheduled at eod_flatten_time.
        
        1. Cancel all open orders (stops, targets)
        2. Close all remaining positions at market
        3. Publish PositionClosedEvent for each
        """
        logger.info("EOD flatten triggered — closing all positions")
        
        for symbol, positions in list(self._managed_positions.items()):
            for position in positions:
                if not position.is_fully_closed:
                    await self._flatten_position(position, reason="eod_flatten")
    
    async def emergency_flatten(self) -> None:
        """Close everything immediately. Used by circuit breakers.
        
        Same as eod_flatten but callable at any time.
        """
        logger.warning("EMERGENCY FLATTEN — closing all positions immediately")
        await self.eod_flatten()
    
    async def _on_circuit_breaker(self, event: CircuitBreakerEvent) -> None:
        """Handle circuit breaker event — trigger emergency flatten."""
        logger.warning("Circuit breaker triggered: %s", event.reason)
        await self.emergency_flatten()
```

### Helper Methods

```python
    async def _submit_stop_order(
        self, position: ManagedPosition, shares: int, stop_price: float
    ) -> None:
        """Submit a stop-loss order and track it."""
        try:
            order = Order(
                symbol=position.symbol,
                side="sell",
                quantity=shares,
                order_type="stop",
                stop_price=stop_price,
            )
            result = await self._broker.place_order(order)
            position.stop_order_id = result.order_id
            
            self._pending_orders[result.order_id] = PendingManagedOrder(
                order_id=result.order_id,
                symbol=position.symbol,
                strategy_id=position.strategy_id,
                order_type="stop",
                shares=shares,
                signal=None,
            )
        except Exception:
            logger.exception(
                "Failed to submit stop order for %s. Retrying once.",
                position.symbol,
            )
            # Retry once (MD-4b config: stop_retry_max=1)
            try:
                result = await self._broker.place_order(order)
                position.stop_order_id = result.order_id
                self._pending_orders[result.order_id] = PendingManagedOrder(
                    order_id=result.order_id,
                    symbol=position.symbol,
                    strategy_id=position.strategy_id,
                    order_type="stop",
                    shares=shares,
                    signal=None,
                )
            except Exception:
                logger.exception(
                    "Stop retry failed for %s. Emergency flattening.",
                    position.symbol,
                )
                await self._flatten_position(position, reason="stop_order_failure")
    
    async def _submit_t1_order(
        self, position: ManagedPosition, shares: int, limit_price: float
    ) -> None:
        """Submit a T1 limit sell order and track it."""
        try:
            order = Order(
                symbol=position.symbol,
                side="sell",
                quantity=shares,
                order_type="limit",
                limit_price=limit_price,
            )
            result = await self._broker.place_order(order)
            position.t1_order_id = result.order_id
            
            self._pending_orders[result.order_id] = PendingManagedOrder(
                order_id=result.order_id,
                symbol=position.symbol,
                strategy_id=position.strategy_id,
                order_type="t1_target",
                shares=shares,
                signal=None,
            )
        except Exception:
            logger.exception(
                "Failed to submit T1 order for %s", position.symbol
            )
    
    async def _flatten_position(
        self, position: ManagedPosition, reason: str
    ) -> None:
        """Cancel all open orders for this position and submit market sell."""
        # Cancel stop order
        if position.stop_order_id:
            try:
                await self._broker.cancel_order(position.stop_order_id)
            except Exception:
                logger.debug("Could not cancel stop %s", position.stop_order_id)
            self._pending_orders.pop(position.stop_order_id, None)
            position.stop_order_id = None
        
        # Cancel T1 if still open
        if position.t1_order_id and not position.t1_filled:
            try:
                await self._broker.cancel_order(position.t1_order_id)
            except Exception:
                logger.debug("Could not cancel T1 %s", position.t1_order_id)
            self._pending_orders.pop(position.t1_order_id, None)
            position.t1_order_id = None
        
        # Submit market sell for remaining shares
        if position.shares_remaining > 0:
            try:
                order = Order(
                    symbol=position.symbol,
                    side="sell",
                    quantity=position.shares_remaining,
                    order_type="market",
                )
                result = await self._broker.place_order(order)
                self._pending_orders[result.order_id] = PendingManagedOrder(
                    order_id=result.order_id,
                    symbol=position.symbol,
                    strategy_id=position.strategy_id,
                    order_type="flatten",
                    shares=position.shares_remaining,
                    signal=None,
                )
            except Exception:
                logger.exception(
                    "CRITICAL: Failed to flatten %s (%d shares remain unprotected)",
                    position.symbol, position.shares_remaining,
                )
    
    async def _close_position(
        self, position: ManagedPosition, exit_price: float, exit_reason: ExitReason
    ) -> None:
        """Finalize a fully closed position. Log trade, publish event, clean up."""
        hold_seconds = int(
            (self._clock.now() - position.entry_time).total_seconds()
        )
        
        # Publish PositionClosedEvent
        await self._event_bus.publish(PositionClosedEvent(
            position_id=generate_ulid(),
            exit_price=exit_price,
            realized_pnl=position.realized_pnl,
            exit_reason=exit_reason,
            hold_duration_seconds=hold_seconds,
        ))
        
        # Log trade
        if self._trade_logger:
            await self._trade_logger.log_trade(
                strategy_id=position.strategy_id,
                symbol=position.symbol,
                side="buy",
                entry_price=position.entry_price,
                exit_price=exit_price,
                shares=position.shares_total,
                pnl=position.realized_pnl,
                hold_duration_seconds=hold_seconds,
                exit_reason=exit_reason.value,
            )
        
        # Remove from managed positions
        positions = self._managed_positions.get(position.symbol, [])
        if position in positions:
            positions.remove(position)
        if not positions:
            self._managed_positions.pop(position.symbol, None)
        
        logger.info(
            "Position closed: %s | PnL: %.2f | Reason: %s | Hold: %ds",
            position.symbol, position.realized_pnl,
            exit_reason.value, hold_seconds,
        )
    
    def _find_position_by_t1_order(
        self, positions: list[ManagedPosition], order_id: str
    ) -> ManagedPosition | None:
        """Find position whose T1 order matches the given order_id."""
        return next(
            (p for p in positions if p.t1_order_id == order_id),
            None,
        )
    
    def _find_position_by_stop_order(
        self, positions: list[ManagedPosition], order_id: str
    ) -> ManagedPosition | None:
        """Find position whose stop order matches the given order_id."""
        return next(
            (p for p in positions if p.stop_order_id == order_id),
            None,
        )
    
    def reset_daily_state(self) -> None:
        """Reset for new trading day. Called by orchestrator pre-market."""
        self._flattened_today = False
        # Positions should be empty after EOD flatten, but clear just in case
        self._managed_positions.clear()
        self._pending_orders.clear()
    
    @property
    def has_open_positions(self) -> bool:
        """True if any managed positions are still open."""
        return any(
            any(not p.is_fully_closed for p in positions)
            for positions in self._managed_positions.values()
        )
    
    @property
    def open_position_count(self) -> int:
        """Number of currently open managed positions."""
        return sum(
            sum(1 for p in positions if not p.is_fully_closed)
            for positions in self._managed_positions.values()
        )
```

---

## Component 4: AlpacaScanner

### File: `argus/data/alpaca_scanner.py`

```python
"""AlpacaScanner — live pre-market gap scanner using Alpaca snapshots.

Replaces StaticScanner for live trading. Scans a configurable universe
of symbols for gap percentage, volume, and price criteria matching
active strategies' requirements.

Uses Alpaca's StockHistoricalDataClient.get_stock_snapshot() for
batch snapshot retrieval.
"""

import logging
from argus.core.config import AlpacaScannerConfig
from argus.data.scanner import Scanner
from argus.models.strategy import ScannerCriteria
from argus.core.events import WatchlistItem

logger = logging.getLogger(__name__)


class AlpacaScanner(Scanner):
    """Live stock scanner using Alpaca's snapshot API."""
    
    def __init__(
        self,
        config: AlpacaScannerConfig,
        alpaca_config,  # AlpacaConfig from Sprint 4a
    ) -> None:
        self._config = config
        self._alpaca_config = alpaca_config
        self._client = None  # StockHistoricalDataClient, initialized in start()
    
    async def start(self) -> None:
        """Initialize the Alpaca data client."""
        from alpaca.data.historical import StockHistoricalDataClient
        
        self._client = StockHistoricalDataClient(
            api_key=self._alpaca_config.api_key,
            secret_key=self._alpaca_config.secret_key,
        )
        logger.info(
            "AlpacaScanner started with %d universe symbols",
            len(self._config.universe_symbols),
        )
    
    async def stop(self) -> None:
        """Clean up client resources."""
        self._client = None
        logger.info("AlpacaScanner stopped")
    
    async def scan(
        self, criteria_list: list[ScannerCriteria]
    ) -> list[WatchlistItem]:
        """Scan universe using Alpaca snapshots, filter by criteria.
        
        1. Merge criteria from all active strategies (use widest ranges)
        2. Fetch snapshots for universe symbols
        3. Filter by merged criteria
        4. Sort by gap_pct descending
        5. Return top max_symbols_returned as WatchlistItems
        """
        if not self._client:
            logger.error("AlpacaScanner not started")
            return []
        
        if not self._config.universe_symbols:
            return []
        
        # Merge criteria: use the widest acceptable ranges
        merged = self._merge_criteria(criteria_list)
        
        # Fetch snapshots
        try:
            from alpaca.data.requests import StockSnapshotRequest
            
            request = StockSnapshotRequest(
                symbol_or_symbols=self._config.universe_symbols
            )
            snapshots = self._client.get_stock_snapshot(request)
        except Exception:
            logger.exception("Failed to fetch Alpaca snapshots")
            return []
        
        # Filter and build watchlist
        items = []
        for symbol, snapshot in snapshots.items():
            item = self._evaluate_snapshot(symbol, snapshot, merged)
            if item is not None:
                items.append(item)
        
        # Sort by gap_pct descending (strongest gappers first)
        items.sort(key=lambda x: abs(x.gap_pct), reverse=True)
        
        # Cap results
        return items[:self._config.max_symbols_returned]
    
    def _evaluate_snapshot(
        self, symbol: str, snapshot, merged: ScannerCriteria
    ) -> WatchlistItem | None:
        """Evaluate a single snapshot against criteria. Return WatchlistItem or None."""
        try:
            daily_bar = snapshot.daily_bar
            prev_bar = snapshot.previous_daily_bar
            
            if daily_bar is None or prev_bar is None:
                return None
            if prev_bar.close is None or prev_bar.close <= 0:
                return None
            
            # Gap calculation
            open_price = daily_bar.open
            if open_price is None or open_price <= 0:
                # Pre-market: use latest trade as proxy
                if snapshot.latest_trade and snapshot.latest_trade.price:
                    open_price = snapshot.latest_trade.price
                else:
                    return None
            
            gap_pct = (open_price - prev_bar.close) / prev_bar.close
            
            # Price filter
            if open_price < self._config.min_price:
                return None
            if open_price > self._config.max_price:
                return None
            
            # Gap filter (from merged criteria)
            if merged.min_gap_pct is not None and gap_pct < merged.min_gap_pct:
                return None
            if merged.max_gap_pct is not None and gap_pct > merged.max_gap_pct:
                return None
            
            # Volume filter
            yesterday_volume = prev_bar.volume or 0
            if yesterday_volume < self._config.min_volume_yesterday:
                return None
            
            # Calculate relative volume if minute bar available
            relative_volume = 0.0
            if snapshot.minute_bar and snapshot.minute_bar.volume:
                # Rough RVOL: current minute volume vs average
                relative_volume = float(snapshot.minute_bar.volume)
            
            return WatchlistItem(
                symbol=symbol,
                gap_pct=gap_pct,
                premarket_volume=int(daily_bar.volume or 0),
            )
            
        except (AttributeError, TypeError, ZeroDivisionError):
            logger.debug("Incomplete snapshot data for %s, skipping", symbol)
            return None
    
    def _merge_criteria(
        self, criteria_list: list[ScannerCriteria]
    ) -> ScannerCriteria:
        """Merge criteria from multiple strategies using widest ranges.
        
        Takes the minimum of all min values and maximum of all max values
        so any symbol that ANY strategy wants gets through.
        """
        if not criteria_list:
            return ScannerCriteria()
        
        min_gap = None
        max_gap = None
        
        for c in criteria_list:
            if c.min_gap_pct is not None:
                if min_gap is None or c.min_gap_pct < min_gap:
                    min_gap = c.min_gap_pct
            if c.max_gap_pct is not None:
                if max_gap is None or c.max_gap_pct > max_gap:
                    max_gap = c.max_gap_pct
        
        return ScannerCriteria(
            min_gap_pct=min_gap,
            max_gap_pct=max_gap,
        )
```

---

## Component 5: Tests

### Test File: `tests/execution/test_order_manager.py`

Target: ~25 tests. All use mocked Broker. No network calls.

#### Test Infrastructure

```python
"""Tests for Order Manager.

All broker calls are mocked. No network calls.
Uses FixedClock for deterministic time control.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    ExitReason,
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderSubmittedEvent,
    OrderType,
    PositionClosedEvent,
    PositionOpenedEvent,
    Side,
    SignalEvent,
    TickEvent,
)
from argus.execution.order_manager import (
    ManagedPosition,
    OrderManager,
    PendingManagedOrder,
)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def mock_broker():
    broker = AsyncMock()
    # Default: place_order returns a result with an order_id
    broker.place_order = AsyncMock(
        side_effect=lambda order: MagicMock(order_id=f"ORD-{order.symbol}-{order.order_type}")
    )
    broker.cancel_order = AsyncMock()
    return broker


@pytest.fixture
def fixed_clock():
    """Clock fixed at 10:00 AM ET on a trading day."""
    from argus.core.clock import FixedClock
    return FixedClock(datetime(2026, 2, 16, 10, 0, 0))


@pytest.fixture
def config():
    return OrderManagerConfig()


@pytest.fixture
def order_manager(event_bus, mock_broker, fixed_clock, config):
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )


def make_signal(
    symbol="AAPL",
    entry_price=150.0,
    stop_price=148.0,
    target_prices=(152.0, 154.0),
    share_count=100,
    strategy_id="orb_breakout",
) -> SignalEvent:
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        share_count=share_count,
        rationale="Test signal",
    )


def make_approved(signal=None, modifications=None) -> OrderApprovedEvent:
    if signal is None:
        signal = make_signal()
    return OrderApprovedEvent(signal=signal, modifications=modifications)
```

#### Test List (25 tests)

**Happy path (7):**
1. `test_submit_signal_places_entry_order` — OrderApprovedEvent → market order submitted to broker
2. `test_entry_fill_creates_managed_position` — Fill event → ManagedPosition created, stop + T1 orders placed
3. `test_t1_fill_moves_stop_to_breakeven` — T1 fill → old stop cancelled, new stop at entry + buffer
4. `test_t2_reached_closes_remaining` — Tick at/above T2 → remaining shares closed
5. `test_stop_fill_closes_position` — Stop fill → position fully closed
6. `test_full_lifecycle_t1_then_stop` — Entry → T1 → breakeven stop = 2 partial exits
7. `test_full_lifecycle_t1_then_t2` — Entry → T1 → T2 = full profit taken

**T1/T2 split (2):**
8. `test_t1_shares_are_half_of_total` — Verify T1 limit order is for 50% of entry shares
9. `test_partial_entry_adjusts_t1_shares` — 80 of 100 shares fill → T1 for 40

**Time-based exits (3):**
10. `test_time_stop_closes_position` — Position open > max_duration → fallback_poll closes it
11. `test_eod_flatten_closes_all_positions` — At 3:50 PM ET, all positions closed
12. `test_eod_flatten_no_positions_is_noop` — No positions → no broker calls

**Emergency (2):**
13. `test_emergency_flatten_closes_everything` — Immediate close all
14. `test_emergency_flatten_cancels_open_orders` — All pending orders cancelled first

**Error handling (4):**
15. `test_stop_order_failure_retries` — If stop order fails, retry once
16. `test_stop_order_failure_after_retry_flattens` — If retry also fails, emergency flatten
17. `test_unknown_fill_event_ignored` — Fill for unknown order_id → no crash
18. `test_approved_with_no_signal_ignored` — OrderApprovedEvent with signal=None → no crash

**Edge cases (3):**
19. `test_stop_fills_before_t1_cancels_t1` — Stop triggered → T1 cancelled
20. `test_on_tick_only_for_managed_symbols` — Ticks for non-managed symbols → ignored
21. `test_position_tracking_after_full_close` — After close, symbol removed from managed positions

**Event Bus integration (4):**
22. `test_subscribes_to_correct_events_on_start` — Verifies all 5 event subscriptions
23. `test_publishes_position_opened_event` — On entry fill, PositionOpenedEvent published
24. `test_publishes_position_closed_event` — On full close, PositionClosedEvent published
25. `test_publishes_order_submitted_events` — Each broker order → OrderSubmittedEvent

### Test File: `tests/data/test_alpaca_scanner.py`

Target: ~10 tests. All use mocked StockHistoricalDataClient.

```python
"""Tests for AlpacaScanner.

All Alpaca API calls are mocked. No network calls.
"""

import pytest
from unittest.mock import MagicMock, patch
from argus.core.config import AlpacaScannerConfig
from argus.data.alpaca_scanner import AlpacaScanner
from argus.models.strategy import ScannerCriteria


def make_snapshot(
    open_price=105.0,
    prev_close=100.0,
    prev_volume=2_000_000,
    minute_volume=5000,
    latest_trade_price=None,
):
    """Create a mock Alpaca snapshot."""
    snapshot = MagicMock()
    snapshot.daily_bar = MagicMock()
    snapshot.daily_bar.open = open_price
    snapshot.daily_bar.volume = 50000
    snapshot.previous_daily_bar = MagicMock()
    snapshot.previous_daily_bar.close = prev_close
    snapshot.previous_daily_bar.volume = prev_volume
    snapshot.minute_bar = MagicMock()
    snapshot.minute_bar.volume = minute_volume
    snapshot.latest_trade = MagicMock()
    snapshot.latest_trade.price = latest_trade_price or open_price
    return snapshot


@pytest.fixture
def scanner_config():
    return AlpacaScannerConfig(
        universe_symbols=["AAPL", "TSLA", "NVDA", "AMD", "MSFT"],
        min_price=5.0,
        max_price=500.0,
        min_volume_yesterday=1_000_000,
        max_symbols_returned=10,
    )


@pytest.fixture
def alpaca_config():
    config = MagicMock()
    config.api_key = "test_key"
    config.secret_key = "test_secret"
    return config
```

**Test list (10):**
1. `test_scan_returns_watchlist_items` — Mock snapshots → WatchlistItems returned
2. `test_filters_by_gap_percentage` — Only symbols within min/max gap returned
3. `test_filters_by_price_range` — Symbols outside price range excluded
4. `test_filters_by_minimum_volume` — Low-volume symbols excluded
5. `test_sorts_by_gap_descending` — Strongest gappers first
6. `test_respects_max_symbols_limit` — Returns at most max_symbols_returned
7. `test_handles_missing_snapshot_data` — Incomplete snapshot → skipped
8. `test_gap_calculation_correct` — Verify gap = (open - prev_close) / prev_close
9. `test_empty_universe_returns_empty` — No symbols configured → empty list
10. `test_all_symbols_filtered_out` — No matches → empty list

### Test File: `tests/test_integration_sprint4b.py`

Target: 3 integration tests with fully mocked broker and data service.

**Tests:**
1. `test_full_pipeline_happy_path` — Scanner → Data → Strategy → Risk → Order Manager → Broker → T1 fill → T2 fill
2. `test_full_pipeline_stop_out` — Same setup but price reverses → stop fills
3. `test_full_pipeline_eod_flatten` — Position open at 3:50 PM → EOD flatten closes it

---

## Build Order

1. **Config models** — `OrderManagerConfig`, `AlpacaScannerConfig` in `argus/core/config.py`
2. **Data models** — `ManagedPosition`, `PendingManagedOrder` dataclasses
3. **Order Manager** — full implementation
4. **Order Manager tests** (~25 tests)
5. **AlpacaScanner** — Scanner ABC implementation
6. **AlpacaScanner tests** (~10 tests)
7. **Integration test** (3 tests)
8. **Full test suite pass + ruff clean**
9. **Commit and push**

---

## New Files

```
argus/execution/order_manager.py       # NEW
argus/data/alpaca_scanner.py           # NEW
config/order_manager.yaml              # NEW
tests/execution/test_order_manager.py  # NEW
tests/data/test_alpaca_scanner.py      # NEW
tests/test_integration_sprint4b.py     # NEW
```

**Modified files:**
```
argus/core/config.py                   # ADD OrderManagerConfig, AlpacaScannerConfig
config/scanner.yaml                    # ADD alpaca_scanner section
```

---

## Decisions In Effect (Do Not Relitigate)

| ID | Rule |
|----|------|
| DEC-011 | Long only for V1 |
| DEC-012 | ORB stop at midpoint of opening range |
| DEC-027 | Approve-with-modification (reduce shares, tighten targets, never widen stops) |
| DEC-028 | Daily-stateful, session-stateless |
| DEC-029 | Event Bus is sole streaming mechanism |
| DEC-030 | Order Manager: tick-driven + 5s poll + EOD flatten |
| DEC-032 | Pydantic BaseModel for all config |
| DEC-033 | Type-only Event Bus subscription |
| DEC-038 | ORB entry is market order + chase protection |
| DEC-039/MD-4a-6 | Bracket: single T1. Order Manager handles T1/T2 split. |
| MD-4b-1 | Stop management: cancel and resubmit (not modify) |
| MD-4b-2 | EOD flatten: checked in fallback poll |
| MD-4b-3 | Trade logging: Order Manager calls directly |
| MD-4b-4 | Scanner universe: static config list |
| MD-4b-5 | Exit rules: prices from signal, time/trail from config |

---

## Adaptation Notes for Claude Code

The code in this spec is a **detailed guide**, not copy-paste-ready. Claude Code must:

1. **Check actual imports and class names** in the repo. The spec references classes like `Order`, `Broker`, `Clock` — verify the exact names and locations in the codebase.
2. **Check the Broker ABC** for the exact method signatures of `place_order`, `cancel_order`, and what they return. The spec assumes `result.order_id`.
3. **Check if `TradeLogger.log_trade()` exists** with the parameters shown, or if the interface is different. If `log_partial_exit` doesn't exist, skip it for now and log via the standard `log_trade`.
4. **Check `generate_ulid()`** location and import.
5. **Check the `Order` dataclass** for fields like `stop_price` and `limit_price` — they may be named differently.
6. **Adapt test fixtures** to use the actual test infrastructure patterns established in Sprints 1-4a.
7. **Run `ruff check`** after implementation and fix any linting issues.
8. **Run the full test suite** (`pytest`) to ensure no regressions.

---

## Success Criteria

Sprint 4b is done when:
- [ ] OrderManagerConfig and AlpacaScannerConfig Pydantic models created
- [ ] ManagedPosition and PendingManagedOrder dataclasses implemented
- [ ] Order Manager converts approved signals to broker orders with T1/T2 split
- [ ] Order Manager moves stop to breakeven when T1 fills
- [ ] Fallback poll catches time stops
- [ ] EOD flatten closes all positions at configured time
- [ ] Emergency flatten works for circuit breakers
- [ ] AlpacaScanner fetches snapshots and filters by gap/volume/price criteria
- [ ] Integration test proves full pipeline: scanner → data → strategy → risk → order manager → broker
- [ ] All tests pass (target: ~320+, up from 282)
- [ ] Ruff clean
- [ ] Committed and pushed

---

## Deferred Items / Sprint 5 Cleanup

- Add `symbol` field to `OrderFilledEvent` and `OrderCancelledEvent` (currently inferred from internal tracking)
- Per-strategy exit rules (time_stop_minutes, trailing_stop) rather than global Order Manager config
- APScheduler for EOD flatten (currently piggybacks on poll loop)
- Entry timeout implementation (market orders assumed to fill immediately in V1)
- `TradeLogger.log_partial_exit()` if not yet implemented
- Health monitoring and heartbeat integration

---

*End of Sprint 4b Implementation Spec*
