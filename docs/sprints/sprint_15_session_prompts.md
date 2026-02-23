# Sprint 15 — Claude Code Session Prompts

Copy-paste these one at a time into fresh Claude Code conversations. Commit and push between each session.

---

## Session 1: Foundation

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 1 (Foundation). Follow the spec exactly — color tokens, format.ts, AppShell layout, Sidebar, MobileNav, React Router routes, TanStack Query provider, and install `lightweight-charts`. Run `npm run build` before you're done. Check the Session 1 gate checklist in the spec.
```

---

## Session 2: Shared Components

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 2 (Shared Components). Build all shared primitives: Card, CardHeader, StatusDot, PnlValue (with flash animation), MetricCard, DataTable (with hideBelow responsive column hiding), Badge, LoadingState, EmptyState. Add the CSS keyframes for pnl-flash and pulse. Follow the spec exactly for props, styling, and Tailwind classes. Run `npm run build` before you're done. Check the Session 2 gate checklist in the spec.
```

---

## Session 3: Data Layer

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 3 (Data Layer). Build all TanStack Query hooks (useAccount, usePositions, useTrades, usePerformance, useHealth, useStrategies) and the enhanced Zustand live store (typed price updates, heartbeat tracking, recent events buffer, QueryClient integration for cache invalidation on WebSocket events). Follow the spec exactly for endpoint URLs, polling intervals, and WebSocket event handling. Run `npm run build` before you're done. Check the Session 3 gate checklist in the spec.
```

---

## Session 4: Dashboard Page

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 4 (Dashboard Page). Build all dashboard components: AccountSummary, DailyPnlCard, MarketStatusBadge, OpenPositionsTable (with WebSocket price integration and P&L flash animation), RecentTrades, HealthMini. Wire up the grid layout with all three responsive breakpoints (<640px phone, 640-1023px tablet, ≥1024px desktop). Connect to the TanStack Query hooks and Zustand live store from Session 3. Run `npm run build` before you're done. Check the Session 4 gate checklist in the spec.
```

---

## Session 5: Trade Log Page

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 5 (Trade Log Page). Build TradeFilters (strategy dropdown, outcome toggle, date range), TradeStatsBar, and TradeTable with pagination, row coloring (green/red tint for wins/losses), and exit reason badges (T1/T2=green, SL=red, TIME=amber, EOD=gray). Filters should persist in URL query params. Three responsive breakpoints for the table columns. Run `npm run build` before you're done. Check the Session 5 gate checklist in the spec.
```

---

## Session 6: Performance Page + Charts

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 6 (Performance Page). Build the reusable LWChart.tsx wrapper component first (Lightweight Charts with ResizeObserver, cleanup, dark theme defaults from chartTheme.ts). Then build: PeriodSelector, MetricsGrid, EquityCurveChart (Lightweight Charts AreaSeries — cumulative P&L), DailyPnlChart (Lightweight Charts HistogramSeries — green/red bars), StrategyBreakdown table, and chartTheme.ts with shared config for both Lightweight Charts and Recharts. Follow the spec exactly for chart heights at each breakpoint, dark theme colors, and data format. Run `npm run build` before you're done. Check the Session 6 gate checklist in the spec.
```

---

## Session 7: System Page

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 7 (System Page). Build SystemOverview (status dot, uptime, mode, broker/data sources, key timestamps), ComponentStatusList (sorted by severity), StrategyCards (name, active status, pipeline stage badge, capital, P&L, trade count, config summary), and EventsLog (collapsible, last 20 WebSocket events with colored type badges, auto-scroll, clear button). Events log default collapsed on mobile, expanded on desktop. Run `npm run build` before you're done. Check the Session 7 gate checklist in the spec.
```

---

## Session 8: Polish & QA

```
Read `docs/sprints/SPRINT_15_SPEC.md` and implement Session 8 (Polish & QA). Do the full responsive audit at 393px (iPhone 16 Pro), 834px (iPad Pro 11" portrait), 1194px (iPad landscape), and 1512px (MacBook Pro 16"). Verify all loading, error, and empty states render correctly on every page. Test WebSocket reconnection behavior. Check dark theme contrast — no white backgrounds or unreadable text anywhere. Ensure touch targets are min 44px on interactive elements. Verify iPhone safe area padding on bottom nav. Clean up any console.log statements. Run `npm run build` AND `npm run lint` — both must pass clean. Check the Session 8 gate checklist in the spec.
```
