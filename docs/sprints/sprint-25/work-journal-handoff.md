# Sprint 25 — Work Journal Handoff

> Paste this into a fresh Claude.ai conversation to create the Sprint 25 Work Journal.
> This conversation tracks session progress, classifies issues, maintains DEF/DEC ledgers,
> and produces the sprint close-out artifacts.

---

## Sprint Context

**Sprint 25: The Observatory**
**Goal:** Build a new Command Center page (page 8) providing immersive, real-time and post-session visualization of the entire ARGUS trading pipeline. Four views (Funnel/Radar/Matrix/Timeline), keyboard-first navigation, detail panel with live candlestick charts, session vitals, and debrief mode.

**Execution mode:** Human-in-the-loop
**Baseline tests:** 2,768 pytest + 523 Vitest = 3,291 total
**Estimated new tests:** ~92 (25 pytest + 67 Vitest)
**Sprint artifacts:** `docs/sprints/sprint-25/`

## Session Breakdown

| Session | Scope | Creates | Modifies | Score | Status |
|---------|-------|---------|----------|-------|--------|
| S1 | Backend API endpoints | observatory_service.py, observatory routes | api/__init__, server.py | 12.5 | |
| S2 | Backend WebSocket | observatory_ws.py | server.py | 12 | |
| S3 | Page shell + routing + keyboard | ObservatoryPage, Layout, keyboard hook, TierSelector | Navigation/routing | 13 | |
| S3f | Visual fixes (contingency) | — | — | — | |
| S4a | Detail panel core | DetailPanel, ConditionGrid, StrategyHistory | Layout | 10 | |
| S4b | Candlestick + hooks | CandlestickChart, useSymbolDetail | DetailPanel | 9 | |
| S4f | Visual fixes (contingency) | — | — | — | |
| S5a | Matrix view core | MatrixView, MatrixRow | ObservatoryPage | 10 | |
| S5b | Matrix scroll + interaction | useMatrixData | MatrixView | 8 | |
| S5f | Visual fixes (contingency) | — | — | — | |
| S6a | Three.js scene setup | FunnelView, FunnelScene | ObservatoryPage | 9.5 | |
| S6b | Symbol particles | FunnelSymbolManager | FunnelScene | 11.5 | |
| S6f | Visual fixes (contingency) | — | — | — | |
| S7 | Radar camera animation | RadarView, useCameraTransition | FunnelScene | 8 | |
| S8 | Timeline view | TimelineView, TimelineLane, useTimelineData | ObservatoryPage | 13 | |
| S8f | Visual fixes (contingency) | — | — | — | |
| S9 | Vitals + debrief mode | VitalsBar, useSessionVitals, useDebriefMode | Layout, all hooks | 13 | |
| S9f | Visual fixes (contingency) | — | — | — | |
| S10 | Integration polish | — | All Observatory components | 12 | |

## Session Dependency Chain

```
S1 → S2 → S3 → S4a → S4b
              → S5a → S5b
              → S6a → S6b → S7
              → S8
S3 + views + S4 → S9
All → S10
```

## "Do Not Modify" File List

- `argus/strategies/` (entire directory)
- `argus/core/orchestrator.py`
- `argus/core/risk_manager.py`
- `argus/execution/` (entire directory)
- `argus/intelligence/quality_engine.py`
- `argus/intelligence/position_sizer.py`
- `argus/intelligence/catalyst/` (entire directory)
- `argus/data/` (entire directory)
- `argus/ai/` (entire directory)
- Existing Command Center page components (Dashboard, Trades, Performance, Orchestrator, PatternLibrary, Debrief, System, Copilot)
- `argus/api/websocket/ai_chat.py`
- Evaluation telemetry schema (EvaluationEventStore table DDL)

## Issue Category Definitions

When session close-outs report issues, classify each into one of:

1. **In-session bug** — Bug introduced and found within the same session. Not tracked as DEF.
2. **Prior-session bug** — Bug from a previous session discovered in this one. Log as DEF if not fixable immediately.
3. **Scope gap** — Something the spec didn't anticipate that needs to be done. May expand scope or be deferred.
4. **Feature idea** — Nice-to-have that occurred during implementation. Always deferred, never in-scope.

## Escalation Triggers

Halt and escalate to human if:
1. Three.js < 30fps with 3,000+ particles
2. Bundle size increase > 500KB gzipped (Observatory chunk)
3. Observatory WS degrades AI Copilot WS
4. Any trading pipeline modification discovered necessary
5. Non-Observatory page load > 100ms increase

## Human Decision Points

- After S6b: Visual checkpoint — does the 3D funnel feel right?
- After S10: Full walkthrough — does the experience match the design intent?

## Reserved Numbers

- **DEC:** 343–360
- **DEF:** 063–070
- **RSK:** (use next available if needed)

## Work Journal Protocol

For each session completed:
1. Read the close-out file (`session-{N}-closeout.md`)
2. Read the review file (`session-{N}-review.md`)
3. Update the session status in the table above
4. Classify any issues reported
5. Track test counts (running total)
6. Log any DEC/DEF/RSK decisions made
7. Flag any concerns or patterns

At sprint close, produce:
- Final test count summary
- DEC/DEF/RSK ledger
- Issue summary (by category)
- Doc-sync prompt for updating project documentation
- Sprint verdict recommendation
