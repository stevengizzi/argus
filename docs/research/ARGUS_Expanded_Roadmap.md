# ARGUS — Expanded Roadmap: Full-Scale Vision

> *Strategic plan for evolving ARGUS from a rules-based multi-strategy system into an AI-powered trading intelligence platform capable of matching or exceeding top discretionary trader performance.*
>
> *Drafted: February 26, 2026. Authors: Steven + Claude.*
> *Status: PROPOSAL — requires review, discussion, and decision before adoption.*

---

## 1. The Thesis

Ross Cameron has demonstrated, with audited broker statements, that a single discretionary trader can generate $1M–$3M+ annually trading low-float momentum stocks — an extraordinary return on deployed capital. His strategies (Gap and Go, ORB, VWAP momentum, bull flags, red-to-green) map directly onto ARGUS's existing strategy roster.

The gap between ARGUS's current architecture and Ross-level returns is not in *strategy selection* — it's in **setup quality grading, dynamic position sizing, order flow intelligence, and simultaneous opportunity coverage.** Every advantage Ross has over ARGUS today is decomposable into quantifiable signals that a well-instrumented system can measure — and in many cases measure *better* than a human watching 3-5 screens.

This roadmap expands ARGUS from a **rules-based multi-strategy system** into an **AI-powered trading intelligence platform** that:

- Scores every setup on a quality continuum (A+ through C-) rather than binary pass/fail
- Dynamically sizes positions based on setup quality, not uniform risk parameters
- Reads Level 2/Level 3 order flow to assess real buying pressure vs. spoofing
- Classifies catalyst quality in real-time using NLP
- Runs 15–20+ pattern types simultaneously across the full small-cap momentum universe
- Learns from its own trade outcomes to continuously sharpen all of the above

The target: **sustainable 5–10%+ monthly returns on deployed capital** at the $100K–$500K scale, with the system running autonomously during US market hours from Taipei.

---

## 2. What Changes — And What Doesn't

### Unchanged (Current Architecture Strengths)

These foundations are correct and remain:

- **Event-driven architecture** with Event Bus, FIFO delivery, sequence numbers
- **Three-tier risk management** (strategy → cross-strategy → account)
- **Broker abstraction** (IBKR for live, Alpaca for incubation, SimulatedBroker for backtest)
- **Data provider abstraction** (Databento primary, adapters swappable)
- **Strategy Incubator Pipeline** (10 stages from concept to retirement)
- **Walk-forward validation** as mandatory overfitting defense
- **Two-Claude workflow** (strategic Claude.ai + tactical Claude Code)
- **Command Center** (three surfaces: web, Tauri desktop, PWA mobile)
- **Daily-stateful, session-stateless** strategy model
- **Trade Logger** as sole persistence interface
- **Parallel Build + Validation tracks**

### What Evolves

| Current | Expanded |
|---------|----------|
| Binary scanner (pass/fail filters) | **Opportunity Ranker** (composite quality score per setup) |
| 5 strategies (ORB, Scalp, VWAP, Afternoon, R2G) | **15–20+ pattern types** covering the full momentum playbook |
| Uniform position sizing (fixed % risk per trade) | **Dynamic position sizing** tied to setup quality grade |
| Price/volume entry triggers only | **Order flow intelligence** using L2/L3 data for entry confidence |
| Tier 2/3 News deferred to Sprint 23+ | **NLP catalyst pipeline** as a core system component |
| AI Layer as advisory add-on (Sprint 22) | **AI Layer as the brain** — real-time setup grading, sizing decisions, learning loop |
| Orchestrator V1 (rules-based allocation) | **Orchestrator V2** (AI-enhanced, intraday dynamic allocation) |
| RegimeClassifier (SPY vol proxy) | **Multi-factor regime engine** with sector rotation awareness |
| Conservative risk defaults | **Graduated risk tiers** (conservative base → aggressive on A+ setups) |

### What's New (Doesn't Exist Yet)

1. **Setup Quality Scoring Engine** — Composite score (0–100) for every potential trade, combining technical pattern strength, catalyst quality, order flow signals, historical pattern match, and regime alignment
2. **Order Flow Model** — L2/L3 data analysis: bid/ask imbalance, iceberg detection, spoofing detection, momentum absorption, tape speed
3. **NLP Catalyst Classifier** — Real-time news/filing classification with quality grading via Claude API
4. **Dynamic Position Sizer** — Maps quality score to risk allocation (C+ = 0.25%, B = 0.75%, A = 1.5%, A+ = 2.5%)
5. **Pattern Library** — Expanded from 5 to 15–20+ pattern recognition modules (bull flags, ABCD, flat-top breakouts, dip-and-rip, HOD breaks, etc.)
6. **Learning Loop** — Post-trade analysis that correlates quality scores with actual outcomes, continuously retraining the scoring model
7. **Pre-Market Intelligence Engine** — Automated pre-market scanning, catalyst research, and watchlist generation starting at 4:00 AM ET

---

