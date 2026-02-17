# ARGUS — Project Knowledge (Claude Context)

> *Paste this into Claude's project instructions. Keep updated as the project evolves. Last updated: Feb 17, 2026.*

---

## What Is Argus

Argus is a fully automated multi-strategy day trading ecosystem with an AI co-captain (Claude), a desktop/mobile Command Center, and multi-asset support. The user is building this to generate income for his family. He can code in Python. He has trading experience but no prior systematic/algorithmic trading system.

## Current Project State

**Phase:** Phase 1 COMPLETE (362 tests, February 16, 2026). Phase 2 in progress.
**Track 1 — Paper Trading Validation:** Running Argus on Alpaca paper trading for 3+ trading days. Validating stability, data integrity, risk compliance, and trade lifecycle correctness. See `08_PAPER_TRADING_GUIDE.md`.
**Track 2 — Phase 2 Build (Backtesting Validation):** Sprints 6, 7, 8, 9 COMPLETE. 542 tests passing. Sprint 10 (Analysis & Parameter Validation Report) in progress — Steps 1–4 complete, Step 5 (write report) pending. See `09_PHASE2_SPRINT_PLAN.md`.
**Next milestone:** Sprint 10 Step 5 (Write Parameter Validation Report). Then Phase 2 is complete → Phase 3 (Live Validation).

## Key Decisions Made (Do Not Relitigate)

- **System name:** Argus
- **Language:** Python 3.11+
- **Brokerages:** Broker-agnostic abstraction layer. Alpaca (primary, free, paper+live) and Interactive Brokers (production scaling). Both implemented from day one.
- **Data:** Alpaca's free market data API for real-time and historical. Data Service abstraction for future swap to Polygon.io or IBKR data.
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

Concept → Exploration (VectorBT) → Validation (Replay Harness + Walk-Forward) → Ecosystem Replay → Paper Trading (20-30 days) → Live Minimum Size (20 days) → Live Full Size → Active Monitoring → Suspended → Retired

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

1. **Core Engine + ORB Strategy** ✅ COMPLETE (Feb 14–16, 2026, 359 tests):
   - Sprint 1: Config system, Event Bus, data models, database, Trade Logger (52 tests)
   - Sprint 2: Broker Abstraction, SimulatedBroker, Risk Manager (112 tests)
   - Sprint 3: BaseStrategy, ORB Breakout, ReplayDataService, Scanner ABC (222 tests)
   - Sprint 4a: AlpacaDataService, AlpacaBroker, Clock injection (282 tests)
   - Sprint 4b: Order Manager, AlpacaScanner (320 tests)
   - Sprint 5: HealthMonitor, system entry point, state reconstruction, structured logging (359 tests)
2. **Backtesting Validation** (IN PROGRESS): Historical data acquisition, Replay Harness, VectorBT parameter sweeps, walk-forward analysis, Parameter Validation Report. Backtrader dropped (DEC-046). See `09_PHASE2_SPRINT_PLAN.md`.
3. **Live Validation**: ORB live at minimum size, compare to backtest expectations. Calendar-bound (20+ trading days). Includes Tier 1 News Integration (economic/earnings calendar as scanner metadata and risk filters).
4. **Orchestrator + Second Strategy**: Orchestrator framework, ORB Scalp, cross-strategy risk management.
5. **Command Center MVP**: Tauri app, real-time dashboard, basic controls.
6. **AI Layer + News Intelligence**: Claude API integration, approval workflow, report generation. Tier 2 news feed ingestion and catalyst classification. Tier 3 AI-powered sentiment analysis via Claude API.
7. **Expand Strategies** (Ongoing): Add strategies one at a time through Incubator Pipeline.
8. **Multi-Asset Expansion** (Future): Crypto via Alpaca, then Forex, then Futures.

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
- [ ] 09_PHASE2_SPRINT_PLAN.md: [status updates needed, or "no changes needed"]
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