# Sprint 24.5: Strategy Observability + Operational Fixes

## Goal

Give the user real-time and historical visibility into what every strategy is
"thinking" on every candle, so that paper trading validation days produce
actionable diagnostic data even when zero trades occur. Fix three operational
issues identified during live QA.

## Scope

### Deliverables

1. **Evaluation Event Model** — Frozen dataclass (`EvaluationEvent`) with enum
   `EvaluationEventType` (TIME_WINDOW_CHECK, INDICATOR_STATUS,
   OPENING_RANGE_UPDATE, ENTRY_EVALUATION, CONDITION_CHECK, SIGNAL_GENERATED,
   SIGNAL_REJECTED, STATE_TRANSITION, QUALITY_SCORED) and result enum (PASS,
   FAIL, INFO). Located in `argus/strategies/telemetry.py`.

2. **In-Memory Ring Buffer** — `StrategyEvaluationBuffer` class wrapping
   `collections.deque(maxlen=1000)` with query methods (filter by symbol,
   limit results, snapshot for REST reads). Attached to `BaseStrategy` as
   `self._eval_buffer`. Fire-and-forget `record_evaluation()` convenience
   method on `BaseStrategy`, try/except guarded.

3. **ORB Family Instrumentation** — `OrbBaseStrategy.on_candle()` instrumented
   at every decision point: time window checks, opening range accumulation and
   finalization, DEC-261 exclusion check, entry window check, risk limit check,
   concurrent position check, breakout condition check, signal generation or
   rejection. ORB Breakout and ORB Scalp `_calculate_pattern_strength()` also
   instrumented.

4. **VWAP Reclaim Instrumentation** — 5-state machine transitions (MONITORING →
   APPROACHING → TESTING → CONFIRMED → ENTERED, plus EXHAUSTED), VWAP cross
   detection, entry condition evaluation, volume/spread checks, pattern strength.

5. **Afternoon Momentum Instrumentation** — Consolidation detection, breakout
   evaluation, all 8 entry condition checks logged individually with pass/fail,
   pattern strength.

6. **SQLite Persistence** — `EvaluationEventStore` class in
   `argus/strategies/telemetry_store.py`. Writes evaluation events to
   `evaluation_events` table in `argus.db`. Indexes on (trading_date,
   strategy_id) and (trading_date, symbol). 7-day retention with auto-purge at
   startup. Async writes via aiosqlite.

7. **REST Endpoint** — `GET /api/v1/strategies/{strategy_id}/decisions` with
   query params: `symbol` (optional), `limit` (default 100, max 500), `date`
   (optional, YYYY-MM-DD). When `date` omitted or today: reads ring buffer.
   When `date` is past: reads SQLite. JWT-protected (DEC-102).

8. **Frontend: Strategy Decision Stream** — `StrategyDecisionStream.tsx`
   component showing live-scrolling evaluation events for a selected strategy.
   Color-coded by result (green=PASS, red=FAIL, amber=STATE_TRANSITION/INFO,
   blue=SIGNAL_GENERATED/QUALITY_SCORED). Symbol filter dropdown. Summary stats
   bar (symbols tracked, signals generated/rejected today). Accessed via
   slide-out panel from `StrategyOperationsCard` — does NOT disrupt 3-column
   layout.

9. **AI Insight Clock Bug Fix** — `_assemble_insight_data()` in
   `argus/ai/summary.py` provides explicit `session_elapsed_minutes` computed
   from 9:30 ET market open. Before open: "pre-market". During session: minutes
   since 9:30 ET. After close: "closed".

10. **Finnhub 403 Log Downgrade** — Per-symbol 403 responses in
    `argus/intelligence/sources/finnhub.py` logged at WARNING instead of ERROR.
    Per-cycle summary counter at INFO level.

11. **FMP Circuit Breaker Test** — Test proving DEC-323 circuit breaker trips
    on first 403 and skips remaining symbols. Confirms `fmp_news.enabled: false`
    in `system_live.yaml`.

### Acceptance Criteria

1. **Evaluation Event Model:**
   - `EvaluationEvent` dataclass instantiable with all fields
   - `EvaluationEventType` enum has exactly 9 values
   - `EvaluationResult` enum has exactly 3 values (PASS, FAIL, INFO)
   - Timestamps are ET naive datetimes (DEC-276)

2. **Ring Buffer:**
   - `StrategyEvaluationBuffer(maxlen=1000)` evicts oldest when full
   - `.record(event)` is O(1) and never raises
   - `.query(symbol=None, limit=100)` returns filtered list
   - `.snapshot()` returns a list copy (safe for concurrent reads)

3. **ORB Instrumentation:**
   - `OrbBaseStrategy.on_candle()` emits ≥1 evaluation event per call
   - Events cover: time window, OR finalization, exclusion check, breakout
     conditions, signal/rejection
   - `_calculate_pattern_strength()` emits QUALITY_SCORED event
   - All instrumentation wrapped in try/except — telemetry failure never
     prevents signal generation

