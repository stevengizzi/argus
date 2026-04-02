# ARGUS — UI/UX Feature Backlog

> Comprehensive inventory of UI/UX enhancements for the ARGUS Command Center.
> Originally extracted from design research (Feb 23, 2026). Major revision Feb 26, 2026: expanded from 4 to 7 pages (DEC-169), AI Copilot added (DEC-170), Sprint 21 split into 21a–21d (DEC-171), intelligence layer UI integration (DEC-168).
> Organized by sprint based on dependencies, effort, and impact.
> Referenced by: `project-knowledge.md`, `docs/roadmap.md`

---

## Design Vision & Principles

### The Vision: Ten-Page Command Center + AI Copilot

ARGUS's Command Center is a 10-page application with a contextual AI Copilot (DEC-170) accessible from every page. Each page has a focused purpose:

| Page | Purpose | Primary User Question |
|------|---------|----------------------|
| **Dashboard** | Ambient awareness | "How am I doing right now?" |
| **Trade Log** | Trade history | "What trades happened and why?" |
| **Performance** | Quantitative analytics | "How have I been performing, and where are the patterns?" |
| **The Arena** ✅ Sprint 32.75 | Real-time position monitoring | "What are all my open positions doing right now?" |
| **Orchestrator** | Operational control | "What is the system doing, why, and how do I change it?" |
| **Pattern Library** | Strategy encyclopedia | "How does each strategy work, and how has it performed?" |
| **The Debrief** | Knowledge accumulation | "What have I learned, and what should I review?" |
| **System** | Infrastructure health | "Is everything running correctly?" |
| **Observatory** | Pipeline visualization | "What is the pipeline doing with every symbol right now?" |
| **Experiments** ✅ Sprint 32.5 | Variant management | "How are my parameterized variants performing in shadow mode?" |

The **AI Copilot** is a persistent slide-out chat panel (desktop: right 35%, mobile: full-screen overlay) triggered by a floating button or `c` keyboard shortcut. Context-aware — automatically receives page context, selected entities, and system state.

### Design North Star

**"Bloomberg Terminal meets modern fintech app."** Information density of a professional trading terminal, with the visual craft and motion design of a consumer-grade app. Every pixel earns its place. Every animation serves an information purpose. The system should feel alive during market hours and calm during review sessions.

### Key Design Principles

1. **Information over decoration.** Every visual element communicates data. Color is semantic: green = positive/healthy, red = negative/loss, amber = warning/paper, blue = active/interactive.
2. **Ambient awareness.** Sparklines, gauges, and heatmaps provide trend information at a glance — the Dashboard should answer its question in under 2 seconds.
3. **Progressive disclosure.** Summary → detail → deep dive. Never force the user to leave context. Intelligence features enrich existing views (DEC-168) — quality scores appear as badges, not separate pages.
4. **Motion with purpose.** Every animation completes in <500ms and never blocks interaction. Staggered entries feel assembled. P&L flash confirms real-time data.
5. **Mobile as primary trading surface.** Steven trades US markets from Cape Town during afternoon/evening hours (3:30 PM – 11:00 PM local). The iPhone PWA is the primary monitoring interface during market hours.
6. **Research lab aesthetics.** ARGUS is a "strategy research laboratory that also trades live." Advanced visualizations (optimization landscapes, heatmaps, correlation matrices) feel like scientific tools.
7. **AI everywhere, not siloed (DEC-170).** The Copilot is contextual — it knows what page you're on and what you're looking at. No separate "AI page" exists.

### Navigation Structure (DEC-169)

**Desktop (icon sidebar):** Grouped by concern with subtle dividers.
- **Monitor:** Dashboard 📊 | Trades 📋 | Performance 📈
- **Operate:** Orchestrator 🎯 | Patterns 🧩
- **Observe:** Observatory 🔭
- **Learn:** Debrief 📚
- **Maintain:** System ⚙️

Keyboard shortcuts: `1`–`9` + `0` page navigation (0 = Experiments, 4 = The Arena), `Cmd+K` copilot, `w` watchlist toggle. Observatory internal: `f`/`m`/`r`/`t` for views, `[`/`]` for tiers, `Tab` for symbols, `Shift+R`/`Shift+F` for camera.

**Mobile (bottom tab bar):** 5 primary tabs + More menu.
- Tabs: Dashboard | Trades | Orchestrator | Patterns | More
- More menu: Performance | Debrief | System | Observatory

Copilot floating button on all surfaces, positioned above tab bar on mobile.

### Design Research Sources

Reference images from Sprint 15 design session (stored locally, referenced by number):
- **Images 1–4:** Bybit crypto exchange. Production trading, dark theme, multi-panel layouts.
- **Image 5:** Analytics dashboard with gradient bar chart and period selector.
- **Image 6:** Dark purple real-time dashboard. Donut progress indicators.
- **Image 7:** Mobile market view with candlestick chart and data grid.
- **Image 8:** Portfolio with card-as-hero pattern and embedded sparkline chart.
- **Image 9:** Gradient wallet with per-asset sparklines.
- **Image 10:** Tradix desktop dashboard with three-column layout.
- **Image 11:** Mount climbing metrics dashboard. Inspiration for Strategy Optimization Landscape.
- **Image 13:** Time-series heatmap with dot matrix. Inspiration for trade activity heatmaps.
- **Image 14:** Energy dashboard with multi-line flowing data. Inspiration for outcome projections.

---

## Priority Tiers

| Tier | Meaning | Criteria |
|------|---------|----------|
| **P0** | High impact, low effort | Enhances existing pages with minimal new infrastructure |
| **P1** | High impact, moderate effort | Requires new components or data sources but delivers clear value |
| **P2** | Medium impact, significant effort | New pages/views or complex visualizations |
| **P3** | Vision items | Multi-sprint efforts or dependent on future infrastructure |

