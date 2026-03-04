# ARGUS — Phase 1 Sprint Plan

> *Version 1.1 | February 16, 2026*
> *✅ PHASE 1 COMPLETE — February 16, 2026 — 362 tests passing, ruff clean.*
> *This document is now historical reference. For current build work, see `09_PHASE2_SPRINT_PLAN.md`.*
> *Original: Canonical step-by-step plan for Phase 1 (Core Trading Engine + ORB Strategy). Maps the original 11-step build order to 6 sprints.*

---

## Phase 1 Goal

ORB Breakout running on Alpaca paper trading with the full pipeline working end-to-end: live market data → strategy decision → risk gate → order placed → position managed → exits executed → trade logged. Minimum 3 trading days of unattended paper trading with no crashes, no missed events, and all trades logged correctly.

---

## Original 11-Step Build Order → Sprint Mapping

The original plan defined 11 implementation steps. During execution, steps were grouped into 6 sprints, and the Data Service was split (replay first, live later). The Scanner was added to Sprint 3 (originally deferred). The original Sprint 4 was split into 4a (live connections) and 4b (position management + scanning) to keep sprint scope manageable.

| Step | Original Scope | Sprint | Actual Scope | Status |
|------|---------------|--------|--------------|--------|
| 1 | Project skeleton + Configuration layer | S1 | As planned. Pydantic BaseModel + YAML (DEC-032). | ✅ Complete |
| 2 | Event Bus | S1 | As planned. Asyncio pub/sub, FIFO per subscriber, monotonic sequence numbers (DEC-025). | ✅ Complete |
| 3 | Data models + Database + Trade Logger | S1 | As planned. SQLite + aiosqlite, ULIDs (DEC-026), DatabaseManager + TradeLogger (DEC-034). | ✅ Complete |
| 4 | Broker Abstraction + Simulated Broker | S2 | As planned. Broker ABC, SimulatedBroker (no margin, DEC-036), BrokerRouter. IBKR deferred (DEC-031). | ✅ Complete |
| 5 | Risk Manager (account level) | S2 | As planned + extras. Three-level risk (strategy/cross-strategy/account), PDT tracking, circuit breakers, approve-with-modification (DEC-027), start-of-day equity (DEC-037). | ✅ Complete |
| 6 | Base Strategy + ORB Strategy | S3 | Expanded. BaseStrategy ABC + ORB Breakout + Scanner ABC + StaticScanner (MD-1, added to plan). | ✅ Complete |
| 7a | Data Service Abstraction | S3 | Split from original Step 7. DataService ABC + ReplayDataService (Parquet, 1m candles, indicator computation). Event Bus delivery only (DEC-029). | ✅ Complete |
| 7b | Alpaca Data Service (live) | S4a | Split from original Step 7. AlpacaDataService (WebSocket bars + trades via alpaca-py, indicator warm-up, stale data monitoring, reconnection with backoff). 20 tests. | ✅ Complete |
| 8 | Alpaca Broker Adapter | S4a | AlpacaBroker (paper trading via alpaca-py SDK, REST + WebSocket, bracket orders with single T1 target, ULID↔UUID order ID mapping). Also: Clock protocol + injection (DEF-001 resolved), AlpacaConfig model. 14 + 19 + 2 tests. Polish: flaky test fix, ruff cleanup, missing broker tests. | ✅ Complete |
| 9 | Order Manager + Position Management | S4b | As planned. Event-driven position management (DEC-030): tick subscription + 5s fallback poll + EOD flatten in poll loop. OrderManager + ManagedPosition + PendingManagedOrder. T1/T2 split with cancel-and-resubmit stop management (DEC-040). 25 tests. | ✅ Complete |
| — | AlpacaScanner | S4b | Added to plan. Implements Scanner ABC using Alpaca StockHistoricalDataClient snapshots. Gap/price/volume filtering. 10 tests. | ✅ Complete |
| 10 | Health Checks + Basic Monitoring | S5 | As planned. HealthMonitor with component status, heartbeat pings, webhook alerts. Structured logging with JSON output. Daily and weekly integrity checks. 20 tests. | ✅ Complete |
| 11 | Integration Test Suite + First Paper Trading Run | S5 | As planned. ArgusSystem entry point with 10-phase startup/shutdown. Strategy and Order Manager reconstruction. Full system integration tests. Paper trading validation pending (post-sprint). | ✅ Complete |

