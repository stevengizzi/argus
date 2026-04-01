# Sprint 32.75: What This Sprint Does NOT Do

## Out of Scope
1. **ABCD detection parameter tuning** — ABCD's 5,927 signals/day is a parameter sensitivity issue, not a system bug. Tuning belongs in the experiment pipeline (Sprint 32.5 variants). The broker_capacity increase to 60 partially alleviates the symptom.
2. **Per-strategy `max_concurrent_positions` enforcement** — Considered and explicitly rejected to preserve maximum real execution data capture during paper trading.
3. **L2/L3 order book visualization** — Post-revenue feature (DEC-238). The Arena is designed to accept this as a future overlay layer but does not implement it.
4. **Organism View alternative visualization** — Deferred. The Arena's grid-of-charts approach addresses the core need; the abstract particle visualization may be revisited later.
5. **Arena click-to-trade or manual override** — The Arena is a monitoring page only. No order entry, position modification, or manual close actions.
6. **Historical replay mode for Arena** — The Arena shows live data only. Replaying past sessions through the Arena is a future feature.
7. **Strategy identity refactoring** — We add entries to the existing parallel maps (strategyConfig.ts, Badge.tsx, AllocationDonut.tsx). We do NOT refactor these into a single source of truth. That consolidation is desirable but increases risk for this sprint.
8. **Learning Strategy Health card fix** — The card showing only 7 strategies is a data availability issue (new strategies lack sufficient trade data for Learning Loop analysis), not a code bug.
9. **IBC actual installation** — The sprint produces documentation and templates. The operator installs IBC manually on their machine using the guide.
10. **Databento reconnection improvements** — The 7 stream disconnection events all self-recovered. The existing retry logic is adequate.

## Edge Cases to Reject
1. **Arena with 100+ positions** — Render performance above 60 positions is best-effort. Positions beyond the viewport use simple placeholders (no chart instance) and are instantiated on scroll. Do not optimize for 100+ in this sprint.
2. **Arena during IBKR disconnection** — Show stale data with a visual disconnection indicator. Do not attempt to maintain synthetic candle formation from cached data.
3. **Arena with zero strategies passing filter** — Show empty state message. Do not auto-clear the filter.
4. **Multiple positions on same symbol from same strategy** — Should not occur in production but could in edge cases. Each gets its own card; no deduplication logic.
5. **TradeChart with zero candles** — Existing empty state handling is sufficient. Do not add Arena-specific empty chart handling.
6. **Post-reconnect delay causing missed EOD flatten** — The 3s delay is applied only to the first portfolio query after reconnect, not to order operations. EOD flatten uses its own order submission path.

## Scope Boundaries
- Do NOT modify: Strategy detection logic (any pattern's `detect()` or `score()`), Risk Manager (`core/risk_manager.py`), Trade Logger (`analytics/trade_logger.py`), BacktestEngine, Experiment Pipeline, Learning Loop core (`intelligence/learning/`), Event Bus (`core/event_bus.py`)
- Do NOT optimize: Arena performance for >60 simultaneous positions, Databento reconnection, existing WebSocket message throughput
- Do NOT refactor: Strategy identity into a single source of truth (add to existing parallel maps only), AllocationDonut SVG rendering, Observatory 3D views, existing Dashboard card component internals
- Do NOT add: New strategy detection patterns, new config Pydantic models (except extending existing ones for reconnect delay), new database tables, new external API integrations

## Interaction Boundaries
- This sprint does NOT change the behavior of: `/ws/v1/live`, `/ws/v1/observatory`, `/ws/v1/ai/chat` WebSocket channels; any existing REST endpoint's response schema; OrderManager position management flow; strategy signal generation pipeline; quality engine scoring
- This sprint does NOT affect: Backtest validation, experiment registry, config proposal manager, catalyst pipeline, VIX data service computation, universe manager routing

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Strategy identity single-source-of-truth refactor | Unscheduled | DEF-135 |
| Arena historical replay mode | Unscheduled | DEF-136 |
| Arena click-to-trade actions | Unscheduled | DEF-137 |
| Arena L2/L3 order book overlay | Post-revenue | DEF-138 |
| Arena 100+ position virtualization | Unscheduled | DEF-139 |
| ABCD signal volume optimization | Sprint 32.5 experiments | DEF-122 (existing) |
| IB Gateway auto-restart implementation | Manual after docs | — |