## 3. The Expanded Architecture

### 3.1 System Diagram (Expanded)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                │
│  Databento (L1/L2/L3)  │  IBKR  │  News APIs  │  SEC EDGAR  │  Claude  │
└───────┬─────────────────┴───┬────┴──────┬──────┴──────┬──────┴────┬─────┘
        │                     │           │             │           │
┌───────▼─────────────────────▼───────────▼─────────────▼───────────▼─────┐
│                     TIER 1: TRADING ENGINE (Expanded)                    │
│                                                                         │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │  Data Service    │  │  Order Flow       │  │  Catalyst Pipeline   │   │
│  │  (L1 + L2 + L3) │  │  Model            │  │  (NLP + EDGAR)       │   │
│  └────────┬────────┘  └────────┬──────────┘  └──────────┬──────────┘   │
│           │                    │                         │              │
│  ┌────────▼────────────────────▼─────────────────────────▼──────────┐   │
│  │                     SETUP QUALITY ENGINE                         │   │
│  │  Opportunity Ranker → Quality Score (0–100) → Grade (A+ to C-)  │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                       │
│  ┌──────────────────────────────▼───────────────────────────────────┐   │
│  │                    EVENT BUS                                     │   │
│  └──┬───┬───┬───┬───┬───┬───┬──────────────────────────────────────┘   │
│     │   │   │   │   │   │   │                                          │
│  ┌──▼─┐ │  ┌▼──┐│  ┌▼──┐│  ┌▼─────────────┐  ┌────────────────────┐  │
│  │ORB │ │  │VWP││  │AFT││  │ Pattern       │  │  AI Brain          │  │
│  │    │...│   ││  │   ││  │ Library       │  │  (Claude Opus)     │  │
│  │Sclp│ │  │R2G││  │...││  │ (15+ types)  │  │  Real-time grading │  │
│  └──┬──┘ │  └─┬─┘│  └─┬─┘│  └──────┬──────┘  └────────┬───────────┘  │
│     │    │    │   │    │  │         │                   │              │
│  ┌──▼────▼────▼───▼────▼──▼─────────▼───────────────────▼──────────┐   │
│  │              DYNAMIC POSITION SIZER                              │   │
│  │  Quality Score → Risk Tier → Share Count                        │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                             │                                          │
│  ┌──────────────────────────▼──────────────────────────────────────┐   │
│  │              RISK MANAGER (Enhanced)                             │   │
│  │  Strategy │ Cross-Strategy │ Account │ Correlation-Aware        │   │
│  └──────────────────────────┬──────────────────────────────────────┘   │
│                             │                                          │
│  ┌──────────────────────────▼──────────────────────────────────────┐   │
│  │              ORDER MANAGER → IBKR                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │  LEARNING LOOP  │  │ ORCHESTRATOR │  │  PRE-MARKET ENGINE       │   │
│  │  (Outcome →     │  │ V2 (AI-      │  │  (4:00 AM → 9:30 AM)    │   │
│  │   Score Update) │  │  Enhanced)   │  │  Watchlist, Research,    │   │
│  └────────────────┘  └──────────────┘  │  Grade pre-seeding       │   │
│                                         └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Setup Quality Engine — The Core Innovation

This is the single most important new component. It transforms ARGUS from "does this setup pass the filter?" to "how good is this setup compared to every setup I've ever seen?"

**Input signals (weighted composite):**

| Signal Category | Weight | Source | What It Measures |
|----------------|--------|--------|-----------------|
| **Pattern Strength** | 25% | Strategy module | How clean is the chart pattern? Textbook or messy? |
| **Catalyst Quality** | 20% | NLP Catalyst Pipeline | FDA approval vs. secondary offering vs. no catalyst |
| **Order Flow** | 20% | L2/L3 Model | Real buying pressure? Thin asks? Absorption? |
| **Volume Profile** | 15% | Databento L1 | RVOL magnitude, pre-market volume quality, volume acceleration |
| **Historical Match** | 10% | Learning Loop DB | How have similar setups (same pattern + catalyst + regime) performed? |
| **Regime Alignment** | 10% | RegimeClassifier V2 | Is the broad market supporting this type of trade today? |

**Output:**

```python
@dataclass
class SetupQuality:
    score: float          # 0-100 composite
    grade: str            # A+, A, A-, B+, B, B-, C+, C, C-
    risk_tier: RiskTier   # AGGRESSIVE, STANDARD, CONSERVATIVE, SKIP
    confidence: float     # 0-1, model's confidence in its own score
    components: dict      # Breakdown by signal category
    rationale: str        # Human-readable explanation
```

**Grade → Risk Tier mapping:**

