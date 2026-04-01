# ARGUS — Strategic Roadmap

> From artisanal strategies to ensemble alpha — the complete path
> **v2.9 — March 30, 2026** (Sprint 28.5 complete — Exit Management)
> **Status:** CANONICAL — this is the single source of truth for ARGUS's strategic direction and sprint queue.
> **Supersedes:** `docs/research/ARGUS_Expanded_Roadmap.md` (Feb 26), `docs/argus_unified_vision_roadmap.md` (Mar 5), `docs/10_PHASE3_SPRINT_PLAN.md` (all forward-looking sections)

---

## 1. The Thesis

ARGUS evolves from a **rules-based multi-strategy system** into an **AI-powered trading intelligence platform** that:

- Scores every setup on a quality continuum (A+ through C-) rather than binary pass/fail
- Dynamically sizes positions based on setup quality, not uniform risk parameters
- Classifies catalyst quality in real-time using NLP via Claude API
- Runs 15+ artisanal pattern types simultaneously across the US equity momentum universe
- Discovers new micro-strategies through systematic parameter search and statistical validation
- Learns from its own trade outcomes to continuously sharpen scoring and allocation
- Presents the entire system as a legible, navigable 3D visualization — the **Synapse**

The target: **sustainable 5–10%+ monthly returns on deployed capital** at the $100K–$500K scale, with the system running autonomously during US market hours from Cape Town.

The path divides into two halves. Everything through Phase 6 builds a strong AI-enhanced multi-strategy trading system — valuable regardless of what comes after. Phases 7–10 build the ensemble infrastructure and test whether systematic search produces validated ensembles that outperform hand-crafted strategies. If the controlled experiment in Phase 8 fails, ARGUS is still strong. If it succeeds, it becomes something without a comparable at the independent trader scale.

### The Adaptive Trading Ecosystem Model

At steady state, ARGUS operates as an adaptive trading ecosystem where strategies exist in one of five states:

1. **Incubating** — new parameter combinations or pattern mutations being backtested overnight (Sprint 41 Continuous Discovery Pipeline)
2. **Validating** — promising candidates running in simulated paper (BacktestEngine on recent 20 days, Sprint 32.5 PromotionPipeline) with stress testing (Sprint 33.5)
3. **Proving** — validated candidates running in real paper trading / counterfactual tracking, accumulating live market data
4. **Active** — proven strategies trading real capital, continuously monitored against their validation baseline
5. **Declining** — active strategies showing degrading performance, getting throttled and eventually retired (Sprint 40 Learning Loop V2)

The daily operator workflow at full vision:
- **Pre-market (10 min):** Review intelligence brief. Check overnight discovery results. Approve/reject pending promotions. Confirm regime classification.
- **Market hours (passive):** Synapse shows real-time activity. Alerts for anomalous behavior. System runs.
- **Post-market (15 min):** Review debrief. Check Learning Loop recommendations. Flag strategies for review.
- **Weekly (30 min):** Deep dive on Performance Workbench. Review cohort promotions. Strategic ensemble assessment.

Total active work: ~45 minutes daily + 30 minutes weekly — exceeding the "few hours per day" goal from the Day Trading Manifesto.

**Key architectural principle:**
- **Sprint 28 is the observation layer** — it establishes the pattern of correlating predictions with outcomes that V2 runs at micro-strategy scale.
- **Sprint 32.5 is the action layer** — ExperimentRegistry + PromotionPipeline provide the infrastructure for acting on Learning Loop insights.
- **Sprint 40–41 close the autonomous loop** — Learning Loop V2 + Continuous Discovery Pipeline create the self-improving system.

**Scale considerations:**
- Target ensemble scale: 200–800 micro-strategies (V1 ensemble). 2,000+ may require Cython hot-path optimization.
- Micro-strategies that fire rarely (e.g., twice/month) are not weak — they're precise. Ensemble power comes from having hundreds of precise strategies that collectively cover most market days.
- At 500+ strategies, human oversight transitions from individual strategy review to cohort-level approval (Sprint 32.5 PromotionPipeline cohort model).

---

## 2. What Changes — And What Doesn't

### Unchanged (Current Architecture Strengths)

These foundations are correct and remain:

- **Event-driven architecture** with Event Bus, FIFO delivery, sequence numbers
- **Three-tier risk management** (strategy → cross-strategy → account)
- **Broker abstraction** (IBKR for live, Alpaca for incubation, SimulatedBroker for backtest)
- **Data provider abstraction** (Databento primary, FMP for scanning, adapters swappable)
- **Strategy Incubator Pipeline** (10 stages from concept to retirement)
- **Walk-forward validation** as mandatory overfitting defense
- **Two-Claude workflow** (strategic Claude.ai + tactical Claude Code)
- **Command Center** (three surfaces: web, Tauri desktop, PWA mobile)
- **Daily-stateful, session-stateless** strategy model
- **Trade Logger** as sole persistence interface
- **Parallel Build + Validation tracks**

### What Evolves

| Current | Expanded |
|---------|----------|
| Binary scanner (pass/fail filters) | **Opportunity Ranker** (composite quality score per setup) |
| 4 active strategies | **15+ artisanal patterns** covering the full momentum playbook, then **hundreds of micro-strategies** via systematic search |
| Uniform position sizing (fixed % risk per trade) | **Dynamic position sizing** tied to setup quality grade |
| Price/volume entry triggers only, static pre-market watchlist | **Full-universe monitoring** with strategy-specific filters + **NLP catalyst pipeline** enriching entry context (DEC-263) |
| AI Layer as advisory add-on (Sprint 22) | **AI Layer as the brain** — real-time setup grading, sizing decisions, learning loop |
| Orchestrator V1 (rules-based allocation) | **Ensemble Orchestrator** (correlation-aware, activation-filtered, hundreds of micro-strategies) |
| RegimeClassifier (SPY vol proxy) | **Multi-factor regime engine** with sector rotation awareness (**Sprint 27.6 ✅** — RegimeVector 6 dimensions) |
| Conservative risk defaults | **Graduated risk tiers** (conservative base → aggressive on A+ setups) |
| Long-only | **Short selling infrastructure** for parabolic short and future short strategies |

### What's New (Doesn't Exist Yet)

1. **Setup Quality Scoring Engine** — Composite score (0–100) for every potential trade, combining technical pattern strength, catalyst quality, volume profile, historical match, and regime alignment. (Order Flow added post-revenue as 6th dimension.)
2. **NLP Catalyst Classifier** — Real-time news/filing classification with quality grading via Claude API
3. **Dynamic Position Sizer** — Maps quality score to risk allocation (C+ = 0.25%, B = 0.75%, A = 1.5%, A+ = 2.5%)
4. **Expanded Pattern Library** — From 4 to 15+ artisanal patterns (bull flags, ABCD, flat-top breakouts, dip-and-rip, HOD breaks, red-to-green, parabolic short, etc.)
5. **Short Selling Infrastructure** — Locate/borrow tracking, inverted risk logic, short-specific Risk Manager rules, uptick rule compliance
6. **Learning Loop** — Post-trade analysis that correlates quality scores with actual outcomes, continuous recalibration
7. **Universe Manager** — Broad-universe monitoring with strategy-specific filters, continuous intra-day screening, pre-market intelligence, and catalyst-driven enrichment (DEC-263)
8. **BacktestEngine** — Production-code backtesting at 5–10x Replay Harness speed, with Research Console UI
9. **Systematic Strategy Search** — Parameterized templates, tiered sweep infrastructure, statistical validation (FDR, smoothness priors)
10. **The Synapse** — 3D strategy space visualization (Three.js) showing all micro-strategies as nodes, with real-time firing animations, correlation connections, and navigable grouping modes. The system's brain made visible.
11. **Continuous Discovery Pipeline** — Overnight parameter exploration, morning discovery briefs, automated staging and promotion
12. **Performance Workbench** — Customizable widget grid (react-grid-layout) for Bloomberg-grade analysis

---

## 3. Velocity Baseline

ARGUS completed 21 sprints + sub-sprints in ~17 calendar days of active development (Feb 14 – Mar 5). Average sprint: ~0.8 calendar days. However, sprint complexity has been increasing — early sprints (1–5) were dense single-day affairs, while later sprints (21a–21d, 21.5) span multiple days. The roadmap below assumes sprint durations of 1–4 days each depending on complexity, with some parallelism where noted.

**Current state:** Sprint 29 complete (March 31, 2026). ~4,178 pytest + 689 Vitest (0 pre-existing pytest failures). Twelve active strategies (7 from Sprint 26 + 5 new PatternModule patterns from Sprint 29). Sprint 28.5 (Exit Management) delivered configurable per-strategy trailing stops (ATR/percent/fixed), partial profit-taking with trail on T1 remainder, and time-based exit escalation across Order Manager, BacktestEngine, and CounterfactualTracker. 6 sessions, 12 adversarial review amendments verified, +110 tests, 0 issues. Full infrastructure stack operational: BacktestEngine + Evaluation Framework + Regime Intelligence (11-field RegimeVector) + Counterfactual Engine + VIX Data Service + Quality Engine + NLP Catalyst Pipeline + Universe Manager + AI Copilot + Learning Loop V1 + Exit Management. Eight-page Command Center + Observatory. Live Databento + IBKR paper trading. Phase 5 Gate complete (March 21, 2026). Strategic check-in completed March 30 (DEC-378–381). Next: Sprint 30 (Short Selling + Parabolic Short).

---

## 4. UI/UX Design Principle

Every capability must be visible the moment it exists. Terminal-only development phases are a failure mode — they disconnect the builder from the system and erode confidence in what the system is actually doing. The design north star remains "Bloomberg Terminal meets modern fintech" and the aspiration remains "a portal, not a tool."

The Command Center evolves from 8 pages to 11 across this roadmap:

| Page | Current | Phase 5 | Phase 6 | Phase 7–8 | Phase 9–10 |
|------|---------|---------|---------|-----------|------------|
| Dashboard | Built | Quality scores visible | Strategy health bands, short exposure | Ensemble health metrics | Full ensemble dashboard |
| Trades | Built | Quality badge per trade | Unchanged | Unchanged | Strategy family attribution |
| Performance | Built | Unchanged | Learning Loop panel, correlation matrix | Sweep comparison views | Ensemble analytics suite |
| Orchestrator | Built | Catalyst alerts | Throttle/boost panel | Template activation view | Ensemble activation map |
| Pattern Library | Built | Unchanged | New strategy cards | Template gallery evolution | Template + ensemble browser |
| The Debrief | Built | AI-generated summaries | Unchanged | Research session recaps | Ensemble debrief |
| System | Built | API health monitoring | Unchanged | BacktestEngine monitoring | Pipeline health |
| Observatory | **Built (Sprint 25)** | — | Strategy-specific views | Ensemble pipeline viz | Full ensemble observatory |
| Copilot | Shell built | Activated (Sprint 22) | Ensemble-aware context | Research assistant mode | Full ensemble copilot |
| Research Console | — | — | — | **New (Sprint 30)** | Discovery pipeline view |
| Synapse | — | — | — | — | **New (Sprint 38–39)** |

---

## 5. Validation Track

Paper trading runs in parallel with the Build Track. Gates are calendar-limited and confidence-gated.

### Gate 1: System Stability ✅ COMPLETE
- Infrastructure validated on Alpaca IEX

### Gate 2: Quality Data Validation (ACTIVE — Databento + IBKR)
- Run all 4 Phase 5 strategies on Databento data with IBKR paper
- Minimum 20 trading days
- Compare to backtest expectations
- Kill criteria apply (from `paper-trading-guide.md`)

