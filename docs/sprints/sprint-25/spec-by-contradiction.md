# Sprint 25: What This Sprint Does NOT Do

## Out of Scope

1. **New strategies (Red-to-Green, Bull Flag, etc.):** Deferred. Sprint 25 was originally planned as "Red-to-Green + Pattern Library Foundation." The Observatory takes priority because understanding the existing 4 strategies' behavior is prerequisite to adding more.
2. **Strategy logic modifications:** No changes to any strategy's entry conditions, exit logic, state machines, or pattern strength calculations. The Observatory is a read-only visualization layer.
3. **Evaluation telemetry schema changes:** The `EvaluationEventStore` schema, `StrategyEvaluationBuffer` ring buffer, and existing `GET /api/v1/strategies/{id}/decisions` endpoint are consumed as-is. No schema migrations.
4. **Quality Engine modifications:** `SetupQualityEngine` and `DynamicPositionSizer` are consumed as-is for score/grade display. No weight changes, no threshold changes.
5. **Catalyst pipeline modifications:** Catalyst data displayed in detail panel is read from existing `CatalystStorage`. No new catalyst sources, no classifier changes.
6. **Historical replay animation:** Debrief mode loads static snapshots of historical data for a given date. It does NOT provide frame-by-frame animated playback of the session ("scrub through time and watch dots move"). That would require event-level timestamps and a replay engine — defer to a future sprint.
7. **Synapse / 3D strategy clustering:** The Funnel/Radar are symbol-centric (where is each symbol in the pipeline?), not strategy-centric (how do strategies relate to each other in parameter space). Synapse is Phase 9–10 scope.
8. **Order flow visualization:** Requires Databento Plus ($1,399/mo), deferred post-revenue per DEC-238.
9. **Replacing existing pages:** The Observatory is additive (page 8). Dashboard, Orchestrator, and all other pages are unchanged.
10. **Mobile/PWA optimization of Observatory:** Three.js 3D visualization targets desktop/tablet. PWA mobile will show the page but 3D performance is not guaranteed on mobile devices. Acceptable for V1.
11. **Backtest re-validation (Sprint 21.6):** Remains deferred. Observation data from live sessions will inform whether re-validation is urgent.

## Edge Cases to Reject

1. **Symbol not in any strategy's universe filter:** Show in Universe and Viable tiers only. No condition data in detail panel — display "Not routed to any strategy" message.
2. **Multiple strategies evaluating the same symbol simultaneously:** Show all strategies' conditions in the detail panel (stacked sections). In Matrix view, the symbol appears once per strategy that's evaluating it, with that strategy's conditions as columns.
3. **WebSocket disconnection mid-session:** Graceful degradation — vitals bar shows "Disconnected" status, data freezes at last known state. Automatic reconnection with exponential backoff. No crash, no blank screen.
4. **Date picker selects date with no data (weekend, holiday, or beyond retention window):** Show empty views with "No data for this date" message. Do not error.
5. **Thousands of symbols on a single tier (Universe/Viable):** Funnel view uses instanced rendering — performance must hold. Matrix view uses virtual scrolling. Do NOT attempt to render 3,000 DOM rows.
6. **Zero symbols at near-trigger or signal tier:** Empty tier renders as an empty ring/row. Tier count shows 0. This is the normal state most of the time.
7. **Strategy window not yet active (e.g., AfMo conditions before 2:00 PM):** In Matrix view, show "–" cells (gray) for that strategy's conditions, NOT red (fail). The conditions haven't been evaluated yet.
8. **Symbol transitions rapidly between tiers (e.g., enters/exits evaluation within one WS update cycle):** Show the latest state. Do not attempt to animate intermediate transitions that weren't observed.

## Scope Boundaries

- Do NOT modify: Any file in `argus/strategies/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/intelligence/catalyst/`, `argus/data/`, existing page components in `argus/ui/src/features/` (Dashboard, Trades, Performance, Orchestrator, PatternLibrary, Debrief, System, Copilot), `argus/ai/`
- Do NOT optimize: Three.js beyond what's needed for 30fps at 3,000 particles. Advanced GPU-based particle systems, WebGL shaders, or compute shaders are out of scope. Instanced meshes are sufficient.
- Do NOT refactor: Existing evaluation telemetry infrastructure. The Observatory reads from it; it does not reshape it. No changes to `BaseStrategy.record_evaluation()`, `StrategyEvaluationBuffer`, or `EvaluationEventStore`.
- Do NOT add: New Event Bus event types. The Observatory reads from REST/WS, not from the Event Bus directly. Adding a subscriber would couple it to the trading pipeline's hot path.

## Interaction Boundaries

- This sprint does NOT change the behavior of: any trading pipeline component (strategies, orchestrator, risk manager, order manager, broker), the AI Copilot WebSocket, the catalyst pipeline, the quality engine scoring, the evaluation telemetry recording
- This sprint does NOT affect: trade execution, signal generation, quality filtering, position sizing, risk management, or any paper trading behavior. A user should be able to run ARGUS with the Observatory page open and see identical trading results as without it.

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Historical replay animation (scrub-through-time playback) | Unscheduled | TBD |
| Observatory mobile/PWA optimization | Unscheduled | TBD |
| Strategy-centric 3D visualization (Synapse) | Sprint 37–38 | — |
| Observatory → AI Copilot integration ("explain why NVDA didn't trigger") | Unscheduled | TBD |
| Heatmap overlay on candlestick chart (volume profile, order flow) | Post-revenue | DEC-238 |
| Red-to-Green strategy + Pattern Library Foundation | Sprint 26 (renumbered) | — |
