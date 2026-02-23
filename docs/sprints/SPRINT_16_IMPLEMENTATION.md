# ARGUS Sprint 16 — Complete Implementation Package

> Generated: Feb 23, 2026
> Contains: Implementation Spec, Session Prompts, Code Review Plan, Handoff Briefs

---

# PART 1: SPRINT 16 IMPLEMENTATION SPEC

> Paste this entire Part 1 into the FIRST Claude Code session. Subsequent sessions get their own targeted prompts (see Part 2).

## Sprint Overview

**Sprint 16 — Desktop/PWA + UX Polish**
**Target:** ~32 hours across 10 Claude Code sessions
**Tests baseline:** 926 (Sprint 15). This sprint adds minimal backend tests (CSV export endpoint, emergency controls). Frontend is primary focus.
**Repo:** https://github.com/stevengizzi/argus.git

### Three Pillars

1. **UX Polish (~18h)** — Transform the functional prototype into a crafted, premium tool. Motion, animation, feedback, ambient awareness.
2. **Multi-Surface Delivery (~7h)** — PWA for iPhone/iPad home screen, Tauri desktop shell with system tray.
3. **Paper Trading Features (~7h)** — CSV export, trade drill-down panel, emergency controls.

### Approved Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Animation library | Framer Motion `variants` + `staggerChildren` pattern | Composable, centralized timing, consistent feel across pages |
| Page transitions | AnimatePresence wrapping Outlet, keyed on `location.pathname` | Fade + subtle upward shift (200ms enter, 100ms exit) |
| Sparklines | SVG `<polyline>` component (~30 lines) | LW Charts mini instances are heavyweight overkill for 30-50 point sparklines |
| Skeleton loading | CSS `linear-gradient` shimmer animation | 60fps guaranteed, zero JS render cost |
| Number morphing | Extend existing `PnlValue` with `requestAnimationFrame` interpolation | Keeps existing flash behavior, adds smooth counting for hero numbers |
| Trade drill-down | Right-side slide-in panel (desktop), full-screen modal (mobile) | Builds foundation for Sprint 21's Stock Detail Panel (21-A) |
| Tauri placement | Last session | Avoids blocking UX polish if Rust toolchain has issues |
| Backtest vs paper comparison | Deferred to Sprint 21 | Requires cross-database joins, fits Strategy Lab scope |

---

## Session 1: Animation Foundation

### Goal
Install Framer Motion, create the core animation system, and add page transitions to all routes.

### Dependencies to Install
```bash
cd argus/ui && npm install framer-motion
```

### New Files

**`src/utils/motion.ts`** — Centralized animation constants and variants
```typescript
// Animation timing constants (DEC-110: <500ms, 60fps, never blocks)
export const DURATION = {
  fast: 0.15,
  normal: 0.25,
  slow: 0.4,
} as const;

export const EASE = {
  out: [0.0, 0.0, 0.2, 1.0] as const,       // ease-out (entries)
  inOut: [0.4, 0.0, 0.2, 1.0] as const,      // ease-in-out (transitions)
  spring: { type: 'spring', stiffness: 300, damping: 30 } as const,
};

// Page transition variants
export const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: DURATION.normal, ease: EASE.out } },
  exit: { opacity: 0, transition: { duration: DURATION.fast } },
};

// Stagger container — wrap around a list of items
export const staggerContainer = (staggerDelay = 0.06) => ({
  hidden: {},
  show: {
    transition: {
      staggerChildren: staggerDelay,
    },
  },
});

// Stagger child — apply to each item in a staggered list
export const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.out },
  },
};

// Fade in only (no translate) — for charts, large content blocks
export const fadeIn = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { duration: DURATION.slow },
  },
};

// Card hover (desktop only — apply via whileHover)
export const cardHover = {
  y: -1,
  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
  transition: { duration: DURATION.fast },
};
```

**`src/components/AnimatedPage.tsx`** — Page transition wrapper
```typescript
import { motion } from 'framer-motion';
import { pageVariants } from '../utils/motion';

interface AnimatedPageProps {
  children: React.ReactNode;
  className?: string;
}

export function AnimatedPage({ children, className = '' }: AnimatedPageProps) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={className}
    >
      {children}
    </motion.div>
  );
}
```

### Modifications

**`src/App.tsx`** — Add AnimatePresence around routes
- Import `AnimatePresence` from `framer-motion`
- Import `useLocation` from `react-router-dom`
- Restructure: The protected route outlet needs to be wrapped. Since `AppShell` renders `<Outlet />`, the AnimatePresence wrapping happens inside AppShell, not App.tsx.

**`src/layouts/AppShell.tsx`** — Wrap Outlet with AnimatePresence
- Import `AnimatePresence` from `framer-motion`
- Import `useLocation` from `react-router-dom`
- Replace bare `<Outlet />` with:
```tsx
const location = useLocation();
// ...
<AnimatePresence mode="wait">
  <motion.div
    key={location.pathname}
    variants={pageVariants}
    initial="initial"
    animate="animate"
    exit="exit"
  >
    <Outlet />
  </motion.div>
</AnimatePresence>
```

**Each page component** (DashboardPage, TradesPage, PerformancePage, SystemPage):
- No changes needed for basic page transitions — the AppShell wrapper handles it
- Stagger animations are added in Session 3

### Verification
- Navigate between all 4 pages — each transition should show subtle fade + upward shift
- No layout jumps during transition
- Animation completes in <300ms perceived
- Mobile bottom nav still works correctly
- Back/forward browser navigation works

---

## Session 2: Skeleton Loading System

### Goal
Replace all loading spinners with content-shaped skeleton placeholders that match actual layout.

### New Files

**`src/components/Skeleton.tsx`** — Skeleton primitive with shimmer
```typescript
// Variants: 'line' (text), 'rect' (card/chart), 'circle' (avatar/dot)
// Shimmer via CSS gradient animation (zero JS cost)
// Uses argus-surface-2 as base, argus-surface-3 as highlight
```

Props:
- `variant`: `'line' | 'rect' | 'circle'`
- `width`: string or number (default: '100%')
- `height`: string or number (default: variant-dependent)
- `className`: additional classes
- `rounded`: boolean (default: true for line/rect, always true for circle)

**`src/index.css`** — Add shimmer keyframe
```css
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
.skeleton-shimmer {
  background: linear-gradient(
    90deg,
    var(--color-argus-surface-2) 25%,
    var(--color-argus-surface-3) 50%,
    var(--color-argus-surface-2) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
```

**`src/features/dashboard/DashboardSkeleton.tsx`** — Dashboard-shaped skeleton
- 3 summary cards (rect skeletons matching AccountSummary/DailyPnlCard/MarketStatusBadge dimensions)
- Positions section (card header line + 3 table row skeletons)
- Bottom row (2 cards with line skeletons)

**`src/features/trades/TradesSkeleton.tsx`** — Trades page skeleton
- Filter bar (3 rect skeletons for dropdowns)
- Stats bar (4 line skeletons)
- Table skeleton (header line + 8 row skeletons)

**`src/features/performance/PerformanceSkeleton.tsx`** — Performance page skeleton
- Period selector line
- Metrics grid (12 small rect skeletons in grid)
- Chart area (large rect skeleton ~300px tall)
- Strategy breakdown (table skeleton)

**`src/features/system/SystemSkeleton.tsx`** — System page skeleton
- 2-column grid with card-shaped rect skeletons

### Modifications

**Each page** — Replace `<LoadingState />` with the page-specific skeleton:
- `DashboardPage`: Needs the skeleton as a separate component since it doesn't have a single loading state (each feature loads independently). The features already have individual loading states — update `AccountSummary`, `DailyPnlCard`, `MarketStatusBadge`, `OpenPositions`, `RecentTrades`, `HealthMini` to show skeleton shapes instead of spinner.
- `TradesPage`: Replace the `isLoading` branch with `<TradesSkeleton />`
- `PerformancePage`: Replace the `isLoading` branch with `<PerformanceSkeleton />`
- `SystemPage`: Each system feature component should show skeleton shapes while loading

### Verification
- Throttle network in browser devtools → confirm skeletons appear shaped like actual content
- Skeletons transition smoothly to real content (no layout shift)
- Shimmer animation runs at 60fps (check Performance tab)
- All 4 pages show appropriate skeletons

---

## Session 3: Staggered Entry Animations

### Goal
Dashboard cards, table rows, metric grids, and section groups animate in with staggered delays on page mount/route entry.

### Approach
Use the `staggerContainer` and `staggerItem` variants from `motion.ts`. Wrap parent containers in `motion.div variants={staggerContainer()} initial="hidden" animate="show"` and each child in `motion.div variants={staggerItem}`.

### Modifications

