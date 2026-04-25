# ARGUS — Risk & Assumptions Register

> *Version 1.1 | March 2026 — Reviewed and triaged during DEC-262 roadmap consolidation*
> *This document explicitly tracks the assumptions the system is built on and the risks that could invalidate them. Review monthly (or after any significant market event) to ensure assumptions still hold and risks are being managed. An unexamined assumption is a hidden risk.*

---

## How to Use This Document

### Assumptions
Things we believe to be true and are building on. Each has a confidence level and a contingency plan.

### Risks
Things that could go wrong and how we'd respond. Each has severity, likelihood, and a mitigation plan.

**Confidence Levels:** High (>90%) / Medium (60–90%) / Low (<60%)
**Severity:** Critical (could end the project) / High (major setback) / Medium (significant but manageable) / Low (minor inconvenience)
**Likelihood:** High (>50%) / Medium (20–50%) / Low (<20%)

---

## Assumptions

### ASM-001 — PDT Reform Timeline
| Field | Value |
|-------|-------|
| **Assumption** | FINRA's PDT reform (eliminating the $25K minimum) will receive SEC approval by mid-2026 |
| **Confidence** | Medium |
| **Basis** | FINRA approved the rule change in September 2025. SEC review is underway. Industry expectation is mid-2026 approval. |
| **If Wrong** | Must operate under current PDT rules: maintain $25K+ in margin account, or use cash account with T+1 settlement limiting trade frequency. |
| **Contingency** | PDT tracking built into Risk Manager from day one. Strategies designed to be effective even with limited day trades. Cash account is a viable fallback. |
| **Review Date** | Monthly until resolved |

---

### ASM-002 — Alpaca API Reliability (SCOPE REDUCED)
| Field | Value |
|-------|-------|
| **Assumption** | Alpaca API is reliable enough for strategy incubator paper testing. |
| **Confidence** | High |
| **Basis** | Alpaca demoted to incubator-only role (DEC-086). 125+ outages in 9 months (StatusGator data) is acceptable for paper testing where missed trades are inconvenient, not catastrophic. Production reliability now depends on IBKR (ASM-013/014) and Databento (ASM-012). |
| **Amendment (2026-02-20)** | Original assumption was that Alpaca maintains >99.5% uptime for production use. Research (DEC-083) revealed 125+ outages across ~100 components in a 9-month monitoring period. Alpaca is no longer on the production path — demoted to strategy incubator only (DEC-086). |
| **If Wrong** | Strategy incubator paper testing is occasionally disrupted. No financial impact — incubator uses simulated capital. SimulatedBroker + ReplayDataService provide alternative incubation paths. |
| **Contingency** | If Alpaca reliability degrades further, incubator paper testing can run on IBKR paper trading account instead. |
| **Review Date** | Low priority — incubator only |

---

### ASM-003 — Backtesting Validity
| Field | Value |
|-------|-------|
| **Assumption** | 6+ months of historical backtesting is sufficient to validate a strategy before live deployment |
| **Confidence** | Medium |
| **Basis** | Industry standard for intraday strategies. Captures multiple market conditions within 6 months. |
| **If Wrong** | Strategies validated on 6 months may fail in unseen regimes (e.g., tested in bull market only, fails in bear market). |
| **Contingency** | Extend to 12+ months when data is available. Explicitly test against known stress periods. Incubator Pipeline's minimum-size live stage catches strategies that pass backtesting but fail in reality. |
| **Review Date** | After first strategy completes backtesting |

---

### ASM-004 — Opening Range Breakout Edge Persistence
| Field | Value |
|-------|-------|
| **Assumption** | The ORB pattern provides a statistically significant edge that will persist |
| **Confidence** | Medium-High |
| **Basis** | ORB exploits a structural market feature (price discovery at open). Edge comes from selectivity and risk management, not secrecy. One of the most documented intraday strategies. |
| **If Wrong** | System relies on other strategies. Multi-strategy ecosystem is designed to handle individual strategy failure. |
| **Contingency** | Orchestrator automatically throttles underperformers. Five-strategy roster reduces dependence on any one. Continuous performance monitoring detects edge decay early. |
| **Review Date** | After 30 live trading days with ORB |

---

### ASM-006 — Sufficient Capital for Multi-Strategy Ecosystem
| Field | Value |
|-------|-------|
| **Assumption** | User will have $25K–$50K+ available for active trading capital |
| **Confidence** | Medium |
| **Basis** | Current portfolio includes $392K across E-Trade accounts and $96K in savings. Specific Argus allocation TBD. |
| **If Wrong** | Under $25K: PDT restrictions apply. Under $50K: thin per-strategy allocations reduce position sizes and profit potential. |
| **Contingency** | System scales from $25K to $100K+. Start with fewer active strategies (1–2), add as capital grows. Cash account mode works at any capital level but limits frequency. |
| **Review Date** | Before Phase 1 development begins |

---

### ASM-007 — Autonomous Market Hours Operation
| Field | Value |
|-------|-------|
| **Assumption** | System can run autonomously 9:30 AM – 4:00 PM EST without requiring user presence |
| **Confidence** | High |
| **Basis** | Core design principle. User wants to spend time on other work and family. |
| **If Wrong** | System defeats its purpose if frequent human intervention is required. |
| **Contingency** | All trading logic fully automated. Circuit breakers handle adverse events autonomously. Notifications only for truly important events. Approval timeouts have safe defaults. Emergency shutdown always available remotely via mobile. |
| **Review Date** | After first month of live trading |

---

### ASM-009 — Slippage Estimates
| Field | Value |
|-------|-------|
| **Assumption** | Average slippage <$0.05/share for stocks $10–$200 with ADV >1M |
| **Confidence** | Medium |
| **Basis** | Liquid stocks with tight spreads. Market orders during high-volume periods near open typically fill close to expected price. |
| **If Wrong** | Higher slippage erodes strategy edge, especially scalp strategies. Backtesting overstates actual performance. |
| **Contingency** | Live trading starts at minimum size specifically to measure actual slippage. Shadow system comparison reveals slippage impact. If >$0.05 consistently, consider limit orders or tighter liquidity filters. |
| **Review Date** | After first 50 live trades |

---

### ASM-010 — Single-User System
| Field | Value |
|-------|-------|
| **Assumption** | System will always serve a single user/family. No multi-tenant requirements. |
| **Confidence** | High |
| **Basis** | User's stated intent. Personal/family system. |
| **If Wrong** | Multi-tenant would require fundamental architectural changes. Essentially a new project. |
| **Contingency** | Not planned. Architecture is intentionally simple because it's single-user. |
| **Review Date** | N/A (foundational) |

---

### ASM-011 — News Data Availability and Quality
| Field | Value |
|-------|-------|
| **Assumption** | Free or low-cost news APIs (Alpaca news, SEC EDGAR, free economic calendars) provide sufficient data quality and timeliness for Tier 1–2 catalyst classification. |
| **Confidence** | Medium |
| **Basis** | Alpaca includes basic news in their API. SEC EDGAR is free and structured. Economic calendar data is widely available. Benzinga Pro is available at $50–100/month if free sources prove insufficient. |
| **If Wrong** | Tier 1 structured calendar data is reliable regardless (dates are facts). Tier 2 classification quality may degrade with poor news sources, producing noisy or late catalyst labels. |
| **Contingency** | Start with Alpaca's built-in news + SEC EDGAR (both free). Evaluate quality during paper trading. Budget up to $200/month for premium feeds (Benzinga Pro) if free sources are insufficient. Tier 2 is only built after Tier 1 proves value, limiting wasted investment. |
| **Review Date** | When Tier 2 implementation begins (Phase 6) |

---

### ASM-012 — Databento Data Quality and Business Continuity
| Field | Value |
|-------|-------|
| **Assumption** | Databento US Equities Standard provides reliable, institutional-grade market data suitable for live trading decisions, and the company remains operational with current pricing/service level for the foreseeable future. |
| **Confidence** | Medium-High (data quality), Medium (business continuity) |
| **Basis** | Data quality: Databento's data sourced from direct exchange proprietary feeds at Equinix NY4 colocation. 99.99% uptime commitment. Community reports confirm 150K+ quotes/second throughput and professional-grade quality. Synthetic NBBO is practically equivalent to SIP NBBO for non-HFT strategies. Business continuity: VC-funded startup ($37.5M total funding, ~$8M revenue, ~38 employees). Growing institutional adoption (IBKR Campus, Tickblaze partnerships). Strong technical team (ex-trading firm engineers). But pre-profitability and dependent on continued funding. |
| **If Wrong** | Data quality issues could produce unreliable signals (false breakouts, incorrect VWAP). Business failure would remove ARGUS's primary data source. DataService abstraction enables swap to IQFeed or Alpaca SIP in ~1 sprint. |
| **Contingency** | (1) Circuit-breaker logic halts new trades on data stream failure. (2) IQFeed exists as proven 20-year fallback. (3) Historical data stored locally in Parquet is provider-independent. (4) Compare Databento prices vs broker fill prices to validate data quality during paper trading. (5) Monitor Databento's blog, status page, and funding news quarterly. |
| **Review Date** | After first 2 weeks of paper trading with Databento data. Business continuity: quarterly. |

