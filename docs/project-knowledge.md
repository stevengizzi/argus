# ARGUS — Project Knowledge (Claude Context)

> *Tier A operational context for Claude Code and Claude.ai. Last updated: March 11, 2026 (Sprint 23.7 doc sync).*
> *Full decision rationale: `docs/decision-log.md` | Sprint details: `docs/sprint-history.md` | DEC index: `docs/dec-index.md`*

---

## What Is ARGUS

ARGUS is a fully automated, AI-enhanced multi-strategy day trading system for US equities. It combines rules-based strategy execution with planned AI-powered setup quality grading, NLP catalyst analysis, and dynamic position sizing. Built in Python (FastAPI backend) with a React/TypeScript Command Center frontend (Tauri desktop + PWA mobile). The user is building this to generate household income for his family. He operates from Taipei, trading US markets during overnight hours (~10:30 PM–5:00 AM local time), making mobile access critical. He can code in Python and has trading experience but no prior algorithmic trading system.

## Current State

**Tests:** 2,529 pytest + 435 Vitest
**Sprints completed:** 1 through 23.8 (23 full sprints + sub-sprints + Universe Manager + Autonomous Sprint Runner + Wide Pipe + NLP Catalyst + Pipeline Integration + Startup Fixes)
**Active sprint:** None (between sprints — live QA campaign in progress)
**Next sprint:** 24 (Setup Quality Engine + Dynamic Sizer)
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

*Full sprint scopes and session details: `docs/sprint-history.md`*

### Build Track Queue

21.6 (Backtest Re-Validation, parallel) → 24 (Setup Quality Engine + Dynamic Sizer) → 25 (Red-to-Green + Pattern Library Foundation) → 26 (Pattern Expansion I) → 27 (Short Selling + Parabolic Short + Pattern Expansion II) → 28 (Learning Loop V1) → 29–31 (BacktestEngine, Sweep Infrastructure, Strategy Templates) → 32–34 (Statistical Validation, ORB Systematic Search ★, Ensemble Analysis) → 35–38 (Cross-Family Search, Ensemble Orchestrator V2, Synapse) → 39–41 (Learning Loop V2, Continuous Discovery, Performance Workbench). Sprint 23.5 (NLP Catalyst Pipeline) complete. Order Flow Model deferred to post-revenue (DEC-238). Full roadmap: `docs/roadmap.md` (DEC-262).

### Validation Track

Paper trading active with Databento EQUS.MINI + IBKR paper (Account U24619949, DEC-236). Gates: IBKR paper 20+ days (Gate 2) → AI-enhanced paper 30+ days (Gate 3) → Full system paper 50+ cumulative days, Sharpe > 2.0 (Gate 4) → CPA consultation → live minimum size (Gate 5).

### Expanded Vision (DEC-163, DEC-262)

15+ artisanal patterns → ensemble systematic search → self-improving trading intelligence platform. Near-term (Phase 5–6): Setup Quality Engine (0–100 scoring, DEC-239), NLP Catalyst Pipeline (SEC EDGAR + FMP + Finnhub + Claude API, **Sprint 23.5 ✅**), Dynamic Position Sizer, Learning Loop V1, Short Selling Infrastructure, Universe Manager with full-universe monitoring (DEC-263, **Sprint 23 ✅**). Mid-term (Phase 7–8): BacktestEngine, parameterized strategy templates, systematic parameter search, controlled experiment (go/no-go gate). Long-term (Phase 9–10): Ensemble Orchestrator V2, Synapse visualization, Continuous Discovery Pipeline, Performance Workbench. Order Flow Model deferred to post-revenue (DEC-238, requires Databento Plus $1,399/mo). Full roadmap: `docs/roadmap.md`.

---

## Architecture

