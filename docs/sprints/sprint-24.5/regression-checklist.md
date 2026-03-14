# Sprint 24.5 — Regression Checklist

Check every item before each session close-out. Items are cumulative — later
sessions check all items from earlier sessions plus their own.

## Core Invariants (Check Every Session)

- [ ] All 4 strategies produce correct SignalEvent output (unchanged from baseline)
- [ ] `on_candle()` return values unchanged for all strategies
- [ ] ORB same-symbol exclusion (DEC-261) still works
- [ ] Quality pipeline flow (`_process_signal()` in main.py) untouched
- [ ] Risk Manager check 0 (share_count ≤ 0 rejection, DEC-336) untouched
- [ ] Existing REST API endpoints return same responses (spot-check /api/v1/strategies, /api/v1/health)
- [ ] WebSocket bridge event types unchanged
- [ ] Existing frontend pages render without console errors

## Session-Specific Checks

### After S1 (Telemetry Infrastructure)
- [ ] BaseStrategy subclass construction works (existing strategy tests pass)
- [ ] `record_evaluation()` never raises (test coverage)
- [ ] New REST endpoint is JWT-protected
- [ ] Existing strategies route endpoints unchanged

### After S2 (ORB Instrumentation)
- [ ] OrbBaseStrategy.on_candle() returns same signals for same inputs
- [ ] ORB Breakout _calculate_pattern_strength() returns same scores
- [ ] ORB Scalp _calculate_pattern_strength() returns same scores
- [ ] All `record_evaluation()` calls are try/except guarded

### After S3 (VWAP + AfMo Instrumentation)
- [ ] VwapReclaimStrategy state machine transitions unchanged
- [ ] AfternoonMomentumStrategy 8 entry conditions unchanged
- [ ] VWAP _calculate_pattern_strength() returns same scores
- [ ] AfMo _calculate_pattern_strength() returns same scores
- [ ] All `record_evaluation()` calls are try/except guarded

### After S3.5 (Persistence)
- [ ] evaluation_events table created without affecting existing tables
- [ ] Persistence failure does not impact ring buffer operation
- [ ] REST endpoint still works without persistence (ring buffer path)
- [ ] Historical date query returns correct subset

### After S4 (Frontend Component)
- [ ] No new TypeScript build errors (baseline: 0 TS errors from Sprint 24.1)
- [ ] Component renders without console errors
- [ ] Existing orchestrator components unaffected

### After S5 (Frontend Integration)
- [ ] OrchestratorPage 3-column layout (Section 4) preserved
- [ ] StrategyOperationsGrid still renders all strategy cards
- [ ] Existing navigation and shortcuts (DEC-199) still work
- [ ] No regressions in other pages (spot-check Dashboard, Trades)

### After S6 (Operational Fixes)
- [ ] AI Insight card generates insights (not broken by clock fix)
- [ ] Finnhub source still fetches news for symbols that work on free tier
- [ ] FMP news source still disabled in system_live.yaml
- [ ] No changes to strategy evaluation or execution paths

## Test Suite Verification

- [ ] Full pytest suite passes with `-n auto` (excluding known DEF-048/049 failures)
- [ ] Full Vitest suite passes
- [ ] No new test failures introduced
- [ ] ruff linting passes