---

### ASM-013 — ib_async Library Production Stability
| Field | Value |
|-------|-------|
| **Assumption** | The `ib_async` library (community-maintained successor to `ib_insync`) is production-stable for order management, position tracking, and account queries against IB Gateway. |
| **Confidence** | Medium-High |
| **Basis** | `ib_insync` was battle-tested across thousands of production trading systems since 2017. `ib_async` is maintained by the `ib-api-reloaded` GitHub organization after the original creator's passing in early 2024. Active community. Asyncio-native design aligns with ARGUS architecture. Multiple GitHub projects demonstrate sophisticated production systems built on this library. |
| **If Wrong** | Adapter development reveals instability or missing features. Fallback: use IBKR's native TWS API directly (more complex callback-based code) or evaluate `ibapi` official SDK with asyncio wrapper. AlpacaBroker adapter remains fully functional as interim execution broker. |
| **Contingency** | Test thoroughly during Sprint 13 development. If `ib_async` proves unstable, evaluate native TWS API or `ib_insync` (legacy, still functional). BrokerAbstraction isolates the library choice. |
| **Review Date** | During Sprint 13 (IBKRBroker adapter development). |

---

### ASM-014 — IB Gateway Operational Reliability
| Field | Value |
|-------|-------|
| **Assumption** | IB Gateway can run reliably in a Docker container with automated reconnection logic, surviving the known nightly reset. |
| **Confidence** | Medium-High |
| **Basis** | IB Gateway in Docker is a well-documented pattern in the algo trading community. Nightly reset (between 11:45 PM – 12:45 AM ET on weekdays) is a known limitation with established workaround patterns. ARGUS trades only during market hours, so the nightly reset window does not overlap with trading. |
| **If Wrong** | Gateway disconnections during market hours would disrupt trading. Existing stops are placed broker-side and remain active even if Gateway disconnects. |
| **Contingency** | Build robust reconnection logic with exponential backoff. Monitor gateway health via HealthMonitor. If instability persists, evaluate TWS (desktop app) as alternative to Gateway. |
| **Review Date** | Sprint 13 + first month of IBKR paper trading |

---

### ASM-016 — Quality Scoring Improves Returns
| Field | Value |
|-------|-------|
| **Assumption** | Composite quality scoring produces meaningful differentiation, with higher-scored setups outperforming lower-scored consistently |
| **Confidence** | Medium |
| **Basis** | Discretionary traders demonstrably outperform when they grade quality. Each component has independent empirical basis. Combined scoring unvalidated for ARGUS. |
| **If Wrong** | Fall back to uniform sizing. No worse than current. Intelligence still valuable for research and pre-market preparation. |
| **Review Date** | After 30+ days paper trading with quality scoring (Gate 3) |

---

### ASM-017 — Free News Sources Provide Adequate Catalyst Coverage
| Field | Value |
|-------|-------|
| **Assumption** | SEC EDGAR + Finnhub + FMP cover 70%+ of catalysts for gapping stocks in ARGUS's target universe |
| **Confidence** | Medium |
| **Basis** | SEC filings cover material corporate events (most reliable). Finnhub aggregates news from multiple sources. FMP provides earnings/calendar data. The combination should cover earnings, FDA, analyst, M&A, and filings. May miss: press releases from smaller companies, some analyst initiations, pre-market color. |
| **If Wrong** | Upgrade to Benzinga Pro via IQFeed (~$200/mo). DEC-164 defines trigger: >30% unclassified rate over 20 days. |
| **Review Date** | After 20 trading days with Catalyst Pipeline active (Sprint 23) |

---

## Risks

### RSK-001 — Strategy Overfitting
| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Medium |
| **Description** | Parameter optimization produces configurations that perform well historically but fail on future data. |
| **Mitigation** | Look for robust parameter ranges (not single optimal points). Out-of-sample testing. Walk-forward analysis. Paper trading catches hindsight-only strategies. Minimum-size live stage limits capital at risk. |
| **Owner** | System Design |

---

### RSK-002 — Correlated Strategy Failure
| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Medium |
| **Description** | Multiple strategies fail simultaneously during a regime change, producing losses exceeding any single strategy's impact. |
| **Mitigation** | Cross-strategy risk monitoring (Level 2). Account-level circuit breakers (Level 3). Intentionally uncorrelated strategy roster (momentum + mean-reversion). Orchestrator deactivates regime-inappropriate strategies. 20% cash reserve never deployed. |
| **Owner** | Risk Manager |

---

### RSK-003 — Flash Crash / Gap Through Stop
| Field | Value |
|-------|-------|
| **Severity** | Medium-High |
| **Likelihood** | Low-Medium |
| **Description** | Sudden price move gaps past stop-loss level, causing a fill far worse than intended. |
| **Mitigation** | Position sizing ensures worst-case fill (3x intended loss) is survivable. Account-level daily loss limit provides hard cap. Scanner filters for liquid stocks reduce gap risk. Avoid holding through known high-risk events. |
| **Owner** | Risk Manager |

---

### RSK-004 — Broker API Breaking Changes
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low-Medium |
| **Description** | Alpaca or IBKR changes their API, breaking the broker adapter. |
| **Mitigation** | Broker abstraction isolates changes to adapter code only. Two implementations provide fallback. Pin SDK versions. Test updates before deploying. Monitor changelogs. |
| **Owner** | Development |

---

### RSK-005 — Regulatory Changes
| Field | Value |
|-------|-------|
| **Severity** | Medium-High |
| **Likelihood** | Low |
| **Description** | New regulations affect day trading — transaction taxes, new restrictions, wash sale rule changes. |
| **Mitigation** | Stay informed on regulatory developments. System design is adaptable. Tax module designed for flexibility. Engage CPA specializing in trader taxation. |
| **Owner** | System Design |

---

### RSK-006 — Edge Decay
| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Medium |
| **Description** | One or more strategies lose their edge as markets evolve or more participants exploit the same patterns. |
| **Mitigation** | Continuous monitoring with rolling metrics. Orchestrator throttles underperformers. Performance benchmarks define minimum viability. Incubator Pipeline ensures new strategies are always in development as replacements. |
| **Owner** | Orchestrator |

---

### RSK-007 — Data Quality Issues
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low-Medium |
| **Description** | Market data feed provides incorrect prices, missing bars, or delayed data undetected. |
| **Mitigation** | Stale data detection (30-second timeout). Candle integrity checks. Periodic cross-reference with secondary source. Shadow system comparison reveals data divergence. Daily reconciliation with broker records. |
| **Owner** | Data Service |

---

### RSK-008 — Psychological Risk (User Override)
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Description** | User overrides system decisions based on emotion — closing winners early, widening stops on losers, disabling strategies during drawdowns. |
| **Mitigation** | Override controls designed to be deliberate (not impulsive). All overrides logged and visible in reports. Claude flags emotional override patterns. Project Bible Principle #1 anchors against this. Consider cool-down requirement during drawdowns. |
| **Owner** | User (supported by system design) |

---

### RSK-009 — Scope Creep
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | High |
| **Description** | Comprehensive vision leads to building too much before validating the core. Months of development before first live trade. |
| **Mitigation** | Strict phased roadmap. Phase 1 is deliberately minimal. Each phase has clear deliverable. Question: "Does this need to exist before the first live trade?" If no, it waits. |
| **Owner** | User + Claude |

---

### RSK-010 — Tax Complexity
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | High |
| **Description** | Hundreds/thousands of trades create complex tax situations (wash sales, short-term gains, multi-asset treatment). |
| **Mitigation** | Every trade logged with full metadata from day one. Wash sale detection in accounting module. Evaluate Section 475 election with CPA. Plan for estimated quarterly payments. Consider TradeLog/GainsKeeper. Engage trader-specialized CPA before first tax year. |
| **Owner** | Accounting Module + CPA |

---

### RSK-011 — Single Point of Failure (User)
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low |
| **Description** | User is the only person who understands the system. Extended unavailability means no oversight. |
| **Mitigation** | Autonomous safety features protect capital without intervention. Auto-safe-mode if user doesn't check in within configurable period. Emergency shutdown accessible remotely. Document a simple "how to shut it down" guide for trusted family member. |
| **Owner** | System Design |

---

### RSK-012 — Security Breach
| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Likelihood** | Low |
| **Description** | Unauthorized access to brokerage API keys could allow trades, withdrawals, or financial damage. |
| **Mitigation** | All keys encrypted, never in code/git. VPS secured: firewall, SSH keys only, regular updates. Dashboard with 2FA. VPN consideration. Broker accounts with their own 2FA. Least-privilege API permissions. Regular security review. |
| **Owner** | Security Architecture |

