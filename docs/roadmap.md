# ARGUS — Strategic Roadmap

> From artisanal strategies to ensemble alpha — the complete path
> **v1.3 — March 10, 2026** (Sprint 23.6 complete — Pipeline integration, warm-up optimization)
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

The target: **sustainable 5–10%+ monthly returns on deployed capital** at the $100K–$500K scale, with the system running autonomously during US market hours from Taipei.

The path divides into two halves. Everything through Phase 6 builds a strong AI-enhanced multi-strategy trading system — valuable regardless of what comes after. Phases 7–10 build the ensemble infrastructure and test whether systematic search produces validated ensembles that outperform hand-crafted strategies. If the controlled experiment in Phase 8 fails, ARGUS is still strong. If it succeeds, it becomes something without a comparable at the independent trader scale.

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
| RegimeClassifier (SPY vol proxy) | **Multi-factor regime engine** with sector rotation awareness |
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

**Current state:** Sprint 23.5 complete. 2,396 pytest + 435 Vitest. Four active strategies. Live Databento + IBKR paper trading. Seven-page Command Center + AI Copilot active. FMP Scanner + Universe Manager integrated. Autonomous Sprint Runner implemented (DEC-278–297). NLP Catalyst Pipeline complete (DEC-300–307).

---

## 4. UI/UX Design Principle

Every capability must be visible the moment it exists. Terminal-only development phases are a failure mode — they disconnect the builder from the system and erode confidence in what the system is actually doing. The design north star remains "Bloomberg Terminal meets modern fintech" and the aspiration remains "a portal, not a tool."

The Command Center evolves from 7 pages to 10 across this roadmap:

| Page | Current | Phase 5 | Phase 6 | Phase 7–8 | Phase 9–10 |
|------|---------|---------|---------|-----------|------------|
| Dashboard | Built | Quality scores visible | Strategy health bands, short exposure | Ensemble health metrics | Full ensemble dashboard |
| Trades | Built | Quality badge per trade | Unchanged | Unchanged | Strategy family attribution |
| Performance | Built | Unchanged | Learning Loop panel, correlation matrix | Sweep comparison views | Ensemble analytics suite |
| Orchestrator | Built | Catalyst alerts | Throttle/boost panel | Template activation view | Ensemble activation map |
| Pattern Library | Built | Unchanged | New strategy cards | Template gallery evolution | Template + ensemble browser |
| The Debrief | Built | AI-generated summaries | Unchanged | Research session recaps | Ensemble debrief |
| System | Built | API health monitoring | Unchanged | BacktestEngine monitoring | Pipeline health |
| Copilot | Shell built | Activated (Sprint 22) | Ensemble-aware context | Research assistant mode | Full ensemble copilot |
| Research Console | — | — | — | **New (Sprint 29)** | Discovery pipeline view |
| Synapse | — | — | — | — | **New (Sprint 37–38)** |

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
- CPA consultation complete
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

### Sprint 21.6: Backtest Re-Validation (DEC-132 / DEC-235)
**Target:** ~2 days (runs parallel with Sprint 22)
**Status:** QUEUED

Re-validate all pre-Databento strategy parameters using Databento tick-level data. All four active strategies. Produce updated parameter sets. Log any parameter changes as DEC entries.

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
**Status:** NEXT

**Scope:**
- **SetupQualityEngine** (`argus/intelligence/quality_engine.py`): Composite 0–100 scoring from 5 weighted inputs (DEC-239): pattern strength (25%), catalyst quality (20%), volume profile (20%), historical match (15%), regime alignment (20%). Order Flow dimension added post-revenue when Databento Plus activated — rebalances to 6 dimensions with Order Flow at 20%. Configurable weights via YAML.
- **DynamicPositionSizer** (`argus/intelligence/position_sizer.py`): Grade → risk tier → share count. A+=2–3%, A=1.5%, B=0.75%, C+=0.25%, C-=SKIP. Replaces fixed `risk_per_trade_pct`. Risk Manager limits still enforced.
- SignalEvent enrichment: `quality_score`, `quality_grade`, `risk_tier` fields.
- Quality History DB table for Learning Loop.
- **UI:** Dashboard gains quality distribution mini-card and Signal Quality Distribution panel. Watchlist/positions/trade log gain quality grade badges. Trade Detail gains radar chart + "Why this size?" breakdown. Performance gains "by quality grade" chart. Debrief gains quality vs. outcome scatter plot.
- **Tests:** ~100 new.

### Phase 5 Gate

