# Sprint 21.5 — Live Integration (Databento + IBKR)

> **Sprint Owner:** Steven + Claude (both instances)
> **Estimated Sessions:** 13–16 (Claude Code) + 3 code reviews (Claude.ai)
> **Prerequisites:** Databento subscription activated, IBKR account approved ✅
> **Target Outcome:** ARGUS running live during market hours with Databento exchange-direct data flowing through all four strategies, executing paper trades on IBKR, visible in Command Center

---

## 1. Sprint Overview

### Why This Sprint Exists

Sprints 12 and 13 built the DatabentoDataService and IBKRBroker adapters against **mocks and unit tests**. No line of adapter code has ever touched a real Databento feed or a real IB Gateway connection. This sprint bridges that gap — it's the "last mile" integration work that turns ARGUS from a well-tested codebase into a live system processing real market data and executing real (paper) trades.

### Success Criteria

By the end of this sprint, Steven should be able to:

1. Start ARGUS before US market open (~9:15 AM ET / 10:15 PM Taipei)
2. Watch the Command Center Dashboard show live market data, strategy states, and watchlist updates
3. See strategies generate real signals based on Databento exchange-direct data
4. See paper trades execute on IBKR and appear in the Command Center Trade Log
5. Watch positions managed in real-time (stops, targets, time stops) through the IBKR paper account
6. Confirm that the system handles a full market session (9:30 AM – 4:00 PM ET) without crashes

### What This Sprint Is NOT

