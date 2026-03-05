# Sprint 21a — Pattern Library Page — Implementation Spec

> **Sprint:** 21a of 21a–21d split (DEC-171)
> **Scope:** Pattern Library page, Incubator Pipeline visualization, Stock/Asset Detail Panel
> **Test baseline:** 1522 pytest + 48 Vitest = 1570 total
> **Test target:** ~1545 pytest (~23 new) + ~65 Vitest (~17 new) = ~1610 total
> **Estimated sessions:** 8–10 Claude Code sessions
> **Estimated hours:** ~33h

---

## 1. Context

ARGUS has 4 active strategies (ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum), a 4-page Command Center (Dashboard, Trade Log, Performance, System), and the expanded vision (DEC-163) calls for 7 pages (DEC-169). Sprint 21a adds the 5th page: **Pattern Library** — the strategy encyclopedia.

### Key Decisions Made During Planning

- **DEC-172:** Strategy metadata enrichment — extend `GET /api/v1/strategies` with `time_window`, `family`, `description_short`, `performance_summary`, `backtest_summary`. Single endpoint, no separate `/patterns` route. Performance summary computed via TradeLogger per-strategy queries.
- **DEC-173:** Pipeline stage stored in strategy config YAML as `pipeline_stage` field. Manual update. 10-stage vocabulary: concept, exploration, validation, ecosystem_replay, paper_trading, live_minimum, live_full, active_monitoring, suspended, retired.
- **DEC-174:** Strategy family classification in config YAML as `family` field. Values: `orb_family`, `momentum`, `mean_reversion`. Display names mapped in frontend.
- **DEC-175:** Strategy spec sheets served as markdown via `GET /api/v1/strategies/{strategy_id}/spec`. Backend reads from `docs/strategies/STRATEGY_*.md`. Frontend renders with `react-markdown`.
- **DEC-176:** Backtest tab as structured placeholder. Summary metrics stored in strategy config YAML under `backtest_summary` key. Interactive explorer deferred to Sprint 21d.
- **DEC-177:** SlideInPanel extraction — shared animated shell component. TradeDetailPanel refactored to use it. SymbolDetailPanel is a new consumer. Zustand `symbolDetailUI` store for global trigger.
- **DEC-178:** Fundamentals section (market cap, float, sector) deferred to Sprint 23 when Finnhub/FMP data source exists. Symbol Detail Panel ships with chart + trading history + position detail only.
- **DEC-179:** Incubator Pipeline responsive design — connected pipeline with arrows on desktop/tablet, compact horizontal scrollable pills on mobile. HTML/CSS implementation (no SVG).

---

## 2. Config YAML Changes

### All 4 strategy YAML files get these new fields:

```yaml
# New fields (add after version/enabled/asset_class)
pipeline_stage: "paper_trading"
family: "orb_family"        # or "momentum", "mean_reversion"
description_short: "One-line thesis"
time_window_display: "9:35–11:30 AM"

# New section (add at bottom)
backtest_summary:
  status: "walk_forward_complete"  # or "sweep_complete", "not_validated"
  wfe_pnl: 0.56
  oos_sharpe: 0.34
  total_trades: 137
  data_months: 35
  last_run: "2026-02-17"
```

#### Per-strategy values:

**orb_breakout.yaml:**
```yaml
pipeline_stage: "paper_trading"
family: "orb_family"
description_short: "Exploits gapping stocks breaking out of the first 5 minutes' high with volume confirmation."
time_window_display: "9:35–11:30 AM"
backtest_summary:
  status: "walk_forward_complete"
  wfe_pnl: 0.56
  oos_sharpe: 0.34
  total_trades: 137
  data_months: 35
  last_run: "2026-02-17"
```

**orb_scalp.yaml:**
```yaml
pipeline_stage: "paper_trading"
family: "orb_family"
description_short: "Quick 0.3R scalp on the same opening range breakout pattern, exiting within 120 seconds."
time_window_display: "9:45–11:30 AM"
backtest_summary:
  status: "not_validated"
  wfe_pnl: null
  oos_sharpe: null
  total_trades: 20880
  data_months: 35
  last_run: "2026-02-25"
```

**vwap_reclaim.yaml:**
```yaml
pipeline_stage: "paper_trading"
family: "mean_reversion"
description_short: "Enters long when a gapping stock pulls back below VWAP, then reclaims above on volume."
time_window_display: "10:00 AM–12:00 PM"
backtest_summary:
  status: "walk_forward_complete"
  wfe_pnl: null
  oos_sharpe: 1.49
  total_trades: 59556
  data_months: 35
  last_run: "2026-02-26"
```

