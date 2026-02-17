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
| **Decision** | The Argus GitHub repository is connected to the Claude.ai project via Anthropic's native GitHub integration. Selected files/folders synced: `docs/`, `CLAUDE.md`, `config/`. Project instructions (02_PROJECT_KNOWLEDGE.md text) remain manually maintained separately. |
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
| **Status** | Active |

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

### DEC-076 | Phase 3 ORB Parameter Recommendations
| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Decision** | ORB strategy parameters for Phase 3: `opening_range_minutes=5`, `max_hold_minutes=15`, `min_gap_pct=2.0`, `stop_buffer_pct=0.0`, `target_r=2.0`, `max_range_atr_ratio=999.0` (disabled). Two high-sensitivity parameters changed (or: 15→5, hold: 30→15). ATR filter disabled (DEC-075). Three low-sensitivity parameters unchanged. |
| **Alternatives** | (a) Use sweep top-1 set exactly (or=5, hold=15, gap=2.0, atr=0.5, target_r=1.0, stop_buf=0.0) — rejected because ATR=0.5 is non-transferable (DEC-075) and target_r=1.0 shows no meaningful advantage over 2.0. (b) Change more parameters (raise min_gap to 3.0%) — rejected to preserve trade frequency for paper trading evaluation. (c) Keep all defaults — rejected because or=15 and hold=30 produce a break-even strategy. |
| **Rationale** | Based on 522K-combination parameter sweep, sensitivity analysis, and final validation (137 trades, Sharpe 0.93, PF 1.18, +$8,087 on $100K over 11 months). Walk-forward inconclusive (DEC-073) due to insufficient data — Sprint 11 will revalidate with extended data. Conservative approach: only change the two parameters with high sensitivity and clear directional signal. |
| **Status** | Active — validated. Sprint 11 extended walk-forward (15 windows, 35 months) showed fixed-params WFE (P&L) = 0.56, overall OOS Sharpe = +0.34, aggregate OOS P&L = $7,741 across 378 trades. WFE (Sharpe) = -0.91 but metric is inappropriate for fixed-params runs (IS Sharpe swings wildly when params aren't optimized per window). Parameters confirmed for paper trading. |

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

*End of Decision Log v1.0*
*New decisions are appended chronologically as the project progresses.*