**Trigger:** Sprint 24 complete.
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression.

**Assessment criteria:**
- AI Layer operational? Copilot responsive and useful?
- Quality Engine producing meaningful differentiation between setups?
- Paper trading health (Gate 2 progress)?
- Phase 6 readiness?
- Velocity calibration for Phase 6 estimates.

---

## 7. Phase 6: Strategy Expansion — Artisanal (Sprints 25–28)

*Expands the strategy roster to 13–15+ hand-crafted patterns including short selling. Adds the Learning Loop for self-monitoring. This is the phase where ARGUS becomes a serious multi-strategy system. UI focus: make strategy health and correlation visible.*

### Sprint 25: Red-to-Green + Pattern Library Foundation (DEC-163, DEC-167)
**Target:** ~2–3 days

**Scope:**
- **RedToGreenStrategy** through Incubator stages 1–3: Gap-down reversal at key levels (VWAP, premarket low, prior close). 9:45–11:00 AM window. State machine similar to VWAP Reclaim.
- **PatternLibrary ABC interface** (`argus/strategies/patterns/`): Standardized pattern detection modules that feed "pattern strength" to Quality Engine.
- **Bull Flag** and **Flat-Top Breakout** pattern modules: Each implements PatternLibrary interface. Stages 1–3 validation.
- **UI:** Pattern Library page gains 3 new strategy cards with full parameter specs and backtest results.
- **7 strategies/patterns active.**
- **Tests:** ~80 new.

### Sprint 26: Pattern Expansion I (DEC-167)
**Target:** ~2–3 days

**Scope:**
- **Dip-and-Rip**, **HOD Break**, **Gap-and-Go** pattern modules. Each through stages 1–3.
- Optionally **Pre-Market High Break** if velocity allows (otherwise deferred to Sprint 27).
- Each module implements PatternLibrary interface. Walk-forward validated. Quality Engine integration.
- **UI:** Pattern Library gains 3–4 new strategy cards. Dashboard gains Short Exposure indicator (infrastructure prep for Sprint 27).
- **10–11 strategies/patterns active.**
- **Tests:** ~60 new.

### Sprint 27: Short Selling Infrastructure + Pattern Expansion II (DEC-166, DEC-167)
**Target:** ~3 days

**Scope:**
- **Short selling infrastructure** (`argus/execution/short_selling.py`): Locate/borrow tracking. Inverted risk logic (stop above entry, target below). Short-specific Risk Manager rules. Uptick rule compliance (SSR detection). Short exposure limits (separate from long limits).
- **Parabolic Short** strategy module: First short strategy. Parabolic extension detection, volume exhaustion, reversal candle patterns. Uses L1 signals only (Order Flow enhancement added post-revenue per DEC-238).
- 1–2 additional long pattern modules (**ABCD Reversal**, **Sympathy Play**, or others from the planned roster) if velocity allows.
- **UI:** Dashboard gains short exposure indicator (active). Orchestrator gains short position section. Pattern Library gains Parabolic Short + any additional strategy cards.
- **13–15 strategies/patterns active (including first short strategy).**
- **Tests:** ~80 new.

### Sprint 28: Learning Loop V1 (DEC-163)
**Target:** ~3 days

**Scope:**
- **LearningDatabase** (`argus/intelligence/learning.py`): Stores all scored setups (traded and untrade), outcomes, quality scores, regime context. Rolling window analysis.
- **PostTradeAnalyzer**: Correlates quality scores with outcomes. Weekly batch retraining of Quality Engine weights. V1 uses statistical lookup tables (pattern × catalyst × regime → performance).
- Performance-aware throttling: Strategies that underperform their historical baseline get throttled. Strategies that outperform get boosted. Recommendations surfaced as action cards for human approval.
- Correlation monitoring: Pairwise correlation between all active strategies over trailing window. Highly correlated pairs flagged.
- **UI — Orchestrator page:** Strategy Health Panel — each strategy gets a health band visualization (horizontal bar, green/amber/red against historical baseline). Throttle/boost recommendations as approve/dismiss action cards.
- **UI — Performance page:** Correlation Matrix heatmap showing pairwise correlation. Highly correlated pairs flagged with warning indicator.
- **UI — Dashboard:** Weekly insight card from Learning Loop.
- **UI — System:** Learning Loop health monitoring.
- **Tests:** ~60 new.

### Phase 6 Gate ★ CRITICAL — LIVE TRADING DECISION POINT ★

**Trigger:** Sprint 28 complete.
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Codebase Health Audit (`codebase-health-audit.md`) + Documentation Compression.

