# Sprint 32.75 Design Summary

**Sprint Goal:** Deliver The Arena (real-time multi-chart position visualization page), fix 13 UI bugs/polish items, and resolve 5 operational issues from the April 1 market session debrief.

**Session Breakdown:**

- Session 1: Strategy identity system — add 5 new PatternModule strategies (Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, PreMarket High Break) to all identity maps across strategyConfig.ts, Badge.tsx, AllocationDonut.tsx, SessionTimeline.tsx. Each strategy gets unique color, badge abbreviation, and display name. Fixes: grey colors, "STRA" badges, "Strat Xxx" naming, Session Timeline showing only 7, Capital Allocation greyed-out donut.
  - Creates: None
  - Modifies: `ui/src/utils/strategyConfig.ts`, `ui/src/components/Badge.tsx`, `ui/src/components/AllocationDonut.tsx`, `ui/src/features/dashboard/SessionTimeline.tsx`
  - Integrates: N/A (foundation)

- Session 2: Dashboard overhaul — remove Recent Trades and System Status cards. Swap Signal Quality and AI Insight card positions. Move All/Open/Closed toggle inline with Positions card header. Redesign VIX Regime card (condense to single-row or enrich with sparkline/regime context).
  - Creates: None
  - Modifies: `ui/src/pages/DashboardPage.tsx`, `ui/src/features/dashboard/VixRegimeCard.tsx`, `ui/src/features/dashboard/OpenPositions.tsx` (~5 files across 3 responsive layouts)
  - Integrates: S1 (strategy colors in timeline, donut)

- Session 3: Orchestrator page fixes — fix Total P&L Today / Trades Today stuck at $0 (backend: wire `record_trade_result()` from Order Manager on position close, or query trade_logger in orchestrator API endpoint). Fix Capital Allocation legend to use display names. Make Catalyst Alert headlines clickable links (`target="_blank"`).
  - Creates: None
  - Modifies: `argus/execution/order_manager.py` or `argus/api/routes/orchestrator.py` (P&L fix), `ui/src/features/orchestrator/` components (~4-5 files)
  - Integrates: S1 (strategy identity auto-propagates to Orchestrator via getStrategyDisplay)

- Session 4: Bug fixes — fix duplicate Entry/Current price labels in TradeChart.tsx (track created price lines in ref, remove before recreating in useEffect). Enhance AI Insight SystemContextBuilder to inject full position portfolio, not just top-5.
  - Creates: None
  - Modifies: `ui/src/components/TradeChart.tsx`, `argus/ai/system_context.py` (~2-3 files)
  - Integrates: N/A

- Session 5: Operational fixes + IBC guide — raise `overflow.broker_capacity` to 60. Add async delay + retry for first portfolio query after IBKR reconnection. Add per-strategy end-of-window evaluation summary log. Investigate stop retry exhaustion frequency (42/day) and document findings. Create IBC setup guide with launchd plist template.
  - Creates: `docs/ibc-setup.md`, `scripts/ibc/com.argus.ibgateway.plist` (template)
  - Modifies: `config/overflow.yaml`, `argus/execution/ibkr_broker.py`, `argus/strategies/base_strategy.py`
  - Integrates: N/A

- Session 6: Arena REST API — candle history endpoint (`GET /api/v1/arena/candles/{symbol}`) serving IntradayCandleStore data. Position list endpoint (`GET /api/v1/arena/positions`) with current levels and P&L for initial page load.
  - Creates: `argus/api/routes/arena.py`
  - Modifies: `argus/api/routes/__init__.py`, `argus/api/server.py` (route registration)
  - Integrates: N/A (backend consumed by S10+)

- Session 7: Arena WebSocket — `/ws/v1/arena` channel streaming position opens/closes, tick updates (price, P&L, R-multiple, trailing stop), completed 1-minute candles for open positions, and aggregate stats (position count, total P&L, net R) every second.
  - Creates: `argus/api/websocket/arena_ws.py`
  - Modifies: `argus/api/server.py` (WS route registration)
  - Integrates: N/A (consumed by S11)

- Session 8: Arena page shell — ArenaPage component, nav registration (9th page), ArenaStatsBar, responsive CSS grid skeleton, empty state, basic page-level controls (sort mode selector, strategy filter dropdown).
  - Creates: `ui/src/pages/ArenaPage.tsx`, `ui/src/features/arena/ArenaStatsBar.tsx`, `ui/src/features/arena/ArenaControls.tsx`
  - Modifies: `ui/src/App.tsx` (router), nav/sidebar component
  - Integrates: S1 (strategy colors for filter dropdown)

- Session 9: MiniChart component — standalone TradingView Lightweight Charts wrapper. Renders candlestick data from props. Static price level lines (entry=blue dashed, stop=red solid, T1=green dashed, trailing stop=yellow). P&L and R-multiple overlay, hold duration timer, stop-to-T1 progress bar. Strategy badge corner overlay.
  - Creates: `ui/src/features/arena/MiniChart.tsx`, `ui/src/features/arena/ArenaCard.tsx`
  - Modifies: None (standalone component)
  - Integrates: S1 (strategy identity for badge/colors)

- Session 10: Arena card integration — wire ArenaCard/MiniChart with REST data via useArenaData hook. Populate grid with real position data. Render candle history from S6 REST endpoint. Sort and filter functional.
  - Creates: `ui/src/hooks/useArenaData.ts`
  - Modifies: `ui/src/pages/ArenaPage.tsx`, `ui/src/features/arena/ArenaCard.tsx`
  - Integrates: S6 REST API + S8 page shell + S9 MiniChart

