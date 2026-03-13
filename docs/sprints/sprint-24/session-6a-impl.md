# Sprint 24, Session 6a: Pipeline Wiring + Unit Tests

## Pre-Flight Checks
1. Read: `argus/main.py` (`_on_candle_for_strategies()`), `argus/intelligence/quality_engine.py`, `argus/intelligence/position_sizer.py`, `argus/core/events.py`, `argus/core/risk_manager.py` (`evaluate_signal()`), `argus/intelligence/storage.py` (`get_catalysts_by_symbol()`)
2. Scoped test: `python -m pytest tests/test_main.py tests/core/test_risk_manager.py -x -q`
3. Branch: `sprint-24`

## Objective
Wire Quality Engine + Dynamic Sizer into `_on_candle_for_strategies()`. Add backtest bypass and config bypass. Add share_count=0 defensive guard in Risk Manager. Add `record_quality_history()` to quality engine. Unit test each branch.

## Requirements

### 1. In `argus/main.py`, modify `_on_candle_for_strategies()`:

After `signal = await strategy.on_candle(event)` and before `self._risk_manager.evaluate_signal()`, insert the quality pipeline with bypass logic. See the signal flow pseudocode in the session breakdown.

The bypass condition: `if self._broker_source == BrokerSource.SIMULATED or not self._config.system.quality_engine.enabled`

Legacy sizing in bypass: `shares = int(strategy.allocated_capital * strategy.config.risk_limits.max_loss_per_trade_pct / abs(signal.entry_price - signal.stop_price))`

Store references to quality engine, position sizer, and catalyst storage on ArgusSystem (set during initialization — these may be None if not yet initialized; check before use).

### 2. In `argus/core/risk_manager.py`, add check 0:

At the very top of `evaluate_signal()`, before the circuit breaker check:
```python
# Check 0: Defensive guard against zero share count (Sprint 24)
if signal.share_count <= 0:
    logger.warning("Signal rejected: share_count=%d (zero or negative)", signal.share_count)
    return OrderRejectedEvent(signal=signal, reason="Invalid share count: zero or negative")
```

### 3. In `argus/intelligence/quality_engine.py`, add `record_quality_history()`:

```python
async def record_quality_history(self, signal: SignalEvent, quality: SetupQuality,
                                  shares: int = 0) -> None:
    """Persist quality scoring result to quality_history table."""
```
Uses aiosqlite via db_manager reference. Writes all columns from schema. Uses ULID for id. Uses ET timestamp per DEC-276.

Add `db_manager` parameter to `__init__` (optional, None if not wiring DB).

### Post-Wiring Verification
Restore `test_full_pipeline_scanner_to_signal` in tests/test_integration_sprint3.py:
change `assert signal.share_count == 0` back to `assert signal.share_count > 0`.
This test must pass — it confirms the Dynamic Sizer is populating share_count
through the full pipeline. If it fails, the wiring is incomplete.

## Constraints
- Do NOT modify: `argus/core/orchestrator.py`, `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`, `argus/backtest/*`
- Risk Manager: ONLY add check 0. No other modifications to evaluate_signal().
- main.py: Do NOT change the existing Universe Manager routing or legacy watchlist path — only add quality pipeline inside the existing signal processing block.

## Test Targets
- `test_quality_pipeline_scores_and_sizes_signal`: Signal with varied pattern_strength → correct quality score and non-zero shares
- `test_quality_pipeline_filters_c_grade`: Low pattern_strength → C grade → signal skipped, quality_history recorded
- `test_quality_pipeline_sizer_zero_shares_skipped`: Sizer returns 0 → signal skipped
- `test_backtest_bypass_uses_legacy_sizing`: BrokerSource.SIMULATED → no quality pipeline, strategy-calculated shares
- `test_config_disabled_bypass`: enabled=false → legacy sizing
- `test_risk_manager_rejects_zero_shares`: SignalEvent(share_count=0) → OrderRejectedEvent
- `test_risk_manager_rejects_negative_shares`: share_count=-1 → rejected
- `test_risk_manager_existing_checks_unchanged`: Positive share_count → proceeds to check 1+
- `test_quality_history_recorded_for_passed_signal`: quality_history row with shares > 0
- `test_quality_history_recorded_for_filtered_signal`: quality_history row with shares = 0
- Minimum: 10
- Test command: `python -m pytest tests/test_main.py tests/core/test_risk_manager.py tests/intelligence/test_quality_engine.py -x -q`

## Definition of Done
- [ ] Quality pipeline wired in main.py
- [ ] Backtest bypass works (BrokerSource.SIMULATED)
- [ ] Config bypass works (enabled=false)
- [ ] RM check 0 rejects share_count ≤ 0
- [ ] quality_history records for all scored signals
- [ ] QualitySignalEvent published for scored signals
- [ ] All existing tests pass
- [ ] 10+ new tests

## Close-Out
Write report to `docs/sprints/sprint-24/session-6a-closeout.md`.

---