### Gate 3: AI-Enhanced Paper Trading (PENDING — After Sprint 24)
- Setup Quality Engine active, scoring every trade
- NLP catalyst pipeline enriching watchlist
- Dynamic position sizing in paper mode
- Full-universe monitoring with strategy-specific filters (DEC-263)
- Minimum 30 trading days
- **Key metric:** Track quality-score-to-outcome correlation. If A+ setups don't outperform B setups, the quality engine isn't working yet.
- **Key metric:** Compare opportunity detection: how many setups per day does the broad universe surface vs. the static pre-market watchlist baseline?

### Gate 4: Full System Paper Trading (PENDING — After Phase 6)
- 13–15+ patterns active including short selling
- Learning Loop V1 providing feedback
- Minimum 20 more trading days (50+ cumulative)
- **Key metric:** System-level Sharpe > 2.0 over rolling 30-day windows

### Gate 5: Live Trading (User Decision)
- Explicit go/no-go by user
- Start at minimum size ($25K, 10-share positions)
- Shadow system runs indefinitely in parallel
- Scale gradually: minimum → intermediate → model-calculated → full

### Kill Criteria (Hard Stops — Apply at All Gates)
- Max drawdown exceeds 15% in any 30-day window
- 3 consecutive losing weeks exceeding 2% each
- System error causes unintended trade execution
- Risk Manager bypass detected

---

## 6. Phase 5: Foundation Completion (Sprints 21.5–24)

*Completes the existing near-term roadmap. Finishes live integration, adds market data scanning, begins AI layer. UI focus: make intelligence and quality filtering visible.*

### Sprint 21.5: Live Integration ✅ COMPLETE (March 5, 2026)

Databento EQUS.MINI live connection. IBKR Gateway paper trading. First paper trade executed (AAPL VWAP Reclaim). End-to-end order lifecycle validated. Key fixes: DEC-251 ($100 absolute risk floor), DEC-252 (IBKR price rounding), DEC-253–256 (post-session fixes), DEC-261 (ORB same-symbol mutual exclusion).

### Sprint 21.5.1: C2 Bug Fixes + UI Polish ✅ COMPLETE (March 5, 2026)

Session C2 bugs fixed. UI polish applied.

### Sprint 21.7: FMP Scanner Integration ✅ COMPLETE (March 5, 2026)

FMP Starter plan ($22/mo) activated. Dynamic pre-market symbol selection via gainers/losers/actives endpoints. Hybrid Databento+FMP architecture (DEC-257, DEC-258, DEC-259). Resolved historical data lag constraint.

### Sprint 21.6: Backtest Re-Validation + Execution Logging (DEC-132 / DEC-358)
**Target:** ~2 days
**Status:** ✅ COMPLETE (March 23, 2026)

**Scope (delivered):**
- Re-validated all 7 active strategies using BacktestEngine with Databento OHLCV-1m data (28-symbol curated universe, 2023-04-01 to 2025-03-01)
- ExecutionRecord logging added to Order Manager for slippage model calibration (DEC-358 §5.1)
- BacktestEngine risk_overrides mechanism for single-strategy backtesting (DEC-359)
- VectorBT dual file naming support, symbol auto-detection from cache
- Revalidation harness script (`scripts/revalidate_strategy.py`)
- **DEC-132 data blocker removed:** Full-universe Parquet cache populated March 2026 (24,321 symbols, 153 months, 3 datasets). Pipeline proven end-to-end, Bull Flag validated (Sharpe 2.78). 6 strategies pending full-universe re-validation runs.
- **Tests:** 3,010 → 3,051 (+41 pytest)

**Prerequisites for full DEC-132 resolution:** ~~Full-universe historical data cache population.~~ **RESOLVED** (March 2026): `scripts/populate_historical_cache.py` populated 24,321 symbols × 153 months across EQUS.MINI + XNAS.ITCH + XNYS.PILLAR (44.73 GB on external drive). Production-representative backtesting now available for Sprints 28+ (Learning Loop) and 33+ (Statistical Validation). Pass `--cache-dir data/databento_cache` to CLI tools.

### Sprint 22: AI Layer MVP + Copilot Activation (DEC-096, DEC-098, DEC-170)
**Target:** ~3–4 days
**Status:** ✅ COMPLETE (March 7, 2026)

**Scope (delivered):**
- Claude API integration (`argus/ai/`): ClaudeClient, PromptManager, SystemContextBuilder, ResponseCache, AIConfig, 5 tool_use definitions. Claude Opus model (DEC-098).
- Approval workflow: ActionManager with DB-persisted proposals, 5-minute TTL, 4-condition pre-execution re-check (DEC-267, DEC-272).
- Persistent chat: ConversationManager with calendar-date keying and tags (DEC-266), 3 SQLite tables.
- WebSocket streaming: `WS /ws/v1/ai/chat` with JWT auth, bidirectional (DEC-265).
- Per-page context injection: `useCopilotContext` hooks on all 7 pages (DEC-268).
- Per-call cost tracking: UsageTracker, ai_usage table (DEC-274).
- **UI:** Full Copilot (CopilotPanel, ChatMessage, StreamingMessage, ActionCard). Dashboard AIInsightCard with auto-refresh. Debrief Learning Journal with conversation browser. Markdown rendering with XSS protection (DEC-270).
- **Tests:** 286 new (205 pytest + 81 Vitest) — 3.4× target.

**Decisions:** DEC-264 through DEC-275. See `docs/decision-log.md` for full rationale.

**Notes:** Largest single-sprint scope. Sessions 3a and 3b compacted, leading to DEC-275 (compaction risk scoring). AIService built but not wired — removed in cleanup. ~6,500 lines backend, ~3,000+ lines frontend.

### Sprint 23: NLP Catalyst Pipeline + Universe Manager (DEC-163, DEC-164, DEC-263)
**Target:** ~4–5 days (scope expanded per DEC-263; may decompose into 23 + 23.5)
**Status:** ✅ PARTIAL (Mar 7–8, 2026) — Universe Manager complete. NLP Catalyst Pipeline deferred to Sprint 23.5.

**Scope (delivered — Universe Manager):**
- **Universe Manager** (`argus/data/universe_manager.py`): Replaces static pre-market watchlist with broad-universe monitoring (DEC-263). FMPReferenceClient fetches Company Profile + Share Float in batches. UniverseManager applies system-level filters (OTC, price, volume; fail-closed on missing data per DEC-277). Pre-computed routing table maps symbols to qualifying strategies via declarative `universe_filter` YAML configs. O(1) route_candle lookup. Fast-path discard in DatabentoDataService drops non-viable symbols before IndicatorEngine. Config-gated: `universe_manager.enabled` in system.yaml.
- **Strategy universe filter declarations:** All 4 active strategies (ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum) updated with explicit `universe_filter` YAML config extracted from `get_scanner_criteria()`. VWAP Reclaim uniquely includes min_market_cap=500M based on institutional flow thesis.
- **UI:** Dashboard gains UniverseStatusCard panel (enabled/disabled/loading/error states). 2 API endpoints (`/api/v1/universe/status`, `/api/v1/universe/symbols`).
- **Tests:** 126 pytest + 15 Vitest new tests. DEC-277 (fail-closed on missing reference data).

**Scope (deferred to Sprint 23.5 — NLP Catalyst Pipeline):**
- **CatalystPipeline** (`argus/intelligence/catalyst.py`): SEC EDGAR filing monitor (10-K, 10-Q, 8-K, insider trades). FMP news feed. Claude API for catalyst classification and quality grading.
- **CatalystEvent** on Event Bus: `(symbol, catalyst_type, quality_grade, summary, source, timestamp)`.
- **Pre-market intelligence brief:** Morning scan results + catalyst research + watchlist generation.
- **UI:** Dashboard catalyst badges, Orchestrator catalyst alert panel, Debrief intelligence brief view.

### Sprint 23.5: NLP Catalyst Pipeline (DEC-163, DEC-164, DEC-300–307)
**Target:** ~3–4 days
**Status:** ✅ COMPLETE (Mar 10, 2026)

**Scope (delivered):**
- **CatalystPipeline** (`argus/intelligence/catalyst/pipeline.py`): Three-source architecture (DEC-304) — SECEdgarSource (8-K, Form 4), FMPNewsSource (stock news, press releases), FinnhubSource (company news, analyst recommendations).
- **CatalystClassifier** (`argus/intelligence/catalyst/classifier.py`): Claude API classification with rule-based fallback (DEC-301). Nine categories: earnings, insider, guidance, analyst, regulatory, partnership, product, restructuring, other.
- **CatalystStorage** (`argus/intelligence/catalyst/storage.py`): SQLite persistence with headline hash (SHA-256) deduplication (DEC-302).
- **BriefingGenerator** (`argus/intelligence/catalyst/briefing.py`): Pre-market intelligence briefs with $5/day cost ceiling enforcement via UsageTracker (DEC-303).
- **CatalystEvent** on Event Bus: `(symbol, category, quality_score, headline, source, timestamp)`.
- **API routes:** `/api/v1/catalysts`, `/api/v1/catalysts/{symbol}`, `/api/v1/catalysts/refresh`, `/api/v1/intelligence/briefings`, `/api/v1/intelligence/briefings/{id}`, `/api/v1/intelligence/briefings/generate`.
- **UI:** CatalystBadge (category-colored), CatalystAlertPanel, IntelligenceBriefView (fourth tab in The Debrief), BriefingCard with expand/collapse.
- **TanStack Query hooks** (DEC-305): `useCatalysts`, `useIntelligenceBriefings`, `useIntelligenceBriefing`.
- **Config-gated** via `catalyst.enabled` (DEC-300, default: false).
- **FMP plan upgrade deferred** — free tier + Finnhub free tier sufficient for V1.
- **Tests:** 94 pytest + 43 Vitest new tests.

**Notes:** No FMP plan upgrade required — Finnhub free tier provides analyst recommendations at no cost. Rule-based fallback ensures graceful degradation when Claude API unavailable or daily cost ceiling reached.

### Sprint 24: Setup Quality Engine + Dynamic Position Sizer (DEC-163, DEC-239)
**Target:** ~3–4 days
**Status:** ✅ COMPLETE (March 14, 2026)

**Scope (delivered):**
- **SetupQualityEngine** (`argus/intelligence/quality_engine.py`): Composite 0–100 scoring from 5 weighted inputs (DEC-239): pattern strength (25%), catalyst quality (20%), volume profile (20%), historical match (15%), regime alignment (20%). Configurable weights via YAML. Grade thresholds: A+ (≥90) through C- (<40).
- **DynamicPositionSizer** (`argus/intelligence/position_sizer.py`): Grade → risk tier → share count. A+=2–3%, A=1.5–2%, B+=1–1.5%, B=0.5–1%, C+=0.25–0.5%, C/C-=SKIP. Pydantic config models with validators.
- **Pattern Strength** on all 4 strategies: `_calculate_pattern_strength()` returns 0–100, strategies emit `share_count=0` for quality pipeline deferred sizing.
- **Firehose Mode** for catalyst sources: Finnhub single general news call, SEC EDGAR single EFTS search (DEC-332).
- **Pipeline Wiring** in main.py: `_process_signal()` runs score → filter → size → enrich → RM. Risk Manager check 0 rejects `share_count ≤ 0`. Bypass modes for SimulatedBroker and disabled quality engine.
- **Quality History DB** table (20 columns, 4 indexes) for Learning Loop.
- **API:** 3 quality endpoints (`/{symbol}`, `/history`, `/distribution`).
- **UI:** QualityBadge component, quality column in Trades, Setup Quality in TradeDetailPanel, QualityDistributionCard (donut) + SignalQualityPanel (histogram) on Dashboard, RecentSignals on Orchestrator, QualityGradeChart on Performance, QualityOutcomeScatter on Debrief. Shared GRADE_COLORS/GRADE_ORDER constants.
- **Tests:** 209 new (158 pytest + 51 Vitest) — 2× target.

