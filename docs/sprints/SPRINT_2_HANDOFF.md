# ARGUS — Sprint 2 Handoff Document

> **Date:** February 15, 2026
> **Purpose:** Everything needed to start Sprint 2 in a fresh conversation.
> **Previous work:** Sprint 1 complete and committed. Cleanup commit done. All docs synced.

---

## Project Context

Argus is a fully automated multi-strategy day trading ecosystem. Full details are in the project instructions and synced docs. This handoff covers only what's needed for Sprint 2.

## What Exists (Sprint 1 — Complete)

**52 tests passing. ruff clean. All committed and pushed.**

### Files Built

```
argus/
├── __init__.py                     # v0.1.0
├── core/
│   ├── config.py                   # Pydantic config models + YAML loader
│   ├── events.py                   # 20+ frozen event dataclasses
│   ├── event_bus.py                # Async pub/sub, monotonic sequence numbers
│   └── ids.py                      # ULID generator
├── models/
│   └── trading.py                  # Order, Position, TradeRecord, DailyPerformance, AccountSnapshot
├── db/
│   ├── schema.sql                  # Full SQLite schema
│   └── manager.py                  # Async DatabaseManager (aiosqlite, WAL mode)
├── analytics/
│   └── trade_logger.py             # Trade logging + daily summaries + queries
config/
├── system.yaml, risk_limits.yaml, brokers.yaml, orchestrator.yaml, notifications.yaml
└── strategies/orb_breakout.yaml
tests/
├── conftest.py                     # Shared fixtures: config, bus, db, trade_logger
├── core/test_config.py             # 15 tests
├── core/test_events.py             # 6 tests
├── core/test_event_bus.py          # 12 tests
├── models/test_trading.py          # Model tests
├── db/test_manager.py              # DB manager tests
└── analytics/test_trade_logger.py  # Trade logger tests
```

### Key Interfaces Available

**EventBus** — `subscribe(event_type, handler)`, `publish(event)`, `drain()`, `reset()`
**DatabaseManager** — `initialize()`, `execute()`, `fetch_one()`, `fetch_all()`, `close()`
**TradeLogger** — `log_trade()`, `get_trade()`, `get_trades_by_strategy()`, `get_trades_by_date()`, `get_daily_summary()`, `save_daily_summary()`
**Config** — `load_config(path)` returns `ArgusConfig` with `.system`, `.risk`, `.broker`, `.orchestrator`, `.notifications`; `load_strategy_config(path)` returns `StrategyConfig`

### Event Types Available (from `argus/core/events.py`)

SignalEvent, OrderApprovedEvent, OrderRejectedEvent, OrderSubmittedEvent, OrderFilledEvent, OrderCancelledEvent, PositionOpenedEvent, PositionUpdatedEvent, PositionClosedEvent, CircuitBreakerEvent, CandleEvent, TickEvent, IndicatorEvent, WatchlistEvent, HeartbeatEvent, RegimeChangeEvent, AllocationUpdateEvent, StrategyActivatedEvent, StrategySuspendedEvent, ApprovalRequestedEvent, ApprovalGrantedEvent, ApprovalDeniedEvent

### Config Models Available (from `argus/core/config.py`)

SystemConfig, AccountRiskConfig, CrossStrategyRiskConfig, PDTConfig, RiskConfig, BrokerConfig (with AlpacaConfig), OrchestratorConfig, NotificationsConfig, StrategyConfig (with StrategyRiskLimits, OperatingWindow, Benchmarks), ArgusConfig

---

## Sprint 2 Scope: Broker Abstraction + Risk Manager (Steps 4–5)

### Step 4 — Broker Abstraction + Simulated Broker

Build these files:
- `argus/execution/broker.py` — Broker ABC
- `argus/execution/simulated_broker.py` — SimulatedBroker (deterministic test double)
- `argus/execution/broker_router.py` — Routes orders to correct broker

**Broker ABC interface** (from Architecture doc Section 3.3):
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

**SimulatedBroker requirements:**
- Fills orders at specified prices (or configurable slippage model)
- Tracks positions internally
- Simulates bracket orders (tracks associated stop and target orders)
- Enforces buying power limits
- Supports `flatten_all` for emergency close
- Deterministic behavior for testing
- Configurable: slippage (none/fixed/random range), partial fills (on/off)

**BrokerRouter:**
- Reads routing config from `config/brokers.yaml`
- Routes by asset class
- V1: everything routes to the single configured broker

**Tests needed:**
- Place order → get fill
- Place bracket order → verify stop and target tracked
- Cancel order
- Get positions, get account
- `flatten_all` closes everything
- Buying power enforcement rejects oversized orders
- BrokerRouter routes based on config

### Step 5 — Risk Manager (Account Level)

Build this file:
- `argus/core/risk_manager.py` — Three-level gate (Phase 1: account level only)

