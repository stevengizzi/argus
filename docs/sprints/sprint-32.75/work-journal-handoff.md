# Sprint 32.75 — Work Journal Handoff

> Paste this into a fresh Claude.ai conversation to create the Sprint 32.75 Work Journal.
> Open this conversation before starting Session 1. Bring issues here throughout the sprint.

---

## Sprint Context

**Sprint 32.75: The Arena + UI/Operational Sweep**
**Goal:** Deliver The Arena (real-time multi-chart position visualization page), fix 13 UI bugs/polish items, and resolve 5 operational issues from the April 1 market session debrief.

**Execution mode:** Human-in-the-loop
**Branch prefix:** `sprint-32.75-session-{N}`
**Sprint directory:** `docs/sprints/sprint-32.75/`
**Test baseline:** ~4,405 pytest + 700 Vitest (+ Sprint 32.5 additions)

---

## Session Breakdown

| Session | Scope | Score | Wave | Creates | Modifies |
|---------|-------|-------|------|---------|----------|
| S1 | Strategy identity (5 new strategies → all maps) | 10 | 1 | — | strategyConfig.ts, Badge.tsx, AllocationDonut.tsx, SessionTimeline.tsx |
| S2 | Dashboard overhaul (remove cards, VIX redesign, toggle) | 10.5 | 2 | — | DashboardPage.tsx, VixRegimeCard.tsx, OpenPositions.tsx |
| S3 | Orchestrator fixes (P&L bug, legend, catalyst links) | 10.5 | 2 | — | orchestrator.py, Orchestrator components |
| S4 | Bug fixes (price labels, AI context) | 7 | 2 | — | TradeChart.tsx, system_context.py |
| S5 | Ops fixes (overflow, reconnect, logging, IBC) | 13.5 | 1 | ibc-setup.md, plist | overflow.yaml, ibkr_broker.py, base_strategy.py |
| S6 | Arena REST API (candles + positions) | 11 | 1 | arena.py | routes/__init__.py |
| S7 | Arena WebSocket (live streaming) | 14 | 2 | arena_ws.py | server.py |
| S8 | Arena page shell (route, grid, stats, controls) | 14 | 2 | ArenaPage.tsx, ArenaStatsBar.tsx, ArenaControls.tsx | App.tsx, nav |
| S9 | MiniChart component (TradingView LC wrapper) | 12 | 1 | MiniChart.tsx, ArenaCard.tsx | — |
| S10 | Arena card integration (REST data, sort, filter) | 13.5 | 3 | useArenaData.ts | ArenaPage.tsx, ArenaCard.tsx |
| S11 | Arena live data (WS → charts, live candles) | 17.5 | 4 | useArenaWebSocket.ts | MiniChart.tsx, ArenaPage.tsx |
| S12 | Arena animations + polish | 5.5 | 5 | — | ArenaPage.tsx, ArenaCard.tsx |
| S12f | Visual review fixes (contingency) | — | 5 | — | TBD |

**Dependency chain:**
- S1 → S2, S3, S4, S8
- S6 → S7, S10
- S8 + S9 → S10
- S7 + S10 → S11
- S11 → S12 → S12f

**Parallelization waves:**
- Wave 1: S1, S5, S6, S9
- Wave 2: S2, S3, S4, S7, S8
- Wave 3: S10
- Wave 4: S11
- Wave 5: S12, S12f

---

## Do-Not-Modify Files
- `argus/core/event_bus.py`
- `argus/core/risk_manager.py`
- `argus/analytics/trade_logger.py`
- `argus/backtest/` (entire directory)
- `argus/intelligence/learning/` (entire directory)
- `argus/intelligence/experiments/` (entire directory)
- Strategy detection logic (`detect()`, `score()` methods)

---

## Issue Categories
- **BLOCKER**: Cannot proceed to next session
- **SCOPE_GAP**: Spec doesn't cover encountered situation
- **REGRESSION**: Pre-existing test broken by changes
- **DESIGN_MISMATCH**: Implementation reveals spec flaw
- **CARRY_FORWARD**: Non-critical, defer to later session or DEF item

---

## Escalation Triggers
1. Arena 30-chart performance >200ms/frame → Tier 3
2. TradingView LC update() API inadequate → evaluate alternatives
3. Arena WS degrades trading pipeline → immediate halt
4. Post-reconnect delay causes position corruption → revert
5. P&L fix reveals trade-to-strategy attribution gap → escalate
6. Any session >5 pre-existing test failures → halt
7. S11 compaction: defer rAF batching to S12

---

## Reserved Numbers
- **DEC:** 382–395
- **DEF:** 135–139 (already assigned in spec-by-contradiction)

---

## How to Use This Journal

Report session outcomes as they complete:
```
Session [N] complete.
- Verdict: [CLEAR / CONCERNS / CONCERNS_RESOLVED]
- Tests: [before] → [after] (+[delta])
- Issues: [any problems encountered]
- DECs logged: [DEC numbers if any]
- Carry-forwards: [items for future sessions]
```

I will track:
- Session verdicts and test deltas
- DEF/DEC number assignments
- Scope gaps and carry-forwards
- Parallelization adjustments if dependencies shift
- Generate the doc-sync prompt at sprint close