**Decisions:** DEC-330 through DEC-341. See `docs/decision-log.md` for full rationale.

**Notes:** 13 sessions (including 11f visual fixes). 2 CONCERNS ratings with acceptable rationale. Quality pipeline fully integrated end-to-end from strategy signals through frontend visualization. Phase 5 Foundation Completion achieved.

### Phase 5 Gate ✅ COMPLETE (March 21, 2026)

**Trigger:** Sprint 24 complete (deferred through Sprint 25.8 due to operational priorities).
**Protocol:** Strategic Check-In (`strategic-check-in.md`).

**Assessment results:**
- AI Layer operational: Yes — Copilot responsive, streaming works, cost tracking active.
- Quality Engine producing differentiation: Partial — 55% of composite active (DEF-082), 45% at neutral defaults (RSK-045). Grade distribution TBD after more paper trading data.
- Paper trading health: 4 valid sessions, 28+ trades. Gate 2 counter reset (DEC-355). ~16 more days needed.
- Phase 6 readiness: Yes, with revised sequencing (DEC-354).
- Velocity: 1.5x multiplier budgeted (1 fix sprint per 2 feature sprints).

**Key decisions:**
- DEC-353: Historical data purchase deferred — Standard plan includes free OHLCV-1m.
- DEC-354: Phase 6 compressed — BacktestEngine to Sprint 27, Learning Loop to Sprint 28.
- DEC-355: Gate 2 day counter reset to ~4 valid days.
- DEC-356: FMP Premium upgrade deferred until Learning Loop data.

---

## 7. Phase 6: Strategy Expansion — Artisanal (Sprints 25–31)

*Opens with The Observatory for operational visibility, then expands the strategy roster to 13–15+ hand-crafted patterns including short selling. Adds the Learning Loop for self-monitoring. This is the phase where ARGUS becomes a serious multi-strategy system. UI focus: make strategy health, correlation, and pipeline behavior visible.*

**Amendment note (DEC-357, DEC-358):** Phase 6 now includes Sprints 27.5, 27.6, 27.7, 27.9, and 27.95 between 21.6 and 28, plus Sprint 28.5 (Exit Management) after 28. These infrastructure sprints transform Sprint 28 (Learning Loop V1) from basic weight tuning into intelligent system analysis with proper evaluation framework, rich multi-dimensional regime data (including VIX-based dimensions from Sprint 27.9), 24× more data volume via counterfactual tracking, and hardened broker safety (Sprint 27.95). Paper trading continues running in parallel throughout, accumulating data.

### Sprint 25: The Observatory (Phase 5 Gate outcome) ✅ COMPLETE (March 18, 2026)

**Context:** Phase 5 Gate strategic check-in identified a critical gap: the system has sophisticated evaluation telemetry (Sprint 24.5) but no way for the operator to observe pipeline behavior immersively. Zero trades were occurring and the operator couldn't tell why. The Observatory addresses this directly — operational visibility is prerequisite to adding more strategies.

**Delivered:**
- **Observatory page** (Command Center page 8): Full-bleed immersive visualization, keyboard-first navigation (f/m/r/t for views, [/] for tiers, Tab for symbols, Shift+R/F for camera)
- **Four views:**
  - **Funnel** (Three.js 3D): Translucent cone with tier discs, symbol particles via InstancedMesh (up to 5,000), CSS2DRenderer labels, OrbitControls
  - **Radar** (Three.js camera animation): Bottom-up perspective of same scene — concentric rings with trigger point at center. Shared-scene pattern with Funnel.
  - **Matrix**: Condition heatmap sorted by proximity to trigger. Green/red/gray cells. Virtual scrolling. Tab navigation.
  - **Timeline**: Strategy lane timeline (9:30–4:00 ET) with SVG event marks at 4 severity levels
- **Detail panel** (right slide-out): Per-symbol condition grid, quality score, catalyst summary, live candlestick chart (Lightweight Charts), chronological strategy history. Persists across view switches.
- **Session vitals bar**: Connection status, evaluation counts, closest miss, top blocking condition
- **Debrief mode**: Date picker switches all views to historical data (7-day retention)
- **Backend**: ObservatoryService (4 query methods) + 4 REST endpoints + Observatory WebSocket (`/ws/v1/observatory`)
- **Config-gated** via `observatory.enabled` (default: true)
- **14 sessions** (S1, S2, S3, S3f, S4a, S4b, S5a, S5b, S6a, S6b, S7, S8, S9, S10)
- **Tests:** pytest −3 (DEF-048 gap), Vitest +76. Net: 2,765 pytest + 599 Vitest = 3,364 total
- **No new DEC entries.** Reserved range DEC-343–360 unused.

### Sprint 25.6: Bug Sweep ✅ COMPLETE (March 20, 2026)

Evaluation telemetry DB separation (`data/evaluation.db`, DEC-345). Periodic regime reclassification (300s interval, DEC-346). Tests: 2,794 pytest + 611 Vitest.

### Sprint 25.7: Post-Session Operational Fixes ✅ COMPLETE (March 21, 2026)

FMP daily bars for regime classification (`fetch_daily_bars()`, DEC-347). Automated debrief export at shutdown (DEC-348). Performance throttler zero-trade-history guard (DEC-349). ORB entry evaluation metadata (DEC-350). Tests: 2,815 pytest + 611 Vitest.

### Sprint 25.8: API Auth 401 + Close-Position Fix ✅ COMPLETE (March 21, 2026)

API auth 401 for unauthenticated requests (DEC-351). Close-position endpoint routes through OrderManager (DEC-352). Tests: 2,815 pytest + 611 Vitest.

### Sprint 26: Red-to-Green + Pattern Library Foundation ✅ COMPLETE (March 22, 2026)

**Delivered:**
- **RedToGreenStrategy** (`argus/strategies/red_to_green.py`): Gap-down reversal at key levels (VWAP, premarket low, prior close). 5-state machine (WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED / EXHAUSTED). 9:35–11:30 AM window.
- **PatternModule ABC** (`argus/strategies/patterns/base.py`): Standardized pattern detection interface with CandleBar, PatternDetection dataclasses, 5 abstract members.
- **PatternBasedStrategy** (`argus/strategies/pattern_strategy.py`): Generic wrapper turning any PatternModule into a full BaseStrategy.
- **BullFlagPattern** (`argus/strategies/patterns/bull_flag.py`): Pole+flag+breakout continuation. Score: 30/30/25/15 weighting.
- **FlatTopBreakoutPattern** (`argus/strategies/patterns/flat_top_breakout.py`): Resistance cluster breakout. Score: 30/30/25/15 weighting.
- **VectorBT R2G** (`argus/backtest/vectorbt_red_to_green.py`): Dedicated R2G backtester.
- **PatternBacktester** (`argus/backtest/vectorbt_pattern.py`): Generic sliding-window backtester for any PatternModule.
- **Integration:** All 3 strategies wired into main.py. Strategy spec sheets created. UI cards added to Pattern Library.
- **Tests:** 119 new (110 pytest + 9 Vitest). Total: 2,925 pytest + 620 Vitest = 3,545.
- **13 sessions** (S1–S10, S10f, micro-fix, cleanup). All review verdicts CLEAR.
- **No new DEC entries.** DEF-088 (PatternParam structured type) deferred to Sprint 27.
- **7 strategies/patterns active.**

### Sprint 27: BacktestEngine Core (DEC-354) ✅ COMPLETE (March 22, 2026)

**Delivered:**
- **SynchronousEventBus** (`argus/core/sync_event_bus.py`): Sequential event dispatch with same interface as async EventBus. Enables deterministic, single-threaded backtesting.
- **HistoricalDataFeed** (`argus/backtest/historical_data_feed.py`): Databento OHLCV-1m download with `metadata.get_cost()` pre-validation and Parquet cache. EQUS.MINI (Apr 2023 – present), XNAS.ITCH + XNYS.PILLAR (May 2018 – Mar 2023). Full-universe cache: 24,321 symbols, 153 months, 44.73 GB on external drive. Population script: `scripts/populate_historical_cache.py`.
- **BacktestEngine** (`argus/backtest/engine.py`): Production-code backtesting engine running real strategy code. Bar-level fill model with worst-case-for-longs priority (stop > target > time_stop > EOD). Multi-day orchestration with scanner simulation. Strategy factory for all 7 strategy types. CLI entry point.
- **Walk-forward integration**: `oos_engine` parameter on `walk_forward.py` selects BacktestEngine vs Replay Harness for OOS evaluation.
- **6 sessions** (S1–S6), all CLEAR. 85 new pytest tests. No new DEC entries.
- **State after:** BacktestEngine operational, all 7 strategies supported, walk-forward integration complete. Tests: 3,010 pytest + 620 Vitest.

### Sprint 21.6: Backtest Re-Validation (after Sprint 27) — NEXT
**Target:** ~2 days

**Scope:**
- Re-validate all 7 active strategies using BacktestEngine + Databento OHLCV-1m data (March 2023 – present).
- Compare Databento-based results against provisional Alpaca-era backtests (DEC-132).
- First real BacktestEngine run — validates speed claims and equivalence with Replay Harness.
- Update strategy parameters if data shows significant divergence.
- **Execution Quality Logging (DEC-358):** Add ExecutionRecord dataclass, logging in OrderManager.submit_order() and fill callback, `execution_records` table in argus.db. Captures expected vs actual fill price, slippage, time-of-day context, order size, latency. Starts calibration data collection from day one of paper trading.
- **Tests:** ~25 new.

### Sprint 27.5: Evaluation Framework (DEC-357) ✅
**Completed:** March 23–24, 2026 (6 sessions + 1 cleanup, +106 pytest)

**Scope:**
- **MultiObjectiveResult** — universal evaluation currency capturing Sharpe, max drawdown, profit factor, win rate, trade count, expectancy, regime breakdown, statistical confidence, walk-forward efficiency. Every downstream evaluator produces and consumes this.
- **ConfidenceTier** (HIGH/MODERATE/LOW/ENSEMBLE_ONLY) — enables hyper-specialized micro-strategies that can't be individually validated. Tier computed from trade count and regime distribution.
- **EnsembleResult** — first-class evaluation for strategy cohorts: aggregate metrics, diversification ratio, marginal contributions, tail correlation, capital utilization.
- **Regime-conditional evaluation** — BacktestEngine segments results by regime automatically, producing per-regime RegimeMetrics alongside aggregate metrics. RegimeMetrics designed for multi-dimensional regime vectors (forward-compatible with Sprint 27.6).
- **Comparison API** — `compare()`, `pareto_frontier()`, `soft_dominance()`, `is_regime_robust()`, `evaluate_cohort_addition()`, `marginal_contribution()`, `identify_deadweight()`.
- **Execution Quality Calibration (DEC-358):** `execution_quality_adjustment` field on MultiObjectiveResult. StrategySlippageModel calibration utility using accumulated ExecutionRecords. BacktestEngine gains optional `slippage_model` parameter.
- **Tests:** ~65 new.

**Dependencies:** Sprint 27 (BacktestEngine) ✅, Sprint 21.6 ✅. No frontend work.

### Sprint 27.6: Regime Intelligence (DEC-358) ✅ COMPLETE (March 24, 2026)
**Target:** ~3 days (6 sessions) → **Actual:** 12 sessions (S1–S10 + S5-fix + S27.6.1)