| Grade | Score Range | Risk % of Capital | Behavior |
|-------|-----------|-------------------|----------|
| A+ | 90–100 | 2.0–3.0% | Maximum conviction. Size up. |
| A | 80–89 | 1.5–2.0% | High confidence. Above-average size. |
| A- | 70–79 | 1.0–1.5% | Good setup. Standard-plus sizing. |
| B+ | 60–69 | 0.75–1.0% | Solid. Standard sizing. |
| B | 50–59 | 0.5–0.75% | Acceptable. Conservative sizing. |
| B- | 40–49 | 0.25–0.5% | Marginal. Minimum sizing. |
| C+ | 30–39 | 0.25% (minimum) | Barely passes. Minimum or skip. |
| C/C- | 0–29 | SKIP | Do not trade. |

### 3.3 Order Flow Model

**Data source:** Databento L2 (MBP-10 top-of-book + depth) and L3 (individual order events) schemas. Currently on the Standard plan — L2/L3 access included.

**Signals extracted:**

| Signal | Description | How It's Used |
|--------|-------------|---------------|
| **Bid/Ask Imbalance** | Ratio of bid volume to ask volume at best levels + 3 deep | Imbalance > 2:1 favoring entry side = bullish |
| **Ask Thinning** | Rate of reduction in ask-side depth above current price | Rapid thinning above breakout level = pending move |
| **Spoofing Detection** | Large orders that appear and disappear within seconds | Filter out false support/resistance |
| **Iceberg Detection** | Hidden orders refreshing at same price level | Indicates institutional accumulation |
| **Momentum Absorption** | Large sell orders being absorbed without price decline | Strong buying interest absorbing selling pressure |
| **Tape Speed** | Prints per second on Time & Sales | Acceleration signals imminent move |
| **Bid Stacking** | Increasing bid depth at and below current price | Building support floor |

**Implementation approach:** Start with the highest-signal, lowest-complexity metrics (bid/ask imbalance, tape speed, ask thinning). Add iceberg/spoofing detection as V2.

### 3.4 NLP Catalyst Pipeline

**Architecture:**

```
News APIs / EDGAR / Pre-market feeds
        │
        ▼
  Symbol Matching (ticker extraction)
        │
        ▼
  Catalyst Classification (Claude API)
        │
        ▼
  Quality Scoring (1-10 scale)
        │
        ▼
  Setup Quality Engine (20% weight)
```

**Catalyst quality scoring (via Claude API):**

| Category | Typical Score | Examples |
|----------|--------------|---------|
| FDA Approval (major) | 9-10 | New drug approved for large indication |
| M&A / Acquisition | 8-9 | Buyout offer at premium |
| Earnings Beat (significant) | 7-8 | Revenue/EPS beat by 20%+ with raised guidance |
| Analyst Upgrade (major bank) | 6-7 | Goldman initiates with Buy, $X target |
| Contract/Partnership | 5-7 | Government contract, major partnership |
| Earnings Beat (moderate) | 4-6 | Small beat, guidance in line |
| Industry Tailwind | 3-5 | Sector news lifting related names |
| SEC Filing (benign) | 2-4 | Routine 8-K, no material change |
| Secondary Offering | 1-3 | Dilutive. Negative for price. |
| Reverse Split / Delisting Risk | 0-1 | Major red flag. Avoid. |

**Claude API usage:** Each catalyst evaluation is a single API call with a structured prompt. At 5-15 watchlist stocks × 1 call each during pre-market, this is ~10 calls/day, well within the $35-50/month budget (DEC-098).

### 3.5 Expanded Pattern Library

Beyond the current 5 strategies, ARGUS needs to recognize the full playbook of momentum day trading patterns. Each pattern is a strategy module implementing BaseStrategy.

**Phase 1 Patterns (Currently Planned — Sprints 18-20):**

| # | Pattern | Status | Time Window |
|---|---------|--------|-------------|
| 1 | ORB (Opening Range Breakout) | ✅ Live | 9:35–11:30 AM |
| 2 | ORB Scalp | ✅ Built | 9:45–11:30 AM |
| 3 | VWAP Reclaim | ✅ Built | 10:00 AM–12:00 PM |
| 4 | Afternoon Momentum | Sprint 20 | 2:00–3:30 PM |
| 5 | Red-to-Green | Sprint 23+ | 9:45–11:00 AM |

**Phase 2 Patterns (New — to be built):**

| # | Pattern | Description | Time Window | Complexity |
|---|---------|-------------|-------------|------------|
| 6 | **Bull Flag** | Consolidation after sharp move, breakout on volume | All day | Medium |
| 7 | **Flat-Top Breakout** | Multiple rejections at same level, clean break | All day | Medium |
| 8 | **ABCD Reversal** | Four-point reversal pattern at support | 10:00 AM–2:00 PM | High |
| 9 | **Dip-and-Rip** | Sharp dip on low vol, aggressive bounce on high vol | 9:45–11:30 AM | Medium |
| 10 | **HOD Break (High of Day)** | New HOD breakout with volume confirmation | All day | Low |
| 11 | **Pre-Market High Break** | Break above pre-market high on open | 9:30–10:30 AM | Low |
| 12 | **Gap-and-Go** | Immediate continuation of gap direction without pullback | 9:30–10:00 AM | Medium |
| 13 | **Parabolic Short** | Overextended parabolic move, short on reversal signal | 10:00 AM–3:00 PM | High |
| 14 | **Sympathy Play** | Secondary mover in same sector as leading catalyst | 9:45–11:30 AM | Medium |
| 15 | **Power Hour Reversal** | Failed breakdown or breakdown-reversal in final hour | 3:00–3:45 PM | Medium |
| 16 | **Earnings Gap Continuation** | Day 2+ continuation of strong earnings gap | 9:30–11:30 AM | Medium |
| 17 | **Volume Shelf Bounce** | Price bounces off high-volume price shelf (VPOC) | All day | High |
| 18 | **Micro Float Runner** | Ultra-low float (<5M) with extreme RVOL (>10x), ride momentum | 9:30–11:30 AM | High |

