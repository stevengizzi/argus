# ARGUS — Phase 1 Sprint Plan

> *Version 1.0 | February 15, 2026*
> *This is the canonical step-by-step plan for Phase 1 (Core Trading Engine + ORB Strategy). It maps the original 11-step build order to 6 sprints and tracks status. If reality diverges from this plan, update the plan — don't operate from memory.*

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
| 9 | Order Manager + Position Management | S4b | As planned. Event-driven position management (DEC-030): tick subscription + 5s fallback poll + scheduled EOD flatten. | 🔜 Next |
| — | AlpacaScanner | S4b | Added to plan. Implements Scanner ABC using Alpaca screener/snapshot API for real pre-market scanning. | 🔜 Next |
| 10 | Health Checks + Basic Monitoring | S5 | As planned. Heartbeat, stale data detection, dead man's switch, integrity checks, system health table. | Pending |
| 11 | Integration Test Suite + First Paper Trading Run | S5 | As planned. Full system on Alpaca paper trading, minimum 3 trading days unattended. | Pending |

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

### Sprint 4b — Position Management + Live Scanning (Step 9) 🔜 NEXT
**Target tests:** ~320+ (282 current + ~40 new)

**Scope:**
- **Order Manager:** Converts approved signals to broker orders. Manages open positions via tick subscription (DEC-030). Stop-to-breakeven when T1 hits. Trailing stop support. Time stop enforcement. EOD flatten at 3:50 PM EST (scheduled task). Emergency flatten for circuit breakers. 5-second fallback poll for time-based exits in illiquid stocks.
- **AlpacaScanner:** Implements Scanner ABC using Alpaca's screener/snapshot API for real pre-market gap screening. Replaces StaticScanner for live trading.
- **Integration:** Full pipeline wired end-to-end: AlpacaDataService → AlpacaScanner → OrbBreakout → RiskManager → OrderManager → AlpacaBroker

**After this sprint:** The complete ORB lifecycle works with real market data and paper orders. Positions are actively managed — stops move to breakeven, time stops fire, EOD flattens everything. The system can run during market hours autonomously. Not yet hardened for unattended operation.

### Sprint 5 — Hardening + Paper Trading (Steps 10, 11)

**Scope:**
- **Health monitoring:** Heartbeat signal every 60 seconds to external monitoring service. System health table with component status. Dead man's switch (alert if no heartbeat for 5 minutes).
- **Stale data handling:** Data feed stall detection (30-second timeout) → pause all strategies, alert.
- **Integrity checks:** Daily: verify all open positions have broker-side stop orders. Weekly: reconcile system trade log with broker's official records.
- **Recovery procedures:** Documented startup/recovery procedure. Strategy state reconstruction on restart. Target time-to-recovery: <5 minutes.
- **Paper trading validation:** Minimum 3 trading days of unattended operation on Alpaca paper trading. Success criteria: no crashes, no missed events, all trades logged correctly, stops managed properly, EOD flatten works, daily performance recorded.

**After this sprint:** Phase 1 is complete. The system is validated for unattended paper trading and ready to move to Phase 2 (Backtesting Validation).

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

## Post-Phase 1 Roadmap (Phases 2-8)

For reference, the phases after Phase 1 (from 02_PROJECT_KNOWLEDGE.md):

| Phase | Scope | Weeks (est.) |
|-------|-------|-------------|
| 2 | Backtesting Validation — VectorBT parameter sweeps, Backtrader validation, Replay Harness build | 3-4 |
| 3 | Live Validation — ORB live at minimum size, compare to backtest expectations | 4-5 |
| 4 | Orchestrator + Second Strategy — Orchestrator framework, ORB Scalp, cross-strategy risk | 4-5 |
| 5 | Command Center MVP — Tauri desktop app, real-time dashboard, basic controls | 6 |
| 6 | AI Layer — Claude API integration, approval workflow, report generation | 6 |
| 7 | Expand Strategies — Add strategies one at a time through Incubator Pipeline | Ongoing |
| 8 | Multi-Asset Expansion — Crypto via Alpaca, then Forex, then Futures | Future |

---

*End of Phase 1 Sprint Plan v1.0*
*Update this document when sprint scope changes or sprints complete.*
