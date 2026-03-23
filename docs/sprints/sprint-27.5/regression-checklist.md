# Sprint 27.5: Regression Checklist

Run at sprint entry (S1 pre-flight), each session close-out, and final review.

## Test Suite Integrity

- [ ] Full pytest suite passes with `--ignore=tests/test_main.py` (expected: ≥3,071 pass, 0 fail)
- [ ] Full Vitest suite passes (expected: ≥620 pass, 0 fail)
- [ ] No new test hangs or timeouts introduced
- [ ] Test count does not decrease from sprint entry baseline

## BacktestEngine Stability

- [ ] `BacktestEngine.run()` returns identical `BacktestResult` for the same inputs as before this sprint (existing behavior unchanged)
- [ ] Existing BacktestEngine tests in `tests/backtest/test_engine.py` all pass without modification
- [ ] CLI entry point (`python -m argus.backtest.engine`) produces same output format
- [ ] `BacktestEngineConfig` with no `slippage_model_path` behaves identically to pre-sprint config

## Metrics Stability

- [ ] `backtest/metrics.py` — `compute_metrics()` produces identical output (file not modified)
- [ ] `backtest/metrics.py` — `compute_sharpe_ratio()` and `compute_max_drawdown()` untouched
- [ ] `analytics/performance.py` — `compute_metrics()` (shared module) produces identical output (file not modified)

## Walk-Forward Stability

- [ ] `backtest/walk_forward.py` — not modified (verify with `git diff`)
- [ ] `WalkForwardResult` structure unchanged
- [ ] Walk-forward tests pass without modification

## Regime Classifier Stability

- [ ] `core/regime.py` — not modified (verify with `git diff`)
- [ ] `RegimeClassifier.classify()` behavior unchanged for same inputs
- [ ] `MarketRegime` enum values unchanged

## Import Integrity

- [ ] No circular imports among new analytics modules (`evaluation.py`, `comparison.py`, `ensemble_evaluation.py`, `slippage_model.py`)
- [ ] No circular imports between new analytics modules and `backtest/engine.py`
- [ ] `import argus.analytics.evaluation` succeeds independently
- [ ] `import argus.analytics.comparison` succeeds independently
- [ ] `import argus.analytics.ensemble_evaluation` succeeds independently
- [ ] `import argus.analytics.slippage_model` succeeds independently

## Config Backward Compatibility

- [ ] `BacktestEngineConfig` with existing YAML (no `slippage_model_path`) → no validation error, `slippage_model_path` defaults to `None`
- [ ] New config field verified against Pydantic model (no silently ignored keys)

## Protected Files (Do Not Modify)

Verify these files have zero diff after the sprint:
- [ ] `argus/backtest/metrics.py`
- [ ] `argus/backtest/walk_forward.py`
- [ ] `argus/core/regime.py`
- [ ] `argus/analytics/performance.py`
- [ ] `argus/analytics/trade_logger.py`
- [ ] `argus/execution/order_manager.py`
- [ ] `argus/execution/execution_record.py`
- [ ] `argus/core/events.py`
- [ ] All strategy files (`argus/strategies/*`)
- [ ] All frontend files (`argus/ui/*`)
- [ ] All API route files (`argus/api/*`)