---

## Sprint Details

### Sprint 1 — Foundation (Steps 1-3) ✅ COMPLETE
**Tests:** 52 passing

**Delivered:**
- Python package structure with all subpackages
- Pydantic config system loading from YAML files
- Event Bus with asyncio pub/sub, sequence numbers, type-based subscription
- All event dataclasses (market data, strategy, risk, execution, position, system events)
- EventStore for event persistence
- Data models: Order, Position, Trade, AccountInfo, DailySummary
- SQLite database with WAL mode, schema initialization, async access via aiosqlite
- DatabaseManager (sole connection owner) + TradeLogger (sole persistence interface)
- ULID generation for all primary keys

### Sprint 2 — Execution + Risk Layer (Steps 4-5) ✅ COMPLETE
**Tests:** 112 passing (after polish)

**Delivered:**
- Broker ABC with full interface (place_order, place_bracket_order, cancel, modify, get_positions, get_account, flatten_all)
- SimulatedBroker with deterministic fills, configurable slippage, bracket order simulation (stop + multiple targets)
- BrokerRouter for asset-class-based routing
- Risk Manager with three-level evaluation gate:
  - Strategy level: internal limits checked via strategy interface
  - Cross-strategy level: single-stock and sector concentration limits
  - Account level: daily/weekly loss limits, cash reserve (start-of-day equity), buying power, max positions
- PDT day trade tracking (rolling 5-business-day window)
- Circuit breaker (non-overridable, resets daily)
- Approve-with-modification (share reduction with 0.25R floor, target tightening)
- State reconstruction from database on mid-day restart (daily P&L, weekly P&L, PDT trades)

### Sprint 3 — Strategy + Data Layer (Steps 6, 7a) ✅ Complete
**Target tests:** ~150+

**Scope:**
- **Pre-sprint fix:** DEC-037 implementation (start-of-day equity in Risk Manager)
- **Config models:** OrbBreakoutConfig, DataServiceConfig, ScannerConfig
- **Strategy models:** ScannerCriteria, ExitRules, ProfitTarget, MarketConditionsFilter, WatchlistItem
- **BaseStrategy ABC:** Full interface from Architecture doc Section 3.4 — on_candle, on_tick, get_scanner_criteria, calculate_position_size, get_exit_rules, get_market_conditions_filter, check_internal_risk_limits, reset_daily_state, reconstruct_state
- **Scanner ABC + StaticScanner:** Scanner interface accepting ScannerCriteria, returning WatchlistItems. StaticScanner reads from config/scanner.yaml. Real AlpacaScanner deferred to Sprint 4.
- **DataService ABC + ReplayDataService:** DataService interface with Event Bus delivery (no callbacks, DEC-029). ReplayDataService reads Parquet files, publishes CandleEvents in chronological order, computes and publishes IndicatorEvents (VWAP, ATR(14), RVOL, SMA 9/20/50). Multi-timeframe framework built, only 1m implemented (MD-2c).
- **ORB Breakout Strategy:** Full lifecycle — OR formation during configurable window, OR validation (ATR bounds), breakout detection (candle close above OR high, volume > 1.5x OR avg, price above VWAP), chase protection, signal emission with correct entry/stop/targets/position sizing. Multi-symbol support via per-symbol state dict.
- **Integration test:** StaticScanner → ReplayDataService → OrbBreakout → RiskManager → SimulatedBroker end-to-end

**After this sprint:** ORB can receive replayed historical data and produce correct SignalEvents that pass through the Risk Manager and reach the SimulatedBroker. No live broker connection. No active position management.

### Sprint 4a — Live Connections (Steps 7b, 8) ✅ Complete

**Test count:** 277 total (276 passing, 1 flaky — `test_reconnection_with_exponential_backoff` timing issue, fix in progress)
**Commits:** fe0af1a (Clock + AlpacaConfig), 1535cfa (AlpacaDataService), 422814d (AlpacaBroker), 58067c1 (integration tests), fa8ceaa (sprint docs)

