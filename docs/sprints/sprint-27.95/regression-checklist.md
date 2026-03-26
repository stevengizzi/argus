# Sprint 27.95: Regression Checklist

## Critical Invariants

- [ ] Normal position lifecycle unchanged: entry → fill → bracket placement → bracket amendment on slippage → stop/target fill → position close → trade logged
- [ ] Risk Manager gating logic unchanged: all 3 levels (strategy, cross-strategy, account) produce identical results for identical inputs
- [ ] Quality Engine pipeline unchanged: pattern_strength → quality score → grade → position sizing → signal enrichment
- [ ] EOD flatten still works for all real positions (not counterfactual)
- [ ] CounterfactualTracker shadow mode (StrategyMode.SHADOW) still works independently of overflow routing
- [ ] CounterfactualTracker rejected signal tracking (quality filter, position sizer, risk manager stages) still works
- [ ] BacktestEngine unaffected — BrokerSource.SIMULATED bypass confirmed for overflow check
- [ ] Reconciliation warn-only mode still works when `auto_cleanup_unconfirmed=false`
- [ ] `_flatten_pending` guard (DEC-363) still prevents duplicate flatten orders
- [ ] Bracket amendment on fill slippage (DEC-366) still operates correctly (stop resubmitted first, safety flatten if T1 ≤ fill)
- [ ] Position reconciliation periodic task (60s) still runs during market hours
- [ ] Real-time P&L publishing on ticks for open positions still works
- [ ] Signal generation rate unchanged — no strategies modified, no filter logic changed
- [ ] Execution record logging (Sprint 21.6) still fires on entry fills
- [ ] IntradayCandleStore (DEC-368) not affected — parallel subscriber unchanged

## Config Validation

- [ ] New config fields verified against Pydantic model (no silently ignored keys)
- [ ] `reconciliation.auto_cleanup_unconfirmed` recognized by ReconciliationConfig
- [ ] `reconciliation.consecutive_miss_threshold` recognized by ReconciliationConfig
- [ ] `overflow.enabled` recognized by OverflowConfig
- [ ] `overflow.broker_capacity` recognized by OverflowConfig
- [ ] `startup.flatten_unknown_positions` recognized by StartupConfig
- [ ] Default values produce correct behavior (reconciliation: warn-only; overflow: enabled at 30; startup: flatten enabled)

## Test Suite Health

- [ ] Full test suite passes at sprint entry (baseline: ~3,610 pytest + 645 Vitest, 0 failures)
- [ ] Full test suite passes at each session close-out
- [ ] Full test suite passes at final review
- [ ] No test hangs introduced
- [ ] `--ignore=tests/test_main.py` still required for xdist (DEF-048)
