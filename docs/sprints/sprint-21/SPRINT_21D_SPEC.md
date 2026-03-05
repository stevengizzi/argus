# Sprint 21d — Implementation Spec
## Dashboard Refinement + Performance Analytics + System Cleanup + AI Copilot Shell + Nav Restructure

**Sprint dates:** Feb 27–28, 2026
**Starting tests:** 1664 pytest + 138 Vitest
**Target tests:** ~1689 pytest + ~182 Vitest
**Sessions:** 14 (implementation) + code reviews at checkpoints
**Decisions:** DEC-204 through DEC-218

---

## Overview

Sprint 21d is the final sub-sprint of Sprint 21 (DEC-171). It refines the three original Command Center pages (Dashboard, Performance, System) now that functionality has been redistributed across newer pages (Orchestrator, Pattern Library, The Debrief), restructures navigation for 7 pages, adds serious analytical depth to Performance, and builds the AI Copilot shell that Sprint 22 will activate.

### Design Principles (DEC-109)
- "Bloomberg Terminal meets modern fintech" — information density with visual craft
- Dashboard answers "How am I doing right now?" in under 2 seconds
- Performance is the analytical backbone — comprehensive quantitative tools
- System narrows to infrastructure health only
- Copilot shell establishes the architecture Sprint 22 activates

---

## Sub-Component A: Dashboard Scope Refinement (DEC-204)

### Removals
Remove these components from Dashboard — they now live on Orchestrator:
- `RiskAllocationPanel` (contains CapitalAllocation donut/bars + RiskGauge + MarketRegimeCard) → Orchestrator page
- Emergency controls (flatten all, pause all) → Orchestrator GlobalControls
- Per-strategy pause/resume → Orchestrator StrategyOperationsGrid

### New Components

#### 1. OrchestratorStatusStrip
**File:** `argus/ui/src/features/dashboard/OrchestratorStatusStrip.tsx`

Single-line data-dense row at top of Dashboard. Contains:
- Strategy count: "4 strategies active"
- Deployed capital: "$24,500 deployed (24.5%)"
- Daily risk consumed: "Risk: 12% of daily budget"
- Regime badge: "Bullish Trending" (colored)
- Click anywhere → `navigate('/orchestrator')`

Data source: `useOrchestratorStatus()` hook (already exists). Falls back gracefully if orchestrator unavailable.

**Responsive:**
- Desktop/tablet: single horizontal row with `|` dividers
- Mobile: 2×2 grid (strategies+capital top, risk+regime bottom)

#### 2. HeatStripPortfolioBar
**File:** `argus/ui/src/features/dashboard/HeatStripPortfolioBar.tsx`

Horizontal bar below OrchestratorStatusStrip. Custom SVG.
- One segment per open position
- Width proportional to capital allocation (position value / total equity)
- Color: green-to-red gradient based on unrealized P&L %
  - Deep green: >+2%, Light green: 0–2%, Light red: 0 to -1%, Deep red: < -1%
- Hover tooltip: symbol, P&L, shares, strategy
- Click segment → open SymbolDetailPanel for that symbol
- Empty state: subtle "No open positions" text, gray bar background

Data source: `usePositions()` hook (already exists) + `useAccount()` for equity.

**Responsive:** Full width on all breakpoints. Minimum segment width 20px — if too many positions, last segments merge into "X more" indicator.

#### 3. PreMarketLayout
**File:** `argus/ui/src/features/dashboard/PreMarketLayout.tsx`

Renders instead of normal Dashboard content when `market_status === 'pre_market'` (before 9:30 AM ET).

Layout:
- **MarketCountdown** component: "Market opens in 2h 14m" with live countdown timer
- **Ranked Watchlist placeholder**: Empty table with columns (Rank, Symbol, Gap%, Catalyst, Quality, Flow). Header text: "Pre-Market Intelligence activating Sprint 23"
- **Regime Forecast card**: Placeholder with "Regime forecast available with AI Layer (Sprint 22)"
- **Catalyst Summary area**: Placeholder card with "Catalyst pipeline activating Sprint 23"
- **Yesterday's summary**: Reuse `SessionSummaryCard` if data exists

