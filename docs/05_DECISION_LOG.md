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

### DEC-003 — Brokerage Architecture
| Field | Value |
|-------|-------|
| **Date** | 2026-02-14 |
| **Decision** | Broker-agnostic abstraction layer. Implement both Alpaca and Interactive Brokers from day one. |
| **Alternatives** | Alpaca only, IBKR only, single-broker with abstraction added later |
| **Rationale** | Alpaca is ideal for development and early live trading (free, clean API, built-in paper trading, included data). IBKR is superior for production scaling (better execution, more asset classes). Abstraction layer costs minimal extra effort upfront and prevents lock-in. |
| **Status** | Active |

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

*End of Decision Log v1.0*
*New decisions are appended chronologically as the project progresses.*
