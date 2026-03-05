# Sprint 21d — Claude Code Session Prompts

## Session Plan Overview

| # | Session | Focus | Review After? |
|---|---------|-------|---------------|
| 1 | Backend: Analytics endpoints | Heatmap, distribution, correlation endpoints | No |
| 2 | Backend: Replay + dev mock + config | Trade replay endpoint, dev_state expansion, goals config | No |
| 3 | Nav restructure | Sidebar dividers, MobileNav 5+More, MoreSheet, keyboard shortcuts | No |
| 4 | Dashboard: Strip + removal | OrchestratorStatusStrip, remove RiskAllocationPanel, re-layout | No |
| 5 | Dashboard: Heat strip + goal + pre-market | HeatStripPortfolioBar, GoalTracker, PreMarketLayout | **YES — Review #1** |
| 6 | Performance: Heatmap + Calendar | TradeActivityHeatmap (D3), CalendarPnlView, tab shell | No |
| 7 | Performance: Histogram + Waterfall | RMultipleHistogram (Recharts), RiskWaterfall | No |
| 8 | Performance: Treemap + Correlation | PortfolioTreemap (D3), CorrelationMatrix | No |
| 9 | Performance: Period overlay + page integration | Comparative overlay, wire all into tabbed PerformancePage | No |
| 10 | Trade Replay | TradeReplay component, playback controls, markers | **YES — Review #2** |
| 11 | System cleanup + Copilot shell | System narrowing, placeholders, CopilotPanel + Button + store | No |
| 12 | Responsive QA + polish | All components at all breakpoints, animation tuning, skeletons | No |
| 13 | Integration + dev mode verification | Full dev mode walkthrough, mock data, edge cases | **YES — Review #3 (Final)** |
| 14 | Docs + commit cleanup | Decision log, Project Knowledge, sprint plan updates | No |

---

## Session 1: Backend Analytics Endpoints

```
Sprint 21d, Session 1 of 14: Backend Analytics Endpoints

Read the sprint spec first: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component B backend section + Sub-Component F).

CONTEXT: We're adding analytical depth to the Performance page. This session builds the backend endpoints that the frontend will consume in Sessions 6-10.

TASKS:
1. Add `get_daily_pnl_by_strategy()` method to TradeLogger (argus/analytics/trade_logger.py):
   - SQL: SELECT date(exit_time) as date, strategy_id, SUM(pnl_dollars) as pnl FROM trades WHERE exit_time IS NOT NULL GROUP BY date, strategy_id
   - Parameters: date_from, date_to (optional)
   - Returns: list[dict] with {date, strategy_id, pnl}

2. Add 3 new endpoints to argus/api/routes/performance.py:
   a. GET /heatmap?period=&strategy_id= — trades grouped by (hour_of_day, day_of_week) with avg R-multiple and count
   b. GET /distribution?period=&strategy_id= — R-multiple histogram in 0.25R bins from -3R to +4R
   c. GET /correlation?period= — NxN strategy correlation matrix using numpy.corrcoef on daily returns

3. Add Pydantic response models for each endpoint (HeatmapCell, HeatmapResponse, DistributionBin, DistributionResponse, CorrelationResponse).

4. Write pytest tests for all new functionality:
   - TradeLogger.get_daily_pnl_by_strategy: empty, single strategy, multi-strategy, date filter (~4 tests)
   - Heatmap endpoint: empty, trades in different hours/days, strategy filter (~4 tests)
   - Distribution endpoint: empty, various R-multiples, strategy filter (~3 tests)
   - Correlation endpoint: insufficient data, 2 strategies, 4 strategies (~3 tests)

IMPORTANT:
- Follow existing patterns in performance.py for date range computation, auth, dependency injection
- Use ET timezone for hour-of-day grouping (trades stored in UTC, need conversion)
- Correlation endpoint needs numpy — already installed for backtesting
- For correlation with <5 data days, return empty matrix with a message
- All endpoints support the same period parameter (today/week/month/all) as existing performance endpoint

Target: ~14 new pytest tests. Run `pytest tests/api/` to verify plus full suite.
```

---

## Session 2: Backend Replay + Dev Mock + Config

