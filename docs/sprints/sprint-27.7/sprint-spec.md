# Sprint 27.7: Counterfactual Engine

## Goal

Build a shadow position tracking system that records the theoretical outcome of every rejected signal, computes filter accuracy metrics for the Learning Loop (Sprint 28), and supports shadow-mode strategies whose signals are tracked counterfactually instead of executed. This transforms the ~90% of evaluated signals that ARGUS currently discards into actionable learning data.

## Scope

### Deliverables

1. **Shared TheoreticalFillModel** — Extract bar-level fill priority logic (stop > target > time_stop > EOD) from BacktestEngine into a reusable module. BacktestEngine refactored to call it. CounterfactualTracker calls the same code. Single source of truth for fill evaluation.

2. **CounterfactualPosition model** — Frozen dataclass capturing the full lifecycle of a theoretical trade: entry parameters (entry, stop, T1 target, time stop), rejection metadata (stage, reason, quality grade/score, regime vector, strategy, conditions passed/failed), monitoring state, and exit outcome (exit price, exit reason, theoretical P&L, R-multiple, MAE, MFE, duration).

3. **CounterfactualTracker** — Core engine that:
   - Subscribes to `SignalRejectedEvent` on the event bus to open counterfactual positions.
   - On position open, queries IntradayCandleStore for historical bars since entry time and processes them through the shared fill model (catches already-triggered exits).
   - Subscribes to `CandleEvent` on the event bus for forward monitoring of open positions.
   - Processes each candle through the shared TheoreticalFillModel for all open positions on that symbol.
   - Closes all remaining positions at EOD (4:00 PM ET) via a scheduled asyncio task.
   - Expires positions that receive no candle data within a configurable timeout (default 300s).
   - Exposes a generic `track(signal, rejection_reason, rejection_stage, metadata)` interface.

4. **CounterfactualStore** — SQLite persistence in `data/counterfactual.db` (separate DB per DEC-345 pattern). Write on position open, update on position close. Query by date range, strategy, rejection stage, quality grade. Configurable retention policy (default 90 days) with periodic cleanup.

5. **SignalRejectedEvent** — New event type on the event bus carrying the original SignalEvent, rejection reason, rejection stage (enum: `QUALITY_FILTER`, `POSITION_SIZER`, `RISK_MANAGER`), and supplementary metadata (quality score/grade if available, regime vector snapshot).

6. **Rejection interception** — Publish `SignalRejectedEvent` from three points in `_process_signal()`:
   - Quality grade below minimum threshold (after `_grade_meets_minimum()` returns False).
   - Position sizer returns 0 shares.
   - Risk Manager returns `OrderRejectedEvent` (after `evaluate_signal()`).

7. **CounterfactualConfig** — Pydantic model with `enabled`, `retention_days`, `no_data_timeout_seconds`, `eod_close_time`. YAML file at `config/counterfactual.yaml`. Config-gated on SystemConfig (pattern: DEC-300).

8. **FilterAccuracy computation** — Aggregate accuracy metrics answering: "What percentage of signals rejected by [stage/reason/grade/regime/strategy] would have lost money?" Breakdowns by rejection stage, rejection reason, quality grade at rejection, regime vector at rejection, and strategy. Accuracy = fraction of rejected signals whose counterfactual outcome was a loss (stop hit or negative mark-to-market at EOD).

9. **REST endpoint** — `GET /api/v1/counterfactual/accuracy` returning filter accuracy metrics. Query parameters for date range, strategy filter, minimum sample count. JWT-protected.

10. **Shadow strategy mode** — `StrategyMode` enum (`LIVE`, `SHADOW`), per-strategy `mode` config field (default `LIVE`). Routing check in `_process_signal()`: shadow-mode signals bypass quality pipeline and risk manager, instead publishing a `SignalRejectedEvent` with `rejection_stage=SHADOW` directly to the counterfactual tracker. The strategy itself is unaware of its mode.

### Acceptance Criteria

1. **Shared TheoreticalFillModel:**
   - Given a bar (high, low, close) and position parameters (stop, target, time_stop_expired), returns the correct ExitResult (exit_price, exit_reason) or None.
   - Fill priority: stop > target > time_stop > EOD. When both stop and target trigger on the same bar, stop wins.
   - BacktestEngine produces identical results before and after the extraction (regression test with known trade set).

2. **CounterfactualPosition model:**
   - Supports 5 exit reasons: STOPPED_OUT, TARGET_HIT, TIME_STOPPED, EOD_CLOSED, EXPIRED (no data).
   - Tracks MAE (max adverse excursion) and MFE (max favorable excursion) updated on each bar.
   - Computes theoretical P&L and R-multiple on close.
   - Uses T1 only from `signal.target_prices` tuple.

3. **CounterfactualTracker:**
   - Opens a position when `SignalRejectedEvent` is received (via event bus subscription).
   - On position open, processes historical bars from IntradayCandleStore if available — a position whose stop was already breached is immediately closed.
   - Correctly closes positions via forward candle monitoring using shared fill model.
   - EOD task closes all remaining positions at configurable time (default 16:00 ET).
   - No-data timeout expires positions that receive zero candles within threshold.
   - Multiple counterfactual positions for the same symbol are tracked independently.
   - Config gating: `enabled: false` → tracker is not created, no subscriptions, zero overhead.

