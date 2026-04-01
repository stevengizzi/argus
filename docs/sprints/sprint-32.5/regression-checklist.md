# Sprint 32.5: Regression Checklist

## Critical Invariants

### Fingerprint Backward Compatibility (DEF-132)
- [ ] `compute_parameter_fingerprint()` with `exit_overrides=None` produces identical hash to pre-expansion version (golden hash test with known input → known output)
- [ ] `compute_parameter_fingerprint()` with `exit_overrides={}` produces identical hash to `exit_overrides=None`
- [ ] Two variants differing only in exit_overrides produce different fingerprints
- [ ] Fingerprint is deterministic: same inputs always produce same hash regardless of dict ordering

### Config Backward Compatibility (DEF-132)
- [ ] `config/experiments.yaml` without `exit_overrides` fields loads without error
- [ ] `config/experiments.yaml` without `exit_sweep_params` field loads without error
- [ ] `ExperimentConfig(extra="forbid")` still rejects truly unrecognized keys
- [ ] New config fields verified against Pydantic model (no silently ignored keys)
- [ ] Existing variant definitions in experiments.db load without migration errors

### BacktestEngine Existing Patterns (DEF-134)
- [ ] bull_flag backtest produces identical results before and after changes
- [ ] flat_top_breakout backtest produces identical results before and after changes
- [ ] `scripts/run_experiment.py --pattern bull_flag` still works
- [ ] `scripts/run_experiment.py --pattern flat_top_breakout` still works
- [ ] BacktestEngine `risk_overrides` behavior unchanged

### Trade Log Functionality (DEF-131)
- [ ] Existing Trade Log page displays trades correctly
- [ ] Trade filtering works as before
- [ ] Trade detail panel opens and displays correctly
- [ ] Trade Log loads without error when no shadow trades exist
- [ ] Export functionality (if any) unaffected

### Navigation and Routing (DEF-131)
- [ ] All 8 existing pages accessible
- [ ] Keyboard shortcuts for existing 8 pages unchanged
- [ ] 9th page (Experiments) accessible via nav and shortcut
- [ ] Page transitions work correctly
- [ ] Deep linking to existing pages unbroken

### Config Gating (Sprint 32 invariant)
- [ ] `experiments.enabled: false` → experiment API endpoints return 503
- [ ] `experiments.enabled: false` → variant spawner and promotion evaluator skip
- [ ] `experiments.enabled: false` → Experiments page shows disabled state
- [ ] `experiments.enabled: false` → Shadow Trades tab still shows counterfactual data (counterfactual != experiments)

### REST API Compatibility
- [ ] `GET /api/v1/experiments` (Sprint 32) response unchanged
- [ ] `GET /api/v1/experiments/{id}` (Sprint 32) response unchanged
- [ ] `GET /api/v1/experiments/baseline/{pattern}` (Sprint 32) response unchanged
- [ ] `POST /api/v1/experiments/run` (Sprint 32) behavior unchanged
- [ ] `GET /api/v1/counterfactual/accuracy` (Sprint 27.7) response unchanged
- [ ] All endpoints return 401 for unauthenticated requests

### Counterfactual Pipeline (Sprint 27.7 invariant)
- [ ] CounterfactualTracker subscription to SignalRejectedEvent unchanged
- [ ] Shadow position tracking (open/monitor/close) logic unchanged
- [ ] CounterfactualStore write path unchanged
- [ ] Fire-and-forget write behavior preserved
- [ ] 90-day retention enforcement unchanged

### Shadow Strategy Mode (Sprint 27.7 invariant)
- [ ] LIVE mode strategies execute normally
- [ ] SHADOW mode strategies bypass quality pipeline and risk manager
- [ ] Mode config field behavior unchanged

## Test Suite Health
- [ ] All pre-existing pytest pass (target: 4,405 baseline, no regressions)
- [ ] All pre-existing Vitest pass (700 baseline, 1 pre-existing failure in GoalTracker.test.tsx)
- [ ] New tests added per session estimates (~36 pytest, ~8 Vitest)
- [ ] Full suite run at sprint entry and final close-out (DEC-328)