- Not building new features or new code paths (those already exist)
- Not optimizing performance or adding new strategies
- Not the DEC-132 backtest re-validation (that's Sprint 21.6 — see Section 8)
- Not AI Layer work (Sprint 22)

This is **configuration, connection, observation, and bug-fixing**. Expect 60% of the work to be diagnosing and fixing issues that only appear with real data/connections.

---

## 2. Resolved Micro-Decisions

### MD-21.5-1: IB Gateway vs TWS → **IB Gateway**
IB Gateway (headless). ARGUS is a headless automated system — no need for TWS GUI. Lower resource usage, Docker-friendly. TWS available as fallback.

### MD-21.5-2: Paper Trading Hours → **Regular Hours Only**
Regular trading hours (9:30 AM – 4:00 PM ET) for initial validation. Matches all four strategy windows.

### MD-21.5-3: Dataset Selection → **XNAS.ITCH First, Add XNYS.PILLAR in Sessions 3–4**
Start with XNAS.ITCH (Nasdaq TotalView-ITCH) in Sessions 1–2 to validate the data pipeline. Add XNYS.PILLAR (NYSE) in Sessions 3–4 once the pipeline is confirmed working. This provides full coverage of the momentum/small-cap day trading universe across both major exchanges. NYSE Arca (`ARCX.PILLAR`) added later only if specifically needed (SPY and many ETFs route through XNYS). Two datasets use 2 of the 10-session Standard plan limit.

### MD-21.5-4: Config File Strategy → **Separate `system_live.yaml`**
Create `config/system_live.yaml` for Databento + IBKR. Original `system.yaml` retained as Alpaca incubator config. `--config` CLI flag selects.

### MD-21.5-5: Secrets Management → **Environment Variables**
All secrets in `.env` (gitignored). `.env.example` committed with variable names documented. `python-dotenv` for loading.

### MD-21.5-6: Strategy Activation → **All Four from Session 11**
Sessions 5 and 10 confirm all four strategies work with real data (without execution and with full startup, respectively). Session 11 goes live with all four active. If Session 10 reveals a strategy-specific issue, that strategy is disabled and debugged separately while the others proceed. Strategy-prefixed logging (`[ORB]`, `[VWAP_RECLAIM]`, etc.) makes per-strategy debugging straightforward. Time-separated operating windows naturally isolate most issues.

---

## 3. Implementation Phases

### Phase A: Databento Activation (Sessions 1–5)

**Goal:** Databento data flowing through the system, strategies receiving real CandleEvents, indicators computing correctly.

| Session | Focus | Deliverable |
|---------|-------|-------------|
| 1 | Databento account setup + basic connection | API key configured, DatabentoDataService connects, receives raw records, logs first data |
| 2 | Data flow validation | CandleEvents published to EventBus, IndicatorEngine computes VWAP/ATR/SMA/RVOL on live bars, verify timestamps and symbol normalization |
| 3 | Scanner + watchlist + NYSE dataset | DatabentoScanner produces gap watchlist at market open. Add XNYS.PILLAR dataset for full exchange coverage. Verify both datasets stream concurrently. |
| 4 | Strategy signal generation (all 4, data only) | All four strategies receive data, track state machines, generate (or correctly don't generate) signals. No execution — broker can fail gracefully. Fix any bugs. |
| 5 | Multi-strategy cross-validation | Cross-strategy interactions with real data: ALLOW_ALL policy, Risk Manager cross-checks, allocation caps. Verify EventBus routing to all strategies (DEC-125). |

### Phase B: IBKR Paper Activation (Sessions 6–9)

**Goal:** IBKR paper account connected, orders placing and filling, positions tracked correctly.

| Session | Focus | Deliverable |
|---------|-------|-------------|
| 6 | IB Gateway setup + IBKRBroker connection | Gateway installed and running, IBKRBroker connects, authenticates, retrieves account info and buying power |
| 7 | Order placement + fill streaming | Place test market orders, verify fill events stream back, confirm position tracking in Order Manager. Test bracket orders (stop + T1 + T2). |
| 8 | Position management lifecycle | Full lifecycle: entry → stop management → T1 fill → stop-to-breakeven → T2 fill OR time stop. Test cancel/flatten flows. Risk Manager integration. TradeLogger persistence. |
| 9 | Reconnection + edge cases | Gateway restart recovery, mid-session disconnect/reconnect, state reconstruction from IBKR positions on ARGUS restart. Nightly reset handling. |

### Phase C: End-to-End Integration (Sessions 10–12)

**Goal:** Full system running live during market hours, visible in Command Center.

| Session | Focus | Deliverable |
|---------|-------|-------------|
| 10 | System startup sequence with live providers | `system_live.yaml` config, full 12-phase startup with Databento + IBKR, verify all components initialize correctly. Pre-market routine runs. All 4 strategies registered. |
| 11 | First live market session (all 4 strategies) 🎯 | Watch full session 9:30–4:00 ET. All four strategies process real data, generate signals, place paper trades on IBKR. Command Center shows real-time updates. Log everything. |
| 12 | Command Center verification + fixes | Verify all 7 pages work with live data (not dev mock data). WebSocket updates flow correctly. Fix any UI issues with real data shapes. Mobile PWA verification. |

### Phase D: Stability + Polish (Sessions 13–15, as needed)

**Goal:** System runs reliably across multiple market sessions.

| Session | Focus | Deliverable |
|---------|-------|-------------|
| 13 | Second full market session — stress observation | Let it run. Take notes. Fix issues found. Focus on: memory usage over time, WebSocket stability, Databento reconnection if stream drops, log volume. Startup automation script. |
| 14 | Overnight workflow + third session | Test Taipei workflow: start ~10:15 PM, monitor on phone, sleep, review in morning. Clean shutdown → clean next-day startup. Mobile PWA during actual use. |
| 15 | Final bug fixes + cleanup | Fix accumulated issues. Production logging levels. CLAUDE.md update. LIVE_OPERATIONS.md. Final clean start/run/stop verification. |

---

## 4. Session-by-Session Claude Code Prompts

### Prompt Conventions

Each prompt below is designed to be copy-pasted directly into a **new Claude Code conversation**. They include:
- Full context on what was accomplished in prior sessions
- Exact goals for this session
- Specific files and paths to reference
- Definition of done

**After each session:** Update the `[Note any specific issues]` placeholders in the NEXT session's prompt with actual findings before pasting it.

---

### Session 1: Databento Account Setup + Basic Connection

```
# ARGUS Sprint 21.5 — Session 1: Databento Basic Connection

## Context
Read CLAUDE.md and docs/10_PHASE3_SPRINT_PLAN.md for full project context.

Sprint 21.5 is the live integration sprint. We're connecting ARGUS to real Databento market data and real IBKR paper trading for the first time. The DatabentoDataService adapter was built in Sprint 12 against mocks — this session connects it to the real Databento API.

## Prerequisites (already done by user)
- Databento subscription activated (US Equities Standard, $199/mo)
- API key stored in environment variable: DATABENTO_API_KEY
- `.env` file created in project root with the key (gitignored)

## Goals for This Session
1. Create `config/system_live.yaml` — copy of `config/system.yaml` with `data_source: databento` and `broker_source: ibkr` (IBKR connection will fail gracefully for now, that's fine)
2. Create `.env.example` documenting all required environment variables (DATABENTO_API_KEY, IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, ARGUS_JWT_SECRET, ARGUS_PASSWORD_HASH)
3. Add `--config` CLI flag to main.py if not already present (check first)
4. Add `python-dotenv` to requirements if not present, wire `.env` loading into main.py startup
5. Start the system with `--config system_live.yaml` and attempt to connect DatabentoDataService to the live Databento API
6. Initial dataset: XNAS.ITCH (Nasdaq TotalView-ITCH). Configured in `config/databento.yaml`.
7. Debug and fix any connection issues (authentication, dataset selection, session creation)
8. Verify: raw Databento records are being received and logged. We don't need them fully processed yet — just confirm the connection works and data flows.

## Key Files
- `argus/data/databento_data_service.py` — the adapter to test
- `argus/data/databento_utils.py` — normalization utilities
- `config/system.yaml` — base config to copy from
- `config/databento.yaml` — Databento-specific config
- `argus/main.py` — startup sequence

## Definition of Done
- `system_live.yaml` exists with databento data source configured
- `.env.example` exists documenting required env vars
- System starts without crash using `--config system_live.yaml`
- DatabentoDataService connects to Databento API with XNAS.ITCH dataset
- Raw data records appear in logs (even if not yet fully processed)
- Any connection errors are diagnosed and fixed
- Commit: `feat(integration): databento live connection + system_live config`
```

---

### Session 2: Data Flow Validation

```
# ARGUS Sprint 21.5 — Session 2: Databento Data Flow Validation

## Context
Read CLAUDE.md for full project context. Sprint 21.5 Session 1 established basic Databento connection. Raw records are flowing from XNAS.ITCH dataset.

## What Session 1 Accomplished
- `system_live.yaml` created with `data_source: databento`
- `.env` / `.env.example` set up with DATABENTO_API_KEY
- DatabentoDataService connects to Databento API and receives raw records
- [Note any specific issues found/fixed in Session 1]

## Goals for This Session
1. Verify databento_utils.py `normalize_databento_df()` correctly processes live records (timestamp normalization, column mapping, UTC handling)
2. Verify CandleEvents are published to EventBus with correct symbol, OHLCV data, and timestamps
3. Verify IndicatorEngine receives CandleEvents and computes indicators:
   - VWAP (should reset daily, accumulate intraday)
   - ATR-14 (should have meaningful values after warmup period)
   - SMA-9, SMA-20, SMA-50
   - RVOL (relative volume vs historical average)
4. Verify IndicatorEvents are published with correct values
5. Compare a few data points against Databento's web dashboard or another source to confirm accuracy
6. Fix any issues with data normalization, timestamp handling, or indicator computation

## Key Files
- `argus/data/databento_data_service.py`
- `argus/data/databento_utils.py`
- `argus/data/indicator_engine.py`
- `argus/core/event_bus.py`

## Testing Approach
- Start system during market hours (or use Databento's replay/historical API if outside market hours)
- Add temporary debug logging to IndicatorEngine to print computed values
- Spot-check: pick 2-3 symbols, compare VWAP/SMA values against a reference (Databento dashboard, TradingView, etc.)

## Definition of Done
- CandleEvents flowing through EventBus with correct data
- All 5 indicators computing without errors
- Spot-check confirms indicator values are in the right ballpark (within 0.1% for VWAP/SMA)
- No crashes or unhandled exceptions during 30+ minutes of data flow
- Commit: `fix(integration): databento data flow validation + indicator fixes`
```

---

### Session 3: Scanner + Watchlist + NYSE Dataset

```
# ARGUS Sprint 21.5 — Session 3: Scanner + Watchlist + NYSE Dataset

## Context
Read CLAUDE.md for full project context. Sprint 21.5, Session 2 confirmed Databento data flows correctly through EventBus and IndicatorEngine on the XNAS.ITCH (Nasdaq) dataset.

## What Sessions 1-2 Accomplished
- DatabentoDataService connects and streams live Nasdaq data
- CandleEvents published correctly, IndicatorEngine computes all indicators
- [Note any specific issues found/fixed]

## Goals for This Session
1. Add XNYS.PILLAR (NYSE) dataset to Databento configuration
   - Update `config/databento.yaml` to include both XNAS.ITCH and XNYS.PILLAR
   - Verify DatabentoDataService can subscribe to multiple datasets concurrently
   - Confirm both datasets stream data without conflicts (symbol collisions, timestamp interleaving)
   - This uses 2 of the 10 allowed concurrent sessions on the Standard plan
2. Verify DatabentoScanner produces a gap watchlist at/before market open
   - Check: symbols with gap >= min_gap_pct (2.0%) appear from BOTH exchanges
   - Check: symbols below min_price are filtered out
   - Check: watchlist is published before 9:35 AM ET (ORB earliest_entry)
3. Verify Orchestrator pre-market routine receives the watchlist and distributes to strategies
4. Verify strategies subscribe to the correct symbols for data streaming
5. If outside market hours: use DataFetcher to pull Databento historical data for a recent date and simulate the scanner flow (also tests the historical data pipeline)

## Key Files
- `argus/data/databento_data_service.py` — multi-dataset subscription
- `argus/data/databento_scanner.py`
- `argus/data/data_fetcher.py` (historical data + Databento backend)
- `argus/core/orchestrator.py` (pre-market routine)
- `config/databento.yaml` — dataset configuration
- `config/scanner.yaml`

## Important Notes
- DatabentoScanner V1 is watchlist-based (DEC-137) — verify the watchlist config has symbols from both exchanges
- Gap calculation requires previous close + current open. Confirm DatabentoScanner has access to both.
- If running outside market hours, historical mode testing is equally valuable.
- Watch for: symbol format differences between XNAS and XNYS, duplicate symbol handling if a symbol appears on both

## Definition of Done
- Both XNAS.ITCH and XNYS.PILLAR streaming concurrently without errors
- Scanner produces a non-empty watchlist of gapped stocks from both exchanges
- Watchlist distributed to strategies via Orchestrator
- Historical data fetch from Databento works correctly (Parquet cache populated)
- Commit: `feat(integration): NYSE dataset + scanner live validation`
```

---

### Session 4: Strategy Signal Generation (All 4 Strategies)

```
# ARGUS Sprint 21.5 — Session 4: All Strategy Live Signals (Data Only)

## Context
Read CLAUDE.md for full project context. Sprint 21.5, Sessions 1-3 established Databento data flow (Nasdaq + NYSE) and scanner. This session tests all four strategies with real data — no execution yet.

## What Sessions 1-3 Accomplished
- Full Databento data pipeline working: connection → normalization → EventBus → IndicatorEngine → indicators
- Both XNAS.ITCH and XNYS.PILLAR datasets streaming concurrently
- Scanner produces watchlist from both exchanges, distributed to strategies
- [Note any specific issues]

## Goals for This Session
1. Enable all four strategies in `system_live.yaml`
2. Run during market hours and observe each strategy's behavior:
   - **ORB (9:35-11:30):** Receives CandleEvents? Identifies opening range (5 min, DEC-076)? Tracks OR high/low? Evaluates breakout conditions? Generates SignalEvent or logs valid rejection?
   - **ORB Scalp (9:45-11:30):** Shared scanner working? Different exit params applied? Scalp-specific timing (DEC-122)?
   - **VWAP Reclaim (10:00-12:00):** 5-state machine (DEC-138)? Pullback detection? VWAP distance tracking?
   - **Afternoon Momentum (2:00-3:30):** Consolidation detection (DEC-153)? Channel tracking? (Only visible if session runs past 2 PM ET)
3. Verify DEC-076 parameters correctly applied for ORB strategies
4. Add detailed strategy-level logging for this session (can be reduced later)
5. If a signal IS generated, verify it reaches Risk Manager for evaluation
6. IBKR connection will fail gracefully — that's expected. We're validating strategy logic, not execution.

## Key Files
- `argus/strategies/orb_breakout.py`
- `argus/strategies/orb_scalp.py`
- `argus/strategies/vwap_reclaim.py`
- `argus/strategies/afternoon_momentum.py`
- `argus/strategies/orb_base.py`
- Config files in `config/strategies/`

## Important Notes
- It's entirely possible that no signals are generated — that's fine if the reasons are correct (no sufficient gaps, no clean breakouts, risk filters blocking)
- The important thing is that each strategy PROCESSES data correctly and makes correct decisions
- Each strategy logs with its name prefix — use this to separate issues per strategy

## Definition of Done
- All four strategies process real Databento data without errors
- Opening range correctly identified for ORB family
- Each strategy's state machine transitions correctly during its active window
- Signals generated OR valid rejections logged for each strategy
- Commit: `fix(integration): all strategies live data validation`
```

---

### Session 5: Multi-Strategy Cross-Validation

```
# ARGUS Sprint 21.5 — Session 5: Cross-Strategy Interactions

## Context
Read CLAUDE.md for full project context. Sprint 21.5, Session 4 validated all four strategies individually with real data. This session focuses on how they interact.

## What Sessions 1-4 Accomplished
- Full data pipeline + scanner + all 4 strategies processing real Databento data
- [Specific findings from Session 4 — signals generated? state machine issues?]

## Goals for This Session
1. Focus on cross-strategy interactions with real data:
   - ALLOW_ALL duplicate stock policy (DEC-121): if same symbol appears in ORB and ORB Scalp watchlists, both process it independently
   - Risk Manager cross-strategy position checks (DEC-124): Risk Manager queries Order Manager via `get_managed_positions()` for cross-strategy exposure
   - Per-strategy allocation caps (DEC-119): single strategy 40% max, verified in Orchestrator
   - max_single_stock_pct (5%) enforced across all strategies (DEC-160)
2. Verify CandleEvent routing via EventBus reaches all strategies simultaneously (DEC-125)
3. Verify Orchestrator regime monitoring (30-min cycle) with real SPY data from Databento
4. Verify PerformanceThrottler tracking (consecutive losses — nothing should trigger yet, but verify the tracking mechanism works)
5. Run for a full market session if possible — longest continuous test so far

## Key Files
- `argus/core/orchestrator.py` — routing, allocation, regime
- `argus/core/risk_manager.py` — cross-strategy checks
- `argus/execution/order_manager.py` — position queries
- `argus/core/regime_classifier.py`
- `argus/core/performance_throttler.py`

## Definition of Done
- Cross-strategy risk controls verified working with real data
- Regime classification produces valid results from live SPY data
- EventBus routes CandleEvents to all 4 strategies concurrently
- No crashes during 2+ hours of concurrent strategy execution
- Commit: `fix(integration): cross-strategy interactions validated with live data`
```

---

### Session 6: IB Gateway Setup + Connection

```
# ARGUS Sprint 21.5 — Session 6: IBKR Gateway + Broker Connection

## Context
Read CLAUDE.md for full project context. Sprint 21.5 Phase B — connecting to IBKR paper trading. Phase A (Databento) is complete.

## Prerequisites (user has done or will do alongside this session)
- IBKR account approved (Account ID: U24619949) ✅
- IB Gateway downloaded and installed (https://www.interactivebrokers.com/en/trading/ibgateway-stable.php)
- Paper trading mode enabled in IBKR account settings
- Gateway started and logged in to paper trading account
- Note: Paper trading accounts typically have a "DU" prefix (e.g., DU12345)

## Goals for This Session
1. Configure IBKR connection parameters:
   - Add IBKR env vars to `.env` and `.env.example`: IBKR_HOST (127.0.0.1), IBKR_PORT (4002 for paper), IBKR_CLIENT_ID (1)
   - Verify `config/system_live.yaml` has `broker_source: ibkr`
   - Verify `config/ibkr.yaml` has correct connection settings
2. Ensure IB Gateway is in API mode:
   - Gateway Config → Settings → API → Enable ActiveX and Socket Clients
   - Socket port: 4002 (paper trading)
   - Trusted IPs: 127.0.0.1
3. Start ARGUS with `--config system_live.yaml` and attempt IBKRBroker connection
4. Debug connection issues (common: wrong port, client ID conflict, Gateway not in API mode, paper trading not enabled, firewall blocking localhost)
5. Once connected, verify:
   - Account info retrieval (buying power, account value)
   - Position query (should be empty initially)
   - Order query (should be empty)
6. Test basic order placement: place a small market buy order for a liquid stock (e.g., AAPL, 1 share)
7. Verify fill event streams back to IBKRBroker

## Key Files
- `argus/execution/ibkr_broker.py`
- `config/ibkr.yaml`
- `config/system_live.yaml`

## Safety Checks — VERIFY BEFORE ANY ORDER PLACEMENT
- [ ] IB Gateway login screen/status shows "Paper Trading" mode
- [ ] Account ID displayed starts with "DU" (paper), NOT "U" (live)
- [ ] `ibkr.yaml` has `port: 4002` (paper), NOT `port: 4001` (live)
- [ ] IBKRBroker connection log shows paper trading account ID

## Definition of Done
- IB Gateway running and accepting API connections on port 4002
- IBKRBroker connects successfully to paper account
- Account info retrieved correctly (buying power, equity)
- Test order placed and filled (1 share of liquid stock)
- Fill event received by IBKRBroker
- Paper account safety triple-checked
- Commit: `feat(integration): IBKR paper trading connection established`
```

---

### Session 7: Order Placement + Fill Streaming

```
# ARGUS Sprint 21.5 — Session 7: IBKR Order Lifecycle

## Context
Read CLAUDE.md for full project context. Session 6 established basic IBKR connection and placed a test order. This session tests the full bracket order lifecycle.

## What Session 6 Accomplished
- IB Gateway running, IBKRBroker connected to paper account
- Basic order placement works, fills stream back
- [Note account ID, any connection quirks, port/client ID used]

## Goals for This Session
1. Test bracket order placement via IBKRBroker.place_bracket_order():
   - Entry (market order) + Stop + T1 (limit) + T2 (limit)
   - Verify all component orders are submitted atomically (DEC-093, DEC-117)
   - Verify parentId linkage and transmit flag sequencing
2. Test fill streaming:
   - Entry fill → ManagedPosition created in Order Manager
   - T1 fill → partial position closed, stop-to-breakeven triggered
   - T2 fill → remaining position closed
   - Verify bracket_stop_order_id, bracket_t1_order_id, bracket_t2_order_id tracking
3. Test stop-loss fill:
   - Place bracket, then wait for paper account to simulate stop trigger
   - Verify stop fills, remaining orders (T1, T2) are cancelled
4. Test order cancellation:
   - Cancel an open order, verify status update streams back
5. Test flatten position:
   - Open a position, then flatten via Order Manager
   - Verify all bracket components are cancelled, market exit order placed

## Key Files
- `argus/execution/ibkr_broker.py`
- `argus/execution/order_manager.py`
- `argus/execution/models.py` (ManagedPosition)

## Important Notes
- Paper trading fills may be delayed or fill at unexpected prices — this is normal IBKR paper behavior
- Bracket orders on IBKR paper may behave slightly differently than live (stop triggers are simulated)
- Focus on verifying the ORDER FLOW logic, not fill price accuracy
- You may need to place multiple brackets to test all paths (T1 hit, T2 hit, stop hit)

## Definition of Done
- Bracket orders (entry + stop + T1 + T2) submit and fill correctly
- Order Manager correctly tracks all bracket component IDs
- Stop-to-breakeven triggers after T1 fill
- Order cancellation works
- Flatten position works (cancels brackets, places exit)
- Commit: `fix(integration): IBKR bracket order lifecycle validation`
```

---

### Session 8: Position Management Lifecycle

```
# ARGUS Sprint 21.5 — Session 8: Full Position Management

## Context
Read CLAUDE.md for full project context. Session 7 validated bracket orders on IBKR. This session tests the higher-level position management that the Order Manager performs, plus Risk Manager and TradeLogger integration.

## What Session 7 Accomplished
- Bracket orders submit and fill correctly on IBKR paper
- Order Manager tracks bracket component IDs
- Cancel and flatten flows work
- [Note any specific issues]

## Goals for This Session
1. Test the complete Order Manager tick-monitoring cycle:
   - Position opened → Order Manager subscribes to tick events for symbol
   - Tick events arrive → time stop countdown active
   - Time stop triggers → position flattened
2. Test EOD flatten:
   - Manually set system time near market close (or wait for actual close)
   - Verify Order Manager's scheduled EOD flatten fires
   - All open positions closed, all pending orders cancelled
3. Test the 5-second fallback poll:
   - Verify Order Manager poll loop checks position health
   - Covers edge case where tick events are delayed
4. Test Risk Manager integration:
   - Simulate a signal that should be approved → verify position opens
   - Simulate a signal that should be rejected (e.g., would exceed max_single_stock_pct) → verify rejection
   - Verify daily loss limit tracking with real trade P&L
5. Test TradeLogger integration:
   - Completed trades written to database
   - Query trades via API — verify Trade Log page shows real completed trades

## Key Files
- `argus/execution/order_manager.py`
- `argus/core/risk_manager.py`
- `argus/analytics/trade_logger.py`
- `argus/api/routes/trades.py`

## Definition of Done
- Full position lifecycle works: signal → risk check → order → fill → management → exit → logged
- Time stop triggers correctly
- EOD flatten works
- Risk Manager correctly approves/rejects based on live state
- Trades appear in database and are queryable via API
- Commit: `fix(integration): position management lifecycle with IBKR paper`
```

---

### Session 9: IBKR Reconnection + Edge Cases

```
# ARGUS Sprint 21.5 — Session 9: IBKR Resilience

## Context
Read CLAUDE.md for full project context. Session 8 completed position management validation. This session tests failure and recovery scenarios.

## What Session 8 Accomplished
- Full position lifecycle working end-to-end
- Risk Manager integration verified
- TradeLogger persisting completed trades
- [Note any specific issues]

## Goals for This Session
1. Test IB Gateway disconnect/reconnect:
   - While ARGUS is running, restart IB Gateway
   - Verify IBKRBroker detects disconnect
   - Verify automatic reconnection attempt
   - Verify state reconstruction: open positions, pending orders rebuilt from IBKR
2. Test nightly Gateway restart handling:
   - IB Gateway auto-restarts daily (configurable time, default ~midnight ET)
   - Verify ARGUS handles the brief disconnect gracefully
   - No orphaned positions, no duplicate orders
3. Test mid-session ARGUS restart:
   - With open positions on IBKR, stop and restart ARGUS
   - Verify state reconstruction: ARGUS queries IBKR for open positions/orders
   - ManagedPosition objects rebuilt correctly
   - Order Manager resumes management of existing positions
4. Test network timeout scenarios:
   - Temporarily block IBKR port (simulate network issue)
   - Verify timeout handling, error logging, reconnection

## Key Files
- `argus/execution/ibkr_broker.py` (reconnection logic)
- `argus/execution/order_manager.py` (state reconstruction)
- `argus/main.py` (startup reconstruction phase)

## Important Notes
- State reconstruction is critical for Taipei operation — Steven may need to restart ARGUS during US market hours (his overnight)
- Focus on: no duplicate orders after reconnect, no orphaned positions, no lost fills

## Definition of Done
- Gateway restart → automatic reconnection → state rebuilt
- ARGUS restart → positions/orders reconstructed from IBKR
- No duplicate orders in any restart scenario
- Clean error logging for all failure modes
- Commit: `fix(integration): IBKR reconnection + state reconstruction validation`
```

---

### Session 10: Full System Startup with Live Providers

```
# ARGUS Sprint 21.5 — Session 10: End-to-End System Startup

## Context
Read CLAUDE.md for full project context. Phase A (Databento, Sessions 1-5) and Phase B (IBKR, Sessions 6-9) are complete individually. This session combines both for the first time.

## What Has Been Accomplished
- Databento: live streaming (XNAS + XNYS), indicators, scanner, all 4 strategies processing data correctly
- IBKR: connection, bracket orders, position management, reconnection, state reconstruction
- Each provider tested independently — this is the first combined test

## Goals for This Session
1. Start ARGUS with `system_live.yaml` — BOTH Databento data AND IBKR execution active simultaneously
2. Walk through the full 12-phase startup sequence and verify each phase:
   - Phase 1: Config loading (system_live.yaml)
   - Phase 2: Database initialization
   - Phase 3: Broker connection (IBKR paper)
   - Phase 4: Event Bus
   - Phase 5: Risk Manager
   - Phase 6: Data Service (Databento — both datasets)
   - Phase 7: Scanner (Databento)
   - Phase 8: Strategies (all 4)
   - Phase 9: Order Manager
   - Phase 10: Health Monitor
   - Phase 11: API Server
   - Phase 12: Orchestrator (pre-market routine)
3. Verify Orchestrator pre-market routine runs with both providers active:
   - Scanner produces watchlist (Databento data)
   - Regime classification runs (SPY data from Databento)
   - Allocation computed
   - Strategies initialized with watchlist
4. Verify all 4 strategies are registered and ready
5. Fix any issues with the combined startup (this is where interaction bugs between the two providers typically surface)
6. If outside market hours: verify startup completes cleanly and system enters "waiting for market open" state

## Key Files
- `argus/main.py` — full startup sequence
- `config/system_live.yaml`
- `argus/core/orchestrator.py`

## Definition of Done
- Full 12-phase startup completes without errors with both Databento + IBKR
- Pre-market routine runs successfully
- All 4 strategies registered and ready
- System enters "ready" state, waiting for market data
- All components healthy (verify via GET /api/v1/health)
- Commit: `feat(integration): full system startup with Databento + IBKR`
```

---

### Session 11: First Live Market Session 🎯

```
# ARGUS Sprint 21.5 — Session 11: First Live Market Session 🎯

## Context
Read CLAUDE.md for full project context. This is THE milestone session — ARGUS running live during market hours with real data and paper execution for the first time. All four strategies active.

## IMPORTANT: This session MUST be run during US market hours (9:30 AM – 4:00 PM ET / 10:30 PM – 5:00 AM Taipei time)

## Pre-Session Checklist
- [ ] IB Gateway running, logged into PAPER account (verify "DU" prefix)
- [ ] Databento subscription active
- [ ] `system_live.yaml` configured: data_source=databento, broker_source=ibkr
- [ ] `.env` has all required keys (DATABENTO_API_KEY, IBKR_HOST/PORT/CLIENT_ID, JWT, password hash)
- [ ] Command Center frontend running (`cd argus/ui && npm run dev`)
- [ ] All four strategies enabled in config

## Goals for This Session
1. Start ARGUS with `--config system_live.yaml` at least 15 minutes before market open (9:15 AM ET)
2. Open Command Center in browser — verify Dashboard loads
3. Monitor the full session across all strategy windows:
   - **Pre-market:** Watchlist generation, regime classification, allocation
   - **9:30 AM:** Market opens, Databento data streaming begins
   - **9:30-9:35:** ORB opening range tracking
   - **9:35-11:30:** ORB + ORB Scalp breakout evaluation, signal generation
   - **10:00-12:00:** VWAP Reclaim state machine (WATCHING → ACCUMULATING → etc.)
   - **2:00-3:30:** Afternoon Momentum consolidation detection + breakout
   - **3:45 PM:** Afternoon Momentum force close (DEC-159)
   - **4:00 PM:** EOD flatten, cleanup
   - If signals generated: watch trades execute on IBKR paper, appear in Command Center
   - Position management: stops, targets, time stops
4. Monitor cross-strategy interactions in real-time:
   - Same symbol in multiple strategies? ALLOW_ALL policy working?
   - Allocation caps enforced? max_single_stock_pct checked?
   - Orchestrator regime monitoring (30-min cycle)?
5. Document everything:
   - Screenshots of Command Center during key moments
   - Log any errors, unexpected behavior, UI issues
   - Note data quality concerns (stale quotes, missing bars, indicator anomalies)
6. Fix critical issues found during the session (non-critical logged for later sessions)

## What To Watch For
- Data gaps (missing bars, especially around market open when volume spikes)
- Timestamp alignment (Databento timestamps vs system clock vs IBKR timestamps)
- Strategy state machine transitions (log level should be DEBUG for strategies)
- Order Manager behavior when signals fire
- WebSocket updates to Command Center (should be real-time, <2s delay)
- Dashboard metrics updating correctly

## Key Monitoring Points
- Command Center Dashboard: live data flowing? Positions appearing?
- Command Center Trade Log: trades appearing after fills?
- Command Center Orchestrator: regime, allocation, decisions?
- Command Center System: all components healthy?
- Terminal logs: any errors or warnings?

## Definition of Done
- Full market session completed without system crashes
- All four strategies processed data during their active windows
- At least one complete data cycle per strategy observed (data → state transition → decision logged)
- Command Center displays real data correctly
- If trades occurred: full lifecycle visible in UI (entry → management → exit)
- Session notes documented with issues to fix
- Commit: `feat(integration): first live market session — all strategies operational`
```

---

### Session 12: Command Center Verification + Fixes

```
# ARGUS Sprint 21.5 — Session 12: Command Center with Live Data

## Context
Read CLAUDE.md for full project context. Session 11 completed the first live market session. This session focuses on the Command Center with real (not mock) data.

## What Session 11 Accomplished
- First full live market session completed
- All 4 strategies processed real data
- [Trades generated? How many? Which strategies?]
- [Issues found? Data quality? UI problems?]

## Goals for This Session
1. Verify all 7 Command Center pages with LIVE data (not `--dev` mock mode):
   - **Dashboard**: OrchestratorStatusStrip, StrategyDeploymentBar, GoalTracker, MarketStatus, TodayStats, SessionTimeline, RecentTrades, OpenPositions — all showing real data?
   - **Trade Log**: Real completed trades from Session 11, filtering works, pagination works, CSV export works
   - **Performance**: Metrics computed from real trades (may be limited data), equity curve, daily P&L
   - **Orchestrator**: Live session phase, regime classification, strategy operations grid, decision timeline, capital allocation donut
   - **Pattern Library**: Strategy cards with real pipeline stages, spec sheets accessible
   - **The Debrief**: Create a real post-Session-11 briefing, journal entry documenting first live session, test research library
   - **System**: All component health statuses reflecting real state (Databento connected, IBKR connected, strategies active/inactive based on time)
2. Verify WebSocket real-time updates:
   - Open positions show live price updates from Databento
   - Strategy state changes reflected immediately
   - Trade fills appear in real-time
3. Test responsive design with live data:
   - Desktop (full browser)
   - Tablet (834px responsive or iPad)
   - Mobile (393px responsive or iPhone — check PWA if configured)
4. Fix any UI issues:
   - Data shape mismatches (real data vs expected format)
   - Missing null/undefined guards for data that doesn't exist yet
   - Layout issues with real string lengths (symbol names, dollar amounts, percentages)
   - Empty states where data is expected but hasn't accumulated yet

## Key Files
- All files in `argus/ui/src/`
- `argus/api/routes/` (all route files)
- `argus/api/websocket.py`

## Definition of Done
- All 7 pages render correctly with live data
- WebSocket real-time updates working
- No console errors in browser
- Responsive layout confirmed at all 3 breakpoints
- At least one Debrief briefing + journal entry created with real session data
- Commit: `fix(integration): command center live data verification + fixes`
```

---

### Session 13: Stability Observation (Second Full Session)

```
# ARGUS Sprint 21.5 — Session 13: Stability + Automation

## Context
Read CLAUDE.md for full project context. Core integration is complete (Sessions 1-12). This session is about observing the system run, catching time-dependent issues, and creating operational tooling.

## MUST be run during US market hours.

## Goals for This Session
1. Run a full market session with all four strategies active — second live session
2. Monitor for stability issues:
   - Memory usage growth over time (watch Python process RSS — `ps aux | grep argus` periodically)
   - WebSocket connection stability (does the Command Center lose connection after extended periods?)
   - Databento stream reliability (any reconnections? data gaps? stale data warnings?)
   - IBKR connection stability (heartbeat OK? any timeouts?)
   - Log file growth (is logging too verbose? disk filling?)
3. Create a startup script (`scripts/start_live.sh` or similar) that:
   - Checks IB Gateway is running (exit with error if not)
   - Checks `.env` exists with required vars
   - Starts ARGUS with `--config system_live.yaml`
   - Optionally starts the frontend dev server
   - Redirects logs to dated file (`logs/argus_YYYY-MM-DD.log`)
4. Create a shutdown script (`scripts/stop_live.sh`) that:
   - Sends graceful shutdown signal to ARGUS
   - Waits for clean exit (positions closed, DB committed)
   - Logs shutdown time
5. Document any new issues for Sessions 14-15

## Definition of Done
- Second full session completed, stability notes documented
- startup/shutdown scripts created and tested
- Memory/connection stability confirmed over full session (no growth, no drops)
- Commit: `feat(integration): operational scripts + stability observation`
```

---

### Session 14: Overnight Workflow + Third Session

```
# ARGUS Sprint 21.5 — Session 14: Taipei Overnight Workflow

## Context
Read CLAUDE.md for full project context. Testing the real-world Taipei overnight workflow — this is how Steven will actually operate ARGUS day-to-day.

## MUST be run during US market hours, from Taipei (or simulating the timezone experience).

## Goals for This Session
1. Test the full Taipei workflow:
   - Start system ~10:15 PM Taipei time (15 min before US open) using startup script from Session 13
   - Monitor on phone (mobile browser or PWA) during pre-market and market open
   - Observe first 30-60 minutes of trading on phone — is the mobile experience sufficient for monitoring?
   - Let system run unattended for several hours (simulate sleeping)
   - Review results after US close (morning in Taipei)
2. Test clean shutdown after market close:
   - All positions closed by EOD flatten
   - Database committed
   - Databento session closed cleanly
   - IBKR orders all cancelled/filled
   - Use shutdown script
3. Test clean startup the next day:
   - Fresh start with startup script
   - Verify system comes up clean — no stale state from yesterday
   - Database has yesterday's trades, today starts fresh
4. Mobile experience assessment (take notes):
   - Dashboard readable on phone? Key metrics visible above the fold?
   - Can you see enough info to decide if intervention is needed?
   - WebSocket updates working on mobile?
   - Any layout issues with real data on small screen?
5. If any issues, fix immediately or log for Session 15

## Definition of Done
- Full overnight workflow completed: start → run → shutdown → next-day start
- Mobile monitoring experience assessed with real data
- Clean shutdown → clean startup verified
- Commit: `fix(integration): overnight workflow + mobile verification`
```

---

### Session 15: Final Bug Fixes + Cleanup

```
# ARGUS Sprint 21.5 — Session 15: Sprint Closeout

## Context
Read CLAUDE.md for full project context. Final session of Sprint 21.5. Fix accumulated issues and create operational documentation.

## Goals for This Session
1. Fix all issues documented in Sessions 11-14 that haven't been addressed yet
2. Adjust logging levels for production use:
   - Strategy decisions: INFO
   - Data flow (individual bars): WARNING (reduce noise from Databento stream)
   - Order events: INFO
   - Fill events: INFO
   - System health: INFO
   - Connection events (connect/disconnect/reconnect): INFO
   - Tick-level data: DEBUG only
   - Indicator computation: DEBUG only
3. Update CLAUDE.md with:
   - New commands (startup/shutdown scripts, `--config system_live.yaml`)
   - Updated "Current State" reflecting live integration complete
   - Any new architectural rules discovered during integration
   - Databento + IBKR connection details
4. Create `docs/LIVE_OPERATIONS.md`:
   - How to start the system (startup script + manual steps)
   - How to stop the system safely (shutdown script)
   - How to restart mid-session (state reconstruction expected behavior)
   - What to monitor during operation (key log messages, Command Center pages)
   - Common issues and fixes (Gateway disconnects, Databento reconnection, stale data)
   - IB Gateway maintenance (nightly restart schedule, manual restart procedure)
   - Emergency procedures (flatten all, pause all, kill process)
5. Run final system check: start → run 30 min → verify all healthy → stop cleanly
6. Update test counts if any new tests were added during integration fixes

## Definition of Done
- All tracked issues resolved
- Logging levels production-appropriate (not too noisy, not missing important events)
- CLAUDE.md updated with live integration context
- LIVE_OPERATIONS.md created and comprehensive
- Clean start → run → stop verified one final time
- Final commit: `feat(integration): sprint 21.5 complete — live integration operational`
```

---

## 5. Code Review Plan

### Review Schedule

| After Session | Review Focus | Materials Needed |
|---------------|-------------|-----------------|
| **Session 5** (end of Phase A) | Databento data integrity | Git diff Sessions 1-5, sample data logs, indicator spot-check results |
| **Session 9** (end of Phase B) | IBKR execution integrity + risk | Git diff Sessions 6-9, test order logs, reconnection test results |
| **Session 12** (end of Phase C) | End-to-end system + UI verification | Git diff Sessions 10-12, Command Center screenshots (all 7 pages × 3 breakpoints), Session 11 observation notes |

### Code Review Procedure

For each review:

1. **Prepare** (before starting review conversation):
   - `git log --oneline` for all commits since last review
   - `git diff <last-review-commit>..HEAD --stat` for scope of changes
   - Copy any observation notes / issue lists from sessions
   - Take Command Center screenshots if UI-related review

2. **Review conversation** (new Claude.ai chat with handoff brief below):
   - Claude reviews the diff, asks questions, flags concerns
   - Discuss any architectural issues or decisions that emerged
   - Log any new decisions (DEC-XXX)
   - Identify items to fix before proceeding

3. **Post-review**:
   - Fix any issues flagged
   - Update docs (Decision Log, Project Knowledge, CLAUDE.md)
   - Commit fixes: `fix(review): sprint 21.5 review N fixes`

### Final Sprint Review

After Session 15, conduct a final sprint review covering:
- Test count delta (new tests added during integration fixes)
- All decisions made during the sprint
- Updated Project Knowledge reflecting live system state
- Sprint 22 readiness check

---

## 6. Code Review Handoff Briefs

### Review 1: Post-Phase A (After Session 5)

```
# ARGUS Sprint 21.5 — Code Review 1: Databento Integration

## What to Review
Sprint 21.5, Phase A (Sessions 1-5) — Databento live data integration.

## Context
Read the project instructions for full ARGUS context. Sprint 21.5 is the live integration sprint, connecting the DatabentoDataService adapter (built in Sprint 12 against mocks) to the real Databento API, and validating data flow through the entire pipeline including all four strategies.

## What Was Built/Changed in Sessions 1-5
- `config/system_live.yaml` — new config file for Databento + IBKR operation
- `.env.example` — documented environment variables
- Databento multi-dataset support (XNAS.ITCH + XNYS.PILLAR)
- Fixes to `argus/data/databento_data_service.py` for live connection issues
- Fixes to `argus/data/databento_utils.py` for real data normalization
- Fixes to `argus/data/indicator_engine.py` for live indicator computation
- Fixes to `argus/data/databento_scanner.py` for live watchlist generation
- Fixes to strategy files for real data handling
- Any new test additions

## Review Checklist
1. **Data integrity**: Are CandleEvents correctly normalized? Timestamps correct? OHLCV values sensible?
2. **Multi-dataset**: XNAS + XNYS streaming concurrently without conflicts?
3. **Indicator accuracy**: VWAP, ATR, SMA values validated against reference source?
4. **Scanner reliability**: Watchlist generated before strategy windows open? Both exchanges represented?
5. **Strategy behavior**: All 4 state machines transitioning correctly with real data?
6. **Cross-strategy**: ALLOW_ALL, allocation caps, risk checks working?
7. **Error handling**: Graceful handling of data gaps, reconnection, malformed records?
8. **Config management**: system_live.yaml clean? Secrets properly externalized?
9. **Logging**: Appropriate levels? Useful for debugging without being noisy?

## Materials
[Paste git log, git diff --stat, and any observation notes here]

## Decisions to Log
[List any decisions made during Sessions 1-5 that need DEC-XXX entries]
```

---

### Review 2: Post-Phase B (After Session 9)

```
# ARGUS Sprint 21.5 — Code Review 2: IBKR Integration

## What to Review
Sprint 21.5, Phase B (Sessions 6-9) — IBKR paper trading integration.

## Context
Read the project instructions for full ARGUS context. This phase connected the IBKRBroker adapter (built in Sprint 13 against mocks) to the real IB Gateway paper trading account.

## What Was Built/Changed in Sessions 6-9
- IB Gateway setup and configuration documentation
- IBKR env vars in `.env` / `.env.example`
- Fixes to `argus/execution/ibkr_broker.py` for live connection issues
- Fixes to `argus/execution/order_manager.py` for real bracket order handling
- Fixes to state reconstruction logic
- Reconnection/recovery fixes
- Risk Manager integration with live positions
- TradeLogger integration with real trades
- Any new test additions

## Review Checklist
1. **Order integrity**: Bracket orders submit correctly? All components linked via parentId?
2. **Fill handling**: Fills stream back and update ManagedPosition correctly? T1/T2 splits accurate?
3. **Risk controls**: Position sizing correct? Stop placement correct? Daily limits enforced? Cross-strategy checks working?
4. **State reconstruction**: After ARGUS restart, positions/orders rebuilt accurately from IBKR?
5. **Reconnection**: Gateway restart handled gracefully? No duplicate orders? No orphaned positions?
6. **Safety**: Paper account confirmed in code and config? No path to live execution?
7. **Error handling**: What happens on timeout? Rejected order? Partial fill? Network drop?
8. **TradeLogger**: Completed trades persisted correctly? Queryable via API?

## Materials
[Paste git log, git diff --stat, test order logs, reconnection test results]

## Decisions to Log
[List any decisions made during Sessions 6-9 that need DEC-XXX entries]
```

---

### Review 3: Post-Phase C (After Session 12)

```
# ARGUS Sprint 21.5 — Code Review 3: End-to-End System + Live Session

## What to Review
Sprint 21.5, Phase C (Sessions 10-12) — Full system integration with live data and paper execution, including the first live market session.

## Context
Read the project instructions for full ARGUS context. This phase combined Databento data and IBKR execution for the first time, ran the first live market session with all four strategies, and validated the Command Center with real data.

## What Was Built/Changed in Sessions 10-12
- Combined Databento + IBKR startup sequence fixes
- Fixes to `argus/main.py` startup phases for dual-provider operation
- Fixes to `argus/core/orchestrator.py` for live operation
- Fixes to API endpoints and WebSocket for real data shapes
- UI fixes for real data rendering
- Session 11 observation notes and fixes

## Review Checklist
1. **System integrity**: Full 12-phase startup clean with both providers? All components healthy?
2. **Data → Execution pipeline**: Signal → Risk → Order → Fill → Log chain unbroken?
3. **Orchestrator**: Pre-market routine, regime classification, allocation — all working with live data?
4. **All 4 strategies**: Each processed data during its window? Correct decisions made?
5. **Command Center**: All 7 pages functional with real data? WebSocket real-time updates working?
6. **Responsive design**: Desktop, tablet, mobile all rendering correctly with real data?
7. **Session lifecycle**: Clean startup, clean shutdown, no orphaned state between sessions?
8. **Performance**: Any latency concerns? Memory growth? Excessive logging?

## Session 11 Observation Notes
[Paste your notes from the first live market session — what happened, any trades, any issues, screenshots]

## Materials
[Paste git log, git diff --stat, Command Center screenshots (all 7 pages × 3 breakpoints)]

## Decisions to Log
[List any decisions made during Sessions 10-12 that need DEC-XXX entries]
```

---

## 7. Sprint 21.6 — Backtest Re-Validation (Separate Sprint, Docs Later)

DEC-132 backtest re-validation is deliberately separated from Sprint 21.5. Full spec, prompts, and review plan will be drafted when Sprint 21.5 is nearing completion — informed by integration discoveries.

**Scope preview:**
1. Pull Databento historical data for all 28+ backtest symbols across 35 months
2. Re-run VectorBT parameter sweeps with exchange-direct data
3. Re-run walk-forward analysis for all 4 strategies
4. Compare results against Alpaca-data baselines
5. Adjust parameters if material differences found
6. Update strategy specs and resolve DEC-132

**Timing:** Runs in parallel with Sprint 22 (AI Layer MVP). Estimated 6-8 sessions.

---

## 8. Impact on Sprint 22+ Sequencing

Sprint 22 (AI Layer MVP) is unchanged in scope. The only prerequisite change:

**Before Sprint 21.5:** Sprint 22 would have been building AI features on top of mock/dev data.
**After Sprint 21.5:** Sprint 22 builds AI features on top of a live system with real data.

This is strictly better — the Copilot can be tested with real market context from day one.

Updated queue:
- **Sprint 21.5** (this sprint): Live Integration — Databento + IBKR
- **Sprint 21.6** (parallel with 22): DEC-132 Backtest Re-Validation with Databento data
- **Sprint 22**: AI Layer MVP (unchanged scope)
- **Sprint 23+**: Unchanged

---

## Appendix: Quick Reference

### Environment Variables Required

```bash
# .env (gitignored — never commit this file)
DATABENTO_API_KEY=db-xxxxxxxxxxxxxxxxxxxx
IBKR_HOST=127.0.0.1
IBKR_PORT=4002          # 4002 = paper, 4001 = live — ALWAYS USE 4002 UNTIL LIVE TRADING
IBKR_CLIENT_ID=1
ARGUS_JWT_SECRET=<random-string-for-api-auth>
ARGUS_PASSWORD_HASH=<bcrypt-hash-for-api-login>
```

### Startup Commands

```bash
# Live mode (Databento + IBKR paper)
python -m argus.main --config system_live.yaml

# Dev mode (mock data, no external connections)
python -m argus.main --dev

# Alpaca incubator mode (legacy)
python -m argus.main --config system.yaml
```

### Databento Datasets

| Dataset | Exchange | Added In |
|---------|----------|----------|
| XNAS.ITCH | Nasdaq (TotalView-ITCH) | Session 1 |
| XNYS.PILLAR | NYSE | Session 3 |

Uses 2 of 10 allowed concurrent sessions on Standard plan.

### IBKR Paper Account Safety Checks

1. IB Gateway login screen shows "Paper Trading" in title bar
2. Account ID starts with "DU" (paper) not "U" (live)
3. `ibkr.yaml` has `port: 4002` (paper) not `port: 4001` (live)
4. IBKRBroker connection log shows paper trading account ID
5. NEVER change port to 4001 until explicit live trading decision (Gate 5)