**Important:** Not all of these will prove to have a backtestable edge. Each goes through the full Incubator Pipeline. The goal is to have 10-12 validated patterns running simultaneously.

### 3.6 Pre-Market Intelligence Engine

Ross's edge starts *before the market opens*. He spends 30-60 minutes reviewing gappers, reading catalysts, sizing up Level 2 pre-market, and building a mental model of the day. ARGUS should automate this entirely.

**Timeline (all times ET):**

| Time | Action |
|------|--------|
| 4:00 AM | Pre-market data feed starts. Scanner begins tracking gaps. |
| 4:00–7:00 AM | Accumulate pre-market volume, price action, bid/ask behavior on all gapping stocks. |
| 7:00 AM | Trigger NLP Catalyst Pipeline. Claude API evaluates news/filings for all gappers. |
| 7:30 AM | Generate ranked watchlist with quality pre-scores (pattern not yet formed, but catalyst + volume + float assessed). |
| 8:00 AM | Deliver Pre-Market Briefing to Command Center + push notification. Includes: top 10 watchlist, regime assessment, catalyst summaries, suggested position sizes per ticker. |
| 9:00 AM | Final watchlist refinement. Update quality scores with latest pre-market action. |
| 9:25 AM | Lock watchlist. System enters ready state. All strategies armed. |
| 9:30 AM | Market open. Strategies begin operating on scored watchlist. |

**For Steven in Taipei (13 hours ahead):**

| Taipei Time | ET Time | What Happens |
|------------|---------|--------------|
| 5:00 PM | 4:00 AM | Pre-market scanning begins (automated) |
| 8:00 PM | 7:00 AM | Catalyst analysis runs (automated) |
| 9:00 PM | 8:00 AM | Pre-Market Briefing delivered → Steven reviews on phone |
| 10:30 PM | 9:30 AM | Market opens → ARGUS trades autonomously |
| 10:30 PM–5:00 AM | 9:30 AM–4:00 PM | Steven monitors on PWA, system runs autonomously |
| 5:00 AM | 4:00 PM | Market close → EOD report delivered |

### 3.7 Learning Loop

Every trade generates a feedback signal that updates the Setup Quality Engine.

```
Trade Outcome
    │
    ▼
Post-Trade Analysis (automated, Claude API)
    │
    ├── Pattern: What type, how clean (1-10)?
    ├── Catalyst: What type, what quality grade was assigned?
    ├── Order Flow: What were the L2 signals at entry?
    ├── Volume: RVOL at entry, acceleration pattern?
    ├── Regime: What was the market doing?
    ├── Result: Win/loss, R-multiple, hold time, exit type
    │
    ▼
Learning Database
    │
    ▼
Quality Score Model Update (weekly batch)
    │
    ├── "A+ setups with FDA catalysts are winning at 72% with avg 1.8R"
    ├── "B setups with earnings catalysts in high-vol regime are underperforming"
    ├── "Order flow imbalance > 3:1 adds 0.3R to expected outcome"
    │
    ▼
Updated Weights → Setup Quality Engine
```

**V1:** Statistical (lookup tables: pattern × catalyst × regime → historical win rate and R-multiple). **V2:** ML model trained on accumulated trade data.

---

## 4. The Expanded Roadmap

### Current State (Sprints 1–20 Complete)

- 1,522 pytest + 48 Vitest tests
- 4 strategies built (ORB, ORB Scalp, VWAP Reclaim, Afternoon Momentum) covering 9:30 AM–3:30 PM

### Phase A: Complete Current Foundation (Sprints 20–22)

*Continue the existing roadmap. These sprints are already designed and remain correct. They complete the minimum viable multi-strategy system.*

| Sprint | Scope | Outcome |
|--------|-------|---------|
| **20** | Afternoon Momentum Strategy ✅ | 4 strategies, full-day coverage |
| **21a** | Pattern Library Page (DEC-169) | Strategy encyclopedia |
| **21b** | Orchestrator Page (DEC-169) | Operational command center |
| **21c** | The Debrief Page (DEC-169) | Knowledge accumulation |
| **21d** | Dashboard + Performance + System + Nav + Copilot Shell (DEC-169–171) | 7-page architecture established |
| **22** | AI Layer MVP + Copilot Activation (DEC-170) | Claude API + contextual chat everywhere |

