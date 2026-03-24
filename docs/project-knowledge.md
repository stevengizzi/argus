# ARGUS — Project Knowledge (Claude Context)

> *Tier A operational context for Claude Code and Claude.ai. Last updated: March 25, 2026 (Sprint 27.65 doc sync — Market Session Safety + Operational Fixes).*
> *Full decision rationale: `docs/decision-log.md` | Sprint details: `docs/sprint-history.md` | DEC index: `docs/dec-index.md`*

---

## What Is ARGUS

ARGUS is a fully automated, AI-enhanced multi-strategy day trading system for US equities. It combines rules-based strategy execution with planned AI-powered setup quality grading, NLP catalyst analysis, and dynamic position sizing. Built in Python (FastAPI backend) with a React/TypeScript Command Center frontend (Tauri desktop + PWA mobile). The user is building this to generate household income for his family. He operates from Cape Town, South Africa, trading US markets during afternoon/evening hours (~3:30 PM–11:00 PM local time), making mobile access critical. He can code in Python and has trading experience but no prior algorithmic trading system.

## Current State

**Tests:** 3,412 pytest + 633 Vitest (0 failures, 0 hangs)
**Sprints completed:** 1 through 27 + 21.6 + 25.9 + 27.5 + 27.6 + 27.65 (28 full sprints + sub-sprints)
**Active sprint:** None (between sprints)
**Next sprint:** 27.7 (Counterfactual Engine)
**GitHub:** `https://github.com/stevengizzi/argus.git` (public)

### Sprint History (Summary)

| Sprint | Name | Tests | Date | Key DECs |
|--------|------|-------|------|----------|
| 1–5 | Core Engine + ORB Strategy | 362 | Feb 14–16 | DEC-001–045 |
| 6–10 | Backtesting Validation | 542 | Feb 16–17 | DEC-046–076 |
| 11 | Extended Backtest (35mo, WFE=0.56) | 542 | Feb 17 | DEC-077–078 |
| 12 | DatabentoDataService adapter | 658 | Feb 21 | DEC-082–091 |
| 12.5 | IndicatorEngine extraction | 685 | Feb 21 | DEC-092 |
| 13 | IBKRBroker adapter | 811 | Feb 22 | DEC-093–095 |
| 14 | Command Center API | 926 | Feb 23 | DEC-099–103 |
| 15 | Command Center Frontend (4 pages) | 926 | Feb 23 | DEC-104–110 |
| 16 | Desktop/PWA + UX Polish | 942 | Feb 24 | DEC-111–112 |
| 17+17.5 | Orchestrator V1 | 1146 | Feb 24–25 | DEC-113–119 |
| 18+18.5+18.75 | ORB Scalp + CapitalAllocation | 1317 | Feb 25 | DEC-120–135 |
| 19 | VWAP Reclaim (OOS Sharpe 1.49) | 1410+40V | Feb 25–26 | DEC-136–151 |
| 20 | Afternoon Momentum | 1522+48V | Feb 26 | DEC-152–162 |
| 21a | Pattern Library page | 1558+70V | Feb 27 | DEC-172–185 |
| 21b | Orchestrator page | 1597+100V | Feb 27 | DEC-186–195 |
| 21c | The Debrief page | 1664+138V | Feb 27 | DEC-196–203 |
| 21d | Dashboard+Performance+System+Copilot shell | 1712+257V | Feb 27–28 | DEC-204–229 |
| 21.5 | Live Integration | 1737+291V | Feb 28–Mar 5 | DEC-230–261 |
| 21.5.1 | C2 Bug Fixes + UI Polish | (included above) | Mar 5 | DEC-261 |
| 21.7 | FMP Scanner Integration | 1754+296V | Mar 5 | DEC-258–259 |
| 22 | AI Layer MVP | 1959+377V | Mar 6–7 | DEC-264–275 |
| 22.1 | Post-Verification Fixes | 1967+377V | Mar 7 | DEC-276 |
| 22.2 | AI Context Data Fixes | 1977+377V | Mar 7 | — |
| 22.3 | Silent Exception Logging | 1977+377V | Mar 7 | — |
| 23 | Universe Manager | 2099+392V | Mar 7–8 | DEC-277 |
| 23.05 | Post-Sprint Fixes | 2101+392V | Mar 8 | — |
| 23.1 | Autonomous Runner Protocol Integration | 2101+392V | Mar 9 | DEC-278–297 |
| 23.2 | Autonomous Sprint Runner Implementation | 2289+392V | Mar 9 | DEC-278–297 (implemented) |
| 23.3 | Impromptu: Wide Pipe + Runner Perms | 2302+392V | Mar 9–10 | DEC-298–299 |
| 23.5 | NLP Catalyst Pipeline | 2396+435V | Mar 10 | DEC-300–307 |
| 23.6 | Tier 3 Remediation + Pipeline Integration | 2490+435V | Mar 10 | DEC-308–315 |
| 23.7 | Startup Scaling Fixes | 2511+435V | Mar 11 | DEC-316–318 |
| 23.8 | Intelligence Pipeline Live QA Fixes | 2529+435V | Mar 12 | DEC-319–328 |
| 23.9 | Frontend + Test Cleanup | 2532+446V | Mar 12 | DEC-329 |
| 24 | Setup Quality Engine + Dynamic Sizer | 2686+497V | Mar 13–14 | DEC-330–341 |
| 24.1 | Post-Sprint Cleanup & Housekeeping | 2709+503V | Mar 14 | — |
| 24.5 | Strategy Observability + Operational Fixes | 2768+523V | Mar 15–16 | DEC-342 |
| 25 | The Observatory | 2765+599V | Mar 17–18 | — (no new DECs) |
| 25.5 | Universe Manager Watchlist Wiring Fix | 2782+599V | Mar 18 | DEC-343–344 |
| 25.6 | Bug Sweep | 2794+611V | Mar 19–20 | DEC-345–346 |
| 25.7 | Post-Session Operational Fixes | 2815+611V | Mar 21 | DEC-347–350 |
| 25.8 | API Auth 401 + Close-Position Fix | 2815+611V | Mar 21 | DEC-351–352 |
| 26 | Red-to-Green + Pattern Library Foundation | 2925+620V | Mar 21–22 | — (no new DECs) |
| 27 | BacktestEngine Core | 3010+620V | Mar 22 | — (no new DECs) |
| 21.6 | Backtest Re-Validation + Execution Logging | 3051+620V | Mar 23 | DEC-359 |
| 21.6.1 | Impromptu: BacktestEngine Sizing + Data Compat | (included above) | Mar 23 | — |
| 21.6.2 | Impromptu: BacktestEngine Risk Overrides | (included above) | Mar 23 | DEC-359 |
| 25.9 | Operational Resilience Fixes | 3071+620V | Mar 23 | DEC-360, DEC-361, DEC-362 |
| 27.5 | Evaluation Framework | 3177+620V | Mar 23–24 | — (no new DECs) |
| 27.6 | Regime Intelligence | 3337+631V | Mar 24 | — (no new DECs) |
| 27.6.1 | Observatory Regime Wiring (Impromptu) | (included above) | Mar 24 | — |
| 27.65 | Market Session Safety + Operational Fixes | 3412+633V | Mar 24–25 | DEC-363–368 |