**ARGUS state at this gate:** 13–15 hand-crafted strategies (including at least one short strategy) with AI quality filtering, NLP catalysts, dynamic sizing, and performance-aware learning loop. Paper trading has been running for 4–6 weeks at this point.

**What you see:** 13–15 strategy cards in the Pattern Library. Health bands on every strategy in the Orchestrator. Correlation heatmap on Performance. Short exposure indicator on Dashboard. Quality-graded signals firing throughout the day. Morning intelligence briefs. AI-generated debrief narratives.

**Critical decisions at this gate:**
1. **CPA consultation** — Tax strategy for live trading (wash sale tracking, entity structure, estimated payments).
2. **Live trading decision** — If paper trading results are strong (Sharpe > 2.0, positive expectancy, no catastrophic drawdowns), this is the natural point for Gate 5 (live minimum deployment). **Live trading with real capital could begin during or after Phase 6.**
3. **Historical data purchase decision** — If proceeding with ensemble vision (Phases 7–10), resolve the data sufficiency risk: acquire 5–10 years of Databento 1-minute historical bars (estimated $1,000–5,000 one-time). This must happen before Phase 8's controlled experiment.
4. **Ensemble go/no-go** — Confirm commitment to the ensemble research path (Phases 7–10). If choosing to defer, ARGUS continues as a strong artisanal multi-strategy system.

**Elapsed time from start:** ~5–7 weeks.

---

## 8. Phase 7: Infrastructure Unification (Sprints 29–31)

*Builds the BacktestEngine and parameterized strategy system. This is the architectural foundation for the ensemble vision. Nothing in this phase changes live trading behavior — it's building the research infrastructure in parallel. UI focus: the Research Console makes strategy research visible and interactive.*

### Sprint 29: BacktestEngine Core + Research Console (NEW PAGE)
**Target:** ~4 days

**Scope (backend):**
- **SynchronousEventBus**: Direct-dispatch, no async overhead — optimized for backtest speed.
- **BacktestEngine** orchestrator: Wires real strategy classes + IndicatorEngine + SimulatedBroker in fast-replay mode.
- **HistoricalDataFeed** adapter for stored Databento data.
- **ResultsCollector** for trades and equity curves.
- Single-strategy, single-parameter-set execution verified against Replay Harness results. Result equivalence is mandatory.

**Scope (frontend):** **Research Console** — Command Center page 9. Mission control for strategy research.
- **Run Manager:** Shows backtest runs in progress (progress bar, ETA), queued runs, completed runs. Each completed run: equity curve thumbnail, Sharpe, win rate, max drawdown, trade count.
- **Result Comparison:** Select 2–4 completed runs to compare side-by-side — overlaid equity curves, key metrics comparison table.
- **Run Configuration:** Form interface to configure BacktestEngine runs — select strategy, parameter values, symbol set, date range. Launch from UI.

**State after:** A new backtesting path exists alongside VectorBT + Replay Harness. It runs real production strategy code at 5–10x async Replay Harness speed. Results match exactly. The entire research workflow is visible on the Research Console.

**Tests:** ~80 new.

### Sprint 30: Parallel Sweep Infrastructure
**Target:** ~3–4 days

**Scope (backend):**
- Multiprocessing harness for BacktestEngine. Parameter grid specification format.
- Worker pool distributing parameter combinations across CPU cores.
- Result aggregation pipeline. Progress monitoring.
- Cloud burst configuration (spin up high-core-count instance for sweep days).

**Scope (frontend):** Research Console upgrades:
- **Sweep Manager:** Like Run Manager but for multi-parameter sweeps. Progress: "12,400 / 48,000 combinations. ETA: 2.3 hours."
- **Sweep Heatmap:** 2D heatmap for any two-parameter sweep. Color = performance metric (Sharpe, win rate, etc.). Hover: full metrics for that cell. Click: detailed results. Progressive rendering as results arrive.
- **Parameter Landscape (3D):** Three.js surface plot for three-parameter exploration. Rotate, zoom, click on peaks and valleys. Toggle between Sharpe, win rate, max drawdown surfaces.

**Tests:** ~60 new.

### Sprint 31: Parameterized Strategy Templates
**Target:** ~3–4 days

