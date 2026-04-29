# ARGUS — Project Bible

> *Version 1.0 | February 2026*
> *This document is the single source of truth for the Argus project. Every design decision, strategy rule, and system behavior must be traceable to this document. If reality conflicts with the Bible, either reality or the Bible must change — never operate in ambiguity.*

---

## 1. Mission

Argus is a fully automated, multi-strategy trading ecosystem designed to generate consistent income from financial markets while requiring minimal human oversight. It is built for one person and one family. The system must be trustworthy enough to run autonomously, transparent enough to be understood completely, and disciplined enough to never deviate from its rules.

The name comes from Argus Panoptes — the all-seeing guardian of Greek mythology — reflecting a system with many strategies watching the market simultaneously, never sleeping, never blinking.

### Core Principles

1. **The system trades, not the human.** Emotions, intuition, and FOMO have no interface to the execution layer. Every trade is the product of predefined logic meeting predefined conditions.
2. **Capital preservation above all.** The system's first job is to not lose money. Its second job is to make money. Never reverse this priority.
3. **Transparency over cleverness.** Every decision the system makes must be explainable. No black boxes in V1. If you can't articulate why a trade was taken, the system has a bug.
4. **Continuous improvement through data.** Every trade, every decision, every market observation feeds a learning loop. The system gets smarter over time — not through guesswork, but through evidence.
5. **Design for the future, build for today.** Architecture supports multi-asset, AI-driven orchestration, and sophisticated regime detection. Implementation starts simple and earns complexity through proven need.
6. **Intelligence compounds.** Every trade the system takes generates data that makes the next trade smarter. The system learns which setups are highest quality, which catalysts drive the strongest moves, and which market conditions favor which patterns — and it applies that learning automatically.

---

## 2. System Overview

Argus is composed of three nested projects, built in sequence:

### Project A: The Trading Engine
The core autonomous trading system. Strategies, orchestrator, risk manager, data service, broker connections, backtesting toolkit. This is the foundation everything else depends on.

### Project B: The Command Center
A Tauri-based desktop application (with mobile web companion) that provides real-time monitoring, human-in-the-loop controls, performance dashboards, accounting tools, report generation, and the strategy incubator interface.

### Project C: The AI Layer
Claude integration as the intelligence brain — real-time setup quality scoring, catalyst analysis, pre-market briefing generation, post-trade evaluation, learning loop model updates, and natural language copilot accessible from every page of the Command Center (DEC-170). The AI Layer is not an add-on; it is the central intelligence that grades every setup, sizes every position, and continuously refines the system's edge. Claude also handles approval workflow for system changes, report generation, and strategy development assistance. Connected to Claude Code for implementation workflow.

The foundation of the AI Layer is the **Universe Manager** (DEC-263) — full-universe monitoring with continuous IndicatorEngine computation (VWAP, ATR, EMAs) on 3,000–5,000 symbols from market open. Each strategy declares its own `universe_filter` (sector, market cap, float, price range, volume) and `behavioral_triggers` in YAML config. Filtering happens at strategy evaluation time, not at subscription time, ensuring any strategy can discover opportunities anywhere in the market without pre-filtering blind spots.

**Build and validation run in parallel.** Project A (Trading Engine) is the foundation and was built first. Projects B (Command Center) and C (AI Layer) are built incrementally alongside ongoing strategy validation. All three were *designed* simultaneously so that Project A's interfaces are dashboard-ready and AI-ready from day one. Real capital deployment gates on strategy validation confidence, but system construction proceeds at development velocity. See DEC-079.

---

## 3. Trading Philosophy

### What We Trade
- **Phase 1:** US stocks and ETFs (NYSE, NASDAQ) — data via Databento, execution via IBKR
- **Phase 2:** Cryptocurrency — execution via IBKR (supports BTC, ETH, LTC, BCH) or Alpaca Crypto
- **Phase 3:** Forex — execution via IBKR (complete coverage), data via IQFeed
- **Phase 4:** Futures — execution via IBKR (CME, CBOT, NYMEX, COMEX, ICE), data via Databento CME ($179/mo + exchange fees)

### How We Trade
- **Direction:** Primarily long. Short selling may be added for specific strategies after the long-only ecosystem is proven.
- **Holding Duration:** Seconds to hours. All positions closed by end of day (for stock strategies). No overnight equity risk.
- **Speed:** The system is capable of sub-second decision-making for scalp strategies, while also supporting multi-hour holds for slower momentum strategies.
- **Frequency:** Unlimited trades per day (requires $25K+ margin account or PDT reform). The system is designed for high frequency across multiple strategies running concurrently.