**`DashboardPage.tsx`**:
- Wrap the top-level div in `motion.div` with `staggerContainer(0.08)` variants
- Wrap each grid section (summary cards row, positions, bottom row) in `motion.div` with `staggerItem` variants
- The 3 summary cards get their own inner stagger with tighter delay (0.05)

**`TradesPage.tsx`**:
- Wrap the top-level div in stagger container
- Header, filters, stats bar, table each get staggerItem

**`PerformancePage.tsx`**:
- Wrap the top-level div in stagger container
- Header+selector, metrics grid, each chart, strategy breakdown get staggerItem
- MetricsGrid internal: each metric card gets sub-stagger (0.04)

**`SystemPage.tsx`**:
- Wrap the top-level div in stagger container
- Header, grid columns, events log get staggerItem

**`MetricsGrid.tsx`** (performance):
- Wrap the grid in stagger container
- Each MetricCard in stagger item

### Important: Only animate on mount
- Use `initial="hidden"` and `animate="show"` — these only fire on mount
- Do NOT re-trigger on data updates (useQuery refetch should not replay animations)
- If data refreshes while the page is visible, content updates in place without re-animating

### Verification
- Navigate to each page — content should "assemble" top-to-bottom with staggered fade+translate
- Navigate away and back — animation replays (new mount)
- Data refetch (pull-to-refresh, auto-refetch) should NOT replay animations
- Animations complete within ~400ms total (stagger * item_count + item_duration)

---

## Session 4: Number Morphing + P&L Flash Enhancement

### Goal
Hero numbers (Account Equity) animate between values with smooth counting. All P&L values flash green/red more prominently on WebSocket updates.

### New Files

**`src/components/AnimatedNumber.tsx`** — Smooth number interpolation
```typescript
// Uses requestAnimationFrame to interpolate between old and new value
// Duration: ~400ms with ease-out
// Format function prop for currency/percent/R-multiple formatting
// Only interpolates when the component is mounted and visible
// Falls back to instant display on first render (no animation from 0)
```

Props:
- `value`: number
- `format`: `(n: number) => string` (formatting function)
- `duration`: number (ms, default 400)
- `className`: string

### Modifications

**`src/components/PnlValue.tsx`** — Enhanced flash
- Increase flash duration from 600ms to 800ms
- Add a subtle scale pulse (1.0 → 1.02 → 1.0) alongside the background flash
- Add transition on the text color itself (smooth transition between profit/loss colors if value crosses zero)

**`src/features/dashboard/AccountSummary.tsx`**:
- Replace the static equity display with `<AnimatedNumber>` using `formatCurrency`
- Cash and Buying Power can use AnimatedNumber too but with shorter duration (200ms)

**`src/features/dashboard/DailyPnlCard.tsx`**:
- Use `<AnimatedNumber>` for the hero P&L number
- Keep the PnlValue flash for the percentage

### CSS Updates

**`src/index.css`** — Enhanced flash animations
```css
@keyframes pnl-flash-profit {
  0% { background-color: rgba(34, 197, 94, 0.3); transform: scale(1.02); }
  50% { background-color: rgba(34, 197, 94, 0.15); }
  100% { background-color: transparent; transform: scale(1); }
}
@keyframes pnl-flash-loss {
  0% { background-color: rgba(239, 68, 68, 0.3); transform: scale(1.02); }
  50% { background-color: rgba(239, 68, 68, 0.15); }
  100% { background-color: transparent; transform: scale(1); }
}
```

### Verification
- Open Dashboard, watch equity number count up/down when dev mode generates updates
- P&L values flash with scale pulse on WebSocket price updates
- Flash doesn't jitter or cause layout shift
- AnimatedNumber handles rapid successive updates gracefully (interrupts current animation)
- Format stays consistent during animation (no flickering decimal places)

---

## Session 5: Hover Feedback + Micro-Interactions

### Goal
Cards lift on hover (desktop), table rows highlight smoothly, nav items have refined hover states, interactive elements have clear affordances.

### Modifications

**`src/components/Card.tsx`** — Add hover lift
```tsx
// Add transition and hover styles
// Desktop only: translateY(-1px) + box-shadow increase
// Use CSS transition (not Framer Motion) for this — simpler, lighter
className={`... transition-all duration-150 hover:translate-y-[-1px] hover:shadow-lg hover:shadow-black/20 ...`}
```
Note: Only add hover effect to interactive cards (ones you click). Non-interactive cards like AccountSummary shouldn't lift. Add an `interactive` prop to Card.

**`src/components/DataTable.tsx`** or individual table rows:
- Add smooth background transition on hover: `transition-colors duration-150 hover:bg-argus-surface-2/50`
- Existing `hover:bg-argus-bg/50` should be smoothed with transition

**`src/layouts/Sidebar.tsx`** — Refined nav hover
- Add slight scale on hover icons (1.0 → 1.05)
- Active indicator: left border accent bar (2px) instead of just background color change
- Tooltip appears with slight delay (200ms) and fade-in

**`src/layouts/MobileNav.tsx`** — Touch feedback
- Active tab: add a small dot indicator below the icon (like iOS tab bar)
- Press feedback via active state (slight scale-down 0.95 on touch)

**Badge component** — Add subtle hover glow for clickable badges
- Only for badges that will be clickable in future sprints
- CSS: `hover:ring-1 hover:ring-current/20`

### New CSS in `index.css`

```css
/* Smooth interactive transitions */
.interactive-card {
  transition: transform 150ms ease, box-shadow 150ms ease;
}
.interactive-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

/* Active nav indicator */
.nav-active-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 24px;
  background-color: var(--color-argus-accent);
  border-radius: 1px;
  transition: opacity 150ms ease;
}
```

### Verification
- Hover over cards on desktop — subtle lift with shadow
- Table rows smoothly highlight
- Nav tooltips appear with delay, not instantly
- Mobile: tap on nav items shows brief press feedback
- No hover effects fire on mobile/touch (CSS media query or pointer check)

---

## Session 6: Chart Animations + Sparklines

### Goal
Equity curve draws left-to-right on load. P&L histogram bars grow from zero. Dashboard summary cards get inline sparkline charts.

### New Files

**`src/components/Sparkline.tsx`** — SVG sparkline component
```typescript
interface SparklineProps {
  data: number[];           // Array of values
  width?: number;           // SVG width (default 120)
  height?: number;          // SVG height (default 40)
  color?: string;           // Line color (default argus-accent)
  fillOpacity?: number;     // Area fill opacity (default 0.1)
  strokeWidth?: number;     // Line width (default 1.5)
  className?: string;
}

// Implementation:
// - Normalize data to [0, height] range with padding
// - Generate polyline points string
// - SVG with <polyline> for line and <polygon> for area fill
// - No axes, labels, or interactivity — pure ambient visualization
// - Handle edge cases: empty array, single point, all same values
```

### Modifications

**`src/features/performance/EquityCurve.tsx`** — Draw-in animation
- Lightweight Charts supports `setData` with animation. After chart creation in `onChartReady`, set data with a slight delay (50ms) so the line animates in.
- Alternative: If LW Charts native animation is insufficient, use a CSS clip-path animation that reveals the chart left-to-right over 500ms.

**`src/features/performance/DailyPnlChart.tsx`** — Bar grow animation
- Similar approach: set histogram data with slight delay for grow animation
- Or use CSS transform on the chart container: `scaleY(0) → scaleY(1)` with `transform-origin: bottom`

**`src/features/dashboard/AccountSummary.tsx`** — Add equity sparkline
- Fetch last 30 days of equity data (needs data source — use daily_pnl from performance endpoint to compute cumulative equity)
- Add `<Sparkline data={equityTrend} />` below the hero number
- Color: argus-accent (blue)

**`src/features/dashboard/DailyPnlCard.tsx`** — Add P&L sparkline
- Use today's intraday P&L data or recent daily P&L data
- Add `<Sparkline data={pnlTrend} />` below the hero P&L number
- Color: argus-profit (green) if net positive, argus-loss (red) if net negative

**API data for sparklines:**
- The performance endpoint already returns `daily_pnl` array with date and pnl per day
- For dashboard sparklines, call `GET /api/v1/performance/month` and extract the `daily_pnl` array
- Create a new hook: `useSparklineData()` that fetches performance/month and extracts trend arrays
- Cache aggressively (5 minute stale time) — sparklines don't need real-time data

### Verification
- Navigate to Performance page — equity curve draws in from left
- P&L histogram bars grow upward from zero line
- Dashboard summary cards show sparklines
- Sparklines render correctly with mock data (positive trend, negative trend, flat)
- Sparklines are responsive (shrink on mobile)
- No performance issues with multiple SVG sparklines rendering

---

## Session 7: Empty States + Trade Slide-In

### Goal
Replace generic "No data" messages with contextual, helpful empty states. New trades slide in from WebSocket updates with visual emphasis.

### Modifications

