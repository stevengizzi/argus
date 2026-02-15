# ARGUS — Project Knowledge (Claude Context)

> *Paste this into Claude's project instructions. Keep updated as the project evolves. Last updated: Feb 15, 2026.*

---

## What Is Argus

Argus is a fully automated multi-strategy day trading ecosystem with an AI co-captain (Claude), a desktop/mobile Command Center, and multi-asset support. The user is building this to generate income for his family. He can code in Python. He has trading experience but no prior systematic/algorithmic trading system.

## Current Project State

**Phase:** Phase 1 COMPLETE. All 5 sprints done (359 tests passing). Ready for paper trading validation.
**Current sprint:** Sprint 5 complete (Health monitoring, system entry point, integration hardening, state reconstruction). Phase 1 finished.
**Next milestone:** Paper trading validation — run system for 3+ trading days on Alpaca paper trading. Then Phase 2 (Backtesting Validation).

## Key Decisions Made (Do Not Relitigate)

- **System name:** Argus
- **Language:** Python 3.11+
- **Brokerages:** Broker-agnostic abstraction layer. Alpaca (primary, free, paper+live) and Interactive Brokers (production scaling). Both implemented from day one.
- **Data:** Alpaca's free market data API for real-time and historical. Data Service abstraction for future swap to Polygon.io or IBKR data.
- **Backtesting:** Three-layer toolkit — VectorBT (fast parameter sweeps), Backtrader (full logic validation), custom Replay Harness (ecosystem-level testing using production code).
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

## Architecture Summary

Three-tier system:
1. **Trading Engine** (Project A, build first): Strategies, Orchestrator, Risk Manager, Data Service, Broker abstraction, Execution layer, Trade Logger, Backtesting toolkit
2. **Command Center** (Project B): Tauri desktop + mobile web, dashboards, human-in-the-loop controls, accounting, reports, Strategy Lab, Learning Journal
3. **AI Layer** (Project C): Claude API integration, approval workflow, report narration, analysis, Claude Code integration

Key components:
- **Strategies** are daily-stateful, session-stateless modular plugins implementing a base interface (state accumulates during market hours, resets between days, reconstructs from DB on restart)
- **Orchestrator** manages capital allocation, strategy activation, performance throttling
- **Risk Manager** gates every order at three levels: strategy, cross-strategy, account
- **Data Service** is the single source of market data, builds candles at multiple timeframes, computes shared indicators (VWAP, ATR, RVOL), exposes pub/sub API to strategies
- **Broker Abstraction** routes orders to correct broker+asset class handler
- **Replay Harness** feeds historical data through production code for ecosystem-level backtesting
- **Shadow System** runs paper trading permanently in parallel with live trading

## Strategy Roster (V1 — US Stocks)

1. **ORB (Opening Range Breakout)** — 9:45–11:30 AM, 5–45 min holds, tiered exit 1R/2R
2. **ORB Scalp** — 9:45–11:30 AM, 10s–5 min holds, quick 0.3–0.5R targets
3. **VWAP Reclaim** — 10:00 AM–12:00 PM, 5–30 min holds, mean-reversion
4. **Afternoon Momentum** — 2:00–3:30 PM, 15–60 min holds, consolidation breakout
5. **Red-to-Green** — 9:45–11:00 AM, 10–45 min holds, gap-down reversal

## Strategy Incubator Pipeline (10 Stages)

Concept → Exploration (VectorBT) → Validation (Backtrader) → Ecosystem Replay → Paper Trading (20-30 days) → Live Minimum Size (20 days) → Live Full Size → Active Monitoring → Suspended → Retired

## Risk Limits (Defaults, Configurable)

- Per-trade risk: 0.5–1% of strategy's allocated capital
- Daily loss limit (account): 3–5%
- Weekly loss limit (account): 5–8%
- Cash reserve: minimum 20% always held
- Max single-stock exposure (all strategies): 5% of account
- Max single-sector exposure: 15% of account
- Circuit breakers are non-overridable

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

