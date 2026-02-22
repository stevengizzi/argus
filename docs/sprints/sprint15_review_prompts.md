# Sprint 15 Code Review Prompts

Paste these into new Claude.ai conversations at each review checkpoint. Attach screenshots from all 3 devices (iPhone 16 Pro, iPad Pro 11", MacBook Pro 16") with each prompt.

---

## Review 1: After Session 1 (Foundation + Layout)

```
Sprint 15 Code Review — Session 1 (Foundation + Layout)

I just completed Session 1 of Sprint 15 (Command Center Frontend). This session built:
- Extended Tailwind v4 color tokens (argus-bg, argus-surface-1/2/3, argus-profit/loss, etc.)
- format.ts utility (currency, percent, P&L, duration, time formatters)
- AppShell layout with responsive navigation
- Sidebar (desktop ≥1024px icon rail) and MobileNav (bottom tabs <1024px)
- React Router nested routes for 4 pages (Dashboard, Trades, Performance, System)
- TanStack Query provider
- lightweight-charts npm package installed

Key design decisions:
- DEC-104: Dual chart libraries (Lightweight Charts for financial time-series, Recharts for non-temporal)
- DEC-105: Three breakpoints — <640px phone (iPhone 16 Pro 393px), 640–1023px tablet (iPad Pro 11" 834px portrait), ≥1024px desktop (iPad landscape 1194px / MacBook 1512px)
- Phone + tablet: bottom tab bar. Desktop: 64px icon sidebar.
- Dark theme only. Single-user trading tool.

I'm attaching screenshots from all 3 devices. Please review:
1. Does the layout shell feel right for a trading command center?
2. Are the breakpoint transitions clean? Especially iPad portrait at 834px.
3. Is the navigation intuitive across all 3 form factors?
4. Any spacing, sizing, or visual hierarchy issues?
5. Does the color system look cohesive?

The full spec is at docs/sprints/SPRINT_15_SPEC.md in the repo if you need details.
```

---

## Review 2: After Session 4 (Dashboard Page)

```
Sprint 15 Code Review — Session 4 (Dashboard Page)

I just completed Session 4 of Sprint 15. Sessions 1-4 are now done. The Dashboard page is the primary view — what I'll look at most during trading hours (10:30 PM+ Taipei time). It includes:

- Account summary (equity, cash, buying power)
- Daily P&L card with trade count
- Market status badges (open/closed, paper mode)
- Open positions table with real-time price updates via WebSocket
- P&L flash animation (600ms green/red fade on price updates)
- Recent trades list (last 8)
- System health mini-display

Data layer (Sessions 2-3) provides:
- TanStack Query hooks for all REST endpoints (10-30s polling)
- WebSocket → Zustand store for live price updates
- WS events trigger TanStack Query cache invalidation (position.closed → refetch positions/account/trades)
- Price updates flow: WS → Zustand → merged into position table for tick-level responsiveness

Responsive behavior:
- Phone (<640px): stacked single column, hero equity number, compact position rows (symbol/P&L/R)
- Tablet (640-1023px): two-column grid, more table columns (symbol/entry/current/P&L/R/hold time)
- Desktop (≥1024px): full 3-column top row, 11-column position table, side-by-side recent trades + health

I'm attaching screenshots from all 3 devices. Please review:
1. Information hierarchy — is the most important info (equity, P&L, open positions) prominent enough?
2. Does it feel like a Bloomberg-meets-modern-fintech command post?
3. Position table readability — can I scan P&L at a glance on each device?
4. Are the compact mobile rows informative enough, or do I need more columns?
5. Any layout, spacing, or visual issues on any device?
6. Does the mock data render correctly across all components?

The full spec is at docs/sprints/SPRINT_15_SPEC.md in the repo.
```

---

## Review 3: After Session 6 (Performance + Charts)

```
Sprint 15 Code Review — Session 6 (Performance Page + Charts)

I just completed Session 6 of Sprint 15. The Performance page is now live with:

- Period selector (today/week/month/all) as tab bar
- Metrics grid: 6 key metrics (total trades, win rate, profit factor, Sharpe, max drawdown, net P&L)
- Equity curve: TradingView Lightweight Charts AreaSeries (cumulative P&L over time)
- Daily P&L histogram: Lightweight Charts HistogramSeries (green/red bars per day)
- Strategy breakdown table (per-strategy metrics)
- chartTheme.ts with shared dark theme config for both Lightweight Charts and Recharts
- Reusable LWChart.tsx wrapper component (ResizeObserver, cleanup, dark theme defaults)

This is the first time Lightweight Charts appears in the app (DEC-104). Key things to verify:
- Financial time axis handles trading day gaps correctly (no weekend gaps)
- Crosshair with price/date tracking works
- Dark theme integration (argus-bg background, argus-border grid lines, argus-text-dim axis labels)
- Charts resize properly when switching between devices / rotating iPad
- Histogram bars are clearly green (profit days) and red (loss days)

Responsive behavior:
- Chart heights: 300/250px desktop, 220/200px tablet, 180/160px mobile (equity/P&L respectively)
- Metrics grid: 2 cols phone → 3 cols tablet → 6 cols desktop

I'm attaching screenshots from all 3 devices. Please review:
1. Do the charts look professional and readable on each device?
2. Is the equity curve gradient fill visible but not overwhelming?
3. Are the P&L histogram bars clearly distinguishable (green vs red)?
4. Does the crosshair feel responsive?
5. Metrics grid — is the layout balanced at each breakpoint?
6. Any chart rendering artifacts, sizing issues, or theme inconsistencies?

The full spec is at docs/sprints/SPRINT_15_SPEC.md in the repo.
```

---

## Review 4: After Session 8 (Final Polish — Full Walkthrough)

```
Sprint 15 Code Review — Session 8 (Final Polish + Full Walkthrough)

Sprint 15 is complete. All 8 sessions implemented. This is the final review before merging. The Command Center now has 4 fully functional pages:

1. **Dashboard**: Account summary, daily P&L, market status, open positions (real-time WS prices), recent trades, system health mini
2. **Trade Log**: Filtered trade history (strategy, outcome, date range), stats bar, paginated table with exit reason badges
3. **Performance**: Period selector, 6-metric grid, equity curve (Lightweight Charts area), daily P&L histogram (Lightweight Charts histogram), strategy breakdown
4. **System**: System overview (uptime, mode, broker/data sources), component health status, strategy cards, collapsible events log

Session 8 specifically addressed:
- Responsive audit at 393px (iPhone), 834px (iPad portrait), 1194px (iPad landscape), 1512px (MacBook)
- Loading, error, and empty states on all pages
- WebSocket reconnection behavior
- Dark theme contrast verification
- Touch target sizes (min 44px on touch devices)
- iPhone safe area padding
- Build verification (zero errors + clean lint)
- Console.log cleanup

I'm attaching screenshots of ALL 4 pages from ALL 3 devices (12 screenshots total). Please review:
1. Full walkthrough — any page that feels unfinished or rough?
2. Visual consistency across pages — do they feel like the same app?
3. Responsive behavior — anything broken or awkward on any device?
4. Information density — too sparse anywhere? Too crowded?
5. Is this something I'd be proud to use as my daily trading tool?
6. Any issues that should be fixed before we move to Sprint 16 (Desktop/PWA)?
7. Anything that should be logged as a defect or deferred item?

The full spec is at docs/sprints/SPRINT_15_SPEC.md in the repo.
```