Sprint 20 complete. Sprint 21 expanded into 21a–21d to establish the 7-page Command Center architecture (DEC-169, DEC-171) before intelligence sprints begin. Sprint 22 expanded to include full AI Copilot activation (DEC-170) — contextual Claude chat accessible from every page. These form the foundation that everything else builds on.

### Phase B: Intelligence Infrastructure (Sprints 23–26)

*This is the new work. Build the infrastructure that transforms ARGUS from rules-based to intelligence-driven.*

#### Sprint 23 — NLP Catalyst Pipeline + Pre-Market Engine
**Target:** ~2–3 days
**Scope:**
- **CatalystService** (`argus/intelligence/catalyst_service.py`): Symbol-matched news ingestion from free sources — SEC EDGAR (8-K, Form 4), Finnhub (company news, calendars, free tier 60 calls/min), Financial Modeling Prep (earnings calendar, press releases, free tier 250 calls/day). Paid sources (Benzinga Pro ~$200/mo) deferred per DEC-164 — trigger: >30% unclassified catalyst rate over 20 days.
- **CatalystClassifier** (`argus/intelligence/catalyst_classifier.py`): Claude API integration for real-time catalyst quality scoring (1-10 scale, category assignment)
- **PreMarketEngine** (`argus/intelligence/premarket_engine.py`): Automated 4:00 AM → 9:25 AM pipeline (gap scanning → catalyst research → watchlist ranking → pre-market briefing)
- **CatalystEvent** on Event Bus: `(symbol, category, quality_score, headline, source, timestamp)`
- Scanner enrichment: catalyst metadata attached to WatchlistItems
- API endpoints: `/api/v1/catalysts/{symbol}`, `/api/v1/premarket/briefing`
- UI: Pre-Market Briefing page/panel in Command Center, catalyst badges on watchlist items
- **Tests:** ~80 new

#### Sprint 24 — Order Flow Model V1
**Target:** ~2–3 days
**Scope:**
- **Databento L2 integration:** Subscribe to MBP-10 schema (top-of-book + 10 depth levels) for watchlist symbols. Extend DatabentoDataService.
- **OrderFlowAnalyzer** (`argus/intelligence/order_flow.py`): Real-time L2 signal extraction — bid/ask imbalance ratio, ask thinning rate, tape speed (prints/sec), bid stacking score
- **OrderFlowEvent** on Event Bus: `(symbol, imbalance_ratio, ask_thin_rate, tape_speed, composite_score, timestamp)`
- **OrderFlowSnapshot** for strategy consumption: strategies can query current order flow state for any watchlist symbol
- Throttled updates (100ms intervals to avoid event flood)
- API endpoint: `/api/v1/orderflow/{symbol}` (current state)
- UI: L2 visualization in stock detail panel (heatmap depth chart)
- **Deferred:** L3 (individual order events) — iceberg/spoofing detection deferred to Sprint 28+
- **Tests:** ~60 new

#### Sprint 25 — Setup Quality Engine + Dynamic Position Sizer
**Target:** ~3–4 days (largest new sprint)
**Scope:**
- **SetupQualityEngine** (`argus/intelligence/quality_engine.py`): Composite scoring (0-100) combining pattern strength, catalyst quality, order flow signals, volume profile, historical match, regime alignment. Configurable weights.
- **SetupQuality** dataclass: score, grade, risk_tier, confidence, components, rationale
- **DynamicPositionSizer** (`argus/intelligence/position_sizer.py`): Maps quality grade → risk tier → actual risk percentage. Replaces fixed `risk_per_trade_pct` in strategy configs. Respects all existing Risk Manager limits (account daily loss, weekly loss, single-stock cap).
- **QualitySignalEvent** on Event Bus: published when a new setup is scored. Strategies subscribe and use quality data in their entry decision.
- **Integration with SignalEvent:** Add `quality_score`, `quality_grade`, `risk_tier` fields to SignalEvent. Risk Manager and Order Manager respect the dynamic sizing.
- **Quality History DB table:** Store every scored setup (traded or not) for Learning Loop.
- API endpoints: `/api/v1/quality/{symbol}`, `/api/v1/quality/history`
- UI: Quality gauge overlay on positions, setup grading breakdown in trade detail panel
- **Tests:** ~100 new (scoring logic, sizer boundaries, Risk Manager integration, edge cases)

#### Sprint 26 — Red-to-Green Strategy + Pattern Library Foundation
**Target:** ~2 days
**Scope:**
- **RedToGreenStrategy**: Gap-down reversal, cross from red to green, operates 9:45–11:00 AM
- **PatternLibrary ABC** (`argus/strategies/pattern_library.py`): Common interface for pattern recognition modules. Each pattern type implements `detect(symbol, bars, indicators) -> PatternSignal | None`.
- **Bull Flag pattern module** (first Phase 2 pattern): Consolidation detection, channel measurement, breakout trigger
- **Flat-Top Breakout pattern module**: Resistance-at-level detection, multiple-touch confirmation
- Integration with Setup Quality Engine: patterns contribute to the "pattern strength" score component
- VectorBT sweep infrastructure for new patterns
- **5 strategies active + 2 pattern modules available**
- **Tests:** ~80 new

