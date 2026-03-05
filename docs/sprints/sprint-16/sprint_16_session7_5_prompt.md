# Sprint 16 — Review B Fixes (Session 7.5)

## Context
Sprint 16 UX Polish (Sessions 1–7) passed code review. This session addresses all bugs and improvements identified in the review. These are surgical fixes — no new features, no new files unless noted.

## Fixes (8 items)

---

### Fix 1: AnimatedNumber — Remove Redundant Sync Effect

**File:** `argus/ui/src/components/AnimatedNumber.tsx`

**Problem:** The `currentValueRef` is synced to `displayValue` via a separate `useEffect`, which creates a one-render-late ref update. The ref can be updated directly where `setDisplayValue` is called.

**Change:**
- Remove the sync effect (`useEffect(() => { currentValueRef.current = displayValue; }, [displayValue]);`)
- Update `currentValueRef.current` directly alongside every `setDisplayValue()` call inside the animation loop
- In the `animate` function, after computing `current`, set both: `currentValueRef.current = current; setDisplayValue(current);`
- Same for the final exact-value set at the end: `currentValueRef.current = value; setDisplayValue(value);`

---

### Fix 2: Holiday Handling in marketTime.ts (Algorithmic)

**File:** `argus/ui/src/utils/marketTime.ts`

**Problem:** No US market holiday awareness. On Christmas Day (a weekday), the system says "Pre-market — market opens in Xh" even though markets are closed.

**Implementation — algorithmic holiday generation (no hardcoded dates, works for any year):**

Add a `getMarketHolidays(year: number): Set<string>` function that computes NYSE observed holidays using fixed rules. Returns a Set of `"YYYY-MM-DD"` strings for fast lookup.

**NYSE holiday rules:**
1. **New Year's Day:** Jan 1 (weekend → observed per standard rules)
2. **MLK Day:** Third Monday of January
3. **Presidents' Day:** Third Monday of February
4. **Good Friday:** Friday before Easter Sunday (Easter computed algorithmically)
5. **Memorial Day:** Last Monday of May
6. **Juneteenth:** June 19 (weekend → observed)
7. **Independence Day:** July 4 (weekend → observed)
8. **Labor Day:** First Monday of September
9. **Thanksgiving:** Fourth Thursday of November
10. **Christmas:** Dec 25 (weekend → observed)

**Weekend-observed rule (NYSE standard):** If a fixed-date holiday falls on Saturday, it's observed the prior Friday. If it falls on Sunday, it's observed the following Monday.

**Helper functions to implement:**

```typescript
/** 
 * Compute Easter Sunday for a given year using the Anonymous Gregorian algorithm.
 * Returns [month (1-indexed), day].
 */
function computeEasterSunday(year: number): [number, number] {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return [month, day];
}

/** Get the Nth occurrence of a weekday in a given month/year. weekday: 0=Sun, 1=Mon, ... */
function nthWeekday(year: number, month: number, weekday: number, n: number): number {
  const firstDay = new Date(year, month - 1, 1).getDay();
  let day = 1 + ((weekday - firstDay + 7) % 7) + (n - 1) * 7;
  return day;
}

/** Get the last occurrence of a weekday in a given month/year. */
function lastWeekday(year: number, month: number, weekday: number): number {
  const lastDate = new Date(year, month, 0).getDate(); // last day of month
  const lastDay = new Date(year, month - 1, lastDate).getDay();
  const diff = (lastDay - weekday + 7) % 7;
  return lastDate - diff;
}

/** Apply NYSE weekend-observed rule to a fixed-date holiday. */
function observedDate(year: number, month: number, day: number): string {
  const date = new Date(year, month - 1, day);
  const dow = date.getDay();
  if (dow === 6) {
    // Saturday → observed Friday
    return formatHolidayDate(year, month, day - 1);
  }
  if (dow === 0) {
    // Sunday → observed Monday
    return formatHolidayDate(year, month, day + 1);
  }
  return formatHolidayDate(year, month, day);
}

function formatHolidayDate(year: number, month: number, day: number): string {
  // Handle month overflow (e.g., Jan 0 → Dec 31)
  const d = new Date(year, month - 1, day);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
```

**Main function:**

