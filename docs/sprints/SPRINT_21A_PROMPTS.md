# Sprint 21a — Session Plan & Claude Code Prompts

## Session Breakdown

| Session | Focus | New pytest | New Vitest | Cumulative |
|---------|-------|-----------|-----------|------------|
| 1 | Config + API backend | ~13 | 0 | 1535 + 48 |
| 2 | Dev mode + page scaffold + nav | ~7 | 0 | 1542 + 48 |
| 3 | Left panel: cards, filters, pipeline | 0 | ~6 | 1542 + 54 |
| 4 | Overview + Backtest tabs | 0 | ~4 | 1542 + 58 |
| 5 | Performance tab | 0 | 0 | 1542 + 58 |
| 6 | Trades + Intelligence tabs + tab wiring | 0 | 0 | 1542 + 58 |
| 7 | SlideInPanel extraction + SymbolDetail | 0 | ~5 | 1542 + 63 |
| 8 | Symbol chart + click-anywhere wiring | 0 | 0 | 1542 + 63 |
| 9 | Polish, responsive QA, remaining tests | 0 | ~2 | 1542 + 65 |
| 10 | Buffer: edge cases, bug fixes, code review prep | 0 | 0 | 1542 + 65 |

**Code review checkpoints:**
- After Session 2 (API + scaffold complete — verify backend is solid before building UI on top)
- After Session 8 (all features implemented — comprehensive review before polish)

---

## Session 1 — Config + API Backend

### Prompt (copy-paste into Claude Code):

```
# Sprint 21a Session 1 — Config YAML + API Backend

Read CLAUDE.md, then docs/10_PHASE3_SPRINT_PLAN.md for sprint context.

Sprint 21a adds the Pattern Library page (strategy encyclopedia). This session builds the backend: config changes + API endpoints.

## Task 1: Config YAML Updates

Add these new fields to ALL 4 strategy YAML configs in config/strategies/:

**orb_breakout.yaml** — add after `asset_class: "us_stocks"`:
```yaml
pipeline_stage: "paper_trading"
family: "orb_family"
description_short: "Exploits gapping stocks breaking out of the first 5 minutes' high with volume confirmation."
time_window_display: "9:35–11:30 AM"
```
And add at the bottom of the file:
```yaml
backtest_summary:
  status: "walk_forward_complete"
  wfe_pnl: 0.56
  oos_sharpe: 0.34
  total_trades: 137
  data_months: 35
  last_run: "2026-02-17"
```

**orb_scalp.yaml** — same pattern:
```yaml
pipeline_stage: "paper_trading"
family: "orb_family"
description_short: "Quick 0.3R scalp on the same opening range breakout pattern, exiting within 120 seconds."
time_window_display: "9:45–11:30 AM"
```
Backtest summary:
```yaml
backtest_summary:
  status: "not_validated"
  wfe_pnl: null
  oos_sharpe: null
  total_trades: 20880
  data_months: 35
  last_run: "2026-02-25"
```

**vwap_reclaim.yaml**:
```yaml
pipeline_stage: "paper_trading"
family: "mean_reversion"
description_short: "Enters long when a gapping stock pulls back below VWAP, then reclaims above on volume."
time_window_display: "10:00 AM–12:00 PM"
```
Backtest summary:
```yaml
backtest_summary:
  status: "walk_forward_complete"
  wfe_pnl: null
  oos_sharpe: 1.49
  total_trades: 59556
  data_months: 35
  last_run: "2026-02-26"
```

**afternoon_momentum.yaml**:
```yaml
pipeline_stage: "paper_trading"
family: "momentum"
description_short: "Catches afternoon consolidation breakouts in gapping stocks between 2:00–3:30 PM."
time_window_display: "2:00–3:30 PM"
```
Backtest summary:
```yaml
backtest_summary:
  status: "sweep_complete"
  wfe_pnl: null
  oos_sharpe: null
  total_trades: null
  data_months: 35
  last_run: "2026-02-26"
```

## Task 2: Pydantic Config Model Updates

In `argus/core/config.py`:

1. Add a new `BacktestSummaryConfig` model:
```python
class BacktestSummaryConfig(BaseModel):
    status: str = "not_validated"
    wfe_pnl: float | None = None
    oos_sharpe: float | None = None
    total_trades: int | None = None
    data_months: int | None = None
    last_run: str | None = None
```

2. Add new fields to `StrategyConfig` base class:
```python
pipeline_stage: str = "concept"
family: str = "uncategorized"
description_short: str = ""
time_window_display: str = ""
```

3. Add `backtest_summary: BacktestSummaryConfig = BacktestSummaryConfig()` to each strategy-specific config class (OrbBreakoutConfig, OrbScalpConfig, VwapReclaimConfig, AfternoonMomentumConfig).

## Task 3: Extend GET /api/v1/strategies

In `argus/api/routes/strategies.py`:

1. Add response models:
```python
class PerformanceSummary(BaseModel):
    trade_count: int
    win_rate: float
    net_pnl: float
    avg_r: float
    profit_factor: float

class BacktestSummary(BaseModel):
    status: str
    wfe_pnl: float | None = None
    oos_sharpe: float | None = None
    total_trades: int | None = None
    data_months: int | None = None
    last_run: str | None = None
```

2. Add to `StrategyInfo`:
```python
time_window: str = ""
family: str = "uncategorized"
description_short: str = ""
performance_summary: PerformanceSummary | None = None
backtest_summary: BacktestSummary | None = None
```

3. In `list_strategies()`, populate the new fields:
- `time_window` from `getattr(strategy.config, 'time_window_display', '')`
- `family` from `getattr(strategy.config, 'family', 'uncategorized')`
- `description_short` from `getattr(strategy.config, 'description_short', '')`
- `backtest_summary` from config if it has a backtest_summary attribute
- `performance_summary` requires querying TradeLogger:
  ```python
  trades = await state.trade_logger.get_trades_by_strategy(strategy_id)
  if trades:
      from argus.analytics.performance import compute_metrics
      metrics = compute_metrics(trades)
      performance_summary = PerformanceSummary(
          trade_count=metrics.total_trades,
          win_rate=metrics.win_rate,
          net_pnl=metrics.net_pnl,
          avg_r=metrics.avg_r_multiple,
          profit_factor=metrics.profit_factor if metrics.profit_factor != float('inf') else 0.0,
      )
  ```

Note: `get_trades_by_strategy` returns trade dicts. The `compute_metrics` function already handles dict input.

## Task 4: New GET /api/v1/strategies/{strategy_id}/spec

In `argus/api/routes/strategies.py`, add:

```python
class StrategySpecResponse(BaseModel):
    strategy_id: str
    content: str
    format: str = "markdown"

STRATEGY_SPEC_MAP = {
    "strat_orb_breakout": "STRATEGY_ORB_BREAKOUT.md",
    "strat_orb_scalp": "STRATEGY_ORB_SCALP.md",
    "strat_vwap_reclaim": "STRATEGY_VWAP_RECLAIM.md",
    "strat_afternoon_momentum": "STRATEGY_AFTERNOON_MOMENTUM.md",
}

