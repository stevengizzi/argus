# Sprint 28: What This Sprint Does NOT Do

> **Amended:** March 28, 2026 — incorporates adversarial review amendments.

## Out of Scope

1. **Automated weight/threshold application without human approval** → Sprint 40
2. **Automated strategy throttle/boost** → Sprint 40. V1 shows observational health bands only.
3. **Statistical lookup tables** → Sprint 40 or V3 (data density insufficient)
4. **ML-based models** → post-revenue backlog (V3)
5. **Strategy parameter recommendations** → Sprint 32+ (requires Parameterized Templates)
6. **Historical match real implementation** → separate DEF item
7. **Ensemble-level analysis** → Sprint 40 (requires ExperimentRegistry)
8. **Scheduled analysis during market hours** → post-session only
9. **ExperimentRegistry writes** → Sprint 32.5 (schema forward-compatible only)
10. **New Command Center page** → UI lives on Performance tab + Dashboard card
11. **In-memory config reload (Amendment 1)** → changes apply at startup only

## Edge Cases to Reject

1. **Zero trades AND zero counterfactual:** Report with all INSUFFICIENT_DATA. Dashboard shows "Collecting data." No error.
2. **Analysis triggered while running:** API 409. Auto trigger skips with WARNING. CLI exits 1. No queuing.
3. **Proposal exceeds max_change_per_cycle:** Status REJECTED_GUARD. API 400 with explanation.
4. **Weights wouldn't sum to 1.0:** Proportional redistribution. If any weight < 0.01, reject.
5. **Pydantic validation failure on write:** Write aborted. YAML preserved. Status REJECTED_VALIDATION. API 400.
6. **Double revert:** API 400 "Already reverted."
7. **Single regime observed:** Overall runs. Per-regime shows single entry with note. No error.
8. **Zero trades in correlation window:** Strategy excluded. Flagged in report.
9. **Shutdown during auto trigger:** asyncio timeout → cancel analysis. Shutdown proceeds.
10. **Config approval at any time (Amendment 1):** Recorded as APPROVED. YAML NOT modified until next startup via apply_pending().
11. **Multiple proposals exceeding cumulative drift (Amendment 2):** apply_pending() applies in order until drift exceeded, stops. Remaining stay APPROVED for next cycle.
12. **YAML parse failure on startup (Amendment 1):** CRITICAL log. Refuse to start. Backup at .bak for manual recovery. NO silent fallback.
13. **Approve SUPERSEDED proposal (Amendment 6):** API 400 "Proposal superseded by report {id}."
14. **Zero-variance P&L outcomes (Amendment 15):** All dimension correlations return INSUFFICIENT_DATA.
15. **Zero-trade session auto trigger (Amendment 10):** Skip analysis if 0 trades AND 0 counterfactual. Run if counterfactual-only data exists.

## Scope Boundaries

- **Do NOT modify:** Any strategy files, core/risk_manager.py, core/orchestrator.py, execution/order_manager.py, intelligence/counterfactual.py, intelligence/counterfactual_store.py, intelligence/filter_accuracy.py, analytics/evaluation.py, analytics/comparison.py, config/system_live.yaml, config/orchestrator.yaml, config/risk_limits.yaml, config/counterfactual.yaml, any existing test files
- **Do NOT optimize:** OutcomeCollector query performance beyond "< 5 seconds"
- **Do NOT refactor:** Quality Engine scoring logic
- **Do NOT add:** WebSocket streaming for Learning Loop, real-time push notifications, AI Copilot integration, in-memory config reload
- **Add SessionEndEvent to core/events.py (Amendment 13).** Do NOT wire auto trigger as direct callback in main.py's flatten logic.

## Interaction Boundaries

- Does NOT change: QE scoring, counterfactual tracking, risk management, orchestrator classification, order execution, strategies, Event Bus events (except adding SessionEndEvent), existing API endpoints
- Does NOT affect: Live signal pipeline during market hours

## Deferred to Future Sprints

| Item | Target Sprint | Rationale |
|------|--------------|-----------|
| Automated weight retraining | Sprint 40 | V1 advisory-only |
| Automated throttle/boost | Sprint 40 | Requires ensemble + kill switch |
| Statistical lookup tables | Sprint 40/V3 | Data density |
| ML calibration | V3 (post-revenue) | Needs training data from V1/V2 |
| Strategy parameters | Sprint 32+ | Requires Parameterized Templates |
| Historical match impl | DEF item | Requires historical outcome DB |
| ExperimentRegistry migration | Sprint 32.5 | Forward-compat schema enables it |
| WebSocket push | Unscheduled | REST sufficient for post-session cadence |
| DB consolidation assessment | Post-Sprint 32.5 | DEF item from adversarial review (A16) |