---

### RSK-016 — Backtest Overfitting Risk
| Field | Value |
|-------|-------|
| **Severity** | High |
| **Likelihood** | Medium |
| **Description** | Parameter optimization against historical data may produce values that look excellent in backtest but fail in live trading. With 3,000+ parameter combinations being tested via VectorBT, the probability of finding a combination that works by chance on the specific historical period is high. |
| **Mitigation** | Walk-forward validation is mandatory (DEC-047). Parameters must show walk-forward efficiency > 0.3. Final parameter selection prioritizes robustness (stable performance across a neighborhood of values) over maximum backtest return. Manual spot-checking of 20+ trades against charts provides a sanity check. |
| **Owner** | Backtest |

---

### RSK-017 | Timezone Comparison Bugs in Time-Windowed Logic
| Field | Value |
|-------|-------|
| **Identified** | 2026-02-16 |
| **Description** | Any component that compares timestamps against hardcoded market-hours constants (ET) is vulnerable to UTC/ET confusion. Found in OrbBreakoutStrategy where `_get_candle_time()` returned UTC time and compared it to ET constants (9:30, 9:45), causing zero opening ranges to form. The bug was silent — no errors, just zero trades. |
| **Likelihood** | Medium (same pattern could recur in new strategies or time-windowed logic) |
| **Impact** | High (strategy silently produces zero trades with no error or warning) |
| **Mitigation** | (1) DEC-061 establishes the conversion pattern. (2) Architectural rule added to CLAUDE.md. (3) Consider a `market_time()` helper in BaseStrategy that all subclasses use, making it harder to accidentally use raw UTC. (4) 8 regression tests added covering UTC→ET conversion including DST. |
| **Status** | Open — mitigated for OrbBreakout, pattern could recur in future strategies |

---

### RSK-018 — News Scanner Signal-to-Noise Ratio
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Description** | A poorly tuned news scanner adds noise instead of signal — false catalyst classifications, irrelevant headlines matched to symbols, or delayed information that triggers incorrect filtering (e.g., filtering out a valid setup due to stale negative news). |
| **Mitigation** | Tier 1 uses only structured data (calendar dates, earnings dates) — no NLP noise. Tier 2 uses strict symbol-ticker matching (not company name matching, which produces false positives). Classification starts with conservative keyword patterns and is refined through manual review during paper trading. News metadata is advisory (enriches scanner output) — it does not veto trades in V1. Kill switch: any tier can be disabled without affecting core trading logic. Manual catalyst logging during Phase 3 paper trading provides ground truth for tuning. |
| **Owner** | Data Service / Intelligence Module |

---

### RSK-020 — Parallel Development Context-Switching and Premature Construction
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low-Medium |
| **Description** | With DEC-079's parallel Build + Validation tracks, two risks emerge: (1) Context-switching between frontend (Command Center), backend (Orchestrator, strategies), and validation monitoring may reduce velocity compared to single-threaded focus. (2) Building infrastructure (Orchestrator, Command Center) before live trading validates architectural assumptions means more code to update if live trading reveals fundamental issues (e.g., execution layer changes needed). |
| **Mitigation** | (1) Sprint structure remains single-threaded within each sprint — context switches happen between sprints, not within them. The two-Claude workflow naturally supports this (design in claude.ai, implement in Claude Code). (2) Architecture already has clean abstractions at the broker, data service, and strategy boundaries. Paper trading exercises the same code paths as live trading, so most issues will surface before live deployment. Live trading is more likely to reveal parameter adjustments than architectural problems. (3) Command Center is read-only in MVP — it adds no risk to the trading engine. Orchestrator is additive infrastructure with its own test suite. |
| **Owner** | Project Management |

---

### RSK-021 — Databento Service Disruption During Market Hours
| Field | Value |
|-------|-------|
| **Risk** | Databento experiences a live data outage during US market hours, preventing ARGUS from receiving real-time market data. February 2026 incidents (historical API outage, replay window reduction) demonstrate operational risk, though live streaming was not affected. |
| **Severity** | High |
| **Likelihood** | Low-Medium |
| **Mitigation** | (1) Circuit-breaker logic: if data stream fails, halt new trades rather than trade blind. (2) Existing stops are placed broker-side and remain active. (3) IQFeed as eventual backup data source provides redundancy. (4) DataService abstraction enables rapid provider switching. (5) Databento commits to 99.99% uptime. |
| **Trigger for action** | Live data stream failure during market hours. Monitor Databento status page during all trading sessions. |
| **Status** | Open — partially mitigated. Stale data monitor with DataStaleEvent/DataResumedEvent implemented in Sprint 12 (Components 1–3). Circuit-breaker halts new trade entries when data is stale. Reconnection with exponential backoff under review (Sprint 12 Components 4–6). Full mitigation confirmed after Sprint 12 Prompt 2 review. |

---

### RSK-022 — IB Gateway Nightly Reset Disruption
| Field | Value |
|-------|-------|
| **Risk** | IB Gateway disconnects nightly between 11:45 PM – 12:45 AM ET for system maintenance. All API connections drop. This is a known, documented behavior — not a bug. Reconnection failures could cause missed trades or position tracking errors if they bleed into market hours. |
| **Severity** | Low (nightly reset itself), Medium (if reconnection fails before market open) |
| **Likelihood** | High (nightly reset is guaranteed; question is whether reconnection handles it cleanly) |
| **Mitigation** | (1) ARGUS trades only during market hours (9:30 AM – 4:00 PM ET). The reset window does not overlap. (2) Docker containerization of IB Gateway for consistent environment. (3) Robust reconnection logic with exponential backoff built into IBKRBroker adapter. (4) All stops placed broker-side — survive gateway disconnections. (5) State reconstruction (already implemented for Alpaca) rebuilds positions and orders from IBKR on reconnect. (6) HealthMonitor detects gateway state and alerts. (7) Community has solved this problem thousands of times — well-documented patterns exist. Mitigated by DEC-254 (auto-shutdown after EOD flatten) and DEC-255 (IBKR maintenance error severity downgrade outside market hours). |
| **Trigger for action** | Reconnection failures during paper trading that result in missed trades or position tracking errors. |
| **Status** | Active — Sprint 21.5 addresses directly. IB Gateway setup (DEC-232), nightly restart handling, and reconnection validated in Sessions 6, 9. |

---

### RSK-023 — Monthly Data Infrastructure Cost
| Field | Value |
|-------|-------|
| **Risk** | ARGUS now has a fixed monthly cost ($199/mo Databento) that was previously $0 on Alpaca's free tier. As the system scales to multi-asset, costs increase: CME futures (+$179/month), OPRA options (+$199/month), IQFeed supplemental (~$160–250/month). Full multi-asset data stack could reach $540–630+/month. These costs exist regardless of trading profitability. |
| **Severity** | Low (current), Medium (at full multi-asset expansion) |
| **Likelihood** | High (cost is certain; question is whether trading revenue exceeds it) |
| **Mitigation** | (1) Start with US equities only ($199/month). (2) Cost deferred until adapter ready (DEC-087). (3) Add asset classes only when strategies for them are validated and paper-traded. (4) Monitor data cost as percentage of trading revenue — target <10% of gross P&L. (5) IQFeed supplemental added only when forex/news features are needed, not speculatively. (6) All subscriptions can be paused if system is taken offline. (7) $199/month is modest relative to trading capital ($25K–100K+). (8) L2/L3 live data confirmed to require Plus tier at $1,399/mo (DEC-237) — not included in Standard as previously assumed. Order Flow Model deferred to post-revenue (DEC-238). |
| **Trigger for action** | Monthly data costs exceed 20% of gross trading P&L after 3 months of live trading. |
| **Status** | Open — accepted. Monthly cost budgeted as cost of doing business. |

---

### RSK-025 | Multi-Strategy Same-Symbol Execution Risk
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-25 |
| **Category** | Execution |
| **Description** | With ALLOW_ALL duplicate stock policy, ORB and ORB Scalp can hold simultaneous positions in the same stock. If both are active and the stock gaps against both positions, the combined loss from one symbol could be significant even if individual positions are within risk limits. |
| **Likelihood** | Medium |
| **Impact** | Medium |
| **Mitigation** | `max_single_stock_pct` (5% of account) caps combined exposure. Circuit breaker triggers on total daily loss regardless of per-stock allocation. Monitor correlation between ORB and Scalp P&L during paper trading. |
| **Status** | Open — monitoring during paper trading |

---

