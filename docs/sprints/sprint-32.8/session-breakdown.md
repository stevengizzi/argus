# Sprint 32.8 Session Breakdown

## Dependency Graph

```
S1 (Backend) ──┐
S2 (Dashboard) ─┤── All parallel, zero file overlap
S3 (Arena UI) ──┤
S4 (Trades Visual) ─┬── S4 parallel with S1/S2/S3
                     └── S5 (Trades Features) sequential after S4
S6f (Visual Fix Contingency) — after any frontend session
```

## Sessions

### Session 1: Arena Pipeline (Backend)
**Objective:** Direct TickEvent subscription for Arena charts + pre-market candle store widening.

| Column | Details |
|--------|---------|
| Creates | None |
| Modifies | `argus/api/websocket/arena_ws.py`, `argus/data/intraday_candle_store.py` |
| Integrates | N/A — self-contained backend, existing frontend consumes via unchanged WS message format |
| Parallelizable | **Yes** — zero file overlap with S2/S3/S4 |

**Compaction Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Pre-flight context reads | 4 (`arena_ws.py`, `intraday_candle_store.py`, `events.py`, `order_manager.py` for TickEvent/PUE reference) | 4 |
| New tests | ~8 | 4 |
| Complex integration wiring (TickEvent subscription + tracked_symbols filter + forming-candle coordination) | 1 | 3 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **13 (Medium)** |

---

### Session 2: Dashboard Layout Refactor
**Objective:** Consolidate Dashboard into 4-row no-scroll layout with VitalsStrip, 70/30 positions+timeline, and matched-height secondary cards.

| Column | Details |
|--------|---------|
| Creates | `argus/ui/src/features/dashboard/VitalsStrip.tsx` |
| Modifies | `argus/ui/src/pages/DashboardPage.tsx`, positions section component (toggle relocation) |
| Integrates | N/A — reorganizes existing components |
| Parallelizable | **Yes** — zero file overlap with S1/S3/S4 |

**Compaction Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (VitalsStrip.tsx) | 2 |
| Files modified | 2 | 2 |
| Pre-flight context reads | 4 (DashboardPage.tsx, existing card components, useDashboardSummary, VixRegimeCard) | 4 |
| New tests | ~5 | 2.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (VitalsStrip.tsx likely >150 lines) | 1 | 2 |
| **Total** | | **12.5 (Medium)** |

---

### Session 3: Arena UI Polish
**Objective:** Remove card borders, add entry markers, auto-zoom to entry, reduce label clutter, label progress bar, filter stats.

| Column | Details |
|--------|---------|
| Creates | None |
| Modifies | `ArenaCard.tsx`, `MiniChart.tsx`, `ArenaPage.tsx`, `ArenaStatsBar.tsx` |
| Integrates | S1's pre-market candles flow through existing pipeline (no wiring needed) |
| Parallelizable | **Yes** — zero file overlap with S1/S2/S4 |

**Compaction Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 4 | 4 |
| Pre-flight context reads | 4 (the 4 files being modified) | 4 |
| New tests | ~6 | 3 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **11 (Medium)** |

---

### Session 4: Trades Visual Unification + Hotkeys
**Objective:** Unify Live/Shadow Trades tab styling to Shadow's denser, higher-contrast look. Add `l`/`s` hotkeys.

| Column | Details |
|--------|---------|
| Creates | None |
| Modifies | `TradesPage.tsx`, `ShadowTradesTab.tsx`, `TradeTable.tsx`, `TradeStatsBar.tsx` |
| Integrates | N/A — styling-only changes |
| Parallelizable | **Yes** — zero file overlap with S1/S2/S3 |

**Compaction Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 4 | 4 |
| Pre-flight context reads | 4 | 4 |
| New tests | ~4 | 2 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **10 (Medium)** |

---

### Session 5: Trades Feature Additions
**Objective:** Add Outcome toggle on Shadow Trades, time presets, infinite scroll replacing pagination, sortable columns, Reason tooltip.

| Column | Details |
|--------|---------|
| Creates | `argus/ui/src/features/trades/SharedTradeFilters.tsx` (extracted shared filter bar) |
| Modifies | `TradesPage.tsx`, `ShadowTradesTab.tsx`, `TradeFilters.tsx`, `useShadowTrades.ts` |
| Integrates | S4's unified styling (builds on S4's visual foundation) |
| Parallelizable | **No** — depends on S4 (file overlap in TradesPage.tsx, ShadowTradesTab.tsx) |

**Compaction Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (SharedTradeFilters.tsx) | 2 |
| Files modified | 4 | 4 |
| Pre-flight context reads | 4 | 4 |
| New tests | ~6 | 3 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13 (Medium)** |

---

### Session 6f: Visual Review Contingency
**Objective:** Fix any visual issues identified during hot-reload review of S2/S3/S4/S5.

| Column | Details |
|--------|---------|
| Creates | None |
| Modifies | Any frontend file from S2/S3/S4/S5 as needed |
| Integrates | N/A |
| Parallelizable | No — reactive to review findings |

**Compaction Score:** ≤8 by definition (surgical fixes only).

---

## Summary

| Session | Title | Score | Parallel | Depends On |
|---------|-------|-------|----------|------------|
| S1 | Arena Pipeline (Backend) | 13 | Yes | — |
| S2 | Dashboard Layout Refactor | 12.5 | Yes | — |
| S3 | Arena UI Polish | 11 | Yes | — |
| S4 | Trades Visual Unification | 10 | Yes | — |
| S5 | Trades Feature Additions | 13 | No | S4 |
| S6f | Visual Review Contingency | ≤8 | No | S2–S5 |

All sessions ≤13. No sessions require splitting.