@router.get("/{strategy_id}/spec", response_model=StrategySpecResponse)
async def get_strategy_spec(
    strategy_id: str,
    _auth: dict = Depends(require_auth),
    state: AppState = Depends(get_app_state),
) -> StrategySpecResponse:
    filename = STRATEGY_SPEC_MAP.get(strategy_id)
    if not filename:
        raise HTTPException(status_code=404, detail=f"No spec sheet for strategy {strategy_id}")
    
    # Navigate from argus/api/routes/ up to project root, then into docs/strategies/
    spec_dir = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "strategies"
    spec_path = spec_dir / filename
    
    if not spec_path.exists():
        raise HTTPException(status_code=404, detail=f"Spec sheet file not found: {filename}")
    
    content = spec_path.read_text(encoding="utf-8")
    return StrategySpecResponse(strategy_id=strategy_id, content=content)
```

Add necessary imports: `from pathlib import Path`, `from fastapi import HTTPException`.

## Task 5: Extend GET /api/v1/performance/{period} with strategy_id filter

In `argus/api/routes/performance.py`:

Add `strategy_id: str | None = None` as a Query parameter to `get_performance()`. When provided, pass it to `state.trade_logger.query_trades()` and `state.trade_logger.get_daily_pnl()`.

The existing TradeLogger methods already support `strategy_id` as a filter parameter — check the method signatures. Pass it through.

## Task 6: New GET /api/v1/market/{symbol}/bars

Create new file `argus/api/routes/market.py`:

```python
"""Market data routes for the Command Center API."""

from __future__ import annotations

import hashlib
import math
import random
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()
ET_TZ = ZoneInfo("America/New_York")


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


def _generate_synthetic_bars(symbol: str, limit: int) -> list[BarData]:
    """Generate deterministic synthetic OHLCV data for dev mode."""
    # Seed from symbol name for deterministic output
    seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    
    # Base price derived from symbol hash (range $10-$500)
    base_price = 10 + (seed % 490)
    volatility = base_price * 0.002  # 0.2% per bar
    
    # Start from today's market open
    now_et = datetime.now(ET_TZ)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    
    bars = []
    price = float(base_price)
    
    for i in range(limit):
        timestamp = market_open + timedelta(minutes=i)
        
        # Random walk with slight mean reversion
        change = rng.gauss(0, volatility)
        mean_reversion = (base_price - price) * 0.01
        price += change + mean_reversion
        price = max(price, 1.0)  # Floor at $1
        
        open_price = price
        close_price = price + rng.gauss(0, volatility * 0.5)
        high_price = max(open_price, close_price) + abs(rng.gauss(0, volatility * 0.3))
        low_price = min(open_price, close_price) - abs(rng.gauss(0, volatility * 0.3))
        
        # Volume: higher at open/close, lower midday
        minutes_from_open = i
        volume_base = 50000 + seed % 200000
        if minutes_from_open < 30:  # First 30 min
            volume_mult = 2.0 + rng.random()
        elif minutes_from_open > 350:  # Last 40 min
            volume_mult = 1.5 + rng.random()
        else:
            volume_mult = 0.5 + rng.random()
        volume = int(volume_base * volume_mult)
        
        bars.append(BarData(
            timestamp=timestamp.isoformat(),
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(close_price, 2),
            volume=volume,
        ))
        
        price = close_price
    
    return bars


@router.get("/{symbol}/bars", response_model=BarsResponse)
async def get_symbol_bars(
    symbol: str,
    timeframe: str = "1m",
    limit: int = 390,
    _auth: dict = Depends(require_auth),
    state: AppState = Depends(get_app_state),
) -> BarsResponse:
    """Get intraday bars for a symbol.
    
    In dev mode, returns synthetic data. In production, queries DataService.
    """
    # For now, always use synthetic data (production DataService integration
    # will be added when Databento is active)
    bars = _generate_synthetic_bars(symbol.upper(), min(limit, 390))
    
    return BarsResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        bars=bars,
        count=len(bars),
    )
```

Register in `argus/api/server.py`:
```python
from argus.api.routes.market import router as market_router
# Add to router includes:
app.include_router(market_router, prefix="/api/v1/market", tags=["market"])
```

## Task 7: Tests

Write pytest tests for all new/modified endpoints. Follow existing test patterns in `tests/api/`.

**tests/api/test_strategies_extended.py** (~4 tests):
- Extended strategies endpoint returns `time_window`, `family`, `description_short`
- `performance_summary` is present (or null if no trades)
- `backtest_summary` is present with correct status
- Config model parses new YAML fields correctly

**tests/api/test_strategy_spec.py** (~3 tests):
- Returns markdown for valid strategy_id
- Returns 404 for unknown strategy_id
- Content contains expected heading from spec file

**tests/api/test_market_bars.py** (~3 tests):
- Returns valid OHLCV data
- Respects limit parameter
- Same symbol always returns same data (deterministic)

**tests/api/test_performance_filter.py** (~3 tests):
- With strategy_id filter, only returns trades for that strategy
- Daily P&L is filtered to the strategy
- by_strategy dict contains only the filtered strategy

Test baseline: 1522 pytest. Target after this session: ~1535 pytest.

## Important Rules
- Run `ruff check argus/` before committing — zero errors.
- Run full pytest suite — zero regressions on existing 1522 tests.
- Don't modify any existing test files unless the API contract change requires it (e.g., if StrategyInfo response shape changes, update test assertions).
```

---

## Session 2 — Dev Mode + Page Scaffold + Nav

### Prompt:

```
# Sprint 21a Session 2 — Dev Mode Extensions + Page Scaffold + Nav

Read CLAUDE.md for current state. Session 1 added config YAML fields, API extensions (enriched /strategies, /strategies/{id}/spec, /market/{symbol}/bars, performance strategy_id filter), and ~13 new tests. Verify all tests pass first.

## Task 1: Dev Mode Mock Data Extensions

In `argus/api/dev_state.py`, update the MockStrategy instances and create_dev_state() to include:

1. Add to MockStrategy dataclass:
```python
family: str = "uncategorized"
description_short: str = ""
time_window_display: str = ""
```

2. Update each mock strategy creation in create_dev_state():

ORB Breakout mock:
- family="orb_family"
- description_short="Exploits gapping stocks breaking out of the first 5 minutes' high with volume confirmation."
- time_window_display="9:35–11:30 AM"

ORB Scalp mock:
- family="orb_family"
- description_short="Quick 0.3R scalp on the same opening range breakout pattern, exiting within 120 seconds."
- time_window_display="9:45–11:30 AM"

VWAP Reclaim mock:
- family="mean_reversion"
- description_short="Enters long when a gapping stock pulls back below VWAP, then reclaims above on volume."
- time_window_display="10:00 AM–12:00 PM"

Afternoon Momentum mock:
- family="momentum"
- description_short="Catches afternoon consolidation breakouts in gapping stocks between 2:00–3:30 PM."
- time_window_display="2:00–3:30 PM"

3. Add backtest_summary to each mock strategy's config. The config objects are Pydantic models — you'll need to add BacktestSummaryConfig instances. Use realistic values matching the YAML files from Session 1.

4. Verify the mock strategies expose the new fields correctly through the enriched /strategies endpoint. The route uses `getattr(strategy.config, ...)` and `getattr(strategy, ...)` — make sure MockStrategy attributes match what the route reads.

5. If the strategies route uses `state.trade_logger.get_trades_by_strategy()` for performance_summary, ensure the dev mode TradeLogger has trades tagged with the correct strategy_ids. The existing dev mode already creates trades with strategy_id tags — verify they match the mock strategy IDs.

## Task 2: Frontend TypeScript Types

In `argus/ui/src/api/types.ts`, update `StrategyInfo` interface:

```typescript
export interface PerformanceSummary {
  trade_count: number;
  win_rate: number;
  net_pnl: number;
  avg_r: number;
  profit_factor: number;
}

