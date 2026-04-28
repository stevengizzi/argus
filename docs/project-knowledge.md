# ARGUS — Project Knowledge (Claude Context)

> *Tier A operational context for Claude Code and Claude.ai. Last updated: April 24, 2026 (Sprint 31.9 campaign-close — A1 short-flip fix validated, DEF-204 mechanism identified).*
> *Full decision rationale: `docs/decision-log.md` | Sprint details: `docs/sprint-history.md` | DEC index: `docs/dec-index.md`*

---

## What Is ARGUS

ARGUS is a fully automated, AI-enhanced multi-strategy day trading system for US equities. It combines rules-based strategy execution with planned AI-powered setup quality grading, NLP catalyst analysis, and dynamic position sizing. Built in Python (FastAPI backend) with a React/TypeScript Command Center frontend (Tauri desktop + PWA mobile). The user is building this to generate household income for his family. He operates from the US East Coast (ET), trading US markets during regular hours. He can code in Python and has trading experience but no prior algorithmic trading system.

## Current State

**Tests:** 5,080 pytest (--ignore=tests/test_main.py) + 39 pass / 5 skip on tests/test_main.py + 866 Vitest. Sprint 31.9 net delta: +146 pytest, +20 Vitest. Known flakes: DEF-150 (time-of-day arithmetic, first 2 min of every hour) + DEF-167 (Vitest hardcoded-date scan) + DEF-171 (ibkr_broker xdist) + DEF-190 (pyarrow/xdist register_extension_type race) + DEF-192 (runtime warning cleanup debt, ~25–27 warnings, xdist-order-dependent within categories). DEF-205 (pytest date-decay sibling of DEF-167) RESOLVED by TEST-HYGIENE-01 on 2026-04-24. Treat all listed flakes as pre-existing.
**Sprints completed:** 1 through 29 + 21.6 + 25.9 + 27.5 + 27.6 + 27.65 + 27.7 + 27.75 + 27.8 + 27.9 + 27.95 + 28.5 + 28.75 + 29.5 + 32 + 32.5 + 32.75 + 32.8 + 32.9 + 32.95 + impromptu hotfix Apr 3 + 31A + 31A.5 + 31A.75 + 31.5 + 31.75 + 31.8 + 31.85 + 31.9 (35 full sprints incl. campaign-close phase + 45 sub-sprints + 10 impromptus + 11 campaign-close sessions + 3 paper-session debriefs)
**Active sprint:** Between sprints. **Sprint 31.9 (Health & Hardening campaign-close) sealed on 2026-04-24.** 22 shadow variants collecting CounterfactualTracker data. Parquet consolidation script delivered (Sprint 31.85); operator repoint of `config/historical_query.yaml` pending. **Next sprint:** operator-decided ordering between (a) `post-31.9-reconciliation-drift` (CRITICAL safety per DEF-204 mechanism identified by IMPROMPTU-11), (b) `post-31.9-component-ownership` (DEF-175/182/193/201/202), (c) `post-31.9-reconnect-recovery-and-rejectionstage` (DEF-194/195/196/177/184), (d) `post-31.9-alpaca-retirement` (DEF-178/183), (e) Sprint 31B (Research Console / Variant Factory). Operational mitigation in effect until DEF-204 lands: operator runs `scripts/ibkr_close_all_positions.py` daily.
**GitHub:** `https://github.com/stevengizzi/argus.git` (public)

### Sprint History (Summary)

Sprints 1–28 (Feb 14 – Mar 29): see `docs/sprint-history.md` for full detail. Recent sprints:

| Sprint | Name | Tests | Date | Key DECs |
|--------|------|-------|------|----------|
| 28.5 | Exit Management | 3955+680V | Mar 30 | — |
| 28.75 | Post-Session Operational + UI Fixes (Impromptu) | 3966+688V | Mar 30 | — |
| 29 | Pattern Expansion I | 4178+689V | Mar 30–31 | — |
| 29.5 | Post-Session Operational Sweep | 4212+700V | Mar 31–Apr 1 | — |
| 32 | Parameterized Templates + Experiment Pipeline | 4405+700V | Apr 1 | — |
| 32.5 | Experiment Pipeline Completion + Visibility | 4489+711V | Apr 1 | — |
| 32.75 | The Arena + UI/Operational Sweep | 4530+805V | Apr 2 | — |
| 32.8 | Arena Latency + UI Polish Sweep | 4539+846V | Apr 2 | — |
| 32.9 | Operational Hardening + Position Safety + Quality Recalibration | 4579+846V | Apr 2 | — |
| 32.95 | Debrief Export Enhancement | 4582+846V | Apr 2 | — |
| (Impromptu Apr 3) | Good Friday Incident — Observability + Holiday Detection | 4674+846V | Apr 3 | — |
| 31A | Pattern Expansion III (DEF-143/144, PMH fix, 3 new patterns, 10-pattern sweep) | 4811+846V | Apr 3 | — |
| 31A.5 | Historical Query Layer — DuckDB Phase 1 (Impromptu) | 4811+846V | Apr 3 | — |
| 31A.75 | Universe-Aware Sweep Flags (Impromptu) | 4823+846V | Apr 3 | — |
| 31.5 | Parallel Sweep Infrastructure | 4857+846V | Apr 3 | — |
| (Impromptu Apr 3–5) | DEF-151 Fix + Sweep Impromptu | 4858+846V | Apr 3–5 | — |
| 31.75 | Sweep Infrastructure Hardening (22 shadow variants deployed) | 4919+846V | Apr 14–20 | DEC-382–383 |
| 31.8 | April 20 Impromptus (Lifespan + VACUUM + Dup-SELL + Recon-Trades) | 4919+846V | Apr 20 | — |
| 31.85 | Parquet Cache Consolidation (DEF-161 resolved) | 4934+846V | Apr 20 | — |
| (Audit Phase 3 in progress) | FIX-00/15/17/20/01/11/02/12/03/21/14 + IMPROMPTU-def172-173-175 | 4965+859V | Apr 21–22 | DEC-384 (FIX-01 standalone overlay registry) |
| 31.9 | Health & Hardening Campaign-Close (A1 short-flip fix validated, DEF-204 mechanism identified, RETRO-FOLD P1–P25) | 5080+866V | Apr 22–24 | — (no new DECs) |

