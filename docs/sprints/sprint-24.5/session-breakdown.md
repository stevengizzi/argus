# Sprint 24.5 — Session Breakdown

## Dependency Chain

```
S1 (infrastructure) → S2 (ORB) ─┐→ S3.5 (persistence) → S4 (frontend) → S5 (integration) → S5f
                    → S3 (VWAP/AfMo)─┘
S6 (operational fixes) — independent (parallelizable with any session)
```

---

## Session 1: Telemetry Infrastructure + REST Endpoint

**Objective:** Create the evaluation event model, ring buffer, BaseStrategy
integration, and REST endpoint. This is the foundation everything else builds on.

**Creates:**
- `argus/strategies/telemetry.py` — EvaluationEvent dataclass, EvaluationEventType
  enum, EvaluationResult enum, StrategyEvaluationBuffer class (~140 lines)

**Modifies:**
- `argus/strategies/base_strategy.py` — add `_eval_buffer` attribute in `__init__()`,
  add `record_evaluation()` convenience method, add `eval_buffer` property
- `argus/api/routes/strategies.py` — add `GET /{strategy_id}/decisions` endpoint

**Integrates:** Self-contained (creates infrastructure for subsequent sessions)

**Pre-flight reads:** `base_strategy.py`, `core/events.py` (QualitySignalEvent
pattern), `api/routes/strategies.py`, `api/routes/quality.py` (endpoint pattern)

**Tests (~10):**
- EvaluationEvent construction with all fields
- EvaluationEventType enum completeness (9 values)
- EvaluationResult enum completeness (3 values)
- Buffer append and FIFO eviction at maxlen
- Buffer query with no filter returns all
- Buffer query with symbol filter
- Buffer query with limit
- Buffer snapshot returns list copy
- REST endpoint returns 200 with events
- REST endpoint returns 404 for unknown strategy
- record_evaluation() swallows exceptions

**Parallelizable:** No (foundation session)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 1 (telemetry.py) | 2 |
| Files modified | 2 (base_strategy.py, strategies.py) | 2 |
| Pre-flight reads | 4 | 4 |
| Tests | ~10 | 5 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large file (>150 lines) | No | 0 |
| **Total** | | **13 (Medium)** |

---

## Session 2: ORB Family Instrumentation

**Objective:** Instrument OrbBaseStrategy and both ORB subclass strategies
with evaluation events at every decision point.

**Creates:** Nothing

**Modifies:**
- `argus/strategies/orb_base.py` — add ~8-10 `record_evaluation()` calls
  throughout `on_candle()`, `_finalize_opening_range()`,
  `_check_breakout_conditions()`, `_build_breakout_signal()`
- `argus/strategies/orb_breakout.py` — add 2-3 calls in
  `_calculate_pattern_strength()`
- `argus/strategies/orb_scalp.py` — add 2-3 calls in
  `_calculate_pattern_strength()`

**Integrates:** S1 telemetry (BaseStrategy.record_evaluation, EvaluationEventType)

**Pre-flight reads:** `telemetry.py` (S1 output), `base_strategy.py` (S1 output),
`orb_base.py`, `orb_breakout.py`, `orb_scalp.py`

**Tests (~8):**
- on_candle with symbol not in watchlist emits no events
- on_candle during OR window emits OPENING_RANGE_UPDATE
- on_candle after OR window emits OR finalization event with high/low
- on_candle with DEC-261 exclusion emits CONDITION_CHECK FAIL
- on_candle with breakout conditions met emits SIGNAL_GENERATED
- on_candle with breakout conditions failed emits SIGNAL_REJECTED with reason
- _calculate_pattern_strength emits QUALITY_SCORED (breakout)
- _calculate_pattern_strength emits QUALITY_SCORED (scalp)

**Parallelizable:** No (depends on S1, but S3 can run parallel with S2)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 0 | 0 |
| Files modified | 3 (orb_base, orb_breakout, orb_scalp) | 3 |
| Pre-flight reads | 5 | 5 |
| Tests | ~8 | 4 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large file (>150 lines) | No | 0 |
| **Total** | | **12 (Medium)** |

---

## Session 3: VWAP + Afternoon Momentum Instrumentation

**Objective:** Instrument VwapReclaimStrategy and AfternoonMomentumStrategy
with evaluation events at every decision point.

**Creates:** Nothing

**Modifies:**
- `argus/strategies/vwap_reclaim.py` — add evaluation events for 5-state machine
  transitions, VWAP cross detection, entry condition checks, pattern strength
- `argus/strategies/afternoon_momentum.py` — add evaluation events for
  consolidation detection, breakout evaluation, 8 entry condition checks
  individually, pattern strength

**Integrates:** S1 telemetry (BaseStrategy.record_evaluation, EvaluationEventType)