```typescript
// Cache holidays per year to avoid recomputation
const holidayCache = new Map<number, Set<string>>();

function getMarketHolidays(year: number): Set<string> {
  if (holidayCache.has(year)) return holidayCache.get(year)!;
  
  const holidays = new Set<string>();
  
  // Fixed-date holidays (with weekend-observed rule)
  holidays.add(observedDate(year, 1, 1));   // New Year's Day
  holidays.add(observedDate(year, 6, 19));  // Juneteenth
  holidays.add(observedDate(year, 7, 4));   // Independence Day
  holidays.add(observedDate(year, 12, 25)); // Christmas
  
  // Nth-weekday holidays (always land on the correct day, no observed rule needed)
  const mlk = nthWeekday(year, 1, 1, 3);        // 3rd Monday of Jan
  holidays.add(formatHolidayDate(year, 1, mlk));
  
  const presidents = nthWeekday(year, 2, 1, 3);  // 3rd Monday of Feb
  holidays.add(formatHolidayDate(year, 2, presidents));
  
  const memorial = lastWeekday(year, 5, 1);       // Last Monday of May
  holidays.add(formatHolidayDate(year, 5, memorial));
  
  const labor = nthWeekday(year, 9, 1, 1);        // 1st Monday of Sep
  holidays.add(formatHolidayDate(year, 9, labor));
  
  const thanksgiving = nthWeekday(year, 11, 4, 4); // 4th Thursday of Nov
  holidays.add(formatHolidayDate(year, 11, thanksgiving));
  
  // Good Friday = 2 days before Easter Sunday
  const [easterMonth, easterDay] = computeEasterSunday(year);
  const goodFriday = new Date(year, easterMonth - 1, easterDay - 2);
  holidays.add(formatHolidayDate(goodFriday.getFullYear(), goodFriday.getMonth() + 1, goodFriday.getDate()));
  
  holidayCache.set(year, holidays);
  return holidays;
}
```

**Add a public function:**

```typescript
function isMarketHoliday(etNow: Date): boolean {
  const year = etNow.getFullYear();
  const month = etNow.getMonth() + 1;
  const day = etNow.getDate();
  const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  return getMarketHolidays(year).has(dateStr);
}
```

**Update `getMarketContext()`:** Add a holiday check right after the weekend check:

```typescript
// Weekend check (existing)
if (day === 0 || day === 6) { ... }

// Holiday check (new — add right after weekend check)
if (isMarketHoliday(etNow)) {
  const nextDay = getNextTradingDay(etNow);
  return {
    status: 'closed',
    message: `Market closed (holiday) — next session: ${nextDay} 9:30 AM ET`,
  };
}
```

**Update `getNextSessionDay()`** → rename to `getNextTradingDay()` and make it skip both weekends and holidays. Check the next 7 calendar days (covers worst case of Friday holiday + weekend + Monday holiday):

```typescript
function getNextTradingDay(etNow: Date): string {
  const d = new Date(etNow);
  const hour = d.getHours();
  const minute = d.getMinutes();
  
  // If before market open today AND today is a trading day, next session is today
  const beforeOpen = hour < MARKET_OPEN_HOUR || (hour === MARKET_OPEN_HOUR && minute < MARKET_OPEN_MINUTE);
  if (beforeOpen && d.getDay() >= 1 && d.getDay() <= 5 && !isMarketHoliday(d)) {
    return 'today';
  }
  
  // Check next 7 days
  for (let i = 1; i <= 7; i++) {
    const next = new Date(d);
    next.setDate(next.getDate() + i);
    const dow = next.getDay();
    if (dow >= 1 && dow <= 5 && !isMarketHoliday(next)) {
      return i === 1 ? 'tomorrow' : next.toLocaleDateString('en-US', { weekday: 'long' });
    }
  }
  
  return 'next week';  // fallback (should never happen)
}
```

**Add a comment at the top of the holiday section:**
```typescript
// NYSE market holidays — computed algorithmically from fixed rules.
// Covers all years. No manual updates needed.
// Source: NYSE Rule 7.2 — Regular Holidays
// Note: Does not handle early closes (day before Independence Day, 
// day after Thanksgiving, Christmas Eve) — these are half days, not closures.
```

---

