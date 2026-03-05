# ARGUS Unified Vision Roadmap

> From artisanal strategies to ensemble alpha — the complete path
> March 5, 2026 (v2 — with integrated UI/UX vision)

---

## Velocity Baseline

ARGUS completed 21 sprints + sub-sprints in ~17 calendar days of active development (Feb 14 – Mar 3). Average sprint: ~0.8 calendar days. However, sprint complexity has been increasing — early sprints (1–5) were dense single-day affairs, while later sprints (21a–21d) span multiple days. The roadmap below assumes sprint durations of 1–3 days each depending on complexity, with some parallelism where noted. Total estimated timeline: **12–18 weeks** from current state to full vision.

**Current state:** Sprint 21.5 in progress. 1,710 pytest + 255 Vitest tests. Four active strategies. Live Databento + IBKR paper trading. Seven-page Command Center.

---

## UI/UX Design Principle

Every capability must be visible the moment it exists. Terminal-only development phases are a failure mode — they disconnect the builder from the system and erode confidence in what the system is actually doing. The design north star remains "Bloomberg Terminal meets modern fintech" and the aspiration remains "a portal, not a tool."

The Command Center evolves from 7 pages to 10 across this roadmap:

| Page | Current | Phase 5 | Phase 6 | Phase 7–8 | Phase 9–10 |
|------|---------|---------|---------|-----------|------------|
| Dashboard | Built | Quality scores visible | Strategy health bands | Ensemble health metrics | Full ensemble dashboard |
| Trades | Built | Quality badge per trade | Unchanged | Unchanged | Strategy family attribution |
| Performance | Built | Unchanged | Learning Loop panel | Sweep comparison views | Ensemble analytics suite |
| Orchestrator | Built | Catalyst alerts | Throttle/boost panel | Template activation view | Ensemble activation map |
| Pattern Library | Built | Unchanged | New strategy cards | Template gallery evolution | Template + ensemble browser |
| The Debrief | Built | AI-generated summaries | Unchanged | Research session recaps | Ensemble debrief |
| System | Built | API health monitoring | Unchanged | BacktestEngine monitoring | Pipeline health |
| Copilot | Shell built | Activated (Sprint 22) | Ensemble-aware context | Research assistant mode | Full ensemble copilot |
| Research Console | — | — | — | **New (Sprint 28)** | Discovery pipeline view |
| Constellation | — | — | — | — | **New (Sprint 36–37)** |

---

## Phase 5: Foundation Completion

*Completes the existing near-term roadmap. Finishes live integration, adds market data scanning, begins AI layer. UI focus: make intelligence and quality filtering visible.*

### Sprint 21.5: Live Integration - COMPLETE (March 5, 2026)

**Scope:** Blocks C+D remaining — first full market day paper session, closeout procedures.

**UI state after:** No new UI work — existing Command Center monitors the live session.

**State after:** ARGUS runs autonomously through a full market session on paper. Databento streaming, IBKR paper execution, all four strategies active. Human monitors via Command Center. Live operations procedures validated.

**Timeline:** ~2 days remaining

---

### Sprint 21.7: FMP Scanner Integration

**Scope:** FMP Starter ($22/mo) integration for pre-market daily bars. Dynamic symbol selection replacing static watchlist fallback. DEC-258/259.

**UI deliverable:** Scanner results surface on the Dashboard as a **Pre-Market Watchlist** panel — shows which symbols were selected this morning, why (volume spike, gap, catalyst tag), and which strategies are targeting each symbol. Replaces the implicit "you have to check the logs to know what's being scanned" experience.

**State after:** ARGUS selects its own symbols each morning based on pre-market data instead of relying on a hardcoded list. The scanner pipeline is data-source-aware (Databento for intraday, FMP for daily). You can see the watchlist on the Dashboard before market open.

**Timeline:** ~2 days

---

### Sprint 22: AI Layer MVP

**Scope:** Claude API (Opus) integration. AI Copilot activation in Command Center shell. Approval workflow for AI suggestions. Contextual analysis of current market conditions and strategy states.

**UI deliverable:** The Copilot pane goes from shell to live. It renders as a slide-out panel (or dedicated page, per DEC-170) with conversational interface, system state context display, and approval action buttons for AI suggestions. The Copilot can reference what it sees — current positions, strategy states, the pre-market watchlist — and present analysis inline.

**State after:** The Copilot pane is live — you can ask it about current positions, strategy states, market conditions, and get contextual analysis during trading sessions. The AI layer has read access to system state but does not yet influence strategy decisions autonomously. This is the "advisor" mode.

**Timeline:** ~3 days

---

### Sprint 23: NLP Catalyst + Pre-Market Engine

**Scope:** SEC EDGAR + Finnhub + FMP + Claude API pipeline (DEC-164). Pre-market intelligence report generation. Catalyst tagging on scanned symbols.

**UI deliverable:** **Pre-Market Intelligence Brief** — a dedicated view (accessible from Dashboard or as a Copilot-generated report) that renders each morning before market open. Shows: macro context (overnight futures, key economic data), per-symbol catalyst cards (earnings date, FDA decision, analyst action, insider activity), and strategy alert flags ("ORB Breakout: 3 high-catalyst names in window"). Catalyst tags also appear as small badges on the Pre-Market Watchlist panel from Sprint 21.7, so you see both the symbol list and their catalyst context in one glance.

The Debrief page evolves: the AI now generates end-of-session narrative summaries alongside the existing metrics — "Today's best trade was the NVDA VWAP Reclaim, which benefited from the morning earnings beat catalyst. The two ORB losses were both in low-catalyst names during the first 15 minutes of choppy price action."

**State after:** Each morning before market open, ARGUS generates an intelligence brief visible in the Command Center. Strategies don't yet consume catalysts directly — they're informational for the operator. Session debriefs now include AI-generated narrative analysis.

**Timeline:** ~3 days

---

### Sprint 24: Setup Quality Engine + Dynamic Sizer

**Scope:** 0–100 quality scoring for setups (DEC-239). AI-graded entry signals. Dynamic position sizing based on quality score — higher quality → larger position within risk limits. Integration with Risk Manager.

**UI deliverable:** Quality scores become visible across the entire Command Center:

- **Trades page:** Every trade row shows a quality badge — a color-coded score (red < 40, amber 40–65, green 65–85, bright green 85+). Clicking the badge expands to show the scoring breakdown: what factors contributed to the grade.
- **Orchestrator page:** Live signal feed shows quality scores in real time as signals fire. You watch signals appear, get graded, and either execute or get filtered — the entire decision pipeline is visible.
- **Dashboard:** A new **Signal Quality Distribution** mini-chart shows today's signal quality histogram — how many signals at each quality tier, what percentage were executed vs. filtered. Over time, this tells you whether market conditions are producing high-quality setups or garbage.
- **The Debrief:** Quality score vs. outcome analysis — did high-quality signals actually produce better results today? A scatter plot of quality score vs. P&L per trade.

**State after:** Every signal generated by the four strategies gets a visible quality grade before execution. The system is now filtering its own signals, and you can *see* the filtering happen. A marginal ORB breakout scores 35/100 and you watch it get rejected on the Orchestrator page. A textbook VWAP reclaim scores 85/100 and you watch it get full allocation.

**Timeline:** ~3–4 days

---

### Phase 5 Checkpoint

**ARGUS state:** An AI-enhanced trading system with four strategies, quality filtering, NLP catalysts, dynamic sizing, and live paper trading. The system is meaningfully smarter than it was at Sprint 21.5 — it doesn't just execute patterns, it evaluates whether patterns are worth executing.

**What you see:** Morning intelligence brief with catalyst cards. Pre-market watchlist with catalyst badges. Live signal quality scoring on the Orchestrator page. Quality badges on every trade. AI-generated debrief narratives. Active Copilot for conversational analysis. This already feels like a different class of product from Sprint 21.5.

**What's possible:** Paper trading with genuine signal quality differentiation. Morning intelligence briefs. Interactive AI copilot during sessions. Data-driven position sizing. This is a competitive standalone system.

**Command Center:** 7 pages + Copilot activated. Dashboard has Pre-Market Watchlist and Signal Quality Distribution panels. Orchestrator shows live quality scoring.

**Elapsed time from now:** ~2–3 weeks

---

## Phase 6: Strategy Expansion (Artisanal)

*Adds strategies one at a time using the existing workflow. Each strategy is hand-designed, backtested, and validated. UI focus: make strategy health and the learning loop visible.*

### Sprint 25: Red-to-Green + Pattern Library Updates

**Scope:** Red-to-Green reversal strategy. Pattern Library page updated with new entry. Strategy spec sheet, VectorBT sweep, Replay Harness validation, walk-forward.

**UI deliverable:** New strategy card in Pattern Library with Red-to-Green's state machine visualization, parameter ranges, and backtest equity curve. The Orchestrator page shows the new strategy in the active strategy grid. Dashboard strategy health cards update to include the fifth strategy.

**State after:** Five active strategies. Morning coverage extended — Red-to-Green catches stocks that gap down and reverse, complementing ORB's breakout-from-open approach. The new strategy is fully visible across all Command Center pages.

**Timeline:** ~2–3 days

---

### Sprint 26: Pattern Expansion I

**Scope:** 2–3 additional strategies (candidates: Gap Fill, ABCD Pattern, Parabolic Short prototype). Each goes through full validation pipeline.

**UI deliverable:** Pattern Library cards for each new strategy. If short selling is introduced, a new **Short Exposure** indicator appears on the Dashboard — showing current long vs. short allocation as a balance bar, since short-side risk is qualitatively different and needs persistent visibility.

**State after:** 7–8 active strategies. Coverage now spans pre-market awareness through afternoon close. Short-side exposure begins (if Parabolic Short is included).

**Timeline:** ~4–5 days

> **ROADMAP CONTRADICTION NOTE:** The existing roadmap has Sprint 27 as "Short Selling + Parabolic Short" as a standalone sprint. This roadmap pulls short selling into Sprint 26 if Parabolic Short is one of the expansion candidates, since the short-selling infrastructure (locate tracking, uptick rule compliance, short-specific risk limits) needs to exist before any short strategy can run. If short selling isn't in Sprint 26, Sprint 27 remains as-is.

---

### Sprint 27: Pattern Expansion II + Learning Loop V1

**Scope:** 2–3 more strategies. Learning Loop V1: automated tracking of per-strategy performance over rolling windows, automatic throttling recommendations, correlation monitoring between strategies.

**UI deliverable:** The Learning Loop gets its own visual presence across two pages:

- **Orchestrator page — Strategy Health Panel:** Each strategy gets a health band visualization — a horizontal bar showing rolling performance against its historical baseline. Green = performing at or above expectation. Amber = below expectation, monitoring. Red = significantly underperforming, throttle recommended. Throttle/boost recommendations appear as action cards that you approve or dismiss with one click.
- **Performance page — Correlation Matrix:** A heatmap showing pairwise correlation between all active strategies over the trailing window. Highly correlated pairs are flagged with a warning indicator — this is early infrastructure for the ensemble vision, surfaced now so you start building intuition about how your strategies relate to each other.

**State after:** 10–11 active strategies. The system monitors its own strategy performance and flags degradation — and you can *see* the monitoring happen. The Orchestrator page shows health bands. The Performance page shows the correlation structure. Throttle/boost recommendations appear as actionable cards.

**Timeline:** ~4–5 days

---

### Phase 6 Checkpoint

**ARGUS state:** ~10 hand-crafted strategies with AI quality filtering, NLP catalysts, dynamic sizing, and performance-aware learning loop. Paper trading has been running for 4–6 weeks at this point.

**What you see:** 10+ strategy cards in the Pattern Library. Health bands on every strategy in the Orchestrator. Correlation heatmap on Performance. Short exposure indicator (if applicable). Quality-graded signals firing throughout the day. Morning intelligence briefs. AI-generated debrief narratives.

**What's possible:** Genuine multi-strategy diversification. Short and long exposure. Quality-filtered signal generation across the full trading day. Self-monitoring performance degradation — visible on screen, not hidden in logs.

**Critical gate:** If paper trading results are strong through this phase (Sharpe > 2.0, positive expectancy across strategies, no catastrophic drawdowns), this is the natural point for the CPA consultation and live-minimum deployment (Gate 5 from the validation track). **Live trading with real capital could begin during or after Phase 6.**

**Command Center:** 7 pages + active Copilot. Dashboard has watchlist, quality distribution, and short exposure panels. Orchestrator has health bands and throttle/boost cards. Performance has correlation matrix.

**Elapsed time from now:** ~5–7 weeks

---

## Phase 7: Infrastructure Unification

*Builds the BacktestEngine and parameterized strategy system. This is the architectural foundation for the ensemble vision. Nothing in this phase changes live trading behavior — it's building the research infrastructure in parallel. UI focus: the Research Console makes strategy research visible and interactive.*

### Sprint 28: BacktestEngine Core + Research Console

