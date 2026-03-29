# ARGUS — Sprint History

> Complete record of all sprints from project inception through current state.
> Active development began February 14, 2026. As of March 29, 2026 (~44 calendar days), 30 full sprints + 34 sub-sprints completed.

---

## Timeline Overview

| Phase | Sprints | Dates | Focus |
|-------|---------|-------|-------|
| A — Core Engine | 1–5 | Feb 14–16 | Trading engine foundation + ORB strategy |
| B — Backtesting | 6–11 | Feb 16–17 | Validation toolkit + parameter optimization |
| C — Infrastructure | 12–13 | Feb 21–22 | Databento + IBKR adapters |
| D — Command Center + Strategies | 14–20 | Feb 23–26 | Frontend, Orchestrator, 3 new strategies |
| E — Seven-Page Architecture + Live | 21a–21.5 | Feb 27–Mar 5 | Full UI, live integration |
| F–K — AI + Intelligence + Quality | 22–24.1 | Mar 6–14 | AI Copilot, NLP Catalyst, Universe Manager, Quality Engine, Housekeeping |
| M — Strategy Observability | 24.5 | Mar 15–16 | Evaluation telemetry, operational fixes |
| N — The Observatory | 25 | Mar 17–18 | Immersive pipeline visualization page |
| O — Watchlist Wiring Fix | 25.5 | Mar 18 | UM watchlist population + zero-eval health warning |
| O — Bug Sweep | 25.6 | Mar 19–20 | Operational bug fixes from first live session post-25.5 |
| P — Pattern Library Foundation | 26 | Mar 21–22 | R2G + PatternModule ABC + Bull Flag + Flat-Top + backtesting |
| Q — BacktestEngine Core | 27 | Mar 22 | Production-code backtesting engine with SyncEventBus |
| R — Backtest Re-Validation | 21.6 | Mar 23 | Databento re-validation + ExecutionRecord logging |
| S — Evaluation Framework | 27.5 | Mar 23–24 | Universal evaluation infrastructure |
| T — Regime Intelligence | 27.6 | Mar 24 | Multi-dimensional RegimeVector (6 dimensions) |
| U — Market Session Safety | 27.65 | Mar 24–25 | Order Manager safety, bracket amendment, IntradayCandleStore |
| V — Counterfactual Engine | 27.7 | Mar 25 | Shadow position tracking for rejected signals, filter accuracy |
| W — Paper Trading Hardening | 27.75 | Mar 26 | Log rate-limiting, paper trading config, trades page fix |
| X — Operational Cleanup | 27.8 | Mar 26 | Ghost position reconciliation fix, validation orchestrator script |
| Y — Broker Safety | 27.95 | Mar 26–28 | Reconciliation redesign, overflow routing, order mgmt hardening |
| Z — Learning Loop | 28 | Mar 28–29 | Learning Loop V1: outcome analysis, config proposals, Performance UI |

---

## Phase A — Core Engine (Sprints 1–5, Feb 14–16)

### Sprint 1 — Foundation (52 tests)
**Date:** Feb 14, 2026
**Scope:** Config system (Pydantic BaseModel, YAML loading), Event Bus (FIFO, monotonic sequence numbers), data models (CandleEvent, TickEvent, SignalEvent, OrderEvent), database schema (SQLite via aiosqlite), Trade Logger.
**Key decisions:** DEC-025 (Event Bus ordering), DEC-026 (ULID trade IDs), DEC-032 (Pydantic config).
**Notes:** First sprint established the development workflow. Single Claude Code session. Clean implementation.

### Sprint 2 — Broker & Risk (112 tests, +60)
**Date:** Feb 14, 2026
**Scope:** Broker abstraction (ABC), SimulatedBroker (market/limit/stop orders, fill simulation, position tracking), Risk Manager (three-level gating: strategy limits, cross-strategy exposure, account-level circuit breakers).
**Key decisions:** DEC-027 (approve-with-modification behavior), DEC-028 (daily-stateful strategies), DEC-029 (Event Bus sole streaming), DEC-036 (no margin model in SimulatedBroker).
**Notes:** First code review conducted. Hit context limits, leading to invention of handoff documents. DEF-NNN tracking system invented.

### Sprint 3 — Strategy & Data (222 tests, +110)
**Date:** Feb 15, 2026
**Scope:** BaseStrategy ABC, OrbBreakoutStrategy (opening range tracking, breakout detection with volume/VWAP confirmation, OR midpoint stop), ReplayDataService (historical data replay), Scanner ABC + StaticScanner.
**Key decisions:** DEC-038 (scanner architecture, multi-timeframe framework, indicators in DataService, ORB tracked internally by strategy, Parquet format, market order + chase protection).
**Notes:** Strategy implementation was clean. Scanner abstraction designed for future real scanner implementations.

### Sprint 4a — Live Data & Clock (282 tests, +60)
**Date:** Feb 15, 2026
**Scope:** AlpacaDataService (bar + trade streams via alpaca-py), AlpacaBroker (order submission, position queries), Clock injection protocol (SystemClock + FixedClock for testing).
**Key decisions:** DEC-039 (alpaca-py not deprecated alpaca-trade-api, dual stream subscription, clock scoped to Risk Manager + BaseStrategy).
**Notes:** Split from Sprint 4b to manage scope.

### Sprint 4b — Order Management (320 tests, +38)
**Date:** Feb 15, 2026
**Scope:** Order Manager (ManagedPosition tracking, T1/T2 partial exits, stop-to-breakeven, time stops, EOD flatten), AlpacaScanner (live gap scanning).
**Key decisions:** DEC-040 (stop management: cancel and resubmit), DEC-041 (EOD flatten fallback poll), DEC-044 (exit rules from Signal + Config).
**Notes:** Order Manager became one of the most complex components. T1/T2 split logic established here.

### Sprint 5 — System Integration (362 tests, +42)
**Date:** Feb 16, 2026
**Scope:** HealthMonitor (component health tracking, alerts), system entry point (procedural main.py with 10-phase startup), state reconstruction (broker position/order recovery on restart), structured logging.
**Key decisions:** DEC-045 (webhook heartbeat, Discord/Slack alerts, historical bar reconstruction on restart, in-memory health storage, procedural main.py).
**Notes:** Phase 1 completed in 2 days vs. original 4-week estimate. Core engine fully functional.

---

## Phase B — Backtesting Validation (Sprints 6–11, Feb 16–17)

### Sprint 6 — Historical Data Acquisition (417 tests, +55)
**Date:** Feb 16, 2026
**Scope:** DataFetcher (Alpaca REST historical data download), Manifest system (tracking downloaded data), DataValidator (integrity checks). Acquired 28 symbols × 11 months = 2.2M+ bars in Parquet format.
**Key decisions:** DEC-048 (Parquet granularity), DEC-049 (UTC storage), DEC-050 (split-adjusted prices), DEC-051 (rate limit handling).
**Notes:** Clean data acquisition. Parquet format chosen for provider-agnostic backtesting.

### Sprint 7 — Replay Harness (473 tests, +56)
**Date:** Feb 16, 2026
**Scope:** BacktestDataService (step-driven, controlled by ReplayHarness), ReplayHarness orchestrator, SimulatedBroker enhancements for backtest mode, synthetic tick generation (4 ticks/bar: O→L→H→C bullish, O→H→L→C bearish).
**Key decisions:** DEC-052 (scanner simulation via gap computation), DEC-053 (synthetic tick worst-case ordering), DEC-054 ($0.01/share fixed slippage), DEC-055 (step-driven DataService), DEC-056 (backtest DB naming).
**Notes:** Replay Harness runs actual production code paths, providing higher fidelity than traditional backtesting frameworks.

### Sprint 8 — VectorBT Parameter Sweeps (506 tests, +33)
**Date:** Feb 16, 2026
**Scope:** Vectorized ORB simulation for parameter sweeps, ATR filtering, heatmap generation.
**Key decisions:** DEC-063 (pure NumPy/Pandas, not VectorBT library due to numba issues), DEC-064 (ATR filter bug fix), DEC-065 (ATR threshold adjustment — old thresholds produced 5 identical buckets).
**Notes:** **CRISIS SPRINT.** Initial implementation used `iterrows()` and took 4+ hours. Caught in review; required unplanned optimization session. Then ATR bug discovered, then parameter thresholds needed recalibration. 2-conversation sprint became 4-conversation odyssey. Root cause: no performance benchmarks in spec. Led to DEC-149 (precompute+vectorize mandate) in later sprints.

### Sprint 9 — Walk-Forward Validation (542 tests, +36)
**Date:** Feb 17, 2026
**Scope:** walk_forward.py (optimizer + fixed-params modes), cross-validation (VectorBT vs Replay Harness comparison), HTML report generator with interactive Plotly charts.
**Key decisions:** DEC-066 (Sharpe with min_trades floor), DEC-067 (HTML-only reports), DEC-068 (Plotly primary), DEC-069 (cross-validation), DEC-070 (legacy slow function removal).
**Notes:** Walk-forward infrastructure became critical for all future strategy validation. Cross-validation caught VectorBT ↔ Replay divergences early.

### Sprint 10 — Analysis & Parameter Validation (542 tests, +0)
**Date:** Feb 17, 2026
**Scope:** Baseline backtests, 522K-combination parameter sweep, walk-forward analysis (inconclusive with 11 months data — DEC-073), parameter recommendations (DEC-076), final validation run (137 trades, Sharpe 0.93, PF 1.18).
**Key decisions:** DEC-073 (walk-forward inconclusive), DEC-074 (cross-validation bug fix — 3 bugs), DEC-075 (disable ATR ratio — daily vs 1-min divergence), DEC-076 (Phase 3 parameters: or_minutes=5, max_hold=15, min_gap=2.0, target_r=2.0).
**Deliverable:** `docs/backtesting/PARAMETER_VALIDATION_REPORT.md`
**Notes:** Discovered fundamental ATR calculation divergence: VectorBT uses daily-bar ATR, production uses 1-minute-bar ATR (5–10x ratio difference). ATR filter disabled for paper trading.

### Sprint 11 — Extended Backtest (542 tests, +0)
**Date:** Feb 17, 2026
**Scope:** Extended dataset to 35 months (Mar 2023–Jan 2026), 15 walk-forward windows. Fixed-params WFE (P&L) = 0.56, OOS Sharpe = +0.34, OOS P&L = $7,741.
**Key decisions:** DEC-077 (phase restructure), DEC-078 (earliest_entry fix 09:45→09:35).
**Notes:** WFE=0.56 exceeded the 0.3 threshold. DEC-076 parameters confirmed for paper trading. Phase 2 complete.

---

## Phase C — Infrastructure Pivot (Sprints 12–13, Feb 21–22)

*Two deep-dive research conversations preceded these sprints (Feb 18–20): market data providers and execution brokers. These produced DEC-082 (Databento) and DEC-083 (IBKR) — foundational decisions that prevented months of rework.*

### Sprint 12 — DatabentoDataService Adapter (658 tests, +116)
**Date:** Feb 21, 2026
**Scope:** DatabentoConfig, DatabentoDataService (live streaming + reconnection + stale monitor), DataFetcher Databento backend (historical data + Parquet cache + manifest tracking), DatabentoScanner (V1 watchlist-based gap scanning), system integration (DataSource enum, provider selection in main.py), shared `databento_utils.py`.
**Key decisions:** DEC-085 (Databento source, Parquet cache), DEC-086 (Alpaca reduced to incubator), DEC-087 (defer subscription until ready), DEC-088 (threading model), DEC-089 (XNAS.ITCH default — later superseded by DEC-248), DEC-090 (DataSource enum), DEC-091 (shared normalization utility).
**Notes:** Clean adapter implementation. Config-driven provider selection.

### Sprint 12.5 — IndicatorEngine Extraction (685 tests, +27)
**Date:** Feb 21, 2026
**Scope:** IndicatorEngine class shared by all four DataService implementations. VWAP, ATR-14, SMA-9/20/50, RVOL computation centralized.
**Key decisions:** DEC-092 (IndicatorEngine extraction, resolves DEF-013).
**Notes:** Pure refactor, zero behavioral changes. Cleanest sprint in the project — completed in 1 session.

### Sprint 13 — IBKRBroker Adapter (811 tests, +126)
**Date:** Feb 22, 2026
**Scope:** IBKRBroker full Broker abstraction via `ib_async` (connection management, order submission, native brackets with T1/T2, fill streaming, reconnection, state reconstruction). IBKRConfig + BrokerSource enum. Order Manager T2 broker-side limit orders.
**Key decisions:** DEC-093 (native IBKR brackets), DEC-094 (BrokerSource enum), DEC-095 (DEF-016 deferred — atomic bracket refactor scope too large).
**Notes:** IBKR adapter was complex but clean. Native bracket orders with parentId linkage and transmit flag. DEF-016 (atomic brackets) deferred here, later resolved in Sprint 17 (DEC-117).

---

## Phase D — Command Center + Strategies (Sprints 14–20, Feb 23–26)

### Sprint 14 — Command Center API (926 tests, +115)
**Date:** Feb 23, 2026
**Scope:** FastAPI REST + WebSocket, JWT auth (bcrypt, HS256, 24h expiry), 7 endpoint groups (auth, health, account, positions, trades, strategies, performance), WebSocket bridge (EventBus → WS with tick throttling), PerformanceCalculator (17 metrics), TradeLogger query methods, dev mode with mock data, React scaffold (Vite + TypeScript + Tailwind v4 + Zustand + React Router).
**Key decisions:** DEC-099 (in-process API, Phase 11 startup), DEC-100 (AppState dependency injection), DEC-101 (WebSocket event filtering), DEC-102 (single-user JWT), DEC-103 (monorepo structure).
**Notes:** 11-phase startup sequence. Dev mode (`--dev`) became critical for frontend development.

### Sprint 15 — Command Center Frontend (926 tests, +0)
**Date:** Feb 23, 2026
**Scope:** Four pages: Dashboard, Trade Log, Performance, System. Responsive at 393px/834px/1194px/1512px. Lightweight Charts for equity curve + daily P&L. WebSocket real-time updates. Dark theme. Icon sidebar (desktop) + bottom tab bar (mobile).
**Key decisions:** DEC-104 (dual chart library), DEC-105 (responsive breakpoints), DEC-106 (UX Feature Backlog), DEC-109 (design north star: "Bloomberg Terminal meets modern fintech"), DEC-110 (Framer Motion + CSS transitions).
**Sessions:** 8 implementation sessions. Code review: 20 screenshots across 3 devices.
**Notes:** First frontend sprint. Established visual language and responsive patterns. Design research session conducted, producing 35-feature UX backlog.

### Sprint 16 — Desktop/PWA + UX Polish (942 tests, +16)
**Date:** Feb 24, 2026
**Scope:** Framer Motion page transitions + stagger animations, skeleton loading (all pages), AnimatedNumber + P&L flash, SVG sparklines, chart draw-in animations, hover feedback (desktop-only), contextual empty states, trade detail slide-in panel, PWA (manifest, service worker, icons, iOS meta), CSV trade export, emergency controls (flatten all, pause all), strategy pause/resume, Tauri v2 desktop shell, platform detection utility.
**Key decisions:** DEC-107 (UX enhancements), DEC-111 (control endpoints), DEC-112 (CSV export).
**Sessions:** 10 implementation sessions. Three delivery surfaces operational (web, Tauri, PWA).
**Notes:** UI work required more iteration than backend — visual bugs visible only in screenshots required multiple fix rounds. Known issue: safe-area-inset padding incomplete (fixed in Sprint 17.5).

### Sprint 17 + 17.5 — Orchestrator V1 (1146 tests, +204)
**Date:** Feb 24–25, 2026
**Sprint 17 scope:** Orchestrator core (pre-market routine, 30-min regime monitoring, intraday throttle, EOD review, decision logging), RegimeClassifier (SPY realized vol as VIX proxy), PerformanceThrottler (consecutive losses/Sharpe/drawdown), CorrelationTracker (V2 infrastructure), equal-weight allocation V1, single-strategy 40% cap, DEF-016 resolved (atomic bracket orders), API (3 orchestrator endpoints + 4 WebSocket event types), UI (SegmentedTab, Badge system, AllocationDonut, RiskGauge), 12-phase main.py startup.
**Sprint 17.5 scope:** Polish — Orchestrator encapsulation properties, safe-area padding fix (additive spacer div), animation-once refs, stable render (removed conditional skeleton swap — always render same DOM structure).
**Key decisions:** DEC-113–119 (regime, allocation, throttle, atomic brackets).
**Sessions:** 13 (Sprint 17) + 4 (Sprint 17.5).
**Notes:** Conditional skeleton/content swaps breaking state was a key learning — always render same DOM structure, let children handle empty states.

### Sprint 18 + 18.5 + 18.75 — ORB Scalp + CapitalAllocation (1317 tests, +171)
**Date:** Feb 25, 2026
**Sprint 18 scope:** OrbBaseStrategy ABC extracted (shared scanner, gap filter, OR tracking, breakout detection). OrbScalpStrategy (single-target 0.3R exit, 120s hold, per-signal time stop). Cross-strategy risk (ALLOW_ALL, Risk Manager ↔ Order Manager reference, CandleEvent routing). VectorBT sweep: 20,880 trades, all aggregate Sharpes negative (bar resolution insufficient). UX: SessionSummaryCard, PositionTimeline.
**Sprint 18.5 scope:** ORB Scalp mock data, mobile fixes, three-way position filter, view toggle persistence, 3 integration test gaps, badge contrast fixes.
**Sprint 18.75 scope:** CapitalAllocation redesign (track-and-fill donut + horizontal bars), MarketRegimeCard, dashboard 3-card grid, API enrichment (per-strategy deployed_capital).
**Key decisions:** DEC-120–135.
**Sessions:** 12 (Sprint 18) + 7 (18.5) + 8 (18.75).
**Notes:** Sprint 18.75 was an impromptu sprint that collided with Sprint 19 prep, requiring DEC renumbering. ORB Scalp backtest inconclusive at 1-min resolution — default params are thesis-driven.

### Sprint 19 — VWAP Reclaim Strategy (1410 pytest + 40 Vitest, +93/+26)
**Date:** Feb 25–26, 2026
**Scope:** VwapReclaimStrategy standalone from BaseStrategy, 5-state machine, pullback swing-low stop, T1=1.0R/T2=2.0R, 30-min time stop. VectorBT sweep: 59,556 trades, 768 combos, avg Sharpe 3.89, WF OOS Sharpe 1.49. Precompute+vectorize architecture mandated (DEC-149). Watchlist Sidebar (responsive, VWAP distance metric, compact badges). Keyboard shortcuts (1–4 nav, w watchlist).
**Key decisions:** DEC-136–151.
**Sessions:** 14 implementation + 2 code review checkpoints.
**Notes:** Strongest backtest results of any strategy. WF OOS Sharpe 1.49 is encouraging (provisional per DEC-132). `.claude/rules/backtesting.md` created after VectorBT performance issues.

### Sprint 20 — Afternoon Momentum Strategy (1522 pytest + 48 Vitest, +112/+8)
**Date:** Feb 26, 2026
**Scope:** AfternoonMomentumStrategy standalone from BaseStrategy, 5-state machine, consolidation high/low channel + ATR filter, 8 simultaneous entry conditions. T1=1.0R/T2=2.0R, dynamic time stop compressed to force_close. Cross-strategy ALLOW_ALL, time-separated coverage. VectorBT sweep: 1,152 combos. System integration: all 4 strategies wired. Dev mode: 4-strategy mock data.
**Key decisions:** DEC-152–162.
**Sessions:** 10 implementation + 2 code review checkpoints.
**Notes:** Fourth and final Phase 1 strategy. Full trading day covered: ORB 9:35–11:30, VWAP 10:00–12:00, Afternoon 2:00–3:30.

---

## Phase E — Seven-Page Architecture + Live (Sprints 21+, Feb 27–)

*DEC-163 (Expanded Vision, Feb 26) transformed ARGUS from 5-strategy rules-based to 15+ pattern AI-enhanced platform. Sprint 21 split into 4 sub-sprints to build the full 7-page Command Center architecture.*

