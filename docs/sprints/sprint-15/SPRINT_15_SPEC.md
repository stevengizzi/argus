# Sprint 15 — Command Center: Core Dashboard Views

> Implementation Spec for Claude Code
> Designed: Feb 23, 2026 | Target: ~8 sessions

---

## Overview

Build the Command Center frontend: four pages (Dashboard, Trades, Performance, System) with real-time WebSocket integration, responsive mobile-first design, and production-grade visual polish. Single React codebase targeting phone (375px), tablet (768px), and desktop (1024px+).

**Dev server:** `python -m argus.api --dev` (password: "argus") provides mock data. Frontend dev is independent of the trading engine.

**Key constraint:** This is a single-user operator's tool. Dark theme. High information density. Financial data formatted precisely. Real-time P&L updates must feel alive without being jarring.

**Chart libraries (DEC-104):** Two libraries — TradingView Lightweight Charts for all financial time-series (equity curve, daily P&L histogram, and future price charts), Recharts for non-time-series visualizations (metric sparklines, distributions, heatmaps in Sprint 21+). Each library does what it's best at.

**Responsive breakpoints (DEC-105):** Three breakpoints targeting iPhone 16 Pro (393px), iPad Pro 11" (834px portrait / 1194px landscape), MacBook Pro 16" (1512px). `<640px` phone layout, `640–1023px` tablet layout, `≥1024px` desktop layout.

---

## Session 1: Foundation & Layout Shell

### 1.1 Expanded Color Tokens

Update `src/index.css` to extend the theme:

```css
@import "tailwindcss";

@theme {
  /* Base palette (existing) */
  --color-argus-bg: #0f1117;
  --color-argus-surface: #1a1d27;
  --color-argus-border: #2a2d3a;
  --color-argus-text: #e1e4eb;
  --color-argus-text-dim: #8b8fa3;
  --color-argus-accent: #3b82f6;

  /* Financial states */
  --color-argus-profit: #22c55e;
  --color-argus-profit-dim: rgba(34, 197, 94, 0.15);
  --color-argus-loss: #ef4444;
  --color-argus-loss-dim: rgba(239, 68, 68, 0.15);
  --color-argus-warning: #f59e0b;
  --color-argus-warning-dim: rgba(245, 158, 11, 0.15);

  /* Surface hierarchy */
  --color-argus-surface-2: #1f2231;
  --color-argus-surface-3: #252838;

  /* Chart palette */
  --color-argus-chart-1: #3b82f6;
  --color-argus-chart-2: #8b5cf6;
  --color-argus-chart-3: #06b6d4;
  --color-argus-chart-4: #f59e0b;
  --color-argus-chart-5: #ec4899;
  --color-argus-chart-6: #10b981;
}

/* Custom animations */
@keyframes pnl-flash-profit {
  0% { background-color: rgba(34, 197, 94, 0.3); }
  100% { background-color: transparent; }
}
@keyframes pnl-flash-loss {
  0% { background-color: rgba(239, 68, 68, 0.3); }
  100% { background-color: transparent; }
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
@keyframes slide-in-top {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

body {
  @apply bg-argus-bg text-argus-text;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
  margin: 0;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

#root {
  min-height: 100vh;
}

/* Utility classes for financial data */
.tabular-nums {
  font-variant-numeric: tabular-nums;
}
.flash-profit {
  animation: pnl-flash-profit 600ms ease-out;
}
.flash-loss {
  animation: pnl-flash-loss 600ms ease-out;
}
.pulse {
  animation: pulse-dot 2s ease-in-out infinite;
}
.slide-in {
  animation: slide-in-top 300ms ease-out;
}
```

### 1.2 Number Formatting Utilities

Create `src/utils/format.ts`:

```typescript
/**
 * Consistent number formatting for financial data.
 * All money values use USD. All percentages show 1-2 decimal places.
 */

const currencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactCurrencyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const decimalFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** Format as currency: $1,234.56 */
export function formatCurrency(value: number): string {
  return currencyFormatter.format(value);
}

/** Format as compact currency (no cents): $1,235 */
export function formatCurrencyCompact(value: number): string {
  return compactCurrencyFormatter.format(value);
}

/** Format as percentage from decimal: 0.125 → 12.5% */
export function formatPercent(value: number): string {
  return percentFormatter.format(value);
}

/** Format as percentage from already-percentage value: 12.5 → 12.5% */
export function formatPercentRaw(value: number): string {
  return `${decimalFormatter.format(value)}%`;
}

/** Format P&L with sign and color class name */
export function formatPnl(value: number): { text: string; className: string } {
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${currencyFormatter.format(value)}`,
    className: value > 0 ? 'text-argus-profit' : value < 0 ? 'text-argus-loss' : 'text-argus-text-dim',
  };
}

