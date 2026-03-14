# Sprint 24.5 — Review Context File

> This file is read by the @reviewer subagent (or manual reviewer) for every
> session in Sprint 24.5. It contains the Sprint Spec, Specification by
> Contradiction, Regression Checklist, and Escalation Criteria.
>
> Session-specific review prompts reference this file by path and add only
> session-specific scope and focus items.

---

## Sprint Spec

### Sprint 24.5: Strategy Observability + Operational Fixes

**Goal:** Give the user real-time and historical visibility into what every
strategy is "thinking" on every candle, so that paper trading validation days
produce actionable diagnostic data even when zero trades occur. Fix three
operational issues identified during live QA.

**Deliverables:**

1. Evaluation Event Model — `EvaluationEvent` frozen dataclass with
   `EvaluationEventType` enum (9 values) and `EvaluationResult` enum (3 values)
   in `argus/strategies/telemetry.py`.

2. In-Memory Ring Buffer — `StrategyEvaluationBuffer` wrapping
   `collections.deque(maxlen=1000)`. Attached to `BaseStrategy` as
   `self._eval_buffer`. Fire-and-forget `record_evaluation()` on BaseStrategy.

3. ORB Family Instrumentation — `OrbBaseStrategy.on_candle()` instrumented at
   every decision point. ORB Breakout and ORB Scalp `_calculate_pattern_strength()`
   also instrumented.

4. VWAP Reclaim Instrumentation — 5-state machine transitions, VWAP cross
   detection, entry conditions, pattern strength.

5. Afternoon Momentum Instrumentation — consolidation detection, breakout
   evaluation, 8 entry conditions individually, pattern strength.

6. SQLite Persistence — `EvaluationEventStore` in
   `argus/strategies/telemetry_store.py`. `evaluation_events` table in argus.db.
   7-day retention with auto-purge.

7. REST Endpoint — `GET /api/v1/strategies/{strategy_id}/decisions` with
   `symbol`, `limit`, `date` query params. Ring buffer for today, SQLite for
   historical.

8. Frontend: Strategy Decision Stream — `StrategyDecisionStream.tsx` with
   color-coded events, symbol filter, summary stats. Slide-out panel from
   `StrategyOperationsCard`.

9. AI Insight Clock Bug Fix — `session_elapsed_minutes` from 9:30 ET market open.

10. Finnhub 403 Log Downgrade — ERROR → WARNING for per-symbol 403s.

11. FMP Circuit Breaker Test — prove DEC-323 trips on first 403.

**Key Constraints:**
- Evaluation events do NOT use EventBus (diagnostic, not trading events)
- ET timestamps (DEC-276)
- `record_evaluation()` must never block candle processing or raise exceptions
- No modifications to strategy entry/exit logic
- No config changes (ring buffer size and retention are code constants)
- Frontend 3-column layout on Orchestrator preserved

---

## Specification by Contradiction

### Out of Scope
1. WebSocket real-time push for evaluation events
2. Candle cache implementation (design doc only if time allows)
3. Process split / architecture separation
4. Strategy logic changes
5. News source upgrades
6. Modifications to Sprint 24 deliverables
7. Evaluation event aggregation or analytics
8. Backfill of historical evaluation events

### Do NOT Modify
- `argus/core/events.py`
- `argus/api/websocket/live.py`
- `argus/main.py`
- `argus/core/orchestrator.py`
- `argus/execution/order_manager.py`
- `argus/core/risk_manager.py`

### Do NOT Add
- Config fields for ring buffer size or retention period
- Evaluation event filtering by event_type in REST API
- Dedicated evaluation events page in frontend
- EventBus event types for evaluation events

### Interaction Boundaries
- No change to: SignalEvent generation, QualitySignalEvent publishing,
  Risk Manager evaluation, Order Manager execution, EventBus subscriptions,
  WebSocket bridge, existing REST endpoints, existing frontend pages.

---

## Sprint-Level Regression Checklist

### Core Invariants (Check Every Session)
- [ ] All 4 strategies produce correct SignalEvent output (unchanged)
- [ ] on_candle() return values unchanged for all strategies
- [ ] ORB same-symbol exclusion (DEC-261) still works
- [ ] Quality pipeline flow (_process_signal() in main.py) untouched
- [ ] Risk Manager check 0 (DEC-336) untouched
- [ ] Existing REST API endpoints return same responses
- [ ] WebSocket bridge event types unchanged
- [ ] Existing frontend pages render without console errors

### After S1 (Telemetry Infrastructure)
- [ ] BaseStrategy subclass construction works
- [ ] record_evaluation() never raises
- [ ] New REST endpoint is JWT-protected
- [ ] Existing strategies route endpoints unchanged

### After S2 (ORB Instrumentation)
- [ ] OrbBaseStrategy.on_candle() returns same signals for same inputs
- [ ] ORB pattern strength scores unchanged
- [ ] All record_evaluation() calls try/except guarded

### After S3 (VWAP + AfMo Instrumentation)
- [ ] VWAP state machine transitions unchanged
- [ ] AfMo 8 entry conditions unchanged
- [ ] Pattern strength scores unchanged
- [ ] All record_evaluation() calls try/except guarded

### After S3.5 (Persistence)
- [ ] evaluation_events table created without affecting existing tables
- [ ] Persistence failure does not impact ring buffer
- [ ] REST endpoint still works without persistence
- [ ] Historical date query returns correct subset

### After S4 (Frontend Component)
- [ ] No new TypeScript build errors (baseline: 0)
- [ ] Component renders without console errors
- [ ] Existing orchestrator components unaffected

### After S5 (Frontend Integration)
- [ ] OrchestratorPage 3-column layout preserved
- [ ] StrategyOperationsGrid renders all strategy cards
- [ ] Navigation and shortcuts (DEC-199) work

### After S6 (Operational Fixes)
- [ ] AI Insight card generates insights
- [ ] Finnhub source fetches news for working symbols
- [ ] FMP news still disabled in system_live.yaml

### Test Suite
- [ ] Full pytest passes with -n auto (excluding DEF-048/049)
- [ ] Full Vitest passes
- [ ] ruff linting passes

---

## Sprint-Level Escalation Criteria

### Critical (Halt Immediately)
1. Strategy on_candle() behavior change — instrumentation alters return value
2. Ring buffer blocks candle processing — measurable latency >100μs
3. BaseStrategy construction breaks — any strategy construction test fails
4. Existing REST endpoints break — non-additive changes to strategies router

### Significant (Complete Current Task, Then Escalate)
5. SQLite write throughput insufficient — can't keep up at 200 events/sec
6. Frontend 3-column layout disruption
7. Test count deviation >50% from estimate
8. AI Insight clock bug not in summary.py — fix approach changes

### Informational (Log and Continue)
9. Pre-existing test failures (DEF-048, DEF-049)
10. Strategy instrumentation placement ambiguity — use best judgment, document
