# ARGUS — Sprint 4b Review + Planning Handoff

> **Date:** February 15, 2026
> **Purpose:** Start a fresh conversation to produce the Sprint 4b implementation spec.
> **Instructions:** Paste this document as your first message. Claude will produce the full Sprint 4b spec.

---

## What Happened Before This Conversation

### Sprint 1 (Complete — 52 tests)
Config system, Event Bus, data models, database (SQLite + aiosqlite), Trade Logger.

### Sprint 2 (Complete — 112 tests after polish)
Broker ABC, SimulatedBroker, BrokerRouter, Risk Manager (three-level, PDT tracking, circuit breakers, approve-with-modification, state reconstruction).

### Sprint 3 (Complete — 222 tests)
BaseStrategy ABC, Scanner ABC + StaticScanner, DataService ABC + ReplayDataService (Parquet, 1m candles, indicator computation — VWAP, ATR, SMA 9/20/50, RVOL), OrbBreakout strategy (full entry/exit logic), integration test.

### Sprint 4a (Complete + Polished — 282 tests)
Clock protocol (SystemClock + FixedClock, DEF-001 resolved), AlpacaConfig, AlpacaDataService (WebSocket bars + trades via alpaca-py, indicator warm-up, stale data monitor, reconnection with backoff), AlpacaBroker (REST + WebSocket via alpaca-py, bracket orders with single T1 target, ULID↔UUID order ID mapping), integration tests.

**Sprint 4a Polish (Complete):** Flaky reconnection test fixed (mocked asyncio.sleep), import random moved to module level, 5 missing broker tests added, all ruff warnings resolved (SIM105, SIM117). Final: 282 tests, 0 flaky, ruff clean. Commits: 738aab8, b95db95.

---

## Sprint 4b Scope

Sprint 4b delivers two components plus integration wiring:

1. **Order Manager** (`argus/execution/order_manager.py`) — The missing link between approved signals and managed positions. Converts `OrderApprovedEvent` to broker orders, then actively manages open positions through their full lifecycle until exit.

2. **AlpacaScanner** (`argus/data/alpaca_scanner.py`) — Live pre-market gap scanner replacing StaticScanner. Implements Scanner ABC using Alpaca's snapshot API.

3. **Integration** — Full pipeline end-to-end: AlpacaDataService → AlpacaScanner → OrbBreakout → RiskManager → OrderManager → AlpacaBroker

**Starting state:** 282 tests, 0 flaky, ruff clean.
**Target end state:** ~320+ tests, 0 flaky, ruff clean, committed and pushed.

---

## What This Sprint Does NOT Include

- Health monitoring / heartbeat (Sprint 5)
- Stale data market hours check (Sprint 5 — RSK-015 mitigation)
- Multi-timeframe candle building (deferred)
- Strategy state reconstruction on crash (Sprint 5 hardening)
- Shadow system
- Any new strategies

---

## Component 1: Order Manager (`argus/execution/order_manager.py`)

### Purpose

