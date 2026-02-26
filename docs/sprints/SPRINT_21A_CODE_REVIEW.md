# Sprint 21a — Code Review Plan & Handoff Briefs

---

## Code Review Schedule

| Review | After Session | Focus | Duration |
|--------|--------------|-------|----------|
| **Checkpoint 1** | Session 2 | Backend API + dev mode + nav | ~30 min |
| **Checkpoint 2** | Session 8 | Full feature review (all UI + integration) | ~60 min |
| **Final Review** | Session 9 or 10 | Polish, tests, regressions | ~30 min |

### Why These Checkpoints

**After Session 2:** The backend is complete (all API endpoints, config changes, dev mode). If there's an API design issue, catching it here avoids cascading frontend rework. This is the "foundation check."

**After Session 8:** All features are implemented — Pattern Library page, all 5 tabs, SlideInPanel, Symbol Detail Panel, click-anywhere wiring. This is the comprehensive review before polish. Any architectural issues or UX problems surface here.

**After Session 9/10:** Quick validation that polish, tests, and edge cases are handled. Mostly a green-light check before merging.

---

## Review Procedure

For each review:

1. **Start a new Claude conversation** in the ARGUS project (claude.ai).
2. **Paste the appropriate handoff brief** (below).
3. **Claude reads the repo** via GitHub access and reviews the code.
4. **Review produces:** Findings categorized as Critical (must fix), Important (should fix), and Minor (nice-to-have). Plus any doc updates needed.
5. **Steven decides** which findings to address.
6. **Fix session:** Address findings before continuing to next implementation sessions.
7. **Doc updates:** Draft DEC entries and doc updates as part of the review conversation.

### What Claude Reviews

- **Spec compliance:** Does the implementation match the Sprint 21a spec?
- **Architectural consistency:** Does new code follow existing patterns (route structure, component patterns, Zustand patterns, test patterns)?
- **Test coverage:** Are new endpoints/components tested? Any gaps?
- **TypeScript types:** Do frontend types match backend response models?
- **Responsive design:** Are all breakpoints handled correctly?
- **Dev mode:** Does `python -m argus.api --dev` work with all new features?
- **Regressions:** Any changes to existing files that could break existing functionality?
- **DEC compliance:** Do implementation choices align with DEC-172 through DEC-179?

---

## Handoff Brief — Checkpoint 1 (After Session 2)

Copy-paste this into a new Claude conversation:

```
# Sprint 21a Code Review — Checkpoint 1 (Backend + Scaffold)

## Context

I'm building ARGUS, an automated multi-strategy day trading system. Sprint 21a adds the Pattern Library page (strategy encyclopedia). Sessions 1–2 of implementation are complete. This is the first code review checkpoint.

**Before doing anything else:** The repo is public at https://github.com/stevengizzi/argus.git. Clone or access it to review the changes. If you can't access it, stop and tell me.

Read these files for context:
1. `CLAUDE.md` — project state (look for Sprint 21a mentions)
2. `docs/10_PHASE3_SPRINT_PLAN.md` — sprint spec
3. `docs/05_DECISION_LOG.md` — DEC-172 through DEC-179

## What Was Built (Sessions 1–2)

### Session 1 — Config + API Backend:
- Updated all 4 strategy YAML configs with: `pipeline_stage`, `family`, `description_short`, `time_window_display`, `backtest_summary` section
- Updated Pydantic config models: `BacktestSummaryConfig`, new fields on `StrategyConfig` base class
- Extended `GET /api/v1/strategies` with: `time_window`, `family`, `description_short`, `performance_summary` (computed from TradeLogger), `backtest_summary`
- New `GET /api/v1/strategies/{strategy_id}/spec` — serves markdown spec sheets from `docs/strategies/`
- Extended `GET /api/v1/performance/{period}` with optional `?strategy_id=` filter
- New `GET /api/v1/market/{symbol}/bars` — synthetic OHLCV data for Symbol Detail chart
- New route file: `argus/api/routes/market.py`
- ~13 new pytest tests

### Session 2 — Dev Mode + Scaffold + Nav:
- Extended `dev_state.py` MockStrategy with new fields
- Frontend TypeScript types for all new API responses
- API client functions for new endpoints
- New hooks: `useStrategySpec`, `useSymbolBars`, `useSymbolTrades`
- New Zustand stores: `patternLibraryUI`, `symbolDetailUI`
- PatternLibraryPage scaffold (placeholder content)
- Nav updated: 5th page (Pattern Library) in Sidebar + MobileNav
- Keyboard shortcuts updated: 1→Dashboard, 2→Trades, 3→Performance, 4→Patterns, 5→System
- ~4 additional pytest tests for dev mode

## What to Review

### Backend (Priority: Critical)
1. **Config model changes** (`argus/core/config.py`): Do the new fields break any existing tests? Is `BacktestSummaryConfig` properly integrated into all 4 strategy configs?
2. **Strategies route** (`argus/api/routes/strategies.py`): Is the performance_summary computation efficient? Does it handle the case where a strategy has zero trades?
3. **Spec endpoint**: Is the file path resolution robust? Does it handle missing files gracefully?
4. **Market bars endpoint** (`argus/api/routes/market.py`): Is the synthetic data generator deterministic? Any issues with the random walk implementation?
5. **Performance filter**: Does the `strategy_id` parameter propagate correctly to TradeLogger queries?
6. **YAML configs**: Verify all 4 configs have consistent formatting and correct values.

### Frontend (Priority: Important)
7. **TypeScript types** (`api/types.ts`): Do they exactly match the backend Pydantic models?
8. **Hooks**: Are TanStack Query keys consistent and properly namespaced?
9. **Stores**: Are the Zustand stores well-typed and following existing patterns?
10. **Nav changes**: Verify 5 items render correctly. Keyboard shortcuts work.

### Tests (Priority: Important)
11. Run `pytest --tb=short -q` — all pass? How many total?
12. Run `cd argus/ui && npx vitest run` — all pass?
13. Any existing tests that needed modification? Were changes minimal?

### Dev Mode (Priority: Critical)
14. Does `python -m argus.api --dev` start correctly?
15. Do all new endpoints return expected data in dev mode?

## Output Format

Categorize findings as:
- **🔴 Critical** — Must fix before continuing. Blocks Sessions 3+.
- **🟡 Important** — Should fix soon. Schedule before Session 8.
- **🟢 Minor** — Nice-to-have. Can defer.

Plus: any DEC entries that should be added or modified, and any doc updates needed.
```