## Build Phases

1. **Core Engine + ORB Strategy** (Weeks 1–4): Base interfaces, ORB module, Risk Manager (account level), Alpaca broker adapter, Trade Logger, basic monitoring
   - Sprint 1 COMPLETE: Config system, Event Bus, data models, database (SQLite + aiosqlite), Trade Logger
   - Sprint 2 IN PROGRESS: Broker Abstraction + SimulatedBroker + Risk Manager (account level)
   - Sprint 3 PENDING: BaseStrategy + ORB strategy + Data Service
   - Sprint 4 PENDING: Alpaca Broker adapter + Order Manager
   - Sprint 5 PENDING: Health monitoring + Integration testing
2. **Backtesting Validation** (Weeks 3–6): VectorBT parameter sweeps, Backtrader validation, Replay Harness build
3. **Live Validation** (Weeks 5–10): ORB live at minimum size, compare to backtest
4. **Orchestrator + Second Strategy** (Weeks 8–12): Orchestrator framework, ORB Scalp, cross-strategy risk management
5. **Command Center MVP** (Weeks 10–16): Tauri app, real-time dashboard, basic controls
6. **AI Layer** (Weeks 14–20): Claude API integration, approval workflow, report generation
7. **Expand Strategies** (Ongoing): Add strategies one at a time through Incubator Pipeline
8. **Multi-Asset Expansion** (Future): Crypto via Alpaca, then Forex, then Futures

## Reference Documents

- `01_PROJECT_BIBLE.md` — Source of truth for what and why
- `02_PROJECT_KNOWLEDGE.md` — This file (Claude context)
- `03_ARCHITECTURE.md` — Technical blueprint for how
- `04_STRATEGY_TEMPLATE.md` — Standard template for strategy documentation
- `05_DECISION_LOG.md` — Record of all key decisions with rationale
- `06_RISK_REGISTER.md` — Assumptions and risks being tracked
- `07_PHASE1_SPRINT_PLAN.md` — Canonical Phase 1 build order with sprint status tracking. **Both Claude instances must update this when sprints complete or scope changes.**

## Communication Style Notes

The user prefers thorough, detailed explanations. He appreciates when Claude pushes back or raises concerns proactively. He values being asked clarifying questions before assumptions are made. He wants to understand the *why* behind every recommendation, not just the *what*. He is building this for his family's financial future — treat every design decision with the seriousness that implies.

- **Deferred items:** Tracked in CLAUDE.md under "Deferred Items" section. Surface proactively when trigger conditions are met.

## Documentation Sync Protocol

Argus has six living documents that are the single source of truth. They exist in three places:
1. The git repo (`docs/` folder and `CLAUDE.md`) — authoritative source
2. This Claude project (project instructions + uploaded files) — Claude.ai's copy
3. Claude Code's context (reads from git repo) — Claude Code's copy

Claude (this instance) is responsible for flagging when documents need updating. This is not optional.

### At the End of Every Conversation Where Decisions Are Made

Output a **Docs Sync Checklist** at the end of the response. Format:
```
## Docs Sync Checklist
- [ ] 02_PROJECT_KNOWLEDGE.md (project instructions): [what to update]
- [ ] 01_PROJECT_BIBLE.md: [what to update, or "no changes needed"]
- [ ] 03_ARCHITECTURE.md: [what to update, or "no changes needed"]
- [ ] 05_DECISION_LOG.md: [new entries needed — list them]
- [ ] 06_RISK_REGISTER.md: [new entries needed, or "no changes needed"]
- [ ] 07_PHASE1_SPRINT_PLAN.md: [status updates needed, or "no changes needed"]
- [ ] CLAUDE.md (repo root): [what to update, or "no changes needed"]
```

Only include docs that actually need changes. Skip the checklist entirely if nothing changed (e.g., a pure Q&A conversation with no decisions).

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

GitHub repo is connected to this project via native integration. Click 'Sync now' after pushing doc updates. Project instructions are separate and updated manually at major milestones.