**Scope (backend):** SynchronousEventBus (direct-dispatch, no async overhead). BacktestEngine orchestrator that wires real strategy classes + IndicatorEngine + SimulatedBroker in fast-replay mode. HistoricalDataFeed adapter for stored Databento data. ResultsCollector for trades and equity curves. Single-strategy, single-parameter-set execution verified against Replay Harness results.

**Scope (frontend):** **Research Console** — Command Center page 9. This is mission control for strategy research. Initial capabilities:

- **Run Manager:** Shows backtest runs in progress (progress bar, estimated time remaining), queued runs, and completed runs. Each completed run shows a summary card: equity curve thumbnail, Sharpe ratio, win rate, max drawdown, trade count.
- **Result Comparison:** Select 2–4 completed runs to compare side-by-side — overlaid equity curves, key metrics in a comparison table.
- **Run Configuration:** A form interface to configure BacktestEngine runs — select strategy, parameter values, symbol set, date range. Kick off a run from the UI instead of the terminal.

This page transforms strategy research from a terminal-only activity into something visual and interactive. When you run a backtest, you watch its progress on screen. When it completes, you see the equity curve immediately. When you want to compare parameter variations, you select them and see the comparison rendered.

**State after:** A new backtesting path exists alongside VectorBT + Replay Harness. It runs real production strategy code through historical data at 5–10x async Replay Harness speed. Results match exactly. And critically — the entire research workflow is visible on the Research Console. You never need to squint at terminal output to understand backtest results.

**Timeline:** ~4 days

---

### Sprint 29: Parallel Sweep Infrastructure

**Scope (backend):** Multiprocessing harness for BacktestEngine. Parameter grid specification format. Worker pool that distributes parameter combinations across CPU cores. Result aggregation pipeline. Progress monitoring. Cloud burst configuration (spin up high-core-count instance for sweep days).

**Scope (frontend):** Research Console upgrades:

- **Sweep Manager:** Configure and launch parameter sweeps from the UI. Define parameter ranges with sliders or inputs. Estimated completion time shown before launch. Live progress: "427 / 1,000 combinations complete. 47 minutes remaining."
- **Sweep Results Heatmap:** When a sweep completes, results render as an interactive heatmap — axes are two selected parameters, color is the target metric (Sharpe, win rate, profit factor). You visually identify the "hot zones" in parameter space where the strategy performs well. Click any cell to see the detailed result for that parameter combination.
- **Parameter Landscape:** A 3D surface plot (using Plotly, already available) showing the performance surface across two parameter dimensions. Rotate, zoom, identify ridges and valleys. This is the first "spatial navigation of strategy space" — early infrastructure for the Constellation concept.

**Acceptance criteria:** 1,000 parameter combinations across 10 symbols completes in < 2 hours on 8-core machine. Results identical to sequential execution. Sweep progress, heatmap, and landscape all render correctly on Research Console.

**State after:** ARGUS can run production-path parameter sweeps at scale, and you can *see* the entire parameter landscape. The heatmap and surface plot make it immediately obvious where strategies work and where they don't — no spreadsheet analysis required. The tiered sweep methodology is available: coarse scan → focused sweep → walk-forward validation.

**Timeline:** ~3–4 days

---

### Sprint 30: Parameterized Strategy Templates

**Scope (backend):** Strategy template system — a strategy class becomes a configurable template with parameter slots and filter slots. Example: ORBBreakoutTemplate accepts entry_threshold, target_R, stop_type, consolidation_bars, time_window_start, time_window_end, min_volume_ratio, sector_filter, market_cap_filter, float_filter as configuration. Template configuration schema (YAML or dataclass). Template validation (parameter ranges, filter compatibility). Template registry for discovery and instantiation. Existing strategies refactored into templates.

**Scope (frontend):** Pattern Library page evolution:

- **Template View:** Instead of showing just one card per strategy, each strategy family expands to show its template — the parameter ranges, the filter options, the dimensions of configurability. An ORB Breakout card now shows "Entry threshold: 0.1–0.8 | Target: 0.3–3.0R | Time window: 9:35–11:30 | Sector: any | Market cap: any" with sliders showing the validated ranges.
- **Instance Browser:** Under each template, a list of instantiated configurations currently active in production. Initially this is just the hand-crafted configurations (e.g., the original ORB Breakout with its tuned parameters). After Phase 8, this list grows to show validated micro-strategies.
- **Template Explorer:** A form-based interface for creating new template configurations. Select parameters, apply filters, and the UI shows whether this configuration has been tested (links to Research Console sweep results if available) or is untested.

> **ROADMAP CONTRADICTION NOTE:** This is a significant refactor of the strategy architecture. Currently, each strategy is a bespoke class (DEC-028: daily-stateful, session-stateless plugins). The template system preserves this contract but adds a layer above it — templates generate strategy instances that behave identically to hand-coded strategies. The Risk Manager, Orchestrator, and Order Manager see no difference. However, the Pattern Library page shifts from strategy gallery to template gallery, which changes how the operator conceptualizes the strategy repertoire.

**State after:** Every existing strategy can be described as a template configuration. New strategies can be created by specifying parameters and filters without writing new Python classes. The Pattern Library visually reflects this — each strategy family is a template with a parameter space, not just a single card. The system still runs the same 10–11 strategies in production — no behavior change — but the infrastructure and visual language for mass strategy generation exists.

**Timeline:** ~3–4 days

---

### Phase 7 Checkpoint

**ARGUS state:** Production trading unchanged (10–11 strategies, AI-enhanced). Research infrastructure now includes the BacktestEngine with parallel sweeps and parameterized templates. The Research Console makes all research activity visible and interactive.

**What you see:** The Research Console (page 9) shows sweep heatmaps and 3D parameter landscapes. The Pattern Library shows templates with parameter ranges and instance browsers. You can configure and launch backtest sweeps from the UI, watch them progress, and explore results visually. The transition from "strategy research happens in the terminal" to "strategy research happens in the Command Center" is complete.

**What's possible:** The controlled experiment. You're ready to test whether systematic search outperforms hand-tuning — and you'll be able to see the results rendered visually, not just as numbers in a CSV.

**Command Center:** 8 pages + Copilot (Research Console is page 9). Pattern Library has evolved to template gallery.

**Elapsed time from now:** ~7–9 weeks

---

## Phase 8: Controlled Experiment

*The proving ground. Takes one strategy family and systematically searches the parameter × filter space. Validates the methodology before scaling. UI focus: make the search process and statistical validation legible.*

### Sprint 31: Statistical Validation Framework