**`src/features/dashboard/OpenPositions.tsx`** — Contextual empty state
- Instead of "No open positions — system is monitoring for signals", determine context:
  - Pre-market: "No open positions — market opens in Xh Xm" (compute from current ET time)
  - Market hours: "No open positions — scanning for setups"
  - After hours: "No open positions — market closed. Next session: tomorrow 9:30 AM ET"
- Add a subtle animated radar/scan icon during market hours (CSS animation, pulsing circle)

**`src/features/dashboard/RecentTrades.tsx`** — Empty state + slide-in
- Empty: "No trades today — opening range forms at 9:35 AM ET" (pre-market) or "No trades today" (other times)
- New trade slide-in: When a trade appears via WebSocket (position.closed event invalidates trades query), the newest row should animate in with `slide-in` class. Use `key` on trade items and Framer Motion `AnimatePresence` + `layoutId` for smooth list updates.

**`src/features/trades/TradeTable.tsx`** — Empty state
- "No trades match your filters" (when filters active)
- "No trades recorded yet — trades will appear here once the strategy takes a position" (when no filters)

**`src/features/performance/PerformancePage.tsx`** — Empty state
- Already has a basic empty state. Enhance: "No trades for [period]. Try a longer time range or check back after the next trading session."

**`src/features/system/EventsLog.tsx`** — Empty state
- "No events yet — events will stream here when the system is active"
- Add a subtle "listening" animation (pulsing dot)

**Helper: `src/utils/marketTime.ts`**
```typescript
// Utility to compute market status and time-to-open/close
// Uses America/New_York timezone
// Returns: { status: 'pre_market' | 'open' | 'closed' | 'after_hours', timeToOpen?: string, timeToClose?: string }
// Used by empty states to show contextual messages
```

### Verification
- With dev server (--dev), verify all empty states show contextual messages
- New trade appearing in RecentTrades slides in smoothly
- Market time calculations correct for current time
- Empty states don't flash on initial load (skeleton → empty, not skeleton → content → empty)

---

## Session 8: PWA Configuration

### Goal
Make the app installable as a PWA on iPhone/iPad with proper icons, manifest, and service worker.

### New Files

**`argus/ui/public/manifest.json`**
```json
{
  "name": "ARGUS Command Center",
  "short_name": "ARGUS",
  "description": "Automated trading system command center",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f1117",
  "theme_color": "#0f1117",
  "orientation": "any",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

**`argus/ui/public/sw.js`** — Service worker (shell caching only)
```javascript
// Cache app shell (HTML, CSS, JS bundles) for offline shell
// Network-first for API calls (never cache trading data)
// Version-keyed cache for clean updates
const CACHE_NAME = 'argus-shell-v1';
const SHELL_ASSETS = ['/', '/index.html'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Network-first for API/WebSocket, cache-first for static assets
  if (event.request.url.includes('/api/') || event.request.url.includes('/ws/')) {
    return; // Don't cache API calls
  }
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
```

**Icon generation:**
- Create a simple "A" icon in the ARGUS accent blue (#3b82f6) on dark background (#0f1117)
- Generate at 192x192 and 512x512
- Generate maskable versions (with safe zone padding)
- Use a Python script with Pillow or a simple SVG-to-PNG conversion
- Place in `argus/ui/public/icons/`

**`argus/ui/public/apple-touch-icon.png`** — 180x180 for iOS home screen

### Modifications

**`argus/ui/index.html`** — Add PWA meta tags
```html
<head>
  <!-- PWA -->
  <link rel="manifest" href="/manifest.json" />
  <meta name="theme-color" content="#0f1117" />

  <!-- iOS PWA -->
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="ARGUS" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />

  <!-- Existing head content... -->
</head>
```

**`src/main.tsx`** — Register service worker
```typescript
// Register service worker after app mount
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((err) => {
      console.warn('SW registration failed:', err);
    });
  });
}
```

### Verification
- Run `npm run build` and serve with a static server
- Open in Safari on iPhone/iPad simulator or real device
- "Add to Home Screen" works and app opens in standalone mode (no Safari chrome)
- App icon appears correctly on home screen
- Status bar style is correct (dark, matches app theme)
- Service worker caches shell assets
- API calls still work (not cached)
- Vite dev server still works normally (SW only activates in production builds)

---

## Session 9: Paper Trading Features

### Goal
CSV trade log export, trade drill-down slide-in panel, and emergency controls (pause/resume, manual close).

### New Backend Files

**`argus/api/routes/trades.py`** — Add CSV export endpoint
```python
@router.get("/export/csv")
async def export_trades_csv(
    strategy_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    _auth: dict = Depends(require_auth),
    state: AppState = Depends(get_app_state),
) -> StreamingResponse:
    """Export trades as CSV file."""
    # Query trades with filters (no pagination — export all)
    # Stream as CSV with proper headers
    # Content-Disposition: attachment; filename="argus_trades_{date}.csv"
```

**`argus/api/routes/controls.py`** — Emergency controls
```python
router = APIRouter(tags=["controls"])

@router.post("/strategies/{strategy_id}/pause")
async def pause_strategy(strategy_id: str, ...):
    """Pause a strategy — stops generating new signals."""

@router.post("/strategies/{strategy_id}/resume")
async def resume_strategy(strategy_id: str, ...):
    """Resume a paused strategy."""

@router.post("/positions/{position_id}/close")
async def close_position(position_id: str, ...):
    """Emergency close a specific position at market."""

@router.post("/emergency/flatten")
async def emergency_flatten_all(...):
    """Emergency flatten all positions across all strategies."""

@router.post("/emergency/pause")
async def emergency_pause_all(...):
    """Emergency pause all strategies."""
```

Register in `argus/api/routes/__init__.py`.

### New Frontend Files

**`src/features/trades/TradeDetailPanel.tsx`** — Slide-in trade detail panel
```typescript
// Right-side panel (desktop: 40% width, slides from right)
// Full-screen modal (mobile: slides up from bottom)
// Content:
//   - Symbol + Strategy badge
//   - Entry/Exit prices with timestamps
//   - P&L (dollars, percent, R-multiple)
//   - Hold duration
//   - Exit reason with explanation text
//   - Stop/T1/T2 levels
//   - Commission
//   - Market regime at time of trade
// Close button + click-outside-to-close + Escape key
// Framer Motion: slideIn from right (desktop) or bottom (mobile)
```

**`src/features/dashboard/EmergencyControls.tsx`** — Emergency action buttons
```typescript
// Red "Emergency" section at bottom of Dashboard or System page
// Buttons: "Flatten All Positions", "Pause All Strategies"
// Confirmation dialog before executing (modal with "Are you sure?")
// Status feedback: loading spinner, success/error toast
```

**`src/hooks/useControls.ts`** — API hooks for control actions
```typescript
// usePauseStrategy(strategyId)
// useResumeStrategy(strategyId)
// useClosePosition(positionId)
// useEmergencyFlatten()
// useEmergencyPause()
// All use useMutation from TanStack Query with optimistic updates
```

### Modifications

**`src/features/trades/TradeTable.tsx`** — Add row click handler
- Each trade row becomes clickable (cursor-pointer, hover highlight)
- Clicking opens TradeDetailPanel with the selected trade
- Add state: `selectedTradeId: string | null`

**`src/pages/TradesPage.tsx`** — Add CSV export button + detail panel
- Export button in header area: `<Download />` icon + "Export CSV" text
- TradeDetailPanel rendered at page level (portal or absolute positioned)

**`src/pages/SystemPage.tsx`** or **`src/pages/DashboardPage.tsx`** — Add emergency controls section
- Emergency controls at bottom of System page
- Strategy pause/resume buttons on each strategy card in SystemPage

**`src/features/system/StrategyCards.tsx`** — Add pause/resume toggle
- Each strategy card gets a pause/resume button
- Visual: paused strategies show amber overlay/badge

### Backend Tests
Add tests for:
- CSV export endpoint (correct format, filtering works)
- Emergency control endpoints (pause, resume, flatten, close)
- Auth required on all control endpoints

### Verification
- Click any trade row → detail panel slides in from right (desktop) or up (mobile)
- Panel shows all trade details correctly
- Click outside or Escape closes the panel
- CSV export downloads a properly formatted CSV file
- Emergency flatten button shows confirmation, then calls API
- Strategy pause/resume toggles correctly
- All new endpoints require authentication

---

## Session 10: Tauri Shell + Final Review

### Goal
Wrap the React app in a Tauri v2 desktop shell with system tray and native notifications. Conduct final cross-device review.

### Tauri Setup

**Prerequisites:** Rust toolchain must be available. If not installable in the Claude Code environment, create the config files and document the local setup steps for Steven.

**Directory structure:**
```
argus/ui/
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── src/
│   │   └── main.rs
│   ├── icons/           (generated from app icon)
│   └── capabilities/
│       └── default.json
```

**`src-tauri/tauri.conf.json`** — Tauri v2 configuration
```json
{
  "$schema": "https://raw.githubusercontent.com/nickel-org/nickel/main/src-tauri/tauri.conf.json",
  "productName": "ARGUS",
  "version": "0.1.0",
  "identifier": "com.argus.trading",
  "build": {
    "frontendDist": "../dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build"
  },
  "app": {
    "withGlobalTauri": false,
    "windows": [
      {
        "title": "ARGUS Command Center",
        "width": 1400,
        "height": 900,
        "minWidth": 800,
        "minHeight": 600,
        "decorations": true,
        "transparent": false
      }
    ],
    "trayIcon": {
      "iconPath": "icons/icon.png",
      "iconAsTemplate": true
    }
  },
  "plugins": {
    "notification": { "enabled": true },
    "autostart": { "enabled": true }
  }
}
```

**`src-tauri/src/main.rs`** — Minimal Tauri app
```rust
// System tray with status icon
// Tray menu: Show/Hide window, Status indicator, Quit
// Notification bridge: expose a Tauri command that frontend can call
// Health status → tray icon color (green/yellow/red)
// Auto-start registration
```

**`src-tauri/Cargo.toml`** — Dependencies
```toml
[dependencies]
tauri = { version = "2", features = ["tray-icon"] }
tauri-plugin-notification = "2"
tauri-plugin-autostart = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