*Full sprint scopes and session details: `docs/sprint-history.md`*

### Build Track Queue

~~26 (Red-to-Green + Pattern Library Foundation)~~ ✅ → ~~27 (BacktestEngine Core — pulled forward per DEC-354)~~ ✅ → ~~21.6 (Backtest Re-Validation + Execution Logging)~~ ✅ → ~~25.9 (Operational Resilience Fixes)~~ ✅ → ~~27.5 (Evaluation Framework)~~ ✅ → ~~27.6 (Regime Intelligence)~~ ✅ → **27.7 (Counterfactual Engine)** → 28 (Learning Loop V1) → 29–31 (Pattern Expansion + Short Selling + Research Console) → 32 (Parameterized Strategy Templates) → **32.5 (Experiment Registry + Promotion Pipeline + Anti-Fragility)** → 33 (Statistical Validation) → **33.5 (Adversarial Stress Testing)** → 34–35 (ORB Systematic Search ★, Ensemble Analysis) → 36–42 (Cross-Family Search, Ensemble Orchestrator V2, Synapse, Learning Loop V2, Continuous Discovery, Performance Workbench). Sprints 27.5/27.6/27.7/32.5/33.5 added by DEC-357/DEC-358 (amendment adoption March 23, 2026). Order Flow Model deferred to post-revenue (DEC-238). Historical data purchase deferred indefinitely (DEC-353); 96 months of OHLCV-1m available at $0 via XNAS.ITCH + XNYS.PILLAR (DEC-358). Full roadmap: `docs/roadmap.md` (DEC-262).

### Validation Track

Paper trading active with Databento EQUS.MINI + IBKR paper (Account U24619949, DEC-236). Gates: IBKR paper 20+ days (Gate 2) → AI-enhanced paper 30+ days (Gate 3) → Full system paper 50+ cumulative days, Sharpe > 2.0 (Gate 4) → CPA consultation → live minimum size (Gate 5).

### Expanded Vision (DEC-163, DEC-262)

15+ artisanal patterns → ensemble systematic search → self-improving trading intelligence platform. Near-term (Phase 5–6): Setup Quality Engine (0–100 scoring, DEC-239, **Sprint 24 ✅**), NLP Catalyst Pipeline (SEC EDGAR + FMP + Finnhub + Claude API, **Sprint 23.5 ✅**), Dynamic Position Sizer (**Sprint 24 ✅**), **Evaluation Framework (MultiObjectiveResult, EnsembleResult, Pareto dominance — Sprint 27.5 ✅)**, **Regime Intelligence (RegimeVector multi-dimensional — Sprint 27.6 ✅)**, **Counterfactual Engine (shadow position tracking — Sprint 27.7)**, Learning Loop V1, Short Selling Infrastructure, Universe Manager with full-universe monitoring (DEC-263, **Sprint 23 ✅**). Mid-term (Phase 7–8): BacktestEngine (**Sprint 27 ✅**), parameterized strategy templates, **Experiment Registry + Promotion Pipeline + Anti-Fragility (Sprint 32.5)**, statistical validation, **Adversarial Stress Testing (Sprint 33.5)**, systematic parameter search, controlled experiment (go/no-go gate). Long-term (Phase 9–10): Ensemble Orchestrator V2, Synapse visualization, Continuous Discovery Pipeline, Performance Workbench. Order Flow Model deferred to post-revenue (DEC-238, requires Databento Plus $1,399/mo). Full roadmap: `docs/roadmap.md`.

---

## Architecture