**Scope (delivered):**
- **RegimeVector** frozen dataclass with 6 dimensions (18 fields): trend (score + conviction), volatility (level + direction), breadth (score + thrust), correlation (average + regime), sector rotation (phase + leading/lagging sectors), intraday character (opening drive, first-30-min range, VWAP slope, direction changes, character classification).
- **Backward-compatible** — `RegimeVector.primary_regime` provides same MarketRegime enum for existing consumers. `regime_confidence` (0.0–1.0) for overall assessment.
- **RegimeOperatingConditions** + `matches_conditions()` API for strategy activation in regime regions.
- **New components:** BreadthCalculator (`core/breadth.py`), MarketCorrelationTracker (`core/market_correlation.py`), SectorRotationAnalyzer (`core/sector_rotation.py`), IntradayCharacterDetector (`core/intraday_character.py`), RegimeClassifierV2 (composes V1 + 4 calculators), RegimeHistoryStore (`core/regime_history.py` — SQLite persistence in `data/regime_history.db`, fire-and-forget, 7-day retention).
- **Config-gated** via `regime_intelligence.enabled` in `config/regime.yaml`. Per-dimension enable flags.
- **BacktestEngine integration** — `use_regime_v2` flag on BacktestEngineConfig.
- **Observatory wiring (Sprint 27.6.1)** — `Orchestrator.latest_regime_vector_summary` property → REST + WS endpoints → frontend `RegimeVitals` component.
- **All data from existing subscriptions** — $0 additional cost.
- **0 of reserved DEC-369–378 used** — sprint spec was comprehensive.
- **Tests:** 171 new (160 pytest + 11 Vitest).
- **DEF items opened:** DEF-091, DEF-092, DEF-093.

**Dependencies:** Sprint 27.5 (RegimeMetrics designed for multi-dimensional vectors) ✅.

### Sprint 27.7: Counterfactual Engine (DEC-358) ✅ COMPLETE (March 25, 2026)

**Actual:** 1 day (6 sessions + 1 cleanup). +105 tests (target ~50). 0 new DECs (reserved 379–385 unused — all patterns followed established precedent).

**Delivered:**
- **TheoreticalFillModel** (`core/fill_model.py`) — shared bar-level exit logic extracted from BacktestEngine. `FillExitReason` enum, `ExitResult` dataclass, `evaluate_bar_exit()` pure function. Used by both BacktestEngine and CounterfactualTracker.
- **CounterfactualTracker** (`intelligence/counterfactual.py`) — intercepts `SignalRejectedEvent` via event bus, opens shadow positions with IntradayCandleStore backfill, monitors via `CandleEvent` using shared fill model, MAE/MFE tracking, EOD close + no-data timeout. `RejectionStage` enum (QUALITY_FILTER, POSITION_SIZER, RISK_MANAGER, SHADOW). Zero-R guard.
- **CounterfactualStore** (`intelligence/counterfactual_store.py`) — SQLite in `data/counterfactual.db` (DEC-345 pattern), WAL mode, fire-and-forget writes, 90-day retention.
- **SignalRejectedEvent** (`core/events.py`) — published from 3 points in `_process_signal()`, gated by `_counterfactual_enabled` flag.
- **FilterAccuracy** (`intelligence/filter_accuracy.py`) — per-stage/reason/grade/regime/strategy accuracy. `GET /api/v1/counterfactual/accuracy` (JWT-protected).
- **Shadow strategy mode** — `StrategyMode` enum (LIVE/SHADOW) in `base_strategy.py`, shadow routing bypasses quality pipeline and risk manager. All 7 strategy YAMLs updated with explicit `mode: live`.
- **Config-gated** via `counterfactual.enabled` in `config/counterfactual.yaml`.

**Dependencies:** Sprint 27.5 ✅, Sprint 27.6 ✅. Existing evaluation telemetry and Databento stream.

### Sprint 27.75: Paper Trading Operational Hardening ✅ COMPLETE (March 26, 2026)

ThrottledLogger for log rate-limiting. Paper trading config overrides (10x risk reduction, throttle disabled, $10 min risk floor). Reconciliation logging consolidated. Tests: 3,528 pytest + 638 Vitest.

### Sprint 27.8: Operational Cleanup + Validation Tooling ✅ COMPLETE (March 26, 2026)

ExitReason.RECONCILIATION in events.py. Reconciliation auto-cleanup (config-gated). Bracket exhaustion detection. Per-strategy health reporting. `scripts/validate_all_strategies.py` batch revalidation. Tests: ~3,542 pytest + 638 Vitest.

### Sprint 27.9: VIX Regime Intelligence ✅ COMPLETE (March 26, 2026)

VIXDataService (yfinance daily VIX+SPX, 5 derived metrics, SQLite cache). 4 VIX calculators wired into RegimeClassifierV2. RegimeVector expanded from 6 to 11 fields. VixRegimeCard dashboard widget. REST endpoints. Config-gated via `vix_regime.enabled`. Tests: ~3,610 pytest + 645 Vitest. +75 new tests.

### Sprint 27.95: Broker Safety + Overflow Routing ✅ COMPLETE (March 26–28, 2026)

Reconciliation redesign with broker-confirmed positions (DEC-369). Overflow routing to CounterfactualTracker when at broker capacity (DEC-375). Stop resubmission cap with exponential backoff (DEC-372). Bracket revision-rejected handling (DEC-373). Fill dedup (DEC-374). Startup zombie cleanup (DEC-376). 9 new DECs (DEC-369–377). Tests: ~3,693 pytest + 645 Vitest.

### Sprint 28: Learning Loop V1 (DEC-163, DEC-354) ✅ COMPLETE (March 29, 2026)

**Delivered:**
- **OutcomeCollector** — read-only queries across trades, counterfactual, quality_history DBs. Source separation (trade vs counterfactual). DataQualityPreamble builder.
- **WeightAnalyzer** — source-separated Spearman correlations per quality dimension, p-value check, normalized positive correlation weight formula, per-regime breakdown, zero-variance guards.
- **ThresholdAnalyzer** — counterfactual-only analysis, missed opportunity rate > 0.40 → lower threshold, correct rejection rate < 0.50 → raise threshold.
- **CorrelationAnalyzer** — pairwise Pearson daily P&L correlations, trade-source preference, flagged pairs, overlap count.
- **LearningService** — pipeline orchestrator with concurrent guard, auto-trigger via SessionEndEvent, per-strategy metrics.
- **ConfigProposalManager** — startup-only application, atomic YAML writes, cumulative drift guard (20% over 30 days), sum-to-1.0 invariant, proposal supersession.
- **LearningStore** — SQLite in `data/learning.db`, 3 tables, retention enforcement.
- **SessionEndEvent** — published after EOD flatten, carries trade/counterfactual counts.
- **REST API** — 8 JWT-protected endpoints: trigger, reports, proposals, approve/dismiss/revert, config-history.
- **CLI** — `scripts/run_learning_analysis.py` with --window-days, --strategy-id, --dry-run.
- **Frontend** — Performance page "Learning" tab (LearningInsightsPanel, StrategyHealthBands, CorrelationMatrix), Dashboard LearningDashboardCard.
- **14 sessions**, 16 adversarial review amendments (3 Critical, 4 Significant, 9 Minor), 12 CLEAR / 2 CONCERNS (both resolved).
- **Tests:** ~3,693+645V → ~3,837+680V (+144 pytest, +35 Vitest).

**Key design decisions:**
- V1 is **advisory-only** — recommendations surface as ConfigProposals requiring human approval. Automated weight application deferred to Sprint 40 (Learning Loop V2).
- **Spearman rank correlation** replaces statistical lookup tables — lookup tables require data density that early paper trading won't provide.
- **Strategy parameters are NOT in scope** — Learning Loop observes and recommends Quality Engine meta-parameters (weights, thresholds, risk tiers). Individual strategy parameter tuning is Sprint 32+ (Parameterized Templates + Systematic Search).

### Sprint 28.5: Exit Management ✅ COMPLETE (March 30, 2026)

**Delivered:**
- **Trailing stops:** Configurable per-strategy trailing stop mechanism (ATR/percent/fixed modes) in Order Manager, with belt-and-suspenders pattern (broker stop + client-side trail check). Trail activates after T1 fill on remainder shares.
- **Partial profit-taking:** T1/T2 split with trail on T1 remainder.
- **Time-based exit escalation:** Progressive stop tightening via phase-based configuration in poll loop.
- **Pure function library:** `core/exit_math.py` — `compute_trail_stop_price()`, `compute_escalation_stop()`, `validate_time_stop()`.
- **Config:** `config/exit_management.yaml` with per-strategy overrides via deep merge.
- **BacktestEngine + CounterfactualTracker alignment:** AMD-7 bar-processing order (escalation → trail → fill model) consistent across all three exit-aware components.
- **SignalEvent `atr_value` field:** All 7 strategies emit ATR for trail distance computation.
- **6 sessions** (S1, S2, S3, S4a, S4b, S5), 12 adversarial review amendments verified, 0 issues.
- **Tests:** pytest +110 (3,845 → 3,955), Vitest +0. New DEFs: 108, 109, 110. No new DECs.

### Phase 6 Gate ★ CRITICAL — LIVE TRADING DECISION POINT ★

**Trigger:** Sprint 31A complete (after Pattern Expansion + Short Selling).
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Codebase Health Audit (`codebase-health-audit.md`) + Documentation Compression.

**ARGUS state at this gate:** 15 hand-crafted strategies (including at least one short strategy) with AI quality filtering, NLP catalysts, dynamic sizing, and performance-aware learning loop. Paper trading has been running for 6–8 weeks at this point. All strategies validated with BacktestEngine + 3 years of Databento data.

**What you see:** 15 strategy cards in the Pattern Library. Health bands on every strategy in the Orchestrator. Correlation heatmap on Performance. Short exposure indicator on Dashboard. Quality-graded signals firing throughout the day. Morning intelligence briefs. AI-generated debrief narratives.

**Critical decisions at this gate:**
1. **Live trading decision** — If paper trading results are strong (Sharpe > 2.0, positive expectancy, no catastrophic drawdowns), this is the natural point for Gate 5 (live minimum deployment). **Live trading with real capital could begin during or after Phase 6.** (CPA consultation removed per DEC-380; tax intelligence built into ARGUS via post-revenue Tax Intelligence Automation.)
2. **Ensemble go/no-go** — Confirm commitment to the ensemble research path (Phases 7–10). If choosing to defer, ARGUS continues as a strong artisanal multi-strategy system. Historical data is already available at no cost (DEC-353).

**Elapsed time from start:** ~5–7 weeks.

---

## 8. Phase 7: Infrastructure Unification (Sprints 29–32.5)

*Expands the strategy roster and adds short selling, then builds parameterized strategy system and experiment infrastructure for the ensemble vision. BacktestEngine (Sprint 27) provides the foundation. Nothing in this phase changes live trading behavior — it's building the research infrastructure in parallel. UI focus: the Research Console makes strategy research visible and interactive.*

**Amendment note (DEC-357):** Phase 7 gains Sprint 32.5 (Experiment Registry + Promotion Pipeline + Anti-Fragility + Hypothesis Generation Design) after Sprint 32. Sprint 33 scope decreases as evaluation framework and experiment storage already exist.

### Sprint 29: Pattern Expansion I (DEC-167, DEC-378) ✅
**Completed:** March 30–31, 2026 (2 days, 10 sessions)

**Delivered:**
- **Dip-and-Rip**, **HOD Break**, **Gap-and-Go**, **ABCD**, **Pre-Market High Break** (stretch scope delivered) pattern modules. All implement PatternModule ABC.
- **PatternParam** frozen dataclass (DEF-088 resolved) — `get_default_params()` returns `list[PatternParam]` with type, range, step, description, category. Bull Flag + Flat-Top Breakout retrofitted.
- **PatternBacktester** grid generation from PatternParam metadata (replaced ±20%/±40% variations).
- `set_reference_data()` hook + `initialize_reference_data()` on PatternBasedStrategy for prior close / PM context.
- Quality Engine integration automatic via `share_count=0` pipeline. Counterfactual tracking automatic.
- **No UI changes** (frontend locked for sprint).
- **12 strategies/patterns active.**
- **Tests:** +213 new (4,178 pytest + 689 Vitest).
- **Deferred to Sprint 32:** Runtime YAML→constructor param wiring (DEF-124), `_create_pattern_by_name()` extension for 4 remaining patterns (DEF-121), ABCD O(n³) sweep optimization (DEF-122). Deferred to Sprint 31.5: grid float accumulation cleanup (DEF-123).

