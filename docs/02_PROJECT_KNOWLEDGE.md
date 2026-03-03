# ARGUS — Project Knowledge (Claude Context)

> *Paste this into Claude's project instructions. Keep updated as the project evolves. Last updated: March 3, 2026.*

---

## What Is Argus

Argus is a fully automated, AI-enhanced multi-strategy trading intelligence platform with 15+ concurrent pattern types, a contextual AI copilot (Claude), a 7-page desktop/mobile Command Center, and multi-asset support. The system combines rules-based strategy execution with AI-powered setup quality grading, order flow intelligence, NLP catalyst analysis, and dynamic position sizing to achieve performance comparable to top discretionary momentum traders. The user is building this to generate income for his family. He can code in Python. He has trading experience but no prior systematic/algorithmic trading system.

## Current Project State

**Structure:** Two parallel tracks (DEC-079, February 19, 2026). Build Track (system construction) + Validation Track (strategy confidence-building).

**Build Track:** 1710 tests (pytest) + 255 (Vitest). Sprints 1–21d complete. Sprint 21.5 (Live Integration) IN PROGRESS — Blocks A+B complete, Block C (market day) + D (closeout) pending. Sprint 22 (AI Layer MVP) is NEXT after 21.5.
- Phase 1 (Core Engine): ✅ COMPLETE — 362 tests, Feb 14–16
- Phase 2 (Backtesting): ✅ COMPLETE — 542 tests, Feb 16–17
- Sprint 11 (Extended Backtest): ✅ COMPLETE — 35 months, 15 WF windows, WFE=0.56
- Sprint 12 (DatabentoDataService adapter): ✅ COMPLETE — 658 tests, Feb 21. DatabentoDataService (live streaming + reconnection), DataFetcher Databento backend (historical + manifest), DatabentoScanner (V1 watchlist), system integration (DataSource enum + config wiring), shared databento_utils.py (DEC-091).
- Sprint 12.5 (IndicatorEngine extraction): ✅ COMPLETE — 685 tests, Feb 21. IndicatorEngine class shared by all four DataService implementations. DEF-013 resolved (DEC-092).
- Sprint 13 (IBKRBroker adapter): ✅ COMPLETE — 811 tests, Feb 22. IBKRBroker full Broker abstraction via `ib_async` (connection, orders, native brackets DEC-093, fills, reconnection, state reconstruction). IBKRConfig + BrokerSource enum (DEC-094). Order Manager T2 broker-side limit orders. System integration (main.py broker branching, __init__.py exports). DEF-016 logged (Order Manager bracket refactor deferred).
- Sprint 14 (Command Center API): ✅ COMPLETE — 926 tests, Feb 23. FastAPI REST + WebSocket, JWT auth, 7 endpoint groups, PerformanceCalculator, TradeLogger queries, dev mode with mock data, React scaffold.
- Sprint 15 (Command Center Frontend): ✅ COMPLETE — 926 tests (no new backend tests), Feb 23. Four pages: Dashboard, Trade Log, Performance, System. Responsive at 393px/834px/1194px/1512px breakpoints. Lightweight Charts for equity curve and daily P&L histogram. WebSocket real-time updates. Dark theme. Icon sidebar nav (desktop/tablet) + bottom tab bar (mobile). 8 implementation sessions. Full code review passed (DEC-106–110).
- Sprint 16 (Desktop/PWA + UX Polish): ✅ COMPLETE — 942 tests (16 new), Feb 24. Framer Motion page transitions + stagger animations. Skeleton loading (all pages). AnimatedNumber + P&L flash enhancements. SVG Sparklines on dashboard. Chart draw-in animations. Hover feedback (desktop-only). Contextual empty states. Trade detail slide-in panel. PWA (manifest, service worker, icons, iOS meta). CSV trade export. Emergency controls (flatten all, pause all). Strategy pause/resume. Tauri v2 desktop shell. Platform detection utility. 10 implementation sessions. Code review passed (DEC-111–112). Known issue: safe-area-inset padding incomplete on PWA (fix queued).
- Sprint 17 (Orchestrator V1): ✅ COMPLETE — 1146 tests (204 new), Feb 24–25. Orchestrator (pre-market routine, 30-min regime monitoring, intraday throttle, EOD review, decision logging). RegimeClassifier (SPY realized vol as VIX proxy, DEC-113). PerformanceThrottler (consecutive losses/Sharpe/drawdown). CorrelationTracker (infrastructure for V2). Equal-weight allocation V1 (DEC-114). Single-strategy 40% cap (DEC-119). DEF-016 resolved — Order Manager atomic bracket orders (DEC-117). API: 3 orchestrator endpoints + 4 WebSocket event types. UI: SegmentedTab, extended Badge system, AllocationDonut, RiskGauge. 12-phase main.py startup. 13 implementation sessions + Sprint 17.5 polish (4 sessions: encapsulation properties, safe-area padding, animation-once pattern, stable render without conditional skeleton swap). Code review passed.
- Sprint 18 (ORB Scalp Strategy): ✅ COMPLETE — 1299 tests (153 new), Feb 25. OrbBaseStrategy ABC extracted (DEC-120) — shared scanner, gap filter, OR tracking, breakout detection. OrbScalpStrategy (DEC-123): single-target 0.3R exit, 120s hold, per-signal time stop (DEC-122). Cross-strategy risk: ALLOW_ALL duplicate stock policy (DEC-121), Risk Manager ↔ Order Manager reference (DEC-124), CandleEvent routing via EventBus (DEC-125). Sector exposure deferred (DEC-126, DEF-020). VectorBT Scalp sweep: 20,880 trades, all aggregate Sharpes negative — bar resolution insufficient (DEC-127, RSK-026). Walk-forward infrastructure wired for multi-strategy. Strategy spec: `docs/strategies/STRATEGY_ORB_SCALP.md`. 14 multi-strategy integration tests. UX: SessionSummaryCard (after-hours recap), PositionTimeline (Gantt viz with strategy badges). Vitest frontend testing (DEC-130). 12 implementation sessions. Code review passed (DEC-120–127).
- Sprint 18.5 (Post-Review Polish): ✅ COMPLETE — 1313 tests (pytest) + 7 (Vitest), Feb 25. ORB Scalp mock data in dev mode (positions, trades, system status, strategy cards). SessionSummaryCard dev-mode override (DEC-131). Mobile timeline label density fix. Three-way position filter All/Open/Closed (DEC-128). View toggle persistence via Zustand store (DEC-129). 3 integration test gap fills (same-symbol collision, partial allocation exhaustion, throttle isolation). Donut chart legend width fix. Badge contrast fix on amber timeline bars. 7 sessions.
- Sprint 18.75 (CapitalAllocation + Dashboard Polish): ✅ COMPLETE — 1317 tests (pytest) + 14 (Vitest), Feb 25. AllocationDonut renamed to CapitalAllocation (DEC-133). Two views: track-and-fill donut (custom SVG, color-tinted track segments, clockwise fill arcs, sweep animation) and horizontal stacked bars (deployed/available/throttled segments, labels above/below). SegmentedTab toggle with Zustand persistence. MarketRegimeCard added to dashboard (DEC-134). Dashboard second row → 3-card equal grid. Responsive: Market + Market Regime always paired at tablet/phone widths. API enrichment: orchestrator status includes per-strategy deployed_capital, deployed_pct, is_throttled, plus total_deployed_capital and total_equity (DEC-135). Dev mode mock data scaled to realistic positions vs allocations. 4 new orchestrator pytest tests, 7 new Vitest component tests. 8 fix sessions. Code review passed (DEC-133–135).
- Sprint 19 (VWAP Reclaim Strategy): ✅ COMPLETE — 1410 tests (pytest, 93 new) + 40 (Vitest, 26 new), Feb 25–26. VwapReclaimStrategy standalone from BaseStrategy (DEC-136), 5-state machine (DEC-138), pullback swing-low stop (DEC-139), T1=1.0R/T2=2.0R, 30-min time stop. Scanner reuse (DEC-137), position sizing with risk floor (DEC-140), ALLOW_ALL cross-strategy (DEC-141). VectorBT parameter sweep: 59,556 trades, 768 combos, avg Sharpe 3.89, WF OOS Sharpe 1.49, P&L $15,820 (DEC-146, provisional per DEC-132). Precompute+vectorize architecture mandated for all sweeps (DEC-149, `.claude/rules/backtesting.md`). VectorBT ↔ live state machine divergences harmonized (DEC-148). Walk-forward pipeline dispatch for VWAP Reclaim (DEC-145). Watchlist Sidebar: responsive (desktop inline 280px / tablet slide-out / mobile overlay), compact single-letter strategy badges, VWAP distance metric, sort controls, edge-mounted collapse pill (DEC-142, DEC-147, DEC-150). Keyboard shortcuts: 1–4 navigation, w watchlist toggle (DEC-151). Dev mode three-strategy mock data. Strategy spec: `docs/strategies/STRATEGY_VWAP_RECLAIM.md`. 14 implementation sessions + 2 code review checkpoints. Code review passed (DEC-144–151).
- Sprint 20 (Afternoon Momentum): ✅ COMPLETE — 1522 tests (pytest, 112 new) + 48 (Vitest, 8 new), Feb 26. AfternoonMomentumStrategy standalone from BaseStrategy (DEC-152), 5-state machine (DEC-155), consolidation high/low channel + ATR filter (DEC-153), 8 simultaneous entry conditions (DEC-156). Gap watchlist reuse (DEC-154). T1=1.0R/T2=2.0R, dynamic time stop compressed to force_close (DEC-157). Trailing stop deferred (DEC-158, DEF-024). EOD handling (DEC-159). Cross-strategy ALLOW_ALL, time-separated coverage (DEC-160). VectorBT sweep: 1,152 combos, precompute+vectorize (DEC-162). Walk-forward pipeline dispatch. System integration: main.py wiring, Orchestrator registration, per-strategy health components (all 4 strategies). Dev mode four-strategy mock data. 16 four-strategy integration tests. Strategy spec: `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md`. Databento activation deferred to Sprint 21 (DEC-161). 10 implementation sessions + 2 code review checkpoints. Code review passed (DEC-152–162).
- Sprint 21a (Pattern Library Page): ✅ COMPLETE — 1558 tests (pytest, 36 new) + 70 (Vitest, 22 new), Feb 27. Backend: config YAML metadata enrichment (pipeline_stage, family, description_short, time_window_display, backtest_summary on all 4 strategies), Pydantic model updates (BacktestSummaryConfig, StrategyConfig base fields), extended GET /strategies (performance_summary, backtest_summary, metadata), new GET /strategies/{id}/spec (auto-discovered markdown spec sheets with document metadata — title, word count, reading time, last modified; DEC-181), extended GET /performance/{period} with ?strategy_id= filter, new GET /market/{symbol}/bars (synthetic OHLCV for dev). Frontend Pattern Library page: IncubatorPipeline (10-stage horizontal pipeline with counts and click-to-filter, filled accent background for active filter), PatternCardGrid (filterable/sortable), PatternCard (badges, stats, accent border+ring+tint selected state, interactive={!isSelected} to prevent hover flicker), PatternFilters (family, time window, sort), PatternDetail (5 tabs: Overview, Performance, Backtest, Trades, Intelligence). OverviewTab (parameter table + document index with metadata; clicking opens DocumentModal for scrollable full-document reading, DEC-184). PerformanceTab (strategy-filtered equity curve, daily P&L, 6-metric grid with compact chart prop DEC-183). BacktestTab (structured placeholder with walk-forward metrics from config). TradesTab (reuses TradeTable with locked strategy filter). IntelligenceTab (placeholder). Master-detail responsive layout (desktop 35%/65% split, tablet/mobile drill-down). SlideInPanel extraction (DEC-177) — shared animated panel shell used by TradeDetailPanel and SymbolDetailPanel. SymbolDetailPanel — global slide-in (mounted in AppShell) with SymbolChart (Lightweight Charts candlestick + volume), SymbolTradingHistory (summary stats + recent trades), SymbolPositionDetail. Click-anywhere symbol wiring: WatchlistItem, OpenPositions, TradeTable, TradeDetailPanel, Dashboard RecentTrades all open SymbolDetailPanel. Dashboard RecentTrades row click opens TradeDetailPanel. Nav updated to 5 pages. Keyboard shortcuts extended to 1–5 (DEC-180). Pattern Library arrow key navigation: ↑/↓ card navigation, ←/→ tab switching, Escape deselect (DEC-185). Explicit z-index hierarchy (DEC-182). 2 new Zustand stores (patternLibraryUI, symbolDetailUI). 4 new hooks (useStrategySpec, useSymbolBars, useSymbolTrades, useSortedStrategies). DocumentModal component for focused document reading. New route: market.py. 8 implementation sessions + 4 polish sessions. Code review passed (DEC-172–185).
- Sprint 21b (Orchestrator Page): ✅ COMPLETE — 1597 tests (pytest, 39 new) + 100 (Vitest, 30 new), Feb 27. Backend: extended GET /orchestrator/status (session_phase, pre_market status, per-strategy throttle metrics, operating windows, health), throttle override endpoint POST /strategies/{id}/override-throttle with duration + mandatory reason, decisions date filter, Orchestrator.pre_market_complete property, _is_override_active() with time-based expiry. Dev mode: realistic 4-strategy mock data with throttle scenario on ORB Scalp. Frontend: OrchestratorPage with 6 sections — hero row layout (DEC-192: SessionOverview + RegimePanel stacked left, CapitalAllocation donut right), StrategyCoverageTimeline (custom SVG, time-to-pixel mapping, "now" marker, throttled hatching), StrategyOperationsGrid (2-col cards with allocation bars, throttle status, pause/resume), DecisionTimeline (newest-first DEC-194, color-coded severity, connecting lines), GlobalControls (force rebalance, emergency flatten/pause with ConfirmModal). RegimePanel gauge redesign (DEC-195: visual gauge bars for Trend/Vol/Momentum with marker dots, regime badge as hero). SessionPhaseBadge extracted to page header. Strategy config consolidation (DEC-193: shared strategyConfig.ts). ThrottleOverrideDialog (duration dropdown, mandatory reason textarea, amber severity styling). Navigation updated to 6 pages (keyboard shortcuts 1–6, DEC-189). 13 sessions (8 implementation + 1 review + 4 polish). Code review passed (DEC-192–195).
- Sprint 21c (The Debrief Page): ✅ COMPLETE — 1664 tests (pytest, 105 new) + 138 (Vitest, 38 new), Feb 27. Backend: DebriefService (992 lines), 3 DB tables (briefings, journal_entries DEC-196, documents DEC-198), 4 API route files, LIKE search (DEC-200), batch trade fetch (DEC-203). Frontend: DebriefPage with 3-section SegmentedTab. Briefings tab: BriefingList (Pre-Market/EOD creation, 409 Conflict via ApiError DEC-202), BriefingCard, BriefingEditor (side-by-side markdown edit/preview, Ctrl+S, unsaved indicator). Research Library: hybrid filesystem (read-only repo docs) + database (CRUD custom docs) DEC-198, ResearchDocCard, DocumentEditor, TagInput. Journal: JournalList (4-filter dimensions, 300ms debounce), JournalEntryCard (4 typed badges with icons, expand/collapse, inline edit via AnimatePresence), JournalEntryForm (collapsed→expanded inline creation), TradeSearchInput (debounced search, linked trade chips → SymbolDetailPanel, batch fetch DEC-203). Shared TagInput component (autocomplete, keyboard nav). DebriefSkeleton (3 variants). Zustand store. 4 TanStack Query hooks. Navigation: 7 pages complete (DEC-199), keyboard shortcuts 1–7, b/r/j tab switching, n new entry, Escape close. Dev mode: 5 briefings, 3+ docs, 10 journal entries. 10 implementation sessions + 2 code reviews + 1 fix session. Code review passed (DEC-196–203). Resolved: DEF-026, DEF-027.
- Sprint 21d (Dashboard refinement + Performance analytics + System cleanup + AI Copilot shell): ✅ **COMPLETE** — 1712 tests (pytest, 48 new) + 257 (Vitest, 119 new), Feb 27–28. Dashboard: OrchestratorStatusStrip, StrategyDeploymentBar (renamed from HeatStripPortfolioBar, strategy-level capital deployment with accent colors and click navigation, DEC-219), GoalTracker (2-column pace dashboard with avg daily + need/day, DEC-220), 3-card row replacing Market+Regime (MarketStatus merged, TodayStats 2×2 metrics, SessionTimeline SVG with strategy windows + "now" marker, DEC-221), PreMarketLayout (DEC-204, DEC-213, DEC-214), dashboard summary aggregate endpoint (DEC-222), useSummaryData hook disabling pattern (DEC-223). Performance: 5-tab layout with 8 visualizations — TradeActivityHeatmap (D3), CalendarPnlView, RMultipleHistogram (Recharts), RiskWaterfall, PortfolioTreemap (D3), CorrelationMatrix, ComparativePeriodOverlay, TradeReplay (DEC-205–209, DEC-215, DEC-218). Unified diverging color scale (DEC-224), WCAG dynamic text contrast (DEC-225), correlation matrix single-letter labels (DEC-226), desktop side-by-side layouts (DEC-227), tab keyboard shortcuts o/h/d/p/r (DEC-228). Performance Workbench deferred (DEC-229). System: narrowed to infrastructure + IntelligencePlaceholders (DEC-210). Nav: sidebar dividers, mobile 5+More bottom sheet (DEC-211, DEC-216). CopilotPanel shell + CopilotButton + copilotUI store (DEC-212, DEC-217). Backend: 5 new endpoints (heatmap, distribution, correlation, replay, goals) + dashboard summary aggregate, GoalsConfig. 13 implementation sessions + 3 code reviews. Code review passed (DEC-204–229). Deferred: DEF-028 (CalendarPnlView strategy filter), DEC-229 (Performance Workbench).
- Sprint 21.5 (Live Integration): **IN PROGRESS** — 1710 tests (pytest) + 255 (Vitest), Feb 28 – Mar 3 (ongoing). Databento EQUS.MINI live streaming confirmed (DEC-248, supersedes XNAS.ITCH DEC-089). IBKR paper trading via IB Gateway operational (DEC-236). Sessions 1–3: Databento connection, API format discoveries (instrument_id direct attribute DEC-241, built-in symbology_map DEC-242, fixed-point prices DEC-243, historical data lag DEC-244). Sessions 4–6: first live market data streaming (30+ min, CandleEvents across 10 symbols, VWAP Reclaim signal on NFLX — correctly rejected by Risk Manager for concentration limit). Session 7: IBKR paper connection, bracket orders, flatten_all() SMART routing fix (DEC-245). Sessions 8–9: position management lifecycle, state reconstruction, reconnection, get_open_orders() Broker ABC (DEC-246). Session A1: validation scripts (13/13 PASS integration + 4/4 PASS resilience). Sessions B0–B5: scanner resilience for historical data lag (DEC-247, 13 new tests), EQUS.MINI diagnostic (DEC-248), position sizing verification, time stop/EOD validation, operational scripts (`start_live.sh`, `stop_live.sh`), `docs/LIVE_OPERATIONS.md` (418 lines), documentation sync. Orphaned DatabentoSymbolMap deleted (replaced by built-in symbology_map DEC-242). Pending: Block C (full market day validation) + Block D (sprint closeout). DEC-241 through DEC-248.