### What We Believe
- Edge comes from *selectivity* (strict filters), *discipline* (no rule-breaking), and *risk management* (small losses, asymmetric payoffs) — not from being faster than institutions.
- No single strategy works in all market conditions. A diversified ecosystem of uncorrelated strategies is more resilient than any single approach.
- Backtesting is necessary but not sufficient. Paper trading and small-size live trading are mandatory validation stages.
- The system should be designed for $50K–$100K+ in active trading capital, even if it launches with less.
- The highest-value skill in momentum trading is setup quality grading — distinguishing A+ setups from C- setups. This can be quantified and automated through composite scoring of pattern strength, catalyst quality, order flow signals, volume profile, historical match, and regime alignment.
- Dynamic position sizing (risking more on high-confidence setups, less on marginal ones) is the primary profit lever beyond strategy count.
- Order flow data (Level 2 depth, tape speed, bid/ask dynamics) provides entry confidence that price/volume candles alone cannot.
- The system's AI copilot should be contextually present everywhere — not siloed in a separate page — so the operator never breaks flow to consult their co-captain.

---

## 4. The Strategy Ecosystem

### 4.1 Strategy Architecture

Every strategy is a self-contained module that implements a common interface. Strategies are independent — they don't know about each other. They emit trade signals that pass through the Risk Manager and Orchestrator before reaching the broker.

Strategies follow a **daily-stateful, session-stateless** model. Within a trading day, strategies accumulate state (e.g., the opening range as it forms, trade count, daily P&L). Between trading days, all state is wiped clean by `reset_daily_state()` — no information carries over from one day to the next except what's in the database and configuration files. If the system restarts mid-day, strategies reconstruct their intraday state from the database (open positions, today's trades). The database is the durable source of truth; in-memory state is a performance cache.

Every strategy defines:
- **Identity:** Name, unique ID, version, asset class, description
- **Market Conditions Filter:** Conditions under which this strategy is eligible to activate
- **Universe Filter:** Sector, market cap, float, price range, volume criteria defining the strategy's eligible universe (DEC-263)
- **Scanner Logic:** How it finds trade candidates from symbols passing the universe filter
- **Entry Criteria:** Non-negotiable conditions that must ALL be true for a trade
- **Position Sizing:** Calculated from the strategy's allocated capital (set by the Orchestrator)
- **Exit Rules:** Stop loss, profit targets, time stops, trailing stops
- **Holding Duration Range:** Expected min/max time in a trade
- **Risk Parameters:** Max loss per trade, max concurrent positions, max daily loss for this strategy
- **Performance Benchmarks:** Minimum win rate, profit factor, and Sharpe ratio to remain active

### 4.2 Strategy Roster (Expanded — DEC-163)

**Phase 1 — Built:**
1. **ORB** — 9:35–11:30 AM, 1–15 min holds. Paper Trading stage.
2. **ORB Scalp** — 9:45–11:30 AM, 10s–5 min holds. Exploration stage.
3. **VWAP Reclaim** — 10:00 AM–12:00 PM, 5–30 min holds. Exploration stage.
4. **Afternoon Momentum** — 2:00–3:30 PM, 15–60 min holds. Exploration stage.

**Phase 2 — Planned (Sprints 26–32, DEC-167):**
5. Red-to-Green — 9:45–11:00 AM, gap-down reversal
6. Bull Flag — All day, consolidation breakout after sharp move
7. Flat-Top Breakout — All day, multiple rejections then clean break (shadow mode post Sprint 32.9)
8. Dip-and-Rip — 9:45–11:30 AM, sharp dip then aggressive bounce
9. HOD Break — All day, new high-of-day with volume
10. Pre-Market High Break — 9:30–10:30 AM
11. Gap-and-Go — 9:30–10:00 AM, immediate gap continuation
12. ABCD Reversal — 10:00 AM–2:00 PM, four-point reversal (shadow mode post Sprint 32.9)
13. Sympathy Play — 9:45–11:30 AM, secondary sector mover
14. Parabolic Short — 10:00 AM–3:00 PM (first short strategy, DEC-166)
15. Power Hour Reversal — 3:00–3:45 PM
16. Earnings Gap Continuation — 9:30–11:30 AM, day 2+ continuation
17. Volume Shelf Bounce — All day, bounce off VPOC
18. Micro Float Runner — 9:30–11:30 AM, ultra-low float extreme RVOL

**Phase 2 additions — PatternModule expansion (Sprint 31A):**
19. **Micro Pullback** — 10:00 AM–2:00 PM, EMA-based continuation after shallow pullback (live; PROVISIONAL)
20. **VWAP Bounce** — 10:30 AM–3:00 PM, bounce off rising VWAP (live; PROVISIONAL; DEF-154 parameter rework)
21. **Narrow Range Breakout** — 10:00 AM–3:00 PM, volatility-compression breakout (live; PROVISIONAL)