### Three-Tier System
1. **Trading Engine** — Strategies, Orchestrator, Risk Manager, Data Service, Broker abstraction, Order Manager, Trade Logger, Backtesting (VectorBT + Replay Harness)
2. **Command Center** — 7 pages (all built): Dashboard, Trade Log, Performance, Orchestrator, Pattern Library, The Debrief, System. Tauri desktop + PWA mobile + web. AI Copilot active.
3. **AI Layer** (Sprint 22) — Claude API (Opus, DEC-098) via ClaudeClient wrapper; PromptManager with system prompt template and behavioral guardrails (DEC-273); SystemContextBuilder for per-page context injection (DEC-268); tool_use for structured action proposals (DEC-271) with 5 defined tools (DEC-272); ActionManager with DB-persisted proposals and 5-min TTL (DEC-267); 5 ActionExecutors with 4-condition pre-execution re-check; ConversationManager with calendar-date keying and tags (DEC-266); UsageTracker for per-call cost tracking (DEC-274); DailySummaryGenerator for insight card + daily summaries; ResponseCache for insight TTL caching. WS /ws/v1/ai/chat for streaming with actual API usage extraction (DEC-265). All timestamps ET-based (DEC-276). All AI features degrade gracefully when ANTHROPIC_API_KEY unset.
4. **Intelligence Layer** (Sprints 23.5 + 23.6) — CatalystPipeline orchestrates three data sources: SECEdgarSource (8-K, Form 4), FMPNewsSource (stock news, press releases), FinnhubSource (company news, analyst recommendations). CatalystClassifier uses Claude API with rule-based fallback (DEC-301). CatalystStorage with SQLite persistence in separate catalyst.db (DEC-309) and headline hash deduplication (DEC-302). BriefingGenerator produces pre-market intelligence briefs with $5/day cost ceiling (DEC-303). Post-classification semantic dedup by (symbol, category, time_window) before storage (DEC-311). Batch-then-publish ordering for data safety (DEC-312). Config-gated via `catalyst.enabled` (DEC-300). Intelligence startup factory in `argus/intelligence/startup.py` builds all components from config (DEC-308). Polling loop via asyncio task with market-hours-aware intervals (DEC-315). Sprint 23.8 hardened the pipeline: `asyncio.wait_for(120)` safety timeout on source gather (DEC-319), polling task health monitoring via `done_callback` (DEC-320), symbol scope reduced from full viable universe to scanner watchlist (DEC-321), FMP news circuit breaker on 401/403 (DEC-323), cost ceiling enforcement wired into classifier with cycle cost logging (DEC-324), and Databento lazy warm-up `end` clamped to `now - 600s` (DEC-326). FMP canary test at startup validates API schema (DEC-313). Frontend: CatalystBadge, CatalystAlertPanel, IntelligenceBriefView with TanStack Query hooks.

### Key Components
- **Strategies:** Daily-stateful, session-stateless plugins (DEC-028). 4 active. 14 more planned.
- **Orchestrator:** Rules-based V1 (DEC-118). Equal-weight allocation, regime monitoring (SPY vol as VIX proxy), performance throttling, pre-market routine.
- **Risk Manager:** Three-level gating (strategy, cross-strategy, account). Approve-with-modification for share reduction and target tightening; never modify stops or entry (DEC-027). Concentration limit approve-with-modification with 0.25R floor (DEC-249).
- **Data Service:** Databento EQUS.MINI primary (DEC-248). Event Bus sole streaming mechanism (DEC-029). Databento callbacks on reader thread, bridged via `call_soon_threadsafe()` (DEC-088). Universe Manager (Sprint 23) adds fast-path discard for non-viable symbols and ALL_SYMBOLS Databento mode. Time-aware indicator warm-up (DEC-316, Sprint 23.7): pre-market boot skips warm-up; mid-session boot uses lazy per-symbol backfill on first candle arrival.
- **Universe Manager (Sprint 23):** FMPReferenceClient fetches Company Profile + Share Float in batches for ~3,000–5,000 symbols. UniverseManager applies system-level filters (OTC, price, volume; fail-closed on missing data per DEC-277), builds pre-computed routing table mapping symbols to qualifying strategies via declarative `universe_filter` YAML configs. O(1) route_candle lookup. Fast-path discard in DatabentoDataService drops non-viable symbols before IndicatorEngine. Config-gated: `universe_manager.enabled` in system.yaml. Backward compatible (disabled = existing scanner flow). Full-universe input pipe active (DEC-299): ~8,000 symbols fetched from FMP stock-list, ~3,000–4,000 viable after system filters. Reference data file cache (DEC-314) with JSON persistence, atomic writes, and per-symbol staleness tracking enables incremental warm-up (~2–5 min vs ~27 min full fetch). Periodic cache saves every 1,000 symbols during fetch + save on shutdown signal (DEC-317, Sprint 23.7) prevent data loss on interrupted cold-starts.
- **Broker Abstraction:** IBKRBroker (live, via `ib_async`), AlpacaBroker (incubator), SimulatedBroker (backtest). Atomic bracket orders (DEC-117). Config-driven selection via BrokerSource enum (DEC-094).
- **Backtesting:** VectorBT (parameter sweeps, precompute+vectorize mandated DEC-149) + Replay Harness (production code replay). Walk-forward validation mandatory, WFE > 0.3 (DEC-047).
- **Event Bus:** FIFO per subscriber, monotonic sequence numbers, no priority queues. In-process asyncio only (DEC-025).
- **Order Manager:** Event-driven (tick-subscribed for open positions) + 5-second fallback poll + scheduled EOD flatten (DEC-030).