/** Format P&L percentage with sign and color */
export function formatPnlPercent(value: number): { text: string; className: string } {
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${decimalFormatter.format(value)}%`,
    className: value > 0 ? 'text-argus-profit' : value < 0 ? 'text-argus-loss' : 'text-argus-text-dim',
  };
}

/** Format R-multiple: 1.5 → +1.50R */
export function formatR(value: number): { text: string; className: string } {
  const sign = value >= 0 ? '+' : '';
  return {
    text: `${sign}${decimalFormatter.format(value)}R`,
    className: value > 0 ? 'text-argus-profit' : value < 0 ? 'text-argus-loss' : 'text-argus-text-dim',
  };
}

/** Format duration from seconds: 3725 → "1h 2m" */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainMinutes = minutes % 60;
  return remainMinutes > 0 ? `${hours}h ${remainMinutes}m` : `${hours}h`;
}

/** Format timestamp to ET time: "9:45:32 AM" */
export function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    timeZone: 'America/New_York',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  });
}

/** Format timestamp to ET date: "Feb 23" */
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
  });
}

/** Format timestamp to full ET: "Feb 23, 9:45 AM" */
export function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/** Format price with appropriate decimal places */
export function formatPrice(value: number): string {
  return decimalFormatter.format(value);
}

/** Format large numbers compactly: 1234567 → "1.23M" */
export function formatCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return decimalFormatter.format(value);
}
```

### 1.3 App Shell Layout

Create `src/layouts/AppShell.tsx`:
- Desktop ≥1024px (`lg:`): Icon sidebar (w-16, 64px) pinned left + main content area
- Tablet 640–1023px (`md:`): Bottom tab bar (same as phone but with more room for labels)
- Phone <640px: Bottom tab bar (h-16, fixed) with icon-only items
- The sidebar/tabs show: 4 nav items (Dashboard, Trades, Performance, System), system status dot, and logout
- Use `NavLink` from react-router for active state styling (active item gets `bg-argus-surface-2` and `text-argus-accent` icon color)
- Main content area has `overflow-y-auto` and `p-4 md:p-5 lg:p-6` padding
- Bottom tab bar uses `pb-[env(safe-area-inset-bottom)]` for iPhone safe area

Create `src/layouts/Sidebar.tsx`:
- Icon-only sidebar on desktop (64px wide, visible at `lg:` breakpoint ≥1024px)
- Each item: icon (lucide-react) + tooltip on hover
- Icons: `LayoutDashboard` (Dashboard), `ScrollText` (Trades), `TrendingUp` (Performance), `Activity` (System)
- Bottom section: status dot (green/amber/red based on health), logout button
- Paper mode badge visible (amber "PAPER" text)
- ARGUS logo mark at top (just the "A" or a small icon, not full wordmark)

Create `src/layouts/MobileNav.tsx`:
- Fixed bottom bar, visible below `lg:` breakpoint (<1024px)
- 4 tab items with icons + short labels (enough room on iPad at 834px)
- Active item highlighted with accent color
- Safe area padding for iPhone notch (`pb-[env(safe-area-inset-bottom)]`)
- Status dot integrated into the System tab icon (small indicator overlay)

### 1.4 Router Restructure

Update `App.tsx`:
```tsx
<BrowserRouter>
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
      <Route index element={<DashboardPage />} />
      <Route path="trades" element={<TradesPage />} />
      <Route path="performance" element={<PerformancePage />} />
      <Route path="system" element={<SystemPage />} />
      <Route path="dev/connection" element={<ConnectionTest />} />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
</BrowserRouter>
```

### 1.5 TanStack Query Provider

Wrap the app with `QueryClientProvider` in `main.tsx`. Configure with:
- `staleTime: 10_000` (10 seconds default)
- `retry: 1` (one retry on failure)
- `refetchOnWindowFocus: true`

### 1.6 Install Lightweight Charts

```bash
cd argus/ui && npm install lightweight-charts
```

Verify it's added to `package.json` dependencies. No additional config needed — it's a pure JS library with TypeScript types included.

### Gate Check (Session 1)
- [ ] Navigation works between all 4 pages (placeholder content OK)
- [ ] Desktop (≥1024px): icon sidebar visible, content area fills remaining width
- [ ] Tablet (640–1023px): bottom tab bar with labels, no sidebar
- [ ] Phone (<640px): bottom tab bar with icons, safe area padding works
- [ ] Active nav item highlighted
- [ ] Login flow still works
- [ ] Paper mode badge visible
- [ ] `npm run build` passes (zero TypeScript errors)

---

## Session 2: Shared Components

### 2.1 Component Library (`src/components/`)

**Card.tsx** — Base container component:
```tsx
interface CardProps {
  children: React.ReactNode;
  className?: string;
  noPadding?: boolean;
}
```
- `bg-argus-surface border border-argus-border rounded-lg`
- Default `p-4` padding, removable via `noPadding`

**CardHeader.tsx** — Section label:
```tsx
interface CardHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode; // For buttons/links in header
}
```
- Title: `text-sm font-medium uppercase tracking-wider text-argus-text-dim`
- This is the Bloomberg-style section label

**StatusDot.tsx** — Health indicator:
```tsx
interface StatusDotProps {
  status: 'healthy' | 'degraded' | 'error' | 'unknown';
  pulse?: boolean; // For heartbeat pulse
  size?: 'sm' | 'md';
}
```
- Colors: healthy=green, degraded=amber, error=red, unknown=gray
- `pulse` adds the `pulse` CSS animation class
- sm=6px, md=8px

**PnlValue.tsx** — P&L display with color and optional flash:
```tsx
interface PnlValueProps {
  value: number;
  format?: 'currency' | 'percent' | 'r-multiple';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  flash?: boolean; // Trigger flash animation on value change
}
```
- Uses `formatPnl`, `formatPnlPercent`, or `formatR` from utils
- `tabular-nums` always applied
- If `flash` is true, applies `flash-profit` or `flash-loss` class when value changes (use a ref to track previous value, apply class on change, remove after animation)
- Size maps: sm=`text-sm`, md=`text-base`, lg=`text-xl`, xl=`text-3xl`

**MetricCard.tsx** — Small stat card:
```tsx
interface MetricCardProps {
  label: string;
  value: string;
  subValue?: string;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}
```
- Label on top (dim, xs), value centered (medium/bold, tabular-nums), optional sub-value below
- Compact: designed for grid layouts of 2-3 across on mobile, 4-6 on desktop

**Badge.tsx** — Status badges:
```tsx
interface BadgeProps {
  children: React.ReactNode;
  variant: 'info' | 'success' | 'warning' | 'danger' | 'neutral';
}
```
- Small pill shape: `px-2 py-0.5 rounded-full text-xs font-medium`
- Variant colors with subtle background (e.g., warning = amber text on amber-dim bg)

**DataTable.tsx** — Reusable table:
```tsx
interface Column<T> {
  key: string;
  header: string;
  render: (item: T) => React.ReactNode;
  align?: 'left' | 'right' | 'center';
  className?: string;
  hideBelow?: 'sm' | 'md' | 'lg'; // Hidden below this breakpoint
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
}
```
- Styled with argus theme: header row in `bg-argus-surface-2`, body rows with `hover:bg-argus-bg/50`
- `hideBelow` columns use Tailwind responsive classes (e.g., `hideBelow: 'md'` → `hidden md:table-cell`)
- Sticky header on scroll
- `tabular-nums` on all number cells

**LoadingState.tsx** — Loading placeholder:
- Subtle skeleton animation or a simple "Loading..." with a spinner
- Should look intentional, not broken

**EmptyState.tsx** — No data placeholder:
- Icon + message + optional action
- e.g., "No trades yet" with a calming icon

### Gate Check (Session 2)
- [ ] All components render correctly in isolation (test on a temp page)
- [ ] PnlValue shows correct colors for positive/negative
- [ ] DataTable handles 0, 1, and 20+ rows
- [ ] Mobile hiding works on DataTable columns at all 3 breakpoints
- [ ] `npm run build` passes

---

## Session 3: Data Layer (TanStack Query Hooks + Enhanced WebSocket)

### 3.1 Query Hooks (`src/hooks/`)

Create hooks wrapping each API call:

**useAccount.ts:**
- `queryKey: ['account']`
- `refetchInterval: 10_000` (10s)

**usePositions.ts:**
- `queryKey: ['positions']`
- `refetchInterval: 5_000` (5s)
- Optional `strategy_id` filter

**useTrades.ts:**
- `queryKey: ['trades', params]`
- `refetchInterval: 30_000` (30s)
- Accepts filter params (strategy_id, date_from, date_to, outcome, limit, offset)

**usePerformance.ts:**
- `queryKey: ['performance', period]`
- `refetchInterval: 30_000` (30s)
- Parameter: `period` ('today' | 'week' | 'month' | 'all')

**useHealth.ts:**
- `queryKey: ['health']`
- `refetchInterval: 15_000` (15s)

**useStrategies.ts:**
- `queryKey: ['strategies']`
- `refetchInterval: 30_000` (30s)

### 3.2 Enhanced Live Store (`src/stores/live.ts`)

Extend the live store to:
1. Parse WebSocket messages by type and maintain typed state
2. Track position price updates: `priceUpdates: Record<string, { price: number; volume: number; timestamp: string }>`
3. Track last heartbeat: `lastHeartbeat: string | null`
4. Track recent events (keep existing array, cap at 50)
5. **Invalidate React Query cache** when relevant events arrive:
   - `position.opened` → invalidate `['positions']`, `['account']`
   - `position.closed` → invalidate `['positions']`, `['account']`, `['trades']`, `['performance', 'today']`
   - `order.filled` → invalidate `['positions']`, `['account']`
   - `system.circuit_breaker` → invalidate `['health']`

To do cache invalidation, the store needs access to the QueryClient. Approach: export a `setQueryClient(client)` function from the store, called once in `App.tsx` after QueryClient is created. When events arrive, call `queryClient.invalidateQueries()`.

### 3.3 WebSocket Auto-Connect

When the user logs in (auth store transitions to `isAuthenticated: true`), automatically connect the WebSocket. When they log out, disconnect. Hook this up in `AppShell.tsx`:

```tsx
useEffect(() => {
  connect();
  return () => disconnect();
}, [connect, disconnect]);
```

### Gate Check (Session 3)
- [ ] All hooks return loading/error/data states correctly
- [ ] Data refreshes on interval
- [ ] WebSocket connects after login
- [ ] Price updates from WS appear in live store
- [ ] Query invalidation works (position.closed triggers trade list refresh)
- [ ] `npm run build` passes

---

## Session 4: Dashboard Page

The command post. This is the most important page — it's what you'll see 90% of the time during trading sessions.

### Layout (Desktop ≥1024px)
```
┌──────────────────────────────────────────────────┐
│ ACCOUNT EQUITY    │ DAILY P&L        │ MARKET    │
│ $100,234.56       │ +$1,234.56       │ ● OPEN    │
│ Cash: $45,678     │ +1.23%           │ 10:45 ET  │
│ BP: $91,234       │ 5 trades today   │ PAPER     │
├──────────────────────────────────────────────────┤
│ OPEN POSITIONS (3)                               │
│ ┌─────┬───────┬────────┬─────────┬──────┬──────┐ │
│ │ SYM │ SIDE  │ ENTRY  │ CURRENT │ P&L  │ R    │ │
│ │ NVDA│ LONG  │ 875.50 │ 886.25  │ +$.. │ +1.2 │ │
│ │ TSLA│ LONG  │ 225.80 │ 226.90  │ +$.. │ +0.3 │ │
│ │ AMD │ LONG  │ 155.25 │ 155.60  │ +$.. │ +0.1 │ │
│ └─────┴───────┴────────┴─────────┴──────┴──────┘ │
├──────────────────────────────────────────────────┤
│ RECENT TRADES (last 8)    │  SYSTEM STATUS       │
│ TSLA +$234.56  T1 9:52    │  ● Broker     OK     │
│ NVDA -$123.45  SL 10:15   │  ● Data       OK     │
│ AAPL +$89.12   T2 10:30   │  ● Orders     OK     │
│ ...                       │  ● Risk       OK     │
│                           │  ● ORB        OK     │
│                           │  Uptime: 4h 23m      │
└──────────────────────────────────────────────────┘
```

### Layout (Tablet 640–1023px — iPad portrait)
```
┌────────────────────────────────────┐
│ ACCOUNT EQUITY   │ DAILY P&L      │
│ $100,234.56      │ +$1,234.56     │
│ Cash: $45,678    │ +1.23% • 5 trd │
│ BP: $91,234      │ ● OPEN  PAPER  │
├────────────────────────────────────┤
│ OPEN POSITIONS (3)                │
│ SYM  ENTRY   CURRENT  P&L    R   │
│ NVDA 875.50  886.25  +$537  +1.2 │
│ TSLA 225.80  226.90  +$165  +0.3 │
│ AMD  155.25  155.60  +$70   +0.1 │
├────────────────────────────────────┤
│ RECENT TRADES     │ SYSTEM STATUS │
│ TSLA +$234 T1     │ ● All OK      │
│ NVDA -$123 SL     │ Uptime: 4h23m │
│ AAPL +$89  T2     │ 5 components  │
├────────────────────────────────────┤
│ [Dashboard] [Trades] [Perf] [Sys] │
└────────────────────────────────────┘
```

### Layout (Phone <640px — stacked)
```
┌──────────────────────┐
│ $100,234.56          │  ← Equity (hero)
│ +$1,234.56 (+1.23%)  │  ← Daily P&L
│ ● OPEN  •  PAPER     │  ← Status badges
├──────────────────────┤
│ OPEN POSITIONS (3)   │
│ NVDA  +$537  +1.2R   │  ← Compact: sym, P&L, R
│ TSLA  +$165  +0.3R   │
│ AMD   +$70   +0.1R   │
├──────────────────────┤
│ RECENT TRADES        │
│ TSLA +$234 T1  9:52  │
│ NVDA -$123 SL 10:15  │
│ AAPL +$89  T2 10:30  │
├──────────────────────┤
│ SYSTEM  ● All OK     │
├──────────────────────┤
│ [Dash] [Trd] [Prf] [Sys] │
└──────────────────────┘
```

### Components

**AccountSummary** (`features/dashboard/AccountSummary.tsx`):
- Uses `useAccount()` hook
- Hero equity number (text-3xl, tabular-nums)
- Cash and buying power below in smaller text
- Uses `formatCurrency` for all values

**DailyPnlCard** (`features/dashboard/DailyPnlCard.tsx`):
- Uses `useAccount()` for daily_pnl and daily_pnl_pct
- Large P&L number with PnlValue component (flash on WS update)
- Trade count below: "5 trades today"

**MarketStatusBadge** (`features/dashboard/MarketStatusBadge.tsx`):
- Shows market_status from account response
- Green dot + "OPEN" during market hours
- Gray dot + "CLOSED" outside hours
- Amber "PAPER" badge if paper_mode from health

**OpenPositionsTable** (`features/dashboard/OpenPositions.tsx`):
- Uses `usePositions()` + live store `priceUpdates` for real-time prices
- Merge logic: if `priceUpdates[symbol]` exists and is newer than REST data, show WS price
- Desktop columns: Symbol, Side, Entry, Current, Unrealized P&L ($), R-Multiple, Hold Time, Stop, T1, T2, T1 Hit
- Tablet columns: Symbol, Entry, Current, P&L ($), R-Multiple, Hold Time
- Phone columns: Symbol, P&L, R-Multiple (3 columns, very compact)
- P&L values use PnlValue with flash enabled
- Row click: future expansion (trade detail view)
- Empty state: "No open positions" with appropriate messaging

**RecentTrades** (`features/dashboard/RecentTrades.tsx`):
- Uses `useTrades({ limit: 8 })` (most recent 8)
- Compact list format, not full table
- Each row: Symbol, P&L, Exit Reason badge, Time
- Link to full trade log at bottom: "View all trades →"

**HealthMini** (`features/dashboard/HealthMini.tsx`):
- Uses `useHealth()`
- Compact list of components with status dots
- Uptime display
- If any component is degraded/error, use warning/error border accent on the card

### Gate Check (Session 4)
- [ ] Dashboard loads with mock data from dev server
- [ ] All metric cards show formatted values
- [ ] Positions table shows 3 mock positions
- [ ] Real-time price updates from WS reflected in position rows
- [ ] P&L flash animation works
- [ ] Mobile layout (iPhone 393px) stacks properly, all data visible
- [ ] Tablet layout (iPad 834px) shows 2-column grid where appropriate
- [ ] Market status and paper mode badges visible
- [ ] `npm run build` passes

---

## Session 5: Trade Log Page

Full trade history with filtering and pagination.

### Layout
```
┌──────────────────────────────────────────────────┐
│ TRADES                                           │
│ ┌────────────────────────────────────────────┐   │
│ │ Strategy: [All ▾]  Outcome: [All ▾]       │   │
│ │ Date: [From] to [To]                      │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ 20 trades  │  Win: 55%  │  Net: +$1,234         │
│                                                  │
│ ┌─────┬──────┬───────┬────────┬──────┬──────┐   │
│ │ DATE│ SYM  │ ENTRY │ EXIT   │ P&L  │ EXIT │   │
│ │ 2/23│ TSLA │ 225.8 │ 229.10 │ +$.. │ T1   │   │
│ │ 2/23│ NVDA │ 875.5 │ 868.00 │ -$.. │ SL   │   │
│ │ ... │      │       │        │      │      │   │
│ └─────┴──────┴───────┴────────┴──────┴──────┘   │
│                                                  │
│ ← Prev  Page 1 of 3  Next →                     │
└──────────────────────────────────────────────────┘
```

### Components

**TradeFilters** (`features/trades/TradeFilters.tsx`):
- Strategy dropdown: populated from `useStrategies()`, includes "All Strategies" option
- Outcome toggle: All / Wins / Losses / Breakeven (button group, not dropdown)
- Date range: simple date inputs (from/to). Default: no filter (all time)
- Filters are URL query params so they persist on refresh
- Compact on mobile: filters stack vertically, use smaller inputs

**TradeStatsBar** (`features/trades/TradeStatsBar.tsx`):
- Shows for the current filtered set: total trades, win rate, net P&L
- Compact horizontal bar with MetricCards
- Updates when filters change

**TradeTable** (`features/trades/TradeTable.tsx`):
- Uses `useTrades()` with filter params from URL
- Desktop columns: Date, Symbol, Side, Entry Price, Exit Price, P&L ($), P&L (R), Shares, Exit Reason, Hold Duration, Commission
- Tablet columns: Date, Symbol, Entry, Exit, P&L ($), R, Exit Reason
- Phone columns: Date/Symbol (combined), P&L, Exit Reason
- Rows colored: subtle green-tinted bg for wins, red-tinted for losses (very subtle, not garish)
- Exit reason as colored badge (T1=green, T2=green, SL=red, TIME=amber, EOD=gray)
- Pagination: limit 20 per page, prev/next buttons, page counter
- Sort: default by date descending (newest first)

### Gate Check (Session 5)
- [ ] Trade table loads with 20 mock trades
- [ ] Filtering by outcome works (wins/losses/breakeven)
- [ ] Strategy filter dropdown populates
- [ ] Pagination works (20 per page)
- [ ] Mobile layout compact and usable at 393px
- [ ] Tablet layout shows additional columns at 834px
- [ ] Row coloring distinguishes wins from losses
- [ ] Exit reason badges colored correctly
- [ ] `npm run build` passes

---

## Session 6: Performance Page

Charts and metrics for analyzing trading performance.

### Lightweight Charts Integration Pattern

Lightweight Charts is imperative (not declarative like Recharts). Create a reusable wrapper:

```typescript
// components/LWChart.tsx — Reusable Lightweight Charts container
// 1. useRef for the container div
// 2. useEffect to create chart on mount, destroy on unmount
// 3. ResizeObserver to handle container resizing → chart.applyOptions({ width })
// 4. Accept chartOptions (merged with lwcDefaultOptions from chartTheme.ts)
// 5. Accept onChartReady callback to let parent add series
// 6. useEffect with data dependency to update series data when props change
```

Key Lightweight Charts API for Sprint 15:
- `createChart(container, options)` — create chart instance
- `chart.addAreaSeries(options)` — for equity curve
- `chart.addHistogramSeries(options)` — for daily P&L bars
- `series.setData(data)` — set/update data points
- `chart.timeScale().fitContent()` — auto-fit visible range
- Data format: `{ time: 'YYYY-MM-DD', value: number }` for area, `{ time: 'YYYY-MM-DD', value: number, color: string }` for histogram

### Layout
```
┌──────────────────────────────────────────────────┐
│ PERFORMANCE                                      │
│ [ Today ] [ Week ] [ Month ] [ All Time ]        │
│                                                  │
│ ┌────────┬────────┬────────┬────────┬────────┐   │
│ │ TRADES │ WIN %  │ PF     │ SHARPE │ MDD    │   │
│ │ 142    │ 55.6%  │ 1.32   │ 0.94   │ -4.2%  │   │
│ └────────┴────────┴────────┴────────┴────────┘   │
│                                                  │
│ EQUITY CURVE                                     │
│ ┌────────────────────────────────────────────┐   │
│ │     ╱╲    ╱╲                               │   │
│ │   ╱╱  ╲╱╱  ╲╲      ╱╱                     │   │
│ │ ╱╱            ╲╲╱╱╱╱                       │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ DAILY P&L                                        │
│ ┌────────────────────────────────────────────┐   │
│ │ ▓ ▓   ▓     ▓ ▓                           │   │
│ │ ▓ ▓ ░ ▓   ░ ▓ ▓ ▓                         │   │
│ │───────░───░────────                        │   │
│ │       ░   ░                                │   │
│ └────────────────────────────────────────────┘   │
│                                                  │
│ BY STRATEGY                                      │
│ ORB Breakout  │ 142 trades │ 55.6% │ +$1,234    │
└──────────────────────────────────────────────────┘
```

### Components

**PeriodSelector** (`features/performance/PeriodSelector.tsx`):
- Tab bar: Today / Week / Month / All
- Styled as button group with active state
- Updates URL query param for selected period
- Default: "month"

**MetricsGrid** (`features/performance/MetricsGrid.tsx`):
- Uses `usePerformance(period)` data
- 5-6 key metrics in a responsive grid (2 cols mobile, 3 cols tablet, 5-6 cols desktop)
- Metrics to show: Total Trades, Win Rate, Profit Factor, Sharpe Ratio, Max Drawdown, Net P&L
- Each uses MetricCard component

**EquityCurveChart** (`features/performance/EquityCurve.tsx`):
- **TradingView Lightweight Charts** `AreaSeries`
- X-axis: dates from daily_pnl array (Lightweight Charts handles trading day gaps natively)
- Y-axis: cumulative P&L (compute from daily_pnl data: running sum)
- Area fill: gradient from argus-accent to transparent
- Line: argus-accent color
- Crosshair with price/date tooltip
- Dark theme: `layout.background.color` = argus-bg, grid line colors = argus-border
- Responsive: wrapped in a container with `ResizeObserver` to call `chart.applyOptions({ width })` on resize
- Height: 300px desktop, 220px tablet, 180px mobile

**DailyPnlChart** (`features/performance/DailyPnlChart.tsx`):
- **TradingView Lightweight Charts** `HistogramSeries`
- X-axis: dates
- Y-axis: daily P&L
- Green bars for positive days, red for negative (set `color` per data point)
- Crosshair synced with equity curve if both on same page (use `crosshairMove` event)
- Same dark theme treatment
- Height: 250px desktop, 200px tablet, 160px mobile

**StrategyBreakdown** (`features/performance/StrategyBreakdown.tsx`):
- Table showing per-strategy metrics from `by_strategy`
- Columns: Strategy Name, Trades, Win Rate, Profit Factor, Net P&L
- Simple DataTable usage

### Chart Theme Configuration

Create `src/utils/chartTheme.ts` with consistent theming for both chart libraries:

```typescript
// Shared color constants used by both Recharts and Lightweight Charts
export const chartColors = {
  primary: '#3b82f6',
  profit: '#22c55e',
  loss: '#ef4444',
  grid: '#2a2d3a',
  text: '#8b8fa3',
  bg: '#0f1117',
  surface: '#1a1d27',
  border: '#2a2d3a',
  series: ['#3b82f6', '#8b5cf6', '#06b6d4', '#f59e0b', '#ec4899', '#10b981'],
};

// TradingView Lightweight Charts default options
export const lwcDefaultOptions = {
  layout: {
    background: { color: chartColors.bg },
    textColor: chartColors.text,
    fontSize: 11,
  },
  grid: {
    vertLines: { color: chartColors.border },
    horzLines: { color: chartColors.border },
  },
  crosshair: {
    vertLine: { color: chartColors.text, width: 1, style: 3, labelBackgroundColor: chartColors.surface },
    horzLine: { color: chartColors.text, width: 1, style: 3, labelBackgroundColor: chartColors.surface },
  },
  timeScale: {
    borderColor: chartColors.border,
    timeVisible: false,
  },
  rightPriceScale: {
    borderColor: chartColors.border,
  },
};

// Recharts shared props (for non-time-series charts in future sprints)
export const rechartsAxisStyle = {
  fontSize: 11,
  fill: chartColors.text,
};

export const rechartsGridStyle = {
  strokeDasharray: '3 3',
  stroke: chartColors.grid,
};

export const rechartsTooltipStyle = {
  contentStyle: {
    backgroundColor: chartColors.surface,
    borderColor: chartColors.border,
    color: chartColors.text,
    borderRadius: '6px',
    fontSize: '12px',
  },
};
```

### Gate Check (Session 6)
- [ ] Period selector switches between today/week/month/all
- [ ] Metrics grid shows correct values
- [ ] Equity curve renders with Lightweight Charts (cumulative P&L, no weekend gaps)
- [ ] Daily P&L histogram shows green/red bars via Lightweight Charts
- [ ] Charts are responsive (resize on container change via ResizeObserver)
- [ ] Charts use dark theme (argus-bg background, argus-border grid lines)
- [ ] Crosshair works on both charts
- [ ] Strategy breakdown table populated
- [ ] `npm run build` passes

---

## Session 7: System Page

The engine room — system health, strategy status, and operational details.

### Layout
```
┌──────────────────────────────────────────────────┐
│ SYSTEM                                           │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ STATUS: ● HEALTHY    Uptime: 4h 23m 12s     │ │
│ │ Mode: Paper Trading  Broker: SimulatedBroker │ │
│ │ Data: Alpaca         Last HB: 10:45:32 AM   │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ COMPONENTS                                       │
│ ┌──────────────────────────────────────────────┐ │
│ │ ● Broker        HEALTHY  Connected to Sim... │ │
│ │ ● Data Service  HEALTHY  Mock data active    │ │
│ │ ● Order Manager HEALTHY  Processing orders   │ │
│ │ ● Risk Manager  HEALTHY  Risk eval active    │ │
│ │ ● ORB Breakout  HEALTHY  Strategy running    │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ STRATEGIES                                       │
│ ┌──────────────────────────────────────────────┐ │
│ │ ORB Breakout v1.0.0                          │ │
│ │ ● Active   │ Paper   │ $100K allocated       │ │
│ │ Today: +$234 │ 3 trades │ 1 open position    │ │
│ │ Config: or=5, hold=15, gap=2.0, r=2.0       │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ▼ RECENT EVENTS (developer)                      │
│   system.heartbeat #142  10:45:32                │
│   position.updated #141  10:45:28                │
│   price.update NVDA #140  10:45:25               │
└──────────────────────────────────────────────────┘
```

### Components

**SystemOverview** (`features/system/SystemOverview.tsx`):
- Uses `useHealth()`
- Overall status with large status dot + text
- Key metadata: uptime (formatted), mode (paper/live), broker source, data source
- Last heartbeat time, last trade time, last data received time
- All times formatted in ET

**ComponentStatusList** (`features/system/ComponentStatus.tsx`):
- List of health components from `components` field
- Each row: status dot, component name, status text, detail text
- Sorted: errors first, then degraded, then healthy

**StrategyCards** (`features/system/StrategyCards.tsx`):
- Uses `useStrategies()`
- One card per strategy
- Shows: name, version, active status (dot), pipeline stage (badge), allocated capital, today's P&L, trade count, open positions
- Config summary displayed as compact key-value pairs
- Future: these cards will get pause/resume controls (Sprint 16+)

**EventsLog** (`features/system/EventsLog.tsx`):
- Uses live store `recentEvents`
- Collapsible section (default collapsed on mobile, expanded on desktop)
- Shows last 20 events with: type (colored), sequence number, timestamp, truncated data
- Auto-scrolls to newest
- "Clear" button to reset

### Gate Check (Session 7)
- [ ] System page shows all health components
- [ ] Strategy card renders with correct data
- [ ] Events log shows WebSocket events
- [ ] Status dots colored correctly
- [ ] Uptime counter displays correctly
- [ ] `npm run build` passes

---

## Session 8: Polish & Responsive QA

### 8.1 Responsive Audit

Test every page at the three target device widths:
1. **393px** (iPhone 16 Pro) — everything must be usable with one hand
2. **834px** (iPad Pro 11" portrait) — two-column layouts, full table columns where room permits
3. **1194px** (iPad Pro 11" landscape) — full desktop layout with sidebar
4. **1512px** (MacBook Pro 16") — full desktop, verify nothing stretches awkwardly

Fix issues:
- Text truncation on small screens (use `truncate` class on long values)
- Table horizontal scroll if needed (wrap in `overflow-x-auto`)
- Chart minimum height enforcement
- Touch target size (min 44px for interactive elements on all touch devices)
- Bottom nav safe area padding on iPhone (`pb-[env(safe-area-inset-bottom)]`)
- iPad Split View (half-screen ~417px) — should degrade gracefully to phone layout

### 8.2 Loading & Error States

Verify every page handles:
- **Loading state:** Shows LoadingState component while queries are in flight
- **Error state:** Shows error message with retry button
- **Empty state:** Shows EmptyState with appropriate messaging
  - Dashboard with 0 positions: "No open positions — system is monitoring for signals"
  - Trades with 0 results: "No trades match your filters"
  - Performance with 0 data: "Not enough data for this period"

### 8.3 WebSocket Resilience

Test:
- WS disconnection (kill dev server, reconnect): UI shows "Disconnected" indicator, reconnects
- WS reconnection: data resumes without page refresh
- Connection indicator visible in sidebar (status dot changes color)

### 8.4 Dark Theme Contrast

Verify:
- All text meets WCAG AA contrast ratio (4.5:1 for normal text)
- Dim text (`text-argus-text-dim`) is still readable
- Charts have sufficient contrast against dark backgrounds
- Focus outlines visible for keyboard navigation

### 8.5 Build Verification

- `npm run build` produces zero errors and zero warnings
- `npm run lint` clean (or only acceptable warnings)
- No console.log statements left in production code (remove or guard with `import.meta.env.DEV`)
- Bundle size check: should be well under 500KB gzipped for this scope

### Gate Check (Session 8)
- [ ] All pages usable at 393px (iPhone 16 Pro)
- [ ] All pages render well at 834px (iPad portrait) and 1194px (iPad landscape)
- [ ] Full desktop layout at 1512px (MacBook Pro 16")
- [ ] All loading/error/empty states render correctly
- [ ] WebSocket reconnection works
- [ ] Dark theme contrast acceptable
- [ ] `npm run build` passes with zero errors
- [ ] No stray console.log statements
- [ ] Dev server walkthrough: login → dashboard → all pages → verify data

---

## File Structure (Final)

```
argus/ui/src/
├── api/
│   ├── client.ts          # (existing) Fetch wrappers
│   ├── types.ts           # (existing) TypeScript interfaces
│   └── ws.ts              # (existing) WebSocket client
├── components/
│   ├── Badge.tsx
│   ├── Card.tsx
│   ├── CardHeader.tsx
│   ├── DataTable.tsx
│   ├── EmptyState.tsx
│   ├── LoadingState.tsx
│   ├── LWChart.tsx           # Reusable Lightweight Charts wrapper
│   ├── MetricCard.tsx
│   ├── PnlValue.tsx
│   ├── ProtectedRoute.tsx    # (existing, moved here)
│   └── StatusDot.tsx
├── features/
│   ├── dashboard/
│   │   ├── AccountSummary.tsx
│   │   ├── DailyPnlCard.tsx
│   │   ├── HealthMini.tsx
│   │   ├── MarketStatusBadge.tsx
│   │   ├── OpenPositions.tsx
│   │   └── RecentTrades.tsx
│   ├── performance/
│   │   ├── DailyPnlChart.tsx
│   │   ├── EquityCurve.tsx
│   │   ├── MetricsGrid.tsx
│   │   ├── PeriodSelector.tsx
│   │   └── StrategyBreakdown.tsx
│   ├── system/
│   │   ├── ComponentStatus.tsx
│   │   ├── EventsLog.tsx
│   │   ├── StrategyCards.tsx
│   │   └── SystemOverview.tsx
│   └── trades/
│       ├── TradeFilters.tsx
│       ├── TradeStatsBar.tsx
│       └── TradeTable.tsx
├── hooks/
│   ├── useAccount.ts
│   ├── useHealth.ts
│   ├── usePerformance.ts
│   ├── usePositions.ts
│   ├── useStrategies.ts
│   └── useTrades.ts
├── layouts/
│   ├── AppShell.tsx
│   ├── MobileNav.tsx
│   └── Sidebar.tsx
├── pages/
│   ├── ConnectionTest.tsx  # (existing, kept for dev)
│   ├── DashboardPage.tsx
│   ├── Login.tsx           # (existing)
│   ├── PerformancePage.tsx
│   ├── SystemPage.tsx
│   └── TradesPage.tsx
├── stores/
│   ├── auth.ts             # (existing)
│   └── live.ts             # (enhanced)
├── utils/
│   ├── chartTheme.ts
│   └── format.ts
├── App.tsx                 # (updated routing)
├── index.css               # (updated theme)
└── main.tsx                # (updated with QueryClientProvider)
```

---

## Dependencies

Already in `package.json`:
- `react`, `react-dom`, `react-router-dom` — routing + rendering
- `@tanstack/react-query` — data fetching + caching
- `recharts` — non-time-series charts (sparklines, distributions, heatmaps in future sprints)
- `lucide-react` — icons
- `zustand` — state management
- `tailwindcss` v4 — styling

**New packages to add in Session 1:**
- `lightweight-charts` — TradingView's open-source financial charting library (~40KB gzipped). Used for equity curve, daily P&L histogram, and future price charts.

```bash
cd argus/ui && npm install lightweight-charts
```

That's it — one new dependency. Lightweight Charts has zero transitive dependencies.

---

## Test Targets

Sprint 15 is frontend-only. No Python tests added. Quality gates:
- `npm run build` passes with zero errors
- `npm run lint` passes (or only benign warnings)
- All pages render with dev server mock data
- All pages usable at 393px (iPhone 16 Pro), 834px (iPad portrait), and 1512px (MacBook)
- WebSocket integration functional (events flow through)

---

## Design Principles (for Claude Code Reference)

1. **Tabular nums everywhere:** Any number that could change in real-time uses `tabular-nums` / `.tabular-nums`
2. **Color = meaning:** Green = profit/healthy, Red = loss/error, Amber = warning, Blue = accent/action, Gray = inactive/dim
3. **Information density over whitespace:** This is a trading tool, not a marketing site. Show data. Compress where possible. But maintain visual rhythm with consistent 4px-based spacing.
4. **Mobile-first CSS:** Write base styles for phone (<640px), add `md:` for tablet (640–1023px) and `lg:` for desktop (≥1024px). Never the reverse. Target devices: iPhone 16 Pro (393px), iPad Pro 11" (834px portrait, 1194px landscape), MacBook Pro 16" (1512px).
5. **No page transitions:** Instant route changes. Data transitions are animated (flash, slide-in), navigation is not.
6. **Type hierarchy is strict:** Use the defined sizes. Don't invent new ones. Hero metrics are `text-3xl`, section labels are `text-sm uppercase tracking-wider`, data is `text-sm tabular-nums`.
7. **Dark theme only:** No light mode toggle. Every color is designed for dark backgrounds.
8. **Chart library selection:** Lightweight Charts for any chart with a time-series x-axis (dates, timestamps). Recharts for everything else (distributions, comparisons, non-temporal data). When in doubt, Lightweight Charts — this is a trading tool.