### Sprint 29.5: Post-Session Operational Sweep ✅
**Completed:** March 31 – April 1, 2026 (7 sessions + final cleanup)

**Delivered:**
- **Flatten/Zombie Safety Overhaul (S1):** IBKR error 404 root-cause fix (re-query broker qty before resubmit), global flatten circuit breaker (`_flatten_abandoned` + `max_flatten_cycles`), EOD broker-only flatten Pass 2 (cleans zombie positions not in `_managed_positions`), startup zombie queue drained at 9:30 ET, time-stop log suppression via ThrottledLogger.
- **Paper Trading Data-Capture Mode (S2):** `daily_loss_limit_pct: 1.0`, `weekly_loss_limit_pct: 1.0`, `throttler_suspend_enabled: false` on OrchestratorConfig — maximum signal data collection for session analysis.
- **Win Rate Bug + UI Fixes (S3):** win_rate × 100 conversion in TradeStatsBar + TodayStats, trades table limit 250→1000, Shares column, "Trail" badge, stats polling 30s→10s.
- **Real-Time Position Updates (S4):** `usePositionUpdates` hook consuming WS `position.updated` events, merges into TanStack Query cache, REST polling reduced 5s→15s.
- **Log Noise Reduction (S5):** `ib_async.wrapper` → ERROR level, weekly loss limit warning throttled (60s), asyncio shutdown task batch cancellation.
- **MFE/MAE Trade Lifecycle Tracking (S6):** 6 fields on ManagedPosition, O(1) tick update, 4 new DB columns, debrief export auto-picks up via dynamic column discovery.
- **ORB Scalp Exclusion Fix (S7):** `orb_family_mutual_exclusion` config flag (default true); `false` disables DEC-261 to enable independent ORB Scalp data capture.
- **Tests:** +34 pytest, +11 Vitest (4,212 + 700 total). No new DECs. DEF-125 through DEF-128 logged.

### Sprint 30: Short Selling Infrastructure + Pattern Expansion II (DEC-166, DEC-167)
**Target:** ~3 days

**Scope:**
- **Short selling infrastructure** (`argus/execution/short_selling.py`): Locate/borrow tracking. Inverted risk logic (stop above entry, target below). Short-specific Risk Manager rules. Uptick rule compliance (SSR detection). Short exposure limits (separate from long limits).
- **Parabolic Short** strategy module: First short strategy. Parabolic extension detection, volume exhaustion, reversal candle patterns. Uses L1 signals only (Order Flow enhancement added post-revenue per DEC-238).
- 1–2 additional long pattern modules if velocity allows.
- **UI:** Dashboard gains short exposure indicator (active). Orchestrator gains short position section. Pattern Library gains Parabolic Short + any additional strategy cards.
- **13–15 strategies/patterns active (including first short strategy).**
- **Tests:** ~80 new.

### Sprint 31A: Pattern Expansion III (DEC-379)
**Target:** ~1–2 days

**Scope:**
- Additional pattern modules to reach 15 total strategies. All implement PatternModule with structured PatternParam metadata (from Sprint 29 DEF-088 resolution).
- Walk-forward validated. Quality Engine integration.
- **UI:** Pattern Library gains remaining strategy cards.
- **15 strategies/patterns active.**
- **Tests:** ~40 new.

### Sprint 31.5: Parallel Sweep Infrastructure (DEC-379)
**Prerequisites from Sprint 29:** DEF-123 (grid float accumulation cleanup).
**Target:** ~3–4 days

**Scope (backend):**
- Multiprocessing harness for BacktestEngine. Parameter grid specification format (consumes PatternParam metadata from Sprint 29).
- **Prerequisites from Sprint 29:** DEF-121 (extend `_create_pattern_by_name()` for remaining 4 patterns), DEF-122 (ABCD O(n³) optimization), DEF-124 (runtime YAML→constructor param wiring). Also wire Bull Flag/Flat-Top dead-code constructor params into detect()/score().
- Worker pool distributing parameter combinations across CPU cores.
- Result aggregation pipeline. Progress monitoring.
- Cloud burst configuration (spin up high-core-count instance for sweep days).

**Tests:** ~60 new.

### Sprint 31B: Research Console (NEW PAGE) — Deferred post-32.5 (DEC-379)
**Target:** ~3 days

**Note:** Deferred from original Sprint 31 position to after Sprint 32.5. Research Console is developer UX for strategy research visibility — valuable but not on the optimization critical path (32 → 32.5 → 33 → 33.5 → 34).

**Scope (frontend):** **Research Console** — Command Center page 9. Mission control for strategy research.
- **Run Manager:** Shows backtest runs in progress (progress bar, ETA), queued runs, completed runs. Each completed run: equity curve thumbnail, Sharpe, win rate, max drawdown, trade count.
- **Result Comparison:** Select 2–4 completed runs to compare side-by-side — overlaid equity curves, key metrics comparison table.
- **Run Configuration:** Form interface to configure BacktestEngine runs — select strategy, parameter values, symbol set, date range. Launch from UI.
- **Sweep Manager:** Like Run Manager but for multi-parameter sweeps. Progress: "12,400 / 48,000 combinations. ETA: 2.3 hours."
- **Sweep Heatmap:** 2D heatmap for any two-parameter sweep. Color = performance metric (Sharpe, win rate, etc.). Hover: full metrics for that cell. Click: detailed results. Progressive rendering as results arrive.
- **Parameter Landscape (3D):** Three.js surface plot for three-parameter exploration. Rotate, zoom, click on peaks and valleys. Toggle between Sharpe, win rate, max drawdown surfaces.

**State after:** The entire research workflow is visible on the Research Console. Combined scope from both original Sprint 31 entries.

**Tests:** ~80 new.

### Sprint 32: Parameterized Strategy Templates
**Target:** ~3–4 days

**Scope:**
- **StrategyTemplate** base class: Defines a strategy as a parameterized template with declared parameter ranges, filter dimensions, and validation criteria.
- Convert existing strategies (ORB Breakout, VWAP Reclaim, etc.) to template format. Template parameters include all tunable values — entry thresholds, targets, stops, time windows, volume filters, market cap filters, sector filters.
- **Template Gallery** on Pattern Library page: Evolves from individual strategy cards to template cards showing parameter ranges, instance count, and a mini sweep heatmap for each template.
- **Template Explorer:** Click a template → see all configured instances, parameter ranges, and which regions of parameter space have been explored.

**State after:** Every strategy exists as both a hand-tuned instance (the artisanal version from Phase 6) and a parameterized template (ready for systematic search). The Pattern Library shows both views.

**Tests:** ~60 new.

### Sprint 32.5: Experiment Registry + Promotion Pipeline (DEC-357)
**Target:** ~4–5 days (9 sessions)

**Scope:**
- **ExperimentRegistry** — persistent storage for every experiment ARGUS runs, designed for millions of entries. Partitioned by `(strategy_family, batch_id)`. Separate tables for core metadata vs full results. Pre-computed aggregate views via SQLite triggers: per-family success rates, per-type success rates (meta-learning), per-batch summaries. Archival policy for old REVERTED experiments.
- **PromotionCohort** — primary unit of promotion (20–50 strategies evaluated together, not individually). Formation rules by cohort type (INDIVIDUAL, FAMILY_SWEEP, CROSS_FAMILY, DISCOVERY_BATCH). HIGH-confidence strategies may form size-1 cohorts; LOW/ENSEMBLE_ONLY strategies require cohort of ≥10.
- **PromotionPipeline** — 8 stages: BACKTEST_VALIDATED → STRESS_TESTED (if Sprint 33.5 adopted) → SIMULATED_PAPER → PAPER_ACTIVE → PAPER_CONFIRMED → LIVE_PENDING_VETO → LIVE_ACTIVE → STABLE/REVERTED. Simulated-paper screening (BacktestEngine on recent 20 days) breaks the paper validation bottleneck from ~8 years to ~2 months.
- **Kill switches** — cohort level (5-day Pareto-dominated by baseline → auto-revert) and individual level (negative marginal Sharpe for 10 days → remove strategy, keep rest of cohort).
- **Human veto window** — 24–72h depending on cohort type. Veto via API endpoint + Command Center UI (DEC-357 modification); ntfy.sh for notifications only.
- **ExperimentQueue + background worker** — overnight autonomous operation. Market-hours-aware scheduling (~200 experiments/night sequential, ~6,400 with cloud burst from Sprint 31). Priority ordering: learning_loop > systematic_search > discovery_pipeline > manual.
- **Anti-Fragility Integration (DEC-358):** Loss-driven queue priority (investigate failures during drawdowns, explore during profits). Post-mortem automation on cohort revert (diagnose toxic strategies, check vulnerability of other cohorts). Drawdown-accelerated experimentation (80/20 diagnostic/exploration split during drawdown, increased monitoring frequency).
- **Hypothesis Generation Design document** — architecture for 4 generation methods (niche identification, pattern mutation, literature mining, anomaly detection) with `GeneratedHypothesis` interface specification. Committed to `docs/design/hypothesis-generation-architecture.md`. Design only — implementation at Sprint 41.
- **API:** 20+ endpoints for experiments, cohorts, queue, meta-learning, promotion pipeline.
- **Tests:** ~95 new.

**Dependencies:** Sprint 27.5 (MultiObjectiveResult, EnsembleResult, comparison API), Sprint 32 (templates define parameter space), Sprint 28 (retrofitted to write to registry). Existing ntfy.sh integration (DEC-279), BacktestEngine (Sprint 27).

### Phase 7 Gate

**Trigger:** Sprint 32.5 complete.
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression.

**Historical data sufficiency — RESOLVED (DEC-358).** XNAS.ITCH + XNYS.PILLAR provide OHLCV-1m back to May 2018 (~96 months) at $0 on Standard plan. Three-way splits across 96 months provide ample statistical power. The data purchase concern from the original roadmap is no longer applicable. BacktestEngine's HistoricalDataFeed gains exchange-specific dataset mode in Sprint 33.5.

**Key assessment:** Confirm Sprint 32.5 scope based on paper trading experience. Adjust cohort sizes, veto windows, kill switch thresholds. Review overnight compute capacity — is sequential worker sufficient for Sprint 33, or should Sprint 31 parallelism be prioritized?

---

## 9. Phase 8: Controlled Experiment (Sprints 33–35)

*The proving ground. Takes one strategy family and systematically searches the parameter × filter space. Validates the methodology before scaling. UI focus: make the search process and statistical validation legible.*

**Amendment note (DEC-358):** Phase 8 gains Sprint 33.5 (Adversarial Stress Testing) between Sprint 33 and Sprint 34. Stress testing becomes a gate in the PromotionPipeline — no cohort reaches paper without surviving simulated crises. Sprint 33.5 also builds the exchange-specific HistoricalDataFeed mode for XNAS.ITCH + XNYS.PILLAR, giving Sprint 33 access to 96 months of data instead of 35.

### Sprint 33: Statistical Validation Framework
**Target:** ~3–4 days