```
Sprint 21d, Session 2 of 14: Backend Replay Endpoint + Dev Mock Data + Goals Config

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Components B and F).

CONTEXT: Completing backend work — trade replay endpoint, goals config, and expanding dev mode mock data for all new endpoints.

TASKS:
1. Add trade replay endpoint to argus/api/routes/trades.py:
   - GET /api/v1/trades/{trade_id}/replay
   - Returns: trade data + 1-minute bars for window (entry_time - 15min to exit_time + 5min)
   - Response model: TradeReplayResponse with bars list, entry/exit bar indices, optional VWAP array
   - Live mode: query DataService for historical bars (stub — returns empty with message for now)
   - Dev mode: generate synthetic bars that create a plausible trade (gap up, breakout, pullback, target hit)

2. Add GoalsConfig to config system:
   - GoalsConfig(BaseModel) with monthly_target_usd: float = 5000.0
   - Add goals field to SystemConfig
   - Add goals section to config/system.yaml
   - New route file: argus/api/routes/config.py with GET /api/v1/config/goals
   - Wire into API router in argus/api/server.py

3. Expand dev_state.py mock data:
   - Heatmap: generate ~200 trades distributed across hours (heavy 9:30-11:00, light afternoon) and weekdays
   - Distribution: generate R-multiples with slight positive skew (peak at -1R stop hits, secondary peak +0.5R to +1R)
   - Correlation: generate 4×4 matrix with realistic low correlations (0.05-0.35 off-diagonal)
   - Replay: generate synthetic 1-min bars for a plausible ORB trade (50 bars, gap up pattern, breakout at bar 15, T1 hit at bar 25)
   - Goals: include monthly_target_usd in mock config

4. Add TypeScript types for new endpoints to argus/ui/src/api/types.ts:
   - HeatmapCell, HeatmapResponse
   - DistributionBin, DistributionResponse
   - CorrelationResponse
   - ReplayBar, TradeReplayResponse
   - GoalsConfig

5. Add TanStack Query hooks:
   - useHeatmapData(period, strategyId?) in argus/ui/src/hooks/useHeatmapData.ts
   - useDistribution(period, strategyId?) in argus/ui/src/hooks/useDistribution.ts
   - useCorrelation(period) in argus/ui/src/hooks/useCorrelation.ts
   - useTradeReplay(tradeId) in argus/ui/src/hooks/useTradeReplay.ts
   - useGoals() in argus/ui/src/hooks/useGoals.ts

6. Write tests:
   - Replay endpoint: valid trade, trade not found (~3 pytest tests)
   - Goals config endpoint: default value (~2 pytest tests)

Target: ~5 new pytest tests. Commit: "feat(api): trade replay endpoint, goals config, dev mock data expansion"
```

---

## Session 3: Navigation Restructure

```
Sprint 21d, Session 3 of 14: Navigation Restructure

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component D).

CONTEXT: Restructuring navigation for the 7-page architecture. Desktop sidebar gets group dividers, mobile bottom bar changes to 5 primary tabs + More bottom sheet.

TASKS:
1. Update argus/ui/src/layouts/Sidebar.tsx:
   - Add `divider?: boolean` property to NAV_ITEMS entries
   - Insert dividers between groups:
     - After Performance (end of Monitor group)
     - After Patterns (end of Operate group)
     - After Debrief (end of Learn group)
   - Render dividers as: <div className="w-8 mx-auto border-b border-argus-border/50 my-1" />
   - Add 'c' keyboard shortcut for copilot toggle (import copilotUI store, call toggle)
   - Keep 1-7 shortcuts unchanged

2. Create argus/ui/src/layouts/MoreSheet.tsx:
   - Framer Motion bottom sheet component
   - Props: isOpen, onClose
   - Backdrop: motion.div bg-black/60, click to dismiss
   - Sheet: motion.div slides up from bottom, rounded-t-xl, bg-argus-surface
   - Drag handle at top: small gray bar (w-10 h-1 rounded-full bg-argus-text-dim/30 mx-auto my-3)
   - 3 rows: Performance (TrendingUp icon), Debrief (GraduationCap icon), System (Activity icon)
   - Each row: NavLink with icon + label, full width, py-4, hover state
   - NavLink onClick also closes the sheet
   - Escape key to close
   - AnimatePresence for enter/exit

3. Update argus/ui/src/layouts/MobileNav.tsx:
   - Change NAV_ITEMS to 5 items: Dashboard, Trades, Orchestrator, Patterns, More
   - "More" item: icon=MoreHorizontal from lucide-react, no NavLink — onClick opens MoreSheet
   - Import and render MoreSheet with local useState for open/close
   - System status dot moves to More sheet's System row (or remove from mobile nav entirely)
   - Active indicator: More tab shows active state if current route is Performance, Debrief, or System

4. Write Vitest tests:
   - MoreSheet: renders 3 items, opens/closes animation (~2 tests)
   - MobileNav: renders 5 items, More tab triggers sheet (~2 tests)
   - Sidebar: renders dividers between groups (~1 test)

Target: ~5 new Vitest tests. Commit: "feat(ui): nav restructure — sidebar dividers, mobile 5+More bottom sheet"
```

---

## Session 4: Dashboard Strip + Removal

