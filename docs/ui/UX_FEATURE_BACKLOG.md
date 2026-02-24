# ARGUS — UI/UX Feature Backlog

> Comprehensive inventory of UI/UX enhancements extracted from design research (Feb 23, 2026).
> Organized by recommended sprint/phase based on dependencies, effort, and impact.
> Reference images: Bybit exchange (images 1–4), analytics dashboards (5–6), mobile trading apps (7–9), desktop dashboards (10–11), data visualizations (12–14).
> Referenced by: `02_PROJECT_KNOWLEDGE.md`, `10_PHASE3_SPRINT_PLAN.md`

---

## Design Vision & Principles

This document was born from the Sprint 15 code review, where all 4 Command Center pages (Dashboard, Trade Log, Performance, System) were reviewed across 3 devices (MacBook, iPad, iPhone — 20 screenshots total). The review confirmed that the foundation is solid, visually consistent, and responsive. The question shifted from "does it work?" to "how do we make it feel like a premium, crafted tool that puts Steven in flow state during trading sessions?"

### The Gap: Status Page → Command Center

The current Dashboard reads as a **status page** — you observe the system. The vision is a **command center** — you make decisions from it. The Bybit Home screen (image 4) exemplifies this: portfolio, watchlist with sparklines, P&L breakdown, activity heatmap, positions, risk overview, platform health — all on one screen, all actionable.

### Design North Star

**"Bloomberg Terminal meets modern fintech app."** Information density of a professional trading terminal, with the visual craft and motion design of a consumer-grade app. Every pixel earns its place. Every animation serves an information purpose. The system should feel alive during market hours — prices updating, charts drawing, P&L flashing — and calm during review sessions.

### Key Design Principles

1. **Information over decoration.** Every visual element communicates data. Gradients and glassmorphism are rejected in favor of clear data hierarchy. Color is semantic: green = positive/healthy, red = negative/loss, amber = warning/paper, blue = active/interactive.
2. **Ambient awareness.** Sparklines, gauges, and heatmaps provide trend information at a glance — you shouldn't need to navigate to a detail page to know if things are going well. The Dashboard should answer "how am I doing?" in under 2 seconds.
3. **Progressive disclosure.** Summary → detail → deep dive. Dashboard gives the overview. Click to open a detail panel (slide-in, not full navigation). Click again for full-page analysis. Never force the user to leave context.
4. **Motion with purpose.** Staggered entry animations make the app feel assembled. Chart draw-ins direct attention. P&L flash confirms real-time data flow. But every animation completes in <500ms and never blocks interaction.
5. **Mobile as primary trading surface.** Steven trades US markets from Taipei during overnight hours (10:30 PM – 5:00 AM local). The iPhone PWA is the primary monitoring interface during market hours. Every feature must have a mobile adaptation that doesn't lose critical information.
6. **Research lab aesthetics.** ARGUS is a "strategy research laboratory that also trades live." Sprint 21+ visualizations (optimization landscapes, heatmaps, correlation matrices) should feel like scientific tools, not consumer dashboards. Think academic paper figures with interactive capabilities.

### Design Research Sources

The following reference materials informed this backlog. The images are stored locally and referenced by number throughout this document:

- **Images 1–4:** Bybit crypto exchange (Orders, Portfolio, Trade, Home). Production trading platform with high information density, dark theme, position management, and multi-panel layouts.
- **Image 5:** Analytics dashboard with gradient bar chart and period selector. Consumer-oriented aesthetic — rejected for core UI but period selector pattern noted.
- **Image 6:** Dark purple real-time dashboard. Donut progress indicators noted as a pattern for risk utilization gauges.
- **Image 7:** Mobile market view with candlestick chart and data grid. Relevant for future symbol detail view on mobile.
- **Image 8:** Portfolio with card-as-hero pattern and embedded sparkline chart. Applicable to position cards.
- **Image 9:** Gradient wallet with per-asset sparklines. Inline sparkline pattern noted; gradient aesthetic rejected.
- **Image 10:** Tradix desktop dashboard with three-column layout. Right-side detail panel pattern noted.
- **Image 11:** Mount climbing metrics dashboard. Mixed visualization types in consistent card grid. Inspiration for Strategy Optimization Landscape ("climbing the mountain toward max profit").
- **Image 12:** Information design / streaming services comparison. Data-art — not directly applicable.
- **Image 13:** Time-series heatmap with dot matrix. Inspiration for trade activity heatmaps (time-of-day × day-of-week).
- **Image 14:** Energy dashboard with multi-line flowing data and vertical checkpoints. Inspiration for multi-line outcome projections (projected vs actual equity curves with milestone markers).

### Sprint 15 Baseline (What Exists Today)

As of Sprint 15 completion (Feb 23, 2026), the Command Center has:

- **Dashboard:** Account equity, daily P&L, market status, open positions table (real-time WS prices), recent trades list, system health mini-display.
- **Trade Log:** Filtered trade history (strategy, outcome, date range), stats bar (trades/win rate/net P&L), paginated table with exit reason badges (T2/SL/TIME/EOD).
- **Performance:** Period selector (Today/Week/Month/All), 12-metric grid, equity curve (Lightweight Charts area), daily P&L histogram (Lightweight Charts), strategy breakdown table.
- **System:** System overview (uptime, mode, sources), component health status, strategy cards with parameters, collapsible events log.
- **Cross-cutting:** Dark theme, icon sidebar nav (desktop/tablet), bottom tab bar (mobile), responsive at 393px/834px/1194px/1512px breakpoints, WebSocket real-time updates, JWT auth, dev mode with mock data.
- **Known defect:** Win rate in Performance → "By Strategy" table displays raw decimal (0.62%) instead of percentage (62%). Fix pending.

---

## Priority Tiers

| Tier | Meaning | Criteria |
|------|---------|----------|
| **P0** | High impact, low effort | Enhances existing pages with minimal new infrastructure |
| **P1** | High impact, moderate effort | Requires new components or data sources but delivers clear value |
| **P2** | Medium impact, significant effort | New pages/views or complex visualizations |
| **P3** | Vision items | Multi-sprint efforts or dependent on future infrastructure |

---

## Sprint 16 — Desktop/PWA (Add-ons)

These are low-effort enhancements that improve perceived quality without new data or infrastructure. They enhance what Sprint 15 already built.

### 16-A. Motion & Animation System [P0]

**Staggered entry animations**
Each card/section fades in with a subtle upward translate (12–20px), staggered by 50–80ms per element. Dashboard loads top-to-bottom, left-to-right. Makes the app feel assembled rather than stamped.
*Effort: ~2 hours. CSS keyframes + stagger delays on existing components.*

**Chart draw-in animations**
Equity curve line draws left-to-right on page load (~500ms). Daily P&L histogram bars grow upward from zero line. Only fires on initial page load, not on live data updates.
*Effort: ~1 hour. Lightweight Charts supports animation options natively.*

**Page transitions**
Subtle cross-fade (150–200ms) between pages. Outgoing page fades slightly, incoming page fades in with a small slide. Framer Motion or CSS transitions on React Router outlets.
*Effort: ~2 hours. Wrap route outlet in AnimatePresence.*

**Skeleton loading states**
Gray placeholder shapes matching actual layout (card outlines, chart rectangle, table rows) with a subtle shimmer pulse. Real data fades in on top when API responds.
*Effort: ~3 hours. One Skeleton component, applied to each page.*

**Number morphing / P&L flash**
When a price or P&L value updates via WebSocket, the number briefly flashes green (up) or red (down) and then settles. Key metrics like Account Equity can do a digit-rolling animation.
*Effort: ~2 hours. CSS transition on color + brief scale pulse.*

### 16-B. Micro-Interaction Polish [P0]