**Scope (backend):**
- FDR correction implementation (Benjamini-Hochberg). Minimum trade count thresholds per micro-strategy.
- Three-way data split infrastructure (train / selection / validation). With XNAS.ITCH + XNYS.PILLAR providing 96 months of data (DEC-358), three-way splits have ample statistical power.
- Smoothness prior — neighboring parameter/filter cells must show correlated performance for any cell to be considered valid.
- Out-of-sample ensemble validation metrics. Walk-forward at ensemble level.
- **Note:** Scope reduced from original plan — evaluation framework (Sprint 27.5), experiment storage (Sprint 32.5), and aggregate views already exist. Sprint 33 focuses purely on statistical methods.

**Scope (frontend):** Research Console — Validation Dashboard:
- **Data Split Visualizer:** Timeline bar showing train / selection / validation partitions.
- **FDR Report View:** Total candidates tested, survivors after FDR correction, effective significance threshold, p-value distribution histogram.
- **Smoothness Heatmap:** Overlay on sweep heatmap showing smoothness prior — validated cells glow, isolated spikes dimmed/crossed out. Toggle raw vs. filtered views.

**Tests:** ~60 new.

### Sprint 33.5: Adversarial Stress Testing (DEC-358)
**Target:** ~3 days (5 sessions)

**Scope:**
- **Historical stress scenarios** — replay ensemble through 5 known crisis periods: COVID crash (Feb–Mar 2020), meme stock mania (Jan–Feb 2021), SVB week (Mar 2023), yen carry unwind (Aug 2024), Treasury selloff (Oct 2023). All confirmed available via XNAS.ITCH + XNYS.PILLAR OHLCV-1m at $0 on Standard plan.
- **Synthetic stress scenarios** — 4 structural stress tests: correlation spike (all pairwise correlations to 0.9), liquidity drought (50% fill failure + 3× slippage), gap-through-stop (2× stop distance overnight gap), simultaneous multi-strategy drawdown (worst historical drawdowns forced concurrent).
- **StressTestResult** — max drawdown, recovery days, kill switch response time, regime detection quality, risk containment metrics, pass/fail verdict.
- **PromotionPipeline integration** — becomes Stage 1.5 gate between BACKTEST_VALIDATED and SIMULATED_PAPER. All scenarios must pass: max drawdown <15%, kill switch fires within 5 days in crash scenarios, no daily loss limit breach, correlation spike Sharpe >0.5, gap-through-stop worst-case <5%.
- **Exchange-specific HistoricalDataFeed mode** — queries XNAS.ITCH + XNYS.PILLAR separately and merges results for pre-March-2023 data. Also benefits Sprint 33 statistical validation with 96 months of data instead of 35.
- **Tests:** ~55 new.

**Dependencies:** Sprint 32.5 (PromotionPipeline for Stage 1.5 gate), Sprint 27.5 (BacktestEngine with MultiObjectiveResult), Sprint 27.6 (regime transition detection quality is a metric), BacktestEngine (Sprint 27).

### Sprint 34: ORB Family Systematic Search ★ THE PIVOTAL EXPERIMENT ★
**Target:** ~4–5 days (compute-heavy — may need cloud burst)

**Scope:** Take the ORB Breakout template and systematically search:
- Entry parameters: 15–20 values
- Target parameters: 10–15 values
- Stop parameters: 5–10 values
- Time windows: 8–10 slices
- Volume filters: 5 buckets
- Market cap filters: 5 buckets
- Sector filters: 11 GICS sectors + "any"
- Day-of-week filters: 5 + "any"

Estimated total combinations: ~500K–2M (many eliminated by incompatibility). Tiered sweep: coarse screen (vectorized, fast) → focused BacktestEngine validation (~50K candidates) → statistical filtering → walk-forward ensemble validation.

**UI experience during the experiment:** Research Console makes this a visual experience:
- **Stage 1 (coarse scan):** Sweep heatmap populates progressively. Hot zones emerge, dead zones darken.
- **Stage 2 (focused validation):** Survivors highlighted. Focused sweep on candidates.
- **Stage 3 (statistical filtering):** FDR report renders. Smoothness overlay activates. Candidates filtered visually.
- **Stage 4 (ensemble validation):** Validated micro-strategies tested as ensemble on out-of-sample data. Ensemble equity curve alongside hand-crafted ORB Breakout + ORB Scalp for direct comparison.

**Success criteria:** Validated ORB micro-strategy ensemble outperforms hand-tuned ORB Breakout + ORB Scalp on out-of-sample data.

**Tests:** ~40 new.

### Sprint 35: Ensemble Performance Analysis
**Target:** ~2–3 days

**Scope:** Deep analysis of Sprint 34 results. Correlation structure among validated micro-strategies. Capital efficiency. Turnover and commission impact. Drawdown comparison. Regime sensitivity.

**UI deliverable:** Research Console — Ensemble Analysis Suite:
- **Correlation Cluster Map:** Force-directed graph of validated micro-strategies, proximity = correlation. 2D precursor to the Synapse.
- **Regime Performance Breakdown:** Faceted chart showing ensemble performance across market regimes.
- **Commission Impact Model:** Net returns after simulated commissions at various trade frequencies.
- **Go/No-Go Dashboard:** Summary view with key comparison metrics, statistical confidence, clear visual verdict.

**Tests:** ~30 new.

### Phase 8 Gate ★★★ THE GO/NO-GO DECISION ★★★

**Trigger:** Sprint 35 complete.
**Protocol:** Custom Gate Review (see SPRINT_CAMPAIGN.md Section 7).

**If GO:** Validated ensemble of ORB micro-strategies outperforms hand-crafted baselines. Methodology proven. Proceed to Phase 9 (cross-family scaling).

