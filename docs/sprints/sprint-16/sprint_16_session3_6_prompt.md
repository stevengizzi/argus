# Sprint 16 Session 3.6 — Remaining Animation Polish

## Context
Session 3.5 fixed 10 animation/UX issues. Three follow-up items remain before we're clean for Session 4.

## Fix 1: Dashboard Bottom Row Left-to-Right Stagger

**File:** `src/pages/DashboardPage.tsx`

**Problem:** The "Recent Trades" and "System Status" cards in the bottom row appear simultaneously. They should stagger left-to-right like the top row's Account/Daily P&L/Market cards do.

**Fix:** Change the bottom row grid from `staggerItem` to `staggerItemWithChildren(0.08)`, and wrap each child in its own `motion.div variants={staggerItem}`:

Change this:
```tsx
<motion.div
  className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 lg:gap-6"
  variants={staggerItem}
>
  <RecentTrades />
  <HealthMini />
</motion.div>
```

To this:
```tsx
<motion.div
  className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 lg:gap-6"
  variants={staggerItemWithChildren(0.08)}
>
  <motion.div variants={staggerItem}>
    <RecentTrades />
  </motion.div>
  <motion.div variants={staggerItem}>
    <HealthMini />
  </motion.div>
</motion.div>
```

This matches the pattern already used in the top row grid.

## Fix 2: Faster, Subtler Trades Filter Crossfade

**Files:** `src/utils/motion.ts`, `src/pages/TradesPage.tsx`

**Problem:** The current filter crossfade uses `fadeIn` (400ms) with `AnimatePresence mode="wait"`, which means: 400ms fade out → 400ms fade in = 800ms total. This feels gratuitous. We need something much snappier.

**Step 1 — Add a quick crossfade variant to `motion.ts`:**
```tsx
// Quick crossfade for in-place content swaps (filter changes, period changes)
// Faster than fadeIn, designed for mode="wait" where total time = exit + enter
export const quickFade: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: DURATION.fast } as Transition,  // 150ms
  },
};
```

**Step 2 — Update `TradesPage.tsx`:**
Replace both `AnimatePresence` blocks to use `quickFade` instead of `fadeIn`:

```tsx
import { staggerContainer, staggerItem, quickFade } from '../utils/motion';
```

In both the stats bar and content area AnimatePresence blocks, change:
```tsx
variants={fadeIn}
```
to:
```tsx
variants={quickFade}
```

This gives 150ms out + 150ms in = 300ms total, which feels snappy and intentional rather than sluggish.

Also remove the `fadeIn` import if it's no longer used in this file.

## Fix 3: Performance Page — Stable Containers, Animated Data

**Files:** `src/pages/PerformancePage.tsx`, `src/features/performance/MetricsGrid.tsx`, `src/features/performance/EquityCurve.tsx`, `src/features/performance/DailyPnlChart.tsx`, `src/features/performance/StrategyBreakdown.tsx`

**Problem:** When the user changes the Performance period, the entire page unmounts (replaced by PerformanceSkeleton during loading), then remounts when data arrives. This causes every container, header, chart, and metric to flash/reload. The user wants:
- Containers (cards, borders, backgrounds) persist — never unmount
- Headers ("Performance", "Equity Curve", "Daily P&L", metric labels like "Trades", "Win Rate", etc.) persist — never unmount
- Only the DATA VALUES and CHART CONTENTS transition with a subtle animation

**This is a fundamental restructure of how PerformancePage handles loading.**

### Step 1: PerformancePage — Never fully unmount content after first load

The current pattern:
```tsx
if (isLoading) {
  return <PerformanceSkeleton />;  // This unmounts everything!
}
```

Replace with a pattern that shows skeletons ONLY on initial load (no data yet), and keeps the real content mounted during subsequent refetches:

```tsx
export function PerformancePage() {
  const [period, setPeriod] = useState<PerformancePeriod>(() => {
    const params = new URLSearchParams(window.location.search);
    return (params.get('period') as PerformancePeriod) || 'month';
  });

  const { data, isLoading, error, isFetching } = usePerformance(period);

  // Track whether we've ever had data (for initial skeleton vs. period change)
  const hasHadData = useRef(false);
  if (data && data.metrics.total_trades > 0) {
    hasHadData.current = true;
  }

  // First load — show skeleton (no data yet)
  if (isLoading && !hasHadData.current) {
    return (
      <div className="space-y-6">
        <PageHeader selectedPeriod={period} onPeriodChange={setPeriod} />
        <PerformanceSkeleton />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="space-y-6">
        <PageHeader selectedPeriod={period} onPeriodChange={setPeriod} />
        <Card>
          <div className="text-center py-8">
            <TrendingUp className="w-8 h-8 text-argus-loss mx-auto mb-4" />
            <p className="text-argus-text-dim">Failed to load performance data</p>
            <p className="text-argus-text-dim text-xs mt-2">{error.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="text-argus-accent hover:underline text-sm mt-4"
            >
              Try again
            </button>
          </div>
        </Card>
      </div>
    );
  }

  if (!data || data.metrics.total_trades === 0) {
    return (
      <div className="space-y-6">
        <PageHeader selectedPeriod={period} onPeriodChange={setPeriod} />
        <Card>
          <div className="text-center py-8">
            <TrendingUp className="w-8 h-8 text-argus-text-dim mx-auto mb-4" />
            <p className="text-argus-text-dim">No trades for this period</p>
          </div>
        </Card>
      </div>
    );
  }

  // Main render — containers are always stable, isFetching dims data during transition
  return (
    <motion.div
      className="space-y-4 md:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Page header with period selector */}
      <motion.div
        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        variants={staggerItem}
      >
        <div className="flex items-center gap-3">
          <TrendingUp className="w-6 h-6 text-argus-accent" />
          <h1 className="text-xl font-semibold text-argus-text">Performance</h1>
        </div>
        <PeriodSelector selectedPeriod={period} onPeriodChange={setPeriod} />
      </motion.div>

      {/* Metrics grid — pass isFetching for subtle transition */}
      <motion.div variants={staggerItem}>
        <MetricsGrid metrics={data.metrics} isTransitioning={isFetching} />
      </motion.div>

      {/* Charts — pass isFetching for subtle transition */}
      <motion.div variants={staggerItem}>
        <ChartErrorBoundary fallback={...}>
          <EquityCurve dailyPnl={data.daily_pnl} isTransitioning={isFetching} />
        </ChartErrorBoundary>
      </motion.div>
      <motion.div variants={staggerItem}>
        <ChartErrorBoundary fallback={...}>
          <DailyPnlChart dailyPnl={data.daily_pnl} isTransitioning={isFetching} />
        </ChartErrorBoundary>
      </motion.div>

      {/* Strategy breakdown */}
      <motion.div variants={staggerItem}>
        <StrategyBreakdown byStrategy={data.by_strategy} isTransitioning={isFetching} />
      </motion.div>
    </motion.div>
  );
}
```

