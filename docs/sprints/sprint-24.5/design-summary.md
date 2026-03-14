# Sprint 24.5 — Design Summary

> **Compaction insurance.** If context is lost, this document alone is sufficient
> to regenerate all sprint artifacts.

## Sprint Identity

- **Number:** 24.5
- **Name:** Strategy Observability + Operational Fixes
- **Execution mode:** Autonomous
- **Baseline tests:** 2,709 pytest + 503 Vitest
- **DEC range:** DEC-342 through DEC-350

## Goal

Give the user real-time and historical visibility into what every strategy is
"thinking" on every candle, so that paper trading validation days produce
actionable diagnostic data even when zero trades occur. Fix three operational
issues identified during live QA.

## Trigger

A full-day market hours log analysis (March 12, 2026) revealed that strategy
observability is zero — 10,000+ candles flowing per 5-minute window at peak,
3,500+ active symbols, but zero logging from the strategy evaluation layer.
When zero trades happen, there is no way to determine whether strategies
correctly evaluated and rejected all setups, or whether candles aren't reaching
strategy instances at all.

## Architecture Decisions

### Evaluation Event Model
- Frozen dataclass in `argus/strategies/telemetry.py` — NOT in `core/events.py`.
  These are diagnostic telemetry, not trading events. They do not participate in
  the execution pipeline or EventBus.
- Fields: timestamp (ET, naive datetime per DEC-276), symbol, strategy_id,
  event_type (enum: TIME_WINDOW_CHECK, INDICATOR_STATUS, OPENING_RANGE_UPDATE,
  ENTRY_EVALUATION, CONDITION_CHECK, SIGNAL_GENERATED, SIGNAL_REJECTED,
  STATE_TRANSITION, QUALITY_SCORED), result (PASS/FAIL/INFO), reason
  (human-readable string), metadata (dict for strategy-specific data).
- Follows `QualitySignalEvent` pattern in `core/events.py` for style consistency.

### Ring Buffer (In-Memory)
- `collections.deque(maxlen=1000)` per strategy instance — O(1) append, automatic
  FIFO eviction when full.
- 1,000 events per strategy. At steady-state (~2,000 symbols, 1-3 events per
  candle), covers ~20-60 seconds unfiltered, effectively full-session history for
  single-symbol filter queries.
- Attached to `BaseStrategy` as `self._eval_buffer: StrategyEvaluationBuffer`.
- `record_evaluation()` convenience method on `BaseStrategy` — fire-and-forget,
  wrapped in try/except so telemetry failures never impact strategy logic.
- Thread-safe: `deque` with GIL + single event-loop writer is sufficient. REST
  endpoint reads via snapshot (list copy).

### SQLite Persistence
- `evaluation_events` table in `argus.db` (not a separate database — these are
  lightweight diagnostic rows, co-located with trade data for query convenience).
- Schema: id (INTEGER PK AUTOINCREMENT), trading_date (TEXT), timestamp (TEXT),
  symbol (TEXT), strategy_id (TEXT), event_type (TEXT), result (TEXT),
  reason (TEXT), metadata_json (TEXT).
- Indexes: (trading_date, strategy_id), (trading_date, symbol).
- Write path: `EvaluationEventStore` receives events from the ring buffer's
  persistence hook. Inline async writes via aiosqlite (not batched — event
  volume is ~200/sec total, well within SQLite WAL throughput).
- Retention: auto-purge events older than 7 trading days. Cleanup runs at
  system startup.
- `EvaluationEventStore` initialized in server lifespan, passed to strategies
  via `BaseStrategy.set_telemetry_store()`.

### REST API
- `GET /api/v1/strategies/{strategy_id}/decisions` — returns evaluation events.
- Query params: `symbol` (optional filter), `limit` (default 100, max 500),
  `date` (optional, YYYY-MM-DD format).
