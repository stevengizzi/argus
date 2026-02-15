# ARGUS — Sprint 2 Review & Sprint 3 Planning Handoff

> **Date:** February 15, 2026
> **Purpose:** Start a fresh conversation to (1) review the Sprint 2 implementation transcript, and (2) plan Sprint 3.
> **Instructions:** Paste this document as your first message, then paste the Claude Code Sprint 2 session transcript immediately after.

---

## Project Context

Argus is a fully automated multi-strategy day trading ecosystem. Full details are in the project instructions and synced docs. This handoff covers only what's needed for this session.

## What Existed Before Sprint 2 (Sprint 1 — Complete)

**52 tests passing. All committed.**

Sprint 1 built: Config system (Pydantic + YAML), Event Bus (async pub/sub with monotonic sequence numbers), data models (Order, Position, TradeRecord, etc.), database layer (SQLite + aiosqlite + DatabaseManager), Trade Logger, and full test suite.

Files: `argus/core/config.py`, `argus/core/events.py`, `argus/core/event_bus.py`, `argus/core/ids.py`, `argus/models/trading.py`, `argus/db/schema.sql`, `argus/db/manager.py`, `argus/analytics/trade_logger.py`, plus config YAMLs and tests.

## What Sprint 2 Was Supposed to Build

Per the Sprint 2 spec (summarized):

### Step 4 — Broker Abstraction + SimulatedBroker
- `argus/execution/broker.py` — Broker ABC with: `connect`, `disconnect`, `place_order`, `place_bracket_order`, `cancel_order`, `modify_order`, `get_positions`, `get_account`, `get_order_status`, `flatten_all`
- `argus/execution/simulated_broker.py` — Deterministic test double. Fills at specified prices, tracks positions/account internally, supports bracket orders (stop + target as PendingBracketOrders), configurable slippage, `simulate_price_update()` for testing bracket triggers, buying power enforcement
- `argus/execution/broker_router.py` — Routes orders to correct broker by asset class. V1: everything routes to primary

### Step 5 — Risk Manager (Account Level)
- `argus/core/risk_manager.py` — Three-level gate (Phase 1: account level only)
- `evaluate_signal()` check order: (1) circuit breaker, (2) daily loss limit, (3) weekly loss limit, (4) max concurrent positions, (5) cash reserve enforcement, (6) buying power check, (7) 0.25R floor on reduced positions, (8) PDT tracking
- Circuit breaker internally enforced (`_circuit_breaker_active` flag, auto-rejects until `reset_daily_state()`)
- PDT tracking: rolling 5-business-day window, margin vs cash account handling, $25K threshold from config
- Approve-with-modification: reduce shares (with 0.25R floor), tighten targets. Never modify stops/entry/side.
- Weekly loss limit: calendar week (Mon–Fri reset)
- State: queries Broker for account info, maintains daily/weekly P&L via EventBus subscription to PositionClosedEvent

### Expected Tests (~52 new)
- ~24 SimulatedBroker tests (order fills, bracket orders, price simulation, slippage, flatten_all, etc.)
- ~4 BrokerRouter tests
- ~20 Risk Manager tests (all rejection/approval/modification paths, PDT, circuit breaker, state management)
- ~4 integration tests (full pipeline: Signal → Risk Manager → SimulatedBroker → TradeLogger)

### Key Micro-Decisions (DEC-035)
1. Weekly loss limit = calendar week reset
2. Circuit breaker = internally enforced by Risk Manager
3. SimulatedBroker has `simulate_price_update()` for bracket testing
4. PDT threshold in config (`pdt.threshold_balance: 25000`)
5. Risk Manager queries Broker for account state (source of truth)

---

## What This Session Should Do

### Part 1: Review the Sprint 2 Transcript

The Claude Code session transcript follows this document. Review it for:

1. **Spec compliance:** Did the implementation match the spec? Note any deviations.
2. **Architectural rule adherence:** Type hints on all signatures, docstrings, no hardcoded config, async everywhere, events through the bus, etc.
3. **Test quality:** Are edge cases covered? Any gaps? Do tests actually test what they claim?
4. **Code quality concerns:** Anything that could cause problems in later sprints? Anti-patterns? Naming inconsistencies with Sprint 1?
5. **Decision drift:** Were any micro-decisions made during implementation that should be recorded in the Decision Log?
6. **Doc updates needed:** Based on what was actually built (vs. spec), do any docs need updating?

Output a structured review with: ✅ (good), ⚠️ (minor concern), ❌ (needs fix). Be specific — cite code locations.

### Part 2: Sprint 3 Planning

After the review, produce a Sprint 3 handoff document at the same level of detail as the Sprint 2 handoff. Sprint 3 scope from the Phase 1 plan:

**Sprint 3 (Steps 6–7): BaseStrategy ABC + ORB Breakout Strategy + Data Service**

From the Phase 1 build plan:
- **Step 6:** BaseStrategy ABC + Scanner interface
- **Step 7:** Data Service abstraction + ReplayDataService + ORB Breakout strategy implementation

Key architecture references:
- BaseStrategy interface: `docs/03_ARCHITECTURE.md` Section 3.4
- Data Service interface: `docs/03_ARCHITECTURE.md` Section 3.2
- ORB strategy rules: `docs/01_PROJECT_BIBLE.md` Section 4.2 (Strategy 1)
- ORB config: `config/strategies/orb_breakout.yaml`
- Strategy template: `docs/04_STRATEGY_TEMPLATE.md`

Before writing the spec, surface any micro-decisions that need sign-off (same format as Sprint 2).

---

## Remaining Phase 1 Sprints (After Sprint 3)

- **Sprint 4** (Steps 8–9): Alpaca Broker adapter (real paper trading) + Order Manager (position management, stop adjustments, time stops, EOD flatten)
- **Sprint 5** (Steps 10–11): Health monitoring + Integration testing (3+ days on Alpaca paper trading)

---

## Key Decisions in Effect (Do Not Relitigate)

| ID | Summary |
|----|---------|
| DEC-027 | Risk Manager approve-with-modification. Reduce shares (0.25R floor), tighten targets. Never modify stops/entry/side. |
| DEC-028 | Strategies: daily-stateful, session-stateless. Reset between days, reconstruct from DB on restart. |
| DEC-029 | Data delivery via Event Bus only. No callback subscription on DataService. Sync queries retained. |
| DEC-030 | Order Manager: event-driven (tick subscription) + 5s fallback poll + scheduled EOD flatten. |
| DEC-031 | IBKR adapter deferred to Phase 3+. Only SimulatedBroker and AlpacaBroker in Phase 1. |
| DEC-032 | Config via Pydantic BaseModel. YAML → Pydantic flow. |
| DEC-033 | Event Bus: type-only subscription. Filtering in handlers, not at bus level. |
| DEC-034 | Async DB via aiosqlite. DatabaseManager owns connection. TradeLogger is sole persistence interface. |
| DEC-035 | Sprint 2 micro-decisions: calendar week for weekly limit, internal circuit breaker, simulate_price_update(), PDT threshold in config, Risk Manager queries Broker for state. |

---

*End of Handoff*

**→ PASTE THE CLAUDE CODE SPRINT 2 TRANSCRIPT BELOW THIS LINE ←**