---

## Current Baseline (Sprint 20 Complete)

As of Sprint 20 completion (Feb 26, 2026), the Command Center has 4 pages:

- **Dashboard:** Account equity, daily P&L, market status, open positions (real-time WS), recent trades, system health mini, CapitalAllocation (donut+bars), RiskGauge, MarketRegimeCard, Orchestrator Status strip, emergency controls (flatten/pause), SessionSummaryCard.
- **Trade Log:** Filtered trade history (strategy, outcome, date range), stats bar, paginated table, exit reason badges, trade detail slide-in panel.
- **Performance:** Period selector, 12-metric grid, equity curve (Lightweight Charts), daily P&L histogram, strategy breakdown.
- **System:** System overview, component health, strategy cards with parameters, per-strategy health (4 strategies), collapsible events log.
- **Cross-cutting:** Dark theme, icon sidebar (4 items, desktop/tablet), bottom tab bar (mobile), responsive at 393px/834px/1194px/1512px breakpoints, WebSocket real-time, JWT auth, dev mode with 4-strategy mock data, Framer Motion animations, skeleton loading, sparklines, CSV export, PWA, Tauri desktop shell.
- **Watchlist Sidebar:** Desktop inline 280px, tablet slide-out, mobile overlay. Single-letter strategy badges. VWAP distance metric. Sort controls.

---

## Completed Sprints (Historical Reference)

### Sprint 16 — Desktop/PWA + UX Polish ✅ COMPLETE

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| 16-A | Motion & Animation System (Framer Motion page transitions, stagger, chart draw-in, skeleton, number morph, P&L flash) | P0 | ✅ |
| 16-B | Micro-Interaction Polish (hover feedback, new trade slide-in, contextual empty states) | P0 | ✅ |
| 16-C | Hero Sparklines on Summary Cards (equity trend, intraday P&L, SPY movement) | P1 | ✅ |

### Sprint 17 — Orchestrator V1 ✅ COMPLETE

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| 17-A | Strategy Allocation Donut → CapitalAllocation (track-and-fill donut + stacked bars, SegmentedTab, Zustand, MarketRegimeCard) | P1 | ✅ Enhanced in Sprint 18.75 |
| 17-B | Segmented Controls with Live Counts (positions, trade log, system components) | P0 | ✅ |
| 17-C | Risk Utilization Gauge (daily/weekly loss budget, concentration) | P1 | ✅ |
| 17-D | Color-Coded Badge System (strategy, regime, risk, exit reason) | P0 | ✅ |

### Sprint 18–20 — New Strategies ✅ COMPLETE

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| 18-A | Positions as Cards with Mini-Charts | P1 | Deferred — table+timeline preferred |
| 18-B | Position Timeline (horizontal Gantt, strategy badges, time stops) | P1 | ✅ Sprint 18 |
| 18-C | Watchlist Sidebar (responsive, badges, VWAP distance, sort, collapse pill) | P1 | ✅ Sprint 19 (DEC-142, 147, 150) |
| 18-D | Session Summary Card (after-hours recap, dismissable) | P0 | ✅ Sprint 18 |
| 18-E | Notification Center (bell icon, alert history) | P1 | Deferred to Sprint 23+ |

---

## Sprint 21a — Pattern Library Page (NEW — DEC-169, DEC-171)

### 21a-A. Pattern Library Master-Detail Layout [P1]

**Strategy encyclopedia page.**
Left panel (35%): Strategy card grid. Each card shows: name, pipeline stage badge (color-coded: green=Active, blue=Paper, amber=Suspended, gray=Retired), operating time window, trade count (lifetime), win rate, net P&L, quality grade distribution mini-bar (appears when Quality Engine active, Sprint 25+).

Filterable by: pipeline stage (Active / Paper / Suspended / Retired / All), time window (Morning / Midday / Afternoon / All Day), pattern family (ORB family / Momentum / Reversal / Mean-Reversion).

Sortable by: name, P&L, win rate, trade count, most recent trade.

Right panel (65%): Tabbed strategy detail view with 5 tabs:
1. **Overview:** Strategy description, thesis, operating window, entry criteria checklist, exit rules, parameter table. Parameters editable via manual override (changes go through approval workflow when AI Layer active). Essentially the Strategy Spec Sheet rendered as an interactive UI panel.
2. **Performance:** Strategy-specific equity curve, P&L histogram, key metrics (Sharpe, PF, win rate, avg R), monthly P&L grid, performance by quality grade (Sprint 25+), performance by catalyst type (Sprint 23+). Comparative overlay with other strategies.
3. **Backtest:** Walk-forward results summary, VectorBT sweep heatmaps (interactive — hover for parameter combos), OOS vs IS comparison, walk-forward efficiency score. Link to full backtest report in The Debrief.
4. **Trades:** All trades taken by this strategy, sortable/filterable. Click opens Trade Detail slide-in panel.
5. **Intelligence (Sprint 25+):** Pattern strength scoring logic, how this pattern feeds Setup Quality Engine, historical win rate by quality grade for this pattern, Learning Loop insights specific to this pattern.

*Effort: ~14 hours. Master-detail layout, card grid, 5-tab system, multiple data source integrations.*

### 21a-B. Incubator Pipeline Visualization [P0]

**Strategy pipeline health at a glance.**
Horizontal pipeline at top of Pattern Library page showing all 10 incubator stages with dot/count indicators showing how many strategies are at each stage. Visual health check. Click a stage to filter the card grid below.

*Effort: ~3 hours. SVG pipeline component.*

### 21a-C. Stock/Asset Detail Panel [P1]

**Universal symbol deep-dive.**
Clicking any symbol anywhere in the app opens a slide-in panel (desktop: right 40%, mobile: full-screen bottom 90vh). Contains:

1. **Price & chart:** Current price, change, interactive candlestick chart (1m/5m/15m/1h/1D via Lightweight Charts), volume bars, VWAP/SMA overlays, opening range as shaded rectangle, entry/exit points as markers.
2. **Your trading history:** All trades on this symbol, win rate, avg R, total P&L, best/worst trade.
3. **Position detail (if open):** Current P&L, R-multiple, time in trade, stop/T1/T2 on chart.
4. **Fundamental context:** Market cap, sector, avg volume, relative volume, float, short interest.
5. **Quality score (Sprint 25+):** Full breakdown radar chart, grade badge, "Why this size?" section.
6. **Order flow (Sprint 24+):** L2 depth heatmap, flow quality indicator, tape speed.
7. **Catalyst (Sprint 23+):** Headlines, category badge, quality score, source link.
8. **Quick actions (future):** Close position, adjust stops, add to watchlist, flag for review.

*Effort: ~14 hours. Major component with chart integration and multiple progressive-disclosure sections.*

---

## Sprint 21b — Orchestrator Page (NEW — DEC-169, DEC-171)

### 21b-A. Three-Column Orchestrator Layout [P1]

**Desktop:** Capital & Allocation (30%) | Decision Stream (40%) | Risk & Controls (30%).
**Tablet:** Two columns (Allocation + Risk merged | Decisions).
**Mobile:** Single column, tabbed (Allocation | Decisions | Risk). Emergency controls pinned at bottom.

*Effort: ~4 hours. Responsive layout shell with tab navigation on mobile.*

### 21b-B. Decision Stream [P1]

**The Orchestrator's thought process, made visible.**
Live chronological feed of every Orchestrator decision: strategy activations/deactivations, throttle events, allocation changes, regime transitions, AI recommendations (Sprint 22+).

Each decision card: timestamp, action type icon, what happened, why (rationale text from Orchestrator decision logging), affected strategy, impact summary (e.g., "ORB allocation reduced 25% → 15% due to 3 consecutive losses").

Filterable by: decision type (allocation, throttle, regime, suspension, AI recommendation), strategy, time range.

AI recommendation cards (Sprint 22+) visually distinct — Claude icon, approve/reject/modify buttons inline.

Pre-market decisions highlighted: "Pre-market routine completed. 4 strategies activated. Regime: Bullish Trending. Allocation: ORB 25%, Scalp 25%, VWAP 25%, Afternoon 25%."

*Effort: ~8 hours. Decision card component, filter controls, existing API consumption (`/orchestrator/decisions`).*

### 21b-C. Capital Allocation Controls [P1]

**See and override the Orchestrator's capital decisions.**
CapitalAllocation visualization migrated from Dashboard (donut + bars). Plus NEW manual override controls:

- Default shows Orchestrator's calculated allocation per strategy.
- "Manual Override" toggle reveals per-strategy sliders (0–100% range).
- Diff display when overridden: "Orchestrator: 25% → You: 35%."
- Auto-revert timer option ("Reset to Orchestrator recommendations in 1 hour").
- Quality-weighted allocation breakdown (Sprint 25+): how much capital went to A+ vs B setups today.
- Opportunity cost log (Sprint 25+): A+ setups skipped due to capital constraints.

*Effort: ~8 hours. Migration + slider controls + diff display + override persistence.*

### 21b-D. Risk & Controls Column [P1]

**Risk visibility and emergency controls in one place.**
- **RiskGauge** (migrated from Dashboard): account daily/weekly loss consumed.
- **Risk waterfall chart:** Stacked bar showing risk budget consumption across tiers (strategy-level, cross-strategy, account-level). "If all stops hit" worst-case scenario.
- **Emergency controls** (migrated from Dashboard): Flatten All, Pause All (confirmation modals). Per-strategy pause/resume toggles. All controls JWT-gated.
- **Regime detail:** Current classification badge + component indicator gauges (SPY vs SMA-20/50, realized vol proxy, 5d ROC). Regime history timeline (last 5 trading days as color-coded strip).
- **Correlation matrix mini** (meaningful with 3+ strategies): pairwise return correlation heatmap.
- **Strategy Optimization Landscape placeholder** (activates Sprint 22 with AI Layer): 3D parameter surface.

*Effort: ~10 hours. Migration + risk waterfall + regime detail + correlation matrix.*

---

## Sprint 21c — The Debrief Page (NEW — DEC-169, DEC-171)

### 21c-A. Daily Briefings Section [P1]

**Pre-market and post-market reports, accumulated over time.**
Reverse-chronological list of all briefing documents. Each briefing is a timestamped, readable document card:

- **Pre-Market Briefing (Sprint 22+ auto-generated):** Regime forecast, ranked watchlist, catalyst summaries, key levels, AI commentary, suggested sizing.
- **EOD Report (Sprint 22+ auto-generated):** Trades taken (with quality grades), P&L, notable events, regime behavior, AI analysis of what went well/poorly, suggestions for tomorrow.
- **Manual entries:** User can add notes at any time (free-form markdown).

Structure: Date-grouped list. Expandable inline or full-view. Search by content. Filter by date range, type (Pre-Market / EOD / Weekly / Monthly / Manual).

Initially populated with placeholder content. AI Layer (Sprint 22) begins generating real briefings.

*Effort: ~8 hours. Document list, markdown viewer, CRUD, date grouping, search.*

### 21c-B. Research Library Section [P1]

**All ARGUS knowledge artifacts in one place.**
Document browser for all project research, reports, and analysis:

- Market data research report
- Execution broker research report
- Parameter validation reports
- Strategy spec sheets (linked from Pattern Library)
- Expanded roadmap
- Backtest result reports with interactive charts
- AI-generated analysis reports (Sprint 22+)