Not all Phase 2 patterns will prove to have a backtestable edge. Each goes through the full Incubator Pipeline. The goal is 10–12 validated patterns running simultaneously. As of Sprint 31.91 (sealed 2026-04-28), the live roster is 13 + 2 shadow (ABCD, Flat-Top Breakout demoted to shadow mode in Sprint 32.9 pending optimization). Sprint 31.91 did not change the roster but architecturally CLOSED both DEF-014 (alert observability gap, PRIMARY DEFECT October 2025; resolved via DEC-388 alert observability pipeline) and the DEF-204 upstream cascade mechanism (via DEC-386 OCA-Group Threading + DEC-385 Side-Aware Reconciliation Contract + S3 retry side-check + S4 falsifiable validation infrastructure). Daily-flatten operator mitigation continues until criterion #5 (5 paper sessions clean post-seal) is met.

### 4.3 Strategy Incubator Pipeline

Every strategy follows a formalized lifecycle:

1. **Concept** — Idea is defined and documented in a Strategy Spec Sheet
2. **Quick Reject** — Fast backtest screen: 50 representative symbols × 3–6 months, seconds per config. Rejects configurations with zero signals, negative expectancy, or win rate below 35%. This is a pre-filter, not a validation gate. (Replaces "Exploration" — DEC-382, Sprint 31.75.)
3. **Shadow** — Survivors deployed as shadow variants via `experiments.yaml`. CounterfactualTracker monitors theoretical outcomes on live market data. This is the real validation gate. Minimum 20 trading days, 30+ trades. Shadow is free (no capital risk, minimal compute). (New stage — DEC-382, Sprint 31.75.)
4. **Promotion Gate** — PromotionEvaluator analyzes shadow performance with statistical significance tests (Sprint 33). Positive expectancy, adequate trade count, acceptable drawdown. Configs that pass are promoted to live paper trading.
5. **Paper Trading** — Promoted from shadow to live paper trading (IBKR paper account). Validates execution quality, fill assumptions, and system integration.
6. **Deep Backtest (Optional)** — Full-universe, multi-year exhaustive analysis for shadow-proven configs only. Informs allocation sizing, regime robustness, and tail risk characterization. Not required for promotion — reserved for capital allocation decisions. (Replaces "Validation" + "Ecosystem Replay" — DEC-382.)
7. **Live (Minimum Size)** — Real money, minimum position sizes, for minimum 20 trading days
8. **Live (Full Size)** — Promoted to full allocation within the Orchestrator
9. **Active Monitoring** — Ongoing performance tracking; may be throttled or suspended
10. **Suspended** — Temporarily removed from active trading; can be reactivated
11. **Retired** — Permanently deactivated; archived for reference

**Validation philosophy (DEC-382):** Validation cost scales with capital risk. Shadow costs nothing → cheap validation. Live trading risks capital → expensive validation. Backtesting is a quick-reject pre-filter, not the primary validation gate. A config showing positive expectancy on 20 days of real market data is a stronger signal than 8 years of historical simulation (regime non-stationarity, curve-fitting, unrealistic fills).

The Strategy Lab section of the Command Center dashboard tracks every strategy's position in this pipeline.

### 4.4 Pattern Library

Beyond the initial strategies, ARGUS recognizes an expanded set of momentum patterns through a shared PatternLibrary interface. Each pattern module implements BaseStrategy and goes through the full Incubator Pipeline (§4.3). Pattern modules contribute a "pattern strength" score to the Setup Quality Engine (§19).

Patterns are built in batches of 3–4 per sprint (DEC-167). Not all will prove viable — the Incubator Pipeline filters are designed to identify and retire patterns that don't earn their keep. Quality over quantity.

---

## 5. The Orchestrator (Meta-Agent)

### 5.1 Role

The Orchestrator is the central decision-maker that manages the strategy ecosystem. It decides which strategies are active, how much capital each receives, and when to throttle or suspend underperformers.

### 5.2 Capital Allocation

Each trading day, before market open, the Orchestrator reviews each active strategy's recent performance and assigns a capital allocation percentage.

**V1 Rules (Rules-Based):**
- Each active strategy receives a base allocation of `100% / N` where N = number of active strategies
- Allocation can shift ±10% based on trailing 20-day performance (Sharpe ratio, profit factor)
- No strategy receives more than 40% of total capital
- No strategy receives less than 10% of total capital (if active)
- Unallocated capital remains in cash reserve
- Minimum 20% of total account value is always held in cash reserve (never deployed)

**V2 Vision (AI-Enhanced, Sprint 31+):**
- Quality-weighted allocation: strategies producing more A+ setups receive more capital
- Intraday dynamic allocation responding to performance and regime shifts
- Correlation-aware allocation reducing aggregate risk
- AI advisor (Claude) proposes allocation changes through approval workflow
- Opportunity cost tracking: log A+ setups skipped due to capital constraints

### 5.3 Activation / Deactivation

The Orchestrator uses Market Regime Classification (see Section 7) to decide which strategies are eligible each day.