**Scope (backend):** FDR correction implementation (Benjamini-Hochberg). Minimum trade count thresholds per micro-strategy. Three-way data split infrastructure (train / selection / validation). Smoothness prior — neighboring parameter/filter cells must show correlated performance for any cell to be considered valid. Out-of-sample ensemble validation metrics. Walk-forward at the ensemble level, not just individual strategy level.

**Scope (frontend):** Research Console — **Validation Dashboard:**

- **Data Split Visualizer:** A timeline bar showing how historical data is partitioned into train / selection / validation periods. Makes the three-way split tangible — you see exactly which months are in each set.
- **FDR Report View:** After statistical filtering runs, a summary showing: total candidates tested, candidates surviving FDR correction, effective significance threshold, false discovery rate. A histogram of p-values across all candidates — the "p-value distribution plot" that immediately tells you whether you have real signal (uniform with a spike near zero) or noise (uniform throughout).
- **Smoothness Heatmap:** An overlay on the sweep heatmap (from Sprint 29) that shows the smoothness prior — validated cells glow, isolated spikes (likely noise) are dimmed or crossed out. You can toggle between "raw results" and "after statistical filtering" to see exactly what the framework is rejecting and why.

**State after:** The statistical machinery to evaluate mass strategy search results exists — and its operation is visible on the Research Console. You don't just trust that FDR correction is working; you see the p-value distribution, the smoothness overlay, and the data splits. The framework answers "which of these are real?" and you can see its reasoning.

**Timeline:** ~3–4 days

---

### Sprint 32: ORB Family Systematic Search

**Scope:** The controlled experiment. Take the ORB Breakout template and systematically search:

- Entry parameters: 15–20 values
- Target parameters: 10–15 values
- Stop parameters: 5–10 values
- Time windows: 8–10 slices
- Volume filters: 5 buckets
- Market cap filters: 5 buckets
- Sector filters: 11 GICS sectors + "any"
- Day-of-week filters: 5 + "any"

Estimated total combinations: ~500K–2M (many eliminated by incompatibility). Tiered sweep: coarse screen (vectorized, fast) → focused BacktestEngine validation (~50K candidates) → statistical filtering → walk-forward ensemble validation.

**UI experience during the experiment:** This is a multi-day compute process, and the Research Console makes it a visual experience rather than a terminal tail:

- **Stage 1 (coarse scan):** The sweep heatmap populates progressively as results arrive. You watch the parameter landscape take shape in real time — hot zones emerge, dead zones darken. The progress indicator shows "Stage 1: 127,000 / 500,000 combinations screened. 3.2 hours remaining."
- **Stage 2 (focused validation):** The surviving candidates from Stage 1 are highlighted on the heatmap. A new focused sweep launches on these candidates. The progress indicator updates: "Stage 2: 12,400 / 48,000 candidates validated."
- **Stage 3 (statistical filtering):** The FDR report renders. The smoothness overlay activates. You watch candidates get filtered — some cells that looked promising in Stage 2 go dark as the smoothness prior rejects isolated spikes. The p-value histogram tells you how much real signal exists.
- **Stage 4 (ensemble validation):** The validated micro-strategies are tested as an ensemble on out-of-sample data. A dedicated ensemble equity curve renders alongside the hand-crafted ORB Breakout + ORB Scalp equity curve for direct comparison. Key metrics side by side: ensemble Sharpe vs. hand-crafted Sharpe, ensemble max drawdown vs. hand-crafted max drawdown.

**Success criteria:** The validated ORB micro-strategy ensemble outperforms hand-tuned ORB Breakout + ORB Scalp on out-of-sample data. If it doesn't, the methodology needs revision before proceeding.

**State after:** You know whether the ensemble approach works — and you arrived at that knowledge *visually*, watching the parameter landscape form, the statistical filtering operate, and the ensemble equity curve render against the baseline. Either: (a) a validated ensemble of 50–200 ORB micro-strategies that collectively outperform, proving the methodology — or (b) evidence that the approach doesn't work for this family, with visual understanding of why.

**Timeline:** ~4–5 days (compute-heavy — may need cloud burst)

---

### Sprint 33: Ensemble Performance Analysis

**Scope:** Deep analysis of Sprint 32 results. Correlation structure among validated micro-strategies. Capital efficiency analysis. Turnover and commission impact. Drawdown comparison. Regime sensitivity.

**UI deliverable:** Research Console — **Ensemble Analysis Suite:**

- **Correlation Cluster Map:** The validated micro-strategies rendered as nodes in a force-directed graph, where proximity indicates correlation. Clusters of correlated strategies are visually grouped. This is a 2D precursor to the full Constellation — you start seeing micro-strategies as spatial objects rather than table rows.
- **Regime Performance Breakdown:** A faceted chart showing ensemble performance across different market regimes (low vol, normal, high vol, trending, choppy). Immediately reveals whether the ensemble's edge is regime-dependent or robust.
- **Commission Impact Model:** A chart showing ensemble net returns after simulated commissions at various trade frequencies. Answers "does the turnover cost eat the edge?"
- **Go/No-Go Dashboard:** A single summary view with the key comparison metrics, statistical confidence measures, and a clear visual verdict. This is the view you screenshot when you decide whether to proceed.

If Sprint 32 succeeded: document the methodology, update the Research Console with the ensemble construction playbook.

If Sprint 32 failed: diagnose why through the visual tools, determine if salvageable.

**State after:** A clear go/no-go decision, arrived at through visual analysis tools that give you genuine comprehension of the results, not just numbers.

**Timeline:** ~2–3 days

---

### Phase 8 Checkpoint

**ARGUS state:** Production trading continues with 10–11 strategies. The controlled experiment has produced a definitive answer on ensemble feasibility.

**What you see:** The Research Console is now a sophisticated analysis environment — sweep heatmaps, 3D parameter landscapes, FDR reports, smoothness overlays, ensemble equity curves, correlation cluster maps, regime breakdowns. You understand the ensemble approach not because you read a report, but because you watched it unfold visually across the Research Console.

**If go:** You have a validated ensemble of ORB micro-strategies, a proven methodology, and the visual tools to understand what the ensemble is doing. The path to Phase 9 is clear.

**If no-go:** The artisanal approach (Phase 6) continues. The Research Console and BacktestEngine are still valuable for individual strategy research. ARGUS is still strong — the ceiling is lower but the floor hasn't changed.

**Command Center:** 9 pages + Copilot. Research Console is the most visually sophisticated page in the system.

**Elapsed time from now:** ~9–11 weeks

---

## Phase 9: Ensemble Scaling