Each document rendered as a readable panel with markdown support. Taggable (Research / Analysis / Report / Strategy Spec / Backtest / Roadmap). Searchable. Filterable by type and date.

Import existing `docs/research/` and `docs/strategies/` files as seed content.

New documents can be generated on-demand via Copilot: "Analyze ORB performance for last 30 days" → saved here permanently.

*Effort: ~8 hours. Document management, markdown renderer, tag/filter system, seed import.*

### 21c-C. Learning Journal Section [P1]

**The qualitative knowledge base (Bible §16).**
Free-form entries with tags and entity links:

- **Manual observations:** "ORB seems to fail on ex-dividend dates."
- **AI-generated insights (Sprint 30+):** "Win rate drops 12% when VIX > 25."
- **Trade annotations:** Per-trade notes (linked to trade IDs). Can be added from Trade Detail panel or Copilot.
- **Pattern observations:** "Bull Flag + FDA catalyst = 80% win rate this month."
- **Weekly digest (Sprint 22+):** Claude-generated "What I Learned" summary.

Each entry: date, content (markdown), tags, linked entities (trade IDs, strategy IDs, symbols). Quick-add via Copilot from any page ("Remember that TSLA ORB entries are better after 10 AM").

*Effort: ~6 hours. Journal CRUD, entity linking, tag system, search.*

---

## Sprint 21d — Dashboard + Performance + System + Nav + Copilot Shell (DEC-169, DEC-171)

### 21d-A. Dashboard Scope Refinement [P0]

**Narrow to pure ambient awareness.**
Remove components migrated to Orchestrator:
- CapitalAllocation donut/bars → Orchestrator page
- Emergency controls (flatten all, pause all) → Orchestrator page
- Per-strategy pause/resume → Orchestrator page
- RiskGauge → Orchestrator page (keep compact risk budget % in Orchestrator Status strip)

Add:
- **Orchestrator Status strip** (top of page, single line): "4 strategies active | $24,500 deployed (24.5%) | Risk: 12% of daily budget | Regime: Bullish Trending". Click navigates to Orchestrator.
- **Pre-market mode:** Before 9:30 AM ET, Dashboard layout transforms to show pre-market content — ranked watchlist placeholder, regime forecast, catalyst summary area. Populated with real data when Pre-Market Engine (Sprint 23) and AI Layer (Sprint 22) are active.
- **Goal tracking indicator (21-J from original backlog):** Persistent widget: "Target: $5,000/month. Current: $3,200 (64%). 8 trading days remaining." Configurable. Motivational.
- **Weekly insight card (Sprint 30+):** One headline finding from Learning Loop.

*Effort: ~6 hours. Removal + strip + pre-market shell + goal tracker.*

### 21d-B. Performance Page Analytics [P1]

**Expanded analytics toolkit.**
All items from the original Sprint 21 UX Backlog that belong on Performance:

- **Trade Activity Heatmap (21-C):** Time-of-day × day-of-week D3 heatmap. Color by avg R-multiple or net P&L. Clickable cells filter trade log. Reveals patterns: "I make money 9:35–10:15 on Tues/Wed."
  *Effort: ~6 hours.*
- **Win/Loss Distribution Histogram (21-D):** R-multiple distribution (Recharts). Ideal: cutoff at -1R, positive skew, long right tail. Compare across strategies/periods/regimes.
  *Effort: ~4 hours.*
- **Portfolio Treemap (21-E):** D3 treemap — rectangles sized by capital, colored by P&L. Hover for tooltip, click for detail panel.
  *Effort: ~6 hours.*
- **Risk Waterfall Chart (21-F):** "If all stops hit" worst-case by position. Running total shows max drawdown scenario. (Also shown on Orchestrator page.)
  *Effort: ~4 hours.*
- **Comparative Period Overlay (21-G):** Ghost line on equity curve showing prior period. "Am I doing better this month than last?"
  *Effort: ~3 hours.*
- **Strategy Correlation Matrix (21-H):** Color-coded matrix of pairwise strategy return correlations. Low = good diversification. (Also shown mini on Orchestrator.)
  *Effort: ~6 hours.*
- **Trade Replay Mode (21-I):** Click any closed trade → animated candlestick walkthrough from entry to exit. Speed controls (1x/2x/5x). Stop/T1/T2 shown. The most powerful learning tool for building strategy intuition.
  *Effort: ~14 hours.*
- **Calendar P&L View:** Daily/weekly/monthly grid with color coding. Click a day to filter trade log.
  *Effort: ~4 hours.*
- **Performance by quality grade (Sprint 25+):** Are A+ setups outperforming? Chart + table.
- **Performance by catalyst type (Sprint 23+):** Which catalysts drive best results?
- **Performance by pattern type:** Which patterns earn most?
- **Quality calibration chart (Sprint 30+):** Predicted vs actual win rate by grade. From Learning Loop.

*Total effort for 21d-B: ~47 hours. This is the largest sub-component.*

### 21d-C. System Page Cleanup [P0]

**Narrow to infrastructure health only.**
Remove components migrated elsewhere:
- Strategy cards (parameters, status) → Pattern Library
- Strategy pause/resume controls → Orchestrator
- Strategy activation/deactivation → Orchestrator

Add placeholder health cards for future intelligence components (show "Not Yet Active" until respective sprint):
- Pre-Market Engine health (Sprint 23)
- Order Flow Analyzer health (Sprint 24)
- Catalyst Service health (Sprint 23)
- Learning Loop status (Sprint 30)

Keep: System overview (uptime, mode, data/broker sources), component health grid, Databento/IBKR connection health, collapsible events log.

*Effort: ~3 hours. Removal + placeholder cards.*

### 21d-D. Seven-Page Nav Restructure [P0]

**Desktop:** Icon sidebar expands from 4 to 7 items with group dividers (Monitor | Operate | Learn | Maintain). Active page indicator. Subtle group labels or divider lines.