### RSK-026 | Sub-Bar Backtesting Precision for Scalp
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-25 |
| **Category** | Validation |
| **Description** | ORB Scalp targets 30–120 second holds, but backtesting uses 1-minute bars. Synthetic ticks give ~15s granularity (4 per bar). Time stops shorter than 60s resolve at the nearest bar boundary, and intra-bar price dynamics (which determine whether the target or stop is hit first) are approximated by O→L→H→C ordering. |
| **Likelihood** | High (guaranteed imprecision) |
| **Impact** | Low-Medium (backtesting results are approximations, not exact) |
| **Mitigation** | Document limitation. Use backtesting for directional guidance, not exact P&L projection. Validate with live paper trading where actual tick data is available. Consider Databento tick-level replay in future if precision needed. |
| **Status** | Accepted — DEF-018 logged |

---

### RSK-027 | Pre-Databento Backtests Require Re-Validation
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-25 |
| **Category** | Validation |
| **Description** | All parameter optimization (ORB Breakout DEC-076, ORB Scalp DEC-127) was performed on Alpaca historical data at 1-minute bar resolution. Databento exchange-direct data may produce different price dynamics, particularly at market open when ORB signals concentrate. Parameters are provisional until re-validated. ORB Scalp additionally requires sub-minute bar data for meaningful backtesting. |
| **Likelihood** | High (different data source will produce different results) |
| **Impact** | Medium (parameters may shift; methodology and infrastructure are validated) |
| **Mitigation** | Schedule a re-validation sprint when Databento subscription activates (~Sprint 19). Re-run VectorBT sweeps, walk-forward, and cross-validation for all strategies. Compare results to Alpaca-based analysis to quantify divergence. |
| **Status** | Open — trigger: Databento activation |
| **Update (2026-03-21)** | Trigger has fired — Databento is active since March 2026. Sprint 21.6 committed for after Sprint 27 (BacktestEngine Core). DEC-353 confirmed free OHLCV-1m data available from March 2023. Re-validation will use BacktestEngine + 3 years of institutional-grade data. Resolution date: estimated late April 2026. |

---

### RSK-028 | Mean-Reversion Strategy Tail Risk During Market Selloffs
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-25 |
| **Category** | Strategy Risk |
| **Description** | VWAP Reclaim is a mean-reversion strategy that buys pullbacks. During genuine market sell-offs, what looks like a "pullback below VWAP" may be the start of a larger decline. The strategy's `max_pullback_pct` (2%) provides some protection, and the EXHAUSTED state prevents chasing deep pullbacks. However, a stock can gap up, break down through VWAP with a "healthy-looking" 1.5% pullback, reclaim VWAP briefly, trigger an entry, and then continue selling off. |
| **Likelihood** | Medium |
| **Impact** | Medium — limited by 1% per-trade risk, 30-minute time stop, and stop-loss at pullback low. Account-level circuit breakers provide additional protection. |
| **Mitigation** | (1) Regime filtering excludes Crisis mode. (2) max_pullback_pct caps pullback depth. (3) Volume confirmation requires increasing volume on reclaim. (4) Per-trade risk limited to 1%. (5) Time stop at 30 minutes caps exposure. (6) Walk-forward validation will identify if parameters overfit to pullback patterns that don't generalize. |
| **Status** | Active — monitor during paper trading validation |

---

### RSK-029 | VWAP Reclaim Backtest Over-Optimism
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-26 |
| **Category** | Validation |
| **Description** | VWAP Reclaim VectorBT sweep shows avg Sharpe 3.89 across 22K combinations with 59K+ trades. Walk-forward OOS Sharpe of 1.49 is still unusually high for a mean-reversion intraday strategy. Results are on Alpaca SIP data (consolidated feed), not exchange-direct. The 35-month backtest period (2022-07 to 2025-06) includes both bull and bear regimes, but the strategy may be overfit to this specific data quality. |
| **Likelihood** | Medium |
| **Impact** | Medium — paper trading validation will surface performance divergence before live capital is risked |
| **Mitigation** | (1) DEC-132 mandates Databento re-validation for all strategies before live deployment. (2) Paper trading on Alpaca provides initial reality check. (3) Conservative parameter selection (not the highest-Sharpe combo) reduces overfit risk. (4) Start at minimum size even after validation passes. |
| **Status** | Open — addressed by Databento re-validation + paper trading |

---

### RSK-031 | EOD Time Stop Compression for Late Afternoon Entries
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-26 |
| **Category** | Strategy Risk |
| **Description** | Entries after 3:15 PM have ≤30 minutes effective hold time due to 3:45 PM force close. If the strategy consistently enters late, most exits will be time stops rather than targets, degrading profitability. |
| **Likelihood** | Medium |
| **Impact** | Low — time stop exits at close price, not stop price. Late entries still capture the power hour move direction. |
| **Mitigation** | Monitor time-of-entry distribution in sweep results. If >60% of entries occur after 3:15 PM, consider tightening latest_entry to 3:15 PM. |
| **Status** | Open |
| **Owner** | Steven |

---

### RSK-032 — Setup Quality Model Overfitting
| Field | Value |
|-------|-------|
| **Risk** | Quality Engine composite scoring overfits to historical patterns, producing high grades on setups that underperform live |
| **Severity** | High |
| **Likelihood** | Medium |
| **Mitigation** | Walk-forward validation on quality scores. Out-of-sample calibration mandatory. Learning Loop V1 provides continuous recalibration. Gate 3 requires A+ to outperform B in paper trading. |
| **Detection** | Quality Calibration chart (Performance page). Weekly predicted vs actual review. |
| **Contingency** | Fall back to uniform sizing (current system). Intelligence infrastructure still provides value for research. |
| **Status** | Open |
| **Update (2026-03-21)** | Now testable with 28+ paper trades producing quality scores. Active monitoring of quality-score-to-outcome correlation begins. RSK-045 notes that 45% of composite is at neutral defaults, which may reduce overfitting risk (less signal to overfit to) but also reduces differentiation power. |

---

### RSK-033 — Dynamic Sizing Amplifies Losses
| Field | Value |
|-------|-------|
| **Risk** | Dynamic sizing (up to 3% on A+) amplifies losses when quality model misidentifies grade |
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Mitigation** | Account-level daily/weekly limits unchanged. Single-trade max 3%. Circuit breakers non-overridable. Three-tier Risk Manager gates every order. Gradual ramp: paper-prove correlation before live. |
| **Status** | Open |

---

### RSK-034 — Pattern Library Complexity Explosion
| Field | Value |
|-------|-------|
| **Risk** | 15+ concurrent patterns create interaction complexity, correlated signals, maintenance burden |
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Mitigation** | Each pattern must pass walk-forward (DEC-047). Retire underperformers. CorrelationTracker flags high-correlation pairs. Max active patterns configurable. Quality > quantity. |
| **Status** | Open |

---

### RSK-035 — Free News Source Insufficiency
| Field | Value |
|-------|-------|
| **Risk** | Free news sources miss catalysts that paid services catch, reducing quality scoring accuracy |
| **Severity** | Low-Medium |
| **Likelihood** | Medium |
| **Mitigation** | Track "unclassified catalyst" rate. Trigger: >30% over 20 days → evaluate Benzinga Pro. Manual catalyst notes as fallback. Architecture supports hot-swap. |
| **Status** | Open |

---

### RSK-036 — AI Copilot Latency During Market Hours
| Field | Value |
|-------|-------|
| **Risk** | Claude API response latency (2–10s) during market hours disrupts operational flow when user needs quick answers |
| **Severity** | Low |
| **Likelihood** | Medium |
| **Mitigation** | Copilot is advisory, not in the execution path. Trades execute regardless of chat state. Pre-compute common contexts (positions, regime, quality scores) so Claude responses can reference cached data. Streaming responses show partial text immediately. |
| **Status** | Open |

---

### RSK-038 — Revenue-Dependent L2 Data Access for Order Flow Model

| Field | Value |
|-------|-------|
| **Risk** | The Order Flow Model (bid/ask imbalance, ask thinning, tape speed, bid stacking) requires Databento Plus tier ($1,399/mo) for live L2 depth streaming. This is $1,200/mo over the current Standard plan. If trading revenue is insufficient or slow to materialize, the Order Flow enhancement may remain indefinitely deferred, limiting the Setup Quality Engine to 5 dimensions instead of the designed 6. |
| **Severity** | Low |
| **Likelihood** | Medium (revenue target of 10%/month on $25K+ should exceed $1,200/mo, but timeline uncertain) |
| **Mitigation** | (1) All 4 current strategies and the intelligence layer operate on L1 data — no functionality blocked. (2) Historical L2 available on Standard plan for backtesting Order Flow Model before committing to Plus. (3) Setup Quality Engine designed with configurable weights — 5-dimension V1 is production-ready. (4) Order Flow adds incremental edge (~3–5% win rate improvement), not foundational capability. (5) Can backtest to quantify exact dollar value of Order Flow signals before deciding to upgrade. |
| **Trigger for action** | Monthly trading net P&L exceeds $2,000 for 3 consecutive months (covers Plus tier upgrade + margin). |
| **Status** | Open — accepted. Order Flow deferred to post-revenue backlog (DEC-238). |

