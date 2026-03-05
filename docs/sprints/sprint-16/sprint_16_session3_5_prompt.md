# Sprint 16 Session 3.5 — Animation & UX Fix-Up

## Context
Sprint 16 Sessions 1–3 implemented animation foundations (Framer Motion page transitions, skeleton loading, stagger entry animations). Code review identified 8 targeted fixes needed before building Sessions 4–7 on this foundation. All changes are in `argus/ui/src/`.

## Scope — 8 Fixes

### Fix 1: Delete Dead Code
Delete `src/components/LoadingState.tsx` — it's no longer imported anywhere (all loading states now use Skeleton components).

### Fix 2: Dashboard Left-to-Right Card Sequencing
**File:** `src/pages/DashboardPage.tsx`

**Problem:** The top row's three summary cards (AccountSummary, DailyPnlCard, MarketStatusBadge) each wrap themselves in a nested `staggerContainer` with their own `initial="hidden" animate="show"`. This causes all three cards to animate simultaneously instead of staggering left-to-right.

**Fix:** Remove the inner `staggerContainer` wrappers. Make each card a direct `staggerItem` child of the grid. The grid itself should be the outer `staggerItem` child, but each card within it should be an individual `staggerItem` under its own inner `staggerContainer` on the grid div itself. Structure should be:

```tsx
{/* Top row grid IS a stagger container for L-to-R card sequencing */}
<motion.div
  className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6"
  variants={staggerContainer(0.08)}
  initial="hidden"
  animate="show"
>
  <motion.div variants={staggerItem} className="h-full">
    <AccountSummary />
  </motion.div>
  <motion.div variants={staggerItem} className="h-full">
    <DailyPnlCard />
  </motion.div>
  <motion.div variants={staggerItem} className="md:col-span-2 lg:col-span-1 h-full">
    <MarketStatusBadge />
  </motion.div>
</motion.div>
```

But note: the top row grid must ALSO be a staggerItem of the outer page container, so the grid itself staggers in sequence with OpenPositions and the bottom row. Nest variants: the grid div uses BOTH the page-level `staggerItem` (to sequence with other page sections) AND its own `staggerContainer` (to sequence cards within). Framer Motion supports this — when a node has its own `variants`, it acts as both a child and a container.

To achieve this, make the grid div use a combined approach. Use `variants` with a custom variant that includes both the staggerItem animation AND staggerChildren for its children:

```tsx
// In motion.ts, add:
export function staggerItemWithChildren(staggerDelay = 0.08): Variants {
  return {
    hidden: { opacity: 0, y: 12 },
    show: {
      opacity: 1,
      y: 0,
      transition: {
        duration: DURATION.normal,
        ease: EASE.out,
        staggerChildren: staggerDelay,
      },
    },
  };
}
```

Then the grid uses `variants={staggerItemWithChildren(0.08)}` — it fades in itself (as a child of the page stagger) AND staggers its own children.

### Fix 3: Account Equity Card Height
**Problem:** AccountSummary card is visually shorter than DailyPnlCard and MarketStatusBadge in the top row because it has less content.

**Fix:** All three cards already use `<Card className="h-full">`. After Fix 2, each card's `motion.div` wrapper already has `className="h-full"`. Verify this fixes it visually. If the cards are still unequal, the grid's default `align-items: stretch` should make all cells the same height — the Card's `h-full` then fills the cell. If still unequal, inspect whether the motion.div wrapper needs explicit `h-full`.

### Fix 4: TradeStatsBar Width Stability
**File:** `src/features/trades/TradeStatsBar.tsx`

**Problem:** When toggling Outcome filter (All/Wins/Losses/BE), the stats bar metric widths shift because the text content changes length (e.g., "12" vs "3", "$1,234" vs "$89").

**Fix:** Give each metric section a fixed minimum width and use `tabular-nums` on all numeric values. Change the layout from `justify-around` to explicit fixed-width sections:

```tsx
<div className="flex items-center justify-between gap-4">
  <div className="flex-1 min-w-0">
    <MetricCard label="Trades" value={...} subValue={...} />
  </div>
  <div className="w-px h-8 bg-argus-border flex-shrink-0" />
  <div className="flex-1 min-w-0">
    <MetricCard label="Win Rate" value={...} trend={...} />
  </div>
  <div className="w-px h-8 bg-argus-border hidden sm:block flex-shrink-0" />
  <div className="hidden sm:block flex-1 min-w-0">
    <MetricCard label="Net P&L" value={...} trend={...} />
  </div>
</div>
```

Each `flex-1 min-w-0` section gets equal width regardless of content. MetricCard already has `tabular-nums` on its value, so numbers should align.

### Fix 5: TradeTable Column Width Stability
**File:** `src/features/trades/TradeTable.tsx`

**Problem:** Table column widths shift when filtered data changes because `<table>` auto-sizes columns to content.

**Fix:** Add `table-fixed` class to the `<table>` element and set explicit column widths via `<colgroup>`:

```tsx
<table className="w-full table-fixed">
  <colgroup>
    {/* Desktop columns */}
    <col className="hidden lg:table-column w-[100px]" /> {/* Date */}
    <col className="hidden lg:table-column w-[80px]" />  {/* Symbol */}
    <col className="hidden lg:table-column w-[55px]" />  {/* Side */}
    <col className="hidden md:table-column w-[85px]" />  {/* Entry */}
    <col className="hidden md:table-column w-[85px]" />  {/* Exit */}
    <col className="w-[90px]" />                          {/* P&L */}
    <col className="hidden md:table-column w-[60px]" />   {/* R */}
    <col className="hidden lg:table-column w-[65px]" />   {/* Shares */}
    <col className="w-[60px]" />                           {/* Exit Reason */}
    <col className="hidden lg:table-column w-[80px]" />   {/* Duration */}
    <col className="hidden lg:table-column w-[65px]" />   {/* Commission */}
    {/* Phone combined column */}
    <col className="lg:hidden" />                          {/* Trade (combined) */}
  </colgroup>
  ...
</table>
```

IMPORTANT: The phone layout uses a combined "Trade" column that should not coexist with the desktop columns. The responsive show/hide on `<col>` elements may not work the same as on `<th>`/`<td>`. An alternative approach: instead of `<colgroup>`, add explicit width classes directly on the `<th>` elements:

```tsx
<th className="hidden lg:table-cell ... w-[100px]">Date</th>
<th className="hidden lg:table-cell ... w-[80px]">Symbol</th>
// etc.
```

Test both approaches — `<colgroup>` is cleaner if Tailwind's responsive classes work on `<col>`, otherwise use `<th>` widths. The key is adding `table-fixed` to the `<table>`.

### Fix 6: Subtle Transition on Outcome Toggle
**File:** `src/pages/TradesPage.tsx`

**Problem:** When toggling the Outcome filter, the stats bar and trade table swap content instantly with no visual transition.

**Fix:** Add a subtle crossfade using Framer Motion `AnimatePresence` + `motion.div` keyed to the outcome filter value. Wrap the stats bar and table content in:

```tsx
import { AnimatePresence, motion } from 'framer-motion';
import { fadeIn } from '../utils/motion';

// Use the outcome value (or a combination of all active filter values) as the key
const filterKey = `${outcome ?? 'all'}-${strategy_id ?? 'all'}`;

<AnimatePresence mode="wait">
  <motion.div
    key={filterKey}
    variants={fadeIn}
    initial="hidden"
    animate="show"
    exit="hidden"
  >
    {/* Stats bar + table content */}
  </motion.div>
</AnimatePresence>
```

Keep it subtle — use the existing `fadeIn` variant from motion.ts (400ms, opacity only, no translate). The `mode="wait"` ensures old content fades out before new fades in.