**Mobile:** Bottom tab bar changes from 4 tabs to 5 + More menu. Dashboard | Trades | Orchestrator | Patterns | More (→ Performance, Debrief, System). More menu as bottom sheet or dropdown.

Keyboard shortcuts extended: `1`–`7` for pages, `c` for copilot, `w` for watchlist (unchanged).

Watchlist sidebar position unchanged — available on all pages via `w` toggle.

React Router updates: 7 routes, lazy-loaded page components.

*Effort: ~5 hours. Nav refactor, More menu, routing, active indicators.*

### 21d-E. AI Copilot Shell [P1]

**Chat panel ready for Sprint 22 activation.**
- **Floating button:** Bottom-right corner on desktop, above tab bar on mobile. Subtle pulse animation on first visit. Keyboard shortcut `c`.
- **Slide-out panel:** Desktop: right side, 35% width, overlays content. Mobile: full-screen overlay from bottom.
- **Panel structure:** Header (context indicator showing current page name + selected entity if any), scrollable message area, text input with send button.
- **Placeholder state:** "AI Copilot activating in Sprint 22. Soon you'll be able to chat with Claude here — contextual, page-aware, with full system knowledge."
- **Panel remembers open/closed state** within session (Zustand).
- **Keyboard shortcut `c`** toggles panel (suppressed in input/textarea).

*Effort: ~5 hours. Panel shell, floating button, slide-out animation, context indicator.*

### 21d-F. Heat Strip Portfolio Bar [P0]

**Single-line portfolio health indicator.**
Horizontal bar at top of Dashboard (below Orchestrator Status strip) divided into segments for each open position. Width = capital allocation, color = P&L (green gradient to red). One glance = portfolio health. Hover for tooltip. Click opens position detail.

*Effort: ~2 hours. Simple SVG/div component.*

---

## Sprint 22 — AI Layer MVP + Copilot Activation (DEC-096, DEC-098, DEC-170)

### 22-A. AI Copilot Full Activation [P1]

**Claude comes alive in the chat panel.**
- Full chat functionality: message send/receive with streaming responses.
- Context injection per page: Dashboard → positions/P&L/regime. Orchestrator → allocation/decisions/risk. Pattern Library → selected strategy. The Debrief → current document. Trade Detail → full trade data.
- Message history persistence (stored in Debrief Learning Journal database).
- Action proposals appear as special message types with approve/reject/modify buttons.
- Claude can: answer questions about any system data, generate reports (saved to Debrief), propose parameter changes, propose allocation overrides, annotate trades, explain Orchestrator decisions.

*Effort: ~8 hours (UI). Backend API handled by Sprint 22 core scope.*

### 22-B. AI Insight Cards [P1]

**Claude-generated observations embedded in Dashboard.**
Cards that appear on Dashboard with AI analysis: "Your win rate on AMD is 75% — significantly above 60% average. Consider increasing allocation." or "Last 3 losses were all TIME exits on Fridays — consider tightening time stops on Fridays."

Dismissable. Can be pinned to Learning Journal via one click.

*Effort: ~6 hours.*

### 22-C. Pre-Market Briefing Generation [P1]

**Automated briefing populates Dashboard pre-market mode and The Debrief.**
Claude generates pre-market briefing from overnight data: regime assessment, ranked watchlist with catalyst summaries, key levels, suggested position sizes. Delivered at configurable time (default 8:00 AM ET / 2:00 PM Cape Town during EDT). Push notification to mobile.

Briefing appears in: Dashboard pre-market mode (live), The Debrief briefings section (stored permanently).

*Effort: ~4 hours (UI). Generation logic in Sprint 22 backend.*

### 22-D. EOD Report Generation [P1]

**Claude analyzes the trading day.**
End-of-day report: trades taken (with quality grades when available), P&L summary, notable events, regime behavior, what went well/poorly, suggestions for tomorrow. Auto-generated after market close. Stored in The Debrief.

*Effort: ~4 hours (UI).*

### 22-E. Strategy Optimization Landscape [P3]

**"Climbing the mountain" visualization (image 11 inspired).**
3D topographic surface on Orchestrator page: X/Y = two strategy parameters, elevation/color = Sharpe ratio from walk-forward. Current parameter set as a marker. Shows if you're near the peak, if the peak is broad (robust) or narrow (fragile).

AI Layer annotates with recommendations: "Moving from 2R to 2.5R target improves Sharpe by 15%."

*Effort: ~20+ hours. Three.js or Plotly 3D surface. Showpiece feature.*

### 22-F. Multi-Line Outcome Projections [P2]

**Projected vs actual equity curves (image 14 inspired).**
On Performance page:
- Current trajectory (extrapolated)
- Best/worst case scenarios
- Monte Carlo confidence bands (10th/50th/90th percentile)
- Vertical milestone markers ("100 trades", "6 months live")
- Actual equity draws itself over time against projections

*Effort: ~12 hours. Monte Carlo simulation, multi-series chart.*

---

## Sprint 23.5 — Catalyst Pipeline UI (DEC-164, DEC-168, DEC-300–307)

### 23-A. CatalystBadge Component [P0] ✅ Sprint 23.5

**Category-colored badges for catalyst types.**
CatalystBadge component displays catalyst category with semantic colors: earnings (blue), insider (purple), guidance (green), analyst (amber), regulatory (red), partnership (teal), product (pink), restructuring (gray). Used in CatalystAlertPanel and IntelligenceBriefView.

*Delivered: Sprint 23.5 S5.*

### 23-B. CatalystAlertPanel [P1] ✅ Sprint 23.5

**Real-time catalyst notifications panel.**
Alert panel showing latest catalysts with category badges, headlines, and timestamps. Supports filtering by category. Progressive disclosure: badge → headline → full catalyst detail.