Time gate: Check `accountData.market_status` from `useAccount()`. In dev mode, provide a toggle to preview pre-market layout.

**Responsive:** Same breakpoint behavior as normal Dashboard.

#### 4. GoalTracker
**File:** `argus/ui/src/features/dashboard/GoalTracker.tsx`

Persistent widget showing monthly target progress.
- Display: "Target: $5,000/mo | Current: $3,200 (64%) | 8 days remaining"
- Progress bar (thin, horizontal) with color: green if on pace, amber if behind, red if significantly behind
- "On pace" calculation: current P&L / (elapsed trading days / total trading days in month) >= target
- Trading days remaining: approximate (22 days/month - elapsed weekdays)

Data source: Monthly target from config (new field `monthly_target_usd` in SystemConfig, default 5000). Current month P&L from `usePerformance('month')`.

**Config addition:**
```yaml
# In config/system.yaml
goals:
  monthly_target_usd: 5000
```

**Pydantic model update:** Add `goals` section to `SystemConfig` with `GoalsConfig` sub-model.

**API update:** Expose `monthly_target_usd` in account or a new lightweight config endpoint.

#### 5. MarketCountdown
**File:** `argus/ui/src/features/dashboard/MarketCountdown.tsx`

Live countdown to market open. Uses `setInterval` (1s) computing difference between now and next 9:30 AM ET. Displays as "2h 14m" or "14m 30s" when under 1 hour. Shows "Market Open" with green pulse when market is open.

### Dashboard Page Layout (Revised)

```
Desktop (≥1024px):
┌─────────────────────────────────────────────────────┐
│ OrchestratorStatusStrip (click → Orchestrator)      │
├─────────────────────────────────────────────────────┤
│ HeatStripPortfolioBar                               │
├─────────────────────────────────────────────────────┤
│ SessionSummaryCard (after-hours only)               │
├──────────┬──────────┬───────────────────────────────┤
│ Account  │ DailyPnl │ GoalTracker                   │
├──────────┴──────────┴───────────────────────────────┤
│ Market Status  │  Market Regime                      │
├─────────────────────────────────────────────────────┤
│ OpenPositions                                       │
├──────────────────────┬──────────────────────────────┤
│ RecentTrades         │ HealthMini                    │
└──────────────────────┴──────────────────────────────┘

Pre-Market Layout (before 9:30 AM ET):
┌─────────────────────────────────────────────────────┐
│ MarketCountdown                                     │
├─────────────────────────────────────────────────────┤
│ SessionSummaryCard (yesterday's)                    │
├──────────────────────┬──────────────────────────────┤
│ Ranked Watchlist     │ Regime Forecast              │
│ (placeholder)        │ (placeholder)                │
├──────────────────────┼──────────────────────────────┤
│ Catalyst Summary     │ GoalTracker                  │
│ (placeholder)        │                              │
└──────────────────────┴──────────────────────────────┘
```

Watchlist sidebar unchanged — still available on all pages via `w` toggle.

---

## Sub-Component B: Performance Page Analytics (DEC-205)

### Architecture: Tabbed Sub-Views

The Performance page expands from a single scroll view to a **tabbed layout** using the existing `SegmentedTab` component pattern.

**Tabs:**
1. **Overview** (default) — existing content: metrics grid, equity curve, daily P&L histogram, strategy breakdown + NEW comparative period overlay
2. **Heatmaps** — trade activity heatmap + calendar P&L view
3. **Distribution** — R-multiple histogram + risk waterfall
4. **Portfolio** — treemap + correlation matrix
5. **Replay** — trade replay mode

Period selector remains global (above tabs, affects all tab content).

**File:** `argus/ui/src/pages/PerformancePage.tsx` — refactored with tab state.

### New Components

#### 1. TradeActivityHeatmap (DEC-206)
**File:** `argus/ui/src/features/performance/TradeActivityHeatmap.tsx`

Time-of-day (x-axis, 9:30–16:00 in 30-min bins = 13 columns) × day-of-week (y-axis, Mon–Fri = 5 rows) grid.