**Scope delivered:**
- **Clock protocol** (`argus/core/clock.py`): SystemClock, FixedClock, Clock protocol. Injected into Risk Manager + BaseStrategy. Resolves DEF-001. 14 tests.
- **AlpacaConfig** (`argus/core/config.py`): New config model for Alpaca connections. Updated `config/brokers.yaml`.
- **Dependencies**: `alpaca-py>=0.30`, `python-dotenv>=1.0`. `.env.example` created. Switched from deprecated `alpaca-trade-api` to current `alpaca-py` (DEC-039/MD-4a-3).
- **AlpacaDataService** (`argus/data/alpaca_data_service.py`): Implements DataService ABC via alpaca-py. Subscribes to both 1m bar stream (CandleEvents) and trade stream (TickEvents + price cache). Indicator warm-up from 60 historical candles. Stale data monitoring (30s timeout). WebSocket reconnection with exponential backoff + jitter. 20 tests.
- **AlpacaBroker** (`argus/execution/alpaca_broker.py`): Implements Broker ABC via alpaca-py. REST (TradingClient) + WebSocket (TradingStream). Order ID mapping (ULID ↔ Alpaca UUID). Bracket orders with single T1 target (Alpaca limitation — Order Manager handles T1/T2 split in Sprint 4b). 19 tests.
- **Integration tests**: 2 tests — signal→risk→broker pipeline, bracket order flow. All alpaca-py clients mocked.

**Sprint 4a Polish:** Flaky reconnection test fixed (mocked `asyncio.sleep`), `import random` moved to module level, 5 missing AlpacaBroker tests added, all ruff warnings resolved (SIM105, SIM117). Final: 282 tests, 0 flaky, ruff clean. Commits: 738aab8 (polish), b95db95 (final cleanup).

**After this sprint:** The system can receive live market data, detect ORB breakouts on real stocks, and submit paper orders to Alpaca. No dynamic position management yet — broker-side bracket orders provide basic exit coverage.

### Sprint 4b — Position Management + Live Scanning (Step 9) ✅ COMPLETE
**Test count:** 320 total (282 + 38 new: 25 Order Manager + 10 AlpacaScanner + 3 integration)
**Completion date:** February 15, 2026
**Commits:** 099ac72 (feat: Order Manager + AlpacaScanner), 76c98ef (docs: sprint docs)

**Scope delivered:**
- **Order Manager** (`argus/execution/order_manager.py`): Converts approved signals to broker orders. Manages open positions via tick subscription (DEC-030). T1/T2 split with separate limit orders. Stop-to-breakeven when T1 hits (cancel-and-resubmit, DEC-040). Time stop enforcement (max_position_duration_minutes). EOD flatten checked in fallback poll loop (DEC-041). Emergency flatten for circuit breakers. 5-second fallback poll for time-based exits. TradeLogger integration via direct call (DEC-042). 25 tests.
- **AlpacaScanner** (`argus/data/alpaca_scanner.py`): Implements Scanner ABC using Alpaca's StockHistoricalDataClient.get_stock_snapshot() for batch pre-market gap screening. Filters by gap%, price range, volume. Sorts by gap descending, caps at max_symbols_returned. Static universe from config (DEC-043). 10 tests.
- **Config models:** OrderManagerConfig, AlpacaScannerConfig in `argus/core/config.py`. YAML files: `config/order_manager.yaml`, updated `config/scanner.yaml`.
- **Data models:** ManagedPosition, PendingManagedOrder dataclasses for position lifecycle tracking.
- **Integration tests:** 3 tests — full pipeline happy path (T1→T2), stop out, EOD flatten.

**After this sprint:** The complete ORB lifecycle works with real market data and paper orders. Positions are actively managed — stops move to breakeven, time stops fire, EOD flattens everything. The system can run during market hours autonomously. Not yet hardened for unattended operation.

### Sprint 5 — Hardening + Paper Trading (Steps 10, 11) ✅ COMPLETE
**Test count:** 359 total (320 + 39 new: 20 HealthMonitor + 10 main entry point + 6 integration + 3 Order Manager reconstruction)
**Completion date:** February 16, 2026

