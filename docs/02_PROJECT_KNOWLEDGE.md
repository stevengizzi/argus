# ARGUS — Project Knowledge (Claude Context)

> *Paste this into Claude's project instructions. Keep updated as the project evolves. Last updated: Feb 25, 2026.*

---

## What Is Argus

Argus is a fully automated multi-strategy day trading ecosystem with an AI co-captain (Claude), a desktop/mobile Command Center, and multi-asset support. The user is building this to generate income for his family. He can code in Python. He has trading experience but no prior systematic/algorithmic trading system.

## Current Project State

**Structure:** Two parallel tracks (DEC-079, February 19, 2026). Build Track (system construction) + Validation Track (strategy confidence-building).

**Build Track:** 1317 tests (pytest) + 14 (Vitest). Sprints 1–18.75 complete. Sprint 19 (VWAP Reclaim) NEXT.
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

**Validation Track:** Paper trading ACTIVE with DEC-076 parameters on Alpaca. Validates system stability only — Alpaca IEX data captures only ~2–3% of market volume (DEC-081), so signal accuracy is not validated until Databento data is integrated (Sprint 12). See `08_PAPER_TRADING_GUIDE.md`.

**Infrastructure Research (Feb 18–20):** Two deep-dive research reports completed:
- Market Data: Databento US Equities Standard ($199/mo) selected as primary data backbone (DEC-082). IQFeed supplemental for forex/news/breadth when needed.
- Execution Broker: Interactive Brokers (IBKR Pro, tiered) selected as sole live execution broker (DEC-083). Direct adoption — no phased Alpaca → IBKR migration.
- Full reports: `argus_market_data_research_report.md` and `argus_execution_broker_research_report.md` in project files.

**IBKR Account (Feb 21):** Application submitted. Account ID U24619949. Individual margin account, IBKR Pro tiered pricing. Awaiting approval — paper trading account will be enabled post-approval for Sprint 13 adapter development.

**Next Build sprints:** VWAP Reclaim (Sprint 19) → Afternoon Momentum (Sprint 20) → CC Analytics & Strategy Lab (Sprint 21) → AI Layer MVP (Sprint 22). See DEC-096, DEC-106–110. UX Feature Backlog (`docs/ui/UX_FEATURE_BACKLOG.md`) provides per-sprint enhancement add-ons alongside core sprint scope. Orchestrator interaction UI planned for Sprint 21 (21-L in UX Feature Backlog). Note: Databento subscription activation recommended around Sprint 19 (DEC-097). All pre-Databento backtests require re-validation with quality data (DEC-132).

**Next Validation gate:** Build through Sprint 21 (four strategies + analytics) using Alpaca data → activate Databento (~Sprint 19, DEC-097) → serious paper trading validation with quality data + IBKR execution → AI Layer (Sprint 22) compounds analysis during validation → CPA consultation → live trading at minimum size on IBKR.

**✅ IBKR APPLICATION SUBMITTED:** Feb 21, 2026. Account ID: U24619949. Individual margin account, IBKR Pro (tiered pricing), Georgia address. Trading permissions requested: Stocks, Options (Level 3), Futures, Currency/Forex, Cryptocurrencies, Mutual Funds. Awaiting approval (typically 1–3 business days, may take longer). Disclosures and agreements archived locally.

## Key Decisions Made (Do Not Relitigate)

- **System name:** Argus
- **Language:** Python 3.11+
- **Brokerages:** Broker-agnostic abstraction layer. Interactive Brokers (sole live execution — DEC-083, `ib_async` library). Alpaca (strategy incubator paper testing only — DEC-086). SimulatedBroker (backtesting/shadow system). IBKR covers entire asset class roadmap (stocks, options, futures, forex, crypto) through single account.
- **Data:** Databento US Equities Standard ($199/mo) for all live market data and new historical data (DEC-082). Full universe, no symbol limits, L0–L3 schemas, exchange-direct proprietary feeds. DataService abstraction for future provider swaps. IQFeed supplemental (forex, Benzinga news, breadth indicators) when needed. Alpaca data deprecated for production use (DEC-081/086).
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
- **Default dataset (DEC-089):** XNAS.ITCH (Nasdaq TotalView-ITCH). Configurable. Deepest historical data, L2/L3 available, covers NASDAQ-listed stocks.
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


## Strategy Roster (V1 — US Stocks)

1. **ORB (Opening Range Breakout)** — 9:35–11:30 AM, 1–15 min holds, stop at OR midpoint, time stop at 15 min
2. **ORB Scalp** — 9:45–11:30 AM, 10s–5 min holds, quick 0.3–0.5R targets
3. **VWAP Reclaim** — 10:00 AM–12:00 PM, 5–30 min holds, mean-reversion
4. **Afternoon Momentum** — 2:00–3:30 PM, 15–60 min holds, consolidation breakout
5. **Red-to-Green** — 9:45–11:00 AM, 10–45 min holds, gap-down reversal

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
| **Current monthly (paper trading)** | **$199/mo** | | Databento only |
| **Projected monthly (live, equities only)** | **~$235–250 + commissions** | | Databento + Claude API + commissions |
| **Projected monthly (full multi-asset)** | **~$575–680 + commissions** | | Databento + IQFeed + futures + Claude API + commissions |

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

**Queue (DEC-096, DEC-104–109):** Desktop/PWA + UX Polish (Sprint 16) → Orchestrator V1 (Sprint 17) → ORB Scalp (Sprint 18) → VWAP Reclaim (Sprint 19) → Afternoon Momentum (Sprint 20) → CC Analytics & Strategy Lab (Sprint 21) → AI Layer MVP (Sprint 22) → Tier 1 News + additional strategies + features (Sprint 23+). Each sprint includes UX enhancement add-ons from `docs/ui/UX_FEATURE_BACKLOG.md` — Sprint 16 adds motion/animation/sparklines (~15h), Sprints 17–20 add multi-strategy awareness features (~33h total), Sprint 21 is the major analytics sprint (~80–100h), Sprint 22 adds AI visualization features (~46h).

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