### Sprint 21a — Pattern Library Page (1558 pytest + 70 Vitest, +36/+22)
**Date:** Feb 27, 2026
**Scope:** Backend: config YAML metadata enrichment, extended strategy endpoints, auto-discovered markdown spec sheets (DEC-181), synthetic OHLCV for dev mode. Frontend: IncubatorPipeline (10-stage horizontal), PatternCardGrid, PatternCard (accent styling), PatternFilters, PatternDetail (5 tabs: Overview, Performance, Backtest, Trades, Intelligence). SlideInPanel extraction (DEC-177). SymbolDetailPanel (global slide-in with candlestick chart + trading history). Click-anywhere symbol wiring. Arrow key navigation. Z-index hierarchy (DEC-182).
**Key decisions:** DEC-172–185.
**Sessions:** 8 implementation + 4 polish.
**Notes:** Pattern Library established the master-detail pattern used across the app. SymbolDetailPanel as a global component was a key architectural choice.

### Sprint 21b — Orchestrator Page (1597 pytest + 100 Vitest, +39/+30)
**Date:** Feb 27, 2026
**Scope:** Backend: extended orchestrator status (session phase, per-strategy throttle, operating windows), throttle override endpoint with duration + reason. Frontend: OrchestratorPage (6 sections), hero row layout, StrategyCoverageTimeline (custom SVG), StrategyOperationsGrid, DecisionTimeline (newest-first), GlobalControls (force rebalance, emergency flatten/pause), RegimePanel gauge redesign, ThrottleOverrideDialog. Navigation updated to 6 pages.
**Key decisions:** DEC-192–195 (layout, display config, ordering, gauge redesign).
**Sessions:** 8 implementation + 1 review + 4 polish.

### Sprint 21c — The Debrief Page (1664 pytest + 138 Vitest, +105/+38)
**Date:** Feb 27, 2026
**Scope:** Backend: DebriefService (992 lines), 3 DB tables (briefings, journal_entries, documents), 4 API route files, LIKE search, batch trade fetch. Frontend: DebriefPage (3 sections via SegmentedTab). Briefings (creation, editing, side-by-side markdown). Research Library (hybrid filesystem + database). Journal (4-filter dimensions, typed badges, expand/collapse, inline edit, trade linking with search + chips). Shared TagInput component. Navigation: 7 pages complete.
**Key decisions:** DEC-196–203.
**Sessions:** 10 implementation + 2 reviews + 1 fix.
**Notes:** Most test-dense sprint on the backend (105 new pytest). DebriefService at 992 lines was the largest single new file.

### Sprint 21d — Dashboard + Performance + System + Copilot Shell (1712 pytest + 257 Vitest, +48/+119)
**Date:** Feb 27–28, 2026
**Scope:** Dashboard: OrchestratorStatusStrip, StrategyDeploymentBar, GoalTracker, 3-card row (MarketStatus + TodayStats + SessionTimeline), PreMarketLayout, aggregate endpoint. Performance: 5-tab layout with 8 visualizations (TradeActivityHeatmap, CalendarPnlView, RMultipleHistogram, RiskWaterfall, PortfolioTreemap, CorrelationMatrix, ComparativePeriodOverlay, TradeReplay). Unified diverging color scale (DEC-224), WCAG dynamic text contrast (DEC-225). System: narrowed to infrastructure. Nav: sidebar dividers, mobile 5+More. CopilotPanel shell + button + store.
**Key decisions:** DEC-204–229.
**Sessions:** 13 implementation + 3 code reviews. **Largest sprint** (14 total sessions — should have been split further).
**Notes:** Most Vitest-dense sprint (119 new). Performance Workbench deferred (DEC-229). Copilot shell ready for Sprint 22 activation.

### Sprint 21.5 — Live Integration (1737 pytest + 291 Vitest, +25/+34)
**Date:** Feb 28 – Mar 5, 2026
**Scope:** Connected live Databento market data feeds (EQUS.MINI) with IBKR paper trading execution via IB Gateway. 4 blocks + unplanned sub-sprint (21.5.1). 49 commits, 150 files modified, 47 new files.
**Block A (1 session):** Validation scripts for Databento + IBKR integration. 13/13 integration PASS, 4/4 resilience PASS.
**Block B (6 sessions):** Scanner resilience for historical data lag (DEC-247, 13 tests). EQUS.MINI confirmed (DEC-248). Concentration limit approve-with-modification (DEC-249). Position sizing verification. Operational scripts (`start_live.sh`, `stop_live.sh`). LIVE_OPERATIONS.md (417 lines). Absolute risk floor replaces 0.25R ratio (DEC-251).
**Block C (3 sessions):** Live paper trading. C1: AAPL VWAP Reclaim +$70.30 (1.22R), price rounding fix (DEC-252), heartbeat logging (DEC-253). C2: 11 trades, +$335.79, 40% win rate, 4 ORB dual-fire incidents discovered. C3: ran with 21.5.1 fixes.
**Block D (1 session):** Sprint closeout, audit, documentation sync.
**Key decisions:** DEC-230–261 (32 decisions). Hybrid multi-source data architecture (DEC-257). FMP Starter for scanning (DEC-258). Sprint 21.7 queued (DEC-259). 5 data providers evaluated and rejected (DEC-260).
**Sessions:** ~25 total (Block A: 1, Block B: 6, Block C: 3, Block D: 1, Sub-sprint 21.5.1: 5+1 hotfix, plus prior sessions 1–9 from earlier conversations).
**Notes:** Largest sprint by scope expansion. Originally scoped as 13–15 sessions, grew to ~25 across 4 blocks. Spawned unplanned sub-sprint 21.5.1. First live paper trade validated end-to-end order lifecycle.

### Sprint 21.5.1 — C2 Bug Fixes + UI Polish (included in 21.5 test counts)
**Date:** Mar 5, 2026
**Scope:** Unplanned sub-sprint triggered by C2 paper trading findings. 5 sessions + 1 hotfix, all in one day.
**Session 1 (Trading Engine):** Flatten fill strategy_id routing with fallback. Pending entry exposure in concentration check. ORB family same-symbol mutual exclusion via ClassVar (DEC-261). +12 pytest.
**Session 2 (Backend Data):** Daily P&L includes unrealized. 0.0 handling fix (is not None). Bars endpoint real data wiring. TradeResponse stop/target fields. +8 pytest, +2 Vitest.
**Session 3 (Frontend UX):** Strategy colors (strat_ prefix normalization). Price levels display. Position timeline zoom (1x–4x). PositionDetailPanel. Sortable/clickable OpenPositions. +20 Vitest.
**Session 4+4b (Trade Chart + Hotfix):** TradeChart with Lightweight Charts v5. Price level overlays. Trade filters (Zustand store). Hotfix: removed is_dev_mode gate blocking real bars in paper trading. +2 pytest, +14 Vitest.
**Key decisions:** DEC-261.
**Notes:** Most UI-dense sub-sprint. All C2 critical bugs resolved in single day.

### Sprint 21.7 — FMP Scanner Integration (1754 pytest + 296 Vitest, +17/+5)
**Date:** Mar 5, 2026
**Scope:** Integrate Financial Modeling Prep (FMP) Starter as pre-market scanning data source (DEC-258/259). Replaces static watchlist with dynamic gap/volume scanning across full US equity universe.
**Session 1 (Backend):** `FMPScannerSource` implementing Scanner ABC. `WatchlistItem` extended with `scan_source` and `selection_reason` fields. 15 new pytest.
**Session 2 (Backend):** Config routing in `main.py` (scanner_type dispatch from scanner.yaml). `scanner.yaml` fmp_scanner section. Watchlist API endpoint wiring. `AppState.cached_watchlist`. 2 new pytest.
**Session 3 (Frontend):** `PreMarketWatchlistPanel` replaces `RankedWatchlistPlaceholder`. Source badge (FMP green / Static neutral). Gap% coloring. Selection reason formatting. 5 new Vitest.
**Key decisions:** DEC-258 (FMP Starter), DEC-259 (Sprint 21.7 scope).
**Sessions:** 3 implementation + 3 Tier 2 reviews.
**Notes:** Cleanest focused mini-sprint. All 3 sessions CLEAN self-assessment, all Tier 2 reviews APPROVED. Pre-market scanning now uses FMP gainers/losers/actives endpoints instead of static 10-symbol watchlist.

### Sprint 22 — AI Layer MVP + Copilot Activation (1959 pytest + 377 Vitest, +205/+81)
**Date:** Mar 6–7, 2026
**Scope:** Full implementation of DEC-170 (AI Copilot with approval workflow, context injection, persistent conversations, daily summaries, insight card, learning journal) in a single sprint rather than phasing across multiple sprints.
**S1 (AI Core Module):** ClaudeClient wrapper (tool_use, rate limiting), PromptManager, SystemContextBuilder, ResponseCache, AIConfig, tools.py with 5 tool definitions. 62 new tests.
**S2a (Chat Persistence):** ConversationManager, UsageTracker, 3 SQLite tables (ai_conversations, ai_messages, ai_usage). 35 new tests.
**S2b (Chat API + WebSocket):** 6 REST endpoints for conversations/messages/actions, WS /ws/v1/ai/chat for streaming. 30 new tests.
**S3a (Approval Workflow):** ActionProposal model, ActionManager with DB persistence, approve/reject routes, Event Bus integration. 32 new tests. **COMPACTED.**
**S3b (Action Executors + AI Content):** 5 ActionExecutors with 4-condition re-check gate, DailySummaryGenerator, AIService (later removed), insight endpoint. 54 new tests. **COMPACTED.**
**S4a (Copilot Core Chat):** CopilotPanel rewrite, ChatMessage, StreamingMessage with react-markdown, ChatInput. 23 new tests.
**S4b (Copilot Integration):** useCopilotContext on 7 pages, Cmd/K shortcut, conversation history, WebSocket reconnection. 20 new tests.
**S5 (Action Cards + Approval UX):** ActionCard component, 6 states (pending, approved, executing, executed, rejected, expired), audio notifications, countdown. 10 new tests.
**S6 (Dashboard AI + Debrief):** AIInsightCard, ConversationBrowser, Learning Journal integration. 18 new tests.
**Fix sessions (5):** S4a-fix (auto-focus, modifier keys, auto-scroll), S3b-fix (system prompt directiveness), S2b-fix (stream event extraction), model ID fix, frontend tool_use event fix, consolidated cleanup (10 issues: YAML config field names, dead AIService code, code hygiene, token buffer, ticker formatting, duplicate shortcuts, proposal sync, keyboard shortcuts, auto-scroll, report click-through).
**Key decisions:** DEC-264 (full scope Sprint 22), DEC-265 (WebSocket streaming), DEC-266 (calendar-date conversation keying), DEC-267 (proposal TTL + DB persistence), DEC-268 (per-page context injection), DEC-269 (demand-refreshed insight card), DEC-270 (markdown rendering stack), DEC-271 (tool_use for proposals), DEC-272 (5-type action enumeration), DEC-273 (system prompt + guardrails), DEC-274 (per-call cost tracking), DEC-275 (compaction risk scoring).
**Sessions:** 9 implementation + 5 fix + 9 Tier 2 reviews.
**Notes:** Largest single-sprint scope. Sessions 3a and 3b compacted, leading to DEC-275 (compaction risk scoring system). AIService class built but not wired into routes — removed in cleanup. 3.4× test target exceeded (288 actual vs. 85 planned). ~6,500 lines backend, ~3,000+ lines frontend.

### Sprint 22.1 — Post-Verification Fixes (1967 pytest + 377 Vitest, +8/+0)
**Date:** Mar 7, 2026
**Scope:** Fix 5 verified failures and 3 code-inspection findings from Sprint 22 automated verification. 4 root-cause bugs: timezone mismatch in usage tracking, DailySummaryGenerator/ResponseCache initialization gap, WS streaming token estimation, conversation date keying.
**Session 1:** Fix 1: ET timestamps in `usage.py`, `routes/ai.py`, `ai_chat.py`, `conversations.py`. Fix 2: `DailySummaryGenerator` + `ResponseCache` initialization in `server.py`. Fix 3: Stream event usage extraction in `client.py` + actual counts in WS handler. Fix 4: Hardcoded cost constants replaced with config values. 8 new tests.
**Key decisions:** DEC-276 (AI timestamps standardized on ET).
**Sessions:** 1 implementation + 1 Tier 2 review.
**Notes:** Tier 2 review discovered an additional `date.today()` in `conversations.py` (pre-existing bug from Sprint 22), fixed during review session. All verification checklist items 2.14.1, 2.14.9, 2.17.2–4 resolved.

### Sprint 22.2 — AI Context Data Fixes (1977 pytest + 377 Vitest, +10/+0)
**Date:** Mar 7, 2026
**Scope:** Fix 6 data assembly bugs in the AI context layer that caused the Copilot to see $0.00 P&L for all trades, empty position lists, and incorrect date filtering.
**Session 1:** Fix 1: Trade P&L column name (`realized_pnl` → `net_pnl`). Fix 2: Dashboard positions iteration (dict keys → `.items()`, correct `ManagedPosition` attribute names, unrealized P&L computed from live `data_service.get_current_price()`). Fix 3: Insight positions compute unrealized P&L from data service. Fix 4: Debrief date filter uses ET timezone. Fix 5: `/insight` endpoint try/except with graceful error response. Fix 6: `generate_insight` top-level error handling. 10 new tests.
**Key decisions:** None (implementation bug fixes only).
**Sessions:** 1 implementation + 1 Tier 2 review.
**Notes:** All 6 bugs were hidden by silent `except Exception: pass` blocks that caught `AttributeError` and `KeyError` and returned empty/zero defaults. Claude received structurally valid but factually wrong context. The Copilot appeared functional but gave analyses based on incorrect data.

### Sprint 22.3 — Silent Exception Logging (1977 pytest + 377 Vitest, +0/+0)
**Date:** Mar 7, 2026
**Scope:** Add `logger.warning` to 12 silent `except Exception: pass` blocks in `context.py` and `summary.py`. Logging-only change — no logic, behavior, or defaults modified. Two inner `get_current_price()` blocks intentionally left silent (expected failures for unsubscribed symbols).
**Key decisions:** None.
**Sessions:** 1 implementation (Tier 2 review skipped — no behavioral changes).
**Notes:** Prevents future data assembly bugs from being silently hidden, as happened with all 6 bugs in Sprint 22.2.

### Sprint 23 — Universe Manager (2099 pytest + 392 Vitest, +122/+15)
**Date:** Mar 7–8, 2026
**Scope:** Replace static pre-market watchlist (15 symbols) with Universe Manager that monitors broad US equity universe via Databento ALL_SYMBOLS, caches FMP reference data (sector, market cap, float), and routes candle events to strategies based on declarative `universe_filter` YAML configs.

**Session 1a:** FMP Reference Data Client — `argus/data/fmp_reference.py`. SymbolReferenceData dataclass, FMPReferenceClient with batched Company Profile + Share Float fetching, OTC detection, cache management. 33 new tests.
**Session 1b:** Universe Manager Core — `argus/data/universe_manager.py`. UniverseManager class with `build_viable_universe()`, system-level filters (OTC, price, volume), reference cache management. 22 new tests.
**Session 2a:** Universe Filter Config Model — `UniverseFilterConfig` and `UniverseManagerConfig` Pydantic models in `config.py`, wired into StrategyConfig and SystemConfig. 10 new tests.
**Session 2b:** ORB Family Filter Declarations — `universe_filter` sections added to `orb_breakout.yaml` and `orb_scalp.yaml` with values extracted from `get_scanner_criteria()`. 6 new tests.
**Session 2c:** VWAP + Afternoon Filter Declarations — `universe_filter` sections added to `vwap_reclaim.yaml` (with min_market_cap=500M for institutional flow) and `afternoon_momentum.yaml`. 6 new tests.
**Session 3a:** Routing Table Construction — O(1) routing table, per-strategy symbol lookup, `route_candle()` via dict.get. 14 new tests.
**Session 3b:** Databento Fast-Path + Events — Fast-path discard in `_on_ohlcv` and `_on_trade` before `_active_symbols` check, IndicatorEngine guard, `UniverseUpdateEvent`. 10 new tests.
**Session 4a:** Universe Manager System Config — `universe_manager:` section in system.yaml and system_live.yaml, temporary dataclass replaced with real Pydantic model. 6 new tests.
**Session 4b:** Main.py Startup Wiring (critical integration) — Universe Manager wired into 12-phase startup sequence, candle routing via routing table when enabled, backward compatibility preserved. 8 new tests.
**Session 5a:** Backend API Endpoints — GET `/api/v1/universe/status` and `/api/v1/universe/symbols` with JWT auth and graceful disabled state. 7 new tests.
**Session 5b:** Frontend Dashboard Panel — UniverseStatusCard component with enabled/disabled/loading/error states, TanStack Query hook with 60s polling, 15 Vitest tests.
**Session 5f:** Visual review fix — AI Insight and Universe Status cards side-by-side on desktop/tablet, stacked on mobile.

**Pre-session fixes:** `.gitignore` root-anchored (`data/` → `/data/`), `test_risk_manager_wired_to_order_manager` missing ActionManager mock.
**Key decisions:** DEC-277 (fail-closed on missing reference data).
**Sessions:** 11 implementation + 1 visual-review fix + 2 pre-session fixes + Tier 2 reviews.
**Notes:** Cleanest sprint to date — zero regressions across all 11 sessions. VWAP Reclaim uniquely includes min_market_cap=500M based on institutional flow thesis. Config-gated (enabled: false default) for safe deployment. NLP Catalyst Pipeline deferred to Sprint 23.5.

### Sprint 23.05 — Post-Sprint Fixes (2101 pytest + 392 Vitest, +2/+0)
**Date:** Mar 8, 2026
**Scope:** Fix 3 pre-existing test failures (UTC/ET timezone mismatch per DEC-276) and implement fail-closed behavior for missing reference data (DEC-277).

**Session A:** Fixed `test_record_usage_custom_endpoint` (UTC→ET date query), `test_get_decisions_paginated` and `test_get_decisions_with_pagination` (UTC→ET in fixture). All same root cause: tests queried by UTC date but data stored with ET dates per DEC-276.
**Session C:** Implemented DEC-277 — `_apply_system_filters()` excludes symbols with None prev_close or avg_volume, `_symbol_matches_filter()` excludes symbols with no cached reference data. 4 new tests.
**Key decisions:** DEC-277 (fail-closed on missing reference data).
**Sessions:** 2 implementation.
**Notes:** Session B was investigation-only (no code changes) that led to DEC-277. Pre-existing failures only manifested after 7 PM ET when UTC and ET dates diverge.

### Sprint 23.1 — Autonomous Runner Protocol Integration (2101 pytest + 392 Vitest, +0/+0)
**Date:** Mar 9, 2026
**Scope:** Documentation-only sprint integrating autonomous sprint runner protocols, schemas, templates, and guides into the repository.

**Session 1:** Created 15 new documentation files: 5 protocol files (autonomous-sprint-runner.md, in-flight-triage-update.md, run-log-spec.md, sprint-planning-update.md, triage-prompt.md), 4 schema files (runner-config-schema.md, run-state-schema.md, structured-closeout-schema.md, structured-review-verdict-schema.md), 4 template files (fix-session-template.md, runner-config-template.yaml, triage-verdict-template.md, work-journal-template.md), 2 guide files (autonomous-process-guide.md, human-in-loop-guide.md).

**Session 2:** Modified 8 existing files to integrate runner support. Updated close-out skill with structured JSON appendix. Updated review skill with CONCERNS verdict and structured JSON appendix. Updated reviewer agent with CONCERNS support. Updated project-knowledge.md with three-tier architecture description. Updated architecture.md with Sprint Runner component. Appended 20 DEC entries (DEC-278–297) covering runner architecture, Tier 2.5 triage, spec conformance, run-log, git hygiene, retry policy, cost tracking, test verification, and more.

**Key decisions:** DEC-278–297 (20 decisions covering autonomous runner architecture and enhancements).
**Sessions:** 2 implementation + Tier 2 reviews.
**Notes:** Documentation-only sprint — no Python, TypeScript, or test files modified. All source code remains unchanged. First sprint to formalize the autonomous execution capability that enables overnight sprint execution.

### Sprint 23.2 — Autonomous Sprint Runner Implementation (2289 pytest + 392 Vitest, +188/+0)
**Date:** Mar 9, 2026
**Scope:** Full implementation of the autonomous sprint runner (DEC-278–297) as a Python orchestrator with 12 modules and 188 tests. Entry point at `scripts/sprint-runner.py` with package at `scripts/sprint_runner/`.