NOTE: The stagger container for the page should NOT re-animate when filters change. Only the content inside the stagger items should crossfade. So wrap just the stats bar content and the table content (not the stagger `motion.div` wrappers) in the AnimatePresence.

### Fix 7: MetricsGrid First-Mount-Only Animation
**File:** `src/features/performance/MetricsGrid.tsx`

**Problem:** The stagger animation replays every time the Performance period changes because MetricsGrid remounts with new data. This makes the page feel like it's fully reloading.

**Fix:** Use a ref to track first mount. Only apply `initial="hidden"` on the first render. On subsequent renders, set `initial={false}` to disable the entrance animation:

```tsx
export function MetricsGrid({ metrics, className = '' }: MetricsGridProps) {
  const hasAnimated = useRef(false);

  return (
    <Card className={className}>
      <motion.div
        className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
        variants={staggerContainer(0.04)}
        initial={hasAnimated.current ? false : "hidden"}
        animate="show"
        onAnimationComplete={() => { hasAnimated.current = true; }}
      >
        {/* ... stagger items unchanged ... */}
      </motion.div>

      <motion.div
        className="hidden md:grid ..."
        variants={staggerContainer(0.04)}
        initial={hasAnimated.current ? false : "hidden"}
        animate="show"
      >
        {/* ... secondary metrics unchanged ... */}
      </motion.div>
    </Card>
  );
}
```

IMPORTANT: `hasAnimated` is a `useRef`, not state — it persists across re-renders without triggering them. The `onAnimationComplete` callback sets it to true after the first stagger completes. On subsequent renders (period change), `initial={false}` tells Framer Motion to skip the initial animation and go straight to the `animate` state.

However, there's a subtlety: if PerformancePage remounts MetricsGrid entirely (which it does, because it shows PerformanceSkeleton during loading and then MetricsGrid when data arrives), the ref resets. This is actually fine — the first mount after loading should animate. The fix prevents re-animation when data changes without unmounting (which happens if we fix the data-freeze issue in Fix 8).

### Fix 8: Performance Page Data Freeze During Exit
**Files:** `src/pages/PerformancePage.tsx`, `src/features/performance/PeriodSelector.tsx`, `src/hooks/useSelectedPeriod.ts`

**Problem:** When navigating away from the Performance page while on a non-default period (e.g., "Week"), the URL changes to the new route, which causes `useSearchParams().get('period')` to return null, which defaults to 'month'. This triggers a data refetch that visibly swaps the page content back to Month data during the 150ms exit fade.

**Fix:** Use local state for the period value instead of reading directly from URL search params. Initialize from URL on mount, sync to URL on user interaction, but don't let URL changes from navigation trigger data changes.

**Step 1:** Update `useSelectedPeriod.ts` to accept an optional override:
```tsx
// This hook is now only used for initial value extraction
export function useInitialPeriod(): PerformancePeriod {
  const [searchParams] = useSearchParams();
  // Only called once via useState initializer — won't re-run on URL change
  return (searchParams.get('period') as PerformancePeriod) || 'month';
}
```

**Step 2:** Update `PerformancePage.tsx`:
```tsx
export function PerformancePage() {
  // Local state initialized from URL — immune to URL changes during exit
  const [period, setPeriod] = useState<PerformancePeriod>(
    () => {
      const params = new URLSearchParams(window.location.search);
      return (params.get('period') as PerformancePeriod) || 'month';
    }
  );
  const { data, isLoading, error } = usePerformance(period);

  // ... rest of component uses `period` and passes `setPeriod` to PeriodSelector
```