### Fix 3: Client-Side Equity Calculation from WebSocket

**Problem:** Account equity is REST-polled every 5 seconds. When WebSocket position price updates arrive, we can compute equity client-side for instant updates between polls.

**Approach:** The live store already receives `price.update` events via WebSocket. We can track a `positionValues` map and compute equity as `cash + sum(position market values)`.

**Files to modify:**
- `argus/ui/src/stores/live.ts` — Add computed equity tracking
- `argus/ui/src/features/dashboard/AccountSummary.tsx` — Use live equity when available
- `argus/ui/src/features/dashboard/DailyPnlCard.tsx` — Use live daily P&L when available

**Implementation details for `live.ts`:**
- Add to the store state:
  - `liveEquity: number | null` — computed equity (null = no WS data yet, fall back to REST)
  - `liveDailyPnl: number | null` — computed daily P&L (null = fall back to REST)
- When a REST account response arrives (via existing polling), store `baseEquity` (the REST-reported equity) and `baseCash` (REST cash). These are the anchors.
- Actually, simpler approach: the positions endpoint already returns current positions with `current_price` and `quantity`. When a `price.update` WS event arrives for a symbol with an open position, update that position's price. Then compute:
  - `liveEquity = cash + sum(position.quantity * position.current_price for all positions)`
  - `liveDailyPnl = liveEquity - (equity at start of day)` — but we don't have start-of-day equity from the WS.

**Revised simpler approach:** 
- The REST `/account` endpoint returns `equity`, `cash`, `daily_pnl`, and `daily_pnl_pct`.
- The WS `price.update` events include `{symbol, price}` for open position symbols.
- The REST `/positions` endpoint returns positions with `quantity`, `avg_entry_price`, `current_price`, `market_value`, `unrealized_pnl`.
- When a `price.update` arrives, we can update the specific position's `current_price` and `market_value` in the positions cache.
- For equity: `liveEquity = restCash + sum(livePositionMarketValues)`.
- For daily P&L: `liveDailyPnl = restDailyPnl + delta` where delta is the sum of position price changes since the last REST poll.

**Even simpler — just update position-level values and let components derive:**
1. In `live.ts`, add a `priceOverrides: Map<string, number>` that stores the latest WS price per symbol.
2. Components that display positions (OpenPositions) already have the positions data. They can check `priceOverrides.get(symbol)` to use the fresher WS price instead of the REST price.
3. `AccountSummary` can compute: take the REST equity, then for each open position, add `(wsPrice - restPrice) * quantity` as a delta.
4. `DailyPnlCard` similarly: take REST daily_pnl, add the same position delta.

**Implement this approach:**

In `live.ts`:
```typescript
// Add to state
priceOverrides: Record<string, number>;  // symbol → latest WS price

// Add action
updatePrice: (symbol: string, price: number) => void;
clearPriceOverrides: () => void;  // called when REST data refreshes
```

In the WS message handler, when `type === 'price.update'`, call `updatePrice(data.symbol, data.price)`.

Create a new hook `useLiveEquity()` in `argus/ui/src/hooks/useLiveEquity.ts`:
```typescript
export function useLiveEquity() {
  const { data: account } = useAccount();
  const { data: positions } = usePositions();
  const priceOverrides = useLiveStore(state => state.priceOverrides);
  
  if (!account || !positions) return null;
  
  // Compute delta from WS price updates vs REST prices
  let delta = 0;
  for (const pos of positions) {
    const wsPrice = priceOverrides[pos.symbol];
    if (wsPrice !== undefined && pos.current_price) {
      delta += (wsPrice - pos.current_price) * pos.quantity;
    }
  }
  
  return {
    equity: account.equity + delta,
    dailyPnl: account.daily_pnl + delta,
    dailyPnlPct: account.equity > 0 
      ? ((account.daily_pnl + delta) / (account.equity - account.daily_pnl)) * 100 
      : 0,
  };
}
```

In `AccountSummary.tsx`: use `useLiveEquity()` — if it returns non-null, use `liveEquity.equity` for the hero number instead of `data.equity`. Fall back to REST data if null.

In `DailyPnlCard.tsx`: use `useLiveEquity()` — if it returns non-null, use `liveEquity.dailyPnl` and `liveEquity.dailyPnlPct`. Fall back to REST data if null.