---

### RSK-039 — Cape Town Latency Impact on Execution Quality

| Field | Value |
|-------|-------|
| **Risk** | ~200–250ms latency to US exchanges from Cape Town may cause slippage on fast-moving entries, particularly ORB strategies during the opening range. |
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Mitigation** | Longer-duration strategies (VWAP Reclaim, Afternoon Momentum) are structurally advantaged. Monitor fill quality per strategy. Consider deactivating ORB Scalp if fill rates are poor. |
| **Status** | Closed |
| **Closed** | 2026-04-20 — Operator relocated to US East Coast (ET). Latency is now minimal (<10ms). No longer a structural concern. |

---

### RSK-042 — Pre-Databento Backtest Re-Validation Not Yet Started

| Field | Value |
|-------|-------|
| **Risk** | DEC-132 requires re-validation but Sprint 21.6 hasn't begun. All current strategy parameters are provisional. |
| **Severity** | High |
| **Likelihood** | Medium |
| **Mitigation** | Sprint 21.6 planned parallel with Sprint 22. Ensure it actually starts — don't let AI Layer work crowd it out. |
| **Status** | Open |
| **Note (2026-03-06)** | Sprint 21.6 is queued and planned to run in parallel with Sprint 22 per ROADMAP.md. Risk remains active until re-validation completes. |

---

### RSK-045 — FMP API Availability

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low |
| **Description** | FMP REST endpoints could experience downtime, schema changes, or rate limiting. This is ARGUS's first dependency on a REST API for real-time-adjacent functionality (pre-market scanning). |
| **Mitigation** | Fallback to static symbol list already implemented in `FMPScannerSource.scan()`. Monitor scanner logs for `scan_source="fmp_fallback"` during paper trading sessions. |
| **Status** | Open |
| **Cross-References** | DEC-257, DEC-258 |

---

### RSK-046 | Broad-Universe Processing Throughput
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-06 (DEC-263) |
| **Status** | Open |
| **Likelihood** | Low |
| **Impact** | Medium |
| **Description** | Full-universe monitoring (3,000–5,000 symbols) with continuous IndicatorEngine computation may exceed CPU budget during volatility spikes. |
| **Mitigation** | Processing math shows ~2–4% CPU with ~97% headroom. Cython/Rust hot-path optimization deferred until profiling shows need. Monitor actual CPU usage during paper trading. |
| **Trigger** | CPU usage exceeds 50% sustained during market hours. |
| **Owner** | Sprint 23 implementation |

---

### RSK-047 | Claude API Dependency
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-06 (Sprint 22) |
| **Likelihood** | Medium |
| **Impact** | Low — trading engine independent |
| **Category** | External dependency |
| **Description** | AI Copilot depends on Anthropic's Claude API. Service outages, rate limiting, or API changes could disrupt AI features. |
| **Mitigation** | All AI features degrade gracefully when `ANTHROPIC_API_KEY` is unset or API unavailable. Trading engine operates identically with or without AI. ResponseCache provides short-term resilience. Rate limiting configured at 10 req/min (DEC-273). |
| **Cross-References** | DEC-264, DEC-265, DEC-098 |

---

### RSK-048 | AI API Cost Overrun
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-06 (Sprint 22) |
| **Likelihood** | Low |
| **Impact** | Low — Opus pricing ~$15/1M input, $75/1M output |
| **Category** | Cost management |
| **Description** | Unexpected usage patterns could lead to higher-than-expected Claude API costs. |
| **Mitigation** | Rate limiting (10 req/min default), response caching, per-call cost tracking in `ai_usage` table. Usage endpoint (`GET /api/v1/ai/usage`) provides real-time visibility. Token budgets enforced: system ≤1,500, page context ≤2,000, history ≤8,000, response ≤4,096 (DEC-273). |
| **Cross-References** | DEC-274, DEC-273, DEC-098 |

---

### RSK-049 | Stale Approval Execution
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-06 (Sprint 22) |
| **Likelihood** | Medium |
| **Impact** | Medium — executing outdated allocation/risk change |
| **Category** | Safety-critical |
| **Description** | Operator approves a proposal after conditions have changed (market regime shift, equity drawdown, strategy state change). Executing the proposal could be harmful. |
| **Mitigation** | 5-minute TTL (DEC-267) limits window for stale approvals. 4-condition pre-execution re-check gate: (1) target entity still exists, (2) regime hasn't changed unfavorably, (3) equity within ±5% of proposal time, (4) no circuit breaker active. Expired proposals auto-cleaned on 30-second interval. |
| **Cross-References** | DEC-267, DEC-272 |

---

### RSK-050 | tool_use Hallucination
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-06 (Sprint 22) |
| **Likelihood** | Low |
| **Impact** | Medium — invalid proposal created |
| **Category** | AI behavior |
| **Description** | Claude emits a `tool_use` block with invalid, nonsensical, or out-of-bounds parameters despite JSON schema validation. |
| **Mitigation** | Strict JSON schema validation in tools.py. Sane range bounds enforced (allocation 0–100%, risk params within defined ranges). Unrecognized tool calls logged as errors, no ActionProposal created. Human approval required for all configuration changes (4 of 5 tools). Audit logging of all proposals and outcomes. |
| **Cross-References** | DEC-271, DEC-272 |

---

### RSK-051 | aiosqlite Write Contention
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-06 (Sprint 22) |
| **Likelihood** | Low |
| **Impact** | Low-Medium — latency spike on trade logging |
| **Category** | Performance |
| **Description** | AI tables (`ai_conversations`, `ai_messages`, `ai_usage`, `ai_action_proposals`) share the same SQLite database file as the Trade Logger. High AI activity during active trading could cause write contention. |
| **Mitigation** | Monitor latency during paper trading. AI tables use `ai_` prefix for clear separation. If contention materializes, separate database file for AI tables is a straightforward migration. aiosqlite uses connection pooling to minimize lock duration. |
| **Cross-References** | DEC-267 |

---

### RSK-052 | FMP Endpoint Deprecation Risk
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-09 (Sprint 23.3) |
| **Likelihood** | Medium |
| **Impact** | High — breaks Universe Manager and Scanner at startup |
| **Category** | External Dependency |
| **Description** | FMP deprecated all legacy v3/v4 endpoints for accounts created after August 2025 with no advance notice. The `/stable/` endpoints could similarly change. ARGUS depends on FMP for both scanning (Sprint 21.7) and universe construction (Sprint 23/23.3). |
| **Mitigation** | (1) Monitor FMP changelog and documentation for deprecation notices. (2) FMP API URLs centralized in `fmp_scanner.py` and `fmp_reference.py` — migration requires two files. (3) Fallback: Universe Manager degrades to scanner symbols if stock-list fails. (4) FMP canary test at startup validates expected response keys (DEC-313). |
| **Trigger** | FMP returns unexpected errors or changes field names in stable API. |
| **Cross-References** | DEC-258, DEC-263, DEC-298, DEC-299, DEC-313 |
| **Status** | Open |

---

### RSK-053 | Finnhub Free Tier Reliability
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-03-10 |
| **Category** | External Dependency |
| **Description** | Finnhub free tier (60 calls/min) used for company news and analyst recommendations in CatalystPipeline. Free tier may have lower reliability guarantees, potential for unannounced rate limit changes, or service degradation during high-traffic periods. |
| **Likelihood** | Medium |
| **Impact** | Low — CatalystPipeline has two other sources (SEC EDGAR, FMP News). Finnhub failure degrades coverage but doesn't break the system. |
| **Mitigation** | Source isolation: each CatalystSource has independent timeout/retry handling. Pipeline continues with remaining sources if one fails. Consider Finnhub paid tier ($0/mo → $50/mo) if reliability issues surface in production. |
| **Owner** | Steven |
| **Status** | Open |
| **Cross-References** | DEC-304, DEC-306 |

---

### RSK-054 | Claude API Classification Cost Spike
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-03-10 |
| **Category** | Cost Management |
| **Description** | CatalystClassifier uses Claude API for headline classification. Unexpected news volume spike (e.g., market crash, major event) could trigger many classification calls, potentially exceeding expected API costs. |
| **Likelihood** | Low (most days have predictable news volume) |
| **Impact** | Low — $5/day ceiling (DEC-303) enforced via UsageTracker. Ceiling breach triggers rule-based fallback, not cost overrun. |
| **Mitigation** | Daily cost ceiling hard-coded at $5/day with automatic fallback to rule-based classifier. UsageTracker monitors and logs all API costs. Ceiling configurable in system.yaml if adjustment needed. |
| **Owner** | Steven |
| **Status** | Open |
| **Cross-References** | DEC-301, DEC-303, DEC-274 |