- Session 11: Arena live data — wire Arena WebSocket to MiniChart instances. Live candle formation (sub-second close/high/low updates to current candle). Dynamic trailing stop line updates. Aggregate stats bar live updates. requestAnimationFrame batching for 30-60 simultaneous chart repaints.
  - Creates: `ui/src/features/arena/useArenaWebSocket.ts`
  - Modifies: `ui/src/features/arena/MiniChart.tsx`, `ui/src/pages/ArenaPage.tsx`, `ui/src/features/arena/ArenaStatsBar.tsx`
  - Integrates: S7 WebSocket + S10 card integration

- Session 12: Arena animations + polish — Framer Motion AnimatePresence for entry (fade+scale) and exit (color tint flash + dissolve) animations. Attention-weighted priority sizing (CSS grid fr units adjusted by proximity-to-exit score, smooth 500ms transitions). Grid reflow on position count changes. Disconnection indicator overlay.
  - Creates: None
  - Modifies: `ui/src/pages/ArenaPage.tsx`, `ui/src/features/arena/ArenaCard.tsx` (~3 files)
  - Integrates: S11

- Session 12f: Visual review fixes — contingency 0.5 session for frontend visual issues.

**Key Decisions:**
- The Arena is a dedicated 9th page, not a Dashboard replacement. The Dashboard remains the ambient awareness hub; the Arena is the active-monitoring immersive view.
- Orchestrator P&L fix: query trade_logger in the API endpoint rather than wiring record_trade_result (more robust, survives reconnection).
- Strategy Health (Learning tab) showing only 7 is a data issue (new strategies lack trade data), not a code bug — dropped from scope.
- Broker capacity raised from 30 to 60 for more real execution data capture.
- IBC setup is documentation only; actual installation is manual on operator's machine.
- Strategy identity additions are the foundation session — no refactoring of existing constant structure, just adding missing entries.

**Scope Boundaries:**
- IN: Arena page, 13 UI fixes/polish items, 5 operational fixes, IBC documentation
- OUT: ABCD parameter tuning, per-strategy position caps, L2/L3 visualization, Organism View, Arena click-to-trade, strategy detection logic changes, historical replay mode, Learning Strategy Health fix (data issue)

**Regression Invariants:**
- All 12 strategies must continue generating signals, executing trades, and logging correctly
- Existing WebSocket channels (/ws/v1/live, /ws/v1/observatory, /ws/v1/ai/chat) must remain functional
- Dashboard, Orchestrator, Performance, Trades, and all other existing pages must render correctly
- EOD flatten, shutdown, Learning Loop auto-trigger unaffected
- IBKR reconnection logic must still work (delay is additive, not a flow change)
- All existing tests pass (4,405 pytest + 700 Vitest baseline)

**File Scope:**
- Modify: strategyConfig.ts, Badge.tsx, AllocationDonut.tsx, SessionTimeline.tsx, DashboardPage.tsx, VixRegimeCard.tsx, OpenPositions.tsx, OrchestratorPage components, TradeChart.tsx, SystemContextBuilder, overflow.yaml, ibkr_broker.py, base_strategy.py, App.tsx, server.py
- Create: ArenaPage.tsx, MiniChart.tsx, ArenaCard.tsx, ArenaStatsBar.tsx, ArenaControls.tsx, arena.py (REST), arena_ws.py (WS), useArenaData.ts, useArenaWebSocket.ts, docs/ibc-setup.md
- Do not modify: Strategy detection logic, Risk Manager, Order Manager (except P&L wiring), Event Bus, Trade Logger, BacktestEngine, Experiment Pipeline, Learning Loop core

**Config Changes:**
- `overflow.broker_capacity: 60` (was 30) in `config/overflow.yaml` → `OverflowConfig.broker_capacity` Pydantic field

**Test Strategy:**
- S1: Update existing Badge/AllocationDonut/SessionTimeline tests for new strategy entries (~8 tests modified)
- S3: Backend P&L fix needs test (~3 new tests)
- S4: TradeChart price line cleanup test (~2 new tests)
- S5: Reconnect delay test, end-of-window logging test (~4 new tests)
- S6: Arena REST endpoint tests (~6 new tests)
- S7: Arena WS channel tests (~8 new tests)
- S8-12: Arena frontend component tests (~15 new tests across sessions)
- Estimated total: ~45 new/modified tests

**Runner Compatibility:**
- Mode: Human-in-the-loop
- Parallelizable sessions:
  - Wave 1: S1, S5, S6, S9 (zero file overlap — confirmed via repo analysis)
  - Wave 2: S2, S3, S4, S7, S8 (different pages/backend modules — zero overlap)
  - Wave 3: S10 (integration)
  - Wave 4: S11
  - Wave 5: S12, S12f
- Critical path: 5 waves

**Dependencies:**
- Sprint 32.5 must be complete (merged to main) before implementation begins
- TradingView Lightweight Charts already in package.json (used by TradeChart, TradeReplay)
- Framer Motion already available (used throughout app)

**Escalation Criteria:**
- TradingView Lightweight Charts cannot support 30+ simultaneous instances without unacceptable performance → Tier 3 review for alternative approach
- Arena WebSocket produces >50ms render latency at 40 positions → performance optimization session needed
- IBKR reconnect delay causes missed fills or order state corruption → revert and redesign

**Doc Updates Needed:**
- project-knowledge.md (new page, strategy identity, operational fixes)
- architecture.md (Arena WS channel, REST endpoints)
- CLAUDE.md (new files, config changes)
- roadmap.md (build track queue update)
- sprint-history.md (sprint entry)
- docs/live-operations.md (IBC setup reference)
- docs/pre-live-transition-checklist.md (broker_capacity note)

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates per session)
4. Implementation Prompt ×12
5. Review Prompt ×12
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Work Journal Handoff Prompt