*Delivered: Sprint 23.5 S5.*

### 23-C. IntelligenceBriefView [P1] ✅ Sprint 23.5 (DEC-307)

**Intelligence tab in The Debrief page.**
Fourth tab in The Debrief showing pre-market intelligence briefings. Three-column layout: briefing list (left), detail view (center), catalyst summary (right). BriefingCard component with expand/collapse and markdown rendering. Generate button triggers new briefing creation.

*Delivered: Sprint 23.5 S6.*

### 23-D. TanStack Query Hooks [P0] ✅ Sprint 23.5 (DEC-305)

**Data hooks for catalyst and briefing data.**
`useCatalysts(symbol?, category?, since?)`, `useIntelligenceBriefings(limit?, since?)`, `useIntelligenceBriefing(id)`. Follows established patterns: 60s stale time for catalysts, 5min for briefings, retry with exponential backoff.

*Delivered: Sprint 23.5 S5.*

### 23-E. Dashboard Pre-Market Mode — Live Data [P1] — DEFERRED

**Pre-market layout populated with real data.**
Dashboard pre-market mode (shell from 21d) to show live ranked watchlist from PreMarketEngine, catalyst summaries from CatalystPipeline, regime forecast from RegimeClassifier. Deferred until PreMarketEngine implemented (Sprint 24+).

*Effort: ~4 hours. Data wiring to existing pre-market shell.*

### 23-F. Watchlist Catalyst Badges [P1] — DEFERRED

**Catalyst badges on watchlist items.**
Each watchlist symbol gains catalyst badge showing latest catalyst category. Deferred until watchlist + catalyst data integration (Sprint 24+).

*Effort: ~3 hours. Badge integration with existing watchlist.*


### 23-G. Trade Detail Panel — Catalyst Section [P1] — DEFERRED

**Catalyst context in trade deep-dive.**
New section in Stock/Asset Detail Panel: catalyst headline, category, quality score, source link. Deferred until trade-catalyst linking implemented (Sprint 24+).

*Effort: ~3 hours. New section in existing panel.*

### 23-H. Performance — By Catalyst Type [P1] — DEFERRED

**Which catalysts produce the best trades?**
New chart on Performance page: win rate, avg R, total P&L broken down by catalyst category. Deferred until sufficient catalyst-tagged trades exist.

*Effort: ~4 hours. New chart + API aggregation.*

### 23-I. Floating Action Context [P1] — DEFERRED

**Contextual action toolbar.**
When hovering/selecting a position or trade, floating toolbar appears. Deferred to UX polish sprint.

*Effort: ~4 hours. Floating toolbar with position-aware placement.*

### 23-F. Collapsible Sections with Memory [P0]

**Persistent UI state.**
Sections remember collapsed/expanded state across sessions (Zustand persist). Filter settings persist on Trades page. Dashboard widget arrangement saves.

*Effort: ~3 hours. Zustand persist integration.*

### 23-J. Catalyst Endpoint Short-Circuit [P0] — DEF-041

**Skip catalyst requests when pipeline is disabled.**
TanStack Query hooks (`useCatalysts`) should check pipeline status before issuing per-symbol `GET /api/v1/catalysts/{symbol}` requests. Currently fires 15+ requests that all return 503 when `catalyst.enabled: false`. Check via `/api/v1/health` component status or a dedicated `/api/v1/catalysts/status` endpoint. Return empty state immediately when pipeline is disabled.

*Discovered: March 12, 2026 live QA. Effort: ~1 hour.*

---

## Sprint 24 — Order Flow UI (DEC-165, DEC-168)

### 24-A. Watchlist Flow Indicator [P0]

**Order flow quality at a glance.**
Each watchlist item gains a small dot indicator: green (strong buy flow), yellow (neutral), red (sell pressure). Derived from OrderFlowAnalyzer composite score.

*Effort: ~2 hours. Dot component + OrderFlowEvent subscription.*

### 24-B. Stock Detail Panel — L2 Depth Heatmap [P1]

**Order flow visualization in symbol deep-dive.**
New section in Stock/Asset Detail Panel: L2 depth heatmap showing bid/ask size at each price level. Color intensity = size. Updates in real-time. Plus: imbalance ratio gauge, tape speed indicator, flow score.

*Effort: ~8 hours. Custom heatmap component + real-time data subscription.*

### 24-C. Trade Detail — Entry Flow Snapshot [P1]

**What did order flow look like at entry?**
Snapshot of L2 state at trade entry time, stored with trade data. Shows in Trade Detail panel. Helps post-trade analysis: "Was there real buying pressure, or did I enter into absorption?"

*Effort: ~4 hours. Snapshot capture + storage + panel section.*

---

## Sprint 25 — The Observatory ✅ COMPLETE (March 18, 2026)

Observatory page (Command Center page 8) with 4 views, detail panel, session vitals, and debrief mode. See `docs/architecture.md` §13 for full technical details.

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| 25-A | Funnel View (Three.js 3D — translucent cone, InstancedMesh particles, CSS2DRenderer labels) | P1 | ✅ Sprint 25 S6a–S6b |
| 25-B | Radar View (Three.js camera animation — shared scene with Funnel, bottom-up perspective) | P1 | ✅ Sprint 25 S7 |
| 25-C | Matrix View (condition heatmap, virtual scrolling, Tab navigation) | P1 | ✅ Sprint 25 S5a–S5b |
| 25-D | Timeline View (SVG strategy lanes, 9:30–4:00 ET, 4 severity levels) | P1 | ✅ Sprint 25 S8 |
| 25-E | Detail Panel (condition grid, candlestick chart, strategy history, quality/catalyst) | P1 | ✅ Sprint 25 S4a–S4b |
| 25-F | Session Vitals + Debrief Mode (live metrics, date picker, 7-day history) | P1 | ✅ Sprint 25 S9 |
| 25-G | Backend (ObservatoryService, 4 REST endpoints, Observatory WebSocket) | P1 | ✅ Sprint 25 S1–S2 |
| 25-H | Keyboard Navigation (f/m/r/t views, [/] tiers, Tab symbols, Shift+R/F camera) | P0 | ✅ Sprint 25 S3+S3f |