**Hover feedback on cards**
Cards lift slightly on hover (1px translate-y + subtle box-shadow increase). Table rows highlight smoothly. Nav items animate underline/background.
*Effort: ~1 hour. Tailwind + transition utilities.*

**New trade slide-in**
When a new trade appears in the Recent Trades list (via WebSocket), it slides in from the top with a brief highlight glow, then settles.
*Effort: ~1 hour. CSS animation on list insert.*

**Contextual empty states**
Replace generic "No data" with helpful messages: "No open positions — market opens in 6h 23m", "No trades today — opening range forms at 9:35 AM ET", "No losing trades this week ✓". Adds personality without adding data dependencies.
*Effort: ~2 hours. Conditional rendering in each section's empty state.*

### 16-C. Hero Sparklines on Summary Cards [P1]

**Dashboard summary cards with inline sparklines**
Each top-level card gets a tiny sparkline:
- Account Equity → 30-day equity trend
- Daily P&L → intraday P&L curve
- Market Status → SPY intraday movement (placeholder until real data)

Uses Lightweight Charts or a simple SVG sparkline component. Data comes from existing API endpoints (equity curve data, daily P&L).
*Effort: ~4 hours. New SparklineChart component + API data wiring.*

---

## Sprint 17 — Orchestrator V1 (Add-ons)

Orchestrator introduces multi-strategy coordination, which unlocks several new visualization needs.

### 17-A. Strategy Allocation Donut [P1]

**Capital allocation visualization**
Donut chart on Dashboard showing capital distributed across strategies, colored by each strategy's P&L contribution. Click a segment to filter the dashboard to that strategy. Becomes meaningful once Orchestrator is allocating capital to 2+ strategies.
*Effort: ~4 hours. Recharts or D3 donut component.*

### 17-B. Segmented Controls with Live Counts [P0]

**Tab badges pattern**
Bybit-style "Positions 4 | Open orders 13" segmented tabs. Apply to:
- Dashboard positions: "Open 3 | Closed 17"
- Trade Log outcomes: "Wins 12 | Losses 8 | BE 0" (counts update with filters)
- System components: "Healthy 5 | Degraded 0 | Down 0"
*Effort: ~2 hours. Reusable SegmentedTab component.*

### 17-C. Risk Utilization Gauge [P1]

**Radial/donut progress indicator**
Shows how much of daily risk budget has been consumed. If daily loss limit is 3% and you've lost 1.2%, gauge shows 40% filled. Color transitions from green → yellow → red as utilization increases.
Secondary gauges for: weekly loss limit, single-stock concentration (approaching 5% limit), margin utilization.
*Effort: ~3 hours. Reusable RadialGauge component. Data from Risk Manager via API.*

### 17-D. Color-Coded Badge System [P0]

**Extended badge vocabulary**
Expand beyond exit reason badges to include:
- Strategy badges on trades (ORB = blue, Scalp = purple, VWAP = teal, etc.)
- Market regime badges on dashboard (Bullish Trending = green, Range-Bound = yellow, etc.)
- Risk level badges on positions (Normal = green, Approaching Limit = yellow, At Limit = red)
- Leverage/sizing indicators if applicable
*Effort: ~2 hours. Badge component variants + color mapping config.*

---

## Sprint 18–20 — New Strategies (Add-ons)

As ORB Scalp, VWAP Reclaim, and Afternoon Momentum come online, the UI needs to support multi-strategy awareness.

### 18-A. Positions as Cards with Mini-Charts [P1]

**Portfolio card view (alternative to table)**
Each open position rendered as a card showing: symbol, strategy badge, entry price, current price, P&L, R-multiple, and a mini candlestick chart from entry to now with stop/T1/T2 as horizontal lines. Toggle between table view (current) and card view.
On mobile, cards stack vertically and are more informative than compressed table rows.
*Effort: ~6 hours. PositionCard component with embedded mini-chart.*

### 18-B. Position Timeline [P1]

