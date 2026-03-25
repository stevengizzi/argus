# Sprint 27.7 Design Summary

**Sprint Goal:** Build the Counterfactual Engine — a shadow position tracking system that records theoretical outcomes of every rejected signal, computes filter accuracy metrics for the Learning Loop (Sprint 28), and supports shadow-mode strategies whose signals are tracked counterfactually instead of executed.

**Execution Mode:** Human-in-the-loop

**DEC Range:** 379–385 (7 available)

**Session Breakdown:**

- Session 1: Core model + tracker logic + shared fill model extraction
  - Creates: `argus/intelligence/counterfactual.py`, `argus/core/fill_model.py`
  - Modifies: `argus/backtest/engine.py`
  - Integrates: N/A (foundational)
- Session 2: CounterfactualStore + config layer
  - Creates: `argus/intelligence/counterfactual_store.py`, `config/counterfactual.yaml`
  - Modifies: `argus/intelligence/config.py`, `argus/core/config.py`
  - Integrates: S1 CounterfactualPosition
- Session 3a: SignalRejectedEvent + rejection publishing
  - Creates: none
  - Modifies: `argus/core/events.py`, `argus/main.py`
  - Integrates: N/A (event publishing, consumers in S3b)
- Session 3b: Startup wiring + event subscriptions + EOD task
  - Creates: none
  - Modifies: `argus/intelligence/startup.py`, `argus/main.py`, `config/system.yaml`, `config/system_live.yaml`
  - Integrates: S1 tracker + S2 store + S2 config + S3a events
- Session 4: FilterAccuracy + API endpoint + integration tests
  - Creates: `argus/intelligence/filter_accuracy.py`
  - Modifies: `argus/api/routes.py`
  - Integrates: S1+S2+S3a+S3b (full lifecycle)
- Session 5: Shadow strategy mode
  - Creates: none
  - Modifies: `argus/strategies/base_strategy.py`, `argus/main.py`, strategy YAML configs
  - Integrates: S1+S3a+S3b tracker (shadow routing)

**Key Decisions:**
- Event-driven rejection interception via new SignalRejectedEvent on event bus (decoupled, extensible)
- Shared TheoreticalFillModel extracted from BacktestEngine into `argus/core/fill_model.py` (single source of truth for fill priority)
- IntradayCandleStore backfill at position open (catches already-triggered exits)
- Separate SQLite DB: `data/counterfactual.db` (DEC-345 pattern)
- T1-only for multi-target signals
- Generic tracker interface: `tracker.track(signal, rejection_reason, rejection_stage, metadata)`
- Shadow mode is minimal: config-driven routing only, no shadow-specific UI or comparison tooling
- Strategy-level near-miss tracking deferred (requires per-strategy changes to all 7 strategies)

**Scope Boundaries:**
- IN: CounterfactualPosition, CounterfactualTracker, CounterfactualStore, SignalRejectedEvent, 3-point rejection interception, shared fill model, candle monitoring with backfill, EOD cleanup, FilterAccuracy, REST endpoint, config gating, retention policy, shadow strategy mode
- OUT: Automated filter adjustment (Sprint 28), near-miss events (future), counterfactual UI (Sprint 31), shadow comparison tooling (Sprint 32.5), short-side tracking, WebSocket streaming, non-viable-universe symbols

**Regression Invariants:**
- BacktestEngine fill behavior unchanged after extraction
- `_process_signal()` unchanged for live-mode + counterfactual disabled
- Event bus FIFO ordering preserved
- All existing strategies default to `mode: live`
- No strategy logic changes (shadow mode is routing)

**File Scope:**
- Create: `counterfactual.py`, `counterfactual_store.py`, `filter_accuracy.py`, `fill_model.py`, `counterfactual.yaml`
- Modify: `engine.py`, `intelligence/config.py`, `core/config.py`, `events.py`, `main.py`, `startup.py`, `routes.py`, `base_strategy.py`, `system.yaml`, `system_live.yaml`, strategy YAMLs
- Do not modify: `risk_manager.py`, `regime.py`, `evaluation.py`, `comparison.py`, `intraday_candle_store.py`, individual strategy Python files, `order_manager.py`, `argus/ui/`

**Config Changes:**

| YAML Path | Pydantic Field | Type | Default |
|-----------|---------------|------|---------|
| `counterfactual.enabled` | `CounterfactualConfig.enabled` | `bool` | `true` |
| `counterfactual.retention_days` | `CounterfactualConfig.retention_days` | `int` | `90` |
| `counterfactual.no_data_timeout_seconds` | `CounterfactualConfig.no_data_timeout_seconds` | `int` | `300` |
| `counterfactual.eod_close_time` | `CounterfactualConfig.eod_close_time` | `str` | `"16:00"` |
| Per-strategy `mode` | Strategy config | `str` | `"live"` |

**Test Strategy:** ~48 new tests across 6 sessions. Full suite run at Session 1 entry and Session 5 close-out. Scoped tests for mid-sprint pre-flights and reviews.

**Runner Compatibility:**
- Mode: Human-in-the-loop
- Parallelizable sessions: none
- Work journal handoff: generated

**Dependencies:** Sprint 27.6 (RegimeVector) ✅, Sprint 27.65 (IntradayCandleStore) ✅, Sprint 27.5 (MultiObjectiveResult) ✅

**Escalation Criteria:** BacktestEngine regression → HALT. Fill priority disagreement → HALT. Event bus ordering violation → HALT. Existing test failure → HALT. `_process_signal()` behavioral change → HALT.

**Doc Updates Needed:** project-knowledge.md, decision-log.md, dec-index.md, sprint-history.md, architecture.md, CLAUDE.md

**Artifacts to Generate:**
1. Sprint Spec ✅
2. Specification by Contradiction ✅
3. Session Breakdown ✅
4. Escalation Criteria ✅
5. Regression Checklist ✅
6. Doc Update Checklist ✅
7. Review Context File ✅
8. Implementation Prompts ×6 ✅
9. Review Prompts ×6 ✅
10. Work Journal Handoff Prompt ✅
