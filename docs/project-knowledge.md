# ARGUS — Project Knowledge (Claude Context)

> *Tier A operational context for Claude Code and Claude.ai. Last updated: March 4, 2026.*
> *Full decision rationale: `docs/decision-log.md` | Sprint details: `docs/sprint-history.md` | DEC index: `docs/dec-index.md`*

---

## What Is ARGUS

ARGUS is a fully automated, AI-enhanced multi-strategy day trading system for US equities. It combines rules-based strategy execution with planned AI-powered setup quality grading, NLP catalyst analysis, and dynamic position sizing. Built in Python (FastAPI backend) with a React/TypeScript Command Center frontend (Tauri desktop + PWA mobile). The user is building this to generate household income for his family. He operates from Taipei, trading US markets during overnight hours (~10:30 PM–5:00 AM local time), making mobile access critical. He can code in Python and has trading experience but no prior algorithmic trading system.

## Current State

**Tests:** 1,710 pytest + 255 Vitest
**Sprints completed:** 1 through 21d (21 full sprints + sub-sprints)
**Active sprint:** 21.5 (Live Integration) — Blocks A+B complete, Block C (market day) + D (closeout) pending
**Next sprint:** 22 (AI Layer MVP)
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
| 21.5 | Live Integration (IN PROGRESS) | 1715+255V | Feb 28– | DEC-230–256 |

*Full sprint scopes and session details: `docs/sprint-history.md`*

### Build Track Queue

21.5 (Live Integration, IN PROGRESS) → 21.6 (Backtest Re-Validation, parallel w/ 22) → 22 (AI Layer MVP) → 23 (NLP Catalyst + Pre-Market Engine) → 24 (Setup Quality Engine + Dynamic Sizer) → 25 (Red-to-Green + Pattern Library) → 26 (Pattern Expansion I) → 27 (Short Selling + Parabolic Short) → 28–32+ (Pattern Expansion II/III, Learning Loop, Orchestrator V2). Order Flow Model deferred to post-revenue (DEC-238).

### Validation Track

Paper trading active with Databento EQUS.MINI + IBKR paper (Account U24619949, DEC-236). Gates: IBKR paper 20+ days (Gate 2) → AI-enhanced paper 30+ days (Gate 3) → Full system paper 50+ cumulative days, Sharpe > 2.0 (Gate 4) → CPA consultation → live minimum size (Gate 5).

### Expanded Vision (DEC-163)

15+ pattern AI-enhanced platform. Planned: Setup Quality Engine (0–100 scoring, DEC-239), NLP Catalyst Pipeline (SEC EDGAR + Finnhub + FMP + Claude API, DEC-164), Dynamic Position Sizer, Learning Loop, Pre-Market Intelligence Engine. Order Flow Model deferred to post-revenue (DEC-238, requires Databento Plus $1,399/mo). See `docs/research/ARGUS_Expanded_Roadmap.md`.

---

## Architecture

### Three-Tier System
1. **Trading Engine** — Strategies, Orchestrator, Risk Manager, Data Service, Broker abstraction, Order Manager, Trade Logger, Backtesting (VectorBT + Replay Harness)
2. **Command Center** — 7 pages (all built): Dashboard, Trade Log, Performance, Orchestrator, Pattern Library, The Debrief, System. Tauri desktop + PWA mobile + web. Copilot shell built (Sprint 22 activates).
3. **AI Layer** (Sprint 22+) — Claude API (Opus, DEC-098), approval workflow, contextual copilot (DEC-170)

### Key Components
- **Strategies:** Daily-stateful, session-stateless plugins (DEC-028). 4 active. 14 more planned.
- **Orchestrator:** Rules-based V1 (DEC-118). Equal-weight allocation, regime monitoring (SPY vol as VIX proxy), performance throttling, pre-market routine.
- **Risk Manager:** Three-level gating (strategy, cross-strategy, account). Approve-with-modification for share reduction and target tightening; never modify stops or entry (DEC-027). Concentration limit approve-with-modification with 0.25R floor (DEC-249).
- **Data Service:** Databento EQUS.MINI primary (DEC-248). Event Bus sole streaming mechanism (DEC-029). Databento callbacks on reader thread, bridged via `call_soon_threadsafe()` (DEC-088).
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
- **Infra:** GitHub (public repo), Databento ($199/mo active), IBKR paper trading active

### File Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus
├── strategies/     # Base class + individual strategy modules
├── data/           # Scanner, Data Service, Indicators, IndicatorEngine
├── execution/      # Broker abstraction, Order Manager
├── analytics/      # Trade Logger, Performance Calculator
├── backtest/       # VectorBT helpers, Replay Harness
├── ui/             # React frontend (Vite + TypeScript)
├── api/            # FastAPI REST + WebSocket
├── ai/             # Claude API integration (Sprint 22+)
├── intelligence/   # Quality Engine, Catalyst, Position Sizer (Sprint 23+)
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