### Phase C: Scale the Edge (Sprints 27–32)

*Expand pattern coverage, add order flow sophistication, and build the learning loop.*

#### Sprint 27 — Pattern Library Expansion I
**Target:** ~2–3 days
**Scope:**
- 4 additional pattern modules: Dip-and-Rip, HOD Break, Pre-Market High Break, Gap-and-Go
- Each through Incubator Pipeline stages 1-3 (Concept → Exploration → Validation)
- VectorBT sweeps + walk-forward for each with Databento data
- Cross-pattern risk integration (10+ signal sources, correlation tracking)
- **9 strategies/patterns active**

#### Sprint 28 — Order Flow Model V2 + Short Selling
**Target:** ~2–3 days
**Scope:**
- **Databento L3 integration:** Subscribe to individual order event schema
- **Iceberg detection algorithm:** Identify hidden refreshing orders
- **Spoofing detection algorithm:** Track large orders that appear/disappear within configurable time window
- **Momentum absorption detector:** Large sells absorbed without price decline
- Update order flow composite score with L3 signals
- **Short selling infrastructure:** Extend strategies and Risk Manager for short positions. Add locate/borrow tracking. First short strategy: **Parabolic Short** pattern module
- **Tests:** ~80 new

#### Sprint 29 — Pattern Library Expansion II
**Target:** ~2–3 days
**Scope:**
- 4 more pattern modules: ABCD Reversal, Sympathy Play, Power Hour Reversal, Earnings Gap Continuation
- Each through Incubator Pipeline stages 1-3
- Cross-strategy correlation matrix update
- **13 strategies/patterns active**

#### Sprint 30 — Learning Loop V1
**Target:** ~2–3 days
**Scope:**
- **LearningDatabase** (`argus/intelligence/learning_db.py`): Schema for storing setup quality scores linked to trade outcomes
- **PostTradeAnalyzer** (`argus/intelligence/post_trade.py`): Automated post-trade decomposition — what was the quality score? What actually happened? Which score components were predictive?
- **Weekly batch retraining:** Statistical model (lookup tables) mapping (pattern_type × catalyst_category × regime × order_flow_quartile) → (historical_win_rate, avg_r_multiple, sample_size)
- **Quality score calibration:** Are A+ setups actually winning more than B setups? Calibrate weights.
- API: `/api/v1/learning/insights`, `/api/v1/learning/calibration`
- UI: Learning insights panel, calibration chart (predicted vs actual outcome by grade)
- **Tests:** ~60 new

#### Sprint 31 — Orchestrator V2 (AI-Enhanced)
**Target:** ~2–3 days
**Scope:**
- **Intraday dynamic allocation:** Orchestrator adjusts capital allocation during the session based on performance, regime shifts, and opportunity quality
- **AI allocation advisor:** Claude API analyzes current positions, available setups, and regime to recommend allocation shifts (approval workflow)
- **Correlation-aware allocation:** Use CorrelationTracker (Sprint 17 infrastructure) to reduce correlated exposure
- **Opportunity cost tracking:** When a quality A+ setup is skipped due to capital constraints, log it. Inform future allocation decisions.
- Replace equal-weight V1 with quality-weighted allocation
- **Tests:** ~60 new

#### Sprint 32 — Pattern Library Expansion III + Volume Profile
**Target:** ~2–3 days
**Scope:**
- 2 remaining pattern modules: Volume Shelf Bounce, Micro Float Runner
- **Volume Profile (VPOC):** Compute value area, point of control from Databento data. Used by Volume Shelf Bounce and as a signal component in Setup Quality Engine.
- **15 strategies/patterns active — full V1 pattern library**
- **Tests:** ~60 new

### Phase D: Optimize and Compound (Sprints 33+)

#### Sprint 33 — Learning Loop V2 (ML)
- Replace statistical lookup tables with gradient-boosted model (LightGBM or similar)
- Feature engineering from accumulated trade data
- Cross-validation against statistical model
- A/B framework: ML model scores alongside statistical model, compare

#### Sprint 34 — Advanced Regime Engine
- Multi-factor regime classification (sector rotation, breadth, yield curve, VIX term structure)
- Regime prediction (not just detection) using trend analysis
- Strategy-specific regime sensitivity profiles

#### Sprint 35 — Multi-Asset Expansion (Crypto)
- Crypto momentum strategies via IBKR
- 24/7 scanning for high-volatility setups
- Adapted pattern library for crypto microstructure

#### Sprint 36+ — Continuous Improvement
- Monte Carlo simulation for risk assessment
- Strategy breeding (genetic algorithms for parameter exploration)
- Cross-market signal detection (futures leading equities, etc.)
- Advanced tax optimization (wash sale avoidance, tax-loss harvesting)

