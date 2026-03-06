# ARGUS — Sprint History

> Complete record of all sprints from project inception through current state.
> Active development began February 14, 2026. As of March 4, 2026 (~18 calendar days), 21 full sprints + sub-sprints completed.

---

## Timeline Overview

| Phase | Sprints | Dates | Focus |
|-------|---------|-------|-------|
| A — Core Engine | 1–5 | Feb 14–16 | Trading engine foundation + ORB strategy |
| B — Backtesting | 6–11 | Feb 16–17 | Validation toolkit + parameter optimization |
| C — Infrastructure | 12–13 | Feb 21–22 | Databento + IBKR adapters |
| D — Command Center + Strategies | 14–20 | Feb 23–26 | Frontend, Orchestrator, 3 new strategies |
| E — Seven-Page Architecture + Live | 21a–21.5 | Feb 27– | Full UI, live integration |

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

---

## Sprint Statistics

- **Total sprints:** 22 full + 8 sub-sprints (12.5, 17.5, 18.5, 18.75, 21.5, 21.5.1, 21.7)
- **Total sessions:** ~230+ Claude Code sessions
- **Total tests:** 1,959 pytest + 377 Vitest = 2,336 total
- **Total decisions:** 275 (DEC-001 through DEC-275)
- **Calendar days (active dev):** ~22 (Feb 14 – Mar 7, 2026)
- **Largest sprint:** 22 (9 implementation + 5 fix + 9 reviews, largest scope)
- **Cleanest sprint:** 12.5 (1 session, pure refactor)
- **Most test-dense:** Sprint 22 (286 new tests) and 21c (105 new pytest backend)
- **Most Vitest-dense:** 21d (119 new Vitest)
- **Crisis sprint:** 8 (VectorBT performance — iterrows() → vectorized, 4 conversations)
- **Most compaction events:** Sprint 22 (Sessions 3a and 3b both compacted, led to DEC-275)