Add `useRef` to imports. Also add `isFetching` to the destructured return from `usePerformance` — TanStack Query provides it. `isFetching` is true during refetches even when `data` still holds the previous value (`isLoading` is only true when there's no cached data at all).

IMPORTANT: TanStack Query's `keepPreviousData` behavior — by default, when the query key changes (period changes), TanStack Query v5 keeps the previous data available while fetching new data. `isLoading` is only true if there's NO cached data. `isFetching` is true during background refetches. So `data` will hold the PREVIOUS period's data while the new period loads. This is exactly what we want — the containers stay populated with stale data (slightly dimmed via `isTransitioning`), then snap to new data when it arrives.

However, to ensure previous data is kept during key changes, add `placeholderData` to the query:

### Step 2: Update `usePerformance.ts`
```tsx
import { useQuery, keepPreviousData } from '@tanstack/react-query';

export function usePerformance(period: PerformancePeriod) {
  return useQuery<PerformanceResponse, Error>({
    queryKey: ['performance', period],
    queryFn: () => getPerformance(period),
    refetchInterval: 30_000,
    placeholderData: keepPreviousData,  // Keep previous period's data while fetching new
  });
}
```

### Step 3: MetricsGrid — Stable Container, Animated Values

Remove the stagger animation entirely. The container and labels should render instantly and persistently. Only the values should animate when they change.

```tsx
interface MetricsGridProps {
  metrics: MetricsData;
  isTransitioning?: boolean;
  className?: string;
}

export function MetricsGrid({ metrics, isTransitioning = false, className = '' }: MetricsGridProps) {
  // ... existing computation logic unchanged ...

  return (
    <Card className={className}>
      <div
        className={`grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 transition-opacity duration-150 ${
          isTransitioning ? 'opacity-50' : 'opacity-100'
        }`}
      >
        <MetricCard label="Trades" value={metrics.total_trades.toString()} />
        <MetricCard label="Win Rate" value={formatPercentRaw(winRatePct)} trend={winRateTrend} />
        <MetricCard label="Profit Factor" value={metrics.profit_factor.toFixed(2)} trend={pfTrend} />
        <MetricCard label="Sharpe" value={metrics.sharpe_ratio.toFixed(2)} trend={sharpeTrend} />
        <MetricCard label="Max DD" value={formatPercentRaw(Math.abs(metrics.max_drawdown_pct))} subValue="drawdown" />
        <MetricCard label="Net P&L" value={formatCurrency(metrics.net_pnl)} trend={metrics.net_pnl > 0 ? 'up' : metrics.net_pnl < 0 ? 'down' : 'neutral'} />
      </div>

      {/* Additional metrics row - visible on tablet+ */}
      <div
        className={`hidden md:grid grid-cols-4 lg:grid-cols-6 gap-4 mt-4 pt-4 border-t border-argus-border transition-opacity duration-150 ${
          isTransitioning ? 'opacity-50' : 'opacity-100'
        }`}
      >
        <MetricCard label="Avg R" value={metrics.avg_r_multiple.toFixed(2) + 'R'} />
        <MetricCard label="Avg Hold" value={formatDuration(metrics.avg_hold_seconds)} />
        <MetricCard label="Largest Win" value={formatCurrency(metrics.largest_win)} />
        <MetricCard label="Largest Loss" value={formatCurrency(Math.abs(metrics.largest_loss))} />
        <MetricCard label="Win Streak" value={metrics.consecutive_wins_max.toString()} />
        <MetricCard label="Loss Streak" value={metrics.consecutive_losses_max.toString()} />
      </div>
    </Card>
  );
}
```

Key changes:
- Remove ALL `motion.div` wrappers and Framer Motion imports from MetricsGrid
- Remove stagger variants — no animation on mount, no animation on data change
- Use plain `div` elements with CSS `transition-opacity duration-150`
- `isTransitioning` dims the values to 50% opacity during fetch, then snaps back to 100% when data arrives
- Labels are always visible and stable

### Step 4: EquityCurve — Stable Container, Animated Chart Data

The Card + CardHeader should never unmount. Only the chart data transitions.

```tsx
interface EquityCurveProps {
  dailyPnl: DailyPnlEntry[];
  isTransitioning?: boolean;
  className?: string;
}

export function EquityCurve({ dailyPnl, isTransitioning = false, className = '' }: EquityCurveProps) {
  // ... existing height + data logic unchanged ...

  // The chart container always renders (never conditionally unmounted)
  return (
    <Card className={className} noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="Equity Curve" />
      </div>
      <div className={`transition-opacity duration-150 ${isTransitioning ? 'opacity-50' : 'opacity-100'}`}>
        {dailyPnl.length === 0 ? (
          <div
            className="flex items-center justify-center text-argus-text-dim text-sm"
            style={{ height: chartHeight }}
          >
            Not enough data for this period
          </div>
        ) : (
          <LWChart
            height={chartHeight}
            onChartReady={handleChartReady}
            className="w-full"
          />
        )}
      </div>
    </Card>
  );
}
```

The Card and CardHeader are outside the transitioning wrapper. Only the chart area gets dimmed/updated.

### Step 5: DailyPnlChart — Same Pattern as EquityCurve

```tsx
interface DailyPnlChartProps {
  dailyPnl: DailyPnlEntry[];
  isTransitioning?: boolean;
  className?: string;
}
```

Apply the same structural change: Card + CardHeader always stable, chart area wrapped in `transition-opacity` div with `isTransitioning` control.

### Step 6: StrategyBreakdown — Same Pattern

```tsx
interface StrategyBreakdownProps {
  byStrategy: Record<string, StrategyMetrics>;
  isTransitioning?: boolean;
  className?: string;
}

export function StrategyBreakdown({ byStrategy, isTransitioning = false, className = '' }: StrategyBreakdownProps) {
  // ... existing logic ...

  // Card and CardHeader always persist
  return (
    <Card className={className} noPadding>
      <div className="p-4 pb-0">
        <CardHeader title="By Strategy" />
      </div>
      <div className={`transition-opacity duration-150 ${isTransitioning ? 'opacity-50' : 'opacity-100'}`}>
        {data.length === 0 ? (
          <div className="text-center py-6 text-argus-text-dim text-sm p-4">
            No strategy data available
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={data}
            keyExtractor={(row) => row.strategyId}
            emptyMessage="No strategy data"
          />
        )}
      </div>
    </Card>
  );
}
```

## Behavior Summary

After these changes, the period-change experience should be:
1. User clicks "Week" on period selector
2. All containers, headers, labels remain perfectly stable — zero layout shift
3. Data values (numbers, chart contents, table rows) dim to ~50% opacity for ~150ms while fetching
4. New data arrives → opacity snaps back to 100% with fresh values
5. No stagger replay, no container flash, no skeleton

The initial page load (first navigation to Performance) still shows the full skeleton → stagger entry animation, because `hasHadData.current` is false and there's no cached data.

## Testing Checklist

1. [ ] `npm run build` — zero TypeScript errors
2. [ ] `npm run lint` — clean
3. [ ] Dashboard: bottom row (Recent Trades, System Status) staggers left-to-right
4. [ ] Trades: toggle outcome filter — crossfade is fast and subtle (~300ms total)
5. [ ] Performance: first load — shows skeleton, then stagger entry animation (unchanged)
6. [ ] Performance: change period — containers/headers/labels stay perfectly stable, only values dim briefly
7. [ ] Performance: change period — charts update data without remounting
8. [ ] Performance: change period — no stagger animation replay
9. [ ] Performance: navigate away while on "Week" — no data flash during exit

## Files Modified (expected)
- `src/utils/motion.ts` — add `quickFade` variant
- `src/pages/DashboardPage.tsx` — bottom row stagger
- `src/pages/TradesPage.tsx` — swap `fadeIn` → `quickFade`
- `src/pages/PerformancePage.tsx` — `keepPreviousData`, `isFetching`, `hasHadData` ref, remove full-unmount skeleton
- `src/hooks/usePerformance.ts` — add `placeholderData: keepPreviousData`
- `src/features/performance/MetricsGrid.tsx` — remove Framer Motion, add CSS opacity transition
- `src/features/performance/EquityCurve.tsx` — stable Card wrapper, `isTransitioning` prop
- `src/features/performance/DailyPnlChart.tsx` — stable Card wrapper, `isTransitioning` prop
- `src/features/performance/StrategyBreakdown.tsx` — stable Card wrapper, `isTransitioning` prop
