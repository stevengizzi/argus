# ARGUS — Decision Log

> *Version 1.0 | February 2026*
> *This log records every significant design, architecture, and strategy decision made during the Argus project. Its purpose is to prevent relitigating settled decisions and to preserve the rationale behind each choice. If a decision needs to be revisited, update its status to "Superseded" and add a new entry referencing the original.*

---

## How to Use This Document

Each entry follows this format:

| Field | Description |
|-------|-------------|
| **ID** | Sequential identifier (DEC-001, DEC-002, ...) |
| **Date** | When the decision was made |
| **Decision** | What was decided |
| **Alternatives Considered** | What else was on the table |
| **Rationale** | Why this choice was made |
| **Status** | Active / Superseded / Under Review |
| **Superseded By** | If applicable, the ID of the replacement decision |

---

## Decisions

### DEC-001 — System Name
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Name the system "Argus" |
| **Alternatives** | Meridian, Sentinel, Nexus, Aegis |
| **Rationale** | Argus Panoptes (the all-seeing guardian) is the best metaphor for a multi-strategy system that watches markets simultaneously. Clean namespace for code, config, and documentation. |
| **Status** | Active |

---

### DEC-002 — Primary Programming Language
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Python 3.11+ as the primary language for the Trading Engine |
| **Alternatives** | Rust, Go, C++, JavaScript/TypeScript |
| **Rationale** | User's strongest language. Richest ecosystem for trading (alpaca-trade-api, ib_insync, pandas, VectorBT, Backtrader, ta-lib). Async support via asyncio is sufficient for seconds-to-minutes holding periods. Development speed is more valuable than raw execution speed at this scale. |
| **Status** | Active |

---

### DEC-003 — Brokerage Architecture (AMENDED)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 (amended 2026-02-15) |
| **Decision** | Broker-agnostic abstraction layer from day one. Alpaca implemented from day one. Interactive Brokers implemented when needed for production scaling (Phase 3+). |
| **Alternatives** | Alpaca only, IBKR only, single-broker with abstraction added later, both implemented from day one (original decision) |
| **Rationale** | Original rationale (abstraction prevents lock-in) still holds. Amended to defer IBKR *implementation* because the abstraction layer alone achieves the anti-lock-in goal. IBKR adapter complexity (TWS Gateway, auth model, event loop integration) provides no value during development and early live trading, which all use Alpaca. See DEC-031 for full rationale. |
| **Status** | Active (amended) |
| **Supersedes** | Original DEC-003 (2026-02-14) |

---

### DEC-004 — Primary Broker for Phase 1
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Alpaca as the primary broker for development, paper trading, and initial live trading |
| **Alternatives** | Start with IBKR directly |
| **Rationale** | Commission-free. Clean Python SDK. Built-in paper trading. Free real-time and historical data included. WebSocket streaming. Servers in AWS us-east-1 (low latency from target VPS). Lower barrier to getting started. |
| **Status** | Active |

---

### DEC-005 — Market Data Strategy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Use Alpaca's included market data API as primary. Build Data Service abstraction for future swappability. |
| **Alternatives** | Polygon.io ($199/month), Tiingo (~$30/month), IBKR data, multiple sources from day one |
| **Rationale** | Alpaca's data is free, provides real-time WebSocket streaming and historical 1-minute bars. Quality comparison showed near-identical results to Polygon.io. Abstraction allows future swap without touching strategy code. Avoids unnecessary monthly cost during development. |
| **Status** | Active |

---

### DEC-006 — Backtesting Framework
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Three-layer approach: VectorBT (parameter sweeps), Backtrader (full-logic validation), custom Replay Harness (ecosystem testing) |
| **Alternatives** | Single framework only, Zipline, custom-only |
| **Rationale** | Each layer serves a distinct purpose. VectorBT is 10-100x faster for parameter sweeps. Backtrader handles complex event-driven logic. Replay Harness feeds historical data through actual production code, eliminating the classic backtest-to-production gap. |
| **Status** | Active |

---

### DEC-007 — Database Technology
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | SQLite for all persistent storage |
| **Alternatives** | PostgreSQL, MySQL, TimescaleDB, flat files |
| **Rationale** | Zero configuration. Single-file database. Easy backups. Python's sqlite3 is built-in. Sufficient for a single-user system with tens of thousands of trades per year. Migrate to PostgreSQL only if complex analytical queries become a bottleneck. |
| **Status** | Active |

---

### DEC-008 — UI Platform
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Tauri desktop app + responsive web app for mobile. Single React codebase. |
| **Alternatives** | Electron, pure web app, native mobile apps, terminal-only |
| **Rationale** | Tauri provides native desktop feel with Rust backend — far lighter than Electron. React frontend is shared between desktop and mobile web. Mobile web can be installed as PWA. System tray and native menus enhance the desktop experience. |
| **Status** | Active |

---

### DEC-009 — Claude's Role
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Co-captain with full advisory capability and approval-gated action capability. Never autonomous. |
| **Alternatives** | Read-only advisor, fully autonomous, no AI integration |
| **Rationale** | Full advisory + action proposal capability gives Claude maximum value. Approval gating provides safety. Graduated permission system allows trust to build over time. Clean audit trail of all proposals and responses. |
| **Status** | Active |

---

### DEC-010 — Asset Class Priority
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | US Stocks → Crypto (via Alpaca) → Forex → Futures |
| **Alternatives** | Start with crypto (24/7), start with futures (no PDT), multi-asset from day one |
| **Rationale** | US stocks align with user's experience and strategy readiness. All five initial strategies are stock-market strategies. Proving the system with one asset class before expanding reduces risk. Crypto via Alpaca is low-effort expansion (same API). |
| **Status** | Active |

---

### DEC-011 — Trading Direction
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Long-only for V1. Short selling evaluated after long-only ecosystem is proven. |
| **Alternatives** | Long and short from day one |
| **Rationale** | Simplifies initial implementation. Long-only strategies are more straightforward to validate. Reduces risk during the learning phase. Short selling adds complexity to position sizing, risk management, and broker interaction. |
| **Status** | Active |

---

### DEC-012 — ORB Stop Placement
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Stop loss at midpoint of opening range (not the bottom) |
| **Alternatives** | Bottom of range, fixed ATR-based, percentage-based |
| **Rationale** | Tighter risk control. A breakout falling to midpoint has likely failed. Improves R-multiple math. Tradeoff is slightly more false stops, but overall expected value is higher. To be validated via backtesting. |
| **Status** | Active |

---

### DEC-013 — Risk Management Structure
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Three-level risk: strategy level, cross-strategy level, account level |
| **Alternatives** | Account-level only, two levels |
| **Rationale** | Defense in depth. Strategy-level is first-line. Cross-strategy catches concentration risk invisible to individual strategies. Account-level is the hard backstop. A failure at one level is caught by the next. |
| **Status** | Active |

---

### DEC-014 — Deployment Infrastructure
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | AWS EC2 in us-east-1 for live trading. Local machine for development. |
| **Alternatives** | DigitalOcean, Linode, GCP, local-only, dedicated server |
| **Rationale** | us-east-1 is closest to Alpaca servers and NYSE/NASDAQ. t3.medium ($10-40/month) is sufficient. systemd for auto-restart. Local development for tight feedback loop. |
| **Status** | Active |

---

### DEC-015 — Notification Channels
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Push notifications (app), Email (summaries), Telegram/Discord bot (real-time) |
| **Alternatives** | SMS, Slack, single channel only |
| **Rationale** | Multiple channels provide redundancy. Push is fastest for critical alerts. Email for detailed summaries. Telegram/Discord for real-time trade notifications and interactive commands. Configurable routing per alert type. |
| **Status** | Active |

---

### DEC-016 — Capital Growth & Withdrawal Model
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Base Capital / Growth Pool model with configurable thresholds and sweep percentages |
| **Alternatives** | Ad hoc withdrawals, fixed monthly salary, reinvest everything |
| **Rationale** | Formalizes the tension between income needs and compounding. Growth Pool concept makes available-for-withdrawal explicit. Configurable thresholds allow adjustment as system matures. Automatic sweep capability removes temptation of emotional decisions. |
| **Status** | Active |

---

### DEC-017 — Shadow Paper Trading System
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Permanent paper trading shadow system running in parallel with live |
| **Alternatives** | No shadow, periodic paper trading only |
| **Rationale** | Continuous validation of live system behavior. Surfaces execution issues (slippage, partial fills) that would otherwise be invisible. Safe testing ground for parameter changes. Standard practice at professional quant firms. Minimal additional cost. |
| **Status** | Active |

---

### DEC-018 — Strategy Incubator Pipeline
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Formalized 10-stage lifecycle: Concept → Exploration → Validation → Ecosystem Replay → Paper → Live Min → Live Full → Monitoring → Suspended → Retired |
| **Alternatives** | Informal process, fewer stages, backtest-to-live directly |
| **Rationale** | Four distinct validation gates before real money dramatically reduces deployment risk. Minimum-size live stage catches execution issues paper trading can't simulate. Clear entry/exit criteria per stage. Strategy Lab dashboard tracks every strategy's position. |
| **Status** | Active |

---

### DEC-019 — Market Regime Classification V1
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Rules-based classification using SPY vs MAs, VIX, breadth, ROC, VWAP. Five categories: Bullish Trending, Bearish Trending, Range-Bound, High Volatility Event, Crisis. |
| **Alternatives** | ML-based from day one, more indicators, no classification |
| **Rationale** | Simple rules are transparent, debuggable, sufficient for V1. Five indicators capture trend, volatility, and breadth. Running all strategies regardless of regime wastes capital. ML classification designed for V2+ after data collection. |
| **Status** | Active |

---

### DEC-020 — Simulation & Stress Testing
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Historical scenario replay for V1. Monte Carlo simulation designed for V2+. |
| **Alternatives** | No stress testing, Monte Carlo only, only historical |
| **Rationale** | Historical replay answers "would my system have survived known extreme events?" — essential before deploying real capital. Buildable using existing Replay Harness. Monte Carlo requires reliable strategy statistics from live trading data; deferred until those exist. |
| **Status** | Active |

---

### DEC-021 — Learning Journal
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Searchable, taggable Learning Journal as a first-class Command Center feature |
| **Alternatives** | External note-taking app, no formal journal, automatic-only insights |
| **Rationale** | Trade logs tell you what happened. The journal captures why and what to do about it. Both user and Claude entries are stored, linked to trades/strategies/dates. Becomes invaluable institutional memory over time. Prevents repeating mistakes. |
| **Status** | Active |

---

### DEC-022 | Two-Claude Workflow with Git as Bridge
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Strategic work (design, decisions, document drafting, review) happens in the Claude.ai project. Implementation (coding, testing, debugging) happens in Claude Code. The `docs/` folder in the git repo is the shared bridge. Claude.ai syncs via GitHub integration; Claude Code reads from the local filesystem. The user keeps both in sync by committing doc updates and clicking "Sync now." |
| **Rationale** | Claude.ai and Claude Code have completely independent context systems with no automatic cross-communication. Shared documentation in a version-controlled repository is the simplest reliable bridge. Git provides history, diffing, and rollback for free. |
| **Status** | Active |

---

### DEC-023 | Documentation Update Protocol Baked into Both Claude Contexts
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Both Claude instances have explicit documentation update rules in their instructions. Claude.ai outputs a Docs Sync Checklist with copy-paste-ready content at the end of every decision-making conversation. Claude Code performs a docs audit at the end of every significant coding session via `.claude/rules/doc-updates.md`. |
| **Rationale** | AI does not consistently perform behaviors not in its instructions. Making doc hygiene an explicit rule — not a hope — ensures it happens. Checklist entries are formatted to match each document's exact template so the user can copy-paste-commit without reformatting. |
| **Status** | Active |

---