### Frontend Modifications for Tauri

**`src/utils/platform.ts`** — Platform detection
```typescript
export const isTauri = () => '__TAURI__' in window;
export const isPWA = () => window.matchMedia('(display-mode: standalone)').matches;
export const isWeb = () => !isTauri() && !isPWA();
```

**Notification bridge:**
- In Tauri mode, use `@tauri-apps/plugin-notification` for native OS notifications
- In web/PWA mode, fall back to Web Notification API (or just skip)
- Hook into WebSocket events: system.circuit_breaker → native notification

### Final Review Checklist
After all code is complete, verify across all surfaces:

**Web (Chrome desktop):**
- [ ] All 4 pages render correctly
- [ ] Page transitions smooth
- [ ] Stagger animations on mount
- [ ] Skeleton loading states
- [ ] Number morphing on equity
- [ ] Chart animations
- [ ] Sparklines on Dashboard
- [ ] Hover effects on cards/rows
- [ ] Empty states contextual
- [ ] Trade detail panel (click row)
- [ ] CSV export works
- [ ] Emergency controls with confirmation

**PWA (iPhone Safari — simulate or real):**
- [ ] "Add to Home Screen" works
- [ ] Opens in standalone mode
- [ ] Bottom nav works
- [ ] Touch targets ≥44px
- [ ] Safe area padding
- [ ] All pages responsive at 393px
- [ ] Sparklines render at mobile size
- [ ] Trade detail panel slides up (full screen)

**Tablet (iPad Safari — simulate or real):**
- [ ] Responsive at 834px
- [ ] Sidebar nav works
- [ ] Grid layouts adapt
- [ ] Charts resize properly

**Tauri (if buildable):**
- [ ] App launches from binary
- [ ] System tray icon visible
- [ ] Tray menu works (show/hide/quit)
- [ ] Window title correct
- [ ] Connects to API correctly

---

## New Dependencies Summary

| Package | Version | Purpose |
|---------|---------|---------|
| framer-motion | ^11.x | Page transitions, stagger animations |
| @tauri-apps/api | ^2.x | Tauri bridge (only imported in Tauri mode) |
| @tauri-apps/plugin-notification | ^2.x | Native notifications in Tauri |
| @tauri-apps/plugin-autostart | ^2.x | Auto-launch on startup |

Note: Tauri CLI and Rust dependencies are dev/build-time only, not bundled in web/PWA builds.

---

## Files Changed Summary

### New Files (~20)
- `src/utils/motion.ts`
- `src/utils/marketTime.ts`
- `src/utils/platform.ts`
- `src/components/AnimatedPage.tsx`
- `src/components/Skeleton.tsx`
- `src/components/Sparkline.tsx`
- `src/components/AnimatedNumber.tsx`
- `src/features/dashboard/DashboardSkeleton.tsx`
- `src/features/trades/TradesSkeleton.tsx`
- `src/features/trades/TradeDetailPanel.tsx`
- `src/features/performance/PerformanceSkeleton.tsx`
- `src/features/system/SystemSkeleton.tsx`
- `src/features/dashboard/EmergencyControls.tsx`
- `src/hooks/useControls.ts`
- `src/hooks/useSparklineData.ts`
- `argus/ui/public/manifest.json`
- `argus/ui/public/sw.js`
- `argus/api/routes/controls.py`
- `src-tauri/` directory (Tauri config)

### Modified Files (~25)
- `src/index.css` (shimmer keyframes, enhanced flash, interactive transitions)
- `src/layouts/AppShell.tsx` (AnimatePresence)
- `src/layouts/Sidebar.tsx` (hover polish, active indicator)
- `src/layouts/MobileNav.tsx` (touch feedback, active dot)
- `src/pages/DashboardPage.tsx` (stagger, emergency controls)
- `src/pages/TradesPage.tsx` (stagger, skeleton, export, detail panel)
- `src/pages/PerformancePage.tsx` (stagger, skeleton, chart animations)
- `src/pages/SystemPage.tsx` (stagger, skeleton, strategy controls)
- `src/components/Card.tsx` (hover lift)
- `src/components/PnlValue.tsx` (enhanced flash)
- `src/components/EmptyState.tsx` (potential updates)
- `src/features/dashboard/AccountSummary.tsx` (AnimatedNumber, sparkline)
- `src/features/dashboard/DailyPnlCard.tsx` (AnimatedNumber, sparkline)
- `src/features/dashboard/OpenPositions.tsx` (contextual empty state)
- `src/features/dashboard/RecentTrades.tsx` (contextual empty, slide-in)
- `src/features/performance/EquityCurve.tsx` (draw-in animation)
- `src/features/performance/DailyPnlChart.tsx` (bar grow animation)
- `src/features/performance/MetricsGrid.tsx` (sub-stagger)
- `src/features/system/StrategyCards.tsx` (pause/resume)
- `src/features/system/EventsLog.tsx` (empty state)
- `argus/ui/index.html` (PWA meta tags)
- `argus/ui/src/main.tsx` (SW registration)
- `argus/ui/package.json` (new dependencies)
- `argus/api/routes/__init__.py` (register controls router)

---

# PART 2: SESSION PROMPTS

Each prompt below is designed to be copy-pasted directly into a fresh Claude Code session. They're self-contained — Claude Code reads CLAUDE.md from the repo for project context, and each prompt provides the specific session scope.

---

## Session 1 Prompt

```
# ARGUS Sprint 16 — Session 1: Animation Foundation

## Context
Sprint 16 transforms the Command Center from functional prototype to polished, premium tool. This is Session 1 of 10. Read CLAUDE.md for project state. Read docs/ui/UX_FEATURE_BACKLOG.md for design vision.

## This Session's Scope
Install Framer Motion and create the core animation infrastructure:

1. **Install dependency:** `cd argus/ui && npm install framer-motion`

2. **Create `src/utils/motion.ts`** — Centralized animation constants and variants:
   - `DURATION` object: fast (0.15s), normal (0.25s), slow (0.4s)
   - `EASE` object: out ([0, 0, 0.2, 1]), inOut ([0.4, 0, 0.2, 1])
   - `pageVariants`: initial (opacity 0, y 8) → animate (opacity 1, y 0, 250ms) → exit (opacity 0, 150ms)
   - `staggerContainer(delay)`: returns variants with staggerChildren
   - `staggerItem`: hidden (opacity 0, y 12) → show (opacity 1, y 0, 250ms)
   - `fadeIn`: hidden (opacity 0) → show (opacity 1, 400ms)
   - Export everything with proper TypeScript types

3. **Create `src/components/AnimatedPage.tsx`** — Wrapper using pageVariants with motion.div

4. **Modify `src/layouts/AppShell.tsx`** — Add AnimatePresence around the route outlet:
   - Import AnimatePresence from framer-motion, useLocation from react-router-dom
   - Wrap `<Outlet />` in `<AnimatePresence mode="wait">` with a `motion.div` keyed on `location.pathname`
   - Apply pageVariants (initial, animate, exit)
   - Keep all existing functionality (WebSocket connect, sidebar, mobile nav, paper mode)

## Design Rules (DEC-110)
- All animations <500ms
- 60fps — never blocks interaction
- Framer Motion for orchestration, CSS for micro-interactions
- motion.ts is the single source of truth for all timing

## Verification
After implementation:
- `cd argus/ui && npm run build` — zero errors
- `npm run lint` — clean
- Navigate between all 4 pages — smooth fade+translate transitions
- No layout jumps during transitions
- Back/forward browser navigation works
- Mobile bottom nav still functions correctly

## Do NOT do in this session
- Stagger animations on page content (Session 3)
- Skeleton loading (Session 2)
- Any backend changes
```

