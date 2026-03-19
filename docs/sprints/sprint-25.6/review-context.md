# Sprint 25.6 — Review Context File

> Shared context for all Tier 2 reviews in Sprint 25.6. Individual review prompts reference this file by path.

---

## Sprint Spec

### Goal
Fix all operational bugs discovered during the March 19 live trading session: telemetry store contention (DEF-065/066), regime stagnation, Trades page UX (DEF-067/068/069/073), Orchestrator display (DEF-070/071), and Dashboard layout (DEF-072).

### Deliverables
1. Telemetry store writes to dedicated `data/evaluation.db`
2. Health check loop reuses existing store instance
3. Telemetry write failure warnings rate-limited to 1/minute
4. Periodic regime reclassification (~5 min) during market hours
5. Trades page: scroll replaces pagination
6. Trades page: metrics from full dataset
7. Trades page: filter state persists on re-entry
8. Trades page: sortable columns
9. "Afternoon Momentum" label not truncated
10. Throttled/hatched bars only for actually throttled strategies
11. Dashboard Positions card visible without scrolling

### Acceptance Criteria
See `sprint-spec.md` for full per-deliverable criteria.

---

## Specification by Contradiction

### Do NOT Modify
- `risk_manager.py`, `order_manager.py`, `ibkr_broker.py`, `trade_logger.py`
- `catalyst_pipeline.py`, `db/manager.py`
- Strategy files: `orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `base_strategy.py`

### Do NOT Add
- New API endpoints, WebSocket channels, config fields
- Trade performance tuning or parameter changes
- Observatory frontend visualization fixes

### Do NOT Change
- Trade execution flow, signal generation, quality scoring, risk gating
- Data flow (Databento → IndicatorEngine → strategies)
- Broker communication, Universe Manager, authentication
- `evaluation_events` table schema (only DB file location changes)

---

## Sprint-Level Escalation Criteria

1. DB separation causes data corruption in `argus.db` → halt and escalate
2. Regime reclassification unexpectedly excludes strategies → escalate
3. Frontend changes require unplanned backend API changes → escalate
4. Test count drops by more than 5 → escalate

---

## Sprint-Level Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Trades still logged to `argus.db` | `sqlite3 data/argus.db "SELECT COUNT(*) FROM trades"` |
| 2 | Quality history still in `argus.db` | `sqlite3 data/argus.db "SELECT COUNT(*) FROM quality_history"` |
| 3 | Catalyst events still in `catalyst.db` | `sqlite3 data/catalyst.db "SELECT COUNT(*) FROM catalyst_events"` |
| 4 | Evaluation events write to `evaluation.db` | Non-zero count after candle processing |
| 5 | No "EvaluationEventStore initialized" spam | At most 2 occurrences (startup) |
| 6 | Regime reclassifies during market hours | Log entries present after 9:35 ET |
| 7 | Regime does NOT update outside market hours | No entries before 9:30 or after 16:00 ET |
| 8 | All 4 strategies register and run | Health monitor shows 4/4 healthy |
| 9 | All trades visible on Trades page | Count matches DB query |
| 10 | Summary metrics match full query | Consistent regardless of scroll position |
| 11 | Dashboard renders all cards | No console errors |
| 12 | Positions visible without scrolling | Visual on 1080p |
| 13 | EOD flatten + auto-shutdown works | Log entry present |
| 14 | `npx tsc --noEmit` clean | No TypeScript errors |
| 15 | Full pytest suite passes | `python -m pytest tests/ --ignore=tests/test_main.py -n auto` |
| 16 | Full Vitest suite passes | `cd argus/ui && npx vitest run` |