```
Sprint 21d, Session 4 of 14: Dashboard — Orchestrator Status Strip + Component Removal

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component A).

CONTEXT: Narrowing Dashboard to pure ambient awareness. Removing components that migrated to Orchestrator, adding OrchestratorStatusStrip.

TASKS:
1. Create argus/ui/src/features/dashboard/OrchestratorStatusStrip.tsx:
   - Single-line data-dense row at top of Dashboard
   - Uses useOrchestratorStatus() hook for data
   - Desktop/tablet: horizontal row with items separated by "│" dividers
     Items: "{N} strategies active │ ${X} deployed ({Y}%) │ Risk: {Z}% of daily │ {Regime Badge}"
   - Mobile: 2×2 grid layout (strategies+capital top row, risk+regime bottom row)
   - Entire strip is clickable → navigate('/orchestrator') via useNavigate()
   - Subtle bg-argus-surface-2/50 background, border-argus-border border, rounded-lg, px-4 py-2
   - Graceful fallback when orchestrator unavailable: "Orchestrator offline" with muted styling
   - Regime badge uses existing RegimeBadge component or inline colored badge

2. Remove RiskAllocationPanel from Dashboard:
   - Remove import and usage from DashboardPage.tsx
   - Do NOT delete the file — it may be referenced elsewhere (Orchestrator imports CapitalAllocation directly, but check)
   - Remove MarketRegimeCard from the Dashboard market pair (it was in the 3-card row and as standalone)
   - Keep MarketStatusBadge (simple card, not duplicated elsewhere)

3. Rebuild DashboardPage.tsx layout:
   Desktop:
   - OrchestratorStatusStrip (full width, top)
   - [placeholder slot for HeatStripPortfolioBar — session 5]
   - SessionSummaryCard (after-hours only)
   - 3-col row: AccountSummary | DailyPnlCard | [placeholder for GoalTracker — session 5]
   - 2-col row: MarketStatusBadge | MarketRegimeCard
   - OpenPositions (full width)
   - 2-col row: RecentTrades | HealthMini
   
   Tablet: Similar but 2-col grid
   Mobile: Single column stack

4. Update dashboard/index.ts exports (remove RiskAllocationPanel if it was exported from here for Dashboard-only use).

5. Write Vitest tests:
   - OrchestratorStatusStrip: renders with mock data, fallback state, click navigation (~3 tests)

Target: ~3 new Vitest tests. Commit: "feat(ui): dashboard scope refinement — status strip, remove migrated components"
```

---

## Session 5: Dashboard Heat Strip + Goal + Pre-Market

```
Sprint 21d, Session 5 of 14: Dashboard — Heat Strip, Goal Tracker, Pre-Market Layout

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component A, remaining items).

CONTEXT: Completing Dashboard refinement with HeatStripPortfolioBar, GoalTracker, and PreMarketLayout.

TASKS:
1. Create argus/ui/src/features/dashboard/HeatStripPortfolioBar.tsx:
   - Custom SVG horizontal bar, full width
   - One segment per open position from usePositions()
   - Segment width = (position_value / total_equity) * total_bar_width
   - Segment color: green-to-red gradient based on unrealized_pnl_pct
     - >+2%: #22c55e (green-500), 0 to +2%: #86efac (green-300)
     - 0 to -1%: #fca5a5 (red-300), <-1%: #ef4444 (red-500)
   - Hover: tooltip with symbol, P&L ($, %), shares, strategy
   - Click segment: open SymbolDetailPanel (use symbolDetailUI store)
   - Empty state: subtle gray bar with "No open positions" centered text
   - Minimum segment width: 20px — if position too small, merge into "+" indicator at end
   - Height: 24px on desktop, 20px on mobile
   - Rounded ends (rx/ry on first and last segments)

2. Create argus/ui/src/features/dashboard/GoalTracker.tsx:
   - Card component showing monthly target progress
   - Data: useGoals() for target, usePerformance('month') for current P&L
   - Display: "Target: $5,000/mo │ Current: $3,200 (64%) │ 8 days left"
   - Thin progress bar (h-1.5, rounded-full)
   - Color logic:
     - Green: on pace (current_pnl / elapsed_pct >= target)
     - Amber: behind but within 80% of pace
     - Red: significantly behind (<80% of pace)
   - Trading days calculation: ~22 days/month, count weekdays elapsed vs remaining
   - Compact card style matching AccountSummary/DailyPnlCard

3. Create argus/ui/src/features/dashboard/PreMarketLayout.tsx:
   - Renders when account.market_status === 'pre_market' (or toggle in dev mode)
   - MarketCountdown component: live countdown to 9:30 AM ET
     - useEffect with setInterval(1000) computing diff to next 9:30 AM ET
     - Format: "2h 14m" or "14m 30s" (under 1 hour) or "Market Open" (green pulse)
   - SessionSummaryCard (yesterday's data)
   - Placeholder cards (2-col grid):
     - "Ranked Watchlist" — empty table header (Rank, Symbol, Gap%, Catalyst, Quality)
       Footer: "Pre-Market Intelligence activating Sprint 23"
     - "Regime Forecast" — placeholder gauge area
       Footer: "AI-powered regime forecast available Sprint 22"
     - "Catalyst Summary" — empty area
       Footer: "NLP Catalyst Pipeline activating Sprint 23"
     - GoalTracker (real data, same as market hours)

4. Create argus/ui/src/features/dashboard/MarketCountdown.tsx:
   - Self-contained countdown component
   - Props: none (computes internally from current time vs 9:30 AM ET)
   - Large display: "Market Opens In" above "2:14:30" countdown
   - Uses formatDuration or custom formatting
   - Subtle animation: number transitions

5. Wire into DashboardPage.tsx:
   - Import PreMarketLayout
   - Add market_status check: if pre_market, render PreMarketLayout; else render normal layout
   - In normal layout: add HeatStripPortfolioBar below OrchestratorStatusStrip
   - Replace third card in top row with GoalTracker
   - Dev mode: add useSearchParams check for ?premarket=true to force pre-market layout for testing

6. Update features/dashboard/index.ts with new exports.

7. Write Vitest tests:
   - HeatStripPortfolioBar: renders segments, color mapping, empty state, click handler (~3 tests)
   - GoalTracker: on pace (green), behind pace (amber), renders correctly (~3 tests)
   - PreMarketLayout: renders countdown and placeholder cards (~2 tests)

Target: ~8 new Vitest tests. Commit: "feat(ui): dashboard heat strip, goal tracker, pre-market layout"

>>> CHECKPOINT: After this session, take screenshots at all 3 breakpoints for Code Review #1.
Run `npm run dev` (or the dev server) and capture:
- Dashboard (market hours) at desktop/tablet/mobile
- Dashboard (pre-market) at desktop/tablet/mobile — use ?premarket=true
- Navigation: sidebar with dividers, mobile More sheet
Total: ~8 screenshots needed for Review #1.
```

