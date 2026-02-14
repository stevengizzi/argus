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

*End of Decision Log v1.0*
*New decisions are appended chronologically as the project progresses.*