### Quality Engine UI (originally planned for Sprint 25, delivered Sprint 24/24.1)

| ID | Feature | Priority | Status |
|----|---------|----------|--------|
| Q-A | Quality Grade Badges (QualityBadge, trades table, dashboard) | P0 | ✅ Sprint 24 S6b + 24.1 S4b |
| Q-B | Trade Detail Panel — Quality Breakdown (SignalDetailPanel, quality score) | P1 | ✅ Sprint 24.1 S4b |
| Q-C | Performance — By Quality Grade (QualityGradeChart, QualityOutcomeScatter) | P1 | ✅ Sprint 24.1 S4a |
| Q-D | Orchestrator — Quality-Weighted Allocation | P1 | Deferred to Sprint 26+ |

---

## Sprint 30 — Learning Loop UI (DEC-163, DEC-168)

### 30-A. Performance — Quality Calibration Chart [P1]

**Predicted vs actual win rate by grade.**
The single most important Learning Loop output. Two-line chart: what the model predicted (grade-based expected win rate) vs what actually happened. If lines converge, scoring is well-calibrated. If they diverge, model needs adjustment.

*Effort: ~4 hours. Two-line chart + calibration API.*

### 30-B. Dashboard — Weekly Insight Card [P0]

**One headline finding from the Learning Loop.**
Small card on Dashboard: "This week's top finding: VWAP Reclaim win rate improves 18% when VIX < 20." Links to full insights in The Debrief Learning Journal.

*Effort: ~2 hours. Insight card + API endpoint.*

### 30-C. System — Learning Loop Health [P0]

**Model monitoring.**
New health card on System page: last retrain date, model version, convergence status, next retrain scheduled. Replaces "Not Yet Active" placeholder from Sprint 21d.

*Effort: ~2 hours. Health card + API.*

---

## Sprint 23+ — Future Enhancements (Backlog)

### Strategy Activity Feed [P1]
Live stream of per-symbol, per-strategy state showing the system's reasoning in real time. Replaces the "black box" gap between "scanning for setups" and "trade executed." Each active strategy reports its current state for each watchlist symbol:
- ORB: `NVDA — WATCHING (price within OR, no breakout yet)` → `NVDA — BREAKOUT (close > OR high, checking volume...)`
- VWAP Reclaim: `GOOGL — ABOVE_VWAP (waiting for dip)` → `GOOGL — PULLBACK (below VWAP 2m ago)` → `GOOGL — RECLAIM_CANDIDATE (crossed back above)`
- Afternoon Momentum: `TSLA — ACCUMULATING (14 bars, range/ATR 0.62)` → `TSLA — CONSOLIDATED (28 bars, watching for breakout)`

**Backend:** New endpoint `GET /api/v1/strategies/activity` returns current state per symbol per strategy. Strategies already track this state internally (state machines in VWAP Reclaim and Afternoon Momentum, OR tracking in ORB family) — just needs to be exposed via API.

**Frontend — Dashboard:** Compact card showing top 3–5 most interesting symbols (closest to triggering, or in advanced states). Answers "what is the system watching right now?" at a glance.

**Frontend — Orchestrator:** Full activity feed with all symbols × all strategies. Filterable by strategy, state, symbol. Complements (not replaces) the Decision Timeline, which shows orchestrator-level events. The Activity Feed shows strategy-level reasoning.

**Progressive disclosure:** Symbol row click → opens SymbolDetailPanel (already built, DEC-177) with strategy state context.

**Note:** Does NOT require AI layer — purely exposes existing strategy state machines. Could be pulled forward to Sprint 22 alongside AI Copilot activation, since the Copilot could reference this same state data for contextual answers.
*Effort: ~8–12 hours (backend 3–4h, Dashboard card 2–3h, Orchestrator feed 3–5h).*

### Allocation Sunburst [P2]
Concentric ring chart: outer = strategy allocation, inner = positions within each strategy. Color by P&L. D3 sunburst.
*Effort: ~6 hours.*

### Market Regime Timeline [P1]
Historical regime changes as horizontal color-coded strip with equity curve overlay. Which regimes favor which strategies?
*Effort: ~6 hours.*

### Symbol Performance Heatmap [P1]
Symbol × time period matrix. Color = P&L magnitude. Reveals consistent winners and losers.
*Effort: ~4 hours.*

### Configurable Dashboard Grid [P3]
Drag-and-drop dashboard widget arrangement. Layout presets (Market Hours, Review Mode, Mobile). React-grid-layout.
*Effort: ~15+ hours.*

### Notification Center [P1]
Bell icon with alert history. Collects trade executions, system warnings, AI recommendations. Badge for unread. Slide-down panel.
*Effort: ~5 hours.*

### Performance Workbench (DEC-229)
Refactor Performance page from fixed 5-tab layout to customizable widget grid using `react-grid-layout`. Stage 1: resize/rearrange widgets within existing tabs, layout persistence via backend API, per-widget min/max size constraints. Stage 2: widget palette/sandbox, custom tab CRUD (add/rename/delete), drag-from-palette, mobile fallback (fixed stack per tab). Backend endpoint for layout serialization.
**Dependencies:** All 8 Performance visualizations complete (DEC-205).
**Resolves:** DEC-229. Supersedes DEC-218 (fixed tab layout).

---

## Summary by Sprint