- Each cell colored by metric (toggle: avg R-multiple or net P&L)
- Color scale: diverging red-white-green (0 = white/neutral gray)
- Cell shows trade count as small number
- Hover tooltip: time range, day, trade count, avg R, net P&L
- Click cell → navigates to Trade Log with time/day filter pre-applied
- Empty cells: dark neutral background

**Library:** D3 for color scales (`d3-scale`, `d3-color`). React renders the SVG structure, D3 provides `scaleSequential` with `interpolateRdYlGn` diverging palette.

**Data source:** New `GET /api/v1/performance/heatmap` endpoint.

**Responsive:**
- Desktop: full grid with labels
- Tablet: full grid, smaller cells
- Mobile: horizontally scrollable, or rotate labels

#### 2. CalendarPnlView
**File:** `argus/ui/src/features/performance/CalendarPnlView.tsx`

Monthly calendar grid (7 cols × 5-6 rows) showing daily P&L.
- Each day cell: date number + P&L value + background color (green/red intensity)
- Weekend cells grayed out
- Month navigation (← →) or show current period's months
- Click day → filter Trade Log to that date
- Summary row: weekly totals

**Library:** Custom SVG. Similar to GitHub contribution heatmap but in calendar format.

**Data source:** Existing `daily_pnl` array from `usePerformance()`. No new endpoint needed — compute calendar layout client-side.

**Responsive:**
- Desktop/tablet: standard calendar grid
- Mobile: compact with abbreviated day names, smaller cells

#### 3. RMultipleHistogram
**File:** `argus/ui/src/features/performance/RMultipleHistogram.tsx`

Distribution of trade outcomes in R-multiples.
- X-axis: R-multiple bins (-3R to +4R in 0.25R increments)
- Y-axis: trade count
- Color: red for negative R, green for positive R
- Vertical line at 0R and at average R
- Strategy filter (dropdown to isolate one strategy)
- Hover: bin range, count, % of total

**Library:** Recharts `BarChart`.

**Data source:** New `GET /api/v1/performance/distribution` endpoint.

#### 4. RiskWaterfall
**File:** `argus/ui/src/features/performance/RiskWaterfall.tsx`

"If all stops hit" worst-case scenario by position.
- Horizontal bar chart, one bar per open position
- Bar length = potential loss (shares × (entry_price - stop_price))
- Running total line showing cumulative worst-case
- Color: intensity by % of account
- Labels: symbol, risk amount, % of equity

**Library:** Custom SVG. Horizontal bars with running total line overlay.

**Data source:** Computed client-side from `usePositions()` data. Each position has entry_price and stop_price.

#### 5. PortfolioTreemap (DEC-207)
**File:** `argus/ui/src/features/performance/PortfolioTreemap.tsx`

Rectangles sized by capital allocation, colored by P&L.
- Each rectangle = one open position
- Size = position value (shares × current_price)
- Color = unrealized P&L % (diverging green-red)
- Label: symbol name + P&L %
- Hover tooltip: full position details
- Click → open SymbolDetailPanel

**Library:** D3 `treemap` layout + `hierarchy`. React renders the positioned rectangles.

**Data source:** Computed client-side from `usePositions()` + `useAccount()`.

**Responsive:**
- Desktop: full treemap
- Mobile: simplified list view fallback (treemap unreadable at small sizes)

#### 6. CorrelationMatrix
**File:** `argus/ui/src/features/performance/CorrelationMatrix.tsx`

Pairwise strategy return correlation heatmap.
- NxN grid (N = number of strategies, currently 4)
- Color: diverging blue-white-red (-1 to +1)
- Diagonal = 1.0 (self-correlation, dark blue)
- Cell label: correlation coefficient
- Low correlation = good diversification

**Library:** D3 color scale, React SVG rendering.

**Data source:** New `GET /api/v1/performance/correlation` endpoint.

#### 7. ComparativePeriodOverlay (DEC-208)
**File:** Enhancement to existing `EquityCurve.tsx`

Ghost line on existing equity curve showing prior period.
- When period = "month", ghost line = previous month
- When period = "week", ghost line = previous week
- Ghost line: same shape, lower opacity (0.3), dashed
- Legend: "Current" (solid) vs "Previous" (dashed)
- Toggle on/off