**Pre-flight reads:** `telemetry.py` (S1 output), `base_strategy.py` (S1 output),
`vwap_reclaim.py`, `afternoon_momentum.py`

**Tests (~8):**
- VWAP state transition MONITORING→APPROACHING emits STATE_TRANSITION
- VWAP state transition to EXHAUSTED emits STATE_TRANSITION
- VWAP entry conditions emit CONDITION_CHECK with pass/fail
- VWAP _calculate_pattern_strength emits QUALITY_SCORED
- AfMo consolidation detected emits STATE_TRANSITION
- AfMo each of 8 entry conditions emits CONDITION_CHECK
- AfMo breakout entry all-pass emits SIGNAL_GENERATED
- AfMo _calculate_pattern_strength emits QUALITY_SCORED

**Parallelizable:** Yes — can run parallel with S2. Both depend only on S1.
S3 modifies `vwap_reclaim.py` and `afternoon_momentum.py`; S2 modifies
`orb_base.py`, `orb_breakout.py`, `orb_scalp.py`. Zero file overlap.
Score is 10 (well under 14).

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 0 | 0 |
| Files modified | 2 (vwap_reclaim, afternoon_momentum) | 2 |
| Pre-flight reads | 4 | 4 |
| Tests | ~8 | 4 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large file (>150 lines) | No | 0 |
| **Total** | | **10 (Medium)** |

---

## Session 3.5: Evaluation Event Persistence

**Objective:** Add SQLite persistence for evaluation events with historical
query support and automatic retention cleanup.

**Creates:**
- `argus/strategies/telemetry_store.py` — EvaluationEventStore class with
  table creation, async write, query by strategy/symbol/date, retention
  cleanup (~120 lines)

**Modifies:**
- `argus/strategies/telemetry.py` — add persistence hook to
  StrategyEvaluationBuffer (optional store reference; when set, events are
  forwarded to store on record)
- `argus/api/routes/strategies.py` — add `?date=YYYY-MM-DD` query param to
  decisions endpoint; when date is past, query SQLite instead of ring buffer

**Integrates:** Wires persistence into S1's ring buffer. Store initialized in
server lifespan and passed to strategies via `set_telemetry_store()` on
BaseStrategy (or via buffer directly).

**Pre-flight reads:** `telemetry.py` (S1 output), `api/routes/strategies.py`
(S1 output), `db/manager.py` (DB patterns), `api/routes/quality.py`
(historical query pattern)

**Tests (~10):**
- Table creation on init
- Write event and read back
- Query by strategy_id returns only matching events
- Query by symbol returns only matching events
- Query by date returns only matching events
- Combined strategy_id + symbol + date query
- Retention cleanup purges events older than 7 days
- Retention cleanup preserves recent events
- REST `?date=` param routes to SQLite for past dates
- REST without date or today's date routes to ring buffer
- Persistence failure does not affect ring buffer operation

**Parallelizable:** No (depends on S1-S3 completion so telemetry.py API is
stable before adding persistence hook)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 1 (telemetry_store.py) | 2 |
| Files modified | 2 (telemetry.py, strategies.py route) | 2 |
| Pre-flight reads | 4 | 4 |
| Tests | ~10 | 5 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large file (>150 lines) | No | 0 |
| **Total** | | **13 (Medium)** |

---

## Session 4: Frontend — Strategy Decision Stream Component

**Objective:** Build the Strategy Decision Stream component and its TanStack
Query hook as self-contained units ready for integration.

**Creates:**
- `argus/ui/src/features/orchestrator/StrategyDecisionStream.tsx` — main
  component with event list, color coding, symbol filter, summary stats
  (~130 lines)
- `argus/ui/src/hooks/useStrategyDecisions.ts` — TanStack Query hook polling
  REST endpoint every 3 seconds (~40 lines)

**Modifies:**
- `argus/ui/src/features/orchestrator/index.ts` — export new component

**Integrates:** Self-contained (S5 wires into page)

**Pre-flight reads:** `features/orchestrator/RecentSignals.tsx` (list display
pattern), `features/orchestrator/SignalDetailPanel.tsx` (panel pattern),
`hooks/useQualityData.ts` (TanStack Query hook pattern), `services/` (API
service layer)

**Tests (~8):**
- Component renders with mock event data
- Events color-coded correctly (PASS=green, FAIL=red, etc.)
- Symbol filter dropdown filters displayed events
- Empty state shows "Awaiting market data" message
- Loading state shows skeleton
- Summary stats bar displays correct counts
- Hook polls at configured interval
- Hook handles API errors gracefully