**Expanded Vision (DEC-163, February 26, 2026):** ARGUS scope expanded from 5-strategy rules-based to 15+ pattern AI-enhanced trading intelligence platform. Core new components: Setup Quality Engine (composite 0–100 scoring), Order Flow Model (Databento L2/L3, DEC-165), NLP Catalyst Pipeline (free sources: SEC EDGAR + Finnhub + FMP + Claude API classification, DEC-164), Dynamic Position Sizer, expanded Pattern Library (15+ types, batch-built DEC-167), Learning Loop, Pre-Market Intelligence Engine. Contextual AI Copilot accessible from every page (DEC-170). Command Center expanded from 4 to 7 pages: Dashboard, Trade Log, Performance, Orchestrator, Pattern Library, The Debrief, System (DEC-169). Sprint 21 split into 21a–21d to establish page architecture (DEC-171). See `docs/research/ARGUS_Expanded_Roadmap.md`.

**Validation Track:** Paper trading ACTIVE with DEC-076 parameters on Alpaca. Validates system stability only — Alpaca IEX data captures only ~2–3% of market volume (DEC-081), so signal accuracy is not validated until Databento data is integrated (Sprint 12). See `08_PAPER_TRADING_GUIDE.md`.

**Infrastructure Research (Feb 18–20):** Two deep-dive research reports completed:
- Market Data: Databento US Equities Standard ($199/mo) selected as primary data backbone (DEC-082). IQFeed supplemental for forex/news/breadth when needed.
- Execution Broker: Interactive Brokers (IBKR Pro, tiered) selected as sole live execution broker (DEC-083). Direct adoption — no phased Alpaca → IBKR migration.
- Full reports: `argus_market_data_research_report.md` and `argus_execution_broker_research_report.md` in project files.

**IBKR Account (Feb 21):** Application submitted. Account ID U24619949. Individual margin account, IBKR Pro tiered pricing. Awaiting approval — paper trading account will be enabled post-approval for Sprint 13 adapter development.

**Next Build sprints:** Live Integration (Sprint 21.5, IN PROGRESS) → Backtest Re-Validation (Sprint 21.6, parallel with 22) → AI Layer MVP (Sprint 22) → NLP Catalyst Pipeline + Pre-Market Engine (Sprint 23) → Setup Quality Engine + Dynamic Position Sizer (Sprint 24, DEC-240) → Red-to-Green + Pattern Library Foundation (Sprint 25) → Pattern Expansion I (Sprint 26) → Short Selling + Parabolic Short (Sprint 27) → Pattern Expansion II (Sprint 28) → Learning Loop V1 (Sprint 29) → Orchestrator V2 AI-Enhanced (Sprint 30) → Pattern Expansion III + Volume Profile (Sprint 31) → Learning Loop V2 ML (Sprint 32+). Order Flow Model V1 and V2 deferred to post-revenue backlog (DEC-238). See `docs/research/ARGUS_Expanded_Roadmap.md`. UX Feature Backlog (`docs/ui/UX_FEATURE_BACKLOG.md`) + DEC-168 (intelligence UI integration) provide per-sprint enhancement add-ons. Databento subscription activation recommended around Sprint 21 (DEC-161). All pre-Databento backtests require re-validation with quality data (DEC-132).

**Validation Track sequence:** Build through Sprint 21d (7-page architecture + analytics) → Sprint 21.5 live integration (Databento + IBKR paper) → activate Databento → IBKR paper trading with quality data (Gate 2, 20+ days, starts during Sprint 21.5) → Sprint 21.6 backtest re-validation (parallel with Sprint 22) → Build through Sprint 25 (intelligence infrastructure — Quality Engine, Catalysts, Pattern Library) → AI-enhanced paper trading with quality scoring (Gate 3, 30+ days) → Build through Sprint 31 (full pattern library + learning loop) → Full system paper trading (Gate 4, 50+ cumulative days, system Sharpe > 2.0) → CPA consultation → live at minimum size on IBKR (Gate 5).