**afternoon_momentum.yaml:**
```yaml
pipeline_stage: "paper_trading"
family: "momentum"
description_short: "Catches afternoon consolidation breakouts in gapping stocks between 2:00–3:30 PM."
time_window_display: "2:00–3:30 PM"
backtest_summary:
  status: "sweep_complete"
  wfe_pnl: null
  oos_sharpe: null
  total_trades: null
  data_months: 35
  last_run: "2026-02-26"
```

### Pydantic Config Model Updates

Add to `StrategyConfig` (base class in `argus/core/config.py`):
```python
pipeline_stage: str = "concept"
family: str = "uncategorized"
description_short: str = ""
time_window_display: str = ""
```

Add a new model:
```python
class BacktestSummaryConfig(BaseModel):
    status: str = "not_validated"
    wfe_pnl: float | None = None
    oos_sharpe: float | None = None
    total_trades: int | None = None
    data_months: int | None = None
    last_run: str | None = None
```

Add to each strategy-specific config (OrbBreakoutConfig, OrbScalpConfig, VwapReclaimConfig, AfternoonMomentumConfig):
```python
backtest_summary: BacktestSummaryConfig = BacktestSummaryConfig()
```

---

## 3. API Changes

### 3.1 Extend `GET /api/v1/strategies` (strategies.py)

**New response fields on StrategyInfo:**
```python
class PerformanceSummary(BaseModel):
    trade_count: int
    win_rate: float
    net_pnl: float
    avg_r: float
    profit_factor: float

class BacktestSummary(BaseModel):
    status: str
    wfe_pnl: float | None
    oos_sharpe: float | None
    total_trades: int | None
    data_months: int | None
    last_run: str | None

class StrategyInfo(BaseModel):
    # ... existing fields (keep all) ...
    time_window: str          # NEW — from config time_window_display
    family: str               # NEW — from config family
    description_short: str    # NEW — from config description_short
    performance_summary: PerformanceSummary | None = None  # NEW
    backtest_summary: BacktestSummary | None = None        # NEW
```

**Implementation:**
- Extract `time_window`, `family`, `description_short` from `strategy.config` via `getattr()`
- For `performance_summary`: call `trade_logger.get_trades_by_strategy(strategy_id)` → `compute_metrics()` → map to `PerformanceSummary`
- For `backtest_summary`: read from `strategy.config.backtest_summary` (the new Pydantic model)
- In dev mode: `MockStrategy` gets the new fields. `dev_state.py` mock data includes performance summaries.

**Note:** The `list_strategies` route becomes async because TradeLogger queries are async. It already is async, so no signature change needed.

### 3.2 New `GET /api/v1/strategies/{strategy_id}/spec` (strategies.py)

```python
class StrategySpecResponse(BaseModel):
    strategy_id: str
    content: str       # Raw markdown
    format: str = "markdown"

@router.get("/{strategy_id}/spec", response_model=StrategySpecResponse)
async def get_strategy_spec(
    strategy_id: str,
    _auth: dict = Depends(require_auth),
    state: AppState = Depends(get_app_state),
) -> StrategySpecResponse:
    """Serve strategy spec sheet as markdown."""
```

**Implementation:**
- Map strategy_id to filename: `strat_orb_breakout` → `STRATEGY_ORB_BREAKOUT.md`, etc.
- Use a dict mapping or derive from strategy_id (strip `strat_` prefix, uppercase, join with `_`)
- Read from `docs/strategies/STRATEGY_{NAME}.md` using `Path(__file__).parent.parent.parent / "docs" / "strategies"` to locate the docs directory
- Return 404 if file not found
- In dev mode: still serve real files (they exist on disk regardless of mode)

### 3.3 Extend `GET /api/v1/performance/{period}` (performance.py)

**Add optional query parameter:**
```python
@router.get("/{period}", response_model=PerformanceResponse)
async def get_performance(
    period: Literal["today", "week", "month", "all"] = "all",
    strategy_id: str | None = None,  # NEW
    _auth: dict = Depends(require_auth),
    state: AppState = Depends(get_app_state),
) -> PerformanceResponse:
```