- **Trending + High Volatility:** Favor momentum strategies (ORB, ORB Scalp, Afternoon Momentum)
- **Trending + Low Volatility:** Favor standard ORB, Afternoon Momentum
- **Range-bound + High Volatility:** Favor mean-reversion (VWAP Reclaim, Red-to-Green)
- **Range-bound + Low Volatility:** Reduce overall activity; only highest-confidence setups
- **Crisis / Extreme Volatility:** Reduce all allocations; widen stops; consider sitting out entirely

### 5.4 Performance-Based Throttling

- If a strategy hits 5 consecutive losses: reduce allocation to minimum (10%)
- If a strategy's 20-day rolling Sharpe drops below 0: suspend the strategy
- If a strategy's drawdown from equity peak exceeds 15%: suspend the strategy
- Suspended strategies move to paper-trade-only mode until they demonstrate recovery over 10+ paper trading days

---

## 6. Risk Management Framework

Risk management operates at three levels simultaneously.

### 6.1 Strategy Level (First Line)
Each strategy enforces its own internal limits:
- Maximum loss per trade (defined per strategy, typically 0.5–1% of allocated capital)
- Maximum concurrent positions (defined per strategy, typically 1–3)
- Maximum daily loss for the strategy (defined per strategy, typically 2–3% of allocated capital)
- Time stops (close positions that haven't moved within defined windows)

### 6.2 Cross-Strategy Level (Second Line)
The Risk Manager monitors aggregate exposure across all strategies:
- No single stock can represent more than 5% of total account value across all strategies
- No single sector can represent more than 15% of total account value
- Total number of concurrent open positions across all strategies cannot exceed a defined maximum
- If two strategies want to enter the same stock simultaneously, the Risk Manager prioritizes the strategy with higher historical win rate on that setup

### 6.3 Account Level (Third Line)
Hard limits that override everything:
- **Daily Loss Limit:** Total realized losses across all strategies cannot exceed 3–5% of total account (configurable)
- **Weekly Loss Limit:** Total realized losses for the week cannot exceed 5–8% of total account (configurable)
- **Cash Reserve:** Minimum 20% of account is always in cash, never deployed
- **Emergency Shutdown:** Flatten all positions immediately if triggered (manual button in dashboard, or automatic on infrastructure failure)
- **PDT Tracking:** If account is under $25K in a margin account, track day trade count and enforce the 3-per-5-day limit

### 6.4 Position Sizing Formula
Universal across all strategies:
```
Shares = Risk Amount / (Entry Price - Stop Loss Price)
Risk Amount = Strategy Allocated Capital × Risk Percentage Per Trade
```
Buying power check: `Shares × Entry Price` must not exceed available buying power. If it does, reduce shares to fit.

---

## 7. Market Regime Classification

The system maintains a real-time assessment of current market conditions. This feeds into the Orchestrator's activation decisions and the Risk Manager's aggressiveness settings.

### V1 Indicators
- **Trend:** SPY position relative to 20-day and 50-day moving averages
- **Volatility:** VIX level (Low < 15, Normal 15–25, High 25–35, Crisis > 35)
- **Breadth:** Advance/decline ratio (are most stocks up or down today?)
- **Momentum:** SPY's 5-day rate of change
- **Intraday Trend:** SPY's position relative to VWAP

### Regime Categories
- Bullish Trending (SPY above MAs, breadth positive, VIX normal/low)
- Bearish Trending (SPY below MAs, breadth negative, VIX elevated)
- Range-Bound (SPY oscillating around MAs, breadth mixed)
- High Volatility Event (VIX spike, often around earnings season, FOMC, geopolitical events)
- Crisis (VIX > 35, broad market selloff, correlations spike to 1)

### V2+ Vision
- ML-based regime classification using broader feature set
- Hidden Markov Models or similar for regime detection
- Regime prediction (not just detection) for proactive allocation shifts

---

## 8. Human-in-the-Loop Controls

### 8.1 Autonomy Levels

The system supports configurable autonomy per action type:

| Action | Default Autonomy | Can Be Changed To |
|--------|-----------------|-------------------|
| Execute trade signals from active strategies | Autonomous | Require approval |
| Modify stop losses (tightening only) | Autonomous | Require approval |
| Activate/deactivate strategies (by Orchestrator rules) | Autonomous | Require approval |
| Adjust capital allocation (within ±10%) | Autonomous | Require approval |
| Trigger circuit breakers | Always autonomous | Cannot be overridden |
| Emergency shutdown | Always autonomous | Cannot be overridden |
| Suspend a strategy (performance-based) | Notify + autonomous | Require approval |
| Promote strategy to next pipeline stage | Always requires approval | — |
| Change system parameters | Always requires approval | — |
| Claude-proposed actions | Always requires approval | Can pre-approve categories |

### 8.2 Approval Workflow

When an action requires approval:
1. The system generates a proposal with: what, why, expected impact, risk level
2. Notification is sent via configured channels (push, Telegram/Discord, email)
3. User approves, rejects, or modifies via dashboard or notification response
4. If no response within configurable timeout: system takes the safe default (typically: do nothing)
5. All proposals and their outcomes are logged in the audit trail

### 8.3 Override Controls (Dashboard)

The dashboard provides manual controls for:
- Emergency shutdown (flatten all positions immediately)
- Pause/resume all trading
- Pause/resume individual strategies
- Manually close any specific position
- Manually adjust strategy allocations (overriding Orchestrator)
- Lock the system (prevent any new trades; existing positions managed to completion)

---

## 9. Claude as Co-Captain

### 9.1 Role Definition

Claude serves as a contextual AI copilot embedded in every page of the Command Center (DEC-170). Claude can analyze, recommend, score setups, generate reports, and — with approval — take actions on the system. Claude is not a separate application; it is present wherever the operator is working, pre-loaded with the context of what they're looking at.

### 9.2 Access Model

Claude is accessible via a persistent slide-out chat panel triggered from any page. When opened, Claude automatically receives:
- **Page context:** What page the user is on and what data is displayed
- **Selected entity:** If a trade, strategy, position, or report is selected/open
- **System state:** Current positions, regime, risk utilization, recent decisions
- **Historical context:** Previous chat messages, Learning Journal entries

Chat history persists in The Debrief's Learning Journal, building institutional memory.

### 9.3 Capabilities

**Real-Time Intelligence:**
- Score setup quality for any watchlist symbol (pattern + catalyst + order flow + volume + history + regime)
- Evaluate pre-market catalysts and generate quality ratings
- Produce pre-market briefings and EOD reports (saved to The Debrief)
- Detect anomalies in system behavior or market conditions during trading hours

**Analysis & Advisory:**
- Review performance and provide narrative analysis at any granularity
- Identify patterns in trading data ("your win rate drops on Mondays")
- Answer questions about system behavior ("why did we skip this setup?")
- Research market conditions and provide regime change context
- Suggest parameter adjustments based on performance data

**Action Proposals (Require Approval):**
- Adjust strategy parameters (stop distances, targets, filters)
- Override capital allocation percentages
- Activate or suspend strategies
- Propose new strategy ideas (generates Strategy Spec Sheet)
- Implement code changes (via Claude Code integration)

**Knowledge Generation:**
- Generate narrative report sections saved to The Debrief
- Create strategy reviews with data-backed analysis
- Annotate trades with analysis (saved to Learning Journal)
- Produce weekly "What I Learned" digests

### 9.4 Boundaries

- Claude never executes trades directly — all proposals go through Risk Manager gates and approval workflow
- Claude never bypasses the approval system
- All interactions and proposals are logged in the audit trail
- Chat is not "god mode" — it works within the existing control framework

---

## 10. Capital Management

### 10.1 Starting Capital
TBD. The system is designed to operate effectively with $25K–$100K in active trading capital. Minimum recommended: $25K (to avoid PDT restrictions in a margin account).

### 10.2 Growth & Withdrawal Framework

**Base Capital:** The minimum amount the system needs to operate all active strategies effectively. Initially set manually; recalculated as strategies are added/removed.

**Growth Pool:** All profits above Base Capital accumulate here.

**Withdrawal Rules (Configurable):**
- Growth Pool must reach a threshold before any withdrawal (e.g., $5,000)
- A percentage of the Growth Pool is available for withdrawal (e.g., 50%)
- The remaining percentage is added to Base Capital to increase future capacity
- Withdrawals are tracked and reported for tax purposes
- Optional: automatic monthly sweep to a designated bank account

### 10.3 Scaling Rules
- Base Capital increases are only applied after a strategy has been profitable for 30+ consecutive trading days
- Position size increases are gradual (no more than 25% increase per month)
- Any drawdown of 10%+ from peak triggers a pause on scaling until recovery

---

## 11. Accounting & Tax

### 11.1 Trade Ledger
Every trade is recorded with full metadata: strategy, asset class, entry/exit prices, timestamps, share count, commissions, P&L (realized and unrealized), cost basis.

### 11.2 Tax Considerations
- **Short-term capital gains:** Day trading profits are taxed as ordinary income
- **Wash Sale Rule:** System tracks and flags wash sales automatically
- **Mark-to-Market (Section 475):** Election analysis built into Tax Intelligence Automation (DEC-380 horizon item); the system supports both MTM and standard accounting
- **Crypto:** Taxed as property; separate cost basis tracking
- **Forex (Section 988 vs 1256):** System will support both elections when forex is added
- **Futures (Section 1256):** 60/40 long-term/short-term treatment when futures are added

### 11.3 Reporting
- Real-time P&L dashboard (daily, monthly, quarterly, annual)
- Estimated tax liability calculator based on configurable tax bracket
- Exportable trade logs compatible with tax software (TradeLog, GainsKeeper) — Tax Intelligence Automation horizon item (DEC-380)
- Integration with dedicated trader tax services (TradeLog, GainsKeeper) evaluated for Phase 2

---

## 12. Disaster Recovery & Failsafes

### 12.1 Infrastructure Failures
| Scenario | Response |
|----------|----------|
| VPS crashes with open positions | Broker-side stop orders remain active. System recovery script flattens any positions without stops on restart. |
| Broker API goes down | System enters "safe mode" — no new trades. Existing stop orders are broker-side (IBKR) and remain active. Alert sent immediately. IB Gateway reconnection logic handles nightly resets automatically. |
| Data feed stalls (no new ticks for >30 seconds) | System pauses all strategies. Existing positions retain their stops. Alert sent. Auto-resume when data returns. |
| Internet connectivity loss | Same as data feed stall. Dead man's switch: if system hasn't sent heartbeat in 5 minutes, monitoring service sends alert. |
| Flash crash / gap through stop | Accepted as a risk of trading. Position sizing ensures max loss per trade is survivable. Account-level daily loss limit provides second line of defense. |

### 12.2 System Health Monitoring
- Heartbeat signal every 60 seconds to external monitoring service
- Automated restart on crash (systemd on Linux)
- Daily integrity check: verify all open positions have associated stop orders at broker
- Weekly integrity check: reconcile system's trade log with broker's official records

### 12.3 Backup & Recovery
- Database backed up daily to cloud storage
- Configuration files version-controlled in git
- System state snapshot every 5 minutes during market hours (allows recovery to near-exact state)
- Documented recovery procedure: time-to-recovery target of <5 minutes

---

## 13. Notification System

### 13.1 Channels
- **Push Notifications (App):** Real-time alerts for critical events
- **Telegram / Discord Bot:** Trade notifications, system status, interactive commands
- **Email:** Daily/weekly summaries and reports

### 13.2 Alert Categories

**Critical (Immediate Push + Telegram/Discord):**
- Circuit breaker triggered
- System error or crash
- Action requiring approval
- Daily loss limit approaching (>75% consumed)
- Infrastructure failure detected

**Informational (Telegram/Discord):**
- Trade executed (entry/exit)
- Strategy activated/deactivated by Orchestrator
- New high watermark reached
- Strategy milestone (e.g., 100th trade)

**Periodic (Email + Dashboard):**
- Pre-market briefing (7:00 AM EST)
- Mid-day summary (12:00 PM EST)
- End-of-day report (4:30 PM EST)
- Weekly performance review (Saturday morning)
- Monthly comprehensive report (1st of month)

---

## 14. Multi-Asset Roadmap

### Phase 1: US Stocks & ETFs
Full implementation. All initial strategies. Data: Databento US Equities Standard ($199/month). Execution: IBKR Pro (tiered pricing). Incubator paper testing: Alpaca.

### Phase 2: Cryptocurrency
Via IBKR (Bitcoin, Ethereum, Litecoin, Bitcoin Cash) or Alpaca crypto API (broader selection, 24/7). Develop crypto-specific strategies. Add crypto-aware tax tracking. Key consideration: crypto market microstructure differs from stocks — wider spreads, different liquidity profiles, manipulation risk.

### Phase 3: Forex
Via IBKR — complete forex coverage through same account and API. Add IQFeed supplemental data for forex ticks and market breadth. Develop forex-specific strategies (session-based momentum, carry trade variants). Session-aware scheduling (Tokyo, London, New York). Different leverage and margin mechanics. Section 988/1256 tax election support.

### Phase 4: Futures
Via IBKR — CME, CBOT, NYMEX, COMEX, ICE through same account and API. Databento CME Globex dataset (+$179/month) for futures market data. Develop futures-specific strategies (E-mini, Micro contracts). No PDT restrictions. 60/40 tax treatment. Nearly 24-hour trading capability.

---

## 15. Paper Trading Shadow System

A permanent paper trading instance runs in parallel with the live system at all times. It executes the exact same code with the exact same data but does not place real orders. Purposes:

- Continuous sanity check (divergence between live and shadow signals a fill quality or execution issue)
- Safe testing ground for parameter changes before applying them to live
- Testing ground for strategies in the Incubator Pipeline stages 5–6
- Fallback validation if live results seem anomalous

---

## 16. Simulation & Stress Testing

### Scenario Analysis
The system can replay historical stress periods through the current configuration:
- March 2020 COVID crash
- 2022 bear market
- Individual flash crash events
- Custom scenarios (user-defined market moves)

### Monte Carlo Simulation (V2+)
Generate thousands of simulated trading sequences based on each strategy's statistical profile (win rate, average win, average loss, trade frequency). Estimate probability distributions of outcomes over 30/90/180/365 day horizons. Identify worst-case drawdown scenarios.

---

## 17. Learning Journal

A searchable knowledge base within the Command Center that captures qualitative insights alongside quantitative data:

- Manual observations ("ORB seems to fail on ex-dividend dates")
- Claude's analytical insights ("Win rate drops 12% when VIX crosses above 25")
- Strategy development notes (what was tried, what worked, what didn't)
- Market regime observations
- Linked to specific trades, time periods, and strategies for context

The Learning Journal is the institutional memory of the trading operation. It turns experience into documented knowledge that informs future decisions.

---

## 18. News & Catalyst Intelligence

### 18.1 Purpose

News is the catalyst that creates the price action Argus trades. Gap stocks gap for a reason — earnings, FDA approvals, analyst upgrades, offerings, geopolitical events. Understanding *why* a stock is moving improves entry confidence, filters out low-quality setups, and protects against traps where a technically perfect pattern sits on a rotten fundamental foundation.

This system provides context to the trading engine, not trading signals. It enhances existing strategies by adding catalyst-type metadata to scanner results, flagging known-risk events, and enriching the Learning Journal with post-trade context.

### 18.2 Three-Tier Architecture

**Tier 1 — Economic & Earnings Calendar (Build Track, near-term)**
Structured calendar data ingested daily before market open. No NLP required.
- **Economic calendar:** FOMC dates, NFP, CPI, GDP releases, Fed speeches. Source: free economic calendar API. Benzinga Pro (included with IQFeed when added) for richer coverage.
- **Earnings calendar:** Which stocks report today/tomorrow. Flag any scanner candidates with pending earnings.
- **Output:** Risk flags on scanner results ("AAPL reports earnings after close today"), regime modifier ("FOMC announcement at 2:00 PM — reduce position sizes in afternoon strategies").
- **Integration point:** Scanner metadata and Risk Manager event-day filters.

**Tier 2 — News Feed Ingestion & Classification (Build Track, later)**
Subscribe to a news API and match headlines to watchlist symbols by ticker mention. Classify into catalyst categories using keyword/regex patterns.
- **Catalyst categories:** Earnings, Analyst Action, FDA/Regulatory, M&A, Offering/Dilution, Insider Activity, Macro/Sector, Legal/SEC, Product Launch, Guidance Change.
- **Output:** Catalyst metadata on scanner results ("MRNA gapped +8%, catalyst: FDA approval"). Historical catalyst-to-outcome correlation data for the Learning Journal.
- **Data sources (evaluated in priority order):** Benzinga Pro (included with IQFeed subscription — DEC-082), SEC EDGAR filings (free, structured, high-value for 8-K/13F/insider transactions), NewsAPI (general news fallback). Alpaca news no longer in the primary data path (DEC-086).
- **Integration point:** Scanner enrichment, Learning Journal, pre-market briefing.

**Tier 3 — AI-Powered Sentiment & Analysis (Build Track, later)**
Feed news articles through Claude's API for nuanced analysis beyond simple classification.
- **Capabilities:** Catalyst quality assessment ("FDA approval for blockbuster category vs. niche indication"), follow-through probability estimation, cross-reference with historical patterns.
- **Output:** Confidence modifiers on trade signals, narrative context in daily reports, automated Learning Journal entries linking news to trade outcomes.
- **Integration point:** Orchestrator confidence weighting, Claude Co-Captain analysis, end-of-day report generation.

### 18.3 Design Principles

- **Defensive value first.** Avoiding bad trades is more valuable than finding good ones. Tier 1's primary job is filtering out landmines (earnings traps, dilutive offerings, pending regulatory actions).
- **Pre-market focus.** For day trading, news latency requirements are relaxed — overnight and pre-market news matters most. Sub-second news latency is not a design goal.
- **Signal over noise.** The financial news firehose is overwhelming. Relevance scoring and strict symbol-matching prevent information overload. Only news matching active watchlist symbols or broad market events (FOMC, CPI) passes through.
- **Structured data first, NLP second.** Economic calendars, earnings dates, and SEC filings are structured and reliable. Unstructured news analysis (Tiers 2–3) layers on top only after structured data proves its value.

### 18.4 Key Constraints

- **Data cost:** Tier 1 is free or near-free. Tier 2 may require $50–200/month for quality real-time feeds. Budget evaluated before implementation.
- **No trading signals from news alone.** News enhances pattern-based strategies; it does not generate independent trade signals in V1. A future "News Momentum" strategy could change this, but it would go through the standard Incubator Pipeline.
- **SEC EDGAR integration:** Free, structured, and extremely valuable. An EDGAR crawler for 8-K filings, 13F institutional holdings changes, and insider transactions (Form 4) is a high-value, low-cost component prioritized within Tier 2.

---

## 19. Setup Quality Engine

### 19.1 Purpose
The core innovation transforming ARGUS from binary pass/fail filtering to intelligence-driven trading. Grades every potential trade 0–100 across six dimensions.

### 19.2 Scoring Dimensions
**V1 — 5 Dimensions (DEC-239):**
| Dimension | Weight | Source |
|-----------|--------|--------|
| Pattern Strength | 30% | Strategy module |
| Catalyst Quality | 25% | NLP Catalyst Pipeline |
| Volume Profile | 20% | Databento L1 |
| Historical Match | 15% | Learning Loop |
| Regime Alignment | 10% | RegimeClassifier |

**Post-Revenue — 6 Dimensions (when Order Flow Model activates, DEC-238):**
| Dimension | Weight | Source |
|-----------|--------|--------|
| Pattern Strength | 25% | Strategy module |
| Catalyst Quality | 20% | NLP Catalyst Pipeline |
| Order Flow | 20% | Order Flow Model (L2) |
| Volume Profile | 15% | Databento L1 |
| Historical Match | 10% | Learning Loop |
| Regime Alignment | 10% | RegimeClassifier |

Weights are YAML-configurable. Rebalancing on Order Flow activation is a config change, not a code change.

### 19.3 Quality Grades and Risk Tiers
| Grade | Score | Risk % | Behavior |
|-------|-------|--------|----------|
| A+ | 90–100 | 2.0–3.0% | Maximum conviction |
| A | 80–89 | 1.5–2.0% | High confidence |
| A- | 70–79 | 1.0–1.5% | Standard-plus |
| B+ | 60–69 | 0.75–1.0% | Standard |
| B | 50–59 | 0.5–0.75% | Conservative |
| B- | 40–49 | 0.25–0.5% | Minimum |
| C+ | 30–39 | 0.25% min | Barely passes |
| C/C- | 0–29 | SKIP | Do not trade |

Account-level limits override. Circuit breakers non-overridable.

### 19.4 Learning Loop
Every trade generates feedback. Weekly batch retraining refines weights. V1: statistical lookup tables (pattern × catalyst × regime → performance). V2 (Sprint 33+): ML model (LightGBM).

---

## 20. Order Flow Intelligence

### 20.1 Purpose
Reveals intent behind price movement: real buying pressure vs spoofing, hidden orders, momentum absorption.

### 20.2 Data Source
Databento L2 (MBP-10, 10 depth levels) for V1. L3 (individual order events) for V2. **Correction (DEC-237):** Live L2/L3 requires Databento Plus tier ($1,399/mo). Standard plan ($199/mo) includes historical L2/L3 only (1-month lookback). Order Flow Model deferred to post-revenue (DEC-238). Historical L2 available immediately for backtesting signal quality.

### 20.3 Signals
V1: bid/ask imbalance, ask thinning rate, tape speed, bid stacking.
V2: iceberg detection, spoofing detection, momentum absorption.

---

## 21. Glossary

| Term | Definition |
|------|-----------|
| **R (Risk Unit)** | The dollar amount risked on a trade. If you risk $100 on a trade, 1R = $100. A 2R winner means you made $200. |
| **Opening Range** | The high and low price of a stock during the first N minutes after market open. |
| **VWAP** | Volume-Weighted Average Price. The average price of a stock weighted by volume. Used as an intraday trend indicator. |
| **ATR** | Average True Range. A measure of a stock's average daily price movement over N periods. Used for stop distance and volatility assessment. |
| **Relative Volume (RVOL)** | Today's volume compared to the average volume for the same time of day over the past 20 days. RVOL of 2.0 means twice the normal volume. |
| **Circuit Breaker** | An automatic system halt triggered by predefined loss limits. Non-overridable. |
| **Orchestrator** | The meta-agent that manages strategy activation, capital allocation, and performance-based throttling. |
| **Risk Manager** | The system component that gates every order, enforcing strategy-level, cross-strategy, and account-level risk limits. |
| **Replay Harness** | A backtesting tool that feeds historical data through the production system code to test the full ecosystem. |
| **Shadow System** | A permanent paper trading instance running in parallel with live trading for continuous validation. |
| **Strategy Spec Sheet** | A standardized document defining every parameter of an individual strategy. |
| **Incubator Pipeline** | The formalized 10-stage lifecycle every strategy passes through from concept to retirement. |
| **Base Capital** | The minimum account balance required to operate all active strategies. |
| **Growth Pool** | Profits above Base Capital, available for withdrawal or reinvestment. |
| **Regime** | A characterization of current market conditions (trending/range-bound, high/low volatility) that influences strategy selection. |
| **Catalyst** | The fundamental reason a stock's price moves significantly — earnings, FDA decisions, analyst actions, M&A announcements, etc. The "why" behind a gap or breakout. |
| **Economic Calendar** | A schedule of known market-moving events (FOMC meetings, jobs reports, CPI releases) used to anticipate volatility regimes. |

---

*End of Project Bible v1.0*
*Next update: After document review and approval of all six foundational documents.*