**✅ IBKR ACCOUNT APPROVED:** Account ID: U24619949. Individual margin account, IBKR Pro (tiered pricing). Paper trading account available. IB Gateway setup and live integration testing in Sprint 21.5 (DEC-232, DEC-236).

## Key Decisions Made (Do Not Relitigate)

- **System name:** Argus
- **Language:** Python 3.11+
- **Brokerages:** Broker-agnostic abstraction layer. Interactive Brokers (sole live execution — DEC-083, `ib_async` library). Alpaca (strategy incubator paper testing only — DEC-086). SimulatedBroker (backtesting/shadow system). IBKR covers entire asset class roadmap (stocks, options, futures, forex, crypto) through single account.
- **Data:** Databento US Equities Standard ($199/mo) for all live market data and new historical data (DEC-082). Full universe, no symbol limits, L0–L1 live schemas (EQUS.MINI, confirmed DEC-248), exchange-direct proprietary feeds. Live streaming + ohlcv-1m/ohlcv-1d/trades/tbbo schemas all verified. L2/L3 historical access included (1-month lookback); live L2/L3 streaming requires Plus tier at $1,399/mo (DEC-237). DataService abstraction for future provider swaps. IQFeed supplemental (forex, Benzinga news, breadth indicators) when needed. Alpaca data deprecated for production use (DEC-081/086).
- **IBKR timing:** IBKRBroker adapter in Sprint 13. IBKR is the production execution broker from day one of live trading. No phased migration from Alpaca (DEC-083). Supersedes DEC-003/DEC-031.
- **Backtesting:** Two-layer toolkit — VectorBT (fast parameter sweeps) and custom Replay Harness (ecosystem-level testing using production code). Backtrader dropped (DEC-046) — Replay Harness provides higher fidelity by running actual production code, and VectorBT covers fast parameter exploration.
- **Walk-forward validation:** Mandatory for all parameter optimization. 70/30 in-sample/out-of-sample split minimum. Non-negotiable overfitting defense (DEC-047).
- **UI Platform:** Tauri desktop app + mobile-responsive web app. Single React codebase shared between both.
- **Orchestrator V1:** Rules-based. Designed for AI enhancement in V2+.
- **Claude's role:** Co-captain with full action capability, gated by user approval. Can analyze, recommend, propose changes, generate reports, implement code (via Claude Code). Never bypasses approval system.
- **Asset class priority:** US Stocks → Crypto (via Alpaca) → Forex → Futures
- **Bank/broker visibility:** Read-only integration now, operational (money movement) later
- **Notifications:** Push notifications (app), Email summaries, Telegram/Discord bot
- **Starting capital:** TBD. System designed for $25K–$100K+. Minimum $25K recommended to avoid PDT.
- **Trading direction:** Long only for V1. Short selling evaluated later.
- **Holding duration:** Seconds to hours. All positions closed intraday (for stock strategies).
- **Event Bus:** FIFO per subscriber, monotonic sequence numbers on all events, no priority queues. In-process asyncio only.
- **Trade IDs:** ULIDs (time-sortable, unique) via `python-ulid` for all database primary keys.
- **Risk Manager modifications:** Approve-with-modification for share count reduction and target tightening. Never modify stops or entry. Minimum 0.25R floor on modified positions.
- **Strategy statefulness:** Daily-stateful, session-stateless. State accumulates during market hours, resets between days, reconstructs from DB on mid-day restart.
- **Data delivery:** Event Bus is the sole streaming mechanism. No callback subscription on DataService. Sync query methods retained.
- **Order Manager model:** Event-driven (tick-subscribed for open positions) + 5-second fallback poll + scheduled EOD flatten.
- **IBKR timing:** Broker abstraction from day one, IBKR adapter deferred to Phase 3+. DEC-003 amended.
- **Config validation:** Pydantic BaseModel (not BaseSettings) for all config. YAML → Pydantic flow. DEC-032.
- **Event Bus filtering:** Type-only subscription; filtering happens in handlers, not at bus level. DEC-033.
- **Database access:** aiosqlite for async DB; DatabaseManager owns connection; TradeLogger is sole persistence interface. DEC-034.
- **SimulatedBroker margin:** No margin model in V1. buying_power = cash. Diverges from real brokers. DEC-036.
- **Scanner architecture:** ABC + StaticScanner in Sprint 3. Real AlpacaScanner in Sprint 4. DEC-038.
- **Data Service timeframes:** Multi-timeframe framework, only 1m in Sprint 3. DEC-038.
- **Indicators:** Computed inside Data Service, published as IndicatorEvent. DEC-038.
- **ORB opening range:** Tracked internally by strategy, not shared indicator. DEC-038.
- **Replay data format:** Parquet only. DEC-038.
- **ORB entry:** Market order + chase protection filter. DEC-038.
- **Breakout confirmation:** Candle close > OR high, volume > 1.5x avg, price > VWAP. DEC-038.
- **Alpaca SDK:** alpaca-py (not alpaca-trade-api, which is deprecated). DEC-039/MD-4a-3.
- **Clock injection:** Clock protocol with SystemClock + FixedClock. Scoped to Risk Manager + BaseStrategy. DEF-001 resolved. DEC-039/MD-4a-5.
- **AlpacaDataService streams:** Subscribes to both 1m bar stream (CandleEvents) and trade stream (TickEvents + price cache). DEC-039/MD-4a-1.
- **Bracket orders:** Single T1 take-profit (Alpaca limitation). Order Manager handles T1/T2 split in Sprint 4b. DEC-039/MD-4a-6.
- **External monitoring:** Generic webhook heartbeat (Healthchecks.io default). DEC-045/MD-5-1.
- **Critical alerts:** Webhook POST to Discord/Slack/generic endpoint. DEC-045/MD-5-2.
- **Strategy reconstruction:** Fetch today's historical bars from Alpaca REST on mid-day restart. Skip-day fallback on failure. DEC-045/MD-5-3.
- **Order Manager reconstruction:** Query broker for open positions/orders at startup, rebuild ManagedPosition objects. DEC-045/MD-5-4.
- **Health storage:** In-memory only (ephemeral). DEC-045/MD-5-5.
- **Entry point:** Procedural main() with explicit 10-phase startup sequence. DEC-045/MD-5-6.
- **Backtesting layers (revised):** Two layers — VectorBT (parameter sweeps) + Replay Harness (production code replay). Backtrader dropped. DEC-046.
- **Walk-forward validation:** Mandatory for all parameter optimization. 70/30 IS/OOS split. Walk-forward efficiency > 0.3 required. DEC-047.
- **Scanner simulation (backtest):** Compute gap from prev_close to day_open, apply scanner filters (min_gap_pct, min_price, volume). Fall back to all symbols (with price filter) if zero candidates. DEC-052.
- **Synthetic tick generation:** 4 ticks per bar (O→L→H→C bullish, O→H→L→C bearish). Worst-case-for-longs ordering. Tests actual Order Manager code path. DEC-053.
- **Backtest slippage:** Fixed $0.01/share for V1. Simple, conservative, configurable. DEC-054.
- **BacktestDataService:** Step-driven DataService controlled by ReplayHarness via feed_bar()/publish_tick(). Shares indicator logic with ReplayDataService. DEC-055.
- **Backtest database naming:** data/backtest_runs/{strategy}_{start}_{end}_{timestamp}.db. Same schema as production. DEC-056.
- **Backtrader dropped:** Replay Harness provides higher fidelity by running actual production code. VectorBT covers fast parameter exploration. DEC-046.
- **Walk-forward validation:** Mandatory for all parameter optimization. 70/30 IS/OOS split. Walk-forward efficiency > 0.3 required. DEC-047.
- **VectorBT fallback:** Pure NumPy/Pandas used instead of VectorBT library (numba compatibility issues). Equivalent functionality, 53-second full sweep. DEC-063.
- **VectorBT ATR filter:** Entry pre-computation keyed on (or_minutes, day); ATR ratio filtering applied at runtime in max_range_atr loop. DEC-064.
- **ATR sweep thresholds:** Changed from [2.0, 3.0, 4.0, 5.0, 8.0, 999.0] to [0.3, 0.5, 0.75, 1.0, 1.5, 999.0]. All OR range/ATR ratios in dataset below 2.0 (max 1.74), so old thresholds produced 5 identical buckets. New thresholds show 25%→65%→84%→89%→92%→100% trade count gradient. DEC-065.
- **Walk-forward optimization metric:** Sharpe ratio with min_trades floor (default 20). Parameter sets producing fewer trades than the floor are disqualified. DEC-066.
- **Report format:** HTML-only with interactive Plotly charts. PDF deferred. DEC-067.
- **Report chart library:** Plotly primary, matplotlib fallback. DEC-068.
- **Cross-validation (DEF-009):** `cross_validate_single_symbol()` compares VectorBT vs Replay Harness trade counts. VectorBT >= Replay = PASS. DEC-069.
- **Legacy slow function removal (DEF-010):** `_simulate_trades_for_day_slow()` removed from vectorbt_orb.py after cross-validation confirmed vectorized path is correct. DEC-070.
- **News & Catalyst Intelligence:** Three-tier architecture — Tier 1 (economic/earnings calendar, Phase 3), Tier 2 (news feed + classification, Phase 6), Tier 3 (AI sentiment via Claude API, Phase 6+). Defensive filtering value prioritized over signal generation. No independent trade signals from news in V1. DEC-071.
- **Cross-validation fix (DEC-074):** Three bugs in cross_validate_single_symbol() fixed — CLI hardcoded params, VectorBT silent defaults, symbol filter missing. Walk-forward pipeline was already correct. Revealed ATR calculation divergence: VectorBT uses daily-bar ATR, production uses 1-minute-bar ATR with Wilder smoothing (5–10x ratio difference). `max_range_atr_ratio` from VectorBT sweeps does not transfer to production — must be calibrated separately or disabled. Other 5 sweep parameters transfer cleanly.
- **ATR filter disabled for Phase 3 (DEC-075):** `max_range_atr_ratio` set to 999.0 (disabled). Production ATR uses 1-minute bars (semantically wrong for range filter — should be daily-scale ATR). Building daily ATR infrastructure is premature until paper trading validates the filter is needed. Other 5 sweep parameters transfer cleanly and are unaffected.
- **Phase 3 ORB parameters (DEC-076):** opening_range_minutes=5, max_hold_minutes=15, min_gap_pct=2.0, stop_buffer_pct=0.0, target_r=2.0, max_range_atr_ratio=999.0 (disabled). Walk-forward inconclusive with 11 months — Sprint 11 revalidates with ~3 years.
- **Phase restructure (DEC-077):** Phase 3 = Comprehensive Validation (extended backtest + paper trading). Phase 4 = Live Trading. All subsequent phases shifted +1.
- **earliest_entry fix (DEC-078):** Changed `earliest_entry` from `"09:45"` to `"09:35"` to match 5-minute opening range. Previous value created 10-minute dead zone where breakouts were missed. All backtests used 9:45, so results are conservative.
- **Parallel development tracks (DEC-079):** Linear phase sequencing replaced with Build Track (system construction at development velocity) and Validation Track (strategy confidence-building at calendar speed). Command Center, Orchestrator, AI Layer, and additional strategies built in parallel with paper/live trading validation. Only real capital deployment gates on validation confidence.
- **Command Center delivery (DEC-080):** Single React codebase ships to three surfaces: web app (any browser), Tauri desktop app (system tray, native notifications, auto-launch), and PWA mobile app (iPhone/iPad home screen install). All three operational after Sprint 16. No native iOS app needed — PWA provides sufficient mobile experience for single-user system.
- **IEX data limitation (DEC-081):** Alpaca's free IEX feed captures only 2–3% of US equity volume. Dedicated market data provider required. Historical Alpaca Parquet data (REST/SIP-quality) remains valid for backtesting.
- **Market data architecture (DEC-082):** Databento US Equities Standard ($199/mo) as primary equities data backbone. No symbol limits — full universe in single API call. Exchange-direct proprietary feeds (not SIP). Modern Python async client. IQFeed added later for forex, Benzinga news, breadth indicators. Alpaca retained for execution only (later superseded by DEC-083 for live).
- **Execution broker — direct IBKR adoption (DEC-083):** Interactive Brokers (IBKR Pro, tiered pricing) is the sole live execution broker. IBKRBroker adapter built before any live trading. No phased Alpaca → IBKR migration. SmartRouting, no PFOF, 100% price improvement rate, complete multi-asset coverage, `ib_async` asyncio-native library.
- **Sprint resequencing (DEC-084):** Data adapter (Sprint 12) and broker adapter (Sprint 13) inserted before Command Center. Quality data and production execution are prerequisites for meaningful validation. Command Center shifts to Sprints 14–16.
- **Historical data: Databento source, Parquet cache (DEC-085):** New historical data fetched from Databento, cached locally as Parquet. Existing Alpaca Parquet files retained. VectorBT and Replay Harness continue reading Parquet — provider-agnostic.
- **Alpaca role reduction (DEC-086):** Alpaca permanently reduced to strategy incubator paper testing. All production data via Databento. All live execution via IBKR. No real capital through Alpaca.
- **Databento cost deferral (DEC-087):** Subscription activated when DatabentoDataService adapter is ready for integration testing, not before. Development uses mock data.
- **System identity reframe:** ARGUS is a "strategy research laboratory that also trades live." Data infrastructure must support unlimited symbol access, on-demand historical queries, and 30+ concurrent strategies without artificial constraints. See `argus_market_data_research_report.md` Section 11.
- **Databento threading model (DEC-088):** Callbacks on Databento's reader thread, bridged to asyncio via `call_soon_threadsafe()`. Record class references stored in `start()` to avoid hot-path imports.
- **Default dataset (DEC-089, SUPERSEDED by DEC-248):** Originally XNAS.ITCH. Now EQUS.MINI (consolidated US equities). EQUS.MINI covers all US exchanges in one feed, eliminating need for separate XNAS.ITCH + XNYS.PILLAR subscriptions.
- **DataSource enum for provider selection (DEC-090):** `DataSource` enum in `SystemConfig` with `alpaca`/`databento` variants. main.py Phase 6/7 branches on this to select DataService and Scanner. Config-driven, extensible.
- **Shared Databento normalization utility (DEC-091):** `normalize_databento_df()` extracted to `argus/data/databento_utils.py`. Both DatabentoDataService and DataFetcher call this shared function. Eliminates duplication of ts_event→timestamp, UTC normalization, column selection, sorting.
- **IndicatorEngine extraction (DEC-092):** `IndicatorEngine` class in `argus/data/indicator_engine.py`. All four DataService implementations delegate indicator computation (VWAP, ATR-14, SMA-9/20/50, RVOL) to this shared engine. Resolves DEF-013. 27 new tests, 685 total.
- **Native IBKR bracket orders (DEC-093):** IBKRBroker `place_bracket_order()` supports multi-target brackets (T1+T2) via `parentId` linkage and `transmit` flag. Order Manager T2 support: `t2_order_id` field, broker-side T2 limit orders, `_handle_t2_fill()`, tick-skip when broker-side T2 exists, T2 cancellation in all exit paths. Backward compatible — Alpaca path (t2_order_id=None) tick-monitors T2 unchanged. Current implementation uses individual `place_order()` calls post-fill rather than atomic bracket submission (DEF-016).
- **BrokerSource enum and IBKRConfig (DEC-094):** `BrokerSource` enum (`alpaca`/`ibkr`/`simulated`) in `SystemConfig`. `IBKRConfig` Pydantic model for IB Gateway connection parameters. `main.py` Phase 3 branches on `broker_source`. Mirrors `DataSource` enum pattern (DEC-090).
- **DEF-016 evaluation — defer (DEC-095):** Atomic bracket refactor deferred to Sprint 17+ or limit entry strategies. Scope balloons (SimulatedBroker, AlpacaBroker, test rewrite). Near-zero risk for market-order strategies. Evaluated Sprint 13.5.
- **Sprint resequencing — empowerment MVP (DEC-096):** Orchestrator (Sprint 16) before Desktop/PWA (Sprint 18). VWAP Reclaim (Sprint 19) and Afternoon Momentum (Sprint 20) inserted. CC Analytics & Strategy Lab (Sprint 21). AI Layer MVP (Sprint 22). Tier 1 News deferred to Sprint 23+. Four strategies covering full trading day before capital deployment.
- **Databento activation timing (DEC-097):** Subscription deferred to ~Sprint 19 when new strategies need quality data. Sprints 14–18 use Alpaca data. Saves $400–600. Amends DEC-087.
- **AI Layer model selection (DEC-098):** Claude Opus for all API calls. Separate Anthropic API account (pay-as-you-go, ~$35–50/month). No mixed-model optimization — cost delta negligible vs. capital at risk. Independent of user's Claude Pro subscription.
- **API server lifecycle (DEC-099):** In-process Phase 11. FastAPI + uvicorn in same asyncio loop as trading engine. Standalone `--dev` mode for frontend development.
- **API dependency injection (DEC-100):** AppState dataclass holds all system components. FastAPI Depends() injects into routes.
- **WebSocket event filtering (DEC-101):** Curated event list (13 types). Tick events filtered to open-position symbols only, throttled to configurable interval (default 1s).
- **Authentication (DEC-102):** Single-user JWT with bcrypt password hash. No username. Token via Authorization header (REST) or query param (WebSocket).
- **Monorepo structure (DEC-103):** `argus/api/` (FastAPI server) + `argus/ui/` (React frontend). Single repo, single deploy.
- **Chart libraries (DEC-104):** TradingView Lightweight Charts for all financial time-series (equity curves, P&L histograms, price charts). Recharts for non-time-series visualizations (distributions, heatmaps, comparisons). Both coexist.
- **Responsive breakpoints (DEC-105):** Three tiers — <640px phone (iPhone 16 Pro), 640–1023px tablet (iPad Pro 11" portrait), ≥1024px desktop (iPad landscape + MacBook Pro 16"). Bottom tab bar on phone/tablet, icon sidebar on desktop.
- **UI/UX Feature Backlog (DEC-106):** `docs/ui/UX_FEATURE_BACKLOG.md` is the canonical inventory of all planned UI/UX enhancements. 35 features, 6 sprint groupings (Sprints 16–23+), priority tiers, effort estimates. Derived from design research reviewing Bybit, analytics dashboards, mobile apps, and data visualizations.
- **Sprint 16 UX enhancements (DEC-107):** ~15 hours of UX polish added to Sprint 16 scope: staggered entry animations, chart draw-ins, page transitions (Framer Motion), skeleton loading, number morphing/P&L flash, hover feedback, contextual empty states, dashboard sparklines.
- **Sprint 21 scope defined (DEC-108):** CC Analytics & Strategy Lab = ~80–100 hours. Individual stock detail panel (slide-in), Dashboard V2, trade activity heatmaps, win/loss distribution histogram, portfolio treemap, risk waterfall, trade replay mode, goal tracking. Additional chart libraries for Sprint 21+: D3 (custom viz, sparingly) + Three.js/Plotly 3D (optimization landscape, Sprint 22). Extends DEC-104. Full specs in UX Feature Backlog.
- **Design north star (DEC-109):** "Bloomberg Terminal meets modern fintech." Six principles: information over decoration, ambient awareness, progressive disclosure, motion with purpose (<500ms, never blocks), mobile as primary trading surface, research lab aesthetics.
- **Animation library (DEC-110):** Framer Motion for page transitions and stagger orchestration. CSS transitions for hover and micro-interactions. Lightweight Charts native for chart draw-ins. Budget: <500ms per animation, 60fps, never blocks interaction.
- **Single-strategy allocation cap (DEC-119):** With fewer than 3 active strategies, the `max_allocation_pct` cap (default 40%) leaves deployable capital idle. Accepted as intentional risk reduction. No special-casing for N=1. Cap irrelevant at N≥3 (Sprint 19+). Performance-weighted allocation (Bible §5.2 ±10% shift) deferred to V2.
- **DEF-016 resolution — atomic brackets (DEC-117):** Order Manager refactored to use `place_bracket_order()` for atomic entry+stop+T1+T2 submission. ManagedPosition tracks bracket component IDs (`bracket_stop_order_id`, `bracket_t1_order_id`, `bracket_t2_order_id`). Individual `_submit_*_order()` methods preserved for mid-position modifications (stop-to-breakeven). 8 new edge case tests. Sprint 17.
- **Orchestrator V1 polling model (DEC-118):** Orchestrator runs its own async poll loop (configurable interval, default 60s) rather than subscribing to Event Bus ticks. Simplifies lifecycle — single `start()`/`stop()` interface. PositionClosedEvent subscription for throttle tracking is the only Event Bus hook.
- **OrbBaseStrategy ABC (DEC-120):** Shared base class for ORB family. OrbBreakout and OrbScalpStrategy both inherit scanner logic, gap filtering, OR tracking, breakout detection. Divergence in exit behavior only.
- **ALLOW_ALL duplicate stock policy (DEC-121):** ORB and ORB Scalp can trade the same symbol simultaneously, subject to max_single_stock_pct (5%) exposure cap. Different strategies exploit different phases of the same momentum event.
- **Per-signal time stops (DEC-122):** `time_stop_seconds` field on SignalEvent, carried to ManagedPosition. Scalp uses seconds (30–300s), ORB uses minutes. Global config becomes safety backstop.
- **ORB Scalp trade management (DEC-123):** Single-target exit, 0.3R target, 120s hold, OR midpoint stop. No T1/T2 split — trades too fast for partial exits.
- **Risk Manager ↔ Order Manager reference (DEC-124):** Risk Manager queries Order Manager for cross-strategy position data via `get_managed_positions()`.
- **CandleEvent routing via EventBus (DEC-125):** main.py subscribes to CandleEvent and routes to all active strategies via Orchestrator registry. Replaces single-strategy singleton.
- **Sector exposure deferred (DEC-126):** No sector classification data available. Single-stock cap (5%) provides V1 concentration protection. DEF-020 logged.
- **ORB Scalp backtest limitation (DEC-127):** VectorBT sweep at 1-min resolution is directional guidance only. Default params thesis-driven, not backtest-optimized.
- **Three-way position filter (DEC-128):** All/Open/Closed filter in both Table and Timeline views. Default: Open during market hours, All after hours.
- **Positions UI Zustand store (DEC-129):** View mode and filter persist across responsive layout re-mounts. Session-level only.
- **Vitest frontend testing (DEC-130):** React component tests via Vitest. 7 PositionTimeline tests. Establishes frontend testing pattern.
- **SessionSummaryCard dev override (DEC-131):** Dev mode bypasses market status gate for testability.
- **Pre-Databento re-validation milestone (DEC-132):** All parameter optimization is provisional until re-validated with Databento exchange-direct data.
- **CapitalAllocation visual design (DEC-133):** Track-and-fill donut (custom SVG with color-tinted track arcs + bright clockwise fill arcs) plus horizontal stacked bars, toggled via SegmentedTab. Zustand view persistence. Replaces nested two-ring donut (too visually noisy).
- **Dashboard 3-card second row (DEC-134):** CapitalAllocation + Risk Budget + Market Regime at equal widths. Market and Market Regime cards pair at tablet/phone breakpoints (always 2-column, never stack to single).
- **Orchestrator deployment state API (DEC-135):** `GET /api/v1/orchestrator/status` enriched with per-strategy deployed_capital, deployed_pct, is_throttled, plus total_deployed_capital and total_equity.
- **Watchlist UX polish — sparklines removed (DEC-150):** Sparklines removed from watchlist items (unreadable at sidebar width). Replaced with `vwap_distance_pct` metric ("Below ↓0.3%") — most actionable for VWAP Reclaim window. Single-letter strategy badges (O/S/V), green left border for entered positions, edge-mounted collapse pill.
- **Keyboard shortcuts (DEC-151):** Global hotkeys — `1`–`4` page navigation (Dashboard, Trades, Performance, System), `w` watchlist toggle. Suppressed in input/textarea.
- **VectorBT performance rule (DEC-149):** `.claude/rules/backtesting.md` mandates precompute+vectorize architecture for all VectorBT sweeps. 29-symbol 35-month sweep must complete in <30s.
- **VectorBT VWAP Reclaim sweep architecture (DEC-144):** Precompute entries per day, vectorized exit detection. ~500x speedup vs naive per-combination loops.
- **Walk-forward VWAP Reclaim dispatch (DEC-145):** IS=VectorBT sweep, OOS=Replay Harness. Param mapping: volume_multiplier→volume_confirmation_multiplier, target_r→target_1_r, time_stop_bars→time_stop_minutes.
- **VWAP Reclaim backtest results provisional (DEC-146):** 59,556 trades, avg Sharpe 3.89, WF OOS Sharpe 1.49. Provisional per DEC-132 (Alpaca SIP data, not Databento exchange-direct).
- **Watchlist Sidebar responsive architecture (DEC-147):** Desktop ≥1024px: 280px collapsible inline sidebar. Tablet 640–1023px: slide-out panel. Mobile <640px: full-screen overlay. Zustand state, 10s TanStack Query polling.
- **VectorBT ↔ live state machine divergences (DEC-148):** ABOVE→BELOW transition harmonized to `<=` in both VectorBT and live strategy. VectorBT single entry per day vs live retry documented (conservative direction).
- **Afternoon Momentum — standalone from BaseStrategy (DEC-152):** Inherits directly from BaseStrategy, not from a shared consolidation base class. Extraction deferred (DEF-025) until a second consolidation-based strategy is designed.
- **Consolidation detection — high/low channel + ATR filter (DEC-153):** Range = midday_high - midday_low. Consolidation confirmed when range/ATR-14 < consolidation_atr_ratio (default 0.75) AND bars >= min_consolidation_bars (default 30). Rejected when range/ATR-14 > max_consolidation_atr_ratio (default 2.0).
- **Afternoon Momentum scanner — gap watchlist reuse (DEC-154):** Shares the same gap scanner as ORB family. No separate scanner needed.
- **Afternoon Momentum state machine — 5 states (DEC-155):** WATCHING → ACCUMULATING → CONSOLIDATED → ENTERED (terminal) or REJECTED (terminal). Range continues updating through CONSOLIDATED state.
- **Afternoon Momentum entry conditions — 8 simultaneous requirements (DEC-156):** State=CONSOLIDATED, within 2:00–3:30 PM, candle close > consolidation_high, volume >= multiplier × avg, chase protection, valid risk, internal limits, position count.
- **Afternoon Momentum stop and target design (DEC-157):** Stop at consolidation_low × (1 - stop_buffer_pct). T1=1.0R (50%), T2=2.0R (50%). Dynamic time stop = min(max_hold_minutes, seconds until force_close_time). Stop-to-breakeven after T1.
- **Trailing stop deferred to V2 (DEC-158):** T1/T2 fixed targets proven across all four strategies. Trailing stop adds complexity only if data shows clear benefit. DEF-024.
- **Afternoon Momentum EOD handling (DEC-159):** Force close at 3:45 PM ET. Order Manager EOD flatten is safety net.
- **Cross-strategy interaction — ALLOW_ALL, time-separated (DEC-160):** ORB 9:35–11:30, VWAP 10:00–12:00, Afternoon 2:00–3:30. Same symbol can be held by multiple strategies simultaneously. max_single_stock_pct (5%) enforced across all strategies.
- **Databento activation deferred to Sprint 21 (DEC-161):** Saves one additional month. Amends DEC-143.
- **VectorBT Afternoon Momentum divergences harmonized (DEC-162):** Precompute+vectorize architecture. ATR method divergence documented (SMA vs Wilder's). Single entry per day in VectorBT vs live retry (conservative).
- **Expanded vision — AI-enhanced platform (DEC-163):** ARGUS expanded from 5-strategy rules-based to 15+ pattern AI-enhanced. Setup Quality Engine, Order Flow Model, NLP Catalyst Pipeline, Dynamic Position Sizer, Pattern Library, Learning Loop, Pre-Market Intelligence Engine. Target 5–10%+ monthly returns at $100K–$500K scale.
- **Catalyst data — free sources first (DEC-164):** SEC EDGAR + Finnhub + FMP for V1. Claude API classifies/scores catalysts. Benzinga Pro deferred until free sources prove insufficient (>30% unclassified rate over 20 days).
- **L2 data for all watchlist symbols (DEC-165, SUPERSEDED by DEC-237):** Databento MBP-10 planned for watchlist symbols. Live L2/L3 requires Plus tier ($1,399/mo), not included in Standard. Order Flow Model deferred to post-revenue (DEC-238).
- **Short selling in Sprint 27 (DEC-166, amended by DEC-238/DEC-240):** Long-only proven first. Parabolic Short first short strategy. Locate/borrow tracking, inverted risk logic. Decoupled from Order Flow V2 — uses L1 signals only.
- **Pattern library batch build (DEC-167):** 3–4 patterns per sprint, stages 1–3 within sprint, paper validation in parallel.
- **UI/UX integration principle (DEC-168):** Intelligence features enrich existing pages, not siloed. Progressive disclosure: badge → breakdown → deep dive.
- **Seven-page architecture (DEC-169):** Dashboard, Trade Log, Performance, Orchestrator, Pattern Library, The Debrief, System. **7 of 7 built** (all complete — Sprint 21c). Desktop icon sidebar grouped by concern. Mobile 7-tab with abbreviated labels (DEC-199).
- **Contextual AI Copilot (DEC-170):** Claude accessible from every page via persistent slide-out chat panel. Context-aware: automatically receives page context, selected entities, visible data. Chat history lives in The Debrief. Can propose actions through approval workflow. Keyboard shortcut `c`.
- **Sprint 21 split (DEC-171):** Four sub-sprints: 21a (Pattern Library page), 21b (Orchestrator page), 21c (The Debrief), 21d (Dashboard + Performance + System + Copilot shell + nav).
- **Orchestrator hero row layout (DEC-192):** 2-column hero row — SessionOverview + RegimePanel stacked left, CapitalAllocation donut right. Three key questions above the fold.
- **Strategy display config consolidation (DEC-193):** Shared `strategyConfig.ts` with `STRATEGY_DISPLAY` record. All components import from single source. Tailwind classes as full static strings for purge compatibility.
- **Decision Log newest-first (DEC-194):** Operational dashboard shows latest events first. Chronological order reserved for The Debrief page.
- **Regime gauge redesign (DEC-195):** Visual gauge bars (Trend/Vol/Momentum) with marker dots on gradient. Session phase badge moved to page header. Regime badge as hero element.
- **ApiError class for HTTP status preservation (DEC-202):** Custom `ApiError` class in `client.ts` throws with `status` property. All `fetchWithAuth` errors throw `ApiError(message, status)`. Enables status-specific error handling (e.g., 409 Conflict in BriefingList).
- **Batch trade fetch endpoint (DEC-203):** `GET /api/v1/trades/batch?ids=<ULIDs>` with 50 ID limit. Replaces client-side filtering of last 100 trades. Ensures linked trade chips always resolve regardless of age.
- **Dashboard scope refinement (DEC-204):** Dashboard narrows to ambient awareness. OrchestratorStatusStrip replaces CapitalAllocation/RiskGauge/emergency controls (migrated to Orchestrator).
- **Performance analytics expansion (DEC-205):** 5-tab layout with 8 visualizations. Tabs: Overview, Heatmaps, Distribution, Portfolio, Replay.
- **Chart library assignments (DEC-215):** D3 modules (scale, color, hierarchy, interpolate) for heatmap/treemap/correlation. Recharts for histogram. Custom SVG for calendar/waterfall. Lightweight Charts for replay/overlay. Extends DEC-104.
- **Mobile primary tabs (DEC-216):** Dashboard, Trades, Orchestrator, Patterns, More. Performance/Debrief/System in More bottom sheet. Amends DEC-199.
- **AI Copilot shell (DEC-212):** CopilotPanel (new component, not SlideInPanel reuse), CopilotButton, copilotUI store. Persists across pages. Sprint 22 activates.
- **Pre-market Dashboard layout (DEC-213):** Full shell with placeholder cards, time-gated. Sprint 23 wires data.
- **Goal tracking (DEC-214):** monthly_target_usd in GoalsConfig. Simple config for V1.
- **Navigation restructure (DEC-211):** Sidebar group dividers, mobile 5+More bottom sheet. Amends DEC-199.
- **StrategyDeploymentBar (DEC-219):** Redesigned from per-position P&L heat to per-strategy capital deployment. Strategy accent colors, letter+dollar labels, click navigates to Pattern Library (strategy pre-selected) or Orchestrator (Available segment). Replaces HeatStripPortfolioBar.
- **GoalTracker pace dashboard (DEC-220):** "MONTHLY GOAL" header, 2-column layout with avg daily P&L and need/day stats. Pace: ahead >110%, on_pace 90–110%, behind <90%. Color-coded green/amber/red.
- **Dashboard 3-card row (DEC-221):** Merged Market + Market Regime into single MarketStatus card. Added TodayStats (2×2 metrics) and SessionTimeline (SVG strategy windows + "now" marker, click → Orchestrator). Equal 1/3 width on desktop/tablet.
- **Dashboard aggregate endpoint (DEC-222):** `GET /api/v1/dashboard/summary` returns all card data in single response. 5s polling, keepPreviousData prevents skeleton flash. Individual hooks retained for other pages.
- **useSummaryData hook disabling pattern (DEC-223):** Components accept `useSummaryData` boolean prop, passing `enabled: false` to internal hooks. Renders structure with placeholders instead of skeletons while waiting for parent data. usePerformance, useTrades, useGoals extended with optional `{ enabled }` param.
- **Unified diverging color scale (DEC-224):** Single shared `colorScales.ts` for all charts encoding profit/loss. Zero=neutral gray, negatives=red/orange, positives=green. Applied to TradeActivityHeatmap, CalendarPnlView, PortfolioTreemap.
- **Dynamic text color for data-driven backgrounds (DEC-225):** Shared `getContrastTextColor()` utility computes WCAG luminance and flips text white↔dark. Applied to heatmap, calendar, treemap, correlation matrix.
- **Correlation matrix strategy labels (DEC-226):** Single-letter badges from `STRATEGY_DISPLAY` (O/S/V/A) with hover tooltips. Replaces meaningless last-4-character labels.
- **Performance desktop layout density (DEC-227):** Distribution tab: RMultipleHistogram + RiskWaterfall side-by-side (50/50). Portfolio tab: PortfolioTreemap + CorrelationMatrix side-by-side (60/40). Stack on mobile.
- **Performance tab keyboard shortcuts (DEC-228):** `o` (Overview), `h` (Heatmaps), `d` (Distribution), `p` (Portfolio), `r` (Replay). Suppressed during input focus. Extends DEC-199.
- **Performance Workbench deferred (DEC-229):** Customizable widget grid via `react-grid-layout`. Stage 1: rearrangeable widgets within tabs. Stage 2: widget palette + custom tab CRUD. Backend layout persistence. Estimated 11–14 sessions. Supersedes DEC-218.
- **Separate live config (DEC-231):** `config/system_live.yaml` for Databento + IBKR. `config/system.yaml` retained as Alpaca incubator config. `--config` CLI flag selects which to use.
- **IB Gateway not TWS (DEC-232):** IB Gateway (headless) for all IBKR API connections. Lower resource usage, Docker-friendly. TWS available as fallback.
- **All strategies from first live session (DEC-233):** No incremental activation. Sessions 4-5 pre-validate all strategies with real data. Session 11 goes live with all four active.
- **Databento datasets phased (DEC-234, AMENDED by DEC-248):** Originally XNAS.ITCH first, then XNYS.PILLAR. Now using EQUS.MINI as single consolidated dataset covering all US exchanges. No multi-dataset management needed.
- **Backtest re-validation separate (DEC-235):** DEC-132 re-validation is Sprint 21.6, runs parallel with Sprint 22 (AI Layer). Spec drafted after Sprint 21.5 completion.
- **IBKR approved (DEC-236):** Account U24619949 approved. Paper trading available for Sprint 21.5.
- **Databento Standard does NOT include live L2/L3 (DEC-237):** Standard plan ($199/mo) provides live L0+L1 only (EQUS.MINI). Live L2 (MBP-10) and L3 (MBO) require Plus tier ($1,399/mo). Historical L2/L3 included in Standard (1-month lookback). Supersedes DEC-165.
- **Order Flow Model deferred to post-revenue (DEC-238):** Order Flow V1 (was Sprint 24) and V2 (was part of Sprint 28) moved to post-revenue backlog. All strategies and intelligence layer operate on L1 data. Order Flow is an edge enhancement, not a foundation. Scheduled when trading income justifies Plus tier upgrade.
- **Setup Quality Engine 5 dimensions in V1 (DEC-239):** Order Flow removed from V1 scoring. Weights: Pattern Strength 30%, Catalyst Quality 25%, Volume Profile 20%, Historical Match 15%, Regime Alignment 10%. 6th dimension (Order Flow) added post-revenue with full rebalance.
- **Sprint roadmap renumbered (DEC-240):** Old Sprints 25–32 renumbered to 24–31 after Order Flow removal. Short selling (was Sprint 28) decoupled from OF V2, now standalone Sprint 27. Post-revenue backlog created for Order Flow V1, V2, and Quality Engine 6th dimension.
- **Databento API format discoveries (DEC-241/242/243):** instrument_id is direct attribute (not nested in header), symbol resolution uses library's built-in `symbology_map` (custom DatabentoSymbolMap deleted), prices are fixed-point format scaled by 1e9.
- **Databento historical data ~15-minute lag for intraday (DEC-244):** Warmup end time uses 20-minute buffer. Separate from daily bar lag which can be multi-day (DEC-247).
- **flatten_all() SMART routing (DEC-245):** Must use `get_stock_contract()` for SMART routing, not position's fill contract directly (retains execution exchange, triggers IBKR error 10311).
- **get_open_orders() Broker ABC (DEC-246):** Added as abstract method to Broker ABC. Implemented in IBKRBroker, AlpacaBroker, SimulatedBroker. Required for Order Manager state reconstruction and Health Monitor.
- **Scanner resilience for historical data lag (DEC-247):** DatabentoScanner gracefully handles 422 errors from Databento historical API via retry with adjusted date range. Falls back to static watchlist if retry fails. Handles multi-day lag over weekends.
- **EQUS.MINI confirmed as production dataset (DEC-248):** Live streaming verified on Standard plan. All required schemas available (ohlcv-1m, ohlcv-1d, trades, tbbo). Multi-symbol queries functional. Supersedes DEC-089 (XNAS.ITCH default). Amends DEC-234 (replaces XNAS.ITCH + XNYS.PILLAR phased approach — EQUS.MINI covers all US exchanges in one feed).


## Architecture Summary

Three-tier system:
1. **Trading Engine** (Project A, build first): Strategies, Orchestrator, Risk Manager, Data Service, Broker abstraction, Execution layer, Trade Logger, Backtesting toolkit
2. **Command Center** (Project B): Tauri desktop + mobile web, dashboards, human-in-the-loop controls, accounting, reports, Strategy Lab, Learning Journal
3. **AI Layer** (Project C): Claude API integration, approval workflow, report narration, analysis, Claude Code integration

Key components:
- **Strategies** are daily-stateful, session-stateless modular plugins implementing a base interface (state accumulates during market hours, resets between days, reconstructs from DB on restart)
- **Orchestrator** manages capital allocation, strategy activation, performance throttling
- **Risk Manager** gates every order at three levels: strategy, cross-strategy, account
- **Data Service** is the single source of market data via Event Bus. Primary: DatabentoDataService (live equities, DEC-082). Supplemental: IQFeedDataService (forex/news/breadth, future). Legacy: AlpacaDataService (incubator only, DEC-086). Backtest: ReplayDataService, BacktestDataService.
- **Broker Abstraction** routes orders to correct broker. Live: IBKRBroker (IBKR Pro via `ib_async`, DEC-083). Incubator: AlpacaBroker. Backtest: SimulatedBroker.
- **Replay Harness** feeds historical Parquet data through production code for ecosystem-level backtesting
- **Shadow System** runs paper trading permanently in parallel with live trading
- **Control endpoints (DEC-111):** Strategy pause/resume, position close, emergency flatten all, emergency pause all. JWT-gated. Confirmation modals for emergency actions.
- **CSV trade export (DEC-112):** GET /trades/export/csv with filters. StreamingResponse, date-stamped filename. 10K row limit.
- **Setup Quality Engine** scores every potential trade 0–100 on six dimensions (pattern strength, catalyst quality, order flow, volume profile, historical match, regime alignment). Outputs quality grade (A+ through C-) driving dynamic position sizing.
- **Order Flow Model** (POST-REVENUE, DEC-238) will process Databento L2 (MBP-10) depth data: bid/ask imbalance, ask thinning, tape speed, bid stacking signals for entry confidence. Requires Databento Plus tier ($1,399/mo, DEC-237). Historical L2 available on Standard for backtesting.
- **NLP Catalyst Pipeline** ingests SEC EDGAR filings, Finnhub news, FMP calendars; classifies and scores catalyst quality via Claude API (DEC-164).
- **Dynamic Position Sizer** maps quality grades to risk tiers: A+ = 2–3% risk, B = 0.5–0.75%, C- = skip. Replaces fixed risk_per_trade_pct.
- **Pre-Market Intelligence Engine** runs automated 4:00 AM → 9:25 AM pipeline: gap scanning, catalyst research, watchlist ranking, quality pre-scoring, briefing delivery.
- **Learning Loop** correlates quality scores with trade outcomes, refining scoring weights weekly (V1 statistical, V2 ML).
- **Pattern Library** provides 15+ pattern recognition modules each implementing BaseStrategy.
- **AI Copilot** (DEC-170) provides contextual Claude chat from every page via slide-out panel. Context-aware with page state injection. Actions go through approval workflow.
- **Strategy metadata in config YAML (DEC-172):** pipeline_stage, family, description_short, time_window_display, backtest_summary added to base StrategyConfig. All 4 strategy YAMLs updated. Config-driven, not code-derived.
- **Pipeline stage in config YAML (DEC-173):** Pipeline stage is a config property, not derived from system state. Enables manual override and offline strategies.
- **Strategy family classification (DEC-174):** Family field in YAML (orb_family, mean_reversion, momentum, etc.). Stable identifiers in config, flexible display labels in UI.
- **Strategy spec sheets served as markdown (DEC-175):** GET /strategies/{id}/spec returns raw markdown. Frontend renders with react-markdown + remark-gfm. Server reads from docs/strategies/.
- **Backtest tab as structured placeholder (DEC-176):** BacktestTab shows summary metrics from config YAML (status, WFE, OOS Sharpe, trade count, data months). Interactive explorer deferred to Sprint 21d.
- **SlideInPanel extraction + Symbol Detail architecture (DEC-177):** SlideInPanel is shared animated panel shell. SymbolDetailPanel is global (mounted in AppShell, driven by Zustand store). Click any symbol anywhere → SymbolDetailPanel opens.
- **Fundamentals section deferred to Sprint 23 (DEC-178):** No fundamentals data source yet. Placeholder in SymbolDetailPanel.
- **Incubator Pipeline responsive design (DEC-179):** Desktop/tablet: horizontal flex with chevrons. Mobile: horizontal scrollable pills.
- **Keyboard shortcuts (DEC-199):** Global hotkeys — `1`–`7` page navigation, `w` watchlist toggle, `c` copilot (future). Debrief page: `b`/`r`/`j` tab switching, `n` new entry, Escape close. Amends DEC-189, DEC-180, DEC-151.
- **Auto-discover strategy spec sheets (DEC-181):** Convention-based resolution (strat_X → STRATEGY_X.md) replaces hardcoded map. Scales to 15+ strategies without code changes.
- **Z-index layering hierarchy (DEC-182):** MobileNav/EmergencyControls z-50, SlideInPanel z-50/z-40, Sidebar z-40, WatchlistSidebar mobile z-40. Explicit stacking prevents overlap.
- **Compact chart prop pattern (DEC-183):** EquityCurve and DailyPnlChart accept compact boolean for reduced padding/height. Replaces fragile CSS child-selector overrides.
- **Strategy documentation modal reader (DEC-184):** Spec sheets shown as clickable document index (title, word count, reading time, last modified). Full content in scrollable DocumentModal. Replaces inline rendering that overwhelmed the page. List structure supports future document types per strategy.
- **Arrow key navigation in Pattern Library (DEC-185):** Page-scoped shortcuts: ↑/↓ card navigation, ←/→ tab switching, Escape deselect. Auto-scrolls selected card into view. Suppressed during input focus and modal open state. Vim-style j/k/h/l removed to avoid conflicts.
- **Unified diverging color scale (DEC-224):** Single shared color scale (`colorScales.ts`) for all charts encoding profit/loss. Zero = neutral gray, negative = red/orange, positive = green. Dynamic text contrast (DEC-225) flips white↔dark based on WCAG luminance.
- **Performance Workbench deferred (DEC-229):** Performance page will be refactored into customizable widget grid using `react-grid-layout` with backend layout persistence. Two stages: rearrangeable presets, then full palette + custom tab CRUD. 11–14 sessions. Deferred post-21d.

## Strategy Roster

### Phase 1 — Built (US Stocks, Sprints 3–20)
1. **ORB (Opening Range Breakout)** — 9:35–11:30 AM, 1–15 min holds, stop at OR midpoint
2. **ORB Scalp** — 9:45–11:30 AM, 10s–5 min holds, quick 0.3R targets
3. **VWAP Reclaim** — 10:00 AM–12:00 PM, 5–30 min holds, mean-reversion
4. **Afternoon Momentum** — 2:00–3:30 PM, 15–60 min holds, consolidation breakout

### Phase 2 — Planned (Sprints 26–32, DEC-163/DEC-167)
5. **Red-to-Green** — 9:45–11:00 AM, gap-down reversal
6. **Bull Flag** — All day, consolidation breakout after sharp move
7. **Flat-Top Breakout** — All day, multiple rejections at same level then clean break
8. **Dip-and-Rip** — 9:45–11:30 AM, sharp dip on low vol, aggressive bounce
9. **HOD Break** — All day, new high-of-day breakout with volume
10. **Pre-Market High Break** — 9:30–10:30 AM, break above pre-market high
11. **Gap-and-Go** — 9:30–10:00 AM, immediate gap continuation without pullback
12. **ABCD Reversal** — 10:00 AM–2:00 PM, four-point reversal at support
13. **Sympathy Play** — 9:45–11:30 AM, secondary mover in leading sector
14. **Parabolic Short** — 10:00 AM–3:00 PM, overextended reversal (first short, DEC-166)
15. **Power Hour Reversal** — 3:00–3:45 PM, failed breakdown reversal
16. **Earnings Gap Continuation** — 9:30–11:30 AM, day 2+ continuation
17. **Volume Shelf Bounce** — All day, bounce off high-volume VPOC
18. **Micro Float Runner** — 9:30–11:30 AM, ultra-low float with extreme RVOL

## Strategy Incubator Pipeline (10 Stages)

Concept → Exploration (VectorBT) → Validation (Replay Harness + Walk-Forward) → Ecosystem Replay → Paper Trading (20-30 days) → Live Minimum Size (20 days) → Live Full Size → Active Monitoring → Suspended → Retired

## Risk Limits (Defaults, Configurable)

- Per-trade risk: 0.5–1% of strategy's allocated capital
- Daily loss limit (account): 3–5%
- Weekly loss limit (account): 5–8%
- Cash reserve: minimum 20% always held
- Max single-stock exposure (all strategies): 5% of account
- Max single-sector exposure: 15% of account
- Circuit breakers are non-overridable

## Monthly Cost Summary

| Item | Cost | When Active | Notes |
|------|------|-------------|-------|
| Databento US Equities Standard | $199/mo | Sprint 12 integration testing onward (DEC-087) | Full universe, no symbol limits, L0–L3 |
| IBKR Pro commissions | ~$43/day at scale | Live trading onward | Offset by ~$200/day execution quality gain vs PFOF |
| IBKR account fees | $0 (waived with activity) | Account opening onward | No minimum balance required |
| IQFeed (forex + news + breadth) | ~$160–250/mo | When forex strategies or Tier 2 news needed | Deferred until specific feature requires it |
| Databento CME Futures | $179/mo + exchange fees | When futures strategies launch | Separate dataset subscription |
| Claude API (AI Layer) | ~$35–50/mo | Sprint 22 onward (DEC-098) | All-Opus, pay-as-you-go. Prompt caching reduces effective cost. |
| Databento Plus (L2/L3 live) | $1,399/mo | Post-revenue (DEC-238) | Required for Order Flow Model. $1,200/mo over Standard. |
| **Current monthly (paper trading)** | **$199/mo** | | Databento only |
| **Projected monthly (live, equities only)** | **~$235–250 + commissions** | | Databento + Claude API + commissions |
| **Projected monthly (full multi-asset)** | **~$575–680 + commissions** | | Databento + IQFeed + futures + Claude API + commissions |
| **Projected monthly (AI-enhanced, no OF)** | **~$249–299 + commissions** | Sprint 24+ | Databento Standard + Claude API + commissions |
| **Projected monthly (AI-enhanced + Order Flow)** | **~$1,449–1,499 + commissions** | Post-revenue | Databento Plus + Claude API + commissions |
| Free news sources (Finnhub/FMP/EDGAR) | $0 | Sprint 23+ | Paid Benzinga upgrade (~$200/mo) only if needed (DEC-164) |


## Market Regime Classification (V1)

Based on: SPY vs 20/50 MA, VIX level, advance/decline breadth, SPY 5-day ROC, SPY vs VWAP.
Categories: Bullish Trending, Bearish Trending, Range-Bound, High Volatility Event, Crisis.

## File Structure (Target)

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus
├── strategies/     # Base class + individual strategy modules
├── data/           # Scanner, Data Service, Indicators
├── execution/      # Broker abstraction, Order Manager
├── analytics/      # Trade Logger, Strategy Reports, Portfolio Reports
├── backtest/       # VectorBT helpers, Backtrader configs, Replay Harness
├── ui/             # Tauri app + React frontend
├── ai/             # Claude API integration, Approval Workflow
├── intelligence/   # Setup Quality Engine, Order Flow, Catalyst, Position Sizer, Learning Loop, Pre-Market Engine
├── notifications/  # Push, Email, Telegram/Discord handlers
├── accounting/     # Tax tracking, P&L, Wash Sale detection
├── config/         # YAML config files (strategies, risk limits, etc.)
├── journal/        # Learning Journal storage
└── tests/          # Unit and integration tests
```

## Naming Conventions

- Strategy files: `snake_case.py` (e.g., `orb_breakout.py`)
- Strategy classes: `PascalCase` (e.g., `OrbBreakout`)
- Config files: `snake_case.yaml`
- Database tables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

## Important Constraints

- PDT Rule: Still active as of Feb 2026 (FINRA reform pending SEC approval, expected mid-2026). Accounts under $25K limited to 3 day trades per 5 rolling business days in margin accounts. Cash accounts exempt but have settlement delays (T+1).
- Wash Sale Rule: Must be tracked automatically for tax compliance.
- All brokerage API keys and secrets stored in encrypted secrets manager, never in code or git.
- Every action (trade, config change, Claude proposal) is logged immutably in audit trail.
- Monthly data infrastructure: Databento US Equities Standard $199/month. Additional datasets priced separately (CME futures +$179/month, OPRA options +$199/month). IQFeed supplemental ~$160–250/month when added. Budget monitored via RSK-023.
- IBKR IB Gateway requires running Java process alongside ARGUS. Nightly resets require automated reconnection. Docker containerization recommended. See RSK-022.
- Databento session limit: 10 simultaneous live sessions per dataset on Standard plan. ARGUS uses 1 session with Event Bus fan-out. Monitor if architecture changes require more sessions.

## Build Phases → Parallel Tracks (DEC-079)

Effective February 19, 2026, ARGUS uses two parallel tracks instead of sequential phases:

### Build Track (velocity-limited, continuous)
Sprints 12+. System construction proceeds at development speed. Each sprint targets a specific component. Order is prioritized but flexible — Validation Track needs can reprioritize.

**Queue (DEC-096, DEC-104–109):** CC Analytics & Strategy Lab (Sprint 21) → AI Layer MVP (Sprint 22) → Tier 1 News + additional strategies + features (Sprint 23+). Sprint 21 is the major analytics sprint (~80–100h), Sprint 22 adds AI visualization features (~46h). `docs/ui/UX_FEATURE_BACKLOG.md` provides per-sprint enhancement add-ons.

**Command Center delivery (DEC-080):** Single React codebase ships to three surfaces: web app (any browser), Tauri desktop app (system tray, native notifications), and PWA mobile app (iPhone/iPad home screen install). All three operational after Sprint 16.

**Monthly infrastructure costs:** Databento US Equities Standard $199/month (Sprint 12+). IBKR commissions variable when live. IQFeed ~$160–250/month when added for forex/news (future). See RSK-023.

### Validation Track (calendar-limited, confidence-gated)
Paper trading → live minimum size → live full size. Gates based on accumulated market data and user confidence. Only real capital deployment gates on this track.

**Current gate:** Paper trading ACTIVE with DEC-076 parameters on Alpaca IEX (system stability testing only — DEC-081). Migrates to Databento data after Sprint 12, then to IBKR paper trading after Sprint 13. Exit requires: Databento data integration + IBKR paper trading validation + user confidence + CPA consultation → live trading on IBKR.

### Completed Work
1. **Core Engine + ORB Strategy** ✅ (Sprints 1–5, 362 tests, Feb 14–16)
   - Sprint 1: Config system, Event Bus, data models, database, Trade Logger (52 tests)
   - Sprint 2: Broker Abstraction, SimulatedBroker, Risk Manager (112 tests)
   - Sprint 3: BaseStrategy, ORB Breakout, ReplayDataService, Scanner ABC (222 tests)
   - Sprint 4a: AlpacaDataService, AlpacaBroker, Clock injection (282 tests)
   - Sprint 4b: Order Manager, AlpacaScanner (320 tests)
   - Sprint 5: HealthMonitor, system entry point, state reconstruction, structured logging (362 tests)
2. **Backtesting Validation** ✅ (Sprints 6–10, 542 tests, Feb 16–17)
   - Sprint 6: Historical data acquisition — DataFetcher, Manifest, DataValidator. 28 symbols × 11 months, 2.2M+ bars (417 tests)
   - Sprint 7: Replay Harness — BacktestDataService, ReplayHarness, SimulatedBroker enhancements, synthetic tick generation (473 tests)
   - Sprint 8: VectorBT parameter sweeps — vectorized ORB simulation, ATR filtering, heatmap generation. Pure NumPy/Pandas (DEC-063). Gate check confirmed tooling (506 tests)
   - Sprint 9: Walk-forward validation — walk_forward.py (optimizer + fixed-params modes), cross-validation, HTML report generator with Plotly charts (542 tests)
   - Sprint 10: Analysis & Parameter Validation Report — baseline backtests, 522K-combo sweep, walk-forward (inconclusive, DEC-073), parameter recommendations (DEC-076), final validation (137 trades, Sharpe 0.93, PF 1.18). Deliverable: `docs/backtesting/PARAMETER_VALIDATION_REPORT.md`
3. **Extended Backtest** ✅ (Sprint 11, 35mo data, 15 WF windows, Feb 17)
   - Sprint 11: Extended backtest — 35 months of data (Mar 2023–Jan 2026), 15 walk-forward windows. Fixed-params WFE (P&L) = 0.56, OOS Sharpe = +0.34, OOS P&L = $7,741. DEC-076 parameters confirmed for paper trading. ✅ COMPLETE
   - Paper Trading (parallel track): Argus on Alpaca paper with DEC-076 parameters. Flexible duration, kill criteria as guardrails. See `08_PAPER_TRADING_GUIDE.md`
   - Exit gate: Walk-forward WFE ≥ 0.3 on extended data + user satisfied with paper trading + CPA consultation
   - See `10_PHASE3_SPRINT_PLAN.md` for tracking
4. **DatabentoDataService Adapter** ✅ (Sprint 12, 658 tests, Feb 21)
   - DatabentoConfig, DatabentoSymbolMap, DatabentoDataService (live streaming + reconnection + stale monitor)
   - DataFetcher Databento backend (historical data + Parquet cache + manifest tracking)
   - DatabentoScanner (V1 watchlist-based gap scanning)
   - System integration: DataSource enum, provider selection in main.py
   - Shared `databento_utils.py` (DEC-091). Deferred: DEF-014, DEF-015.
5. **IndicatorEngine Extraction** ✅ (Sprint 12.5, 685 tests, Feb 21)
   - IndicatorEngine class shared by all four DataService implementations (DEC-092, DEF-013 resolved)
   - Pure refactor — zero behavioral changes
6. **IBKRBroker Adapter** ✅ (Sprint 13, 811 tests, Feb 22)
   - IBKRBroker full Broker abstraction via `ib_async` (DEC-083, DEC-093, DEC-094)
   - Native bracket orders with T1/T2 support, fill streaming, reconnection, state reconstruction
   - Order Manager T2 broker-side limit orders, config-driven broker selection (BrokerSource enum)
   - System integration: main.py broker branching. Deferred: DEF-016.
7. **DEF-016 Evaluation** ✅ (Sprint 13.5, Feb 22)
   - Atomic bracket refactor evaluated and deferred to Sprint 17+ (DEC-095)
   - Scope exceeds threshold: SimulatedBroker sync fills, AlpacaBroker single-target, full test rewrite
8. **Command Center API** ✅ (Sprint 14, 926 tests, Feb 23)
   - FastAPI REST API with JWT auth (bcrypt password hashing, HS256 tokens, 24h expiry)
   - 7 endpoint groups: auth (login/refresh/me), health, account, positions, trades, strategies, performance
   - WebSocket bridge: EventBus → WebSocket streaming with tick throttling, position filtering, heartbeat
   - PerformanceCalculator with 17 metrics (win rate, profit factor, Sharpe, max drawdown, etc.)
   - TradeLogger query methods (filtering, pagination, daily P&L aggregation)
   - Dev mode with realistic mock data (`python -m argus.api --dev`)
   - React scaffold (Vite + TypeScript + Tailwind CSS v4 + Zustand + React Router)
   - 11-phase system startup (API server as Phase 11). DEC-099 through DEC-103.
9. **Command Center Frontend** ✅ (Sprint 15, 926 tests unchanged, Feb 23)
   - Four pages: Dashboard (account summary, open positions with real-time WS prices, recent trades, system health mini), Trade Log (filtered history, stats bar, paginated table with exit reason badges), Performance (period selector, 12-metric grid, equity curve via Lightweight Charts, daily P&L histogram, strategy breakdown), System (overview, component health, strategy cards, collapsible events log)
   - Responsive design: 393px (iPhone SE), 834px (iPad portrait), 1194px (iPad landscape), 1512px (MacBook Pro). Icon sidebar nav on desktop/tablet, bottom tab bar on mobile.
   - 8 implementation sessions. Loading/error/empty states on all pages. WebSocket reconnection. Dark theme. Touch targets ≥44px. iPhone safe area padding. Zero build errors + clean lint.
   - Code review: all 4 pages reviewed across all 3 devices (20 screenshots). Visual consistency confirmed.
   - Design research session conducted (DEC-106–110). UX Feature Backlog created with 35 features across 6 sprint groupings.
10. **Desktop/PWA + UX Polish** ✅ (Sprint 16, 942 tests, Feb 24)
   - UX Polish (DEC-107): Framer Motion page transitions + stagger animations, skeleton loading, AnimatedNumber, P&L flash, SVG sparklines, chart draw-in, contextual empty states, card hover lift (desktop-only)
   - Trade detail slide-in panel (desktop: right 40%, mobile: full-screen bottom 90vh)
   - Controls: emergency flatten all, emergency pause all (confirmation modals), per-strategy pause/resume, individual position close (DEC-111)
   - CSV trade export with filters (DEC-112). PWA (manifest, service worker, icons, iOS meta). Tauri v2 desktop shell.
   - Three delivery surfaces operational: web app, Tauri desktop, PWA mobile (DEC-080)
11. **Orchestrator V1** ✅ (Sprint 17 + 17.5, 1146 tests, Feb 24–25)
   - Sprint 17: Orchestrator core (pre-market, regime monitoring, throttle, EOD review, decision logging). RegimeClassifier (SPY realized vol as VIX proxy, DEC-113). PerformanceThrottler. CorrelationTracker (V2 infrastructure, DEC-116). Equal-weight allocation V1 (DEC-114, DEC-119). DEF-016 resolved — atomic bracket orders (DEC-117). API: 3 orchestrator endpoints + 4 WS event types. UI: SegmentedTab, Badge system, AllocationDonut, RiskGauge. 12-phase startup. 13 sessions.
   - Sprint 17.5: Polish — Orchestrator encapsulation properties (public API for route access), safe-area padding fix (additive spacer div), donut/gauge animation-once refs, RiskAllocationPanel stable render (removed conditional skeleton swap — always renders same DOM structure, children handle empty states). 4 sessions.

See `10_PHASE3_SPRINT_PLAN.md` for current sprint plan and queue.

## Reference Documents

- `01_PROJECT_BIBLE.md` — Source of truth for what and why
- `02_PROJECT_KNOWLEDGE.md` — This file (Claude context)
- `03_ARCHITECTURE.md` — Technical blueprint for how
- `04_STRATEGY_TEMPLATE.md` — Standard template for strategy documentation
- `05_DECISION_LOG.md` — Record of all key decisions with rationale
- `06_RISK_REGISTER.md` — Assumptions and risks being tracked
- `07_PHASE1_SPRINT_PLAN.md` — Phase 1 build order (COMPLETE). Historical reference.
- `08_PAPER_TRADING_GUIDE.md` — Step-by-step guide for Alpaca paper trading validation.
- `09_PHASE2_SPRINT_PLAN.md` — Canonical Phase 2 build order with sprint status tracking. **Both Claude instances must update this when sprints complete or scope changes.**
- `10_PHASE3_SPRINT_PLAN.md` — Active sprint plan. Build Track queue + Validation Track status. *Renamed from "Phase 3 Sprint Plan" per DEC-079.*
- `docs/backtesting/PARAMETER_VALIDATION_REPORT.md` — Phase 2 deliverable. ORB parameter analysis and recommendations.
- `docs/research/argus_market_data_research_report.md` — Deep-dive research report on market data providers. Databento selected (DEC-082). Covers pricing, latency, API design, symbol coverage, and historical data across 8+ providers.
- `docs/research/argus_execution_broker_research_report.md` — Deep-dive research report on execution brokers. Interactive Brokers selected (DEC-083). Covers routing quality, commission structures, API capabilities, multi-asset coverage, and PFOF analysis.
- `docs/ui/UX_FEATURE_BACKLOG.md` — Prioritized inventory of 35 UI/UX enhancements across Sprints 16–23+. Design vision, principles, per-sprint features with effort estimates. Born from Sprint 15 code review + design research.

## Communication Style Notes

The user prefers thorough, detailed explanations. He appreciates when Claude pushes back or raises concerns proactively. He values being asked clarifying questions before assumptions are made. He wants to understand the *why* behind every recommendation, not just the *what*. He is building this for his family's financial future — treat every design decision with the seriousness that implies.

- **Deferred items:** Tracked in CLAUDE.md under "Deferred Items" section. Surface proactively when trigger conditions are met.

## Docs Update Procedure

**Trigger:** Steven says "update all docs" (or similar: "sync docs", "docs update"). Also triggered at the end of any conversation where decisions were made.

### The Checklist

For each document, ask: "Did this session change anything this doc tracks?" Skip docs where nothing changed.

| Document | Update If... | What to Update |
|----------|-------------|----------------|
| **05_DECISION_LOG.md** | Any design/implementation decision was made | Add new DEC-NNN entry (check current highest number first!). Use the standard table format. Never reuse or skip numbers. |
| **02_PROJECT_KNOWLEDGE.md** | Decisions made, sprint completed, constraints discovered, architecture changed | Add new decisions to "Key Decisions Made" with DEC reference. Update "Current Project State" (Build Track + Validation Track). Update Build Track queue. Add new constraints. |
| **03_ARCHITECTURE.md** | New components, schema change, new API endpoints, dependency added | Update relevant section. Mark new items as implemented. |
| **01_PROJECT_BIBLE.md** | System invariants changed, strategy rules changed, risk parameters changed | Rare — only update if a fundamental rule changed. |
| **06_RISK_REGISTER.md** | New risk identified, existing risk status changed, assumption validated/invalidated | Add new RSK-NNN or ASM-NNN, or update existing entry status. |
| **10_PHASE3_SPRINT_PLAN.md** | Sprint completed, scope changed, Build Track queue reordered, Validation Track status changed | Move sprint to completed table. Update test counts. Record outcomes. |
| **CLAUDE.md** | Current state changed, new architectural rule, new command, project structure changed | Update "Current State", "Architectural Rules", "Commands", or "Deferred Items" as needed. |

### Rules

1. **Check the current highest DEC/RSK/ASM number before adding new entries.** The #1 source of doc bugs is duplicate numbers from not checking.
2. **Draft actual content, not just "update X".** Every doc change should be copy-pasteable. Include the exact text to add or change.
3. **Sprint numbers are the canonical identifier.** Use sprint numbers (Sprint 12, Sprint 13) in all docs. Historical phases referenced by name only.
4. **Don't update docs that didn't change.** The checklist is a filter, not a mandate. Most sessions touch 2–3 docs at most.
5. **Project Knowledge is also the Claude.ai project instructions.** After updating `02_PROJECT_KNOWLEDGE.md`, remind Steven to sync the project instructions if changes are significant.

### Output Format (Claude.ai)

Output a **"## Docs Sync"** section with the drafted content for each doc that needs updating, grouped by file. Include the exact text to add/change so Steven can copy-paste directly.

### Output Format (Claude Code)

Directly edit the files in the repo. Commit doc updates as a separate commit: `docs: update [list of changed docs]`.

## Two-Claude Workflow Summary

- **This Claude (claude.ai project):** Strategic work, design, decisions, document drafting, performance review. Reads from project instructions + uploaded files.
- **Claude Code (terminal):** Implementation, coding, testing, debugging. Reads from CLAUDE.md + .claude/rules/ + docs/ in git repo.
- **Bridge:** The docs/ folder in the git repo. Both Claudes read from it. Updates flow: decision here → draft update here → user commits to repo → Claude Code reads next session. Or: discovery in Claude Code → user brings here for discussion or commits directly.
- **User's job:** Keep the two in sync by committing doc updates to git and re-uploading to this project when they diverge. Both Claudes will remind you.
- **"Update all docs" shorthand:** Works in both contexts. Claude.ai drafts copy-paste content. Claude Code edits files directly.

GitHub repo is accessible at https://github.com/stevengizzi/argus.git. Project instructions are separate and updated manually at major milestones.

### When to Flag Updates

Flag updates to **Project Knowledge (02)** when:
- A build phase starts or completes
- The "Current Project State" changes
- A new key decision is made that should prevent relitigation
- New constraints or gotchas are discovered

Flag updates to **Decision Log (05)** when:
- ANY design or implementation decision is made during conversation
- An existing decision is changed or superseded
- Draft the full DEC-XXX entry so the user can paste it directly

Flag updates to **Risk Register (06)** when:
- A new assumption is identified
- An existing assumption is validated or invalidated
- A new risk is identified
- A risk's likelihood or impact changes based on new information

Flag updates to **Bible (01)** when:
- Strategy rules, risk parameters, or system behavior rules change
- New sections are added to the system vision
- Existing sections are modified based on implementation reality

Flag updates to **Architecture (03)** when:
- Interfaces, schemas, or API endpoints change
- New modules are added or existing ones restructured
- Technology stack changes (new libraries, changed tools)

Flag updates to **CLAUDE.md** when:
- Current build phase changes
- Project structure changes
- New commands are available
- New architectural rules are established

Flag updates to **Phase 1 Sprint Plan (07)** when:
- A sprint is reviewed and confirmed complete
- Sprint scope changes (components move between sprints)
- New sprints are added or existing ones are split/merged
- The document should always reflect current reality — never let it go stale

### Drafting Updates

When flagging an update, don't just say "update the Decision Log." Draft the actual content so the user can copy-paste it. All drafted content should use code notation. For example:

"Add to Decision Log:
### DEC-025 | WebSocket Library Choice
| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Decision** | Use Python's built-in websockets library instead of socket.io. |
| **Rationale** | Lighter weight, no additional dependency, sufficient for our pub/sub needs. |
| **Status** | Active |"

This makes the user's job trivial: copy, paste, commit.

### Weekly Sync Reminder

If a conversation happens to fall near the end of a week, remind the user:
"Weekly sync check: Is your project instructions copy of 02_PROJECT_KNOWLEDGE.md current with what's in the git repo? Any docs that were updated in Claude Code sessions this week that need to be re-uploaded here?"

## Two-Claude Workflow Summary

- **This Claude (claude.ai project):** Strategic work, design, decisions, document drafting, performance review. Reads from project instructions + uploaded files.
- **Claude Code (terminal):** Implementation, coding, testing, debugging. Reads from CLAUDE.md + .claude/rules/ + docs/ in git repo.
- **Bridge:** The docs/ folder in the git repo. Both Claudes read from it. Updates flow: decision here → draft update here → user commits to repo → Claude Code reads next session. Or: discovery in Claude Code → user brings here for discussion or commits directly.
- **User's job:** Keep the two in sync by committing doc updates to git and re-uploading to this project when they diverge. Both Claudes will remind you.

GitHub repo is accessible at https://github.com/stevengizzi/argus.git. Project instructions are separate and updated manually at major milestones.