**Interface** (from Architecture doc Section 3.5):
```python
class RiskManager:
    async def evaluate_signal(self, signal: SignalEvent) -> OrderApprovedEvent | OrderRejectedEvent
    async def on_position_update(self, event: PositionUpdatedEvent) -> None
    async def check_circuit_breakers(self) -> CircuitBreakerEvent | None
    async def daily_integrity_check(self) -> IntegrityReport
```

**Account-level checks to implement (Phase 1):**
- Daily loss limit (default 3% of account, from config)
- Weekly loss limit (default 5% of account, from config)
- Cash reserve enforcement (minimum 20% always held, from config)
- Max concurrent positions (default 10, from config)
- PDT tracking (3 day trades per 5 rolling business days in margin accounts under $25K)
- Circuit breaker logic (non-overridable, fires at daily loss limit)

**Approve-with-modification rules (DEC-027):**
- PERMITTED: Reduce share count to fit buying power or position limits
  - Reject if reduced position yields < 0.25R potential profit
- PERMITTED: Tighten profit targets if cross-strategy exposure requires it
- PROHIBITED: Widen stop loss (strategy set the stop for a reason)
- PROHIBITED: Change entry price (Risk Manager gates execution, doesn't alter thesis)
- PROHIBITED: Change side (signal direction is inviolable)
- All modifications recorded in `OrderApprovedEvent.modifications` with reason string

**Strategy-level checks:** NOT in Sprint 2 scope — handled inside strategies themselves (Sprint 3)
**Cross-strategy checks:** NOT in Sprint 2 scope — needs multiple strategies (Phase 4)

**Risk config** already exists in `config/risk_limits.yaml`:
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
```

**Tests needed:**
- Signal that violates daily loss limit → rejected with reason
- Signal that exceeds cash reserve → rejected
- Signal that breaches max concurrent positions → rejected
- Signal with oversized share count → approved with reduced shares + modification logged
- Signal reduced below 0.25R threshold → rejected (not worth taking)
- PDT counter tracks correctly across rolling 5-day window
- PDT enforces 3-trade limit in margin account under $25K
- PDT does not restrict cash accounts
- Circuit breaker fires when daily loss limit hit
- Circuit breaker publishes CircuitBreakerEvent to Event Bus
- Valid signal in normal conditions → approved with no modifications

**Integration test (end of Sprint 2):**
- Full pipeline: create SignalEvent → Risk Manager evaluates → SimulatedBroker fills → Trade Logger records
- This is the first end-to-end flow test

---

## Sprint 2 Definition of Done

1. `ruff check argus/ tests/` — clean
2. `pytest tests/ -v` — all tests pass (Sprint 1 tests + Sprint 2 tests)
3. SimulatedBroker fills orders deterministically
4. Risk Manager correctly rejects, approves, or modifies signals at account level
5. PDT tracking works for both margin and cash account modes
6. Circuit breaker fires and publishes event when triggered
7. End-to-end flow works: Signal → Risk Manager → SimulatedBroker → Trade Logger
8. All public methods have type hints and docstrings
9. No hardcoded config values

---

## Key Decisions to Follow (Do Not Relitigate)

| ID | Decision | Summary |
|----|----------|---------|
| DEC-027 | Risk Manager modifications | Approve-with-modification for share count reduction and target tightening. Never modify stops or entry. 0.25R floor. |
| DEC-031 | IBKR deferral | Only SimulatedBroker and AlpacaBroker in Phase 1. IBKR deferred to Phase 3+. |
| DEC-032 | Config via Pydantic | All config from YAML through Pydantic BaseModel. |
| DEC-033 | Event Bus type-only | No predicate filtering at bus level. |
| DEC-034 | Async DB via aiosqlite | DatabaseManager owns connection. TradeLogger is sole persistence interface. |

---

## Architecture References

- **Broker ABC:** `docs/03_ARCHITECTURE.md` Section 3.3
- **Risk Manager:** `docs/03_ARCHITECTURE.md` Section 3.5
- **Event types:** `docs/03_ARCHITECTURE.md` Section 3.1
- **Risk limits config:** `docs/03_ARCHITECTURE.md` Section 3.5 (Configuration block)
- **Full build plan:** Phase 1 Handoff Document (in previous conversation)

---

## Remaining Phase 1 Steps (After Sprint 2)

- **Sprint 3** (Steps 6–7): BaseStrategy ABC + ORB Breakout strategy + Data Service abstraction + Alpaca Data Service + ReplayDataService
- **Sprint 4** (Steps 8–9): Alpaca Broker adapter (real paper trading) + Order Manager (position management, stop adjustments, time stops, EOD flatten)
- **Sprint 5** (Steps 10–11): Health monitoring + Integration testing (3+ days on Alpaca paper trading)

---

## What This Conversation Should Do

1. Review this handoff and confirm understanding of Sprint 2 scope
2. Identify any micro-decisions needed before writing the spec (bring to user for sign-off)
3. Produce a detailed Sprint 2 implementation spec — file-by-file, class-by-class, test-by-test — same level of detail as the Sprint 1 spec
4. Deliver the spec as a document the user hands to Claude Code

---

*End of Sprint 2 Handoff*