The Order Manager is the execution layer between risk approval and the broker. It:
1. Receives `OrderApprovedEvent` from Risk Manager
2. Converts approved signals into broker orders (handling T1/T2 split that Alpaca can't do natively)
3. Subscribes to `TickEvent` for symbols with open positions
4. Evaluates exit conditions on every tick (stop-to-breakeven, trailing stop, price targets)
5. Runs a 5-second fallback poll for time-based exits (time stops, inactivity)
6. Flattens all positions at EOD (scheduled task at configurable time, default 3:50 PM EST)
7. Provides emergency flatten for circuit breakers

### Architecture

Per DEC-030 (Order Manager Position Management Model):

```
              OrderApprovedEvent
                     │
                     ▼
            ┌─────────────────┐
            │  Order Manager   │
            │                  │
            │  submit_signal() │──→ Broker.place_order()
            │                  │      (entry + stop + T1)
            │  on_fill()       │←── OrderFilledEvent
            │    │             │      - Subscribe to TickEvent for symbol
            │    │             │      - Track position in _managed_positions
            │    ▼             │
            │  on_tick()       │←── TickEvent (primary management)
            │    │             │      - Check stop-to-breakeven
            │    │             │      - Check trailing stop
            │    │             │      - Check T2 target
            │    │             │
            │  fallback_poll() │    (5-second loop)
            │    │             │      - Check time stops
            │    │             │      - Check position max duration
            │    │             │
            │  eod_flatten()   │    (scheduled at 3:50 PM EST)
            │    │             │      - Close all remaining positions
            │    │             │
            │  emergency_flatten()  (circuit breaker trigger)
            │                  │      - Immediate close all
            └─────────────────┘
```

### Config: `config/order_manager.yaml`

```yaml
eod_flatten_time: "15:50"          # EST, 10 min before close
eod_flatten_timezone: "America/New_York"
fallback_poll_interval_seconds: 5
enable_stop_to_breakeven: true
breakeven_buffer_pct: 0.001        # Move stop to entry + 0.1% (not exact entry)
enable_trailing_stop: false        # V1: disabled by default, strategies can override
trailing_stop_atr_multiplier: 2.0  # If enabled: trail at 2x ATR below high
max_position_duration_minutes: 120 # Hard time stop — close if position open > 2 hours
```

Create a `OrderManagerConfig` Pydantic model in `argus/core/config.py`.

### Interface

```python
class OrderManager:
    """Manages the full lifecycle of trades from approval to exit.
    
    Subscribes to OrderApprovedEvent, OrderFilledEvent, OrderCancelledEvent,
    and TickEvent via the Event Bus. Runs a fallback poll loop for time-based
    exits and a scheduled EOD flatten.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        broker: Broker,
        clock: Clock,
        config: OrderManagerConfig,
    ) -> None:
        """Initialize Order Manager.
        
        Args:
            event_bus: For subscribing to events and publishing position events.
            broker: For placing/modifying/cancelling orders.
            clock: For time checks (EOD flatten, time stops).
            config: Order Manager configuration.
        """
        self._event_bus = event_bus
        self._broker = broker
        self._clock = clock
        self._config = config
        
        # Managed positions: keyed by symbol
        self._managed_positions: dict[str, ManagedPosition] = {}
        
        # Pending orders awaiting fill: keyed by order_id
        self._pending_orders: dict[str, PendingManagedOrder] = {}
        
        # Fallback poll task
        self._poll_task: asyncio.Task | None = None
        
        # EOD flatten task  
        self._eod_task: asyncio.Task | None = None
        
        # Running flag
        self._running: bool = False
    
    async def start(self) -> None:
        """Start the Order Manager.
        
        1. Subscribe to OrderApprovedEvent, OrderFilledEvent, 
           OrderCancelledEvent, TickEvent on the Event Bus
        2. Start the fallback poll loop (5-second interval)
        3. Schedule the EOD flatten task
        """
    
    async def stop(self) -> None:
        """Stop the Order Manager. Cancel poll and EOD tasks."""
    
    async def on_approved(self, event: OrderApprovedEvent) -> None:
        """Handle an approved signal from the Risk Manager.
        
        1. Create entry order (market) via broker
        2. Create stop order at signal's stop_price
        3. Create T1 target order (limit at target_prices[0]) for 50% of shares
        4. Store all as PendingManagedOrder awaiting fill confirmation
        5. Publish OrderSubmittedEvent
        
        T1/T2 Split Logic (works around Alpaca's single-target bracket limitation):
        - Submit entry as market order (NOT a bracket order)
        - On fill: submit stop order for full position
        - On fill: submit T1 limit order for 50% of shares
        - T2 is tracked internally — when T1 fills, remaining shares ride to T2
          or get stopped out / time-stopped / EOD-flattened
        
        Why not use Alpaca bracket orders here: Alpaca brackets support only 
        ONE take-profit. ORB needs T1 (1R, 50%) and T2 (2R, 50%). The Order 
        Manager handles this split manually.
        """
    
    async def on_fill(self, event: OrderFilledEvent) -> None:
        """Handle an order fill event.
        
        Cases:
        a) Entry fill → Create ManagedPosition, submit stop + T1 orders,
           subscribe to TickEvent for this symbol
        b) T1 fill → Move stop to breakeven (entry + buffer), 
           remaining shares now targeting T2. Cancel old stop, submit new stop.
        c) Stop fill → Position closed. Unsubscribe from TickEvent.
           Record trade via TradeLogger.
        d) T2 fill → Position fully closed. Unsubscribe. Record trade.
        e) Partial fill → Update quantities, continue tracking.
        """
    
    async def on_cancel(self, event: OrderCancelledEvent) -> None:
        """Handle order cancellation (e.g., broker rejected)."""
    
    async def on_tick(self, event: TickEvent) -> None:
        """Primary position management — called on every tick for managed symbols.
        
        For each managed position on this symbol:
        1. Update high watermark (for trailing stop)
        2. If trailing stop enabled and price < high - trail_distance:
           → Close position at market
        3. If T2 target reached (price >= target_prices[1]):
           → Close remaining shares at market (don't wait for limit fill)
        
        Note: Stop-to-breakeven is handled in on_fill() when T1 fills,
        not here. The broker-side stop order handles the actual stop exit.
        on_tick() is for conditions the broker can't evaluate autonomously.
        """
    
    async def fallback_poll(self) -> None:
        """Runs every 5 seconds. Handles time-based exits.
        
        For each managed position:
        1. Time stop: if position open > max_position_duration_minutes → close
        2. Time window: if past strategy's latest_entry + buffer → close
        
        This catches positions in illiquid stocks where ticks may be infrequent.
        """
    
    async def eod_flatten(self) -> None:
        """Scheduled at config.eod_flatten_time (default 3:50 PM EST).
        
        1. Cancel all open orders (stops, targets)
        2. Close all remaining positions at market
        3. Publish PositionClosedEvent for each
        4. Log all trades
        """
    
    async def emergency_flatten(self) -> None:
        """Close everything immediately. Used by circuit breakers.
        
        Same as eod_flatten but callable at any time.
        Also called by Risk Manager when circuit breaker trips.
        """
```

### ManagedPosition Dataclass

```python
@dataclass
class ManagedPosition:
    """Tracks a position being actively managed by the Order Manager."""
    symbol: str
    strategy_id: str
    side: OrderSide                # BUY (long only in V1)
    entry_price: float             # Actual fill price
    entry_time: datetime           # When entry filled
    shares_total: int              # Original total shares
    shares_remaining: int          # Shares still open
    stop_price: float              # Current stop price
    stop_order_id: str | None      # Broker-side stop order ID
    t1_price: float                # T1 target price
    t1_order_id: str | None        # Broker-side T1 limit order ID
    t1_shares: int                 # Shares allocated to T1
    t1_filled: bool                # Whether T1 has been hit
    t2_price: float                # T2 target price
    high_watermark: float          # Highest price since entry (for trailing stop)
    exit_rules: ExitRules          # From the strategy's signal
    
    @property
    def is_fully_closed(self) -> bool:
        return self.shares_remaining <= 0


@dataclass  
class PendingManagedOrder:
    """Tracks an order awaiting fill confirmation."""
    order_id: str
    symbol: str
    strategy_id: str
    order_type: str                # "entry", "stop", "t1_target", "t2_target", "flatten"
    signal: OrderApprovedEvent     # Original approved signal (for reference)
```

### Event Subscriptions

The Order Manager subscribes to these events via the Event Bus:

| Event | Handler | Purpose |
|-------|---------|---------|
| `OrderApprovedEvent` | `on_approved()` | New signal approved by Risk Manager |
| `OrderFilledEvent` | `on_fill()` | Entry/stop/target filled |
| `OrderCancelledEvent` | `on_cancel()` | Order rejected or cancelled |
| `TickEvent` | `on_tick()` | Price update for managed symbols |

The Order Manager publishes:
- `OrderSubmittedEvent` — when placing orders with broker
- `PositionClosedEvent` — when a position is fully exited
- Uses `TradeLogger` to record completed trades

### T1/T2 Split — Detailed Flow

This is the most complex part. Here's the exact sequence:

```
1. OrderApprovedEvent arrives (e.g., BUY 100 AAPL @ market, stop=148, T1=152, T2=154)

2. on_approved():
   - Submit market BUY 100 AAPL → entry_order_id
   - Store PendingManagedOrder(order_id=entry_order_id, type="entry")

3. on_fill(entry_fill):  [entry_order_id filled at 150.00]
   - Create ManagedPosition(shares_total=100, shares_remaining=100, ...)
   - Submit STOP SELL 100 AAPL @ 148.00 → stop_order_id  
   - Submit LIMIT SELL 50 AAPL @ 152.00 → t1_order_id  (50% for T1)
   - Store both as PendingManagedOrders
   - Subscribe to TickEvent (will filter for AAPL in on_tick)

4. on_fill(t1_fill):  [t1_order_id filled — 50 shares at 152.00]
   - Cancel old stop (stop_order_id for 100 shares)
   - Submit new STOP SELL 50 AAPL @ 150.10  (breakeven = entry + buffer)
   - Update: shares_remaining=50, t1_filled=True, stop_price=150.10
   - Record T1 partial exit via TradeLogger

5a. on_fill(stop_fill):  [new stop filled — 50 shares at 150.10]
    - Position fully closed. shares_remaining=0.
    - Unsubscribe from TickEvent for AAPL
    - Record final exit via TradeLogger
    - Publish PositionClosedEvent

5b. OR on_tick() detects price >= T2 (154.00):
    - Cancel stop order
    - Submit market SELL 50 AAPL → flatten remaining
    - (on_fill will handle the rest)

5c. OR fallback_poll() detects time stop exceeded:
    - Cancel all open orders for this symbol
    - Submit market SELL 50 AAPL
    
5d. OR eod_flatten() fires at 3:50 PM:
    - Cancel all open orders
    - Submit market SELL for all remaining shares
```

### Edge Cases to Handle

1. **Entry doesn't fill** — Market order should always fill, but handle timeout. If no fill within 30 seconds, cancel and abandon.
2. **Partial entry fill** — Adjust T1 shares proportionally. If only 80 of 100 shares fill, T1 is 40 shares.
3. **T1 doesn't fill (price reverses after touching T1)** — Stop order covers the full position. T1 limit stays open. Normal outcome.
4. **Stop fills before T1** — Full position stopped out. Cancel T1 limit order. Record loss.
5. **Multiple positions same symbol** — Support via list of ManagedPositions per symbol (though ORB config limits to 1 concurrent per symbol, other strategies might not).
6. **Broker rejects order** — Log error, publish alert event. Don't leave positions unprotected — if stop order fails, retry once, then emergency flatten.

### Tests (`tests/execution/test_order_manager.py`)

Target: ~25 tests

**Happy path:**
1. `test_submit_signal_places_entry_order` — OrderApprovedEvent → market order submitted to broker
2. `test_entry_fill_creates_managed_position` — Fill event → ManagedPosition created, stop + T1 orders placed
3. `test_t1_fill_moves_stop_to_breakeven` — T1 fill → old stop cancelled, new stop at entry + buffer
4. `test_t2_reached_closes_remaining` — Tick at/above T2 → remaining shares closed
5. `test_stop_fill_closes_position` — Stop fill → position fully closed, TickEvent unsubscribed
6. `test_full_lifecycle_t1_then_stop` — Entry → T1 fill → stop hit on remaining = 2 partial exits recorded
7. `test_full_lifecycle_t1_then_t2` — Entry → T1 fill → T2 hit = full profit taken

**T1/T2 split:**
8. `test_t1_shares_are_half_of_total` — Verify T1 limit order is for 50% of entry shares
9. `test_partial_entry_adjusts_t1_shares` — If 80 of 100 shares fill, T1 is for 40

**Time-based exits:**
10. `test_time_stop_closes_position` — Position open > max_duration → fallback_poll closes it
11. `test_eod_flatten_closes_all_positions` — At 3:50 PM, all positions closed, all orders cancelled
12. `test_eod_flatten_no_positions_is_noop` — No positions → no broker calls

**Emergency:**
13. `test_emergency_flatten_closes_everything` — Immediate close all, regardless of targets/stops
14. `test_emergency_flatten_cancels_open_orders` — All pending orders cancelled first

**Error handling:**
15. `test_stop_order_failure_retries` — If stop order fails, retry once
16. `test_stop_order_failure_after_retry_flattens` — If retry also fails, emergency flatten
17. `test_unknown_fill_event_ignored` — Fill for unknown order_id → logged, no crash
18. `test_entry_no_fill_timeout` — Entry not filled within timeout → cancel order

**Edge cases:**
19. `test_stop_fills_before_t1_cancels_t1` — Stop triggered → T1 limit cancelled
20. `test_on_tick_only_for_managed_symbols` — Ticks for non-managed symbols → ignored
21. `test_position_tracking_after_full_close` — After close, symbol removed from managed positions

**Integration with Event Bus:**
22. `test_subscribes_to_correct_events_on_start` — Verifies all 4 event subscriptions
23. `test_publishes_position_closed_event` — On full close, PositionClosedEvent published
24. `test_publishes_order_submitted_events` — Each broker order → OrderSubmittedEvent

**All tests use mocked Broker. No network calls.**

---

## Component 2: AlpacaScanner (`argus/data/alpaca_scanner.py`)

### Purpose

Replaces StaticScanner for live trading. Scans for stocks matching ORB criteria pre-market using Alpaca's snapshot API.

### How It Works

Alpaca provides a snapshot endpoint that returns the latest quote, latest trade, latest minute bar, daily bar, and previous daily bar for given symbols. The AlpacaScanner:

1. Maintains a **universe** of symbols to scan (configurable, e.g., top 500 US stocks by volume)
2. At scan time, fetches snapshots for the universe
3. Filters by the ScannerCriteria provided by active strategies (gap %, volume, price range)
4. Returns matching symbols as WatchlistItems with pre-populated metadata

### Alpaca Snapshot API Usage

```python
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockSnapshotRequest

client = StockHistoricalDataClient(api_key, secret_key)

# Get snapshots for multiple symbols
request = StockSnapshotRequest(symbol_or_symbols=["AAPL", "TSLA", "NVDA"])
snapshots = client.get_stock_snapshot(request)

# Each snapshot contains:
# - latest_trade: Trade (price, size, timestamp)
# - latest_quote: Quote (bid, ask, bid_size, ask_size)
# - minute_bar: Bar (open, high, low, close, volume)
# - daily_bar: Bar (today's OHLCV so far)
# - previous_daily_bar: Bar (yesterday's close)
```

### Gap Calculation

```
gap_pct = (daily_bar.open - previous_daily_bar.close) / previous_daily_bar.close
```

If `daily_bar.open` is not yet available (pre-market before open), use `latest_trade.price` as a proxy.

### Config: `config/scanner.yaml` Update

```yaml
# Add alongside existing static config:
scanner_type: "alpaca"   # Switch from "static" to "alpaca" for live
alpaca_scanner:
  universe_source: "config"    # "config" = use list below, future: "dynamic"
  universe_symbols:            # Top liquid US stocks to scan
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
    # ... expand as needed
  min_price: 5.0
  max_price: 500.0
  min_volume_yesterday: 1000000   # Minimum previous-day volume
  max_symbols_returned: 10        # Cap the watchlist size
```

Add `AlpacaScannerConfig` Pydantic model in `argus/core/config.py`.

### Interface

```python
class AlpacaScanner(Scanner):
    """Live stock scanner using Alpaca's snapshot API.
    
    Scans a configurable universe of symbols for gap percentage,
    relative volume, and price criteria matching active strategies.
    """
    
    def __init__(
        self,
        config: AlpacaScannerConfig,
        alpaca_config: AlpacaConfig,
    ) -> None:
        """Initialize with scanner and Alpaca connection config."""
    
    async def start(self) -> None:
        """Initialize StockHistoricalDataClient."""
    
    async def stop(self) -> None:
        """Clean up client resources."""
    
    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Scan universe using Alpaca snapshots, filter by criteria.
        
        1. Fetch snapshots for all universe symbols
        2. Calculate gap_pct for each from previous_daily_bar.close to daily_bar.open
        3. Filter by merged criteria from all active strategies:
           - gap_pct within [min_gap_pct, max_gap_pct]
           - price within [min_price, max_price]
           - yesterday's volume >= min_volume
        4. Sort by gap_pct descending (strongest gappers first)
        5. Return top max_symbols_returned as WatchlistItems
        
        Each WatchlistItem is populated with:
        - symbol, gap_pct, relative_volume, atr (if available)
        """
```

### Tests (`tests/data/test_alpaca_scanner.py`)

Target: ~10 tests

1. `test_scan_returns_watchlist_items` — Mock snapshots, verify WatchlistItem output
2. `test_filters_by_gap_percentage` — Only symbols within min/max gap returned
3. `test_filters_by_price_range` — Symbols outside price range excluded
4. `test_filters_by_minimum_volume` — Low-volume symbols excluded
5. `test_sorts_by_gap_descending` — Strongest gappers first
6. `test_respects_max_symbols_limit` — Returns at most max_symbols_returned
7. `test_handles_missing_snapshot_data` — If a symbol's snapshot is incomplete, skip it
8. `test_gap_calculation_correct` — Verify gap = (open - prev_close) / prev_close
9. `test_empty_universe_returns_empty` — No symbols configured → empty list
10. `test_all_symbols_filtered_out` — No matches → empty list

**All tests use mocked StockHistoricalDataClient. No network calls.**

---

## Component 3: Integration Test

### File: `tests/test_integration_sprint4b.py`

Full pipeline test with mocks:

```
AlpacaScanner (mocked snapshots)
    → provides watchlist to OrbBreakout
    → AlpacaDataService (mocked WebSocket) sends CandleEvents  
    → OrbBreakout detects breakout, emits SignalEvent
    → RiskManager approves signal → OrderApprovedEvent
    → OrderManager receives approval, places entry order
    → Mock broker fills entry → OrderFilledEvent  
    → OrderManager places stop + T1 orders
    → Mock broker fills T1 → OrderFilledEvent
    → OrderManager moves stop to breakeven
    → Mock tick at T2 price
    → OrderManager closes remaining shares
    → PositionClosedEvent published
    → TradeLogger records the trade
```

This is the "everything works together" test for the complete ORB lifecycle.

Target: 2-3 integration tests (happy path, stop-out path, EOD flatten path).

---

## Micro-Decisions to Make Before Implementation

These need to be decided before Claude Code starts. Review and confirm:

### MD-4b-1: Order Manager T1/T2 — Separate Orders or Modify-in-Place?

When T1 fills and the stop needs to move to breakeven:
- **(a)** Cancel the old stop order (for full shares), submit a new stop order (for remaining shares) at breakeven price. Two broker operations.
- **(b)** Modify the existing stop order in place using `broker.modify_order()` — change qty and price simultaneously. One broker operation.

**Recommendation:** (a) — Cancel and resubmit. `modify_order` on Alpaca replaces the entire order, and if the replace fails mid-flight, we might briefly have no stop protection. Cancel-then-submit is more explicit, and if the new submit fails we can detect and emergency flatten. The brief window with no stop between cancel and resubmit is acceptable because the Order Manager is also monitoring ticks.

### MD-4b-2: EOD Flatten Scheduling Mechanism

- **(a)** asyncio-based: Run a loop that checks `clock.now()` against flatten time every 5 seconds (piggyback on fallback_poll).
- **(b)** APScheduler: Use a proper scheduler for the EOD task.

**Recommendation:** (a) for Sprint 4b. We don't have APScheduler integrated yet, and the fallback_poll already runs every 5 seconds. Adding an EOD time check there is trivial. APScheduler can be introduced in Sprint 5 for more sophisticated scheduling.

### MD-4b-3: Order Manager Scope — TradeLogger Integration

Should the Order Manager directly call TradeLogger to record trades, or should it publish events and let a separate component handle persistence?

- **(a)** Order Manager calls TradeLogger directly when a position fully closes.
- **(b)** Order Manager publishes PositionClosedEvent. A separate listener (or the existing TradeLogger subscription) handles persistence.

**Recommendation:** (a) for simplicity. The Order Manager has the complete trade data (entry price, exit price, shares, P&L) at close time. Publishing a PositionClosedEvent is still done (for other subscribers), but the Order Manager is responsible for the `log_trade()` call.

### MD-4b-4: AlpacaScanner Universe — Static Config or Dynamic?

- **(a)** Static: Universe is a fixed list in config/scanner.yaml. Simple, predictable.
- **(b)** Dynamic: Fetch top N stocks by volume from Alpaca's assets endpoint at startup.

**Recommendation:** (a) for V1. A curated list of 20-50 liquid stocks is more than enough for ORB. Dynamic universe adds complexity (what if the API is down at startup? rate limits?). Easy to expand the list manually as needed.

### MD-4b-5: How Does the Order Manager Get ExitRules?

The `OrderApprovedEvent` contains the original signal data. Does it contain the strategy's ExitRules?

- **(a)** ExitRules are embedded in the SignalEvent/OrderApprovedEvent (already available — check if the existing event model includes them).
- **(b)** Order Manager queries the strategy for exit rules by strategy_id.

**Recommendation:** (a) — The signal should carry its own exit rules. Check the existing `SignalEvent` dataclass. If `exit_rules` or equivalent fields (stop_price, target_prices, time_stop_minutes) are already present, use them directly. If not, add them to the event model.

---

## Build Order

1. **Config models** — OrderManagerConfig, AlpacaScannerConfig
2. **ManagedPosition + PendingManagedOrder** dataclasses
3. **Order Manager** — core logic (on_approved, on_fill, on_tick, fallback_poll, eod_flatten, emergency_flatten)
4. **Order Manager tests** (~25 tests)
5. **AlpacaScanner** — Scanner ABC implementation with mocked Alpaca client
6. **AlpacaScanner tests** (~10 tests)
7. **Integration test** (2-3 tests)
8. **Full test suite pass + ruff clean**
9. **Commit and push**

---

## New Files Created This Sprint

```
argus/execution/order_manager.py
argus/data/alpaca_scanner.py
config/order_manager.yaml
tests/execution/test_order_manager.py
tests/data/test_alpaca_scanner.py
tests/test_integration_sprint4b.py
```

**Modified files:**
```
argus/core/config.py            (add OrderManagerConfig, AlpacaScannerConfig)
config/scanner.yaml             (add alpaca_scanner section)
```

---

## Decisions in Effect (Do Not Relitigate)

| ID | Relevant Rule |
|----|---------------|
| DEC-011 | Long only for V1 |
| DEC-012 | ORB stop at midpoint of opening range |
| DEC-027 | Approve-with-modification (reduce shares, tighten targets, never widen stops) |
| DEC-028 | Daily-stateful, session-stateless |
| DEC-029 | Event Bus is sole streaming mechanism |
| DEC-030 | Order Manager: event-driven (tick subscription) + 5s fallback poll + scheduled EOD flatten |
| DEC-033 | Type-only Event Bus subscription. Filtering in handlers. |
| DEC-038 | ORB entry is market order + chase protection |
| DEC-039/MD-4a-6 | Bracket orders: single T1 (Alpaca limitation). Order Manager handles T1/T2 split. |

---

## Success Criteria

Sprint 4b is done when:
- [ ] OrderManagerConfig and AlpacaScannerConfig Pydantic models created
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

## Documentation Update Protocol

At the END of this sprint, output a "Docs Status" summary per CLAUDE.md rules. Flag any docs that need updating.

---

*End of Sprint 4b Spec*
