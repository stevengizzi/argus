# Sprint 24: What This Sprint Does NOT Do

> **Post-adversarial-review revision.** See `revision-rationale.md` for changes.

## Out of Scope

1. **Learning Loop implementation (Sprint 28)** — Only the quality_history recording table is built. No post-trade analysis, no weight retraining, no statistical lookup tables, no outcome correlation.

2. **ML or Claude API for quality scoring** — All scoring is deterministic arithmetic on passed-in data. No LLM calls in the scoring path.

3. **Changes to strategy entry/exit logic** — Strategies still decide *when* to signal. Quality Engine only scores and sizes *after* signal generation.

4. **Changes to Risk Manager gate logic** — Risk Manager remains a downstream safety net. No modifications to its 7-check sequence. *(Exception: one defensive guard added — see Permitted Modifications below.)*

5. **PreMarketEngine** — Catalyst data comes from background firehose polling. No automated 4:00 AM → 9:25 AM pipeline.

6. **New strategies or pattern types** — Sprint 25 adds Red-to-Green + PatternLibrary ABC.

7. **CatalystClassifier modifications** — Classification logic, categories, and fallback unchanged. Only how raw data *reaches* the classifier changes (firehose vs. per-symbol).

8. **WebSocket streaming for quality events** — REST API only for quality data.

9. **Order flow scoring (DEC-238)** — Post-revenue. `order_flow` parameter reserved/None.

10. **CatalystStorage schema changes** — Existing `catalyst_events` table in `catalyst.db` unchanged. New `quality_history` table is in `argus.db`.

11. **Quality score caching or memoization** — Each signal scored fresh.

12. **quality_history retention or archival** — No TTL cleanup. Sprint 28 defines retention.

13. **Orchestrator allocation or throttling changes** — Equal-weight allocation unchanged. Sprint 28 adds performance-based throttling.

14. **FMP news firehose** — FMP endpoints return 403 on Starter plan. No firehose for FMP.

15. **Outcome recording automation** — `outcome_*` columns in quality_history are NULL. Sprint 28 wires PositionClosedEvent to update them.

16. **On-demand live API fetch at signal time** — Removed from scope per adversarial review Finding 3. Catalyst data comes from local catalyst.db only. No live network calls in the quality scoring path.

## Edge Cases to Reject

1. **Quality Engine called with no CatalystStorage available** — Catalyst Quality dimension scores 50 (neutral). Log warning. Do not crash.

2. **Strategy returns pattern_strength outside [0, 100]** — Clamp to [0, 100]. Log warning. Do not reject signal.

3. **All dimensions return neutral (50)** — Valid composite score of 50 (grade B). Normal sizing applies. Expected state for HM stub.

4. **Concurrent signals from same strategy for same symbol** — Impossible in current architecture. No special handling.

5. **Quality Engine exception during scoring** — Fail-closed: signal does NOT execute. Log at ERROR. Consistent with DEC-277.

6. **Dynamic Sizer produces shares exceeding strategy's old calculation** — Expected for A/A+ grades. Risk Manager's existing gates are the safety net. No artificial cap.

7. **Signal with share_count=0 reaches Risk Manager** — Rejected by new check 0 defensive guard: "Invalid share count: zero or negative." Defense-in-depth.

8. **Backtest/replay mode** — Quality pipeline bypassed entirely. Legacy sizing path used. Backtest behavior unchanged from pre-sprint.

9. **quality_engine.enabled set to false** — Same legacy sizing path as backtest mode. All quality scoring, filtering, recording skipped.

## Scope Boundaries

- **Do NOT modify:** `argus/core/orchestrator.py`, `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`, `argus/ai/*`, `argus/intelligence/classifier.py`, `argus/intelligence/storage.py`, `argus/intelligence/models.py`, `argus/intelligence/sources/fmp_news.py`, `argus/backtest/*`, `argus/intelligence/briefing.py`
- **Permitted modifications (adversarial review carve-outs):**
  - `argus/core/risk_manager.py` — ONE change only: add check 0 in `evaluate_signal()` rejecting signals with `share_count <= 0`. No other modifications.
- **Do NOT optimize:** Quality Engine scoring performance. Database query performance for quality_history.
- **Do NOT refactor:** Existing CatalystPipeline internals beyond adding firehose branch. Existing strategy `on_candle()` flow beyond adding pattern_strength and setting share_count=0.
- **Do NOT add:** Manual quality override, quality-based Copilot tools, quality WebSocket stream, strategy-level quality thresholds, quality alerts/notifications, on-demand live API fetch in scoring path.

## Interaction Boundaries

- This sprint does NOT change the behavior of: Orchestrator allocation, Order Manager lifecycle, Trade Logger persistence, Broker abstraction, Event Bus delivery semantics, existing CatalystClassifier categories, existing CatalystStorage queries, authentication/authorization, health monitoring (except quality engine registration).
- This sprint does NOT affect: Backtesting infrastructure (VectorBT, Replay Harness) — backtest bypass ensures identical pre-sprint behavior. AI Copilot behavior. Existing dashboard/trades/performance page data (only new panels/columns added).
- Risk Manager behavior change is limited to: rejecting share_count=0 signals (new check 0). All 7 existing checks unchanged.

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Learning Loop (outcome analysis, weight retraining) | Sprint 28 | — |
| quality_history outcome column population | Sprint 28 | DEF-049 |
| quality_history retention/archival | Sprint 28 | DEF-050 |
| Order Flow scoring dimension | Post-revenue | DEC-238 |
| PreMarketEngine | Sprint 24+ | DEF-051 |
| Quality-based Copilot context enrichment | Unscheduled | DEF-052 |
| FMP news firehose | FMP Premium upgrade | — |
| WebSocket streaming for quality events | Unscheduled | — |
| Manual quality override mechanism | Not planned | — |
| On-demand live API fetch in quality scoring path | Removed from Sprint 24 scope | — |
| Grade threshold recalibration | Sprint 28 (after HM stub replaced) | — |
| Intra-grade risk interpolation | Unscheduled | — |