---

## Session 6: Performance Heatmap + Calendar

```
Sprint 21d, Session 6 of 14: Performance — Trade Activity Heatmap + Calendar P&L + Tab Shell

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component B).

CONTEXT: Starting Performance page expansion. This session adds the tab navigation shell and the first two visualizations.

TASKS:
1. Install D3 modules: cd argus/ui && npm install d3-scale d3-color d3-hierarchy d3-interpolate @types/d3-scale @types/d3-color @types/d3-hierarchy @types/d3-interpolate

2. Create Performance tab navigation in PerformancePage.tsx:
   - Add SegmentedTab below PeriodSelector (reuse existing SegmentedTab component pattern)
   - Tabs: Overview | Heatmaps | Distribution | Portfolio | Replay
   - Tab state: local useState (or Zustand if you prefer persistence)
   - Each tab renders its own content section
   - Overview tab contains all existing content (MetricsGrid, EquityCurve, DailyPnlChart, StrategyBreakdown)
   - Other tabs render new components (built in this and subsequent sessions)
   - Period selector remains global (above tabs)

3. Create argus/ui/src/features/performance/TradeActivityHeatmap.tsx:
   - Uses useHeatmapData(period) hook from Session 2
   - SVG grid: 13 columns (9:30-16:00 in 30-min bins) × 5 rows (Mon-Fri)
   - Cell sizing: compute from container width (responsive)
   - Color scale: d3.scaleSequential with d3.interpolateRdYlGn, domain centered on 0
   - Toggle: "Color by R-Multiple" / "Color by P&L" (local state)
   - Cell content: trade count as small centered text (white on dark cells, dark on light)
   - Hover: tooltip div with time range, day, count, avg R, net P&L
   - Click cell: navigate to /trades with query params ?hour={}&day={} (or show filtered trades inline)
   - X-axis labels: "9:30", "10:00", ..., "15:30"
   - Y-axis labels: "Mon", "Tue", "Wed", "Thu", "Fri"
   - Empty state: "No trades in this period" centered message
   - Legend: color bar showing scale from red through white to green

4. Create argus/ui/src/features/performance/CalendarPnlView.tsx:
   - Uses daily_pnl from usePerformance(period) — no new endpoint needed
   - Monthly calendar grid (7 cols: Sun-Sat, 5-6 rows)
   - Month navigation: ← → arrows, month/year label
   - Day cells:
     - Date number (top-left)
     - P&L value (center, formatted currency)
     - Background color: green/red intensity based on P&L magnitude
     - Weekend cells: grayed out, no data
     - No-trade days: neutral background
   - Click day: navigate to /trades?date={YYYY-MM-DD}
   - Bottom summary: "Week 1: +$350 | Week 2: -$120 | ..." (weekly totals)
   - Custom SVG rendering (similar pattern to CapitalAllocation donut)
   
5. Wire both into PerformancePage.tsx Heatmaps tab.

6. Write Vitest tests:
   - TradeActivityHeatmap: renders grid cells, handles empty data, color scale applies (~3 tests)
   - CalendarPnlView: renders month grid, correct day positions, P&L colors (~3 tests)

Target: ~6 new Vitest tests. Commit: "feat(ui): performance tabs, trade activity heatmap, calendar P&L"
```

---

## Session 7: Performance Histogram + Waterfall