- When `date` is omitted or matches today: read from ring buffer (fast, in-memory).
- When `date` is a past date: read from SQLite.
- Response: JSON array of event objects.
- Auth: JWT (DEC-102), consistent with all other API endpoints.

### Strategy Instrumentation Points

**OrbBaseStrategy (shared by ORB Breakout + ORB Scalp):**
- TIME_WINDOW_CHECK: Is candle in OR window? Past OR window?
- OPENING_RANGE_UPDATE: OR candle accumulated, OR finalized (with high/low/valid)
- ENTRY_EVALUATION: Breakout direction check, volume confirmation
- CONDITION_CHECK: Entry window check, internal risk limits, concurrent positions,
  DEC-261 same-symbol exclusion
- SIGNAL_GENERATED / SIGNAL_REJECTED: Final outcome with full reason

**ORB Breakout / ORB Scalp (subclass-specific):**
- QUALITY_SCORED: `_calculate_pattern_strength()` result with component scores

**VWAP Reclaim:**
- STATE_TRANSITION: Each transition in 5-state machine (MONITORING → APPROACHING
  → TESTING → CONFIRMED → ENTERED, plus EXHAUSTED)
- INDICATOR_STATUS: VWAP value, price-to-VWAP distance
- ENTRY_EVALUATION: Volume/spread checks
- CONDITION_CHECK: Per-condition pass/fail
- QUALITY_SCORED: Pattern strength result

**Afternoon Momentum:**
- STATE_TRANSITION: Consolidation detection, breakout phase
- ENTRY_EVALUATION: 8 entry conditions — each logged individually with pass/fail
- CONDITION_CHECK: Each of the 8 conditions as separate events
- QUALITY_SCORED: Pattern strength result

### Frontend: Strategy Decision Stream
- New component: `StrategyDecisionStream.tsx` in
  `argus/ui/src/features/orchestrator/`.
- Live-scrolling log of evaluation events for a selected strategy.
- Color coding: green (PASS), red (FAIL), amber (STATE_TRANSITION/INFO),
  blue (SIGNAL_GENERATED/QUALITY_SCORED).
- Symbol filter dropdown at top.
- Summary stats bar: symbols actively tracked, symbols past time window,
  signals generated today, signals rejected today.
- Access: slide-out panel triggered from strategy cards in
  `StrategyOperationsGrid` — "View Decisions" button. Does NOT disrupt the
  existing 3-column layout (DecisionTimeline + CatalystAlerts + RecentSignals).
- TanStack Query hook (`useStrategyDecisions`) polls REST endpoint every 3
  seconds. Appends new events to local state (Zustand or React state) for
  smooth scrolling.
- Follows existing patterns: `RecentSignals.tsx` for list display,
  `SignalDetailPanel.tsx` for slide-out panel, `GRADE_COLORS` for quality display.

### Operational Fixes

**AI Insight clock bug:**
- In `argus/ai/summary.py`, method `_assemble_insight_data()` — currently
  computes `market_open` boolean but does not compute elapsed session time.
  The insight prompt receives current_time but not a "minutes into session"
  value. The bug is likely in the prompt template or in how the AI generates
  the elapsed time claim using the uptime from the health endpoint.
- Fix: Add explicit `session_elapsed_minutes` field to insight data. Compute
  from 9:30 ET market open. Before open: negative (or "pre-market" string).
  During session: minutes since 9:30 ET. After close: "closed". Include in
  the insight prompt context so the AI uses the correct value instead of
  inferring from uptime.

**Finnhub 403 downgrade:**
- In `argus/intelligence/sources/finnhub.py`, line 341-342: change
  `logger.error("Finnhub API access denied (HTTP 403)")` to
  `logger.warning("Finnhub HTTP 403 for %s — free tier coverage gap", url)`.
- Add per-cycle 403 counter. After each poll cycle, emit single INFO summary:
  "Finnhub: {n}/{total} symbols returned 403 — free tier coverage gap."