**Scope delivered:**
- **Structured Logging** (`argus/core/logging_config.py`): JSON file output + colored console output. All logging goes through Python's logging module.
- **HealthConfig** (`argus/core/config.py`): Heartbeat interval, webhook URLs, daily/weekly check toggles. Updated `config/system.yaml`.
- **HealthMonitor** (`argus/core/health.py`): Component status registry (STARTING/HEALTHY/DEGRADED/UNHEALTHY/STOPPED). Heartbeat publishing via EventBus. Webhook alerts (Discord format supported). Daily integrity check (verifies stops on positions). Weekly reconciliation (compares trade log to broker). Circuit breaker event subscription. 20 tests.
- **Stale Data Market Hours Fix** (`argus/data/alpaca_data_service.py`): Stale data monitor only checks during market hours (9:30 AM - 4:00 PM ET, weekdays only). Prevents false alerts outside trading.
- **Strategy Reconstruction** (`argus/data/alpaca_data_service.py`): `fetch_todays_bars()` fetches today's 1m historical bars for mid-day restart reconstruction.
- **Order Manager Reconstruction** (`argus/execution/order_manager.py`): `reconstruct_from_broker()` recovers open positions and stop orders from broker state. 3 tests.
- **System Entry Point** (`argus/main.py`): `ArgusSystem` class with 10-phase startup (config, db, broker, health, risk, data, scanner, strategy, order_manager, streaming). Graceful shutdown in reverse order. Signal handlers (SIGINT/SIGTERM). CLI args (--config, --paper, --dry-run). 10 tests.
- **Integration Tests** (`tests/test_integration_sprint5.py`): Full system startup/shutdown, heartbeat firing, circuit breaker alerts, stale data handling, Order Manager reconstruction. 6 tests.

**After this sprint:** Phase 1 code is complete. All components are wired together and can run end-to-end on Alpaca paper trading. Paper trading validation (3+ trading days unattended) is done by the user post-sprint.

---

## What Changed From the Original Plan

| Change | Why |
|--------|-----|
| Scanner added to Sprint 3 (originally deferred from Phase 1) | Scanner ABC + StaticScanner is lightweight and gives strategies a testable interface. Real AlpacaScanner still deferred to Sprint 4b. |
| Data Service split across Sprints 3 and 4a | ReplayDataService needed in Sprint 3 for ORB testing. AlpacaDataService needs real broker context, fits naturally with Sprint 4a. |
| Original Sprint 4 split into 4a and 4b | Live connections (data + broker) are one coherent unit. Position management (Order Manager) and live scanning (AlpacaScanner) are another. Splitting keeps each sprint focused and reviewable. |
| AlpacaDataService moved to Sprint 4a | Can't paper trade without live data. Must ship with Alpaca Broker. |
| IBKR adapter deferred to Phase 3+ (DEC-031) | Broker ABC achieves anti-lock-in goal. IBKR implementation adds 3-5 days of work with zero value until production scaling. |

---

## Post-Phase 1 Roadmap (Phases 2–9)

Updated estimates reflect the two-Claude workflow velocity observed during Phase 1 (original 4-week estimate completed in 2 days). Phase numbers updated per DEC-077 restructure.

| Phase | Scope | Original Est. | Revised Est. | Notes |
|-------|-------|--------------|-------------|-------|
| 2 | Backtesting Validation | 3-4 weeks | ✅ COMPLETE | 5 days. 542 tests. Parameter Validation Report written. |
| 3 | Comprehensive Validation — Extended backtest + paper trading | N/A (new) | 1–2 days build + flexible paper trading | Sprint 11 + parallel paper trading. DEC-077. |
| 4 | Live Trading — ORB live at minimum size, compare to backtest | 4-5 weeks | 4-5 weeks | Calendar-bound: 20+ trading days required. Cannot compress. |
| 5 | Orchestrator + Second Strategy — Orchestrator framework, ORB Scalp, cross-strategy risk | 4-5 weeks | 2-4 days | Same pattern as Phase 1: backend Python, clear architecture. |
| 6 | Command Center MVP — Tauri desktop app, real-time dashboard, basic controls | 6 weeks | 1-2 weeks | Frontend/UI is more iterative and harder to spec precisely. |
| 7 | AI Layer + News Intelligence — Claude API, approval workflow, news tiers | 6 weeks | 3-5 days | Well-defined API integration work. |
| 8 | Expand Strategies — Add strategies through Incubator Pipeline | Ongoing | Ongoing | Per-strategy effort: ~1-2 days build + validation period. |
| 9 | Multi-Asset Expansion — Crypto via Alpaca, then Forex, then Futures | Future | Future | Requires broker adapter work per asset class. |

---

*End of Phase 1 Sprint Plan v1.1*
*Phase 1 complete. This document is now historical reference.*
*Active sprint tracking has moved to `09_PHASE2_SPRINT_PLAN.md`.*