**Session 1 (S1):** Core infrastructure — `config.py` (RunnerConfig Pydantic model, SprintPackage, SessionSpec), `state.py` (RunState, SessionResult), `lock.py` (file-based locking). 28 new tests.
**Session 2 (S2):** Execution core — `executor.py` (SessionExecutor, Claude Code CLI invocation, output parsing), `git_ops.py` (GitOperations, per-session commits, checkpoint management). 44 new tests.
**Session 3 (S3):** Main loop foundation — `main.py` initial structure (SprintRunner class, session iteration, proceed/halt logic). 16 new tests.
**Session 4 (S4):** Notifications + loop completion — `notifications.py` (ntfy.sh integration, 5 priority tiers), main loop state transitions and resume logic. 27 new tests. Ruff lint issue fixed (unused import).
**Session 5 (S5):** Triage + conformance + cost — `triage.py` (Tier 2.5 automated triage, scope gap detection), `conformance.py` (spec conformance checking), `cost.py` (token usage tracking, cost ceiling). 34 new tests. Heaviest session by scope score (~24 points).
**Session 6 (S6):** Parallel execution + CLI + resume — `parallel.py` (parallel session execution via asyncio gather), full CLI interface with all flags, resume from checkpoint, output file validation. 36 new tests.
**Sprint 23.2.1 (fix):** Skip-session dependency validation — ensures skipped sessions don't break file existence validation for subsequent sessions. 3 new tests.

**Modules implemented:**
- `config.py` — RunnerConfig, SprintPackage, SessionSpec, ReviewContext Pydantic models
- `state.py` — RunState, SessionResult, persistence to run-state.json
- `lock.py` — File-based lock preventing concurrent runner instances
- `executor.py` — SessionExecutor, Claude Code CLI subprocess management
- `git_ops.py` — GitOperations, per-session commits, branch checkpoints
- `notifications.py` — ntfy.sh mobile push notifications, 5 priority tiers
- `triage.py` — Tier 2.5 automated triage for scope gaps and prior-session bugs
- `conformance.py` — Spec conformance checking at session boundaries
- `cost.py` — Token usage tracking, configurable cost ceiling enforcement
- `parallel.py` — Parallel session execution with serialized git commits
- `main.py` — SprintRunner orchestrator, 77KB main loop with all defense-in-depth checks

**Key decisions:** DEC-278–297 (implemented — all 20 decisions from Sprint 23.1 now have working code).
**Sessions:** 6 implementation + 1 fix (23.2.1) + 6 Tier 2 reviews.
**Test counts per session:** S1(+28), S2(+44), S3(+16), S4(+27), S5(+34), S6(+36), 23.2.1(+3) = 188 new pytest.
**Review outcomes:** 4 CLEAR, 2 CONCERNS (S4: ruff lint — fixed same session; 23.2.1: skip-dep validation — resolved with fix session).
**Notes:** All 6 implementation sessions CLEAN self-assessment. Two CONCERNS verdicts both resolved within the sprint. Heaviest session was S5 (triage + conformance + cost, ~24 compaction risk points). Judgment calls: triage subagent failure → HALT (conservative), conformance subagent failure → CONFORMANT (permissive) — asymmetric by design since triage failures are safety-critical. urllib.request used for notifications (stdlib, simpler than aiohttp). Parallel session git commits serialized via sequential commit after asyncio.gather. Known issue: Pydantic serialization warnings on `review_verdict` field (cosmetic, tracked as DEF-034).

### Sprint 23.3 — Impromptu: Wide Pipe + Runner Permissions (2302 pytest + 392 Vitest, +13/+0)
**Date:** Mar 9–10, 2026
**Scope:** Universe Manager Wide Pipe (full FMP stock-list instead of 15-symbol scanner watchlist) + Warm-Up Fix + Runner Permission Bypass + Session Timeout Fix. Impromptu sprint addressing live deployment discoveries.

**Session 1 (S1): Universe Manager Wide Pipe + Warm-Up Fix**
- Added `fetch_stock_list()` to FMPReferenceClient retrieving `/stable/stock-list` (~8,000 symbols)
- Updated `fetch_reference_data()` with async concurrency (semaphore=5, 0.2s spacing, 3 retries with exponential backoff), progress logging
- Rewired `main.py` to use full stock-list → `build_viable_universe()` → ~3,000–4,000 viable symbols → warm-up
- Migrated FMPReferenceClient from legacy `/api/v3/` and `/api/v4/` to `/stable/` endpoints (DEC-298)
- Field name mappings: `mktCap` → `marketCap`, `exchangeShortName` → `exchange`, `volAvg` → `averageVolume`
- 12 new pytest tests

**Session 2 (S2): Runner Permissions + Timeout Fix**
- Added `--dangerously-skip-permissions` flag for autonomous mode in `executor.py`
- Set session timeout to 1800s (30 minutes) for long-running sessions
- 2 new pytest tests

**Key decisions:** DEC-298 (FMP stable API migration), DEC-299 (full-universe input pipe via FMP stock-list)
**Sessions:** 2 implementation
**Test counts:** S1(+12), S2(+2) = +14 new pytest (but reported as +13 due to test consolidation)
**Notes:** Impromptu sprint triggered by live deployment testing. FMP legacy endpoint deprecation discovered at runtime — hotfix applied same day. DEC-263 full-universe pipe now complete. ~27 min pre-market load time accepted as pre-market fetch has no hard deadline.

### Sprint 23.5 — NLP Catalyst Pipeline (2396 pytest + 435 Vitest, +94/+43)
**Date:** Mar 10, 2026
**Scope:** NLP Catalyst Pipeline (DEC-164) — three data sources (SEC EDGAR, FMP News, Finnhub), Claude API classification with rule-based fallback, headline hash deduplication, daily cost ceiling enforcement, intelligence briefing generation, frontend components (CatalystBadge, CatalystAlertPanel, IntelligenceBriefView, BriefingCard).

**Session 1 (S1): Data Sources + CatalystSource Interface**
- Created `argus/intelligence/catalyst/` package structure
- Implemented abstract `CatalystSource` base class
- Built `SECEdgarSource` for 8-K filings and Form 4 insider transactions
- Built `FMPNewsSource` for stock news and press releases
- Built `FinnhubSource` for company news and analyst recommendations
- 18 new pytest tests

**Session 2 (S2): CatalystClassifier + Rule-Based Fallback**
- Implemented `CatalystClassifier` with Claude API integration
- Added keyword-based rule fallback for graceful degradation (DEC-301)
- Classification categories: earnings, insider, guidance, analyst, regulatory, partnership, product, restructuring, other
- 14 new pytest tests

**Session 3 (S3): CatalystStorage + Pipeline Orchestration**
- Implemented `CatalystStorage` with SQLite persistence
- Headline hash (SHA-256) deduplication with UNIQUE constraint (DEC-302)
- Built `CatalystPipeline` orchestrating sources, classifier, storage
- Config-gated via `catalyst.enabled` (DEC-300)
- 16 new pytest tests

**Session 4 (S4): BriefingGenerator + API Routes**
- Implemented `BriefingGenerator` for pre-market intelligence briefs
- Daily cost ceiling enforcement ($5/day) via UsageTracker (DEC-303)
- Added `/api/v1/catalysts` and `/api/v1/intelligence/briefings` routes
- 22 new pytest tests

**Session 5 (S5): Frontend Components + TanStack Query Hooks**
- Created `CatalystBadge` component with category-colored badges
- Created `CatalystAlertPanel` for real-time catalyst notifications
- Created TanStack Query hooks: `useCatalysts`, `useIntelligenceBriefings`, `useIntelligenceBriefing` (DEC-305)
- 24 new pytest tests, 25 new Vitest tests

**Session 6 (S6): IntelligenceBriefView + BriefingCard**
- Built `IntelligenceBriefView` as fourth tab in The Debrief page (DEC-307)
- Created `BriefingCard` component with expand/collapse and markdown rendering
- Three-column layout: briefing list, detail view, catalyst summary
- Keyboard shortcut: `i` for Intelligence tab
- 18 new Vitest tests

**Key decisions:** DEC-300 (config-gated), DEC-301 (rule-based fallback), DEC-302 (headline hash dedup), DEC-303 (cost ceiling), DEC-304 (three-source architecture), DEC-305 (TanStack Query hooks), DEC-306 (Finnhub free tier), DEC-307 (Intelligence Brief view)
**Sessions:** 6 implementation
**Test counts:** S1(+18), S2(+14), S3(+16), S4(+22), S5(+24/+25V), S6(+0/+18V) = 94 new pytest, 43 new Vitest
**Notes:** Three free data sources (SEC EDGAR, FMP News, Finnhub) provide broad catalyst coverage at no incremental cost. Rule-based fallback ensures graceful degradation when Claude API unavailable or cost ceiling reached. Finnhub free tier reliability noted as risk (RSK-053). SEC EDGAR rate limiting noted as risk (RSK-055).

### Sprint 23.6 — Tier 3 Remediation + Pipeline Integration + Warm-Up Optimization (2490 pytest + 435 Vitest, +83/+0)
**Date:** Mar 10, 2026
**Scope:** Address all findings from the Tier 3 architectural review of Sprints 23–23.5: storage/query defects, CatalystEvent timezone alignment, SEC EDGAR email validation, FMP canary test, semantic deduplication, batch-then-publish ordering, intelligence startup factory, app lifecycle wiring, polling loop, reference data file cache, incremental warm-up, runner CLI extraction, conformance fallback monitoring.

**Session 1 (S1): Storage Schema & Query Fixes**
- Added `get_total_count()` with `SELECT COUNT(*)` (replaces fetching 10K rows)
- Added `store_catalysts_batch()` for transactional batch inserts
- Added `fetched_at` column to `catalyst_events` with ALTER TABLE migration
- Pushed `since` datetime filter to SQL WHERE clause in `get_catalysts_by_symbol`
- 12 new pytest tests

**Session 2a (S2a): Event & Source Fixes**
- Changed CatalystEvent `published_at`/`classified_at` defaults from UTC to ET (DEC-276)
- Added `user_agent_email` validation in SEC EDGAR `start()` — raises ValueError if empty/whitespace
- 5 new pytest tests

**Session 2b (S2b): Pipeline Batch Store + FMP Canary + Semantic Dedup + Publish Ordering**
- Added `dedup_window_minutes` config field (default 30)
- FMP canary test at startup validates expected response keys (DEC-313)
- Post-classification semantic dedup by (symbol, category, time_window) — highest quality_score wins (DEC-311)
- Pipeline batch store + separate publish phase with per-item error handling (DEC-312)
- 11 new pytest tests

**Session 3a (S3a): Intelligence Startup Factory**
- Created `argus/intelligence/startup.py` with `IntelligenceComponents` dataclass
- `create_intelligence_components()` factory builds all pipeline components from config
- Returns None when disabled; `shutdown_intelligence()` cleanup helper
- 8 new pytest tests

**Session 3b (S3b): App Lifecycle Wiring**
- Added `CatalystConfig` to `SystemConfig` (DEC-310)
- Intelligence components initialized in FastAPI lifespan handler when enabled
- `pipeline.start()` called; AppState fields populated; graceful shutdown via `shutdown_intelligence()`
- Config YAML key validation test
- 9 new pytest tests

**Session 3c (S3c): Polling Loop**
- `run_polling_loop()` with market-hours-aware interval switching (9:30–16:00 ET)
- Symbols from Universe Manager viable_symbols or cached watchlist fallback
- Overlap protection via `asyncio.Lock()`; graceful CancelledError handling
- Polling task started/stopped in lifespan handler
- 6 new pytest tests

**Session 4a (S4a): Reference Data Cache Layer**
- JSON file cache with per-symbol `cached_at` timestamps
- `save_cache()` with atomic write (temp file + `os.replace()`)
- `load_cache()` with corrupt-file fallback; `get_stale_symbols()` for incremental diffs
- `SymbolReferenceData.to_dict()`/`from_dict()` serialization
- Fixed S3c lint issues (import sorting, contextlib.suppress)
- 14 new pytest tests

**Session 4b (S4b): Incremental Warm-Up Wiring**
- `fetch_reference_data_incremental()`: load cache → diff stale → fetch delta → merge → save
- `build_viable_universe()` wired to use incremental fetch
- Reduces ~27-minute warm-up to ~2–5 minutes on subsequent runs (DEC-314)
- 9 new pytest tests

**Session 5 (S5): Runner CLI Extraction + Conformance Monitoring**
- Extracted `Colors`, `print_*` helpers, `build_argument_parser()` from `main.py` to `cli.py`
- `main.py` reduced from 2,187 to 2,067 lines (~120 line reduction)
- `conformance_fallback_count` in RunState; `is_fallback` flag in ConformanceVerdict
- WARNING logged when fallback count exceeds 2 per run
- 9 new runner tests (201 → 210)

**Key decisions:** DEC-308 (deferred initialization), DEC-309 (separate catalyst.db), DEC-310 (CatalystConfig in SystemConfig), DEC-311 (semantic dedup), DEC-312 (batch-then-publish), DEC-313 (FMP canary), DEC-314 (reference data cache), DEC-315 (polling loop)
**Sessions:** 9 implementation (S1, S2a, S2b, S3a, S3b, S3c, S4a, S4b, S5)
**Test counts:** S1(+12), S2a(+5), S2b(+11), S3a(+8), S3b(+9), S3c(+6), S4a(+14), S4b(+9), S5(+9) = +83 new pytest, +0 Vitest
**Notes:** Tier 3 review remediation sprint. All 9 sessions CLEAR at Tier 2 review (S3c had CONCERNS for 2 lint issues, fixed in S4a). No architectural escalations. DEF-036 (stock-list caching) resolved by reference data cache. Runner now 13 modules, 210 tests.

---

### Sprint 23.7 — Startup Scaling Fixes (2511 pytest + 435 Vitest, +21/+0)

**Trigger:** Live QA campaign (post-Sprint 23.6) discovered 3 bugs preventing full-universe boot.
**Type:** Impromptu triage. **Urgency:** URGENT — system could not reach RUNNING state with `universe_manager.enabled: true`.

**Session 1 (S1): Time-Aware Indicator Warm-Up**
- Replaced blocking per-symbol warm-up (12+ hours for 6,005 symbols) with time-aware approach
- Pre-market boot (≤9:30 AM ET): warm-up skipped entirely — live stream builds indicators from open
- Mid-session boot (>9:30 AM ET): lazy per-symbol backfill on first candle arrival
- Backfill runs synchronously on reader thread before candle dispatch (preserves DEC-025 FIFO)
- Thread-safe warm-up tracking via `threading.Lock` (consistent with DEC-088)
- Failed backfills mark symbol as warmed (no retry loop) — fail-closed via indicator validity
- 9 new pytest tests

**Session 2 (S2): Reference Cache Resilience + API Double-Bind Fix**
- Periodic cache saves every 1,000 successfully fetched symbols during reference data fetch
- Shutdown signal handler saves partial cache before exit
- Internal `_cache` pre-populated with non-stale entries so checkpoints include old + new data
- API server double-bind root cause: duplicate WebSocket bridge start in lifespan handler — removed
- Port-availability guard via `socket.bind()` check before `uvicorn.run()`
- Headless mode fallback on port conflict (system continues without API server)
- 12 new pytest tests

**Key decisions:** DEC-316 (time-aware warm-up), DEC-317 (periodic cache saves), DEC-318 (port guard)
**Sessions:** 2 implementation (S1, S2)
**Test counts:** S1(+9), S2(+12) = +21 new pytest, +0 Vitest
**Notes:** Both sessions CLEAN at Tier 1, CLEAR at Tier 2. No escalations. Tier 2 S2 noted cosmetic test count discrepancy in close-out (reported 14, actual 12). TOCTOU race in port guard noted as acceptable defense-in-depth.

---

### Sprint 23.8 — Intelligence Pipeline Live QA Fixes (2529 pytest + 435 Vitest, +18/+0)

**Trigger:** First-ever live run of the NLP Catalyst Pipeline (Sprint 23.5/23.6) during March 12 QA session revealed multiple bugs preventing end-to-end operation.
**Type:** Impromptu triage. **Urgency:** DISCOVERED — found during live QA campaign.

**Session 1 (S1): Pipeline Resilience + Symbol Scope**
- Added `asyncio.wait_for(120)` safety timeout wrapping pipeline gather in polling loop
- Validated existing `done_callback` and `app_state.intelligence_polling_task` from QA session
- Fixed `get_symbols()` to return scanner watchlist (~15 symbols) instead of full viable universe (6,342)
- Added fallback: viable universe capped at `max_batch_size` when watchlist empty
- Symbol count logged per poll cycle
- Fixed pre-existing config alignment test (system_live.yaml catalyst section)
- Cleaned QA debug patches (log level INFO→DEBUG)
- 5 new pytest tests

**Session 2 (S2): Cost Ceiling Enforcement + Classifier Guards**
- Added cycle cost tracking via `_classify_with_claude` return type change to `tuple[list | None, float]`
- Validated existing `record_usage()` calls and `usage_tracker is not None` guards
- Updated classification log format to include dollar cost: `"Classification cycle cost: $X.XXXX (N via Claude, N via fallback, N cached)"`
- Ceiling breach logs at WARNING level (judgment call — more operationally appropriate than INFO)
- 5 new pytest tests

**Session 3 (S3): Source Hardening + Databento Warm-Up Fix**
- Validated existing `ClientTimeout(total=30, sock_connect=10, sock_read=20)` on all three sources
- Implemented FMP news circuit breaker: first 401/403 sets `_disabled_for_cycle` flag, remaining symbols/batches skipped, WARNING with skip count at cycle end, flag resets next cycle
- Clamped Databento lazy warm-up `end` to `now - 600s`, skip if clamped end < start (DEBUG log)
- Pre-market boot path (DEC-316 skip) unaffected
- 8 new pytest tests