**Implementation:** Add a second series to the existing Lightweight Charts instance. Requires fetching prior period data alongside current.

**Data source:** Two calls to existing `usePerformance()` — current period + shifted dates.

#### 8. TradeReplay (DEC-209)
**File:** `argus/ui/src/features/performance/TradeReplay.tsx`

Animated candlestick walkthrough of any closed trade.
- **Trade selector:** Dropdown of recent trades (from current period), or click "Replay" button in Trade Log
- **Chart:** Lightweight Charts candlestick (1-minute bars)
  - Time window: entry_time - 15 min to exit_time + 5 min
  - Entry marker: green triangle + dashed line at entry_price
  - Exit marker: red/green triangle at exit_price
  - Stop line: red dashed horizontal at stop_price
  - T1/T2 lines: blue dashed horizontals
  - Opening range: shaded rectangle (if ORB strategy)
  - VWAP line overlay (if VWAP strategy)
- **Playback controls:**
  - Play/Pause button
  - Speed selector: 1x, 2x, 5x, 10x
  - Scrubber: drag to any point in the trade
  - Step forward/backward (one bar at a time)
- **Info panel:** Current time, price, P&L at current playback position

**Implementation:** 
- Bars loaded all at once from API
- Playback uses `setInterval` to progressively reveal bars by setting `chart.timeScale().setVisibleRange()`
- Markers added at entry/exit bars
- Lines added as horizontal price lines

**Data source:** New `GET /api/v1/trades/{id}/replay` endpoint returning bars + trade metadata.

**Responsive:**
- Desktop: chart + controls side by side
- Mobile: chart full width, controls below as compact row

### Performance Page Layout (Revised)

```
┌─────────────────────────────────────────────────────┐
│ Performance            [Period: Today|Week|Month|All]│
├─────────────────────────────────────────────────────┤
│ [Overview] [Heatmaps] [Distribution] [Portfolio] [Replay] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  (Tab content renders here)                         │
│                                                     │
└─────────────────────────────────────────────────────┘

Overview tab:
  MetricsGrid
  EquityCurve (with comparative overlay toggle)
  DailyPnlChart
  StrategyBreakdown

Heatmaps tab:
  TradeActivityHeatmap
  CalendarPnlView

Distribution tab:
  RMultipleHistogram
  RiskWaterfall

Portfolio tab:
  PortfolioTreemap
  CorrelationMatrix

Replay tab:
  TradeReplay (full width)
```

### New Backend Endpoints

#### GET /api/v1/performance/heatmap
```python
class HeatmapCell(BaseModel):
    hour: int          # 9-15 (ET)
    day_of_week: int   # 0=Mon, 4=Fri
    trade_count: int
    avg_r_multiple: float
    net_pnl: float

class HeatmapResponse(BaseModel):
    cells: list[HeatmapCell]
    period: str
    timestamp: str
```

Query: Group trades by `strftime('%H', entry_time_et)` and `strftime('%w', entry_time_et)`.

#### GET /api/v1/performance/distribution
```python
class DistributionBin(BaseModel):
    range_min: float   # e.g., -1.0
    range_max: float   # e.g., -0.75
    count: int
    avg_pnl: float

class DistributionResponse(BaseModel):
    bins: list[DistributionBin]
    total_trades: int
    mean_r: float
    median_r: float
    period: str
    timestamp: str
```

Bins: 0.25R width from -3R to +4R (28 bins). Compute from trade `pnl_r_multiple`.

#### GET /api/v1/performance/correlation
```python
class CorrelationResponse(BaseModel):
    strategy_ids: list[str]
    matrix: list[list[float]]  # NxN correlation matrix
    period: str
    data_days: int
    timestamp: str
```

Implementation: `TradeLogger.get_daily_pnl_by_strategy()` → pivot to strategy columns → `numpy.corrcoef()`.

New TradeLogger method:
```python
async def get_daily_pnl_by_strategy(
    self,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Get daily P&L broken out by strategy.
    
    Returns list of {date, strategy_id, pnl} rows.
    """
```

