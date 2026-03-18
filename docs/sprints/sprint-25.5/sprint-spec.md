# Sprint 25.5: Universe Manager Watchlist Wiring Fix

## Goal
Fix the critical bug where strategy watchlists are empty when Universe Manager is enabled, causing all four strategies to silently drop every candle since Sprint 23 (March 7). Populate strategy watchlists from Universe Manager routing, convert watchlist storage to set for O(1) lookups at scale, and add a zero-evaluation health warning to prevent future silent failures.

## Scope

### Deliverables
1. **Watchlist population from Universe Manager routing table.** After `build_routing_table()` in main.py, call `set_watchlist()` on each strategy with its UM-routed symbol set via `get_strategy_symbols()`. When UM is disabled, the existing scanner-based `set_watchlist()` path remains unchanged.
2. **Watchlist internal storage converted from list to set.** `BaseStrategy._watchlist` becomes a `set[str]` for O(1) membership checks. The public `watchlist` property continues to return `list[str]`.
3. **Startup log confirmation.** Each strategy logs its watchlist size at INFO level after population (e.g., `strat_orb_breakout: watchlist set to 2101 symbols (source: universe_manager)`).
4. **Zero-evaluation health warning.** HealthMonitor emits a WARNING if an active strategy has zero evaluation events 5 minutes after its configured time window opens. Distinguishes "UM routed 0 symbols" (legitimate, no warning) from "watchlist populated but no evaluations recorded" (warning).
5. **End-to-end telemetry verification tests.** Tests confirming the full path: candle event → strategy `on_candle()` → `record_evaluation()` → `StrategyEvaluationBuffer` (ring buffer) → `EvaluationEventStore` (SQLite). Plus Observatory endpoint smoke tests.

### Acceptance Criteria
1. **Watchlist population:**
   - With UM enabled: after startup, `strategy.watchlist` returns a list with length matching `universe_manager.get_strategy_symbols(strategy_id)` for each strategy
   - With UM disabled: after startup, `strategy.watchlist` returns scanner symbols (existing behavior)
   - `evaluation_events` table accumulates rows within 5 minutes of each strategy's time window opening (verified by SQL query)
2. **List-to-set conversion:**
   - `set_watchlist()` accepts `list[str]` input (no caller changes required)
   - `symbol not in self._watchlist` is O(1) (set-based)
   - `strategy.watchlist` property returns `list[str]` (API contract preserved)
3. **Startup logging:**
   - INFO log line per strategy showing watchlist size and source (`universe_manager` or `scanner`)
4. **Zero-evaluation health warning:**
   - WARNING emitted if an active strategy with a non-empty watchlist has 0 evaluation events 5 minutes after its time window opens
   - No warning emitted if the strategy's watchlist is empty due to UM routing returning 0 symbols
   - No warning emitted before the strategy's time window opens
   - No warning emitted if the strategy has recorded at least 1 evaluation event
5. **E2E telemetry tests:**
   - Test confirming a candle delivered to a strategy with a populated watchlist results in an evaluation event in the ring buffer
   - Test confirming evaluation events in the ring buffer are persisted to `evaluation_events` SQLite table
   - Test confirming `/api/v1/observatory/pipeline` returns non-empty data when evaluation events exist
   - Test confirming `/api/v1/observatory/session-summary` returns non-empty data when evaluation events exist

### Performance Benchmarks
| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| `on_candle` watchlist check | O(1) per call | Code inspection (set membership) |
| Startup watchlist population | < 100ms for 2,101 symbols | Timestamp delta in logs |
| No observable event loop latency | Heartbeat candle counts unchanged | Compare heartbeat logs before/after fix |

### Config Changes
No config changes in this sprint.

## Dependencies
- `UniverseManager.get_strategy_symbols(strategy_id)` exists and returns `set[str]` (confirmed in codebase)
- `EvaluationEventStore` initialized and wired to strategy buffers in `server.py` (confirmed)
- Observatory endpoints registered and returning 200 (confirmed from March 18 logs)
- Sprint 25 (Observatory) complete (confirmed)

## Relevant Decisions
- DEC-263: Full-universe strategy-specific monitoring — the architectural intent that Universe Manager provides per-strategy symbol routing
- DEC-277: Fail-closed on missing reference data — symbols without reference data are excluded from viable universe
- DEC-299: Full-universe input pipe via stock-list — ~8,000 symbols fetched, ~3,000-4,000 viable
- DEC-342: Strategy evaluation telemetry — ring buffer + SQLite persistence + REST endpoint
- DEC-316: Time-aware warm-up — pre-market boot skips warm-up (relevant: indicators build from live stream on first candles after watchlist fix)
- DEC-328: Test suite tiering — full suite at sprint entry and each closeout; scoped tests mid-sprint

## Relevant Risks
- RSK-022: IBKR Gateway nightly resets — not directly affected, but the fix means strategies will actually generate signals requiring broker interaction
- New risk: 140× increase in symbols hitting strategy logic per candle may surface latent performance issues in per-symbol state management (opening range tracking, VWAP state machines). If observed, halt and scope a performance sprint.

## Session Count Estimate
2 sessions estimated. Session 1 is the core wiring fix (main.py + base_strategy.py). Session 2 adds the health warning and e2e telemetry tests, depending on Session 1. Both score Medium on compaction risk (10 and 12 respectively).