```
Sprint 21d, Session 7 of 14: Performance — R-Multiple Histogram + Risk Waterfall

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component B).

CONTEXT: Building the Distribution tab visualizations.

TASKS:
1. Create argus/ui/src/features/performance/RMultipleHistogram.tsx:
   - Uses useDistribution(period, strategyId) hook
   - Recharts BarChart with custom styling
   - X-axis: R-multiple bins (-3R to +4R in 0.25R steps)
   - Y-axis: trade count
   - Bar colors: red (#ef4444) for negative R bins, green (#22c55e) for positive R bins
   - Vertical reference lines: 0R (white dashed), mean R (blue dashed with label)
   - Strategy filter dropdown above chart (All / ORB / Scalp / VWAP / Afternoon)
   - Hover tooltip: bin range, count, % of total, avg P&L for this bin
   - Annotation: "Mean: 0.45R | Median: 0.22R | Skew: +0.3" below chart
   - ResponsiveContainer for auto-sizing
   - Empty state: "No trades to analyze"

2. Create argus/ui/src/features/performance/RiskWaterfall.tsx:
   - Custom SVG horizontal waterfall chart
   - Data: compute from usePositions() — each position's max risk = shares × (entry_price - stop_price)
   - One horizontal bar per open position, sorted by risk size (largest first)
   - Bar length proportional to risk amount
   - Bar color: opacity based on % of daily risk limit
   - Running total line: cumulative risk shown as a stepped line above bars
   - Labels: symbol name (left), risk amount (right of bar), cumulative % (on running total)
   - Final marker: "Total risk: $1,250 (2.5% of equity)" 
   - Empty state (no open positions): "No open positions — zero risk exposure"
   - Responsive: horizontal scrollable on mobile if many positions

3. Wire both into PerformancePage.tsx Distribution tab.

4. Write Vitest tests:
   - RMultipleHistogram: renders bars, color coding, strategy filter, empty state (~3 tests)
   - RiskWaterfall: renders bars, running total, empty state (~2 tests)

Target: ~5 new Vitest tests. Commit: "feat(ui): R-multiple histogram, risk waterfall chart"
```

---

## Session 8: Performance Treemap + Correlation

```
Sprint 21d, Session 8 of 14: Performance — Portfolio Treemap + Correlation Matrix

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component B).

CONTEXT: Building the Portfolio tab visualizations. These use D3 more heavily.

TASKS:
1. Create argus/ui/src/features/performance/PortfolioTreemap.tsx:
   - Uses usePositions() and useAccount() for data
   - D3 treemap layout: d3.treemap().size([width, height]).padding(2)
   - D3 hierarchy: d3.hierarchy({ children: positions }).sum(d => d.shares * d.current_price)
   - Rectangle rendering via React (map over treemap.leaves())
   - Color: diverging green-red based on unrealized_pnl_pct (d3.scaleSequential)
   - Labels: symbol name + P&L % (only if rectangle large enough — skip label if width < 60px)
   - Hover tooltip: symbol, shares, value, P&L ($, %), strategy, entry price
   - Click rectangle: open SymbolDetailPanel
   - Container: responsive via ResizeObserver or useRef + getBoundingClientRect
   - Empty state: "No open positions"
   - Mobile fallback: if container width < 400px, show sorted list instead of treemap
     (each item: symbol, value bar, P&L badge — same data, simpler layout)

2. Create argus/ui/src/features/performance/CorrelationMatrix.tsx:
   - Uses useCorrelation(period) hook
   - NxN grid (currently 4×4 for 4 strategies)
   - Color scale: d3.scaleSequential with d3.interpolateRdBu, domain [-1, 1]
   - Diagonal cells: always 1.0, darker shade
   - Cell labels: correlation coefficient (2 decimal places)
   - Row/column headers: strategy short names (O, S, V, A or full names if space)
   - Hover tooltip: "ORB ↔ VWAP: 0.23 (low correlation)"
   - Interpretation helper below: "Low correlations (<0.3) indicate good diversification"
   - Empty state: "Insufficient data for correlation analysis (need 5+ trading days)"

3. Wire both into PerformancePage.tsx Portfolio tab.

4. Write Vitest tests:
   - PortfolioTreemap: renders rectangles, handles empty data, mobile fallback (~3 tests)
   - CorrelationMatrix: renders NxN grid, color scale, empty state (~2 tests)

Target: ~5 new Vitest tests. Commit: "feat(ui): portfolio treemap (D3), correlation matrix"
```

---

## Session 9: Performance Period Overlay + Page Integration

```
Sprint 21d, Session 9 of 14: Performance — Comparative Period Overlay + Full Page Integration

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component B).

CONTEXT: Adding comparative overlay to equity curve and wiring all performance components into the tabbed page.

TASKS:
1. Add comparative period overlay to argus/ui/src/features/performance/EquityCurve.tsx:
   - New prop: showComparison?: boolean (default false)
   - New prop: comparisonData?: DailyPnlEntry[] (previous period's data)
   - When enabled, add second series to Lightweight Charts:
     - Previous period data shifted to align with current period start date
     - Styling: dashed line (or lower opacity line), different color (e.g., argus-text-dim)
     - Legend entry: "Previous {period}" with dashed line indicator
   - Toggle button above chart: "Compare with previous {period}" checkbox/switch
   - Implementation: chart.addLineSeries() for comparison data, with visible toggle

2. Create hook for comparison data:
   - In PerformancePage, when comparison enabled, compute previous period dates
   - Week: previous Monday to previous Sunday
   - Month: previous month 1st to last day
   - Fetch usePerformance with previous dates
   - Pass comparison daily_pnl to EquityCurve

3. Final integration of PerformancePage.tsx:
   - Ensure all 5 tabs render correctly
   - Overview tab: MetricsGrid, EquityCurve (with comparison toggle), DailyPnlChart, StrategyBreakdown
   - Heatmaps tab: TradeActivityHeatmap, CalendarPnlView
   - Distribution tab: RMultipleHistogram, RiskWaterfall
   - Portfolio tab: PortfolioTreemap, CorrelationMatrix
   - Replay tab: placeholder "Trade Replay loading in next session" (Session 10 builds the component)
   - Loading states: each tab should show skeleton/loading when data is fetching
   - Tab state persistence within session (survives period changes)
   - Verify period selector affects all tab content

4. Add any missing index.ts exports for new performance components.

5. Write Vitest tests:
   - EquityCurve comparison: toggle shows/hides comparison line (~2 tests)
   - PerformancePage integration: renders tabs, switching works (~2 tests)

Target: ~4 new Vitest tests. Commit: "feat(ui): comparative period overlay, performance page integration"
```

