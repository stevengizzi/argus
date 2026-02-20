# ARGUS — Market Data Infrastructure Research Report

> **Document Type:** Research Deep Dive — Archaeological Record  
> **Date Range:** February 18–20, 2026  
> **Status:** Final  
> **Author:** Steven (project owner) with Claude (AI co-captain)  
> **Classification:** Internal Reference — ARGUS Project  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Catalyst](#2-research-catalyst)
3. [ARGUS Vision & Requirements](#3-argus-vision--requirements)
4. [The US Market Data Landscape](#4-the-us-market-data-landscape)
5. [Provider Evaluation: Tier 1 — Seriously Considered](#5-provider-evaluation-tier-1--seriously-considered)
6. [Provider Evaluation: Tier 2 — Evaluated and Eliminated](#6-provider-evaluation-tier-2--evaluated-and-eliminated)
7. [Provider Evaluation: Tier 3 — Dismissed Early](#7-provider-evaluation-tier-3--dismissed-early)
8. [Community Evidence & Practitioner Reports](#8-community-evidence--practitioner-reports)
9. [Comparative Analysis](#9-comparative-analysis)
10. [The Full-Universe Question](#10-the-full-universe-question)
11. [The Strategy Research Laboratory Reframe](#11-the-strategy-research-laboratory-reframe)
12. [Decision Evolution](#12-decision-evolution)
13. [Final Architecture Decision](#13-final-architecture-decision)
14. [Implementation Implications](#14-implementation-implications)
15. [Risk Assessment](#15-risk-assessment)
16. [Appendix A: Pricing Details](#appendix-a-pricing-details)
17. [Appendix B: Source Material](#appendix-b-source-material)

---

## 1. Executive Summary

This report documents a three-day research process (February 18–20, 2026) evaluating market data providers for the ARGUS automated day trading system. The research was triggered by the discovery that Alpaca's free-tier IEX data feed captures only 2–3% of actual US equity market volume, rendering live trading unreliable.

What began as a simple "which data provider should we use?" question evolved into a fundamental reexamination of ARGUS's system identity and data architecture. Through iterative analysis across two conversation sessions, the provider recommendation reversed from its initial direction:

- **Session 1 (Feb 19):** Recommended IQFeed as primary backbone, Databento as supplemental precision source.
- **Session 2 (Feb 19–20):** After deeper analysis of Databento's capabilities and a critical reframing of ARGUS's use case as a "strategy research laboratory that also trades live," the recommendation reversed to Databento as primary equities backbone, IQFeed as supplemental for specific capabilities Databento lacks.

**Final Decision:** Databento US Equities Standard ($199/month) as the primary equities data backbone, with IQFeed added later for forex, news feeds, and breadth indicators. Alpaca retained for order execution only.

---

## 2. Research Catalyst

### 2.1 The IEX Discovery (DEC-081, February 18, 2026)

During paper trading validation on February 18, 2026, ARGUS successfully connected to Alpaca's WebSocket market data feed and began streaming data for the configured watch list (NVDA, AMZN, GOOGL, MSFT, NFLX, AAPL). The connection was stable and bars were being delivered, but the data quality was problematic: most 1-minute bars were either missing entirely or built from a tiny fraction of actual trades.

Investigation revealed the root cause: Alpaca's free Basic plan only provides IEX (Investors Exchange) data, which represents approximately 2–3% of total US equity volume. IEX is a single exchange among 15+ US equity exchanges and 30+ Alternative Trading Systems (ATSs). For a stock like NVDA trading millions of shares per minute at market open, the IEX feed might capture only a few hundred shares — producing candles that bear little resemblance to the actual market.

This was documented as Decision DEC-081 (IEX Data Feed Limitation Acknowledged) and Risk RSK-021 (Data Quality Risk) in the ARGUS project documentation.

### 2.2 Why Not Just Upgrade Alpaca?

The obvious fix was to upgrade to Alpaca's SIP (Securities Information Processor) data tier at $99/month, which provides the full consolidated tape from all exchanges. This option was evaluated and rejected for several reasons:

1. **Alpaca is an execution broker, not a data company.** Their core business is order routing and brokerage services. Market data is a pass-through offering, not their primary product. Data reliability and feature depth will always be secondary priorities.
2. **Single point of failure.** Using the same provider for both data and execution means a single Alpaca outage takes down the entire system.
3. **Feature limitations.** Even with the SIP upgrade, Alpaca provides no Level 2 market depth data, no news feeds, no breadth indicators, no historical tick data beyond a limited window, and no forex or futures data through the same API.
4. **Symbol limits.** Alpaca's WebSocket data feed limits subscribers to 1,000 symbols simultaneously.
5. **Strategic misalignment.** ARGUS's long-term vision (detailed in Section 3) requires capabilities far beyond what any brokerage data feed can provide.

Steven made the strategic call to evaluate the full landscape of dedicated market data providers rather than apply a band-aid to the immediate problem. This proved to be the right decision, as it surfaced fundamental questions about ARGUS's architecture and identity.

### 2.3 Research Timeline

| Date | Event |
|------|-------|
| Feb 14–16 | Phase 1 complete (362 tests). Paper trading begins on Alpaca. |
| Feb 17 | Paper trading sessions reveal data quality issues. Enum conversion bugs fixed. |
| Feb 18 | IEX data limitation diagnosed and documented (DEC-081). |
| Feb 19 (Session 1) | Comprehensive provider evaluation. 6+ providers analyzed. IQFeed recommended as primary. Report drafted (argus_market_data_report.md). |
| Feb 19–20 (Session 2) | Databento deep dive. Full-universe analysis. Vision reframed as "strategy research laboratory." Recommendation reversed to Databento-primary. |
| Feb 20 | Final report (this document) produced. |

---

## 3. ARGUS Vision & Requirements

During the first research session (February 19), Steven articulated several requirements that had not been fully captured in existing project documentation. These emerged organically as the data provider analysis forced examination of what ARGUS actually needs to become.

### 3.1 Household Income Mission

Steven stated: *"I want ARGUS to be the one-stop shop that can support my entire household income through autonomous action. I want it to become a powerhouse of a trading program, deploying multiple different strategies across different asset classes, different time scales, different resolutions, different risk profiles."*

This elevates ARGUS from a side income tool to a primary income generator. The reliability, risk management, and data quality standards must match this mission. System downtime during market hours is lost income. Data quality issues are financial losses.

### 3.2 Sub-Minute Trading Resolution

Steven stated: *"I want ARGUS to be capable of day trading with a smaller resolution than minutes. I want to be able to deploy strategies that rely on trades that get in and out in a matter of seconds."*

The system must support tick-level data ingestion and strategies that execute at whatever speed the strategy demands — no artificial floor on hold duration. The design principle is: **no artificial constraints on trade resolution.**

### 3.3 Multi-Asset Flexibility

Steven stated: *"If I need to switch from stocks to futures during a certain market turn to ensure profitability, so be it. We need the system to be robust."*

The multi-asset roadmap (US Stocks → Crypto → Forex → Futures) is a core requirement for the income mission, not a nice-to-have expansion plan.

### 3.4 Full-Market Scanning

ARGUS should not be limited to scanning 20–50 symbols. Different strategies work best in different sectors and market cap ranges. The pre-market scanner must be capable of screening the entire US equity market (~8,000+ actively traded symbols) to find optimal candidates for each active strategy.

### 3.5 Level 2 Market Depth

Analysis established that L2 (market depth) data is valuable for planned strategies — particularly for sub-second entry execution quality, stop loss management, breakout confirmation, and futures trading. L3 (full order-by-order) data is overkill for current timeframes. The recommendation: design for L2 from the start, leave L3 as a future option.

### 3.6 Data-First Backtesting Philosophy

A quote from a Reddit practitioner resonated strongly with Steven: *"Once you're struck with inspiration, the last thing you want to do is spend your day writing code for getting or massaging data. You want this in place and ready to rock on your hypothesis."*

The data infrastructure should cover all asset classes and timeframes before strategies are built for them. When Steven has an idea at 2 AM, he should be able to pull data and run a backtest that same session.

### 3.7 The Strategy Research Laboratory (Session 2 Reframe)

In the second session (February 19–20), Steven crystallized the vision further:

*"My thought is that I don't even know how effective my current ORB strategy is, or how much I'll use it. It may be extremely useful, or it may just be a placeholder strategy. I know that even with paper trading, as soon as I start seeing trades being made, and real P/L, I'm quickly going to be gripped by a desire to experiment with multiple strategies, fine-tuning all the variables, determining the optimal conditions for many different strategies, in different sectors, at different time intervals. I am going to want the ability to take a strategy and test it across the entire universe of stocks to see where it performs the best. I can imagine wanting to actively run 30+ strategies in real-time on paper trading, on live market data, to see which ones perform the best over time."*

This statement was the pivotal moment in the research. It reframed ARGUS from "a trading system that needs data" to "a strategy research laboratory that also trades live." The implications for data provider selection were immediate and decisive.

---

## 4. The US Market Data Landscape

### 4.1 How US Equity Market Data Works

Understanding the provider landscape requires understanding how market data is generated and distributed in the US:

**Exchanges:** There are 15 registered US equity exchanges (NYSE, NASDAQ, Cboe BZX/BYX/EDGA/EDGX, IEX, MEMX, MIAX Pearl, LTSE, etc.) plus 30+ Alternative Trading Systems (ATSs, also known as dark pools). Each exchange generates its own proprietary data feed with all orders, trades, and quotes on that venue.

**The SIP (Securities Information Processor):** The Consolidated Tape Association (CTA) and Unlisted Trading Privileges (UTP) plan operate the SIPs, which consolidate data from all exchanges into a single feed. The SIP calculates the National Best Bid and Offer (NBBO), Limit Up/Limit Down bands, and provides the official consolidated trade stream. SIP data is the regulatory standard — brokers must execute at NBBO or better.

**Proprietary Feeds vs. SIP:** Direct exchange proprietary feeds are faster (fewer network hops) and richer (full depth of book, odd lot quotes, auction imbalance data) than SIP, but more expensive and complex to integrate. SIP is simpler but L1-only and has an additional network hop through the consolidation process.

**Data Levels:**
- **L0:** Aggregates — OHLCV bars, end-of-day summaries
- **L1:** Top-of-book quotes (NBBO) and trade-by-trade data
- **L2:** Market depth — multiple price levels showing the order book at each exchange
- **L3:** Full order-by-order data — every add, cancel, modify at each exchange

### 4.2 What ARGUS Needs

Based on the vision requirements in Section 3:

| Requirement | Minimum | Ideal |
|---|---|---|
| Symbol coverage | 500+ active candidates | Full universe (8,000+) simultaneously |
| Data resolution | 1-minute bars | Tick-by-tick (every trade, every quote) |
| Market depth | L1 (NBBO) | L2 (10-level depth per exchange) |
| Asset classes | US equities | Equities + futures + forex + options |
| Historical depth | 3+ years bars | 7+ years bars, 1+ year ticks |
| Latency | < 1 second | < 100 milliseconds |
| News | Earnings calendars | Real-time news with classification |
| Reliability | 99.9% during market hours | 99.99% with redundancy |

---

## 5. Provider Evaluation: Tier 1 — Seriously Considered

These providers received full analysis because they met the minimum bar of data quality, API capability, and cost feasibility.

### 5.1 Databento

**Company profile:** Series A startup founded 2019 in Boston. $37.5M total funding. ~$8M annual revenue. ~38 employees. Backed by Redpoint Ventures, Belvedere Trading, and others. Engineering team includes former trading firm infrastructure engineers.

**Data sourcing:** All US equities data sourced from direct exchange proprietary feeds — not SIP. Databento consolidates feeds at their colocation facility in Equinix NY4, providing lower latency and richer data than SIP (odd lot quotes, full depth, auction imbalance, accurate trade signs). They construct a synthetic NBBO from the proprietary feeds rather than passing through the SIP NBBO.

**Coverage (as of February 2026):**
- US Equities: 15 exchanges + 30 ATSs, 21,000+ products, 3M+ symbols
- Futures: CME Group (CME, CBOT, NYMEX, COMEX) — separate dataset/subscription
- Options: OPRA (all 17 US equity options exchanges) — separate dataset/subscription
- European: ICE Futures Europe, ICE Endex, Eurex — separate datasets
- Forex: NOT AVAILABLE (on public roadmap as feature request, no timeline)
- News: NOT AVAILABLE
- Breadth indicators: NOT AVAILABLE

**Symbol limits:** None. Subscribe to entire exchange universe in a single API call.

**Data schemas available:** MBO (L3, full order book), MBP-10 (L2, 10-level depth), MBP-1 (L1, top of book), TBBO (trade-attached BBO), trades, OHLCV bars (1s, 1m, 1h, 1d), instrument definitions, auction imbalance, and statistics.

**API quality:** Official Python client library with full async support. Also Rust and C++ clients. Raw TCP protocol for lowest latency. Historical and live APIs share the same data structures, enabling identical code for backtest and live. Nanosecond-resolution timestamps.

**Performance:** 6.1-microsecond normalization latency. 99.99% uptime. 90th percentile delivery latency: 42μs (cross-connect) or 590μs (internet). Historical replay at 19.2M ticks/second.

**Session limits:** 10 simultaneous live sessions per dataset on Standard plan. 50 on Plus/Unlimited. A "session" is a TCP connection. Each session can subscribe to unlimited symbols. Databento recommends a middleware fan-out architecture (one connection, distribute internally) rather than one-session-per-consumer.

**Pricing (US Equities Standard, as of January 2025):**
- Monthly: $199/month
- Includes: Unlimited live streaming, 15+ years OHLCV history, 12 months L0/L1 history, 1 month L2/L3 history
- Additional historical data beyond included windows: pay-as-you-go
- No exchange license fees for personal non-display use

**Known issues and limitations:**
- Synthetic NBBO rather than actual SIP NBBO (practically equivalent for all but the most latency-sensitive HFT applications)
- Historical API outage on February 8, 2026 (memory limits from traffic spike)
- Intraday replay window temporarily reduced from 24h to 10h on February 5, 2026 due to disk space from elevated market activity
- Feed timing inconsistencies noted: Nasdaq TotalView-ITCH B-side can lag A-side, requiring robust packet handling
- Occasional mismatches between data and official exchange statistics
- No forex, no news, no breadth indicators

**Strengths for ARGUS:** No symbol limits (critical for strategy research laboratory), modern Python API (faster adapter development), full L1–L3 through single API, on-demand historical queries, $199/month flat rate for full universe.

**Weaknesses for ARGUS:** No forex (blocks multi-asset expansion), no news (blocks Tier 2 catalyst system), no breadth indicators (limits market regime classification), VC-funded startup (business continuity risk), per-dataset cost stacking for multi-asset ($199 equities + $179 CME + $199 OPRA = $577+/month before reaching multi-asset coverage).

### 5.2 IQFeed (DTN)

**Company profile:** Owned by DTN (now part of TelVista), operating since the early 2000s. Over 20 years of track record. Profitable, established business. Quad-redundant data center infrastructure.

**Data sourcing:** SIP consolidated data (actual CTA/UTP feed) for equities. Direct exchange feeds for futures. Professional-grade data processing infrastructure with 20+ years of refinement.

**Coverage:**
- US Equities: Full SIP consolidated data, L1 + L2 (market depth)
- Futures: CME, CBOT, NYMEX, COMEX, ICE, and others
- Options: Full OPRA coverage
- Forex: Complete coverage (unique advantage — the only provider in this evaluation with forex)
- News: Benzinga Pro included (real-time financial news with classification)
- Breadth indicators: 700+ market internals (TICK, TRIN, advance/decline, etc.)
- Historical: 180 days of tick data, 11+ years of 1-minute bars, 80+ years of daily data

**Symbol limits:** 500 simultaneous symbols on base plan. Expandable to 2,500 with add-on packs ($24.50–$49/month per 500-symbol pack). This is a hard architectural ceiling — no amount of spending breaks the 2,500 limit.

**API:** Socket-based TCP protocol. No official Python client; community library (pyiqfeed) available. Requires IQConnect.exe gateway process, which runs on Windows only — Linux deployment requires Wine + xvfb in a Docker container (production-proven pattern, community Docker images available).

**Performance:** Professional-grade latency, comparable to other SIP data vendors. Not as fast as Databento's exchange-direct feeds, but more than adequate for ARGUS's non-HFT strategies.

**Pricing (as of December 2025):**
- Base service: $83/month (equities, basic futures, news, 500 symbols)
- Exchange fees: $10–40/month depending on exchanges
- Symbol expansion: $24.50–49/month per 500-symbol pack
- Estimated total for ARGUS equities-only: ~$123/month
- Estimated total for full multi-asset vision: ~$480–540/month

**Strengths for ARGUS:** All asset classes in one platform (including forex — unique), included Benzinga news (Tier 2 catalyst system), 700+ breadth indicators (market regime classification), actual SIP consolidated data, 20+ years of proven reliability, deep historical data archive, profitable and stable company.

**Weaknesses for ARGUS:** 2,500 symbol hard cap (fatal ceiling for strategy research laboratory), requires Wine/Docker on Linux (operational complexity), older TCP socket API (more development effort for adapter), no official Python client, no symbol-unlimited scanning capability.

### 5.3 Alpaca SIP Upgrade

**What it is:** Upgrading from Alpaca's free IEX data to their SIP (full consolidated) tier at $99/month.

**Evaluated as:** A short-term bridge to unblock paper trading while building a permanent data provider adapter.

**Decision:** Rejected. Development velocity with ARGUS (entire phases completed in 2–3 days) means a proper data adapter can be built in the same time it would take to set up, validate, and later tear down an Alpaca SIP bridge. Building the bridge means two validation cycles and a throwaway subscription for perhaps 3–5 days of head start. Better to go straight to the long-term solution.

---

## 6. Provider Evaluation: Tier 2 — Evaluated and Eliminated

### 6.1 Polygon.io

**Why considered:** Popular in the algo-trading community. REST and WebSocket APIs. Pay-as-you-go pricing.

**Why eliminated:**
- Community reports of significant data quality issues: delayed trades, stream freezes lasting 3+ minutes during high-volume periods, data losses during market open (the exact window ORB strategies need).
- One practitioner's measured latency test: "There were moments where Polygon froze for 3 minutes. Can't explain it."
- Polygon's own CEO acknowledged scaling issues in Reddit responses.
- Another report: "Polygon throttles requests to 300 per minute. For 200 tickers that means you get updated quotes and trades once every 40 seconds."
- Professional quant assessment: Polygon has "the worst quality issues."
- Pricing: $199/month for Starter with real-time access. Comparable to Databento but with worse reported reliability and quality.

**Verdict:** Unacceptable reliability for a household income system. Eliminated.

### 6.2 Tradier

**Why considered:** Brokerage with data API access.

**Why eliminated:** Provides only one-sided quotes for real-time options feeds (confirmed by practitioner thicc_dads_club on Reddit). Incomplete data for any serious analysis. Eliminated.

### 6.3 Yahoo Finance / yfinance

**Why considered:** Free, widely used in backtesting community.

**Why eliminated:** Survivorship bias (only currently listed tickers), significant price inaccuracies on 1-minute timeframe (practitioner report: "$100+ moves in a single candle for TSLA trading at $200"), rate limiting, not suitable for real-time streaming, no L2 data. Useful for preliminary research only. Eliminated.

---

## 7. Provider Evaluation: Tier 3 — Dismissed Early

### 7.1 Bloomberg Terminal

**Why dismissed:** $24,000/year per terminal. Designed for institutional users with teams of analysts. API (BLPAPI) optimized for portfolio management, not algorithmic execution. Wildly disproportionate to ARGUS's needs.

### 7.2 Refinitiv (LSEG)

**Why dismissed:** Enterprise-grade pricing ($5,000–25,000+/month). Legacy infrastructure. Slow onboarding (weeks of enterprise sales process). Not accessible to individual traders.

### 7.3 Direct Exchange Feeds / Colocation

**Why dismissed:** Subscribing directly to each exchange's proprietary feed (NYSE XDP, NASDAQ TotalView-ITCH, Cboe PITCH, etc.) from a colocated server at Equinix NY4. Cost: $10,000–100,000+/month between exchange fees, colocation, network, and hardware. Requires C++/Rust feed handlers — Python cannot keep up with raw exchange firehose rates. This is what HFT firms do. Wildly disproportionate to ARGUS's needs.

### 7.4 Quandl / Nasdaq Data Link

**Why dismissed:** Primarily daily/end-of-day data. No real-time tick streaming. Unsuitable for intraday trading system.

### 7.5 Alpha Vantage

**Why dismissed:** Rate-limited free tier. Paid tiers still limited. Data quality reports inconsistent. Not suitable for real-time streaming at scale.

---

## 8. Community Evidence & Practitioner Reports

Reddit threads from r/algotrading, r/quant, and related subreddits were analyzed as primary sources during this research. The following summarizes key practitioner reports that informed the evaluation.

### 8.1 Professional Quant Assessment (r/quant)

A quant working at a fund provided a comprehensive provider ranking across institutional, HFT, and retail tiers. Key assessment:

- **Databento:** "Overall the best API, support, and value today. Very easy to use. Limited exchange coverage and history."
- **IQFeed:** Consistently ranked in the top tier for retail/individual algo traders across multiple threads.
- **Polygon.io:** "The worst quality issues."

### 8.2 Databento User Reports

**Phunk_Nugget (1 year ago):** Uses Databento for L1 bid/ask/trade data, injects into simulation exchange for event-driven backtesting. Controls simulated latency for fills. Uses "super efficient custom storage formats" because "data size is huge." This workflow closely mirrors ARGUS's Replay Harness architecture.

**laukax (1 year ago):** Tried Databento but had two issues: (1) doesn't provide L2 data from all exchanges (note: coverage has since expanded significantly), (2) uncertainty about which dataset to select. Uses live-recorded data from scanner candidates instead, serialized as pickled class instances. Notes that loading speed matters more than compression ratio.

**thicc_dads_club (7 months ago):** Uses Databento at $199/month for options. Receives approximately 150,000 quotes per second with latency under 20ms to Google Cloud. Previously used Polygon for historical and live, migrated to Databento for live due to better quality and reliability. Confirmed Databento provides "every quote" — much higher volume than competing providers.

**DatabentoHQ (official, 7 months ago):** Confirmed their daily files for options quotes run "closer to 700 GB compressed, not 100 GB" because they publish every quote rather than subsampled data. Noted that their historical data has been "quite solid since changes made in June [2025]" and that "some of the options exchanges even use our data for cross-checking."

### 8.3 IQFeed User Reports

Multiple threads consistently praised IQFeed's reliability and data quality. No substantive complaints about data accuracy or stream stability were found across the analyzed threads. The primary complaints were about the Windows-only IQConnect.exe requirement (solved with Wine/Docker on Linux) and the older API paradigm (socket-based TCP vs modern REST/WebSocket).

### 8.4 Polygon User Reports

**Adderalin (r/algotrading):** Measured latency data from colocated NJ machine showed concerning performance characteristics.

**slayerofcables:** Reported stream freezes lasting multiple minutes.

**MichaelMach:** Reported request throttling that made real-time multi-symbol scanning impractical (300 requests/minute cap means 200 tickers updated once every 40 seconds).

---

## 9. Comparative Analysis

### 9.1 Head-to-Head: Databento vs. IQFeed

This is the core comparison, as these were the only two providers that survived full evaluation.

| Dimension | Databento | IQFeed | Winner |
|---|---|---|---|
| **Symbol limits** | None — full universe | 2,500 max (hard cap) | **Databento** |
| **Data source** | Exchange proprietary feeds (synthetic NBBO) | SIP consolidated (official NBBO) | Draw (both adequate) |
| **L1 data** | Full tick-by-tick | Full tick-by-tick | Draw |
| **L2 data** | Per-exchange depth (MBP-10) | Consolidated L2 | **IQFeed** (simpler) |
| **L3 data** | Full order-by-order (MBO) | Not available | **Databento** |
| **US equities coverage** | 15 exchanges + 30 ATSs | All via SIP | Draw |
| **Futures** | CME Group (+$179/mo) | CME, ICE, more (included in base+exchange) | **IQFeed** (simpler pricing) |
| **Options** | OPRA (+$199/mo) | OPRA (included in base+exchange) | **IQFeed** (simpler pricing) |
| **Forex** | NOT AVAILABLE | Complete coverage | **IQFeed** (unique) |
| **News** | NOT AVAILABLE | Benzinga Pro included | **IQFeed** (unique) |
| **Breadth indicators** | NOT AVAILABLE | 700+ (TICK, TRIN, A/D, etc.) | **IQFeed** (unique) |
| **Historical bars** | 15+ years OHLCV, 12mo L1 (Standard) | 80+ years daily, 11+ years 1-min | **IQFeed** |
| **Historical ticks** | 1 month L2/L3 (Standard) | 180 days tick | **IQFeed** |
| **Python API** | Official async client library | Community pyiqfeed (TCP sockets) | **Databento** |
| **Linux support** | Native | Wine + xvfb Docker required | **Databento** |
| **Latency** | 42μs (cross-connect), 590μs (internet) | Professional SIP-grade | **Databento** |
| **Timestamps** | Nanosecond (PTP-synced) | Millisecond | **Databento** |
| **Company stability** | VC-funded startup, ~$8M revenue | 20+ year profitable company | **IQFeed** |
| **Live session limits** | 10 per dataset (Standard) | Unlimited connections | **IQFeed** |
| **Equities-only cost** | $199/mo | ~$123/mo | **IQFeed** |
| **Full multi-asset cost** | $577+/mo (no forex, no news) | ~$480–540/mo (everything) | **IQFeed** |
| **Full-universe equities** | $199/mo | Not achievable at any price | **Databento** |

### 9.2 Cost Comparison for Different Configurations

| Configuration | Databento | IQFeed | Notes |
|---|---|---|---|
| US equities only, base | $199/mo | $123/mo | IQFeed cheaper by $76/mo |
| US equities with full-market scanning | $199/mo | $248–373/mo | IQFeed requires 3–4 symbol packs and still caps at 2,500 |
| US equities + CME futures | $378/mo | $226–266/mo | IQFeed cheaper for this combo |
| Full multi-asset (equities + futures + options) | $577+/mo | $480–540/mo | IQFeed cheaper AND includes forex/news |
| Databento equities + IQFeed supplemental | $299–449/mo | — | Best of both: unlimited symbols + forex/news |

---

## 10. The Full-Universe Question

A critical question emerged during the second research session: *"What would I have to do to get full access to the entire universe of stocks, at sub-second real-time resolution, with full L1/L2 coverage?"*

### 10.1 Scale of the Requirement

"Full universe" means:
- ~8,000+ actively traded US equity symbols across 15 exchanges and 30+ ATSs
- Tick-by-tick streaming (every trade, every quote change)
- L1 (NBBO consolidated) + L2 (market depth)
- Data volume: millions of messages per second at peak, tens of GB per day compressed

### 10.2 Three Realistic Paths

**Path 1: Databento US Equities Standard — $199/month.**
The most straightforward path. Subscribe to entire universe in single API call. All L1/L2/L3 schemas available. No symbol limits, no exchange license fees for personal non-display use. Modern Python client. This is the "just give me everything" option for US equities.

**Path 2: IQFeed — Tiered Scanning Architecture (Cannot Do Full Universe).**
Maximum 2,500 simultaneous symbols with full expansion. Requires architectural workaround: snapshot full universe via historical/REST API, apply scanner filters, stream only filtered candidates in real-time. Dynamic rotation of symbol slots based on scanning results. Covers 30–60% of actively traded universe at any given moment. Workable but architecturally constrained.

**Path 3: Direct Exchange Feeds / Colocation — $10,000–100,000+/month.**
Subscribe to each exchange's proprietary feed directly. Colocate at Equinix NY4. Process raw binary protocols at wire speed. Full L1/L2/L3 from every exchange, every symbol, every nanosecond. Requires C++/Rust feed handlers. Wildly disproportionate to ARGUS's needs.

### 10.3 Implications for Architecture

The full-universe question has direct implications for the 30+ strategy vision. If each strategy watches 100 candidate symbols, 30 strategies collectively need ~3,000 unique symbols (before overlap). Add a full-market scanner running in the background and the total exceeds IQFeed's 2,500 hard cap.

Databento has no such limit. One API call, subscribe to everything. This is what makes it the natural backbone for a strategy research laboratory.

---

## 11. The Strategy Research Laboratory Reframe

### 11.1 The Pivotal Insight

The most important moment in this research was Steven's articulation of how he envisions using ARGUS (see Section 3.7). The key phrase: *"I can imagine wanting to actively run 30+ strategies in real-time on paper trading, on live market data, to see which ones perform the best over time."*

This description reframes the system's primary identity. ARGUS is not "a trading system that needs data." It is "a strategy research laboratory that happens to also trade live."

### 11.2 What This Means for Data Architecture

A trading system needs reliable data for the symbols it's currently trading. A strategy research laboratory needs:

- **Unlimited symbol access:** Test any strategy against any universe of symbols at any time
- **On-demand historical data:** Pull data for any symbol/date range/schema when inspiration strikes
- **Concurrent strategy execution:** Run dozens of strategies simultaneously on live data
- **Rapid iteration:** Spin up a paper strategy Monday, kill it Friday if it underperforms
- **Data as a non-bottleneck:** The limiting factor should be idea quality, not data access

IQFeed's 2,500 symbol cap is an architectural ceiling that directly constrains this workflow. Databento's unlimited access enables it without compromise.

### 11.3 How This Reversed the Recommendation

The initial recommendation (IQFeed primary, Databento supplemental) was sound for the requirements as they stood in Session 1, where the focus was on getting the current ORB strategy running with reliable data. IQFeed's all-in-one coverage (equities + futures + forex + news) and proven reliability made it the natural choice for a trading system.

But the strategy research laboratory framing changes the calculus. The single most valuable property of a data provider for a research laboratory is breadth of access — the ability to explore without constraints. Databento delivers this for US equities at $199/month with no architectural ceilings. IQFeed's superior all-in-one coverage becomes supplemental rather than primary, because the things IQFeed provides that Databento doesn't (forex, news, breadth indicators) are add-on capabilities rather than the core foundation.

---

## 12. Decision Evolution

This section documents how the recommendation changed through the research process, and why.

### 12.1 Initial State (Pre-Research)

ARGUS used Alpaca for both data and execution. Data came from the free IEX feed. No separate data provider was planned. This was adequate for early development but inadequate for live trading.

### 12.2 Session 1 Recommendation (February 19, Morning)

**IQFeed as primary backbone, Databento as supplemental.**

Rationale: IQFeed provides everything — equities, futures, forex, options, news, breadth indicators — through one platform with 20+ years of proven reliability. The 500-base/2,500-expanded symbol limit was manageable through a tiered scanner architecture. Databento was positioned as a precision supplement for L3 data and nanosecond analysis when specific strategies required it.

This was documented in argus_market_data_report.md and proposed as DEC-082.

### 12.3 The Full-Universe Question (February 19–20, Bridge)

Steven asked: "What would I have to do to get full access to the entire universe of stocks?" This forced quantitative analysis of what "full universe" actually means and which providers could deliver it. The answer: only Databento (at the retail tier) can deliver unlimited simultaneous symbol access.

### 12.4 The Vision Reframe (February 19–20)

Steven's articulation of the 30+ strategy concurrent research workflow made the IQFeed symbol cap a structural limitation rather than a manageable constraint. The question shifted from "which provider covers the most asset classes?" to "which provider enables unlimited research experimentation?"

### 12.5 The Databento Deep Dive (February 20)

Additional Reddit practitioner evidence and web research confirmed:
- Databento's data quality is professional-grade (exchange-direct proprietary feeds)
- The Python client is modern and well-maintained (async support, official library)
- 150,000+ quotes/second throughput confirmed by practitioners
- Pricing is transparent and competitive
- Known limitations (no forex, no news) are real but supplementable

### 12.6 Final Recommendation (February 20)

**Databento as primary equities backbone, IQFeed as supplemental for specific capabilities.**

This reverses the Session 1 recommendation based on the evolved understanding of ARGUS's system identity.

---

## 13. Final Architecture Decision

### 13.1 Decision: Amended DEC-082

**Decision:** Databento US Equities Standard ($199/month) as primary equities data backbone. IQFeed added later as supplemental provider for forex, news feeds, and breadth indicators. Alpaca retained for order execution only.

**Rationale:**
1. Databento's unlimited symbol access directly serves the strategy research laboratory vision — no architectural ceiling on experimentation breadth.
2. Modern Python client with async support enables faster adapter development (no Wine/Docker/xvfb infrastructure).
3. Exchange-direct proprietary feeds provide richer data than SIP (odd lot quotes, full depth, auction imbalance, accurate trade signs).
4. $199/month for full-universe US equities is cheaper than IQFeed with symbol expansion packs, and without the 2,500 cap.
5. On-demand historical API enables the "data-first backtesting philosophy" — pull data when inspiration strikes without pre-downloading.
6. The 10-session limit on Standard is manageable with ARGUS's Event Bus fan-out architecture (one Databento connection, distribute internally).
7. IQFeed's unique capabilities (forex, Benzinga news, breadth indicators) are supplemental and can be added when those specific features are needed, rather than making them the foundation.

**Supersedes:** Initial DEC-082 draft (IQFeed primary). Extends DEC-005 (data broker-agnostic abstraction). Resolves DEC-081 (IEX limitation).

### 13.2 Architecture: Two-Provider with Clear Roles

| Role | Provider | Cost | When |
|---|---|---|---|
| **US Equities data backbone** | Databento Standard | $199/mo | Sprint 12 (immediate) |
| **Order execution** | Alpaca (paper → live) | $0 | Already integrated |
| **Forex + News + Breadth** | IQFeed | ~$160–250/mo | When needed (Phase 4+) |
| **Production execution scaling** | Interactive Brokers | Variable | When live trading scales |

### 13.3 Data Flow Architecture

```
Databento US Equities ──TCP──> DatabentoDataService ──EventBus──> All Strategies
                                      │                              │
                                      ├── CandleEvents (1m bars)     ├── Strategy 1
                                      ├── TickEvents (every trade)   ├── Strategy 2
                                      ├── IndicatorEvents (VWAP,ATR) ├── ...
                                      └── L2 Depth (when needed)     └── Strategy 30+

IQFeed (later) ──TCP/Wine──> IQFeedDataService ──EventBus──> Forex Strategies
                                      │                         News Classifier
                                      ├── Forex ticks            Breadth Monitor
                                      └── Benzinga news

Alpaca ──REST/WS──> AlpacaBroker ──EventBus──> Order Manager
                                                     │
                                                     └── Executes trades
```

---

## 14. Implementation Implications

### 14.1 Sprint 12 Scope: DatabentoDataService Adapter

The highest priority Build Track sprint. Components:

1. **DatabentoDataService** implementing the DataService abstraction: uses databento-python client library, subscribes to OHLCV-1m bars and trades streams, publishes CandleEvents and TickEvents through Event Bus.
2. **Historical data interface:** On-demand queries to Databento historical API for backtesting and strategy reconstruction. Replaces the current Parquet-file-based approach for new data needs.
3. **L2 depth integration:** Designed from sprint one (schema subscription to MBP-10), activated when a strategy requires it.
4. **Scanner integration:** Full-universe subscription at L0/L1, filtered by strategy-specific criteria. No tiered scanning workaround needed — Databento delivers everything.
5. **Session management:** Single live session, Event Bus fan-out to all consumers. Reconnection logic with exponential backoff.
6. **Comprehensive test suite** matching existing DataService test patterns.

### 14.2 Adapter Complexity Comparison

The DatabentoDataService adapter will be simpler than the originally planned IQFeedDataService:

| Aspect | IQFeed | Databento |
|---|---|---|
| Gateway process | Wine + xvfb Docker container | None (Python-native) |
| Protocol | Raw TCP sockets, custom parsing | Python client library (pip install) |
| Session management | Multiple socket connections | Single TCP session with multiplexing |
| Symbol management | Dynamic slot rotation (2,500 cap) | Subscribe-all, no management needed |
| Development estimate | 3–5 days | 2–3 days |

### 14.3 Paper Trading Unblocked

With the DatabentoDataService adapter, paper trading resumes with:
- Institutional-grade data quality (exchange-direct, not SIP-consolidated)
- Full universe available from day one
- Architecture ready for 30+ simultaneous strategies
- No symbol cap constraints on experimentation

---

## 15. Risk Assessment

### 15.1 Startup Business Continuity Risk

**Risk:** Databento is a VC-funded startup with ~$8M revenue against $37.5M in funding. They are pre-profitability. If they raise prices significantly, change terms, or go under, ARGUS loses its primary data source.

**Mitigation:**
- ARGUS's DataService abstraction makes provider swaps mechanical (build new adapter, ~1 sprint)
- Historical data stored locally in Parquet files is provider-independent
- IQFeed exists as a proven 20+ year fallback that can become primary
- Databento's $37.5M in funding provides runway; their partnerships with firms like Tickblaze and IBKR Campus suggest growing institutional adoption

**Residual risk level:** Medium. Manageable through architectural isolation.

### 15.2 Data Quality Divergence Risk

**Risk:** Databento's synthetic NBBO (constructed from proprietary feeds) may diverge slightly from the official SIP NBBO that brokers use for execution.

**Mitigation:**
- Due to Reg NMS price protection rules, proprietary feed prices are very close to SIP NBBO
- For ARGUS's strategies (multi-second to multi-minute holds), microsecond-level divergence is irrelevant
- Databento's approach actually provides more data (odd lots, depth) than SIP

**Residual risk level:** Low. Practically negligible for ARGUS's timeframes.

### 15.3 No Forex Coverage Risk

**Risk:** Databento has no forex data and no committed timeline. ARGUS's multi-asset vision includes forex as the third asset class.

**Mitigation:**
- IQFeed provides comprehensive forex coverage and is planned as the supplemental provider
- Forex strategies are not immediate priority (US equities → crypto → forex on roadmap)
- The DataService abstraction supports multiple providers simultaneously

**Residual risk level:** Low. Planned mitigation exists.

### 15.4 Session Limit Risk

**Risk:** 10 live sessions per dataset on Standard may become constraining as ARGUS scales beyond simple Event Bus fan-out.

**Mitigation:**
- Current architecture (single session, Event Bus fan-out) uses only 1 session
- Shadow paper trading system alongside live can use a second session
- 10 sessions is adequate for foreseeable needs
- Plus plan ($1,500/mo) provides 50 sessions if needed

**Residual risk level:** Low for current architecture. Monitor as system grows.

### 15.5 Operational Reliability Risk

**Risk:** Databento has experienced recent operational incidents (February 2026 historical API outage, replay window reduction).

**Mitigation:**
- Live streaming (the critical path for trading) was not affected by the February 2026 incidents
- 99.99% uptime commitment
- ARGUS should implement circuit-breaker logic: if data stream fails, halt new trades rather than trade blind
- IQFeed as backup data source (when implemented) provides redundancy

**Residual risk level:** Medium. Standard for any cloud-dependent system. Circuit-breaker logic is essential.

---

## Appendix A: Pricing Details

### Databento Pricing (as of January 2025)

**US Equities Plans:**

| Plan | Monthly Cost | Live Data | Historical Included |
|---|---|---|---|
| Standard | $199/mo | Unlimited L0–L3 | 15yr OHLCV, 12mo L0/L1, 1mo L2/L3 |
| Plus | $1,500/mo | Unlimited L0–L3, 50 sessions | 15yr OHLCV, 7yr L0/L1, 2yr L2/L3 |
| Unlimited | $4,000/mo | Unlimited everything | Full archive (15yr+ all schemas) |

**Other Datasets (each separate subscription):**

| Dataset | Standard | Notes |
|---|---|---|
| CME Globex (futures) | $179/mo | + CME exchange license fees |
| OPRA (options) | $199/mo | + OPRA license fees |
| ICE Futures Europe | $199/mo | + ICE exchange license fees |
| ICE Endex | $199/mo | + ICE exchange license fees |

### IQFeed Pricing (as of December 2025)

| Component | Monthly Cost | Notes |
|---|---|---|
| Base service | $83/mo | Equities + basic futures + news + 500 symbols |
| CME real-time | $10/mo | Exchange fee |
| Other exchanges | $10–40/mo | Per exchange |
| 500 symbol pack | $24.50/mo | Up to 4 additional packs |
| DTN Prop. Exchange | $49/mo | Additional exchange access |
| Estimated equities-only | ~$123/mo | Base + exchange fees |
| Estimated full multi-asset | ~$480–540/mo | All exchanges + symbol expansion |

---

## Appendix B: Source Material

### Primary Sources

1. **argus_market_data_report.md** — Session 1 report (February 19, 2026). Contains full provider evaluation, Reddit evidence summary, and initial IQFeed-primary recommendation. Archived as project file.
2. **Claude conversation: "Paper trading market open in Taipei"** — Session 1 conversation where the provider evaluation was conducted.
3. **Claude conversation: Current session** — Session 2 conversation (February 19–20, 2026) where the Databento deep dive and recommendation reversal occurred.

### Web Sources Consulted

- Databento official documentation, pricing pages, blog posts, and status page
- Databento public roadmap (roadmap.databento.com)
- Databento GitHub (github.com/databento)
- IQFeed official website and pricing documentation
- NYSE Consolidated Tape Association documentation
- Wikipedia: Securities Information Processor
- QuantVPS Databento Review (July 2025)
- TechList.ai Databento company profile
- Tracxn Databento funding data
- HFT University: Databento's C++ Choice article (October 2025)
- Databento blog: OPRA processing at 40 Gbps (October 2025)
- Databento blog: Direct Proprietary Feeds vs SIPs (November 2024)
- Databento blog: How to Get Real-Time US Stock Market Data (February 2024)
- Databento blog: Introducing Databento US Equities (January 2025)
- Databento blog: Changes to Live Connection Limits (January 2025)
- Databento blog: Pricing Plan Changes (January 2025)
- Databento blog: New CME Pricing Plans (April 2025)
- Databento blog: New OPRA Pricing Plans (June 2025)
- Databento blog: New ICE Subscription Plans (February 2025)
- Elite Trader: Databento auction imbalance discussion (March 2023)
- Medium: "RBR Algo with Databento" by Amal Tyagi (January 2026)

### Reddit Threads Analyzed

1. **r/quant** — "Polygon.io, Intrinio, Alpaca, or Xignite?" — Professional quant provider ranking across institutional, HFT, and retail tiers.
2. **r/algotrading** — Polygon vs IQFeed latency comparison — Measured latency data, stream freeze reports, throttling issues.
3. **r/algotrading** — Backtesting architecture discussion — Data-first philosophy quote, event-driven backtester descriptions, Databento/IQFeed usage patterns.
4. **r/algotrading** — Headless Linux trading setup — Databento migration report (150K quotes/sec), Databento vs Polygon accuracy, Wine-based Docker confirmation for IQFeed.
5. **r/algotrading** — Multiple Databento discussion threads — User experience reports, L2 coverage concerns, pricing discussion, comparisons with other providers.

---

*End of Report — February 20, 2026 — ARGUS Market Data Infrastructure Research Report (Final)*
