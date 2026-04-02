# Sprint 32.8 Design Summary

**Sprint Goal:** Fix Arena chart latency (bypass 1s Order Manager throttle), add pre-market candle context, and polish the Arena/Dashboard/Trades UI for daily operational use.

**Session Breakdown:**
- Session 1: Arena pipeline backend — direct TickEvent subscription for chart data, pre-market candle store widening, trail stop dict lookup
  - Creates: none
  - Modifies: `argus/api/websocket/arena_ws.py`, `argus/data/intraday_candle_store.py`
  - Integrates: N/A (self-contained backend changes)
- Session 2: Dashboard layout refactor — vitals strip, 70/30 positions+timeline layout, secondary card consolidation
  - Creates: `argus/ui/src/features/dashboard/VitalsStrip.tsx`
  - Modifies: `argus/ui/src/pages/DashboardPage.tsx`, position table section (toggle relocation)
  - Integrates: N/A (self-contained frontend rework)
- Session 3: Arena UI polish — remove borders, entry markers, auto-zoom, label cleanup, progress bar label, filtered stats
  - Creates: none
  - Modifies: `ArenaCard.tsx`, `MiniChart.tsx`, `ArenaPage.tsx`, `ArenaStatsBar.tsx`
  - Integrates: S1's pre-market candles visible via existing REST → chart pipeline (no wiring needed)
- Session 4: Trades visual unification — adopt Shadow density across both tabs, shared styling, `l`/`s` hotkeys
  - Creates: none
  - Modifies: `TradesPage.tsx`, `ShadowTradesTab.tsx`, `TradeTable.tsx`, `TradeStatsBar.tsx`
  - Integrates: N/A (self-contained frontend rework)
- Session 5: Trades feature additions — Outcome toggle on Shadow, time presets, infinite scroll, sortable columns, Reason tooltip
  - Creates: `argus/ui/src/features/trades/SharedTradeFilters.tsx` (extracted shared component)
  - Modifies: `TradesPage.tsx`, `ShadowTradesTab.tsx`, `TradeFilters.tsx`, `useShadowTrades.ts`
  - Integrates: S4's visual styling (S5 builds on S4's unified look)
- Session 6f: Visual review contingency — 0.5 session per frontend session as needed

**Key Decisions:**
- Arena WS subscribes directly to TickEvent for chart data; PositionUpdatedEvent kept only for P&L/R numbers
- IntradayCandleStore widens to 4:00 AM ET (pre-market) from current 9:30 AM
- Dashboard eliminates Monthly Goal + Universe cards; consolidates to 4-row no-scroll layout
- Trades page adopts Shadow tab's visual density as the standard; both tabs share a filter bar
- No new DECs anticipated — all changes follow established patterns

**Scope Boundaries:**
- IN: Arena latency fix (backend pipeline), pre-market candles, Arena visual polish (6 items), Dashboard layout refactor (4 rows), Trades page visual + feature unification, hotkeys
- OUT: Zombie flatten bugs (DEF-139/140 — separate impromptu), shadow trade outcome investigation, new strategies, experiment pipeline changes, any backend logic changes beyond Arena WS + candle store

**Regression Invariants:**
- All 12 strategies must remain active and evaluating
- Arena WS still delivers position open/close events and stats
- Dashboard still shows all data (repositioned, not removed, except Monthly Goal + Universe)
- Live Trades tab retains all existing functionality
- Existing pytest + Vitest baseline must pass
- No changes to trading engine, risk manager, order manager logic

**File Scope:**
- Modify: `arena_ws.py`, `intraday_candle_store.py`, `DashboardPage.tsx`, `ArenaCard.tsx`, `MiniChart.tsx`, `ArenaPage.tsx`, `ArenaStatsBar.tsx`, `TradesPage.tsx`, `ShadowTradesTab.tsx`, `TradeTable.tsx`, `TradeStatsBar.tsx`, `TradeFilters.tsx`, `useShadowTrades.ts`
- Create: `VitalsStrip.tsx`, `SharedTradeFilters.tsx`
- Do not modify: any Python outside of `arena_ws.py` and `intraday_candle_store.py`, `order_manager.py`, strategy files, risk manager, orchestrator, event definitions, API route files (except arena routes if needed), database schemas

**Config Changes:** No config changes.

**Test Strategy:**
- S1: ~8 tests (TickEvent subscription filtering, pre-market candle acceptance, trail stop dict)
- S2: ~5 tests (VitalsStrip rendering, layout structure)
- S3: ~6 tests (marker rendering, auto-zoom logic, filtered stats)
- S4: ~4 tests (styling consistency, hotkey handlers)
- S5: ~6 tests (infinite scroll, outcome filter, sortable columns)
- Estimated total: ~29 new tests

**Runner Compatibility:**
- Mode: human-in-the-loop (visual review throughout via Vite dev server)
- Parallelizable sessions: S1 || S2 || S3 || S4 (all four parallel); S5 sequential after S4
- Estimated token budget: ~5 sessions × ~80K avg = ~400K tokens
- Runner-specific escalation notes: N/A (HITL mode)

**Dependencies:**
- ARGUS running on port 8000 with IBKR connected (for live data visual testing)
- Vite dev server running on port 5175 (for hot-reload visual review)
- Sprint 32.75 test baseline: ~4,530 pytest + ~805 Vitest

**Escalation Criteria:**
- Any modification to order management, risk management, or trading engine code
- Any change to event definitions (events.py)
- Arena WS TickEvent subscription causing measurable CPU increase >5% on backend
- Dashboard refactor accidentally removing data access (not just repositioning)

**Doc Updates Needed:**
- `docs/project-knowledge.md` (Arena, Dashboard, Trades sections)
- `CLAUDE.md` (test counts, page descriptions)
- `docs/sprint-history.md` (Sprint 32.8 entry)
- `docs/ui/ux-feature-backlog.md` (mark completed items)

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with compaction scores)
4. Implementation Prompts ×5
5. Review Prompts ×5
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Review Context File
10. Work Journal Handoff