### DEC-024 | GitHub Repo Connected to Claude.ai Project via Native Integration
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | The Argus GitHub repository is connected to the Claude.ai project via Anthropic's native GitHub integration. Selected files/folders synced: `docs/`, `CLAUDE.md`, `config/`. Project instructions (project-knowledge.md text) remain manually maintained separately. |
| **Rationale** | Eliminates manual file re-upload. Both Claudes read from the same git-based source of truth — Claude Code reads from the local filesystem, Claude.ai reads via GitHub sync. Clicking "Sync now" after pushing is the only manual step. Project instructions are a separate text field that doesn't sync from GitHub, but they change infrequently (major milestones only). |
| **Alternatives Considered** | ClaudeSync (third-party Python tool, one-way sync — unnecessary given native integration), manual file upload (tedious, error-prone), syncing entire repo (wasteful — Claude.ai doesn't need source code for strategic conversations) |
| **Status** | Active |

---

### DEC-025 | Event Bus Ordering Guarantees
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | FIFO delivery per subscriber. No global ordering guarantees. No priority queues. Every event carries a monotonic sequence number for debugging and replay. |
| **Alternatives** | Priority queues, global total ordering, external message broker (RabbitMQ, Redis Streams) |
| **Rationale** | In-process asyncio pub/sub at V1 volumes (hundreds of events/second peak) has no realistic ordering issues. FIFO per subscriber is the natural asyncio behavior. Monotonic sequence numbers cost nothing and enable deterministic replay and post-hoc debugging (sort any event log by sequence number to see exact order). Global ordering and priority queues add complexity with no demonstrated need at this scale. Revisit if the system moves to multi-process or distributed architecture. |
| **Status** | Active |

---

### DEC-026 | Trade ID Format
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Use ULIDs (Universally Unique Lexicographically Sortable Identifiers) for all primary keys across all database tables. Use the `python-ulid` library. |
| **Alternatives** | UUIDs (v4), auto-incrementing integers, custom timestamp-based IDs |
| **Rationale** | ULIDs provide global uniqueness (like UUIDs) plus chronological sortability. `SELECT * FROM trades ORDER BY id` returns trades in time order without touching the timestamp column. 26 characters (vs UUID's 36). The timestamp component allows visual inspection of when a record was created from the ID alone. Millisecond precision handles V1 volumes with no collision risk. |
| **Status** | Active |

---

### DEC-027 | Risk Manager Modification Behavior
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Risk Manager uses an "approve-with-modification" model. Permitted modifications: reduce share count (with minimum viable size floor — reject if reduced position yields less than 0.25R potential profit), tighten profit targets. Prohibited modifications: widen stops, change entry price, change side. All modifications logged with rationale in the `OrderApprovedEvent.modifications` field. Trade Logger records both the original signal and the modified execution. |
| **Alternatives** | Reject-only model (signal is all-or-nothing), unconstrained modification |
| **Rationale** | Rejecting outright when a signal is partially valid wastes edge. If ORB identifies a quality setup but buying power only allows 60% of the requested size, taking the smaller trade is usually correct. Prohibiting stop modification preserves the strategy's thesis — stops are set for a reason. The 0.25R floor prevents taking positions too small to matter. Logging both original and modified values enables analysis of modification frequency and impact on performance. |
| **Status** | Active |

---

### DEC-028 | Strategy Statefulness Model
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Strategies follow a "daily-stateful, session-stateless" model. Within a trading day, strategies accumulate state (opening range, trade count, daily P&L, active watchlist). Between trading days, all state is wiped by `reset_daily_state()`. On mid-day restart, strategies reconstruct intraday state from the database (open positions, today's trades). |
| **Alternatives** | Fully stateless (query DB on every decision), fully stateful (persist in-memory state to disk) |
| **Rationale** | ORB must track the opening range as it forms. All strategies must know their trade count and daily P&L for internal risk limits. This is intraday state. Calling strategies "stateless" (as prior docs did) was misleading. "Daily-stateful, session-stateless" precisely describes the reality: state accumulates during market hours, resets at day boundary, and can be reconstructed from the database after a crash. The reconstruction requirement ensures no data loss on restart — the database is the durable source of truth, in-memory state is a performance cache. |
| **Status** | Active |

---

### DEC-029 | Data Delivery Mechanism
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Market data flows exclusively through the Event Bus. The Data Service publishes `CandleEvent`, `TickEvent`, and `IndicatorEvent` to the bus. Strategies and other components subscribe via the Event Bus. The callback-based subscription API (`subscribe_candles`, `subscribe_ticks`) is removed from the `DataService` interface. Synchronous query methods (`get_current_price`, `get_indicator`, `get_historical_candles`) are retained for point-in-time lookups. |
| **Alternatives** | Dual delivery (Event Bus + callbacks), callback-only, direct method calls |
| **Rationale** | Two parallel data paths (Event Bus and callbacks) create confusion about which to use and risk subtle bugs where some consumers get data via one path and others via the other. The Event Bus is the system's communication backbone (per DEC-025 and the Architecture doc). Making it the sole delivery mechanism for streaming data is consistent. Synchronous query methods serve a different purpose (point-in-time lookups for position sizing, indicator checks) and don't duplicate the streaming path. |
| **Status** | Active |

---

### DEC-030 | Order Manager Position Management Model
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Position management is event-driven. The Order Manager subscribes to `TickEvent` for all symbols with open positions and evaluates exit conditions on each tick. A 5-second fallback polling loop handles time-based exits (time stops, inactivity in illiquid stocks). End-of-day flattening is a scheduled task (default 3:50 PM EST, configurable). No per-strategy management interval configuration. |
| **Alternatives** | Fixed polling interval (configurable per strategy), pure polling, pure event-driven with no fallback |
| **Rationale** | Event-driven management naturally adapts to each strategy's speed: ORB Scalp (seconds) gets tick-level management automatically, while ORB (minutes) doesn't waste cycles polling. The 5-second fallback covers edge cases where tick data is sparse (illiquid stocks) or the data feed stalls — time stops and EOD flatten must fire regardless of data availability. EOD flatten as a scheduled task is cleaner than embedding it in the polling loop. This approach handles all five V1 strategies without per-strategy configuration. |
| **Status** | Active |

---

### DEC-031 | IBKR Adapter Phase Deferral
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Phase 1 builds the `Broker` ABC, `SimulatedBroker`, and `AlpacaBroker`. The IBKR adapter is deferred to Phase 3 or later (when production scaling is needed). A comprehensive `Broker` ABC test suite ensures any future adapter is drop-in compatible. |
| **Alternatives** | Implement IBKR adapter in Phase 1 (per original DEC-003) |
| **Rationale** | The broker abstraction layer (built in Phase 1) achieves the anti-lock-in goal of DEC-003 without actually implementing IBKR. The IBKR adapter is meaningfully harder than Alpaca (requires TWS Gateway, different auth model, `ib_insync` event loop integration, different order model). This represents 3–5 days of work providing zero value until production scaling — all Phase 1-3 trading uses Alpaca. A comprehensive test suite against the `Broker` ABC guarantees drop-in compatibility when IBKR is implemented. See amended DEC-003. |
| **Status** | Superseded by DEC-083 |

### DEC-032 | Configuration Validation via Pydantic
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Use Pydantic `BaseModel` (not `BaseSettings`) for all configuration validation. YAML files are loaded via `yaml.safe_load()`, then passed to Pydantic models for type validation, default values, and constraint enforcement. Each config domain has its own model (`SystemConfig`, `RiskConfig`, `BrokerConfig`, `OrchestratorConfig`, `NotificationsConfig`). A top-level `ArgusConfig` composes them. Strategy configs use a `StrategyConfig` base that individual strategies extend. |
| **Alternatives** | Raw dicts with manual validation, dataclasses with manual checks, attrs, Pydantic `BaseSettings` (designed for env vars, not YAML) |
| **Rationale** | Pydantic provides type coercion, range validation (`Field(ge=0, le=1.0)`), nested model support, clear error messages, and IDE autocomplete — all for free. Manual validation would be more code, worse error messages, and no schema documentation. `BaseModel` was chosen over `BaseSettings` because our configs come from YAML files, not environment variables. Missing YAML files fall back to model defaults, so the system always has a valid configuration. |
| **Status** | Active |

### DEC-033 | Event Bus Type-Only Subscription (V1)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Event Bus subscribers register for an event type only (e.g., `CandleEvent`). All filtering (by symbol, timeframe, etc.) happens inside the handler. No predicate-based filtering at the bus level.
| **Alternatives** | Type + predicate subscription `(subscribe(CandleEvent, handler, filter=lambda e: e.symbol in watchlist))`, topic-based routing |
| **Rationale** | At V1 volumes (~50 symbols, hundreds of events/second peak), the overhead of delivering unneeded events to a handler that immediately discards them is negligible. Predicate filtering at the bus level makes debugging harder — you can't easily inspect "what events did this subscriber receive?" because the filtering is invisible. Type-only subscription keeps the Event Bus simple and transparent. Predicate filtering can be added later as a backward-compatible enhancement if profiling shows it's needed. |
| **Status** | Active |

### DEC-034 | Async Database Access via aiosqlite
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Use `aiosqlite` for all database operations. The `DatabaseManager` class owns the connection and provides async methods (`execute`, `fetch_one`, `fetch_all`). The `TradeLogger` is the sole interface for trade-related persistence — other components read and write through it, never accessing the database directly. |
| **Alternatives** | Synchronous `sqlite3` (stdlib), SQLAlchemy async, raw `aiosqlite` without manager abstraction |
| **Rationale** | The main event loop is async. Synchronous `sqlite3` calls block the entire loop — during a fast market open, a database write could delay processing the next tick. `aiosqlite` runs SQLite operations in a thread pool, keeping the event loop responsive. A `DatabaseManager` abstraction centralizes connection management, schema initialization, and provides a clean async interface. The `TradeLogger` as sole persistence interface prevents scattered database access and gives a single place to manage queries, migrations, and connection lifecycle. SQLAlchemy was rejected as unnecessary overhead for a single-user SQLite system. |
| **Status** | Active |

---

### DEC-035 | Sprint 2 Micro-Decisions
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Five implementation micro-decisions for Sprint 2: (1) Weekly loss limit uses calendar week (Mon–Fri reset), not rolling 5-day. (2) Circuit breaker internally enforced by Risk Manager via `_circuit_breaker_active` flag — auto-rejects all signals until `reset_daily_state()`. (3) SimulatedBroker has `simulate_price_update(symbol, price)` for testing bracket order stop/target triggers. (4) PDT $25K threshold stored in config (`pdt.threshold_balance`) — regulatory value but respects no-hardcode rule. (5) Risk Manager queries Broker for account state (source of truth); maintains in-memory tracking only for daily/weekly P&L and PDT counts via EventBus subscription. |
| **Alternatives** | (1) Rolling 5-day window (more complex, marginal benefit). (2) External enforcement by Orchestrator (doesn't exist yet). (3) Manual test setup per test (tedious). (4) Hardcode in code (violates architectural rules). (5) Mirror all state internally (stale data risk). |
| **Rationale** | Each choice optimizes for simplicity, correctness, and consistency with existing architectural decisions (DEC-027, DEC-028, DEC-032). |
| **Status** | Active |

---

### DEC-036 | SimulatedBroker Has No Margin Model
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | SimulatedBroker sets `buying_power = cash` (no margin). The Risk Manager's cash reserve check (step 5) and buying power check (step 6) currently produce equivalent results. These will diverge when AlpacaBroker introduces margin in Sprint 4. |
| **Alternatives** | Simulate margin in SimulatedBroker |
| **Rationale** | Margin simulation adds complexity with no testing value until real margin data is available. The two-step check structure is correct; only the input data differs between simulated and real brokers. |
| **Status** | Active |

---

### DEC-037 | Cash Reserve Uses Start-of-Day Equity
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | The Risk Manager's cash reserve is calculated as `start_of_day_equity * cash_reserve_pct`. The `_start_of_day_equity` value is snapshotted during `reset_daily_state()` (called by the Orchestrator pre-market). It does not change during the trading day. |
| **Alternatives** | (a) Use live equity (includes unrealized P&L — creates perverse incentive where drawdowns lower the reserve threshold, allowing more risk). (c) Use high water mark (ratchets up permanently — overly conservative, one good day raises the floor forever). |
| **Rationale** | Start-of-day equity is stable throughout the session, immune to unrealized P&L swings, and resets naturally each morning. Avoids the perverse dynamic of live equity while not being permanently ratcheted like high water mark. |
| **Status** | Active |

---

### DEC-038 | Sprint 3 Micro-Decisions
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Six implementation decisions for Sprint 3: (1) Scanner architecture: ABC + StaticScanner; real AlpacaScanner deferred to Sprint 4. (2) Data Service timeframes: multi-timeframe framework built, only 1m implemented in Sprint 3. (3) Indicator computation: inside Data Service, published as IndicatorEvent on the Event Bus. (4) ORB opening range tracking: internal to the strategy as daily state. (5) ReplayDataService data format: Parquet only. (6) ORB entry order: market order with chase protection pre-entry filter (skip if >0.5% past breakout). (7) Breakout confirmation: candle must close above OR high, breakout candle volume > 1.5x average of OR formation candles, price above VWAP. |
| **Rationale** | (1) Testable interface without requiring live data; StaticScanner supports replay/backtest. (2) Framework-first avoids rework; 1m is all ORB needs. (3) Centralized computation avoids duplicate work across strategies. (4) Opening range is ORB-specific, not a shared indicator. (5) Parquet is typed, compact, standard in quant. (6) Market orders guarantee fills; chase filter handles slippage risk pre-entry. (7) Close-based confirmation avoids false signals from wicks; volume and VWAP provide conviction. |
| **Status** | Active |

---

### DEC-039 | Sprint 4a Micro-Decisions
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Sprint 4a implementation decisions (MD-4a-1 through MD-4a-6 from spec), plus: MD-4a-7: AlpacaDataService uses IndicatorState dataclass (matching ReplayDataService pattern) instead of separate IndicatorEngine class. |
| **Rationale** | MD-4a-1: Dual stream (bars + trades) provides reliable candles plus real-time price cache. MD-4a-2: Exponential backoff with jitter matches Architecture doc. MD-4a-3: alpaca-py is the current official SDK. MD-4a-4: Direct async integration via _run_forever() on existing event loop. MD-4a-5: Clock injection scoped to Risk Manager + BaseStrategy. MD-4a-6: Single T1 target for bracket orders (Alpaca limitation). MD-4a-7: Consistent indicator pattern across DataService implementations. |
| **Status** | Active |

---

### DEC-040 | Order Manager Stop Management — Cancel and Resubmit
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | When T1 fills and stop needs to move to breakeven, cancel the old stop order and submit a new one. Do not use broker modify_order(). |
| **Rationale** | modify_order on Alpaca replaces the entire order. If the replace fails mid-flight, position could briefly have no stop protection with no detection mechanism. Cancel-then-submit is explicit: failure to submit new stop is immediately detectable and triggers emergency flatten. Brief window between cancel and resubmit is acceptable because Order Manager also monitors ticks. |
| **Alternatives Rejected** | Modify-in-place via broker.modify_order() — risk of silent failure leaving position unprotected. |
| **Status** | Active |

---

### DEC-041 | EOD Flatten Scheduling — Fallback Poll
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | EOD flatten time check piggybacks on the 5-second fallback poll loop. No APScheduler dependency. |
| **Rationale** | Fallback poll already runs every 5 seconds. Adding clock.now() >= eod_flatten_time check is trivial. A _flattened_today flag prevents re-triggering. APScheduler can be introduced in Sprint 5+ if needed. |
| **Alternatives Rejected** | APScheduler — adds dependency for a single scheduled task. |
| **Status** | Active |

---

### DEC-042 | TradeLogger Integration — Direct Call from Order Manager
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Order Manager calls TradeLogger directly when a position fully closes. TradeLogger is an optional constructor dependency (None in tests). PositionClosedEvent is still published for other subscribers. |
| **Rationale** | Order Manager has complete trade data at close time (entry price, exit price, shares, P&L, hold duration, exit reason). Direct call is simpler than event-driven persistence and avoids race conditions. |
| **Alternatives Rejected** | Event-driven: publish PositionClosedEvent and let a listener handle persistence — adds indirection without benefit at this stage. |
| **Status** | Active |

---

### DEC-043 | AlpacaScanner Universe — Static Config
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Scanner universe is a fixed list of symbols in config/scanner.yaml. No dynamic fetching. |
| **Rationale** | A curated list of 20-50 liquid stocks is sufficient for ORB. Dynamic universe adds complexity (API failures at startup, rate limits, mid-day changes) for no V1 benefit. |
| **Alternatives Rejected** | Dynamic: fetch top N by volume from Alpaca assets endpoint — fragile at startup, rate limit risk. |
| **Status** | Active |

---

### DEC-044 | Exit Rules Delivery — Prices from Signal, Time/Trail from Config
| Field | Value |
|-------|-------|
| **Date** | 2026-02-15 |
| **Decision** | Order Manager extracts stop_price and target_prices from SignalEvent (via OrderApprovedEvent). Time-based rules (max_position_duration_minutes) and trailing stop settings come from OrderManagerConfig. All positions share the same time/trail config. |
| **Rationale** | SignalEvent already carries stop_price and target_prices. Adding ExitRules to the frozen dataclass would require modifying the event model. Per-strategy exit rule customization is deferred to Phase 2+. |
| **Alternatives Rejected** | Embed full ExitRules in SignalEvent — requires modifying frozen dataclass and all producers. Query strategy by ID — couples Order Manager to strategy instances. |
| **Status** | Active |

---

### DEC-045 | Sprint 5 Micro-Decisions
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Six implementation-level decisions for Sprint 5: (1) External monitoring via generic webhook with Healthchecks.io as default target (MD-5-1). (2) Critical alerts via webhook POST — Discord webhook for paper trading phase (MD-5-2). (3) Strategy state reconstruction on mid-day restart — fetch today's historical 1m bars from Alpaca REST, replay through strategy; if fetch fails, strategy sits out the day (MD-5-3). (4) Order Manager reconstruction — query broker for open positions and orders at startup, rebuild ManagedPosition objects, resume management (MD-5-4). (5) System health status stored in-memory only — ephemeral by nature, logged for post-hoc analysis (MD-5-5). (6) Procedural `main()` entry point — single `async def main()` with explicit component wiring, no DI container (MD-5-6). |
| **Alternatives** | MD-5-1: Uptime Kuma (self-hosted), custom endpoint. MD-5-2: Logging only, console only. MD-5-3: Skip-day only, hybrid. MD-5-4: Emergency flatten orphaned positions, skip reconstruction. MD-5-5: SQLite table. MD-5-6: DI container. |
| **Rationale** | All decisions optimize for simplicity and minimal new dependencies while meeting Sprint 5's operational requirements. Webhook pattern is reusable across heartbeat and alerts with zero infrastructure. Procedural main is readable, debuggable, and sufficient for a single-strategy single-user system. In-memory health avoids unnecessary persistence for inherently ephemeral data. Broker-based reconstruction enables the <5 minute recovery target. |
| **Status** | Active |

---

### DEC-046 | Backtrader Removal from Phase 2
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Drop Backtrader from the backtesting toolkit. Phase 2 uses only VectorBT (fast parameter sweeps) and the Replay Harness (full-fidelity production code replay). |
| **Alternatives** | Keep all three layers as originally planned (DEC-006/DEC-038 backtesting section). |
| **Rationale** | The Replay Harness runs actual production code (Event Bus, Strategy, Risk Manager, Order Manager) with FixedClock injection — zero translation gap between backtest and live. VectorBT covers fast parameter exploration. Backtrader would require reimplementing strategy logic as a Backtrader Strategy subclass, creating a parallel implementation that could diverge from production. The engineering effort provides no unique value. If the Replay Harness proves too slow for iterative work, Backtrader can be reconsidered (tracked as DEF-006). |
| **Supersedes** | Amends DEC-006 (Three-layer → Two-layer) |
| **Status** | Active |

---

### DEC-047 | Walk-Forward Validation Requirement
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | All parameter optimization in Phase 2 must include walk-forward validation. Minimum 70/30 in-sample/out-of-sample split. Walk-forward efficiency (OOS return / IS return) must be reported for every parameter set. Parameters with walk-forward efficiency below 0.3 are flagged as overfit. |
| **Alternatives** | Simple train/test split, no formal overfitting check, rely on paper trading as the out-of-sample test. |
| **Rationale** | Overfitting is the single biggest risk in backtesting. A strategy that looks amazing on historical data but fails live is worse than useless — it creates false confidence. Walk-forward analysis is the industry standard defense. Making it non-negotiable prevents the temptation to skip it when results "look good enough." |
| **Status** | Active |

---

### DEC-048 | Parquet File Granularity
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | One Parquet file per symbol per month. Path: `data/historical/1m/{SYMBOL}/{SYMBOL}_{YYYY}-{MM}.parquet` |
| **Rationale** | Small files (~300–500 KB), trivial resume on interrupted downloads, aligns with walk-forward monthly boundaries, efficient selective loading for date range queries. |
| **Alternatives** | Per-quarter (fewer files but harder resume), per-year (simpler but loads too much for partial ranges). |
| **Status** | Active |

---

### DEC-049 | Historical Data Time Zone Storage
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Store all historical bar timestamps in UTC. Convert to ET at read time in consumers. |
| **Rationale** | UTC is unambiguous (no DST transitions), matches Alpaca API output, matches existing ReplayDataService expectation (`timestamp: datetime (UTC)` in Sprint 3 spec), future-proof for non-US assets. |
| **Alternatives** | Store in ET (simpler for strategy logic but introduces DST ambiguity and diverges from existing code). |
| **Status** | Active |

---

### DEC-050 | Split-Adjusted Prices for Backtesting
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Always use `adjustment=Adjustment.SPLIT` when fetching historical bars. No dividend adjustment. |
| **Rationale** | Day trading strategies don't hold overnight, so dividends don't affect P&L. Split adjustment is essential to avoid phantom price jumps. Adjustment type recorded in manifest for traceability. |
| **Alternatives** | `all` (split + dividend — unnecessary for intraday), `raw` (would break any backtest spanning a split). |
| **Status** | Active |

---

### DEC-051 | Alpaca Free Tier Rate Limit Handling
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Throttle to 150 requests/minute (vs 200 limit). Sliding window rate limiter. Exponential backoff retry on 429. No overnight batching needed — full download completes in ~2–3 minutes. |
| **Rationale** | 30 symbols × 12 months = 360 requests, each returning ~8,190 bars (under 10,000 limit). Leaving 25% headroom prevents hitting the hard limit. Retry logic is a safety net, not expected to fire. |
| **Alternatives** | Paid plan at $99/month for 10,000 req/min (unnecessary for this volume). |
| **Status** | Active |

---

### DEC-052 | Scanner Simulation via Gap Computation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Replay Harness simulates pre-market scanning by computing gap_pct from previous day's close to current day's 9:30 open. Applies same min_gap_pct and price filters as live scanner config. Falls back to all symbols if gap filter produces zero candidates. Price filters are always applied, even in fallback mode. |
| **Rationale** | No pre-market data available in IEX feed (DEF-007). Gap computation from regular hours data captures overnight moves including pre-market activity reflected in the open. Fallback prevents wasting trading days on zero-candidate scenarios. The 28-symbol universe is already curated for liquidity, reducing the importance of volume-based filtering. |
| **Alternatives** | (a) Static watchlist every day — unrealistic. (b) Feed all symbols always — doesn't test scanner interaction. (c) Download pre-market data — costs money, deferred. |
| **Status** | Active |

---

### DEC-053 | Synthetic Tick Generation from Bar OHLC
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Generate 4 synthetic ticks per 1m bar: Open, Low, High, Close for bullish bars; Open, High, Low, Close for bearish bars. This "worst-case for longs" ordering tests stops before targets on bullish bars, producing conservative results. |
| **Rationale** | The Replay Harness must run the actual Order Manager code (tick-driven exits), which requires TickEvents. Synthetic ticks are an approximation but exercise the real code path. Option (b) — a simplified bar-close evaluator — would create a parallel implementation that could diverge from production. Known limitation: real intra-bar paths are more complex, and the 4-tick model may miss scenarios where both stop and target are hit within one bar. |
| **Alternatives** | (b) Simplified replay-mode Order Manager evaluating on bar close only. (c) Random walk simulation within OHLC bounds — more complex, marginal benefit. |
| **Status** | Active |

---

### DEC-054 | Fixed Slippage Model for V1 Backtesting
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | $0.01/share fixed slippage for all backtest fills. Configured via `BacktestConfig.slippage_per_share`. |
| **Rationale** | Simple, conservative, configurable. At 100 shares per trade and 2 fills per round trip, this adds $2 drag per trade — meaningful over hundreds of trades. Can be refined in Sprint 9 after comparing backtest to paper trading results. Volume-dependent slippage adds complexity with no calibration data yet. |
| **Alternatives** | (b) Percentage-based (0.05%). (c) Volume-dependent. (d) No slippage. |
| **Status** | Active |

---

### DEC-055 | BacktestDataService (Step-Driven DataService)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | New BacktestDataService implements DataService ABC but is driven step-by-step via `feed_bar()` and `publish_tick()` methods. Does not reuse ReplayDataService's `start()` method (which runs autonomously). Shares indicator computation logic with ReplayDataService via the IndicatorState dataclass. |
| **Rationale** | The Replay Harness needs fine-grained control over clock advancement, event ordering, and daily lifecycle that ReplayDataService's autonomous iteration doesn't provide. The strategy needs a DataService for `get_indicator()` / `get_current_price()` lookups. BacktestDataService satisfies both requirements. Indicator logic is shared (not duplicated) to ensure identical computation across all DataService implementations. |
| **Alternatives** | (a) Modify ReplayDataService to support step mode — invasive, breaks existing tests. (b) Harness publishes events directly without a DataService — strategy can't call `get_indicator()`. |
| **Status** | Active |

---

### DEC-056 | Backtest Database Naming Convention
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Backtest output databases stored at `data/backtest_runs/{strategy}_{start}_{end}_{timestamp}.db`. Example: `orb_breakout_20250601_20251231_20260216_143022.db`. Directory is gitignored. |
| **Rationale** | Strategy name and date range in filename enables easy identification and filtering. Run timestamp ensures uniqueness across repeated runs. Same schema as production database allows reuse of all SQL queries and TradeLogger methods. |
| **Alternatives** | (a) `run_YYYYMMDD_HHMMSS.db` — less informative filename. |
| **Status** | Active |

---

### DEC-057 | VectorBT Open-Source for Parameter Sweeps
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Use open-source `vectorbt` package for Sprint 8 parameter sweeps. If compatibility issues arise with current NumPy/Pandas versions, fall back to pure NumPy/Pandas vectorized implementation. VectorBT Pro not needed. |
| **Rationale** | Open-source VectorBT provides `Portfolio.from_signals()` which handles combinatorial parameter grids and portfolio statistics. The ORB sweep logic is simple enough (~100 lines of NumPy) to replicate without the framework if needed. Avoiding a paid dependency for functionality we may outgrow. |
| **Alternatives** | (a) VectorBT Pro ($) — unnecessary features. (b) Pure NumPy from the start — viable but loses VectorBT's built-in stats and grid handling. |
| **Status** | Active |

---

### DEC-058 | VectorBT Gap Scan Pre-Filter
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Pre-compute qualifying trading days per symbol using gap_pct (prev close → day open) before parameter sweeps. Same logic as ScannerSimulator. min_gap_pct is a swept parameter. Non-qualifying days masked out of sweep entirely. |
| **Rationale** | Mirrors production scanner behavior. Pre-filtering avoids evaluating 18,000 parameter combos on days the strategy would never trade, improving sweep performance. Sweeping min_gap_pct as a parameter tests whether the gap threshold itself is sensitive. |
| **Alternatives** | (a) Run all days regardless of gap — unrealistic, inflates no-trade days. (b) Fixed gap threshold — misses the sensitivity question. |
| **Status** | Active |

---

### DEC-059 | Per-Symbol VectorBT Sweeps with Aggregation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Run parameter sweeps independently per symbol. Store per-symbol results as Parquet. Aggregate across symbols for summary metrics. Portfolio-level sweeps deferred until Orchestrator exists (Phase 4). |
| **Rationale** | Per-symbol sweeps isolate strategy logic performance from portfolio construction decisions (capital allocation, concurrent position limits) that belong to the Orchestrator. Cross-symbol aggregation (average Sharpe, parameter rank stability) identifies parameters that work broadly vs those that only work on specific symbols. |
| **Alternatives** | (a) Portfolio-level sweep with capital allocation — premature without Orchestrator. (b) Single combined sweep across all symbols — obscures per-symbol behavior. |
| **Status** | Active |

---

### DEC-060 | Dual Visualization for Parameter Sweeps
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Generate both static (matplotlib + seaborn, PNG) and interactive (plotly, HTML) heatmaps from sweep results. Static for quick review and documentation. Interactive for deep exploration and reuse in Sprint 9 report generator. |
| **Rationale** | Static PNGs are easy to embed in markdown reports and commit to git. Interactive HTML enables zooming, hovering for exact values, and parameter filtering — essential for exploring 18,000+ combinations. Building both from the same results DataFrame is trivial. Interactive files become building blocks for Sprint 9's report generator. |
| **Alternatives** | (a) Static only — insufficient for exploration. (b) Interactive only — harder to embed in documentation. |
| **Status** | Active |

---

### DEC-061 | Strategy Timezone Conversion at Consumer
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | All strategy time comparisons must convert UTC timestamps to Eastern Time before comparing against ET constants. Conversion happens in the strategy (consumer), not in the data layer. `_get_candle_time()` uses `candle.timestamp.astimezone(ET).time()`. Module-level `ET = ZoneInfo("America/New_York")` constant. |
| **Rationale** | DEC-049 established UTC storage. The bug was the strategy extracting `.time()` from UTC timestamps and comparing against ET constants (9:30, 9:45, etc.), causing the opening range to never form. This affected both backtest and live trading. Fix follows the DEC-049 principle: store UTC, convert at read time in consumers. Codebase audit confirmed the bug was isolated to OrbBreakoutStrategy — other components (OrderManager, main.py, AlpacaDataService) already converted correctly. |
| **Scope** | OrbBreakoutStrategy `_get_candle_time()` method. 8 regression tests added including DST edge case. |
| **Status** | Active |

---

### DEC-062 | max_range_atr_ratio Added to VectorBT Sweep
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Add `max_range_atr_ratio` as 6th sweep parameter with values [2.0, 3.0, 4.0, 5.0, 8.0, 999.0]. Total combinations increase from 3,000 to 18,000 per symbol. |
| **Rationale** | 7-month harness validation showed 98.5% OR rejection rate at default threshold (~2.0). Relaxing to 5.0 increased trades from 5 to 59 (12x). This is the dominant parameter for trade volume and must be swept to find the robustness/volume tradeoff. 999.0 effectively disables the filter as a baseline. |
| **Alternatives** | (a) Keep original 5-parameter grid — misses the most impactful parameter. (b) Remove the filter entirely — loses the ability to measure its effect. |
| **Status** | Active |

---

### DEC-063 | VectorBT Fallback to Pure NumPy/Pandas
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Implemented Sprint 8 parameter sweeps using pure NumPy/Pandas vectorized operations instead of VectorBT. VectorBT had numba/coverage compatibility issues at install time. Plotly installed successfully for interactive heatmaps. |
| **Rationale** | VectorBT's numba dependency failed with `coverage.types` AttributeError. Per DEC-057's fallback clause, proceeded with pure NumPy/Pandas implementation. The ORB sweep logic is simple (~400 lines) and the fallback provides identical functionality: entry/exit simulation, metrics computation (Sharpe, drawdown, profit factor), and per-combination results. Existing metrics.py functions (`compute_sharpe_ratio`, `compute_max_drawdown`) provided reference implementations. |
| **Impact** | No functional impact. Sweep performance is sufficient (seconds to minutes per symbol for 18K combinations). If VectorBT is needed for future, more complex strategies, can revisit after resolving numba/coverage version conflict. |
| **Status** | Active |

---

### DEC-064 | VectorBT ATR Filter Bug Fix
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Restructured `run_single_symbol_sweep()` to pre-compute entries per `(or_minutes, day)` outside the `max_range_atr` loop, with ATR ratio filtering applied at runtime inside the loop. Added `or_range` and `atr` fields to `EntryInfo` TypedDict. |
| **Bug Description** | The original implementation appeared to filter `valid_or` by `max_range_atr_ratio` before computing entries, but values 2.0-8.0 produced identical trade counts. The restructure ensures filtering logic is explicit and correct: entries are computed once per (or_min, day), then filtered by `or_range / atr <= max_range_atr` for each threshold. |
| **Validation** | Post-fix analysis revealed all OR range / ATR ratios in the data are below 2.0 (max 1.74 across 945 days, 7 symbols). This explains why 2.0-8.0 produce identical results — all days pass. The only differentiation is between <999.0 (requires valid ATR, excludes ~7% NaN days) and 999.0 (includes NaN days). Consider adding lower thresholds (0.5, 1.0, 1.5) in future sweeps for meaningful ATR ratio differentiation. |
| **Files Changed** | `argus/backtest/vectorbt_orb.py` — `EntryInfo` TypedDict, `_precompute_entries_for_day()`, `run_single_symbol_sweep()` |
| **Status** | Active |

---

### DEC-065 | ATR Sweep Threshold Adjustment
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Changed `max_range_atr_list` default in `SweepConfig` from `[2.0, 3.0, 4.0, 5.0, 8.0, 999.0]` to `[0.3, 0.5, 0.75, 1.0, 1.5, 999.0]`. |
| **Rationale** | Post-fix data analysis (DEC-064) revealed all OR range / ATR ratios in the 29-symbol dataset are below 2.0 (max 1.74, mean 0.41). Old thresholds 2.0–8.0 produced 5 identical trade counts — wasting 5/6 of the ATR dimension. New thresholds produce a clear gradient: 0.3 = 25% of baseline trades, 0.5 = 65%, 0.75 = 84%, 1.0 = 89%, 1.5 = 92%, 999.0 = 100%. This is critical for Sprint 9 walk-forward analysis — identical parameter values would produce artificially inflated robustness scores. |
| **Alternatives** | (a) Keep old thresholds and add lower ones, expanding the grid beyond 6 values — increases sweep time. (b) Remove ATR filtering from sweep — loses ability to measure its effect. |
| **Impact** | 522,000 combinations, 53-second full sweep. No test changes needed (tests use explicit overrides, not defaults). |
| **Status** | Active |

---

### DEC-066 | Walk-Forward Optimization Metric
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Use Sharpe ratio with a configurable minimum trade count floor (default 20) as the walk-forward in-sample optimization metric. Parameter sets producing fewer than `min_trades` in the IS window are disqualified regardless of Sharpe. |
| **Rationale** | Pure Sharpe can be gamed by parameter sets that trade very rarely but win when they do (VectorBT sweep showed as few as 5 trades with tight filters). A hard floor is simpler and more transparent than a composite score. |
| **Alternatives** | (a) Pure Sharpe without floor — risks selecting rare-but-lucky params. (b) Composite score (`sharpe * min(1.0, trade_count / min_trades)`) — smoothly penalizes low counts but less transparent. (c) Profit factor — doesn't balance return and risk. |
| **Status** | Active |

---

### DEC-067 | Report Format: HTML Only
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Generate HTML-only reports in Sprint 9. PDF export deferred. |
| **Rationale** | HTML is easier to generate, supports interactive Plotly charts with hover tooltips, and is sufficient for personal use. PDF adds a dependency (weasyprint or headless Chrome) with no unique value at this stage. |
| **Status** | Active |

---

### DEC-068 | Report Chart Library: Plotly Primary
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Use Plotly as primary chart library for report generation, matplotlib as fallback. Consistent with Sprint 8's dual-output pattern. |
| **Rationale** | Plotly provides interactive hover tooltips on equity curves and trade markers, which are valuable for manual inspection. Already installed from Sprint 8. |
| **Status** | Active |

---

### DEC-069 | Cross-Validation Implementation (DEF-009)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Implement `cross_validate_single_symbol()` in walk_forward.py. Compare VectorBT trade count vs Replay Harness trade count for identical parameters on one symbol. VectorBT >= Replay = PASS (VectorBT has fewer filters, so should produce equal or more trades). |
| **Rationale** | VectorBT uses simplified ORB logic (no VWAP, no volume filter, no T1/T2 split) for speed. It should produce more trades than the full Replay Harness. If VectorBT produces fewer trades, something is wrong with the vectorized implementation. |
| **Status** | Active |

---

### DEC-070 | Legacy Slow Function Removal (DEF-010)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-16 |
| **Decision** | Remove `_simulate_trades_for_day_slow()` from vectorbt_orb.py (~115 lines). Update tests to use a wrapper function that calls the vectorized `_precompute_entries_for_day()` and `_find_exit_vectorized()` functions. |
| **Rationale** | The legacy slow-path was kept during Sprint 8 vectorization for diff-testing. Now that Sprint 9 walk-forward analysis validates the vectorized path produces correct results, the slow path is dead code. The test wrapper maintains backward compatibility with existing unit tests while using the production vectorized code. |
| **Status** | Active |

---

### DEC-071 | News & Catalyst Intelligence — Three-Tier Architecture
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | Implement News & Catalyst Intelligence as a three-tier system: Tier 1 (economic/earnings calendar — structured data, Phase 3), Tier 2 (news feed ingestion + keyword classification, Phase 6), Tier 3 (AI-powered sentiment via Claude API, Phase 6+). Tier 1 integrates as scanner metadata and Risk Manager event-day filters. Tiers 2–3 enrich scanner results with catalyst type, feed the Learning Journal, and provide confidence modifiers to the Orchestrator. News does not generate independent trade signals in V1. |
| **Alternatives** | (a) Build all tiers at once in a dedicated phase — too much scope, delays validation of simpler tiers. (b) Skip entirely and rely purely on price action — leaves money on the table defensively (avoiding bad setups) and offensively (catalyst quality assessment). (c) Third-party sentiment product (e.g., MarketPsych, Sentifi) — expensive, black box, less integration flexibility. |
| **Rationale** | Gap stocks gap because of news. Understanding the catalyst type improves trade quality assessment (earnings gap vs. dilutive offering gap have very different follow-through profiles). Tier 1 is nearly free and provides immediate defensive value (don't trade into earnings, reduce size during FOMC). Tiers 2–3 build incrementally on proven Tier 1 value. SEC EDGAR filings (8-K, Form 4, 13F) are free, structured, and high-value — prioritized within Tier 2. Pre-market latency requirements are relaxed (overnight news, not millisecond), making implementation tractable. |
| **Status** | Active |

---

### DEC-072 | Walk-Forward Fixed-Params Mode
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | Added fixed-params walk-forward mode to `walk_forward.py`. This evaluates specific parameter sets across walk-forward windows without IS re-optimization, complementing the existing optimizer-driven mode. |
| **Rationale** | The standard walk-forward flow optimizes parameters in each IS window. For Sprint 10 Step 3, we needed to test whether specific parameter sets (from the VectorBT sweep) generalize OOS — a different question than "does the optimizer find good params." Fixed-params mode answers "do THESE params hold forward?" |
| **Status** | Active |

---

### DEC-073 | Sprint 10 Walk-Forward Results — Scenario C (Inconclusive)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | Walk-forward validation produced inconclusive results (Scenario C per Sprint 10 spec). No candidate achieved WFE ≥ 0.3. Tight-filter candidates (A–C) produced only 2 OOS trades (insufficient for evaluation). Relaxed candidate (D) showed classic overfitting (IS Sharpe +3.49 → OOS Sharpe -7.24). Contributing factors: only 11 months of data yielding 3 walk-forward windows (industry standard is 8–12+), and a cross-validation mismatch between VectorBT and Replay Harness trade counts. |
| **Rationale** | Per DEC-047, WFE > 0.3 is required. This threshold was not met. However, the result is inconclusive rather than definitively negative — the data quantity is insufficient for the tight-filter configurations that showed promise in the full-period sweep. Paper trading provides the forward-looking validation that backtesting cannot. |
| **Implications** | (1) Do not abandon ORB strategy based solely on this result. (2) Investigate cross-validation mismatch before finalizing parameter recommendations. (3) Paper trading validation becomes the primary evidence for/against the strategy. (4) Consider acquiring more historical data (2–3 years) for future walk-forward analysis. |
| **Status** | Active |

---

### DEC-074 | Cross-Validation Mismatch — RESOLVED
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | Cross-validation issues investigated and resolved. Three bugs fixed: (1) CLI only exposed 2 of 6 params; (2) `cross_validate_single_symbol()` used `.get()` with defaults; (3) Replay Harness loaded ALL symbols, not just the target. |
| **Root Causes** | (a) CLI hardcoded `stop_buffer_pct=0.0`, `max_hold_minutes=60`, `min_gap_pct=2.0`, `max_range_atr_ratio=999.0`. (b) VectorBT params used `.get()` with fallback defaults. (c) `BacktestConfig` lacked `symbols` field, causing 29-symbol vs 1-symbol comparison. |
| **Fixes Applied** | (a) Added 4 CLI args (`--stop-buffer`, `--max-hold`, `--min-gap`, `--max-atr`). (b) Removed `.get()` defaults; requires all 6 params explicitly. (c) Added `symbols` to `BacktestConfig`; `ReplayHarness._load_data()` now filters. |
| **Results After Fix** | Candidate A params (or=5, target_r=2.0, max_atr=0.5): VectorBT 17, Replay 0. **PASS** (VectorBT ≥ Replay). With max_atr=999.0: VectorBT 21, Replay 39. This is a legitimate FAIL indicating VectorBT entry detection is more restrictive than expected — a known architectural difference, not a parameter mismatch bug. |
| **Known ATR Divergence** | VectorBT uses daily ATR; BacktestDataService uses 1m ATR with Wilder smoothing. Range/ATR ratios are ~5-10x higher in Replay Harness, causing more rejections with tight filters. This is documented, not a bug requiring code changes. |
| **Walk-Forward Impact** | `validate_out_of_sample` already passed params correctly. Symbol filter fix now ensures OOS validation respects `WalkForwardConfig.symbols`. |
| **Status** | Resolved — 542 tests passing |

---

### DEC-075 | Disable max_range_atr_ratio for Phase 3
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | Set `max_range_atr_ratio=999.0` (effectively disabled) for Phase 3 live validation. Do not build daily ATR infrastructure until paper trading demonstrates the filter is needed. |
| **Rationale** | The production ATR is computed from 1-minute bars (Wilder smoothing), producing range/ATR ratios 5–10x higher than VectorBT's daily-bar ATR. VectorBT sweep thresholds (0.3–1.5) are meaningless in production-space. The "correct" fix is adding a daily-scale ATR indicator to the production DataService, but the ATR filter's value is unproven — the sweep showed `opening_range_minutes` and `min_gap_pct` are the dominant parameters. Building infrastructure for an unvalidated filter is premature. Paper trading will reveal whether wide-range setups are a consistent losing pattern. If so, add daily ATR indicator with empirical calibration data. If not, drop the parameter entirely. |
| **Alternatives Rejected** | (1) Calibrate ATR threshold empirically in Replay-space — still building on a semantically wrong indicator (1-minute ATR vs daily volatility). (2) Align VectorBT to use 1-minute ATR — wrong direction, would destroy the parameter's discriminating power in sweeps. (3) Add daily ATR to production now — half-sprint of engineering for an unvalidated filter. |
| **Implications** | (1) `orb_breakout.yaml` updated to `max_range_atr_ratio: 999.0` as part of Step 4 parameter finalization. (2) During Phase 3 paper trading, manually log whether losing trades had overextended opening ranges. (3) If pattern emerges, build daily ATR indicator (new DataService work + strategy update). If not, remove the parameter. (4) VectorBT sweep results for the other 5 parameters remain valid and transferable. |
| **Status** | Active |

---

### DEC-076 | Sprint 10 Parameter Recommendations for Phase 3
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | Lock ORB strategy parameters for Phase 3 paper trading: `orb_window_minutes=5`, `time_stop_minutes=15`, `min_gap_pct=2.0`, `stop_buffer_pct=0.0`, `target_r=2.0`, `max_range_atr_ratio=999.0` (disabled). Config updated in `orb_breakout.yaml`. |
| **Rationale** | Two high-sensitivity parameters changed based on VectorBT sweep (522K combos): `orb_window_minutes` 15→5 (monotonic shorter=better trend, all top-10 sets agree) and `time_stop_minutes` 30→15 (clear shorter=better gradient). Three low/medium-sensitivity parameters kept at defaults (target_r, stop_buffer_pct, min_gap_pct). ATR filter disabled per DEC-075. Walk-forward was inconclusive (Scenario C, DEC-073) so recommendations bias toward sweep consensus rather than optimized peaks. Final validation: 137 trades, Sharpe 0.93, PF 1.18, +$8,087 on $100K. |
| **Alternatives Rejected** | (1) Keep original defaults (or=15, hold=30) — 8 trades in 11 months, untestable. (2) Use sweep winner exactly (or=5, hold=15, atr=0.5) — ATR threshold doesn't transfer (DEC-075). (3) Tighten min_gap to 3.0% — reduces trade frequency during paper validation when volume matters. |
| **Status** | Active |

---

### DEC-077 | Phase Restructure — Comprehensive Validation Phase
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | Restructured project phases. Former Phase 3 ("Live Validation") becomes Phase 4. New Phase 3 ("Comprehensive Validation") contains Sprint 11 (extended backtest with ~3 years of data) and paper trading validation as parallel tracks, with an exit gate requiring both to pass before live capital. All subsequent phases shift +1 (old Phase 4 → Phase 5, etc.). |
| **Alternatives** | (a) Keep original structure, proceed to live trading after paper validation only — rejected because walk-forward was inconclusive and extended data is cheap to acquire. (b) Require a fixed paper trading duration (e.g., 40 days minimum) — rejected in favor of flexible user-decides-when-confident approach. |
| **Rationale** | Paper trading was an informal parallel track during Phase 2, not formalized into the phase structure. Extended backtesting (Sprint 11) was identified as high-value/low-cost: ~1–2 days of work to extend data from 11 months to ~3 years, enabling 12+ walk-forward windows vs. the 3 that produced an inconclusive result. Making both activities first-class tracked items with an explicit exit gate ensures neither is rushed. |
| **Status** | Active |

---

### DEC-078 | Fix earliest_entry to Match 5-Minute Opening Range
| Field | Value |
|-------|-------|
| **Date** | 2026-02-18 |
| **Decision** | Change `earliest_entry` from `"09:45"` to `"09:35"` in `config/strategies/orb_breakout.yaml`. |
| **Rationale** | When `opening_range_minutes` was reduced from 15 to 5 (DEC-076), the operating window was not updated. With or=5, the opening range completes at 9:35 AM, creating a 10-minute dead zone (9:35–9:45) where breakouts occur but the strategy cannot enter. Combined with `chase_protection_pct: 0.005` (0.5%), any breakout during this window would be rejected by the time 9:45 arrives because price moved too far past the OR high. All Phase 2/Sprint 11 backtests ran with the 9:45 gate, so historical results are conservative — fixing this should improve forward performance. The VectorBT sweep (which identified or=5 as optimal) did not enforce earliest_entry, meaning it valued or=5 partly because of early breakouts that the production system was missing. |
| **Alternatives Rejected** | (1) Keep 9:45 to match backtest conditions — rejected because the backtest results are already conservative, and the 10-minute gap wastes the primary edge of a shorter OR. (2) Set to 9:36 to add a 1-minute buffer — unnecessary, the OR candle closes at 9:35 and the next candle at 9:36 is the first possible breakout signal. 9:35 is correct because the strategy evaluates breakouts on candle close, so the earliest breakout signal is the 9:35–9:36 candle closing above OR high. |
| **Implications** | (1) Paper trading will see more trades than backtesting predicted (the 9:35–9:45 breakouts were previously filtered out). (2) Backtest results (137 trades, Sharpe 0.93) are a conservative lower bound. (3) Walk-forward results similarly conservative. (4) If paper trading performance is worse than backtest despite this fix, that's a stronger negative signal. |
| **Status** | Active |

### DEC-079 | Parallel Development Tracks — Build vs Validation Separation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-19 |
| **Decision** | Restructure the project roadmap from a linear phase sequence (where each phase blocks the next) to two parallel tracks: a **Build Track** (system construction) and a **Validation Track** (strategy confidence-building). The Build Track proceeds at development velocity. The Validation Track is calendar-bound and confidence-gated. Only the deployment of real capital gates on the Validation Track. |
| **What Changed** | Previously, the Command Center was Phase 6, the AI Layer Phase 7, and additional strategies Phase 8 — all blocked behind live trading validation (Phase 4). Now, system construction (Command Center, Orchestrator, additional strategies, AI Layer) proceeds in parallel with paper trading and live trading validation. The only true gate is: real capital requires paper trading confidence + CPA consultation. |
| **New Structure** | **Build Track** sprints are numbered sequentially (Sprint 12+) regardless of which component they target. **Validation Track** runs continuously: paper trading → live minimum size → live full size. Build Track deliverables enhance the Validation Track (e.g., Command Center makes paper trading more productive; Orchestrator enables multi-strategy paper testing). |
| **Alternatives Rejected** | (1) Keep linear phases — rejected because system construction doesn't depend on strategy validation; the original sequencing was overly conservative and is costing development time. (2) Build a throwaway Streamlit/Dash dashboard now, then rebuild properly later — rejected because it wastes effort; better to build the real Command Center MVP on the target stack (FastAPI + React) where everything carries forward permanently. (3) Build the full Command Center vision before anything else — rejected because the full scope (Strategy Lab, Learning Journal, accounting) is too large; MVP scoped to paper trading utility. |
| **Rationale** | Phases 1 and 2 proved the architecture is solid and development velocity is ~10x original estimates. The two-Claude workflow enables rapid context-switching between components. The original linear sequencing conflated "building the system" with "validating the strategy" — these have different dependency graphs. Strategy validation is calendar-bound (needs market days); system construction is velocity-bound (needs development time). Running them in parallel maximizes both. Every piece of infrastructure built now makes the eventual live trading launch better: more visibility, more tools, more confidence in the system. |
| **Risk** | Live trading could reveal architectural issues (slippage patterns, API latency, fill behavior) that require changes to code built during the Build Track. Mitigated by: (a) clean abstractions at broker/data boundaries already in place, (b) paper trading exercises the same code paths as live, (c) production discoveries are more likely parameter tweaks than architectural rewrites. See RSK-020 in Risk Register. |
| **Status** | Active |

---

### DEC-080 | Command Center Delivery: Web + Desktop + Mobile from Single Codebase
| Field | Value |
|-------|-------|
| **Date** | 2026-02-19 |
| **Decision** | Build the Command Center as a single React frontend that ships to three surfaces simultaneously: (1) **Web app** — accessible from any browser, primary development target. (2) **Tauri desktop app** — native shell wrapping the same React code, adds system tray, native notifications, auto-launch. (3) **PWA (Progressive Web App)** — "Add to Home Screen" on iPhone/iPad, own icon, no Safari chrome, push notification support. All three run the identical React codebase against the same FastAPI backend. |
| **Alternatives Rejected** | (1) Desktop-first with Tauri from Sprint 12 — rejected because it adds Rust/Tauri build complexity before the React frontend is stable, and blocks mobile access until a separate effort. (2) Native iOS app (Swift) — rejected as overkill for a single-user system; PWA provides sufficient mobile experience without App Store overhead. (3) Web-only, defer desktop and mobile — rejected because the user values native app feel and mobile access during US market hours (10:30 PM+ in Taipei timezone). |
| **Rationale** | Tauri is fundamentally a thin native shell around a web frontend — the React code is identical in both contexts. Building the React app as responsive from the start means mobile browser access is free. PWA configuration (manifest, service worker, icons) is ~30 minutes of work and gives iOS/iPad a home-screen app experience. Tauri shell addition to an existing React app is a half-day task. This approach delivers all three surfaces by the end of Sprint 14 without building anything throwaway. The user is in Taipei (UTC+8) and accesses the system at varying times from desk, couch, and mobile — all surfaces serve real use cases. |
| **Implementation** | Sprint 12: API layer + React scaffolding. Sprint 13: Core dashboard views with responsive design (mobile-first CSS). Sprint 14: Paper trading features + PWA manifest/icons + Tauri desktop shell. After Sprint 14: desktop app, web app, and home-screen mobile app all operational. |
| **Status** | Active |

---

### DEC-081 | IEX Data Feed Limitation Acknowledged
| Field | Value |
|-------|-------|
| **Date** | 2026-02-18 |
| **Decision** | Alpaca's free-tier IEX data feed captures only 2–3% of US equity market volume (IEX is one exchange among 15+ US equity exchanges and 30+ ATSs). This renders live trading unreliable — most 1-minute bars are either missing or built from a tiny fraction of actual trades. A dedicated market data provider is required. |
| **Alternatives Rejected** | (1) Ignore and keep using IEX — rejected because data quality directly determines strategy P&L; trading on 2–3% of volume produces candles that don't represent actual market conditions. (2) Upgrade Alpaca to SIP at $99/month — rejected because it's a band-aid that maintains the single-point-of-failure problem (same provider for data and execution), limited to 1,000 WebSocket symbols, and no L2/news/breadth capabilities. See DEC-082 for full provider evaluation. |
| **Rationale** | Paper trading on February 17–18 revealed most 1-minute bars were either missing or built from a tiny fraction of actual trades. For NVDA trading millions of shares per minute at market open, the IEX feed captured only a few hundred shares. This makes all price-derived signals (breakout confirmation, VWAP, volume filters) unreliable. |
| **Implications** | Triggers a full market data provider evaluation (see `argus_market_data_research_report.md`). Paper trading on Alpaca IEX data continues for system stability testing but price/signal accuracy is not validated until a proper data source is integrated. Historical backtesting data from Alpaca (35 months of Parquet files) was obtained via REST API which uses SIP-quality data, so backtest results remain valid. |
| **Status** | Active — resolved by DEC-082 |

---

### DEC-082 | Market Data Architecture — Databento Primary, IQFeed Supplemental
| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Decision** | Databento US Equities Standard ($199/month) as primary equities data backbone. IQFeed added later as supplemental provider for forex, news feeds, and breadth indicators. Alpaca retained for order execution only (subsequently superseded by DEC-083 for live execution). Data and execution fully decoupled — separate providers, separate failure domains. |
| **Alternatives Rejected** | (1) Alpaca SIP upgrade ($99/month) — rejected as band-aid; single point of failure, no L2/news/breadth, 1,000 symbol WebSocket limit. (2) IQFeed as primary — rejected because 2,500 symbol hard cap is an architectural ceiling for the strategy research laboratory vision (30+ concurrent strategies × 100 candidates each exceeds the cap). IQFeed was the Session 1 recommendation but reversed after the "strategy research laboratory" reframe. (3) Polygon.io — rejected for documented data quality and reliability issues (stream freezes, throttling). (4) Bloomberg/Refinitiv — enterprise pricing, disproportionate to needs. (5) Direct exchange feeds — $10K–100K/month, requires C++/Rust, overkill. |
| **Rationale** | (1) Databento has no symbol limits — subscribe to entire US equity universe in a single API call ($199/month flat). (2) Modern Python client with async support enables faster adapter development (no Wine/Docker like IQFeed). (3) Exchange-direct proprietary feeds provide richer data than SIP (odd lot quotes, full depth, auction imbalance). (4) On-demand historical API enables data-first backtesting philosophy. (5) 10-session limit manageable with Event Bus fan-out architecture. (6) IQFeed's unique capabilities (forex, Benzinga news, breadth indicators) are supplemental — added when needed, not the foundation. |
| **Vision alignment** | ARGUS is reframed as a "strategy research laboratory that also trades live." The single most valuable property of a data provider for this use case is breadth of access — unlimited symbols, on-demand history, no artificial constraints on experimentation. Databento delivers this. |
| **Cost** | Databento: $199/month (US equities, unlimited symbols, L0–L3). IQFeed: ~$160–250/month when added (forex + news + breadth). Total eventual: ~$360–450/month. |
| **Architecture** | Databento → DatabentoDataService → Event Bus → All strategies (live). Databento Historical API → Parquet cache → Backtesting tools (historical). IQFeed → IQFeedDataService → Event Bus → Forex strategies + News + Breadth (future). |
| **Known limitations** | No forex data (IQFeed supplemental covers this). No news feeds (IQFeed Benzinga Pro covers this). No breadth indicators (IQFeed covers this). VC-funded startup with ~$8M revenue (mitigated by DataService abstraction enabling provider swap in ~1 sprint). |
| **Supersedes** | Original plan to use Alpaca for both data and execution. Extends DEC-005 (data broker-agnostic abstraction). Resolves DEC-081. |
| **Reference** | Full analysis: `argus_market_data_research_report.md` (project file). |
| **Status** | Active |

---

### DEC-083 | Execution Broker — Direct IBKR Adoption (No Phased Migration)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Decision** | Interactive Brokers (IBKR Pro, tiered pricing) is the sole live execution broker for ARGUS. The IBKRBroker adapter is built before any live trading. No phased Alpaca → IBKR migration — IBKR from day one of live trading. Alpaca demoted to strategy incubator paper testing only. |
| **Alternatives Rejected** | (1) Stay on Alpaca permanently — rejected because PFOF routing (Virtu/Citadel) structurally limits price improvement; 125+ outages in 9 months unacceptable for household income; no futures/forex. (2) Phased migration (Alpaca live first, IBKR later) — rejected because it means two learning curves, throwaway operational knowledge, and migration risk during live trading. With no time pressure to go live, building the right adapter first is cleaner. (3) Tradier — rejected as a middle ground that doesn't solve any actual problem better than IBKR or Alpaca. (4) TradeStation — credible but IBKR dominates on all dimensions. |
| **Rationale** | (1) IBKR SmartRouting across 20+ venues, no PFOF, 100% price improvement rate (independently verified). (2) 9 consecutive years outperforming industry on TAG execution quality audits. (3) Complete multi-asset coverage (stocks, options, futures, forex, crypto) through single account — covers entire ARGUS roadmap. (4) 100+ order types eliminate Order Manager workarounds for bracket order limitations. (5) Publicly traded (NASDAQ: IBKR), profitable since 1978 — maximum business stability. (6) `ib_async` library provides asyncio-native Python integration compatible with ARGUS architecture. (7) Learning one broker's characteristics instead of two eliminates throwaway knowledge. |
| **Alpaca's Permanent Role** | AlpacaBroker adapter retained in codebase for strategy incubator pipeline paper testing (where PFOF and execution quality are irrelevant). Alpaca paper trading continues until IBKRBroker adapter is built and validated, then IBKR takes over all paper and live trading. |
| **Cost** | IBKR tiered: ~$0.0035/share commission + clearing/exchange fees. Estimated ~$43/day at full scale (100 trades × 100 shares). Offset by estimated $200/day execution quality advantage vs PFOF brokers. Net cost-positive even at half the estimated advantage. |
| **Operational requirements** | IB Gateway process must run alongside ARGUS (Docker container recommended). Nightly reset requires reconnection logic. Initial credential setup through browser, then session maintains until logout/reset. |
| **Action item** | Begin IBKR account application immediately — approval can take days to weeks. Paper trading account sufficient to begin adapter development. |
| **Supersedes** | DEC-003 (amended) — IBKR no longer deferred to "Phase 3+"; it is the immediate next broker adapter. DEC-031 (IBKR timing) fully superseded. |
| **Reference** | Full analysis: `argus_execution_broker_research_report.md` (project file). |
| **Status** | Active |

---

### DEC-084 | Sprint Resequencing — Data and Broker Adapters Before Command Center
| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Decision** | Insert two new sprints at the top of the Build Track queue: Sprint 12 (DatabentoDataService adapter) and Sprint 13 (IBKRBroker adapter). Command Center MVP shifts to Sprints 14–16. All subsequent sprints renumbered accordingly. |
| **Previous order** | Sprint 12 (Command Center API), Sprint 13 (Command Center Dashboard), Sprint 14 (Command Center Multi-Surface). |
| **Rationale** | (1) Quality market data is prerequisite for meaningful paper trading — the current IEX feed produces unreliable candles (DEC-081). DatabentoDataService unblocks high-fidelity paper trading. (2) IBKRBroker adapter must be built before live trading (DEC-083). Building it immediately after data means both infrastructure foundations are solid before UI work begins. (3) Command Center is valuable but not blocking — paper trading and live trading can proceed via logs/CLI until the dashboard exists. (4) Both adapters are estimated at 2–3 days each, so the Command Center delay is ~1 week. |
| **New Build Track Queue** | Sprint 12: DatabentoDataService → Sprint 13: IBKRBroker → Sprint 14: Command Center API → Sprint 15: Command Center Dashboard → Sprint 16: Command Center Multi-Surface → Sprint 17: Orchestrator → Sprint 18: ORB Scalp → Sprint 19: Tier 1 News → Sprint 20: AI Layer MVP → Sprint 21+: Expansion |
| **Implications** | Command Center MVP delivery shifts from Sprint 14 to Sprint 16. Paper trading continues on Alpaca IEX data for system stability testing during Sprint 12–13, then migrates to Databento data + IBKR paper trading. |
| **Status** | Active |

---

### DEC-085 | Historical Data Strategy — Databento Source, Parquet Cache
| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Decision** | Hybrid approach: Databento as the data source for new historical data fetches, Parquet as the local cache format. Existing Alpaca-sourced Parquet files (35 months, 29 symbols) retained for current ORB backtesting. The DataFetcher gains a Databento backend alongside the existing Alpaca backend. VectorBT and Replay Harness continue reading from Parquet files unchanged — they are provider-agnostic. |
| **Rationale** | (1) Existing backtesting infrastructure (VectorBT sweeps, Replay Harness, walk-forward) reads Parquet files — no rewrite needed. (2) Parquet is provider-agnostic storage — if Databento goes away, swap the fetch source, keep everything else. (3) Databento's on-demand historical API enables the "pull data when inspiration strikes" workflow. (4) Databento Standard includes 15+ years OHLCV and 12 months L0/L1 history — plenty for new backtest data pulls. (5) Local Parquet cache avoids repeated API calls and egress costs for the same data. |
| **Data Flow** | Live: Databento → DatabentoDataService → Event Bus (no Parquet). Historical: Databento Historical API → DataFetcher → Parquet files → VectorBT / Replay Harness. Legacy: Existing Alpaca Parquet files remain valid and usable. |
| **Status** | Active |

---

### DEC-086 | Alpaca Role Reduction — Strategy Incubator Only
| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Decision** | Alpaca is no longer the primary broker or data provider for ARGUS. Its permanent role is strategy incubator paper testing only — a convenient sandbox for rapid strategy prototyping where execution quality and data fidelity are irrelevant. All production data flows through Databento (DEC-082). All live execution flows through IBKR (DEC-083). |
| **Previous role** | Primary broker for both market data (IEX feed) and order execution (paper + live). |
| **New role** | Strategy Incubator pipeline stages 1–6 (concept through paper trading). Alpaca's excellent developer experience and simple API make it ideal for rapid strategy prototyping where execution quality and data fidelity are less critical. |
| **What remains** | AlpacaBroker adapter (~80 tests), AlpacaDataService adapter, AlpacaScanner — all maintained in codebase. Alpaca paper trading account remains active for incubator use. |
| **What changes** | Alpaca is removed from the live trading path entirely. No real capital flows through Alpaca. IBKR paper trading replaces Alpaca paper trading for pre-live validation once IBKRBroker adapter is built (Sprint 13). |
| **Rationale** | Follows from DEC-081 (IEX data inadequacy), DEC-082 (Databento data), and DEC-083 (IBKR execution). Alpaca's value proposition — simplicity and free tier — remains ideal for low-stakes strategy incubation. |
| **Status** | Active |

---

### DEC-087 | Databento Subscription Timing — Defer Until Adapter Ready
| Field | Value |
|-------|-------|
| **Date** | 2026-02-20 |
| **Decision** | Delay activating the Databento subscription ($199/month) until the DatabentoDataService adapter (Sprint 12) is built and ready for integration testing. Sprint 12 development uses mock data and unit tests. Subscription activated only when needed for integration testing and paper trading resumption with quality data. |
| **Rationale** | No reason to pay $199/month while the adapter doesn't exist yet. Sprint 12 can be developed and unit-tested against mock Databento responses. The subscription is activated at the end of Sprint 12 for integration testing, then continues monthly for paper trading and eventually live trading. |
| **Status** | Active |

---

### DEC-088 | DatabentoDataService Threading Model
| Field | Value |
|-------|-------|
| **Date** | 2026-02-21 |
| **Decision** | Databento Live client callbacks run on Databento's internal reader thread. Bridge to asyncio via `loop.call_soon_threadsafe()` → `asyncio.ensure_future(event_bus.publish(...))`. Record class references stored during `start()` to avoid module imports on the hot path. |
| **Alternatives** | (a) `async for record in live_client` iteration pattern — also valid but callback pattern is Databento's documented recommendation and gives explicit control over thread bridging. (b) Import databento in every `_dispatch_record()` call — functionally correct but unnecessary overhead on high-frequency path. |
| **Rationale** | Callback pattern is officially documented by Databento. Storing class references avoids repeated `sys.modules` lookups on a path that processes hundreds of messages per second during market hours. Price/indicator cache updates (single-key dict operations) are GIL-protected and safe without locks. |
| **Status** | Active |

---

### DEC-089 | Default Databento Dataset — XNAS.ITCH
| Field | Value |
|-------|-------|
| **Date** | 2026-02-21 |
| **Decision** | XNAS.ITCH (Nasdaq TotalView-ITCH) as the default Databento dataset for live streaming. Configurable via `DatabentoConfig.dataset`. |
| **Alternatives** | (a) DBEQ.BASIC — consolidated, but lower fidelity. (b) XNYS.PILLAR — NYSE only, misses NASDAQ-listed stocks that ORB primarily targets. (c) Multiple datasets simultaneously — adds complexity, deferred. |
| **Rationale** | Databento's most recommended feed for trading firms. Deepest historical data availability (best backtest/live parity). Provides L2/L3 when needed. Covers the majority of high-gap NASDAQ-listed stocks that ORB targets. XNYS.PILLAR can be added later for NYSE-listed coverage if needed. |
| **Status** | Superseded by DEC-248 |

---

### DEC-090 | DataSource Enum for Provider Selection
| Field | Value |
|-------|-------|
| **Date** | 2026-02-21 |
| **Decision** | Added `DataSource` enum to `SystemConfig` with `alpaca` and `databento` variants. `main.py` Phase 6/7 branches on this to select DataService and Scanner implementations. |
| **Rationale** | Clean config-driven provider selection. Supports future providers without code changes to main.py beyond adding enum values and factory branches. |
| **Status** | Active |

---

### DEC-091 | Shared Databento Normalization Utility
| Field | Value |
|-------|-------|
| **Date** | 2026-02-21 |
| **Decision** | Extracted `normalize_databento_df()` into `argus/data/databento_utils.py`. Both `DatabentoDataService` and `DataFetcher` call this shared function instead of maintaining separate implementations. |
| **Rationale** | Eliminates code duplication. Single source of truth for Databento → ARGUS schema conversion (ts_event → timestamp, UTC normalization, column selection, sorting). |
| **Status** | Active |

---

### DEC-092 | IndicatorEngine Extraction (Sprint 12.5 / DEF-013)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-21 |
| **Decision** | Extracted duplicated indicator computation logic into a shared `IndicatorEngine` class (`argus/data/indicator_engine.py`). All four DataService implementations (AlpacaDataService, DatabentoDataService, ReplayDataService, BacktestDataService) now delegate to IndicatorEngine instead of maintaining separate implementations. |
| **Alternatives** | (1) Leave duplication in place (rejected — maintenance burden, bug risk), (2) Create a mixin class (rejected — inheritance complexity), (3) Create a shared module with standalone functions (rejected — less testable, state management awkward) |
| **Rationale** | Pure refactor resolving DEF-013. Indicator state (VWAP, ATR-14, SMA-9/20/50, RVOL) was duplicated across four files. IndicatorEngine encapsulates all state and computation in a per-symbol object. Provides: single source of truth, comprehensive unit tests (27 new tests), auto-reset detection for day boundaries, warm-up support, property accessors for current values. Zero behavioral changes — existing 658 tests pass unchanged plus 27 new IndicatorEngine tests (685 total). |
| **Status** | Active |

---

### DEC-093 | Native IBKR Bracket Orders with T1/T2 Support
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | IBKRBroker implements `place_bracket_order()` supporting multi-target brackets (T1 + T2) using IBKR's native `parentId` linkage and `transmit` flag pattern. Parent (entry) + stop + T1 + T2 submitted atomically. Order Manager receives T2 support via `t2_order_id` field on ManagedPosition, `_submit_t2_order()` method, `_handle_t2_fill()` handler, and `on_tick()` skip logic when broker-side T2 exists. |
| **Alternatives** | (1) Single-target brackets only like Alpaca (rejected — wastes IBKR's multi-leg capability), (2) Full bracket refactor of Order Manager to call `place_bracket_order()` atomically from `on_approved()` (deferred — DEF-016, large scope change to Order Manager core flow) |
| **Rationale** | IBKR supports unlimited bracket legs via `parentId` cascading. T2 as a broker-side limit order survives ARGUS crashes and doesn't require tick monitoring. Current implementation submits T2 as an individual `place_order()` from `_handle_entry_fill()` rather than via `place_bracket_order()` — functionally correct with explicit cancellation in all exit paths. Atomic bracket integration deferred to DEF-016. Backward compatible: Alpaca path (t2_order_id=None) continues tick-based T2 monitoring unchanged. |
| **Status** | Active |

---

### DEC-094 | BrokerSource Enum and IBKRConfig
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | Added `BrokerSource` enum (`alpaca`, `ibkr`, `simulated`) to `SystemConfig` for broker selection. Added `IBKRConfig` (Pydantic BaseModel) with IB Gateway connection parameters: host, port, client_id, account, timeout, readonly, reconnection settings, rate limit. `main.py` Phase 3 branches on `config.system.broker_source` to instantiate the correct broker. |
| **Alternatives** | (1) Separate config files per broker (rejected — already have brokers.yaml, adding enum is simpler), (2) Auto-detect from environment (rejected — explicit configuration is safer for a system managing real money) |
| **Rationale** | Mirrors the `DataSource` enum pattern from Sprint 12 (DEC-090). Config-driven broker selection allows switching between IBKR (production), Alpaca (incubator), and SimulatedBroker (backtesting) via a single YAML field. IBKRConfig centralizes all IB Gateway connection parameters with sensible defaults (port 4002 for paper, 45 orders/sec rate limit matching IBKR's documented limit). |
| **Status** | Active |

---

### DEC-095 | DEF-016 Evaluation — Atomic Bracket Refactor Deferred
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | Defer Order Manager atomic bracket refactor (DEF-016) to Sprint 17+ (Orchestrator) or when limit entry strategies are implemented. Current post-fill individual `place_order()` submission is functionally correct and sufficient for market-order strategies. |
| **Rationale** | (1) No trigger conditions met — no limit entries, no IBKR timing issues observed, no Orchestrator refactor yet. (2) Scope balloons: SimulatedBroker's synchronous fill model conflicts with pre-fill bracket submission, AlpacaBroker only supports single-target brackets, and nearly all Order Manager tests assume post-fill submission. Estimated 1.5–2 days — disproportionate to benefit. (3) Market orders fill in milliseconds on IBKR, making the unhedged gap between entry fill and exit leg submission negligible. (4) Explicit T2 cancellation in all exit paths provides functional correctness. (5) Command Center (Sprint 14) is higher priority for daily operations. |
| **Alternatives Rejected** | Implement now — scope exceeds 0.5-day threshold from evaluation criteria. SimulatedBroker compatibility alone is a multi-hour change. |
| **Status** | Active |

---

### DEC-096 | Sprint Resequencing — Empowerment MVP (Sprints 14–22)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | Resequenced Build Track queue to prioritize the interactive operator experience before live capital deployment. New order: CC API (14) → CC Frontend (15) → Desktop/PWA (16) → Orchestrator V1 (17) → ORB Scalp (18) → VWAP Reclaim (19) → Afternoon Momentum (20) → CC Analytics & Strategy Lab (21) → AI Layer MVP (22). Orchestrator moved ahead of Desktop/PWA packaging. Two new strategy sprints (VWAP Reclaim, Afternoon Momentum) inserted before AI Layer. Tier 1 News deferred to Sprint 23+. |
| **Alternatives** | (1) Original queue: CC MVP (14–16) → Orchestrator (17) → ORB Scalp (18) → News (19) → AI (20) → CC expansion (21) — rejected because user needs to experience the system as an operator (persistent UI + orchestrator + multiple strategies) before deploying capital. (2) Original queue with Tier 1 News at Sprint 19 and strategies deferred to 22+ — rejected because four uncorrelated strategies are needed for meaningful validation before live capital. |
| **Rationale** | User insight: understanding strategies and building conviction requires a persistent visual interface with orchestration controls and real-time data — not terminal output and backtest reports. Four uncorrelated strategies covering the full trading day (morning breakouts, mid-morning mean-reversion, afternoon momentum) provide meaningful orchestration and diverse signal validation. Analytics suite enables pattern recognition across strategies and market conditions. AI Layer built during paper trading validation period so its analysis compounds as trade data accumulates. Desktop/PWA is a packaging step that doesn't unlock new capability — web app works on all devices including mobile. |
| **Status** | Active |
| **Supersedes** | DEC-084 (sprint resequencing — data/broker before CC) for queue ordering beyond Sprint 13. Sprint 14 scope unchanged. |

---

### DEC-097 | Databento Activation Timing — Post-Sprint 18
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | Defer Databento subscription activation ($199/mo) until approximately Sprint 19 (VWAP Reclaim), when new strategies require quality data for backtesting and parameter validation. Sprints 14–18 (Command Center, Orchestrator, ORB Scalp, Desktop/PWA) are UI and infrastructure work that can use Alpaca paper data. |
| **Alternatives** | (1) Activate immediately — rejected because $200–600 would be spent during sprints that don't benefit from quality data. (2) Activate after Sprint 22 — rejected because strategy development (Sprints 19–20) needs quality data for backtesting and walk-forward validation. |
| **Rationale** | Saves $400–600 during UI/infrastructure development sprints with zero downside. Databento data matters when building signal intuition and validating strategy parameters — not when building dashboards and orchestration logic. Alpaca paper trading data is sufficient for Command Center development and testing. Amends DEC-087 timing guidance. |
| **Status** | Superseded by DEC-143 |
| **Amends** | DEC-087 (cost deferral — original timing was "when adapter ready for integration testing") |

---

### DEC-098 | AI Layer Model Selection — All Opus
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | ARGUS AI Layer uses Claude Opus (currently Opus 4.5, $5/$25 per MTok) for all API calls — pre-market briefings, post-trade analysis, anomaly detection, natural language queries, weekly reviews. No mixed-model optimization. Separate Anthropic API account (pay-as-you-go), independent of user's Claude Max subscription. |
| **Alternatives** | (1) Mixed-model approach: Haiku for anomaly detection, Sonnet for trade analysis, Opus for complex reasoning — rejected because cost delta (~$20/month) is negligible relative to trading capital, and user prioritizes maximum intelligence for all tasks involving real money. (2) Use Claude Max subscription — not possible; Max is for interactive chat, API is separate billing. |
| **Rationale** | Estimated all-Opus cost: $35–50/month. With prompt caching (90% savings on repeated system context), likely lower. Cost is trivial relative to Databento ($199/mo), IBKR commissions, and the $25K–100K+ trading capital at stake. Missing an anomaly or generating a weaker analysis to save $20/month is irrational risk optimization. API account setup: console.anthropic.com, credit card, API key stored in encrypted secrets manager (existing architectural rule). |
| **Status** | Active |

---

### DEC-099 | API Server Lifecycle — In-Process Phase 11
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | FastAPI API server runs in the same process as the trading engine, as Phase 11 of the 10-phase startup sequence. Uses `uvicorn.Server` programmatic API within the existing asyncio event loop. Also runnable standalone (`python -m argus.api.server --dev`) with mock data for frontend development. |
| **Alternatives Considered** | Separate process with shared SQLite (rejected — adds IPC complexity, requires message queue bridge for WebSocket events, no benefit at single-user scale). |
| **Rationale** | Same-process means direct Python references to EventBus, TradeLogger, Broker, HealthMonitor, etc. No serialization overhead. Dramatically simpler for a single-user system. Standalone `--dev` mode enables frontend development without running the full trading engine. |
| **Status** | Active |

---

### DEC-100 | API Dependency Injection — AppState + FastAPI Depends()
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | A singleton `AppState` dataclass holds references to all trading engine components. Initialized during startup, injected into route handlers via FastAPI's `Depends()` mechanism. |
| **Alternatives Considered** | Global module-level variables (rejected — harder to test, implicit coupling). Flask-style app.config (rejected — not idiomatic FastAPI). |
| **Rationale** | Clean boundary between API layer and trading engine. Easy to test — inject mock `AppState` in test fixtures. No global state pollution. Idiomatic FastAPI pattern. |
| **Status** | Active |

---

### DEC-101 | WebSocket Event Filtering — Curated List with Tick Throttling
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | WebSocket bridge forwards a curated list of Event Bus events (position, order, system, scanner, strategy events). TickEvents are throttled to max 1/sec/symbol and only forwarded for symbols with open positions. Clients can filter by event type via subscription messages. |
| **Alternatives Considered** | Forward all events (rejected — TickEvents for all symbols would be thousands/second, unusable). Client-only filtering (rejected — wastes bandwidth sending events the client will discard). |
| **Rationale** | Frontend needs position-relevant price updates and system events, not raw market data. Throttle-from-day-one prevents architectural debt when Databento's full-universe feed arrives. |
| **Status** | Active |

---

### DEC-102 | Authentication — Single-User JWT with bcrypt
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | Single-user JWT authentication. Password hash (bcrypt) stored in `config/system.yaml`. CLI tool (`python -m argus.api.setup_password`) generates hash. JWT with configurable expiry (default 24h). No user table, no registration, no 2FA in V1. |
| **Alternatives Considered** | Full user management (rejected — over-engineered for single-operator system). API key only (rejected — less secure than JWT for browser-based access). 2FA now (rejected — premature for paper trading phase, appropriate before live capital). |
| **Rationale** | Adequate security for development and paper trading. JWT + HTTPS (production) handles connection interception risk. 2FA deferred to pre-live-trading hardening. |
| **Status** | Active |

---

### DEC-103 | Monorepo Structure — argus/api/ + argus/ui/
| Field | Value |
|-------|-------|
| **Date** | 2026-02-22 |
| **Decision** | React frontend lives in `argus/ui/` within the same repository. FastAPI serves the built React app (`argus/ui/dist/`) as static files in production. Development uses Vite dev server (port 5173) with proxy to FastAPI (port 8000). |
| **Alternatives Considered** | Separate repository for frontend (rejected — adds synchronization overhead for a single-developer project). |
| **Rationale** | Single repo keeps everything together. Vite proxy provides seamless development experience. Production serving via FastAPI StaticFiles avoids needing a separate web server. |
| **Status** | Active |

---

### DEC-104 | Chart Libraries — Dual Library (Lightweight Charts + Recharts)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Decision** | Use TradingView Lightweight Charts for all financial time-series charts (equity curves, P&L histograms, future price/candlestick charts). Use Recharts for non-time-series visualizations (distributions, heatmaps, sparklines, comparisons). Both libraries coexist in the codebase. |
| **Alternatives Considered** | (A) Recharts only — simpler but lacks financial time-axis handling (weekend gaps, market hours). (B) Lightweight Charts only — excellent for financial data but limited for non-temporal analytics charts needed in Sprint 21+. |
| **Rationale** | ARGUS is a trading tool — every time-series chart benefits from Lightweight Charts' native financial axis, crosshair, and zoom. Recharts fills the gap for non-financial visualizations in analytics views. Combined bundle cost is modest (~90KB gzipped). Each library does what it's best at. |
| **Status** | Active |

---

### DEC-105 | Responsive Breakpoints — Three-Tier Device Targeting
| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Decision** | Three responsive breakpoints: <640px (phone — iPhone 16 Pro 393px), 640–1023px (tablet — iPad Pro 11" portrait 834px), ≥1024px (desktop — iPad landscape 1194px, MacBook Pro 16" 1512px). Phone and tablet use bottom tab bar navigation; desktop uses icon sidebar. |
| **Alternatives Considered** | Two breakpoints (<768px / ≥768px) — iPad portrait at 834px barely clears 768px threshold and would get a desktop layout too cramped for that width. |
| **Rationale** | User's actual devices are iPhone 16 Pro, iPad Pro 11" M4, and MacBook Pro 16". iPad portrait (834px) needs its own treatment — not squeezed into phone layout, not stretched into full desktop. Three Tailwind breakpoints (sm/md/lg) add minimal implementation cost. iPad landscape (1194px) gets full desktop experience with sidebar. |
| **Status** | Active |

---

### DEC-106 | UI/UX Feature Backlog Document

| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Decision** | Created `docs/ui/UX_FEATURE_BACKLOG.md` as the canonical inventory of all planned UI/UX enhancements. 35 features organized across 6 sprint groupings (Sprints 16–23+) with priority tiers (P0–P3), effort estimates, and implementation notes. Derived from design research session reviewing Bybit, analytics dashboards, mobile trading apps, and data visualization references. |
| **Rationale** | Sprint 15 established the Command Center foundation. The next question is "how do we evolve from status page to command center?" Capturing the full vision in one document prevents piecemeal design decisions and ensures future sprints have clear design targets. |
| **Alternatives** | (a) Add features ad-hoc as sprints arise — rejected, loses the coherent vision. (b) Full design spec per feature — premature, effort estimates and priorities may shift. |
| **Status** | Active |

---

### DEC-107 | Sprint 16 UX Enhancements — Motion, Sparklines, Polish

| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Decision** | Sprint 16 (Desktop/PWA) scope expanded to include ~15 hours of UX polish: staggered entry animations, chart draw-in animations, page transitions, skeleton loading states, number morphing/P&L flash, hover feedback, contextual empty states, and hero sparklines on dashboard summary cards. These enhance perceived quality without new data infrastructure. |
| **Rationale** | Low effort, high impact. Motion and micro-interactions transform the app from "functional prototype" to "premium tool." Sprint 16 is the right time because it's the packaging sprint — Tauri desktop and PWA mobile wrapping happens alongside these polish items. |
| **Alternatives** | (a) Defer all polish to Sprint 21 — rejected, 5+ sprints of using an app without animation feels unfinished. (b) Add animation earlier in Sprint 15 — rejected, Sprint 15 was already at scope limit. |
| **Status** | Active |

---

### DEC-108 | Sprint 21 Scope — CC Analytics & Strategy Lab Defined

| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Decision** | Sprint 21 (CC Analytics & Strategy Lab) scope defined as ~80–100 hours covering: Individual Stock/Asset Detail Panel (slide-in), Dashboard V2 Command Center layout, trade activity heatmaps, win/loss distribution histogram, portfolio treemap, risk waterfall chart, comparative period overlay, strategy correlation matrix, trade replay mode, goal tracking, and heat strip portfolio bar. Additional chart libraries for Sprint 21+: D3 (treemaps, heatmaps, sunbursts — use sparingly) and Three.js or Plotly 3D (strategy optimization landscape in Sprint 22). These extend the DEC-104 chart stack. Full specifications in `docs/ui/UX_FEATURE_BACKLOG.md` items 21-A through 21-K. |
| **Rationale** | Sprint 21 was previously a placeholder. Design research defined what "analytics" concretely means. The stock detail panel (21-A) is the single biggest functional gap vs. production trading platforms. Trade replay (21-I) is the highest-value learning tool. Together they transform ARGUS from a monitoring tool into a research laboratory. |
| **Alternatives** | (a) Smaller Sprint 21 scope — likely necessary in practice; the backlog provides a prioritized menu to select from. (b) Spread analytics across Sprints 18–20 — rejected, strategy development is the priority for those sprints. |
| **Status** | Active |

---

### DEC-109 | Design North Star — "Bloomberg Terminal Meets Modern Fintech"

| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Decision** | Established six design principles for the Command Center: (1) Information over decoration, (2) Ambient awareness via sparklines/gauges/heatmaps, (3) Progressive disclosure (summary → detail panel → full page), (4) Motion with purpose (<500ms, never blocks interaction), (5) Mobile as primary trading surface (Taipei overnight hours), (6) Research lab aesthetics for Sprint 21+ visualizations. All future UI decisions evaluated against these principles. |
| **Rationale** | Design research revealed the gap between current "status page" Dashboard and envisioned "command center." Codifying principles prevents drift toward either consumer-app aesthetics (gradients, glassmorphism) or bare-data terminal (no visual craft). The principles are grounded in Steven's actual usage pattern: monitoring from iPhone during overnight Taipei hours, detailed analysis on desktop during off-hours. |
| **Alternatives** | None — these are guiding principles, not exclusive technical choices. |
| **Status** | Active |

---

### DEC-110 | Animation Library — Framer Motion + CSS Transitions

| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Decision** | Framer Motion for page transitions and staggered entry animations. CSS transitions for hover effects and micro-interactions. Lightweight Charts native animation for chart draw-ins. Animation budget: every animation <500ms, never blocks interaction, 60fps minimum. |
| **Rationale** | Framer Motion integrates cleanly with React Router (AnimatePresence for page transitions) and provides stagger orchestration. CSS transitions are sufficient and more performant for simple hover/focus effects. No need for a heavier library like GSAP. |
| **Alternatives** | (a) Pure CSS only — rejected, staggered orchestration is awkward in pure CSS. (b) React Spring — viable but Framer Motion has better React Router integration. (c) GSAP — overkill for this use case. |
| **Status** | Active |

---

### DEC-111 | Control Endpoints & Emergency Controls
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision** | Backend control endpoints: strategy pause/resume, position close, emergency flatten all, emergency pause all. All gated by JWT auth. Frontend confirmation modals for emergency actions. |
| **Rationale** | Operator needs real-time control during trading sessions. Emergency flatten is critical safety mechanism. Confirmation modals prevent accidental activation. Single-position close uses broker flatten_all(symbols=[symbol]) — acceptable for V1 single-strategy; revisit for multi-strategy. |
| **Alternatives** | WebSocket-based commands (rejected — REST is simpler, stateless, easier to test). Strategy-scoped position close (deferred — requires Order Manager changes). |
| **Status** | Active |

---

### DEC-112 | CSV Trade Export
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision** | CSV export endpoint at GET /trades/export/csv with strategy_id, date_from, date_to filters. StreamingResponse with date-stamped filename. 10,000 row limit. |
| **Rationale** | Enables trade data portability for tax prep, external analysis, and record-keeping. Filters match the trades query endpoint for consistency. Frontend downloads via blob URL. |
| **Status** | Active |

---

### DEC-113: Regime Classification V1 Data Source
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision:** | Fetch SPY daily bars via REST at pre-market time through DataService. Use SPY 20-day realized volatility as VIX proxy. Skip breadth (advance/decline) in V1. |
| **Rationale:** | SPY is a market barometer, not a traded symbol — shouldn't pollute the real-time data stream. Daily bars are sufficient for MA, momentum, and volatility computation. Alpaca REST provides reliable daily bars (IEX accuracy issues only affect intraday data). VIX requires a separate CBOE dataset subscription even on Databento. Breadth requires IQFeed ($160–250/mo) — not justified for V1 with one strategy. Architecture supports adding real VIX and breadth later with zero Orchestrator code changes. |

---

### DEC-114: Orchestrator Allocation Method — Equal Weight V1
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision:** | Equal-weight allocation for V1. `allocation_method: "equal_weight"` in config. Performance-weighted allocation deferred to post-Sprint 21 when sufficient multi-strategy trade data exists. |
| **Rationale:** | Performance-weighted allocation requires statistically meaningful trade history across multiple strategies. With one strategy and limited paper trading, the data doesn't exist yet. The allocation engine interface supports future methods via config-driven dispatch. |
| **Future:** | `performance_weighted` method (±10% shift based on trailing 20-day Sharpe/profit factor, per Bible Section 5.2), Kelly criterion, ML-based allocation. Tracked as DEF-017. |

---

### DEC-115: Continuous Regime Monitoring
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision:** | Orchestrator re-evaluates market regime every 30 minutes during market hours (configurable). If regime shifts, Orchestrator adjusts strategy activation immediately (prevents new signals, does not flatten existing positions). |
| **Rationale:** | Surprise market events (Fed announcements, tariff news, flash crashes) can invalidate the morning's regime classification. Without intraday re-evaluation, strategies continue trading in conditions they're not designed for. The RegimeClassifier is already callable on-demand; adding periodic re-evaluation is minimal scope. |

---

### DEC-116: Strategy Correlation Tracker — Infrastructure Now, Allocation Later
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision:** | Build `CorrelationTracker` class that records daily P&L per strategy and computes pairwise correlation matrix. Wire it into the allocation engine as an optional modifier. Correlation-adjusted allocation is not active in V1 — tracker collects data silently. Can be seeded from backtested returns when Sprints 18–20 produce strategy backtests. |
| **Rationale:** | 4 strategies coming online within the week (Sprints 18–20). Correlation computation requires 20–30 days of parallel daily returns — infrastructure must exist before data accumulates. Backtested returns can bootstrap initial estimates. Correlation-adjusted allocation activates when sufficient data exists (configurable minimum days threshold). |
| **Future:** | Active correlation-adjusted allocation when `min_correlation_days` threshold is met. Tracked as part of DEF-017. |

---

### DEC-117: DEF-016 Resolution — Atomic Bracket Orders in Order Manager
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision:** | Refactor Order Manager to use `place_bracket_order()` for entry+stop+T1+T2 submission. All three broker implementations already support `place_bracket_order()`. The refactor is scoped to Order Manager's `on_approved()` and `_handle_entry_fill()` methods plus test updates. |
| **Rationale:** | Eliminates the unprotected window between entry fill and stop/target placement. For a system managing family income, "near-zero risk" is not the right standard — zero risk is. SimulatedBroker already has working `place_bracket_order()`. IBKRBroker uses native IBKR bracket linkage. AlpacaBroker supports single-target brackets (acceptable for incubator use). |

---

### DEC-118: Pre-Market Scheduling — Self-Contained Poll Loop
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision:** | Orchestrator runs its own background polling loop (like Order Manager's fallback poll). Checks clock every 30 seconds. Fires pre-market routine at configured time (default 9:25 AM ET), regime re-evaluation every N minutes during market hours, and EOD review at configured time (default 4:05 PM ET). No APScheduler dependency. |
| **Rationale:** | Consistent with Order Manager's time-based trigger pattern. Self-contained, no new dependencies. Handles mid-day restarts gracefully (detects market hours, runs abbreviated pre-market). |

---

### DEC-119: Single-Strategy Allocation Cap
| Field | Value |
|-------|-------|
| **Date** | 2026-02-24 |
| **Decision:** | With fewer than 3 active strategies, the `max_allocation_pct` cap (default 40%) leaves deployable capital idle. This is accepted as intentional risk reduction during the early validation phase. No special-casing for N=1. The cap becomes naturally irrelevant at N≥3 (Sprint 19+). Performance-weighted allocation (Bible §5.2 ±10% shift) deferred until sufficient multi-strategy performance history exists. |
| **Rationale:** | The single-strategy period (Sprints 17-18) is the highest-risk phase for discovering issues the backtest missed. Idle capital acts as a built-in safety buffer that automatically loosens as validated strategies are added. Adding a `single_strategy_full_allocation` config flag would create temporary complexity for a transitional state. |
| **Alternatives:** | (a) Allow 100% of deployable capital to single strategy — rejected as too aggressive for unproven live performance. (b) Add config toggle — rejected as unnecessary complexity for a 2-sprint transitional period. |
| **Status:** | Active |

---

### DEC-120 | ORBBase Strategy Extraction
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Extract shared opening range formation and breakout detection logic into `OrbBaseStrategy` base class. Both `OrbBreakoutStrategy` and `OrbScalpStrategy` inherit from it. |
| **Rationale** | ORB Scalp shares ~70% of ORB's code (OR formation, breakout detection, position sizing, scanner criteria). Extracting to a base class eliminates duplication and ensures future ORB variants slot in cleanly. Subclasses override only signal construction and exit rules. |
| **Alternatives** | (A) Subclass ORB directly — messy override of trade management. (B) Copy code — duplication risk. |
| **Status** | Active |

---

### DEC-121 | ALLOW_ALL Duplicate Stock Policy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Add `ALLOW_ALL` to `DuplicateStockPolicy` enum and set it as the default. ORB and ORB Scalp can trade the same symbol simultaneously, subject to `max_single_stock_pct` (5%) exposure cap. |
| **Rationale** | ORB targets 2R over 15 minutes. Scalp targets 0.3R over 30–120 seconds. They exploit different phases of the same momentum event and have independent risk profiles. Combined exposure is already gated by the single-stock cap. Blocking same-stock trades across strategies would eliminate valid diversified signals. |
| **Alternatives** | BLOCK_ALL — too restrictive. FIRST_SIGNAL — arbitrary winner. PRIORITY_BY_WIN_RATE — requires win rate data not yet available in real-time. |
| **Status** | Active |

---

### DEC-122 | Per-Signal Time Stop
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Add `time_stop_seconds: int | None` field to `SignalEvent`. Carried to `ManagedPosition`. Order Manager checks per-position time stop before falling back to global `max_position_duration_minutes`. |
| **Rationale** | ORB Scalp needs time stops in seconds (30–300s), not minutes. Different strategies have fundamentally different hold durations. A per-signal mechanism is cleaner than per-strategy config on the Order Manager. The global config becomes a safety backstop. |
| **Alternatives** | Per-strategy config on Order Manager — breaks encapsulation, requires OM to know about strategies. |
| **Status** | Active |

---

### DEC-123 | ORB Scalp Trade Management
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | ORB Scalp uses single-target exit (no T1/T2 split), defaulting to 0.3R target, 120s max hold, OR midpoint stop. Sends `target_prices=(target,)` with one element. |
| **Rationale** | Scalp trades are too fast for partial exits. The entire position exits at the single target or gets stopped/timed out. 0.3R keeps the expected win rate high (>55%) while generating enough P&L per trade. 120s hold aligns with the "capture initial momentum burst" thesis. |
| **Alternatives** | T1/T2 split like ORB — unnecessary complexity for sub-5-minute trades. Higher R target — would reduce win rate below the scalp thesis. |
| **Status** | Active |

---

### DEC-124 | Risk Manager ↔ Order Manager Reference
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Risk Manager receives an Order Manager reference (via setter) for cross-strategy position queries. `get_managed_positions()` public method added to Order Manager. |
| **Rationale** | Cross-strategy risk checks need to know what positions are currently open *per strategy*. `broker.get_positions()` returns raw broker positions without strategy attribution. The Order Manager's `ManagedPosition` objects have `strategy_id`, making them the correct source for cross-strategy queries. |
| **Alternatives** | Query broker + match by symbol — loses strategy attribution. Shared position tracker — unnecessary abstraction for V1. |
| **Status** | Active |

---

### DEC-125 | CandleEvent Routing via EventBus
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | main.py subscribes to CandleEvent on the EventBus and routes candles to all active strategies via `_on_candle_for_strategies()`. Replaces the single-strategy `self._strategy` singleton. Strategies are accessed through `orchestrator.get_strategies()`. |
| **Rationale** | The live system had no CandleEvent → strategy routing (only existed in Replay Harness). With multiple strategies, a centralized router that checks `is_active` and watchlist membership before calling `on_candle()` is the cleanest pattern. Using the Orchestrator's registry as the source of truth keeps strategy lifecycle management in one place. |
| **Alternatives** | Each strategy subscribes to CandleEvent directly — would bypass active/watchlist checks and require strategies to self-filter. |
| **Status** | Active |

---

### DEC-126 | Sector Exposure Check Deferred
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Cross-strategy sector exposure check (`max_single_sector_pct`) deferred. No sector classification data available. Logged as DEF-020. |
| **Rationale** | Implementing the exposure cap requires mapping symbols to sectors (SIC codes, GICS, or similar). No data source currently provides this. Building a static mapping is fragile. IQFeed or Databento fundamentals could provide this when integrated. The single-stock cap (5%) provides sufficient concentration protection for V1. |
| **Status** | Active |

---

### DEC-127 | ORB Scalp VectorBT Sweep — Directional Guidance Only
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | ORB Scalp VectorBT sweep (16 combos × 29 symbols = 20,880 trades) produces directional guidance only, not actionable parameter optimization. All aggregate Sharpe ratios are negative. Default parameters (scalp_target_r=0.3, max_hold_seconds=120) are thesis-driven, not backtest-optimized. |
| **Rationale** | 1-minute bar resolution cannot meaningfully simulate 30–300 second holds. Synthetic ticks (4/bar) approximate intra-bar price paths but cannot determine whether a 0.3R target was hit before or after a stop. This is a fundamental resolution limitation (RSK-026), not a strategy deficiency. VectorBT infrastructure is correctly built and will produce actionable results when Databento tick-level data is available. |
| **Alternatives** | (A) Attempt sub-bar interpolation — inaccurate without real tick data. (B) Skip sweep entirely — loses directional signal about parameter landscape shape. |
| **Status** | Active |

---

### DEC-128 | Three-Way Position Filter (All / Open / Closed)
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Dashboard positions section uses a three-way filter: All / Open / Closed. Works identically in both Table and Timeline views. "All" shows open positions bright and closed positions at reduced opacity (timeline) or combined list with section headers (table). Default: "Open" during market hours, "All" after hours. |
| **Rationale** | Two-way toggle (Open/Closed) felt incomplete — the timeline's value is showing the full session narrative. "All" preserves this while letting users focus during active trading. Default follows natural workflow: monitor live positions during hours, review full session after close. |
| **Alternatives** | Keep two-way toggle — loses the "full session" view. Different filters for table vs timeline — confusing. |
| **Status** | Active |

---

### DEC-129 | Positions UI State in Zustand Store
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Display mode (table/timeline) and position filter (all/open/closed) managed in a dedicated Zustand store (`stores/positionsUI.ts`). Session-level persistence — survives responsive layout re-mounts but resets on full page reload. No localStorage. |
| **Rationale** | Component-level React state was resetting when window resize crossed responsive breakpoints (sidebar ↔ bottom tab bar transition re-mounts parent components). Zustand store lives outside the React tree, so state persists regardless of mount/unmount cycles. localStorage unnecessary for ephemeral view preferences. |
| **Alternatives** | Lift state to a never-remounting ancestor — fragile, depends on layout structure. localStorage — overkill for view toggles. |
| **Status** | Active |

---

### DEC-130 | Frontend Testing — Vitest
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Vitest adopted for React component testing. First tests: 7 tests for PositionTimeline. Config: `vitest.config.ts`, setup: `src/test/setup.ts`. Test scripts added to `package.json`. |
| **Rationale** | Vitest integrates natively with Vite (already the build tool), provides Jest-compatible API, and runs significantly faster than Jest for Vite projects. Establishes the pattern for future frontend testing. |
| **Alternatives** | Jest — requires additional babel/transform config for Vite projects. Playwright — for E2E, not unit/component tests. |
| **Status** | Active |

---

### DEC-131 | Session Summary Card — Dev Mode Override
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | In `--dev` mode, SessionSummaryCard bypasses the market status gate so it's always visible for testing. Production behavior unchanged: card shows only when market is `after_hours` or `closed` AND trades exist for the current session. |
| **Rationale** | The card is untestable during market hours without a dev-mode override. Market status in dev mode was hardcoded to `open`, preventing the card from ever appearing. Dev-mode overrides follow the same pattern as existing mock data. |
| **Alternatives** | Manual market status override via URL param — acceptable but less discoverable. |
| **Status** | Active |

---

### DEC-132 | Pre-Databento Backtests Require Re-Validation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | All parameter optimization performed pre-Databento (ORB Breakout DEC-076, ORB Scalp DEC-127) was run against Alpaca historical data at 1-minute bar resolution. Parameters are provisional. When Databento activates (~Sprint 19), a dedicated re-validation pass will re-run VectorBT sweeps, walk-forward analysis, and cross-validation for all strategies with exchange-direct data. ORB Scalp additionally requires sub-minute data for meaningful backtesting. |
| **Rationale** | Alpaca historical data is SIP-quality but was fetched via REST (not the limited IEX stream). Databento provides exchange-direct proprietary feeds which may show different price dynamics, particularly at the open when ORB signals concentrate. The backtesting *infrastructure* and *methodology* are validated — only the parameter *values* are provisional. |
| **Status** | Active — trigger: Databento subscription activation |

---

### DEC-133 | CapitalAllocation Component — Track + Fill Donut with Bars Toggle
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Renamed AllocationDonut → CapitalAllocation. Two visualization modes toggled via SegmentedTab: (1) Track-and-fill donut — custom SVG with per-segment color-tinted track arcs at low opacity plus bright clockwise fill arcs proportional to deployment %, center stat shows total deployed %. (2) Horizontal stacked bars — one bar per strategy + reserve, labels above/below, deployed/available/throttled segments. Zustand store persists view preference (DEC-129 pattern). |
| **Rationale** | Original nested two-ring donut (outer = allocation, inner = deployment) created visual clutter — 6 competing elements at similar weight. Track-and-fill approach creates clear figure/ground: bright fills are the primary reading, tinted tracks are secondary context. Bars view provides precise per-strategy comparison. Toggle lets user pick preferred reading mode. |
| **Alternatives Rejected** | (1) Nested two-ring donut — too visually noisy. (2) Single donut + center stat only — loses per-strategy deployment detail. (3) Single donut with inside-to-outside fill levels — directionally confusing (fills should sweep clockwise like segments). |
| **Status** | Active |

---

### DEC-134 | Dashboard Grid — Three-Card Second Row + Market Regime Card
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Dashboard second row restructured from 2 cards (CapitalAllocation + Risk Budget at 1/3 + 2/3) to 3 equal-width cards (CapitalAllocation + Risk Budget + Market Regime). MarketRegimeCard shows current regime (RegimeClassifier data) with color-coded badge + description. At tablet/phone breakpoints, Market and Market Regime cards pair into an always-2-column row; they never stack to single column. |
| **Rationale** | Risk Budget card had excessive dead space at 2/3 width. Market Regime data already computed by Orchestrator (Sprint 17) — surfacing it adds genuine situational awareness. Market + Market Regime pairing at narrow widths keeps related status info together and avoids excessive vertical stacking on mobile. |
| **Status** | Active |

---

### DEC-135 | Orchestrator Status API — Deployment State Enrichment
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Enriched `GET /api/v1/orchestrator/status` response with per-strategy deployment state: `deployed_capital` (sum of entry_price × shares_remaining for open positions), `deployed_pct` (deployed_capital / total_equity), `is_throttled` (derived from throttle_action). Added top-level `total_deployed_capital` and `total_equity` fields. Computed from Order Manager open positions and broker account data. |
| **Rationale** | CapitalAllocation visualization requires deployment state to show how much of each strategy's allocation is currently in open positions. Computing server-side ensures consistency between donut and bars views. |
| **Status** | Active |

---

### DEC-136 | VwapReclaimStrategy — Standalone from BaseStrategy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | VwapReclaimStrategy inherits directly from BaseStrategy, NOT from OrbBaseStrategy. No shared base class with ORB family. If a second VWAP-based strategy (e.g., VWAP Fade) is built later, a VwapBaseStrategy ABC can be extracted at that point. |
| **Rationale** | Zero shared logic between VWAP Reclaim and ORB. ORB uses opening range formation, breakout detection, and OR state tracking. VWAP Reclaim uses a VWAP crossover state machine with pullback tracking. Premature extraction would create an abstraction with no concrete shared behavior. Follow the ORB pattern: extract after the second variant exists (DEC-120 extracted OrbBase after Scalp was designed). |
| **Status** | Active |

---

### DEC-137 | VWAP Reclaim Scanner — Reuse ORB Gap Watchlist
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | VWAP Reclaim reuses the same gap scanner watchlist as the ORB family. No independent scanner run. The strategy receives symbols via `set_watchlist()` from the Orchestrator (same as ORB/Scalp) and filters candidates through its internal state machine. |
| **Rationale** | Stocks that gap up strongly are the natural universe for VWAP pullback-and-reclaim patterns. The gap scanner already identifies stocks with institutional interest and elevated volume. A second scanner would duplicate effort and potentially create a different watchlist that misses the cross-strategy synergy (ORB trades the breakout, VWAP Reclaim trades the pullback on the same stocks). If VWAP Reclaim later needs non-gap stocks, a dedicated scanner can be added. |
| **Status** | Active |

---

### DEC-138 | VWAP Reclaim State Machine Design
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Per-symbol 5-state machine: WATCHING → ABOVE_VWAP → BELOW_VWAP → ENTERED / EXHAUSTED. BELOW_VWAP loops back to ABOVE_VWAP when a reclaim occurs without meeting all entry conditions (e.g., volume not confirmed), allowing multiple pullback attempts per symbol per day. EXHAUSTED is terminal — triggered when pullback depth exceeds `max_pullback_pct`. Entry requires candle CLOSE above VWAP (not intra-bar cross), consistent with ORB's breakout confirmation pattern. |
| **Rationale** | The loop-back from BELOW_VWAP → ABOVE_VWAP is critical — stocks often touch VWAP multiple times before the confirmed reclaim with volume. A single-attempt model would miss the highest-quality entries. EXHAUSTED state prevents chasing stocks in genuine sell-offs. Candle close confirmation reduces false signals and works correctly at 1-minute bar resolution. |
| **Status** | Active |

---

### DEC-139 | VWAP Reclaim Stop Placement — Pullback Swing Low
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Stop placed below the pullback swing low (lowest low during the below-VWAP period) with a small buffer (`stop_buffer_pct`, default 0.1%). Not VWAP-based. |
| **Rationale** | Three alternatives considered: (a) Stop below VWAP — rejected because VWAP moves intraday, creating a moving stop target; VWAP could also be very close to entry price, making risk per share tiny and position size enormous. (b) Fixed ATR-based stop — rejected because it doesn't relate to the trade's thesis. (c) Pullback swing low — chosen because it's a fixed reference point (known at entry time), represents natural support, and directly relates to the trade thesis (if the stock breaks below where the pullback bottomed, the mean-reversion has failed). |
| **Status** | Active |

---

### DEC-140 | VWAP Reclaim Position Sizing — Minimum Risk Floor
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Position sizing uses `effective_risk = max(risk_per_share, entry_price × 0.003)` as the denominator, capping position size when the stop is very close to entry. Prevents enormous positions from shallow pullbacks where the pullback low is near VWAP. |
| **Rationale** | Mean-reversion entries can have very tight stops. If a stock pulls back 0.2% below VWAP and reclaims, risk per share on a $100 stock is only $0.20, producing a 5,000-share position on $1,000 risk. The 0.3% floor caps this to ~333 shares. The Risk Manager's `max_single_stock_pct` (5%) provides account-level protection, but the strategy should self-limit to avoid sending oversized signals that Risk Manager must modify. |
| **Status** | Active |

---

### DEC-141 | VWAP Reclaim Cross-Strategy Policy — ALLOW_ALL
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | ALLOW_ALL duplicate stock policy (DEC-121) extends to VWAP Reclaim. ORB, ORB Scalp, and VWAP Reclaim can hold positions in the same symbol simultaneously, subject to `max_single_stock_pct` (5%) cross-strategy exposure cap. |
| **Rationale** | The strategies target different phases of the same momentum event: ORB catches the initial breakout (9:35–10:00), VWAP Reclaim catches the pullback recovery (10:00–12:00). Same-symbol positions across strategies represent intentional diversification across time and thesis, not redundant concentration. The 5% cap prevents excessive single-stock exposure regardless. |
| **Status** | Active |

---

### DEC-142 | Watchlist Sidebar (UX Feature 18-C) in Sprint 19
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | UX Feature 18-C (Watchlist Sidebar) included in Sprint 19 scope. 18-A (Position Cards with Mini-Charts) and 18-E (Notification Center) deferred to Sprint 20+. |
| **Rationale** | With three strategies sharing a watchlist, visibility into which symbols each strategy is tracking becomes operationally important. The sidebar also provides a natural home for VWAP Reclaim's per-symbol state machine status (WATCHING/ABOVE/BELOW/ENTERED), which is unique visual feedback not available elsewhere in the UI. 18-A and 18-E are valuable but less directly relevant to the three-strategy watchlist management need. |
| **Status** | Active |

---

### DEC-143 | Databento Activation Deferred to Sprint 20
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Databento subscription activation deferred from Sprint 19 to Sprint 20, amending DEC-097. Sprint 19 uses Alpaca historical data for backtesting and Alpaca paper trading for validation. |
| **Rationale** | VWAP Reclaim's 5–30 minute hold duration is well within 1-minute bar resolution — unlike ORB Scalp (DEC-127), bar resolution is not a limitation. Backtesting with Alpaca data produces directional results (subject to DEC-132 re-validation). Activating Databento with four strategies (after Sprint 20) gives more validation value per $199/month. No urgent data quality need for Sprint 19 specifically. |
| **Status** | Active — supersedes DEC-097 timing |

---

### DEC-144 | VectorBT VWAP Reclaim Sweep Architecture
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | VectorBT VWAP Reclaim sweep uses precompute+vectorize architecture: precompute entry candidates per day ONCE, filter by parameters at runtime, vectorized NumPy exit detection. |
| **Alternatives** | (1) Naive per-combination Python loops with DataFrame operations — rejected: ~500x slower. (2) Full vectorization across days — complexity not justified given single-entry-per-day semantics. |
| **Rationale** | Matches the performance pattern established in vectorbt_orb.py. Original naive implementation was prohibitively slow for the 768-combo × 29-symbol × 700-day grid. Precomputing entries per day (parameter-independent) and vectorizing exits achieves 29-symbol sweep in ~27 seconds. |
| **Status** | Active |

---

### DEC-145 | Walk-Forward Pipeline — VWAP Reclaim Dispatch
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Walk-forward pipeline extended with `--strategy vwap_reclaim` dispatch. In-sample: VectorBT sweep. Out-of-sample: Replay Harness. Parameter mapping: volume_multiplier → volume_confirmation_multiplier, target_r → target_1_r, time_stop_bars → time_stop_minutes. |
| **Alternatives** | Separate walk-forward scripts per strategy — rejected for code duplication. |
| **Rationale** | Unified walk-forward entry point (`walk_forward.py`) with strategy dispatch maintains single interface for all strategies. Parameter name mapping handles sweep-to-config translation. Fixed-params mode supported for comparison runs. |
| **Status** | Active |

---

### DEC-146 | VWAP Reclaim Backtest Results — Provisional
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | VWAP Reclaim backtest results accepted as provisional guidance, subject to Databento re-validation per DEC-132. Results: 35mo/29sym/768 combos: 59,556 trades, avg Sharpe 3.89, best 6.39. Walk-forward OOS Sharpe 1.49, P&L $15,820. |
| **Alternatives** | Wait for Databento data before any parameter selection — rejected: delays Sprint 19 completion. |
| **Rationale** | Results on Alpaca SIP data provide directional parameter guidance. Recommended params (pullback=0.001–0.003, bars=2–3, vol=1.0, target_r=1.5, time_stop=30) are thesis-consistent and stable across walk-forward windows. Re-validation with exchange-direct data mandatory before live capital deployment. |
| **Status** | Active — provisional per DEC-132 |

---

### DEC-147 | Watchlist Sidebar Responsive Architecture
| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Decision** | Watchlist Sidebar uses three-tier responsive layout: Desktop (≥1024px) = 280px collapsible inline sidebar. Tablet (640–1023px) = slide-out panel from right edge. Mobile (<640px) = full-screen overlay with FAB toggle. |
| **Alternatives** | (1) Single collapsible sidebar all breakpoints — rejected: mobile usability. (2) Bottom sheet for mobile — rejected: conflicts with bottom nav. |
| **Rationale** | Follows established Command Center responsive patterns. Inline sidebar on desktop preserves dashboard context. Slide-out panel on tablet balances space efficiency and accessibility. Full-screen overlay on mobile maximizes usable space for watchlist interaction. Zustand store manages state across breakpoints. TanStack Query 10s polling for live updates. |
| **Status** | Active |

---

### DEC-148 | VectorBT ↔ Live State Machine Divergences
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Two divergences between VectorBT sweep and live strategy identified and addressed: (1) ABOVE_VWAP → BELOW_VWAP transition: VectorBT uses `close <= vwap`, live originally used `close < vwap` — harmonized to `<=` in Session 11. (2) VectorBT uses single entry per day, live allows retry after failed conditions — documented, kept divergent (conservative direction for backtest). |
| **Alternatives** | (1) Keep both divergences undocumented — rejected: creates confusion when comparing backtest to live. (2) Make live single-entry-per-day — rejected: retry behavior is valuable for live trading. |
| **Rationale** | The `<=` vs `<` divergence could cause VectorBT to start pullback tracking while live doesn't on close==VWAP bars. Harmonizing to `<=` aligns the state machines. The single-entry divergence is acceptable because it makes backtest conservative (fewer entries than live could produce). |
| **Status** | Resolved (Session 11) |

---

### DEC-149 | VectorBT Performance Rule
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | `.claude/rules/backtesting.md` created mandating precompute+vectorize architecture for all future VectorBT sweeps. Performance benchmark: 29-symbol 35-month sweep must complete in <30 seconds. |
| **Alternatives** | Ad-hoc optimization per sweep — rejected: leads to repeated naive implementations. |
| **Rationale** | The naive per-combination loop pattern (vectorbt_vwap_reclaim.py original implementation) was ~500x slower. Codifying the precompute+vectorize pattern as a rule prevents regression in Sprint 20 (Afternoon Momentum) and future strategies. Exit priority rules (stop > target > time_stop > EOD with worst-case stop price) also documented to ensure conservative backtest assumptions. |
| **Status** | Active |

---

### DEC-150 | Watchlist UX Polish — Sparkline Removal + VWAP Distance
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Removed sparklines from watchlist items. Added `vwap_distance_pct` metric and compact single-letter strategy badges (O/S/V). Three rounds of iteration: v1 (density + sort), v2 (sparkline removal + VWAP distance), v3 (alignment + header + collapse button redesign as edge-mounted pill). |
| **Rationale** | Sparklines need 80–100px to be readable; at sidebar width (~280px minus padding) they were visual texture without actionable information. VWAP distance (e.g., "Below ↓0.3%") is the most actionable metric for the 10:00–12:00 VWAP Reclaim window — tells the operator instantly how close a symbol is to reclaim entry. Compact single-letter badges (fixed 20px width) replaced full-word badges for horizontal space savings. Green 3px left border on `entered` state items provides instant position identification without consuming layout space. Collapse button moved from circular overlay to slim vertical pill flush with sidebar edge — eliminates header icon collision. |
| **Alternatives** | Keep sparklines at reduced size (too noisy), show VWAP distance as separate column (too wide), use icons instead of letter badges (less scannable). |
| **Status** | Active |

---

### DEC-151 | Keyboard Shortcuts — Navigation + Watchlist Toggle
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Global keyboard shortcuts: `1`–`4` for page navigation (Dashboard, Trades, Performance, System), `w` for watchlist sidebar toggle. Implemented via `keydown` event listeners in Sidebar.tsx and WatchlistSidebar.tsx. Shortcuts suppressed when focus is in input/textarea elements. |
| **Rationale** | Power-user efficiency for single-operator system. Number keys match sidebar icon order. `w` is mnemonic for "watchlist." During overnight trading sessions (10:30 PM–5:00 AM Taipei time), quick keyboard navigation reduces friction. |
| **Status** | Active |

---

### DEC-152 | Afternoon Momentum — Standalone from BaseStrategy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | AfternoonMomentumStrategy inherits from BaseStrategy directly, not from OrbBaseStrategy or any shared consolidation base. |
| **Rationale** | Despite structural similarity to ORB (range → breakout), the range formation is fundamentally different. ORB: predefined time window. Afternoon Momentum: organically formed midday consolidation. Follows VWAP Reclaim precedent (DEC-136). Shared base extracted later if needed (DEF-022 pattern). |
| **Status** | Active |

---

### DEC-153 | Consolidation Detection — High/Low Channel + ATR Filter
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Consolidation identified by tracking high/low of midday bars (12:00–2:00 PM), confirmed by midday_range / ATR-14 < threshold (default 0.75). |
| **Rationale** | Simple, testable, vectorizable. ATR filter confirms range is genuinely tight vs. just a low-volatility stock. Bollinger Bands require new indicator computation. Moving average convergence too indirect. |
| **Status** | Active |

---

### DEC-154 | Afternoon Momentum Scanner — Gap Watchlist Reuse
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Afternoon Momentum reuses the same gap scanner criteria as ORB and VWAP Reclaim (min_gap=2%, min_price=$10, max_price=$200, min_volume=1M, min_rvol=2.0). |
| **Rationale** | Gap watchlist identifies institutional-quality stocks with catalysts — natural candidates for midday consolidation and afternoon breakout. Consolidation detection is the second filter. Matches DEC-137 scanner reuse pattern. |
| **Status** | Active |

---

### DEC-155 | Afternoon Momentum State Machine — 5 States
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | 5-state machine: WATCHING (before 12:00 PM), ACCUMULATING (tracking midday range), CONSOLIDATED (range confirmed tight), ENTERED (position taken, terminal), REJECTED (range too wide, terminal). |
| **Rationale** | ACCUMULATING → CONSOLIDATED split prevents false entries on insufficient data. min_consolidation_bars gate ensures meaningful range measurement. CONSOLIDATED continues updating range, so widening can still reject. Parallels VWAP Reclaim 5-state pattern (DEC-138). |
| **Status** | Active |

---

### DEC-156 | Afternoon Momentum Entry Conditions — 8 Simultaneous Requirements
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Entry requires ALL: (1) CONSOLIDATED state, (2) time 2:00–3:30 PM, (3) candle close > consolidation_high, (4) volume ≥ multiplier × avg, (5) chase protection, (6) risk > 0, (7) internal risk limits pass, (8) position count limit. |
| **Rationale** | Same comprehensive gating pattern as ORB and VWAP Reclaim. Close-based confirmation (not intra-bar) is consistent across all strategies. |
| **Status** | Active |

---

### DEC-157 | Afternoon Momentum Stop and Target Design
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Stop below consolidation_low with buffer (0.1%). T1=1.0R (50%), T2=2.0R (50%). Dynamic time stop: min(max_hold_minutes, seconds_until_3:45_PM). |
| **Rationale** | Same T1/T2 pattern proven across three strategies. Dynamic time stop handles EOD proximity — a 3:25 PM entry gets 20-min time stop, not 60-min. Trailing stop deferred (DEC-158). |
| **Status** | Active |

---

### DEC-158 | Trailing Stop — Deferred to V2
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | No trailing stop mechanism in V1 of Afternoon Momentum. |
| **Rationale** | Trailing stops touch Order Manager, Risk Manager, backtesting, and VectorBT sweep architecture — cross-cutting complexity. T1/T2 fixed targets are proven. If walk-forward shows afternoon moves routinely exceed T2, trailing stop becomes a future sprint item. |
| **Status** | Active |

---

### DEC-159 | Afternoon Momentum EOD Handling
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Last entry 3:30 PM. Force close 3:45 PM. Time stop at signal creation = min(max_hold_minutes × 60, seconds_until_3:45_PM). Order Manager EOD flatten is safety net. |
| **Rationale** | Dynamic time stop calculation ensures no position is targeted for closure after the hard cutoff. Earliest-exit-wins logic in Order Manager already handles overlap between time stop and EOD flatten. |
| **Status** | Active |

---

### DEC-160 | Cross-Strategy Interaction — ALLOW_ALL, Time-Separated
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Same ALLOW_ALL duplicate stock policy (DEC-121) for Afternoon Momentum. No additional cross-strategy restrictions. |
| **Rationale** | Time windows are well-separated: ORB/Scalp done by ~10:15 AM, VWAP Reclaim done by ~12:30 PM, Afternoon Momentum starts at 2:00 PM. Cross-strategy collisions effectively impossible. 5% max_single_stock_pct cap remains as safety net. |
| **Status** | Active |

---

### DEC-161 | Databento Activation — Deferred to Sprint 21
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Databento subscription not activated for Sprint 20. Defer to Sprint 21 (analytics sprint). |
| **Rationale** | Saves $199/month. Sprint 20 uses Alpaca Parquet data like all other strategies. All results provisional per DEC-132. Databento most valuable when four strategies are built AND analytics toolkit is ready for serious validation. Amends DEC-143. |
| **Status** | Active |

---

### DEC-162 | VectorBT Afternoon Momentum Divergences Harmonized
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | VectorBT Afternoon Momentum sweep updated to track running midday_low and max_consolidation_ratio through afternoon bars, matching live strategy's CONSOLIDATED state behavior. Remaining divergence: VectorBT single entry per day vs live retry. ATR calculation uses SMA(14) vs production Wilder's EMA (same class as DEC-074). |
| **Rationale** | Aligns backtest fidelity with live behavior for stop placement and rejection logic. Single-entry-per-day is conservative (VectorBT produces fewer trades than live might). ATR method difference acceptable — consolidation ratio thresholds will be recalibrated with Databento data (DEC-132). |
| **Status** | Active |

---

### DEC-163 | Expanded Vision — AI-Enhanced Trading Intelligence Platform

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Expand ARGUS from a 5-strategy rules-based system to a 15+ pattern AI-enhanced trading intelligence platform. Core additions: Setup Quality Engine (composite 0–100 scoring), Order Flow Model (Databento L2/L3), NLP Catalyst Pipeline (free sources + Claude API), Dynamic Position Sizer, expanded Pattern Library (15+ types), Learning Loop (outcome → score refinement), Pre-Market Intelligence Engine (4:00 AM → 9:25 AM automated pipeline). Target: 5–10%+ monthly returns on deployed capital at $100K–$500K scale. |
| **Rationale** | Current rules-based architecture applies uniform filters and sizing to every setup. Top discretionary traders achieve dramatically higher returns by grading setup quality, adjusting size dynamically, reading order flow, and covering more patterns simultaneously. Every component of that discretionary edge is decomposable into quantifiable signals that ARGUS can measure — and measure across more stocks simultaneously than any human. The current architecture (Event Bus, broker abstraction, strategy abstraction, data provider abstraction) supports this evolution. |
| **Scope** | Phases B–D in Expanded Roadmap. ~16 new sprints (23–36+). ~2–3 months Build Track. Infrastructure cost increases from $199/mo to ~$449–499/mo at full scale. |
| **Impact** | Bible §4, §5, §9, §18. Architecture §3. Sprint Plan Sprints 23–36+. All six core docs. |
| **Status** | Active |
| **References** | `docs/research/ARGUS_Expanded_Roadmap.md` |

---

### DEC-164 | News/Catalyst Data — Free Sources First, Paid Later

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | NLP Catalyst Pipeline starts with free data sources: SEC EDGAR (8-K filings, Form 4 insider transactions), Finnhub (company news, earnings/FDA/IPO calendars, analyst recommendations, free tier 60 calls/min), and Financial Modeling Prep (earnings calendar, press releases, free tier 250 calls/day). Claude API performs catalyst classification and quality scoring. Paid news services (Benzinga Pro via IQFeed, ~$200/mo) deferred until free sources prove insufficient — trigger: >30% unclassified catalyst rate over 20 trading days. |
| **Rationale** | ARGUS's pre-market use case (4:00–9:30 AM research) doesn't require sub-second news latency — catalysts happened overnight. Free sources provide structured SEC filings (highest reliability), ticker-tagged news (Finnhub), and calendar data (FMP). Claude API classifies and scores catalysts from raw headlines, replacing the pre-tagging Benzinga provides. Saves ~$200/month. |
| **Amends** | Bible §18.2 Tier 2 data source priority. Does NOT change IQFeed plans for forex/breadth (future). |
| **Status** | Active |

---

### DEC-165 | L2 Data for All Watchlist Symbols

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Subscribe to Databento L2 (MBP-10, 10 depth levels) for all watchlist symbols. Watchlist rebuilt fresh each trading day during pre-market scanning (4:00 AM → 9:25 AM). L2 subscriptions activate at watchlist lock (9:25 AM), deactivate EOD. Databento Standard plan includes L2/L3 at no additional cost; constraint is session count (10 simultaneous), not symbol count within a session. ARGUS uses 1 session with Event Bus fan-out. |
| **Rationale** | Order flow intelligence requires L2 depth data. Full-watchlist subscription (typically 15–25 stocks) ensures no opportunity missed. Single session handles all symbols. |
| **Status** | Superseded by DEC-237 (Standard plan does NOT include live L2/L3) |

---

### DEC-166 | Short Selling Introduction — Sprint 28

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Short selling infrastructure (locate/borrow tracking, inverted risk logic, short-specific Risk Manager rules) in Sprint 28. First short strategy: Parabolic Short. Long-only strategies unaffected. |
| **Rationale** | Short selling inverts several risk assumptions (unlimited loss potential, borrow costs, short squeeze risk). Adding after long-only system proven (15+ sprints of validation) and alongside L3 order flow data provides data foundation for safe short entries. |
| **Status** | Active |

---

### DEC-167 | Pattern Library — Build in Batches, Validate in Parallel

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | New patterns built in batches of 3–4 per sprint, each through Incubator Pipeline stages 1–3 (Concept → Exploration → Validation). Paper trading validation runs in parallel. Patterns that don't pass walk-forward are suspended, not removed. Walk-forward validation non-negotiable (DEC-047). |
| **Rationale** | One-at-a-time building stretches timeline to 6+ months. Batch building with parallel validation matches sprint velocity. Quality gates maintained. |
| **Status** | Active |

---

### DEC-168 | UI/UX Integration Principle — Intelligence Visible Everywhere

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | New intelligence features (Quality Engine, Order Flow, Catalyst Pipeline, Dynamic Sizing, Learning Loop) integrate into existing Command Center pages via enrichment and progressive disclosure — not as separate siloed pages. Every intelligence signal is visible where the user already looks. Progressive disclosure: summary badge → click for breakdown → deep dive for analysis. |
| **Rationale** | The design north star ("Bloomberg Terminal meets modern fintech") demands information density without navigation tax. A quality score is most useful on the position card. Order flow is most useful in the stock detail panel. |
| **Status** | Active |

---

### DEC-169 | Seven-Page Application Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Command Center expands from 4 pages to 7. Existing pages refined/narrowed, 3 new pages added. Navigation: icon sidebar (desktop) groups by concern, bottom tab bar (mobile) shows 5 primary tabs + "More" menu. |
| **Pages** | (1) **Dashboard** — pure ambient awareness, narrower scope, pre-market mode before 9:30 AM. (2) **Trade Log** — unchanged, gains quality/catalyst/pattern columns. (3) **Performance** — analytics-focused, adds quality/catalyst/pattern breakdowns. (4) **Orchestrator** — NEW: operational command center, all decisioning visible and manually overridable, capital allocation controls, decision stream, risk gauges, emergency controls. (5) **Pattern Library** — NEW: strategy encyclopedia, master-detail layout, every strategy's parameters/performance/backtests/intelligence visible, incubator pipeline visualization. (6) **The Debrief** — NEW: knowledge accumulation surface, daily briefings (pre/post-market), research library, learning journal. (7) **System** — narrowed to infrastructure health only. |
| **Rationale** | The 4-page structure designed for a simpler system. Dashboard tried to be ambient + operational. System mixed infrastructure health with strategy management. No home for accumulated knowledge/research. Three new pages solve: Orchestrator (operational controls), Pattern Library (strategy deep dives), The Debrief (knowledge accumulation). Existing pages get narrower, more focused scope. |
| **Nav (desktop)** | Icon sidebar grouped: Monitor (Dashboard, Trades, Performance) → Operate (Orchestrator, Patterns) → Learn (Debrief) → Maintain (System). Keyboard shortcuts 1–7. |
| **Nav (mobile)** | 5 bottom tabs: Dashboard, Trades, Orchestrator, Patterns, More (→ Performance, Debrief, System). During market hours the 5 you need most are always one tap away. |
| **Status** | Active |

---

### DEC-170 | Contextual AI Copilot — Claude Everywhere

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Claude is accessible from every page in the Command Center via a persistent, context-aware chat interface. Not a separate "AI page" — a slide-out panel (desktop: right side, 35% width; mobile: full-screen overlay) triggered by a floating button or keyboard shortcut (`c`). When opened, Claude automatically receives context about what page the user is on, what data is visible, and any selected entity (trade, strategy, position, report). Chat history persists in The Debrief's Learning Journal. Claude can take actions from chat (propose allocation changes, generate reports, annotate trades) that go through the standard approval workflow. |
| **Rationale** | Having to leave the app to talk to Claude breaks operational flow. The user operates from Taipei during US market hours (10:30 PM – 5:00 AM local) — context-switching between ARGUS and Claude.ai wastes critical attention. Contextual AI means Claude already knows what you're looking at. "Why did we skip this setup?" asked from the Watchlist sidebar gives Claude the symbol, quality score, and order flow data automatically. "Analyze this strategy's performance" asked from Pattern Library gives Claude the strategy ID and time range. The chat panel is the AI Layer's primary user interface. |
| **Context injection** | Each page provides a context payload when chat opens: Dashboard → current positions, P&L, regime. Orchestrator → allocation state, recent decisions, risk utilization. Pattern Library → selected strategy ID, parameters, recent performance. The Debrief → current document/briefing being viewed. Trade Detail Panel → full trade data, quality score, catalyst, order flow snapshot. |
| **Action capabilities** | From chat, Claude can: generate a report (saved to The Debrief), propose parameter changes (approval flow), propose allocation override (approval flow), annotate a trade (saved to Learning Journal), trigger a backtest comparison, answer questions about any system data. All actions logged in audit trail. |
| **Boundaries** | Claude never executes trades directly from chat. All trade-affecting proposals go through Risk Manager gates and approval workflow. Chat is not a "god mode" — it's a contextual assistant that works within the existing control framework. |
| **Implementation** | Sprint 22 (AI Layer MVP) builds the API infrastructure. Chat panel UI built in Sprint 21d as a shell (initially shows "AI Layer coming in Sprint 22" placeholder). Full chat functionality activates when Sprint 22 completes. |
| **Status** | Active |

---

### DEC-171 | Sprint 21 Split — Four Sub-Sprints for Page Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Sprint 21 split into four sub-sprints to establish the 7-page architecture before intelligence features are added in Sprints 23+. (a) Pattern Library page + stock detail panel. (b) Orchestrator page + control migration. (c) The Debrief page + research library. (d) Dashboard refinement + Performance analytics + System cleanup + AI Copilot shell + nav restructure. |
| **Rationale** | Original Sprint 21 (~80–100h) was already flagged for potential split (RSK-025). Expanding from 4 to 7 pages requires establishing the page structure first so intelligence sprints (23–32) add features to the correct locations. Each sub-sprint is independently valuable and demoable. |
| **Amends** | DEC-096, DEC-108. |
| **Status** | Active |

---

### DEC-172 | Strategy Metadata Enrichment
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Extend `GET /api/v1/strategies` with `time_window`, `family`, `description_short`, `performance_summary`, `backtest_summary`. Single enriched endpoint rather than separate `/patterns` route. Performance summary computed via TradeLogger per-strategy queries at request time. |
| **Rationale** | Avoids naming split between "strategies" (operational) and "patterns" (library) — they're the same objects. Single endpoint reduces client complexity. Per-strategy TradeLogger queries are fast (4 SQLite queries, sub-millisecond each). |
| **Alternatives** | (B) Separate `/api/v1/patterns` endpoint — rejected, creates artificial distinction. (C) Composite client-side join of `/strategies` + `/performance` — rejected, adds latency and complexity. |
| **Status** | Active |

---

### DEC-173 | Pipeline Stage in Config YAML
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Store strategy pipeline stage as `pipeline_stage` field in each strategy's YAML config. Manual update. 10-stage vocabulary: concept, exploration, validation, ecosystem_replay, paper_trading, live_minimum, live_full, active_monitoring, suspended, retired. |
| **Rationale** | Simple, config-driven, consistent with ARGUS's YAML-first design. Only 4 strategies currently — DB-backed solution premature. Can migrate to database when 15+ strategies make YAML editing cumbersome. |
| **Alternatives** | (B) Database-backed — rejected as premature for 4 strategies. (C) Computed from system state — rejected, insufficient granularity (can't distinguish "validation" from "exploration"). |
| **Status** | Active |

---

### DEC-174 | Strategy Family Classification
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Store strategy family as `family` field in config YAML. Values: `orb_family`, `momentum`, `mean_reversion`, `uncategorized`. Display names mapped in frontend. Mapping: ORB Breakout/Scalp → orb_family, VWAP Reclaim → mean_reversion, Afternoon Momentum → momentum. |
| **Rationale** | Consistent with DEC-173 (config-driven). YAML values are stable identifiers; UI labels are flexible. Same file, same update workflow. |
| **Status** | Active |

---

### DEC-175 | Strategy Spec Sheets Served as Markdown
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | New `GET /api/v1/strategies/{strategy_id}/spec` endpoint serves strategy spec sheets from `docs/strategies/STRATEGY_*.md` as raw markdown. Frontend renders with react-markdown + remark-gfm. Overview tab combines live parameter table (from YAML config) with rendered spec sheet (from markdown file). |
| **Rationale** | Avoids duplicating well-maintained strategy documentation. Spec sheets are the authoritative source — rendering them directly ensures consistency. react-markdown is lightweight (~12KB gzipped). Markdown files exist on disk in all modes (dev and production). |
| **Alternatives** | (A) Hardcoded frontend descriptions — rejected, content duplication. (B) API returns structured description object — rejected, more work for same result, loses rich formatting. |
| **Status** | Active |

---

### DEC-176 | Backtest Tab as Structured Placeholder
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Backtest tab shows static summary from `backtest_summary` config section (status, WFE, OOS Sharpe, trade count, data months, last run date). No interactive backtest explorer in Sprint 21a — deferred to Sprint 21d. Existing walk-forward/VectorBT reports remain in docs/backtesting/ as files. |
| **Rationale** | Ingesting backtest reports into a queryable API is a data pipeline project beyond Sprint 21a scope. Config-based summary provides the key metrics users need. Interactive explorer is Sprint 21d scope when analytics infrastructure is richer. |
| **Status** | Active |

---

### DEC-177 | SlideInPanel Extraction + Symbol Detail Architecture
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Extract shared SlideInPanel component from TradeDetailPanel. Handles animation, backdrop, close behavior, responsive sizing (desktop: right 40%, mobile: bottom 90vh). TradeDetailPanel refactored to use SlideInPanel as wrapper. SymbolDetailPanel is a new consumer. SymbolDetail triggered via `symbolDetailUI` Zustand store — any component can call `open(symbol)` to trigger the panel globally. |
| **Rationale** | Two panels (trade detail, symbol detail) share identical slide-in UX. Extracting the shell eliminates duplication and ensures consistent animation behavior. Global Zustand store enables "click any symbol anywhere" without prop drilling. |
| **Status** | Active |

---

### DEC-178 | Fundamentals Section Deferred to Sprint 23
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Symbol Detail Panel in Sprint 21a ships without fundamentals section (market cap, float, sector, short interest). No data source exists for this data until Finnhub/FMP integration in Sprint 23 (NLP Catalyst Pipeline). Panel ships with: candlestick chart, trading history, position detail. |
| **Rationale** | Building UI for data we can't populate is wasted effort. Clean panel with available data is better than empty sections. Fundamentals section adds naturally in Sprint 23 when CatalystService provides the data. |
| **Status** | Active |

---

### DEC-179 | Incubator Pipeline Responsive Design
| Field | Value |
|-------|-------|
| **Date** | 2026-02-26 |
| **Decision** | Desktop/tablet (≥640px): Connected pipeline with chevron arrows, stage nodes with counts. HTML/CSS flexbox implementation. Mobile (<640px): Compact horizontal scrollable pill row. Click-to-filter toggles: click stage to filter card grid, click same stage to clear filter. |
| **Rationale** | Connected pipeline gives Pattern Library a distinctive visual signature on desktop. Compact pills save vertical space on mobile. HTML/CSS over SVG avoids complexity for what's essentially a styled flex row. |
| **Status** | Active |

---

### DEC-180 | Keyboard Shortcuts Extended to 1–5
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Keyboard shortcuts dynamically mapped to `NAV_ITEMS.length`. With Pattern Library as 5th page, shortcuts are now 1–5 (Dashboard, Trades, Performance, Patterns, System). `w` for watchlist unchanged. |
| **Rationale** | Implementation already dynamic. Doc-only update to match reality. |
| **Amends** | DEC-151 (was 1–4). |
| **Status** | Active |

---

### DEC-181 | Auto-Discover Strategy Spec Sheets
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Strategy spec sheet resolution uses naming convention (`strat_X` → `STRATEGY_X.md`) instead of hardcoded map. New strategies only need to place a spec file following the convention. |
| **Rationale** | With 15+ strategies planned (DEC-163), a hardcoded map becomes a maintenance burden. Convention-based discovery scales without code changes. |
| **Amends** | DEC-175 (spec sheet serving approach unchanged, discovery mechanism updated). |
| **Status** | Active |

---

### DEC-182 | Z-Index Layering Hierarchy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Explicit z-index hierarchy: MobileNav/EmergencyControls z-50, SlideInPanel z-50/z-40 (panel/backdrop), Sidebar z-40, WatchlistSidebar mobile z-40 (demoted from z-50). SlideInPanel always renders above WatchlistSidebar. |
| **Rationale** | Prevents unpredictable stacking when both panels open on mobile. SlideInPanel is a focused inspection tool that should always be on top. |
| **Status** | Active |

---

### DEC-183 | Compact Chart Prop Pattern
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | EquityCurve and DailyPnlChart accept `compact` boolean prop for reduced padding and height. Used in PerformanceTab (Pattern Library detail) to fit charts in constrained space. Replaces fragile CSS override pattern. |
| **Rationale** | CSS child selector overrides (`[&_.p-4]:p-3`) are brittle. Explicit prop is self-documenting and won't break silently on refactor. |
| **Status** | Active |

---

### DEC-184 | Document Modal Reader Pattern
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Strategy documentation rendered as document index with metadata (title, word count, reading time, last modified) plus full-screen modal reader. Replaces inline markdown rendering. |
| **Rationale** | Strategy specs are 500+ words. Inline rendering consumes too much vertical space and makes the Overview tab unwieldy. Modal provides focused reading experience with escape/backdrop dismiss. Metadata helps users gauge document length before opening. |
| **Status** | Active |

---

### DEC-185 | Arrow Key Navigation in Pattern Library
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Pattern Library supports arrow key navigation: ↑/↓ to navigate cards, ←/→ to switch tabs (when detail panel open), Escape to clear selection. Selection auto-scrolls into view. |
| **Rationale** | Accessible keyboard navigation without interfering with text input. Combined with existing 1–5 page navigation (DEC-180), enables full keyboard-only operation. Vim-style j/k/h/l removed to avoid conflicts. |
| **Status** | Active |

---

### DEC-186 | Orchestrator Page Layout — Vertical Flow
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Orchestrator page uses full-width vertical flow layout (no master-detail). Sections top-to-bottom: RegimePanel, StrategyCoverageTimeline, CapitalAllocation, StrategyOperationsGrid, DecisionTimeline, GlobalControls. |
| **Alternatives Considered** | (A) Three-column layout (Capital | Decisions | Risk) — original 21b spec in sprint plan. (B) Master-detail with strategy list + detail panel. (C) Tab-based sections. |
| **Rationale** | Vertical flow matches the "progressive disclosure" principle (DEC-109): ambient summary at top, operational detail in middle, controls at bottom. Master-detail would hide the coverage timeline and decision log behind clicks. Three-column was too dense on tablet. The operator reads this page top-to-bottom during market hours — the layout should match that flow. |
| **Status** | Active |

---

### DEC-187 | Throttle Override Design
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Throttle override requires duration selection (30 min / 1 hour / rest of day) + written reason + confirmation dialog. Override stored in-memory as `_override_until` dict on Orchestrator. Logged as `throttle_override` decision for audit trail. Override checked in `_calculate_allocations` — active override converts REDUCE/SUSPEND to NONE. |
| **Alternatives Considered** | (A) One-click instant override lasting until next poll cycle. (B) Persistent override stored in DB surviving restarts. (C) No override — only manual resume via pause/resume. |
| **Rationale** | This is overriding risk controls protecting capital. The UI must feel appropriately weighty — not a casual toggle. Duration prevents "forgot to un-override" scenarios. Reason creates accountability in the decision log. In-memory storage is acceptable because overrides are inherently session-scoped (a restart should re-evaluate from scratch). |
| **Status** | Active |

---

### DEC-188 | Strategy Coverage Timeline — Custom SVG
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Strategy coverage timeline uses custom SVG with fixed 9:30–16:00 time axis. Per-strategy colored bars from earliest_entry to latest_entry. "Now" marker as red dashed vertical line. Throttled/paused strategies at reduced opacity. Strategy colors match Badge system (ORB=blue, Scalp=purple, VWAP=teal, Momentum=amber). |
| **Alternatives Considered** | (A) D3.js time-scale visualization. (B) CSS Grid with percentage widths. (C) Recharts bar chart. |
| **Rationale** | The visualization is simple: fixed time axis, 4–18 bars, one moving marker. D3 adds a large dependency for something achievable in ~100 lines of SVG math. CSS Grid can't easily do the "now" marker overlay. Custom SVG follows the proven pattern from CapitalAllocation donut (DEC-133). Time-to-pixel mapping is trivial: `(minuteOfDay - 570) / 390 * width`. |
| **Status** | Active |

---

### DEC-189 | Mobile Navigation with 6 Pages
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Mobile bottom nav expanded from 5 to 6 items with abbreviated labels ("Dash", "Trades", "Perf", "Patterns", "Orch", "System") at 9px text. All 6 items visible — no "More" menu. |
| **Alternatives Considered** | (A) 5 items + "More" menu hiding Orchestrator and/or System. (B) Keep full labels and allow horizontal scroll. (C) Context-dependent nav showing different items per page. |
| **Rationale** | All 6 pages are frequently accessed — hiding any behind "More" adds friction during trading hours. Abbreviated labels at 9px fit within the 393px iPhone width. "More" menu restructure deferred to Sprint 21d when the 7th page (The Debrief) is added — at 7 pages, "More" becomes necessary. |
| **Status** | Active |

---

### DEC-190 | Session Phase Computation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Session phase computed server-side from current ET time. Six phases: pre_market (before 9:30), market_open (9:30–11:30), midday (11:30–14:00), power_hour (14:00–16:00), after_hours (16:00–20:00), market_closed (after 20:00 or weekends). Included in orchestrator status response. |
| **Alternatives Considered** | (A) Client-side computation. (B) Phase derived from strategy activity. (C) Manual phase selection. |
| **Rationale** | Server-side ensures consistency — all clients see the same phase. Time-based is deterministic and requires no state. Phase boundaries align with trading conventions: market_open covers the highest-activity morning period, power_hour captures the afternoon surge. |
| **Status** | Active |

---

### DEC-191 | Regime Input Display — Client-Side Scoring
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | RegimeInputBreakdown component computes trend score, volatility bucket, and momentum confirmation client-side from the raw indicator values already in the orchestrator status response. Displays each factor with its directional assessment (bullish/bearish/neutral). |
| **Alternatives Considered** | (A) Backend computes and returns scoring breakdown as separate fields. (B) Display only raw values without interpretation. (C) Full diagnostic with all thresholds and intermediate calculations. |
| **Rationale** | The raw indicator values (spy_price, spy_sma_20, spy_sma_50, spy_roc_5d, spy_realized_vol_20d) are already in the API response. The scoring logic is simple and deterministic (trend: compare price vs SMAs; vol: compare to fixed thresholds; momentum: compare ROC to ±1%). Computing client-side avoids API schema changes and keeps the scoring visible/debuggable in the UI code. Option (B) would show numbers without "so what?" context. Option (C) is too noisy for an at-a-glance display. |
| **Status** | Active |

---

### DEC-192 | Orchestrator Hero Row Layout
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Sprint** | 21b (review) |
| **Decision** | Orchestrator page top section uses a 2-column hero row: left column stacks SessionOverview (aggregated daily metrics) + RegimePanel, right column holds CapitalAllocation donut. Left column uses flex-1 on RegimePanel to match right column height. |
| **Rationale** | Answers three key questions above the fold: how's the day going, what's the market doing, where's the capital. Previous layout had CapitalAllocation + SessionOverview in a separate row below the timeline, wasting vertical space. Stacking SessionOverview + RegimePanel naturally matches donut height. Mobile stacks: SessionOverview → RegimePanel → CapitalAllocation. |
| **Alternatives** | (1) Three separate full-width rows (too much scrolling), (2) CapitalAllocation full-width with bars view (wasted horizontal space for donut) |
| **Status** | Active |

---

### DEC-193 | Strategy Display Config Consolidation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Sprint** | 21b (review) |
| **Decision** | Unified `strategyConfig.ts` with `STRATEGY_DISPLAY` record containing name, shortName, letter, color, tailwindColor, badgeId for all strategies. Helper functions: `getStrategyDisplay()`, `getStrategyBorderClass()`, `getStrategyBarClass()`, `getStrategyColor()`. All components import from shared config. Tailwind classes kept as full static strings for purge compatibility. |
| **Rationale** | Strategy colors and names were duplicated across StrategyCoverageTimeline, StrategyOperationsCard, and ThrottleOverrideDialog with slight inconsistencies. Single source of truth scales to 15+ strategies without per-component updates. |
| **Status** | Active |

---

### DEC-194 | Decision Log Newest-First Ordering
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Sprint** | 21b (review) |
| **Decision** | DecisionTimeline sorts newest-first so latest orchestrator decisions appear at top without scrolling. Subtitle shows "X today · newest first" to indicate ordering. |
| **Rationale** | Orchestrator page is an operational dashboard — the question is always "what just happened?" Chronological reading order suits The Debrief page (post-session review), not live operations. |
| **Status** | Active |

---

### DEC-195 | Regime Card Gauge Redesign + Session Phase in Header
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Sprint** | 21b (review) |
| **Decision** | RegimePanel redesigned: regime badge as hero element, three visual gauge bars (Trend, Vol, Momentum) with positioned marker dots on red→yellow→green gradient. Normalization: Trend (-2 to +2 → 0-1), Volatility (0-50% inverted, low vol = green/right), Momentum (-5% to +5% ROC → 0-1). Scale labels: Bear/Bull, Crisis/Calm, Bearish/Bullish. Session phase badge extracted to `SessionPhaseBadge` component and moved to page header next to "Orchestrator" title with countdown timer. |
| **Rationale** | Previous text-row layout with check/X icons was a data dump — no instant gut feel. Gauge bars provide immediate visual read of market state. Session phase applies to entire page, not just regime card. |
| **Alternatives** | (1) Keep text rows with better formatting (rejected — still requires reading), (2) Circular gauges/dials (rejected — take more horizontal space than linear bars) |
| **Status** | Active |

---

### DEC-196 | Journal Entry Types — Updated
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Journal entry_type values updated from original schema ('observation', 'analysis', 'decision', 'insight') to ('observation', 'trade_annotation', 'pattern_note', 'system_note'). Schema DROP + recreate since table was never populated. |
| **Rationale** | New types better reflect actual usage patterns: observations for general notes, trade annotations for per-trade learning, pattern notes for strategy refinement, system notes for platform/infrastructure observations. |
| **Status** | Active |

---

### DEC-197 | Briefings Table Schema
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | New `briefings` table with UNIQUE(date, briefing_type) constraint. Two types: pre_market and eod. Three statuses: draft, final, ai_generated. Template-based creation generates markdown section headers server-side. |
| **Rationale** | One briefing per type per day enforces discipline. Template generation ensures consistent structure without requiring users to remember section headers. ai_generated status prepares for Sprint 22 AI Layer. |
| **Status** | Active |

---

### DEC-198 | Research Library — Hybrid Filesystem + Database Source
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Research Library serves documents from two sources: filesystem (auto-discovered from docs/research/, docs/strategies/, docs/backtesting/) and database (user-created via UI). Filesystem docs are read-only with stable IDs (fs_{category}_{filename}). Database docs support full CRUD with categories and tags. |
| **Rationale** | Repo documentation should be accessible without duplication. Database docs enable user-created research notes and future AI-generated reports. Hybrid approach serves both needs. |
| **Status** | Active |

---

### DEC-199 | Navigation — 7 Pages
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Command Center expanded to 7 pages: Dashboard, Trade Log, Performance, Pattern Library, Orchestrator, The Debrief, System. GraduationCap icon for Debrief. Keyboard shortcuts 1–7. Mobile nav: Dash/Trades/Perf/Patterns/Orch/Debrief/System. |
| **Rationale** | The Debrief is the 6th functional page (before System). Positioned after Orchestrator because it's the knowledge/review layer accessed after operational monitoring. Mobile labels abbreviated to fit 7 items. |
| **Amends** | DEC-169 (was 6 pages built, now 7 of 7), DEC-180 (shortcuts 1–5 → 1–7), DEC-189 (mobile 6-tab → 7-tab) |
| **Status** | Active |

---

### DEC-200 | Search — LIKE Queries Over FTS5
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Full-text search across debrief content (briefings, journal, documents) uses comprehensive LIKE queries across title+content+tags columns. FTS5 virtual tables not implemented. |
| **Rationale** | At <1,000 entries, LIKE '%term%' is instant. FTS5 adds virtual table creation, sync triggers on INSERT/UPDATE/DELETE, rebuild commands, different query syntax, and CI compatibility concerns for zero user-visible benefit at current scale. Can be swapped in as a backend optimization if search performance degrades at >10K entries. |
| **Resolves** | DEF-026 (FTS5 deferred → replaced with LIKE search, which is the shipped solution) |
| **Status** | Active |

---

### DEC-201 | Journal Trade Linking — Full UI in Sprint 21c
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Journal trade linking includes full search UI (TradeSearchInput component) in Sprint 21c. Search trades by symbol, select from dropdown, display linked trades as removable chips. |
| **Rationale** | Trade annotations without trade linking have limited value. The search component (~200 lines) is tractable within sprint scope and completes the journal's core value proposition. |
| **Resolves** | DEF-027 (trade linking UI deferred → now included) |
| **Status** | Active |

---

### DEC-202 | ApiError Class for HTTP Status Preservation
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Custom `ApiError` class in `client.ts` preserves HTTP status code on API errors. `fetchWithAuth` throws `ApiError(message, status)` instead of plain `Error`. Consumers check `error.status` for status-specific handling (e.g., 409 Conflict). |
| **Rationale** | Plain `Error` objects lose HTTP status codes, making status-specific error handling impossible. Discovered when 409 Conflict detection in BriefingList silently failed — `error.status === 409` was always `undefined`. Pattern applies to all future API error handling. |
| **Status** | Active |

---

### DEC-203 | Batch Trade Fetch Endpoint
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | `GET /api/v1/trades/batch?ids=<comma-separated-ULIDs>` returns trades matching provided IDs. `TradeLogger.get_trades_by_ids()` method. 50 ID limit per request (400 if exceeded). |
| **Rationale** | TradeSearchInput previously fetched last 100 trades and filtered client-side to resolve linked trade chips — older trades would never display. Batch endpoint ensures linked trade chips always resolve regardless of age. Generalizes to any future UI needing to resolve a known set of trade IDs. |
| **Status** | Active |

---

### DEC-204 | Dashboard Scope Refinement
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Dashboard narrows to pure ambient awareness. CapitalAllocation donut/bars, RiskGauge, MarketRegimeCard, and emergency controls removed (all live on Orchestrator page). Replaced by OrchestratorStatusStrip — single-line compact data row with strategy count, deployed capital, risk budget %, and regime badge. Click navigates to Orchestrator. |
| **Rationale** | Avoids duplication across Dashboard and Orchestrator. Status strip provides essential operational numbers in one scannable line without the visual weight of charts and gauges. |
| **Alternatives** | (A) Keep full donut on both pages — rejected, duplication with divergence risk. (C) Remove all orchestrator info from Dashboard — rejected, loses ambient awareness. |
| **Status** | Active |

---

### DEC-205 | Performance Page Expansion
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Performance page expands from single scroll view to 5-tab layout with 8 new visualizations: TradeActivityHeatmap, CalendarPnlView, RMultipleHistogram, RiskWaterfall, PortfolioTreemap, CorrelationMatrix, ComparativePeriodOverlay, and TradeReplay. Tabs: Overview, Heatmaps, Distribution, Portfolio, Replay. Period selector remains global above tabs. |
| **Rationale** | Performance is the analytical backbone of ARGUS. Full suite built in Sprint 21d to avoid return trips. ~47 hours but delivers complete analytical depth. |
| **Status** | Active |

---

### DEC-206 | Trade Activity Heatmap — D3 Color Scales
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | TradeActivityHeatmap uses D3 color scales (scaleSequential + interpolateRdYlGn) with React SVG rendering. 13×5 grid (30-min time bins × weekdays). Toggle between avg R-multiple and net P&L coloring. |
| **Rationale** | D3 provides superior diverging color interpolation. React handles DOM. Best of both worlds — D3 for math, React for rendering. |
| **Status** | Active |

---

### DEC-207 | Portfolio Treemap — D3 Hierarchy
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | PortfolioTreemap uses D3 hierarchy + treemap layout (d3-hierarchy module). Rectangles sized by position value, colored by unrealized P&L %. Mobile fallback to sorted list when container width < 400px. |
| **Rationale** | Treemap tiling algorithms (squarify) are non-trivial. D3 is the right tool — justifies the dependency. Mobile fallback prevents unreadable tiny rectangles. |
| **Status** | Active |

---

### DEC-208 | Comparative Period Overlay
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Ghost line added to existing EquityCurve component showing previous period returns. Lower opacity (0.3), dashed styling. Toggle on/off. Previous period data fetched alongside current and date-shifted to align. |
| **Rationale** | Minimal new code (second series on existing Lightweight Charts instance), high analytical insight. Enables "am I doing better or worse than last week/month?" at a glance. |
| **Status** | Active |

---

### DEC-209 | Trade Replay Mode
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | TradeReplay uses Lightweight Charts candlestick with progressive bar reveal for playback animation. Playback controls: play/pause, speed (1x/2x/5x/10x), scrubber, step forward/back. Entry/exit/stop/target markers appear at correct bars. |
| **Rationale** | Reuses existing chart library. setInterval + setVisibleRange creates smooth animated playback without custom rendering. Most powerful learning tool in the Performance suite. |
| **Status** | Active |

---

### DEC-210 | System Page Cleanup
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | System page removes StrategyCards (migrated to Pattern Library + Orchestrator) and EmergencyControls (migrated to Orchestrator GlobalControls). Adds IntelligencePlaceholders — grid of 6 future component cards (AI Copilot, Pre-Market Engine, Catalyst Service, Order Flow Analyzer, Setup Quality Engine, Learning Loop) with sprint activation dates. |
| **Rationale** | Clean separation: Pattern Library for strategy info, Orchestrator for operations, System for infrastructure health. Intelligence placeholders give roadmap visibility. |
| **Status** | Active |

---

### DEC-211 | Navigation Restructure
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Desktop sidebar: thin 1px divider lines between nav groups (Monitor: Dashboard/Trades/Performance, Operate: Orchestrator/Patterns, Learn: Debrief, Maintain: System). Mobile bottom bar: 5 primary tabs (Dashboard, Trades, Orchestrator, Patterns, More) + Framer Motion bottom sheet for overflow (Performance, Debrief, System). |
| **Rationale** | 7 items need visual grouping on desktop. Mobile can't fit 7 equal tabs — More sheet is native-feeling overflow pattern. Primary mobile tabs prioritize market-hours needs (awareness + control). |
| **Alternatives** | (B) Spacing-only groups — too subtle with 7 items. (C) Group labels — sidebar too narrow at 64px. Mobile: (B) Scrollable tabs — discoverability poor. (C) Hamburger menu — hides key pages. |
| **Status** | Active. Amends DEC-199 (mobile tab arrangement). |

---

### DEC-212 | AI Copilot Shell Architecture
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | CopilotPanel is a new dedicated component, not reusing SlideInPanel. Persists across page navigation (mounted in AppShell). Has own Zustand store (copilotUI). Shows page context indicator from React Router. Sprint 21d builds shell with placeholder content; Sprint 22 activates with Claude API. CopilotButton is floating action button — desktop bottom-right 24px inset, mobile above tab bar. |
| **Rationale** | Different lifecycle from data panels (SlideInPanel). Persists across pages, maintains chat state, needs own z-index layer. Will grow significantly in Sprint 22 — starting fresh avoids fighting assumptions baked into SlideInPanel. |
| **Status** | Active |

---

### DEC-213 | Pre-Market Dashboard Layout
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Full pre-market layout shell built in Sprint 21d with placeholder cards for watchlist, regime forecast, and catalyst summary. Time-gated on market_status from account endpoint. Dev mode supports ?premarket=true override. |
| **Rationale** | Building the layout now (2 extra hours) means Sprint 23 wires data into existing components rather than designing from scratch. Placeholder cards communicate the roadmap. |
| **Status** | Active |

---

### DEC-214 | Goal Tracking Configuration
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | GoalTracker reads monthly_target_usd from GoalsConfig sub-model in SystemConfig. Default $5,000. Simple config YAML field for V1. GoalTracker widget computes progress from current month P&L and elapsed trading days. |
| **Rationale** | Simple config value sufficient for single-user system. Database-backed goal history with tracking over time can upgrade later when the feature proves its value. |
| **Status** | Active |

---

### DEC-215 | Chart Library Assignments
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | D3 individual modules (d3-scale, d3-color, d3-hierarchy, d3-interpolate) for heatmap color scales, treemap layout, and correlation matrix. Recharts for R-multiple histogram. Custom SVG for calendar P&L and risk waterfall. Lightweight Charts for trade replay and comparative overlay. No full D3 bundle import. |
| **Rationale** | Each library used where it excels. D3 modules imported individually to minimize bundle size. Extends DEC-104 (Lightweight Charts primary, Recharts for non-time-series). |
| **Status** | Active. Extends DEC-104. |

---

### DEC-216 | Mobile Primary Tabs
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Mobile bottom bar shows 5 tabs: Dashboard, Trades, Orchestrator, Patterns, More. Performance, Debrief, System accessible via More bottom sheet. |
| **Rationale** | Market hours (primary mobile use case) need ambient awareness (Dashboard), trade details (Trades), operational control (Orchestrator), and strategy reference (Patterns). Performance and Debrief are post-session desktop activities. System is rarely accessed. |
| **Status** | Active. Amends DEC-199. |

---

### DEC-217 | Copilot Button Positioning
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | CopilotButton: desktop fixed bottom-right 24px from edges. Mobile fixed right-aligned, bottom offset to clear MobileNav (h-16 + pb-3 + gap ≈ 88px). Button hides when CopilotPanel is open. Subtle entrance animation (scale spring) on first mount only. |
| **Rationale** | Avoids tab bar overlap on mobile. Clean toggle behavior — no visual redundancy when panel visible. |
| **Status** | Active |

---

### DEC-218 | Performance Tab Organization
| Field | Value |
|-------|-------|
| **Date** | 2026-02-27 |
| **Decision** | Performance page uses 5-tab layout: Overview (existing metrics + equity curve + P&L + strategy breakdown + comparative overlay), Heatmaps (activity heatmap + calendar P&L), Distribution (R-multiple histogram + risk waterfall), Portfolio (treemap + correlation matrix), Replay (trade replay). Period selector global above tabs. |
| **Rationale** | Organizes 8 new visualizations into focused analytical lenses without overwhelming. Each tab answers a different question. Overview preserves existing page content for zero disruption. |
| **Status** | Active |

---

### DEC-219 | StrategyDeploymentBar Redesign
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Redesigned HeatStripPortfolioBar → StrategyDeploymentBar. Segments represent capital deployed per strategy (using strategy accent colors from strategyConfig.ts) plus an "Available" segment in muted dark. Labels show strategy abbreviation + dollar amount (letter-only below 60px, hidden below 30px). Only outer edges of first/last segments get rounded corners. Clicking a strategy segment navigates to Pattern Library with that strategy pre-selected. Clicking "Available" navigates to Orchestrator. |
| **Rationale** | Per-position P&L heat coloring was unreadable at a glance — no labels, no way to identify which stock was which without hovering. Strategy-level deployment with accent colors communicates "how much capital is where" instantly, which the positions table doesn't give as quickly. |
| **Supersedes** | Original HeatStripPortfolioBar design |
| **Status** | Active |

---

### DEC-220 | GoalTracker Enhancement
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | GoalTracker card enhanced with "MONTHLY GOAL" header label, 2-column layout: left column (progress bar, dollar amount, pace status), right column (avg daily P&L, need/day). Pace calculation: ahead (>110% of expected pace), on_pace (90–110%), behind (<90%). Color-coded: green for ahead/on_pace, amber for behind (>50%), red for behind (≤50%). |
| **Rationale** | Original card had no label, wasted space above/below the progress bar. Adding pace stats turns it from a simple progress bar into a "pace dashboard" — instantly see if daily average is above or below what's needed. |
| **Status** | Active |

---

### DEC-221 | Market + Regime Row → 3-Card Row
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Merged Market and Market Regime into single "Market Status" card (~1/3 width). Added two new cards: "Today's Stats" (2×2 grid: trade count, win rate, avg R, best trade) and "Session Timeline" (custom SVG horizontal timeline with strategy operating windows as colored bars, "now" marker, and "Active: X" label). Session Timeline click navigates to Orchestrator page. All three cards at equal 1/3 width on desktop/tablet, stacked on mobile. |
| **Rationale** | Two separate cards for Market and Market Regime used too much horizontal space for too little data at desktop width. Session Timeline answers "what should be running right now?" at a glance without navigating to Orchestrator. Today's Stats provides the quick session summary previously unavailable on Dashboard. |
| **Status** | Active |

---

### DEC-222 | Dashboard Aggregate Endpoint
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | New `GET /api/v1/dashboard/summary` endpoint returns all Dashboard card data in a single response: account, today_stats, goals, market, regime, deployment, orchestrator. Frontend `useDashboardSummary()` hook polls at 5s with `placeholderData: keepPreviousData` to prevent skeleton flash on refetch or tab-switch. Individual hooks (usePerformance, useGoals, etc.) retained for other pages. |
| **Rationale** | TodayStats and GoalTracker loaded visibly slower than other cards because they depended on separate slower queries. Aggregate endpoint eliminates multi-query waterfall — one request, one loading state. |
| **Status** | Active |

---

### DEC-223 | useSummaryData Hook Disabling Pattern
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Components that accept pre-fetched data via props also accept a `useSummaryData` boolean prop. When true, internal TanStack Query hooks pass `enabled: false`, preventing them from firing. Components render their normal structure with dash/zero placeholders while waiting for prop data, avoiding skeleton flash. Applied to TodayStats and GoalTracker. `usePerformance`, `useTrades`, and `useGoals` hooks extended with optional `{ enabled }` parameter. |
| **Rationale** | React's rules of hooks prevent conditional hook calls. Even with prop data intended, hooks fired unconditionally and showed skeleton loading states during the brief window before the summary endpoint responded. Disabling hooks entirely when the parent owns the data flow eliminates the stagger. |
| **Status** | Active |

---

### DEC-224 | Unified Diverging Color Scale
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Single shared diverging color scale (`colorScales.ts`) for all charts encoding profit/loss. Zero maps to neutral gray, negatives to red/orange, positives to green. Applied to TradeActivityHeatmap, CalendarPnlView, PortfolioTreemap. |
| **Rationale** | Three charts used slightly different color mappings, causing negative values to render green in some cases. Unified scale ensures visual consistency and eliminates misreadings. |
| **Status** | Active |

---

### DEC-225 | Dynamic Text Color for Data-Driven Backgrounds
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Shared `getContrastTextColor()` utility computes WCAG luminance and flips text from white to dark when background is too light. Applied to heatmap, calendar, treemap, and correlation matrix cells. |
| **Rationale** | White text on light green/yellow/off-white cells was illegible. Dynamic contrast ensures readability regardless of underlying data value. |
| **Status** | Active |

---

### DEC-226 | Correlation Matrix Strategy Labels
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Correlation matrix axis labels use single-letter strategy badges from `STRATEGY_DISPLAY` in `strategyConfig.ts` (O, S, V, A) with hover tooltips for full names. Replaces last-4-characters of strategy ID. |
| **Rationale** | Previous labels ("ntum", "kout", "calp", "laim") were meaningless. Single letters match existing visual language (watchlist badges, position timeline, strategy cards). |
| **Status** | Active |

---

### DEC-227 | Performance Desktop Layout Density
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Distribution tab: RMultipleHistogram + RiskWaterfall side-by-side (50/50) on desktop. Portfolio tab: PortfolioTreemap + CorrelationMatrix side-by-side (60/40) on desktop. Stack vertically on tablet/mobile. Overview, Heatmaps, Replay tabs unchanged. |
| **Rationale** | Full-width cards wasted horizontal space for charts that don't need it. Side-by-side pairing improves information density without sacrificing readability. |
| **Status** | Active |

---

### DEC-228 | Performance Tab Keyboard Shortcuts
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Performance page tab shortcuts: `o` (Overview), `h` (Heatmaps), `d` (Distribution), `p` (Portfolio), `r` (Replay). Suppressed during input/textarea focus. |
| **Rationale** | Extends keyboard shortcut system (DEC-199) for intra-page navigation. Mnemonic first-letter mapping. |
| **Status** | Active |

---

### DEC-229 | Performance Workbench — Deferred
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Performance page will be refactored into a customizable widget grid ("Performance Workbench") using `react-grid-layout`. Two stages: Stage 1 (rearrangeable/resizable widgets within tabs, layout persistence), Stage 2 (widget palette, custom tab CRUD, drag-from-palette). Layout persistence via backend API endpoint. Deferred to post-Sprint 21d, estimated 11–14 sessions. |
| **Rationale** | Fixed tab layouts don't scale as visualization count grows (8 now, 15+ by Sprint 25). Custom layouts let the user build analysis workflows tailored to different contexts (morning prep, post-session review, weekly report). react-grid-layout is mature and handles snap, resize, responsive breakpoints. Backend persistence keeps user state centralized. |
| **Status** | Deferred |
| **Supersedes** | DEC-218 (fixed 5-tab organization) — tabs become user-customizable presets |

---

### DEC-230 | Sprint 21.5 — Live Integration Sprint

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Insert Sprint 21.5 (Live Integration) between Sprint 21d and Sprint 22. Dedicated sprint for connecting DatabentoDataService and IBKRBroker adapters to real services, validating end-to-end data flow, and running first live market sessions with paper trading. |
| **Rationale** | Sprints 12 and 13 built adapters against mocks/unit tests. No code has touched real Databento feeds or real IB Gateway. Integration testing against live services is non-trivial — timestamp formats, reconnection under real network conditions, data gaps during fast markets, and order rejection edge cases only surface with real connections. This work was not on the roadmap and represents a significant gap between "adapters built" and "system operational." |
| **Alternatives** | (1) Fold integration work into Sprint 22 sessions — rejected because Sprint 22 (AI Layer) has its own complexity; mixing infrastructure debugging with AI feature development would compromise both. (2) Skip dedicated sprint, just "turn it on" — rejected because every adapter-to-real-service connection historically hits issues that require focused debugging. |
| **Status** | Active |

---

### DEC-231 | Separate Config File for Live Operation

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Create `config/system_live.yaml` as a separate config file for Databento + IBKR operation. Original `config/system.yaml` retained as Alpaca incubator config. Selected via `--config` CLI flag. |
| **Rationale** | Clean separation between incubator (Alpaca) and production (Databento/IBKR) configurations. Easy to switch between modes. No risk of accidentally running live config during development. |
| **Alternatives** | (1) Modify system.yaml in place — rejected because loses ability to quickly switch back to Alpaca mode. (2) Environment variable override — rejected because too many values to override; config file is cleaner. |
| **Status** | Active |

---

### DEC-232 | IB Gateway for API Connection (Not TWS)

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Use IB Gateway (headless) rather than Trader Workstation (TWS) for IBKR API connections. |
| **Rationale** | ARGUS is a headless automated system — no need for TWS GUI. Gateway uses fewer resources, is easier to Docker-containerize (RSK-022), and is designed for automated trading systems. TWS available as fallback if Gateway has issues. |
| **Alternatives** | TWS — functional but unnecessary resource overhead for headless operation. |
| **Status** | Active |

---

### DEC-233 | All Four Strategies Active from First Live Session

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | All four strategies active from the first live market session (Session 11). No incremental activation. Sessions 4-5 validate all strategies with real data (without execution), Session 10 validates combined startup. If Session 10 reveals a strategy-specific issue, that strategy is disabled while others proceed. |
| **Rationale** | Strategy-prefixed logging makes per-strategy debugging straightforward. Strategies operate in time-separated windows (ORB morning, VWAP mid-morning, Afternoon afternoon), naturally isolating most issues. By Session 11, data flow through all four strategies has already been validated in Sessions 4-5. The only new variable is IBKR execution, which is strategy-agnostic. Incremental activation would add 2-3 sessions with marginal debugging benefit. |
| **Alternatives** | Incremental activation (ORB → +Scalp → +VWAP → +Afternoon over 4 sessions) — rejected as overly cautious given pre-validation in earlier sessions and time-separated strategy windows. |
| **Status** | Active |

---

### DEC-234 | Databento Datasets: XNAS First, Add XNYS in Sessions 3-4

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Start with XNAS.ITCH (Nasdaq TotalView-ITCH) in Sessions 1-2 for pipeline validation. Add XNYS.PILLAR (NYSE) in Sessions 3-4 once Nasdaq data flow is confirmed working. Two datasets use 2 of the 10 allowed concurrent sessions on the Databento Standard plan. NYSE Arca (ARCX.PILLAR) added later only if specifically needed. |
| **Rationale** | The momentum/small-cap day trading universe spans both NASDAQ and NYSE. NASDAQ-only would systematically miss NYSE-listed gappers — if the best opportunity on a given day is NYSE-listed, the scanner wouldn't see it. However, debugging multi-dataset streaming on day one adds unnecessary complexity. Starting with XNAS validates the pipeline, then adding XNYS is a small incremental change. SPY (needed for RegimeClassifier) routes through NYSE data. |
| **Alternatives** | (1) XNAS only for weeks — rejected because it systematically misses a large portion of the tradeable universe. (2) Both datasets from Session 1 — rejected because validating one dataset first isolates data pipeline issues from multi-dataset issues. |
| **Status** | Superseded by DEC-248 |

---

### DEC-235 | Sprint 21.6 — Backtest Re-Validation Separated from Live Integration

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | DEC-132 backtest re-validation (re-running parameter sweeps and walk-forward analysis with Databento data) is a separate Sprint 21.6, not part of Sprint 21.5. Sprint 21.6 runs in parallel with Sprint 22 (AI Layer). Full spec to be drafted after Sprint 21.5 completes, informed by integration discoveries. |
| **Rationale** | Re-validation is analytical work (data processing, parameter sweeps, statistical analysis) that is fundamentally different from integration testing (connecting, configuring, debugging). Separating them allows Sprint 21.5 to focus purely on "does the system work" and Sprint 21.6 on "are the parameters valid." Sprint 21.6 doesn't block AI Layer development. Deferring the spec allows integration discoveries to inform the re-validation approach. |
| **Alternatives** | Include in Sprint 21.5 — rejected because it extends the sprint significantly and mixes two different types of work. |
| **Status** | Active |

---

### DEC-236 | IBKR Account Approved — Paper Trading Ready

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | IBKR account (U24619949) approved. Paper trading account available for Sprint 21.5 integration testing. Blocker removed — IBKR paper trading proceeds in parallel with Databento integration. |
| **Rationale** | Account approval was a prerequisite for Sprint 21.5 Phase B. With both Databento subscription and IBKR approval ready, Sprint 21.5 can proceed at full velocity across both phases. |
| **Status** | Active |

---

### DEC-237 | Databento Standard Plan Does NOT Include Live L2/L3 — Supersedes DEC-165

| Field | Value |
|-------|-------|
| **Date** | 2026-03-01 |
| **Decision** | Databento Standard plan ($199/mo) includes live L0 + L1 data only (EQUS.MINI dataset). Live L2 (MBP-10) and L3 (MBO) streaming requires Plus tier ($1,399/mo + annual contract) or Unlimited ($3,500/mo). Standard plan DOES include historical L2/L3 access (1-month lookback) for backtesting. Verified via Databento dashboard pricing matrix (March 1, 2026) and confirmed by Session 1 live connection test returning "A live data license is required to access XNAS.ITCH." |
| **Supersedes** | DEC-165 (which incorrectly stated "L2 included in Standard plan") |
| **Rationale** | DEC-165 was based on ambiguous pricing page language. The dashboard's "Plans and live data" matrix clearly shows L2/L3 checkmarks only on Plus and Unlimited tiers. Historical API access (which our test used successfully) is a different entitlement than live streaming. |
| **Impact** | Order Flow Model (live L2 depth) cannot be built at $199/mo. Requires $1,200/mo upgrade to Plus tier. |
| **Status** | Active |

---

### DEC-238 | Order Flow Model Deferred to Post-Revenue

| Field | Value |
|-------|-------|
| **Date** | 2026-03-01 |
| **Decision** | Order Flow Model V1 (was Sprint 24) and Order Flow V2 + L3 integration (was part of Sprint 28) deferred to post-revenue trading. These sprints move to a "Post-Revenue Backlog" and will be scheduled when monthly trading income justifies the $1,200/mo Databento Plus upgrade. All four current strategies and the planned intelligence layer (AI, catalysts, quality scoring, pattern library, learning loop) operate on L1 data. Order Flow is an edge enhancement, not a foundation. |
| **Rationale** | (1) Live L2/L3 requires Databento Plus at $1,399/mo — a $1,200/mo increase over current Standard. (2) Profitable day trading at 10%+/month is achievable without L2 data — top retail traders (Ross Cameron, SMB Capital trainees) use price action and volume (L1). (3) All four ARGUS strategies use L1 signals (candle breakouts, volume surges, VWAP crosses). (4) Setup Quality Engine can score on 5 dimensions without Order Flow and add it as a 6th dimension post-revenue. (5) Historical L2 remains available on Standard for backtesting the Order Flow Model before going live. |
| **Supersedes** | Sprint 24 scope (DEC-163), Sprint 28 Order Flow V2 scope (DEC-163) |
| **Amends** | DEC-166 (Short Selling) — decoupled from Order Flow V2, now standalone sprint |
| **Status** | Active |

---

### DEC-239 | Setup Quality Engine — 5 Dimensions in V1, Order Flow Added Post-Revenue

| Field | Value |
|-------|-------|
| **Date** | 2026-03-01 |
| **Decision** | Setup Quality Engine launches with 5 scoring dimensions (Order Flow removed from V1). Weights redistributed: Pattern Strength 30% (was 25%), Catalyst Quality 25% (was 20%), Volume Profile 20% (was 15%), Historical Match 15% (was 10%), Regime Alignment 10% (unchanged). When Order Flow Model activates post-revenue, it becomes the 6th dimension and all weights rebalance to the original 6-dimension design. |
| **Rationale** | Order Flow was 20% of composite score. Redistributing to the remaining 5 dimensions preserves the scoring framework. Pattern Strength and Catalyst Quality get the largest increases as the highest-signal dimensions. The engine's YAML-configurable weights (DEC-163) make post-revenue rebalancing trivial. |
| **Amends** | Bible Section 19.2 scoring dimensions |
| **Status** | Active |

---

### DEC-240 | Sprint Roadmap Renumbered — Order Flow Removed, Queue Collapsed

| Field | Value |
|-------|-------|
| **Date** | 2026-03-01 |
| **Decision** | Future sprint queue renumbered after removing Order Flow sprints. Mapping: old Sprint 25 → new Sprint 24, old Sprint 26 → new Sprint 25, old Sprint 27 → new Sprint 26, old Sprint 28 (short selling only, OF V2 removed) → new Sprint 27, old Sprint 29 → new Sprint 28, old Sprint 30 → new Sprint 29, old Sprint 31 → new Sprint 30, old Sprint 32 → new Sprint 31, old Sprint 33+ → new Sprint 32+. Net effect: 2 sprints removed from pre-revenue path, accelerating time to live trading. |
| **Rationale** | Consistent numbering prevents confusion. Sprints 22–23 unchanged. Gap from removing Sprint 24 (OF V1) collapsed. Sprint 28's OF V2 component moved to post-revenue backlog; short selling infrastructure retained as standalone Sprint 27. |
| **Status** | Active |

---

### DEC-241 | Databento API — instrument_id Is Direct Attribute (Not Nested in Header)

| Field | Value |
|-------|-------|
| **Date** | 2026-03-02 |
| **Decision** | Databento library changed: `msg.instrument_id` replaces `msg.hd.instrument_id`. The `hd` (header) nesting was removed in a library update. All record types now expose `instrument_id` as a direct attribute. |
| **Rationale** | Discovered during first live connection. Runtime AttributeError on every incoming record. |
| **Status** | Active |

---

### DEC-242 | Databento Symbology — Use Library's Built-In `symbology_map`

| Field | Value |
|-------|-------|
| **Date** | 2026-03-02 |
| **Decision** | Symbol resolution uses `self._live_client.symbology_map.get(instrument_id)` instead of custom `DatabentoSymbolMap`. The Databento library maintains its own `symbology_map` dict (instrument_id → symbol) populated from SymbolMappingMsg records at session start. |
| **Rationale** | Custom DatabentoSymbolMap was not being populated with current library. Built-in mapping is maintained automatically and is O(1) lookup. |
| **Status** | Active |

---

### DEC-243 | Databento Prices Are Fixed-Point Format (Scaled by 1e9)

| Field | Value |
|-------|-------|
| **Date** | 2026-03-02 |
| **Decision** | All Databento price fields (open, high, low, close, price) are in fixed-point integer format scaled by 1e9. Multiply by 1e-9 to get standard floating-point prices. Applied to both OHLCVMsg and TradeMsg handlers. |
| **Rationale** | Discovered when prices appeared as ~150,000,000,000 instead of ~150.00. Databento uses fixed-point for precision on their wire protocol. |
| **Status** | Active |

---

### DEC-244 | Databento Historical Data Has ~15-Minute Lag

| Field | Value |
|-------|-------|
| **Date** | 2026-03-02 |
| **Decision** | Databento historical API returns data with approximately 15 minutes of lag. Indicator warmup end time uses a 20-minute buffer (`clock.now() - 20min`) to avoid 422 errors from requesting data beyond available range. |
| **Rationale** | Warmup was requesting data up to `now()`, which returned 422 "data_end_after_available_end". 20-minute buffer provides margin. Slightly stale warmup data is acceptable for indicator seeding. |
| **Status** | Active |

---

### DEC-245 | flatten_all() SMART Routing Fix

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | `flatten_all()` in IBKRBroker must use `get_stock_contract()` for SMART routing, not `ib_pos.contract` directly. The fill contract retains the execution exchange (e.g., ARCA), and IBKR's precautionary settings block direct routing to specific exchanges. |
| **Rationale** | Sprint 21.5 Session 7 discovered IBKR error 10311 ("This order will be directly routed to ARCA") when flatten_all() used the position's contract object directly. Using the contract resolver ensures SMART routing for all exit orders. |
| **Status** | Active |

---

### DEC-246 | get_open_orders() Broker ABC Method

| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Decision** | Added `get_open_orders()` as abstract method to Broker ABC. Implemented in IBKRBroker (via `ib_async` `openTrades()` with ULID recovery from `orderRef`), AlpacaBroker (via `get_orders()` API), and SimulatedBroker (returns pending bracket orders). |
| **Rationale** | Order Manager's `reconstruct_from_broker()` and Health Monitor both called this method, but it was never implemented in any broker class. Discovered during Sprint 21.5 Session 9 resilience validation. Critical for state reconstruction after restarts. |
| **Status** | Active |

---

### DEC-247 | Scanner Resilience for Databento Historical Data Lag

| Field | Value |
|-------|-------|
| **Date** | 2026-03-03 |
| **Decision** | DatabentoScanner gracefully handles Databento historical API lag via `_fetch_daily_bars_with_lag_handling()`. When the scanner receives a 422 `data_end_after_available_end` error, it extracts the available end date from the error message via regex, retries the query with the adjusted date range, and falls back to the static watchlist if the retry also fails. Gap calculations use the most recent available daily bars (may be 1–6 days old depending on weekends/processing). |
| **Rationale** | Databento EQUS.MINI historical data has a multi-day lag (up to ~6 days over weekends), much longer than the ~15-minute lag observed for intraday data during market hours (DEC-244). The scanner's daily bar query for gap calculation triggered 422 errors when requesting data beyond the available range. This is distinct from the live streaming API, which operates independently. Scanner failure must not block system startup — the static watchlist fallback ensures strategies always have symbols to trade. |
| **Alternatives** | (1) Hardcode a lookback buffer (e.g., always query 7 days back) — rejected because it wastes bandwidth and doesn't handle variable lag. (2) Omit `end` parameter entirely — rejected because Databento API may return unexpected ranges. (3) Accept scanner failure silently — rejected because clear logging aids diagnosis. |
| **Status** | Active |

---

### DEC-248 | EQUS.MINI Confirmed as Production Live Dataset

| Field | Value |
|-------|-------|
| **Date** | 2026-03-03 |
| **Decision** | EQUS.MINI confirmed as the production dataset for ARGUS on Databento Standard plan. Diagnostic script (`scripts/diagnose_databento.py`) verified: (1) live streaming subscription accepted without license error, (2) symbology mappings received, (3) historical ohlcv-1m bars available, (4) all four required schemas functional (ohlcv-1m, ohlcv-1d, trades, tbbo), (5) multi-symbol queries working (8 symbols tested). XNAS.ITCH is no longer the default — EQUS.MINI provides consolidated exchange-direct data across all US equities in a single subscription. |
| **Rationale** | Earlier sessions (4–6) used XNAS.ITCH successfully for live streaming, but DEC-237 revealed XNAS.ITCH requires a live data license on Standard plan. EQUS.MINI (the consolidated equities mini dataset) is included in Standard for both historical and live L0+L1 data. The diagnostic confirmed EQUS.MINI supports all schemas ARGUS requires, including `tbbo` (top-of-book bid/offer) for L1 quote data. Supersedes DEC-089 (default dataset was XNAS.ITCH). Amends DEC-234 (phased dataset plan) — EQUS.MINI replaces the XNAS.ITCH + XNYS.PILLAR multi-dataset approach since it already covers all US exchanges in one feed. |
| **Status** | Active |

---

### DEC-249 | Concentration Limit Uses Approve-With-Modification

| Field | Value |
|-------|-------|
| **Date** | 2026-03-03 |
| **Decision** | The single-stock concentration limit (5% of equity) now uses approve-with-modification instead of hard rejection. When a signal's position value would exceed the concentration limit, shares are reduced to fit within the limit. If the reduced position falls below the 0.25R floor (reduced risk < 0.25 × original risk), the signal is rejected entirely. |
| **Rationale** | Sprint 21.5 Session B1 investigation found that VWAP Reclaim's NFLX signal (3,573 shares, ~$346K) was rejected for concentration (5% limit = $50K). The issue was systemic: risk-based position sizing (`shares = $2K risk / tight stop`) produces large positions that exceed concentration limits for mid-to-high priced stocks with tight stops. Rather than reject these signals outright, the system now right-sizes them by reducing shares to fit within concentration, similar to the existing cash reserve and buying power constraints. The 0.25R floor prevents taking positions that are "not worth it" after reduction. |
| **Alternatives** | (1) Keep as hard rejection — rejected because most VWAP Reclaim signals on stocks >$50 would be rejected, producing noise. (2) Add pre-flight check in strategy — rejected because strategies don't have access to total equity, and it duplicates Risk Manager logic. (3) Reduce risk budget in strategy config — rejected because it would make trades not worth taking for lower-priced stocks. |
| **Status** | Active |

---

### DEC-250 | Metarepo Workflow Retrofit

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Decision** | Process transition point. All future sprints use the metarepo sprint-planning protocol, three-tier review system (close-out + Tier 2 reviewer + Tier 3 architectural review in Claude.ai), and universal rules from `.claude/rules/universal.md`. Sprint numbering continues from current (next sprint is 22). Documentation split into Tier A (Claude.ai Project Knowledge + `.claude/`) and Tier B (repo `docs/`). |
| **Rationale** | 21 sprints of organic process evolution distilled into a repeatable framework. Two-Claude workflow formalized with explicit protocols, review tiers, and documentation hierarchy. Prevents regression to ad-hoc practices as project scales. See `docs/process-evolution.md` for pre-retrofit history. |
| **Status** | Active |

---

### DEC-251 | Replace 0.25R Ratio Floor with Absolute Minimum Risk Floor

| Field | Value |
|-------|-------|
| **Date** | 2026-03-03 |
| **Sprint** | 21.5 (Session C1) |
| **Decision** | Replace the 0.25R ratio-based floor (which compared reduced shares against the uncapped position) with a $100 absolute minimum risk dollar floor. Any position risking ≥$100 is worth taking; below $100 is rejected. Configurable via `min_position_risk_dollars` in risk config. |
| **Rationale** | The 0.25R floor was rejecting every signal on stocks above ~$50 because risk-based sizing produces massive uncapped positions that the 5% concentration cap reduces to 15–20% of original — always below the 25% threshold. Discovered during first live market session when all VWAP Reclaim signals were rejected despite valid setups. An absolute dollar floor avoids this structural mismatch. |
| **Supersedes** | N/A (modifies DEC-249 implementation; DEC-249 itself still valid) |
| **Cross-References** | DEC-249 (concentration approve-with-modification) |
| **Status** | Active |

---

### DEC-252 | Round Order Prices to Tick Size Before IBKR Submission

| Field | Value |
|-------|-------|
| **Date** | 2026-03-03 |
| **Sprint** | 21.5 (Session C1) |
| **Decision** | Round all order prices (entry limit, stop, T1 target, T2 target) to $0.01 tick size in `IBKRBroker` before submitting to IBKR. Strategies compute mathematically precise values; the broker adapter normalizes for exchange requirements. Helper `_round_price()` with configurable tick size (default $0.01 for US equities). |
| **Rationale** | IBKR rejected all 9 bracket order legs across 3 symbols with Error 110 ("price does not conform to minimum price variation") because strategy calculations produced values like 296.703, 299.857000001, 188.37144. The broker adapter is the correct boundary for this normalization. |
| **Cross-References** | DEC-117 (atomic bracket orders), DEC-083 (IBKR sole broker) |
| **Status** | Active |

---

### DEC-253 | Add Data Heartbeat Logging

| Field | Value |
|-------|-------|
| **Date** | 2026-03-03 |
| **Sprint** | 21.5 (Session C1) |
| **Decision** | Log a single INFO line every 5 minutes showing candle count and active symbol count: "Data heartbeat: 50 candles received in last 5m (10 symbols active)". Provides data flow confirmation without per-candle noise. |
| **Rationale** | During C1 startup, initial diagnosis couldn't determine if Databento data was flowing because CandleEvent processing had no INFO-level logging. The heartbeat provides low-noise confirmation that the data pipeline is alive. |
| **Cross-References** | DEC-248 (EQUS.MINI confirmed) |
| **Status** | Active |

---

### DEC-254 | Auto-Shutdown After EOD Flatten

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Sprint** | 21.5 (Session C1 closeout) |
| **Decision** | After EOD flatten completes and confirms 0 open positions, schedule graceful shutdown with configurable delay (default 60s). Implemented via `ShutdownRequestedEvent`. Config flag `auto_shutdown_after_eod: true` in `OrderManagerConfig`. |
| **Rationale** | During C1, ARGUS kept running overnight after market close, cycling IBKR 1100 disconnect errors every 15–30 minutes. Operator was asleep (3:50 AM Taipei when EOD flatten runs). Auto-shutdown eliminates unnecessary overnight resource usage and log noise. Manual shutdown via `stop_live.sh` is unacceptable for Taipei timezone operation. |
| **Cross-References** | RSK-022 (nightly IB Gateway resets) |
| **Status** | Active |

---

### DEC-255 | Downgrade IBKR Maintenance Errors Outside Market Hours

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Sprint** | 21.5 (Session C1 closeout) |
| **Decision** | IBKR error codes 1100, 1102, 2107, 2157 (farm connectivity messages) logged at INFO instead of CRITICAL/WARNING outside market hours (9:30 AM – 4:00 PM ET). During market hours, severity unchanged. |
| **Rationale** | C1 overnight log had 20+ CRITICAL alerts from IBKR cycling connections during nightly maintenance. These are expected behavior, not actionable. With auto-shutdown (DEC-254) this is less critical but still relevant during the post-market window before shutdown completes. |
| **Cross-References** | DEC-254 (auto-shutdown), RSK-022 (nightly IB Gateway resets) |
| **Status** | Active |

---

### DEC-256 | Add Symbol Field to PositionClosedEvent

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Sprint** | 21.5 (Session C1 closeout) |
| **Decision** | Added `symbol` field to `PositionClosedEvent`. The `ArgusSystem._on_position_closed_for_strategies` handler requires the symbol to route the event to the correct strategy. |
| **Rationale** | Discovered during first live trade (AAPL time-stop exit). Handler raised an exception on `PositionClosedEvent` (seq=93981) because the symbol field was missing. Trade still completed because the event bus continued processing other handlers, but strategies were not notified of position closures. Bug fix, not a design choice. |
| **Cross-References** | DEC-025 (Event Bus FIFO) |
| **Status** | Active |

---

### DEC-257 | Hybrid Multi-Source Data Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Sprint** | Pre-21.7 planning |
| **Decision** | ARGUS uses a hybrid multi-source data architecture: Databento for live streaming and backtesting, FMP for pre-market scanning, IBKR for execution. Each provider used for its architectural strength — no overlap, no redundancy. Push-based streaming (Databento) cannot be replaced by REST polling (FMP or any other REST API) for live strategy execution. |
| **Alternatives Considered** | 1. Single-provider (Databento for everything): Rejected — Databento historical daily bar lag (DEC-247) makes scanner non-functional. 2. Single-provider (FMP Ultimate for everything): Rejected — REST polling at ~600ms/symbol intervals cannot support sub-second strategy state transitions (VWAP Reclaim 5-state machine, ORB breakout detection). FMP lacks trade-level data needed for Replay Harness. 3. IQFeed as replacement for both: Rejected — more expensive ($143+/mo), Windows-dependent, 500-symbol cap kills scanning. 4. dxFeed: Rejected — enterprise pricing (~$350/mo), no self-service API. 5. Exegy: Rejected — institutional HFT infrastructure ($50K–500K+/year), irrelevant at 150ms Taipei latency. |
| **Rationale** | Databento's push-based streaming delivers every trade and quote to the Event Bus within microseconds. Strategies react to individual trades — this is a fundamental architectural requirement, not a nice-to-have. C1 session proved this with a successful VWAP Reclaim trade on AAPL. FMP provides exactly what Databento lacks: reliable pre-market daily bars and screener endpoints for gap/volume scanning across the full US equity universe. The two providers are complementary with zero overlap. Total cost: $221/mo ($199 Databento + $22 FMP Starter). |
| **Cross-References** | DEC-082 (Databento primary), DEC-247 (scanner historical lag), DEC-248 (EQUS.MINI confirmed), DEC-258 (FMP Starter), DEC-259 (Sprint 21.7) |
| **Status** | Active |

---

### DEC-258 | FMP Starter for Pre-Market Scanning

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Sprint** | Pre-21.7 planning |
| **Decision** | Add Financial Modeling Prep (FMP) Starter plan ($22/mo) as the scanning data source. FMP provides REST endpoints for daily bars, pre-market gainers/losers, and stock screener — exactly what the scanner needs to replace the broken Databento historical daily bar path (DEC-247). |
| **Alternatives Considered** | 1. FMP Premium ($59/mo): Premature — Starter covers scanning needs; upgrade when Sprint 23 (NLP Catalyst) activates. 2. FMP Ultimate ($149/mo): Same — the additional features (earnings transcripts, 1-min intraday, 13F holdings) are Sprint 23–24 requirements, not scanning requirements. 3. Finnhub free tier: Rejected — 15-min delayed data, recent reports of stale WebSocket news feeds with no support response. 4. Fix Databento scanner: Not viable — multi-day historical lag is a Databento infrastructure limitation, not a bug we can work around. |
| **Rationale** | $22/mo solves the scanner problem completely. FMP Starter provides 250 API calls/min, daily OHLCV bars with no lag, pre-market gainers/losers endpoint, and stock screener. Implementation is lightweight: one REST call pre-market, parse JSON, return ranked symbol list. Upgrade path to Premium/Ultimate is clean for future NLP and fundamentals needs. |
| **Cross-References** | DEC-247 (scanner lag problem), DEC-257 (hybrid architecture), DEC-259 (Sprint 21.7), DEC-164 (NLP Catalyst Pipeline — future FMP upgrade), DEF-015 (full-universe scanning — partially addressed) |
| **Implementation** | Sprint 21.7, Sessions 1–3 (March 5, 2026). `FMPScannerSource` in `argus/data/fmp_scanner.py`. 15 tests. |
| **Status** | Active |

---

### DEC-259 | Sprint 21.7 — FMP Scanner Integration

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Sprint** | Pre-21.7 planning |
| **Decision** | Sprint 21.7 is a focused 2–3 session mini-sprint to integrate FMP Starter as the scanning data source. Slotted between Sprint 21.5 (Live Integration) and Sprint 21.6 (Backtest Re-Validation). Implementation: `FMPScannerSource` class making 1–2 REST calls pre-market, config entry for API key, tests. |
| **Alternatives Considered** | 1. Bundle into Sprint 22 (AI Layer): Rejected — scanner is independent of AI Layer and should be validated before AI Copilot observes symbol selection. 2. Bundle into Sprint 21.6 (Backtest Re-Validation): Rejected — different concern entirely; 21.6 is about parameter validation, not data sourcing. 3. Defer to later: Rejected — every paper trading session with the static 10-symbol watchlist produces less meaningful validation data. Earlier scanner activation means better Gate 2 metrics. |
| **Rationale** | Small, focused scope (2–3 sessions). Independent of all other sprints. Directly improves paper trading quality by enabling dynamic symbol selection from full US equity universe. Once activated, every subsequent paper trading session produces more meaningful alpha validation data. |
| **Cross-References** | DEC-257 (hybrid architecture), DEC-258 (FMP Starter), DEC-247 (scanner lag), DEF-015 (full-universe scanning) |
| **Implementation** | Completed March 5, 2026. Session 1: `FMPScannerSource` + `WatchlistItem` fields. Session 2: Config routing + API wiring. Session 3: Pre-Market Watchlist panel (frontend). 17 new pytest, 5 new Vitest. |
| **Status** | Active |

---

### DEC-260 | Data Provider Evaluation — IQFeed, dxFeed, Exegy, Finnhub, QuantConnect Rejected

| Field | Value |
|-------|-------|
| **Date** | 2026-03-04 |
| **Sprint** | Pre-21.7 planning |
| **Decision** | Five additional data providers evaluated and rejected for current ARGUS needs. IQFeed: $143+/mo, Windows-dependent, 500-symbol cap. dxFeed: enterprise pricing (~$350/mo), no self-service API. Exegy: institutional HFT ($50K–500K+/year), irrelevant at Taipei latency. Finnhub: possible future NLP supplement but FMP covers same ground with better screeners; free tier is 15-min delayed. QuantConnect: platform requiring complete ARGUS rewrite, not a data provider. |
| **Alternatives Considered** | Each provider was the alternative. See DEC-257 for the chosen architecture. |
| **Rationale** | None of the five providers offer a better cost/capability ratio than the Databento + FMP hybrid for ARGUS's specific requirements (push-based live streaming + REST pre-market scanning + Taipei latency constraints + Python-native APIs). Finnhub remains on radar as supplementary NLP source if FMP's news coverage proves insufficient during Sprint 23. |
| **Cross-References** | DEC-257 (hybrid architecture), DEC-258 (FMP Starter), DEC-082 (Databento primary), DEF-011 (IQFeed — remains deferred for forex/breadth use case) |
| **Status** | Active |

---

### DEC-261 | ORB Family Same-Symbol Mutual Exclusion

| Field | Value |
|-------|-------|
| **Date** | 2026-03-05 |
| **Sprint** | 21.5.1 (Session 1) |
| **Decision** | ORB Breakout and ORB Scalp share a class-level `_orb_family_triggered_symbols: ClassVar[set[str]]` on `OrbBaseStrategy`. When either subclass generates a signal for a symbol, it adds that symbol to the set. Phase 2 breakout detection in `on_candle` checks the set and skips if the symbol is already present. The set is cleared in `reset_daily_state()`. An autouse pytest fixture in `tests/conftest.py` clears the set between tests. |
| **Rationale** | C2 paper trading session (March 4) produced 4 dual-fire incidents: AMZN, NFLX, META, and SPY each triggered both ORB Breakout and ORB Scalp simultaneously on the same candle. This doubled risk exposure on those symbols (2 positions × ~5% concentration = ~10–12.5% actual exposure) and violated the concentration limit's intent. Since both strategies share OrbBaseStrategy and monitor the same opening range, the first to fire wins. ClassVar ensures cross-instance visibility without Event Bus coupling. |
| **Alternatives** | (1) Event Bus notification between strategies — rejected because OrbBaseStrategy already shares code; ClassVar is simpler and zero-latency. (2) Risk Manager cross-strategy duplicate check — rejected because it would require the Risk Manager to understand strategy family relationships, violating separation of concerns. (3) Orchestrator-level coordination — rejected as too heavyweight for a same-family exclusion; Orchestrator manages strategy lifecycle, not signal-level deconfliction. |
| **Cross-References** | DEC-120 (OrbBaseStrategy ABC), DEC-121 (ALLOW_ALL cross-strategy), DEC-261 |
| **Status** | Active |

---

### DEC-262 | Roadmap Consolidation — Unified Strategic Direction

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Between sprints (documentation maintenance) |
| **Decision** | Consolidated four competing roadmap documents (`docs/research/ARGUS_Expanded_Roadmap.md`, `docs/argus_unified_vision_roadmap.md`, `docs/argus_master_sprint_plan.md`, `docs/10_PHASE3_SPRINT_PLAN.md`) into a single canonical `docs/roadmap.md`. The Unified Vision (ensemble/systematic search thesis) is adopted as the strategic direction with modifications: (1) Phase 6 expanded from 3 to 4 sprints — Sprint 27 restores short selling infrastructure + Parabolic Short + Pattern Expansion II; Sprint 28 becomes standalone Learning Loop V1 (was combined with Pattern Expansion II). Results in 13–15 artisanal strategies at Phase 6 Gate instead of 9–11. (2) Phases 7–10 renumbered +1 (BacktestEngine=Sprint 29, pivotal experiment=Sprint 33). (3) "Constellation" visualization renamed to "Synapse" (neural/brain imagery). (4) Post-Revenue Backlog consolidated from all sources: Order Flow V1/V2/L3 (DEC-238), multi-asset expansion (crypto/forex/futures), Cython/Rust hot path, Monte Carlo, Advanced Regime Engine, multi-account management, tax optimization, strategy breeding, cross-market signals. (5) Three superseded documents archived. (6) File naming standardized: numbered prefixes dropped, kebab-case adopted. |
| **Alternatives Considered** | 1. Artisanal-only path (Phase 3 plan, skip ensemble infrastructure): Rejected — ensemble vision is highest-ceiling outcome and everything through Phase 6 is valuable regardless; Phase 8 go/no-go gate protects against downside. 2. Unified Vision as-is (9–11 artisanal strategies, no short selling): Rejected — dropping short selling and reducing artisanal count weakened Phase 6 baseline without benefit. 3. Maintain multiple roadmap documents with cross-references: Rejected — four competing documents with conflicting sprint orderings caused confusion; Claude Code sessions were planning against Phase 3 ordering while Unified Vision existed unlinked. |
| **Rationale** | The two-Claude workflow's velocity depends on documentation currency. Four roadmap documents — three of which weren't referenced by operational docs (`project-knowledge.md`, `CLAUDE.md`) — meant the strategic direction existed in documents Claude Code never saw. Consolidation to a single canonical roadmap.md ensures all participants (Claude.ai, Claude Code, the developer) are aligned on the plan at all times. Short selling restored because going long-only into the ensemble phase is a structural limitation. Phase 6 expanded because the Unified Vision's Sprint 27 (Pattern Expansion II + Learning Loop V1, estimated 4–5 days) was overloaded — Learning Loop deserves standalone sprint treatment. |
| **Cross-References** | DEC-163 (expanded vision), DEC-238 (Order Flow deferred), DEC-166 (short selling), DEC-167 (pattern expansion), DEC-079 (parallel tracks). Risk: historical data sufficiency (Phase 7 Gate resolution). |
| **Status** | Active |

---

### DEC-263 | Full-Universe Strategy-Specific Monitoring Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Pre-Sprint 23 planning |
| **Decision** | Full-universe strategy-specific monitoring. Each strategy declares `universe_filter` (sector, market cap, float, price range, volume) and `behavioral_triggers` (pattern conditions requiring live indicator data) in structured YAML config. ARGUS subscribes to the broadest viable universe via Databento EQUS.MINI (3,000–5,000 symbols). Full IndicatorEngine computation (VWAP, ATR, EMAs) runs on every subscribed symbol from market open — no lazy computation, no tiered processing. Strategies evaluate every candle against their declared filters with early-exit for non-matching symbols. Universe Manager replaces "Pre-Market Intelligence Engine" in Sprint 23 scope. Pre-market scan is the Universe Manager's first invocation, not a separate system. Cython optimization deferred until profiling shows need. |
| **Rationale** | Stateful indicators (VWAP cumulative sums, ATR Wilder smoothing, SMA rolling windows) require continuous computation — lazy backfill on first signal creates multi-minute latency at the worst moment. Processing budget analysis shows ~8,000–12,000 ticks/sec across full universe. Per-tick work (VWAP sums, candle high/low, volume) ~1–2μs/event → ~2% CPU. Per-candle work (ATR, EMAs, strategy evaluation at 4,000 updates/min) negligible. Total: ~2–4% of one CPU core in pure Python with ~97% headroom. Most strategy setups are purely technical (consolidation breakouts, VWAP reclaims) and don't require news correlation — broad technical monitoring captures far more opportunities than catalyst-driven watchlist expansion. |
| **Alternatives** | (1) Static pre-market watchlist — rejected: misses intraday setups forming on symbols not in morning scan. (2) Tiered/lazy processing — rejected: stateful indicators require continuous computation; backfill latency unacceptable at signal time. (3) Catalyst-driven expansion only — rejected: most setups are technical, not news-correlated; overweights catalyst dependency. (4) Cython from Sprint 23 — rejected: 2–4% CPU with 97% headroom doesn't justify premature optimization; defer until Phase 9+ ensemble scale if profiling shows need. |
| **Cross-References** | DEC-092 (IndicatorEngine extraction), DEC-248 (EQUS.MINI), DEC-258 (FMP Starter for scanning), DEF-015 (superseded — full-universe scanning now addressed), DEC-163 (expanded vision). Risk: RSK-046 (broad-universe processing throughput at ensemble scale). |
| **Status** | Active |

---

### DEC-264 | Full DEC-170 Scope in Sprint 22

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Implement the full scope of DEC-170 (AI Copilot with approval workflow, context injection, persistent conversations, daily summaries, insight card, learning journal) in a single sprint rather than phasing across multiple sprints. |
| **Alternatives Considered** | 1. Phase 1/Phase 2 split (chat only → approval workflow): Rejected because the approval workflow is the architecturally interesting part and testing it requires the full pipeline. 2. Backend-only sprint + frontend sprint: Rejected because validating the UX requires end-to-end testing in the same sprint cycle. |
| **Rationale** | The Copilot shell was already built (Sprint 21d). The backend and frontend are tightly coupled for this feature — splitting would mean the shell sits unused for another sprint. Steven's "build complete, not phased" principle applies. Sprint 22 is the largest sprint to date (9 sessions). Compaction risk managed via a/b session splits. |
| **Cross-References** | DEC-170, DEC-212 |
| **Status** | Active |

---

### DEC-265 | WebSocket for AI Chat Streaming

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Use WebSocket (`WS /ws/v1/ai/chat`) for AI chat streaming, not Server-Sent Events (SSE). JWT auth token sent in initial message, matching existing `/ws/v1/live` pattern. |
| **Alternatives Considered** | 1. SSE (Server-Sent Events): Rejected because SSE is unidirectional (server→client only). WebSocket supports bidirectional communication needed for stream cancellation and future server-initiated messages. 2. Long polling: Rejected — adds latency, complexity, and doesn't support streaming. |
| **Rationale** | ARGUS already has WebSocket infrastructure (`/ws/v1/live`). Reusing the same transport and auth pattern reduces complexity. WebSocket also enables future features like server-initiated alerts (Sprint 23+). |
| **Constraints** | Must coexist with existing `/ws/v1/live` endpoint. Separate router, separate connection set. |
| **Cross-References** | DEC-170, DEC-099 |
| **Status** | Active |

---

### DEC-266 | Calendar-Date Conversation Keying with Tags

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Key conversations by calendar date (not trading day) with an optional tag field. Valid tags: "pre-market", "session", "research", "debrief", "general" (default). |
| **Alternatives Considered** | 1. Trading-day keying: Rejected because trading days have ambiguous boundaries (pre-market for Monday starts Sunday night) and weekend research conversations wouldn't belong to any trading day. 2. No tags: Rejected because filtering by conversation type is valuable for the Learning Journal. |
| **Rationale** | Calendar date is unambiguous. Tags provide flexible categorization without rigid structure. Tags auto-assigned by page context (e.g., Dashboard → "session", Performance → "research"). |
| **Constraints** | Tag validation enforced in ConversationManager. Invalid tags raise ValueError. |
| **Cross-References** | DEC-170, DEC-268 |
| **Status** | Active |

---

### DEC-267 | Action Proposal TTL with DB Persistence

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Action proposals have a 5-minute TTL (configurable in AIConfig.proposal_ttl_seconds). Proposals are persisted to `ai_action_proposals` SQLite table. Expired proposals cleaned on startup and via periodic 30-second cleanup task. |
| **Alternatives Considered** | 1. In-memory proposals: Rejected because proposals would be lost on restart, creating safety ambiguity (was it approved before the crash?). 2. Longer TTL (15 min): Rejected because market conditions change rapidly. 5 minutes is enough to review but short enough that stale proposals auto-expire. |
| **Rationale** | DB persistence ensures audit trail and restart safety. Short TTL prevents stale approvals. Periodic cleanup prevents table growth. |
| **Constraints** | Shares SQLite write lock with other AI tables and Trade Logger (RSK-031). |
| **Cross-References** | DEC-272, RSK-029, RSK-031 |
| **Status** | Active |

---

### DEC-268 | Per-Page Context Injection Hooks

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Each of the 7 Command Center pages provides context to the AI Copilot via a `useCopilotContext` hook. Context includes page name, selected entity (if any), and key visible data. Context is registered in the Zustand store and included in API calls. |
| **Alternatives Considered** | 1. Global context only (no per-page): Rejected because Claude's responses are dramatically more useful when it knows what the operator is looking at. 2. URL-based inference: Rejected — fragile, doesn't capture selected entities or visible data. |
| **Rationale** | The hook pattern is lightweight (2 lines per page), lazy-evaluated via useRef to prevent re-registration, and the context is attached at send-time (not continuously streamed). |
| **Constraints** | Total page context must stay within 2,000-token budget. |
| **Cross-References** | DEC-170, DEC-273 |
| **Status** | Active |

---

### DEC-269 | Demand-Refreshed AI Insight Card

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Dashboard AI insight card is demand-refreshed: manual click or auto-refresh every 5 minutes during market hours. Cached response with configurable TTL. Graceful "AI not available" state when service is disabled. |
| **Alternatives Considered** | 1. Always-on auto-refresh: Rejected — unnecessary API cost during non-market hours. 2. Push-based (server sends insight): Rejected — adds complexity; demand-pull is simpler and sufficient. |
| **Rationale** | During market hours, insights are time-sensitive and worth refreshing. Outside market hours, manual refresh is sufficient. |
| **Constraints** | Requires `useAIInsight` TanStack Query hook with conditional `refetchInterval`. |
| **Cross-References** | DEC-170, DEC-274 |
| **Status** | Active |

---

### DEC-270 | Markdown Rendering Stack

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Use `react-markdown` + `remark-gfm` + `rehype-sanitize` for rendering AI responses. XSS protection mandatory via rehype-sanitize. |
| **Alternatives Considered** | 1. Rendering raw HTML: Rejected — XSS vulnerability. 2. Plain text only: Rejected — Claude's responses use markdown heavily (code blocks, tables, lists). 3. marked + DOMPurify: Rejected — react-markdown integrates better with React component model. |
| **Rationale** | react-markdown is the standard React markdown library. remark-gfm adds GitHub-flavored markdown (tables, strikethrough). rehype-sanitize prevents XSS from any HTML in Claude's responses. |
| **Constraints** | Bundle size impact: ~30-50KB gzipped (well under 200KB threshold). |
| **Cross-References** | DEC-170 |
| **Status** | Active |

---

### DEC-271 | Claude tool_use for Structured Action Proposals

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Use Claude's native `tool_use` API for structured action proposals. Tools are defined as JSON schemas passed in the API request. When Claude wants to propose an action, it emits a `tool_use` content block. Backend intercepts the block, creates an `ActionProposal`, returns a `tool_result`, and Claude continues its response. |
| **Alternatives Considered** | 1. JSON-in-free-text parsing: Rejected per adversarial review finding. Fragile regex parsing of JSON embedded in natural language responses. Claude's native tool_use is purpose-built for this and dramatically more reliable. |
| **Rationale** | tool_use is the Anthropic-recommended approach for structured outputs. It guarantees valid JSON matching the schema. The adversarial review correctly identified that rejecting tool_use in favor of manual parsing was the highest-risk design decision in the original spec. |
| **Constraints** | Tool definitions must be included in every API call (adds to input token count). |
| **Cross-References** | DEC-272, DEC-273 |
| **Status** | Active |

---

### DEC-272 | Five-Type Closed Action Enumeration

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | MVP supports exactly 5 action types: `propose_allocation_change`, `propose_risk_param_change`, `propose_strategy_suspend`, `propose_strategy_resume`, `generate_report`. First 4 require approval. `generate_report` executes immediately. |
| **Alternatives Considered** | 1. Open-ended actions (Claude proposes anything): Rejected — unbounded action space is a safety risk. 2. Fewer actions (just suspend/resume): Rejected — allocation and risk param changes are high-value for the operator. 3. More actions (annotate_trade, manual_rebalance): Rejected for MVP — annotate_trade is low value, manual_rebalance is high risk with unclear UX. |
| **Rationale** | These 5 actions cover the operator's primary needs during a trading session. The closed enumeration ensures every possible AI action has been reviewed and has an executor with validation. |
| **Constraints** | Unrecognized tool calls from Claude are logged and treated as errors (no ActionProposal created). |
| **Cross-References** | DEC-271, DEC-170 |
| **Status** | Active |

---

### DEC-273 | System Prompt Template with Token Budgets

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | System prompt template includes: ARGUS description, operator context, active strategy summaries, behavioral guardrails (advisory only, never recommend specific entries/exits, caveat uncertainty, reference actual data, never fabricate). Mandatory tool_use directive section instructs Claude to call tools immediately for configuration changes. Token budgets: system ≤1,500, page context ≤2,000, history ≤8,000, response ≤4,096. |
| **Alternatives Considered** | 1. No system prompt (Claude defaults): Rejected — Claude needs domain context to be useful. 2. Minimal prompt (just "you are a trading assistant"): Rejected — behavioral guardrails are critical for safety. 3. Dynamic prompt construction (fetched from DB): Rejected for MVP — over-engineering. Prompts managed in code. |
| **Rationale** | The system prompt is the most important safety mechanism in the AI layer. Explicit guardrails prevent Claude from recommending specific trades or fabricating data. The mandatory tool_use directive prevents Claude from narrating intent instead of calling tools. |
| **Constraints** | Total context window budget: ~12,000 tokens for system + page + history. Remainder for response. |
| **Cross-References** | DEC-271, DEC-098 |
| **Status** | Active |

---

### DEC-274 | Per-Call Cost Tracking

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 |
| **Decision** | Track token usage for every Claude API call in `ai_usage` table. Fields: conversation_id, timestamp, input_tokens, output_tokens, model, estimated_cost_usd. `GET /api/v1/ai/usage` returns daily and monthly totals. `GET /api/v1/ai/status` includes current-month spend and per-day average. |
| **Alternatives Considered** | 1. Aggregate-only tracking (daily totals): Rejected — per-call granularity enables debugging of cost anomalies. 2. No cost tracking (rely on Anthropic dashboard): Rejected — operator needs in-app visibility without switching to another service. |
| **Rationale** | Cost is trivial per DEC-098, but tracking from day one enables trend analysis and anomaly detection. The Anthropic dashboard has delayed reporting; in-app tracking is real-time. |
| **Constraints** | Streaming responses extract actual token counts from API events (`message_start` for input, `message_delta` for output). Falls back to content-length estimation (4 chars ≈ 1 token) if API usage data is unavailable. Non-streaming `/chat` responses use exact API-reported counts. All timestamps stored in ET (DEC-276). |
| **Cross-References** | DEC-098, RSK-028 |
| **Status** | Active |

---

### DEC-275 | Compaction Risk Scoring System

| Field | Value |
|-------|-------|
| **Date** | 2026-03-06 |
| **Sprint** | Sprint 22 (mid-sprint process improvement) |
| **Decision** | Replace the qualitative compaction risk assessment ("Low / Medium / High based on files created, files modified, integration surface area") with a quantitative point-based scoring system. Each session is scored across 7 factors: new files created (+2 each), files modified (+1 each), pre-flight context reads (+1 each), new tests (+0.5 each), complex integration wiring (+3), external API debugging (+3), and large files exceeding ~150 lines (+2 each). Thresholds: 0–8 Low (proceed), 9–13 Medium (proceed with caution), 14–17 High (must split), 18+ Critical (split into 3+). Each sub-session must independently score ≤13. Session Breakdown artifact must include the full scoring table per session. Compaction events logged in close-out reports with planning score and failure point for threshold calibration. |
| **Alternatives Considered** | 1. Keep qualitative ratings with stricter reviewer judgment — rejected because Sprint 22 proved the qualitative system consistently under-rates risk; "Medium-Low" and "Medium" sessions both compacted. 2. Fixed heuristic (e.g., "max 2 files created per session") — rejected because file count alone is insufficient; a session creating 1 large file with 10 context reads and 15 tests is higher risk than one creating 3 small files with 2 context reads and 4 tests. |
| **Rationale** | Sprint 22 Sessions 3a and 3b both compacted despite being rated Medium-Low and Medium respectively. Retrospective analysis: Session 3a scored ~15 (1 large file, 2 mods, 6 context reads, 8 tests, integration wiring). Session 3b scored ~23 (3 files, 1 large, 2 mods, 10 context reads, 15 tests, integration wiring) — it compacted before reaching 50% of requirements. The qualitative assessment missed two critical factors: (a) pre-flight context reads consume significant context window before implementation begins, and (b) test count is a major token consumer that scales with scope. The point system captures all token-consuming factors with weights calibrated against Sprint 22 empirical data. |
| **Cross-References** | DEC-264 (Sprint 22 scope), DEC-079 (parallel tracks — session design). Protocol updates: `sprint-planning.md`, `implementation-prompt.md`, `review-prompt.md` in Claude.ai project. |
| **Status** | Active |

---

### DEC-276 | AI Timestamps Standardized on ET

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Sprint 22.1 |
| **Decision** | All AI-related timestamps and date-keyed operations use ET (America/New_York), stored as naive local datetime strings (no timezone offset). Applies to: `ai_usage.timestamp`, conversation `date` fields in creation paths, and usage query date parameters. |
| **Alternatives Considered** | 1. UTC with offset (e.g., `2026-03-07T02:30:00+00:00`): Rejected — SQLite's `date()` function cannot reliably extract the date from offset-bearing ISO strings, causing query mismatches. 2. UTC without offset (e.g., `2026-03-07T02:30:00`): Rejected — requires timezone conversion at every query point. This was the original implementation and failed in production: server running in Taipei (UTC+8) stored UTC timestamps, but `date.today()` queries used server-local dates, producing a multi-hour window daily where usage records were invisible. 3. Store both UTC and ET columns: Rejected — over-engineered, doubles write cost for a single use case. |
| **Rationale** | ARGUS's canonical timezone is ET because US markets operate in ET. Conversation date keying (DEC-266) is designed around trading days, which are ET days. Storing timestamps as naive ET strings means `date(timestamp)` in SQLite directly yields the ET date, matching the query parameters without conversion. The bug this fixes: usage tracking returned all-zero results for any server not in the ET timezone because `date.today()` returned a different date than the UTC-stored timestamps. Applied to `usage.py`, `routes/ai.py`, `websocket/ai_chat.py`, and `conversations.py`. |
| **Constraints** | All future AI-layer code that stores or queries timestamps must use `datetime.now(ZoneInfo("America/New_York"))`. UTC must not be used for AI timestamp storage. The canonical import is `from zoneinfo import ZoneInfo` with `ZoneInfo("America/New_York")` (not `US/Eastern` or pytz). |
| **Cross-References** | DEC-266 (calendar-date conversation keying), DEC-274 (per-call cost tracking) |
| **Status** | Active |

---

### DEC-277 | Fail-Closed on Missing Reference Data in System Filters

| Field | Value |
|-------|-------|
| **Date** | 2026-03-08 |
| **Sprint** | Sprint 23.05 |
| **Decision** | Symbols with `None` values for `prev_close` or `avg_volume` are excluded at the system filter level in `UniverseManager._apply_system_filters()`. Symbols with no cached reference data are excluded from strategy routing in `_symbol_matches_filter()`. The semantic intent of "minimum price" and "minimum volume" filters requires data to evaluate — absence of data is not a pass condition. |
| **Alternatives Considered** | 1. Fail-open with logging (monitor then decide): Rejected — investigation confirmed a concrete exploit path where ORB strategies accept None ATR and Risk Manager does not check reference data, so no downstream guard exists. Deferring the decision risks live capital on unknown symbols. 2. Guard at routing table level only: Rejected — system filters are the earliest gate. Letting unknown symbols into the viable universe wastes memory and creates false coverage. 3. Guard at strategy level: Rejected — requires modifying all 4 strategy Python files (do-not-modify scope boundary) and creates N-strategy maintenance burden vs. one centralized check. |
| **Rationale** | Sprint 23 Session 1b judgment call allowed None values to pass system filters (rationale: missing data shouldn't auto-disqualify). Post-sprint investigation traced the full path: symbol with all-None reference data → passes system filters → routed to all strategies → ORB accepts None ATR → signal generated → Risk Manager approves (no reference data checks) → order placed on unknown symbol. Worst case: trading low-float traps, illiquid symbols, or untrackable sector exposure. Trading context demands fail-closed on unknowns. |
| **Constraints** | Cannot modify strategy Python files (Sprint 23 scope boundary). System filter and routing table are the only gates within scope. |
| **Cross-References** | DEC-263 (full-universe monitoring architecture) |
| **Status** | Active |

---

### DEC-278 | Autonomous Sprint Runner Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Build a Python-based orchestrator (`scripts/sprint-runner.py`) that drives the sprint execution loop by invoking Claude Code CLI programmatically. The runner is a deterministic state machine — it does not use LLM tokens for coordination logic. It reads sprint package files from disk, invokes Claude Code for each session, parses structured output, makes rule-based proceed/halt decisions, and maintains full state on disk for resume-from-checkpoint capability. Supports two modes: autonomous (full loop) and human-in-the-loop (optional structured logging). |
| **Alternatives Considered** | 1. LLM-based orchestrator: Rejected — coordination logic is deterministic, wastes tokens. 2. Agent teams as orchestrator: Rejected — sprint sessions are sequential, not parallel. 3. Third-party framework (LangChain, CrewAI): Rejected — unnecessary dependency complexity. |
| **Rationale** | Sprint packages are already machine-readable. A Python script is the simplest, most reliable, and most debuggable solution. Zero LLM cost for coordination, immune to compaction. |
| **Constraints** | Must work with Claude Code CLI, support resume from any checkpoint, preserve all session output for audit trail. |
| **Cross-References** | DEC-275 (compaction risk scoring), DEC-290 (Claude.ai role) |
| **Status** | Active |

---

### DEC-279 | Notification via ntfy.sh

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Use ntfy.sh as the primary notification channel for runner events. Mobile push notifications via the ntfy app on iPhone. Single HTTP POST per notification, no API keys, no OAuth. Five notification tiers: HALTED (high priority), SESSION_COMPLETE (normal), PHASE_TRANSITION (low), WARNING (low), COMPLETED (normal). HALTED and COMPLETED cannot be disabled. |
| **Alternatives Considered** | 1. Slack webhook only: Rejected — requires app setup and running Slack client. 2. Email only: Rejected — lacks urgency tiers. 3. SMS via Twilio: Rejected — cost and complexity. |
| **Rationale** | Runner operates while developer is away. ntfy.sh provides reliable mobile push with simplest possible integration. |
| **Constraints** | Must work on iPhone, support priority levels, not require running a server. |
| **Cross-References** | DEC-278 (runner architecture) |
| **Status** | Active |

---

### DEC-280 | Structured Close-Out Appendix

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Extend the close-out skill to produce a machine-parseable JSON block appended to the existing human-readable close-out report. The JSON block is fenced with ` ```json:structured-closeout ` for reliable extraction. Contains: session identifier, verdict enum, test counts, files created/modified, scope additions, scope gaps, prior-session bugs, deferred observations, doc impacts, DEC entries needed. |
| **Alternatives Considered** | 1. Separate structured file: Rejected — creates two artifacts. 2. YAML instead of JSON: Rejected — JSON more reliably parseable. 3. Replace human-readable entirely: Rejected — human readability essential. |
| **Rationale** | Runner needs machine-parseable outcomes for proceed/halt decisions. Structured appendix gives reliable data while preserving human-readable report. |
| **Constraints** | Must not break existing close-out format, extractable via regex, validate against schema. |
| **Cross-References** | DEC-278 (runner architecture), DEC-282 (Tier 2.5 triage) |
| **Status** | Active |

---

### DEC-281 | Structured Review Verdict

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Extend the review skill to produce a machine-parseable JSON block appended to the existing human-readable review report. Fenced with ` ```json:structured-verdict `. Contains: verdict enum (CLEAR / CONCERNS / ESCALATE), findings array with severity and category, files reviewed, spec-conformance assessment, recommended actions. |
| **Alternatives Considered** | 1. Parse verdict from prose: Rejected — fragile and error-prone. 2. Structured-only output: Rejected — human readability needed for manual mode. |
| **Rationale** | Same as DEC-280. Runner needs reliable signal for proceed vs halt. |
| **Constraints** | Must not break existing review format. CLEAR/CONCERNS/ESCALATE enum unambiguous. |
| **Cross-References** | DEC-280 (structured close-out), DEC-278 (runner) |
| **Status** | Active |

---

### DEC-282 | Tier 2.5 Automated Triage Layer

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Insert an automated triage step between Tier 2 review and human escalation. When structured close-out contains non-empty scope_gaps or prior_session_bugs, runner invokes a separate Claude Code session with a triage prompt. Triage session classifies issues using Category 1–4 system and recommends: insert fix session, defer to post-sprint, or halt for human decision. Read-only session (no file modifications). |
| **Alternatives Considered** | 1. Rule-based classification only: Rejected — scope gap severity requires language understanding. 2. Always halt for human triage: Rejected — eliminates autonomy benefit. 3. Never halt: Rejected — Category 3–4 issues require human judgment. |
| **Rationale** | Tier 2.5 handles middle-severity cases that don't warrant waking the developer but aren't simple enough for regex rules. Uses LLM judgment in constrained, auditable way. |
| **Constraints** | Read-only, receives sprint spec for context, produces structured output, logged to issues.jsonl. |
| **Cross-References** | DEC-278 (runner), DEC-280 (structured close-out) |
| **Status** | Active |

---

### DEC-283 | Spec Conformance Check at Session Boundaries

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | After each session receives a CLEAR verdict, runner invokes spec conformance check via Claude Code subagent. Check compares cumulative git diff (sprint start to current HEAD) against sprint spec and spec-by-contradiction. Output: CONFORMANT / DRIFT-MINOR / DRIFT-MAJOR. CONFORMANT and DRIFT-MINOR: proceed. DRIFT-MAJOR: halt and notify. |
| **Alternatives Considered** | 1. No conformance check: Rejected — small deviations compound. 2. Check only at sprint end: Rejected — drift caught early is cheap to fix. 3. AST-based automated checking: Rejected — too complex, naming drift requires semantic understanding. |
| **Rationale** | Session reviews verify individual sessions. Conformance checks verify cumulative result matches overall sprint design. Catches emergent drift. |
| **Constraints** | Uses cumulative diff, references both spec and spec-by-contradiction, lightweight execution. |
| **Cross-References** | DEC-278 (runner), DEC-281 (structured verdict) |
| **Status** | Active |

---

### DEC-284 | Run-Log Architecture

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Every byte of runner output written to disk immediately in structured run-log directory. Structure: `run-state.json`, `session-{id}/` with implementation output, closeout, review, git-diff, `issues.jsonl`, `scope-changes.jsonl`, `doc-sync-queue.jsonl`, `work-journal.md`. All .jsonl files append-only. Work-journal.md auto-generated from structured data. |
| **Alternatives Considered** | 1. In-memory state: Rejected — crash loses all progress. 2. Database (SQLite): Rejected — overkill, JSONL simpler and git-friendly. 3. Claude.ai conversation as state: Rejected — subject to compaction, not machine-parseable. |
| **Rationale** | Solves compaction problem permanently. No LLM invocation needs full sprint history — state lives on disk. Each session gets fresh context window. |
| **Constraints** | All writes atomic (temp → rename), committed to git after each session, JSONL one object per line. |
| **Cross-References** | DEC-278 (runner), DEC-275 (compaction risk scoring) |
| **Status** | Active |

---

### DEC-285 | Git Hygiene Protocol for Autonomous Runner

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Runner manages git state: before each session create branch checkpoint, after CLEAR verdict + conformance check commit with `[Sprint N] Session {id}: {title}`, after ESCALATE rollback to checkpoint, fix sessions get own commits, resume validates current SHA matches run-state.json. All diffs saved as .patch files regardless of verdict. |
| **Alternatives Considered** | 1. One big commit at sprint end: Rejected — loses per-session atomicity. 2. Feature branches per session: Rejected — unnecessary proliferation for sequential work. |
| **Rationale** | Clean git state prerequisite for session isolation. Per-session commits provide clean audit trail. |
| **Constraints** | Never leave repo dirty between sessions, preserve all work via .patch files. |
| **Cross-References** | DEC-278 (runner), DEC-284 (run-log) |
| **Status** | Active |

---

### DEC-286 | Runner Retry Policy

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Runner retries session up to 2 times when failure appears transient: no output, test suite timeout, git operation failure, CLI non-zero exit without structured output. Uses exponential backoff (DEC-295). LLM-compliance failures (output present but structured JSON missing) get reinforcement instruction on first retry. After 2 retries, halt and notify. Non-transient failures (test assertions, ESCALATE verdict) never retried. |
| **Alternatives Considered** | 1. No retries: Rejected — transient failures cause unnecessary interruption. 2. Unlimited retries: Rejected — burns tokens on broken sessions. 3. Retry with modified prompt: Rejected — runner should not modify prompts. |
| **Rationale** | Transient failures common with API calls and test suites. Two retries survives momentary hiccups. |
| **Constraints** | Retry count configurable, each retry starts from clean git state. |
| **Cross-References** | DEC-278 (runner), DEC-285 (git hygiene), DEC-295 (exponential backoff) |
| **Status** | Active |

---

### DEC-287 | Cost Tracking and Ceiling

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Runner tracks estimated token usage per session (from CLI output), maintains running cost estimate in run-state.json. Configurable cost ceiling triggers HALTED notification if cumulative cost exceeds threshold. Uses API token pricing as proxy even on subscription plan. |
| **Alternatives Considered** | 1. No cost tracking: Rejected — no visibility into consumption. 2. Hard kill: Rejected — halt with notification gives option to continue. |
| **Rationale** | Autonomous execution removes natural cost awareness. Runner needs circuit breaker for runaway consumption. |
| **Constraints** | Default ceiling $50/sprint, token counts from CLI stdout/stderr. |
| **Cross-References** | DEC-278 (runner), DEC-274 (AI layer cost tracking) |
| **Status** | Active |

---

### DEC-288 | Dynamic Test Baseline Patching

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | In autonomous mode, runner dynamically patches pre-flight test count based on previous session's actual count from structured close-out. Original planning-time count preserved for audit; runner adds comment with adjusted count. In human-in-the-loop mode, developer manually notes current count. |
| **Alternatives Considered** | 1. Static counts only: Rejected — session 1 adds tests, making session 2's static count incorrect. 2. Remove test count entirely: Rejected — knowing expected count is valuable sanity check. |
| **Rationale** | Sequential sessions accumulate tests. Static prompts can't predict exact count. Dynamic patching keeps pre-flight checks meaningful. |
| **Constraints** | Original count preserved, patching uses structured close-out test.after field. |
| **Cross-References** | DEC-278 (runner), DEC-280 (structured close-out) |
| **Status** | Active |

---

### DEC-289 | Session Parallelizable Flag

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Add `parallelizable` field (boolean, default: false) to Session Breakdown artifact. When true, runner may invoke Claude Code with agent teams enabled for internal parallelism. Requires Creates list with clearly independent outputs that don't modify same files. Sprint planner must justify flag. In human-in-the-loop mode, flag is informational only. |
| **Alternatives Considered** | 1. Always use agent teams: Rejected — 3–4× more tokens, coordination overhead. 2. Never use: Rejected — some sessions benefit from parallel execution. 3. Runtime decision: Rejected — parallelizability is planning decision. |
| **Rationale** | Agent teams powerful but expensive. Explicit planning-time decision ensures justified use. |
| **Constraints** | Default false, sessions scoring 14+ on compaction risk should NOT be parallelized. |
| **Cross-References** | DEC-278 (runner), DEC-275 (compaction risk scoring) |
| **Status** | Active |

---

### DEC-290 | Claude.ai Role in Autonomous Mode

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | In autonomous mode, Claude.ai shifts to exception handler and strategic layer. Stays in Claude.ai: sprint planning, adversarial review, Tier 3 review, strategic check-ins, codebase audits, discovery. Moves to runner + Claude Code: work journal triage (→ structured close-out + Tier 2.5), fix session generation, session-to-session orchestration, doc-sync execution. Implementation and review sessions stay in Claude Code unchanged. |
| **Alternatives Considered** | 1. Remove Claude.ai entirely: Rejected — planning/adversarial review need multi-turn exploratory reasoning. 2. Keep Claude.ai in real-time loop: Rejected — mechanical parts waste tokens and developer time. |
| **Rationale** | Claude.ai strengths are exploratory reasoning, design iteration, adversarial analysis — planning-time and exception-time activities. Execution loop is mechanical coordination. |
| **Constraints** | Claude.ai remains venue for all architectural decisions. Runner never makes decisions requiring DEC entry. |
| **Cross-References** | DEC-278 (runner), DEC-282 (Tier 2.5 triage) |
| **Status** | Active |

---

### DEC-291 | Independent Test Verification at Session Boundaries

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Runner independently runs test suite after implementation completes and before invoking review, comparing actual results against structured close-out's claimed test counts. If close-out claims `all_pass: true` but runner's run shows failures, or count diverges beyond tolerance (default: 0), session is flagged. Addresses compaction risk where LLM produces close-out from memory of earlier test run rather than final state. |
| **Alternatives Considered** | 1. Trust close-out entirely: Rejected — compaction-induced false positives are known failure mode. 2. Re-run tests in review: Rejected — review trusts close-out for baseline. |
| **Rationale** | Close-out produced by same LLM that did implementation. In compaction scenario, both may be degraded. Independent test run by orchestrator (Python, not LLM) is ground-truth check immune to compaction. |
| **Constraints** | Uses same commands as pre-flight (pytest + vitest), tolerance configurable. |
| **Cross-References** | DEC-278 (runner), DEC-280 (structured close-out), DEC-275 (compaction risk) |
| **Status** | Active |

---

### DEC-292 | Pre-Session File Existence Validation

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Before running each session, runner validates that all files listed in prior sessions' Creates columns actually exist on disk. Also validates current session's pre-flight "Read these files" list exists and is non-empty. If validation fails: halt with specific message identifying missing files and which session was supposed to create them. |
| **Alternatives Considered** | 1. Trust CLEAR verdict means all files exist: Rejected — CLEAR means review passed, not every planned artifact produced. |
| **Rationale** | File existence is trivially checkable (zero LLM cost), catches failures that would otherwise cause next session to fail mid-implementation. |
| **Constraints** | Checks existence and non-zero size, not content correctness. Uses session breakdown Creates columns as source of truth. |
| **Cross-References** | DEC-278 (runner) |
| **Status** | Active |

---

### DEC-293 | Compaction Detection Heuristic

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Runner tracks implementation output size (bytes) per session, flags sessions exceeding threshold (default: 100KB) as "compaction-likely." For compaction-likely sessions: independent test verification mandatory, output size logged in run-state.json, WARNING notification sent. Data used to calibrate DEC-275's compaction risk scoring over time. |
| **Alternatives Considered** | 1. No compaction tracking: Rejected — runner has empirical data planning-time system lacks. 2. Automatic session splitting: Rejected — splitting requires planning-time decisions. |
| **Rationale** | Planning-time scoring based on estimates. Runner provides post-implementation ground truth for feedback loop improving future scoring accuracy. |
| **Constraints** | Threshold configurable, data logged for calibration, does not trigger halts by itself. |
| **Cross-References** | DEC-278 (runner), DEC-275 (compaction risk scoring), DEC-291 (test verification) |
| **Status** | Active |

---

### DEC-294 | Session Boundary Diff Validation

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | After implementation completes and before review, runner performs `git diff --stat HEAD` and compares changed files against session breakdown's planned Creates/Modifies columns. Catches gross failures: file should have been created but wasn't, file shouldn't have been touched but was, no changes at all. If diff shows files on "do not modify" list were changed, escalate immediately without invoking review (saves tokens). Missing expected files logged as review context but don't halt. |
| **Alternatives Considered** | 1. Rely entirely on review: Rejected — review costs tokens, free filesystem check pre-empts obvious escalations. |
| **Rationale** | File-level diff checking is instantaneous, catches highest-severity errors (scope violations, missing deliverables) before spending tokens on review. |
| **Constraints** | Filesystem-only (no LLM cost), "do not modify" violations trigger immediate ESCALATE, missing expected files logged not auto-escalated. |
| **Cross-References** | DEC-278 (runner), DEC-283 (spec conformance) |
| **Status** | Active |

---

### DEC-295 | Exponential Retry Backoff

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Runner retries use exponential backoff: first retry at `retry_delay_seconds` (default: 30s), second at `retry_delay_seconds × 4` (default: 120s). If CLI output contains rate-limit error with "retry after" duration, that duration used instead of configured delay. Amends DEC-286. |
| **Alternatives Considered** | 1. Flat delay: Rejected — 30s often insufficient for hourly rate limits but wasteful for 5-second transient hiccups. 2. Parse API headers for exact retry-after: Rejected — runner invokes CLI, rate limit info may be in stderr text. |
| **Rationale** | Exponential backoff is standard approach for rate-limited APIs. Simple to implement, significantly improves second retry success odds. |
| **Constraints** | Backoff multiplier 4×, rate-limit detection via grep for "rate limit" or "429" in stderr. |
| **Cross-References** | DEC-286 (retry policy), DEC-278 (runner) |
| **Status** | Active |

---

### DEC-296 | Planning-Time Mode Declaration

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Sprint planning Phase A adds mode declaration step: "Declare execution mode: autonomous / human-in-the-loop / undecided." Affects downstream artifact generation. Autonomous: skip work journal handoff, generate runner config, parallelizable assessment mandatory. Human-in-the-loop: skip runner config, generate work journal handoff, parallelizable flags informational only. Undecided (default): generate both. |
| **Alternatives Considered** | 1. Always generate everything: Rejected — wastes planning effort on unused artifacts. 2. Decide mode after planning: Rejected — mode affects artifact generation during planning. |
| **Rationale** | Current protocol generates all artifacts regardless of mode. Once dual-mode common, this creates unnecessary work. Early mode declaration allows skipping irrelevant artifacts. |
| **Constraints** | Default "undecided" (safe for transition), mode declaration doesn't affect spec-level artifacts. |
| **Cross-References** | DEC-278 (runner), DEC-290 (Claude.ai role) |
| **Status** | Active |

---

### DEC-297 | Review Context File Hash Verification

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Pre-Sprint 23.5 |
| **Decision** | Runner computes SHA-256 hash of review context file at sprint start, stores in run-state.json. Before each review invocation, re-hashes and compares. If hash changed: log WARNING, proceed with review (change may be intentional during halt resolution), include warning in session's run-log entry. Prevents subtle bug class where review checks against spec different from what implementation was coded against. |
| **Alternatives Considered** | 1. Halt on any change: Rejected — legitimate spec revisions during halt resolution would require manual override. 2. No verification: Rejected — review context file is spec-of-record, undetected changes undermine review process. |
| **Rationale** | Review context file is referenced by all review prompts. Verifying integrity is cheap (one hash per session) defense-in-depth measure. |
| **Constraints** | SHA-256, stored in run-state.json under `review_context_hash`, change detection is WARNING not HALT. |
| **Cross-References** | DEC-278 (runner), DEC-284 (run-log) |
| **Status** | Active |

---

### DEC-298 | FMP Stable API Migration (Legacy v3/v4 → Stable Endpoints)

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Impromptu 23.3 |
| **Decision** | Migrate FMPReferenceClient from legacy `/api/v3/` and `/api/v4/` endpoints to FMP's `/stable/` endpoint family. Profile fetches change from path-based (`/api/v3/profile/AAPL`) to query-param-based (`/stable/profile?symbol=AAPL`). Batch profile requests (comma-separated symbols) replaced with per-symbol calls because the stable API on Starter tier does not support batch. Field name mappings updated: `mktCap` → `marketCap`, `exchangeShortName` → `exchange`, `volAvg` → `averageVolume`. |
| **Alternatives Considered** | 1. Stay on legacy endpoints: Not viable — FMP returns "Legacy Endpoint" errors for accounts created after August 31, 2025. ARGUS account activated March 2026. 2. Upgrade to FMP Premium for batch support: Rejected for now — $59/mo vs $22/mo, and per-symbol calls work within rate limits. Deferred as DEF-035. |
| **Rationale** | Discovered during live deployment testing on March 9, 2026. The FMP Scanner (`fmp_scanner.py`) was already on `/stable/` endpoints, but FMPReferenceClient was not. Hotfix applied during live session and committed to `main`. |
| **Constraints** | FMP unilaterally deprecated legacy endpoints for new accounts. No migration notice was received — discovered at runtime. |
| **Supersedes** | N/A |
| **Cross-References** | DEC-258, DEC-263, RSK-052, DEF-035 |
| **Status** | Active |

---

### DEC-299 | Full-Universe Input Pipe via FMP Stock-List Endpoint

| Field | Value |
|-------|-------|
| **Date** | 2026-03-09 |
| **Sprint** | Impromptu 23.3 |
| **Decision** | Feed the Universe Manager the complete FMP stock-list (~8,000 symbols) instead of the FMP Scanner's 15-symbol pre-market watchlist. Pipeline: `fetch_stock_list()` retrieves `/stable/stock-list` (~8,000 symbols) → `fetch_reference_data()` fetches per-symbol profiles with async concurrency (semaphore=5, 0.2s spacing, 3 retries with exponential backoff) → `build_viable_universe()` applies system-level filters → ~3,000–4,000 viable symbols. Total pre-market load: ~27 minutes. No pre-filtering of the stock-list — all filtering uses actual reference data inside `build_viable_universe()`. Fallback to scanner symbols if stock-list endpoint fails. |
| **Alternatives Considered** | 1. Symbol-pattern pre-filter (exclude OTC-looking tickers by regex): Rejected — cannot reliably determine security type from ticker symbol alone. False-positive risk on legitimate equities (e.g., `BRK-B` contains `-`, `BLDR` ends in `R`). System-level filters already handle this using actual exchange and volume data. 2. FMP exchange-specific endpoint: Not confirmed available on Starter tier. Timing constraint was relaxed (can start earlier), removing motivation. |
| **Rationale** | DEC-263 specified full-universe monitoring with ~3,000–5,000 viable symbols. Sprint 23 built the infrastructure correctly but `main.py` was wired to pass only 15 scanner symbols. This completes the DEC-263 architecture. The 27-minute load time was accepted because pre-market fetch time is not a hard constraint. |
| **Constraints** | FMP Starter tier ($22/mo): 300 API calls/min, no batch endpoints. |
| **Supersedes** | N/A |
| **Cross-References** | DEC-263, DEC-277, DEC-298, RSK-052, DEF-035, DEF-036 |
| **Status** | Active |

---

### DEC-300 | Config-Gated Catalyst Pipeline Feature Flag

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | CatalystPipeline and all intelligence layer components are gated by `catalyst.enabled` config flag (default: `false`). When disabled: no API calls to SEC EDGAR, FMP News, Finnhub, or Claude API for classification. UI components (CatalystBadge, CatalystAlertPanel, IntelligenceBriefView) render gracefully with "No catalysts" state. Pattern follows Universe Manager's config-gated approach (DEC-277). |
| **Alternatives Considered** | 1. Always enabled: Rejected — external API costs accumulate even during development/testing. 2. Environment variable: Rejected — YAML config is established pattern for feature flags. |
| **Rationale** | Allows staged rollout and cost control. Development can proceed without incurring Claude API costs. Production activation is a single config change. |
| **Constraints** | Default `false` prevents accidental cost accumulation. |
| **Cross-References** | DEC-277 (Universe Manager config-gating), DEC-274 (cost tracking) |
| **Status** | Active |

---

### DEC-301 | Rule-Based Fallback Classifier for Catalyst Classification

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | CatalystClassifier uses Claude API as primary classification engine with keyword-based rule fallback when: (1) ANTHROPIC_API_KEY unset, (2) daily cost ceiling reached ($5/day), (3) API call fails after 3 retries. Fallback rules match keywords against headlines: "earnings" → `earnings`, "insider" or "Form 4" → `insider`, "guidance" → `guidance`, "analyst" or "upgrade" or "downgrade" → `analyst`, "FDA" or "SEC" → `regulatory`, "partnership" or "acquisition" → `partnership`, "launch" or "product" → `product`, "restructuring" or "layoff" → `restructuring`, else → `other`. |
| **Alternatives Considered** | 1. Fail closed (no classification): Rejected — catalyst data still valuable even with reduced classification accuracy. 2. Cache Claude responses for similar headlines: Considered for future — adds complexity, headlines rarely repeat exactly. |
| **Rationale** | Graceful degradation is core ARGUS principle (AI layer). Rule-based fallback achieves ~70% accuracy based on headline analysis, sufficient for non-critical catalyst tagging. |
| **Constraints** | Fallback rules are conservative — prefer `other` over false positives. |
| **Cross-References** | DEC-273 (AI graceful degradation), DEC-303 (cost ceiling) |
| **Status** | Active |

---

### DEC-302 | Headline Hash Deduplication for Catalyst Storage

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | CatalystStorage deduplicates catalysts using SHA-256 hash of `symbol + headline + source`. Hash stored in `headline_hash` column with UNIQUE constraint. Insert operations use `INSERT OR IGNORE` to silently skip duplicates. Deduplication prevents: (1) same headline appearing from multiple API calls, (2) headline republished across sources, (3) re-fetching during pipeline retries. |
| **Alternatives Considered** | 1. UNIQUE on (symbol, headline, source): Rejected — headline text can be long, hash is fixed 64 chars. 2. No deduplication: Rejected — API sources frequently return overlapping news, would pollute UI with duplicates. |
| **Rationale** | News aggregators and SEC filings often surface the same information. Hash-based deduplication is O(1) lookup, space-efficient, and collision-resistant for practical purposes. |
| **Constraints** | Hash collision probability negligible for expected volume (<10K catalysts/day). |
| **Cross-References** | DEC-034 (SQLite persistence) |
| **Status** | Active |

---

### DEC-303 | Daily Cost Ceiling Enforcement for Catalyst Classification

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | BriefingGenerator enforces $5/day ceiling on Claude API costs for catalyst classification. Ceiling enforced via UsageTracker integration: before each Claude API call, check `usage_tracker.get_daily_cost()` against `catalyst.daily_cost_ceiling`. When ceiling reached: log warning, switch to rule-based fallback for remainder of day, include "cost ceiling reached" notice in briefing metadata. Ceiling resets at midnight ET. |
| **Alternatives Considered** | 1. No ceiling: Rejected — unbounded API costs unacceptable. 2. Hard cutoff (no fallback): Rejected — defeats purpose of intelligence layer if it just stops working. 3. Per-symbol ceiling: Rejected — adds complexity, daily aggregate is simpler to reason about. |
| **Rationale** | $5/day = ~$150/month worst case, acceptable for intelligence layer value. Ceiling is configurable in system.yaml. UsageTracker already tracks per-call costs (DEC-274). |
| **Constraints** | Default ceiling: $5/day. Configurable via `catalyst.daily_cost_ceiling`. |
| **Cross-References** | DEC-274 (UsageTracker), DEC-301 (fallback classifier) |
| **Status** | Active |

---

### DEC-304 | Three-Source Architecture for Catalyst Data

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | CatalystPipeline ingests from three data sources via abstract `CatalystSource` interface: (1) SECEdgarSource — 8-K filings (material events) and Form 4 (insider transactions) from SEC EDGAR, (2) FMPNewsSource — stock news and press releases from FMP API (already paid via Starter tier), (3) FinnhubSource — company news and analyst recommendations from Finnhub free tier. Each source implements `async fetch(symbols: list[str]) -> list[RawCatalyst]`. Pipeline runs sources in parallel with individual timeout/retry handling. |
| **Alternatives Considered** | 1. Single source (FMP only): Rejected — FMP news coverage is incomplete, SEC filings are authoritative. 2. Paid news API (Benzinga, IEX Cloud): Deferred — free sources sufficient for V1. 3. Web scraping: Rejected — fragile, TOS concerns. |
| **Rationale** | Diversified sources improve coverage. SEC EDGAR is authoritative for regulatory filings. FMP already in stack (DEC-258). Finnhub free tier adds analyst recommendations at no cost. Abstract interface allows adding sources later. |
| **Constraints** | All sources must handle rate limits gracefully. Source failures are isolated (other sources continue). |
| **Cross-References** | DEC-258 (FMP integration), DEC-306 (Finnhub), DEC-164 (NLP catalyst plan) |
| **Status** | Active |

---

### DEC-305 | TanStack Query Hooks for Catalyst and Briefing Data

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | Frontend catalyst data access via TanStack Query hooks: `useCatalysts(symbol?, category?, since?)` for catalyst list with filters, `useIntelligenceBriefings(limit?, since?)` for briefing list, `useIntelligenceBriefing(id)` for single briefing. Hooks follow established patterns (DEC-222): stale time 60s for catalysts, 5min for briefings; retry 3 times with exponential backoff; placeholder data from Zustand store during loading. Query keys: `['catalysts', filters]`, `['intelligence-briefings', params]`, `['intelligence-briefing', id]`. |
| **Alternatives Considered** | 1. Direct fetch in components: Rejected — established TanStack Query pattern provides caching, deduplication, background refresh. 2. Zustand-only: Rejected — TanStack Query handles server state better. |
| **Rationale** | Consistent with existing hooks (useTrades, usePositions, useOrchestratorStatus). Catalyst data is server-authoritative, fits TanStack Query model. |
| **Constraints** | Follows existing hook patterns in `src/hooks/`. |
| **Cross-References** | DEC-222 (aggregate endpoint pattern), DEC-130 (frontend testing) |
| **Status** | Active |

---

### DEC-306 | Finnhub Free Tier for News and Analyst Data

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | Add Finnhub as third catalyst data source using free tier. Endpoints: `/company-news` (company-specific news), `/recommendation` (analyst recommendations). Rate limit: 60 calls/minute on free tier. API key stored in environment variable `FINNHUB_API_KEY`. Source gracefully degrades if API key unset (logs warning, returns empty list). |
| **Alternatives Considered** | 1. Finnhub paid tier: Not needed — free tier covers news and recommendations. 2. Skip Finnhub entirely: Rejected — analyst recommendations are valuable signal not available from other sources. 3. IQFeed: Deferred (DEF-011) — $160–250/mo, overkill for news. |
| **Rationale** | Finnhub free tier provides analyst recommendations (upgrade/downgrade/initiate) not available from SEC EDGAR or FMP. Zero incremental cost. API is well-documented and reliable. |
| **Constraints** | 60 calls/min rate limit. Free tier may have reliability concerns (RSK-053). |
| **Cross-References** | DEC-304 (three-source architecture), DEF-011 (IQFeed deferral), RSK-053 |
| **Status** | Active |

---

### DEC-307 | Intelligence Brief View in The Debrief Page

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.5 |
| **Decision** | Add IntelligenceBriefView as new section in The Debrief page. Three-column layout: (1) briefing list with date/time and status badges, (2) briefing detail with formatted markdown content, (3) catalyst summary panel showing symbols covered and category breakdown. BriefingCard component renders individual briefings with expand/collapse. Generate button triggers `/api/v1/intelligence/briefings/generate` endpoint. View integrated into existing SegmentedTab structure as fourth tab ("Intelligence"). |
| **Alternatives Considered** | 1. Separate Intelligence page: Rejected — aligns with The Debrief's mission (pre-market prep, EOD review). 2. Modal instead of tab: Rejected — briefings are substantial content, deserve full tab real estate. 3. Dashboard widget only: Rejected — dashboard is for glanceable summaries, detailed briefings belong in Debrief. |
| **Rationale** | The Debrief page already houses pre-market briefings (manual markdown). Intelligence briefings are auto-generated pre-market content — natural fit. Keeps intelligence features discoverable alongside existing debrief workflows. |
| **Constraints** | Tab keyboard shortcut: `i` (after existing b/r/j). |
| **Cross-References** | DEC-196 (The Debrief design), DEC-305 (TanStack Query hooks) |
| **Status** | Active |

---

### DEC-308 | CatalystPipeline Initialization Deferred to Sprint 23.6

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | CatalystPipeline was built in Sprint 23.5 but not wired into the running application. Sprint 23.6 adds the startup factory, lifespan wiring, and polling loop as a separate integration sprint. This separates component construction from system integration. |
| **Alternatives Considered** | 1. Wire in Sprint 23.5: Rejected — Sprint 23.5 was already at 6 sessions; adding integration would risk compaction and mixing concerns. 2. Wire in Sprint 24: Rejected — Sprint 24 (Quality Engine) depends on catalyst data flowing; must be live before then. |
| **Rationale** | Follows the "build components first, integrate second" pattern established by Universe Manager (Sprint 23 build + Sprint 23.3 wide pipe). Keeps each sprint focused. Tier 3 review specifically flagged the missing integration. |
| **Constraints** | CatalystPipeline components must remain backward-compatible with Sprint 23.5 tests. |
| **Cross-References** | DEC-300 (config-gated feature), DEC-164 (NLP catalyst plan) |
| **Status** | Active |

---

### DEC-309 | Separate catalyst.db SQLite Database

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | Catalyst data stored in a separate `catalyst.db` SQLite file (path: `{data_dir}/catalyst.db`) rather than the main ARGUS database. |
| **Alternatives Considered** | 1. Main database: Rejected — adds WAL contention with trade logging, couples catalyst lifecycle to trading data. 2. PostgreSQL: Rejected — premature for single-user system, adds operational complexity. |
| **Rationale** | Isolation from trading data, independent lifecycle (can be deleted/rebuilt without affecting trades), avoids WAL contention during high-frequency catalyst inserts. Pattern matches Databento's Parquet cache — separate storage for separate concerns. |
| **Cross-References** | DEC-034 (SQLite persistence), DEC-302 (headline hash dedup) |
| **Status** | Active |

---

### DEC-310 | CatalystConfig Added to SystemConfig

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | `CatalystConfig` added as a field on `SystemConfig` with `Field(default_factory=CatalystConfig)`. Intelligence components initialized in FastAPI lifespan handler when `catalyst.enabled: true`. AppState gains `catalyst_storage` and `briefing_generator` fields. |
| **Alternatives Considered** | 1. Separate config file: Rejected — follows established pattern of embedding feature configs in SystemConfig (AIConfig, UniverseManagerConfig). 2. Environment variable gating: Rejected — YAML config is the standard mechanism (DEC-032). |
| **Rationale** | Consistent with AIConfig and UniverseManagerConfig patterns. Enables lifespan handler access via `app_state.config.catalyst`. Default-factory means zero-config for disabled state. |
| **Cross-References** | DEC-032 (Pydantic config), DEC-300 (config-gated feature) |
| **Status** | Active |

---

### DEC-311 | Post-Classification Semantic Deduplication

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | After classification, CatalystPipeline deduplicates catalysts by `(symbol, category, dedup_window_minutes)` grouping. Within each group, the catalyst with the highest `quality_score` is retained; others are dropped. Window defaults to 30 minutes, configurable via `catalyst.dedup_window_minutes`. |
| **Alternatives Considered** | 1. Pre-classification headline similarity: Rejected — requires NLP infrastructure (embedding model) not yet in stack. 2. No dedup beyond headline hash: Rejected — Tier 3 review flagged that different headlines about the same event produce near-duplicate catalysts. 3. Embedding-based dedup: Deferred to DEF-038. |
| **Rationale** | Simple, deterministic rule that catches the most common duplicate pattern (same symbol, same category, close in time) without requiring NLP. Configurable window accommodates different event types. |
| **Cross-References** | DEC-302 (headline hash dedup — complementary), DEF-038 (future embedding-based dedup) |
| **Status** | Active |

---

### DEC-312 | Batch-Then-Publish Pipeline Ordering

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | CatalystPipeline stores all classified catalysts via `store_catalysts_batch()` in a single transaction, then publishes CatalystEvents in a separate pass with per-item error handling. A failed publish does not lose data. |
| **Alternatives Considered** | 1. Store-and-publish per item: Rejected — N commits for N catalysts, and a publish failure mid-batch could leave the Event Bus in an inconsistent state relative to storage. 2. Publish before store: Rejected — publish failure could lose data. |
| **Rationale** | Data persistence is the priority. Event Bus subscribers (future Quality Engine, Orchestrator) can tolerate brief delays; they cannot tolerate missing data. Per-item error handling in the publish loop prevents one bad CatalystEvent from blocking others. |
| **Cross-References** | DEC-025 (Event Bus FIFO), DEC-302 (storage dedup) |
| **Status** | Active |

---

### DEC-313 | FMP Canary Test at Startup

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | `FMPReferenceClient.start()` performs a canary test — fetches one known symbol (AAPL) and validates that expected response keys (`symbol`, `mktCap`, `volAvg`, `price`, `exchangeShortName`, `isEtf`, `sector`, `industry`) are present. Non-blocking: logs WARNING and continues if canary fails. |
| **Alternatives Considered** | 1. Blocking canary (raise on failure): Rejected — prevents startup for a non-critical issue. FMP may have transient issues. 2. No canary: Rejected — Tier 3 review flagged that FMP schema changes (RSK-052) were only discovered at runtime during Sprint 23.3 with no early warning. |
| **Rationale** | Early warning for API schema changes. RSK-052 materialized in Sprint 23.3 when FMP deprecated legacy endpoints. Canary catches field-name changes before they corrupt the reference cache. Non-blocking because FMP issues should degrade gracefully, not prevent trading. |
| **Cross-References** | DEC-298 (FMP stable API migration), RSK-052 (FMP endpoint deprecation risk) |
| **Status** | Active |

---

### DEC-314 | Reference Data File Cache for Incremental Warm-Up

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | FMPReferenceClient gains JSON file cache (`fmp_reference_cache.json`) with per-symbol `cached_at` timestamps, configurable max age (`cache_max_age_hours`, default 24), atomic writes via temp-file + `os.replace()`, and corrupt-file fallback (returns empty dict with WARNING). Incremental warm-up: load cache → identify stale/missing symbols → fetch only those → merge → save. Reduces ~27-minute warm-up to ~2–5 minutes on subsequent runs. |
| **Alternatives Considered** | 1. SQLite cache: Rejected — JSON file simpler for key-value reference data, no WAL contention. 2. Redis: Rejected — adds infrastructure dependency for a single-user system. 3. No cache (always full fetch): Rejected — 27 minutes is unacceptable for daily restarts. |
| **Rationale** | Reference data (company profiles, float shares) changes slowly — daily cache freshness is sufficient. JSON is human-inspectable for debugging. Atomic write prevents corruption from interrupted writes. Per-symbol staleness enables partial refreshes when a few symbols change. |
| **Constraints** | Cache file path configurable via `fmp_reference.cache_file` config. Default: `{data_dir}/fmp_reference_cache.json`. |
| **Cross-References** | DEF-036 (stock-list response caching — RESOLVED by this), DEC-299 (full-universe input pipe) |
| **Status** | Active |

---

### DEC-315 | Intelligence Polling Loop via asyncio Task

| Field | Value |
|-------|-------|
| **Date** | 2026-03-10 |
| **Sprint** | 23.6 |
| **Decision** | `run_polling_loop()` in `argus/intelligence/startup.py` runs as an asyncio task started in the FastAPI lifespan handler. Market-hours-aware interval switching: `poll_interval_seconds` (default 300s) during market hours (9:30–16:00 ET), `poll_interval_off_hours_seconds` (default 1800s) outside. Symbols sourced from Universe Manager viable_symbols (preferred) or cached_watchlist (fallback). Each poll: get symbols → `pipeline.run_poll(symbols)` → sleep. Overlap protection via `asyncio.Lock()`. Graceful shutdown via `CancelledError`. |
| **Alternatives Considered** | 1. APScheduler: Rejected — adds dependency for a simple interval timer. asyncio.sleep() is sufficient. 2. Cron-style scheduling: Rejected — interval-based is simpler and more responsive. 3. Event-driven (poll on new candle): Rejected — catalyst sources are external APIs, not tick-driven. |
| **Rationale** | Market hours need more frequent updates (new filings, earnings). Off-hours can poll less frequently. Universe Manager symbols provide broad coverage; cached_watchlist fallback handles the case where Universe Manager is disabled. Lock prevents overlapping polls if one takes longer than the interval. |
| **Cross-References** | DEC-300 (config-gated), DEC-308 (initialization lifecycle) |
| **Status** | Active |

---

### DEC-316 | Time-Aware Indicator Warm-Up

| Field | Value |
|-------|-------|
| **Date** | 2026-03-11 |
| **Sprint** | 23.7 |
| **Decision** | Replace blocking per-symbol indicator warm-up with time-aware approach. Pre-market boot (at or before 9:30 AM ET) skips warm-up entirely — indicators build naturally from the live stream. Mid-session boot (after 9:30 AM ET) enables lazy mode: each symbol is backfilled from market open (9:30 ET) on first live candle arrival, synchronously on the Databento reader thread before candle dispatch. Warm-up tracking set protected by `threading.Lock`. Failed backfills mark the symbol as warmed (no retry loop) — fail-closed via existing indicator validity checks. |
| **Alternatives Considered** | 1. Batch ALL_SYMBOLS historical request: Rejected — unknown Databento API behavior for ALL_SYMBOLS in historical context; large response size risk for 6,000+ symbols × N minutes of 1-min candles. 2. Warm up only scanner symbols: Rejected — loses indicator state for all universe symbols on mid-session restart. 3. Keep blocking warm-up with parallelism: Rejected — still O(N) individual API calls; parallelism helps but doesn't solve the fundamental scaling problem (6,000+ calls would still take hours). |
| **Rationale** | The warm-up was designed for 8–15 scanner symbols. With Sprint 23's full-universe pipe producing 6,005+ viable symbols, the blocking warm-up made 6,000+ sequential Databento historical API calls, taking 12+ hours. The system could not reach RUNNING state before market close. Pre-market boot (the normal operating mode from Taipei) needs no warm-up because the live stream delivers candles from 9:30 and indicators build naturally. Mid-session boot (crash recovery) uses lazy per-symbol backfill to spread the cost across only symbols that actually produce live candles. Lazy backfill runs synchronously on the reader thread, preserving FIFO ordering (DEC-025). Thread safety via `threading.Lock` for warm-up tracking set, consistent with DEC-088 threading model. |
| **Cross-References** | DEC-025 (Event Bus FIFO), DEC-088 (Databento threading), DEC-263 (full-universe monitoring) |
| **Status** | Active |

---

### DEC-317 | Periodic Reference Cache Saves

| Field | Value |
|-------|-------|
| **Date** | 2026-03-11 |
| **Sprint** | 23.7 |
| **Decision** | Save reference data cache to disk every 1,000 successfully fetched symbols during fetch and on shutdown signal. Uses existing atomic write mechanism (temp file + `os.replace()`). Internal `_cache` dict pre-populated with valid (non-stale) entries before incremental fetch begins, so checkpoints include both previously cached and newly fetched data. Shutdown flag (`_shutdown_requested`) checked in fetch loop triggers final save of current progress. |
| **Alternatives Considered** | 1. Save only on clean completion: Previous behavior — lost all progress on interrupt (observed: 75 minutes of fetching lost on Ctrl+C, requiring full 2-hour re-fetch). |
| **Rationale** | Cold-start reference fetch takes ~2 hours for ~37,000 symbols. The cache (DEC-314) only saved on successful completion, meaning any interruption lost all progress. With periodic saves every 1,000 symbols, at most ~3 minutes of fetch time is lost on interrupt. |
| **Cross-References** | DEC-314 (reference data file cache) |
| **Status** | Active |

---

### DEC-318 | API Server Port Guard and Double-Bind Fix

| Field | Value |
|-------|-------|
| **Date** | 2026-03-11 |
| **Sprint** | 23.7 |
| **Decision** | Fix root cause of API server double-bind (duplicate WebSocket bridge start in both `main.py` and FastAPI lifespan handler — removed from lifespan) and add port-availability guard as defense in depth. `check_port_available()` uses `socket.bind()` to verify port before `uvicorn.run()`. On port conflict, system continues in headless mode (no API server) via `PortInUseError` handling in `main.py`, rather than crashing. |
| **Alternatives Considered** | 1. Guard only (no root cause fix): Rejected — masks the underlying bug; duplicate WS bridge initialization could cause other issues. 2. Root cause fix only (no guard): Rejected — doesn't protect against external port conflicts (e.g., stale ARGUS process from previous run). |
| **Rationale** | Observed on March 10 Boot 2: uvicorn started successfully, then a second uvicorn process attempted to bind port 8000 and crashed with `[Errno 48]`. Root cause: the FastAPI lifespan handler was starting the WebSocket bridge, but `main.py` also starts it, causing duplicate initialization. Known TOCTOU race in port check is acceptable as defense-in-depth since root cause is also fixed. |
| **Cross-References** | None |
| **Status** | Active |

---

*End of Decision Log v1.0*
*Next DEC: 319*
*Last updated: 2026-03-11 (Sprint 23.7 doc-sync — DEC-316–318)*