*Extends the proven methodology across all strategy families. Builds the Orchestrator and monitoring infrastructure to handle hundreds of micro-strategies. UI focus: the Constellation — making the full ensemble comprehensible as a living system.*

### Sprint 34: Cross-Family Search (VWAP + Afternoon Momentum)

**Scope (backend):** Apply the validated methodology to VWAP Reclaim and Afternoon Momentum template families. Same tiered sweep → statistical filtering → ensemble validation pipeline. Cross-family correlation analysis.

**Scope (frontend):** Research Console — **Cross-Family View:**

- The correlation cluster map (from Sprint 33) expands to show micro-strategies from multiple families, color-coded by family. You immediately see whether ORB, VWAP, and Momentum clusters are separated (good — uncorrelated alpha) or overlapping (concerning — hidden correlation).
- A **Family Contribution Chart** shows what percentage of ensemble returns come from each strategy family, broken down by regime. "In trending markets, ORB contributes 45% and VWAP contributes 35%. In choppy markets, Afternoon Momentum contributes 60%."

**State after:** Three strategy families have validated micro-strategy ensembles. Cross-family diversification measured and visualized. Total validated micro-strategies: likely 100–400.

**Timeline:** ~4–5 days

---

### Sprint 35: Cross-Family Search (Remaining Families)

**Scope:** Red-to-Green, Gap Fill, ABCD, and any other artisanal strategies from Phase 6 get the systematic search treatment. Each family's template is swept and filtered.

**UI deliverable:** Research Console correlation map now shows the full strategy universe — all families, all validated micro-strategies, all cross-family correlations. This is getting dense enough that you start needing the Constellation.

**State after:** All strategy families have validated ensembles. Total micro-strategies: potentially 200–800. Full cross-family correlation matrix computed and visualized.

**Timeline:** ~4–5 days

---

### Sprint 36: Ensemble Orchestrator V2 + Constellation (Analysis Mode)

**Scope (backend):** Replace the current equal-weight Orchestrator with an ensemble-aware version.

Core capabilities:
- **Activation filtering:** At any moment, only micro-strategies whose specific conditions match current market state are "hot." The rest are dormant. This is a lookup, not a computation — conditions are pre-specified by the template parameters.
- **Capital allocation across active micro-strategies:** Correlation-aware allocation. Highly correlated active strategies share a capital pool; uncorrelated strategies get independent allocation.
- **Position limiting:** When 50 micro-strategies want to buy NVDA simultaneously, the Orchestrator consolidates into a single position with size reflecting the aggregate conviction, not 50 separate positions.
- **Regime-dependent ensemble selection:** In high-volatility regimes, only micro-strategies validated in high-vol conditions activate. The Learning Loop (from Sprint 27) feeds regime classification into the Orchestrator.

**Scope (frontend):** **The Constellation** — Command Center page 10.

This is the centerpiece visualization of the ensemble vision. Initial build (analysis mode — not yet real-time):

**3D Strategy Space (Three.js):**
Each validated micro-strategy is a node — a small sphere — floating in a 3D space rendered via WebGL. The three spatial axes are mapped to configurable dimensions. Default mapping: X = time-of-day (left = morning, right = afternoon), Y = hold duration (bottom = short, top = long), Z = strategy family (depth layers). A control panel lets you remap any axis to: sector, market cap, volume regime, quality score, recent Sharpe, recent win rate, correlation cluster, or any template parameter.

**Color system:**
- Each strategy family has a base hue: blue for ORB, green for VWAP, amber for Afternoon Momentum, purple for Red-to-Green, etc.
- Brightness encodes validation strength — strongly validated strategies glow brighter, marginal strategies are dimmer.
- Opacity encodes recent activity — strategies that fired recently are more opaque, dormant strategies are translucent.

**Size encodes capital allocation.** Larger nodes have more capital. When the Orchestrator adjusts allocation, node sizes animate smoothly.

**Connections encode correlation.** Thin lines between highly correlated micro-strategies, color intensity proportional to correlation strength. Toggle connections on/off. When connections are on, the correlation structure of the entire ensemble is immediately visible — tight clusters, isolated outliers, cross-family bridges.

**Navigation:**
- Click-drag to rotate the entire constellation.
- Scroll to zoom.
- Click a node: info panel slides in showing the micro-strategy's full specification, recent performance, current state, trade history.
- Click a cluster: aggregate metrics for that group.
- Double-click a cluster: zoom in to see internal structure at higher resolution.

**Grouping modes** (smooth animated transitions between views):
- **By family:** Strategy family clusters. Shows alpha source diversity.
- **By time window:** Morning / midday / afternoon sectors. Shows temporal coverage.
- **By sector:** GICS sector groupings. Shows market exposure.
- **By regime:** Low-vol / normal / high-vol validated strategies grouped. Shows regime adaptiveness.
- **By performance:** Hot (recent winners) vs. cold (recent losers). Shows where alpha is coming from right now.

Each grouping mode rearranges the constellation with a smooth fly-through animation — nodes flow from one arrangement to another, maintaining identity so you can track individual strategies across views.

**Data pipeline:** Backend provides ensemble state via REST endpoint. Frontend renders in Three.js with instanced mesh geometry for performance (500–800 nodes is well within budget). Zustand manages constellation state. Grouping mode transitions are animated with spring physics.

> **ROADMAP CONTRADICTION NOTE:** This supersedes the existing "Orchestrator V2" concept from the build track queue. The original Orchestrator V2 was envisioned as an enhanced version of the rules-based V1, still managing a small number of strategies. This Ensemble Orchestrator V2 is a fundamentally different system. Also: the Constellation page replaces the role that an enhanced Pattern Library page would have played — at ensemble scale, a card-based gallery can't meaningfully represent hundreds of strategies, but a spatial visualization can.

**State after:** ARGUS can run hundreds of micro-strategies simultaneously in paper trading, with intelligent activation, allocation, and consolidation. And the Constellation page lets you *see* the entire ensemble — its structure, its diversity, its correlation topology — in a single navigable 3D view. You can spin through it, regroup it by different dimensions, click into clusters, and understand what your system is doing at a level that no spreadsheet or log file could provide.

**Timeline:** ~6–7 days (the largest sprint in the roadmap — backend Orchestrator + full 3D visualization)

---

### Sprint 37: Ensemble Monitoring + Real-Time Constellation

**Scope (backend):** WebSocket stream for ensemble state changes. Micro-strategy activation events, position events, allocation changes, health status changes — all pushed to the frontend in real time.

**Scope (frontend):** The Constellation goes live.