**Horizontal timeline of active positions**
Shows when each position was entered, current elapsed time, and projected hold time (based on max_hold_minutes). Positions approaching their time stop get visually distinct (pulsing border or color change). Especially useful during market hours when managing multiple positions across multiple strategies.
*Effort: ~4 hours. Custom timeline component with time-based layout.*

### 18-C. Watchlist Sidebar [P1]

**Symbol watchlist with sparklines and change %**
Right sidebar (desktop) or dedicated section (mobile) showing tracked symbols: name, last price, change %, tiny sparkline. Sourced from scanner candidates across all active strategies. Clicking a symbol opens the detail panel (see 21-A).
*Effort: ~4 hours. Watchlist component + API endpoint for scanner candidates.*

### 18-D. Session Summary Card [P0]

**End-of-day debrief**
When you open the app after market close (or at session end), a summary card appears: "Today: 3 trades, 2 wins, +$1,847. Best trade: AMD +2.0R. Strategy fill rate: 4/4 signals (100%). Market regime: Bullish Trending." Dismissable. Stored for historical review.
*Effort: ~3 hours. SessionSummary component + API endpoint aggregating daily data.*

### 18-E. Notification Center [P1]

**Bell icon with notification history**
Collects all alerts, trade executions, system warnings, and (eventually) AI recommendations. Badge count for unread items. Slide-down panel or drawer. Essential as system complexity grows with multiple strategies.
*Effort: ~5 hours. NotificationCenter component + notification event collection.*

---

## Sprint 21 — CC Analytics & Strategy Lab

This is where the advanced data visualization ideas land. Sprint 21 is already scoped for analytics — these features define what "analytics" means.

### 21-A. Individual Stock/Asset Detail Panel [P1]

**Slide-in detail panel**
Clicking any symbol anywhere in the app opens a right-side panel (desktop, ~40% width) or full-screen modal (mobile). Contains:

1. **Price & chart section:** Current price, change, interactive candlestick chart (1m/5m/15m/1h/1D), volume bars, VWAP/SMA overlays, opening range as shaded rectangle, entry/exit points plotted as markers.
2. **Your trading history on this symbol:** All trades taken, win rate, avg R, total P&L, best/worst trade. Answers "how do I perform on this stock?"
3. **Position detail (if open):** Current P&L, R-multiple, time in trade, stop/T1/T2 levels on chart, projected P&L at target vs stop.
4. **Fundamental context:** Market cap, sector, avg volume, relative volume, float, short interest.
5. **News/catalysts (when Tier 2 news available):** Recent headlines, earnings date, upcoming catalysts.
6. **Quick actions (future):** Close position, adjust stops, add to watchlist, flag for review.

*Effort: ~12–16 hours. Major new component with chart integration and multiple data sources.*

### 21-B. Dashboard V2 — Command Center Layout [P2]

**Comprehensive dashboard redesign**
Evolve from "status page" to "command center" inspired by Bybit Home (image 4) and Mount (image 11). Single screen showing:

- Hero metrics with sparklines (from 16-C)
- Compact equity curve widget (~200px tall)
- Risk utilization gauges (from 17-C)
- Strategy allocation donut (from 17-A)
- Activity heatmap (GitHub contribution style — trade count or P&L by day)
- Open positions (table or card view toggle)
- Watchlist sidebar (from 18-C)
- P&L breakdown widget (realized gains, losses, unrealized, fees, net)
- Recent trades (compact)
- System health mini

Layout: Configurable grid. User can rearrange/resize widgets. Desktop gets the full density. Tablet shows 2-column subset. Mobile stacks priority widgets vertically.

*Effort: ~20–30 hours. Grid layout system, multiple new widgets, responsive configurations.*

### 21-C. Trade Activity Heatmap [P1]