**Scope:**
- **StrategyTemplate** base class: Defines a strategy as a parameterized template with declared parameter ranges, filter dimensions, and validation criteria.
- Convert existing strategies (ORB Breakout, VWAP Reclaim, etc.) to template format. Template parameters include all tunable values — entry thresholds, targets, stops, time windows, volume filters, market cap filters, sector filters.
- **Template Gallery** on Pattern Library page: Evolves from individual strategy cards to template cards showing parameter ranges, instance count, and a mini sweep heatmap for each template.
- **Template Explorer:** Click a template → see all configured instances, parameter ranges, and which regions of parameter space have been explored.

**State after:** Every strategy exists as both a hand-tuned instance (the artisanal version from Phase 6) and a parameterized template (ready for systematic search). The Pattern Library shows both views.

**Tests:** ~60 new.

### Phase 7 Gate

**Trigger:** Sprint 31 complete.
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Documentation Compression.

**Critical resolution required:** Historical data sufficiency. If not already purchased at Phase 6 Gate, the data purchase MUST happen now. Three-way splits (train/selection/validation) across only 35 months of data may not provide enough statistical power. Options: acquire 5–10 years of Databento 1-minute bars; synthetic data augmentation (block bootstrap); accept lower granularity for coarse screening.

---

## 9. Phase 8: Controlled Experiment (Sprints 32–34)

*The proving ground. Takes one strategy family and systematically searches the parameter × filter space. Validates the methodology before scaling. UI focus: make the search process and statistical validation legible.*

### Sprint 32: Statistical Validation Framework
**Target:** ~3–4 days

**Scope (backend):**
- FDR correction implementation (Benjamini-Hochberg). Minimum trade count thresholds per micro-strategy.
- Three-way data split infrastructure (train / selection / validation).
- Smoothness prior — neighboring parameter/filter cells must show correlated performance for any cell to be considered valid.
- Out-of-sample ensemble validation metrics. Walk-forward at ensemble level.

**Scope (frontend):** Research Console — Validation Dashboard:
- **Data Split Visualizer:** Timeline bar showing train / selection / validation partitions.
- **FDR Report View:** Total candidates tested, survivors after FDR correction, effective significance threshold, p-value distribution histogram.
- **Smoothness Heatmap:** Overlay on sweep heatmap showing smoothness prior — validated cells glow, isolated spikes dimmed/crossed out. Toggle raw vs. filtered views.

**Tests:** ~60 new.

### Sprint 33: ORB Family Systematic Search ★ THE PIVOTAL EXPERIMENT ★
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

### Sprint 34: Ensemble Performance Analysis
**Target:** ~2–3 days

**Scope:** Deep analysis of Sprint 33 results. Correlation structure among validated micro-strategies. Capital efficiency. Turnover and commission impact. Drawdown comparison. Regime sensitivity.

**UI deliverable:** Research Console — Ensemble Analysis Suite:
- **Correlation Cluster Map:** Force-directed graph of validated micro-strategies, proximity = correlation. 2D precursor to the Synapse.
- **Regime Performance Breakdown:** Faceted chart showing ensemble performance across market regimes.
- **Commission Impact Model:** Net returns after simulated commissions at various trade frequencies.
- **Go/No-Go Dashboard:** Summary view with key comparison metrics, statistical confidence, clear visual verdict.

**Tests:** ~30 new.

### Phase 8 Gate ★★★ THE GO/NO-GO DECISION ★★★

**Trigger:** Sprint 34 complete.
**Protocol:** Custom Gate Review (see SPRINT_CAMPAIGN.md Section 7).

**If GO:** Validated ensemble of ORB micro-strategies outperforms hand-crafted baselines. Methodology proven. Proceed to Phase 9 (cross-family scaling).