In `OpenPositions.tsx`: use `priceOverrides` from live store to override `current_price` per position for the real-time price column.

**Important:** When REST data refreshes (every 5 seconds), clear `priceOverrides` so they don't accumulate stale deltas. Do this by clearing overrides when the account query refetches. The simplest way: in `useAccount`, add an `onSuccess` callback (or `useEffect` on `data`) that calls `clearPriceOverrides()`. Actually cleaner: don't clear — just let the REST data be the baseline each time it arrives. The delta computation always uses the *current* REST price as baseline, so stale overrides just produce zero delta once REST catches up. No clearing needed.

Wait — that's only true if the REST positions data also refreshes. Confirm: `usePositions()` and `useAccount()` both poll at the same interval. If they do, the delta naturally zeros out after each REST refresh. If a WS price update arrives *between* REST polls, the delta is correct. This is self-correcting.

**Test:** In dev mode, the mock WebSocket sends price updates. Verify that the equity number updates between REST polls.

---

### Fix 4: Scroll-to-Top on Navigation

**File:** `argus/ui/src/layouts/AppShell.tsx`

**Problem:** `mainRef.current.scrollTo(0, 0)` doesn't work because `<main>` never actually scrolls — the body/window scrolls instead. The outer `<div>` has `min-h-screen` which lets it grow beyond viewport.

**Fix:** Change the outer wrapper class from `min-h-screen` to `h-dvh` (dynamic viewport height). This constrains the flex container to viewport height, making `<main>` with `flex-1` and `overflow-y-auto` the actual scroll container.

```tsx
// Before:
<div className="flex min-h-screen bg-argus-bg">

// After:
<div className="flex h-dvh bg-argus-bg overflow-hidden">
```

The `overflow-hidden` on the outer prevents any body scroll from leaking through.

**Verify:** After this change, navigate between pages and confirm:
1. Long pages scroll within `<main>`, not the body
2. Navigating to a new page scrolls to top
3. The sidebar and mobile nav remain fixed (they already use `fixed` positioning)
4. Content doesn't get clipped at the bottom on mobile (account for `pb-24` on main for mobile nav space)

---

### Fix 5: Smooth Chart Draw-In with Point Interpolation

**File:** `argus/ui/src/utils/chartAnimation.ts`

**Problem:** Current animation reveals data points in integer steps (1, 2, 3...), causing visible "staircase" jumps between data points.

**Fix:** Interpolate a partial point at the drawing edge so the line extends smoothly between data points.

Replace the current `step()` function body with:

```typescript
function step(): void {
  const elapsed = performance.now() - startTime;
  const progress = Math.min(elapsed / durationMs, 1);
  const easedProgress = 1 - Math.pow(1 - progress, 3);

  // Calculate continuous position in the data array
  const continuousIndex = easedProgress * (data.length - 1);
  const wholeIndex = Math.floor(continuousIndex);
  const fraction = continuousIndex - wholeIndex;

  // Include all complete data points up to wholeIndex
  const visibleData = data.slice(0, wholeIndex + 1);

  // Add interpolated point between current and next data point
  if (wholeIndex < data.length - 1 && fraction > 0) {
    const current = data[wholeIndex];
    const next = data[wholeIndex + 1];
    
    // Interpolate the value (works for both AreaData and HistogramData)
    const interpolatedValue = (current as any).value + 
      ((next as any).value - (current as any).value) * fraction;
    
    visibleData.push({
      ...next,  // Use next point's time slot so chart doesn't create duplicate x
      value: interpolatedValue,
    } as any);
  }

  series.setData(visibleData);

  if (progress < 1) {
    requestAnimationFrame(step);
  } else {
    // Ensure final frame shows exact data
    series.setData(data);
  }
}
```

Note: For histogram (bar) charts, interpolation between bars doesn't make visual sense — a half-height bar at the edge would look odd. The interpolation primarily benefits line/area charts. Add a parameter to control this:

```typescript
export function animateChartDrawIn<T extends SeriesType>(
  series: ISeriesApi<T>,
  data: SeriesDataItemTypeMap[T][],
  chart: IChartApi,
  durationMs = 800,
  interpolate = true  // Set to false for histogram series
): void {
```

