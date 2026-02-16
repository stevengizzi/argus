# ARGUS — Risk & Assumptions Register

> *Version 1.0 | February 2026*
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

### ASM-002 — Alpaca API Reliability
| Field | Value |
|-------|-------|
| **Assumption** | Alpaca API maintains >99.5% uptime during market hours; WebSocket latency remains <200ms |
| **Confidence** | Medium-High |
| **Basis** | Alpaca is well-funded with thousands of algorithmic traders. Strong historical uptime record. |
| **If Wrong** | Strategy performance degrades. Scalp strategies may become unviable at >200ms latency. |
| **Contingency** | IBKR adapter built from day one as fallback. Data stall detection (30-second timeout) triggers safe mode. All stops placed broker-side. Continuous latency monitoring. |
| **Review Date** | After first month of live trading |

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

### ASM-005 — Commission-Free Trading Sustainability
| Field | Value |
|-------|-------|
| **Assumption** | Alpaca will continue offering commission-free trading |
| **Confidence** | Medium |
| **Basis** | Industry standard since 2019. Alpaca's business model is built around it. |
| **If Wrong** | Scalp strategy profitability most affected (many trades, small gains). Longer-hold strategies less impacted. |
| **Contingency** | IBKR Lite as commission-free alternative. System tracks hypothetical commission impact on each strategy. Commission parameter in profitability calculations (currently $0, easily adjustable). |
| **Review Date** | Quarterly |

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

### ASM-008 — VPS Reliability
| Field | Value |
|-------|-------|
| **Assumption** | AWS EC2 in us-east-1 provides >99.9% uptime during market hours |
| **Confidence** | High |
| **Basis** | AWS SLA guarantees 99.99% for EC2. us-east-1 is their most mature region. |
| **If Wrong** | Positions unmanaged during outage. Broker-side stops remain active but no dynamic management. |
| **Contingency** | All stops placed at broker level. Dead man's switch alerts user if system goes silent. Recovery procedure targets <5 minutes. Consider multi-AZ if single instance proves unreliable. |
| **Review Date** | After first major AWS incident |

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

### RSK-013 — Weekly Loss Limit Reset on Restart
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | Low |
| **Description** | If the system restarts mid-week, the weekly realized P&L must be reconstructed from the database. Without reconstruction, the weekly loss limit effectively resets to zero, allowing more risk than intended. |
| **Mitigation** | `reconstruct_state()` method queries TradeLogger for the current week's trades and rebuilds weekly P&L. Tested explicitly. Integrity check verifies reconstruction accuracy. Implemented and tested in Sprint 2 polish. |
| **Owner** | Risk Manager |

---

### RSK-014 — Flaky Reconnection Test ✅ CLOSED
| Field | Value |
|-------|-------|
| **Severity** | Low |
| **Likelihood** | High |
| **Description** | `test_reconnection_with_exponential_backoff` in AlpacaDataService tests is timing-dependent and fails intermittently. Not a production issue, but degrades CI reliability and masks real failures. |
| **Mitigation** | Fixed in Sprint 4a polish: mocked `asyncio.sleep` to make the test deterministic. Validated with 10x consecutive passes. Commit 738aab8. |
| **Status** | **Closed** — February 15, 2026 |
| **Owner** | Development |

---

### RSK-015 — Stale Data False Positives Outside Market Hours ✅ CLOSED
| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Likelihood** | High |
| **Description** | The stale data monitor in AlpacaDataService runs continuously but only expects data during market hours (9:30 AM – 4:00 PM EST). Outside those hours, lack of data is normal but will trigger stale data alerts and potentially pause strategies unnecessarily during pre-market startup. |
| **Mitigation** | Stale data monitor now checks market hours (9:30–16:00 ET) and weekdays before alerting. Implemented in Sprint 5 with market hours gating in `_stale_data_monitor()`. |
| **Status** | **Closed** — February 16, 2026 |
| **Owner** | Data Service |

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

### RSK-019 | VectorBT / Replay Harness Trade Count Divergence
| Field | Value |
|-------|-------|
| **Date Identified** | 2026-02-17 |
| **Category** | Data Integrity |
| **Likelihood** | Confirmed (cross-validation failed) |
| **Impact** | High — walk-forward results may be unreliable if IS optimization (VectorBT) and OOS validation (Replay Harness) disagree on trade counts for identical parameters |
| **Description** | Cross-validation on TSLA showed VectorBT producing 21 trades vs Replay Harness producing 135 for the same symbol and date range. Expected VectorBT ≥ Replay (VectorBT has fewer filters). Immediate cause: cross_validate function hardcodes `max_range_atr_ratio=999.0` for Replay. Deeper question: does the walk-forward engine pass consistent parameters to both engines? |
| **Mitigation** | (1) Investigate cross_validate parameter passing — fix the hardcoded ATR override. (2) Re-run cross-validation with matched parameters. (3) If engines still diverge, audit the walk-forward pipeline for parameter consistency between IS and OOS phases. |
| **Status** | Open |
| **Trigger** | Blocks Sprint 10 Steps 4–5 (parameter recommendations and final report). |

---

## Review Schedule

| Review Type | Frequency | Next Review |
|-------------|-----------|-------------|
| Full register review | Monthly | March 14, 2026 |
| Assumption spot-check | After significant market events | As needed |
| Risk re-assessment | After system incidents | As needed |
| Post-phase review | After each build phase | End of Phase 1 |

---

*End of Risk & Assumptions Register v1.0*
