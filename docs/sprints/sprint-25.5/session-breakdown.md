# Sprint 25.5: Session Breakdown

## Session 1: Watchlist Wiring + List-to-Set Performance Fix

**Objective:** Populate strategy watchlists from Universe Manager routing table after `build_routing_table()`. Convert `_watchlist` internal storage from `list` to `set` for O(1) membership checks. Preserve backward compatibility when UM is disabled.

**Creates:** None

**Modifies:**
- `argus/main.py` — Add watchlist population block after Phase 9.5 (`build_routing_table()`), calling `strategy.set_watchlist(list(universe_manager.get_strategy_symbols(strategy_id)))` for each strategy. Add INFO log per strategy with watchlist size and source.
- `argus/strategies/base_strategy.py` — Change `_watchlist: list[str] = []` to `_watchlist: set[str] = set()`. Update `set_watchlist()` to store as set. Update `watchlist` property to return `list(self._watchlist)`. Update `reset_daily_state()` to clear with `set()`.

**Integrates:** N/A (first session)

**Parallelizable:** No

**Tests (~8):**
1. UM enabled: strategy watchlist populated with UM-routed symbols
2. UM disabled: strategy watchlist populated with scanner symbols
3. `set_watchlist()` accepts `list[str]`, stores as set
4. `watchlist` property returns `list[str]`
5. `on_candle()` processes candle for watchlisted symbol (not early-returned)
6. `on_candle()` returns None for non-watchlisted symbol
7. Empty UM routing → empty watchlist (no crash)
8. `reset_daily_state()` clears watchlist to empty set

**Compaction Risk:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 | 2 |
| Context/pre-flight reads | 4 (main.py, base_strategy.py, universe_manager.py, orb_base.py) | 4 |
| New tests | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **10 (Medium)** |

---

## Session 2: Zero-Evaluation Health Warning + E2E Telemetry Verification

**Objective:** Add a health check that warns when an active strategy has zero evaluation events 5 minutes after its time window opens (detecting future silent failures). Write end-to-end tests confirming evaluation telemetry flows from candle delivery through to SQLite persistence and Observatory endpoints.

**Creates:**
- `tests/test_evaluation_telemetry_e2e.py` — End-to-end telemetry verification tests

**Modifies:**
- `argus/core/health.py` — Add `check_strategy_evaluations()` method. Called periodically (or on-demand). For each active strategy: if current time > strategy window start + 5 min AND strategy watchlist is non-empty AND evaluation count for this strategy today == 0, emit WARNING. Requires access to strategy references and EvaluationEventStore (or a count query method).

**Integrates:** Session 1 (e2e tests require watchlist-populated strategies to produce evaluation events)

**Parallelizable:** No (depends on Session 1)

**Tests (~8):**
1. Warning fires: active strategy, non-empty watchlist, 0 evaluations, 5 min past window start
2. No warning: strategy has ≥1 evaluation event
3. No warning: strategy watchlist is empty (UM routed 0 symbols — legitimate)
4. No warning: before strategy's time window + 5 min
5. E2E: candle → strategy `on_candle()` → `record_evaluation()` → ring buffer contains event
6. E2E: evaluation event in ring buffer → persisted to `evaluation_events` SQLite table
7. Observatory `/api/v1/observatory/pipeline` returns non-empty when evaluations exist
8. Observatory `/api/v1/observatory/session-summary` returns non-empty when evaluations exist

**Compaction Risk:**
| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 | 2 |
| Files modified | 1 | 1 |
| Context/pre-flight reads | 5 (health.py, base_strategy.py, telemetry_store.py, server.py, observatory_service.py) | 5 |
| New tests | 8 | 4 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **12 (Medium)** |

---

## Session Dependency Chain

```
Session 1 (Watchlist Wiring) → Session 2 (Health Warning + E2E Tests)
```

Session 2 cannot start until Session 1 is verified — the e2e tests depend on candles reaching strategy evaluation logic.