**Implementation:**
- When `strategy_id` is provided, pass it to `trade_logger.query_trades()` and `trade_logger.get_daily_pnl()` as filter
- Everything else stays the same — `compute_metrics()` works on whatever trade list it receives
- The `by_strategy` dict in the response will only contain the single strategy when filtered

### 3.4 New `GET /api/v1/market/{symbol}/bars` (new file: market.py)

```python
class BarData(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class BarsResponse(BaseModel):
    symbol: str
    timeframe: str
    bars: list[BarData]
    count: int

@router.get("/{symbol}/bars", response_model=BarsResponse)
async def get_symbol_bars(
    symbol: str,
    timeframe: str = "1m",
    limit: int = 390,
    _auth: dict = Depends(require_auth),
    state: AppState = Depends(get_app_state),
) -> BarsResponse:
```

**Implementation:**
- In production mode: query DataService for recent bars (if data available)
- In dev mode: generate synthetic OHLCV data using deterministic random walk seeded by symbol name. Base price derived from hash of symbol. Generates `limit` bars starting from today's market open. Realistic price action with trends, volatility clustering, volume spikes at open/close.
- Register route in server.py as `market_router` with prefix `/api/v1/market`

### 3.5 Dev Mode Extensions (dev_state.py)

Extend `MockStrategy` with:
```python
@dataclass
class MockStrategy:
    # ... existing fields ...
    # New fields for Pattern Library
    family: str = "uncategorized"
    description_short: str = ""
    time_window_display: str = ""
```

**Extend `create_dev_state()`:**
- Set `family`, `description_short`, `time_window_display` on each mock strategy
- Add `backtest_summary` to each mock strategy config
- Populate `performance_summary` via mock trades already in TradeLogger (these already exist with `strategy_id` tags)

---

## 4. Frontend — New Components

### 4.1 Page: PatternLibraryPage

**File:** `argus/ui/src/pages/PatternLibraryPage.tsx`

**Structure:**
```
<AnimatedPage>
  <IncubatorPipeline onStageClick={filterByStage} />
  <div className="responsive-master-detail">
    {/* Desktop: side-by-side. Tablet/Mobile: stacked with drill-down */}
    <PatternCardGrid
      strategies={strategies}
      filters={filters}
      sort={sort}
      selectedId={selectedId}
      onSelect={setSelectedId}
    />
    {selectedId && (
      <PatternDetail
        strategyId={selectedId}
        onClose={() => setSelectedId(null)}
      />
    )}
  </div>
</AnimatedPage>
```

**Responsive behavior:**
- Desktop (≥1024px): `flex` row. Left panel 35% width, right panel 65% width. Both visible simultaneously.
- Tablet (640–1023px): Card grid fills width. Selecting a card transitions to full-width detail view with back button.
- Mobile (<640px): Same as tablet but stacked vertically. Full-screen detail on selection.

Use `useMediaQuery` hook (already exists) to switch layout mode.

### 4.2 Component: IncubatorPipeline

**File:** `argus/ui/src/features/patterns/IncubatorPipeline.tsx`

**Props:** `strategies: StrategyInfo[]`, `activeStageFilter: string | null`, `onStageClick: (stage: string | null) => void`

**Desktop/Tablet (≥640px):** Connected pipeline — horizontal flex row of stage nodes connected by chevron arrows (`→` or `›`). Each node shows stage name (abbreviated) and count badge. Active stages (count > 0) are bright, empty stages are dimmed. Clicking a stage toggles filter (click same stage again = clear filter). Active filter stage has ring/highlight.

**Stage abbreviations for pipeline display:**
| Full Name | Pipeline Label |
|-----------|---------------|
| concept | Concept |
| exploration | Explore |
| validation | Validate |
| ecosystem_replay | Eco Replay |
| paper_trading | Paper |
| live_minimum | Live Min |
| live_full | Live Full |
| active_monitoring | Monitor |
| suspended | Suspended |
| retired | Retired |

**Mobile (<640px):** Horizontal scrollable row of compact pills. Each pill: `Stage (N)`. Same click-to-filter behavior.

### 4.3 Component: PatternCardGrid

**File:** `argus/ui/src/features/patterns/PatternCardGrid.tsx`

**Contains:** Filter bar (PatternFilters), sort dropdown, and grid of PatternCards.

