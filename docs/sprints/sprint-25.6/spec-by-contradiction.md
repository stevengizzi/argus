# Sprint 25.6: What This Sprint Does NOT Do

## Out of Scope
1. **Trade performance tuning:** No changes to T1/T2 distances, concentration limits, risk parameters, or strategy thresholds. One day of data is insufficient to calibrate. Deferred to Learning Loop (Sprint 29).
2. **Observatory frontend visualization fixes:** The 3D funnel, radar, matrix, and timeline views need data flowing before fixes are meaningful. DEF-065 fix enables data capture; Observatory UI fixes deferred to future sprint.
3. **New strategy development or parameter changes:** No modifications to strategy evaluation logic, entry conditions, or pattern strength calculations.
4. **Telemetry event schema changes:** The `evaluation_events` table schema stays identical — only the database file location changes.
5. **Full regime classification redesign:** This sprint adds periodic re-evaluation using existing `_classify_regime()` logic. It does NOT introduce new regime types, change classification thresholds, or add alternative data sources for classification.
6. **Dashboard card content changes:** Layout reordering only. Card internals (data sources, calculations, display formats) are unchanged.

## Edge Cases to Reject
1. **Evaluation DB file doesn't exist on startup:** `aiosqlite.connect()` creates it automatically — no special handling needed.
2. **Regime reclassification during position exit:** Regime changes mid-trade do not affect open positions (strategies don't re-check regime after entry). This is correct behavior — do not add position-aware regime gating.
3. **Trades page with 10,000+ rows:** Scroll implementation does not need virtualization for now. Current paper trading produces <100 trades/day. Performance optimization deferred.
4. **Dashboard layout on mobile/tablet:** This sprint optimizes desktop layout only. Mobile/tablet remain unchanged.

## Scope Boundaries
- Do NOT modify: `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`, `trade_logger.py`, `catalyst_pipeline.py`, `db/manager.py`, any strategy file (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`), `base_strategy.py`
- Do NOT optimize: Query performance in telemetry store (correctness first)
- Do NOT refactor: `server.py` lifespan structure (only modify initialization wiring for store instance passing)
- Do NOT add: New API endpoints, new WebSocket channels, new config fields

## Interaction Boundaries
- This sprint does NOT change: Trade execution flow, signal generation, quality scoring, risk gating, order management, catalyst pipeline, AI copilot behavior
- This sprint does NOT affect: Data flow (Databento → IndicatorEngine → strategies), broker communication, Universe Manager, authentication

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Observatory frontend visualization fixes | Post-DEF-065 data validation | Unscheduled |
| Trades page virtualized scroll (10K+ rows) | If needed post-live | Unscheduled |
| Dashboard mobile/tablet layout optimization | UI polish sprint | Unscheduled |
| Learning Loop parameter calibration | Sprint 29 | Roadmap |