**Key decisions:** DEC-319 (wait_for timeout), DEC-320 (done_callback), DEC-321 (watchlist scope), DEC-322 (source timeouts validated), DEC-323 (FMP circuit breaker), DEC-324 (cost ceiling enforcement), DEC-325 (None guards validated), DEC-326 (warm-up end clamp)
**Sessions:** 3 implementation (S1, S2, S3)
**Test counts:** S1(+5), S2(+5), S3(+8) = +18 new pytest, +0 Vitest
**Notes:** S1 CLEAN/CLEAR, S2 CLEAN/CLEAR, S3 MINOR_DEVIATIONS/CONCERNS. S3 CONCERNS: SEC Edgar timeout test is tautological (doesn't call `start()`, tests hardcoded values) — tracked for Sprint 23.9 rewrite. Several "fixes" turned out to be validations of existing Sprint 23.5/23.6 code — the implementations were more complete than QA session diagnostics suggested. 2 pre-existing test_main.py failures discovered under xdist parallel execution (`test_orchestrator_in_app_state`, `test_multiple_strategies_registered_with_orchestrator`) — tracked for Sprint 23.9 investigation.

---

### Sprint 23.9 — Frontend + Test Cleanup (2532 pytest + 446 Vitest, +3/+11)

**Trigger:** Issues discovered during live QA campaign (March 12) and Sprint 23.8 Tier 2 review CONCERNS.
**Type:** Impromptu triage (fast-follow to 23.8). **Urgency:** DISCOVERED.

**Session 1 (S1): Catalyst Hook Gating + Test Fixes + Debrief Investigation**
- Created `usePipelineStatus` hook extracting `catalyst_pipeline` component status from existing `useHealth()` hook (15s polling, no new network requests). Fail-closed: queries disabled when pipeline status unknown or errored.
- Gated `useCatalysts` and `useIntelligenceBriefings` TanStack Query hooks on `isPipelineActive` via `enabled` option. Zero catalyst/briefing HTTP requests when pipeline is inactive.
- Registered `catalyst_pipeline` component with `health_monitor` in `server.py` after successful pipeline init (health.py was on do-not-modify list).
- Rewrote tautological SEC Edgar timeout test: now calls `await client.start()` with mocked CIK map refresh, inspects `client._session.timeout` values. Matches Finnhub/FMP timeout test pattern.
- Fixed xdist test isolation: `load_dotenv()` in `ArgusSystem.__init__()` re-loaded real `ANTHROPIC_API_KEY` from `.env` after `monkeypatch.delenv()`, and `AIConfig.auto_detect_enabled` model validator overrode `enabled=False` → `True`. Fix: `monkeypatch.setenv("ANTHROPIC_API_KEY", "")` + explicit `ai: enabled: false` in test YAML.
- Investigated debrief 503 root cause (read-only): `DebriefService` initialized in `dev_state.py` but never wired in `server.py` lifespan. Findings reported in close-out for Session 2.
- 11 new Vitest tests (5 for `usePipelineStatus`, 3 for catalyst gating, 3 for briefing gating)

**Session 2 (S2): Debrief 503 Fix**
- Initialized `DebriefService(db)` in `server.py` lifespan using `trade_logger._db`, matching `dev_state.py` pattern (~10 lines). Guard clause `debrief_service is None` in `dependencies.py` preserved for genuine init failure.
- Frontend empty state already existed in `BriefingList.tsx:226-238` — the 503 was triggering the error path instead. No frontend changes needed.
- 3 new pytest tests (`TestDebriefEndpointWiring`: 503 when None, 200 empty, 200 with data)

**Key decisions:** DEC-329 (pipeline health hook gating)
**Sessions:** 2 implementation (S1, S2)
**Test counts:** S1(+0 pytest, +11 Vitest), S2(+3 pytest, +0 Vitest) = +3 new pytest, +11 new Vitest
**DEF closures:** DEF-041 (catalyst hook short-circuit), DEF-043 (debrief 503), DEF-045 (SEC Edgar test rewrite), DEF-046 (xdist — 2 named tests fixed, 4 additional pre-existing failures tracked as DEF-048)
**Notes:** S1 MINOR_DEVIATIONS/CLEAR. Deviation: server.py health monitor registration was unanticipated but justified (health.py on do-not-modify list). S2 CLEAN/CONCERNS. CONCERNS: close-out ran scoped tests instead of full suite for final session (DEC-328 violation — process only, code correct). 4 additional xdist failures remain pre-existing (DEF-048, same `load_dotenv` race pattern). 22 pre-existing TypeScript build errors unrelated to this sprint.

---

### Sprint 24 — Setup Quality Engine + Dynamic Sizer (2686 pytest + 497 Vitest, +154/+51)

**Date:** March 13–14, 2026
**Scope:** Full quality pipeline from strategy pattern strength through quality scoring, dynamic position sizing, API endpoints, and frontend visualization across all 7 pages.
**Type:** Planned sprint. **Phase:** 5 (Foundation Completion).

**Session 1 (S1): SignalEvent Enrichment + ORB Pattern Strength**
- Added 4 optional fields to SignalEvent: `pattern_strength`, `signal_context`, `quality_score`, `quality_grade`
- Created QualitySignalEvent for UI consumption
- Implemented `_calculate_pattern_strength()` on OrbBaseStrategy (4-factor: volume 30%, ATR 25%, chase 25%, midpoint 20%)
- Stored `atr_ratio` in OrbSymbolState to avoid redundant indicator fetches
- 22 new pytest tests

**Session 2 (S2): VWAP Reclaim + Afternoon Momentum Pattern Strength**
- Implemented `_calculate_pattern_strength()` for VWAP Reclaim (4-factor: volume 30%, pullback 25%, reclaim 25%, VWAP proximity 20%)
- Implemented `_calculate_pattern_strength()` for Afternoon Momentum (4-factor: volume 30%, consolidation 25%, breakout 25%, ATR-relative 20%)
- All 4 strategies now emit `share_count=0` for quality pipeline deferred sizing
- Order Manager `on_approved()` early-returns on zero shares
- 12 new pytest tests

**Session 3 (S3): Firehose Source Refactoring (DEC-327)**
- Added `firehose: bool = False` parameter to CatalystSource.fetch_catalysts()
- Finnhub firehose: single `GET /news?category=general` call
- SEC EDGAR firehose: single EFTS search-index call
- 17 new intelligence tests

**Session 4 (S4): SetupQualityEngine Core**
- Created `quality_engine.py` (139 lines) with SetupQuality dataclass
- 5-dimension scoring: pattern strength, catalyst quality, volume profile, historical match, regime alignment
- QualityEngineConfig with configurable weights and thresholds
- Grade thresholds: A+ (≥90), A (≥80), B+ (≥70), B (≥60), C+ (≥50), C (≥40), C- (<40)
- 23 new intelligence tests

**Session 5a (S5a): DynamicPositionSizer + Config Models**
- Created DynamicPositionSizer: grade → risk tier → share count
- Replaced flat dict configs with Pydantic models: QualityWeightsConfig, QualityThresholdsConfig, QualityRiskTiersConfig
- Field validators: weights sum to 1.0, thresholds in descending order
- 19 new pytest tests

**Session 5b (S5b): Config Wiring + YAML + DB Schema**
- Wired QualityEngineConfig into SystemConfig
- Created `config/quality_engine.yaml` with all defaults
- Added `quality_engine` sections to system.yaml and system_live.yaml (enabled: false)
- Created `quality_history` table: 20 columns, 4 indexes
- 9 new pytest tests

**Session 6a (S6a): Pipeline Wiring + RM Check 0 + Quality History**
- Extracted `_process_signal()` in main.py for quality pipeline flow
- Risk Manager check 0: rejects `share_count ≤ 0` before circuit breaker evaluation
- Quality history recording via `record_quality_history()`
- QualitySignalEvent published after scoring
- Pipeline bypass: BrokerSource.SIMULATED or quality_engine.enabled=false → legacy sizing
- `_grade_meets_minimum()` helper on ArgusSystem
- 14 new pytest tests

**Session 6b (S6b): Integration Tests + Error Paths**
- 12 comprehensive integration tests: engine exception fallback, missing catalyst/RVOL, regimes, bypasses
- Fixed test_main.py hang: dangling asyncio task in shutdown test (added cleanup)
- test_main.py runtime reduced from 7+ minutes to 2.16s

**Session 7 (S7): Quality Server Init + Firehose Pipeline**
- Quality engine initialization in server.py lifespan
- `firehose: true` default for background polling loop
- Gated Finnhub per-symbol recs behind `if not firehose`
- Registered quality engine as health component
- 14 new pytest tests

**Session 8 (S8): Quality API Endpoints**
- 3 endpoints: `GET /{symbol}` (latest), `GET /history` (paginated), `GET /distribution` (grade counts)
- Registered quality router in routes/__init__.py
- 12 new API tests

**Session 9 (S9): Quality UI — QualityBadge + Trades Integration**
- QualityBadge component with grade coloring + tooltip
- 3 TanStack Query hooks: useQualityScore, useQualityHistory, useQualityDistribution
- Quality column in Trades table (tablet+ breakpoint)
- Setup Quality section in TradeDetailPanel
- 22 new Vitest tests

**Session 10 (S10): Dashboard Panels + Orchestrator Signals**
- QualityDistributionCard (donut chart) on Dashboard
- SignalQualityPanel (histogram) on Dashboard
- RecentSignals list on Orchestrator page
- `strategy_id` added to API response (backward-compatible)
- 16 new Vitest tests

**Session 11 (S11): Performance Grade Chart + Debrief Scatter Plot**
- QualityGradeChart: grouped bars by grade (avg PnL, win rate, R-multiple) on Performance
- QualityOutcomeScatter: quality score vs R-multiple with linear trend line on Debrief
- Outcome fields added to quality API
- 13 new Vitest tests, 4 new pytest tests

**Session 11f (S11f): Visual Review Fixes + Code Cleanup**
- Extracted GRADE_COLORS/GRADE_ORDER to shared `quality/constants.ts`
- Fixed 3 visual bugs: RecentSignals crash, QualityGradeChart invisible bars, QualityOutcomeScatter no dots
- Defensive `== null` checks for API response field omission
- Removed unused Line import, updated DebriefPage docstring
- Created QA seed script for visual testing
- 0 new tests (all existing pass, no regressions)

**Key decisions:** DEC-330 (SignalEvent enrichment), DEC-331 (VWAP/AfMo pattern strength + OM guard), DEC-332 (firehose refactoring), DEC-333 (quality engine 5-dimension scoring), DEC-334 (dynamic sizer + config models), DEC-335 (config wiring + YAML + DB schema), DEC-336 (pipeline wiring + RM check 0), DEC-337 (integration tests + error paths), DEC-338 (server init + firehose pipeline), DEC-339 (quality API routes), DEC-340 (quality UI — badge + hooks + trades), DEC-341 (quality UI — dashboard + orchestrator + performance + debrief)
**Sessions:** 13 implementation (S1, S2, S3, S4, S5a, S5b, S6a, S6b, S7, S8, S9, S10, S11, S11f)
**Test counts:** S1(+22), S2(+12), S3(+17), S4(+23), S5a(+19), S5b(+9), S6a(+14), S6b(+12), S7(+14), S8(+12), S9(+22V), S10(+16V), S11(+4+13V), S11f(+0) = +158 new pytest, +51 new Vitest
**Review verdicts:** S1 MINOR_DEVIATIONS, S2 CLEAR, S3 CLEAR, S4 CLEAR, S5a CONCERNS (test count documentation), S5b CLEAR, S6a CONCERNS (spec deviation with rationale), S6b CLEAR, S7 CLEAR, S8 CLEAR, S9 CLEAR, S10 CLEAR, S11 CLEAR, S11f CLEAR
**New deferred items:** DEF-050 (ArgusSystem e2e test), DEF-052 (dashboard quality interactivity), DEF-053 (dashboard tables quality column), DEF-054 (orchestrator clickable signals), DEF-055 (orchestrator 3-column layout), DEF-056 (scatter plot page placement), DEF-057 (EFTS URL validation), DEF-058 (trades DB quality columns), DEF-059 (TS build errors), DEF-060 (PROVISIONAL comment gap), DEF-061 (quality API private attrs), DEF-062 (seed script cleanup)
**Notes:** Largest Sprint 24 scope: quality pipeline end-to-end from strategy signals through scoring, sizing, API, and full frontend integration across all 7 Command Center pages. 2 CONCERNS ratings (S5a test count documentation, S6a test assertion spec deviation) both have acceptable rationales. S11f cleaned up visual bugs and shared constant duplication. All sessions completed successfully. Ready for Phase 5 Gate (Sprint 24.5).

### Sprint 24.1 — Post-Sprint Cleanup & Housekeeping (2,709 pytest + 503 Vitest, +23/+6)
**Date:** March 14, 2026
**Scope:** Clean up 13 accumulated housekeeping items (DEF-050 through DEF-062) from Sprint 24 reviews before the Phase 5 Gate strategic check-in. No new features, no architectural changes, no new DEC entries.

**Session 1a (S1a): Trades Quality Column Wiring**
- Wired quality_grade/quality_score from SignalEvent through Order Manager → TradeLogger → DB schema
- Added quality columns to trades table schema with migration
- Fixed falsy-zero write bug in trade_logger.py:94 (post-review)
- 5 new pytest tests

**Session 1b (S1b): Trivial Backend Fixes**
- CatalystStorage init log level: `debug` → `warning` in main.py
- Added `@property` accessors for `_db`/`_config` on SetupQualityEngine
- Added PROVISIONAL comments to system.yaml/system_live.yaml quality sections
- Added production guard to seed_quality_data.py script
- 4 new pytest tests

**Session 2 (S2): ArgusSystem E2E Integration Test + EFTS Validation**
- Full strategy → quality engine → sizer → RM integration test (DEF-050)
- Validated SEC EDGAR EFTS URL works with User-Agent header (DEF-057, no code change needed)
- 4 new pytest tests

**Session 3 (S3): TypeScript Build Error Fixes**
- Fixed all 22 pre-existing TypeScript build errors (DEF-059)
- Removed unused `pageKey` prop from CopilotPanel, removed PAGE_KEYS constant
- Added `badge` prop to CardHeader component (cascading from `icon` prop addition)
- 3 new Vitest tests

**Session 4a (S4a): Orchestrator 3-Column Layout + Scatter Relocation**
- Combined Decision Log, Catalyst Alerts, Recent Signals into 3-column row (DEF-055)
- Relocated QualityOutcomeScatter from Debrief Quality tab to Performance Distribution tab (DEF-056)
- 2 new Vitest tests

**Session 4b (S4b): Quality Tooltips, Table Badges, Clickable Signals**
- Dashboard quality chart tooltips and legend (DEF-052)
- Quality column in Dashboard Positions/Recent Trades tables (DEF-053)
- Clickable signal rows with SignalDetailPanel in Orchestrator (DEF-054)
- 1 new Vitest test

**Session 4f (S4f): Visual Review Fixes**
- Expanded from 0.5-session contingency to full session + follow-up round (8 visual fixes)
- Removed QualityDistributionCard from Dashboard (redundant with SignalQualityPanel)
- Redesigned QualityGradeChart as ComposedChart (bars + line, dropped Avg R)
- Orchestrator header formatting consistency fix
- Performance Distribution tab 2x2 equal-height grid layout
- Histogram bar resize animation fix (isAnimationActive={false})
- Tooltip slide animation fix on all quality charts
- RecentTrades quality column alignment fix (fixed-width spans)
- Performance charts side-by-side grid layout
- No formal Tier 2 review (visual-only, developer-verified)
- 0 new tests

**Key decisions:** None (no DEC entries created — housekeeping only)
**Sessions:** 7 (S1a, S1b, S2, S3, S4a, S4b, S4f)
**Test counts:** S1a(+5), S1b(+4), S2(+4), S3(+3V), S4a(+2V), S4b(+1V), S4f(+0) = +23 new pytest (S1a+S1b+S2 subtotal: 13; S3: 0 pytest change; S4a+S4b: 10 pytest implied by total), +6 new Vitest
**Review verdicts:** S1a CONCERNS (resolved in-session), S1b CLEAR, S2 CLEAR, S3 CONCERNS (non-blocking), S4a CLEAR, S4b CLEAR, S4f no formal review
**DEF items resolved:** DEF-050 (e2e test), DEF-051 (backend fixes), DEF-052 (chart tooltips/legend), DEF-053 (quality columns), DEF-054 (clickable signals), DEF-055 (3-column layout), DEF-056 (scatter relocation), DEF-057 (EFTS validation), DEF-058 (trades quality wiring), DEF-059 (TS errors), DEF-060–062 (PROVISIONAL comments, seed guard, quality accessors)
**TS errors:** 22 → 0
**Notes:** Housekeeping-only sprint consuming accumulated DEF items from Sprint 24 reviews. S4f expanded beyond original 0.5-session contingency scope to cover 8 visual fixes (all frontend CSS/layout/animation, zero backend impact). All DEF-050 through DEF-062 resolved. No new DEF items assigned. Ready for Phase 5 Gate (Sprint 24.5).

### Sprint 24.5 — Strategy Observability + Operational Fixes (2,768 pytest + 523 Vitest, +59/+20)
**Date:** March 15–16, 2026
**Scope:** Real-time and historical visibility into what every strategy evaluates on every candle, so that paper trading validation produces actionable diagnostic data even when zero trades occur. Plus three operational fixes discovered during live QA.

**Session 1 (S1): Telemetry Infrastructure**
- Created `StrategyEvaluationBuffer` (ring buffer, maxlen=1000) on `BaseStrategy`
- Defined `EvaluationEventType` (9 types) and `EvaluationResult` (3 types) StrEnums
- `record_evaluation()` with try/except guard (never raises)
- REST endpoint `GET /api/v1/strategies/{id}/decisions` (JWT-protected)
- DEC-342: Strategy evaluation telemetry — ring buffer, no EventBus
- 7 new pytest tests

**Session 2 (S2): ORB Family Instrumentation**
- Instrumented OrbBaseStrategy and OrbBreakoutStrategy with evaluation events
- OR accumulation, finalization, exclusion checks, entry conditions, signal generation
- Per-failure-mode ENTRY_EVALUATION events for diagnostic granularity
- 11 new pytest tests

**Session 3 (S3): VWAP + AfMo Instrumentation**
- Instrumented VwapReclaimStrategy and AfternoonMomentumStrategy
- AfMo `_check_breakout_entry()` restructured from sequential early-return to evaluate-all-then-check pattern for 8 individual CONDITION_CHECK events
- 3 informational-only conditions (body_ratio, spread_range, time_remaining) — emit PASS/FAIL but do not gate signal
- 17 new pytest tests

**Session 3.5 (S3.5): Event Persistence**
- `EvaluationEventStore` — SQLite persistence with 7-day retention (ET-date cleanup)
- Fire-and-forget async forwarding from buffer to store via `loop.create_task()`
- REST endpoint supports `?date=` param for historical queries (routes to store for non-today dates, buffer for today)
- `AppState.telemetry_store` wired in server lifespan with `close()` resource cleanup
- 11 new pytest tests

**Session 4 (S4): Frontend Decision Stream**
- `StrategyDecisionStream` component with TanStack Query hook (`useStrategyDecisions`, 3s polling)
- Color-coded event rows (PASS=green, FAIL=red, INFO=amber, signals=blue)
- Symbol filter, summary stats, expandable metadata
- Error state rendering
- 10 new Vitest tests

**Session 4a-fix (S4a): Frontend Type Fix**
- Fixed response type mismatch: changed frontend from `StrategyDecisionsResponse` wrapper to `EvaluationEvent[]` bare array
- Summary stats derived from filtered events (was unfiltered)
- 4 new Vitest tests

**Session 5 (S5): Orchestrator Integration**
- "View Decisions" button on strategy cards opens slide-out panel
- Optional `onViewDecisions` callback prop on `StrategyOperationsCard` and `StrategyOperationsGrid` for backward compatibility
- AnimatePresence animation on slide-out panel
- 4 new Vitest tests

**Session 5f (S5f): Visual Fixes — Round 1**
- 3-column container y-values aligned (min-h-10 on CardHeader)
- Strategy card heights made consistent (fullHeight + flex layout + mt-auto footer)
- Dropdown chevron padding fix (pl-2 pr-8)
- 3 new pytest tests

**Session 5f-fix (S5f-fix): MockStrategy + Card Height Fix**
- Added `eval_buffer` field to MockStrategy in `dev_state.py` with mock event seeding
- Fixed 3-column card heights (h-full flex flex-col + Card flex-1)
- 2 new Vitest tests

**Session 5f-fix2 (S5f-fix2): Esc Key, Two-Line Rows, Filter Bugs**
- Esc key closes slide-out panel (useEffect keydown listener in OrchestratorPage)
- Two-line event row layout (time+symbol+result / event_type+reason)
- Removed stagger animation (caused opacity:0 bug on filtered-in items)
- Removed server-side symbol filter (caused dropdown to lose options)
- Replaced max-h-96 with flex-1 min-h-0 for event list fill
- 1 new pytest test

**Session 6 (S6): Operational Fixes**
- AI insight data enriched with `session_status`, `session_elapsed_minutes`, `minutes_until_open` (replaces binary open/closed)
- Finnhub 403 responses downgraded from ERROR to WARNING with per-cycle counters and summary log
- FMP circuit breaker (DEC-323) dedicated test coverage added
- 2 new pytest tests

**Key decisions:** DEC-342 (strategy evaluation telemetry)
**Sessions:** 11 (S1, S2, S3, S3.5, S4, S4a-fix, S5, S5f, S5f-fix, S5f-fix2, S6)
**Test counts:** pytest 2,709 → 2,768 (+59), Vitest 503 → 523 (+20) = 79 new tests total
**Review verdicts:** S1 CLEAR, S2 CLEAR, S3 CONCERNS (accepted — AfMo restructure necessary), S3.5 CLEAR, S4 CONCERNS (resolved S4a), S5 CLEAR, S6 CLEAR
**DEF items:** None created — all 18 tracked issues resolved in-sprint
**Notes:** Observability sprint focused on paper trading diagnostic value. The evaluation telemetry system is intentionally separated from the EventBus to avoid flooding subscribers with ~200 diagnostic events per candle across 4 strategies. AfMo's `_check_breakout_entry()` restructure was the only non-additive change — necessary to emit 8 individual condition check events per the sprint spec.

---

### Sprint 25 — The Observatory (2,765 pytest + 599 Vitest = 3,364 total)
**Date:** Mar 17–18, 2026
**Scope:** New Observatory page (Command Center page 8) providing immersive, real-time and post-session visualization of the entire ARGUS trading pipeline. Four views (Funnel/Radar/Matrix/Timeline), keyboard-first navigation, detail panel with live candlestick charts, session vitals, and debrief mode. ObservatoryService backend with 4 query methods. Observatory WebSocket for push-based pipeline updates. Config-gated via `observatory.enabled`.
**Key decisions:** DEC-342 (carried from Sprint 24.5 — strategy evaluation telemetry)
**No new DEC or DEF entries created during this sprint.**

**Session 1 (S1): Backend API — ObservatoryService + REST Endpoints**
- ObservatoryService (`argus/analytics/observatory_service.py`): read-only query service over EvaluationEventStore and UniverseManager
- 4 methods: `get_pipeline_stages`, `get_closest_misses`, `get_symbol_journey`, `get_session_summary`
- ObservatoryConfig Pydantic model wired into SystemConfig
- 4 REST endpoints under `/api/v1/observatory/`
- New pytest tests

**Session 2 (S2): Backend WebSocket — Observatory Live Updates**
- Observatory WebSocket endpoint (`/ws/v1/observatory`) independent from AI chat WS
- Push-based tier transition detection and evaluation summaries
- JWT authentication on WS connection
- New pytest tests

**Session 3 (S3): Page Shell + Routing + Keyboard Navigation**
- Observatory page component with React.lazy code-splitting
- View switching via keyboard (initially 1-4 keys)
- Sidebar navigation updated (7 → 8 pages)
- Suspense fallback, responsive layout shell
- New Vitest tests

**Session 3f (S3f): Keybinding Fix**
- View-switching keys changed from 1-4 to f/m/r/t (mnemonic) due to conflict with sidebar navigation shortcuts
- Camera control placeholders repurposed; camera controls moved to Shift+R/Shift+F

**Session 4a (S4a): Detail Panel Core**
- Right slide-out detail panel with per-symbol condition grid
- Quality score display, catalyst summary section
- Strategy history chronological list
- Panel persists across view switches
- New Vitest tests

**Session 4b (S4b): Candlestick Chart + Hooks**
- Live candlestick chart in detail panel via Lightweight Charts
- TanStack Query hooks for observatory data (pipeline stages, symbol journey, closest misses)
- API client types for observatory endpoints
- New Vitest tests

**Session 5a (S5a): Matrix View Core**
- Condition heatmap sorted by proximity to trigger
- Green/red/gray cells for pass/fail/unknown conditions
- Column headers with condition names
- New Vitest tests

**Session 5b (S5b): Matrix Scroll + Interaction**
- Virtual scrolling for large symbol lists
- Tab key navigation for symbol selection
- Click-to-select with detail panel integration
- Highlight + selection unified state management
- New Vitest tests

**Session 6a (S6a): Three.js Scene Setup**
- Three.js (r128) integration with React.lazy code-splitting (separate chunk)
- Shared scene architecture: Funnel and Radar share single Three.js scene with camera presets
- Translucent cone geometry with tier disc overlays
- OrbitControls for camera manipulation
- Camera shortcuts: Shift+R (reset), Shift+F (fit)
- New Vitest tests

**Session 6b (S6b): Symbol Particles**
- InstancedMesh for symbol particles (up to 5,000 symbols)
- CSS2DRenderer for symbol labels with LOD behavior
- Monotonic instance slot allocation
- TIER_DEFS extracted to shared constants.ts
- New Vitest tests

**Session 7 (S7): Radar Camera Animation**
- RadarView as thin wrapper passing mode="radar" to FunnelView
- Bottom-up camera perspective with smooth animation transition
- Concentric ring visualization with trigger point at center
- New Vitest tests

**Session 8 (S8): Timeline View**
- Strategy lane timeline (9:30 AM–4:00 PM ET) with SVG rendering
- Event marks at 4 severity levels (pass/fail/skip/trigger)
- Horizontal time axis with market hours
- New Vitest tests

**Session 9 (S9): Session Vitals + Debrief Mode**
- Session vitals bar: connection status, evaluation counts, closest miss, top blocking condition
- Live metrics via WS + REST polling
- Debrief mode: date picker switches all views to historical data (7-day retention from EvaluationEventStore)
- New Vitest tests

**Session 10 (S10): Integration Polish**
- Tab handler overlap fix (unified highlight+selection with isMatrixActive flag)
- EvaluationEventStore public API: `execute_query()` method and `is_connected` property added
- Type narrowing (object|None → float|str|bool|None)
- Unused reason column removed from SELECT
- Inline import moved to top-level
- Imperative loop replaced with reduce()
- TIER_DEFS duplication resolved (shared constants.ts)
- Suspense fallback text added
- Unused VIEW_LABELS removed
- 2 new camera shortcut tests
- system_live.yaml observatory config added

**Sessions:** 14 (S1, S2, S3, S3f, S4a, S4b, S5a, S5b, S6a, S6b, S7, S8, S9, S10)
**Test counts:** pytest 2,768 → 2,765 (−3, DEF-048 xdist gap), Vitest 523 → 599 (+76) = 73 net new tests
**Review verdicts:** 10 CLEAR, 4 CONCERNS (all non-blocking; resolved in-sprint or accepted as LOW/INFO)
**DEF items:** None created. All review findings resolved in-sprint.
**Notes:** Purely additive sprint — no architectural decisions affecting the trading pipeline. The −3 pytest delta is from known DEF-048 xdist ignore gap, not a regression. Three.js is code-split via React.lazy to avoid impacting initial bundle size. Shared-scene pattern (Funnel+Radar) avoids duplicate Three.js contexts. EvaluationEventStore gained `execute_query()` public method to replace private `_conn` access by ObservatoryService.

---

### Sprint 25.5 — Universe Manager Watchlist Wiring Fix (2,782 pytest + 599 Vitest = 3,381 total)
**Date:** Mar 18, 2026
**Scope:** Fix critical bug where strategy watchlists are empty when Universe Manager is enabled, causing all four strategies to silently drop every candle since Sprint 23 (March 7, 10+ days of inert paper trading). Populate strategy watchlists from UM routing, convert watchlist to set for O(1) lookups, add zero-evaluation health warning.
**Type:** Bugfix sprint. **Urgency:** CRITICAL.

**Session 1 (S1): Watchlist Wiring + List-to-Set**
- Populated each strategy's watchlist from UM routing table after `build_routing_table()` in Phase 9.5 of main.py startup via `strategy.set_watchlist(symbols, source="universe_manager")`
- Converted `_watchlist` from `list[str]` to `set[str]` for O(1) membership checks in `on_candle()` gates
- Added `source` parameter to `set_watchlist()` (default `"scanner"`) for logging provenance
- `watchlist` property continues to return `list[str]` — external API unchanged
- `reset_daily_state()` clears to `set()`
- New pytest tests

**Session 2 (S2): Zero-Evaluation Health Warning + E2E Telemetry Tests**
- `HealthMonitor.check_strategy_evaluations()` detects active strategies with populated watchlists but zero evaluation events after operating window + 5 min grace period
- Sets component status to DEGRADED; self-corrects to HEALTHY when evaluations resume (idempotent)
- Periodic 60s asyncio task in main.py during market hours only (9:30–16:00 ET)
- Opens/closes its own `EvaluationEventStore` per check cycle to avoid coupling with server.py-managed store lifecycle
- E2E telemetry tests in `tests/test_evaluation_telemetry_e2e.py`
- New pytest tests (including 9th test `test_health_warning_self_corrects` beyond the 8 required — justified by spec's idempotency requirement)

**Key decisions:** DEC-343 (watchlist population from UM routing), DEC-344 (zero-evaluation health warning)
**Sessions:** 2 implementation (S1, S2)
**Test counts:** pytest 2,765 → 2,782 (+17), Vitest 599 → 599 (+0)
**Review verdicts:** S1 CLEAR, S2 CLEAR
**DEF items:** None created. No new deferred items.
**Notes:** Critical bugfix sprint. Root cause: `set_watchlist()` was never called in the UM code path, but every strategy's `on_candle()` gates on `self._watchlist` as the first check. 10+ days of inert paper trading where candles were routed correctly by UM but silently dropped at strategy level. Zero-evaluation health check ensures this class of silent failure is detected automatically within minutes of market open.

---

### Sprint 25.6 — Bug Sweep (2,794 pytest + 611 Vitest = 3,405 total)
**Date:** Mar 19–20, 2026
**Scope:** Fix all operational bugs from March 19 live session — first session after Sprint 25.5 watchlist wiring fix. Nine DEF items (065–073) plus regime stagnation and log hygiene.
**Type:** Bug sweep sprint.

**Session 1 (S1): Telemetry Store DB Separation + Log Hygiene**
- Separated EvaluationEventStore to `data/evaluation.db` (eliminates SQLite write contention)
- Rate-limited write failure warnings to 1 per 60s via `time.monotonic()`
- Health check loop reuses `self._eval_store` instead of creating/closing per cycle
- Store created in main.py Phase 10.3; server.py conditional creation in standalone/dev mode
- DEF-065 (telemetry DB contention), DEF-066 (log bloat from write warnings) resolved
- +6 pytest
- Verdict: CONCERNS (undocumented frontend changes in shared commit — process artifact of parallel execution; hardcoded path in server.py — absorbed into S2)

**Session 2 (S2): Periodic Regime Reclassification**
- Added `Orchestrator.reclassify_regime()` public method returning `tuple[MarketRegime, MarketRegime]`
- Existing `_run_regime_recheck()` refactored to delegate to `reclassify_regime()` (single source of truth)
- Independent 300s periodic task in `main.py._run_regime_reclassification()` with market hours guard (9:30–16:00 ET)
- Sleep-first pattern avoids redundant reclassification immediately after pre-market routine
- SPY unavailability retains current regime, logs WARNING
- +6 pytest
- Verdict: CLEAR

**Session 3 (S3): Trades Page Fixes**
- Replaced pagination with scrollable table (`max-h-[800px]`)
- Full-dataset metrics (removed `limit`/`offset` from `useTrades` call)
- Zustand filter persistence (TradesPage reads from store on mount)
- 6 sortable columns added
- DEF-067 (pagination→scroll), DEF-068 (metrics from paginated subset), DEF-069 (filter persistence), DEF-073 (non-sortable columns) resolved
- +4 Vitest
- Verdict: CLEAR

**Session 4 (S4): Orchestrator Timeline Fixes**
- Strategy Coverage Timeline label width increased to 140px for full strategy names
- Throttled vs suspended visual distinction with separate `isSuspended`/`isThrottled` logic, labels, and tooltips
- DEF-070 (label truncation), DEF-071 (throttled/suspended indistinguishable) resolved
- +3 Vitest
- Verdict: CLEAR

**Session 5 (S5): Dashboard Layout Restructure**
- Positions promoted to Row 2 (above fold on 1080p)
- MarketStatusCard removed from desktop layout (OrchestratorStatusStrip covers same info)
- Universe + SignalQuality moved below fold
- DEF-072 (Positions below fold) resolved
- +2 Vitest
- Verdict: CLEAR

**Session 5f (S5f): Visual Review Fixes**
- Label width bumped from 140px to 160px
- Added Side, Quality, and Exit Type sortable columns with grade-order-aware Quality sort
- DEF-070 (label width finalized), DEF-073 (additional sort columns) finalized
- +3 Vitest
- Verdict: CLEAR

**Parallelization:** S1+S3 ran simultaneously (Track A backend + Track B frontend), then S2+S4 simultaneously. S5 sequential. S5f after visual review.

**Key decisions:** DEC-345 (evaluation.db separation), DEC-346 (periodic regime reclassification).
**DEFs resolved:** DEF-065, DEF-066, DEF-067, DEF-068, DEF-069, DEF-070, DEF-071, DEF-072, DEF-073.
**DEFs created:** DEF-074 (dual regime recheck path consolidation).
**Prior-session bug noted:** 4 pre-existing e2e telemetry test failures in test_evaluation_telemetry_e2e.py (from Sprint 25.5).

---

### Sprint 25.7 — Post-Session Operational Fixes + Debrief Export (2,815 pytest + 611 Vitest = 3,426 total)
**Date:** Mar 21, 2026
**Scope:** Post-session operational fixes from March 20 live session plus debrief export automation. Plus Pylance cleanup (~200 errors across ~20 files, type annotations only).
**Type:** Impromptu operational sprint.

**Session 1 (S1): Operational Fixes + Debrief Export**
- Implemented `DatabentoDataService.fetch_daily_bars()` via FMP stable API (`GET /stable/historical-price-eod/full`) — regime classification now works in live mode (DEC-347)
- Added `last_update` attribute to DatabentoDataService, set in `_dispatch_record()` — health endpoint `last_data_received` no longer null (DEF-076)
- Diagnostic logging when position sizer returns 0 shares (DEF-077)
- Rate-limited regime reclassification warnings (DEF-078)
- New module `argus/analytics/debrief_export.py` — automated debrief data export at shutdown producing `logs/debrief_YYYYMMDD.json` (DEC-348, DEF-079)
- `PerformanceThrottler.check()` zero-trade-history guard (DEC-349, DEF-080)
- `ENTRY_EVALUATION` events include `conditions_passed`/`conditions_total` metadata (DEC-350, DEF-081)
- `Orchestrator.spy_data_available` public property
- `scripts/launch_monitor.sh` — unattended launch + monitoring script with 5 checkpoints and ntfy.sh notifications
- +20 pytest (1 pre-existing updated)

**Post-review:** Pylance cleanup (~200 errors across ~20 files, type annotations only). Bug fix: Position model fields in debrief export. Bug fix: `flatten_all(symbols=...)` invalid kwarg in controls.py.

**Key decisions:** DEC-347, DEC-348, DEC-349, DEC-350
**DEFs resolved:** DEF-075, DEF-076, DEF-077, DEF-078, DEF-079, DEF-080, DEF-081
**Test counts:** pytest 2,794 → 2,815 (+21), Vitest 611 → 611 (+0)

---

### Sprint 25.8 — API Auth 401 + Close-Position Fix (2,815 pytest + 611 Vitest = 3,426 total)
**Date:** Mar 21, 2026
**Scope:** Fix API auth returning 403 instead of 401 for unauthenticated requests. Fix close-position endpoint that either crashed (invalid kwarg) or closed all positions (kwarg removed).
**Type:** Impromptu micro-fix sprint.

**Session 1 (S1): Auth + Close-Position**
- `HTTPBearer(auto_error=False)` + explicit 401 with `WWW-Authenticate: Bearer` header (DEC-351, DEF-083)
- `POST /controls/positions/{id}/close` routes through new `OrderManager.close_position(symbol)` (DEC-352, DEF-085)
- +5 pytest, 35 previously-failing tests now pass

**Key decisions:** DEC-351, DEC-352
**DEFs resolved:** DEF-083, DEF-085
**Test counts:** pytest 2,815 → 2,815 (+5 new, 35 fixed, net count unchanged due to consolidation)

---

### Test Infrastructure Fixes (post-sprint, no sprint number)
**Date:** Mar 21, 2026
**Scope:** Two rounds of test infrastructure work. No production code changes in Round 2.

**Round 1: Test Speed Fix**
- Made `rate_limit_delay_seconds` configurable on `FMPReferenceConfig` (default 0.2), set to 0 in all test fixtures
- Added `slow` pytest marker to pyproject.toml
- Full suite 454s → 178s (−61%). FMP tests 270s → 6.3s (−97.6%)

**Round 2: Fix All Pre-Existing Failures (DEF-086 + DEF-087)**
- Fixed 19 broken tests (11 failures + 8 hangs). Zero production code changes.
- WebSocket tests: rewrote 8 hanging async tests to test bridge pipeline directly via send_queue
- data_fetcher: relaxed datetime64 precision assertion for Pandas 2.x
- e2e telemetry: fixed hardcoded date + added flush helper for async writes
- integration sprint20: updated allocation assertions for regime-based eligibility
- Dependencies upgraded: matplotlib, scipy, scikit-learn for NumPy 2.x compat
- **Final suite: 2,815 passed, 0 failures, 0 hangs. 39s with xdist.**

**DEFs resolved:** DEF-084 (partially — runtime optimized), DEF-086, DEF-087
**Standard test command:** `python -m pytest --ignore=tests/test_main.py -n auto -q` (only test_main.py needs ignoring now)

---

### Phase 5 Gate — Strategic Check-In (March 21, 2026)

**Protocol:** Strategic Check-In (6 sections). Conducted in Claude.ai.

**Key findings:**
- Paper trading: 4 valid sessions, 28+ trades. Gate 2 counter reset (DEC-355).
- Historical data: Databento Standard includes free OHLCV-1m (DEC-353). $1K–$5K purchase eliminated.
- Phase 6 compression: BacktestEngine pulled to Sprint 27 (DEC-354). Learning Loop to Sprint 28.
- Quality Engine: 55% signal active, 45% at neutral defaults (RSK-045). FMP upgrade deferred (DEC-356).
- Velocity: 1.5x multiplier (1 fix sprint per 2 feature sprints).
- PDT reform: FINRA filed with SEC Dec 2025. SEC extended review Jan 2026. Approval expected Q1–Q2 2026.

**Decisions:** DEC-353, DEC-354, DEC-355, DEC-356.
**New risks:** RSK-045 (Quality Engine partial signal).
**Updated risks:** RSK-027 (re-validation committed), RSK-032 (now testable).

---

## Phase P — Pattern Library Foundation (Sprint 26, Mar 21–22)

### Sprint 26 — Red-to-Green + Pattern Library Foundation (2,925 pytest + 620 Vitest = 3,545 total)
**Date:** Mar 21–22, 2026
**Scope:** Add Red-to-Green reversal strategy, PatternModule ABC, Bull Flag and Flat-Top Breakout pattern modules, VectorBT backtesting for all three, integration wiring into main.py, and UI cards for Pattern Library page. From 4 to 7 active strategies/patterns.
**Type:** Feature sprint. **Execution:** Autonomous runner (human-in-the-loop mode).

**Session 1 (S1): PatternModule ABC**
- Created `argus/strategies/patterns/` package with `base.py`
- `CandleBar` frozen dataclass, `PatternDetection` dataclass, `PatternModule` ABC (5 abstract members)
- +10 pytest
- Verdict: CLEAR

**Session 2 (S2): R2G Config + State Machine Skeleton**
- `RedToGreenConfig` Pydantic model, `config/strategies/red_to_green.yaml`
- State machine skeleton (5 states: WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED / EXHAUSTED)
- Key level identification (VWAP, premarket_low, prior_close)
- +12 pytest
- Verdict: CLEAR

**Session 3 (S3): R2G Entry/Exit Logic**
- Full entry logic: gap-down confirmation, level proximity, reclaim detection, volume confirmation
- Exit logic: T1/T2 targets, time stop, max_level_attempts=2
- +13 pytest
- Verdict: CLEAR

**Session 4 (S4): PatternBasedStrategy Wrapper**
- Generic `PatternBasedStrategy` class wrapping any `PatternModule` into a `BaseStrategy`
- Operating window, per-symbol candle deque, signal generation, telemetry integration
- Circular import resolution via `__getattr__` lazy import
- +12 pytest
- Verdict: CLEAR

**Session 5 (S5): BullFlagPattern**
- Pole detection, flag validation, breakout confirmation, measured move targets
- Score weighting: pattern quality 30%, breakout strength 30%, volume 25%, flag tightness 15%
- +11 pytest
- Verdict: CLEAR

**Session 6 (S6): FlatTopBreakoutPattern**
- Resistance clustering, consolidation validation with range narrowing, breakout confirmation
- Score weighting: resistance strength 30%, consolidation quality 30%, breakout conviction 25%, volume surge 15%
- +11 pytest
- Verdict: CLEAR

**Session 7 (S7): VectorBT R2G Backtester**
- Dedicated `vectorbt_red_to_green.py` with gap-down detection, key level identification, reclaim entry simulation
- Walk-forward dispatch via `walk_forward.py` (additive changes only)
- +13 pytest
- Verdict: CLEAR

**Session 8 (S8): Generic PatternBacktester**
- `vectorbt_pattern.py` — generic sliding-window backtester for any PatternModule
- Parameter grid generation (±20%/±40% variations of defaults)
- Self-contained walk-forward loop
- +20 pytest
- Verdict: CLEAR

**Session 9 (S9): Integration Wiring**
- Wired R2G, Bull Flag, Flat-Top into `main.py` startup sequence
- Strategy spec sheets: `STRATEGY_RED_TO_GREEN.md`, `STRATEGY_BULL_FLAG.md`, `STRATEGY_FLAT_TOP_BREAKOUT.md`
- +8 pytest
- Verdict: CLEAR

**Session 10 (S10): UI Cards + Pattern Library**
- Pattern Library family mappings for new strategies in `strategyConfig.ts`
- UI labels, colors, descriptions for R2G, Bull Flag, Flat-Top
- +8 Vitest (strategyConfig.test.ts)
- Verdict: CLEAR

**Session 10f (S10f): Visual Review Fixes**
- Fixed dev_state.py for 3 new mock strategies + health components
- Updated Badge.tsx labels (R2G/FLAG/FLAT) + colors
- Updated 7 additional UI files with hardcoded strategy maps: AllocationBars, AllocationDonut, PortfolioTreemap, RMultipleHistogram, TradeActivityHeatmap, strategyConfig.ts
- +1 Vitest
- Verdict: CLEAN (no formal review)

**Micro-fix (between S6 and S8):** Updated test assertion in `test_red_to_green.py` to match S7's YAML backtest_summary status change (`not_validated` → `vectorbt_module_ready`).

**Post-review cleanup:** Fixed 4 observations from adversarial review — `reconstruct_state` efficiency (O1), `recent_volumes` deque(maxlen=50) (O2), dead code removal in `bull_flag.py` (O4), unused `Any` import in `vectorbt_pattern.py` (O11).

**Parallelization:** S1∥S2, S3∥S4, S5∥S7 ran in parallel.
**WFE note:** Walk-forward efficiency not evaluated (no historical data available). Option 1 accepted: proceed to paper trading.

**Key decisions:** None (no DEC entries created — all decisions followed established patterns). Reserved range DEC-357–370 unused.
**New deferred items:** DEF-088 (PatternParam structured type for `get_default_params()`, pre-assigned at sprint planning, deferred to Sprint 27).
**Sessions:** 13 (S1, S2, S3, S4, S5, S6, S7, S8, S9, S10, S10f, micro-fix, post-review cleanup)
**Test counts:** pytest 2,815 → 2,925 (+110), Vitest 611 → 620 (+9) = 119 new tests total
**Review verdicts:** S1 CLEAR, S2 CLEAR, S3 CLEAR, S4 CLEAR, S5 CLEAR, S6 CLEAR, S7 CLEAR, S8 CLEAR, S9 CLEAR, S10 CLEAR, S10f CLEAN
**Notes:** First sprint using PatternModule ABC architecture. Three parallel session pairs (S1∥S2, S3∥S4, S5∥S7) enabled by independent module boundaries. No regressions. All 10 review verdicts CLEAR. Strategy count: 4 → 7. New files: 23. Modified files: 20.

---

## Phase Q — BacktestEngine Core (Sprint 27, Mar 22)

### Sprint 27 — BacktestEngine Core (3,010 pytest + 620 Vitest = 3,630 total)
**Date:** Mar 22, 2026
**Scope:** Build a production-code backtesting engine running real ARGUS strategy code against Databento OHLCV-1m historical data via synchronous event dispatch. ≥5x speed over Replay Harness. Backend only, no UI.
**Type:** Feature sprint. **Execution:** Autonomous runner (human-in-the-loop mode).

**Session 1 (S1): SynchronousEventBus + Config**
- Created `argus/core/sync_event_bus.py` — sequential event dispatch, same interface as async EventBus
- Extended `argus/backtest/config.py` — BacktestConfig with strategy_type, symbols, date range, config overrides
- Extended StrategyType enum with `red_to_green`, `bull_flag`, `flat_top_breakout`
- Fixed pre-existing gap: `test_all_strategy_types_present` missing `red_to_green`
- +15 pytest
- Verdict: CLEAR

**Session 2 (S2): HistoricalDataFeed**
- Created `argus/backtest/historical_data_feed.py` — Databento OHLCV-1m download with Parquet cache
- `metadata.get_cost()` pre-validation before download
- Supports XNAS.ITCH + XNYS.TRADES datasets (March 2023 – present)
- +12 pytest
- Verdict: CLEAR

**Session 3 (S3): BacktestEngine Assembly + Strategy Factory**
- Created `argus/backtest/engine.py` — component assembly mirroring ReplayHarness pattern
- Strategy factory creates instances from StrategyType enum with config overrides
- SynchronousEventBus wired to strategies, Risk Manager, Order Manager, SimulatedBroker
- +15 pytest
- Verdict: CLEAR

**Session 4 (S4): Day Loop + Bar-Level Fill Model**
- Multi-day orchestration: iterate trading days, reset daily state, scanner simulation per day
- Bar-level fill model with worst-case-for-longs exit priority: stop > target > time_stop > EOD
- Scanner simulation: gap from prev_close → day_open with filter application
- +17 pytest
- Verdict: CLEAR

**Session 5 (S5): Multi-Day Orchestration + Scanner + CLI**
- Results collection and aggregation across multi-day runs
- CLI entry point: `python -m argus.backtest.engine --symbols ... --start ... --end ... --strategy ...`
- `run()` loads data before `_setup()` so empty runs skip component initialization
- Per-run SQLite database persistence in `data/backtest_runs/`
- +14 pytest
- Verdict: CLEAR

**Session 6 (S6): Walk-Forward Integration + Equivalence Tests**
- Walk-forward `oos_engine` parameter: `"replay"` (default) or `"backtest_engine"`
- Directional equivalence tests (mocked data) validating BacktestEngine produces comparable results
- Speed benchmark infrastructure (real benchmarking deferred to first real run)
- +12 pytest
- Verdict: CLEAR

**Key decisions:** None (no DEC entries created — all implementation followed existing patterns and decisions). Reserved range DEC-357–DEC-365 unused.
**New deferred items:** DEF-089 (in-memory ResultsCollector for parallel sweeps, pre-assigned during planning, deferred to Sprint 32).
**Sessions:** 6 (S1–S6)
**Test counts:** pytest 2,925 → 3,010 (+85), Vitest 620 → 620 (+0)
**Review verdicts:** S1 CLEAR, S2 CLEAR, S3 CLEAR, S4 CLEAR, S5 CLEAR, S6 CLEAR
**AR items:** AR-1 (metadata), AR-2 (limitation docstring), AR-3 (fail-closed cost), AR-4 (oos_engine field)
**Notes:** Clean sprint — all 6 sessions CLEAR, no new DECs, no regressions. BacktestEngine operational with all 7 strategy types supported. Walk-forward integration enables production-code OOS evaluation. New files: 4 (sync_event_bus.py, historical_data_feed.py, engine.py, test files). Modified files: 3 (config.py, walk_forward.py, test files). Directional equivalence validated with mocked data; real equivalence validation deferred to Sprint 21.6 with actual historical data.

---

## Phase R — Backtest Re-Validation (Sprint 21.6, Mar 23)

### Sprint 21.6 — Backtest Re-Validation + Execution Logging (3,051 pytest + 620 Vitest = 3,671 total)
**Date:** Mar 23, 2026
**Scope:** Re-validate all 7 active strategies using BacktestEngine with Databento OHLCV-1m data (DEC-132), and add ExecutionRecord logging to OrderManager for slippage model calibration (DEC-358 §5.1). 4 main sessions + 2 impromptu fix sessions (21.6.1, 21.6.2) + 2 inline fixes.
**Type:** Validation sprint. **Execution:** Human-in-the-loop.

**Session 1 (S1): ExecutionRecord Model + Storage**
- Created `argus/execution/execution_record.py` — `ExecutionRecord` dataclass with 16 fields capturing expected vs actual fill price, slippage metrics, market conditions
- Created `execution_records` table with 4 indexes (symbol, strategy_id, timestamp, order_id)
- Fire-and-forget recording — exceptions logged at WARNING, never disrupt order management
- +14 pytest

**Session 2 (S2): Order Manager Integration**
- Wired ExecutionRecord creation into `OrderManager.on_fill()` for entry fills
- Captures expected_price (from SignalEvent), actual_price (from fill), slippage_bps, market_cap_bucket, avg_daily_volume (placeholder — requires UM reference data)
- bid_ask_spread_bps always None until L1 data available (Standard plan limitation)
- +10 pytest

**Session 3 (S3): Revalidation Harness Script**
- Created `scripts/revalidate_strategy.py` — CLI script running BacktestEngine + walk-forward for each strategy against Databento data
- Produces JSON result files in `data/backtest_runs/validation/`
- +8 pytest

**Human Step: Backtest Execution**
- Ran revalidation script for all 7 strategies against 28-symbol curated universe (2023-04-01 to 2025-03-01)
- Bull Flag validated (Sharpe 2.78, 57.5% WR, PF 1.55)
- 2 strategies zero trades (AfMo, R2G — expected given 28-symbol constraint)
- 4 strategies preliminary results (not production-representative with 28 symbols)

**Session 4 (S4): Results Analysis + YAML Updates + Validation Report**
- Analyzed all 7 validation result JSONs
- Updated all 7 strategy YAML `backtest_summary` sections with Databento-era metrics
- Created comprehensive validation report at `docs/sprints/sprint-21.6/validation-report.md`
- Status categories: `databento_validated` (Bull Flag), `databento_preliminary` (4 strategies), `databento_insufficient_data` (AfMo, R2G)
- +9 pytest

**Sprint 21.6.1 — Impromptu: BacktestEngine Sizing + Data Compat**
- **BacktestEngine position sizing gap:** Strategies emit `share_count=0` since Sprint 24; BacktestEngine wasn't updated to apply legacy sizing. Fixed by adding sizing logic in `_on_candle_event()`.
- **VectorBT file naming mismatch:** HistoricalDataFeed writes `{YYYY-MM}.parquet`, VectorBT expects `{SYMBOL}_{YYYY-MM}.parquet`. Fixed with dual-glob fallback in all 5 `vectorbt_*.py` files.
- **BacktestEngine `symbols=None`:** `_load_data()` treated None as empty list. Fixed with auto-detection from cache directory.

**Sprint 21.6.2 — Impromptu: BacktestEngine Risk Overrides (DEC-359)**
- Production risk limits (min $100 risk, 5% concentration, 20% cash reserve) reject all signals in single-strategy backtests
- Added `risk_overrides` dict to `BacktestEngineConfig` with permissive defaults (DEC-359)
- Applied via `setattr` on Pydantic sub-models in `_load_risk_config()` — BacktestEngine-only path

**Inline fixes:**
- Revalidation script `initial_cash` increased from $100K to $1M for non-binding single-strategy validation
- `compute_metrics` queried `self._config.strategy_id` instead of `self._strategy.strategy_id`, causing zero-trade metric results

**Key decisions:** DEC-359 (BacktestEngine risk overrides for single-strategy backtesting).
**DEC-132 status:** PARTIALLY RESOLVED — pipeline proven end-to-end with Databento OHLCV-1m data; Bull Flag validated; 6 strategies require full-universe re-validation (28-symbol results are preliminary).
**Sessions:** 4 main + 2 impromptu + 2 inline fixes
**Test counts:** pytest 3,010 → 3,051 (+41), Vitest 620 → 620 (+0)
**Review verdicts:** S4 CLEAR (Tier 2 review)
**Notes:** First use of BacktestEngine for real validation. 28-symbol curated universe is not production-representative — strategies dependent on scanner selectivity (ORB, AfMo, R2G) are most affected. Full-universe re-validation (3,000–4,000 symbols) is a prerequisite for completing DEC-132. No parameter changes warranted.

---

## Sprint 25.9 — Operational Resilience Fixes (March 23, 2026)

**Type:** Impromptu (operational fixes)
**Origin:** Dead market session March 23 2026 (`bearish_trending` blocked all strategies) + FMP cache incident (data-destructive checkpoint bug + blocking startup).

**Session 1 (S1): Regime Fixes + Operational Visibility**
- Added `bearish_trending` to all 7 strategies' `allowed_regimes` (DEC-360)
  - 6 strategy files edited; `PatternBasedStrategy.get_market_conditions_filter()` covers both Bull Flag and Flat-Top via inheritance
  - Only `crisis` remains as universal block regime
- Zero-active-strategy WARNING in `Orchestrator._calculate_allocations()` (guarded by `_is_market_hours()`)
- Regime reclassification INFO logging every 6th check (~30 min) via counter-based approach
- "Watching N symbols" display fix: uses `UniverseManager.viable_count` when available, falls back to scanner count
- Startup alert also updated to use Universe Manager count (scope addition — same misleading count sent to notification channels)

**Session 2 (S2): Cache Checkpoint Fix + Trust Cache on Startup**
- B1 (DEC-361): Cache checkpoint merge fix — `fetch_reference_data()` loads existing disk cache at start so checkpoints write union of existing + fresh entries. Prevents data-destructive overwrites during interrupted fetches.
- B2 (DEC-362): Trust-cache-on-startup — `trust_cache_on_startup: true` (default) in `UniverseManagerConfig`. Startup loads cached reference data immediately; background asyncio task refreshes stale entries post-startup with atomic routing table rebuild via `rebuild_after_refresh()`. Follows same task lifecycle pattern as `_regime_task` and `_eval_check_task`. Resolves DEF-063.
- Config: `trust_cache_on_startup` added to `system.yaml` and `system_live.yaml`
- Backward compatible: `trust_cache_on_startup: false` reverts to blocking fetch

**Key decisions:** DEC-360 (bearish_trending for all strategies), DEC-361 (checkpoint merge fix), DEC-362 (trust cache on startup).
**DEF resolved:** DEF-063 (trust cache on startup).
**Sessions:** 2 (both CLEAR verdict)
**Test counts:** pytest 3,051 → 3,071 (+20), Vitest 620 → 620 (+0)
**Review verdicts:** S1 CLEAR, S2 CLEAR
**Notes:** E1 (regime fix) is the single most impactful item — prevents an entire class of dead sessions where `bearish_trending` blocks all strategies. B2 (trust cache) prevents a repeat of the 100-minute blocking startup that missed market open.

---

## Sprint 27.5 — Evaluation Framework (March 23–24, 2026)

**Type:** Planned (DEC-357/DEC-358 amendment adoption)
**Origin:** Phase 6 evaluation infrastructure — universal evaluation framework for all downstream optimization sprints.

**Session 1 (S1): Core Data Models** — CLEAR
- Created `argus/analytics/evaluation.py` (361 lines)
- `MultiObjectiveResult` dataclass: primary metrics + per-regime `RegimeMetrics` + `ConfidenceTier` + WFE + optional execution quality adjustment + placeholder p-value/CI
- `ConfidenceTier` enum: HIGH (50+ trades, 3+ regimes at 15+), MODERATE (30+ trades, 2+ regimes at 10+, or 50+ with insufficient regime coverage), LOW (10–29), ENSEMBLE_ONLY (<10)
- `ComparisonVerdict` enum: DOMINATES, DOMINATED, INCOMPARABLE, INSUFFICIENT_DATA
- `parameter_hash()`: deterministic SHA-256 of sorted JSON config
- `from_backtest_result()` factory: bridges BacktestResult → MultiObjectiveResult
- JSON serialization roundtrip (to_dict/from_dict) with infinity and None handling
- 21 new tests

**Session 2 (S2): Regime Tagging in BacktestEngine** — CLEAR
- Modified `argus/backtest/engine.py`
- `_load_spy_daily_bars()`: reads SPY 1-min Parquet, 3-month lookback margin, resamples to daily OHLCV
- `_compute_regime_tags()`: RegimeClassifier per day, RANGE_BOUND default for insufficient history
- `_compute_regime_metrics()`: per-regime Sharpe/DD/PF/WR/expectancy from dollar P&L
- `to_multi_objective_result()`: async, loads SPY, partitions trades by exit_date, produces MOR
- Falls back to single RANGE_BOUND regime when SPY not in Parquet cache
- 11 new tests

**Session 3 (S3): Individual Comparison API** — CLEAR
- Created `argus/analytics/comparison.py` (347 lines)
- 5 comparison metrics: Sharpe↑, max_drawdown_pct↑, profit_factor↑, win_rate↑, expectancy↑
- `compare(a, b)` → ComparisonVerdict via Pareto dominance
- `pareto_frontier()`: O(n²), filters to HIGH/MODERATE confidence
- `soft_dominance()` with configurable tolerance dict
- `is_regime_robust()`: positive expectancy across minimum regime count
- NaN → INSUFFICIENT_DATA, float('inf') handled natively
- 23 new tests

**Session 4 (S4): Ensemble Evaluation** — CONCERNS_RESOLVED
- Created `argus/analytics/ensemble_evaluation.py` (~650 lines)
- `EnsembleResult`: aggregate portfolio-level MOR + diversification_ratio + tail_correlation + capital_utilization + turnover_rate + per-strategy `MarginalContribution`
- `build_ensemble_result()`, `evaluate_cohort_addition()`, `marginal_contribution()`, `identify_deadweight()`
- Marginal contributions via exact leave-one-out recomputation
- Metric-level approximation documented; trade-level deferred to Sprint 32.5
- CONCERNS: 2 docstring fixes (diversification ratio formula, tail correlation limitation) resolved in-session; 1 accepted limitation (cohort addition key mismatch, Sprint 32.5 scope)
- 22 new tests

**Session 5 (S5): Slippage Model Calibration** — CONCERNS
- Created `argus/analytics/slippage_model.py`
- `StrategySlippageModel` dataclass, `calibrate_slippage_model()` async
- Time-of-day buckets (pre_10am, 10am_2pm, post_2pm ET), size adjustment linear regression
- Confidence tiers: HIGH ≥50, MODERATE ≥20, LOW ≥5, INSUFFICIENT <5
- Atomic JSON persistence (tempfile + rename)
- CONCERNS: pre-existing upstream issue — execution_record.py stores time_of_day in UTC, not ET (DEF-090)
- 8 new tests

**Session 6 (S6): Integration Wiring + E2E Tests** — CLEAR
- Modified `argus/backtest/config.py`: added `slippage_model_path: str | None = None`
- Modified `argus/backtest/engine.py`: slippage model loading in __init__, `_compute_execution_quality_adjustment()` helper
- execution_quality_adjustment: first-order Sharpe impact approximation with $50 avg entry price placeholder
- Graceful FileNotFoundError handling (logs warning, proceeds without model)
- 17 integration tests covering full pipeline roundtrip
- 17 new tests

**Cleanup Session** — CLEAR
- Fix 1 (DEF-090): execution_record.py time_of_day UTC→ET via `.astimezone(_ET)`
- Fix 2: RegimeMetrics.to_dict() return type annotation includes str
- Fix 3: 3 assert isinstance → if not isinstance: raise TypeError in MOR.from_dict()
- Fix 4: Negative infinity serialization roundtrip (4 locations)
- Fix 5: _load_spy_daily_bars async conversion, removed deprecated asyncio.get_event_loop()
- 1 new test (negative infinity roundtrip)

**Key decisions:** None issued — all design decisions pre-specified by DEC-357/DEC-358 amendment adoption. Reserved range DEC-363–DEC-368 not consumed.
**DEF opened:** DEF-090 (execution_record.py UTC/ET mismatch).
**DEF resolved:** DEF-090 (cleanup session).
**Sessions:** 6 main + 1 cleanup (all reviewed)
**Review verdicts:** S1 CLEAR, S2 CLEAR, S3 CLEAR, S4 CONCERNS_RESOLVED, S5 CONCERNS (pre-existing upstream), S6 CLEAR, Cleanup CLEAR
**Test counts:** pytest 3,071 → 3,177 (+106), Vitest 620 → 620 (+0)
**Notes:** First sprint with 3-wide parallelism (S2+S3+S5 after S1). Pure backend infrastructure — no frontend, no API endpoints, no new YAML config. Evaluation framework is the shared currency for Sprints 28, 32.5, 33, 34, 38, 40, 41.

---

## Phase T — Regime Intelligence (Sprint 27.6, Mar 24)

### Sprint 27.6 — Regime Intelligence (3,337 pytest + 631 Vitest = 3,968 total)
**Date:** Mar 24, 2026
**Scope:** Replace single-dimension MarketRegime with multi-dimensional RegimeVector (6 dimensions: trend, volatility, breadth, correlation, sector rotation, intraday character). All from existing data sources at zero additional cost. Config-gated via `regime_intelligence.enabled`. Includes Observatory visualization wiring (impromptu Sprint 27.6.1).
**Type:** Feature sprint. **Execution:** Human-in-the-loop.

**Session 1 (S1): RegimeVector + V2 Shell + Config**
- Created `RegimeVector` frozen dataclass in `core/regime.py` — 6 dimensions with 18 fields + backward-compatible `primary_regime`
- Created `RegimeOperatingConditions` frozen dataclass with `matches_conditions()` API
- Created `RegimeClassifierV2` shell composing V1 with dimension calculators
- Created `config/regime.yaml` with per-dimension enable flags
- Created `RegimeIntelligenceConfig` Pydantic model in `core/config.py`
- Verdict: CLEAR

**Session 2 (S2): BreadthCalculator**
- Created `core/breadth.py` — per-symbol MA tracking, breadth score computation, thrust detection
- Configurable `ma_period`, `thrust_threshold`, `min_symbols`, `min_bars_for_valid`
- Streaming `update(symbol, close)` + batch `compute()` pattern
- Verdict: CLEAR

**Session 3 (S3): MarketCorrelationTracker**
- Created `core/market_correlation.py` — pairwise correlation of top N symbols
- Dispersed/normal/concentrated classification based on configurable thresholds
- Uses cached daily returns data
- Verdict: CLEAR

**Session 4 (S4): SectorRotationAnalyzer**
- Created `core/sector_rotation.py` — FMP sector performance endpoint
- Risk-on/risk-off/mixed/transitioning classification
- Graceful degradation on HTTP 403 (FMP Starter plan limitation)
- Verdict: CLEAR

**Session 5 (S5): IntradayCharacterDetector**
- Created `core/intraday_character.py` — SPY candle analysis
- Opening drive strength, first 30min range ratio, VWAP slope, direction change count
- Character classification: trending/choppy/reversal/breakout
- Configurable classification times (default: 9:35/10:00/10:30 ET)
- Verdict: CONCERNS→RESOLVED (S5-fix confirmed configurability with 2 new tests)

**Session 5-fix: Configurability Fixes**
- Confirmed SPY symbol and 5-bar lookback already configurable in S5 implementation
- Added 2 targeted tests verifying configurability
- S5 verdict upgraded to CONCERNS_RESOLVED
- Verdict: CLEAR

**Session 6 (S6): Integration**
- Wired RegimeClassifierV2 into Orchestrator with `_latest_regime_vector` attribute
- Wired calculators into main.py startup sequence
- Config-gated: falls back to V1 when `regime_intelligence.enabled: false`
- Added `RegimeIntelligenceConfig` to `SystemConfig`
- Verdict: CLEAR (PASS_WITH_NOTES)

**Session 7 (S7): BacktestEngine V2 Integration**
- Added `use_regime_v2: bool` flag on `BacktestEngineConfig`
- BacktestEngine uses RegimeClassifierV2 for regime tagging when flag enabled
- `RegimeOperatingConditions` matching integrated into operating conditions API
- Verdict: CLEAR

**Session 8 (S8): E2E Integration Tests + Cleanup**
- Created comprehensive E2E tests for full regime pipeline
- Cleanup verification tests ensuring no regressions
- Golden fixture test data for regression detection
- Verdict: CLEAR

**Session 9 (S9): Operating Conditions**
- `RegimeOperatingConditions` matching API complete
- Strategy activation gating based on regime regions
- YAML-based operating condition definitions
- Verdict: CLEAR

**Session 10 (S10): Observatory Visualization**
- Frontend `RegimeVitals` component in `SessionVitalsBar`
- `RegimeVectorSummary` TypeScript interface in `types.ts`
- Session vitals bar displays regime dimensions
- Verdict: CLEAR

**Sprint 27.6.1 (Impromptu): Observatory Regime Vector Wiring**
- Added `Orchestrator.latest_regime_vector_summary` property (duck-typed `to_dict()`, no RegimeVector import)
- Wired regime_vector_summary to Observatory REST `/session-summary` endpoint
- Wired regime_vector_summary to Observatory WebSocket push
- All optional — None/null when regime intelligence disabled
- +5 pytest
- Verdict: CLEAR

**Key decisions:** None issued — 0 of reserved DEC-369–378 used. Sprint spec was comprehensive enough that no new architectural decisions arose.
**New deferred items:** DEF-091 (public accessors on V1 RegimeClassifier for V2 access), DEF-092 (unused Protocol types in regime.py), DEF-093 (main.py duplicate orchestrator YAML load + Orchestrator `_latest_regime_vector` typing).
**Sessions:** 12 (S1–S10 + S5-fix + S27.6.1)
**Test counts:** pytest 3,177 → 3,337 (+160), Vitest 620 → 631 (+11) = 171 new tests total
**Review verdicts:** S1 CLEAR, S2 CLEAR, S3 CLEAR, S4 CLEAR, S5 CONCERNS→RESOLVED, S5-fix CLEAR, S6 CLEAR (PASS_WITH_NOTES), S7 CLEAR, S8 CLEAR, S9 CLEAR, S10 CLEAR, S27.6.1 CLEAR
**New files:** 12 (6 impl modules + 6 test files + 1 golden fixture)
**Modified files:** 11 (regime.py, config.py, events.py, orchestrator.py, main.py, engine.py, backtest/config.py, observatory.py route, observatory_ws.py, types.ts, SessionVitalsBar + hooks)
**Notes:** Clean sprint — all 12 sessions CLEAR (S5 resolved in-sprint), no new DECs, no regressions. RegimeVector is the foundation for Sprint 27.7 (Counterfactual Engine) regime tagging and Sprint 28 (Learning Loop) multi-dimensional optimization. All data from existing subscriptions at zero additional cost. Backward-compatible via `primary_regime` field.

---

## Sprint 27.65: Market Session Safety + Operational Fixes (March 24–25, 2026)

**Type:** Impromptu (discovered during March 24 paper trading session)
**Origin:** Real-time log analysis during market session revealed critical Order Manager bug — duplicate flatten orders on time-stop created $2.8M in phantom short positions at IBKR.
**Sessions:** 6 (S1 + S3 parallel, S2 + S5 parallel, S4 → S4.5 sequential)
**Tests:** pytest 3,337 → 3,412 (+75), Vitest 631 → 633 (+2) = 77 new tests
**New DECs:** DEC-363 through DEC-368 (6 decisions)
**New DEF items:** DEF-094 (ORB Scalp time-stop dominance), DEF-095 (submit-before-cancel bracket amendment), DEF-096 (Protocol type for candle store)

**Session S1: Order Management Safety (CRITICAL)**
- `_flatten_pending` guard prevents duplicate flatten orders (DEC-363)
- Graceful shutdown: `cancel_all_orders()` on Broker ABC before disconnect (DEC-364)
- Periodic position reconciliation: 60s async task, warn-only (DEC-365)
- +13 tests
- Verdict: CONCERNS → CONCERNS_RESOLVED (S2 added shutdown ordering test)

**Session S3: Strategy Fixes (parallel with S1)**
- R2G root cause: `prior_close` never populated — zero evaluations for 30+ minutes
- Fix: `initialize_prior_closes()` from UM reference data (zero new API calls)
- Pattern strategy: bar append moved before operating window check (was discarding pre-window candles)
- `backfill_candles()` hook exposed for IntradayCandleStore wiring
- +13 tests
- Verdict: CLEAR

**Session S2: Trade Correctness + Risk Config (parallel with S5)**
- Bracket leg amendment on fill slippage — delta-based recalculation (DEC-366)
- ZD scenario prevented: target was below cost basis due to +$0.28 slippage
- Concurrent position limits optional: 0 = disabled (DEC-367)
- Zero-R signal guard: suppress signals with < $0.01 profit potential
- S1 CONCERNS resolved: shutdown ordering test, typed ReconciliationResult
- +12 tests
- Verdict: CONCERNS → CONCERNS_RESOLVED (S4.5 added R2G guards)

**Session S5: Frontend + Observatory Fixes (parallel with S2)**
- Session Timeline: dynamic via `useStrategies()` hook, all 7 strategies shown
- Observatory Funnel: backend response format aligned with frontend `tiers` type
- FMP 403: downgraded from ERROR to WARNING ("Starter plan" message)
- Performance polling: 30s → 60s for non-critical display data
- DEF-094: ORB Scalp time-stop dominance logged
- +4 pytest + 2 Vitest
- Verdict: CLEAR

**Session S4: IntradayCandleStore + Live P&L**
- IntradayCandleStore: centralized intraday bar accumulator (DEC-368)
- Market bars endpoint: store → DataService → synthetic fallback (3-tier priority)
- Real-time P&L via WebSocket: PositionUpdatedEvent on ticks (1/sec/symbol throttle)
- Account updates via WebSocket: AccountUpdateEvent through event bus (30s poll)
- Pattern strategy backfill wired (set_candle_store + _try_backfill_from_store)
- +16 tests
- Verdict: CONCERNS → CONCERNS_RESOLVED (S4.5 cleaned dead code)

**Session S4.5: Final Integration + Carry-Forward Fixes**
- R2G zero-R guard and concurrent position guard added (defense-in-depth)
- AccountUpdateEvent dead code resolved (Option A: publish via event bus)
- `reduced_confidence` dead code scaffolding removed from pattern_strategy
- DEF-095, DEF-096 logged
- S2 and S4 review artifacts updated to CONCERNS_RESOLVED
- +4 tests
- Verdict: CLEAR

**Key decisions:** DEC-363 (flatten guard), DEC-364 (shutdown cancel), DEC-365 (position reconciliation), DEC-366 (bracket amendment), DEC-367 (optional concurrent limits), DEC-368 (IntradayCandleStore).
**Operational script:** `scripts/ibkr_close_all_positions.py` — emergency position cleanup via IB Gateway.
**Notes:** Most critical impromptu sprint to date. The flatten-pending bug would have been catastrophic in live trading (CNK: 36 duplicate SELL orders × 1,759 shares = 63,324 shares short). Parallelization across 3 tracks reduced calendar time by ~50%. All 6 reviews resolved cleanly. System is now safe for continued paper trading.

---

## Sprint 27.7: Counterfactual Engine (March 25, 2026)

**Type:** Planned (DEC-358, Intelligence Architecture amendment)
**Goal:** Shadow position tracking system for rejected signals — records theoretical outcomes, computes filter accuracy for Learning Loop (Sprint 28), supports shadow-mode strategies.
**Sessions:** 6 (S1 → S2 → S3a → S3b → S4 → S5, strict sequential) + 1 cleanup session
**Tests:** pytest 3,412 → ~3,517 (+105), Vitest 633 (unchanged) = ~105 new tests
**New DECs:** None (reserved range 379–385 unused — all patterns followed established precedent)
**New DEF items:** None

**Session S1: Core Model + Tracker Logic + Shared Fill Model**
- TheoreticalFillModel extracted from BacktestEngine: `FillExitReason` enum, `ExitResult` dataclass, `evaluate_bar_exit()` pure function
- BacktestEngine refactored to call shared fill model (behavior-preserving, 406 backtest tests unchanged)
- CounterfactualPosition frozen dataclass + CounterfactualTracker with IntradayCandleStore backfill
- RejectionStage enum (QUALITY_FILTER, POSITION_SIZER, RISK_MANAGER, SHADOW)
- Named enum `FillExitReason` (not `ExitReason`) to avoid collision with events.py
- +24 tests (10 fill model + 14 counterfactual)
- Verdict: CONCERNS (low) — missing zero-R guard, quality_score falsy check (both fixed in S3b)

**Session S2: CounterfactualStore + Config Layer**
- CounterfactualStore: SQLite in `data/counterfactual.db`, WAL mode, fire-and-forget writes
- CounterfactualConfig Pydantic model wired into SystemConfig
- `config/counterfactual.yaml` with 4 fields (enabled, retention_days, no_data_timeout_seconds, eod_close_time)
- +12 tests
- Verdict: CLEAR

**Session S3a: SignalRejectedEvent + Rejection Publishing**
- SignalRejectedEvent frozen dataclass added to events.py
- Three rejection publish points in `_process_signal()` (quality filter, position sizer, risk manager)
- `_counterfactual_enabled` flag gates all publishing (default False)
- `_capture_regime_snapshot()` DRY helper for regime vector capture
- +12 tests
- Verdict: CLEAR

**Session S3b: Startup Wiring + Event Subscriptions + EOD Task**
- `build_counterfactual_tracker()` factory in startup.py
- Event bus subscriptions: SignalRejectedEvent → tracker handler, CandleEvent → tracker.on_candle
- `_counterfactual_enabled` flipped True after successful init
- EOD close in shutdown sequence + 60s maintenance task (timeout checks during market hours)
- Retention enforcement at boot
- `counterfactual` section added to system.yaml and system_live.yaml
- S1 carry-forward fixes applied: zero-R guard, quality_score check
- +12 tests
- Verdict: APPROVED_WITH_CONCERNS (low — RejectionStage case mismatch bridged with .lower(), fixed in cleanup)

**Session S4: FilterAccuracy + API Endpoint + Integration Tests**
- FilterAccuracyBreakdown/FilterAccuracyReport dataclasses
- `compute_filter_accuracy()` with breakdowns by stage/reason/grade/regime/strategy
- `GET /api/v1/counterfactual/accuracy` (JWT-protected, date range + strategy filters, min sample threshold)
- 5 full lifecycle integration tests (rejection → candle processing → accuracy query)
- +24 tests (13 accuracy + 6 API + 5 integration)
- Verdict: CLEAR

**Session S5: Shadow Strategy Mode**
- `StrategyMode` StrEnum (LIVE/SHADOW) in base_strategy.py
- `mode` field on StrategyConfig (default "live")
- Shadow routing at top of `_process_signal()` — bypasses quality pipeline and risk manager
- All 7 strategy YAML configs updated with explicit `mode: live`
- Shadow + counterfactual disabled = silent drop (no events published)
- +21 tests
- Verdict: CLEAR

**Cleanup Session: Post-Review Fixes**
- 5 low-severity findings addressed: `asyncio.get_running_loop()` migration, RejectionStage case normalization, `Callable` type annotation, `timedelta` import cleanup, config-disabled integration test
- Single commit, no new tests beyond S5 count

---

## Data Infrastructure — Full-Universe Cache Population (March 25–26, 2026)

**Type:** Infrastructure work (not a formal sprint — scripting + background download)
**Origin:** A-series items from data infrastructure spec. A7 investigation confirmed Databento ALL_SYMBOLS downloads at $0 cost, ~6.4 min/month. Full download completed overnight.

**Script:** `scripts/populate_historical_cache.py`
- ALL_SYMBOLS per-month downloads (35 API calls for EQUS.MINI, 59 each for XNAS.ITCH + XNYS.PILLAR)
- Per-month: download → resolve symbology via `request_symbology(client)` → split by symbol → normalize to ARGUS schema → write `{SYMBOL}/{YYYY-MM}.parquet`
- XNYS.PILLAR overlap skipping: symbols already covered by XNAS.ITCH are skipped
- Retry logic (3 attempts with backoff) for streaming errors
- Manifest tracking (`cache_manifest.json`) with per-month metadata
- Resumable: skips months already in manifest
- `--update` mode for monthly incremental downloads

**Results:**
- EQUS.MINI: 35 months (Apr 2023 – Feb 2026), ~11,000 symbols/month
- XNAS.ITCH: 59 months (May 2018 – Mar 2023), ~8,000–12,000 symbols/month
- XNYS.PILLAR: 59 months (May 2018 – Mar 2023), ~500–90 new symbols/month (overlap-skipped ~95%)
- Total: 153 months, 44.73 GB, 24,321 unique symbols
- Cache location: `/Volumes/LaCie/argus-cache` (external drive)
- Download time: ~23 hours (1 streaming error retried successfully, 0 data loss)
- Cost: $0.00

**A-series resolution:**
- A1 (bulk download): ✅ `populate_historical_cache.py`
- A2 (continuous maintenance): `--update` mode built; cron not yet scheduled (DEF-097)
- A3 (download optimization): ✅ Solved — ALL_SYMBOLS eliminates per-symbol API calls
- A4 (storage planning): ✅ External drive, 500 GB free
- A5 (XNAS.ITCH + XNYS.PILLAR): ✅ Included in this download
- A6 (cache integrity): ✅ Manifest + per-file validation
- A7 (rate limits + cost): ✅ Investigation confirmed $0, no rate limit issues

**DEC-132 status:** Data blocker removed. Full-universe re-validation can proceed.

---

## Sprint 27.75: Paper Trading Operational Hardening (March 26, 2026)

**Type:** Impromptu (DISCOVERED during March 25 market session debrief)
**Goal:** Address operational noise from paper trading: log rate-limiting, paper-optimized risk config, frontend display bugs, trades page filter fix.
**Sessions:** 2 (S1: Backend, S2: Frontend)
**Tests:** pytest 3,517 → 3,528 (+11), Vitest 633 → 638 (+5) = +16 new tests
**New DECs:** None (all changes followed established patterns)
**New DEF items:** DEF-098 through DEF-102 (logged in doc-sync)

**Session S1: Backend Log Throttle + Paper Trading Config**
- `ThrottledLogger` utility class (`argus/utils/log_throttle.py`): per-key rate limiting with configurable interval, burst allowance, summary counts
- IBKR error 399/202/10148 log rate-limiting via ThrottledLogger
- Risk Manager rejection log rate-limiting
- Order Manager reconciliation logging consolidated to single WARNING summary + DEBUG detail
- Paper trading config: 10x risk tier reduction in `quality_engine.yaml` + `system_live.yaml`, `consecutive_loss_throttle: 999` in `orchestrator.yaml`, `min_position_risk_dollars: 10` in `risk_limits.yaml`
- +11 pytest tests
- Verdict: CONCERNS (low — config-coupled test assertions, carried to DEF-101)
- **Note:** Implementation prompt specified `system_live.yaml` for orchestrator/risk settings, but config architecture loads from `orchestrator.yaml`/`risk_limits.yaml`. Claude Code correctly placed changes in the right files.

**Session S2: Frontend Suspension Display + Trades Filter Fix**
- StrategyOperationsCard: additive suspension section for circuit-breaker inactive state
- Trades page `limit: 50` → `limit: 250` fix (root cause of stats not updating on period toggle)
- Post-sprint manual fix: operating window "Suspended" condition changed from `!allocation.is_active` to `!allocation.is_active && !isThrottled`
- +5 Vitest tests
- Verdict: CONCERNS (low — operating window condition, fixed post-sprint)

**Notes:** Focused operational hardening sprint. Primary achievement: log noise reduction from hundreds of lines/minute to rate-limited summaries. Paper trading config enables maximum signal generation for data collection while protecting against capital exhaustion. All changes config-gated or paper-trading-specific. DEF-098 through DEF-102 captured from session debrief analysis.

---

## Sprint 27.8: Operational Cleanup + Validation Tooling (March 26, 2026)

**Type:** Impromptu (DISCOVERED during March 25 market session debrief)
**Goal:** Fix ghost position reconciliation (DEF-099), health monitor inconsistency, decouple config-coupled tests (DEF-101), add validation orchestrator script.
**Sessions:** 2 (S1: Backend fixes, S2: Validation script), run in parallel
**Tests:** pytest ~3,528 → ~3,542 (+14), Vitest 638 (unchanged) = +14 new tests
**New DECs:** None (all patterns followed established precedent)
**New DEF items:** None (DEF-099 partially resolved, DEF-101 resolved)

**Session S1: Ghost Position Reconciliation + Health + Config-Coupled Tests**
- `ExitReason.RECONCILIATION` added to events.py
- `reconcile_positions()` made async; config-gated orphan cleanup: when `reconciliation.auto_cleanup_orphans=true` and ARGUS=N/IBKR=0, generates synthetic close records (exit_price=entry_price, P&L=0)
- Bracket exhaustion detection in `on_cancel()`: when t1_target cancelled and all bracket legs None, triggers flatten attempt
- Config wiring: `reconciliation.auto_cleanup_orphans: true` in system_live.yaml, dict-style access in main.py
- Per-strategy health reporting: replaced 7 hardcoded if-blocks with loop checking `strategy.is_active`, reports DEGRADED for regime-filtered strategies
- DEF-101 resolved: `test_engine_sizing.py` reads YAML and asserts match, `test_config.py` uses ordering invariant assertions
- +8 new tests (7 reconciliation + 1 health), 3 rewritten (DEF-101)
- Judgment calls: `reconcile_positions` sync→async (cleanest approach), used `_close_position` (real method name vs spec's `_close_position_and_log`), QualityRiskTiersConfig has no `.c` field (assertions stop at `c_plus`)
- Verdict: CLEAR (2 LOW findings: ordering assertions use >=, maintenance note on position state mutation before _close_position)

**Session S2: Validation Orchestrator Script**
- `scripts/validate_all_strategies.py`: batch validation of all 7 strategies via subprocess calls to revalidate_strategy.py
- Strategy registry with all 7 strategies and appropriate date ranges
- Pareto frontier + pairwise comparison + regime robustness + optional ensemble analysis (--ensemble flag)
- Summary table to stdout, full JSON output with --output flag
- Error handling: individual strategy failures don't abort batch
- Zero production code modifications
- +8 new tests
- Judgment calls: expectancy derived from PF*WR-(1-WR) since JSON lacks direct field, max_drawdown_pct=0.0 (data limitation)
- Verdict: CLEAR (0 findings)

**Notes:** Both sessions run in parallel (zero file overlap). S1 addresses DEF-099 (highest-priority paper trading issue) and DEF-101 (config-coupled tests). S2 provides tooling for the 6-strategy re-validation push (Proposal E from March 25 debrief). Combined: root-cause fix for ghost positions + operational tooling for validation pipeline.

---

## Sprint 27.9: VIX Regime Intelligence (March 26, 2026)

**Type:** Planned
**Goal:** Deliver VIX-based regime intelligence infrastructure — VIX data service, 4 threshold-based RegimeVector dimensions, pipeline integration (briefing, regime history, orchestrator) — so Sprint 28 (Learning Loop) has VIX context from day one.
**Sessions:** 8 (S1a, S1b, S2a, S2b, S2c, S3a, S3b, S4) + 1 micro-fix commit, 0 contingency used
**Tests:** pytest ~3,542 → ~3,610 (+68), Vitest ~638 → ~645 (+7) = +75 new tests
**New DECs:** None (all patterns followed established precedent; reserved range DEC-369–378 unused)
**New DEF items:** DEF-103 (yfinance reliability risk)

**Session S1a: VixRegimeConfig + VIXDataService Skeleton**
- VixRegimeConfig Pydantic model with 3 boundary sub-models (VolRegimeBoundaries, TermStructureBoundaries, VRPBoundaries) and 4 string enums (VolRegimePhase, VolRegimeMomentum, TermStructureRegime, VRPTier)
- VIXDataService skeleton with SQLite persistence (`data/vix_landscape.db`), trust-cache-on-startup, staleness self-disable
- `config/vix_regime.yaml` with all boundary thresholds
- +11 tests
- Verdict: CONCERNS_RESOLVED (enum naming reconciled to match spec)

**Session S1b: yfinance Integration + Derived Metrics**
- yfinance VIX + SPX daily OHLC ingestion with `_flatten_columns()` MultiIndex handler
- 5 derived metrics: vol-of-vol ratio, VIX percentile rank, term structure proxy, realized vol, variance risk premium
- Daily update task, `_fetch_range()` helper for DRY
- `yfinance>=0.2.31,<1` added to pyproject.toml
- +11 tests
- Verdict: CONCERNS_RESOLVED (VRP test coverage gap fixed, `_flatten_columns()` input mutation fixed with df.copy())

**Session S2a: RegimeVector Expansion**
- RegimeVector frozen dataclass expanded from 6 to 11 fields (4 new Optional VIX enum fields + `vix_close: Optional[float]`)
- `matches_conditions()` treats None as match-any for new dimensions
- `to_dict()` / `from_dict()` updated with backward compatibility
- RegimeOperatingConditions expanded with 4 new Optional VIX enum fields
- RegimeHistoryStore migration: `vix_close REAL` column via idempotent ALTER TABLE
- +10 tests
- Verdict: CLEAR

**Session S2b: 4 VIX Calculators + V2 Wiring**
- VolRegimePhaseCalculator, VolRegimeMomentumCalculator, TermStructureRegimeCalculator, VarianceRiskPremiumCalculator in `core/vix_calculators.py`
- All wired into RegimeClassifierV2 via `vix_calculators_enabled` config flag
- All return None gracefully when VIX data unavailable or stale
- `regime_intelligence.vix_calculators_enabled` added to regime.yaml
- +11 tests
- Verdict: CLEAR

**Session S2c: Strategy YAML Match-Any Documentation**
- All 7 strategy YAML configs updated with comment-only documentation for VIX match-any behavior
- No functional changes — match-any is the default when `operating_conditions` block omits VIX fields
- +0 tests (comment-only)
- Verdict: CLEAR

**Session S3a: VIX Server Init + REST Endpoints**
- `GET /api/v1/vix/current` — latest VIX data + all classifications + staleness info
- `GET /api/v1/vix/history?start_date=&end_date=` — historical data with date range filter
- Both JWT-protected, return `{"status": "unavailable"}` when VIX service absent
- Unconditional router registration (simplifies testing; graceful unavailable response)
- `get_history_range()` method added to VIXDataService
- VIXDataService wired into server.py lifespan (start/stop lifecycle)
- +12 tests
- Verdict: CLEAR

**Session S3b: Pipeline Consumer Wiring**
- BriefingGenerator: VIX context section in user message (VIX close, VRP, vol-of-vol, percentile, term structure). Graceful omission when unavailable
- Orchestrator: pre-market INFO logging of VIX context (VIX close, phase, momentum, VRP tier, term structure)
- SetupQualityEngine: FUTURE comment in `_score_regime_alignment()` — dormant until post-Sprint 28
- RegimeHistoryStore: `vix_close` recorded with each entry (nullable)
- +6 tests
- Verdict: CLEAR

**Session S4: Dashboard VIX Widget**
- VixRegimeCard React component: VIX close, VRP tier badge, vol regime phase label, momentum direction arrow
- Hidden when `vix_regime.enabled: false` or data unavailable
- `useVixData` TanStack Query hook with 60s polling
- TypeScript interfaces for VIX API response types
- +7 Vitest tests
- Verdict: CLEAR

**Micro-fix commit:** Added `yfinance>=0.2.31,<1` to pyproject.toml, fixed contango_threshold docstring ("above" → "at or below"), removed dead `vix_update_task` variable from server.py, fixed term structure description.

**Notes:** 8 sessions + micro-fix, zero contingency used. 6 CLEAR verdicts, 2 CONCERNS_RESOLVED (both fixed in-session). Zero new DECs — all implementation followed established patterns (DEC-300 config-gating, DEC-345 separate DB, DEC-362 trust-cache, DEC-277 fail-closed). DEF-103 tracks yfinance reliability as unofficial scraping library (mitigated by SQLite cache + staleness self-disable + FMP fallback option). Sprint delivers VIX context infrastructure so Sprint 28 (Learning Loop V1) can incorporate VIX regime data from day one.

---

## Sprint 27.95: Broker Safety + Overflow Routing (March 26–28, 2026)

**Type:** Impromptu (DISCOVERED during March 26 paper trading session)
**Goal:** Fix reconciliation position-destruction bug (336 of 371 positions destroyed), add dynamic overflow routing to CounterfactualTracker, harden five related order management failure modes from March 26 market session, and clean up carry-forward review findings.
**Sessions:** 8 (S1a, S3a, S1b, S2, S4, S3b, S3c, S5)
**Tests:** pytest ~3,610 → ~3,693 (+83), Vitest 645 → 645 (+0) = +83 new tests
**New DECs:** DEC-369 through DEC-377 (9 decisions)
**New DEF items:** DEF-104 (dual ExitReason enum sync), DEF-105 (reconciliation trades inflate total_trades count)

**Session S1a: Reconciliation Redesign (CRITICAL)**
- `_broker_confirmed` dict tracks positions with confirmed IBKR entry fills — immune to reconciliation (DEC-369)
- `auto_cleanup_unconfirmed: false` default replaces aggressive `auto_cleanup_orphans` (DEC-370)
- Legacy config backward compatibility with 4-branch logic
- +14 tests
- Verdict: CLEAR

**Session S3a: Overflow Infrastructure**
- `OverflowConfig` Pydantic model, `config/overflow.yaml`
- `overflow.enabled` and `overflow.broker_capacity` fields wired into SystemConfig
- `BROKER_OVERFLOW` added to `RejectionStage` enum
- +8 tests
- Verdict: CLEAR

**Session S1b: Trade Logger Reconciliation Fix**
- `RECONCILIATION` added to `models/trading.py:ExitReason` (DEC-371)
- Defensive defaults in `_close_position`: `stop_price=entry_price`, `gross_pnl=0.0` for reconciliation closes
- +5 tests
- Verdict: CLEAR

**Session S2: Order Management Hardening**
- Stop resubmission cap with exponential backoff: `stop_cancel_retry_max=3`, flatten on exhaustion (DEC-372)
- Bracket revision-rejected handling: fresh order on "Revision rejected" cancellation (DEC-373)
- Duplicate fill callback deduplication via `_last_fill_state` + `_fill_order_ids_by_symbol` reverse index (DEC-374)
- +16 tests
- Verdict: CONCERNS_RESOLVED (fill dedup cleanup fixed post-review)

**Session S4: Startup Zombie Cleanup**
- Order-based heuristic: bracket orders present = managed, no orders = zombie (DEC-376)
- `startup.flatten_unknown_positions` config (default true)
- Zero-qty guard for ghost positions
- +10 tests
- Verdict: CONCERNS (non-blocking — `_managed_positions` always empty at startup, fixed with order heuristic)

**Session S3b: Overflow Routing Logic**
- `_check_overflow_routing()` in `_process_signal()`: capacity check after Risk Manager approval
- Publishes `SignalRejectedEvent(BROKER_OVERFLOW)` when at capacity
- Bypassed for `BrokerSource.SIMULATED`
- +12 tests
- Verdict: CLEAR

**Session S3c: Overflow → Counterfactual Integration Tests**
- End-to-end tests: overflow signal → CounterfactualTracker receives → shadow position created
- Config toggle tests: disabled overflow, simulated broker bypass
- +8 tests
- Verdict: CLEAR

**Session S5: Carry-Forward Cleanup**
- Split `stop_retry_max` into connectivity + cancel-event retry configs (DEC-377)
- Restored S4 code overwritten by S3b (git show recovery)
- `getattr()` refactored: direct access for normal path, `getattr` only for reconciliation
- Zero-qty startup zombie guard
- `SignalRejectedEvent.rejection_stage` comment updated with BROKER_OVERFLOW
- +10 tests
- Verdict: CLEAR

**Key decisions:** DEC-369 (broker-confirmed immunity), DEC-370 (warn-only default), DEC-371 (RECONCILIATION ExitReason), DEC-372 (stop retry cap), DEC-373 (revision-rejected handling), DEC-374 (fill dedup), DEC-375 (overflow routing), DEC-376 (startup zombie cleanup), DEC-377 (separate retry configs).
**Review verdicts:** S1a CLEAR, S3a CLEAR, S1b CLEAR, S2 CONCERNS_RESOLVED, S4 CONCERNS (non-blocking), S3b CLEAR, S3c CLEAR, S5 CLEAR
**New source files:** 1 (`config/overflow.yaml`)
**New test files:** 5 (`test_order_manager_reconciliation_redesign.py`, `test_order_manager_hardening.py`, `test_trade_logger_reconciliation.py`, `test_counterfactual_overflow.py`, `test_overflow_routing.py`)
**Notes:** Most impactful broker-safety sprint since Sprint 27.65. The reconciliation redesign (DEC-369/370) prevents the class of bug that destroyed 336 positions on March 26. Overflow routing (DEC-375) preserves learning data that would otherwise be lost to position cap rejection. Five order management failure modes from the March 26 session hardened. System is now substantially safer for continued paper trading.

---

## Sprint 28: Learning Loop V1 (March 28–29, 2026)

**Type:** C (Architecture-Shifting) — adversarial review mandatory
**Goal:** Close the feedback loop between Quality Engine predictions and actual trading outcomes. Build analysis infrastructure, human-approved config proposal pipeline, and Performance page UI.
**Sessions:** 14 (S1, S2a, S2b, S4, S3a, S3b, S5, S6a, S6b, S6c, S6cf-1, S6cf-2, S6cf-3, S6cf-4)
**Tests:** pytest ~3,693 → ~3,837 (+144), Vitest 645 → 680 (+35) = +179 new tests
**New DECs:** None (all design decisions captured in sprint spec + 16 adversarial review amendments; reserved range DEC-378+ not consumed)
**New DEF items:** DEF-106 (assert statements in models.py from_dict), DEF-107 (unused raiseRec destructured variable)
**50 files changed, 11,953 insertions, 17 deletions**

**Session S1: OutcomeCollector + Models**
- OutcomeCollector: read-only queries across trades, counterfactual, quality_history DBs
- OutcomeRecord dataclass with source separation (trade vs counterfactual)
- DataQualityPreamble builder for report context
- LearningLoopConfig Pydantic model + `config/learning_loop.yaml`
- +16 pytest
- Verdict: CLEAR

**Session S2a: WeightAnalyzer**
- Source-separated Spearman correlations per quality dimension
- P-value significance check, normalized positive correlation weight formula
- Per-regime breakdown, zero-variance guards
- max_weight_change_per_cycle guard (±0.10)
- +14 pytest
- Verdict: CLEAR

**Session S2b: ConfigProposalManager**
- Startup-only config application via apply_pending()
- Atomic YAML writes (tempfile + os.rename)
- Cumulative drift guard (max 20% over 30-day window)
- Weight redistribution with sum-to-1.0 invariant
- Proposal supersession
- Config change history persistence
- +18 pytest
- Verdict: CLEAR

**Session S4: LearningStore** (created ahead of S3a for parallel track)
- SQLite persistence in data/learning.db (DEC-345 pattern)
- WAL mode, fire-and-forget, rate-limited warnings
- 3 tables: learning_reports, config_proposals, config_change_history
- Retention enforcement protects APPLIED/REVERTED-referenced reports
- +12 pytest
- Verdict: CLEAR

**Session S3a: ThresholdAnalyzer**
- Counterfactual-only analysis (missed opportunity rate, correct rejection rate)
- Threshold proposal generation (±5 points delta)
- Both raise and lower can fire simultaneously
- +10 pytest
- Verdict: CLEAR

**Session S3b: CorrelationAnalyzer**
- Pairwise Pearson daily P&L correlations
- Trade-source preference, flagged pairs at |corr| ≥ threshold
- Overlap count per pair, excluded strategies tracking
- +11 pytest
- Verdict: CLEAR

**Session S5: LearningService + SessionEndEvent + Auto-Trigger**
- Pipeline orchestrator: collect → analyze → report → persist → supersede → propose
- Concurrent execution guard
- SessionEndEvent published after EOD flatten
- Auto-trigger via Event Bus subscription with zero-trade guard
- Per-strategy StrategyMetricsSummary (Sharpe, win rate, expectancy)
- +18 pytest
- Verdict: CLEAR

**Session S6a: REST API + CLI**
- 8 JWT-protected endpoints (trigger, reports, proposals, approve/dismiss/revert, config-history)
- CLI script: scripts/run_learning_analysis.py (--window-days, --strategy-id, --dry-run)
- +16 pytest
- Verdict: CLEAR

**Session S6b: LearningInsightsPanel + StrategyHealthBands**
- Performance page "Learning" tab (6th tab, lazy-loaded, keyboard shortcut 'l')
- LearningInsightsPanel: weight + threshold recommendation cards with approve/dismiss UX
- StrategyHealthBands: placeholder bands with mock data
- +12 Vitest
- Verdict: CLEAR

**Session S6c: CorrelationMatrix + Dashboard Card**
- CorrelationMatrix: custom SVG heatmap with tooltip
- LearningDashboardCard: pending count, last analysis, data quality
- Responsive 3-column grid on desktop
- +8 Vitest
- Verdict: CLEAR

**Session S6cf-1: Batch Findings + Visual Fixes**
- Fixed critical correlation matrix key delimiter bug (`:` vs `|` — colon conflicts with strategy:strategy pair parsing)
- Replaced ~8 assert isinstance with if/raise in config_proposal_manager.py and learning.py routes
- TypeScript strict null fixes
- +5 Vitest
- Verdict: CONCERNS (2 findings: DEF-106 assert statements in models.py, DEF-107 unused raiseRec — both LOW)

**Session S6cf-2: Trade Overlap Count + Dead Code Cleanup**
- CorrelationMatrix tooltip now shows real overlap count from report data
- Removed dead code and unused imports
- +4 Vitest
- Verdict: CLEAR

**Session S6cf-3: Strategy Health Bands Real Data**
- StrategyHealthBands wired to real per-strategy metrics from learning reports
- Green/amber/red bands based on Sharpe thresholds
- Insufficient data handling
- +4 Vitest
- Verdict: CLEAR

**Session S6cf-4: Final Polish**
- LearningInsightsPanel conflicting signal detection and merged display
- Report selector functionality
- Minor styling fixes
- +2 Vitest
- Verdict: CLEAR

**Adversarial review:** 16 amendments adopted (3 Critical, 4 Significant, 9 Minor). Key amendments: A1 (startup-only application), A2 (cumulative drift guard), A3 (source separation for threshold analysis), A5 (normalized positive correlation weight formula), A9 (atomic YAML writes), A10 (zero-trade guard), A11 (retention protection for referenced reports), A13 (SessionEndEvent auto-trigger), A15 (zero-variance guard).

**Parallelization:** S2a∥S2b parallel, S3a∥S3b parallel, S4 created ahead of S3a (LearningStore needed by both S3a and S3b).

**Key decisions:** None — all design decisions were captured in the sprint spec and its 16 adversarial review amendments. The implementation sessions made no decisions that deviated from the spec.
**Sessions:** 14
**Test counts:** pytest 3,693 → ~3,837 (+144), Vitest 645 → 680 (+35) = 179 new tests total
**Review verdicts:** 12 CLEAR, 2 CONCERNS (S6cf-1: DEF-106/107 both LOW; all resolved)
**New source files:** ~29 production + ~14 test = ~43
**Modified source files:** ~7 production + ~2 frontend pages
**Notes:** First sprint using adversarial review with amendments integrated into implementation prompts. The 16 amendments prevented multiple design flaws (e.g., A1 prevented mid-session config writes, A2 added cumulative drift ceiling, A9 prevented corrupt YAML from partial writes). S6cf-1 discovered and fixed the correlation matrix key delimiter bug (`:` vs `|`) which would have caused runtime failures. ConfigProposalManager is the first ARGUS module that programmatically writes config — startup-only application with atomic writes and drift guard ensures safety.

---

## Sprint Statistics

- **Total sprints:** 30 full + 34 sub-sprints (12.5, 17.5, 18.5, 18.75, 21.5, 21.5.1, 21.6, 21.7, 22.1–22.3, 23.05, 23.1, 23.2, 23.3, 23.5, 23.6, 23.7, 23.8, 23.9, 24.1, 24.5, 25.5, 25.6, 25.7, 25.8, 25.9, 27.5, 27.6, 27.65, 27.7, 27.75, 27.8, 27.9, 27.95)
- **Total sessions:** ~445+ Claude Code sessions
- **Total tests:** ~3,837 pytest + 680 Vitest = ~4,517 total
- **Total decisions:** 377 (DEC-001 through DEC-377)
- **Calendar days (active dev):** ~44 (Feb 14 – Mar 29, 2026)
- **Largest sprint:** 22 (9 implementation + 5 fix + 9 reviews, largest scope)
- **Cleanest sprint:** 23 (11 sessions, 0 regressions, 0 scope gaps requiring follow-up)
- **Most test-dense:** Sprint 22 (286 new tests), Sprint 24 (209 new tests), Sprint 23.2 (188 new tests), Sprint 28 (179 new tests), Sprint 27.6 (171 new tests), Sprint 23 (141 new tests across 23+23.05)
- **Most Vitest-dense:** 21d (119 new Vitest), Sprint 25 (76 new Vitest), Sprint 24 (51 new Vitest), Sprint 28 (35 new Vitest)
- **Crisis sprint:** 8 (VectorBT performance — iterrows() → vectorized, 4 conversations)
- **Most compaction events:** Sprint 22 (Sessions 3a and 3b both compacted, led to DEC-275)
- **Most adversarial amendments:** Sprint 28 (16 amendments: 3 Critical, 4 Significant, 9 Minor)