**Parallelizable:** No (depends on S3.5 for complete REST API shape)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 2 (component + hook) | 4 |
| Files modified | 1 (index.ts export) | 1 |
| Pre-flight reads | 4 | 4 |
| Tests | ~8 | 4 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large file (>150 lines) | No | 0 |
| **Total** | | **13 (Medium)** |

---

## Session 5: Frontend — Orchestrator Page Integration

**Objective:** Wire the Strategy Decision Stream into the Orchestrator page
as a slide-out panel accessible from strategy cards.

**Creates:** Nothing

**Modifies:**
- `argus/ui/src/pages/OrchestratorPage.tsx` — add slide-out panel state and
  rendering (similar to existing dialog patterns)
- `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx` — add
  "View Decisions" button that triggers the slide-out panel with strategy_id

**Integrates:** S4's StrategyDecisionStream component into the Orchestrator page

**Pre-flight reads:** `OrchestratorPage.tsx`, `StrategyOperationsCard.tsx`,
`StrategyDecisionStream.tsx` (S4 output), `useStrategyDecisions.ts` (S4 output)

**Tests (~4):**
- Clicking "View Decisions" opens the slide-out panel
- Panel receives correct strategy_id
- Closing panel unmounts the Decision Stream (stops polling)
- 3-column layout (Section 4) is preserved after changes

**Parallelizable:** No (depends on S4)

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 0 | 0 |
| Files modified | 2 (OrchestratorPage, StrategyOperationsCard) | 2 |
| Pre-flight reads | 4 | 4 |
| Tests | ~4 | 2 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large file (>150 lines) | No | 0 |
| **Total** | | **8 (Low)** |

---

## Session 5f: Visual Review Fixes (Contingency — 0.5 session)

**Objective:** Fix any visual issues discovered during Session 5 review.

**Creates:** Nothing
**Modifies:** TBD based on visual review findings
**Tests:** TBD

**Compaction Risk:** ~5 (Low). Contingency slot — unused if visual review clean.

---

## Session 6: Operational Fixes

**Objective:** Fix three operational issues: AI Insight clock bug, Finnhub 403
log noise, FMP circuit breaker test coverage. Optionally produce candle cache
design doc.

**Creates:**
- (Optional) `docs/designs/candle-cache.md` — design document for future sprint

**Modifies:**
- `argus/ai/summary.py` — add `session_elapsed_minutes` to insight data, compute
  from 9:30 ET market open instead of system boot time
- `argus/intelligence/sources/finnhub.py` — change per-symbol 403 from
  `logger.error` to `logger.warning`, add per-cycle 403 counter with INFO summary

**Integrates:** N/A (standalone fixes, no dependencies on S1-S5)

**Pre-flight reads:** `ai/summary.py`, `ai/context.py` (check for related
uptime references), `intelligence/sources/finnhub.py`,
`intelligence/sources/fmp_news.py` (circuit breaker verification)

**Tests (~8):**
- Clock fix: during market hours returns correct minutes since 9:30 ET
- Clock fix: before market open returns pre-market indicator
- Clock fix: after market close returns closed indicator
- Finnhub 403: per-symbol 403 logged at WARNING level
- Finnhub 403: per-cycle summary logged at INFO level
- FMP circuit breaker: first 403 sets _disabled_for_cycle = True
- FMP circuit breaker: subsequent symbols skipped after 403
- FMP system_live.yaml has fmp_news.enabled = false

**Parallelizable:** Yes — fully independent of S1-S5. Modifies different files.
Score is 10 (well under 14).

**Compaction Risk:**

| Factor | Count | Points |
|--------|-------|--------|
| Files created | 0 (design doc optional, not scored) | 0 |
| Files modified | 2 (summary.py, finnhub.py) | 2 |
| Pre-flight reads | 4 | 4 |
| Tests | ~8 | 4 |
| Complex integration wiring | No | 0 |
| External API debugging | No | 0 |
| Large file (>150 lines) | No | 0 |
| **Total** | | **10 (Medium)** |

---

## Summary

| Session | Scope | Score | Risk | Parallel |
|---------|-------|-------|------|----------|
| S1 | Telemetry infrastructure + REST | 13 | Medium | No |
| S2 | ORB instrumentation | 12 | Medium | No |
| S3 | VWAP + AfMo instrumentation | 10 | Medium | Yes (with S2) |
| S3.5 | Persistence layer | 13 | Medium | No |
| S4 | Frontend component + hook | 13 | Medium | No |
| S5 | Frontend page integration | 8 | Low | No |
| S5f | Visual review fixes | ~5 | Low | Contingency |
| S6 | Operational fixes | 10 | Medium | Yes (independent) |

**Total estimated new tests:** ~56 pytest + ~12 Vitest = ~68
**Post-sprint targets:** ~2,765 pytest + ~515 Vitest