---

## Session 10: Trade Replay

```
Sprint 21d, Session 10 of 14: Performance — Trade Replay Mode

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Component B, TradeReplay section).

CONTEXT: Building the most ambitious visualization — animated candlestick trade walkthrough. This is the most powerful learning tool in the Performance suite.

TASKS:
1. Create argus/ui/src/features/performance/TradeReplay.tsx:
   
   STRUCTURE:
   - Trade selector: dropdown of trades from current period (useTradeFilters or custom query)
     - Each option: "{symbol} {side} {date} {P&L}" 
     - Or: "Select from Trade Log" button that navigates to /trades with "replay" mode
   - Chart area: Lightweight Charts candlestick (full component width)
   - Controls bar: below chart
   - Info panel: alongside or below controls
   
   CHART SETUP:
   - Use useTradeReplay(selectedTradeId) hook for bar data
   - Create Lightweight Charts instance with 1-minute candlestick series
   - Initially show all bars but with visible range set to show none (or first few)
   - As playback progresses, expand visible range to reveal bars progressively
   
   MARKERS AND LINES:
   - Entry: green upward triangle marker at entry bar, horizontal dashed line at entry_price (green)
   - Stop: horizontal dashed line at stop_price (red, labeled "Stop")
   - T1: horizontal dashed line at t1_price (blue, labeled "T1")
   - T2: horizontal dashed line at t2_price (blue, labeled "T2")  
   - Exit: red/green triangle marker at exit bar
   - Opening range (ORB strategies): shaded rectangle from OR low to OR high
   - VWAP line (VWAP strategies): line series overlay from replay data
   
   PLAYBACK CONTROLS:
   - Play/Pause button (toggles between ▶ and ⏸)
   - Speed selector: buttons [1x] [2x] [5x] [10x] — highlighted current speed
   - Scrubber: range input (slider) from 0 to totalBars, updates chart on change
   - Step buttons: ⏪ (step back 1 bar) and ⏩ (step forward 1 bar)
   - Reset button: return to start
   
   PLAYBACK LOGIC:
   - State: currentBarIndex (0 to bars.length), isPlaying, speed
   - useEffect with setInterval: when playing, increment currentBarIndex at (1000/speed)ms
   - On currentBarIndex change: update chart visible range to show bars 0..currentBarIndex
   - Markers appear when their bar index is reached
   - At end of bars: auto-pause
   
   INFO PANEL (beside or below controls):
   - Current time: timestamp of current bar
   - Current price: close of current bar  
   - Unrealized P&L: computed from entry to current close (only after entry bar)
   - R-Multiple: current P&L / risk per share
   - Trade result: shown after exit bar reached
   
   RESPONSIVE:
   - Desktop: chart 70% width, info panel 30% right
   - Mobile: chart full width, controls + info below as compact rows

2. Wire into PerformancePage.tsx Replay tab (replace placeholder).

3. Handle edge cases:
   - No trade selected: show prompt "Select a trade to replay"
   - Trade has no bars (data unavailable): show "Bar data not available for this trade"
   - Very short trades (< 5 bars): still works, just fast

4. Write Vitest tests:
   - TradeReplay: renders chart container, playback controls visible (~2 tests)
   - Playback: play/pause state, speed change (~2 tests)
   - Trade selector: renders options, selection triggers data fetch (~1 test)

Target: ~5 new Vitest tests. Commit: "feat(ui): trade replay mode with animated candlestick playback"

>>> CHECKPOINT: After this session, take screenshots for Code Review #2.
Run dev mode and capture:
- Performance page: all 5 tabs at desktop width
- Performance Overview tab with comparison toggle
- Heatmap tab at desktop and mobile
- Distribution tab at desktop
- Portfolio tab at desktop
- Trade Replay in action (paused mid-trade) at desktop and mobile
Total: ~10 screenshots needed for Review #2.
```

---

## Session 11: System Cleanup + Copilot Shell