#### GET /api/v1/trades/{trade_id}/replay
```python
class ReplayBar(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class TradeReplayResponse(BaseModel):
    trade: Trade
    bars: list[ReplayBar]
    entry_bar_index: int
    exit_bar_index: int | None
    vwap: list[float] | None  # VWAP values aligned with bars
    timestamp: str
```

Implementation: 
- Live mode: query DataService for historical bars around trade time window
- Dev mode: generate synthetic bars that create a plausible trade scenario

---

## Sub-Component C: System Page Cleanup (DEC-210)

### Removals
- `StrategyCards` component — removed from SystemPage (strategy info on Pattern Library, operations on Orchestrator)
- `EmergencyControls` component — removed from SystemPage (lives on Orchestrator GlobalControls)

### Additions

#### IntelligencePlaceholders
**File:** `argus/ui/src/features/system/IntelligencePlaceholders.tsx`

Grid of placeholder cards for future intelligence components. Each card:
- Component name
- "Not Yet Active" badge (neutral gray)
- Sprint number when it activates
- Brief description of what it will do

Cards:
1. **AI Copilot** — "Sprint 22 — Contextual Claude chat from every page"
2. **Pre-Market Engine** — "Sprint 23 — Automated 4:00 AM scanning + watchlist generation"
3. **Catalyst Service** — "Sprint 23 — News/filing classification and scoring"
4. **Order Flow Analyzer** — "Sprint 24 — L2/L3 depth analysis and flow signals"
5. **Setup Quality Engine** — "Sprint 25 — Composite 0–100 trade scoring"
6. **Learning Loop** — "Sprint 30 — Score calibration and continuous improvement"

**Layout:** 2-col grid on desktop, single column on mobile. Same card styling as ComponentStatusList.

### System Page Layout (Revised)

```
┌─────────────────────────────────────────────────────┐
│ System                                              │
├──────────────────────┬──────────────────────────────┤
│ SystemOverview       │ ComponentStatusList           │
│ (uptime, mode,       │ (Event Bus, Data Service,     │
│  data/broker source) │  Broker, Database, API)       │
├──────────────────────┴──────────────────────────────┤
│ Intelligence Components                             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│ │AI Copilot│ │Pre-Market│ │Catalyst  │             │
│ │Sprint 22 │ │Sprint 23 │ │Sprint 23 │             │
│ └──────────┘ └──────────┘ └──────────┘             │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│ │Order Flow│ │Quality   │ │Learning  │             │
│ │Sprint 24 │ │Sprint 25 │ │Sprint 30 │             │
│ └──────────┘ └──────────┘ └──────────┘             │
├─────────────────────────────────────────────────────┤
│ EventsLog (collapsible)                             │
└─────────────────────────────────────────────────────┘
```

---

## Sub-Component D: Navigation Restructure (DEC-211)

### Desktop Sidebar

**File:** `argus/ui/src/layouts/Sidebar.tsx`

Add thin horizontal divider lines (`border-b border-argus-border/50`) between groups:

```
[Logo]
────────
Dashboard        ← Monitor group
Trades
Performance
────────
Orchestrator     ← Operate group
Patterns
────────
Debrief          ← Learn group
────────
System           ← Maintain group
────────
[Status] [Logout]
```

Implementation: Add `divider: true` property to NAV_ITEMS array between groups. Render as `<hr>` or `<div className="border-b ...">` in the nav loop.

### Mobile Bottom Bar

**File:** `argus/ui/src/layouts/MobileNav.tsx`

Change from 7 items to 5 primary + More:

Primary tabs: Dashboard, Trades, Orchestrator, Patterns, More
More menu contains: Performance, Debrief, System

**More menu item:**
- Icon: `MoreHorizontal` from lucide-react
- Tap opens `MoreSheet` bottom sheet

#### MoreSheet
**File:** `argus/ui/src/layouts/MoreSheet.tsx`

Framer Motion bottom sheet:
- Backdrop: `bg-black/60`, tap to dismiss
- Sheet: slides up from bottom, rounded top corners
- Content: 3 rows (Performance, Debrief, System) with icons and labels
- Each row is a NavLink that closes the sheet on click
- Drag handle at top (subtle gray bar)
- Escape to close