**Time-of-day × day-of-week heatmap**
Color intensity maps to average R-multiple or net P&L per cell. Reveals patterns: "I make money between 9:35–10:15 on Tues/Wed" or "Friday afternoons are consistently negative." Clickable cells filter the trade log to that time/day combination.
*Effort: ~6 hours. Custom heatmap component (D3 or canvas) + aggregation API endpoint.*

### 21-D. Win/Loss Distribution Histogram [P1]

**R-multiple distribution chart**
Vertical histogram showing the distribution of your trade outcomes by R-multiple. Ideal shape: hard cutoff at -1R (stop discipline), slight positive skew, long right tail (winners running). Compare across strategies, time periods, or market regimes. Evolution over time shows whether discipline is improving.
*Effort: ~4 hours. Recharts histogram + API aggregation.*

### 21-E. Portfolio Treemap [P2]

**Capital allocation treemap**
Each position as a rectangle, sized by capital allocated, colored by P&L (green gradient for winners, red for losers). Instantly shows "where is my money and how is it doing?" Hover for detail tooltip. Click to open detail panel. Complements the positions table/card views.
*Effort: ~6 hours. D3 treemap or Recharts treemap.*

### 21-F. Risk Waterfall Chart [P1]

**"If all stops hit" scenario visualization**
Waterfall chart showing the damage by position if every stop loss triggers simultaneously. Each bar represents one position's potential loss. Running total shows worst-case drawdown. Makes risk management tangible rather than abstract.
*Effort: ~4 hours. Custom waterfall chart component.*

### 21-G. Comparative Period Overlay [P1]

**Previous period ghost line on equity curve**
Toggle overlay showing the prior period's equity curve as a faded line behind the current period. "Am I doing better this month than last month?" answered instantly. Works on Performance page equity curve.
*Effort: ~3 hours. Second data series on existing Lightweight Charts instance.*

### 21-H. Strategy Correlation Matrix [P2]

**Multi-strategy return correlation**
Color-coded matrix showing correlation between strategy returns. Low correlation = good diversification. High correlation = doubling down on same risk. Directly informs Orchestrator capital allocation decisions. Only meaningful with 3+ strategies active.
*Effort: ~6 hours. Custom matrix heatmap + correlation calculation API.*

### 21-I. Trade Replay Mode [P2]

**Animated trade walkthrough**
Click any closed trade in the trade log → animated candlestick chart plays through the trade from entry to exit. Shows where your stop, T1, T2 were relative to price action in real time. Speed controls (1x, 2x, 5x). Entry and exit moments highlighted. The single most powerful learning tool for building intuition about strategy behavior.
*Effort: ~12–16 hours. Replay engine, animated chart with timeline scrubber, historical data fetching.*

### 21-J. Goal Tracking Indicator [P0]

**Persistent progress toward defined target**
Small indicator (top bar or dashboard widget): "Target: $5,000/month. Current: $3,200 (64%). 8 trading days remaining." Configurable goal (monthly P&L, win rate, number of trades). Keeps the mission front and center. Motivational without being preachy.
*Effort: ~3 hours. GoalTracker component + settings config.*

### 21-K. Heat Strip (Portfolio Health Bar) [P0]

**Single-line portfolio summary**
Horizontal bar divided into segments for each position. Width = capital allocation, color = P&L performance (green gradient to red gradient). One glance tells you portfolio health. Sits at top of Dashboard or Positions section.
*Effort: ~2 hours. Simple SVG/div component.*

### 21-L. Orchestrator Interaction Panel [P1]

**Decision cockpit for understanding and overriding the Orchestrator.**
Dedicated tab within Strategy Lab (or standalone page) showing the Orchestrator's decision-making in real time:

1. **Decision timeline:** Chronological log of all allocation, regime change, throttle, and suspension decisions with full rationale text. Powered by existing `/orchestrator/decisions` endpoint. Filterable by decision type and strategy.
2. **Regime dashboard:** Current regime badge + indicator gauges (SPY vs SMA-20/50, realized vol/VIX proxy, 5d ROC). Historical regime chart showing transitions over time.
3. **Throttle status:** Per-strategy cards showing consecutive loss count, rolling Sharpe, drawdown from peak, and current throttle action (NONE / REDUCE / SUSPEND). Color-coded severity.
4. **Manual overrides:** Force-activate or force-suspend individual strategies. Trigger manual rebalance (existing `/orchestrator/rebalance` endpoint). Temporarily override allocation percentages (with auto-revert timer). All overrides logged as decisions.
5. **Allocation history:** Line chart showing how capital allocation per strategy has evolved over time (from daily CorrelationTracker data).

This gives the operator a "take over the controls" cockpit for understanding and intervening in Orchestrator decisions without cluttering the day-to-day Dashboard.

*Effort: ~12–16 hours. Multiple new API consumers, decision timeline component, regime chart, override forms with confirmation modals.*

---

## Sprint 22 — AI Layer MVP (Add-ons)

AI integration unlocks intelligent features that build on the visualization infrastructure.

### 22-A. AI Insight Cards [P1]

**Claude-generated analysis embedded in UI**
Cards that appear on the Dashboard or Performance page with AI-generated observations: "Your win rate on AMD is 75% (6/8) — significantly above your overall 60%. Consider increasing allocation." or "Last 3 losses were all TIME exits on Fridays — consider reducing position size on Fridays or tightening time stops."
*Effort: ~6 hours (UI component). API integration handled by Sprint 22 core scope.*

### 22-B. Setup Quality Overlay [P2]

**AI confidence indicator on scanner candidates**
When viewing watchlist symbols or scanner output, Claude rates each setup on a 1–5 scale with brief rationale. Visual overlay on the symbol's chart showing AI confidence zones.
*Effort: ~8 hours. Requires Claude API integration + overlay rendering.*

### 22-C. Strategy Optimization Landscape [P3]

**"Climbing the mountain" visualization (image 11 inspired)**
Topographic visualization where X/Y axes = two strategy parameters (e.g., opening_range_minutes, target_r) and elevation/color = Sharpe ratio from walk-forward results. Current parameter set plotted as a marker. Shows whether you're near the peak, whether the peak is broad (robust) or narrow (fragile), and what parameter space is unexplored.

For multi-strategy optimization: "which combination of strategies with what capital allocations produces the best risk-adjusted return?" Multiple paths up the mountain, each representing a different strategy mix.

AI Layer can annotate the landscape with recommendations: "Moving from 2R to 2.5R target improves Sharpe by 15% with minimal trade count reduction."

*Effort: ~20+ hours. 3D visualization (Three.js or Plotly 3D surface), parameter sweep data pipeline, AI annotation layer. This is a showpiece feature.*

### 22-D. Multi-Line Outcome Projections [P2]

**Projected vs actual equity curves (image 14 inspired)**
Chart showing multiple projected equity curves:
- Current trajectory (extrapolated)
- Best case (optimized parameters)
- Worst case (historical max drawdown applied)
- Monte Carlo confidence bands (10th/50th/90th percentile)

Vertical milestone markers: "100 trades," "6 months live," "first drawdown recovery," "strategy diversification." Actual realized equity curve draws itself over time against projections. Powerful for emotional discipline — see that current drawdown is within expected range.

*Effort: ~12 hours. Monte Carlo simulation, multi-series chart, milestone markers.*

---

## Sprint 23+ — Future Enhancements

### 23-A. Floating Action Context [P1]

**Contextual action toolbar**
When hovering over or selecting a position/trade, a subtle floating toolbar appears with relevant quick actions: close position, view chart, copy symbol, add to watchlist, open detail panel. More discoverable than right-click menus.
*Effort: ~4 hours. Floating toolbar component with position-aware placement.*

### 23-B. Allocation Sunburst [P2]

**Concentric ring allocation chart**
Outer ring = strategy allocation. Inner ring = positions within each strategy. Color-coded by performance. Shows both macro allocation and position-level detail in a single visualization.
*Effort: ~6 hours. D3 sunburst chart.*