```
Sprint 21d, Session 11 of 14: System Page Cleanup + AI Copilot Shell

Read the sprint spec: docs/sprints/SPRINT_21D_SPEC.md (Sub-Components C and E).

CONTEXT: Two smaller tasks combined. Narrowing System page to infrastructure-only, plus building the Copilot panel shell.

TASKS — SYSTEM:
1. Update argus/ui/src/pages/SystemPage.tsx:
   - Remove StrategyCards import and rendering
   - Remove EmergencyControls import and rendering
   - Add IntelligencePlaceholders component
   - New layout: SystemOverview + ComponentStatusList (2-col) above IntelligencePlaceholders above EventsLog

2. Create argus/ui/src/features/system/IntelligencePlaceholders.tsx:
   - Card with header "Intelligence Components"
   - Grid of 6 placeholder items (2-col desktop, 1-col mobile):
     1. AI Copilot — Sprint 22
     2. Pre-Market Engine — Sprint 23
     3. Catalyst Service — Sprint 23
     4. Order Flow Analyzer — Sprint 24
     5. Setup Quality Engine — Sprint 25
     6. Learning Loop — Sprint 30
   - Each item: icon (Brain/Sunrise/Newspaper/BarChart3/Star/RefreshCw from lucide-react), name, sprint badge, one-line description
   - Badge styling: neutral gray "Sprint XX" pill
   - Overall muted/dim styling — these are future items, not active

TASKS — COPILOT:
3. Create argus/ui/src/stores/copilotUI.ts:
   - isOpen: boolean (default false)
   - toggle(), open(), close() actions
   - No persist — session-level only

4. Create argus/ui/src/features/copilot/CopilotPlaceholder.tsx:
   - Centered content for the empty copilot panel
   - AI icon (Bot or Sparkles from lucide-react), large, accent colored
   - "AI Copilot" heading
   - Description paragraph about Sprint 22 activation
   - Bullet list (styled, not raw bullets): "Answer questions about any system data", "Generate reports saved to The Debrief", "Propose parameter and allocation changes", "Annotate trades with insights", "Explain Orchestrator decisions"
   - Subtle border, rounded, padded card within the panel

5. Create argus/ui/src/features/copilot/CopilotPanel.tsx:
   - Uses copilotUI store for isOpen
   - AnimatePresence + motion.div for slide-in animation
   - Desktop: fixed right side, width 35% (min-w-[400px] max-w-[560px]), full height, border-l
   - Mobile: fixed bottom, 90vh, rounded-t-xl, border-t
   - Backdrop: motion.div bg-black/40, click to close
   - Header: "AI Copilot" title + context indicator (current page name from useLocation) + close button
   - Context mapping: / → "Dashboard", /trades → "Trade Log", /performance → "Performance", etc.
   - Body: scrollable area containing CopilotPlaceholder
   - Footer: disabled input field with placeholder "Activating Sprint 22..." + disabled send button
   - Escape key to close (don't conflict with other panel Escape handlers — check isOpen first)

6. Create argus/ui/src/features/copilot/CopilotButton.tsx:
   - Uses copilotUI store
   - Floating action button
   - Desktop: fixed bottom-6 right-6
   - Mobile: fixed right-4, bottom offset to clear MobileNav (bottom-[88px] to clear h-16 + pb-3 + gap)
   - 48px circle, bg-argus-accent, white icon (MessageCircle from lucide-react)
   - Hover: scale-105 transition
   - Tap: scale-95 active state
   - When panel is open: button hidden (AnimatePresence exit animation)
   - Entrance animation: scale from 0 to 1 with spring (on first mount only — use useRef flag)

7. Create argus/ui/src/features/copilot/index.ts with exports.

8. Mount in AppShell.tsx:
   - Import CopilotPanel and CopilotButton
   - Add after SymbolDetailPanel: <CopilotPanel /> then <CopilotButton />

9. Add 'c' keyboard shortcut:
   - Already wired in Session 3's Sidebar update — verify it works
   - Also add to MobileNav or AppShell if needed for mobile (mobile doesn't have Sidebar keyboard handler)
   - Best approach: move keyboard shortcut handler to AppShell level so it works on all surfaces

10. Write Vitest tests:
   - IntelligencePlaceholders: renders 6 items (~1 test)
   - CopilotPanel: opens/closes, shows context indicator, placeholder content (~3 tests)
   - CopilotButton: renders, hides when panel open, responsive positioning (~2 tests)

Target: ~6 new Vitest tests. Commit: "feat(ui): system cleanup + AI copilot shell"
```

---

## Session 12: Responsive QA + Polish

```
Sprint 21d, Session 12 of 14: Responsive QA + Polish

CONTEXT: All new components are built. This session ensures everything works at all breakpoints with proper loading states and animations.

TASKS:
1. Responsive verification at 3 breakpoints (393px, 834px, 1024px+):
   - Dashboard (market hours layout)
   - Dashboard (pre-market layout via ?premarket=true)
   - Performance: all 5 tabs
   - System page
   - Navigation: sidebar dividers, mobile More sheet
   - Copilot panel + button
   - Check for overflow, text truncation, touch targets (≥44px)

2. Skeleton loading states:
   - Add skeleton to Performance tabs that don't have it
   - OrchestratorStatusStrip skeleton (pulsing bar placeholder)
   - HeatStripPortfolioBar skeleton (pulsing full-width bar)
   - GoalTracker skeleton (pulsing text lines)
   - Verify existing skeletons still work (DashboardSkeleton, PerformanceSkeleton)

3. Animation tuning:
   - Verify stagger animations on new Dashboard layout
   - HeatStripPortfolioBar: subtle entrance animation (segments grow from left)
   - GoalTracker progress bar: animate-in on mount (width transition)
   - Performance tab transitions: fade between tabs (AnimatePresence or CSS)
   - MoreSheet: smooth spring slide-up and backdrop fade
   - CopilotPanel: spring slide matches SlideInPanel timing
   - CopilotButton entrance: verify first-mount-only scale animation

4. Empty states:
   - All new charts: verify empty state messages render correctly
   - Pre-market mode: verify all placeholder cards show proper messages
   - Copilot: verify placeholder renders with proper styling

5. Error states:
   - What happens when analytics endpoints fail? Verify error boundaries catch chart errors
   - PerformancePage already has ChartErrorBoundary — ensure new tabs use it

6. Touch interactions:
   - Heatmap cells: verify tap works on mobile (not just hover)
   - Calendar days: verify tap works
   - Treemap rectangles: verify tap opens SymbolDetailPanel
   - Heat strip segments: verify tap opens SymbolDetailPanel

7. Fix any issues found during verification.

Target: ~3 new Vitest tests (if test gaps found). Commit: "fix(ui): responsive polish, skeleton loading, animation tuning"
```