Cross-strategy: ALLOW_ALL (DEC-121/160). Time windows largely non-overlapping. 5% max single-stock exposure across all strategies. ORB family shares OrbBaseStrategy ABC (DEC-120). Per-signal time stops (DEC-122).

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
- **Databento EQUS.MINI historical lag:** Multi-day lag for daily bars (DEC-247). Scanner handles with retry + static watchlist fallback.
- **Latency from Taipei:** ~150–200ms to US exchanges. Scalping has structural disadvantages; longer-duration strategies (5–30 min holds) preferred.
- **Secrets:** All API keys in encrypted secrets manager, never in code/git.
- **Audit:** Every action logged immutably.

---

## Monthly Costs

| Item | Cost | Status |
|------|------|--------|
| Databento US Equities Standard | $199/mo | Active |
| IBKR commissions | ~$43/day at scale | Paper trading (no cost yet) |
| Claude API (Sprint 22+) | ~$35–50/mo | Not yet active |
| IQFeed (forex/news, future) | ~$160–250/mo | Deferred |
| Databento Plus (live L2/L3) | $1,399/mo | Post-revenue (DEC-238) |

---

## Key Active Decisions (Quick Reference)

*Full rationale: `docs/decision-log.md`. Full index: `docs/dec-index.md`.*

**Foundational:** DEC-025 (Event Bus FIFO), DEC-027 (Risk Manager modifications), DEC-028 (strategy statefulness), DEC-029 (Event Bus sole streaming), DEC-032 (Pydantic config), DEC-047 (walk-forward mandatory), DEC-079 (parallel tracks), DEC-082 (Databento primary), DEC-083 (IBKR sole broker), DEC-098 (Claude Opus), DEC-132 (re-validation required).

**Data & Execution:** DEC-088 (Databento threading), DEC-090 (DataSource enum), DEC-094 (BrokerSource enum), DEC-117 (atomic brackets), DEC-237 (no live L2 on Standard), DEC-248 (EQUS.MINI confirmed), DEC-249 (concentration approve-with-modification).

**Frontend:** DEC-099 (in-process API), DEC-102 (JWT auth), DEC-104/215 (chart libraries), DEC-109 (design north star), DEC-149 (VectorBT precompute+vectorize), DEC-169 (7-page architecture), DEC-170 (AI Copilot), DEC-199 (navigation + shortcuts).

**Superseded (do not use):** DEC-031 (IBKR deferral → DEC-083), DEC-089 (XNAS.ITCH → DEC-248), DEC-097 (activation timing → DEC-143/161), DEC-165 (L2 included → DEC-237), DEC-234 (XNAS+XNYS phased → DEC-248).

---

## Workflow

**Two-Claude architecture:** Claude.ai (this instance) handles strategic design, code review, documentation, and decisions. Claude Code handles implementation. Git is the bridge. All significant decisions logged with sequential DEC numbers. Deferred items tracked in CLAUDE.md.

**Sprint methodology:** Sprint spec → session prompts → Claude Code implementation → code review → polish → doc sync. By Sprint 18+, evolved into comprehensive "sprint packages" (spec + prompts + review plans + doc updates in one conversation).

**Review workflow:** Three-tier system — close-out review, Tier 2 implementation review, Tier 3 architectural review in Claude.ai. See `.claude/rules/` for protocols.

---

## Reference Documents

| Document | Purpose |
|----------|---------|
| `01_PROJECT_BIBLE.md` | Source of truth — what and why |
| `project-knowledge.md` | This file (Claude context) |
| `03_ARCHITECTURE.md` | Technical blueprint — how |
| `docs/decision-log.md` | All DEC entries with full rationale |
| `docs/dec-index.md` | Quick-reference DEC index with status |
| `docs/sprint-history.md` | Complete sprint history |
| `docs/process-evolution.md` | Workflow evolution narrative |
| `risk-register.md` | Assumptions and risks |
| `10_PHASE3_SPRINT_PLAN.md` | Active sprint plan + queue |
| `CLAUDE.md` | Claude Code session context |
| `docs/LIVE_OPERATIONS.md` | Live trading procedures (418 lines) |
| `docs/research/ARGUS_Expanded_Roadmap.md` | AI-enhanced platform roadmap |
| `docs/ui/UX_FEATURE_BACKLOG.md` | 35 planned UI features |
| `docs/strategies/STRATEGY_*.md` | Per-strategy spec sheets |

---

## Communication Style

The user prefers thorough, detailed explanations and expects structured outputs ready for copy-paste. He appreciates proactive pushback and concerns. He values clarifying questions before assumptions. He wants the *why* behind every recommendation. He is building this for his family's financial future — treat every decision with the seriousness that implies. Direct, technically precise communication.