### Three-Tier System
1. **Trading Engine** — Strategies, Orchestrator, Risk Manager, Data Service, Broker abstraction, Order Manager, Trade Logger, Backtesting (VectorBT + Replay Harness)
2. **Command Center** — 8 pages (all built): Dashboard, Trade Log, Performance, Orchestrator, Pattern Library, The Debrief, System, Observatory. Tauri desktop + PWA mobile + web. AI Copilot active.
3. **AI Layer** (Sprint 22) — Claude API (Opus, DEC-098) via ClaudeClient wrapper; PromptManager with system prompt template and behavioral guardrails (DEC-273); SystemContextBuilder for per-page context injection (DEC-268); tool_use for structured action proposals (DEC-271) with 5 defined tools (DEC-272); ActionManager with DB-persisted proposals and 5-min TTL (DEC-267); 5 ActionExecutors with 4-condition pre-execution re-check; ConversationManager with calendar-date keying and tags (DEC-266); UsageTracker for per-call cost tracking (DEC-274); DailySummaryGenerator for insight card + daily summaries; ResponseCache for insight TTL caching. WS /ws/v1/ai/chat for streaming with actual API usage extraction (DEC-265). All timestamps ET-based (DEC-276). All AI features degrade gracefully when ANTHROPIC_API_KEY unset.
4. **Intelligence Layer** (Sprints 23.5 + 23.6 + 24) — CatalystPipeline orchestrates three data sources: SECEdgarSource (8-K, Form 4), FMPNewsSource (stock news, press releases), FinnhubSource (company news, analyst recommendations). CatalystClassifier uses Claude API with rule-based fallback (DEC-301). CatalystStorage with SQLite persistence in separate catalyst.db (DEC-309) and headline hash deduplication (DEC-302). BriefingGenerator produces pre-market intelligence briefs with $5/day cost ceiling (DEC-303). Post-classification semantic dedup by (symbol, category, time_window) before storage (DEC-311). Batch-then-publish ordering for data safety (DEC-312). Config-gated via `catalyst.enabled` (DEC-300). Intelligence startup factory in `argus/intelligence/startup.py` builds all components from config (DEC-308). Polling loop via asyncio task with market-hours-aware intervals (DEC-315). Sprint 23.8 hardened the pipeline: `asyncio.wait_for(120)` safety timeout on source gather (DEC-319), polling task health monitoring via `done_callback` (DEC-320), symbol scope reduced from full viable universe to scanner watchlist (DEC-321), FMP news circuit breaker on 401/403 (DEC-323), cost ceiling enforcement wired into classifier with cycle cost logging (DEC-324), and Databento lazy warm-up `end` clamped to `now - 600s` (DEC-326). FMP canary test at startup validates API schema (DEC-313). Frontend: CatalystBadge, CatalystAlertPanel, IntelligenceBriefView with TanStack Query hooks. Sprint 23.9 added `usePipelineStatus` hook gating all catalyst/briefing queries on pipeline health status from `/api/v1/health` — zero requests when pipeline inactive (DEC-329). DebriefService initialized in `server.py` lifespan (was only wired in dev mode, causing 503 in live mode).
5. **Quality Engine** (Sprints 24 + 24.1) — SetupQualityEngine scores setups on 5 weighted dimensions: pattern strength (30%), catalyst quality (25%), volume profile (20%), historical match (15%), regime alignment (10%). Produces quality_grade (A+ through C) and quality_score (0–100). DynamicPositionSizer maps grades to risk tiers (A+=2–3%, A=1.5%, B=0.75%, C+=0.25%, C-=SKIP). Strategies emit `share_count=0` with `pattern_strength` (0–100); `_process_signal()` in main.py runs quality pipeline (score → filter by minimum grade → size → enrich SignalEvent). Risk Manager check 0 rejects `share_count ≤ 0` before circuit breaker evaluation. Pipeline bypass: `BrokerSource.SIMULATED` or `quality_engine.enabled: false` → legacy sizing. QualitySignalEvent published after scoring (informational). Quality history persisted to `quality_history` table (20 columns, 4 indexes). Quality grade/score wired through Order Manager → TradeLogger → DB (Sprint 24.1). Config: `config/quality_engine.yaml` with Pydantic models (QualityWeightsConfig, QualityThresholdsConfig, QualityRiskTiersConfig) with validators. Firehose mode for catalyst sources: Finnhub single `GET /news?category=general`, SEC EDGAR single EFTS search (DEC-332). API: 3 endpoints (`/api/v1/quality/{symbol}`, `/api/v1/quality/history`, `/api/v1/quality/distribution`). UI: QualityBadge component, quality column in Trades table, Setup Quality in TradeDetailPanel, SignalQualityPanel (histogram) on Dashboard, RecentSignals with clickable SignalDetailPanel on Orchestrator (Sprint 24.1), QualityGradeChart (ComposedChart: bars for Avg P&L + line for Win Rate) on Performance, QualityOutcomeScatter on Performance Distribution tab (relocated from Debrief in Sprint 24.1). Orchestrator uses 3-column layout for Decision Log + Catalyst Alerts + Recent Signals (Sprint 24.1). Shared GRADE_COLORS/GRADE_ORDER constants extracted for consistency.