---

## Session 13: Integration + Dev Mode Verification

```
Sprint 21d, Session 13 of 14: Integration + Dev Mode Verification

CONTEXT: Final verification. Full dev mode walkthrough ensuring all mock data renders correctly, cross-page navigation works, and no regressions in existing functionality.

TASKS:
1. Full dev mode walkthrough (python -m argus.api --dev + npm run dev):
   a. Login
   b. Dashboard: verify OrchestratorStatusStrip, HeatStripPortfolioBar, GoalTracker all render with mock data
   c. Click StatusStrip → verify navigation to Orchestrator
   d. Click HeatStrip segment → verify SymbolDetailPanel opens
   e. Add ?premarket=true → verify PreMarketLayout renders
   f. Navigate to Trades → verify existing functionality unchanged
   g. Navigate to Performance → verify all 5 tabs:
      - Overview: existing content + comparison toggle
      - Heatmaps: heatmap grid populated, calendar shows days with P&L
      - Distribution: histogram bars, waterfall chart
      - Portfolio: treemap rectangles, correlation matrix 4x4
      - Replay: trade selector with mock trades, playback works
   h. Navigate to Orchestrator → verify existing functionality unchanged
   i. Navigate to Pattern Library → verify existing functionality unchanged
   j. Navigate to Debrief → verify existing functionality unchanged
   k. Navigate to System → verify: no strategy cards, no emergency controls, intelligence placeholders visible
   l. Press 'c' → verify Copilot panel opens with placeholder content
   m. Verify context indicator shows correct page name
   n. Close panel → verify button reappears

2. Mobile walkthrough (browser dev tools, 393px):
   a. Verify 5 bottom tabs (Dashboard, Trades, Orchestrator, Patterns, More)
   b. Tap More → verify bottom sheet with Performance, Debrief, System
   c. Navigate to each page via More sheet
   d. Verify copilot button positioned above tab bar
   e. Tap copilot button → full-screen overlay panel

3. Cross-page navigation verification:
   - Keyboard shortcuts 1-7 all work
   - 'w' watchlist toggle works on all pages
   - 'c' copilot toggle works on all pages
   - Symbol clicks from any page open SymbolDetailPanel
   - Trade clicks from Trade Log open TradeDetailPanel

4. Check for regressions:
   - Run full Vitest suite: cd argus/ui && npx vitest run
   - Run full pytest suite: pytest
   - Verify no console errors in browser dev tools
   - Verify no TypeScript errors: npx tsc --noEmit

5. Fix any issues found.

Target: ~2 new Vitest tests (if gaps found). Commit: "test: sprint 21d integration verification"

>>> CHECKPOINT: After this session, take final screenshots for Code Review #3.
Capture at desktop width:
- Dashboard (market hours)
- Dashboard (pre-market)
- Performance: all 5 tabs
- System page
- Mobile: Dashboard + More sheet + Copilot
Total: ~12 screenshots needed for Final Review.
```

---

## Session 14: Docs + Commit Cleanup

```
Sprint 21d, Session 14 of 14: Documentation + Commit Cleanup

CONTEXT: Final session. Update all project documentation and clean up commits.

TASKS:
1. Update CLAUDE.md:
   - Current State: Sprint 21d COMPLETE, test counts
   - Add Sprint 21d Results section
   - Update Build Track queue (21d done, Sprint 22 next)
   - Add new components to Components implemented list

2. Update docs/05_DECISION_LOG.md:
   - Add DEC-204 through DEC-218 (all decisions from sprint spec)
   - Verify no number gaps or duplicates

3. Update docs/02_PROJECT_KNOWLEDGE.md:
   - Sprint 21d entry in Build Track with test counts and summary
   - Update "Next Build sprints" to show Sprint 22 as NEXT
   - Add new decisions to Key Decisions section

4. Update docs/10_PHASE3_SPRINT_PLAN.md:
   - Move Sprint 21d to completed table
   - Record test counts and outcomes

5. Update docs/03_ARCHITECTURE.md:
   - New API endpoints (heatmap, distribution, correlation, replay, goals)
   - New UI components (copilot, performance charts, nav components)

6. Commit all doc changes: "docs: sprint 21d completion — decisions, architecture, sprint plan"

7. Final commit message for any remaining changes.

8. Tag: No git tag needed (tags reserved for phase completions).
```