**Filters:**
- Stage: All / Paper / Active / Suspended / Retired (SegmentedTab)
- Family: All / ORB Family / Momentum / Mean-Reversion (SegmentedTab or dropdown)
- Time: All / Morning / Midday / Afternoon (SegmentedTab or dropdown)

**Sort:** Dropdown — Name (A→Z), P&L (high→low), Win Rate (high→low), Trade Count (high→low)

**Grid layout:**
- Desktop: 1 column (cards stack vertically in the 35% panel)
- Tablet/Mobile: 1 column (full width)

### 4.4 Component: PatternCard

**File:** `argus/ui/src/features/patterns/PatternCard.tsx`

**Shows:**
- Strategy name (bold)
- Pipeline stage badge (color-coded using existing Badge component)
- Family badge (smaller, dimmer)
- Time window text
- Mini stats row: trade count | win rate | net P&L
- Selected state: ring/border highlight

**Click:** Calls `onSelect(strategy_id)`.

**Color mapping for pipeline stages:**
- `paper_trading` → amber/warning
- `live_minimum`, `live_full`, `active_monitoring` → green/success
- `concept`, `exploration`, `validation`, `ecosystem_replay` → blue/info
- `suspended` → red/danger
- `retired` → gray/neutral

### 4.5 Component: PatternDetail

**File:** `argus/ui/src/features/patterns/PatternDetail.tsx`

**Props:** `strategyId: string`

**Structure:** SegmentedTab with 5 tabs — Overview, Performance, Backtest, Trades, Intelligence. Tab state persisted in patternLibraryUI store.

**Desktop:** Fills the right 65% panel. Scrollable.
**Tablet/Mobile:** Full-width view with back button at top.

### 4.6 Tab: OverviewTab

**File:** `argus/ui/src/features/patterns/tabs/OverviewTab.tsx`

**Two sections:**
1. **Parameter table** (top) — Grid of current config values from the strategy data. Two-column table: Parameter | Value. Formatted nicely (not raw YAML). Read-only label: "Parameters are view-only. Editing available with AI Layer (Sprint 22)."
2. **Strategy spec sheet** (below) — Rendered markdown from `/strategies/{id}/spec` endpoint. Uses `react-markdown` with `remark-gfm` for table support. Styled to match the app's dark theme. Tables, headings, code blocks all properly themed.

### 4.7 Tab: PerformanceTab

**File:** `argus/ui/src/features/patterns/tabs/PerformanceTab.tsx`

**Content:**
- Period selector (reuse PeriodSelector component from Performance page)
- Metrics grid (6 key metrics: Sharpe, PF, win rate, avg R, max DD, total trades) — reuse MetricCard
- Equity curve (LWChart, same as Performance page but filtered to this strategy)
- Daily P&L histogram (same chart component, filtered)

**Data source:** `GET /api/v1/performance/{period}?strategy_id={id}` — existing endpoint with new filter param.

### 4.8 Tab: BacktestTab

**File:** `argus/ui/src/features/patterns/tabs/BacktestTab.tsx`

**Content (from backtest_summary in strategy data):**
- Status badge: "Walk-Forward Complete" (green) / "Sweep Complete" (amber) / "Not Validated" (gray)
- Summary metrics card (if available): WFE (P&L), OOS Sharpe, Total Trades, Data Months, Last Run Date
- Note: "All pre-Databento backtests require re-validation with exchange-direct data (DEC-132)."
- Future placeholder: "Interactive backtest explorer and VectorBT heatmaps coming in Sprint 21d."

### 4.9 Tab: TradesTab

**File:** `argus/ui/src/features/patterns/tabs/TradesTab.tsx`

**Content:** Thin wrapper around existing `TradeTable` component with `strategy_id` locked as a filter.

Uses `useTrades` hook with the strategy_id filter. Passes trades to `TradeTable`. Click opens `TradeDetailPanel`.

### 4.10 Tab: IntelligenceTab

**File:** `argus/ui/src/features/patterns/tabs/IntelligenceTab.tsx`

**Content:** Placeholder with EmptyState component.
- Icon: Brain or Sparkles from lucide-react
- Message: "Intelligence features coming in Sprint 25"
- Sub-message: "Pattern strength scoring, quality grade breakdown, and Learning Loop insights will appear here."

### 4.11 Component: SlideInPanel (shared)

**File:** `argus/ui/src/components/SlideInPanel.tsx`

**Extracted from:** Existing TradeDetailPanel slide-in behavior.