*Full sprint scopes and session details: `docs/sprint-history.md`*

### Build Track Queue

**Next 5 sprints (priority order):**
1. **31B (Research Console / Variant Factory)** — reframed as fast Stage 1 screen: generate configs → quick-reject backtest → push survivors to shadow.
2. **Post-31.9 Component Ownership Refactor** (DEF-175) — dedicated sprint migrating `CatalystStorage` / `SetupQualityEngine` / `DynamicPositionSizer` / `ExperimentStore` construction out of `api/server.py` lifespan into `ArgusSystem` Phase 9.x.
3. **30** (Short Selling) — deferred until longs profitable.
4. **33** (Statistical Validation) — applied to shadow-proven configs, not raw grid sweeps.
5. **33.5** (Adversarial Stress Testing).

**Horizon:** 34 (FRED Macro, DEF-148) → 35–42 (Cross-Family Search, Ensemble Orchestrator V2, Synapse, Learning Loop V2, Continuous Discovery, Performance Workbench).

**Current state:** 22 shadow variants collecting CounterfactualTracker data. All build-track history, completed-sprint annotations, and roadmap rationale have been relocated to `docs/roadmap.md`.

### Validation Track

Paper trading active with Databento EQUS.MINI + IBKR paper (Account U24619949, DEC-236). Gates: IBKR paper 20+ days (Gate 2) → AI-enhanced paper 30+ days (Gate 3) → Full system paper 50+ cumulative days, Sharpe > 2.0 (Gate 4) → live minimum size (Gate 5). CPA consultation removed per DEC-380; tax intelligence built into ARGUS as post-revenue automation.

### Expanded Vision (DEC-163, DEC-262, April 2026 strategic reframe)

ARGUS evolves into a fully autonomous evolutionary ecosystem of hundreds to thousands of strategy variants running simultaneously. The architecture is non-zero-sum — each variant is an independent agent that fires when its conditions are met, and any number can be live simultaneously. Capital allocation (Risk Manager concentration limits + overflow routing) manages aggregate exposure, but does not pick winners.

**Three phases of repertoire growth:**
1. **Parameterized variants** (Sprint 32): Take existing PatternModule templates and spawn multiple parameterized variants. Each variant runs in shadow or live mode. The repertoire only grows — variants are never deleted, just promoted/demoted between live and shadow.
2. **Standalone strategy retrofit** (~Sprint 33): Bring the 5 non-PatternModule strategies (ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, Red-to-Green) into the same variant framework.
3. **Novel strategy discovery** (Sprint 36+ Continuous Discovery Pipeline): ARGUS invents new detection logic by analyzing market data patterns, not just optimizing human-designed templates.

**Validation model:** Backtesting is a pre-filter that prevents obviously bad variants from wasting shadow compute. The real validation gate is live shadow performance via CounterfactualTracker — a variant earns promotion to live only after sustained demonstrated edge in actual market conditions. This inverts the traditional workflow (backtest → paper → live) into a continuous parallel evaluation.

**Autonomous promotion:** The system promotes and demotes variants autonomously during paper trading. The advisory approval workflow from Learning Loop V1 is a training wheel — by the time ARGUS transitions to live trading, the autonomous loop should have a proven track record. The switch to live trading IS the confidence gate for full autonomy.

**Intraday adaptation** at multiple levels: individual strategy parameter awareness (startup-loaded, intraday mode changes), capital allocation across strategies (Orchestrator regime awareness), and eventually microstructure-informed decisions (post-revenue L2/L3 data, DEC-238).

**Soft risk limits:** Hard floors for catastrophic protection (circuit breakers non-overridable), but soft limits (position sizing, concentration, daily loss thresholds) that the system earns the right to expand based on its track record.

**Operator's daily routine:** Zero required interaction. ARGUS runs as a fully automatic process. The operator receives pings throughout the day and optionally checks in to see positions, intelligence at work, real-time decision-making rationale, the Synapse visualization of the full strategy landscape, intelligence history reports (both quantitative dashboards and narrative briefings), and individual strategy track records over time. Manual overrides available but rarely used.

**Completed infrastructure:** Canonical inventory lives in `CLAUDE.md` § Current State (structured by layer). Briefly: Setup Quality Engine + DEC-384 standalone overlay registry, NLP Catalyst Pipeline, Dynamic Position Sizer, Evaluation Framework (regime-tagged MultiObjectiveResult + slippage model), Regime Intelligence V2 (11-field RegimeVector + VIX calculators), Counterfactual Engine, Learning Loop V1, Exit Management, BacktestEngine + MFE/MAE, Experiment Pipeline (pattern factory + fingerprinting + autonomous promotion/demotion), The Arena (10-page Command Center), Operational Hardening (EOD flatten sync, margin circuit breaker, pre-EOD signal cutoff), NYSE Holiday Calendar, OHLCV-1m observability, DuckDB HistoricalQueryService, universe-aware sweep flags, Parquet cache consolidation tooling. See `docs/sprint-history.md` for per-sprint attribution.

**Next:** 22 shadow variants collecting CounterfactualTracker data during paper trading. See *Build Track Queue* above and `docs/roadmap.md` for full priority list.

---

## Architecture