---

### RSK-055 | SEC EDGAR Rate Limiting
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-03-10 |
| **Category** | External Dependency |
| **Description** | SEC EDGAR has rate limits (10 requests/second for authenticated, lower for unauthenticated). High-volume scans during pre-market could trigger rate limiting, delaying catalyst data availability. |
| **Likelihood** | Low (ARGUS scans ~10-15 symbols, well within limits) |
| **Impact** | Low — SEC filings are time-insensitive (8-K filings are typically hours/days old). Delays of seconds or minutes don't affect trading decisions. |
| **Mitigation** | SECEdgarSource implements exponential backoff on 429 responses. User-Agent header includes contact email per SEC guidelines. Consider adding API key for authenticated access if volume increases significantly. |
| **Owner** | Steven |
| **Status** | Open |
| **Cross-References** | DEC-304 |

---

### RSK-056 | External API Concentration Risk
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-10 (Sprint 23.6) |
| **Likelihood** | Medium |
| **Impact** | High — FMP is single point of failure for Universe Manager, Catalyst news, and scanning |
| **Category** | External Dependency |
| **Description** | ARGUS depends on three free/low-cost external APIs for intelligence: FMP ($22/mo), Finnhub (free), SEC EDGAR (free). FMP is the highest-risk dependency — it powers Universe Manager reference data, catalyst news ingestion, and pre-market scanning. A sustained FMP outage would degrade universe construction and catalyst coverage simultaneously. |
| **Mitigation** | (1) Graceful degradation per source — each CatalystSource has independent error handling. (2) FMP canary test (DEC-313) provides early warning. (3) Reference data file cache (DEC-314) enables startup without FMP for cached symbols. (4) Universe Manager fallback to scanner symbols if stock-list fails. (5) Consider backup data provider (Polygon.io, Alpha Vantage) if FMP reliability degrades. |
| **Trigger** | FMP outage lasting >2 hours during pre-market or market hours. |
| **Cross-References** | DEC-258 (FMP integration), DEC-298 (stable API migration), DEC-313 (canary test), DEC-314 (cache), RSK-052 (endpoint deprecation) |
| **Status** | Open |

---

## Review Schedule

| Review Type | Frequency | Next Review |
|-------------|-----------|-------------|
| Full register review | Monthly | March 14, 2026 |
| Assumption spot-check | After significant market events | As needed |
| Risk re-assessment | After system incidents | As needed |
| Post-phase review | After each build phase | End of Phase 1 |

---

## Archived Entries

*Closed, resolved, or superseded items moved here for historical reference. Archived 2026-03-06 during DEC-262 documentation consolidation.*

### ASM-005 — Commission-Free Trading Sustainability (SUPERSEDED)
| Field | Value |
|-------|-------|
| **Assumption** | ~~Commission-free trading remains available.~~ No longer relevant — IBKR Pro uses tiered commission pricing (DEC-083). |
| **Confidence** | N/A |
| **Basis** | IBKR Pro charges ~$0.0035/share + clearing/exchange fees. This is an explicit cost, offset by estimated $0.02/share execution quality advantage over PFOF brokers. Net cost-positive. |
| **Status** | Superseded by DEC-083. Commission costs are explicit and budgeted. |
| **Closed** | 2026-03-06 — Superseded by IBKR production architecture. |

---

### ASM-008 — VPS Reliability
| Field | Value |
|-------|-------|
| **Assumption** | AWS EC2 in us-east-1 provides >99.9% uptime during market hours |
| **Confidence** | High |
| **Basis** | AWS SLA guarantees 99.99% for EC2. us-east-1 is their most mature region. |
| **If Wrong** | Positions unmanaged during outage. Broker-side stops remain active but no dynamic management. |
| **Contingency** | All stops placed at broker level. Dead man's switch alerts user if system goes silent. Recovery procedure targets <5 minutes. Consider multi-AZ if single instance proves unreliable. |
| **Closed** | 2026-03-06 — ARGUS now runs locally (previously Taipei, then Cape Town, now US East Coast), not on AWS VPS. Assumption no longer applies. |

---

### ASM-015 — IBKR Account Opening Timeline
| Field | Value |
|-------|-------|
| **Assumption** | IBKR account (including paper trading) can be opened within 1–2 weeks, not blocking Sprint 13 significantly. |
| **Confidence** | Medium-High |
| **Basis** | Application submitted Feb 21, 2026. Account ID: U24619949. Individual margin account, IBKR Pro, Georgia address. Standard US citizen application — typically approved in 1–3 business days. Applying while physically in Taiwan may trigger additional verification, but IBKR is known to be accommodating of US citizens abroad. |
| **If Wrong** | Sprint 13 development proceeds against mock Gateway responses. Integration testing delayed until account is approved. |
| **Contingency** | Develop IBKRBroker adapter using mock/recorded responses. Integration testing happens when account is ready. Alpaca paper trading continues unaffected during the wait. Contact newaccounts@interactivebrokers.com if no response within 5 business days. |
| **Review Date** | Feb 26, 2026 (5 business days post-submission) |
| **Closed** | Resolved (DEC-236) — IBKR account approved Feb 28, 2026. Paper trading ready for Sprint 21.5. |

---

### RSK-013 — Weekly Loss Limit Reset on Restart
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low |
| **Description** | If the system restarts mid-week, the weekly realized P&L must be reconstructed from the database. Without reconstruction, the weekly loss limit effectively resets to zero, allowing more risk than intended. |
| **Mitigation** | `reconstruct_state()` method queries TradeLogger for the current week's trades and rebuilds weekly P&L. Tested explicitly. Integrity check verifies reconstruction accuracy. Implemented and tested in Sprint 2 polish. |
| **Owner** | Risk Manager |
| **Closed** | 2026-03-06 — State reconstruction implemented and tested in Sprint 2. Risk fully mitigated. |

---

### RSK-014 — Flaky Reconnection Test
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Likelihood** | High |
| **Description** | `test_reconnection_with_exponential_backoff` in AlpacaDataService tests is timing-dependent and fails intermittently. Not a production issue, but degrades CI reliability and masks real failures. |
| **Mitigation** | Fixed in Sprint 4a polish: mocked `asyncio.sleep` to make the test deterministic. Validated with 10x consecutive passes. Commit 738aab8. |
| **Closed** | February 15, 2026 |
| **Owner** | Development |

---

### RSK-015 — Stale Data False Positives Outside Market Hours
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | High |
| **Description** | The stale data monitor in AlpacaDataService runs continuously but only expects data during market hours (9:30 AM – 4:00 PM EST). Outside those hours, lack of data is normal but will trigger stale data alerts and potentially pause strategies unnecessarily during pre-market startup. |
| **Mitigation** | Stale data monitor now checks market hours (9:30–16:00 ET) and weekdays before alerting. Implemented in Sprint 5 with market hours gating in `_stale_data_monitor()`. |
| **Closed** | February 16, 2026 |
| **Owner** | Data Service |

---

### RSK-019 | VectorBT / Replay Harness Trade Count Divergence
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-17 |
| **Date Resolved** | 2026-02-17 |
| **Category** | Data Integrity |
| **Likelihood** | Mitigated |
| **Impact** | Reduced — parameter mismatch bugs fixed; known ATR divergence is architectural, not a bug |
| **Description** | Original issue: cross-validation showed VectorBT 21 trades vs Replay Harness 135 trades (ratio 0.16). Root causes identified: (1) CLI hardcoded 4 of 6 parameters, (2) function used `.get()` with defaults, (3) Replay Harness loaded all 29 symbols vs VectorBT's 1 symbol. |
| **Resolution** | (1) Added all 6 CLI args for cross-validation mode. (2) Function now requires all params explicitly (raises KeyError if missing). (3) Added `symbols` field to `BacktestConfig`; Replay Harness now filters symbols. After fixes: TSLA with matched params (max_atr=0.5) shows VectorBT 17, Replay 0 — PASS. With max_atr=999.0: VectorBT 21, Replay 39 — known divergence due to ATR calculation difference (daily vs 1m), not a bug. |
| **Remaining Known Divergence** | VectorBT computes ATR(14) from daily bars; BacktestDataService uses 1m bars. This causes range/ATR ratios to be higher in Replay Harness, rejecting more entries with tight filters. This is an architectural difference — VectorBT is an approximation for fast parameter sweeps, not a perfect emulator. |
| **Closed** | 2026-02-17 — no longer blocks Sprint 10 |
| **Tests** | 542 tests passing; new test `test_cross_validate_missing_params_raises` verifies param validation |

---

