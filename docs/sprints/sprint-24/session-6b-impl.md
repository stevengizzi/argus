# Sprint 24, Session 6b: Integration Tests + Error Paths

## Pre-Flight Checks
1. Read: `argus/main.py` (Session 6a wiring), `argus/intelligence/quality_engine.py`, `argus/core/risk_manager.py`
2. Scoped test: `python -m pytest tests/test_main.py tests/intelligence/ -x -q`
3. Branch: `sprint-24`

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

## Close-Out
Write report to `docs/sprints/sprint-24/session-6b-closeout.md`.
