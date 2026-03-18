# Sprint 25.5 Design Summary

**Sprint Goal:** Fix the Universe Manager ↔ Strategy watchlist wiring gap that has silently prevented all strategy evaluation since Sprint 23 (March 7). Populate strategy watchlists from UM routing table, convert watchlist to set for O(1) lookups, and add a health warning to detect zero-evaluation states in the future.

**Session Breakdown:**
- Session 1: Watchlist wiring from Universe Manager routing table + list→set performance fix
  - Creates: None
  - Modifies: `argus/main.py`, `argus/strategies/base_strategy.py`
  - Integrates: N/A
- Session 2: Zero-evaluation health warning + end-to-end telemetry verification tests
  - Creates: New e2e telemetry test file (e.g., `tests/test_evaluation_telemetry_e2e.py`)
  - Modifies: `argus/core/health.py`
  - Integrates: Session 1 (e2e test requires watchlist-populated strategies)

**Key Decisions:**
- Populate watchlists from UM routing (via `get_strategy_symbols()`) rather than removing the watchlist check
- Convert `_watchlist` from `list` to `set` internally for O(1) membership checks
- `watchlist` property still returns `list[str]` to preserve API contract
- Health warning fires per-strategy, respecting each strategy's time window
- Health warning distinguishes "UM routed 0 symbols" (legitimate) from "watchlist never populated" (bug)

**Scope Boundaries:**
- IN: Watchlist wiring from UM routing, list→set conversion, backward compat when UM disabled, startup log confirming watchlist per strategy, zero-eval health warning, e2e telemetry test
- OUT: Strategy performance optimization for large symbol counts, UM filter/routing logic changes, Observatory frontend changes, quality/catalyst pipeline changes, new evaluation event types, backfilling lost paper trading data

**Regression Invariants:**
- Scanner-only flow (UM disabled) unchanged
- `watchlist` property returns `list[str]` (not set)
- Strategy `on_candle()` logic unchanged
- Risk Manager, quality pipeline, order flow untouched
- Event Bus FIFO ordering preserved
- All existing tests pass

**File Scope:**
- Modify: `argus/main.py`, `argus/strategies/base_strategy.py`, `argus/core/health.py`
- Do not modify: `argus/data/universe_manager.py`, `argus/strategies/orb_base.py`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/analytics/observatory_service.py`, any config files

**Config Changes:** None.

**Test Strategy:**
- Session 1: ~8 tests, Session 2: ~8 tests
- Estimated delta: +16 tests

**Runner Compatibility:**
- Mode: Human-in-the-loop
- Parallelizable sessions: None
- Runner config: Not generated

**Dependencies:**
- `UniverseManager.get_strategy_symbols(strategy_id)` exists (confirmed)
- `EvaluationEventStore` wired to strategy buffers (confirmed)
- Observatory endpoints returning 200 (confirmed)

**Escalation Criteria:**
- Performance degradation after watchlist fix
- >5 existing tests break from list→set

**Doc Updates Needed:**
- `docs/project-knowledge.md`, `docs/sprint-history.md`, `CLAUDE.md`, `docs/decision-log.md`, `docs/dec-index.md`, `docs/risk-register.md`

**Artifacts to Generate:**
1. Sprint Spec ✅
2. Specification by Contradiction ✅
3. Session Breakdown ✅
4. Escalation Criteria ✅
5. Regression Checklist ✅
6. Doc Update Checklist ✅
7. Review Context File ✅
8. Implementation Prompt ×2 ✅
9. Review Prompt ×2 ✅
10. Work Journal Handoff Prompt ✅
