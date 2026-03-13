# Sprint 24, Session 6b: Integration Tests + Error Paths

## Pre-Flight Checks
1. Read: `argus/main.py` (Session 6a wiring), `argus/intelligence/quality_engine.py`, `argus/core/risk_manager.py`
2. Scoped test: `python -m pytest tests/test_main.py tests/intelligence/ -x -q`
3. Branch: `sprint-24`

## Pre-Flight Fix: test_main.py Performance Regression (DEF-051)

`test_main.py` (43 tests) takes 7+ minutes to run, causing review session timeouts.
The S6a review session could not complete test_main.py verification at all. Since
Session 6b is test-only and every remaining session (7 more + reviews) pays this cost,
fix it here.

### Diagnosis
Run: `python -m pytest tests/test_main.py --durations=20 -v 2>&1 | tail -40`

Identify whether the bottleneck is:
- (a) Per-test ArgusSystem initialization (each test spins up full system)
- (b) Phase 10.25 additions (CatalystStorage, QualityEngine, PositionSizer init)
- (c) External service connection attempts (Databento, FMP, IBKR) timing out
- (d) Database initialization overhead per test

### Fix Strategy (pick the minimal one that works)
1. **If external connections:** Add/verify mocks or patches for Databento, FMP, IBKR
   clients in the test fixtures so no real connections are attempted.
2. **If per-test init:** Convert the ArgusSystem fixture to `scope="module"` or
   `scope="class"` where tests don't mutate shared state. Tests that DO mutate
   state keep their own fixture.
3. **If Phase 10.25:** Ensure CatalystStorage, QualityEngine, and PositionSizer
   init is mocked/lightweight in test mode.

### Constraints
- All 43 existing tests must still pass with identical assertions.
- No test logic changes — only fixture/setup optimization.
- Target: full test_main.py suite completes in < 60 seconds.
- Source code changes to test files ONLY (this is an exception to the "test_main.py
  is not modified" convention — the fix is to test infrastructure, not production code).

### Verification
Before and after timing:
```bash
time python -m pytest tests/test_main.py -x -q
```
Report both times in the close-out.

## Objective
Full integration tests running multiple signals through the quality pipeline. Error path coverage. Backtest bypass verification.

## Requirements

Write integration tests covering:

1. **Multi-signal pipeline**: Create ArgusSystem in test mode with quality engine enabled. Feed multiple CandleEvents that trigger signals from different strategies. Verify each signal gets a different quality score based on different pattern_strength + different catalyst data.

2. **Error paths**:
   - Quality engine `score_setup()` raises exception → fail-closed (signal does NOT execute), error logged
   - CatalystStorage unavailable (None) → catalyst dimension = 50, signal still scored
   - RVOL unavailable (None) → volume dimension = 50, signal still scored
   - Regime data unavailable → regime dimension = 50

3. **Bypass verification**:
   - Full test with BrokerSource.SIMULATED: signals go through legacy path, no quality_history rows, no QualitySignalEvents
   - Full test with enabled=false: same behavior

4. **Defensive guard end-to-end**: Construct a scenario where a signal with share_count=0 somehow reaches evaluate_signal() — verify it's rejected.

## Constraints
- This is a TEST-ONLY session. Do NOT modify any source code files.
- Tests should use appropriate mocking for external dependencies (broker, data service, catalyst storage).

## Test Targets
- `test_integration_multiple_strategies_different_scores`: 2+ strategies → different quality grades
- `test_integration_quality_engine_exception_failclosed`: Exception → no order submitted
- `test_integration_catalyst_storage_none_graceful`: No storage → scores still computed
- `test_integration_rvol_none_graceful`: No RVOL → volume dimension neutral
- `test_integration_backtest_bypass_no_quality_history`: SIMULATED → 0 quality_history rows
- `test_integration_backtest_bypass_no_quality_events`: SIMULATED → 0 QualitySignalEvents
- `test_integration_disabled_bypass`: enabled=false → legacy path
- `test_integration_c_grade_never_reaches_rm`: Low-quality signal → RM never called
- `test_integration_enriched_signal_preserves_original_fields`: strategy_id, symbol, etc. unchanged
- `test_integration_quality_signal_event_published`: QualitySignalEvent on event bus for scored signal
- `test_integration_zero_shares_rejected_by_rm`: Defense-in-depth verification
- Minimum: 11
- Test command: `python -m pytest tests/test_main.py tests/intelligence/ -x -q`

## Definition of Done
- [ ] All error paths covered
- [ ] Bypass modes verified
- [ ] No source code modified
- [ ] 11+ new tests passing
- [ ] test_main.py runs in < 60 seconds (was 7+ minutes)

## Close-Out
Write report to `docs/sprints/sprint-24/session-6b-closeout.md`.
