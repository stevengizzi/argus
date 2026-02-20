# ARGUS — Execution Broker Research Report

> **Document Type:** Research Deep Dive — Archaeological Record  
> **Date:** February 20, 2026  
> **Status:** Final  
> **Author:** Steven (project owner) with Claude (AI co-captain)  
> **Classification:** Internal Reference — ARGUS Project  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Catalyst](#2-research-catalyst)
3. [ARGUS Execution Requirements](#3-argus-execution-requirements)
4. [Provider Evaluation: Tier 1 — Full Analysis](#4-provider-evaluation-tier-1--full-analysis)
5. [Provider Evaluation: Tier 2 — Quick Assessment](#5-provider-evaluation-tier-2--quick-assessment)
6. [Provider Evaluation: Tier 3 — Dismissed Early](#6-provider-evaluation-tier-3--dismissed-early)
7. [Community Evidence & Practitioner Reports](#7-community-evidence--practitioner-reports)
8. [Comparative Analysis](#8-comparative-analysis)
9. [Decision Framework](#9-decision-framework)
10. [Final Architecture Decision](#10-final-architecture-decision)
11. [Implementation Implications](#11-implementation-implications)
12. [Risk Assessment](#12-risk-assessment)
13. [Appendix A: Pricing Details](#appendix-a-pricing-details)
14. [Appendix B: Regulatory Filings & Source Material](#appendix-b-regulatory-filings--source-material)

---

## 1. Executive Summary

This report documents a rigorous evaluation of execution brokers for the ARGUS automated day trading system. The research was triggered by the market data investigation (DEC-081/082, February 18–20) which dismantled the assumption that Alpaca should serve as both data provider and execution broker. Having established Databento as the data backbone, the execution side warranted equivalent scrutiny before real capital flows through it.

Three Tier 1 brokers received full analysis: Alpaca Markets (incumbent), Interactive Brokers (planned for scaling), and Tradier (API-first alternative). Three Tier 2 brokers received quick assessments. Three Tier 3 brokers were dismissed early.

**Key findings:**

- **Alpaca's PFOF model routes orders to Virtu Financial and Citadel Securities**, receiving payment of up to 12 cents per 100 shares on marketable orders. A September 2024 SEC fine ($400K) for recordkeeping violations and 125+ tracked outages in a 9-month monitoring period raise reliability concerns for a household income system.
- **Interactive Brokers' execution quality is industry-leading**: SmartRouting across 20+ venues, 100% price improvement rate on independently verified tests, no PFOF, direct exchange routing. The `ib_async` Python library (successor to `ib_insync`) provides asyncio-native access compatible with ARGUS's architecture.
- **Tradier is a viable API-first alternative** with clean REST APIs and subscription-based commission-free equities, but offers neither the execution quality of IBKR nor the development convenience of Alpaca. It occupies a middle ground that doesn't solve ARGUS's actual needs.

**Recommendation — Direct IBKR Adoption:**

~~The original recommendation was a phased Alpaca → IBKR migration. After further discussion, the decision was revised:~~

1. **Immediate (next Build Track sprint):** Build the IBKRBroker adapter. Interactive Brokers becomes the execution broker for both pre-live paper trading validation and live trading from day one.
2. **Rationale for revision:** With no immediate pressure to go live, the phased migration optimized for "fastest path to first live trade" — a constraint that wasn't actually binding. The 3–5 day adapter build + 2-week IBKR paper trading validation fits the timeline. Learning one broker's operational characteristics instead of two eliminates throwaway knowledge and migration risk.
3. **Alpaca's role:** AlpacaBroker adapter retained in codebase permanently for strategy incubator paper testing (where PFOF is irrelevant). Alpaca paper trading continues until IBKR adapter is validated, then IBKR takes over.

**Critical action item:** Begin IBKR account application immediately. Account approval can take days to weeks and should not block adapter development. A paper trading account is sufficient to begin Sprint 12.

---

## 2. Research Catalyst

### 2.1 The Data Provider Precedent

The market data research (February 18–20, 2026) established a critical architectural principle: convenience defaults deserve the same rigor as deliberate choices. Alpaca was originally selected for both data and execution as a single-provider convenience — the same assumption that collapsed when IEX data turned out to capture only 2–3% of market volume, forcing the switch to Databento.

Decision DEC-082 established that data and execution should be decoupled — separate providers, separate failure domains. Databento now handles all market data. The execution side remained unexamined.

### 2.2 What This Research Must Answer

Three questions, in order of urgency:

1. **Is Alpaca adequate for initial live trading at minimum size?** Can we proceed to live trading validation, or must we build a different broker adapter first?
2. **What is the right long-term execution broker for ARGUS?** Where do we end up when the system runs 30+ strategies across multiple asset classes?
3. **When should the transition happen?** Before live? After initial validation? At a specific scaling threshold?

### 2.3 ARGUS Context for Broker Selection

ARGUS is not a casual trading experiment. Key context:

- **Mission:** Household income generation through autonomous trading. Reliability is existential.
- **Current state:** 542 tests passing. Paper trading active on Alpaca with DEC-076 ORB parameters.
- **Broker abstraction exists.** The `BrokerAbstraction` layer means switching brokers requires building a new adapter (~3–5 day sprint), not rearchitecting the system.
- **AlpacaBroker is built and tested.** ~80 tests covering order placement, bracket orders, WebSocket fill streaming, position management.
- **Typical order profile:** Market orders on liquid large-caps (NVDA, AMZN, GOOGL, MSFT, AAPL, NFLX). Order sizes of $500–$5,000. 5-minute opening range breakout strategy with 15-minute maximum hold time and 2R profit targets. ~5–15 trades per day initially, scaling to 50–100+ with multiple strategies.
- **Asset class roadmap:** US Stocks (now) → Crypto → Forex → Futures.
- **Operating timezone:** Steven is in Taipei. US market open (9:30 AM ET) is 10:30 PM local time. Broker support responsiveness during US hours matters more than during Asian business hours.

---

## 3. ARGUS Execution Requirements

### 3.1 Critical Requirements (Must Have)

| Requirement | Rationale |
|---|---|
| Reliable order execution at US market open (9:30–9:35 AM ET) | ORB strategy's entire edge depends on the first 5–15 minutes |
| Market orders with sub-second fill on liquid large-caps | Breakout entries are time-critical |
| Bracket orders (stop-loss + take-profit) | Core risk management mechanism |
| WebSocket or streaming fill notifications | Order Manager needs real-time fill confirmation |
| Python API (official or high-quality community) | ARGUS is Python-native, asyncio architecture |
| Paper trading environment | Strategy validation before live deployment |
| SIPC insurance | Non-negotiable for household capital |
| $25K+ account support without restrictions | PDT rule management |

### 3.2 High-Priority Requirements (Strong Preference)

| Requirement | Rationale |
|---|---|
| Direct exchange routing (non-PFOF) | Better price improvement on breakout entries |
| 100+ order types and algo orders | Future strategy sophistication |
| Multi-asset via single API | Roadmap: crypto, forex, futures |
| Server-side stop management | Reduces client-side failure modes |
| Short selling capability | Future strategy development |
| Portfolio margin availability | Capital efficiency at scale |

### 3.3 Nice-to-Have Requirements

| Requirement | Rationale |
|---|---|
| Co-location/low-latency infrastructure | Not needed for 5-minute+ timeframes, but valuable later |
| FIX protocol access | Institutional-grade integration option |
| Fractional shares | Precision position sizing |
| Extended hours trading | Pre-market/after-hours strategies |

---

## 4. Provider Evaluation: Tier 1 — Full Analysis

### 4.1 Alpaca Markets (Incumbent)

**Company overview:** Founded 2015, FINRA/SEC registered since 2018. API-first broker targeting developers and algorithmic traders. Commission-free equities through Payment for Order Flow. Venture-backed (Series C). Headquarters in San Francisco.

#### 4.1.1 Execution Quality

**Order routing model:** Payment for Order Flow (PFOF). SEC Rule 606 reports (Q3 2025) reveal:

- **Routing destinations:** Virtu Financial and Citadel Securities handle all marketable and non-marketable order flow.
- **PFOF rates for marketable orders:** 12 cents per 100 shares, capped at 5 cents per share. This means for a typical ARGUS order of 50–200 shares on a $100–$500 stock, Alpaca receives approximately $0.06–$0.24 per order from the market maker.
- **Non-marketable orders ≥$1:** 20 mils ($0.0020) per share rebate to Alpaca.
- **Extended hours:** Orders routed to Virtu with no payment/rebate.

**What PFOF means for ARGUS:** Market makers (Virtu, Citadel) profit from the spread between what they pay Alpaca's customers and what they can capture in the market. They're legally required to provide NBBO (National Best Bid and Offer) or better, and SEC Rule 605 reports show that most retail orders do receive some price improvement. However, the price improvement on a PFOF broker is structurally less than what direct exchange routing achieves, because the market maker must extract profit from the spread *and* pay PFOF to the broker.

For ARGUS's ORB strategy with 2R profit targets on stocks gapping 2%+, the typical target size is $1–$4 per share. Slippage of a few cents per share from PFOF routing represents approximately 1–5% of the profit target — meaningful but not fatal for initial validation. At scale with tighter strategies (ORB Scalp, 0.3–0.5R targets), PFOF slippage could consume 10–30% of profit targets.

**Verdict:** Acceptable for initial validation with current ORB parameters. Increasingly inadequate as strategies tighten or volume scales.

#### 4.1.2 Reliability & Uptime

**Monitoring data (StatusGator, March–December 2025):** 125+ outages tracked across ~100 components over a 9-month period. This averages to roughly 14 outages per month across the platform. Not all of these affect trading — many involve data endpoints, options snapshots, or non-critical services. However, the volume indicates a platform that experiences frequent service disruptions.

**Notable incidents:**
- December 15–16, 2025: Multiple warning-level incidents.
- November 25, 2025: Last acknowledged outage prior to this report.
- May 2025: Options snapshots degraded for 5+ consecutive days.
- Scheduled monthly maintenance: 2nd Saturday of each month, 9:00–10:00 AM EST. All APIs intermittently unavailable.

**Community evidence:** An Alpaca community forum thread from 2021 documented a user pulling $40,000 from Alpaca after the v1→v2 API migration caused market data and WebSocket failures overnight without warning. While this was five years ago, it illustrates the risk profile of a smaller, venture-backed broker during platform transitions.

**Verdict:** The outage frequency is concerning for a household income system. Individual outages may be brief, but 14+ per month across the platform creates a non-trivial probability of disruption during the critical 9:30–9:45 AM window on any given day. For initial validation (where a missed day is inconvenient, not catastrophic), this is tolerable. For production trading (where missed entries directly reduce income), this is unacceptable.

#### 4.1.3 Regulatory Standing

**SEC enforcement action (September 24, 2024):** Alpaca was fined $400,000 for recordkeeping violations — specifically, pervasive use of unapproved communication channels (off-channel communications) by personnel at multiple authority levels. This was part of a 12-firm enforcement action totaling $88.2 million in penalties. The SEC found willful violation of Section 17(a) of the Securities Exchange Act and Rule 17a-4(b)(4).

**FINRA heightened supervision:** Following the SEC action, Alpaca executed a heightened supervision plan on January 10, 2025. This indicates ongoing regulatory attention.

**Assessment:** The $400K fine is relatively modest and the violation (recordkeeping, not fraud or customer harm) is a common compliance failure across the industry. However, it signals that Alpaca's compliance infrastructure is still maturing. For a household income system, we want a broker with a pristine regulatory record — or at least one where violations are administrative rather than operational.

#### 4.1.4 Commission Structure & Costs

- **Equities:** $0 commission (PFOF model)
- **Regulatory fees (sells only):** SEC fee ($0.00 per $1M principal as of current rate), FINRA TAF ($0.000166/share, capped at $8.30), CAT fee (per-trade)
- **Platform fees:** None
- **Account minimums:** None
- **Data fees:** None for execution (data now handled by Databento separately)

**Cost at ARGUS scale (50 trades/day, 100 shares avg):**  
Direct commissions: $0. Regulatory fees: ~$0.83/day sell-side TAF + negligible SEC/CAT fees. Effective cost: under $1/day in explicit fees. The real cost is the hidden PFOF execution quality tax.

#### 4.1.5 API Quality & Integration

- **SDK:** `alpaca-py` (official, modern, maintained). Clean REST + WebSocket APIs.
- **Authentication:** Simple API key + secret. No OAuth dance.
- **Rate limits:** 200 requests/minute. Adequate for current 5–15 trades/day. At 30+ concurrent strategies, may need careful request batching.
- **Paper trading:** Same API, different base URL. Excellent development experience.
- **Async support:** WebSocket streaming for fills/order updates. REST for order placement and account queries.
- **ARGUS integration:** AlpacaBroker adapter fully built, ~80 tests passing.

**Verdict:** Best-in-class developer experience among retail brokers. The simplest API to integrate with, and ARGUS already has a fully tested adapter.

#### 4.1.6 Multi-Asset Support

- **US Equities:** Full support (stocks + ETFs)
- **Options:** Added recently via API
- **Crypto:** Available through Alpaca Crypto LLC (separate entity, same API)
- **Futures:** Not available
- **Forex:** Not available

**Verdict:** Covers current needs (US equities) and near-term expansion (crypto). Cannot support futures or forex. ARGUS will eventually need a supplementary broker for these asset classes regardless.

#### 4.1.7 Summary Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Execution quality | Adequate (now) / Poor (at scale) | PFOF acceptable for 2R targets; erodes on tighter strategies |
| Reliability | Concerning | 125+ outages in 9 months; tolerable for validation, not production |
| API quality | Excellent | Best developer experience; adapter already built |
| Multi-asset | Partial | No futures or forex |
| Order types | Adequate | Bracket orders with single TP leg; Order Manager compensates |
| Cost structure | Excellent (explicit) / Unknown (implicit) | $0 commissions but hidden PFOF tax |
| Regulatory standing | Acceptable | Recent SEC fine; heightened supervision |

---

### 4.2 Interactive Brokers (Planned for Scaling)

**Company overview:** Founded 1978 by Thomas Peterffy. Interactive Brokers Group (IBKR) is publicly traded (NASDAQ: IBKR), profitable, and self-clearing. Serves institutional and retail clients globally across 150+ exchanges in 200+ countries. The standard-bearer for professional-grade retail and semi-institutional algorithmic trading.

#### 4.2.1 Execution Quality

**Order routing model:** Direct exchange routing via SmartRouting technology. **No Payment for Order Flow on IBKR Pro accounts.** This is the most significant differentiator.

**SmartRouting capabilities:**
- Continuously scans 20+ venues including exchanges, dark pools (8 dark pools integrated), and ECNs.
- Dynamically re-routes orders based on real-time conditions — adapts to microsecond market shifts.
- Multi-leg routing: Each leg of spread orders is independently routed to the best available venue.
- AutoRecovery: Automatically re-routes US options orders when an exchange experiences a malfunction. IBKR assumes the risk of double-execution.
- Customizable routing strategies on Cost Plus (tiered) pricing: highest rebate exchange, listing exchange, highest volume with rebate, lowest fee for liquidity removal.

**Independent verification:**
- BrokerChooser independent testing: 100% price improvement rate.
- TAG (Transaction Auditing Group) measurements: IBKR outperformed the industry for 9 consecutive years (2007–2016) on execution quality metrics.
- Q1 2025 Order Routing Report: 15% year-over-year improvement in price improvement statistics.
- Historical price improvement: 28–53 cents per 100 shares on equities, varying by period.

**SEC Rule 605/606 data:** IBKR Pro accounts show 99.8% execution quality per SEC reports. Because there is no PFOF, all price improvement accrues to the customer rather than being split between customer, market maker, and broker.

**What this means for ARGUS:** On a typical 100-share market order at market open, IBKR's SmartRouting captures approximately $0.02/share more price improvement than PFOF brokers on average. That's $2 per trade, or $10–$30/day at ARGUS's initial volume, and $100–$200/day at scale. Over a year, the execution quality advantage alone could exceed $25,000 — more than paying for commissions and then some.

**Verdict:** Industry-leading execution quality. The clear winner on the most important dimension for ARGUS.

#### 4.2.2 Reliability & Uptime

**Architecture:** Self-clearing, self-custodying broker with its own infrastructure. Not dependent on third-party clearing or execution services.

**Known limitations:**
- **Daily reset:** IB Gateway/TWS performs a nightly system reset, disconnecting all clients. For US accounts, this occurs between 12:15 AM – 1:00 AM ET. This requires reconnection logic in the ARGUS adapter.
- **Gateway session management:** Some developers report periodic disconnections, though these are generally brief and recoverable with proper keep-alive and reconnection logic.
- **TWS version dependency:** API stability can depend on TWS/IB Gateway version. The community recommends using stable releases only.

**Mitigation in ARGUS's context:** The nightly reset occurs well outside market hours (11:00 PM – midnight for ARGUS's ORB window). Reconnection logic is a standard pattern that would be built into the IBKRBroker adapter. The `ib_async` library (successor to `ib_insync`) has automatic reconnection built in.

**Community assessment (QuantConnect):** "Users have long-term stable algorithms for months at a time due to automatic reconnection logic." IB's API has been in production use for algorithmic trading for over two decades — the failure modes are well-understood and well-documented.

**Verdict:** Fundamentally more reliable than Alpaca for production trading. The nightly reset is a known, handled limitation rather than an unpredictable outage. The self-clearing, self-custodying architecture eliminates dependency on third-party infrastructure.

#### 4.2.3 Regulatory Standing

- **Memberships:** NYSE, FINRA, SIPC
- **Regulated by:** SEC, CFTC
- **No recent enforcement actions** found in research
- **Company profile:** Publicly traded (NASDAQ: IBKR), profitable, founded 1978. One of the most established brokerages in the world.
- **SIPC coverage:** Standard $500,000 (including $250,000 cash). IBKR also carries excess SIPC insurance through Lloyd's of London.

**Verdict:** Impeccable regulatory standing. The gold standard for a household income system.

#### 4.2.4 Commission Structure & Costs

**IBKR Pro — Fixed Pricing:**
- $0.005/share, $1.00 minimum per order, 1% of trade value maximum
- For a typical ARGUS trade (100 shares, $200 stock): $0.50 commission

**IBKR Pro — Tiered Pricing (volume-based):**
- 0–300K shares/month: $0.0035/share ($0.35 minimum, 1% maximum)
- Volume tiers scale down to $0.0005/share at 100M+ shares/month
- Additional clearing fee: $0.0002/share
- Exchange fees vary by venue (some rebates offset this)

**IBKR Lite (alternative — NOT recommended for ARGUS):**
- $0 commission for US stocks/ETFs
- Uses PFOF (defeats the purpose of choosing IBKR)
- Limited order types and routing restrictions
- Not suitable for algorithmic trading

**Cost at ARGUS scale (50 trades/day, 100 shares avg, tiered pricing):**
- Commission: ~$0.35 × 50 = $17.50/day
- Clearing: ~$0.02 × 50 = $1.00/day
- Exchange fees: variable, partially offset by rebates
- **Effective cost: ~$20/day** or approximately $5,000/year

**Net cost comparison vs Alpaca:**
- Alpaca explicit cost: ~$1/day
- IBKR explicit cost: ~$20/day
- IBKR execution quality advantage: ~$10–$30/day (estimated $0.02/share × 100 shares × 50 trades)
- **Net: IBKR is cost-neutral or cost-positive** — the execution quality advantage covers or exceeds the commission cost.

**Verdict:** Commissions are modest and are effectively paid for by better execution quality. The math strongly favors IBKR at any meaningful trading volume.

#### 4.2.5 API Quality & Integration

**Official APIs:**
- TWS API: Native support for Java, C++, C#, Python, Visual Basic
- Client Portal API: REST-based web API (newer, simpler, but less full-featured)
- WebSocket streaming for real-time order/fill updates and market data

**Community libraries (Python):**
- `ib_async` (actively maintained successor to `ib_insync`): Asyncio-native Python framework for the TWS API. Provides clean, Pythonic interface over the TWS API's callback complexity. Event-driven with `asyncio` integration — directly compatible with ARGUS's architecture.
- Original `ib_insync` by Ewald de Wit: Production-proven across thousands of algorithmic trading systems. The creator passed away in early 2024; `ib_async` is the community-maintained successor under the `ib-api-reloaded` GitHub organization.

**Architecture compatibility with ARGUS:**
- `ib_async` uses `asyncio` — same as ARGUS's Event Bus and Order Manager
- Event-driven model maps naturally to ARGUS's event-driven architecture
- Automatic state synchronization with TWS/Gateway
- Supports all 100+ order types available through IBKR

**Integration complexity:**
- Requires TWS or IB Gateway running as a local application (Java-based). This adds operational overhead: the ARGUS deployment must include a TWS/Gateway process alongside the Python trading engine.
- Authentication requires a running client session (not simple API key like Alpaca).
- The learning curve is steeper, but ARGUS's `BrokerAbstraction` pattern isolates this complexity.

**Rate limits:** Up to 50 orders per second — orders of magnitude more than ARGUS needs. Market data updates every 250ms minimum, bar updates every 5 seconds (a known limitation that's irrelevant for ARGUS since data comes from Databento).

**Paper trading:** Available via separate paper trading account. Same API, different account credentials.

**Verdict:** More complex to integrate than Alpaca, but `ib_async`'s asyncio-native design aligns perfectly with ARGUS's architecture. The complexity is contained within the IBKRBroker adapter and doesn't leak into the rest of the system.

#### 4.2.6 Multi-Asset Support

- **US Equities:** Full support (stocks, ETFs, fractional shares)
- **Options:** Full OPRA coverage with sophisticated order types (spreads, combos, etc.)
- **Futures:** CME, CBOT, NYMEX, COMEX, ICE, and many more
- **Forex:** Complete coverage — all major and minor pairs
- **Crypto:** Bitcoin, Ethereum, Litecoin, Bitcoin Cash (added 2021)
- **Single account access** across all asset classes

**Verdict:** Complete coverage of ARGUS's entire asset class roadmap (US Stocks → Crypto → Forex → Futures) through a single account and API. No supplementary broker needed for any planned asset class.

#### 4.2.7 Order Types & Capabilities

IBKR supports 100+ order types and algorithms, including:

- Market, Limit, Stop, Stop-Limit, Trailing Stop
- Bracket orders with full multi-leg take-profit
- OCO (One-Cancels-Other), IOC, FOK, GTC
- Algorithmic orders: Accumulate/Distribute (HFT-capable), Adaptive, VWAP, TWAP, Iceberg
- Extended hours trading
- Short selling with comprehensive easy-to-borrow list

**Verdict:** Eliminates the workarounds required by Alpaca's limited bracket order support (single take-profit leg). The Order Manager simplification alone justifies the integration effort.

#### 4.2.8 Summary Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Execution quality | **Excellent** | SmartRouting, no PFOF, 100% price improvement rate |
| Reliability | **Very Good** | Known nightly reset; otherwise robust with decades of production track record |
| API quality | Good (with complexity) | `ib_async` is excellent; requires TWS/Gateway process |
| Multi-asset | **Excellent** | Complete roadmap coverage in single account |
| Order types | **Excellent** | 100+ types; eliminates Order Manager workarounds |
| Cost structure | Good | Commissions offset by execution quality advantage |
| Regulatory standing | **Excellent** | Publicly traded, pristine record, established since 1978 |

---

### 4.3 Tradier (API-First Alternative)

**Company overview:** Founded 2012. FINRA/SIPC member. Headquartered in Charlotte, NC. API-first brokerage targeting developers and options traders. Won "Most Innovative Options Broker" at 2024 Benzinga Fintech Awards. Offers subscription-based pricing model.

#### 4.3.1 Execution Quality

**Order routing:** Tradier's execution quality data is limited in public sources. Their SEC Rule 605/606 reports were not prominently featured in research. The broker appears to use standard retail order routing, likely including PFOF on the free/standard tier, though specifics are less transparent than Alpaca's.

**Verdict:** Insufficient data to assess definitively. The absence of prominent execution quality marketing (unlike IBKR's detailed SmartRouting documentation) suggests execution quality is not a competitive differentiator for Tradier.

#### 4.3.2 Reliability & Uptime

Tradier markets "100% uptime" as a goal, but no independent monitoring data was found. BrokerChooser rated Tradier's customer service 2.5/5 (lowest among top 10 algo brokers reviewed in 2026), which is a proxy concern for issue resolution speed.

**Verdict:** Insufficient independent data to assess. The customer service rating is a red flag for a system that requires rapid issue resolution during market hours.

#### 4.3.3 Commission Structure

**Pricing tiers:**
- **Lite (Free):** $0 per order, $0.35 per options contract. Web + mobile + API access.
- **Pro ($10/month):** Commission-free stocks, equity options, and ETF options. $0.35/contract for index options. Desktop access included.
- **Pro Plus ($35/month):** Everything in Pro, plus $0.10/contract for index options, reduced futures commissions.

**Futures:** Available through Tradier Futures (separate entity, separate application, separate account). Uses Dorman Trading as clearing firm. Requires CQG ($10/month) or Rithmic ($25/month) connection.

**Account note:** $50 annual inactivity fee if account value < $2,000 and < 2 trades/year. International accounts: $20/month inactivity fee if < 2 trades/month.

#### 4.3.4 API Quality

- **Architecture:** REST/JSON API with WebSocket streaming. Simple API key authentication.
- **SDKs:** Native Python and Node.js. Community wrappers (e.g., `uvatradier`) on GitHub.
- **Order types:** Market, Limit, Stop, Stop-Limit, Trailing Stops, OCO. Bracket orders confirmed available.
- **Paper trading:** Sandbox environment available.
- **MCP Server:** Tradier lists an MCP server on their website, suggesting modern AI integration awareness.

**Verdict:** Clean, developer-friendly API. Simpler than IBKR, comparable to Alpaca. However, ARGUS doesn't need another simple API — it needs better execution quality.

#### 4.3.5 Multi-Asset Support

- **US Equities:** Full support
- **Options:** Full support (options-focused broker)
- **Futures:** Available through separate entity/account (Tradier Futures)
- **Forex:** Not confirmed
- **Crypto:** Not confirmed

**Verdict:** Partial coverage. Futures require a separate account. Inferior to IBKR's unified multi-asset model.

#### 4.3.6 Summary Assessment

| Dimension | Rating | Notes |
|---|---|---|
| Execution quality | Unknown | Insufficient public data |
| Reliability | Unknown | No independent uptime data; low customer service rating |
| API quality | Good | Clean REST API, simple auth, comparable to Alpaca |
| Multi-asset | Partial | Futures require separate account; no forex/crypto confirmed |
| Order types | Good | Bracket orders, OCO, trailing stops |
| Cost structure | Good | $10/month for commission-free equities |
| Regulatory standing | Good | FINRA/SIPC member since 2012 |

**Overall verdict on Tradier:** Tradier occupies a middle ground that doesn't serve ARGUS's needs. It offers neither Alpaca's development convenience (adapter already built) nor IBKR's execution quality and multi-asset breadth. For ARGUS, Tradier is a solution in search of a problem — the system has already identified its initial broker (Alpaca) and its production broker (IBKR). Tradier adds no value to this trajectory.

---

## 5. Provider Evaluation: Tier 2 — Quick Assessment

### 5.1 Charles Schwab (TD Ameritrade successor)

**Status:** The legacy TD Ameritrade API was permanently shut down after May 10, 2024 following the Schwab acquisition. Schwab has launched a replacement "Trader API" via developer.schwab.com.

**Key issues for ARGUS:**
- **Authentication requires manual refresh every 7 days.** Schwab's token system does not support indefinite automated refresh — tokens expire after 7 days and must be manually regenerated through a browser-based OAuth flow. This is a dealbreaker for a fully autonomous trading system.
- **New API, immature ecosystem.** The Schwab API launched in 2024 and is still evolving. Community libraries (`schwab-py`) exist but are young compared to IBKR's decades-old ecosystem.
- **No PFOF data available.** Execution quality characteristics of the new platform are not yet well-documented.
- **EasyLanguage/thinkorswim lacks direct API access** for automation.

**Verdict:** Eliminated. The 7-day manual token refresh alone disqualifies Schwab for autonomous algo trading. The immature API ecosystem compounds the problem.

### 5.2 Webull

**Status:** Webull offers an API, but it is primarily designed for mobile-first retail trading. The API capabilities for algorithmic trading are limited and not well-documented.

**Key issues:** PFOF model, limited order types via API, no established algo trading community, reliability data sparse.

**Verdict:** Eliminated. Not designed for the algo trading use case.

### 5.3 TradeStation

**Status:** TradeStation offers a multi-asset RESTful API (v3) supporting equities, futures, and options. Self-clearing broker with direct market access capabilities. Proprietary EasyLanguage for strategy development.

**Key strengths:**
- Execution speed: 0.051 seconds average for equity market orders (Q4 2025). Price improvement on 97% of market orders.
- Multi-asset API (equities, futures, options) from single key.
- Python support via REST API.
- Decade of history in systematic trading community.

**Key issues for ARGUS:**
- **OAuth authentication complexity** (similar to Schwab's model).
- **EasyLanguage dependency** for much of the platform's power — ARGUS needs raw API access, not a proprietary language.
- **$10/month platform fee** (waivable with trading activity).
- **Smaller algo-trading Python ecosystem** compared to IBKR.
- **Self-clearing is a positive**, but IBKR offers the same plus broader multi-asset coverage.

**Verdict:** Credible alternative if IBKR weren't available. TradeStation's execution quality is excellent and its self-clearing architecture is robust. However, IBKR dominates on multi-asset breadth, Python ecosystem maturity, and community depth. TradeStation would be the recommendation if IBKR somehow became unavailable, but as things stand, it's the second-best option on every dimension that matters.

---

## 6. Provider Evaluation: Tier 3 — Dismissed Early

### 6.1 Robinhood
No serious trading API. Mobile-first consumer product. PFOF-only. No bracket orders via API. Dismissed.

### 6.2 E*Trade
API exists but is not designed for algorithmic use cases. Now owned by Morgan Stanley. Authentication complexity. Limited community support for algo trading. Dismissed.

### 6.3 Fidelity
No public trading API. Manual/web trading only. Excellent as a long-term investment brokerage but irrelevant for automated execution. Dismissed.

### 6.4 Emerging/Niche Brokers Sweep

Research included a sweep of r/algotrading, Hacker News, and developer communities for emerging API-first brokers. No new entrants were found that challenge the Alpaca/IBKR/Tradier/TradeStation landscape for US equities. The market data research surfaced Databento as a hidden gem in the data space; no equivalent surprise exists in the execution broker space. The execution brokerage market is more mature and consolidated than the market data market.

---

## 7. Community Evidence & Practitioner Reports

### 7.1 Alpaca Community Sentiment

**Positive signals:**
- TradingView user reviews (2024–2025) consistently praise Alpaca's execution speed and seamless integration. One high-frequency trader running 100+ trades/day reports "trade execution is super fast which reduces slippage."
- BrokerChooser rated Alpaca as the #1 broker for algorithmic trading in the US in 2026, citing developer-friendly API, low fees, and smooth onboarding.
- QuantConnect lists Alpaca as a supported brokerage with commission-free equities.

**Negative signals:**
- An Electronic Trading Hub article documents a practitioner who migrated off Alpaca to TD Ameritrade after the v1→v2 API migration broke WebSocket data feeds overnight with $40K at stake. The author described Alpaca's slippage as noticeably worse than TD Ameritrade for options (though acceptable for equities).
- Alpaca Community Forum posts from users report slow execution speed as a dealbreaker for latency-sensitive strategies.
- Rate limit of 200 requests/minute noted as insufficient for traders wanting to scan the full market.

**Synthesis:** Alpaca is well-suited for early-stage algo traders and development/testing. Its limitations emerge when strategies tighten, volume increases, or reliability becomes mission-critical. This exactly describes ARGUS's trajectory.

### 7.2 Interactive Brokers Community Sentiment

**Positive signals:**
- The algo trading community universally acknowledges IBKR as the standard for production algorithmic trading.
- QuantConnect reports "users have long-term stable algorithms for months at a time" on IBKR.
- The `ib_async`/`ib_insync` ecosystem has been battle-tested across thousands of production trading systems since 2017.
- Multiple GitHub projects (e.g., `mmr` — Python algo trading platform) demonstrate sophisticated production systems built on IBKR's API with asyncio, vectorbt, and real-time tick data.

**Negative signals:**
- The nightly TWS/Gateway reset is a persistent annoyance. Every IBKR algo trader must build reconnection logic.
- IB Gateway session management can be fragile — one developer report describes intermittent disconnections despite following all keep-alive protocols. However, the issue is well-understood and solutions exist.
- The Client Portal API has authentication challenges — some developers report sessions dropping and requiring manual browser-based re-authentication. The TWS API (via `ib_async`) does not have this problem.
- Learning curve is steep. The native TWS API is callback-heavy and unintuitive. `ib_async` exists specifically to solve this problem.
- API bar updates are delayed by 5 seconds (IB-internal processing). This is irrelevant for ARGUS since data comes from Databento, not from IBKR.

**Synthesis:** IBKR's limitations are well-documented, well-understood, and have established workarounds. The platform is battle-hardened over decades of production use. The complexity is real but containable within a well-designed broker adapter.

### 7.3 Key Community Insight

A critical insight from the Electronic Trading Hub article captures the broker landscape perfectly: brokers that offer simple API authentication (Alpaca, Tradier) tend to have execution quality and reliability tradeoffs. Brokers that offer excellent execution quality (IBKR) tend to have API complexity tradeoffs. There is no broker that excels on all dimensions simultaneously. The choice is between ease of development (Alpaca) and quality of execution (IBKR), and the right choice depends on which phase of system development you're in.

ARGUS is transitioning from development phase (where Alpaca's simplicity is correct) to production phase (where IBKR's execution quality is necessary).

---

## 8. Comparative Analysis

### 8.1 Dimension-by-Dimension Comparison

| Dimension | Weight | Alpaca | IBKR | Tradier | TradeStation |
|---|---|---|---|---|---|
| **Execution quality** | Critical | Adequate (PFOF) | **Excellent** (SmartRouting, no PFOF) | Unknown | Excellent |
| **Reliability** | Critical | Concerning (125+ outages) | **Very Good** (known nightly reset, decades of production use) | Unknown | Good |
| **API quality** | High | **Excellent** (simplest) | Good (complex, but `ib_async` helps) | Good | Good |
| **Multi-asset** | High | Partial (no futures/forex) | **Excellent** (complete) | Partial | Good (no forex) |
| **Order types** | Medium | Adequate | **Excellent** (100+) | Good | Good |
| **Cost structure** | Medium | **Excellent** (explicit) | Good (commissions offset by execution) | Good | Good |
| **Account features** | Low | Good | **Excellent** | Good | Good |
| **Regulatory standing** | — | Acceptable | **Excellent** | Good | Good |

### 8.2 ARGUS-Specific Fit Assessment

**For initial live validation and production trading:**
IBKR wins. The original analysis favored Alpaca for initial validation based on path dependency (adapter already built) and time-to-first-trade optimization. On reflection, neither constraint is binding: the adapter build is a 3–5 day sprint, and there's no urgency to go live. With that framing removed, IBKR wins on every dimension — and building directly on the production platform eliminates a migration step, avoids learning two sets of operational quirks, and ensures paper trading validation reflects production fill characteristics.

**Alpaca's permanent role:**
AlpacaBroker adapter remains in the codebase for strategy incubator paper testing. Its excellent developer experience and simple API make it ideal for rapid strategy prototyping where execution quality is irrelevant.

**Tradier and TradeStation both lose** in this framing: neither is better than IBKR for any purpose, and Alpaca fills the strategy-incubator niche better than either.

---

## 9. Decision Framework

### 9.1 The Three Questions, Answered

**Q1: Is Alpaca adequate for initial live trading at minimum size?**

**Yes, but this question is now moot.** Alpaca is adequate for validation-stage live trading with 2R targets on liquid large-caps at minimum position sizes. However, per the revised decision, ARGUS will build the IBKRBroker adapter before going live, making Alpaca's live trading adequacy academic. The analysis below is retained for the record.

**Original assessment (still valid if the decision were reversed):**
- Monitor outage frequency during market open hours (9:30–9:45 AM ET). If outages occur more than once per week during this window, accelerate the IBKR migration.
- Track actual fill prices vs NBBO to quantify the PFOF execution quality tax. If slippage consistently exceeds $0.05/share, accelerate migration.
- Do not scale beyond minimum position sizes or add strategies on Alpaca. It's a validation platform, not a production platform.

**Q2: What is the right long-term execution broker for ARGUS?**

**Interactive Brokers, unambiguously.** IBKR is the terminal destination for every dimension that matters to ARGUS's household income mission: execution quality, reliability, multi-asset coverage, order type depth, regulatory standing, and long-term business stability. The API complexity is a one-time cost (building the adapter) that pays dividends on every subsequent trade.

**Q3: When should the transition happen?**

**Before initial live trading. Build the IBKRBroker adapter as the next Build Track sprint.** The original phased approach (validate on Alpaca first, migrate to IBKR later) optimized for fastest path to first live trade. On reflection, this wasn't the binding constraint — the user is not in a rush to go live, and prefers to learn one broker's operational characteristics rather than two. The revised sequencing:

1. **Now:** Continue Alpaca paper trading while IBKR adapter is built. Begin IBKR account application immediately.
2. **Sprint 12 (Build Track):** Build IBKRBroker adapter (~3–5 days). Test against IBKR paper trading account.
3. **Post-adapter:** Run IBKR paper trading with DEC-076 parameters for 2+ weeks to build confidence.
4. **Live trading gate:** When IBKR paper trading confirms adapter stability + user confidence + CPA consultation → live trading on IBKR at minimum size.
5. **Alpaca's permanent role:** Strategy incubator paper testing platform. AlpacaBroker adapter maintained in codebase.

---

## 10. Final Architecture Decision

### 10.1 Target Execution Architecture

```
Strategy → Risk Manager → Order Manager → BrokerAbstraction
                                              ├── AlpacaBroker  → Alpaca API     [paper trading / validation]
                                              └── IBKRBroker    → IB Gateway     [live production trading]
```

**Both adapters remain permanent fixtures** of the ARGUS codebase. AlpacaBroker is used for paper trading all strategies in the Strategy Incubator pipeline. IBKRBroker is used for all live trading once an adapter passes validation.

### 10.2 Decision Summary

| Decision | Choice | Rationale |
|---|---|---|
| Initial live broker | Interactive Brokers (IBKR Pro, tiered pricing) | Build adapter before live trading; validate on production platform from day one; one learning curve |
| Production live broker | Interactive Brokers (IBKR Pro, tiered pricing) | Best execution quality, reliability, multi-asset, regulatory standing |
| Paper trading broker | IBKR (primary) + Alpaca (strategy incubator) | IBKR for pre-live validation; Alpaca retained for strategy incubator pipeline (PFOF irrelevant for paper) |
| Tradier | Not adopted | No role in the direct-to-IBKR trajectory |
| TradeStation | Not adopted (noted as backup) | Strong broker, but IBKR dominates on all relevant dimensions |
| IBKR adapter timing | Sprint 12 (next Build Track sprint) | Before initial live trading; no time pressure makes direct adoption the cleaner path |

### 10.3 IBKR Account Configuration (Open Immediately)

**Action item: Begin IBKR account application now.** Account approval can take days to weeks. A paper trading account is sufficient to begin Sprint 12 development.

- **Account type:** IBKR Pro (not Lite — Lite uses PFOF)
- **Pricing:** Tiered (not Fixed) — better rates for ARGUS's order profile
- **Market data subscriptions:** None needed for execution (Databento handles all data). May add Level 2 data later if strategies require it.
- **Gateway setup:** IB Gateway (not TWS) for headless server operation. Stable release channel.
- **API library:** `ib_async` (successor to `ib_insync`) for asyncio-native integration

---

## 11. Implementation Implications

### 11.1 Build Track Impact

**IBKRBroker adapter moves to top of Build Track queue.** The original plan deferred the adapter to Sprint 15–16 (after Command Center MVP). The revised decision (direct IBKR adoption, no phased migration) elevates it to Sprint 12:

| Sprint | Content | Status |
|---|---|---|
| **Sprint 12** | **IBKRBroker adapter + IB Gateway integration** | **Next** |
| Sprint 13 | Command Center API layer | Planned |
| Sprint 14 | Command Center React UI | Planned |
| Sprint 15 | Command Center PWA/Tauri | Planned |
| Sprint 16 | Orchestrator V1 | Planned |

The exact sprint number may shift if validation reveals urgency (frequent Alpaca outages during market open), but the adapter is not on the critical path for initial live trading.

### 11.2 IBKRBroker Adapter Scope (Sprint Estimate: 3–5 Days)

Based on the existing `BrokerAbstraction` interface and the `ib_async` library:

1. **Connection management:** IB Gateway connection/reconnection with keep-alive logic
2. **Order submission:** Map ARGUS order types to IBKR order types (market, limit, bracket)
3. **Fill streaming:** Subscribe to order status events via `ib_async` event system
4. **Account queries:** Position, buying power, open order retrieval
5. **Error handling:** Map IBKR error codes to ARGUS error events
6. **Testing:** Comprehensive test suite comparable to AlpacaBroker (~80 tests)

The existing AlpacaBroker test suite serves as a template — most test scenarios transfer directly with only the adapter-specific implementation changing.

### 11.3 Operational Changes for IBKR

- **IB Gateway process:** Must run alongside ARGUS. Deployment scripts need to manage this. Docker container recommended.
- **Authentication:** IB Gateway requires initial credential setup but then maintains session until manual logout or nightly reset.
- **Account funding:** Separate from Alpaca. Wire transfer or ACH to fund IBKR account.
- **Paper trading setup:** IBKR paper trading requires a separate paper account linked to the live account.

### 11.4 Validation Track Impact

Paper trading continues on Alpaca with DEC-076 parameters until the IBKRBroker adapter is built and validated. Once the adapter passes its gate check (Sprint 12), paper trading migrates to IBKR for a minimum 2-week validation period before the live trading gate. This means the Validation Track timeline extends slightly, but the user validates on the same platform they'll trade live — eliminating migration risk and ensuring fill characteristics are consistent between paper and live.

---

## 12. Risk Assessment

### 12.1 Risks of the Recommended Approach (Direct IBKR Adoption)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| IBKRBroker adapter takes longer than estimated | Medium | Low (Alpaca paper trading continues; adapter is not blocking validation) | Use AlpacaBroker test suite as template; `ib_async` simplifies integration |
| IB Gateway operational complexity | Medium | Low (well-documented; Docker containerization simplifies) | Build robust reconnection logic; use stable Gateway release |
| IBKR account opening delays | Low | Medium (blocks paper trading migration to IBKR) | Begin IBKR account application immediately; develop against paper account |
| IBKR paper trading fidelity differs from live | Low | Low (all paper trading has this limitation; IBKR's is well-understood) | Track paper vs live fill characteristics once live trading begins |
| Learning curve on IB Gateway/TWS operations | Low | Low (one-time cost; well-documented by community) | Allocate time for operational familiarization during paper trading period |

### 12.2 Risks of Alternative Approaches

**Risk of the original phased approach (Alpaca live first, IBKR later):**
- Two learning curves instead of one — operational knowledge of Alpaca's quirks becomes throwaway
- Paper trading validation on Alpaca doesn't transfer confidence to IBKR (different fill simulation, latency profile)
- Migration introduces a second high-risk transition after initial live trading is already running
- Alpaca reliability concerns (125+ outages in 9 months) affect live trading, not just paper

**Risk of staying on Alpaca permanently:**
- Execution quality degrades strategy P&L as strategies tighten and volume scales
- Reliability concerns compound as more capital and more strategies flow through Alpaca
- No futures or forex support limits long-term strategy diversification
- VC-backed broker carries inherent business stability risk vs publicly-traded IBKR

### 12.3 Assumption Register

| Assumption | Status | Trigger for Reassessment |
|---|---|---|
| ASM: `ib_async` library is production-stable for order management | Assumed (community evidence) | Test during IBKRBroker adapter development (Sprint 12) |
| ASM: IB Gateway can run reliably in Docker container | Assumed | Test during infrastructure setup (Sprint 12) |
| ASM: IBKR paper trading account can be opened quickly enough to not block Sprint 12 | Unvalidated | Steven begins IBKR account application; if approval > 1 week, start with mock Gateway testing |
| ASM: IBKR tiered pricing nets cost-neutral vs Alpaca after execution quality gains | Estimated | Calculate after 30 days of IBKR live trading |
| ASM: IBKR paper trading fill simulation is representative enough to validate strategy | Assumed | Compare paper vs live fill characteristics once live trading begins |

---

## Appendix A: Pricing Details

### A.1 Alpaca — Cost Model at ARGUS Scale

| Component | Calculation | Daily Cost | Annual Cost |
|---|---|---|---|
| Commission | $0 (PFOF model) | $0 | $0 |
| FINRA TAF (sells) | $0.000166/share × 50 sells × 100 shares | $0.83 | $208 |
| SEC fee (sells) | Negligible at current rates | ~$0 | ~$0 |
| **Explicit total** | | **~$1/day** | **~$250/year** |
| PFOF execution tax (est.) | $0.01–0.05/share × 100 trades × 100 shares | $100–500/day | **$25K–$125K/year** |

Note: The "PFOF execution tax" is the estimated cost of receiving worse price improvement vs direct exchange routing. The wide range reflects uncertainty — actual impact should be measured during initial live trading.

### A.2 IBKR Pro (Tiered) — Cost Model at ARGUS Scale

| Component | Calculation | Daily Cost | Annual Cost |
|---|---|---|---|
| Commission | $0.0035/share × 100 trades × 100 shares | $35 | $8,750 |
| Clearing fee | $0.0002/share × 100 trades × 100 shares | $2 | $500 |
| Exchange fees | Variable, partially offset by rebates | ~$5 | ~$1,250 |
| Regulatory fees | Similar to Alpaca | ~$1 | ~$250 |
| **Explicit total** | | **~$43/day** | **~$10,750/year** |
| Execution quality gain (est.) | $0.02/share × 100 trades × 100 shares | $200/day | **$50,000/year** |
| **Net (cost − gain)** | | **−$157/day** | **−$39,250/year** |

Note: The execution quality gain estimate is based on IBKR's reported average price improvement of $0.02/share vs PFOF brokers. Actual gains will vary. Even at half the estimated advantage, IBKR is cost-positive.

### A.3 Tradier Pro — Cost Model at ARGUS Scale

| Component | Calculation | Monthly Cost | Annual Cost |
|---|---|---|---|
| Subscription | Pro plan | $10 | $120 |
| Commission | $0 (equities on Pro plan) | $0 | $0 |
| Regulatory fees | Similar to Alpaca | ~$25 | ~$300 |
| **Total** | | **~$35/month** | **~$420/year** |

---

## Appendix B: Regulatory Filings & Source Material

### B.1 Key Sources Consulted

**Alpaca Markets:**
- SEC Rule 606 Report (Q3 2025): Order routing destinations, PFOF rates
- SEC Administrative Proceeding (September 24, 2024): $400,000 fine for recordkeeping violations
- FINRA BrokerCheck: Heightened supervision plan (January 10, 2025)
- StatusGator monitoring data (March–December 2025): 125+ outages across ~100 components
- Alpaca Community Forum: User experience reports on execution speed and API stability
- TradingView verified reviews: Recent user satisfaction data

**Interactive Brokers:**
- SEC Rule 605/606 data: 99.8% execution quality
- IBKR SmartRouting documentation: 20+ venues, dynamic re-routing, dark pool integration
- TAG (Transaction Auditing Group) independent audit: 9 consecutive years of outperformance
- Q1 2025 Order Routing Report: 15% YoY improvement in price improvement
- BrokerChooser independent testing: 100% price improvement rate
- `ib_async` GitHub repository (ib-api-reloaded): API documentation, community activity
- QuantConnect Forum: Long-term algo stability reports

**Tradier:**
- Official pricing page: Subscription tiers, commission structure
- TradingView broker reviews: User satisfaction data
- BrokerChooser review: 2.5/5 customer service rating
- Tradier Futures documentation: Separate entity/account structure

**TradeStation:**
- Official API documentation (api.tradestation.com)
- QuantVPS execution speed benchmarks: 0.051s average equity market orders (Q4 2025)
- Investopedia/StockBrokers.com reviews: Execution quality rankings

**Charles Schwab / TD Ameritrade:**
- schwab-py documentation: 7-day token refresh limitation
- Schwab Developer Portal: Trader API specifications
- Community migration reports: TDA API shutdown timeline

**Community sources:**
- Electronic Trading Hub: Comprehensive brokerage comparison from practitioner perspective
- r/algotrading community: General consensus on broker selection
- BrokerChooser 2026 algo trading broker rankings
- AlgoTrading101: `ib_insync` and IBKR API guides

---

*End of Report — February 20, 2026*