---

## Session 2 Prompt

```
# ARGUS Sprint 16 — Session 2: Skeleton Loading System

## Context
Sprint 16, Session 2 of 10. Session 1 added Framer Motion + page transitions. This session replaces loading spinners with content-shaped skeleton placeholders.

Read CLAUDE.md for project state. The current LoadingState component (src/components/LoadingState.tsx) shows a spinner — we're replacing this pattern with shaped skeletons.

## This Session's Scope

1. **Add shimmer CSS to `src/index.css`:**
   ```css
   @keyframes shimmer {
     0% { background-position: -200% 0; }
     100% { background-position: 200% 0; }
   }
   .skeleton-shimmer {
     background: linear-gradient(90deg, var(--color-argus-surface-2) 25%, var(--color-argus-surface-3) 50%, var(--color-argus-surface-2) 75%);
     background-size: 200% 100%;
     animation: shimmer 1.5s ease-in-out infinite;
   }
   ```

2. **Create `src/components/Skeleton.tsx`** — Skeleton primitive:
   - Props: variant ('line' | 'rect' | 'circle'), width, height, className, rounded (default true)
   - Renders a div with skeleton-shimmer class and appropriate dimensions
   - 'line': default height 16px, full width, rounded-md
   - 'rect': explicit width/height, rounded-lg
   - 'circle': equal width/height, rounded-full

3. **Create page-specific skeleton layouts** that match actual content shapes:
   - `src/features/dashboard/DashboardSkeleton.tsx` — 3 summary card skeletons (top row), position table skeleton, 2 bottom cards
   - `src/features/trades/TradesSkeleton.tsx` — Filter bar + stats row + 8 table rows
   - `src/features/performance/PerformanceSkeleton.tsx` — Period selector + 12-metric grid + chart rect + table
   - `src/features/system/SystemSkeleton.tsx` — 2-column grid with card skeletons

4. **Update each page and feature component** to show skeletons instead of `<LoadingState />`:
   - Dashboard features (AccountSummary, DailyPnlCard, MarketStatusBadge, OpenPositions, RecentTrades, HealthMini): each shows its own skeleton shape while loading
   - TradesPage: replace isLoading branch with TradesSkeleton
   - PerformancePage: replace isLoading branch with PerformanceSkeleton
   - SystemPage features: each shows skeleton shapes while loading

## Key Principle
Skeletons should be shaped like the actual content — card outlines, table row lines, chart rectangles. When data loads, content fades in ON TOP of the skeleton shape, so there's zero layout shift.

## Verification
- `npm run build` — zero errors
- `npm run lint` — clean
- Throttle network in devtools → skeletons visible and shaped correctly
- Fast network → brief skeleton flash then content appears
- No layout shift when content replaces skeleton
- Shimmer runs at 60fps
```

---

## Session 3 Prompt

```
# ARGUS Sprint 16 — Session 3: Staggered Entry Animations

## Context
Sprint 16, Session 3 of 10. Sessions 1-2 added page transitions and skeleton loading. This session adds staggered entry animations so content "assembles" when navigating to each page.

Read `src/utils/motion.ts` for the staggerContainer and staggerItem variants created in Session 1.

## This Session's Scope

Apply stagger animations to all 4 pages. Each page wraps its top-level container in `motion.div` with `staggerContainer` variants, and each major section gets `staggerItem` variants.

### DashboardPage.tsx
- Top-level div → `motion.div variants={staggerContainer(0.08)} initial="hidden" animate="show"`
- Summary cards row → `motion.div variants={staggerItem}`
- Each summary card inside gets sub-stagger with tighter delay (0.05)
- OpenPositions section → staggerItem
- Bottom row (RecentTrades + HealthMini) → staggerItem

### TradesPage.tsx
- Top-level div → stagger container
- Page header → staggerItem
- TradeFilters → staggerItem
- TradeStatsBar → staggerItem
- TradeTable → staggerItem

### PerformancePage.tsx
- Top-level div → stagger container
- Header + PeriodSelector → staggerItem
- MetricsGrid → staggerItem (plus internal sub-stagger on each MetricCard at 0.04 delay)
- Each chart → staggerItem
- StrategyBreakdown → staggerItem

### SystemPage.tsx
- Top-level div → stagger container
- Page header → staggerItem
- Grid columns → staggerItem
- EventsLog → staggerItem

## Critical Rule
Only animate on MOUNT (initial="hidden" animate="show"). When data refetches (React Query re-render), the page content should update in place WITHOUT replaying stagger animations. The variants pattern handles this correctly — `initial` only fires on mount, `animate` is the resting state.

## Verification
- Navigate to each page → content assembles with staggered fade+translate
- Navigate away and back → animation replays (new mount)
- Wait for auto-refetch → content updates silently, no re-animation
- Total animation duration per page < 500ms (stagger * items + item_duration)
- `npm run build && npm run lint` — clean
```

---

## Session 4 Prompt

```
# ARGUS Sprint 16 — Session 4: Number Morphing + P&L Flash Enhancement

## Context
Sprint 16, Session 4 of 10. This session makes financial numbers feel alive — hero equity counts up/down smoothly, P&L values flash with more emphasis on WebSocket updates.

## This Session's Scope

1. **Create `src/components/AnimatedNumber.tsx`:**
   - Uses requestAnimationFrame to interpolate between previous and new value
   - Props: value (number), format (function: number → string), duration (ms, default 400), className
   - Easing: ease-out cubic
   - On first render: display value immediately (no animation from 0)
   - On value change: animate from previous to new
   - Handle rapid updates: if a new value arrives during animation, interrupt and start new animation from current interpolated position
   - Use useRef for previous value tracking, no unnecessary re-renders

2. **Enhance `src/components/PnlValue.tsx`:**
   - Update flash keyframes in index.css — add subtle scale pulse (1.0 → 1.02 → 1.0) alongside background flash
   - Increase flash duration to 800ms
   - Add smooth color transition when value crosses zero (profit↔loss color change animates over 300ms)

3. **Update `src/features/dashboard/AccountSummary.tsx`:**
   - Replace static equity text with `<AnimatedNumber value={data.equity} format={formatCurrency} />`
   - Cash and Buying Power: use AnimatedNumber with shorter duration (200ms)

4. **Update `src/features/dashboard/DailyPnlCard.tsx`:**
   - Use AnimatedNumber for the hero daily P&L dollar value

5. **Update flash keyframes in `src/index.css`:**
   ```css
   @keyframes pnl-flash-profit {
     0% { background-color: rgba(34, 197, 94, 0.3); transform: scale(1.02); }
     50% { background-color: rgba(34, 197, 94, 0.15); }
     100% { background-color: transparent; transform: scale(1); }
   }
   @keyframes pnl-flash-loss {
     0% { background-color: rgba(239, 68, 68, 0.3); transform: scale(1.02); }
     50% { background-color: rgba(239, 68, 68, 0.15); }
     100% { background-color: transparent; transform: scale(1); }
   }
   ```

## Verification
- Start dev server (`python -m argus.api --dev` + `npm run dev`)
- Dashboard equity number smoothly counts between values
- P&L values flash with visible scale pulse on updates
- No jitter, no layout shift during animations
- Rapid successive updates handled cleanly
- `npm run build && npm run lint` — clean
```

---

## Session 5 Prompt

```
# ARGUS Sprint 16 — Session 5: Hover Feedback + Micro-Interactions

## Context
Sprint 16, Session 5 of 10. This session adds tactile feedback: cards lift on hover, table rows highlight smoothly, nav items get refined states.

## This Session's Scope

1. **`src/components/Card.tsx`** — Add optional hover lift:
   - New prop: `interactive?: boolean` (default false)
   - When interactive=true: `transition-all duration-150 hover:translate-y-[-1px] hover:shadow-lg hover:shadow-black/20`
   - Non-interactive cards: no hover effect
   - Update all Card usages where clicking is/will be supported

2. **Table row transitions** — Smooth hover backgrounds:
   - OpenPositions table rows: add `transition-colors duration-150` to existing hover:bg
   - TradeTable rows: same treatment + add cursor-pointer (prep for Session 9 detail panel)
   - Strategy breakdown table: same treatment

3. **`src/layouts/Sidebar.tsx`** — Refined desktop nav:
   - Active state: add 2px left border bar in accent color (absolute positioned)
   - Hover: slight icon scale (1.05) with transition
   - Tooltip: add 200ms delay before showing (CSS transition-delay or JS timeout)

4. **`src/layouts/MobileNav.tsx`** — Touch feedback:
   - Active tab: small accent-colored dot below icon (4px circle)
   - Active press state: scale(0.95) on tap via CSS :active pseudo-class

5. **CSS additions in `src/index.css`:**
   - Desktop-only hover check: `@media (hover: hover)` wrapper for hover effects
   - This prevents hover styles from sticking on touch devices

## Verification
- Desktop: hover over cards → subtle lift with shadow transition
- Desktop: hover over table rows → smooth background highlight
- Desktop: hover nav items → icon scales slightly, tooltip appears after brief delay
- Mobile: tap nav → brief scale-down feedback
- Mobile: NO hover effects persisting after touch
- `npm run build && npm run lint` — clean
```