export interface BacktestSummary {
  status: string;
  wfe_pnl: number | null;
  oos_sharpe: number | null;
  total_trades: number | null;
  data_months: number | null;
  last_run: string | null;
}

export interface StrategyInfo {
  // ... keep all existing fields ...
  time_window: string;          // NEW
  family: string;               // NEW
  description_short: string;    // NEW
  performance_summary: PerformanceSummary | null;  // NEW
  backtest_summary: BacktestSummary | null;        // NEW
}

// New types for Pattern Library
export interface StrategySpecResponse {
  strategy_id: string;
  content: string;
  format: string;
}

export interface BarData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BarsResponse {
  symbol: string;
  timeframe: string;
  bars: BarData[];
  count: number;
}
```

## Task 3: API Client Extensions

In `argus/ui/src/api/client.ts`, add functions:

```typescript
export async function fetchStrategySpec(strategyId: string): Promise<StrategySpecResponse> { ... }
export async function fetchSymbolBars(symbol: string, limit?: number): Promise<BarsResponse> { ... }
```

Follow the existing `fetchXxx` pattern in that file for auth headers and error handling.

## Task 4: New Hooks

Create `argus/ui/src/hooks/useStrategySpec.ts`:
- TanStack Query hook for fetching strategy spec markdown
- Key: ['strategies', strategyId, 'spec']
- Stale time: 5 minutes
- Only enabled when strategyId is provided

Create `argus/ui/src/hooks/useSymbolBars.ts`:
- TanStack Query hook for fetching intraday bars
- Key: ['market', symbol, 'bars']
- Stale time: 30 seconds
- Only enabled when symbol is provided

Create `argus/ui/src/hooks/useSymbolTrades.ts`:
- Hook that uses the existing trades fetching pattern but filters by symbol
- Key: ['trades', { symbol }]
- Uses the existing /trades endpoint with a symbol query param

Update `argus/ui/src/hooks/index.ts` to export the new hooks.

## Task 5: Zustand Stores

Create `argus/ui/src/stores/patternLibraryUI.ts`:
```typescript
import { create } from 'zustand';

interface PatternLibraryUIState {
  selectedStrategyId: string | null;
  activeTab: string;
  filters: {
    stage: string | null;
    family: string | null;
    timeWindow: string | null;
  };
  sortBy: string;
  setSelectedStrategy: (id: string | null) => void;
  setActiveTab: (tab: string) => void;
  setFilter: (key: 'stage' | 'family' | 'timeWindow', value: string | null) => void;
  setSortBy: (sort: string) => void;
}

export const usePatternLibraryUI = create<PatternLibraryUIState>((set) => ({
  selectedStrategyId: null,
  activeTab: 'overview',
  filters: { stage: null, family: null, timeWindow: null },
  sortBy: 'name',
  setSelectedStrategy: (id) => set({ selectedStrategyId: id }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setFilter: (key, value) => set((state) => ({
    filters: { ...state.filters, [key]: value },
  })),
  setSortBy: (sort) => set({ sortBy: sort }),
}));
```

Create `argus/ui/src/stores/symbolDetailUI.ts`:
```typescript
import { create } from 'zustand';

interface SymbolDetailUIState {
  selectedSymbol: string | null;
  isOpen: boolean;
  open: (symbol: string) => void;
  close: () => void;
}

export const useSymbolDetailUI = create<SymbolDetailUIState>((set) => ({
  selectedSymbol: null,
  isOpen: false,
  open: (symbol) => set({ selectedSymbol: symbol, isOpen: true }),
  close: () => set({ isOpen: false, selectedSymbol: null }),
}));
```

## Task 6: Page Scaffold + Routing

Create `argus/ui/src/pages/PatternLibraryPage.tsx` — minimal scaffold for now:
```tsx
import { AnimatedPage } from '../components/AnimatedPage';
import { BookOpen } from 'lucide-react';

export function PatternLibraryPage() {
  return (
    <AnimatedPage>
      <div className="flex items-center gap-3 mb-6">
        <BookOpen className="w-6 h-6 text-argus-accent" />
        <h1 className="text-xl font-semibold text-argus-text">Pattern Library</h1>
      </div>
      <div className="text-argus-text-dim">
        Pattern Library content coming in Sessions 3–8.
      </div>
    </AnimatedPage>
  );
}
```

Update `argus/ui/src/App.tsx`:
- Import PatternLibraryPage
- Add route: `<Route path="patterns" element={<PatternLibraryPage />} />`

## Task 7: Nav Updates

**Sidebar.tsx:** Add Pattern Library at position 4, System moves to position 5.
```typescript
import { LayoutDashboard, ScrollText, TrendingUp, BookOpen, Activity, LogOut } from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/trades', icon: ScrollText, label: 'Trades' },
  { to: '/performance', icon: TrendingUp, label: 'Performance' },
  { to: '/patterns', icon: BookOpen, label: 'Pattern Library' },
  { to: '/system', icon: Activity, label: 'System' },
] as const;
```

Keyboard shortcuts already work based on NAV_ITEMS index, so `4` → Pattern Library, `5` → System automatically.

**MobileNav.tsx:** Same change — add Pattern Library at position 4, System at 5. With 5 items and a phone width of 393px, each item gets ~78px — well above the 44px touch target minimum.

## Task 8: Dev Mode Verification

Start dev mode: `cd argus/ui && npm run dev` (in one terminal) and `python -m argus.api --dev` (in another).

Verify:
1. `/api/v1/strategies` returns all 4 strategies with new fields (time_window, family, description_short, performance_summary, backtest_summary)
2. `/api/v1/strategies/strat_orb_breakout/spec` returns markdown content
3. `/api/v1/market/AAPL/bars` returns synthetic OHLCV data
4. Pattern Library page renders at `/patterns` route
5. Sidebar shows 5 nav items, bottom nav shows 5 items
6. Keyboard shortcut `4` navigates to Pattern Library, `5` to System

## Task 9: Tests

Write tests for dev mode extensions:

**tests/api/test_dev_state_patterns.py** (~4 tests):
- Dev state mock strategies have family, description_short, time_window_display
- Dev state performance summaries are populated from trade data
- Backtest summaries are present on mock strategy configs
- All 4 mock strategies have distinct family values

Run full test suite — all existing tests must still pass.

Test target after session: ~1542 pytest + 48 Vitest.
```

---

## Session 3 — Left Panel: Cards, Filters, Pipeline

### Prompt:

```
# Sprint 21a Session 3 — Left Panel: Card Grid, Filters, Pipeline

Read CLAUDE.md for current state. Sessions 1–2 completed: config YAML, API extensions, dev mode, page scaffold, nav (5 pages), stores, hooks. All tests pass. This session builds the Pattern Library left panel.

## Architecture Reminder

The Pattern Library page has a master-detail layout:
- Desktop (≥1024px): Left panel 35%, right panel 65%, side by side
- Tablet (640–1023px): Full-width card list. Selecting a card transitions to full-width detail view.
- Mobile (<640px): Same as tablet — full-width stacked cards, tap for full-screen detail.

This session builds the left panel: IncubatorPipeline, PatternCardGrid, PatternCard, and PatternFilters. The right panel (PatternDetail + tabs) is Sessions 4–6.

## File Structure

Create directory: `argus/ui/src/features/patterns/`

Create these files:

### 1. IncubatorPipeline.tsx

Horizontal pipeline visualization showing 10 Incubator stages with strategy counts.

Props:
```typescript
interface IncubatorPipelineProps {
  strategies: StrategyInfo[];
  activeStageFilter: string | null;
  onStageClick: (stage: string | null) => void;
}
```

**10 stages with display labels:**
```typescript
const PIPELINE_STAGES = [
  { key: 'concept', label: 'Concept' },
  { key: 'exploration', label: 'Explore' },
  { key: 'validation', label: 'Validate' },
  { key: 'ecosystem_replay', label: 'Eco Replay' },
  { key: 'paper_trading', label: 'Paper' },
  { key: 'live_minimum', label: 'Live Min' },
  { key: 'live_full', label: 'Live Full' },
  { key: 'active_monitoring', label: 'Monitor' },
  { key: 'suspended', label: 'Suspended' },
  { key: 'retired', label: 'Retired' },
] as const;
```

**Desktop/Tablet (≥640px):** Flex row of stage nodes connected by chevron arrows (use `ChevronRight` from lucide or just a `›` character). Each node is a rounded badge showing the label + count. Stages with count > 0 have bright text and a subtle background. Stages with count = 0 are dimmed (argus-text-dim, no background). Clicking a stage toggles the filter — clicking the same stage clears it. The active filter stage gets a ring/border highlight (argus-accent border).

**Mobile (<640px):** Horizontal scrollable row (`overflow-x-auto`) of compact pills. Each pill shows `Label (N)`. Same click behavior.

Wrapped in a Card component at the top of the page. Title: "Strategy Pipeline".

### 2. PatternCard.tsx

Individual strategy card in the grid.

Props:
```typescript
interface PatternCardProps {
  strategy: StrategyInfo;
  isSelected: boolean;
  onSelect: (id: string) => void;
}
```

**Content layout:**
- Top row: Strategy name (bold, argus-text) + pipeline stage badge (use existing Badge component with appropriate variant)
- Second row: Family badge (smaller, dimmer) + time window text (argus-text-dim)
- Bottom row: Mini stats — trade count, win rate (%), net P&L ($). Use performance_summary if available, otherwise show "—" for each.

**States:**
- Default: Card component with standard styling
- Selected: argus-accent border/ring
- Hover: subtle lift (existing card hover pattern from Sprint 16)

**Click:** Calls `onSelect(strategy.strategy_id)`.

**Pipeline badge colors** (reuse getPipelineBadgeVariant pattern from StrategyCards.tsx in system/):
- paper_trading → warning (amber)
- live_minimum, live_full, active_monitoring → success (green)
- concept, exploration, validation, ecosystem_replay → info (blue)
- suspended → danger variant or custom red
- retired → neutral (gray)

**Family display names:**
```typescript
const FAMILY_LABELS: Record<string, string> = {
  'orb_family': 'ORB Family',
  'momentum': 'Momentum',
  'mean_reversion': 'Mean-Reversion',
};
```

### 3. PatternFilters.tsx

Filter and sort controls above the card grid.

Props:
```typescript
interface PatternFiltersProps {
  filters: { stage: string | null; family: string | null; timeWindow: string | null };
  sortBy: string;
  onFilterChange: (key: 'stage' | 'family' | 'timeWindow', value: string | null) => void;
  onSortChange: (sort: string) => void;
}
```

**Filters:** Use SegmentedTab components (existing) or compact dropdown selects.
- Family: All | ORB Family | Momentum | Mean-Reversion
- Time: All | Morning (before 12pm) | Afternoon (after 12pm)

Note: The stage filter is controlled by IncubatorPipeline click, not a separate control here. So PatternFilters only shows family + time + sort.

**Sort:** Dropdown with options: Name (A→Z), P&L (high→low), Win Rate (high→low), Trades (high→low).

Keep it compact — one row if possible.

### 4. PatternCardGrid.tsx

Container that applies filters/sort and renders the card grid.

Props:
```typescript
interface PatternCardGridProps {
  strategies: StrategyInfo[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}
```

Reads filters and sortBy from `usePatternLibraryUI` store. Applies filtering logic:
- Stage filter: match `strategy.pipeline_stage`
- Family filter: match `strategy.family`
- Time window filter: classify by `time_window` text (if contains "AM" and no "PM" → morning, etc.)

Applies sorting logic on the filtered list. Renders PatternFilters + grid of PatternCards.

If no strategies match filters, show EmptyState: "No strategies match the current filters."

### 5. Update PatternLibraryPage.tsx

Replace the scaffold with the real master-detail layout:

```tsx
export function PatternLibraryPage() {
  const { data: strategiesData, isLoading } = useStrategies();
  const { selectedStrategyId, setSelectedStrategy, filters } = usePatternLibraryUI();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  
  // On tablet/mobile, selecting a strategy shows detail view (hides grid)
  const showDetail = selectedStrategyId !== null;
  const showGrid = isDesktop || !showDetail;
  
  return (
    <AnimatedPage>
      <IncubatorPipeline ... />
      
      <div className={isDesktop ? 'flex gap-6 mt-6' : 'mt-6'}>
        {showGrid && (
          <div className={isDesktop ? 'w-[35%] flex-shrink-0' : 'w-full'}>
            <PatternCardGrid
              strategies={strategiesData?.strategies ?? []}
              selectedId={selectedStrategyId}
              onSelect={setSelectedStrategy}
            />
          </div>
        )}
        
        {showDetail && (
          <div className={isDesktop ? 'flex-1 min-w-0' : 'w-full'}>
            <PatternDetail
              strategyId={selectedStrategyId!}
              onClose={() => setSelectedStrategy(null)}
            />
          </div>
        )}
      </div>
    </AnimatedPage>
  );
}
```

For now, PatternDetail is a placeholder div — it gets built in Sessions 4–6.

### 6. Create index.ts barrel export

`argus/ui/src/features/patterns/index.ts` — export all public components.

### 7. Vitest Tests

Create test files in the features/patterns/ directory:

**IncubatorPipeline.test.tsx** (~3 tests):
- Renders all 10 stage labels
- Shows correct count for stages with strategies
- Click toggles filter (calls onStageClick)

**PatternCard.test.tsx** (~3 tests):
- Renders strategy name and badges
- Shows performance stats when available
- Click calls onSelect with correct ID

Follow existing Vitest patterns (see PositionTimeline.test.tsx, StrategyCards.test.tsx, WatchlistItem.test.tsx).

Test target after session: 1542 pytest + ~54 Vitest.
```

---

## Session 4 — Overview + Backtest Tabs

### Prompt:

```
# Sprint 21a Session 4 — Overview Tab + Backtest Tab

Read CLAUDE.md. Sessions 1–3 complete: API, dev mode, nav, left panel (pipeline + cards + filters). This session builds two of the five tabs in the right panel.

## Task 1: Install Dependencies

```bash
cd argus/ui && npm install react-markdown remark-gfm
```

## Task 2: MarkdownRenderer Component

Create `argus/ui/src/components/MarkdownRenderer.tsx`:

A styled wrapper around react-markdown with remark-gfm for table support. Must match the dark theme.

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <h1 className="text-xl font-bold text-argus-text mt-6 mb-3">{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-semibold text-argus-text mt-5 mb-2 border-b border-argus-border pb-1">{children}</h2>,
        h3: ({ children }) => <h3 className="text-base font-semibold text-argus-text mt-4 mb-1">{children}</h3>,
        p: ({ children }) => <p className="text-sm text-argus-text leading-relaxed mb-3">{children}</p>,
        ul: ({ children }) => <ul className="text-sm text-argus-text list-disc list-inside mb-3 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="text-sm text-argus-text list-decimal list-inside mb-3 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="text-sm text-argus-text">{children}</li>,
        table: ({ children }) => (
          <div className="overflow-x-auto mb-4">
            <table className="w-full text-sm border-collapse">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="border-b border-argus-border">{children}</thead>,
        th: ({ children }) => <th className="text-left text-argus-text-dim font-medium py-2 px-3">{children}</th>,
        td: ({ children }) => <td className="text-argus-text py-2 px-3 border-b border-argus-border/50">{children}</td>,
        code: ({ children, className }) => {
          const isBlock = className?.includes('language-');
          if (isBlock) {
            return <code className="block bg-argus-surface-2 rounded-md p-3 text-xs font-mono overflow-x-auto mb-3">{children}</code>;
          }
          return <code className="bg-argus-surface-2 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>;
        },
        pre: ({ children }) => <pre className="mb-3">{children}</pre>,
        blockquote: ({ children }) => <blockquote className="border-l-2 border-argus-accent/50 pl-4 italic text-argus-text-dim mb-3">{children}</blockquote>,
        a: ({ href, children }) => <a href={href} className="text-argus-accent hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
        hr: () => <hr className="border-argus-border my-4" />,
        strong: ({ children }) => <strong className="font-semibold text-argus-text">{children}</strong>,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

## Task 3: OverviewTab

Create `argus/ui/src/features/patterns/tabs/OverviewTab.tsx`:

Props: `strategyId: string`, receives strategy data from parent (PatternDetail).

**Two sections:**

**Section 1: Parameter Table**
- Card with header "Current Parameters"
- Subtitle: "View-only. Parameter editing available with AI Layer (Sprint 22)."
- Two-column table: Parameter Name | Value
- Read from `strategy.config_summary` field (already available in StrategyInfo)
- Format parameter names nicely: `orb_window_minutes` → "ORB Window (min)", `target_1_r` → "Target 1 R", etc.
- Format values appropriately: numbers with sensible precision, booleans as Yes/No

**Section 2: Strategy Spec Sheet**
- Card with header "Strategy Documentation"
- Uses useStrategySpec hook to fetch markdown
- Loading state: Skeleton lines
- Error state: "Unable to load strategy documentation"
- Success state: MarkdownRenderer component renders the content

## Task 4: BacktestTab

Create `argus/ui/src/features/patterns/tabs/BacktestTab.tsx`:

Props: `strategy: StrategyInfo` (full strategy object, has backtest_summary).

**Content:**

**Status Badge:**
Map backtest_summary.status to visual:
- "walk_forward_complete" → Badge variant="success", text="Walk-Forward Complete"
- "sweep_complete" → Badge variant="warning", text="Parameter Sweep Complete"
- "not_validated" → Badge variant="neutral", text="Not Yet Validated"

**Summary Metrics (if available):**
Card with a grid of metrics from backtest_summary:
- WFE (P&L): `backtest_summary.wfe_pnl` or "—"
- OOS Sharpe: `backtest_summary.oos_sharpe` or "—"
- Total Trades: `backtest_summary.total_trades` or "—"
- Data Coverage: `backtest_summary.data_months` months or "—"
- Last Run: `backtest_summary.last_run` or "—"

Use MetricCard components or a simple grid similar to the Performance page metrics grid.

**Note (always shown):**
"⚠️ All pre-Databento backtests require re-validation with exchange-direct data (DEC-132)."

**Future placeholder:**
"Interactive backtest explorer, VectorBT sweep heatmaps, and walk-forward visualizations coming in Sprint 21d."

## Task 5: Vitest Tests

**OverviewTab.test.tsx** (~2 tests):
- Renders parameter table with config data
- Shows loading state while fetching spec

**BacktestTab.test.tsx** (~2 tests):
- Renders correct status badge for each status type
- Shows summary metrics when available

Test target after session: 1542 pytest + ~58 Vitest.
```

---

## Session 5 — Performance Tab

### Prompt:

```
# Sprint 21a Session 5 — Performance Tab

Read CLAUDE.md. Sessions 1–4 complete: API, dev mode, nav, left panel, Overview tab, Backtest tab. This session builds the Performance tab in the Pattern Detail right panel.

## Task 1: PerformanceTab Component

Create `argus/ui/src/features/patterns/tabs/PerformanceTab.tsx`:

Props: `strategyId: string`

This tab shows strategy-specific performance analytics, reusing existing components from the Performance page where possible.

**Structure:**

1. **Period Selector** — Reuse the PeriodSelector component from `features/performance/PeriodSelector.tsx`. Same "Today / Week / Month / All" tabs.

2. **Metrics Grid** — 6 key metrics using MetricCard components:
   - Total Trades
   - Win Rate (%)
   - Profit Factor
   - Sharpe Ratio
   - Avg R-Multiple
   - Max Drawdown (%)
   
   Data comes from the performance endpoint. You need to call `GET /api/v1/performance/{period}?strategy_id={strategyId}` — use the existing `usePerformance` hook or create a variant that accepts a strategy_id parameter.

   **Check the existing usePerformance hook** (`argus/ui/src/hooks/usePerformance.ts`). If it doesn't support a strategy_id filter, extend it to accept an optional `strategyId` parameter and pass it as a query param to the API. The backend was updated in Session 1 to accept `?strategy_id=`.

3. **Equity Curve** — LWChart (Lightweight Charts) line chart showing cumulative P&L over time. Reuse the EquityCurve component pattern from `features/performance/EquityCurve.tsx`. The data source is the daily_pnl array from the performance response — compute cumulative sum for the equity curve.

4. **Daily P&L Histogram** — Reuse DailyPnlChart component from `features/performance/DailyPnlChart.tsx`. Same visualization, different data (filtered to this strategy).

**Important:** The existing Performance page components (MetricsGrid, EquityCurve, DailyPnlChart) may be tightly coupled to the PerformancePage. If they take their data as props, you can reuse them directly. If they fetch their own data internally, you'll need to either:
- (a) Refactor them to accept data as props (preferred — makes them reusable), or
- (b) Create lightweight copies for the Pattern Library tab

Check the component signatures before deciding. The goal is code reuse, not duplication.

**Comparative overlay (stretch goal for this session):**
A "Compare with..." dropdown that lets you overlay another strategy's equity curve. This is nice-to-have. If time allows, implement it as a multi-select that overlays 1–2 additional equity curves on the same chart. If not, add a placeholder: "Strategy comparison coming soon."

## Task 2: Hook Updates

If usePerformance doesn't support strategy_id filtering, update it:

```typescript
// In usePerformance.ts (or create useStrategyPerformance.ts)
export function usePerformance(period: string, strategyId?: string) {
  const queryParams = new URLSearchParams();
  if (strategyId) queryParams.set('strategy_id', strategyId);
  
  return useQuery({
    queryKey: ['performance', period, { strategyId }],
    queryFn: () => fetchPerformance(period, strategyId),
    staleTime: 30_000,
  });
}
```

And update the API client function in `api/client.ts` to pass the strategy_id query parameter.

No new Vitest tests required this session — the components reuse existing tested components. New tests will be added in Session 9.
```

---

## Session 6 — Trades Tab + Intelligence Tab + Tab Wiring

### Prompt:

```
# Sprint 21a Session 6 — Trades Tab + Intelligence Tab + Tab Wiring

Read CLAUDE.md. Sessions 1–5 complete: API, dev mode, nav, left panel, Overview tab, Backtest tab, Performance tab. This session builds the remaining tabs and wires up the full tabbed detail view.

## Task 1: TradesTab

Create `argus/ui/src/features/patterns/tabs/TradesTab.tsx`:

Props: `strategyId: string`

This is a thin wrapper around the existing TradeTable component with the strategy filter locked.

```tsx
export function TradesTab({ strategyId }: { strategyId: string }) {
  // Use existing trade fetching with strategy_id filter
  // The existing useTrades hook or /trades endpoint supports ?strategy= filter
  // Check argus/ui/src/hooks/useTrades.ts for the interface
  
  // State for pagination
  const [page, setPage] = useState(1);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  
  const { data, isLoading } = useTrades({
    strategy_id: strategyId,
    limit: 20,
    offset: (page - 1) * 20,
  });
  
  return (
    <div>
      <TradeTable
        trades={data?.trades ?? []}
        totalCount={data?.total_count ?? 0}
        limit={20}
        page={page}
        onPageChange={setPage}
        onRowClick={setSelectedTrade}
        isLoading={isLoading}
      />
      
      {selectedTrade && (
        <TradeDetailPanel
          trade={selectedTrade}
          onClose={() => setSelectedTrade(null)}
        />
      )}
    </div>
  );
}
```

**Important:** Check the actual TradeTable props interface in `features/trades/TradeTable.tsx`. The props may differ from what I've shown above — match them exactly. Also check how useTrades works and what parameters it accepts.

Also check if the existing /trades endpoint supports a `strategy` query param. Looking at the backend routes (`argus/api/routes/trades.py`), the `query_trades` endpoint should support strategy filtering. If the useTrades hook doesn't pass strategy_id, extend it.

## Task 2: IntelligenceTab

Create `argus/ui/src/features/patterns/tabs/IntelligenceTab.tsx`:

Simple placeholder using EmptyState component.

```tsx
import { Sparkles } from 'lucide-react';
import { EmptyState } from '../../../components/EmptyState';

export function IntelligenceTab() {
  return (
    <div className="py-8">
      <EmptyState
        icon={Sparkles}
        message="Intelligence features coming in Sprint 25"
      />
      <div className="mt-4 text-center text-sm text-argus-text-dim max-w-md mx-auto">
        <p>This tab will show:</p>
        <ul className="mt-2 space-y-1 text-left pl-4">
          <li>• Pattern strength scoring logic</li>
          <li>• Quality grade breakdown for this pattern</li>
          <li>• Historical win rate by quality grade</li>
          <li>• Learning Loop insights and recommendations</li>
        </ul>
      </div>
    </div>
  );
}
```

## Task 3: PatternDetail Component

Create `argus/ui/src/features/patterns/PatternDetail.tsx`:

This is the right-panel container that holds the tabbed detail view.

Props:
```typescript
interface PatternDetailProps {
  strategyId: string;
  onClose: () => void;
}
```

Structure:
```tsx
export function PatternDetail({ strategyId, onClose }: PatternDetailProps) {
  const { activeTab, setActiveTab } = usePatternLibraryUI();
  const { data: strategiesData } = useStrategies();
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  
  const strategy = strategiesData?.strategies.find(s => s.strategy_id === strategyId);
  
  if (!strategy) return null;
  
  const tabs = [
    { key: 'overview', label: 'Overview' },
    { key: 'performance', label: 'Performance' },
    { key: 'backtest', label: 'Backtest' },
    { key: 'trades', label: 'Trades' },
    { key: 'intelligence', label: 'Intelligence' },
  ];
  
  return (
    <div>
      {/* Back button for tablet/mobile */}
      {!isDesktop && (
        <button onClick={onClose} className="flex items-center gap-1 text-sm text-argus-text-dim hover:text-argus-text mb-4">
          <ChevronLeft className="w-4 h-4" /> Back to strategies
        </button>
      )}
      
      {/* Strategy header */}
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-lg font-semibold text-argus-text">{strategy.name}</h2>
        <Badge variant={getPipelineBadgeVariant(strategy.pipeline_stage)}>
          {strategy.pipeline_stage.replace('_', ' ').toUpperCase()}
        </Badge>
      </div>
      <p className="text-sm text-argus-text-dim mb-4">{strategy.description_short}</p>
      
      {/* Tab navigation */}
      <SegmentedTab
        tabs={tabs.map(t => t.label)}
        activeIndex={tabs.findIndex(t => t.key === activeTab)}
        onChange={(index) => setActiveTab(tabs[index].key)}
      />
      
      {/* Tab content */}
      <div className="mt-4">
        {activeTab === 'overview' && <OverviewTab strategyId={strategyId} strategy={strategy} />}
        {activeTab === 'performance' && <PerformanceTab strategyId={strategyId} />}
        {activeTab === 'backtest' && <BacktestTab strategy={strategy} />}
        {activeTab === 'trades' && <TradesTab strategyId={strategyId} />}
        {activeTab === 'intelligence' && <IntelligenceTab />}
      </div>
    </div>
  );
}
```

**Note:** Check the SegmentedTab component interface — it may use different prop names. Match exactly.

## Task 4: Wire Everything Together in PatternLibraryPage

Update `PatternLibraryPage.tsx` to replace the placeholder PatternDetail div with the real component:

```tsx
import { PatternDetail } from '../features/patterns/PatternDetail';
```

The page scaffold from Session 3 should already have the conditional rendering logic. Just ensure PatternDetail is imported and rendered correctly.

## Task 5: Full Integration Test

Start dev mode and verify:
1. Selecting a strategy shows the detail panel
2. All 5 tabs render and switch correctly
3. Overview tab shows parameter table + markdown spec
4. Performance tab shows metrics and charts
5. Backtest tab shows status and metrics
6. Trades tab shows trade table (filtered to strategy)
7. Intelligence tab shows placeholder
8. On tablet/mobile, selecting shows full-width detail with back button
9. Back button returns to card grid

## Task 6: Update features/patterns/index.ts

Export all new components from the barrel file.

No new tests required this session — visual integration verification. Tests come in Session 9.
```

---

## Session 7 — SlideInPanel + Symbol Detail

### Prompt:

```
# Sprint 21a Session 7 — SlideInPanel Extraction + Symbol Detail Panel

Read CLAUDE.md. Sessions 1–6 complete: Full Pattern Library page working (pipeline, cards, filters, all 5 tabs). This session extracts the shared SlideInPanel and builds the Symbol Detail Panel.

## Task 1: Extract SlideInPanel

Create `argus/ui/src/components/SlideInPanel.tsx`:

This is a shared animated panel shell extracted from the TradeDetailPanel's slide-in behavior.

```tsx
interface SlideInPanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: string;  // Desktop width, default "40%"
}
```

**Behavior (matches existing TradeDetailPanel):**
- Desktop (≥1024px): Slides in from right. Fixed position, right-aligned. Width from prop (default 40%). Full height minus top padding. Background overlay (backdrop).
- Mobile (<1024px): Slides up from bottom. Fixed position. Height: 90vh. Full width. Rounded top corners.
- Animation: Framer Motion — desktop: `x: '100%' → 0`, mobile: `y: '100%' → 0`. Duration ~300ms, ease out.
- Close triggers: X button in header, Escape key, click on backdrop
- Body scroll lock when open (prevents scroll-through)

**Header:** Title (left), close X button (right). Subtitle under title if provided.

**Body:** Scrollable content area (children).

**Look at the existing TradeDetailPanel** (`features/trades/TradeDetailPanel.tsx`) — it has the slide-in animation already implemented. Extract the shell (animation, backdrop, header, close logic) into SlideInPanel, then refactor TradeDetailPanel to use SlideInPanel as its wrapper.

## Task 2: Refactor TradeDetailPanel

Refactor `features/trades/TradeDetailPanel.tsx` to use SlideInPanel:

```tsx
export function TradeDetailPanel({ trade, onClose }: TradeDetailPanelProps) {
  return (
    <SlideInPanel
      isOpen={!!trade}
      onClose={onClose}
      title={trade ? `${trade.symbol} — ${trade.side}` : ''}
      subtitle={trade?.entry_time ? formatDate(trade.entry_time) : undefined}
    >
      {trade && (
        <div>
          {/* Existing trade detail content — keep all of it */}
        </div>
      )}
    </SlideInPanel>
  );
}
```

**Critical:** Don't break the existing TradeDetailPanel functionality. The refactor should be invisible to users — same animation, same behavior, same content. Only the code structure changes.

## Task 3: Symbol Detail Panel

Create `argus/ui/src/features/symbol/SymbolDetailPanel.tsx`:

Triggered by the `useSymbolDetailUI` Zustand store. Any component can call `useSymbolDetailUI.getState().open('AAPL')` to open it.

```tsx
export function SymbolDetailPanel() {
  const { selectedSymbol, isOpen, close } = useSymbolDetailUI();
  
  if (!selectedSymbol) return null;
  
  return (
    <SlideInPanel
      isOpen={isOpen}
      onClose={close}
      title={selectedSymbol}
    >
      <div className="space-y-6">
        <SymbolChart symbol={selectedSymbol} />
        <SymbolTradingHistory symbol={selectedSymbol} />
        <SymbolPositionDetail symbol={selectedSymbol} />
      </div>
    </SlideInPanel>
  );
}
```

## Task 4: SymbolTradingHistory Component

Create `argus/ui/src/features/symbol/SymbolTradingHistory.tsx`:

Shows your trading history on this specific symbol.

**Content:**
- Header: "Your Trading History"
- Summary stats row: Total Trades | Win Rate | Avg R | Net P&L
- List of recent trades (last 10) — compact format: date, side, entry/exit prices, P&L, R-multiple
- If no trades found: "No trading history for {symbol}"

**Data source:** Use the trades endpoint with a symbol filter. Check if the existing `/api/v1/trades` endpoint supports filtering by symbol. If not, you'll need to add a `symbol` query parameter to the trades endpoint (in `argus/api/routes/trades.py` — it uses `trade_logger.query_trades()` which should support it; check the TradeLogger method).

## Task 5: SymbolPositionDetail Component

Create `argus/ui/src/features/symbol/SymbolPositionDetail.tsx`:

Shows current open position on this symbol (if any).

**Content:**
- Header: "Open Position" (only shown if position exists)
- If position exists: strategy name, entry price, current P&L, R-multiple, time in trade, stop/T1/T2 levels
- If no position: don't render anything (component returns null)

**Data source:** Use existing positions data (from usePositions hook or from the live store). Filter to the selected symbol.

## Task 6: SymbolChart Placeholder

Create `argus/ui/src/features/symbol/SymbolChart.tsx`:

For this session, create a PLACEHOLDER that shows:
- Symbol header with price (from positions data if available, otherwise "Price data loading...")
- A placeholder div where the chart will go: "Candlestick chart loading in Session 8"
- The actual LWChart candlestick implementation comes in Session 8

## Task 7: Mount SymbolDetailPanel

Add SymbolDetailPanel to `AppShell.tsx` so it's available globally:

```tsx
import { SymbolDetailPanel } from '../features/symbol';