**Step 3:** Update `PeriodSelector.tsx` to accept props:
```tsx
interface PeriodSelectorProps {
  className?: string;
  selectedPeriod: PerformancePeriod;
  onPeriodChange: (period: PerformancePeriod) => void;
}

export function PeriodSelector({ className = '', selectedPeriod, onPeriodChange }: PeriodSelectorProps) {
  const [, setSearchParams] = useSearchParams();

  const handlePeriodChange = (period: PerformancePeriod) => {
    onPeriodChange(period);  // Update parent state (drives data fetch)
    setSearchParams({ period }, { replace: true });  // Sync URL for bookmarking
  };

  // Use selectedPeriod prop instead of reading from URL
  return (
    <div className={`flex gap-1 ${className}`}>
      {periods.map(({ value, label }) => (
        <button
          key={value}
          onClick={() => handlePeriodChange(value)}
          className={`... ${selectedPeriod === value ? 'bg-argus-accent text-white' : '...'}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
```

**Step 4:** In PerformancePage, pass props to PeriodSelector and the PageHeader component:
```tsx
<PeriodSelector selectedPeriod={period} onPeriodChange={setPeriod} />
```

Also update the `PageHeader` component (used in loading/error states) to accept and pass these props through.

### Fix 9: Trades Page Data Freeze During Exit
**File:** `src/pages/TradesPage.tsx`

**Same problem as Fix 8** but for the Trades page. When navigating away while outcome is set to "Wins", the URL loses the `outcome=win` param, causing a refetch with `outcome=all` during exit.

**Fix:** Use local state for ALL filter values (strategy, outcome, dates, page), initialize from URL on mount, and sync to URL on user interaction.

```tsx
export function TradesPage() {
  // Snapshot URL params into local state on mount
  const [filters, setFilters] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return {
      strategy_id: params.get('strategy') || undefined,
      outcome: (params.get('outcome') as 'win' | 'loss' | 'breakeven') || undefined,
      date_from: params.get('from') || undefined,
      date_to: params.get('to') || undefined,
      page: parseInt(params.get('page') || '1', 10),
    };
  });

  const [, setSearchParams] = useSearchParams();

  // Update both local state and URL
  const updateFilters = useCallback((updates: Partial<typeof filters>) => {
    setFilters(prev => {
      const next = { ...prev, ...updates };
      // Reset page on filter change (unless page itself is being updated)
      if (!('page' in updates)) next.page = 1;
      return next;
    });

    // Sync to URL
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      for (const [key, value] of Object.entries(updates)) {
        const urlKey = key === 'strategy_id' ? 'strategy' : key === 'date_from' ? 'from' : key === 'date_to' ? 'to' : key;
        if (value === undefined || value === 'all' || (key === 'page' && value === 1)) {
          next.delete(urlKey);
        } else {
          next.set(urlKey, String(value));
        }
      }
      if (!('page' in updates)) next.delete('page');
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  // Data hook uses local state, not URL
  const { data, isLoading, error } = useTrades({
    strategy_id: filters.strategy_id,
    outcome: filters.outcome,
    date_from: filters.date_from,
    date_to: filters.date_to,
    limit: ITEMS_PER_PAGE,
    offset: (filters.page - 1) * ITEMS_PER_PAGE,
  });

  // ... pass updateFilters to TradeFilters as a prop
```

Update `TradeFilters` to accept an `onFilterChange` callback prop and use it instead of directly manipulating URL params. It should still render the current filter state (pass as props or have it read from a shared source).

### Fix 10: Chart Draw-In Animation
**Files:** `src/features/performance/EquityCurve.tsx`, `src/features/performance/DailyPnlChart.tsx`, and a new utility `src/utils/chartAnimation.ts`

**Create `src/utils/chartAnimation.ts`:**
```tsx
/**
 * Progressive chart data reveal animation.
 *
 * Feeds data points in batches using requestAnimationFrame to create
 * a left-to-right draw-in effect. Uses fixed viewport (full time range
 * set upfront) so the chart doesn't zoom during animation.
 *
 * Stays within DEC-110 budget: <500ms, 60fps.
 */

import type { IChartApi, ISeriesApi, SeriesDataItemTypeMap, Time } from 'lightweight-charts';

type SeriesType = keyof SeriesDataItemTypeMap;

export function animateChartDrawIn<T extends SeriesType>(
  series: ISeriesApi<T>,
  data: SeriesDataItemTypeMap[T][],
  chart: IChartApi,
  durationMs = 400
) {
  if (data.length === 0) return;

  // Set full viewport upfront so chart doesn't zoom during animation
  // First set all data to establish the time range, then clear and animate
  series.setData(data);
  chart.timeScale().fitContent();

  // Now get the visible range and clear data
  series.setData([]);

  const startTime = performance.now();

  function step() {
    const elapsed = performance.now() - startTime;
    const progress = Math.min(elapsed / durationMs, 1);
    // Ease-out cubic for natural deceleration
    const easedProgress = 1 - Math.pow(1 - progress, 3);

    const targetIndex = Math.max(1, Math.ceil(easedProgress * data.length));
    series.setData(data.slice(0, targetIndex));

    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }

  requestAnimationFrame(step);
}
```

**Update `EquityCurve.tsx`** — in `handleChartReady`, replace:
```tsx
series.setData(dataRef.current);
chart.timeScale().fitContent();
```
with:
```tsx
import { animateChartDrawIn } from '../../utils/chartAnimation';
// ...
animateChartDrawIn(series, dataRef.current, chart);
```

**Update `DailyPnlChart.tsx`** — same change in `handleChartReady`:
```tsx
import { animateChartDrawIn } from '../../utils/chartAnimation';
// ...
animateChartDrawIn(series, dataRef.current, chart);
```

For the data-update `useEffect` (when period changes), do NOT animate — just set data directly. The animation is only for the initial chart mount.

## Testing Checklist

After implementing all fixes, verify:

1. [ ] `npm run build` — zero TypeScript errors
2. [ ] `npm run lint` — clean
3. [ ] Dashboard: top row cards animate left-to-right in sequence (not simultaneously)
4. [ ] Dashboard: all three top-row cards are the same height
5. [ ] Trades: toggle between All/Wins/Losses/BE — stats bar widths stay fixed
6. [ ] Trades: toggle between outcomes — table column widths stay fixed
7. [ ] Trades: toggling outcome shows a subtle fade transition
8. [ ] Performance: changing period does NOT replay the MetricsGrid stagger animation
9. [ ] Performance: navigate to Trades while on "Week" period — no visible data flash during exit fade
10. [ ] Trades: navigate to Dashboard while on "Wins" filter — no visible data flash during exit fade
11. [ ] Performance: equity curve draws left-to-right on page load
12. [ ] Performance: daily P&L histogram draws left-to-right on page load
13. [ ] All pages: page transition (fade out → fade in) still works correctly
14. [ ] All pages: stagger entry animations still fire on navigation

## Run the dev server for visual testing
```bash
cd argus/ui && npm run dev
```
In another terminal, start the API mock server:
```bash
cd argus && python -m argus.api --dev
```

## Files Modified (expected)
- `src/components/LoadingState.tsx` — DELETED
- `src/utils/motion.ts` — add `staggerItemWithChildren` variant
- `src/utils/chartAnimation.ts` — NEW FILE
- `src/pages/DashboardPage.tsx` — restructure top row stagger
- `src/pages/PerformancePage.tsx` — state-based period management
- `src/pages/TradesPage.tsx` — state-based filter management, crossfade
- `src/features/performance/PeriodSelector.tsx` — accept props
- `src/features/performance/MetricsGrid.tsx` — first-mount-only animation
- `src/features/performance/EquityCurve.tsx` — chart draw-in
- `src/features/performance/DailyPnlChart.tsx` — chart draw-in
- `src/features/trades/TradeStatsBar.tsx` — fixed-width layout
- `src/features/trades/TradeTable.tsx` — table-fixed + column widths
- `src/features/trades/TradeFilters.tsx` — accept filter callback prop
- `src/hooks/useSelectedPeriod.ts` — simplified or removed