### Key Components
- **Strategies:** Daily-stateful, session-stateless plugins (DEC-028). 7 active. 11 more planned. All strategies implement `_calculate_pattern_strength()` returning 0–100 score and emit `share_count=0` for quality pipeline sizing (Sprint 24, DEC-330/331). `_watchlist` is `set[str]` internally for O(1) membership checks; `set_watchlist()` accepts `list[str]` input with `source` parameter (default `"scanner"`); `watchlist` property returns `list[str]` — external API unchanged (DEC-343, Sprint 25.5). BaseStrategy includes `StrategyEvaluationBuffer` (ring buffer, maxlen=1000) for diagnostic telemetry — `record_evaluation()` logs decision-point events with try/except guard (never raises). `EvaluationEventStore` provides SQLite persistence in `data/evaluation.db` (separated from `argus.db` in Sprint 25.6 to eliminate write contention, DEC-345) with 7-day retention and ET-date-based queries; exposes `execute_query()` public method and `is_connected` property (Sprint 25 S10). Write failure warnings rate-limited to 1 per 60s. REST endpoint `GET /api/v1/strategies/{id}/decisions` returns buffer contents (JWT-protected). Frontend `StrategyDecisionStream` slide-out panel on Orchestrator page (DEC-342, Sprint 24.5).
- **Pattern Library (Sprint 26):** PatternModule ABC (`argus/strategies/patterns/base.py`) — standardized pattern detection interface with 5 abstract members: `name`, `lookback_bars`, `detect()`, `score()`, `get_default_params()`. CandleBar frozen dataclass (independent of events.py). PatternDetection dataclass for detection results. PatternBasedStrategy (`argus/strategies/pattern_strategy.py`) — generic wrapper that handles operating window, per-symbol candle deque, signal generation, and telemetry for any PatternModule. BullFlagPattern (`argus/strategies/patterns/bull_flag.py`) — pole detection, flag validation, breakout confirmation, measured move targets. Score: 30/30/25/15 weighting. FlatTopBreakoutPattern (`argus/strategies/patterns/flat_top_breakout.py`) — resistance clustering, consolidation validation with range narrowing, breakout confirmation. Score: 30/30/25/15 weighting. RedToGreenStrategy (`argus/strategies/red_to_green.py`) — standalone from BaseStrategy, 5-state machine (WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED / EXHAUSTED), key level identification (VWAP, premarket_low, prior_close), max_level_attempts=2. PatternBacktester (`argus/backtest/vectorbt_pattern.py`) — generic sliding-window backtester for any PatternModule with parameter grid generation (±20%/±40% variations). VectorBT R2G (`argus/backtest/vectorbt_red_to_green.py`) — dedicated R2G backtester with gap-down detection. **Sprint 27.65 fixes:** PatternBasedStrategy bar accumulation moved before operating window check (candles from pre-window period now contribute to lookback history). `backfill_candles(symbol, bars)` method prepends historical bars from IntradayCandleStore on first candle per symbol. `set_candle_store()` accepts duck-typed store reference. RedToGreenStrategy `initialize_prior_closes()` populates `prior_close` from UM reference data (was never initialized, causing zero evaluations in live mode).
- **Observatory (Sprint 25):** ObservatoryService (`argus/analytics/observatory_service.py`) — read-only query service over EvaluationEventStore and UniverseManager with 4 methods: `get_pipeline_stages`, `get_closest_misses`, `get_symbol_journey`, `get_session_summary`. Observatory WebSocket (`/ws/v1/observatory`) — push-based pipeline updates with tier transition detection and evaluation summaries, independent from AI chat WS. ObservatoryConfig (`argus/analytics/config.py`) — Pydantic model wired into SystemConfig, config-gated via `observatory.enabled`. Frontend: 4 views (Funnel 3D, Radar 3D, Matrix heatmap, Timeline SVG), detail panel with candlestick chart, session vitals bar, debrief mode (7-day history). Three.js (r128) code-split via React.lazy. Shared-scene pattern: Funnel and Radar share single Three.js scene with camera presets. InstancedMesh for symbol particles (up to 5,000). Keyboard: f/m/r/t for views, [/] for tiers, Tab for symbols, Shift+R/F for camera. **Sprint 27.65 fix:** Pipeline endpoint response format aligned with frontend `ObservatoryPipelineResponse` type (was returning flat fields, frontend expected `tiers` dict with `count` + `symbols` per tier).
- **Regime Intelligence (Sprint 27.6):** RegimeClassifierV2 (`core/regime.py`) — multi-dimensional regime classification composing V1 delegation with 4 new calculators: BreadthCalculator (`core/breadth.py`, universe fraction above 20-day MA + thrust detection), MarketCorrelationTracker (`core/market_correlation.py`, pairwise correlation of top N symbols, dispersed/normal/concentrated classification), SectorRotationAnalyzer (`core/sector_rotation.py`, FMP sector performance for risk-on/risk-off detection), IntradayCharacterDetector (`core/intraday_character.py`, SPY candle analysis at configurable times for trending/choppy/reversal/breakout classification). RegimeVector frozen dataclass with 6 dimensions (trend, volatility, breadth, correlation, sector rotation, intraday character) + backward-compatible `primary_regime` (MarketRegime enum). RegimeOperatingConditions dataclass + `matches_conditions()` API for strategy activation in regime regions. RegimeHistoryStore (`core/regime_history.py`) — SQLite persistence in `data/regime_history.db` with fire-and-forget writes and 7-day retention. Config-gated via `regime_intelligence.enabled` in `config/regime.yaml`. BacktestEngine `use_regime_v2` flag. All data from existing subscriptions ($0 additional cost). Observatory REST + WS wired (Sprint 27.6.1).
- **Orchestrator:** Rules-based V1 (DEC-118). Equal-weight allocation, regime monitoring (SPY vol as VIX proxy), performance throttling, pre-market routine. Public `reclassify_regime()` method (DEC-346, Sprint 25.6) enables periodic regime reclassification — independent 300s asyncio task in main.py during market hours (9:30–16:00 ET), INFO-level logging every 6th check (~30 min) for operational visibility (Sprint 25.9). Zero-active-strategy WARNING when regime filtering eliminates all strategies during market hours (DEC-360, Sprint 25.9). `_is_market_hours()` helper for market-hours guards. Public `spy_data_available` property (Sprint 25.7). `PerformanceThrottler` returns `ThrottleAction.NONE` for strategies with zero trade history (DEC-349, Sprint 25.7). `latest_regime_vector_summary` property returns dict from RegimeVector via duck-typed `to_dict()` (Sprint 27.6.1).
- **Risk Manager:** Three-level gating (strategy, cross-strategy, account). Check 0 rejects `share_count ≤ 0` before circuit breaker evaluation (Sprint 24, DEC-336). Approve-with-modification for share reduction and target tightening; never modify stops or entry (DEC-027). Concentration limit approve-with-modification with 0.25R floor (DEC-249). Optional concurrent position limits (DEC-367, Sprint 27.65): `max_concurrent_positions: 0` disables the check entirely (both per-strategy and cross-strategy). Paper trading configs set to 0; capital and concentration limits are the real constraints.
- **Data Service:** Databento EQUS.MINI primary (DEC-248). Event Bus sole streaming mechanism (DEC-029). Databento callbacks on reader thread, bridged via `call_soon_threadsafe()` (DEC-088). `fetch_daily_bars()` implemented via FMP stable API for regime classification (DEC-347, Sprint 25.7). `last_update` attribute tracks last data receipt for health endpoint (Sprint 25.7). Universe Manager (Sprint 23) adds fast-path discard for non-viable symbols and ALL_SYMBOLS Databento mode. Time-aware indicator warm-up (DEC-316, Sprint 23.7): pre-market boot skips warm-up; mid-session boot uses lazy per-symbol backfill on first candle arrival. **IntradayCandleStore** (DEC-368, Sprint 27.65): `argus/data/intraday_candle_store.py` — parallel CandleEvent subscriber that accumulates 1-min bars per symbol in dict of deques (max 390 bars = full trading day). Market-hours filter (9:30–16:00 ET). Query API: `get_bars(symbol, start, end)`, `get_latest(symbol, count)`, `has_bars()`, `bar_count()`. Used by: market bars REST endpoint (Priority 1 source, replacing synthetic fallback), PatternBasedStrategy backfill on first candle per symbol.
- **Universe Manager (Sprint 23):** FMPReferenceClient fetches Company Profile + Share Float in batches for ~3,000–5,000 symbols. UniverseManager applies system-level filters (OTC, price, volume; fail-closed on missing data per DEC-277), builds pre-computed routing table mapping symbols to qualifying strategies via declarative `universe_filter` YAML configs. O(1) route_candle lookup. After `build_routing_table()` in Phase 9.5, strategy watchlists are populated from UM routing via `set_watchlist(symbols, source="universe_manager")` (DEC-343, Sprint 25.5). Fast-path discard in DatabentoDataService drops non-viable symbols before IndicatorEngine. Config-gated: `universe_manager.enabled` in system.yaml. Backward compatible (disabled = existing scanner flow). Zero-evaluation health warning (DEC-344, Sprint 25.5): `HealthMonitor.check_strategy_evaluations()` detects strategies with populated watchlists but zero evaluations after operating window + 5 min grace; sets DEGRADED, self-corrects when evaluations appear. Periodic 60s asyncio task during market hours. Full-universe input pipe active (DEC-299): ~8,000 symbols fetched from FMP stock-list, ~3,000–4,000 viable after system filters. Reference data file cache (DEC-314) with JSON persistence, atomic writes, and per-symbol staleness tracking enables incremental warm-up (~2–5 min vs ~27 min full fetch). Periodic cache saves every 1,000 symbols during fetch + save on shutdown signal (DEC-317, Sprint 23.7) prevent data loss on interrupted cold-starts. Cache checkpoint merge fix (DEC-361, Sprint 25.9): checkpoints write union of existing + fresh entries, preventing data-destructive overwrites during interrupted fetches. Trust-cache-on-startup (DEC-362, Sprint 25.9): `trust_cache_on_startup: true` (default) loads cached reference data immediately at startup, spawns background asyncio task to refresh stale entries post-startup with atomic routing table rebuild on completion. Resolves DEF-063.
- **Broker Abstraction:** IBKRBroker (live, via `ib_async`), AlpacaBroker (incubator), SimulatedBroker (backtest). Atomic bracket orders (DEC-117). Config-driven selection via BrokerSource enum (DEC-094). All brokers implement `cancel_all_orders()` (DEC-364, Sprint 27.65): IBKRBroker calls `reqGlobalCancel()`, used in shutdown sequence and emergency cleanup. `scripts/ibkr_close_all_positions.py` — operational script for manual position cleanup via IB Gateway.
- **Backtesting:** VectorBT (parameter sweeps, precompute+vectorize mandated DEC-149) + Replay Harness (production code replay) + PatternBacktester (generic sliding-window backtester for PatternModule patterns, Sprint 26) + VectorBT R2G (dedicated R2G backtester, Sprint 26) + **BacktestEngine** (Sprint 27: production-code backtesting via SynchronousEventBus, Databento OHLCV-1m + Parquet cache via HistoricalDataFeed, bar-level fill model with worst-case-for-longs priority, multi-day orchestration, scanner simulation, CLI entry point; walk-forward integration via `oos_engine` parameter selects BacktestEngine vs Replay Harness; Sprint 27.5: `to_multi_objective_result()` produces regime-tagged `MultiObjectiveResult`, optional `slippage_model_path` on BacktestEngineConfig). Walk-forward validation mandatory, WFE > 0.3 (DEC-047). Sprint 21.6 additions: `risk_overrides` dict on BacktestEngineConfig for single-strategy backtesting (DEC-359); VectorBT dual file naming support (`{YYYY-MM}.parquet` + `{SYMBOL}_{YYYY-MM}.parquet`); symbol auto-detection from cache directory when `symbols=None`. Revalidation script: `scripts/revalidate_strategy.py`.
- **Evaluation Framework (Sprint 27.5):** `MultiObjectiveResult` (`analytics/evaluation.py`) — universal evaluation currency capturing primary metrics (Sharpe, drawdown, profit factor, win rate, trades, expectancy), per-regime `RegimeMetrics` breakdown (string-keyed for Sprint 27.6 `RegimeVector` forward-compat), `ConfidenceTier` (HIGH/MODERATE/LOW/ENSEMBLE_ONLY), walk-forward efficiency, optional `execution_quality_adjustment`. `from_backtest_result()` factory bridges `BacktestResult` → `MultiObjectiveResult`. Comparison API (`analytics/comparison.py`) — `compare()` returns `ComparisonVerdict` (DOMINATES/DOMINATED/INCOMPARABLE/INSUFFICIENT_DATA), `pareto_frontier()` filters to HIGH/MODERATE confidence, `soft_dominance()` with configurable tolerance, `is_regime_robust()` checks positive expectancy across minimum regime count. Ensemble evaluation (`analytics/ensemble_evaluation.py`) — `EnsembleResult` with aggregate portfolio-level metrics, `MarginalContribution` per strategy via leave-one-out recomputation, `diversification_ratio`, `tail_correlation`, `evaluate_cohort_addition()`, `identify_deadweight()`. Metric-level approximations documented; trade-level upgrade deferred to Sprint 32.5. Slippage model (`analytics/slippage_model.py`) — `StrategySlippageModel` calibrated from `execution_records` table, time-of-day buckets (ET), size adjustment slope, confidence tiers, JSON persistence.
- **Event Bus:** FIFO per subscriber, monotonic sequence numbers, no priority queues. In-process asyncio only (DEC-025).
- **Order Manager:** Event-driven (tick-subscribed for open positions) + 5-second fallback poll + scheduled EOD flatten (DEC-030). ExecutionRecord logging (Sprint 21.6, DEC-358 §5.1) captures expected vs actual fill price on every entry fill for slippage model calibration. Fire-and-forget — exceptions logged at WARNING, never disrupts order management. Data persisted to `execution_records` table (16 columns, 4 indexes). **Sprint 27.65 safety additions:** `_flatten_pending` guard (DEC-363) prevents duplicate flatten orders by tracking in-flight flatten order IDs per symbol — clears on fill, cancel, reject, or position close. Bracket leg amendment on fill slippage (DEC-366): after entry fill, if actual fill price differs from signal entry by >$0.01, cancels and resubmits stop/target legs with delta-shifted prices (stop first for safety). Real-time P&L publishing: on each tick for open positions, computes unrealized P&L and R-multiple, publishes `PositionUpdatedEvent` via event bus (throttled to 1/sec/symbol). `ReconciliationResult` dataclass for typed position reconciliation state.