### 23-C. Market Regime Timeline [P1]

**Historical regime classification visualization**
Horizontal timeline showing market regime changes over time (Bullish Trending, Range-Bound, High Vol, etc.) with your equity curve overlaid. Reveals which regimes your strategies perform best/worst in. Informs regime-based allocation decisions.
*Effort: ~6 hours. Dual-axis timeline chart + regime classification data.*

### 23-D. Collapsible Sections with Memory [P0]

**Persistent UI state**
Sections remember collapsed/expanded state across sessions (localStorage). Filter settings persist on Trades page. Dashboard widget arrangement saves. Users customize their view once and it sticks.
*Effort: ~3 hours. useLocalStorage hook applied to relevant components.*

### 23-E. Symbol Performance Heatmap [P1]

**Symbol × time period performance matrix**
Grid showing P&L by symbol across weeks/months. Color intensity = magnitude. Reveals which symbols consistently work and which to avoid. Clickable to drill into specific symbol/period combination.
*Effort: ~4 hours. Heatmap grid component + aggregation API.*

### 23-F. Configurable Dashboard Grid [P3]

**Drag-and-drop dashboard customization**
Users can rearrange, resize, add, and remove dashboard widgets. Layout persists across sessions. Presets for different use cases: "Market Hours" (positions-heavy), "Review Mode" (analytics-heavy), "Mobile Quick Check" (just P&L and status). React-grid-layout or similar library.
*Effort: ~15+ hours. Grid layout system, widget registration, state persistence.*

---

## Summary by Sprint

| Sprint | Items | Total Est. Hours | Theme |
|--------|-------|-----------------|-------|
| **16** | 16-A (motion), 16-B (micro-interactions), 16-C (sparklines) | ~15h | Polish & perceived quality |
| **17** | 17-A (donut), 17-B (tabs), 17-C (gauges), 17-D (badges) | ~11h | Multi-strategy awareness |
| **18–20** | 18-A (position cards), 18-B (timeline), 18-C (watchlist), 18-D (session summary), 18-E (notifications) | ~22h | Multi-strategy operations |
| **21** | 21-A through 21-L (analytics, detail panel, heatmaps, treemap, replay, goals, orchestrator interaction) | ~92–116h | Analytics & Strategy Lab |
| **22** | 22-A (AI cards), 22-B (setup quality), 22-C (optimization landscape), 22-D (projections) | ~46h | AI-enhanced visualization |
| **23+** | 23-A through 23-F (actions, sunburst, regime, persistence, configurability) | ~38h | Customization & refinement |

---

## Implementation Notes

### Animation Library Recommendation
Framer Motion for page transitions and staggered entry animations. CSS transitions for hover effects and micro-interactions. Lightweight Charts native animation for chart draw-ins. Keep the animation budget minimal — every animation should complete in <500ms and serve an information purpose.

### Chart Library Stack
- **Lightweight Charts** (already integrated): Equity curves, candlestick charts, area charts, histograms.
- **Recharts**: Donut charts, bar charts, simple histograms. Good React integration.
- **D3**: Treemaps, heatmaps, sunbursts, complex custom visualizations. Use sparingly — only for things Recharts can't do.
- **Three.js or Plotly 3D**: Strategy optimization landscape (22-C). Single use case, high impact.

### Mobile-First Considerations
Every feature should have a mobile adaptation plan. Common patterns:
- Detail panels → full-screen modals on mobile
- Side-by-side layouts → stacked vertical
- Complex charts → simplified with tap-to-expand
- Hover interactions → long-press or tap
- Floating toolbars → bottom sheet actions

### Performance Budgets
- Dashboard should render interactive in <1 second on LAN
- Animations should never drop below 60fps
- Charts with >1000 data points should use canvas rendering (not SVG)
- WebSocket updates should batch UI re-renders (requestAnimationFrame)