---

## 5. Sprint Sizing and Timeline Estimate

### Summary Table

| Phase | Sprints | New Tests (est.) | Calendar Estimate | Cumulative Strategies |
|-------|---------|-----------------|-------------------|-----------------------|
| **A: Current Foundation** | 20–22 | ~300 | 3–5 days | 5 (incl. R2G at Sprint 23) |
| **B: Intelligence Infrastructure** | 23–26 | ~320 | 8–12 days | 7 + 2 pattern modules |
| **C: Scale the Edge** | 27–32 | ~340 | 12–18 days | 15 strategies/patterns |
| **D: Optimize and Compound** | 33–36+ | ~200+ | 10–15+ days | 15+ with ML optimization |
| **TOTAL** | 20–36+ | ~1,160+ | ~33–50 days | 15+ strategies/patterns |

At the demonstrated development velocity (~1 sprint/day for focused sprints, 2-3 days for complex ones), this represents approximately **2–3 months of Build Track work** alongside continuous Validation Track activity.

### Test Count Projection

| Milestone | pytest | Vitest | Total |
|-----------|--------|--------|-------|
| Current (Sprint 19) | 1,410 | 40 | 1,450 |
| End Phase A (Sprint 22) | ~1,710 | ~80 | ~1,790 |
| End Phase B (Sprint 26) | ~2,030 | ~120 | ~2,150 |
| End Phase C (Sprint 32) | ~2,370 | ~160 | ~2,530 |
| End Phase D (Sprint 36+) | ~2,570+ | ~180+ | ~2,750+ |

### Infrastructure Cost Projection

| Item | Current | Phase B | Phase C | Phase D |
|------|---------|---------|---------|---------|
| Databento US Equities | $199/mo | $199/mo | $199/mo | $199/mo |
| Databento L2/L3 | included | included | included | included |
| Claude API (AI Layer) | — | ~$50/mo | ~$75/mo | ~$100/mo |
| IQFeed (news/breadth) | — | ~$200/mo | ~$200/mo | ~$200/mo |
| IBKR commissions | — | variable | variable | variable |
| **Monthly total** | **$199** | **~$449** | **~$474** | **~$499 + commissions** |

---

## 6. Validation Gates — When to Deploy Real Capital

The expanded roadmap doesn't change the fundamental validation philosophy. It *raises the bar* for what "ready" looks like:

### Gate 1: System Stability (Current — Alpaca paper trading)
- ✅ Already running
- Validates infrastructure, not strategy edge

### Gate 2: Quality Data Validation (After Databento activation)
- Run all 4 Phase A strategies on Databento data with IBKR paper
- Minimum 20 trading days
- Compare to backtest expectations
- Kill criteria apply (existing ones from `08_PAPER_TRADING_GUIDE.md`)

### Gate 3: AI-Enhanced Validation (After Phase B, Sprint 26)
- Setup Quality Engine active, scoring every trade
- NLP catalyst pipeline enriching watchlist
- Order Flow V1 contributing to entry decisions
- Dynamic position sizing in paper mode
- Minimum 30 trading days
- **New metric:** Track quality-score-to-outcome correlation. If A+ setups don't outperform B setups, the quality engine isn't working yet.

### Gate 4: Full System Validation (After Phase C, Sprint 32)
- 15 patterns active
- Learning Loop V1 providing feedback
- Orchestrator V2 managing allocation
- Minimum 20 more trading days (50+ cumulative)
- **New metric:** System-level Sharpe > 2.0 over rolling 30-day windows

### Gate 5: Live Trading (User Decision)
- CPA consultation complete
- Explicit go/no-go by user
- Start at minimum size ($25K, 10-share positions)
- Shadow system runs indefinitely in parallel
- Scale gradually: minimum → intermediate → model-calculated → full

---