Then in the `step()` function, only add the interpolated point if `interpolate` is true. Otherwise, just use the integer slice like before.

**Update callers:**
- `EquityCurve.tsx`: `animateChartDrawIn(series, data, chart)` — default `interpolate=true` ✓
- `DailyPnlChart.tsx`: `animateChartDrawIn(series, data, chart, 800, false)` — disable interpolation for histogram

---

### Fix 6: useResponsiveHeight — React to Window Resizes

**Files:** 
- `argus/ui/src/features/performance/EquityCurve.tsx`
- `argus/ui/src/features/performance/DailyPnlChart.tsx`

**Problem:** `useResponsiveHeight()` reads `window.innerWidth` at render time but doesn't subscribe to resize events. iPad rotation won't update chart heights.

**Fix:** Replace the inline `useResponsiveHeight` function in both files with a version that uses the existing `useMediaQuery` hook:

```typescript
import { useMediaQuery } from '../../hooks/useMediaQuery';

function useResponsiveHeight(desktop: number, tablet: number, mobile: number): number {
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const isTablet = useMediaQuery('(min-width: 640px)');
  if (isDesktop) return desktop;
  if (isTablet) return tablet;
  return mobile;
}
```

Usage in EquityCurve: `const chartHeight = useResponsiveHeight(300, 220, 180);`
Usage in DailyPnlChart: `const chartHeight = useResponsiveHeight(250, 200, 160);`

Since `useMediaQuery` uses `useSyncExternalStore` with a `matchMedia` listener, this will properly react to viewport changes.

You can extract `useResponsiveHeight` to a shared location (e.g., `hooks/useMediaQuery.ts`) or keep it local in each file. Shared is cleaner since both charts use the same pattern.

---

### Fix 7: EventsLog — Nested Button Fix

**File:** `argus/ui/src/features/system/EventsLog.tsx`

**Problem:** Line 158 has a `<motion.button>` (clear button) nested inside a `<button>` (collapsible header). Nested interactive elements are invalid HTML.

**Fix:** Change the outer `<button>` to a `<div>` with appropriate ARIA attributes:

```tsx
// Before (line 131):
<button
  onClick={() => setIsExpanded(!isExpanded)}
  className="w-full flex items-center justify-between p-4 h-[60px] hover:bg-argus-surface-2 transition-colors"
>

// After:
<div
  role="button"
  tabIndex={0}
  onClick={() => setIsExpanded(!isExpanded)}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setIsExpanded(!isExpanded); } }}
  className="w-full flex items-center justify-between p-4 h-[60px] hover:bg-argus-surface-2 transition-colors cursor-pointer"
>
```

And change the matching closing tag from `</button>` to `</div>`.

The inner `<motion.button>` for Clear remains a proper `<button>`. The `e.stopPropagation()` already prevents it from toggling the expand state.

---

### Fix 8: Sparkline — Responsive Width

**File:** `argus/ui/src/components/Sparkline.tsx`

**Problem:** SVG width is hardcoded (default 200px). While CSS `w-full` stretches it, the internal coordinate math is based on the fixed width, and callers have to pass a magic number.

**Fix:** Make the Sparkline automatically fill its container width using a `ResizeObserver`.

```typescript
import { useMemo, useRef, useState, useEffect } from 'react';

// Inside the component, before the useMemo:
const containerRef = useRef<HTMLDivElement>(null);
const [measuredWidth, setMeasuredWidth] = useState(width);

useEffect(() => {
  const el = containerRef.current;
  if (!el) return;
  
  const observer = new ResizeObserver((entries) => {
    const entry = entries[0];
    if (entry) {
      setMeasuredWidth(Math.round(entry.contentRect.width));
    }
  });
  observer.observe(el);
  return () => observer.disconnect();
}, []);
```

Use `measuredWidth` instead of `width` in the `useMemo` dependency array and calculations. Wrap the SVG in the measured container div:

```tsx
return (
  <div ref={containerRef} className={className} style={{ width: '100%' }}>
    <svg
      width={measuredWidth}
      height={height}
      viewBox={`0 0 ${measuredWidth} ${height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      ...
    </svg>
  </div>
);
```

Remove `className` from the `<svg>` element (it's now on the wrapper div). Remove `preserveAspectRatio="none"` since the SVG now matches its container width exactly — no stretching needed.

**Update callers** in `AccountSummary.tsx` and `DailyPnlCard.tsx`: remove the `width={200}` and `className="w-full"` props. Just use:
```tsx
<Sparkline data={equityTrend} height={32} color="var(--color-argus-accent)" fillOpacity={0.15} />
```

The Sparkline will auto-measure its container width.

---

### Fix 9: Vertical Stagger on Phone (Bonus — flagged as broken in review)

**File:** `argus/ui/src/pages/DashboardPage.tsx`

**Problem:** On single-column (phone), cards in grid groups stagger simultaneously with sibling groups, creating overlapping animations instead of clean top-to-bottom flow.

**Fix:** In single-column mode, render all cards as direct children of one stagger container without intermediate grid wrappers:

```tsx
export function DashboardPage() {
  const isMultiColumn = useIsMultiColumn();

  if (!isMultiColumn) {
    // Phone: flat vertical stagger, all cards as direct children
    return (
      <motion.div
        className="space-y-4"
        variants={staggerContainer(0.08)}
        initial="hidden"
        animate="show"
      >
        <motion.div variants={staggerItem}><AccountSummary /></motion.div>
        <motion.div variants={staggerItem}><DailyPnlCard /></motion.div>
        <motion.div variants={staggerItem}><MarketStatusBadge /></motion.div>
        <motion.div variants={staggerItem}><OpenPositions /></motion.div>
        <motion.div variants={staggerItem}><RecentTrades /></motion.div>
        <motion.div variants={staggerItem}><HealthMini /></motion.div>
      </motion.div>
    );
  }

  // Tablet/Desktop: grid layout with grouped stagger (existing code)
  return (
    <motion.div
      className="space-y-4 md:space-y-5 lg:space-y-6"
      variants={staggerContainer(0.08)}
      initial="hidden"
      animate="show"
    >
      {/* Top row: 2-col tablet, 3-col desktop */}
      <motion.div
        className="grid grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItemWithChildren(0.08)}
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

      {/* Open positions - full width */}
      <motion.div variants={staggerItem}>
        <OpenPositions />
      </motion.div>

      {/* Bottom row: 2-col */}
      <motion.div
        className="grid grid-cols-2 gap-4 md:gap-5 lg:gap-6"
        variants={staggerItemWithChildren(0.08)}
      >
        <motion.div variants={staggerItem}>
          <RecentTrades />
        </motion.div>
        <motion.div variants={staggerItem}>
          <HealthMini />
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
```

Import `staggerItemWithChildren` from `../../utils/motion` (it already exists). The `staggerItemResponsive` function is no longer needed and can be removed from `motion.ts` if nothing else uses it.

---

## Verification Checklist

After all fixes, verify:
- [ ] `npm run build` passes with zero errors
- [ ] `npm run lint` passes clean (or only pre-existing warnings)
- [ ] Dashboard loads correctly at all 3 breakpoints
- [ ] AnimatedNumber transitions smoothly on value change (check equity and daily P&L)
- [ ] Sparklines render at full container width (no hardcoded 200px)
- [ ] Equity curve draws in with smooth line animation (not staircase)
- [ ] P&L histogram draws in without interpolation (integer bar reveal)
- [ ] Navigating between pages scrolls to top
- [ ] Phone layout staggers cards top-to-bottom sequentially
- [ ] Rotating iPad updates chart heights
- [ ] EventsLog expand/collapse works, clear button works, no HTML validation errors
- [ ] Holiday check: temporarily set a test date to Dec 25, 2026 and verify "Market closed (holiday)" message. Also verify Jul 4, 2026 (Saturday) shows observed Friday Jul 3 as holiday. Verify Good Friday 2026 (Apr 3) is detected. Verify a normal Tuesday is NOT flagged as holiday.
- [ ] WS price updates cause equity/P&L to update between REST polls (test in dev mode)

## Notes
- This is a fix-only session. No new components, no new pages.
- All existing tests should continue to pass (these are frontend-only changes, 926 backend tests unaffected).
- Commit message: `ui: sprint 16 review B fixes — 9 items`