// In the AppShell return, add after MobileNav:
<SymbolDetailPanel />
```

## Task 8: index.ts barrel

Create `argus/ui/src/features/symbol/index.ts` exporting the public components.

## Task 9: Vitest Tests

**SlideInPanel.test.tsx** (~2 tests):
- Renders when isOpen is true, hides when false
- Calls onClose when X button clicked

**SymbolDetailPanel.test.tsx** (~3 tests):
- Renders symbol name when opened
- Shows trading history section
- Shows chart placeholder section

Test target after session: 1542 pytest + ~63 Vitest.
```

---

## Session 8 — Symbol Chart + Click-Anywhere Wiring

### Prompt:

```
# Sprint 21a Session 8 — Symbol Candlestick Chart + Click-Anywhere Wiring

Read CLAUDE.md. Sessions 1–7 complete: Full Pattern Library, SlideInPanel extracted, Symbol Detail Panel with placeholder chart. This session implements the candlestick chart and wires up symbol clicks across the entire app.

## Task 1: SymbolChart Implementation

Replace the placeholder in `argus/ui/src/features/symbol/SymbolChart.tsx` with a real candlestick chart.

Use Lightweight Charts (already in the project as `lightweight-charts` — see `argus/ui/src/components/LWChart.tsx` for the existing wrapper pattern).

**Implementation:**
- Fetch bars from `GET /api/v1/market/{symbol}/bars` using the `useSymbolBars` hook created in Session 2
- Display as candlestick series (not line chart)
- Volume as histogram series below (if LW Charts supports it — it does via addHistogramSeries)
- Time axis: intraday minutes
- Price axis: auto-scaled
- Dark theme colors matching the app (green candles for up, red for down)
- Loading state: Skeleton box matching chart dimensions
- Error state: "Unable to load chart data"

**Reference the existing LWChart component** to understand how Lightweight Charts is integrated. You may be able to extend it or create a similar wrapper specifically for candlestick data.

**Key Lightweight Charts API:**
```typescript
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts';

