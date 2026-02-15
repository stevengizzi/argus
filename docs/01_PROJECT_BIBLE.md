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

---

## 2. System Overview

Argus is composed of three nested projects, built in sequence:

### Project A: The Trading Engine
The core autonomous trading system. Strategies, orchestrator, risk manager, data service, broker connections, backtesting toolkit. This is the foundation everything else depends on.

### Project B: The Command Center
A Tauri-based desktop application (with mobile web companion) that provides real-time monitoring, human-in-the-loop controls, performance dashboards, accounting tools, report generation, and the strategy incubator interface.

### Project C: The AI Layer
Claude integration as co-captain — advisory analysis, action proposals with approval workflow, report narration, strategy development assistance, and system optimization recommendations. Connected to Claude Code for implementation workflow.

**Build order is strict: A → B → C.** Each depends on the one before it. However, all three are *designed* simultaneously so that Project A's interfaces are dashboard-ready and AI-ready from day one.

---

## 3. Trading Philosophy

### What We Trade
- **Phase 1:** US stocks and ETFs (NYSE, NASDAQ)
- **Phase 2:** Cryptocurrency (via Alpaca's unified API)
- **Phase 3:** Forex (via IBKR or OANDA)
- **Phase 4:** Futures (via IBKR or NinjaTrader)

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

---

## 4. The Strategy Ecosystem

### 4.1 Strategy Architecture

Every strategy is a self-contained module that implements a common interface. Strategies are independent — they don't know about each other. They emit trade signals that pass through the Risk Manager and Orchestrator before reaching the broker.

Strategies follow a **daily-stateful, session-stateless** model. Within a trading day, strategies accumulate state (e.g., the opening range as it forms, trade count, daily P&L). Between trading days, all state is wiped clean by `reset_daily_state()` — no information carries over from one day to the next except what's in the database and configuration files. If the system restarts mid-day, strategies reconstruct their intraday state from the database (open positions, today's trades). The database is the durable source of truth; in-memory state is a performance cache.

Every strategy defines:
- **Identity:** Name, unique ID, version, asset class, description
- **Market Conditions Filter:** Conditions under which this strategy is eligible to activate
- **Scanner Logic:** How it finds trade candidates
- **Entry Criteria:** Non-negotiable conditions that must ALL be true for a trade
- **Position Sizing:** Calculated from the strategy's allocated capital (set by the Orchestrator)
- **Exit Rules:** Stop loss, profit targets, time stops, trailing stops
- **Holding Duration Range:** Expected min/max time in a trade
- **Risk Parameters:** Max loss per trade, max concurrent positions, max daily loss for this strategy
- **Performance Benchmarks:** Minimum win rate, profit factor, and Sharpe ratio to remain active

### 4.2 Initial Strategy Roster (US Stocks)

**Strategy 1: ORB (Opening Range Breakout)**
The foundational strategy. Identifies stocks gapping on volume, records the opening range, enters on confirmed breakouts with volume and VWAP alignment. Tiered exit: 50% at 1R, 50% at 2R. Time stop at 30 minutes. Operates 9:45–11:30 AM EST. Holding duration: 5–45 minutes.

**Strategy 2: ORB Scalp**
A faster variant of ORB. Same scanner and entry criteria, but targets a quick 0.3–0.5R partial profit within the first 30–120 seconds, then exits entirely. Higher win rate, smaller gains, more trades per day. Operates 9:45–11:30 AM EST. Holding duration: 10 seconds – 5 minutes.

**Strategy 3: VWAP Reclaim**
Mean-reversion strategy. Buys stocks that pulled back below VWAP on low volume, then reclaim VWAP on increasing volume. Works well mid-morning when breakout momentum fades. Operates 10:00 AM – 12:00 PM EST. Holding duration: 5–30 minutes.

**Strategy 4: Afternoon Momentum**
Identifies stocks from the morning watchlist that consolidate midday (12:00–2:00 PM), then break out of the consolidation range in the afternoon. Operates 2:00–3:30 PM EST. Holding duration: 15–60 minutes.

**Strategy 5: Red-to-Green**
Stocks that gap down at open but reverse and cross from negative to positive on the day. A specific reversal pattern with high reliability when filtered for catalyst + volume. Operates 9:45–11:00 AM EST. Holding duration: 10–45 minutes.

Additional strategies will be developed over time and documented in individual Strategy Spec Sheets following the standardized template.

### 4.3 Strategy Incubator Pipeline

Every strategy follows a formalized lifecycle:

1. **Concept** — Idea is defined and documented in a Strategy Spec Sheet
2. **Exploration** — Parameter sweeps via VectorBT to identify promising configurations
3. **Validation** — Full-fidelity testing via the Replay Harness, which feeds historical data through the actual production code (Event Bus, Strategy, Risk Manager, SimulatedBroker) using FixedClock injection. Walk-forward analysis validates that parameters generalize beyond the optimization period (DEC-047).
4. **Ecosystem Replay** — Strategy added to the full system and tested via the Replay Harness against historical data alongside other active strategies
5. **Paper Trading** — Live paper trading for minimum 20–30 trading days
6. **Live (Minimum Size)** — Real money, minimum position sizes, for minimum 20 trading days
7. **Live (Full Size)** — Promoted to full allocation within the Orchestrator
8. **Active Monitoring** — Ongoing performance tracking; may be throttled or suspended
9. **Suspended** — Temporarily removed from active trading; can be reactivated
10. **Retired** — Permanently deactivated; archived for reference

The Strategy Lab section of the Command Center dashboard tracks every strategy's position in this pipeline.

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

**V2+ Vision (AI-Enhanced):**
- Machine learning model trained on historical allocation decisions and outcomes
- Dynamic allocation that responds to intraday performance, not just daily reviews
- Correlation-aware allocation that reduces aggregate risk

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

Claude serves as a continuous expert advisor embedded in the system. Claude can analyze, recommend, and — with approval — take actions on the system.

### 9.2 Capabilities

**Analysis & Advisory:**
- Review daily/weekly/monthly performance and provide narrative analysis
- Identify patterns in trading data (e.g., "your win rate drops on Mondays")
- Answer questions about system behavior ("why didn't Strategy 3 trade today?")
- Research market conditions and provide context for regime changes
- Suggest parameter adjustments based on performance data

**Action Proposals (Require Approval):**
- Adjust strategy parameters (stop distances, targets, filters)
- Activate or suspend strategies
- Modify Orchestrator allocation rules
- Propose new strategy ideas (generates Strategy Spec Sheet)
- Implement code changes (via Claude Code integration)

**Report Generation:**
- Generate narrative sections of performance reports
- Create strategy reviews with data-backed analysis
- Produce the pre-market briefing and end-of-day summary

### 9.3 Boundaries

- Claude never bypasses the approval system
- Claude never has direct access to execute trades without going through the standard pipeline
- Claude's action proposals go through the same Risk Manager gates as any other action
- All Claude interactions and proposals are logged in the audit trail

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
- **Mark-to-Market (Section 475):** Election should be evaluated with a CPA; the system supports both MTM and standard accounting
- **Crypto:** Taxed as property; separate cost basis tracking
- **Forex (Section 988 vs 1256):** System will support both elections when forex is added
- **Futures (Section 1256):** 60/40 long-term/short-term treatment when futures are added

### 11.3 Reporting
- Real-time P&L dashboard (daily, monthly, quarterly, annual)
- Estimated tax liability calculator based on configurable tax bracket
- Exportable trade logs compatible with tax software and CPA handoff
- Integration with dedicated trader tax services (TradeLog, GainsKeeper) evaluated for Phase 2

---

## 12. Disaster Recovery & Failsafes

### 12.1 Infrastructure Failures
| Scenario | Response |
|----------|----------|
| VPS crashes with open positions | Broker-side stop orders remain active. System recovery script flattens any positions without stops on restart. |
| Broker API goes down | System enters "safe mode" — no new trades. Existing stop orders are broker-side and remain active. Alert sent immediately. |
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
Full implementation. All initial strategies. Alpaca + IBKR.

### Phase 2: Cryptocurrency
Leverage Alpaca's unified API for seamless integration. Develop crypto-specific strategies (momentum strategies adapt well to crypto's 24/7 volatile markets). Add crypto-aware tax tracking. Key consideration: crypto market microstructure differs from stocks — wider spreads, different liquidity profiles, manipulation risk.

### Phase 3: Forex
Add OANDA or IBKR forex connection. Develop forex-specific strategies (session-based momentum, carry trade variants). Session-aware scheduling (Tokyo, London, New York). Different leverage and margin mechanics. Section 988/1256 tax election support.

### Phase 4: Futures
Add futures broker connection (IBKR, NinjaTrader, or AMP). Develop futures-specific strategies (E-mini, Micro contracts). No PDT restrictions. 60/40 tax treatment. Nearly 24-hour trading capability.

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

## 18. Glossary

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

---

*End of Project Bible v1.0*
*Next update: After document review and approval of all six foundational documents.*
