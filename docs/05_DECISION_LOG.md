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
| **Status** | Active |

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
| **Status** | Active |
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

## DEC-163 | Expanded Vision — AI-Enhanced Trading Intelligence Platform

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
| **Status** | Active |

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

*End of Decision Log v1.0*
*New decisions are appended chronologically as the project progresses.*