---

## Handoff Brief — Checkpoint 2 (After Session 8)

Copy-paste this into a new Claude conversation:

```
# Sprint 21a Code Review — Checkpoint 2 (Full Feature Review)

## Context

I'm building ARGUS, an automated multi-strategy day trading system. Sprint 21a adds the Pattern Library page. Sessions 1–8 of implementation are complete. This is the comprehensive review — all features are implemented.

**Before doing anything else:** The repo is public at https://github.com/stevengizzi/argus.git. Clone or access it to review all changes since Sprint 20.

Read these files for context:
1. `CLAUDE.md` — project state
2. `docs/05_DECISION_LOG.md` — DEC-172 through DEC-179
3. `docs/10_PHASE3_SPRINT_PLAN.md` — sprint spec

## What Was Built (Sessions 1–8)

### Backend (Sessions 1–2):
- Config YAML updates (pipeline_stage, family, description_short, time_window_display, backtest_summary) on all 4 strategies
- Pydantic model updates (BacktestSummaryConfig, StrategyConfig base fields)
- Extended GET /strategies (performance_summary, backtest_summary, new metadata)
- New GET /strategies/{id}/spec (markdown spec sheets)
- Extended GET /performance/{period} with ?strategy_id= filter
- New GET /market/{symbol}/bars (synthetic OHLCV)
- Dev mode extensions (MockStrategy fields, mock data)

### Frontend — Pattern Library Page (Sessions 3–6):
- IncubatorPipeline — 10-stage horizontal pipeline with counts and click-to-filter
- PatternCardGrid — filterable/sortable strategy card grid
- PatternCard — strategy card with badges, stats, selection state
- PatternFilters — family, time window, sort controls
- PatternDetail — tabbed right panel (5 tabs)
- OverviewTab — parameter table + rendered markdown spec sheet
- PerformanceTab — strategy-specific equity curve, metrics, daily P&L
- BacktestTab — structured placeholder with summary metrics
- TradesTab — reuses TradeTable with locked strategy filter
- IntelligenceTab — placeholder
- Master-detail responsive layout (desktop split, tablet/mobile drill-down)
- react-markdown + remark-gfm for spec rendering
- MarkdownRenderer component with dark theme styling

### Frontend — Symbol Detail + SlideInPanel (Sessions 7–8):
- SlideInPanel — extracted shared animated panel shell
- TradeDetailPanel — refactored to use SlideInPanel
- SymbolDetailPanel — global slide-in with chart + history + position
- SymbolChart — Lightweight Charts candlestick chart
- SymbolTradingHistory — trade summary + recent trades for symbol
- SymbolPositionDetail — open position info
- Click-anywhere wiring: WatchlistItem, OpenPositions, TradeTable all open SymbolDetailPanel on symbol click

### Infrastructure:
- Nav updated to 5 pages (Sidebar + MobileNav)
- 2 new Zustand stores (patternLibraryUI, symbolDetailUI)
- 3 new hooks (useStrategySpec, useSymbolBars, useSymbolTrades)
- New route file: market.py

## What to Review

### Architecture (Priority: Critical)
1. **SlideInPanel extraction**: Is it properly generic? Does TradeDetailPanel still work identically after refactoring? Any animation regressions?
2. **SymbolDetailPanel mounting in AppShell**: Correct placement? No z-index conflicts with other overlays?
3. **Symbol click wiring**: `e.stopPropagation()` on symbol clicks in TradeTable — does it prevent row click from firing without breaking other functionality?
4. **Master-detail layout**: Is the responsive switching clean? Any layout shifts when selecting/deselecting strategies?

### Components (Priority: Important)
5. **IncubatorPipeline**: Does click-to-filter work both ways (click to set, click again to clear)?
6. **PatternCard**: Selection state visible at all breakpoints?
7. **OverviewTab markdown rendering**: Does the dark theme styling work for all markdown elements (tables, code blocks, headers, lists)?
8. **PerformanceTab**: Is the usePerformance hook properly extended? No caching issues with strategy_id variants?
9. **TradesTab**: Does the strategy filter work correctly? Pagination correct?
10. **SymbolChart**: Lightweight Charts properly initialized and cleaned up on unmount? No memory leaks from chart instances?
11. **PatternFilters**: Filtering logic correct? Time window classification working?

### Responsive Design (Priority: Important)
12. Review at all 3 breakpoints:
    - Desktop (≥1024px): Master-detail layout, sidebar nav, desktop panels
    - Tablet (640–1023px): Full-width cards, drill-down detail, bottom nav 5 items
    - Mobile (<640px): Stacked cards, full-screen detail, compact pipeline, bottom nav

### Tests (Priority: Important)
13. Run full test suite. Report counts (pytest + Vitest).
14. Any regressions on existing tests?
15. Coverage gaps? Components without tests?

### Code Quality (Priority: Important)
16. `ruff check argus/` — any errors?
17. Component naming conventions consistent?
18. Import paths clean? No circular dependencies?
19. Zustand store patterns match existing ones?

### Dev Mode (Priority: Critical)
20. `python -m argus.api --dev` — fully functional Pattern Library?
21. All tabs render with realistic data?
22. Symbol Detail opens for dev mode symbols?

## Output Format

Categorize findings as:
- **🔴 Critical** — Must fix before merge.
- **🟡 Important** — Should fix in Session 9/10.
- **🟢 Minor** — Defer to Sprint 21d or later.

Also provide:
- DEC entries to add or modify
- Doc updates needed (CLAUDE.md, Project Knowledge, Sprint Plan)
- Deferred items to log (DEF-NNN)
```

