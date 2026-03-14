# Sprint 24.5: What This Sprint Does NOT Do

## Out of Scope

1. **WebSocket real-time push for evaluation events:** Excluded to avoid flooding
   the EventBus (DEC-029) with high-volume diagnostic telemetry (~200 events/sec
   at peak). REST polling at 3-second intervals is adequate for a diagnostic log.
   Deferred to a future sprint if the polling approach proves insufficient.

2. **Candle cache implementation:** Only a design document is produced (if time
   allows in Session 6). The implementation is a separate sprint — it involves
   persistence format design, replay mechanism, indicator rebuild flow, and
   safety guards against order submission during replay. Deferred to Sprint 25+.

3. **Process split / architecture separation:** No changes to the single-process
   FastAPI architecture. Data engine and API server remain co-located.

4. **Strategy logic changes:** No modifications to entry conditions, exit rules,
   position sizing formulas, or risk parameters for any strategy. Telemetry
   observes; it does not alter.

5. **News source upgrades:** No FMP Premium upgrade, no Benzinga integration, no
   new data sources.

6. **Modifications to Sprint 24 deliverables:** Quality Engine, Dynamic Sizer,
   quality_history table, QualitySignalEvent — all untouched.

7. **Evaluation event aggregation or analytics:** No dashboard-level aggregations
   (e.g., "rejection rate by strategy over time"), no statistical analysis of
   evaluation patterns. Raw event access only. Analytics deferred to Learning
   Loop V1 (Sprint 28).

8. **Backfill of historical evaluation events:** Persistence only captures events
   from this sprint forward. No retroactive generation of events for past
   trading sessions.

## Edge Cases to Reject

1. **Ring buffer empty (pre-market, no candles received yet):** REST endpoint
   returns empty array `[]`. Frontend shows "Awaiting market data" empty state.
   Do NOT synthesize placeholder events.

2. **Strategy not found in ring buffer lookup:** REST returns 404 with message
   "Strategy {id} not found." Do NOT fall through to SQLite.

3. **SQLite write failure:** Log WARNING and continue. Do NOT retry. Do NOT block
   strategy evaluation. The ring buffer still holds the events for real-time
   queries — persistence failure means only historical review is degraded.

4. **Concurrent ring buffer access during REST read:** Use `.snapshot()` (list
   copy from deque) to avoid iterator invalidation. Do NOT add locks that could
   block the strategy evaluation path.

5. **Evaluation event with missing/None metadata fields:** Store as-is. Do NOT
   validate metadata contents — strategies populate what they have. Metadata is
   a flexible dict, not a schema-enforced structure.

6. **Ring buffer size exhausted during high-volume period:** Normal FIFO eviction.
   Do NOT dynamically resize. Do NOT alert. This is expected behavior at
   1,000 events with 3,500+ symbols active.

7. **Historical query for a date with no events:** Return empty array `[]`.
   Do NOT return 404. An empty trading day is valid.

8. **Frontend receives events faster than user can read:** Auto-scroll to bottom
   with newest events. Do NOT implement virtual scrolling or pagination in this
   sprint — the limit param caps the query size.

## Scope Boundaries

- **Do NOT modify:** `argus/core/events.py` (no new EventBus event types),
  `argus/api/websocket/live.py` (no WS bridge changes), `argus/main.py`
  (no changes to `_process_signal()` or startup sequence — persistence
  initialization goes in `server.py` lifespan only),
  `argus/core/orchestrator.py` (no changes to route_candle),
  `argus/execution/order_manager.py`, `argus/core/risk_manager.py`

- **Do NOT optimize:** Ring buffer query performance beyond O(n) scan. 1,000
  events is small enough that linear scan with filtering is adequate.
  SQLite query performance beyond basic indexing. No full-text search,
  no FTS5, no query caching.

- **Do NOT refactor:** Strategy inheritance hierarchy. Do NOT introduce a
  TelemetryMixin or extract telemetry into a decorator pattern. Keep it
  simple: a buffer attribute on BaseStrategy and explicit `record_evaluation()`
  calls at each decision point.

- **Do NOT add:** Configuration for ring buffer size or retention period (keep
  as code constants). Do NOT add evaluation event filtering by event_type to
  the REST API (symbol and date filters are sufficient for now). Do NOT add
  a dedicated evaluation events page in the frontend (integrate into existing
  Orchestrator page only).

## Interaction Boundaries

- This sprint does NOT change the behavior of: SignalEvent generation,
  QualitySignalEvent publishing, Risk Manager evaluation, Order Manager
  execution, EventBus subscriptions, WebSocket bridge message types,
  existing REST API endpoints, existing frontend pages.

- This sprint does NOT affect: Trade execution pipeline, position management,
  P&L calculation, backtesting infrastructure, AI Copilot behavior (except
  the clock fix), Universe Manager, Catalyst Pipeline operation.

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| WebSocket push for evaluation events | Unscheduled | DEF-063 (new) |
| Evaluation event aggregation/analytics | Sprint 28 (Learning Loop V1) | DEF-064 (new) |
| Candle cache implementation | Sprint 25+ | DEF-065 (new) |
| Ring buffer size configurability | Unscheduled | — (trivial, no DEF needed) |
| Virtual scrolling for Decision Stream | Unscheduled | — (UI polish, no DEF needed) |