### RSK-024 | Sprint 21 Scope Risk — Analytics Sprint May Exceed Single Sprint
| Field | Value |
|-------|-------|
| **Date** | 2026-02-23 |
| **Description** | Sprint 21 (CC Analytics & Strategy Lab) is estimated at 80–100 hours across 11 features (21-A through 21-K). This significantly exceeds the scope of previous sprints. Risk of scope creep or quality degradation if attempted as a single sprint. |
| **Likelihood** | High |
| **Impact** | Medium — schedule slip, potential quality issues |
| **Mitigation** | Plan to split into Sprint 21a (highest-priority items: stock detail panel, Dashboard V2, heatmaps) and Sprint 21b (remaining items: treemap, correlation matrix, trade replay, etc.). Use priority tiers from UX Feature Backlog to select which items ship first. The backlog is a menu, not a mandate. |
| **Closed** | Mitigated ✅ — Sprint 21 split into 21a–21d (DEC-171). All 4 sub-sprints completed on schedule (Feb 27–28). Scope managed successfully through incremental delivery. |

---

### RSK-030 | Low Afternoon Trade Counts in Alpaca IEX Data
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-26 |
| **Category** | Data Quality |
| **Description** | Afternoon Momentum consolidation detection and breakout confirmation are volume-sensitive. Alpaca's IEX data captures only ~2-3% of market volume (DEC-081). VectorBT sweep may produce very few qualifying trades, making statistical analysis unreliable. |
| **Likelihood** | High |
| **Impact** | Medium — sweep results are directional guidance only, not statistically validated. |
| **Mitigation** | All results provisional per DEC-132. True validation requires Databento exchange-direct data. Low trade counts don't invalidate the strategy thesis — they indicate data limitations. |
| **Owner** | Steven |
| **Closed** | 2026-03-06 — Databento EQUS.MINI is now the primary data source (DEC-248). Alpaca IEX data quality is irrelevant for production. |

---

### RSK-037 | First Live Integration Discovery Risk
| Field | Value |
|-------|-------|
| **Date** | 2026-02-28 |
| **Risk** | Integration testing against real Databento and IBKR services may uncover issues not caught by mock-based unit tests (data format differences, timing edge cases, network reliability, API behavior discrepancies). |
| **Likelihood** | High (nearly certain some issues will surface) |
| **Impact** | Low-Medium (delays Sprint 21.5 completion by 2-4 sessions at most) |
| **Mitigation** | Sprint 21.5 is structured with buffer sessions (13-15) specifically for fixing discovered issues. Phased approach (Databento first, IBKR second, combined third) isolates problems. No real capital at risk during this phase. |
| **Outcome** | VALIDATED — Risk materialized as expected. Six integration discoveries required code fixes: (1) Databento `instrument_id` direct attribute, not nested in header (DEC-241), (2) built-in `symbology_map` replaces custom DatabentoSymbolMap (DEC-242), (3) fixed-point price format ×1e9 (DEC-243), (4) historical data ~15-min intraday lag (DEC-244), (5) `flatten_all()` SMART routing for exit orders (DEC-245), (6) `get_open_orders()` missing from Broker ABC (DEC-246). Additional discovery: historical daily bar data has multi-day lag (~6 days over weekends), handled by scanner resilience fix (DEC-247). All issues resolved within the sprint's buffer sessions. Impact was exactly as estimated — Low-Medium. |
| **Closed** | 2026-03-05 — Sprint 21.5 |

---