---

## Handoff Brief — Final Review (After Session 9/10)

Copy-paste this into a new Claude conversation:

```
# Sprint 21a Code Review — Final Review

## Context

I'm building ARGUS, an automated multi-strategy day trading system. Sprint 21a (Pattern Library page) is complete. All 8–10 implementation sessions done. This is the final review before merging.

**Repo:** https://github.com/stevengizzi/argus.git — clone and review.

Read: `CLAUDE.md`, `docs/05_DECISION_LOG.md` (DEC-172–179+).

## What to Verify

1. **Test suite passes completely:**
   - `pytest --tb=short -q` → expected ~1542+ pytest
   - `cd argus/ui && npx vitest run` → expected ~65+ Vitest
   - Zero regressions on pre-existing tests

2. **Code quality:**
   - `ruff check argus/` → zero errors
   - No TODOs or FIXMEs that should be resolved before merge
   - No debug code left in (console.logs, print statements)

3. **Dev mode works end-to-end:**
   - `python -m argus.api --dev` starts cleanly
   - Pattern Library page at /patterns — all features working
   - Symbol Detail Panel opens from any symbol click
   - All 5 tabs in PatternDetail render correctly

4. **Checkpoint 2 findings addressed:**
   - Were all 🔴 Critical issues fixed?
   - Were 🟡 Important issues either fixed or deferred with DEF numbers?

5. **Definition of Done checklist** (from implementation spec):
   - [ ] All 4 strategy YAML configs updated
   - [ ] Pydantic config models updated
   - [ ] /strategies returns enriched data
   - [ ] /strategies/{id}/spec serves markdown
   - [ ] /performance/{period}?strategy_id= filters correctly
   - [ ] /market/{symbol}/bars returns OHLCV
   - [ ] Pattern Library page renders at all breakpoints
   - [ ] Incubator Pipeline works
   - [ ] All 5 tabs render
   - [ ] SlideInPanel extracted, TradeDetailPanel refactored
   - [ ] SymbolDetailPanel works globally
   - [ ] Nav shows 5 pages
   - [ ] react-markdown installed and themed

## Output Format

**PASS / FAIL** with list of any remaining issues.

If PASS: Draft the "Sprint 21a Complete" summary for doc updates (CLAUDE.md, Project Knowledge, Sprint Plan, Decision Log).

If FAIL: List blocking issues with fix instructions.
```

---

## Doc Update Timing

| When | What |
|------|------|
| **Now (before implementation)** | Decision Log entries DEC-172–179. Sprint plan Sprint 21a spec update. |
| **After Checkpoint 2** | CLAUDE.md current state update (if significant findings). |
| **After Final Review (sprint complete)** | Full doc sync: CLAUDE.md, Project Knowledge (02), Sprint Plan (10), Decision Log (05), Architecture (03) if endpoints changed. |