Animation: Framer Motion `motion.div` with `y: '100%'` → `y: 0` spring animation.

**State:** Local state in MobileNav (no Zustand needed — simple open/close).

### Keyboard Shortcuts Update

**File:** `argus/ui/src/layouts/Sidebar.tsx` (keyboard handler)

Shortcuts remain `1`–`7` for all pages. The More menu is a mobile-only UI pattern — keyboard shortcuts work on all surfaces.

Add `c` for Copilot toggle (implemented in Sub-Component E).

### Route Updates

No routing changes needed — all 7 routes already exist from Sprint 21c. Only nav component rendering changes.

---

## Sub-Component E: AI Copilot Shell (DEC-212)

### CopilotPanel
**File:** `argus/ui/src/features/copilot/CopilotPanel.tsx`

Slide-out chat panel. **New component, not reusing SlideInPanel** — different lifecycle (persists across pages, maintains chat state, different z-index layer).

**Desktop (≥1024px):**
- Right side, 35% width (min 400px, max 560px)
- Slides in from right (spring animation matching SlideInPanel physics)
- Backdrop: semi-transparent `bg-black/40`
- Does NOT block page interaction entirely — backdrop click closes

**Mobile (<1024px):**
- Full-screen overlay from bottom (90vh)
- Same pattern as SlideInPanel mobile behavior

**Panel structure:**
```
┌─────────────────────────────────┐
│ 🤖 AI Copilot        [Context] X│  ← Header
│ Page: Dashboard                 │  ← Context indicator
├─────────────────────────────────┤
│                                 │
│  (Placeholder message area)     │  ← Scrollable
│                                 │
│  ┌─────────────────────────┐    │
│  │ 🤖 AI Copilot           │    │
│  │                         │    │
│  │ Contextual AI assistant │    │
│  │ activating Sprint 22.   │    │
│  │                         │    │
│  │ Soon you'll chat with   │    │
│  │ Claude here — page-     │    │
│  │ aware, with full system │    │
│  │ knowledge.              │    │
│  │                         │    │
│  │ Features coming:        │    │
│  │ • Answer questions      │    │
│  │ • Generate reports      │    │
│  │ • Propose changes       │    │
│  │ • Annotate trades       │    │
│  └─────────────────────────┘    │
│                                 │
├─────────────────────────────────┤
│ [Message input - disabled]  [→] │  ← Input (disabled placeholder)
└─────────────────────────────────┘
```

**Context indicator:** Shows current page name from React Router `useLocation()`. Maps pathname to label:
- `/` → "Dashboard"
- `/trades` → "Trade Log"
- `/performance` → "Performance"
- etc.

When a specific entity is selected (future Sprint 22 feature), context shows: "Dashboard > AAPL position".

**Placeholder state:** Single centered card with AI icon, description text, and bullet list of Sprint 22 features. Input field present but disabled with placeholder text "Activating Sprint 22...".

### CopilotButton
**File:** `argus/ui/src/features/copilot/CopilotButton.tsx`

Floating action button that toggles CopilotPanel.

**Desktop (≥1024px):**
- Fixed position: bottom-right, 24px from edges
- Size: 48px circle
- Icon: `MessageCircle` from lucide-react (or custom AI icon)
- Background: `bg-argus-accent`
- Hover: slight scale up (1.05)
- Subtle entrance animation on first page load (scale from 0 to 1 with spring)

**Mobile (<1024px):**
- Fixed position: bottom-right, 16px from right edge
- Bottom: above tab bar (`bottom: 80px` to clear MobileNav h-16 + pb-3 + gap)
- Same icon and styling
- Active:scale-95 for tap feedback

**When panel is open:** Button hides (panel has its own close button).

### CopilotPlaceholder
**File:** `argus/ui/src/features/copilot/CopilotPlaceholder.tsx`

The placeholder content shown inside CopilotPanel. Extracted as separate component for clean replacement in Sprint 22.

### Zustand Store
**File:** `argus/ui/src/stores/copilotUI.ts`

```typescript
interface CopilotUIState {
  isOpen: boolean;
  toggle: () => void;
  open: () => void;
  close: () => void;
}
```

