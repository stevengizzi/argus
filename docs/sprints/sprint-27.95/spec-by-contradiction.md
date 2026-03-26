# Sprint 27.95: What This Sprint Does NOT Do

## Out of Scope
These items are related to the sprint goal but are explicitly excluded:

1. **Frontend UI changes for overflow signals** — Overflow-routed signals will appear in CounterfactualTracker data via existing UI paths. No new UI components, badges, or indicators for overflow status. Deferred: natural fit for Sprint 28 (Learning Loop) when counterfactual data is consumed more broadly.

2. **Overflow routing dashboard/metrics** — No API endpoint for "how many signals overflowed today" or real-time overflow count display. Data is available in logs and counterfactual DB. A dedicated view is deferred.

3. **Dynamic broker_capacity adjustment** — The threshold is static config. Auto-scaling based on account equity, margin utilization, or IBKR buying power is not in scope. Can be added later if needed.

4. **Reconciliation position recovery** — When a confirmed position is missing from the IBKR snapshot, this sprint logs a WARNING but does not attempt to re-query IBKR, re-request portfolio, or probe for the position's actual status. Recovery logic is complex and not needed — the position naturally resolves when its bracket legs fill.

5. **IBKR API rate limiting** — The March 26 session hit ~2,490 orders. This sprint reduces order volume via overflow routing but does not add explicit IBKR API throttling or request queuing.

6. **Historical reconciliation data analysis** — No retroactive repair of March 26 trade records (336 reconciliation closes with PnL=0). The data is contaminated and should be excluded from Learning Loop training windows.

7. **Multi-account overflow** — Overflow routing to a second IBKR paper account for additional real execution capacity. Not needed at this stage.

## Edge Cases to Reject
The implementation should NOT handle these cases in this sprint:

1. **Overflow with partial fills in flight** — If a signal is approved and sent to IBKR but the position count crosses the threshold before the fill arrives, the fill is processed normally. Overflow check is a point-in-time decision at signal approval time, not retroactively applied.

2. **IBKR portfolio returning negative position sizes** — Short positions are not yet supported (Sprint 29). If IBKR reports negative share counts, log WARNING and skip. Do not attempt cleanup.

3. **Reconciliation during startup** — The first reconciliation cycle should not run until startup is complete (all phases finished). If it currently runs during startup, that's a separate timing issue — do not fix sequencing in this sprint, just ensure the new logic handles the edge case gracefully.

4. **Concurrent modification of _broker_confirmed dict** — Order Manager runs on the asyncio event loop (single-threaded). No locking needed. If threading model changes in the future, this becomes a concern — not now.

5. **Overflow threshold of 0** — Setting `broker_capacity: 0` means all signals go to counterfactual. This is valid behavior (useful for pure-observation mode) and should work, but do not add special-case UI messaging for it.

## Scope Boundaries
- Do NOT modify: `argus/strategies/` (any strategy file), `argus/backtest/` (BacktestEngine, VectorBT, replay harness), `argus/intelligence/counterfactual.py` (core CounterfactualTracker logic — only add new enum value consumed by it), `argus/analytics/evaluation.py`, `argus/ui/` (any frontend file), `argus/ai/` (AI layer), `argus/data/` (data service, indicators, universe manager)
- Do NOT optimize: Reconciliation cycle frequency (60s is fine), overflow check performance (simple integer comparison)
- Do NOT refactor: Order Manager class structure, position tracking data model, trade logger architecture
- Do NOT add: New API endpoints, new WebSocket messages, new database tables, new frontend components

## Interaction Boundaries
- This sprint does NOT change the behavior of: signal generation, strategy evaluation, Quality Engine scoring, Risk Manager gating logic, Capital Allocation, EOD flatten scheduling, CounterfactualTracker shadow mode routing, BacktestEngine execution
- This sprint does NOT affect: Observatory, AI Copilot, Catalyst Pipeline, Briefing Generator, VIX Data Service, Regime Intelligence classification, Evaluation Framework comparison/Pareto logic

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Overflow metrics API endpoint | Unscheduled | — |
| Dynamic broker_capacity based on margin | Unscheduled | — |
| Historical data cleanup (March 26 contaminated records) | Sprint 28 pre-work | — |
| IBKR API rate limiting / request queuing | Unscheduled | — |
| Reconciliation active recovery (re-query missing positions) | Unscheduled | — |
