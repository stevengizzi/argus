# Sprint 27.7: Regression Checklist

Check each item after every session. Items marked with a session number are only relevant after that session.

## Critical Path (Must Pass)

- [ ] All existing pytest tests pass (`pytest --ignore=tests/test_main.py` — expected count ~3,412 ± tolerance)
- [ ] All existing Vitest tests pass (expected count ~633)
- [ ] **(S1)** BacktestEngine produces identical trade results after fill model extraction — run a known backtest (e.g., Bull Flag on 1 month of data) and compare P&L, trade count, and individual fill prices before vs after
- [ ] **(S1)** `evaluate_bar_exit()` matches original BacktestEngine fill priority for all edge cases: stop-only bar, target-only bar, both-trigger bar (stop wins), time-stop bar, time-stop + stop bar (stop wins), EOD bar, no-trigger bar
- [ ] **(S3a)** `_process_signal()` for live-mode strategies with `counterfactual.enabled: false` follows identical code path as pre-sprint (no new awaits, no new function calls, no behavioral change)
- [ ] **(S3a)** `_process_signal()` for live-mode strategies with `counterfactual.enabled: true` produces identical OrderApprovedEvent/OrderRejectedEvent results (counterfactual publishing is purely additive side-effect)
- [ ] **(S3b)** Event bus FIFO ordering preserved — SignalRejectedEvent does not disrupt delivery order of CandleEvent, OrderApprovedEvent, or any other event type
- [ ] **(S5)** All existing strategies default to `mode: live` — no strategy behavior changes without explicit config modification
- [ ] **(S5)** Strategy internal logic (evaluation, signal generation, state machines) is completely unaware of mode — shadow mode is a routing decision in `main.py`, not in strategy code

## Config Integrity

- [ ] **(S2)** New config fields verified against Pydantic model: `counterfactual.enabled` → `CounterfactualConfig.enabled`, `counterfactual.retention_days` → `CounterfactualConfig.retention_days`, `counterfactual.no_data_timeout_seconds` → `CounterfactualConfig.no_data_timeout_seconds`, `counterfactual.eod_close_time` → `CounterfactualConfig.eod_close_time`
- [ ] **(S2)** `CounterfactualConfig` on `SystemConfig` has correct default factory (enabled=true)
- [ ] **(S2)** `config/system.yaml` and `config/system_live.yaml` parse correctly with new section
- [ ] **(S5)** Per-strategy `mode` field defaults to `"live"` — existing strategy configs without the field still work (Pydantic default)

## Data Integrity

- [ ] **(S2)** CounterfactualStore uses `data/counterfactual.db` — NOT `data/argus.db` (DEC-345 pattern)
- [ ] **(S2)** Retention enforcement only deletes counterfactual records, not other data
- [ ] **(S4)** FilterAccuracy handles zero-division gracefully (no rejections in a category → None, not crash)
- [ ] **(S4)** FilterAccuracy minimum sample threshold is respected (< 10 samples → None)

## Do-Not-Modify Enforcement

- [ ] `argus/core/risk_manager.py` — NOT modified in any session
- [ ] `argus/core/regime.py` — NOT modified
- [ ] `argus/analytics/evaluation.py` — NOT modified
- [ ] `argus/analytics/comparison.py` — NOT modified
- [ ] `argus/data/intraday_candle_store.py` — NOT modified (read-only consumer)
- [ ] Individual strategy files (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `red_to_green.py`, `patterns/bull_flag.py`, `patterns/flat_top_breakout.py`) — NOT modified
- [ ] `argus/execution/order_manager.py` — NOT modified
- [ ] `argus/ui/` — No frontend files modified