4. **VWAP Instrumentation:**
   - Every state transition emits STATE_TRANSITION event with from/to states
   - Entry condition checks emit CONDITION_CHECK with pass/fail
   - Pattern strength emits QUALITY_SCORED

5. **Afternoon Momentum Instrumentation:**
   - Each of 8 entry conditions emits a CONDITION_CHECK event with pass/fail
   - Consolidation detection emits STATE_TRANSITION
   - Pattern strength emits QUALITY_SCORED

6. **Persistence:**
   - `evaluation_events` table created at startup
   - Events written asynchronously without blocking strategy evaluation
   - Query by (strategy_id, date) returns correct events
   - Query by (strategy_id, symbol, date) returns filtered events
   - Events older than 7 trading days are purged at startup

7. **REST Endpoint:**
   - `GET /api/v1/strategies/{strategy_id}/decisions` returns 200 with JSON array
   - `?symbol=AAPL` filters to only AAPL events
   - `?limit=50` returns at most 50 events
   - `?date=2026-03-12` queries SQLite for historical data
   - Unknown strategy_id returns 404
   - Requires JWT auth

8. **Frontend:**
   - `StrategyDecisionStream` renders a scrolling list of events
   - Events are color-coded by result type
   - Symbol filter dropdown filters displayed events
   - Summary stats bar shows symbol count and signal counts
   - Component accessible from `StrategyOperationsCard` slide-out
   - Does NOT modify 3-column layout in Section 4 of OrchestratorPage

9. **AI Insight Clock Fix:**
   - During market hours (9:30–16:00 ET), insight data includes correct
     `session_elapsed_minutes` from 9:30 ET
   - Before market open, shows pre-market state
   - After close, shows closed state
   - Test covers all three time windows

10. **Finnhub 403:**
    - Per-symbol 403 logged at WARNING (not ERROR)
    - Per-cycle summary at INFO: "Finnhub: {n}/{total} symbols returned 403"
    - Test verifies log level

11. **FMP Circuit Breaker:**
    - Test mocks 403 on first symbol, verifies `_disabled_for_cycle = True`
    - Test verifies remaining symbols are skipped
    - `system_live.yaml` has `fmp_news.enabled: false`

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| `record_evaluation()` latency | < 1μs (deque append) | Not formally measured — O(1) by construction |
| Ring buffer query (1000 events) | < 5ms | pytest timing assertion |
| REST endpoint response | < 50ms (ring buffer), < 200ms (SQLite) | Manual verification |
| SQLite write throughput | ≥ 200 events/sec | Covered by existing aiosqlite WAL performance |

### Config Changes

No config changes in this sprint. Ring buffer size (1,000) and retention period
(7 days) are constants in code.

## Dependencies

- Sprint 24 + 24.1 merged to `main` (confirmed — all Quality Engine + cleanup complete)
- All 4 strategies implement `_calculate_pattern_strength()` (Sprint 24, confirmed)
- `BaseStrategy` ABC is the sole strategy parent class (DEC-028, confirmed)
- `OrbBaseStrategy` ABC is shared by ORB Breakout + ORB Scalp (DEC-120, confirmed)
- Existing `strategies.py` route in `argus/api/routes/` (confirmed)
- aiosqlite available (existing dependency, used throughout)

## Relevant Decisions

- DEC-025: Event Bus FIFO — evaluation events do NOT use EventBus (they are not trading events)
- DEC-028: Strategy daily-stateful, session-stateless — telemetry follows same lifecycle (ring buffer cleared on daily reset, persistence keyed by trading date)
- DEC-029: Event Bus sole streaming — NOT violated; evaluation events bypass EventBus intentionally to avoid flooding trading event queues
- DEC-088: Databento threading — by the time on_candle() executes, we're on the asyncio event loop; no threading concerns for telemetry writes
- DEC-102: JWT auth — new REST endpoint must be JWT-protected
- DEC-120: OrbBaseStrategy ABC — instrumentation goes in shared base
- DEC-261: ORB same-symbol exclusion — must be preserved; instrumentation logs when exclusion fires
- DEC-276: ET timestamps for AI layer — evaluation events use ET naive datetimes
- DEC-336: Risk Manager check 0 — separate from telemetry; not modified

## Relevant Risks

- RSK-022: IBKR Gateway nightly resets — not affected (telemetry is strategy-layer, not broker-layer)

## Session Count Estimate

7 sessions + 0.5 contingency estimated. 4 backend sessions (infrastructure,
ORB instrumentation, VWAP/AfMo instrumentation, persistence), 2 frontend
sessions (component, integration) + 0.5 visual-review fix contingency, 1
operational fixes session. Persistence session added per user decision to
include SQLite historical storage.