Session-level only (no persist). Panel remembers open/closed state during navigation.

### Keyboard Shortcut
`c` key toggles copilot panel. Suppressed in input/textarea/contentEditable. Added to existing keyboard handler in `Sidebar.tsx`.

### AppShell Integration
**File:** `argus/ui/src/layouts/AppShell.tsx`

Add `CopilotPanel` and `CopilotButton` as global components (mounted once, persist across pages):

```tsx
{/* Global panels */}
<SymbolDetailPanel />
<CopilotPanel />
<CopilotButton />
```

---

## Sub-Component F: Backend Changes

### New Endpoints Summary

| Endpoint | Method | File | Purpose |
|----------|--------|------|---------|
| `/api/v1/performance/heatmap` | GET | `performance.py` | Trade activity by hour×weekday |
| `/api/v1/performance/distribution` | GET | `performance.py` | R-multiple histogram bins |
| `/api/v1/performance/correlation` | GET | `performance.py` | Strategy correlation matrix |
| `/api/v1/trades/{trade_id}/replay` | GET | `trades.py` | Historical bars for trade replay |
| `/api/v1/config/goals` | GET | `config.py` (new) | Goal tracking config |

### New TradeLogger Method

```python
async def get_daily_pnl_by_strategy(
    self,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Get daily P&L broken out by strategy.
    
    Returns: [{"date": "2026-02-27", "strategy_id": "strat_orb_breakout", "pnl": 150.0}, ...]
    """
```

SQL: `SELECT date(exit_time) as date, strategy_id, SUM(pnl_dollars) as pnl FROM trades WHERE exit_time IS NOT NULL GROUP BY date, strategy_id`

### Config Changes

Add to `SystemConfig`:
```python
class GoalsConfig(BaseModel):
    monthly_target_usd: float = 5000.0

class SystemConfig(BaseModel):
    # ... existing fields ...
    goals: GoalsConfig = GoalsConfig()
```

Add to `config/system.yaml`:
```yaml
goals:
  monthly_target_usd: 5000
```

### Dev Mode Mock Data Expansion

**File:** `argus/api/dev_state.py`

Add mock data for:
1. **Heatmap:** Generate realistic trade distribution (more trades 9:30–11:00 AM, fewer afternoon)
2. **Distribution:** Generate R-multiple distribution (slightly positive skew, peak at -1R and +0.5R)
3. **Correlation:** Generate 4×4 correlation matrix (low correlations 0.1–0.3 for good diversification)
4. **Replay bars:** Generate synthetic 1-minute bars that create a plausible ORB trade scenario
5. **Goals config:** Default $5,000/month target

---

## Dependencies

### New npm packages
- `d3-scale` — color scales for heatmaps
- `d3-color` — color interpolation
- `d3-hierarchy` — treemap layout
- `d3-interpolate` — color interpolation helpers

Install: `npm install d3-scale d3-color d3-hierarchy d3-interpolate @types/d3-scale @types/d3-color @types/d3-hierarchy @types/d3-interpolate`

Note: We import individual D3 modules, NOT the full `d3` bundle. Keeps bundle size minimal.

### New Python packages
- `numpy` (already installed for backtesting) — used for correlation matrix computation

---

## Test Requirements

### Backend (pytest)
- Heatmap endpoint: empty data, single trade, multiple trades across hours/days, strategy filter, period filter (~5 tests)
- Distribution endpoint: empty data, various R-multiples, bin boundaries, strategy filter (~4 tests)
- Correlation endpoint: insufficient data, 2 strategies, 4 strategies, period filter (~4 tests)
- Replay endpoint: valid trade, trade not found, bars generation (~3 tests)
- Goals config endpoint: default value, custom value (~2 tests)
- TradeLogger.get_daily_pnl_by_strategy: empty, single strategy, multiple strategies, date range (~4 tests)
- **Total: ~22 new pytest tests**