// Create chart
const chart = createChart(container, {
  width,
  height: 300,
  layout: { background: { color: 'transparent' }, textColor: '#9ca3af' },
  grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
  crosshair: { mode: 0 },
  timeScale: { timeVisible: true, secondsVisible: false },
});

// Add candlestick series
const candleSeries = chart.addSeries(CandlestickSeries, {
  upColor: '#22c55e',
  downColor: '#ef4444',
  borderVisible: false,
  wickUpColor: '#22c55e',
  wickDownColor: '#ef4444',
});

// Set data — bars need to be { time: UTCTimestamp, open, high, low, close }
candleSeries.setData(bars.map(b => ({
  time: Math.floor(new Date(b.timestamp).getTime() / 1000),
  open: b.open,
  high: b.high,
  low: b.low,
  close: b.close,
})));
```

**Note:** Check the lightweight-charts version installed in the project and use the correct API (v3 vs v4 have different APIs). The existing LWChart.tsx will show which version is being used.

**Chart dimensions:**
- Desktop: fill the panel width, 300px height
- Mobile: fill width, 250px height

## Task 2: Wire Symbol Clicks Across the App

The SymbolDetailPanel is mounted globally in AppShell. Now wire up symbol clicks from existing components to open it.

**Components that show stock symbols and should be clickable:**

1. **WatchlistItem** (`features/watchlist/WatchlistItem.tsx`):
   - The symbol text should be clickable → opens SymbolDetailPanel
   - Add an onClick handler that calls `useSymbolDetailUI.getState().open(symbol)`

2. **OpenPositions** (`features/dashboard/OpenPositions.tsx`):
   - The symbol in each position row should be clickable
   - Add onClick → open symbol detail

3. **TradeTable** (`features/trades/TradeTable.tsx`):
   - The symbol column in each trade row should be clickable
   - Add onClick → open symbol detail
   - Be careful not to conflict with the existing row click (which opens TradeDetailPanel). The symbol text click should open SymbolDetailPanel; clicking elsewhere on the row opens TradeDetailPanel.
   - Implementation: wrap the symbol text in a button/span with `onClick` + `e.stopPropagation()` to prevent row click from firing.

4. **PatternCard** (`features/patterns/PatternCard.tsx`):
   - No symbol here — cards show strategy info, not individual stocks. Skip.

**Visual indication:** Clickable symbols should have a subtle hover effect — underline or color change on hover to indicate interactivity. Use `cursor-pointer hover:text-argus-accent transition-colors` or similar.

**Import pattern:**
```typescript
import { useSymbolDetailUI } from '../../stores/symbolDetailUI';