---

## Session 6 Prompt

```
# ARGUS Sprint 16 — Session 6: Chart Animations + Sparklines

## Context
Sprint 16, Session 6 of 10. This session adds chart draw-in animations and dashboard sparklines for ambient awareness.

## This Session's Scope

1. **Create `src/components/Sparkline.tsx`** — Lightweight SVG sparkline:
   - Props: data (number[]), width (default 120), height (default 40), color (default argus-accent), fillOpacity (default 0.1), strokeWidth (default 1.5), className
   - Implementation: normalize data to fit SVG viewBox, generate polyline points, render SVG with polyline (stroke) and polygon (area fill below line)
   - Edge cases: empty array → render nothing, single point → horizontal line, all same values → horizontal line at center
   - No axes, labels, tooltips — pure ambient visualization
   - Responsive: SVG viewBox makes it scale with container

2. **Create `src/hooks/useSparklineData.ts`:**
   - Fetches `GET /api/v1/performance/month` for sparkline data
   - Extracts daily_pnl array → computes cumulative equity trend (for equity sparkline)
   - Extracts daily_pnl array → uses raw P&L values (for P&L sparkline)
   - 5 minute stale time (sparklines don't need real-time)
   - Returns: { equityTrend: number[], pnlTrend: number[], isLoading: boolean }

3. **Update `src/features/dashboard/AccountSummary.tsx`:**
   - Add Sparkline below the hero equity number showing 30-day equity trend
   - Color: argus-accent (blue)
   - Width: responsive (full card width minus padding)

4. **Update `src/features/dashboard/DailyPnlCard.tsx`:**
   - Add Sparkline showing recent daily P&L values
   - Color: argus-profit if net positive, argus-loss if net negative

5. **Chart draw-in animations:**
   - `src/features/performance/EquityCurve.tsx`: After chart creation in onChartReady, delay setData by 50ms so LW Charts animates the data appearance. If native animation isn't sufficient, wrap the chart container in a motion.div with a clip-path reveal from left to right over 500ms.
   - `src/features/performance/DailyPnlChart.tsx`: Same approach for histogram bars.

## Verification
- Dashboard shows sparklines on Account Equity and Daily P&L cards
- Sparklines render correctly with positive/negative/flat trends
- Sparklines are responsive (shrink on mobile, expand on desktop)
- Performance page: equity curve draws in from left on page load
- P&L histogram bars grow upward
- Chart animations only fire on mount, not on data refresh
- `npm run build && npm run lint` — clean
```

---

## Session 7 Prompt

```
# ARGUS Sprint 16 — Session 7: Empty States + Trade Slide-In

## Context
Sprint 16, Session 7 of 10. This session replaces generic "No data" messages with contextual, time-aware empty states and adds smooth trade slide-in animation.

## This Session's Scope

1. **Create `src/utils/marketTime.ts`:**
   - `getMarketContext()`: Returns { status, message } based on current ET time
   - Pre-market (before 9:30 ET): "Market opens in Xh Xm"
   - Market hours (9:30-16:00 ET): "Market is open"
   - After hours (16:00-20:00 ET): "After hours — market closed"
   - Closed (other times): "Market closed — next session: [day] 9:30 AM ET"
   - Account for weekends: next Monday
   - Use America/New_York timezone conversion

2. **Update empty states across all features:**

   **OpenPositions** (dashboard):
   - Pre-market: "No open positions — market opens in Xh Xm" + clock icon
   - Market hours: "No open positions — scanning for setups" + subtle animated pulse/radar
   - After hours/closed: "No open positions — market closed" + moon icon

   **RecentTrades** (dashboard):
   - "No trades today — first signal expected after 9:35 AM ET" (if before market)
   - "No trades today" + chart icon (during/after market)

   **TradeTable** (trades page):
   - With filters: "No trades match your filters — try adjusting the date range or strategy"
   - Without filters: "No trades recorded yet — trades appear here once the strategy takes a position"

   **EventsLog** (system):
   - "Listening for events..." + subtle animated dot

3. **Trade slide-in animation (RecentTrades):**
   - When new trades appear (React Query refetch after position.closed), the newest row should animate in
   - Use Framer Motion AnimatePresence on the trade list with layoutId on each item
   - New items enter with: opacity 0→1, translateY -8→0, brief highlight glow (bg flash)
   - Existing items don't re-animate

## Verification
- All empty states show contextual messages appropriate to current time
- Market time calculations handle timezone correctly
- Trade slide-in works when dev mode generates a new trade
- No flash of wrong empty state during loading (skeleton shows first)
- `npm run build && npm run lint` — clean
```

---

## Session 8 Prompt