### Frontend (Vitest)
- OrchestratorStatusStrip: renders with data, fallback without data, click navigation (~3 tests)
- HeatStripPortfolioBar: renders segments, color mapping, empty state (~3 tests)
- GoalTracker: on pace, behind pace, renders percentages (~3 tests)
- PreMarketLayout: renders countdown, shows placeholders (~2 tests)
- MoreSheet: opens/closes, navigation works (~2 tests)
- TradeActivityHeatmap: renders grid, handles empty data (~2 tests)
- RMultipleHistogram: renders bars, handles empty data (~2 tests)
- CalendarPnlView: renders calendar, day colors (~2 tests)
- CorrelationMatrix: renders NxN grid, color scale (~2 tests)
- PortfolioTreemap: renders rectangles, handles empty (~2 tests)
- RiskWaterfall: renders bars, running total (~2 tests)
- TradeReplay: renders chart, playback controls (~3 tests)
- CopilotPanel: opens/closes, context indicator, placeholder content (~3 tests)
- CopilotButton: renders, responsive position, hides when panel open (~2 tests)
- Navigation: sidebar dividers render, More sheet opens (~3 tests)
- **Total: ~36 new Vitest tests**

---

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-204 | Dashboard narrows to ambient awareness; CapitalAllocation, RiskGauge, emergency controls removed (live on Orchestrator). OrchestratorStatusStrip replaces as compact data-dense row. | Avoids duplication across Dashboard and Orchestrator. Status strip provides essential numbers in one line. |
| DEC-205 | Performance page expands with 8 new visualizations in 5-tab layout (Overview, Heatmaps, Distribution, Portfolio, Replay). | Performance is the analytical backbone. Full suite built now to avoid return trips. |
| DEC-206 | Trade Activity Heatmap uses D3 color scales with React SVG rendering. | D3 provides superior diverging color scales. React handles DOM. Best of both. |
| DEC-207 | Portfolio Treemap uses D3 hierarchy + treemap layout. | Treemap tiling algorithms are non-trivial. D3 is the right tool. |
| DEC-208 | Comparative Period Overlay adds ghost line to existing EquityCurve via second Lightweight Charts series. | Minimal new code, high insight value. |
| DEC-209 | Trade Replay uses Lightweight Charts with progressive bar reveal for playback animation. | Reuses existing chart library. setInterval + setVisibleRange creates smooth playback. |
| DEC-210 | System page removes StrategyCards and EmergencyControls (migrated). Adds intelligence component placeholders. | Clean separation: Pattern Library for strategy info, Orchestrator for operations, System for infrastructure. |
| DEC-211 | Desktop sidebar gets thin divider lines between nav groups. Mobile bottom bar changes to 5 tabs + More bottom sheet. | Dividers felt but not read. Bottom sheet is native-feeling mobile overflow pattern. |
| DEC-212 | AI Copilot shell is a new CopilotPanel component (not reusing SlideInPanel). Persists across pages, has chat UI, own z-index layer. | Different lifecycle from data panels. Will grow significantly in Sprint 22. Starting fresh avoids fighting assumptions. |
| DEC-213 | Pre-market Dashboard layout is a full shell with placeholder cards, not just a message. Time-gated on market_status. | Building the layout now means Sprint 23 wires data into existing components rather than designing from scratch. |
| DEC-214 | Goal tracking reads monthly_target_usd from config YAML via GoalsConfig. System page provides edit capability. | Simple config value for V1. Database-backed goals with history can upgrade later. |
| DEC-215 | D3 used for heatmap, treemap, and correlation matrix (data-dense grid visualizations). Recharts for histogram. Custom SVG for calendar and waterfall. Lightweight Charts for replay and overlay. | Each library used where it excels. D3 individual modules imported, not full bundle. |
| DEC-216 | Mobile primary tabs: Dashboard, Trades, Orchestrator, Patterns, More. Performance/Debrief/System in More sheet. | Market hours (primary mobile use) need ambient awareness and operational control. Analytics/review done on desktop. |
| DEC-217 | CopilotButton position: desktop bottom-right 24px inset, mobile above tab bar right-aligned. Hides when panel open. | Avoids tab bar overlap on mobile. Clean toggle behavior. |
| DEC-218 | Performance tabs: Overview, Heatmaps, Distribution, Portfolio, Replay. Period selector global above tabs. | Organizes 8 new visualizations without overwhelming. Each tab is a focused analytical lens. |