**If NO-GO:** Diagnose through visual tools. Determine if salvageable (methodology adjustment → revised Sprint 33) or fundamental (approach doesn't work → continue artisanal path). BacktestEngine, Research Console, and statistical framework remain valuable for individual strategy research regardless. ARGUS remains a strong multi-strategy system with the Phase 6 roster.

**ARGUS state regardless of outcome:** Production trading continues with 13–15 strategies. The Research Console is a sophisticated analysis environment — sweep heatmaps, 3D parameter landscapes, FDR reports, smoothness overlays, ensemble equity curves.

**Elapsed time from start:** ~9–12 weeks.

---

## 10. Phase 9: Ensemble Scaling (Sprints 35–38)

*ONLY EXECUTES IF PHASE 8 GO.*

*Extends the proven methodology across all strategy families. Builds the Ensemble Orchestrator and the Synapse visualization. UI focus: making the full ensemble comprehensible as a living neural system.*

### Sprint 35: Cross-Family Search (VWAP + Afternoon Momentum)
**Target:** ~4–5 days

**Scope (backend):** Apply Sprint 33 methodology to VWAP Reclaim and Afternoon Momentum template families. Same tiered sweep → statistical filtering → ensemble validation pipeline. Cross-family correlation analysis.

**Scope (frontend):** Research Console — Cross-Family View:
- Multi-family color-coded correlation cluster map (expanding the Sprint 34 cluster map).
- **Family Contribution Chart:** Percentage of ensemble returns from each strategy family, broken down by regime. "In trending markets, ORB contributes 45% and VWAP contributes 35%."

**State after:** Three strategy families have validated micro-strategy ensembles. Cross-family diversification measured. Total validated micro-strategies: likely 100–400.

### Sprint 36: Cross-Family Search (Remaining Families)
**Target:** ~4–5 days

**Scope:** Red-to-Green, Gap-and-Go, ABCD, Parabolic Short, and remaining artisanal strategies from Phase 6 get the systematic search treatment. Each family's template is swept and filtered.

**UI deliverable:** Research Console correlation map shows full strategy universe — all families, all validated micro-strategies, all cross-family correlations. Density reaching the point where the Synapse becomes necessary.

**State after:** All strategy families have validated ensembles. Total micro-strategies: potentially 200–800.

### Sprint 37: Ensemble Orchestrator V2 + Synapse (Analysis Mode)
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

### Sprint 38: Ensemble Monitoring + Real-Time Synapse
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

**Trigger:** Sprint 38 complete.
**Protocol:** Strategic Check-In (`strategic-check-in.md`) + Codebase Health Audit (`codebase-health-audit.md`) + Documentation Compression.

**Assessment:** Ensemble operational in paper trading? Synapse working? 20–60 micro-strategies activating per day as expected? Ensemble Sharpe tracking toward 3.0+? System fast enough at scale?

**ARGUS state:** 200–800 validated micro-strategies across all families. Ensemble-aware Orchestrator. Correlation-managed allocation. Comprehensive visual monitoring anchored by the real-time Synapse.

**Elapsed time from start:** ~12–16 weeks.

---

## 11. Phase 10: Full Vision (Sprints 39–41)

*The self-improving system. The ensemble doesn't just execute — it learns, adapts, and evolves. UI focus: make adaptation and discovery visible.*

### Sprint 39: Learning Loop V2 (Ensemble Edition)
**Target:** ~4–5 days

**Scope (backend):**
- Automated performance tracking at micro-strategy level. Underperformers automatically throttled, outperformers boosted (within risk limits).
- Rolling recalibration: every N trading days, statistical validation re-runs on recent data to check if validated strategies still hold.
- Automatic retirement of strategies that lose their edge. Automatic promotion of promising candidates from staging queue (human approval still required).

**Scope (frontend):** The Synapse becomes a living ecosystem:
- **Lifecycle visualization:** Newly promoted strategies fade in and grow from zero. Throttled strategies shrink gradually. Retiring strategies fade out over several sessions — dimmer, greyer, smaller, like neurons going dark.
- **Health decay indicators:** Declining performance causes slow color shift from family hue toward grey.
- **Adaptation Timeline** on Research Console: Ensemble evolution over time — additions, retirements, throttles, boosts, net ensemble metrics. "Week 3: +12 ORB variants promoted, -4 VWAP variants retired, net ensemble Sharpe: 2.7 → 2.9."

### Sprint 40: Continuous Discovery Pipeline
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

### Sprint 41: Performance Workbench
**Target:** ~4–5 days

**Scope:** Customizable widget grid using `react-grid-layout`. Drag/drop/resize visualizations into personalized analysis workflows.

**Widget palette:** Strategy family performance charts, correlation matrix heatmap, regime analysis panels, micro-strategy activation heatmap (time-of-day × day-of-week), capital utilization over time, drawdown decomposition, sector exposure history, quality score distribution, win rate breakdowns (by family / regime / time-of-day), commission impact tracker, ensemble Sharpe rolling window, Mini-Synapse (embeddable), discovery pipeline status, custom metric formulas.

**Two-stage build:**
1. Rearrangeable tab system — save custom page layouts as named tabs ("Morning Review," "Live Session," "Post-Session Analysis," "Weekly Deep Dive").
2. Full widget palette — drag any widget onto any tab, resize and arrange freely.

**State after:** Bloomberg-terminal-grade analysis environment. Build views that match your workflow, not a predetermined layout.

### Phase 10 Gate (Full Vision)

**Trigger:** Sprint 41 complete.
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
| 6: Strategy Expansion | 25–28 | 13–15 artisanal strategies, short selling, Learning Loop V1 | ~2–3 weeks | Weeks 3–6 |
| 7: Infrastructure Unification | 29–31 | BacktestEngine, templates, Research Console | ~2–2.5 weeks | Weeks 6–8.5 |
| 8: Controlled Experiment | 32–34 | Statistical framework, ORB search, go/no-go | ~2–2.5 weeks | Weeks 8.5–11 |
| 9: Ensemble Scaling | 35–38 | Cross-family search, Synapse, live ensemble | ~3–4 weeks | Weeks 11–15 |
| 10: Full Vision | 39–41 | Learning Loop V2, discovery pipeline, workbench | ~2.5–3.5 weeks | Weeks 15–18+ |

**Total: ~41 sprints across ~18+ weeks / 4.5+ months**

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
| 29 | **+Research Console (page 9):** Run Manager, Result Comparison, Run Configuration |
| 30 | Research Console: +Sweep Manager, +Sweep Heatmap, +Parameter Landscape (3D) |
| 31 | Pattern Library: evolves to template gallery with instance browser and template explorer |
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
Evolves from individual strategy gallery (current) → template gallery with parameter ranges (Sprint 31) → secondary to the Synapse for ensemble visualization (Sprint 37+). The Pattern Library doesn't disappear, but its role shifts from "primary strategy view" to "template reference and configuration tool."

### Dashboard Density Management
The Dashboard accumulates significant new panels across this roadmap. The Performance Workbench (Sprint 41) partially solves this by letting you customize which panels appear where. Until then, use progressive disclosure: panels appear only when relevant features are active.

### Orchestrator V2 Supersession
The original Orchestrator V2 concept (enhanced rules-based for ~15 strategies) is superseded by the Ensemble Orchestrator in Sprint 37. These are incompatible approaches — the ensemble version handles hundreds of micro-strategies with correlation-aware allocation and activation filtering.

---

## 15. Critical Risks

| Risk | Severity | Phase | Mitigation |
|------|----------|-------|------------|
| **Historical data insufficiency** | High | 8 | Purchase 5–10yr Databento history before Phase 8. Resolve at Phase 7 Gate. |
| **Overfitting the quality model** | High | 5–6 | Walk-forward validation on quality scores. Out-of-sample calibration mandatory. |
| **Phase 8 experiment failure** | Medium | 8 | System is valuable regardless (Phase 6 artisanal trading continues). Ensemble ceiling lost but floor unchanged. |
| **Pattern library complexity explosion** | Medium | 6–7 | Each pattern must pass walk-forward independently. Retire patterns that don't earn their keep. |
| **Dynamic sizing amplifies losses** | Medium | 5 | A+ sizing caps at 3%. Account-level daily/weekly limits unchanged. Circuit breakers still override. |
| **Claude API latency** | Medium | 5 | Cache catalyst scores (don't change intraday). Pre-compute during pre-market. Only novel catalysts need real-time scoring. |
| **Broad-universe processing throughput** | Low | 5–9 | Pure Python at 4,000 symbols uses ~2–4% CPU. Monitor during paper trading. If per-second processing exceeds 100ms, Cythonize IndicatorEngine hot path (~0.5 day effort). DEC-263. |
| **Three.js performance at scale** | Medium | 9 | Instanced mesh geometry. Performance target: 60fps at 800 nodes. Budget for optimization sessions. |
| **Scope creep extending timeline** | Medium | All | Each sprint is independently valuable. Can pause at any phase boundary. |
| **Taipei latency (~150–200ms)** | Low | All | Structural disadvantage for ultra-short holds. Longer-duration strategies (5–30 min) preferred. Already reflected in strategy design. |
| **IBKR Gateway nightly resets** | Low | All | Automated reconnection (RSK-022). live-operations.md procedures. |

---

## 16. Post-Revenue Backlog

Items deferred until monthly trading income justifies their cost or complexity. These are tracked here so nothing is lost from previous roadmap iterations.

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

One-time costs: Historical data purchase (~$1,000–5,000, Phase 7 Gate). Cloud burst compute (pay-per-use, Phases 8–9).

---

## 18. The Decision That Matters Most

The entire roadmap pivots on the outcome of Sprint 33 (ORB Family Systematic Search). Everything before it is valuable regardless — live trading, AI layer, artisanal strategies, short selling, BacktestEngine, Research Console. Everything after it depends on whether systematic search produces validated ensembles that outperform hand-crafted strategies.

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