**Props:**
```typescript
interface SlideInPanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  width?: string; // Desktop width, default "40%"
}
```

**Behavior:**
- Desktop: slides in from right, configurable width, overlay with backdrop
- Mobile: slides up from bottom, 90vh height
- Framer Motion animation (matches existing TradeDetailPanel)
- Close on: X button, Escape key, backdrop click
- Locks body scroll when open

**Refactor:** TradeDetailPanel becomes a consumer of SlideInPanel (it passes its content as children).

### 4.12 Component: SymbolDetailPanel

**File:** `argus/ui/src/features/symbol/SymbolDetailPanel.tsx`

**Triggered by:** `symbolDetailUI` Zustand store. Any component can call `useSymbolDetailUI.getState().open('AAPL')`.

**Content:**
1. **Header:** Symbol name, current price (if available from positions/live data), change
2. **Chart:** Candlestick chart via LWChart, consuming data from `GET /api/v1/market/{symbol}/bars`
3. **Trading History:** All trades for this symbol, summary stats (trade count, win rate, avg R, net P&L). Mini version of trade list (last 10 trades).
4. **Open Position (if any):** Current P&L, R-multiple, time in trade, stop/T1/T2 levels. Only shown if there's an active position on this symbol.

**Files also needed:**
- `argus/ui/src/features/symbol/SymbolChart.tsx` — LWChart candlestick wrapper
- `argus/ui/src/features/symbol/SymbolTradingHistory.tsx` — Trade summary + recent trades list
- `argus/ui/src/features/symbol/SymbolPositionDetail.tsx` — Open position info card
- `argus/ui/src/features/symbol/index.ts` — barrel export

### 4.13 Zustand Stores

**`argus/ui/src/stores/patternLibraryUI.ts`:**
```typescript
interface PatternLibraryUIState {
  selectedStrategyId: string | null;
  activeTab: string; // 'overview' | 'performance' | 'backtest' | 'trades' | 'intelligence'
  filters: {
    stage: string | null;    // pipeline stage or null for all
    family: string | null;   // family or null for all
    timeWindow: string | null; // 'morning' | 'midday' | 'afternoon' | null
  };
  sortBy: string; // 'name' | 'pnl' | 'win_rate' | 'trade_count'
  setSelectedStrategy: (id: string | null) => void;
  setActiveTab: (tab: string) => void;
  setFilter: (key: string, value: string | null) => void;
  setSortBy: (sort: string) => void;
}
```

**`argus/ui/src/stores/symbolDetailUI.ts`:**
```typescript
interface SymbolDetailUIState {
  selectedSymbol: string | null;
  isOpen: boolean;
  open: (symbol: string) => void;
  close: () => void;
}
```

### 4.14 TanStack Query Hooks

**`argus/ui/src/hooks/useStrategySpec.ts`:**
```typescript
// Fetches markdown spec sheet for a strategy
// Key: ['strategies', strategyId, 'spec']
// Stale time: 5 minutes (content changes rarely)
```

**`argus/ui/src/hooks/useSymbolBars.ts`:**
```typescript
// Fetches intraday bars for symbol detail chart
// Key: ['market', symbol, 'bars']
// Stale time: 30 seconds (price data)
```

**`argus/ui/src/hooks/useSymbolTrades.ts`:**
```typescript
// Fetches trades for a specific symbol
// Key: ['trades', { symbol }]
// Uses existing trades endpoint with symbol filter
```

### 4.15 Nav Updates

**Sidebar.tsx:** Add Pattern Library as 5th item:
```typescript
const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Performance' },
  { to: '/patterns', icon: BookOpen, label: 'Pattern Library' },  // NEW
  { to: '/system', icon: Activity, label: 'System' },
] as const;
```

Icon: `BookOpen` from lucide-react (represents encyclopedia/library).

**MobileNav.tsx:** Same addition. With 5 items, the bottom nav still fits on iPhone SE (393px / 5 = 78.6px per item, well above 44px touch target minimum).

**App.tsx:** Add route:
```typescript
<Route path="patterns" element={<PatternLibraryPage />} />
```

**Keyboard shortcuts:** Update to support `1`–`5`. `5` → `/patterns`. System moves to position 5 at `5` key.

Wait — with 5 pages, the keyboard mapping is:
- `1` → Dashboard
- `2` → Trades
- `3` → Performance
- `4` → Pattern Library
- `5` → System