**If NO-GO:** Diagnose through visual tools. Determine if salvageable (methodology adjustment → revised Sprint 34) or fundamental (approach doesn't work → continue artisanal path). BacktestEngine, Research Console, and statistical framework remain valuable for individual strategy research regardless. ARGUS remains a strong multi-strategy system with the Phase 6 roster.

**ARGUS state regardless of outcome:** Production trading continues with 13–15 strategies. The Research Console is a sophisticated analysis environment — sweep heatmaps, 3D parameter landscapes, FDR reports, smoothness overlays, ensemble equity curves.

**Elapsed time from start:** ~9–12 weeks.

---

## 10. Phase 9: Ensemble Scaling (Sprints 36–39)

*ONLY EXECUTES IF PHASE 8 GO.*

*Extends the proven methodology across all strategy families. Builds the Ensemble Orchestrator and the Synapse visualization. UI focus: making the full ensemble comprehensible as a living neural system.*

### Sprint 36: Cross-Family Search (VWAP + Afternoon Momentum)
**Target:** ~4–5 days

**Scope (backend):** Apply Sprint 34 methodology to VWAP Reclaim and Afternoon Momentum template families. Same tiered sweep → statistical filtering → ensemble validation pipeline. Cross-family correlation analysis.

**Scope (frontend):** Research Console — Cross-Family View:
- Multi-family color-coded correlation cluster map (expanding the Sprint 35 cluster map).
- **Family Contribution Chart:** Percentage of ensemble returns from each strategy family, broken down by regime. "In trending markets, ORB contributes 45% and VWAP contributes 35%."

**State after:** Three strategy families have validated micro-strategy ensembles. Cross-family diversification measured. Total validated micro-strategies: likely 100–400.

### Sprint 37: Cross-Family Search (Remaining Families)
**Target:** ~4–5 days

**Scope:** Red-to-Green, Gap-and-Go, ABCD, Parabolic Short, and remaining artisanal strategies from Phase 6 get the systematic search treatment. Each family's template is swept and filtered.

**UI deliverable:** Research Console correlation map shows full strategy universe — all families, all validated micro-strategies, all cross-family correlations. Density reaching the point where the Synapse becomes necessary.

**State after:** All strategy families have validated ensembles. Total micro-strategies: potentially 200–800.

### Sprint 38: Ensemble Orchestrator V2 + Synapse (Analysis Mode)
**Target:** ~6–7 days (the largest sprint in the roadmap — backend Orchestrator + full 3D visualization)

**This sprint should be decomposed into 37a (backend) and 37b (frontend) during sprint planning.**

**Scope (backend) — Ensemble Orchestrator V2:**

Replaces the current equal-weight Orchestrator (DEC-118) with an ensemble-aware system. Core capabilities:
- **Activation filtering:** Only micro-strategies whose conditions match current market state are "hot." Pre-specified conditions make this a lookup, not a computation.
- **Correlation-aware capital allocation:** Highly correlated active strategies share a capital pool. Uncorrelated strategies get independent allocation.
- **Position consolidation:** When 50 micro-strategies want to buy NVDA simultaneously, the Orchestrator consolidates into a single position sized by aggregate conviction.
- **Regime-dependent ensemble selection:** In high-volatility regimes, only micro-strategies validated in high-vol conditions activate. Learning Loop feeds regime classification.

> **Note:** This supersedes the original "Orchestrator V2" concept from previous roadmaps. The original was an enhanced rules-based system for ~15 strategies. This is fundamentally different — it handles hundreds of micro-strategies with correlation-aware allocation.

**Scope (frontend) — The Synapse** — Command Center page 10.

The centerpiece visualization of the ensemble vision. Initial build (analysis mode — not yet real-time).

**3D Strategy Space (Three.js):** Each validated micro-strategy is a node — a small sphere — floating in 3D space rendered via WebGL. Three spatial axes mapped to configurable dimensions. Default: X = time-of-day, Y = hold duration, Z = strategy family (depth layers). Control panel remaps any axis to: sector, market cap, volume regime, quality score, recent Sharpe, win rate, correlation cluster, or any template parameter.

**Visual encoding:**
- **Color:** Family base hue (blue=ORB, green=VWAP, amber=Afternoon Momentum, purple=Red-to-Green, etc.). Brightness = validation strength.
- **Opacity:** Recent activity — recently fired nodes are opaque, dormant nodes are translucent.
- **Size:** Capital allocation. Larger nodes = more capital. Smooth animation on reallocation.
- **Connections:** Thin lines between highly correlated micro-strategies, intensity proportional to correlation strength. Toggleable.

**Navigation:** Click-drag to rotate. Scroll to zoom. Click node → info panel (full spec, performance, state, trade history). Click cluster → aggregate metrics. Double-click cluster → zoom in.

**Grouping modes** (smooth animated transitions between views):
- **By family:** Strategy family clusters. Alpha source diversity.
- **By time window:** Morning / midday / afternoon sectors. Temporal coverage.
- **By sector:** GICS sector groupings. Market exposure.
- **By regime:** Low-vol / normal / high-vol validated strategies. Regime adaptiveness.
- **By performance:** Hot (recent winners) vs. cold (recent losers).

Each grouping mode rearranges with smooth fly-through animation — nodes flow from one arrangement to another, maintaining identity.

**Performance target:** 60fps with 800 nodes. Instanced mesh geometry. Zustand state management. Spring physics for transitions.

**Special: Mini-Discovery before implementation.** Run a focused Three.js research conversation before writing code (can overlap with 37a backend work). Explore instanced mesh geometry, spring physics, WebGL performance budgets.

### Sprint 39: Ensemble Monitoring + Real-Time Synapse
**Target:** ~5–6 days

**This sprint should be decomposed into 38a (backend WebSocket) and 38b (frontend) during sprint planning.**

**Scope (backend):** WebSocket stream for ensemble state changes. Micro-strategy activation events, position events, allocation changes, health status — all pushed real-time.

**Scope (frontend):** The Synapse goes live.

**Real-time firing effects:**
- Signal generated → node **pulses** — bright flash radiating outward as a spherical ripple, like a neuron firing.
- Signal executed → ripple solidifies into persistent glow, gentle pulsing with P&L ring (green = profitable, red = underwater, thickness = magnitude).
- Signal rejected → ripple fades with brief red flash, node returns to dormant translucency.
- Over a trading day, activation patterns sweep across the Synapse — morning strategies lighting up the left side, afternoon strategies lighting up the right. Sector clusters flash on news. High-vol strategies activate on volatility spikes.

**Timeline scrubber:** Replay the day's activity in fast-forward. Watch the entire session's firing patterns compressed into 30 seconds.

**Dashboard evolution:**
- **Ensemble Heartbeat:** Active strategy count, capital utilization, aggregate position count, portfolio heat.
- **Family Activity Bars:** Horizontal bars per family showing activation level.
- **Mini-Synapse:** Simplified 2D Synapse embedded in Dashboard. Click to open full page.

**Orchestrator evolution:**
- **Activation Stream:** Real-time feed — "14:23:07 | ORB-T47 | NVDA | Signal: BUY | Quality: 78 | EXECUTED @ $892.34"
- **Capital Allocation Treemap:** How capital is distributed across families, strategies, positions. Larger rectangles = more capital. Color = P&L.

**Performance evolution:**
- **Contribution Attribution:** Waterfall chart showing which families/clusters/micro-strategies contributed to today's P&L.
- **Correlation Stability Monitor:** Time series showing whether historically uncorrelated families remain uncorrelated. Drift detection alerts.

**Debrief evolution:** AI-generated ensemble narrative — "Today ARGUS activated 47 micro-strategies across 4 families. The ORB cluster was most active in the first hour, contributing $340 in realized P&L across 12 positions..."

### Phase 9 Gate

**Trigger:** Sprint 39 complete.
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Codebase Health Audit (`codebase-health-audit.md`) + Documentation Compression.

**Assessment:** Ensemble operational in paper trading? Synapse working? 20–60 micro-strategies activating per day as expected? Ensemble Sharpe tracking toward 3.0+? System fast enough at scale?

**ARGUS state:** 200–800 validated micro-strategies across all families. Ensemble-aware Orchestrator. Correlation-managed allocation. Comprehensive visual monitoring anchored by the real-time Synapse.

**Elapsed time from start:** ~12–16 weeks.

---

## 11. Phase 10: Full Vision (Sprints 40–42)

*The self-improving system. The ensemble doesn't just execute — it learns, adapts, and evolves. UI focus: make adaptation and discovery visible.*

### Sprint 40: Learning Loop V2 (Ensemble Edition)
**Target:** ~4–5 days

**Scope (backend):**
- Automated performance tracking at micro-strategy level. Underperformers automatically throttled, outperformers boosted (within risk limits).
- Rolling recalibration: every N trading days, statistical validation re-runs on recent data to check if validated strategies still hold.
- Automatic retirement of strategies that lose their edge. Automatic promotion of promising candidates from staging queue (human approval still required).

**Scope (frontend):** The Synapse becomes a living ecosystem:
- **Lifecycle visualization:** Newly promoted strategies fade in and grow from zero. Throttled strategies shrink gradually. Retiring strategies fade out over several sessions — dimmer, greyer, smaller, like neurons going dark.
- **Health decay indicators:** Declining performance causes slow color shift from family hue toward grey.
- **Adaptation Timeline** on Research Console: Ensemble evolution over time — additions, retirements, throttles, boosts, net ensemble metrics. "Week 3: +12 ORB variants promoted, -4 VWAP variants retired, net ensemble Sharpe: 2.7 → 2.9."

### Sprint 41: Continuous Discovery Pipeline
**Target:** ~3–4 days

**Scope (backend):**
- Background process exploring new parameter/filter combinations overnight (US markets closed).
- When market conditions change (new sectors emerge, volatility regime shifts), pipeline searches for micro-strategies that work in new conditions.
- Validated discoveries enter staging queue for human review before activation.
- Morning intelligence brief gains "Overnight Discovery" section.

**Scope (frontend):** Research Console — Discovery Feed:
- **Overnight Results:** Morning panel showing discoveries — "3 new micro-strategies validated in healthcare sector with earnings catalyst filter." Approve/reject buttons per discovery.
- **Staging Queue on Synapse:** Ghost nodes showing where discoveries would live in strategy space. Preview how new strategies change ensemble shape before committing.
- **Discovery Heatmap:** Which regions of parameter/filter space are being explored, exhausted, or yielding discoveries.

### Sprint 42: Performance Workbench
**Target:** ~4–5 days

**Scope:** Customizable widget grid using `react-grid-layout`. Drag/drop/resize visualizations into personalized analysis workflows.

**Widget palette:** Strategy family performance charts, correlation matrix heatmap, regime analysis panels, micro-strategy activation heatmap (time-of-day × day-of-week), capital utilization over time, drawdown decomposition, sector exposure history, quality score distribution, win rate breakdowns (by family / regime / time-of-day), commission impact tracker, ensemble Sharpe rolling window, Mini-Synapse (embeddable), discovery pipeline status, custom metric formulas.

**Two-stage build:**
1. Rearrangeable tab system — save custom page layouts as named tabs ("Morning Review," "Live Session," "Post-Session Analysis," "Weekly Deep Dive").
2. Full widget palette — drag any widget onto any tab, resize and arrange freely.

**State after:** Bloomberg-terminal-grade analysis environment. Build views that match your workflow, not a predetermined layout.

### Phase 10 Gate (Full Vision)

**Trigger:** Sprint 42 complete.
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Final Documentation Reconciliation.

**Full system assessment:**
- All 10 pages operational? Synapse live? Discovery pipeline running? Performance Workbench customizable?
- Ensemble Sharpe on paper trading? Drawdown metrics? Comparison to Phase 6 artisanal baseline?
- Is the nightly workflow (review brief → approve discoveries → monitor session → review debrief) sustainable? Achieving "few hours of active work" goal?
- If not already live from Phase 6 gate, is this the right time?
- Horizon items priority ordering.

**What this means for the family:** If the ensemble achieves Sharpe 3.0+ on $200K+ capital, the income generation goal from the Day Trading Manifesto is met with substantial margin. The few hours of active work per night becomes: review intelligence brief, approve/reject discoveries, monitor the Synapse during the session, review the debrief. The system runs. You supervise.

**Elapsed time from start:** ~15–20 weeks (~4–5 months).

---

## 12. Summary Timeline

| Phase | Sprints | Focus | Duration | Cumulative |
|-------|---------|-------|----------|------------|
| 5: Foundation Completion | 21.5–24 | Live trading, AI layer, quality filtering | ~2–3 weeks | Weeks 1–3 |
| 6: Strategy Expansion | 25–31A | 15 artisanal strategies, short selling, Learning Loop V1, Exit Management | ~2–3 weeks | Weeks 3–6 |
| 7: Infrastructure Unification | 31.5–32.5 | Parallel sweeps, templates, experiment registry | ~2–2.5 weeks | Weeks 6–8.5 |
| 7.5: Research Console | 31B | Research Console (deferred from Phase 6 per DEC-379) | ~0.5 week | Week 9 |
| 8: Controlled Experiment | 33–35 | Statistical framework, stress testing, ORB search, go/no-go | ~2–2.5 weeks | Weeks 9–11.5 |
| 9: Ensemble Scaling | 36–39 | Cross-family search, Synapse, live ensemble | ~3–4 weeks | Weeks 11.5–15.5 |
| 10: Full Vision | 40–42 | Learning Loop V2, discovery pipeline, workbench | ~2.5–3.5 weeks | Weeks 15.5–19+ |

**Total: ~42+ sprints across ~19+ weeks / 4.5+ months**

---

## 13. Command Center Evolution Summary

| Sprint | Page Changes |
|--------|-------------|
| 21.7 ✅ | Dashboard: +Pre-Market Watchlist panel (FMP Scanner) |
| 22 | Copilot: shell → live |
| 23 | Dashboard: +catalyst badges. Debrief: +AI narratives. +Pre-Market Intelligence Brief view |
| 24 | Trades: +quality badges. Orchestrator: +live quality scoring. Dashboard: +Signal Quality Distribution. Debrief: +quality vs. outcome scatter |
| 25 | Pattern Library: +3 new strategy cards (R2G, Bull Flag, Flat-Top) |
| 26 | Pattern Library: +3–4 cards. Dashboard: +Short Exposure indicator (prep) |
| 27 | Pattern Library: +Parabolic Short + 1–2 cards. Dashboard: Short Exposure active. Orchestrator: +short positions |
| 28 | Orchestrator: +Strategy Health Panel with health bands + throttle/boost cards. Performance: +Correlation Matrix. Dashboard: +weekly insight card |
| 29 | Pattern Library: +4–5 new strategy cards (ABCD, Dip-and-Rip, HOD Break, Gap-and-Go) |
| 30 | Pattern Library: +Parabolic Short + 1–2 cards. Dashboard: Short Exposure active. Orchestrator: +short positions |
| 31A | Pattern Library: remaining strategy cards to reach 15 total |
| 31B (post-32.5) | **+Research Console (page 9):** Run Manager, Result Comparison, Run Configuration, Sweep Manager, Sweep Heatmap, Parameter Landscape (3D) |
| 32 | Pattern Library: evolves to template gallery with instance browser and template explorer |
| 32 | Research Console: +Data Split Visualizer, +FDR Report, +Smoothness Heatmap overlay |
| 33 | Research Console: live progressive sweep rendering, staged validation views |
| 34 | Research Console: +Correlation Cluster Map, +Regime Breakdown, +Go/No-Go Dashboard |
| 35 | Research Console: +Cross-Family View, +Family Contribution Chart |
| 37 | **+Synapse (page 10):** 3D strategy space, grouping modes, navigation. Analysis mode. Ensemble Orchestrator V2 backend |
| 38 | Synapse: +real-time firing, +timeline scrubber. Dashboard: +Ensemble Heartbeat, +Family Activity Bars, +Mini-Synapse. Orchestrator: +Activation Stream, +Capital Treemap. Performance: +Contribution Attribution, +Correlation Stability. Debrief: ensemble-scale AI narratives |
| 39 | Synapse: +lifecycle animations. Research Console: +Adaptation Timeline |
| 40 | Research Console: +Discovery Feed, +Staging Queue (ghost nodes on Synapse), +Discovery Heatmap. Intelligence Brief: +overnight discovery results |
| 41 | **Performance Workbench:** react-grid-layout widget system, customizable analysis tabs |

---

## 14. Key Architectural Notes

### VectorBT Role Transition
VectorBT currently handles all parameter sweeps. After Phase 7, the BacktestEngine takes over for serious validation work. VectorBT remains useful for rapid coarse screening (Stage 1 of the tiered sweep) but is no longer the primary optimization tool.

### Pattern Library Page Semantics
Evolves from individual strategy gallery (current) → template gallery with parameter ranges (Sprint 32) → secondary to the Synapse for ensemble visualization (Sprint 38+). The Pattern Library doesn't disappear, but its role shifts from "primary strategy view" to "template reference and configuration tool."

### Dashboard Density Management
The Dashboard accumulates significant new panels across this roadmap. The Performance Workbench (Sprint 42) partially solves this by letting you customize which panels appear where. Until then, use progressive disclosure: panels appear only when relevant features are active.

### Orchestrator V2 Supersession
The original Orchestrator V2 concept (enhanced rules-based for ~15 strategies) is superseded by the Ensemble Orchestrator in Sprint 38. These are incompatible approaches — the ensemble version handles hundreds of micro-strategies with correlation-aware allocation and activation filtering.

---

## 15. Critical Risks

| Risk | Severity | Phase | Mitigation |
|------|----------|-------|------------|
| **Historical data insufficiency** | ~~High~~ RESOLVED | 8 | ~~Purchase 5–10yr Databento history before Phase 8.~~ XNAS.ITCH + XNYS.PILLAR provide OHLCV-1m back to May 2018 (~96 months) at $0 on Standard plan (DEC-358). Exchange-specific HistoricalDataFeed mode built in Sprint 33.5. |
| **Overfitting the quality model** | High | 5–6 | Walk-forward validation on quality scores. Out-of-sample calibration mandatory. |
| **Phase 8 experiment failure** | Medium | 8 | System is valuable regardless (Phase 6 artisanal trading continues). Ensemble ceiling lost but floor unchanged. |
| **Pattern library complexity explosion** | Medium | 6–7 | Each pattern must pass walk-forward independently. Retire patterns that don't earn their keep. |
| **Dynamic sizing amplifies losses** | Medium | 5 | A+ sizing caps at 3%. Account-level daily/weekly limits unchanged. Circuit breakers still override. |
| **Claude API latency** | Medium | 5 | Cache catalyst scores (don't change intraday). Pre-compute during pre-market. Only novel catalysts need real-time scoring. |
| **Broad-universe processing throughput** | Low | 5–9 | Pure Python at 4,000 symbols uses ~2–4% CPU. Monitor during paper trading. If per-second processing exceeds 100ms, Cythonize IndicatorEngine hot path (~0.5 day effort). DEC-263. |
| **Three.js performance at scale** | Medium | 9 | Instanced mesh geometry. Performance target: 60fps at 800 nodes. Budget for optimization sessions. |
| **Scope creep extending timeline** | Medium | All | Each sprint is independently valuable. Can pause at any phase boundary. |
| **Cape Town latency (~200–250ms)** | Low | All | Structural disadvantage for ultra-short holds. Longer-duration strategies (5–30 min) preferred. Already reflected in strategy design. |
| **IBKR Gateway nightly resets** | Low | All | Automated reconnection (RSK-022). live-operations.md procedures. |

---

## 16. Post-Revenue Backlog

Items deferred until monthly trading income justifies their cost or complexity. These are tracked here so nothing is lost from previous roadmap iterations.

### Tax Intelligence Automation (DEC-380)

**Trigger:** Live trading active, real tax liability being generated.

**Tax Compliance Automation (~2–3 days):**
- **Wash sale rule tracking and avoidance** — automatic detection of wash sale violations across all strategies; proactive avoidance mode that blocks re-entry into a symbol within the 30-day wash sale window when a loss was realized. Config-gated (can disable avoidance for strategies where re-entry is more valuable than tax benefit).
- **Cost basis method optimization** — support FIFO, LIFO, and specific identification; recommend optimal method per position based on tax impact. Track cost basis per lot.
- **Trade log export** — compatible export formats for TradeLog, GainsKeeper, and standard CPA handoff (CSV + PDF summary). Include wash sale adjustments, cost basis, holding periods.

**Tax Planning Intelligence (~1–2 days):**
- **Section 475 MTM election analysis** — model P&L impact of mark-to-market vs standard accounting based on actual trading patterns. Present recommendation with projected tax difference.
- **Estimated tax payment calculator** — quarterly estimated payment amounts based on realized P&L, projected annual income, and applicable tax brackets. Push notification reminders before quarterly deadlines (April 15, June 15, September 15, January 15).
- **Year-end tax planning** — tax-loss harvesting opportunities, strategy-level P&L attribution for Schedule D, short-term vs long-term classification (all day trades are short-term, but system should track for any swing positions).

**AI Copilot Tax Context (~0.5 day):**
- Tax-aware recommendations in AI Copilot — "You have $X in unrealized losses that could offset today's gains if harvested before year-end."
- Tax impact preview on trade proposals — estimated tax liability of proposed position.

**UI:** Performance page gains "Tax" tab with year-to-date liability, wash sale exposure, estimated payments timeline, and export controls.

### Order Flow Intelligence (DEC-238)

**Trigger:** Monthly trading income justifies Databento Plus tier ($1,399/mo). Historical L2/L3 available on current Standard plan for backtesting signal quality before activation.

**Order Flow Model V1** (~2–3 days):
- Databento L2 (MBP-10, 10 depth levels) subscription for watchlist symbols. Extend DatabentoDataService.
- **OrderFlowAnalyzer** (`argus/intelligence/order_flow.py`): Real-time L2 signal extraction — bid/ask imbalance ratio, ask thinning rate, tape speed (prints/sec), bid stacking score.
- **OrderFlowEvent** on Event Bus. **OrderFlowSnapshot** for strategy consumption.
- Throttled updates (100ms intervals).
- API endpoint: `/api/v1/orderflow/{symbol}`.
- UI: L2 visualization in stock detail panel (heatmap depth chart), flow quality indicators.

**Order Flow Model V2 + L3** (~1–2 days):
- Databento L3 integration (individual order events).
- Iceberg detection, spoofing detection, momentum absorption analysis.

**Setup Quality Engine 6th Dimension** (~0.5 day):
- Add Order Flow (20%) to quality scoring. Rebalance all weights to original 6-dimension design per DEC-239.
- Config change, not code change (weights are YAML-configurable).

**Order Flow in Ensemble Context:**
- Micro-strategies incorporating order flow signals. Synapse gains "order flow strength" dimension for axis mapping.

### Multi-Asset Expansion

**Phase 2: Cryptocurrency**
- Via IBKR (BTC, ETH, LTC, BCH) or Alpaca Crypto (broader selection, 24/7).
- Crypto-specific strategies. Crypto-aware tax tracking.
- Different market microstructure — wider spreads, different liquidity profiles, manipulation risk.
- Ensemble methodology applicable: parameterized crypto templates, systematic search.
- Synapse gains asset-class color layers.

**Phase 3: Forex**
- Via IBKR (complete coverage, same account/API).
- IQFeed supplemental data for forex ticks and market breadth (~$160–250/mo, DEF-011).
- Forex-specific strategies (session-based momentum, carry trade variants).
- Session-aware scheduling (Tokyo, London, New York).
- Section 988/1256 tax election support.

**Phase 4: Futures**
- Via IBKR (CME, CBOT, NYMEX, COMEX, ICE, same account/API).
- Databento CME Globex dataset (+$179/mo).
- Futures-specific strategies (E-mini, Micro contracts).
- No PDT restrictions. 60/40 tax treatment. Nearly 24-hour trading.

### Performance & Infrastructure

**Cython/Rust Hot Path:**
- If BacktestEngine speed is the bottleneck for continuous discovery, rewrite inner loop in compiled code for 10–50x speedup.
- If live IndicatorEngine processing on broad universe (DEC-263) exceeds 100ms/sec during Phase 9+ ensemble scale, Cythonize VWAP/ATR/EMA update functions. Estimated ~0.5 day effort, 10–50x speedup on hot path. Not expected to be needed before Phase 9 (~200+ micro-strategies).

**Monte Carlo Simulation:**
- Risk assessment via simulation. Confidence intervals on expected returns, drawdown probabilities.

**Advanced Regime Engine:**
- Multi-factor regime classification (sector rotation, breadth, yield curve, VIX term structure).
- Regime prediction (not just detection) using trend analysis.
- Strategy-specific regime sensitivity profiles.

### Account & Tax Management

**Multi-Account Management:**
- Different ensemble configurations for different risk profiles (conservative IRA vs. aggressive individual account).
- Synapse shows account-specific views.

**Advanced Tax Optimization:**
- Wash sale avoidance automation. Tax-loss harvesting.
- Integration with dedicated trader tax services (TradeLog, GainsKeeper).

### Strategy Development

**Learning Loop V3 (ML):**
- Replace statistical lookup tables with gradient-boosted model (LightGBM or similar).
- Feature engineering from accumulated trade data.
- A/B framework: ML model alongside statistical model, compare.

**Strategy Breeding:**
- Genetic algorithms for parameter exploration. Cross-strategy feature combination.

**Cross-Market Signal Detection:**
- Futures leading equities, sector rotation signals, international market correlation.

### Aspirational

**Synapse VR/AR Mode:**
- At 1,000+ strategies, true 3D navigation via VR headset becomes compelling.
- Walk through strategy space, reach out and touch clusters, see firing patterns surround you.
- WebXR — aspirational but technically feasible.

---

## 17. Infrastructure Cost Projection

| Phase | Monthly Cost | What's Added |
|-------|-------------|-------------|
| Current (Phase 5) | ~$221/mo | Databento Standard ($199) + FMP Starter ($22) |
| Phase 5 (Sprint 22+) | ~$256–271/mo | + Claude API (~$35–50) |
| Phase 6+ | ~$315–420/mo | + FMP Premium/Ultimate ($59–149 for NLP in Sprint 23) |
| Post-Revenue | ~$1,620–1,820/mo | + Databento Plus ($1,399 for Order Flow) |
| Multi-Asset | ~$1,800–2,070/mo | + Databento CME ($179) + IQFeed ($160–250) |

One-time costs: ~~Historical data purchase~~ — deferred indefinitely per DEC-353 (Standard plan includes free OHLCV-1m history). Cloud burst compute (pay-per-use, Phases 8–9). Tick-level historical data only if systematic search requires sub-minute precision (estimated $0.21/symbol/month via pay-as-you-go).

---

## 18. The Decision That Matters Most

The entire roadmap pivots on the outcome of Sprint 34 (ORB Family Systematic Search). Everything before it is valuable regardless — live trading, AI layer, artisanal strategies, short selling, BacktestEngine, Research Console. Everything after it depends on whether systematic search produces validated ensembles that outperform hand-crafted strategies.

If you build nothing beyond Phase 6, you still have a strong AI-enhanced multi-strategy trading system with 13–15 patterns and live capital deployment. If you build through Phase 8 and the experiment fails, you still have the best strategy research infrastructure of any independent trader. The ensemble vision is the ceiling, not the floor.

But if the experiment succeeds — and you build the Synapse, the real-time firing, the self-adapting learning loop, the continuous discovery pipeline — then you've built something that doesn't have a comparable at the independent trader scale. A system that discovers its own alpha, validates it statistically, deploys it intelligently, and shows you the entire process as a living, breathing 3D neural visualization.

That's the portal, not the tool.

---

## 19. Reference Documents

| Document | Purpose |
|----------|---------|
| `docs/roadmap.md` | This document — strategic vision + sprint queue |
| `docs/sprint-campaign.md` | Operational sprint choreography (protocols, skills, agents per sprint) |
| `docs/project-bible.md` | Source of truth — what and why |
| `docs/project-knowledge.md` | Claude context (Tier A) |
| `docs/architecture.md` | Technical blueprint — how |
| `docs/decision-log.md` | All DEC entries with full rationale |
| `docs/dec-index.md` | Quick-reference DEC index |
| `docs/sprint-history.md` | Completed sprint history |
| `docs/risk-register.md` | Assumptions and risks |
| `docs/process-evolution.md` | Workflow evolution narrative |
| `docs/live-operations.md` | Live trading procedures |
| `CLAUDE.md` | Claude Code session context |
| `docs/ui/ux-feature-backlog.md` | Planned UI features |
| `docs/strategies/STRATEGY_*.md` | Per-strategy spec sheets |

### Archived (Historical Reference)
| Document | Status |
|----------|--------|
| `docs/archived/ARGUS_Expanded_Roadmap.md` | Superseded by this document (Feb 26, 2026 original vision) |
| `docs/archived/argus_unified_vision_roadmap.md` | Superseded by this document (Mar 5, 2026 ensemble vision) |
| `docs/archived/10_PHASE3_SPRINT_PLAN.md` | Superseded — completed sprint history preserved in `sprint-history.md` |
| `docs/archived/02_PROJECT_KNOWLEDGE.md` | Legacy project knowledge |
| `docs/archived/07_PHASE1_SPRINT_PLAN.md` | Phase 1 historical |
| `docs/archived/09_PHASE2_SPRINT_PLAN.md` | Phase 2 historical |