### RSK-040 — Sprint 21.5 Block C Not Yet Validated
| Field | Value |
|-------|-------|
| **Risk** | No full market day has been run with all 4 strategies live. System-level interactions under real market conditions are untested. |
| **Severity** | High |
| **Likelihood** | High (it hasn't happened yet) |
| **Mitigation** | Block C is the next milestone. Must complete before advancing to Sprint 22. |
| **Closed** | 2026-03-06 — Sprint 21.5 completed March 5, 2026. Block C validated with all 4 strategies running live. |

---

### RSK-041 — Documentation Tier Transition Risk
| Field | Value |
|-------|-------|
| **Risk** | Moving from monolithic Project Knowledge to Tier A/B split creates a window where some context may be in the old format and some in the new. |
| **Severity** | Low |
| **Likelihood** | Medium |
| **Mitigation** | Complete file placement in repo before starting Sprint 22. Verify Claude Code reads new CLAUDE.md correctly in first post-retrofit session. |
| **Closed** | 2026-03-06 — Metarepo installation complete. Documentation tier transition successful. All files renamed to kebab-case and archived. |

---

### RSK-043 | ORB Dual-Fire on Same Symbol
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-04 (C2 paper trading) |
| **Resolved** | 2026-03-05 (Sprint 21.5.1 Session 1) |
| **Description** | ORB Breakout and ORB Scalp fired simultaneously on the same symbol, doubling risk exposure beyond concentration limits. |
| **Impact** | 4 incidents in C2: AMZN, NFLX, META, SPY. Effective concentration ~10–12.5% vs 5% cap. |
| **Resolution** | DEC-261: ClassVar `_orb_family_triggered_symbols` on OrbBaseStrategy provides first-to-fire-wins mutual exclusion. |

---

### RSK-044 | Concentration Limit Race Condition
| Field | Value |
|-------|-------|
| **Identified** | 2026-03-04 (C2 analysis) |
| **Resolved** | 2026-03-05 (Sprint 21.5.1 Session 1) |
| **Description** | Multiple signals approved before fills arrived, allowing total exposure to exceed concentration limit. |
| **Impact** | All 4 C2 dual-fire symbols hit ~12.3–12.5% vs 5% cap. |
| **Resolution** | `get_pending_entry_exposure()` on OrderManager now included in Risk Manager concentration check. |

---

### RSK-045 — Quality Engine Running on Partial Signal
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-03-21 |
| **Severity** | Medium |
| **Likelihood** | High (confirmed — DEF-082) |
| **Description** | 45% of the Quality Engine composite score (catalyst_quality 25% + volume_profile 20%) returns neutral defaults (50.0) because real-time RVOL and symbol-specific catalyst data are not flowing to the scorer. The Dynamic Position Sizer makes sizing decisions based on 55% of intended signal (pattern_strength 30%, historical_match 15%, regime_alignment 10%). Quality grades may cluster with less differentiation than designed. |
| **Mitigation** | (1) Learning Loop V1 (Sprint 28) will correlate quality scores with trade outcomes, revealing whether the active 55% is sufficient. (2) If >80% of trades cluster in 2 adjacent grades, consider reweighting active dimensions to use the full 0–100 range. (3) FMP Premium upgrade (DEC-356) revisited after Learning Loop data. |
| **Detection** | Monitor quality_history table grade distribution weekly. Flag if grade variance is below threshold. |
| **Owner** | Quality Engine / Learning Loop |
| **Status** | Open |

---

### RSK-046 — Phase 6 Infrastructure Density

| Field | Value |
|-------|-------|
| **Date Identified** | 2026-03-23 |
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Description** | With DEC-357 and DEC-358 adopted, Phase 6 now includes five consecutive sprints (21.6, 27.5, 27.6, 27.7, 28) before the Learning Loop produces its first actionable result. That's ~12–15 days of infrastructure building before the feedback loop closes. Risk: morale and momentum may suffer from extended infrastructure phase without visible trading system improvement. |
| **Mitigation** | (1) Paper trading continues running in parallel throughout, accumulating data that makes Sprint 28 more powerful when it arrives. (2) Each infrastructure sprint has clear, testable deliverables — not speculative design. (3) If implementation runs faster than estimated, opportunities exist to absorb 27.6 or 27.7 scope into adjacent sprints. (4) The three infrastructure sprints (27.5, 27.6, 27.7) transform Sprint 28 from basic weight tuning into intelligent system analysis with 24× more data — the delay pays for itself in Sprint 28 quality. |
| **Owner** | Steven |
| **Status** | Closed |
| **Closed** | 2026-03-30 — Entire infrastructure arc (Sprints 27–28.5, 13 sprints in ~8 calendar days) completed successfully. Learning Loop V1, Exit Management, Counterfactual Engine, Evaluation Framework, Regime Intelligence, VIX Data Service, Broker Safety all operational. Morale and momentum concerns did not materialize. |

---

### RSK-047 — yfinance Reliability as Unofficial Scraping Library

| Field | Value |
|-------|-------|
| **Date Identified** | 2026-03-26 |
| **Severity** | Low |
| **Likelihood** | Medium |
| **Description** | VIXDataService (Sprint 27.9) depends on yfinance, an unofficial Yahoo Finance scraper with no SLA. Yahoo may change their HTML structure or API endpoints at any time, breaking data ingestion. This would cause VIX-based regime dimensions to return None (graceful degradation) but would blind the system to VIX context until fixed. |
| **Mitigation** | (1) SQLite persistence cache (`data/vix_landscape.db`) survives outages — cached data remains available. (2) Staleness self-disable (`max_staleness_days=3`) — VIX calculators return None after 3 trading days without fresh data, preventing stale classifications. (3) Optional FMP fallback (`fmp_fallback_enabled` config flag) — not yet implemented but architecture supports it. (4) Daily-only frequency — not real-time, so brief outages during off-hours are invisible. (5) All VIX dimensions are Optional in RegimeVector — system operates normally without VIX data. |
| **Owner** | Steven |
| **Status** | Open |

---

### RSK-048 — Quality Engine Grade Clustering Under Partial Signal

| Field | Value |
|-------|-------|
| **Date Identified** | 2026-03-30 |
| **Category** | System Effectiveness |
| **Severity** | Medium |
| **Likelihood** | Medium-High |
| **Description** | Escalation of RSK-045. With 752+ trades/day under current configuration, there is now sufficient data to measure whether the Quality Engine's partial signal (55% of designed input — pattern_strength 30%, historical_match 15%, regime_alignment 10%; catalyst_quality and volume_profile return neutral 50.0 defaults) produces meaningful grade differentiation. If grades cluster tightly (e.g., 80%+ of trades in B to B+ range), the Dynamic Position Sizer is barely differentiating between setups, defeating the purpose of quality-based sizing. The Learning Loop should be detecting this — if it recommends weight redistribution away from stubbed dimensions, that's the system self-correcting. |
| **Mitigation** | (1) Paper trading data audit (DEC-381, week of April 6+) will include grade distribution analysis. (2) Learning Loop V1 WeightAnalyzer should surface low-correlation dimensions for weight reduction. (3) If clustering is confirmed, consider: reweighting active dimensions to use full 0–100 range, or temporarily setting catalyst_quality and volume_profile weights to 0 and redistributing to active dimensions. (4) FMP Premium upgrade ($59/mo, DEC-356) would activate volume_profile dimension. |
| **Detection** | Query `quality_history` table for grade distribution. Flag if >70% of trades receive the same grade or if grade standard deviation < 5 points. |
| **Owner** | Learning Loop / Quality Engine |
| **Status** | Open |

---

### RSK-049 — Shadow Variant Throughput Impact
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-04-01 |
| **Category** | System Performance |
| **Severity** | High |
| **Likelihood** | Medium |
| **Description** | Running dozens of shadow strategy variants simultaneously may cause throughput degradation to live strategy signal processing. Each shadow variant subscribes to CandleEvents on the Event Bus. As the variant repertoire grows (Sprint 32+), the aggregate Event Bus subscriber count and per-event handler time may introduce latency in the live signal path. |
| **Mitigation** | `max_shadow_variants_per_pattern` config cap (default 5). Performance benchmarking during Sprint 32 implementation. Escalation to Tier 3 if >10% throughput impact measured in any session. |
| **Owner** | Sprint 32 implementation |
| **Status** | Open |

---

### RSK-050 — Promotion Oscillation
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-04-01 |
| **Category** | System Stability |
| **Severity** | Medium |
| **Likelihood** | Medium |
| **Description** | A variant may be repeatedly promoted and demoted due to changing market regimes, creating instability and unnecessary mode switches. Each mode switch disrupts position tracking continuity and may create confusing audit trails. |
| **Mitigation** | Minimum shadow days threshold before promotion eligibility. Hysteresis in PromotionEvaluator — recently promoted variants immune from demotion for `promotion_min_shadow_days`. PromotionEvent audit trail enables detection of oscillation patterns. |
| **Owner** | Sprint 32 PromotionEvaluator design |
| **Status** | Open |

---

### RSK-051 — DuckDB Unusable on 983K-File Parquet Cache
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-04-20 |
| **Category** | Research Infrastructure |
| **Severity** | Medium |
| **Likelihood** | Confirmed |
| **Description** | 983K individual monthly Parquet files make all DuckDB query paths unusable. `CREATE VIEW` scans every file on every query (60+ minutes for `COUNT DISTINCT`). `CREATE TABLE` materialization estimated 16+ hours. Blocks Research Console SQL features (Sprint 31B) and any future analytical queries against the full historical cache. |
| **Mitigation** | **Resolved by Sprint 31.85 (DEF-161).** `scripts/consolidate_parquet_cache.py` produces a derived `data/databento_cache_consolidated/` cache with ~24K per-symbol files, an embedded `symbol` column, non-bypassable row-count validation, and a DuckDB benchmark harness. `HistoricalQueryService` is repointed to the consolidated cache via operator edit of `config/historical_query.yaml` (unchanged in-sprint). Original cache remains read-only source of truth for `BacktestEngine`. Interim `scripts/resolve_symbols_fast.py` retained for symbol resolution; consolidated cache supersedes it for general DuckDB queries. |
| **Owner** | Sprint 31.85 (resolved); post-sprint operator runs the consolidation and repoints the config. |
| **Status** | **Mitigated — pending operator activation.** Code path closed; risk drops to Low after first successful consolidation run and config repoint. |

---

### RSK — Upstream Cascade Mechanism (DEF-204)

| Field | Value |
|-------|-------|
| **ID** | RSK-DEF-204 |
| **Date Identified** | 2026-04-24 |
| **Category** | Operational Safety — Critical |
| **Severity** | Critical |
| **Likelihood** | Confirmed (3 successive paper-session debriefs Apr 22–24) |
| **Description** | Bracket children placed via `parentId` only without explicit `ocaGroup`, combined with redundant standalone SELL orders from trail/escalation paths sharing no OCA group with bracket children, allow multi-leg fill races. ARGUS's exit-side accounting is also side-blind in 3 surfaces (reconcile orphan-loop one-direction-only; reconcile call site strips side info; DEF-158 retry path side-blind). On Apr 24 paper trading: 44 symbols / 14,249 shares of unintended short positions accumulated through gradual reconciliation-mismatch drift over a 6-hour session. Today's raw upstream cascade is ~2.0× worse than yesterday's pre-doubling magnitude despite the lightest network stimulus of the three debriefed days. |
| **Mitigation (in effect)** | Operator runs `scripts/ibkr_close_all_positions.py` daily at session close. IMPROMPTU-04's A1 fix (DEF-199) correctly refuses to amplify these at EOD (1.00× signature, zero doubling) and escalates to operator with CRITICAL alert. `ArgusSystem._startup_flatten_disabled` invariant (`check_startup_position_invariant()` in `argus/main.py`) gates `OrderManager.reconstruct_from_broker()` on any non-BUY broker side at boot. |
| **Owner** | post-31.9-reconciliation-drift sprint (3 sessions, all-three-must-land-together, adversarial review required at every session boundary). |
| **Status** | **OPEN — mitigation in effect; fix scoped and scheduled.** Not safe for live trading until post-31.9-reconciliation-drift lands. |
| **Cross-references** | DEF-204 (CLAUDE.md DEF table); IMPROMPTU-11 mechanism diagnostic (`docs/sprints/sprint-31.9/IMPROMPTU-11-mechanism-diagnostic.md`); Apr 24 debrief §A2/§C12 (`docs/sprints/sprint-31.9/debrief-2026-04-24-triage.md`); post-31.9-reconciliation-drift DISCOVERY (`docs/sprints/post-31.9-reconciliation-drift/DISCOVERY.md`). |

---

### RSK — Risk Manager WARNING-Spam Throttling Gap (DEF-203)

| Field | Value |
|-------|-------|
| **ID** | RSK-DEF-203 |
| **Date Identified** | 2026-04-24 |
| **Category** | Operational Hygiene |
| **Severity** | Low |
| **Likelihood** | High (10,729 events on Apr 24, 8,996 on Apr 23 — confirmed pattern) |
| **Description** | `max_concurrent_positions` WARNING spam not throttled. WARNING-level emit from `argus/core/risk_manager.py` does not wrap through `ThrottledLogger` (Sprint 27.75 / DEC-363) like other per-symbol high-volume sites. One of the larger non-`pattern_strategy` log-volume contributors during high-signal-velocity sessions. |
| **Mitigation** | **MONITOR-only.** Fix queued for next `argus/core/risk_manager.py` touch (likely as part of post-31.9-reconnect-recovery-and-rejectionstage's DEF-195 work — that sprint will already be in `risk_manager.py` for the broker-state divergence count fix). Proposed change: ThrottledLogger at 60s/symbol, OR downgrade to DEBUG and rely on aggregate counters (Risk Manager already tracks rejection counts via SignalRejectedEvent). |
| **Owner** | Next `argus/core/risk_manager.py` touch (most likely post-31.9-reconnect-recovery-and-rejectionstage). |
| **Status** | **Open — MONITOR.** No immediate operational impact beyond log noise; cosmetic regression of the Sprint 27.75 throttling discipline. |
| **Cross-references** | DEF-203 (CLAUDE.md DEF table); DEC-363 ThrottledLogger pattern; DEF-195 cross-reference (paired sprint candidate). |

---

*End of Risk & Assumptions Register v1.7*