### Tech Stack
- **Backend:** Python 3.11+, FastAPI (in-process Phase 12 startup, DEC-099), aiosqlite (DEC-034), asyncio Event Bus
- **Frontend:** React + TypeScript, TanStack Query, Zustand, Framer Motion, TradingView Lightweight Charts + Recharts + D3 (DEC-104/215), Tailwind CSS v4
- **Desktop/mobile:** Tauri v2 desktop, PWA (iPhone/iPad) (DEC-080)
- **Testing:** pytest + Vitest (DEC-130), ruff linting
- **Config:** YAML → Pydantic BaseModel validation (DEC-032)
- **IDs:** ULIDs via `python-ulid` (DEC-026)
- **Infra:** GitHub (public repo), Databento ($199/mo active), FMP Starter ($22/mo, Sprint 21.7), IBKR paper trading active

### File Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus
├── strategies/     # Base class + individual strategy modules
├── data/           # Scanner, Data Service, Indicators, IndicatorEngine, Universe Manager, FMP Reference
├── execution/      # Broker abstraction, Order Manager
├── analytics/      # Trade Logger, Performance Calculator
├── backtest/       # VectorBT helpers, Replay Harness
├── ui/             # React frontend (Vite + TypeScript)
├── api/            # FastAPI REST + WebSocket
├── ai/             # Claude API integration (Sprint 22+)
├── intelligence/   # CatalystPipeline, CatalystClassifier, CatalystStorage, BriefingGenerator (Sprint 23.5)
├── config/         # YAML config files (system.yaml, system_live.yaml, strategies/)
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

Cross-strategy: ALLOW_ALL (DEC-121/160). Time windows largely non-overlapping. 5% max single-stock exposure across all strategies. ORB family shares OrbBaseStrategy ABC (DEC-120) with same-symbol mutual exclusion — first ORB strategy to fire on a symbol blocks the other for the day (DEC-261). Per-signal time stops (DEC-122).

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
- **Pre-Databento backtests provisional:** All pre-Databento parameter optimization requires re-validation (DEC-132).
- **No live L2/L3 on Standard plan:** Requires Plus tier $1,399/mo (DEC-237).
- **Databento EQUS.MINI historical lag:** Multi-day lag for daily bars (DEC-247). **Resolved by Sprint 21.7:** FMP Scanner now provides dynamic pre-market symbol selection via gainers/losers/actives endpoints.
- **Latency from Taipei:** ~150–200ms to US exchanges. Scalping has structural disadvantages; longer-duration strategies (5–30 min holds) preferred.
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

**Pipeline Integration (Sprint 23.6):** DEC-308 (deferred initialization), DEC-309 (separate catalyst.db), DEC-310 (CatalystConfig in SystemConfig), DEC-311 (semantic dedup), DEC-312 (batch-then-publish), DEC-313 (FMP canary test), DEC-314 (reference data cache), DEC-315 (polling loop).

**Startup Scaling (Sprint 23.7):** DEC-316 (time-aware warm-up — skip pre-market, lazy mid-session), DEC-317 (periodic cache saves every 1,000 symbols), DEC-318 (API port guard + double-bind fix).

**Documentation:** DEC-262 (roadmap consolidation — single canonical roadmap.md), DEC-275 (compaction risk scoring system).

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
| `docs/decision-log.md` | All DEC entries with full rationale |
| `docs/dec-index.md` | Quick-reference DEC index with status |
| `docs/sprint-history.md` | Complete sprint history |
| `docs/process-evolution.md` | Workflow evolution narrative |
| `docs/risk-register.md` | Assumptions and risks |
| `docs/live-operations.md` | Live trading procedures |
| `CLAUDE.md` | Claude Code session context |
| `docs/ui/ux-feature-backlog.md` | Planned UI features |
| `docs/strategies/STRATEGY_*.md` | Per-strategy spec sheets |
| `workflow/` | Claude-workflow metarepo (protocols, templates, runner) |

---

## Communication Style

The user prefers thorough, detailed explanations and expects structured outputs ready for copy-paste. He appreciates proactive pushback and concerns. He values clarifying questions before assumptions. He wants the *why* behind every recommendation. He is building this for his family's financial future — treat every decision with the seriousness that implies. Direct, technically precise communication.