This reorders from the current `4` → System. Since we're adding Pattern Library at position 4 and System moves to 5, the keyboard shortcut for System changes from `4` to `5`.

### 4.16 Dependencies

**New npm packages:**
- `react-markdown` — markdown rendering (lightweight, ~12KB gzipped)
- `remark-gfm` — GFM table/strikethrough support for react-markdown

Install: `npm install react-markdown remark-gfm`

### 4.17 MarkdownRenderer Component

**File:** `argus/ui/src/components/MarkdownRenderer.tsx`

Thin wrapper around `react-markdown` with:
- `remark-gfm` plugin enabled
- Custom component overrides for dark theme styling:
  - `h1`, `h2`, `h3`: appropriate text sizes + argus-text color
  - `table`: argus-border, alternating row shading
  - `code`: argus-surface-2 background
  - `a`: argus-accent color
  - `p`: argus-text color, proper line spacing

---

## 5. Tests

### 5.1 Pytest (Backend)

| Test File | Tests | What |
|-----------|-------|------|
| `tests/api/test_strategies_extended.py` | 4 | Extended strategies endpoint: returns new fields, performance_summary present, backtest_summary present, family/time_window fields |
| `tests/api/test_strategy_spec.py` | 3 | Spec endpoint: returns markdown for valid strategy, 404 for invalid, content matches file |
| `tests/api/test_market_bars.py` | 3 | Bars endpoint: returns valid OHLCV, respects limit param, dev mode synthetic data |
| `tests/api/test_performance_strategy_filter.py` | 3 | Performance with strategy_id filter: filters correctly, daily P&L filtered, by_strategy has single entry |
| `tests/core/test_config_new_fields.py` | 4 | Config: pipeline_stage, family, description_short, backtest_summary parse from YAML |
| `tests/api/test_dev_state_patterns.py` | 3 | Dev mode: mock strategies have all new fields, mock performance summaries populated |
| **Subtotal** | **~20** | |

### 5.2 Vitest (Frontend)

| Test File | Tests | What |
|-----------|-------|------|
| `IncubatorPipeline.test.tsx` | 3 | Renders all 10 stages, highlights stages with strategies, click toggles filter |
| `PatternCard.test.tsx` | 3 | Renders strategy info, shows correct badge colors, click calls onSelect |
| `OverviewTab.test.tsx` | 2 | Renders parameter table, renders markdown content |
| `BacktestTab.test.tsx` | 2 | Renders summary metrics, shows correct status badge |
| `SlideInPanel.test.tsx` | 2 | Opens/closes correctly, calls onClose on escape |
| `SymbolDetailPanel.test.tsx` | 3 | Opens with symbol, shows trading history section, shows chart section |
| **Subtotal** | **~15** | |

---

## 6. Definition of Done

- [ ] All 4 strategy YAML configs updated with new fields
- [ ] Pydantic config models updated (StrategyConfig base + BacktestSummaryConfig)
- [ ] `GET /strategies` returns enriched data with performance_summary and backtest_summary
- [ ] `GET /strategies/{id}/spec` serves markdown spec sheets
- [ ] `GET /performance/{period}?strategy_id=` filters correctly
- [ ] `GET /market/{symbol}/bars` returns OHLCV (synthetic in dev mode)
- [ ] Dev mode mock data includes all Pattern Library fields
- [ ] Pattern Library page renders at all 3 breakpoints (phone/tablet/desktop)
- [ ] Incubator Pipeline shows 10 stages with counts, click-to-filter works
- [ ] Strategy card grid with filters (stage, family, time) and sort
- [ ] All 5 tabs render: Overview (params + markdown), Performance (charts + metrics), Backtest (placeholder), Trades (reuses TradeTable), Intelligence (placeholder)
- [ ] SlideInPanel extracted, TradeDetailPanel refactored to use it
- [ ] SymbolDetailPanel opens on symbol click (candlestick chart + trading history + position detail)
- [ ] Nav updated: 5th page in sidebar + bottom nav, keyboard shortcut `5`
- [ ] react-markdown + remark-gfm installed, MarkdownRenderer component themed
- [ ] ~20 new pytest tests pass (1542+ total)
- [ ] ~15 new Vitest tests pass (63+ total)
- [ ] Zero regressions — existing 1522 pytest + 48 Vitest all pass
- [ ] `ruff check` passes with zero errors
- [ ] Dev mode (`python -m argus.api --dev`) shows Pattern Library with all features working