**Real-time firing effects:**
- When a micro-strategy's conditions are met and it generates a signal, its node **pulses** — a bright flash that radiates outward as a spherical ripple, like a neuron firing.
- If the signal passes quality filtering and gets executed: the ripple solidifies into a persistent glow, and the node enters its "holding" state — a gentle pulsing glow with a ring indicating P&L (green ring for profitable, red for underwater, ring thickness proportional to magnitude).
- If the signal gets rejected (quality too low, risk limit hit, correlated strategy already deployed): the ripple fades with a brief red flash and the node returns to dormant translucency.
- Over the course of a trading day, you watch patterns of activation sweep across the constellation — morning strategies lighting up the left side (time-of-day axis), afternoon strategies lighting up the right. Sector-specific clusters flash when news hits. High-vol strategies activate when volatility spikes.

**Timeline scrubber:**
A control at the bottom of the Constellation lets you replay the day's activity in fast-forward. Watch the entire trading session's firing patterns compressed into 30 seconds. See where capital flowed, which clusters were active, when the ensemble shifted from offense to defense. This is both an analysis tool and, honestly, the most visually compelling thing in the entire system.

**Dashboard evolution:**
The Dashboard shifts from per-strategy cards to ensemble health metrics:
- **Ensemble Heartbeat:** A real-time indicator showing active strategy count, current capital utilization, aggregate position count, and portfolio heat (how much risk is deployed vs. available).
- **Family Activity Bars:** Horizontal bars for each strategy family showing current activation level (what % of that family's micro-strategies are active right now).
- **Mini-Constellation:** A small, simplified 2D version of the Constellation embedded in the Dashboard — a sparkline-style overview of ensemble activity. Click to open the full Constellation page.

**Orchestrator page evolution:**
Instead of showing individual strategy cards (impractical at 500+ strategies), the Orchestrator shows:
- **Activation Stream:** A real-time feed of strategy activations, signal generations, quality scores, and execution decisions. Each line: "14:23:07 | ORB-T47 | NVDA | Signal: BUY | Quality: 78 | EXECUTED @ $892.34"
- **Active Strategy Count:** By family, by regime, by sector — compact summary of what's currently running.
- **Capital Allocation Treemap:** A treemap visualization showing how capital is distributed across families, strategies, and positions at this moment. Larger rectangles = more capital. Color = P&L.

**Performance page evolution:**
- **Contribution Attribution:** Which families, which clusters, which individual micro-strategies are contributing to today's P&L? A waterfall chart showing the contribution of each component.
- **Correlation Stability Monitor:** Is the correlation structure behaving as expected? A time series showing whether historically uncorrelated families are remaining uncorrelated. Drift detection alerts if correlation structure changes.

**The Debrief evolution:**
The AI-generated narrative now covers the ensemble: "Today ARGUS activated 47 micro-strategies across 4 families. The ORB cluster was most active in the first hour, contributing $340 in realized P&L across 12 positions. VWAP strategies activated after 10:30 AM when 3 names reclaimed VWAP following the CPI data release. The highest-quality signal of the day was VWAP-T23 on AAPL (quality 91/100), which produced a 2.1R winner in 18 minutes. The ensemble's correlation structure was stable — cross-family correlation remained below 0.15."

**State after:** This is the complete visual experience. You open the Command Center during a trading session and you can *see* the ensemble thinking. The Constellation shows firing patterns in real time. The Dashboard shows ensemble health at a glance. The Orchestrator shows the decision stream. The Performance page shows contribution attribution. The Debrief tells you the story of the day. The system is fully legible at every level of abstraction — from the single micro-strategy node you click on in the Constellation, up to the ensemble-level heartbeat on the Dashboard.

**Timeline:** ~5–6 days

---

### Phase 9 Checkpoint

**ARGUS state:** A fully operational ensemble trading system with 200–800 validated micro-strategies across all families, ensemble-aware Orchestrator, correlation-managed allocation, and comprehensive visual monitoring — anchored by the real-time Constellation. Paper trading at ensemble scale.

**What you see:** The Constellation — hundreds of nodes floating in 3D space, organized by whatever dimension you choose, lighting up as they fire, connected by correlation threads. The Dashboard heartbeat pulsing with ensemble activity. The activation stream scrolling on the Orchestrator. Family contribution charts on Performance. AI-narrated debriefs covering the full ensemble.

**What's possible:** On any given market day, perhaps 20–60 micro-strategies are active. Each deploys modest capital with high conviction. You watch the patterns of activation sweep across the Constellation and understand, intuitively and visually, what your system is doing and why. In aggregate, the system generates consistent returns with dramatically lower drawdown than any individual strategy.

**Command Center:** 10 pages. Constellation is the centerpiece.

**Elapsed time from now:** ~11–14 weeks

---

## Phase 10: Full Vision

*The self-improving system. The ensemble doesn't just execute — it learns, adapts, and evolves. UI focus: make adaptation and discovery visible.*

### Sprint 38: Learning Loop V2 (Ensemble Edition)

**Scope (backend):** Automated performance tracking at micro-strategy level. Strategies that underperform their historical expectation get automatically throttled. Strategies that outperform get boosted (within risk limits). Rolling recalibration: every N trading days, the statistical validation framework re-runs on recent data to check if validated strategies are still valid. Automatic retirement of strategies that lose their edge. Automatic promotion of promising candidates from a research queue.

**Scope (frontend):** The Constellation becomes a living ecosystem:

- **Lifecycle visualization:** Nodes in the Constellation now show their lifecycle state — newly promoted strategies have a "birth" animation (fade in, grow from zero size). Strategies being throttled shrink gradually. Strategies being retired fade out over several sessions, like stars dimming. The constellation is visibly evolving over time, not static.
- **Health decay indicators:** A node whose performance is decaying shows a slow color shift from its family hue toward grey. Before it's retired, it's visually "dying" — dimmer, greyer, smaller. This gives you intuitive awareness of which parts of the ensemble are aging.
- **Adaptation Timeline:** A new panel on the Research Console showing the ensemble's evolution over time — strategies added, retired, throttled, boosted — as a timeline. "Week 3: +12 ORB variants promoted, -4 VWAP variants retired, net ensemble Sharpe: 2.7 → 2.9."

**State after:** The ensemble is self-maintaining. Degraded strategies visibly fade. Strong strategies visibly grow. You watch the ensemble evolve over days and weeks — the Constellation is not a snapshot, it's a living system. The Adaptation Timeline gives you the long view of how the ensemble is changing.

**Timeline:** ~4–5 days

---

### Sprint 39: Continuous Discovery Pipeline

**Scope (backend):** A background process that continuously explores new parameter/filter combinations. When market conditions change (new sectors emerge, volatility regime shifts), the pipeline searches for micro-strategies that work in the new conditions. Validated discoveries enter a staging queue for human review before activation.

The pipeline runs overnight (while US markets are closed), using historical data updated daily. Each morning, the intelligence brief (from Sprint 23) includes a "research findings" section.

**Scope (frontend):** Research Console — **Discovery Feed:**

- **Overnight Results:** Each morning, a panel shows what the discovery pipeline found overnight: "3 new micro-strategies validated in healthcare sector with earnings catalyst filter. 1 new Afternoon Momentum variant for small-cap names." Each discovery is a card showing the strategy specification, backtest metrics, and approve/reject buttons.
- **Staging Queue Visualization:** Approved discoveries appear in a "staging" layer on the Constellation — ghost nodes showing where they'd live in the strategy space, pending deployment. You can see how new discoveries would change the ensemble's shape and coverage before committing to them.
- **Discovery Heatmap:** A view showing which regions of the parameter/filter space the discovery pipeline is currently exploring, which regions have been exhausted, and which regions are yielding new discoveries. This tells you where the frontier of strategy research is.

The morning intelligence brief (Sprint 23) now includes: "Overnight Discovery: 3 strategies validated | 2 strategies recommended for retirement | Net expected Sharpe impact: +0.03"

**State after:** ARGUS discovers its own opportunities. Each morning, you review discoveries visualized as ghost nodes on the Constellation, approve the ones you like, and watch them join the ensemble. The system's strategy repertoire grows organically. The Discovery Heatmap tells you where the fertile ground is and where the search has been exhausted.

**Timeline:** ~3–4 days

---

### Sprint 40: Performance Workbench

**Scope:** Customizable widget grid using `react-grid-layout`. Drag/drop/resize visualizations into personalized analysis workflows.

**Widget palette:**
- Strategy family performance (line charts, bar charts)
- Correlation matrix heatmap
- Regime analysis panels
- Micro-strategy activation heatmap (time-of-day × day-of-week)
- Capital utilization over time
- Drawdown decomposition
- Sector exposure history
- Quality score distribution
- Win rate by family / regime / time-of-day
- Commission impact tracker
- Ensemble Sharpe rolling window
- Constellation mini-view (embeddable)
- Discovery pipeline status
- Custom metric formulas

**Two-stage build:**
1. Rearrangeable tab system — save custom page layouts as named tabs ("Morning Review," "Post-Session Analysis," "Weekly Deep Dive").
2. Full widget palette — drag any widget onto any tab, resize and arrange freely.

**State after:** You have a Bloomberg-terminal-grade analysis environment. During trading sessions, your "Live Session" tab shows the widgets you need in real time. During analysis, your "Deep Dive" tab shows the analytical tools. You build the views that match your workflow, not a predetermined layout.

**Timeline:** ~4–5 days

---

### Sprint 41+: Horizon Items

These are natural extensions that become possible after the full vision is operational:

- **Order Flow Model integration** (post-revenue, DEC-238): Databento Plus ($1,399/mo) for L2/L3 data. Micro-strategies that incorporate order flow signals. The Constellation gains a new dimension: order flow strength.
- **Options strategies:** Ensemble approach applied to options (covered calls on positions, volatility strategies). New family hues in the Constellation.
- **Multi-asset expansion:** Futures, forex. Same ensemble infrastructure, different data feeds and strategy templates. The Constellation shows asset-class clusters.
- **Cython/Rust hot path:** If BacktestEngine speed is the bottleneck for continuous discovery, rewrite the inner loop in compiled code for 10–50x speedup.
- **Multi-account management:** Run different ensemble configurations for different risk profiles (e.g., conservative IRA vs. aggressive individual account). Constellation shows account-specific views.
- **Constellation VR/AR mode:** At the scale of 1,000+ strategies, true 3D navigation via VR headset becomes compelling — walk through your strategy space, reach out and touch clusters, see firing patterns surround you. Aspirational but technically feasible with WebXR.

---

### Phase 10 Checkpoint (Full Vision)

**ARGUS state:** A self-improving ensemble trading system with hundreds of validated micro-strategies, adaptive allocation, continuous discovery, and comprehensive visual monitoring — all rendered through the Constellation, Performance Workbench, and 10-page Command Center.

**What you see:** You open the Command Center at 10 PM Taipei time. The Pre-Market Intelligence Brief is waiting — macro context, catalyst cards, overnight discovery results with ghost nodes on the Constellation. You approve two new discoveries. You check the Adaptation Timeline — the ensemble has gained 8 strategies and retired 3 this week, net Sharpe trending up. Market opens. The Constellation comes alive — morning strategies light up across the left side, firing ripples spreading through the ORB cluster. The Dashboard heartbeat shows 34 active strategies, 12% capital deployed. A high-quality VWAP reclaim fires on AAPL — you see the bright pulse, the green ring growing. The activation stream scrolls on the Orchestrator. By 3 AM, the afternoon strategies have taken over, the right side of the Constellation is lit up, the left side has gone dormant. You scrub back through the session on the timeline, watching the entire day's activity replay in 30 seconds — a wave of activation moving left to right across the strategy space. The Debrief generates: "47 activations, 31 executions, 28 wins, 3 losses. Net +$1,247. Highest contributor: ORB cluster (+$580). Ensemble Sharpe (30-day rolling): 3.2."

**What this means for your family:** If the ensemble achieves a Sharpe of 3.0+ on $200K+ capital, the income generation goal from the Day Trading Manifesto is met with substantial margin. The few hours of "active work" per night becomes: review the intelligence brief, approve/reject discoveries, watch the Constellation during the session (monitoring, not managing), review the debrief. The system runs. You supervise.

**Elapsed time from now:** ~14–18 weeks (roughly 4 months)

---

## Summary Timeline

| Phase | Sprints | Focus | Duration | Cumulative |
|-------|---------|-------|----------|------------|
| 5: Foundation Completion | 21.5–24 | Live trading, AI layer, quality filtering | ~2–3 weeks | Weeks 1–3 |
| 6: Strategy Expansion | 25–27 | Artisanal strategies, learning loop V1 | ~2–3 weeks | Weeks 3–6 |
| 7: Infrastructure Unification | 28–30 | BacktestEngine, templates, Research Console | ~2–2.5 weeks | Weeks 6–8.5 |
| 8: Controlled Experiment | 31–33 | Statistical framework, ORB search, go/no-go | ~2–2.5 weeks | Weeks 8.5–11 |
| 9: Ensemble Scaling | 34–37 | Cross-family search, Constellation, live ensemble | ~3–4 weeks | Weeks 11–15 |
| 10: Full Vision | 38–41+ | Learning loop V2, discovery pipeline, workbench | ~2.5–3.5 weeks | Weeks 15–18 |

**Total: ~41 sprints across ~18 weeks / 4.5 months**

---

## Command Center Evolution Summary

| Sprint | Page Changes |
|--------|-------------|
| 21.7 | Dashboard: +Pre-Market Watchlist panel |
| 22 | Copilot: shell → live |
| 23 | Dashboard: +catalyst badges. Debrief: +AI narratives. +Pre-Market Intelligence Brief view |
| 24 | Trades: +quality badges. Orchestrator: +live quality scoring. Dashboard: +Signal Quality Distribution. Debrief: +quality vs. outcome scatter |
| 26 | Dashboard: +Short Exposure indicator (if applicable) |
| 27 | Orchestrator: +Strategy Health Panel with health bands + throttle/boost cards. Performance: +Correlation Matrix heatmap |
| 28 | **+Research Console (page 9):** Run Manager, Result Comparison, Run Configuration |
| 29 | Research Console: +Sweep Manager, +Sweep Heatmap, +Parameter Landscape (3D) |
| 30 | Pattern Library: evolves to template gallery with instance browser and template explorer |
| 31 | Research Console: +Data Split Visualizer, +FDR Report, +Smoothness Heatmap overlay |
| 32 | Research Console: live progressive sweep rendering, staged validation views |
| 33 | Research Console: +Correlation Cluster Map, +Regime Breakdown, +Go/No-Go Dashboard |
| 34 | Research Console: +Cross-Family View, +Family Contribution Chart |
| 36 | **+Constellation (page 10):** 3D strategy space, grouping modes, navigation. Analysis mode |
| 37 | Constellation: +real-time firing, +timeline scrubber. Dashboard: +Ensemble Heartbeat, +Family Activity Bars, +Mini-Constellation. Orchestrator: +Activation Stream, +Capital Treemap. Performance: +Contribution Attribution, +Correlation Stability. Debrief: ensemble-scale AI narratives |
| 38 | Constellation: +lifecycle animations (birth/decay/death). Research Console: +Adaptation Timeline |
| 39 | Research Console: +Discovery Feed, +Staging Queue (ghost nodes on Constellation), +Discovery Heatmap. Intelligence Brief: +overnight discovery results |
| 40 | **Performance Workbench:** react-grid-layout widget system, customizable analysis tabs |

---

## Key Contradictions with Existing Roadmap

1. **Orchestrator V2 scope change.** The existing roadmap envisions Orchestrator V2 as an enhanced rules-based system for ~15 strategies. The ensemble vision requires a fundamentally different Orchestrator that handles hundreds of micro-strategies with correlation-aware allocation and activation filtering. These are incompatible — the ensemble Orchestrator (Sprint 36) supersedes the original V2 concept.

2. **Strategy development methodology pivot.** The existing roadmap (Sprints 25–28+) adds strategies one at a time through manual design. The ensemble vision (Phase 8+) generates strategies through systematic search. These coexist until Phase 8's go/no-go decision — if the controlled experiment succeeds, future strategy development shifts from artisanal to industrial. If it fails, the artisanal approach continues.

3. **Performance Workbench timing.** Currently deferred with no sprint assignment. The ensemble vision makes it significantly more important — monitoring 500 micro-strategies requires customizable analysis tools. Placed at Sprint 40 in this roadmap. A case exists for pulling it earlier to Sprint 37, but the Constellation and ensemble monitoring take priority there.

4. **VectorBT role reduction.** VectorBT currently handles all parameter sweeps. After Phase 7, the BacktestEngine takes over for serious validation work. VectorBT remains useful for rapid coarse screening (Stage 1 of the tiered sweep) but is no longer the primary optimization tool. Not a contradiction exactly — more a graceful role transition.

5. **Pattern Library page semantics.** Evolves from individual strategy gallery (current) → template gallery with parameter ranges (Sprint 30) → secondary to the Constellation for ensemble visualization (Sprint 36+). The Pattern Library doesn't disappear, but its role shifts from "primary strategy view" to "template reference and configuration tool."

6. **Dashboard density.** The Dashboard accumulates significant new panels across this roadmap: Pre-Market Watchlist, Signal Quality Distribution, Short Exposure indicator, Ensemble Heartbeat, Family Activity Bars, Mini-Constellation. This needs careful UX work to avoid clutter — the Performance Workbench (Sprint 40) partially solves this by letting you customize which panels appear where. Consider progressive disclosure: panels appear only when relevant features are active.

---

## Critical Risk: Historical Data Sufficiency

The single biggest risk to the ensemble vision (Phases 8–10) is data. Three-way splits (train/selection/validation) across 35 months of data may not provide enough statistical power to validate micro-strategies, especially those that trigger rarely. Options:

- **Acquire deeper history.** Databento historical data for 5–10 years of 1-minute bars. Cost: one-time purchase, potentially $1,000–5,000 depending on scope. This is almost certainly worth it if the ensemble vision is pursued.
- **Synthetic data augmentation.** Generate realistic market data through statistical resampling (block bootstrap, etc.) to supplement real data. Adds volume but introduces model risk.
- **Accept lower granularity.** Use 5-minute bars for the historical sweep (more years of data available from cheaper sources) and validate final candidates on 1-minute Databento data.

This risk should be resolved during Phase 7, before the controlled experiment begins. A DEC entry reserving this decision is warranted now.

---

## The Decision That Matters Most

The entire roadmap pivots on the outcome of Sprint 32 (ORB Family Systematic Search). Everything before it is valuable regardless — live trading, AI layer, artisanal strategies, BacktestEngine, Research Console. Everything after it depends on whether systematic search produces validated ensembles that outperform hand-crafted strategies.

If you build nothing beyond Phase 6, you still have a strong AI-enhanced multi-strategy trading system. If you build through Phase 8 and the experiment fails, you still have the best strategy research infrastructure of any independent trader. The ensemble vision is the ceiling, not the floor.

But if the experiment succeeds — and you build the Constellation, the real-time firing, the self-adapting learning loop, the continuous discovery pipeline — then you've built something that doesn't have a comparable at the independent trader scale. A system that discovers its own alpha, validates it statistically, deploys it intelligently, and shows you the entire process as a living, breathing 3D visualization.

That's the portal, not the tool.
