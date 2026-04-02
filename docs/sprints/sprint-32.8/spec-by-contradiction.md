# Sprint 32.8: Specification by Contradiction

## This sprint does NOT:

1. **Modify the Order Manager tick handling or PnL throttle** — the 1s throttle on `_publish_position_pnl` stays. Arena gets its own direct TickEvent subscription instead.
2. **Change event definitions in events.py** — no new event types. Arena WS subscribes to existing TickEvent.
3. **Add any new API endpoints** — all data flows through existing REST and WebSocket endpoints.
4. **Change any trading logic** — no modifications to strategies, risk manager, orchestrator, position management, or order flow.
5. **Add new config fields or YAML files** — no Pydantic model changes.
6. **Change database schemas** — no migration scripts, no new tables, no column additions.
7. **Fix the zombie flatten bugs (DEF-139/140)** — deferred to separate impromptu.
8. **Investigate shadow trade missing outcomes** — deferred to operational sweep.
9. **Add new Dashboard cards or data sources** — only reorganizes existing components. Monthly Goal and Universe are relocated, not deleted from codebase.
10. **Change the Arena grid layout to a different paradigm** — cards stay, density stays. Only visual styling within cards changes.
11. **Add chart interactivity (click-to-expand, drill-down)** — charts remain view-only mini-charts.
12. **Replace Lightweight Charts with a different library** — stays as the Arena chart renderer.
13. **Modify the Shadow Trades backend API** — all Shadow Trades changes are frontend-only.
14. **Add new keyboard shortcuts beyond `l`/`s`** — no other navigation changes.