### Three-Tier System
1. **Trading Engine** — Strategies, Orchestrator, Risk Manager, Data Service, Broker abstraction, Order Manager, Trade Logger, Backtesting (VectorBT + Replay Harness)
2. **Command Center** — 10 pages (all built): Dashboard, Trade Log (with Shadow Trades tab), Performance, The Arena, Orchestrator, Pattern Library, The Debrief, System, Observatory, Experiments. Tauri desktop + PWA mobile + web. AI Copilot active. Keyboard shortcuts 1–9 + 0 (0 = Experiments, 4 = The Arena); `l`/`s` hotkeys for Trade Log tab switching. All 15 strategies have unique colors, badge glyphs, and single-letter identifiers across all UI components (Sprint 32.75 strategy identity system). **Dashboard (Sprint 32.8):** 4-row layout: VitalsStrip (equity + daily P&L sparkline + today's stats + VIX regime) → Strategy Allocation Bar → Positions Table (70%) + Session Timeline / Signal Quality (30%) → AI Insight + Learning Loop. Row 3 fills remaining viewport height. **Trade Log (Sprint 32.8):** Both Live Trades and Shadow Trades tabs unified to same visual density (compact row height, identical filter bar / stats bar styling). `l`/`s` hotkeys for tab switching. Shadow Trades: outcome toggle, time presets, infinite scroll, 10 sortable columns, reason tooltip.
3. **AI Layer** (Sprint 22) — Claude API (Opus, DEC-098) via ClaudeClient wrapper; PromptManager with system prompt template and behavioral guardrails (DEC-273); SystemContextBuilder for per-page context injection (DEC-268); tool_use for structured action proposals (DEC-271) with 5 defined tools (DEC-272); ActionManager with DB-persisted proposals and 5-min TTL (DEC-267); 5 ActionExecutors with 4-condition pre-execution re-check; ConversationManager with calendar-date keying and tags (DEC-266); UsageTracker for per-call cost tracking (DEC-274); DailySummaryGenerator for insight card + daily summaries; ResponseCache for insight TTL caching. WS /ws/v1/ai/chat for streaming with actual API usage extraction (DEC-265). All timestamps ET-based (DEC-276). All AI features degrade gracefully when ANTHROPIC_API_KEY unset.
4. **Intelligence Layer** (Sprints 23.5 + 23.6 + 24) — CatalystPipeline orchestrates three data sources: SECEdgarSource (8-K, Form 4), FMPNewsSource (stock news, press releases), FinnhubSource (company news, analyst recommendations). CatalystClassifier uses Claude API with rule-based fallback (DEC-301). CatalystStorage with SQLite persistence in separate catalyst.db (DEC-309) and headline hash deduplication (DEC-302). BriefingGenerator produces pre-market intelligence briefs with $5/day cost ceiling (DEC-303). Post-classification semantic dedup by (symbol, category, time_window) before storage (DEC-311). Batch-then-publish ordering for data safety (DEC-312). Config-gated via `catalyst.enabled` (DEC-300). Intelligence startup factory in `argus/intelligence/startup.py` builds all components from config (DEC-308). Polling loop via asyncio task with market-hours-aware intervals (DEC-315). Sprint 23.8 hardened the pipeline: `asyncio.wait_for(120)` safety timeout on source gather (DEC-319), polling task health monitoring via `done_callback` (DEC-320), symbol scope reduced from full viable universe to scanner watchlist (DEC-321), FMP news circuit breaker on 401/403 (DEC-323), cost ceiling enforcement wired into classifier with cycle cost logging (DEC-324), and Databento lazy warm-up `end` clamped to `now - 600s` (DEC-326). FMP canary test at startup validates API schema (DEC-313). Frontend: CatalystBadge, CatalystAlertPanel, IntelligenceBriefView with TanStack Query hooks. Sprint 23.9 added `usePipelineStatus` hook gating all catalyst/briefing queries on pipeline health status from `/api/v1/health` — zero requests when pipeline inactive (DEC-329). DebriefService initialized in `server.py` lifespan (was only wired in dev mode, causing 503 in live mode).
5. **Quality Engine** (Sprints 24 + 24.1) — SetupQualityEngine scores setups on 5 weighted dimensions: pattern strength (30%), catalyst quality (25%), volume profile (20%), historical match (15%), regime alignment (10%). Produces quality_grade (A+ through C) and quality_score (0–100). DynamicPositionSizer maps grades to risk tiers (A+=2–3%, A=1.5%, B=0.75%, C+=0.25%, C-=SKIP). Strategies emit `share_count=0` with `pattern_strength` (0–100); `_process_signal()` in main.py runs quality pipeline (score → filter by minimum grade → size → enrich SignalEvent). Risk Manager check 0 rejects `share_count ≤ 0` before circuit breaker evaluation. Pipeline bypass: `BrokerSource.SIMULATED` or `quality_engine.enabled: false` → legacy sizing. QualitySignalEvent published after scoring (informational). Quality history persisted to `quality_history` table (20 columns, 4 indexes). Quality grade/score wired through Order Manager → TradeLogger → DB (Sprint 24.1). Config: `config/quality_engine.yaml` with Pydantic models (QualityWeightsConfig, QualityThresholdsConfig, QualityRiskTiersConfig) with validators. Firehose mode for catalyst sources: Finnhub single `GET /news?category=general`, SEC EDGAR single EFTS search (DEC-332). API: 3 endpoints (`/api/v1/quality/{symbol}`, `/api/v1/quality/history`, `/api/v1/quality/distribution`). UI: QualityBadge component, quality column in Trades table, Setup Quality in TradeDetailPanel, SignalQualityPanel (histogram) on Dashboard, RecentSignals with clickable SignalDetailPanel on Orchestrator (Sprint 24.1), QualityGradeChart (ComposedChart: bars for Avg P&L + line for Win Rate) on Performance, QualityOutcomeScatter on Performance Distribution tab (relocated from Debrief in Sprint 24.1). Orchestrator uses 3-column layout for Decision Log + Catalyst Alerts + Recent Signals (Sprint 24.1). Shared GRADE_COLORS/GRADE_ORDER constants extracted for consistency.

### Key Components

> Interface-level summaries only. For detail, see `docs/architecture.md` (listed section references). Sprint-tagged implementation history is in `docs/sprint-history.md`.

- **Strategies:** Daily-stateful, session-stateless plugins (DEC-028). 13 live + 2 shadow. BaseStrategy includes `StrategyEvaluationBuffer` (ring buffer, maxlen=1000) for telemetry persisted to `data/evaluation.db` (DEC-345, DEC-342). Arch §3.4.
- **Pattern Library:** PatternModule ABC (10 patterns) + PatternBasedStrategy wrapper + pattern factory (`build_pattern_from_config()`) + PatternParam metadata for sweep grids (Sprint 29 S2, DEC-378). Arch §3.4.4.
- **Observatory:** Read-only query service (4 methods) + `/ws/v1/observatory` push. 4 frontend views (Funnel 3D, Radar 3D, Matrix, Timeline). Arch §13.
- **Regime Intelligence V2:** RegimeClassifierV2 composes V1 delegation with 8 calculators (breadth, correlation, sector, intraday, 4 VIX). 11-field RegimeVector frozen dataclass. Arch §3.6.1.
- **VIX Data Service:** yfinance daily VIX/SPX → SQLite `data/vix_landscape.db` + 5 derived metrics. Config-gated (`vix_regime.enabled`). `GET /api/v1/vix/current` + `/history`. DEF-170 open — calculators stay None in production. Arch §3.6.1 VIX block.
- **Market Calendar:** Pure-algorithmic NYSE holiday calendar (Anonymous Gregorian for Easter). `is_market_holiday()`, `get_next_trading_day()`. Integrated into Orchestrator, HealthMonitor, DatabentoDataService, `GET /api/v1/market/status` (no auth). Arch §3.8.1.
- **Orchestrator:** Rules-based V1 (DEC-118). Public `reclassify_regime()` (300s periodic during market hours, DEC-346). `_is_market_hours()` honors NYSE holidays. `throttler_suspend_enabled` + `orb_family_mutual_exclusion` config flags for paper data capture. Arch §3.6.
- **Risk Manager:** Three-level gating (strategy, cross-strategy, account). Check 0 rejects `share_count ≤ 0` before circuit breaker (DEC-336). Approve-with-modification for shares/target only — never stops or entry (DEC-027). Arch §3.5.
- **Data Service:** Databento EQUS.MINI primary (DEC-248). Event Bus sole streaming mechanism (DEC-029). Time-aware indicator warm-up (DEC-316). OHLCV-1m observability (per-gate drop counters, first-event sentinels). IntradayCandleStore (DEC-368): parallel CandleEvent subscriber, 720 bars/symbol, 4:00 AM–16:00 ET window. Arch §3.2 + §3.8.1.
- **Universe Manager:** FMPReferenceClient + fail-closed semantic filters (DEC-277). Pre-computed routing table, O(1) lookups. `trust_cache_on_startup` + background refresh (DEC-362). `UniverseFilterConfig` Pydantic model with `min_price`/`max_price`/`min_avg_volume`/`min_relative_volume`/`min_gap_percent`/`min_premarket_volume`. Arch §3.7d.
- **Broker Abstraction:** IBKRBroker (live) + AlpacaBroker (incubator) + SimulatedBroker (backtest). Atomic bracket orders (DEC-117). `cancel_all_orders()` on ABC (DEC-364). Arch §3.3 + §3.3c.
- **Backtesting:** VectorBT legacy + Replay Harness + PatternBacktester + **BacktestEngine** (Sprint 27: SynchronousEventBus, Databento Parquet, shared `TheoreticalFillModel`, walk-forward via `oos_engine`, `to_multi_objective_result()`). Full-universe Parquet cache: 24,321 symbols × 153 months, 44.73 GB. Arch §5.
- **Evaluation Framework:** `MultiObjectiveResult` + per-regime `RegimeMetrics` + `ConfidenceTier`. Comparison API (Pareto, soft-dominance, regime-robust). Ensemble evaluation (leave-one-out MarginalContribution). Slippage model from `execution_records`. Arch §14.
- **Counterfactual Engine:** Shadow tracking for rejected signals. `SignalRejectedEvent` + `RejectionStage` enum. CounterfactualTracker (MAE/MFE per bar). SQLite `data/counterfactual.db`. `GET /api/v1/counterfactual/accuracy`. Config-gated. Arch §3.11 Counterfactual block.
- **Learning Loop V1:** OutcomeCollector → WeightAnalyzer (Spearman per-dimension) → ThresholdAnalyzer → CorrelationAnalyzer → LearningService → ConfigProposalManager (atomic YAML writes, 20%/30d drift guard). SQLite `data/learning.db`. 8 REST endpoints. Advisory-only (human approval required). Config-gated (`learning_loop.enabled`). Arch §3.11 Learning Loop block.
- **Event Bus:** FIFO per subscriber, monotonic sequence numbers, in-process asyncio only (DEC-025). Arch §3.1.
- **Order Manager:** Event-driven + 5s fallback poll + EOD flatten (DEC-030). `_flatten_pending` guard (DEC-363), bracket amendment on fill slippage (DEC-366), broker-confirmed reconciliation (DEC-369/370), overflow routing (DEC-375), startup zombie cleanup (DEC-376), flatten circuit breaker (Sprint 29.5), MFE/MAE tracking. Arch §3.7.
- **Exit Management:** Pure-function `core/exit_math.py` (trail stop, escalation, time stop). `config/exit_management.yaml` with per-strategy overrides + `deep_update()` merge. SignalEvent `atr_value` field. Arch §3.11 Exit block.
- **Experiment Pipeline:** Pattern factory + parameter fingerprinting (SHA-256 of canonical JSON of detection params + exit_overrides) + VariantSpawner + ExperimentRunner (parallel via `ProcessPoolExecutor`, universe pre-filter via `HistoricalQueryService`) + PromotionEvaluator (Pareto + hysteresis + SessionEndEvent). SQLite `data/experiments.db`. 3 REST endpoints (variants, promotions, counterfactual positions). 22 shadow variants in `config/experiments.yaml`. Config-gated. Arch §15.
- **Historical Query Service:** DuckDB read-only analytical layer over Parquet cache. 6 query methods; `validate_symbol_coverage()` is the sweep-tooling integration point. 4 REST endpoints. `scripts/query_cache.py` CLI. Config-gated. Arch §3.8.2.
- **The Arena:** 10th Command Center page. REST `/api/v1/arena/positions` + `/candles/{symbol}`. WS `/ws/v1/arena` with 6 message types including `arena_tick_price` (bypasses 1s throttle). Per-connection `trail_stop_cache`. Arch §13.5.

### Tech Stack
- **Backend:** Python 3.11+, FastAPI (in-process Phase 12 startup, DEC-099), aiosqlite (DEC-034), asyncio Event Bus
- **Frontend:** React + TypeScript, TanStack Query, Zustand, Framer Motion, TradingView Lightweight Charts + Recharts + D3 (DEC-104/215) + Three.js r128 (Observatory 3D views, code-split), Tailwind CSS v4
- **Desktop/mobile:** Tauri v2 desktop, PWA (iPhone/iPad) (DEC-080)
- **Analytics:** DuckDB (in-process analytical DB for Parquet queries, `duckdb>=1.0,<2`, Sprint 31A.5)
- **Testing:** pytest + Vitest (DEC-130), ruff linting
- **Config:** YAML → Pydantic BaseModel validation (DEC-032)
- **IDs:** ULIDs via `python-ulid` (DEC-026)
- **Infra:** GitHub (public repo), Databento ($199/mo active), FMP Starter ($22/mo, Sprint 21.7), IBKR paper trading active

### File Structure

See `CLAUDE.md` § Project Structure — authoritative module map.

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
| 5 | Red-to-Green | 9:45–11:00 AM | 1–15 min | Gap-down reversal at key levels (VWAP, premarket low, prior close), 5-state machine |
| 6 | Bull Flag | 10:00–15:00 | 5–30 min | Pole+flag+breakout continuation pattern (PatternModule) |
| 7 | Flat-Top Breakout | 10:00–15:00 | 5–30 min | Resistance cluster breakout pattern (PatternModule) |
| 8 | Dip-and-Rip | 9:45–11:30 AM | 1–15 min | Intraday dip + recovery, volume confirmation, VWAP/level interaction (PatternModule, Sprint 29) |
| 9 | HOD Break | 10:00–15:30 | 5–30 min | Dynamic HOD tracking, ATR consolidation, multi-test resistance, hold-bar breakout (PatternModule, Sprint 29) |
| 10 | Gap-and-Go | 9:35–10:30 AM | 5–15 min | Gap-up continuation, VWAP hold, pullback/direct entry modes (PatternModule, Sprint 29) |
| 11 | ABCD | 10:00–15:00 | 10–45 min | Harmonic swing pattern, Fibonacci validation, leg ratio checking (PatternModule, Sprint 29) — **shadow mode** |
| 12 | Pre-Market High Break | 9:35–10:30 AM | 5–15 min | PM high breakout, PM volume qualification, gap context scoring (PatternModule, Sprint 29); `lookback_bars=400`, `min_detection_bars=10`, reference data wired in main.py Phase 9.5 |
| 13 | Micro Pullback | 10:00–14:00 | 5–30 min | EMA-based impulse→pullback→bounce continuation, self-contained EMA, scoring 30/25/25/20 (PatternModule, Sprint 31A) |
| 14 | VWAP Bounce | 10:30–15:00 | 5–30 min | VWAP support approach→touch→bounce, prior uptrend validation, VWAP from indicators dict, scoring 30/25/25/20 (PatternModule, Sprint 31A) |
| 15 | Narrow Range Breakout | 10:00–15:00 | 5–30 min | Volatility compression → expansion breakout, self-contained ATR, long-only gate, scoring 30/25/25/20 (PatternModule, Sprint 31A) |

Cross-strategy: ALLOW_ALL (DEC-121/160). Time windows largely non-overlapping. 5% max single-stock exposure across all strategies. 15 strategies across 5 families (ORB, reversal, continuation/breakout, harmonic, pullback/bounce). ORB family shares OrbBaseStrategy ABC (DEC-120) with same-symbol mutual exclusion — first ORB strategy to fire on a symbol blocks the other for the day (DEC-261). Exclusion is configurable via `OrchestratorConfig.orb_family_mutual_exclusion` (default `true`); set to `false` for paper trading to enable independent ORB Scalp data capture (Sprint 29.5 S7). 10 of 15 strategies use PatternModule ABC via PatternBasedStrategy wrapper (Sprints 26 + 29 + 31A). All strategies allow `bearish_trending` regime (DEC-360, Sprint 25.9); only `crisis` remains as a universal block. Per-signal time stops (DEC-122). Zero-R signal guard (Sprint 27.65): all strategies suppress signals where `abs(target - entry) < $0.01` via `BaseStrategy._has_zero_r()`. Shadow strategy mode (Sprint 27.7): `StrategyMode` enum (LIVE/SHADOW) with per-strategy `mode` config field (default "live"); shadow-mode signals bypass quality pipeline and risk manager, routed directly to CounterfactualTracker. Flat-Top Breakout and ABCD are in shadow mode awaiting optimization.

### Pipeline Stages
Concept → Exploration (VectorBT) → Validation (Replay + WF) → Ecosystem Replay → Paper (20–30 days) → Live Min → Live Full → Active → Suspended → Retired

---

## Risk Limits (Defaults)

Per-trade risk: 0.5–1% of strategy allocation. Daily loss limit: 3–5%. Weekly loss limit: 5–8%. Cash reserve: 20% minimum. Max single-stock: 5%. Max single-sector: 15%. Circuit breakers non-overridable. Concentration limit uses approve-with-modification (DEC-249). **Paper trading overrides (Sprint 29.5):** `daily_loss_limit_pct: 1.0` and `weekly_loss_limit_pct: 1.0` for maximum data capture; restore to 0.03/0.05 before live. `throttler_suspend_enabled: false` disables PerformanceThrottler suspension; restore to `true` before live.

---

## Active Constraints

- **PDT Rule:** Active as of Feb 2026. $25K minimum for margin day trading.
- **Wash Sale Rule:** Must be tracked automatically for tax compliance.
- **Databento session limit:** 10 simultaneous per dataset on Standard. ARGUS uses 1 with Event Bus fan-out.
- **IBKR Gateway:** Requires running Java process. Nightly resets need automated reconnection (RSK-022). **IBC** automates IBKR Gateway startup/shutdown — see `docs/ibc-setup.md` for launchd template and configuration guide (Sprint 32.75).
- **Pre-Databento backtests provisional:** All pre-Databento parameter optimization requires re-validation (DEC-132). PARTIALLY RESOLVED (Sprint 21.6) — pipeline proven end-to-end, Bull Flag validated (Sharpe 2.78), 6 strategies pending full-universe re-validation. **Data blocker removed** (March 2026): full-universe Parquet cache populated with 24,321 symbols across 96 months (3 datasets). Re-validation runs can proceed using `--cache-dir data/databento_cache`.
- **No live L2/L3 on Standard plan:** Requires Plus tier $1,399/mo (DEC-237).
- **Databento EQUS.MINI historical lag:** Multi-day lag for daily bars (DEC-247). **Resolved by Sprint 21.7:** FMP Scanner now provides dynamic pre-market symbol selection via gainers/losers/actives endpoints.
- **Latency:** Minimal from US East Coast (<10ms). No longer a structural concern for any strategy type.
- **Secrets:** All API keys in encrypted secrets manager, never in code/git.
- **FMP Starter plan news restriction:** FMP news endpoints (`stock_news`, `press_releases`) return HTTP 403 on Starter plan ($22/mo). `fmp_news.enabled: false` in `system_live.yaml`. FMP news circuit breaker (DEC-323) prevents request spam if accidentally enabled. Upgrade to Premium ($59/mo) would resolve.
- **Audit:** Every action logged immutably.
- **Paper trading config overrides (Sprint 27.75):** Risk tiers reduced 10x in `quality_engine.yaml` and `system_live.yaml`, `consecutive_loss_throttle: 999` in `orchestrator.yaml`, `min_position_risk_dollars: 10.0` in `risk_limits.yaml`. These must be restored before live trading — see `docs/pre-live-transition-checklist.md`.
- **Overflow routing (Sprint 27.95):** When open positions reach `overflow.broker_capacity` (50 as of Sprint 32.9, aligned with `max_concurrent_positions`), approved signals route to CounterfactualTracker as shadow positions instead of IBKR. Config: `overflow.enabled`, `overflow.broker_capacity` in `config/overflow.yaml`. Preserves learning data. Bypassed for SimulatedBroker. Note: evaluate `broker_capacity` before live trading — see `docs/pre-live-transition-checklist.md`.
- **Max concurrent positions (Sprint 32.9):** `max_concurrent_positions: 50` in `risk_limits.yaml` activates the DEC-367 position count check. New entries are rejected when 50 positions are open.
- **NYSE holiday detection (Apr 3 hotfix):** `core/market_calendar.py` detects 10 full-day NYSE closures per year (including Easter). Early market close days (e.g., day before Thanksgiving, 1 PM close) are NOT yet detected. ARGUS will operate normally on early-close days — manual monitoring recommended. `GET /api/v1/market/status` reports holiday name and next trading day.
- **Pre-EOD signal cutoff (Sprint 32.9):** `signal_cutoff_time: "15:30"` (ET) on OrchestratorConfig stops new signal processing after 3:30 PM. Strategies still evaluate but approved signals are discarded. Config-gated via `signal_cutoff_enabled: true` in `orchestrator.yaml`.
- **Margin circuit breaker (Sprint 32.9):** Order Manager tracks IBKR Error 201 margin rejections on entry orders. Circuit opens after `margin_rejection_threshold: 10` rejections, blocking new entry orders. Bypassed for flattens/stops/bracket legs. Auto-resets when position count drops below `margin_circuit_reset_positions: 20`. Daily reset at market open.
- **Sweep qualification uses 24-symbol momentum set (Sprint 31A):** Parameter sweeps in `config/experiments.yaml` were run against a 24-symbol momentum universe. NR Breakout (2 trades) and VWAP Bounce (negative dollar P&L despite positive R) produced misleading results because the momentum set doesn't match their natural populations. Universe-aware re-sweeps using `config/universe_filters/{pattern}.yaml` are required before treating non-qualifying patterns as definitively unqualified. DEF-145 (31A.75 Sweep Tooling Impromptu) resolves this.
- **Sweep symbol representativeness (Apr 5 → PARTIALLY RESOLVED Apr 20):** Symbol resolution solved via `scripts/resolve_symbols_fast.py` (pyarrow sampling, 41s for 24K symbols, 791–4,008 symbols per pattern). DuckDB query path still broken for ad-hoc SQL (DEF-161 — 983K Parquet files). Strategic pivot (DEC-382): exhaustive grid sweeps deprioritized in favor of shadow-first validation. 22 shadow variants deployed for CounterfactualTracker data collection (DEC-383). Full-universe backtests reserved for shadow-proven configs only.
- **DuckDB materialization gap (Apr 20 → RESOLVED Apr 20 via Sprint 31.85):** Was a structural problem with `HistoricalQueryService` over the original 983K-file cache (`CREATE VIEW` ~60 min per query, `CREATE TABLE` ~16 hours to materialize). Resolved by `scripts/consolidate_parquet_cache.py` — original 983K monthly files consolidated to ~24K per-symbol files at `data/databento_cache_consolidated/`, queries now sub-3s (Q1 COUNT DISTINCT: 2.7s, Q2 single-symbol: 0.1s, Q3 100-symbol batch: 2.1s against consolidated cache). `historical_query.yaml` repointed to consolidated cache in commit dc91e1f. See `docs/operations/parquet-cache-layout.md` for the canonical cache-separation reference.
- **Strategy shadow mode (Sprint 32.9):** ABCD and Flat-Top Breakout set to `mode: shadow`. Both generate counterfactual data via CounterfactualTracker but do not place live orders. 10 strategies remain in live mode.
- **Paper trading data-capture overrides (Sprint 29.5):** `daily_loss_limit_pct: 1.0`, `weekly_loss_limit_pct: 1.0`, `throttler_suspend_enabled: false`, `orb_family_mutual_exclusion: false`. All documented in `docs/pre-live-transition-checklist.md` for restoration before live trading.
- **Reconciliation safety (Sprint 27.95):** Broker-confirmed positions (with IBKR entry fill callbacks) are NEVER auto-closed by reconciliation. `auto_cleanup_unconfirmed: false` by default (warn-only). See `docs/pre-live-transition-checklist.md` for live trading config decisions.

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

*Full index (status + sprint attribution + supersession chains): `docs/dec-index.md`. Full rationale: `docs/decision-log.md`. Per-sprint DEC listings have been removed from this doc — `dec-index.md` is authoritative.*

**Most-cited foundational decisions** (sessions routinely touch these):
- DEC-025 (Event Bus FIFO) · DEC-027 (Risk Manager modifications — share/target only, never stops/entry) · DEC-028 (strategy daily-stateful, session-stateless)
- DEC-029 (Event Bus sole streaming mechanism) · DEC-032 (Pydantic config, not BaseSettings) · DEC-047 (walk-forward validation mandatory, WFE > 0.3)
- DEC-117 (atomic bracket orders) · DEC-248 (Databento EQUS.MINI primary) · DEC-345 (separate-DB pattern for telemetry stores)
- DEC-383 (22 shadow variant fleet) · DEC-384 (FIX-01: standalone overlay registry — `_STANDALONE_SYSTEM_OVERLAYS` extensible registry in `argus/core/config.py`) · **DEC-386 (Sprint 31.91 OCA-group threading + broker-only safety — 4-layer architecture closing ~98% of DEF-204's mechanism, Tier 3 verdict 2026-04-27, most recent)**

**Superseded (do not use):** DEC-031 → DEC-083; DEC-089 → DEC-248; DEC-097 → DEC-143/161; DEC-165 → DEC-237; DEC-234 → DEC-248.

---

## Workflow

Three-tier architecture: Claude.ai (strategic + planning) → Autonomous Sprint Runner (execution orchestrator) → Claude Code (implementation + review). Git is the bridge. Autonomous mode drives the full execution loop; human-in-the-loop mode still benefits from structured logging. All decisions logged with sequential DEC numbers (see `docs/dec-index.md`); deferred items tracked in `CLAUDE.md`.

**Sprint methodology:** Sprint spec → session prompts → Claude Code implementation → code review → polish → doc sync. Since Sprint 18+, sessions ship as comprehensive "sprint packages" (spec + prompts + review plans + doc updates in one conversation).

**Full runner documentation:** `workflow/protocols/autonomous-sprint-runner.md` (modules, notifications, conformance checks, session-boundary diff validation, compaction risk scoring DEC-275). Universal protocols, templates, and the runner live in the `workflow/` submodule (https://github.com/stevengizzi/claude-workflow); ARGUS-specific rules remain in `.claude/rules/`.

**Workflow protocols:** ARGUS sprint workflow uses the `claude-workflow` metarepo (https://github.com/stevengizzi/claude-workflow). The metarepo uses **per-file semantic versioning** — each protocol/template/schema evolves on its own version line, **not** a global metarepo-wide version. Key protocols at the time of last sprint planning: `protocols/sprint-planning.md` (v1.2.0), `protocols/in-flight-triage.md` (v1.3.0), `protocols/mid-sprint-doc-sync.md` (v1.0.0, NEW 2026-04-28); key templates: `templates/implementation-prompt.md` (v1.5.0, structural-anchor amendment 2026-04-28), `templates/doc-sync-automation-prompt.md` (v1.2.0). See `bootstrap-index.md` in the metarepo for the canonical index. Cross-cutting amendments are tracked per-file in commit history (this is the **per-file pointer** model) rather than as a metarepo-wide version bump.

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| `docs/project-bible.md` | Source of truth — what and why |
| `docs/project-knowledge.md` | This file (Claude context) |
| `docs/architecture.md` | Technical blueprint — how |
| `docs/roadmap.md` | Strategic vision + sprint queue (DEC-262) |
| `docs/sprint-campaign.md` | Operational sprint choreography |
| `docs/decision-log.md` | All DEC entries with full rationale. Latest: DEC-386 (Sprint 31.91 OCA-group threading + broker-only safety, Tier 3 verdict 2026-04-27). |
| `docs/dec-index.md` | Quick-reference DEC index with status |
| `docs/sprint-history.md` | Complete sprint history + per-sprint follow-on detail |
| `docs/pre-live-transition-checklist.md` | Config + test values to restore before live trading |
| `docs/process-evolution.md` | Workflow evolution narrative |
| `docs/risk-register.md` | Assumptions and risks |
| `docs/live-operations.md` | Live trading procedures |
| `docs/protocols/market-session-debrief.md` | Post-market diagnostic runbook (7-phase: session boundaries → startup health → data flow → strategy pipeline → catalysts → error catalog → synthesis) |
| `CLAUDE.md` | Claude Code session context |
| `docs/ui/ux-feature-backlog.md` | Planned UI features |
| `docs/strategies/STRATEGY_*.md` | Per-strategy spec sheets |
| `workflow/` | Claude-workflow metarepo (protocols, templates, runner) |

## Key Learnings

> Durable, cross-sprint design rules. Sprint-specific situational findings (24-symbol momentum set not representative, DuckDB CREATE VIEW over 983K files, PMH 0 live trades on Apr 2, etc.) have been relocated to the relevant sprint section in `docs/sprint-history.md`.

**Behavioral / operational:**
- **Learning Loop V1 is advisory-only.** Recommendations surface as ConfigProposals requiring human approval. Automated application deferred to Sprint 40. Every V1 approval/dismiss decision is training data.
- **ConfigProposalManager validates through Pydantic before writing.** Changes queue until next session start. `max_change_per_cycle` guard prevents radical reconfiguration from a single report.
- **IBKR error 404 on SELL orders indicates qty mismatch.** When ARGUS tracks multiple positions on the same symbol but IBKR merges them, partial closes can trigger a locate hold. Fix: re-query IBKR's actual position qty before resubmitting flatten orders.
- **ORB Scalp is structurally shadowed by ORB Breakout under DEC-261.** Both share identical entry conditions; Breakout fires first. Configurable via `orb_family_mutual_exclusion: false` for paper data capture.
- **ARGUS has no awareness of market holidays without the calendar — always check before debugging zero-candle sessions.** `core/market_calendar.py` detects full-day NYSE closures. `GET /api/v1/market/status` and the startup log are the first check.

**Code conventions / gotchas:**
- **Win rate from backend is a 0–1 proportion, not a percentage.** Frontend display code must multiply by 100.
- **`getattr(pos, "qty", 0)` silently returns 0 on Position objects.** Position uses `shares`; `qty` is an Order attribute. (DEF-139/140 root cause.)
- **Spec default values frequently diverge from actual constructor defaults.** Cross-validation tests comparing PatternParam metadata against Pydantic config defaults catch these at test time. Always trust constructor defaults when they conflict with spec.
- **Pydantic Field bounds must be validated against PatternParam ranges.** A tighter Pydantic ge/le/gt/lt silently rejects valid sweep values.
- **Parameter fingerprint uses detection params only.** SHA-256 of canonical JSON — `strategy_id`, `name`, `enabled`, `operating_window` are excluded.
- **`lookback_bars` is deque capacity, not detection eligibility.** Use `min_detection_bars` (overrideable) to separate the two. Always verify `lookback_bars` accommodates the full data window a pattern needs.
- **Reference data wiring must be explicit in main.py Phase 9.5 + periodic refresh.** `PatternBasedStrategy.initialize_reference_data()` must be called for patterns needing `prior_close` (PMH, GapAndGo).

**Test / Vitest:**
- **Unmocked WebSocket hooks in Vitest cause fork workers to hang.** Mock the hook at the test file level with `vi.mock()` before rendering the component. Global `testTimeout: 10_000` + `hookTimeout: 10_000` is the safety net.

**Data pipeline / storage:**
- **DuckDB over Parquet eliminates ETL.** SQL queries run directly against the Parquet cache. Always use `:memory:` connections — the cache IS the persistent store.
- **Two Parquet caches, two purposes, one source of truth.** Original per-month (`data/databento_cache/`, ~983K files) is authoritative for `BacktestEngine`; consolidated per-symbol (`data/databento_cache_consolidated/`) is a derived artifact for `HistoricalQueryService` only. Pointing either at the wrong cache silently misses data. See `docs/operations/parquet-cache-layout.md`.
- **Per-bar Parquet volume is not daily volume.** OHLCV-1m stores per-minute volume; universe filters expect daily. Aggregate bars to daily before comparing against `min_avg_volume`.
- **`json.dumps()` without `default=str` silently drops results when dataclasses contain `date` objects.** The fire-and-forget write pattern (WARNING log only) makes this a silent-data-loss class bug. (DEF-151.)
- **SQLite retention DELETE must be followed by VACUUM or file size grows unbounded.** aiosqlite cannot VACUUM — use close → sync VACUUM via `asyncio.to_thread()` → reopen. (Sprint 31.8 S2, `evaluation.db` grew to 4 GB.)
- **Lifespan handlers must never call synchronous I/O that blocks indefinitely.** Background via `asyncio.create_task(asyncio.to_thread(...))` with shutdown cleanup. `_wait_for_port()` in `main.py` is the reference pattern.
- **Non-bypassable validation is a design posture, not a flag default.** No `--skip-validation` / no env var / no swallow-and-continue `except`. Structural sequence so unreachable-on-failure. Pair with a grep-guard regression test.
- **Derived artifacts: prove the original cache is read-only with an inode+mtime+size snapshot, not just `exists()`.** `test_original_cache_is_unmodified` is the pattern.

**Execution safety:**
- **MFE/MAE enables "was it green before it went red" analysis.** Track peak favorable and adverse excursion per tick. R-multiples use `original_stop_price` (never trail stop).
- **Exit order paths must coordinate: multiple safety mechanisms can independently place flatten/SELL orders.** Always query broker state before resubmitting. Stop fills must cancel concurrent flatten orders; startup cleanup must cancel residual bracket orders before placing flatten. Without cross-checks, positions flip short. (DEF-158.)

**Strategic / sweep philosophy:**
- **Sweep axis selection is critical.** Always verify that swept parameters actually affect the metric you care about (signal frequency, quality, selectivity). Before committing overnight compute, check that swept dimensions move the target metric.
- **Sweep symbol representativeness matters.** A small "representative" subset is not a substitute for the natural population of each pattern. Use `config/universe_filters/{pattern}.yaml` via `--universe-filter`.
- **Full cartesian product grid sizes are billions — always use `--params`.** 10–15 PatternParams per pattern → 10⁹–10¹³ grid points. Restrict to 2–3 key params.
- **Exhaustive grid sweeps are misaligned with the shadow-first validation philosophy (DEC-382).** A 5-day backtest sweep is Stage 4 work (sizing proven configs) at Stage 1 (quick-reject). Shadow testing via CounterfactualTracker is free, real, and produces answers in 20 trading days. Reserve exhaustive backtests for configs that survive shadow.
- **Concurrent BacktestEngine processes can starve the SSD.** Each process with `--workers 2` spawns 2 workers reading Parquet. Use sequential orchestration (`run_sweep_batch.sh`) rather than 11+ concurrent processes.
- **ARGUS late-night boot collides with after-hours auto-shutdown.** Starting ARGUS after ~22:30 ET can fire the auto-shutdown mid-init. Verify services directly in a script against production config rather than via full ARGUS boot. (DEF-164/165.)

---

## Communication Style

The user prefers thorough, detailed explanations and expects structured outputs ready for copy-paste. He appreciates proactive pushback and concerns. He values clarifying questions before assumptions. He wants the *why* behind every recommendation. He is building this for his family's financial future — treat every decision with the seriousness that implies. Direct, technically precise communication.