| Sprint | Items | Est. Hours | Theme |
|--------|-------|-----------|-------|
| **16** ✅ | Motion, micro-interactions, sparklines | ~15h | Polish & perceived quality |
| **17** ✅ | Donut/bars, tabs, gauges, badges | ~11h | Multi-strategy awareness |
| **18–20** ✅ | Timeline, watchlist, session summary | ~11h | Multi-strategy operations |
| **21a** ✅ | Pattern Library page (master-detail, pipeline, stock detail panel) | ~31h | Strategy encyclopedia |
| **21b** ✅ | Orchestrator page (3-column, decisions, allocation, risk) | ~30h | Operational command center |
| **21c** ✅ | The Debrief page (briefings, research, journal) | ~22h | Knowledge accumulation |
| **21d** ✅ | Dashboard + Performance analytics + System + Nav + Copilot shell | ~68h | Architecture + analytics |
| **22** | Copilot activation, AI insight cards, briefings, EOD, optimization landscape, projections | ~54h | AI-enhanced visualization |
| **22+** | Strategy Activity Feed | ~8–12h | Real-time strategy reasoning visibility |
| **23.5** ✅ | CatalystBadge, CatalystAlertPanel, IntelligenceBriefView, TanStack Query hooks | ~12h | Catalyst intelligence UI foundation |
| **23+** | Sunburst, regime timeline, symbol heatmap, configurable grid, notifications | ~36h | Refinement & customization |
| **24** | Flow indicator, L2 heatmap, entry snapshot | ~14h | Order flow UI |
| **25** ✅ | Observatory page (4 views, detail panel, vitals, debrief mode, Three.js 3D) | ~14 sessions | Pipeline visualization |
| **32.5** ✅ | Experiments page (9th page), Shadow Trades tab on Trade Log, Experiments variants/promotions UI | ~11 Vitest | Experiment pipeline visibility |
| **32.75** ✅ | The Arena (10th page), strategy identity system (colors/badges/letters), Dashboard overhaul, Arena REST + WS, AI Copilot context, catalyst links, TradeChart dedup | ~94 Vitest | Real-time position monitoring |
| **32.8** ✅ | Arena TickEvent subscription (latency fix), arena_tick_price, pre-market candles, VitalsStrip, Dashboard 4-row layout, Trades unified styling + Shadow Trades features (outcome toggle, time presets, infinite scroll, sortable columns) | ~41 Vitest | Arena latency + daily operations polish |
| **30** | Calibration chart, weekly insight, learning loop health | ~8h | Learning loop UI |

---

## Implementation Notes

### Animation Library Stack
- **Framer Motion:** Page transitions, stagger orchestration, panel slide-in/out.
- **CSS transitions:** Hover effects, micro-interactions, badge animations.
- **Lightweight Charts native:** Chart draw-ins, candlestick animations.
- Budget: <500ms per animation, 60fps, never blocks interaction.

### Chart Library Stack
- **Lightweight Charts** (integrated): Equity curves, candlestick, area, histograms.
- **Recharts** (integrated): Donut/bar charts, radar charts, simple histograms.
- **D3** (Sprint 21d+): Treemaps, heatmaps, correlation matrices, sunbursts. Use sparingly.
- **Three.js r128** (Sprint 25): Observatory Funnel/Radar 3D views. Code-split via React.lazy. InstancedMesh for symbol particles, CSS2DRenderer for labels. Shared-scene pattern (Funnel+Radar share one scene with camera presets).

### Mobile-First Patterns
- Detail panels → full-screen modals on mobile
- Side-by-side → stacked vertical
- Complex charts → simplified with tap-to-expand
- Hover interactions → long-press or tap
- Floating toolbars → bottom sheet actions
- More menu for pages 6–7

### Performance Budgets
- Dashboard renders interactive in <1 second on LAN
- Animations never drop below 60fps
- Charts with >1000 data points use canvas (not SVG)
- WebSocket updates batch via requestAnimationFrame (rAF batching used in Arena WS — Sprint 32.75)
- Any hook that creates a real `WebSocket` in jsdom must be mocked with `vi.mock()` in test files; `vitest.config.ts` uses `testTimeout: 10_000` + `hookTimeout: 10_000` as safety net (Sprint 32.8)
- AI Copilot streams partial responses immediately

---

## Deferred Items From Sprint 32.8

### DEF-139 — Startup zombie flatten queue not draining at market open [MEDIUM]
Pre-market zombie positions queued in `_startup_flatten_queue` may not drain correctly at market open if the Order Manager poll loop timing doesn't align with the 9:30 ET check. Deferred to dedicated operational fixes sprint. Location: `argus/execution/order_manager.py` — `_drain_startup_flatten_queue()`.

### DEF-140 — EOD flatten reports positions closed but broker retains them [MEDIUM]
EOD flatten Pass 1 may log a successful close but the broker (IBKR paper) retains the position in some edge cases. Pass 2 (broker-only sweep) intended to catch this but timing issues may cause false-positives. Deferred to dedicated operational fixes sprint. Location: `argus/execution/order_manager.py` — `eod_flatten()`.

### Outstanding Code-Level Items (Low Priority)
- Live Trades quick filter missing no-op guard on double-click (`TradeFilters.tsx` — `handleQuickFilter`)
- `todayStats.trade_count` capped at 1000 by backend query — Dashboard summary API
- Shadow Trades outcome counts reflect loaded pages only (intentional judgment call, not a bug)
- Shadow `tbody` has `opacity-80`, Live does not (intentional visual differentiation)

### Window summary wiring — BaseStrategy subclasses [LOW]
`BaseStrategy._log_window_summary()` and helpers are implemented but not yet wired into any of the 12 strategy subclasses. Wiring touches all 12 strategies + tests. Deferred to a dedicated sprint. This would provide per-session evaluation coverage metrics in logs.