// In component:
const openSymbolDetail = useSymbolDetailUI((state) => state.open);

// On click:
onClick={(e) => {
  e.stopPropagation();
  openSymbolDetail(symbol);
}}
```

## Task 3: Integration Verification

Start dev mode and verify:
1. Symbol Detail Panel opens with candlestick chart for any symbol
2. Chart data loads from /market/{symbol}/bars endpoint
3. Clicking a symbol in Watchlist Sidebar opens Symbol Detail
4. Clicking a symbol in Open Positions opens Symbol Detail
5. Clicking a symbol in Trade Table opens Symbol Detail (row click still opens TradeDetailPanel)
6. Symbol Detail shows trading history and position info (if applicable)
7. Panel closes on X, Escape, backdrop click
8. Responsive: works on mobile (bottom sheet), tablet, desktop

No new tests this session — visual/integration verification. Remaining tests added in Session 9.
```

---

## Session 9 — Polish, Responsive QA, Remaining Tests

### Prompt:

```
# Sprint 21a Session 9 — Polish, Responsive QA, Remaining Tests

Read CLAUDE.md. Sessions 1–8 complete: Full Pattern Library page, Symbol Detail Panel with chart, click-anywhere wiring. This session is about polish, responsive testing, and writing remaining tests.

## Task 1: Skeleton Loading States

Ensure all Pattern Library components have proper skeleton loading states:

1. **PatternCardGrid** — skeleton cards while strategies loading (use Skeleton component, similar to existing StrategyCardsSkeleton in system/)
2. **PatternDetail tabs** — skeleton for each tab while data loads (overview markdown, performance metrics, trades)
3. **SymbolChart** — skeleton rectangle while bars load
4. **SymbolTradingHistory** — skeleton lines while trades load

## Task 2: Empty States

1. **PatternCardGrid** with filters that match nothing: EmptyState with "No strategies match the current filters" + suggestion to clear filters
2. **PerformanceTab** with no trades: EmptyState with "No trades recorded for this strategy yet"
3. **TradesTab** with no trades: EmptyState (TradeTable should already handle this)
4. **SymbolTradingHistory** with no trades: "No trading history for {symbol}"

## Task 3: Animations

1. **Card selection** — selected card gets a smooth ring/border transition (CSS transition, not Framer Motion)
2. **Tab switching** — content fades in when switching tabs (subtle, fast)
3. **Pipeline stage hover** — stages with count > 0 get subtle scale on hover
4. **Card grid stagger** — cards stagger in when page loads (reuse staggerContainer/staggerItem from utils/motion)

## Task 4: Responsive QA

Test all three breakpoints manually. Fix any issues:

**Desktop (≥1024px):**
- [ ] Master-detail layout: left 35%, right 65%
- [ ] Pipeline spans full width above the split
- [ ] Cards stack vertically in left panel, scrollable independently
- [ ] Detail panel scrolls independently
- [ ] Symbol Detail Panel overlays at 40% width

**Tablet (640–1023px):**
- [ ] Cards fill full width
- [ ] Selecting card transitions to full-width detail view
- [ ] Back button returns to card grid
- [ ] Pipeline stages don't overflow (scroll if needed)
- [ ] Bottom nav shows 5 items

**Mobile (<640px):**
- [ ] Cards fill full width, stacked vertically
- [ ] Detail view is full-screen with back button
- [ ] Pipeline is compact scrollable pills
- [ ] Symbol Detail Panel is bottom sheet (90vh)
- [ ] Bottom nav 5 items all fit
- [ ] Touch targets ≥44px

## Task 5: Remaining Vitest Tests

If not already written, add:

**IncubatorPipeline.test.tsx** — verify if tests from Session 3 were created. If not, add them now.

**PatternCard.test.tsx** — verify, add if missing.

**Additional tests if needed to reach ~65 total Vitest.**

## Task 6: ruff + Full Test Suite

```bash
cd /path/to/argus
ruff check argus/
pytest --tb=short -q
cd argus/ui && npx vitest run
```

Fix any linting errors. Fix any test failures. Target: 1542+ pytest, 65+ Vitest, zero regressions.

## Task 7: Code Review Prep

Create a summary of what was built in Sprint 21a:

1. List of all new files created
2. List of all modified files
3. New test count (pytest + Vitest)
4. Any known issues or deferred items
5. Screenshots / descriptions of key screens for code review
```

