# Sprint 25.5 — Review Context File

> This file is shared by all session review prompts. It contains the Sprint Spec,
> Specification by Contradiction, Regression Checklist, and Escalation Criteria.
> Individual review prompts reference this file by path.

---

## Sprint Spec

### Goal
Fix the critical bug where strategy watchlists are empty when Universe Manager is enabled, causing all four strategies to silently drop every candle since Sprint 23 (March 7). Populate strategy watchlists from Universe Manager routing, convert watchlist storage to set for O(1) lookups at scale, and add a zero-evaluation health warning to prevent future silent failures.

### Deliverables
1. **Watchlist population from Universe Manager routing table.** After `build_routing_table()` in main.py, call `set_watchlist()` on each strategy with its UM-routed symbol set via `get_strategy_symbols()`. When UM is disabled, the existing scanner-based `set_watchlist()` path remains unchanged.
2. **Watchlist internal storage converted from list to set.** `BaseStrategy._watchlist` becomes a `set[str]` for O(1) membership checks. The public `watchlist` property continues to return `list[str]`.
3. **Startup log confirmation.** Each strategy logs its watchlist size at INFO level after population with source attribution.
4. **Zero-evaluation health warning.** HealthMonitor emits a WARNING if an active strategy has zero evaluation events 5 minutes after its configured time window opens. Distinguishes "UM routed 0 symbols" from "watchlist populated but no evaluations."
5. **End-to-end telemetry verification tests.** Tests confirming candle → strategy → ring buffer → SQLite → Observatory endpoints.

### Acceptance Criteria
1. **Watchlist population:**
   - UM enabled: `strategy.watchlist` length matches `universe_manager.get_strategy_symbols(strategy_id)` size
   - UM disabled: `strategy.watchlist` returns scanner symbols
   - `evaluation_events` accumulates rows within 5 min of strategy window opening
2. **List-to-set conversion:**
   - `set_watchlist()` accepts `list[str]`
   - `symbol not in self._watchlist` is O(1)
   - `strategy.watchlist` returns `list[str]`
3. **Startup logging:** INFO line per strategy with watchlist size and source
4. **Zero-evaluation health warning:**
   - WARNING if active strategy, non-empty watchlist, 0 evaluations, 5 min past window start
   - No warning if watchlist empty (UM routed 0)
   - No warning before window start + 5 min
   - No warning if ≥1 evaluation recorded
5. **E2E telemetry tests:**
   - Candle → evaluation in ring buffer
   - Ring buffer → SQLite persistence
   - Observatory endpoints return non-empty data when evaluations exist

### Config Changes
No config changes in this sprint.

### Session Count
2 sessions. Session 1: watchlist wiring + list→set. Session 2: health warning + e2e tests.

---

## Specification by Contradiction

### Out of Scope
1. Performance optimization for large symbol counts
2. Changes to Universe Manager filters or routing logic
3. Observatory frontend changes
4. Quality/catalyst pipeline changes
5. New evaluation event types or telemetry schema changes
6. Backfilling lost paper trading data
7. Removing the strategy-level watchlist check
8. Changes to candle routing path in main.py (lines 724-745)

### Do NOT Modify
- `argus/data/universe_manager.py`
- `argus/strategies/orb_base.py`
- `argus/strategies/vwap_reclaim.py`
- `argus/strategies/afternoon_momentum.py`
- `argus/core/orchestrator.py`
- `argus/core/risk_manager.py`
- `argus/execution/order_manager.py`
- `argus/analytics/observatory_service.py`
- Any config YAML files
- Any frontend files

### Do NOT Add
New API endpoints, config fields, database tables, WebSocket channels, or frontend components.

### Interaction Boundaries
Does NOT change: `on_candle()` logic in any strategy, `route_candle()` in UM, `_process_signal()` in main.py, Risk Manager gating, Order Manager execution, Event Bus delivery, Observatory WS push, any REST API response schema.

---

## Regression Checklist

- [ ] Scanner-only flow unchanged (UM disabled → strategies get scanner symbols)
- [ ] `watchlist` property returns `list[str]` (not set)
- [ ] `set_watchlist()` accepts `list[str]` input
- [ ] Strategy `on_candle()` evaluation logic unchanged
- [ ] Risk Manager not affected
- [ ] Event Bus FIFO ordering preserved
- [ ] Order Manager not affected
- [ ] Quality pipeline not affected
- [ ] Observatory endpoints return 200
- [ ] No files in "do not modify" list were changed
- [ ] All pre-existing tests pass
- [ ] Candle routing path in main.py (lines 724-745) unchanged

### Test Commands
**Full suite:** `pytest --ignore=tests/test_main.py -n auto` + `cd argus/ui && npx vitest run`
**Scoped (Session 1):** `pytest tests/test_strategies/ tests/test_main_startup.py -v`
**Scoped (Session 2):** `pytest tests/test_evaluation_telemetry_e2e.py tests/test_health.py -v`

---

## Escalation Criteria

### Tier 3 Triggers
1. Performance degradation: heartbeat candle counts drop significantly or API latency degrades
2. More than 5 existing tests break from list→set conversion
3. Evaluation events not in SQLite despite ring buffer being populated
4. Observatory endpoints empty despite evaluation_events having rows

### Session-Level Halts
- Session 1: pre-flight failure unrelated to scope → halt; `get_strategy_symbols()` unexpected results → halt
- Session 2: Session 1 review verdict REJECT → do not start; HealthMonitor lacks time-delayed check mechanism → redesign needed