4. **CounterfactualStore:**
   - Persists positions on open and updates on close.
   - Queries by date range, strategy_id, rejection_stage, quality_grade return correct results.
   - Retention enforcement deletes records older than `retention_days`.
   - Separate DB file at `data/counterfactual.db`.

5. **SignalRejectedEvent + rejection interception:**
   - Event published when quality grade filter rejects (includes quality_score, quality_grade).
   - Event published when sizer returns 0 shares (includes quality_score, quality_grade).
   - Event published when Risk Manager rejects (includes rejection reason from RiskManager).
   - All three events carry the original SignalEvent with entry/stop/target prices.
   - No event published when counterfactual is disabled.
   - Publishing does not measurably affect `_process_signal()` latency (event bus is fire-and-forget).

6. **FilterAccuracy:**
   - Given known set of counterfactual outcomes, computes correct accuracy percentage per breakdown.
   - Minimum sample count threshold (default 10) — breakdowns with fewer samples return `None` / insufficient data.
   - Handles zero-division (no rejections in a category).

7. **REST endpoint:**
   - Returns JSON with accuracy breakdowns by stage, reason, grade, regime, strategy.
   - Respects date range and strategy query parameters.
   - Returns 200 with empty results when no counterfactual data exists.
   - JWT-protected (401 for unauthenticated).

8. **Shadow strategy mode:**
   - Strategy with `mode: shadow` in config generates signals normally but signals are routed to counterfactual tracker.
   - Strategy with `mode: live` (default) behaves exactly as before (no code path change).
   - Shadow signals appear in counterfactual data with `rejection_stage=SHADOW`.
   - Shadow mode does not affect strategy's internal state machine or evaluation logic.

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| `_process_signal()` latency with counterfactual enabled | < 1ms added overhead | Event bus publish is fire-and-forget; verify no awaits added to critical path |
| CounterfactualStore write latency | < 5ms p95 | SQLite write benchmark in test |
| FilterAccuracy computation (1000 records) | < 100ms | Unit test with synthetic data |
| Memory per open counterfactual position | < 2KB | Estimate from dataclass fields |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Type | Default |
|-----------|---------------|------------|------|---------|
| `counterfactual.enabled` | `CounterfactualConfig` | `enabled` | `bool` | `true` |
| `counterfactual.retention_days` | `CounterfactualConfig` | `retention_days` | `int` | `90` |
| `counterfactual.no_data_timeout_seconds` | `CounterfactualConfig` | `no_data_timeout_seconds` | `int` | `300` |
| `counterfactual.eod_close_time` | `CounterfactualConfig` | `eod_close_time` | `str` | `"16:00"` |
| Per-strategy `mode` | Strategy config model | `mode` | `str` (StrategyMode enum) | `"live"` |

## Dependencies

- Sprint 27.6 (Regime Intelligence) — `RegimeVector` for tagging counterfactual positions ✅
- Sprint 27.65 (Market Session Safety) — `IntradayCandleStore` for historical bar backfill ✅
- Sprint 27.5 (Evaluation Framework) — `MultiObjectiveResult` not directly consumed, but filter accuracy feeds it in Sprint 28 ✅
- Sprint 24.5 (Strategy Observability) — `EvaluationEvent` telemetry infrastructure (pattern reference) ✅
- Existing Databento candle stream — counterfactual symbols are already in viable universe, no new subscriptions needed

## Relevant Decisions

- DEC-025: Event Bus FIFO — SignalRejectedEvent follows same ordering guarantees
- DEC-029: Event Bus sole streaming mechanism — counterfactual candle monitoring via event bus subscription
- DEC-300: Config-gating pattern — counterfactual.enabled follows established pattern
- DEC-345: Separate SQLite DBs for write-intensive subsystems — counterfactual.db follows evaluation.db/catalyst.db pattern
- DEC-342: Strategy evaluation telemetry — pattern reference for fire-and-forget event recording
- DEC-357/358: Amendment adoption — Sprint 27.7 scope defined in Intelligence Architecture amendment
- DEC-368: IntradayCandleStore — enables backfill at position open (not available when amendment was written)

## Relevant Risks

- RSK-022: IBKR Gateway nightly reset — counterfactual positions are in-memory during market hours; no impact from gateway reset (positions close at EOD before reset)
- New risk: Fill priority drift between BacktestEngine and CounterfactualTracker. Mitigated by shared TheoreticalFillModel extraction.

## Session Count Estimate

5 sessions estimated. Sessions 1–2 build foundational library code (model, tracker, store, config). Session 3 is the integration session wiring everything into the running system. Session 4 adds analytics and API exposure. Session 5 adds shadow strategy mode. Strict dependency chain: S1→S2→S3→S4→S5. No frontend sessions (no visual review contingency needed). Estimated ~2.5–3 days.