## 7. Key Risks of the Expanded Vision

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Overfitting the quality model** | High | Walk-forward validation on quality scores, not just strategy parameters. Out-of-sample quality score calibration mandatory. |
| **L2/L3 data cost escalation** | Medium | L2/L3 included in Databento Standard plan. Monitor session count (limit: 10). |
| **Claude API latency for real-time scoring** | Medium | Cache catalyst scores (they don't change intraday). Pre-compute during pre-market. Only novel mid-day catalysts need real-time scoring. |
| **Pattern library complexity explosion** | High | Each pattern must pass walk-forward independently. Retire patterns that don't earn their keep. Quality > quantity. |
| **Dynamic sizing amplifies losses on bad scores** | Medium | A+ sizing caps at 3% per trade. Account-level daily/weekly limits unchanged. Circuit breakers still override everything. |
| **Scope creep extending timeline** | Medium | Phase A is unchanged. Phase B/C/D sprints are designed to be independently valuable — each sprint delivers a working increment. Can pause expansion at any phase boundary. |

---

## 7.5 Command Center Architecture — Seven Pages + AI Copilot

### Seven-Page Structure (DEC-169)

The expanded ARGUS vision requires expanding the Command Center from 4 to 7 pages. Each page has a focused purpose:

1. **Dashboard** — Pure ambient awareness. "How am I doing right now?" in under 2 seconds. Pre-market mode before 9:30 AM. Narrower scope than original — operational controls migrated to Orchestrator.
2. **Trade Log** — Trade history. Unchanged from current, gains quality/catalyst/pattern columns.
3. **Performance** — Quantitative analytics. Adds quality/catalyst/pattern breakdowns, heatmaps, treemaps, calibration charts.
4. **Orchestrator** (NEW) — Operational command center. All Orchestrator decisioning visible and manually overridable. Capital allocation controls, decision stream with AI recommendation cards, risk gauges, emergency controls.
5. **Pattern Library** (NEW) — Strategy encyclopedia. Master-detail layout. Every strategy's parameters, performance, backtests, incubator pipeline position visible. The window into how the system works.
6. **The Debrief** (NEW) — Knowledge accumulation. Daily briefings (pre/post-market), research library, learning journal. ARGUS's institutional memory.
7. **System** — Infrastructure health only. Narrowed from original scope — strategy management migrated to Pattern Library, controls migrated to Orchestrator.

### AI Copilot — Claude Everywhere (DEC-170)

Claude is accessible from every page via a persistent slide-out chat panel (desktop: right 35%, mobile: full-screen overlay). Triggered by floating button or `c` keyboard shortcut.

**Context-aware:** When opened, Claude automatically receives the page context (what you're viewing), selected entity (trade, strategy, position), system state (positions, regime, risk utilization), and chat history.

**Actions from chat:** Generate reports (saved to Debrief), propose parameter changes (approval workflow), propose allocation overrides, annotate trades (saved to Learning Journal), explain any system decision.

**Boundary:** Claude never executes trades directly. All proposals go through Risk Manager gates and approval workflow.

### Navigation

Desktop: Icon sidebar with 7 items grouped — Monitor (Dashboard, Trades, Performance) | Operate (Orchestrator, Patterns) | Learn (Debrief) | Maintain (System). Keyboard shortcuts 1–7, `c` for copilot, `w` for watchlist.

Mobile: 5 bottom tabs (Dashboard, Trades, Orchestrator, Patterns, More → Performance, Debrief, System). Copilot button floats above tab bar.

---

## 8. What Success Looks Like

### 3-Month Milestone (End of Phase B)
- 7 strategies active with quality scoring
- Setup Quality Engine grading every trade
- Pre-Market Briefing delivered automatically by 8:00 AM ET
- Order flow V1 contributing to entry confidence
- Paper trading showing quality score → outcome correlation
- Monthly paper returns: 3–5%+ on simulated capital

### 6-Month Milestone (End of Phase C)
- 15 patterns active across the full trading day
- Learning Loop V1 refining quality scores weekly
- Dynamic position sizing proven in paper trading
- System-level Sharpe > 2.0 consistently
- Monthly paper returns: 5–8%+ on simulated capital
- Ready for Gate 5 (live trading decision)

### 12-Month Milestone (Phase D, Live Trading)
- Live trading at full model-calculated sizing
- Learning Loop V2 (ML) compounding insights
- Monthly live returns: approaching 10%+ target
- Shadow system confirming live vs. paper convergence
- System generating sufficient income to contribute meaningfully to household

---

## 9. Relationship to Existing Documents

This roadmap, if adopted, would supersede or amend the following:

| Document | Change Required |
|----------|----------------|
| **01_PROJECT_BIBLE.md** | New sections: Setup Quality Engine, Order Flow, NLP Catalyst Pipeline, Expanded Pattern Library, Dynamic Position Sizing. Update Strategy Roster (§4.2) from 5 to 15+. Update AI Layer (§9) from advisory to core brain. Update Multi-Asset Roadmap timing. |
| **02_PROJECT_KNOWLEDGE.md** | Major update to "Current Project State", "Key Decisions Made", sprint queue, architecture summary, monthly cost summary. |
| **03_ARCHITECTURE.md** | New module specs: SetupQualityEngine, OrderFlowAnalyzer, CatalystService, DynamicPositionSizer, PreMarketEngine, LearningLoop, PatternLibrary. Updated data flow diagram. New Event types. |
| **05_DECISION_LOG.md** | 6+ new DECs for decisions listed in §9. |
| **06_RISK_REGISTER.md** | New risks for expanded scope. Update existing assumptions about strategy count, data costs, AI Layer role. |
| **10_PHASE3_SPRINT_PLAN.md** | Sprints 23–36+ added to Build Track queue. Validation Track updated with Gates 3–5. |

**These updates should only be made after the meta-decision (§9, item 1) is confirmed.**

---

*End of Expanded Roadmap v1.0*
*Next: Review with Steven → decide on adoption → update core docs if yes → continue Sprint 20 regardless.*