```
# ARGUS Sprint 16 — Session 8: PWA Configuration

## Context
Sprint 16, Session 8 of 10. This session makes ARGUS installable as a PWA on iPhone/iPad.

## This Session's Scope

1. **Generate app icons:**
   - Create a simple script (Python with Pillow, or Node.js with canvas) that generates the "A" icon:
     - Background: #0f1117 (argus-bg)
     - Letter "A": #3b82f6 (argus-accent), bold, centered
     - Sizes: 192x192, 512x512 (regular), 192x192, 512x512 (maskable with padding), 180x180 (apple-touch-icon)
   - Save to `argus/ui/public/icons/` and `argus/ui/public/apple-touch-icon.png`
   - If Pillow isn't available, create SVG icons and convert, or create simple CSS-rendered icons

2. **Create `argus/ui/public/manifest.json`:**
   - name: "ARGUS Command Center", short_name: "ARGUS"
   - display: "standalone", background_color: "#0f1117", theme_color: "#0f1117"
   - orientation: "any"
   - Icons array with all sizes + maskable variants
   - start_url: "/"

3. **Create `argus/ui/public/sw.js`:**
   - Cache app shell (index.html, CSS, JS bundles) for offline shell loading
   - Network-first for /api/ and /ws/ paths (NEVER cache trading data)
   - Version-keyed cache name for clean updates
   - self.skipWaiting() + self.clients.claim() for immediate activation

4. **Update `argus/ui/index.html`:**
   - Add: `<link rel="manifest" href="/manifest.json" />`
   - Add: `<meta name="theme-color" content="#0f1117" />`
   - Add: `<meta name="apple-mobile-web-app-capable" content="yes" />`
   - Add: `<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />`
   - Add: `<meta name="apple-mobile-web-app-title" content="ARGUS" />`
   - Add: `<link rel="apple-touch-icon" href="/apple-touch-icon.png" />`

5. **Update `src/main.tsx`:**
   - Register service worker after app mount (production only check)
   - `if ('serviceWorker' in navigator) { window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js').catch(console.warn); }); }`

## Verification
- `npm run build` succeeds
- Serve built output with a static server: `npx serve dist`
- manifest.json loads correctly (check DevTools → Application → Manifest)
- Service worker registers (check DevTools → Application → Service Workers)
- Icons display correctly in manifest viewer
- Vite dev server still works normally (SW only in production)
- `npm run lint` — clean
```

---

## Session 9 Prompt

```
# ARGUS Sprint 16 — Session 9: Paper Trading Features

## Context
Sprint 16, Session 9 of 10. This session adds CSV export, trade drill-down panel, and emergency controls.

## This Session's Scope

### Backend (Python)

1. **CSV export endpoint in `argus/api/routes/trades.py`:**
   - `GET /api/v1/trades/export/csv` with optional filters (strategy_id, date_from, date_to)
   - Returns StreamingResponse with Content-Disposition attachment header
   - CSV columns: id, strategy_id, symbol, side, entry_price, entry_time, exit_price, exit_time, shares, pnl_dollars, pnl_r_multiple, exit_reason, hold_duration_seconds, commission
   - Requires auth

2. **Emergency controls in new `argus/api/routes/controls.py`:**
   - `POST /api/v1/controls/strategies/{strategy_id}/pause` — set strategy.is_active = False
   - `POST /api/v1/controls/strategies/{strategy_id}/resume` — set strategy.is_active = True
   - `POST /api/v1/controls/positions/{position_id}/close` — call order_manager to close position
   - `POST /api/v1/controls/emergency/flatten` — call order_manager.emergency_flatten_all()
   - `POST /api/v1/controls/emergency/pause` — pause all strategies
   - All require auth. Return JSON confirmation.
   - Register router in `argus/api/routes/__init__.py`

3. **Backend tests** in `tests/api/test_controls.py`:
   - Test each control endpoint (auth required, correct behavior)
   - Test CSV export (format, filtering, auth)

### Frontend

4. **Create `src/features/trades/TradeDetailPanel.tsx`:**
   - Slide-in panel: desktop = right side 40% width, mobile = full screen from bottom
   - Framer Motion: animate x (desktop) or y (mobile) with spring physics
   - Content: symbol (large), strategy badge, entry/exit prices+times, P&L (dollars/percent/R), hold duration, exit reason with human-readable explanation, stop/T1/T2 levels, commission, market regime
   - Close: X button, click overlay backdrop, Escape key
   - Exit reason explanations: T1="Target 1 hit", T2="Target 2 hit", SL="Stop loss triggered", TIME="Time stop expired", EOD="End of day flatten", MANUAL="Manual close"

5. **Update `src/features/trades/TradeTable.tsx`:**
   - Make rows clickable (cursor-pointer)
   - onClick → set selectedTradeId state
   - Pass selectedTradeId to TradeDetailPanel

6. **Update `src/pages/TradesPage.tsx`:**
   - Add "Export CSV" button in header (Download icon from lucide-react)
   - Render TradeDetailPanel with selected trade state
   - Export button calls `/api/v1/trades/export/csv` and triggers browser download

7. **Create `src/hooks/useControls.ts`:**
   - useMutation hooks for each control action
   - Invalidate relevant queries on success (positions, strategies)
   - Return loading/error state for UI feedback

8. **Create `src/features/dashboard/EmergencyControls.tsx`:**
   - "Emergency Controls" card with red accent
   - "Flatten All" button → confirmation modal → API call
   - "Pause All" button → confirmation modal → API call
   - Only show in paper/live mode (not dev mode hint)

9. **Update `src/features/system/StrategyCards.tsx`:**
   - Add pause/resume toggle button on each strategy card
   - Paused: amber border/badge, "PAUSED" label
   - Active: normal styling

10. **Add EmergencyControls to SystemPage.tsx** (bottom of page)

## Verification
- Click trade row → panel slides in from right (desktop) or up (mobile)
- Panel shows all trade details correctly formatted
- Escape/backdrop click closes panel
- "Export CSV" downloads a correctly formatted file
- Emergency flatten shows confirmation then calls API
- Strategy pause/resume toggles correctly with visual feedback
- All new backend endpoints require auth
- Backend tests pass: `python -m pytest tests/api/test_controls.py -v`
- `npm run build && npm run lint` — clean
```

---

## Session 10 Prompt

```
# ARGUS Sprint 16 — Session 10: Tauri Shell + Final Review

## Context
Sprint 16, Session 10 of 10 (final session). This session sets up the Tauri v2 desktop shell and conducts final cross-device verification.

## This Session's Scope

### Tauri Setup

1. **Initialize Tauri v2 in the UI directory:**
   - If Rust toolchain is available: `cd argus/ui && npm install @tauri-apps/cli@next && npx tauri init`
   - If Rust is NOT available: create the directory structure and config files manually for Steven to build locally

2. **Create/configure `src-tauri/tauri.conf.json`:**
   - productName: "ARGUS", identifier: "com.argus.trading"
   - Window: 1400x900, min 800x600, title "ARGUS Command Center"
   - Tray icon enabled
   - Build paths: frontendDist="../dist", devUrl="http://localhost:5173"

3. **Create `src-tauri/src/main.rs`:**
   - System tray with icon (reuse PWA icon)
   - Tray menu: "Show ARGUS" (toggle window visibility), separator, "Quit"
   - Window close → hide to tray (not quit)
   - Minimal Rust — no custom backend logic

4. **Create `src/utils/platform.ts`:**
   - `isTauri()`: checks for `__TAURI__` in window
   - `isPWA()`: checks display-mode: standalone
   - `isWeb()`: neither Tauri nor PWA

5. **Update `package.json`** with Tauri scripts:
   ```json
   "scripts": {
     "tauri": "tauri",
     "tauri:dev": "tauri dev",
     "tauri:build": "tauri build"
   }
   ```

### Final Review

Run through every page on every breakpoint and verify the complete Sprint 16 feature set:

**Dashboard:**
- [ ] Stagger animation on mount
- [ ] Account Equity animates between values (AnimatedNumber)
- [ ] Sparklines on Account Equity and Daily P&L cards
- [ ] Open positions: contextual empty state based on market time
- [ ] P&L flash with scale pulse on WebSocket updates
- [ ] Card hover lift (interactive cards only)
- [ ] Emergency controls section visible and functional

**Trades:**
- [ ] Stagger animation on mount
- [ ] Skeleton loading state (shaped like content)
- [ ] Table rows clickable → trade detail panel slides in
- [ ] Trade detail panel: correct data, close on Escape/backdrop
- [ ] Export CSV button downloads file
- [ ] Empty states contextual (with/without filters)

**Performance:**
- [ ] Stagger animation on mount
- [ ] Skeleton loading
- [ ] Equity curve draw-in animation
- [ ] Daily P&L histogram grow animation
- [ ] Metrics grid sub-stagger

**System:**
- [ ] Stagger animation on mount
- [ ] Strategy cards with pause/resume buttons
- [ ] Events log empty state with animated listening dot
- [ ] Emergency controls at bottom

**Cross-cutting:**
- [ ] Page transitions between all routes (fade + translate)
- [ ] PWA manifest loads correctly
- [ ] Service worker registered
- [ ] Mobile: bottom nav with active dot indicator
- [ ] Mobile: touch feedback on nav items
- [ ] Desktop: sidebar with active left border indicator
- [ ] All hover effects desktop-only (media query check)
- [ ] `npm run build` — zero errors
- [ ] `npm run lint` — clean

Fix any issues found during review. Commit everything.

## Docs Status
After completing all fixes, output a brief Docs Status noting:
- Sprint 16 complete
- Any decisions made during implementation
- Which docs need updating (CLAUDE.md, 10_PHASE3_SPRINT_PLAN.md, etc.)
```

---

# PART 3: CODE REVIEW PLAN

## When to Review

Conduct code review after **three natural checkpoints:**

| Review | After Sessions | Focus | Est. Review Time |
|--------|---------------|-------|-----------------|
| **Review A** | Sessions 1–3 | Animation foundation verified | ~30 min |
| **Review B** | Sessions 4–7 | Full UX polish verified | ~45 min |
| **Review C** | Sessions 8–10 | Complete sprint verified, docs updated | ~60 min |

### Why Three Reviews (Not One)

- **Review A** catches animation architecture issues before they compound across 7 more sessions
- **Review B** validates the UX polish pillar (your highest priority) before moving to infrastructure/backend work
- **Review C** is the final gate before marking the sprint complete

## What Materials Are Needed

For each review, Steven should:

1. **Pull latest code:** `git pull` to get all commits from the Claude Code sessions
2. **Run the app:** `cd argus/ui && npm install && npm run dev` (in one terminal) + `python -m argus.api --dev` (in another)
3. **Take screenshots** of each page at each breakpoint you can test:
   - iPhone (393px) — use browser DevTools mobile simulator
   - iPad portrait (834px)
   - Desktop (1512px)
4. **Note any issues** — visual bugs, animation timing that feels wrong, features that don't match spec
5. **Run tests:** `python -m pytest tests/ -x` to confirm no regressions
6. **Run build:** `cd argus/ui && npm run build` to confirm production build works

## Review Procedure

1. **Start a new Claude.ai conversation** using the handoff brief (Part 4)
2. **Share screenshots** if possible (upload images to the conversation)
3. **Report issues** found during your testing
4. **Claude reviews the code** by reading the repo files
5. **Claude flags** any architectural concerns, missing pieces, or quality issues
6. **Generate fix list** if needed — items for the next Claude Code session
7. **After Review C:** Claude drafts all document updates (Decision Log, Project Knowledge, CLAUDE.md, Sprint Plan)

---

# PART 4: CODE REVIEW HANDOFF BRIEFS

## Review A Handoff Brief (After Sessions 1–3)

```
# ARGUS Sprint 16 — Code Review A (Animation Foundation)

## Context
Sprint 16 is implementing Desktop/PWA + UX Polish for the ARGUS Command Center. Sessions 1–3 of 10 are complete. This review validates the animation foundation before building the remaining 7 sessions on top of it.

## What Was Implemented
- **Session 1:** Framer Motion installed, motion.ts animation constants/variants, AnimatePresence page transitions in AppShell
- **Session 2:** Skeleton loading system (Skeleton primitive + page-specific skeleton layouts replacing LoadingState spinners)
- **Session 3:** Staggered entry animations on all 4 pages (Dashboard, Trades, Performance, System)

## Repo
https://github.com/stevengizzi/argus.git — pull latest and read the changes.

## What I Need You to Review

1. **Animation architecture:** Read `src/utils/motion.ts` and confirm the variants pattern is correct and composable. Are the timing values right? Is the stagger pattern used consistently across pages?

2. **Page transitions:** Read `src/layouts/AppShell.tsx` — is AnimatePresence correctly integrated with React Router? Any issues with exit animations or route keys?

3. **Skeleton system:** Read `src/components/Skeleton.tsx` and the page-specific skeleton layouts. Do they match the actual content shapes? Is the shimmer CSS performant?

4. **Stagger implementation:** Check each page component — are stagger animations only firing on mount (not on data refetch)? Are the motion.div wrappers correctly placed?

5. **Build health:** Confirm `npm run build` produces zero errors and `npm run lint` is clean.

## My Testing Notes
[Steven: paste your notes here — any visual issues, timing concerns, bugs noticed]

## Screenshots
[Steven: upload screenshots of each page at desktop and mobile widths]

## What Comes Next
Sessions 4–7 build on this foundation: number morphing, hover feedback, chart animations, sparklines, empty states. If there are architectural issues, now is the time to catch them.
```

---

## Review B Handoff Brief (After Sessions 4–7)

```
# ARGUS Sprint 16 — Code Review B (UX Polish Complete)

## Context
Sprint 16 UX Polish pillar is complete (Sessions 1–7). This review validates the full user experience before moving to infrastructure (PWA, Tauri) and backend features (controls, CSV export) in Sessions 8–10.

## What Was Implemented (Sessions 4–7)
- **Session 4:** AnimatedNumber component (requestAnimationFrame interpolation), enhanced PnlValue flash with scale pulse, hero equity countup on Dashboard
- **Session 5:** Card hover lift (interactive prop), table row transitions, Sidebar active indicator (left border), MobileNav active dot + touch feedback, desktop-only hover media query
- **Session 6:** Sparkline SVG component, dashboard sparklines (equity trend, P&L trend), useSparklineData hook, equity curve draw-in, P&L histogram grow animation
- **Session 7:** Contextual empty states (time-aware messages), marketTime utility, trade slide-in animation on RecentTrades

## Previously Reviewed (Sessions 1–3)
- Framer Motion + page transitions ✅
- Skeleton loading system ✅
- Staggered entry animations ✅

## Repo
https://github.com/stevengizzi/argus.git — pull latest.

## What I Need You to Review

1. **AnimatedNumber:** Read `src/components/AnimatedNumber.tsx`. Does it handle rapid updates correctly? Is the rAF cleanup proper? Performance concerns?

2. **Sparklines:** Read `src/components/Sparkline.tsx`. SVG rendering correct? Edge cases handled (empty, single point, all same)? Responsive behavior?

3. **Hover system:** Check that hover effects are desktop-only (media query). Card interactive prop used correctly. No hover sticking on touch devices.

4. **Empty states:** Read the contextual empty state implementations. Market time calculations correct? Messages appropriate for each context?

5. **Overall feel:** Based on screenshots, does the app feel cohesive? Do animations complement each other or feel disjointed? Any timing adjustments needed?

6. **Performance:** Any concerns about multiple Framer Motion instances, SVG sparklines, or rAF animations running simultaneously?

## My Testing Notes
[Steven: paste your notes — how does it FEEL? What's working, what's off?]

## Screenshots
[Steven: upload screenshots across all breakpoints, especially Dashboard with sparklines]

## What Comes Next
Sessions 8–10: PWA setup, paper trading features (CSV export, trade detail panel, emergency controls), Tauri desktop shell, final cross-device review.
```

---

## Review C Handoff Brief (After Sessions 8–10 — Final)

```
# ARGUS Sprint 16 — Code Review C (Sprint Complete)

## Context
Sprint 16 is complete (all 10 sessions). This is the final review before marking the sprint done and updating all project documents.

## What Was Implemented (Sessions 8–10)
- **Session 8:** PWA configuration (manifest.json, service worker, app icons, Apple meta tags)
- **Session 9:** Backend CSV export endpoint, emergency control endpoints (pause/resume/flatten/close), trade drill-down panel (slide-in), export button, strategy pause/resume UI, backend tests
- **Session 10:** Tauri v2 shell setup (config, tray icon, minimal Rust), platform detection utility, final cross-device review, bug fixes

## Full Sprint 16 Deliverables
- [x] Framer Motion page transitions
- [x] Skeleton loading states (all pages)
- [x] Staggered entry animations (all pages)
- [x] AnimatedNumber (hero equity countup)
- [x] Enhanced P&L flash with scale pulse
- [x] Card hover lift + table row transitions
- [x] Sidebar/MobileNav polish (active indicators, touch feedback)
- [x] SVG Sparklines on Dashboard cards
- [x] Chart draw-in animations (equity curve, P&L histogram)
- [x] Contextual empty states (time-aware)
- [x] Trade slide-in animation
- [x] PWA (manifest, service worker, icons, iOS meta tags)
- [x] CSV trade export
- [x] Trade detail panel (slide-in)
- [x] Emergency controls (flatten, pause, close)
- [x] Strategy pause/resume
- [x] Tauri v2 desktop shell
- [x] Platform detection utility

## Repo
https://github.com/stevengizzi/argus.git — pull latest.

## What I Need You to Review

1. **Complete code review:** Scan all new and modified files for quality, consistency, and correctness.

2. **Backend:** Read the new control endpoints and CSV export. Auth on all routes? Error handling? Tests passing?

3. **Trade detail panel:** Correct data display? Responsive (desktop slide-in vs mobile full-screen)? Close behavior (Escape, backdrop, X button)?

4. **PWA:** manifest.json valid? Service worker caching strategy correct? Icons generated at all required sizes? Apple meta tags complete?

5. **Tauri:** Config correct? If not buildable in Claude Code, are the files ready for Steven to build locally?

6. **Test count:** How many new tests? Update the count for docs.

7. **Draft all document updates:** This is the big one. After review, draft copy-paste content for:
   - `05_DECISION_LOG.md` — Any new DEC entries needed?
   - `02_PROJECT_KNOWLEDGE.md` — Update Current Project State (Sprint 16 complete), Build Track queue
   - `10_PHASE3_SPRINT_PLAN.md` — Move Sprint 16 to completed table, update test count
   - `CLAUDE.md` — Update Current State, add any new commands, note Sprint 16 results
   - `03_ARCHITECTURE.md` — Update Section 4.1 (Frontend) with new components and libraries

## My Testing Notes
[Steven: paste comprehensive testing notes across all devices and features]

## Screenshots
[Steven: upload final screenshots of all pages across all breakpoints]

## Known Issues
[Steven: list any issues found during Session 10 final review that weren't fixed]
```

---

# PART 5: QUICK REFERENCE

## Session → Review Mapping

```
Session 1  (Animation Foundation)     ─┐
Session 2  (Skeleton Loading)          ├─→ Review A
Session 3  (Stagger Animations)       ─┘
Session 4  (Number Morphing)          ─┐
Session 5  (Hover Feedback)            │
Session 6  (Charts + Sparklines)       ├─→ Review B
Session 7  (Empty States)             ─┘
Session 8  (PWA)                      ─┐
Session 9  (Paper Trading Features)    ├─→ Review C (Final)
Session 10 (Tauri + Final Review)     ─┘
```

## Estimated Timeline

| Activity | Duration | Notes |
|----------|----------|-------|
| Sessions 1–3 | ~9h | Animation foundation |
| Review A | ~30 min | Catch architecture issues early |
| Sessions 4–7 | ~11h | UX polish complete |
| Review B | ~45 min | Validate the soul of the sprint |
| Sessions 8–10 | ~12h | Infrastructure + backend + final |
| Review C | ~60 min | Final gate + docs update |
| **Total** | **~34h** | Consistent with Sprint 15 pacing |

## Emergency Recovery

If a session goes wrong:
1. `git stash` or `git reset --hard HEAD~1` to undo last commit
2. Re-read the session prompt and retry
3. If the issue is architectural (e.g., Framer Motion pattern doesn't work), bring it to Review A/B for redesign

## Dependencies Between Sessions

```
Session 1 (motion.ts, AnimatePresence) ──→ Session 3 (stagger uses motion.ts)
                                        ──→ Session 4 (can use motion.ts easing)
                                        ──→ Session 7 (AnimatePresence for trade slide-in)
Session 2 (Skeleton) ──→ independent (no other session depends on it)
Session 6 (Sparkline) ──→ independent
Session 8 (PWA) ──→ independent
Session 9 (backend controls) ──→ Session 10 uses platform.ts
```

Session 1 is the only hard prerequisite. Sessions 2, 4, 5, 6, 7, 8 could theoretically be reordered, but the proposed order builds the most value incrementally.