---

## Session 10 — Buffer (Edge Cases + Bug Fixes)

### Prompt:

```
# Sprint 21a Session 10 — Buffer: Edge Cases, Bug Fixes, Final QA

Read CLAUDE.md. Sessions 1–9 complete. This is the buffer session for any remaining issues.

## Check These Edge Cases

1. **Strategy spec endpoint with no file on disk** — does it 404 gracefully?
2. **Performance tab for strategy with zero trades** — does it show empty state, not crash?
3. **Symbol Detail for a symbol with no trades and no position** — shows chart + empty history, no errors?
4. **Pipeline click → filter → click same stage again** — clears filter correctly?
5. **Navigating away from Pattern Library and back** — preserves selected strategy and tab? (Zustand store persists)
6. **Very long strategy spec markdown** — scrollable, doesn't overflow?
7. **Keyboard shortcut `4` from any page** — navigates to Pattern Library?
8. **Symbol clicks in Trade Detail Panel** — if symbol appears in trade detail, clicking it opens Symbol Detail?

## Fix Any Issues Found

If any bugs surfaced during code review feedback or Session 9 QA, fix them here.

## Final Checks

- [ ] `ruff check argus/` — zero errors
- [ ] `pytest --tb=short -q` — all pass, check count matches expected
- [ ] `cd argus/ui && npx vitest run` — all pass, check count
- [ ] `python -m argus.api --dev` — Pattern Library page fully functional
- [ ] Git status clean, all changes committed

## If No Issues

If everything passes and there are no issues to fix, this session can be skipped. Move directly to code review.
```