**FMP circuit breaker verification:**
- Write test: mock first symbol returning 403, verify `_disabled_for_cycle`
  is set True, verify remaining symbols are skipped.
- Verify `fmp_news.enabled: false` in `system_live.yaml` (confirmed — already
  false on current main).
- No code change expected — just test coverage for existing DEC-323
  implementation.

## Scope Exclusions

- WebSocket real-time push for evaluation events (EventBus flooding risk with
  diagnostic telemetry; REST polling at 3s adequate for diagnostic log)
- Candle cache implementation (design doc only if time allows in S6)
- Process split / architecture separation
- Changes to strategy logic or entry/exit conditions
- News source upgrades
- Modifications to Sprint 24 deliverables (Quality Engine, Dynamic Sizer)

## Session Breakdown

| Session | Scope | Creates | Modifies | Integrates | Score | Parallel |
|---------|-------|---------|----------|------------|-------|----------|
| S1 | Telemetry infrastructure + REST endpoint | `strategies/telemetry.py` | `strategies/base_strategy.py`, `api/routes/strategies.py` | Self-contained | 13 | No |
| S2 | ORB family instrumentation | — | `strategies/orb_base.py`, `strategies/orb_breakout.py`, `strategies/orb_scalp.py` | S1 telemetry | 12 | No (depends S1) |
| S3 | VWAP + AfMo instrumentation | — | `strategies/vwap_reclaim.py`, `strategies/afternoon_momentum.py` | S1 telemetry | 10 | Yes (parallel S2) |
| S3.5 | Evaluation event persistence | `strategies/telemetry_store.py` | `strategies/telemetry.py`, `api/routes/strategies.py` | S1 buffer persistence hook | 13 | No (depends S1-S3) |
| S4 | Frontend Decision Stream component | `ui/.../StrategyDecisionStream.tsx`, `ui/.../useStrategyDecisions.ts` | `ui/.../orchestrator/index.ts` | Self-contained | 13 | No (depends S3.5) |
| S5 | Frontend Orchestrator integration | — | `ui/pages/OrchestratorPage.tsx`, `ui/.../StrategyOperationsCard.tsx` | S4 component | 8 | No (depends S4) |
| S5f | Visual review fixes (contingency) | — | TBD | S5 | ~5 | No |
| S6 | Operational fixes | — | `ai/summary.py`, `intelligence/sources/finnhub.py` | N/A | 10 | Yes (independent) |

Dependency chain: S1 → S2 → S3.5 → S4 → S5 → S5f
                  S1 → S3 ↗ (S3 parallel with S2)
                  S6 independent (parallel with any)

## Test Expectations

- Backend: ~56 new pytest tests
- Frontend: ~12 new Vitest tests
- Post-sprint targets: ~2,765 pytest + ~515 Vitest

## Config Changes

None. Ring buffer size (1,000) is a constant in `telemetry.py`. Retention
period (7 days) is a constant in `telemetry_store.py`. No new YAML fields.

## Regression Risks

- `BaseStrategy.__init__()` change could break strategy construction → verify
  all strategy construction tests pass
- `strategies.py` route addition could break existing endpoints → verify
  existing strategy listing tests pass
- Strategy `on_candle()` instrumentation must never throw → all
  `record_evaluation()` calls try/except guarded
- `OrchestratorPage.tsx` must preserve 3-column layout → visual review
- ORB same-symbol exclusion (DEC-261) must still work after instrumentation
- Quality pipeline (`_process_signal()` in main.py) must be untouched

## Doc Update Targets

- `docs/project-knowledge.md` (new telemetry layer section, updated test counts)
- `CLAUDE.md` (active sprint, updated state, new deferred items if any)
- `docs/dec-index.md` (new DEC entries)
- `docs/decision-log.md` (new DEC entries with rationale)
- `docs/sprint-history.md` (Sprint 24.5 entry)
- `docs/architecture.md` (telemetry subsystem)