### Tech Stack
- **Backend:** Python 3.11+, FastAPI (in-process Phase 12 startup, DEC-099), aiosqlite (DEC-034), asyncio Event Bus
- **Frontend:** React + TypeScript, TanStack Query, Zustand, Framer Motion, TradingView Lightweight Charts + Recharts + D3 (DEC-104/215) + Three.js r128 (Observatory 3D views, code-split), Tailwind CSS v4
- **Desktop/mobile:** Tauri v2 desktop, PWA (iPhone/iPad) (DEC-080)
- **Testing:** pytest + Vitest (DEC-130), ruff linting
- **Config:** YAML → Pydantic BaseModel validation (DEC-032)
- **IDs:** ULIDs via `python-ulid` (DEC-026)
- **Infra:** GitHub (public repo), Databento ($199/mo active), FMP Starter ($22/mo, Sprint 21.7), IBKR paper trading active

### File Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus, Regime Intelligence
├── strategies/     # Base class + individual strategy modules + patterns/ package
│   └── patterns/   # PatternModule ABC, BullFlagPattern, FlatTopBreakoutPattern
├── data/           # Scanner, Data Service, Indicators, IndicatorEngine, Universe Manager, FMP Reference
├── execution/      # Broker abstraction, Order Manager
├── analytics/      # Trade Logger, Performance Calculator, Debrief Export, Evaluation Framework
├── backtest/       # VectorBT helpers, Replay Harness, BacktestEngine (Sprint 27)
├── ui/             # React frontend (Vite + TypeScript)
├── api/            # FastAPI REST + WebSocket
├── ai/             # Claude API integration (Sprint 22+)
├── intelligence/   # CatalystPipeline, CatalystClassifier, CatalystStorage, BriefingGenerator (Sprint 23.5)
├── config/         # YAML config files (system.yaml, system_live.yaml, strategies/, regime.yaml)
└── tests/          # pytest + Vitest
```

### Naming Conventions
Strategy files: `snake_case.py` → classes: `PascalCase`. Config: `snake_case.yaml`. DB tables: `snake_case`. Constants: `UPPER_SNAKE_CASE`.

---

## Active Strategies

| # | Strategy | Window | Hold | Key Mechanic |
|---|----------|--------|------|-------------|
| 1 | ORB Breakout | 9:35–11:30 AM | 1–15 min | Opening range break, OR midpoint stop |
| 2 | ORB Scalp | 9:45–11:30 AM | 10s–5 min | Quick 0.3R target, 120s hold |
| 3 | VWAP Reclaim | 10:00 AM–12:00 PM | 5–30 min | Mean-reversion, 5-state machine, OOS Sharpe 1.49 |
| 4 | Afternoon Momentum | 2:00–3:30 PM | 15–60 min | Consolidation breakout, 8 entry conditions |
| 5 | Red-to-Green | 9:35–11:30 AM | 1–15 min | Gap-down reversal at key levels (VWAP, premarket low, prior close), 5-state machine |
| 6 | Bull Flag | 10:00–15:00 | 5–30 min | Pole+flag+breakout continuation pattern (PatternModule) |
| 7 | Flat-Top Breakout | 10:00–15:00 | 5–30 min | Resistance cluster breakout pattern (PatternModule) |

Cross-strategy: ALLOW_ALL (DEC-121/160). Time windows largely non-overlapping. 5% max single-stock exposure across all strategies. 7 strategies across 3 families (ORB, reversal, continuation/breakout). ORB family shares OrbBaseStrategy ABC (DEC-120) with same-symbol mutual exclusion — first ORB strategy to fire on a symbol blocks the other for the day (DEC-261). Bull Flag and Flat-Top Breakout use PatternModule ABC via PatternBasedStrategy wrapper (Sprint 26). All 7 strategies allow `bearish_trending` regime (DEC-360, Sprint 25.9); only `crisis` remains as a universal block. Per-signal time stops (DEC-122). Zero-R signal guard (Sprint 27.65): all strategies suppress signals where `abs(target - entry) < $0.01` via `BaseStrategy._has_zero_r()`.

### Pipeline Stages
Concept → Exploration (VectorBT) → Validation (Replay + WF) → Ecosystem Replay → Paper (20–30 days) → Live Min → Live Full → Active → Suspended → Retired

---

## Risk Limits (Defaults)

Per-trade risk: 0.5–1% of strategy allocation. Daily loss limit: 3–5%. Weekly loss limit: 5–8%. Cash reserve: 20% minimum. Max single-stock: 5%. Max single-sector: 15%. Circuit breakers non-overridable. Concentration limit uses approve-with-modification (DEC-249).

---

## Active Constraints

- **PDT Rule:** Active as of Feb 2026. $25K minimum for margin day trading.
- **Wash Sale Rule:** Must be tracked automatically for tax compliance.
- **Databento session limit:** 10 simultaneous per dataset on Standard. ARGUS uses 1 with Event Bus fan-out.
- **IBKR Gateway:** Requires running Java process. Nightly resets need automated reconnection (RSK-022).
- **Pre-Databento backtests provisional:** All pre-Databento parameter optimization requires re-validation (DEC-132). PARTIALLY RESOLVED (Sprint 21.6) — pipeline proven end-to-end, Bull Flag validated (Sharpe 2.78), 6 strategies pending full-universe re-validation.
- **No live L2/L3 on Standard plan:** Requires Plus tier $1,399/mo (DEC-237).
- **Databento EQUS.MINI historical lag:** Multi-day lag for daily bars (DEC-247). **Resolved by Sprint 21.7:** FMP Scanner now provides dynamic pre-market symbol selection via gainers/losers/actives endpoints.
- **Latency from Cape Town:** ~200–250ms to US exchanges. Scalping has structural disadvantages; longer-duration strategies (5–30 min holds) preferred.
- **Secrets:** All API keys in encrypted secrets manager, never in code/git.
- **FMP Starter plan news restriction:** FMP news endpoints (`stock_news`, `press_releases`) return HTTP 403 on Starter plan ($22/mo). `fmp_news.enabled: false` in `system_live.yaml`. FMP news circuit breaker (DEC-323) prevents request spam if accidentally enabled. Upgrade to Premium ($59/mo) would resolve.
- **Audit:** Every action logged immutably.

---

## Monthly Costs

| Item | Cost | Status |
|------|------|--------|
| Databento US Equities Standard | $199/mo | Active |
| FMP Starter (pre-market scanning) | $22/mo | Sprint 21.7 activation (DEC-258) |
| IBKR commissions | ~$43/day at scale | Paper trading (no cost yet) |
| Claude API | ~$35–50/mo | Active (Sprint 22, DEC-274) |
| Finnhub Free | $0/mo | Sprint 23.5 activation (DEC-306) |
| IQFeed (forex/breadth, future) | ~$160–250/mo | Deferred (DEF-011) |
| Databento Plus (live L2/L3) | $1,399/mo | Post-revenue (DEC-238) |

---

## Key Active Decisions (Quick Reference)

*Full rationale: `docs/decision-log.md`. Full index: `docs/dec-index.md`.*

**Foundational:** DEC-025 (Event Bus FIFO), DEC-027 (Risk Manager modifications), DEC-028 (strategy statefulness), DEC-029 (Event Bus sole streaming), DEC-032 (Pydantic config), DEC-047 (walk-forward mandatory), DEC-079 (parallel tracks), DEC-082 (Databento primary), DEC-083 (IBKR sole broker), DEC-098 (Claude Opus), DEC-132 (re-validation required).

**Data & Execution:** DEC-088 (Databento threading), DEC-090 (DataSource enum), DEC-094 (BrokerSource enum), DEC-117 (atomic brackets), DEC-237 (no live L2 on Standard), DEC-248 (EQUS.MINI confirmed), DEC-249 (concentration approve-with-modification), DEC-257 (hybrid Databento+FMP architecture), DEC-258 (FMP Starter for scanning), DEC-263 (full-universe strategy-specific monitoring), DEC-298 (FMP stable API migration), DEC-299 (full-universe input pipe via stock-list). DEC-251 (absolute risk floor), DEC-252 (price rounding), DEC-261 (ORB exclusion).

**Frontend:** DEC-099 (in-process API), DEC-102 (JWT auth), DEC-104/215 (chart libraries), DEC-109 (design north star), DEC-149 (VectorBT precompute+vectorize), DEC-169 (7-page architecture), DEC-170 (AI Copilot), DEC-199 (navigation + shortcuts).

**AI Layer:** DEC-264 (full scope Sprint 22), DEC-265 (WebSocket streaming), DEC-266 (calendar-date conversation keying), DEC-267 (proposal TTL + DB persistence), DEC-268 (per-page context injection), DEC-269 (demand-refreshed insight card), DEC-270 (markdown rendering stack), DEC-271 (tool_use for proposals), DEC-272 (5-type action enumeration), DEC-273 (system prompt + guardrails), DEC-274 (per-call cost tracking), DEC-276 (ET timestamps for AI layer).

**Universe Manager:** DEC-263 (full-universe monitoring architecture), DEC-277 (fail-closed on missing reference data).

**NLP Catalyst Pipeline:** DEC-300 (config-gated feature), DEC-301 (rule-based fallback classifier), DEC-302 (headline hash deduplication), DEC-303 (daily cost ceiling enforcement), DEC-304 (three-source architecture), DEC-305 (TanStack Query hooks), DEC-306 (Finnhub free tier for news), DEC-307 (Intelligence Brief view).

**Pipeline Hardening (Sprint 23.8):** DEC-319 (wait_for timeout), DEC-320 (polling task health monitoring), DEC-321 (watchlist symbol scope), DEC-322 (source socket timeouts), DEC-323 (FMP circuit breaker), DEC-324 (cost ceiling enforcement), DEC-325 (classifier None guards), DEC-326 (Databento warm-up clamp), DEC-327 (firehose architecture deferred), DEC-328 (test suite tiering).

**Frontend + Test Cleanup (Sprint 23.9):** DEC-329 (gate frontend intelligence hooks on pipeline health status).

**Setup Quality Engine (Sprint 24):** DEC-330 (SignalEvent enrichment + ORB pattern strength), DEC-331 (VWAP/AfMo pattern strength + OM share_count=0 guard), DEC-332 (firehose source refactoring), DEC-333 (SetupQualityEngine 5-dimension scoring), DEC-334 (DynamicPositionSizer + config models), DEC-335 (config wiring + quality_engine.yaml + quality_history table), DEC-336 (pipeline wiring + RM check 0 + quality history recording), DEC-337 (integration tests + error paths), DEC-338 (server quality component init + firehose pipeline wiring), DEC-339 (quality API routes — 3 endpoints), DEC-340 (quality UI — QualityBadge + hooks + trades integration), DEC-341 (quality UI — dashboard/orchestrator/performance/debrief panels).

**Strategy Observability (Sprint 24.5):** DEC-342 (strategy evaluation telemetry — ring buffer + SQLite persistence + REST endpoint + Decision Stream frontend).

**Pipeline Integration (Sprint 23.6):** DEC-308 (deferred initialization), DEC-309 (separate catalyst.db), DEC-310 (CatalystConfig in SystemConfig), DEC-311 (semantic dedup), DEC-312 (batch-then-publish), DEC-313 (FMP canary test), DEC-314 (reference data cache), DEC-315 (polling loop).

**Startup Scaling (Sprint 23.7):** DEC-316 (time-aware warm-up — skip pre-market, lazy mid-session), DEC-317 (periodic cache saves every 1,000 symbols), DEC-318 (API port guard + double-bind fix).

**Documentation:** DEC-262 (roadmap consolidation — single canonical roadmap.md), DEC-275 (compaction risk scoring system).

**Watchlist Wiring (Sprint 25.5):** DEC-343 (watchlist population from UM routing — `set_watchlist(symbols, source="universe_manager")` after `build_routing_table()` in Phase 9.5, `_watchlist` list→set for O(1) lookups), DEC-344 (zero-evaluation health warning — `HealthMonitor.check_strategy_evaluations()` detects populated watchlist + zero evaluations, DEGRADED status, self-correcting).

**Bug Sweep (Sprint 25.6):** DEC-345 (evaluation telemetry DB separation — `data/evaluation.db`), DEC-346 (periodic regime reclassification — 300s interval, market hours only, `Orchestrator.reclassify_regime()` public method).

**Post-Session Operational Fixes (Sprint 25.7):** DEC-347 (FMP daily bars for regime classification — `fetch_daily_bars()` via FMP stable API), DEC-348 (automated debrief data export at shutdown — `debrief_export.py`), DEC-349 (performance throttler zero-trade-history guard), DEC-350 (entry evaluation conditions_passed metadata in ORB telemetry).

**API Auth + Close-Position Fix (Sprint 25.8):** DEC-351 (API auth 401 for unauthenticated requests — `HTTPBearer(auto_error=False)`), DEC-352 (close-position endpoint routes through `OrderManager.close_position()`).

**Phase 5 Gate (March 2026):** DEC-353 (historical data purchase deferred — free OHLCV-1m on Standard plan), DEC-354 (Phase 6 compression — BacktestEngine to Sprint 27), DEC-355 (Gate 2 day counter reset), DEC-356 (FMP Premium deferred until Learning Loop data).

**Amendment Adoption (March 2026):** DEC-357 (Experiment Infrastructure amendment — Sprints 27.5 + 32.5 adopted; mods: API-based veto, SQLite interim storage), DEC-358 (Intelligence Architecture amendment — Sprints 27.6 + 27.7 + 33.5 adopted; execution quality mods to 21.6 + 27.5; historical data confirmed: XNAS.ITCH + XNYS.PILLAR OHLCV-1m back to May 2018 at $0). DEC ranges reserved: 363–372 (27.5), 369–378 (27.6), 379–385 (27.7), 386–395 (32.5), 396–402 (33.5). Amendment documents: `docs/amendments/`.

**Backtest Re-Validation (Sprint 21.6):** DEC-359 (BacktestEngine risk overrides for single-strategy backtesting — permissive defaults via `risk_overrides` dict, production paths unaffected).

**Operational Resilience (Sprint 25.9):** DEC-360 (bearish_trending added to all 7 strategies' allowed_regimes — prevents dead sessions), DEC-361 (cache checkpoint merge fix — writes union of existing + fresh entries), DEC-362 (trust cache on startup — non-blocking startup with background refresh, resolves DEF-063).

**Market Session Safety (Sprint 27.65):** DEC-363 (flatten-pending guard — `_flatten_pending` dict tracks in-flight flatten orders per symbol, prevents duplicate SELL orders on time-stop retry loop), DEC-364 (graceful shutdown order cancellation — `cancel_all_orders()` on Broker ABC, IBKRBroker calls `reqGlobalCancel()` before disconnect), DEC-365 (periodic position reconciliation — 60s async task compares OrderManager internal state vs IBKR actual positions, warn-only, `GET /api/v1/positions/reconciliation` endpoint), DEC-366 (bracket leg amendment on fill slippage — delta-based recalculation of stop/target after entry fill, stop resubmitted first, safety flatten if T1 ≤ fill price), DEC-367 (optional concurrent position limits — `max_concurrent_positions: 0` disables check, paper trading configs set to 0), DEC-368 (IntradayCandleStore — centralized queryable intraday bar accumulator, parallel CandleEvent subscriber, 390 bars/symbol max, market-hours filter, replaces synthetic bar fallback).

**Superseded (do not use):** DEC-031 (IBKR deferral → DEC-083), DEC-089 (XNAS.ITCH → DEC-248), DEC-097 (activation timing → DEC-143/161), DEC-165 (L2 included → DEC-237), DEC-234 (XNAS+XNYS phased → DEC-248).

---

## Workflow

**Three-tier architecture:** Claude.ai handles strategic design, architectural
review, and planning. Claude Code handles implementation and review execution.
The Autonomous Sprint Runner (Python orchestrator) coordinates the execution
loop between Claude Code sessions, making deterministic proceed/halt decisions
based on structured output. Git is the bridge between all tiers.

In **autonomous mode**, the runner drives the full execution loop. Claude.ai is
invoked only for sprint planning, adversarial review, Tier 3 escalation
resolution, and strategic check-ins. In **human-in-the-loop mode**, the
developer manually drives sessions while the runner optionally provides
structured logging and record-keeping.

All significant decisions logged with sequential DEC numbers. Deferred items tracked in CLAUDE.md.

**Autonomous Runner (DEC-278, Sprint 23.2):** Python-based orchestrator at
`scripts/sprint-runner.py` (thin entry point importing from `workflow/runner/`
submodule). 13 modules, 210 tests. Reads sprint package, invokes Claude Code CLI
per session, parses structured close-out and review verdicts, makes rule-based
proceed/halt decisions, and maintains full run-log on disk. Supports resume
from any checkpoint and parallel session execution. Notifications via ntfy.sh
(DEC-279). Tier 2.5 automated triage for scope gaps and prior-session bugs
(DEC-282). Spec conformance check at session boundaries (DEC-283). Cost tracking
with configurable ceiling (DEC-287). Independent test verification (DEC-291),
pre-session file validation (DEC-292), compaction detection heuristic (DEC-293),
and session boundary diff validation (DEC-294) provide defense-in-depth between
sessions. See `workflow/protocols/autonomous-sprint-runner.md`.

Universal protocols, templates, and the runner live in the `workflow/` submodule
(https://github.com/stevengizzi/claude-workflow). ARGUS-specific rules remain in
`.claude/rules/`.

**Sprint methodology:** Sprint spec → session prompts → Claude Code implementation → code review → polish → doc sync. By Sprint 18+, evolved into comprehensive "sprint packages" (spec + prompts + review plans + doc updates in one conversation).

**Review workflow:** Three-tier system — close-out review, Tier 2 implementation review, Tier 3 architectural review in Claude.ai. See `.claude/rules/` for protocols.

**Compaction risk scoring (DEC-275):** Sessions are scored across 7 factors (files created, files modified, context reads, tests, integration wiring, external API debugging, large files) with point thresholds: 0–8 Low, 9–13 Medium, 14–17 High (must split), 18+ Critical (split into 3+). Calibrated against Sprint 22 empirical compaction data. Session Breakdown artifact includes full scoring table per session.

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| `docs/project-bible.md` | Source of truth — what and why |
| `docs/project-knowledge.md` | This file (Claude context) |
| `docs/architecture.md` | Technical blueprint — how |
| `docs/roadmap.md` | Strategic vision + sprint queue (DEC-262) |
| `docs/sprint-campaign.md` | Operational sprint choreography |
| `docs/decision-log.md` | All 368 DEC entries with full rationale (6 new in Sprint 27.65) |
| `docs/dec-index.md` | Quick-reference DEC index with status |
| `docs/sprint-history.md` | Complete sprint history (1–27 + 21.6 + 25.9 + 27.5 + 27.6 + 27.65) |
| `docs/process-evolution.md` | Workflow evolution narrative |
| `docs/risk-register.md` | Assumptions and risks |
| `docs/live-operations.md` | Live trading procedures |
| `docs/protocols/market-session-debrief.md` | Post-market diagnostic runbook (7-phase: session boundaries → startup health → data flow → strategy pipeline → catalysts → error catalog → synthesis) |
| `CLAUDE.md` | Claude Code session context |
| `docs/ui/ux-feature-backlog.md` | Planned UI features |
| `docs/strategies/STRATEGY_*.md` | Per-strategy spec sheets |
| `workflow/` | Claude-workflow metarepo (protocols, templates, runner) |

---

## Communication Style

The user prefers thorough, detailed explanations and expects structured outputs ready for copy-paste. He appreciates proactive pushback and concerns. He values clarifying questions before assumptions. He wants the *why* behind every recommendation. He is building this for his family's financial future — treat every decision with the seriousness that implies. Direct, technically precise communication.
