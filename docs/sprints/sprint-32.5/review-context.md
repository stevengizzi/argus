# Sprint 32.5: Review Context File

> This file is referenced by all Tier 2 session review prompts. It contains
> the Sprint Spec, Specification by Contradiction, Regression Checklist, and
> Escalation Criteria. Read this file ONCE at the start of each review.

---

## Sprint Spec

### Goal
Close three critical gaps in the experiment pipeline (exit parameters as variant dimensions, BacktestEngine support for all 7 PatternModule patterns, and full operational visibility via API + UI) and document the Adaptive Capital Intelligence architectural vision.

### Deliverables

1. **DEF-132: Exit parameters as variant dimensions.** VariantDefinition expanded with `exit_overrides`, fingerprint expanded to namespaced canonical JSON, spawner applies exit overrides, runner grid includes exit dimensions.
2. **DEF-134: BacktestEngine support for all 7 PatternModule patterns.** 5 remaining patterns wired. Reference data supply for gap_and_go and premarket_high_break.
3. **DEF-131: Experiments + counterfactual visibility.** 3 new REST endpoints. Shadow Trades tab on Trade Log. Experiments Dashboard (9th page).
4. **DEF-133: Adaptive Capital Intelligence vision document.**
5. **Doc-sync.**

### Acceptance Criteria

**DEF-132:**
- VariantDefinition accepts exit_overrides: dict[str, Any] | None
- Fingerprint with exit_overrides=None identical to pre-expansion (golden hash)
- Different exit_overrides → different fingerprints
- Spawner applies exit_overrides via deep_merge
- Runner generates grid with exit dimensions when configured
- experiments.yaml loads with and without exit_overrides

**DEF-134:**
- All 7 patterns work via run_experiment.py (non-zero trades)
- bull_flag + flat_top_breakout unchanged (regression)
- gap_and_go receives prior close, premarket_high_break receives PM high
- First day of range for ref-data patterns: warning + skip

**DEF-131:**
- 3 new JWT-protected endpoints (positions, variants, promotions)
- Shadow Trades tab on Trade Log with rejection metadata, P&L, MFE/MAE
- Experiments page with variant table, promotion log, comparison
- Empty state handling on both pages
- experiments.enabled=false degrades gracefully

**DEF-133:**
- Document at docs/architecture/allocation-intelligence-vision.md
- Contains all 9 sections (problem, vision, 6 dimensions, phased roadmap, data requirements, architectural sketch, interface design, hard floors, component relationships)

### Config Changes

| YAML Path | Pydantic Model | Field Name | Type | Default |
|-----------|---------------|------------|------|---------|
| experiments.yaml → variant defs → exit_overrides | VariantDefinition | exit_overrides | dict[str, Any] \| None | None |
| experiments.yaml → exit_sweep_params | ExperimentConfig | exit_sweep_params | list[ExitSweepParam] \| None | None |

---

## Specification by Contradiction

### Out of Scope
1. Standalone strategy retrofit to variant framework (Sprint 33)
2. ABCD O(n³) optimization (DEF-122)
3. New PatternModule patterns
4. Real-time experiment monitoring
5. Parameter heatmap visualization
6. 3D visualizations on Experiments page
7. Live position management from Experiments UI (read-only)
8. Experiment runner trigger from UI (CLI only)
9. Fingerprint migration for existing variants
10. Adaptive Capital Intelligence implementation (vision doc only)
11. Dedicated /summary endpoint (client-side aggregation)

### Do NOT Modify
core/events.py, core/regime.py, execution/order_manager.py, intelligence/counterfactual.py (tracker write/subscription logic), any strategy files under strategies/ (strategy logic), core/exit_math.py, core/config.py (ExitManagementConfig)

### Do NOT Change Behavior Of
Existing 4 experiment REST endpoints, counterfactual accuracy endpoint, shadow strategy mode, PromotionEvaluator logic, CounterfactualTracker tracking, Event Bus subscriptions, existing 8 navigation pages

---

## Regression Checklist

### Fingerprint Backward Compatibility
- [ ] compute_parameter_fingerprint() with exit_overrides=None → identical hash to pre-expansion
- [ ] exit_overrides={} → identical hash to exit_overrides=None
- [ ] Different exit_overrides → different fingerprints
- [ ] Deterministic: same inputs → same hash regardless of dict ordering

### Config Backward Compatibility
- [ ] experiments.yaml without exit_overrides loads without error
- [ ] experiments.yaml without exit_sweep_params loads without error
- [ ] ExperimentConfig extra="forbid" still rejects unknown keys
- [ ] New config fields verified against Pydantic model
- [ ] Existing variant definitions in experiments.db load

### BacktestEngine Existing Patterns
- [ ] bull_flag backtest identical before/after
- [ ] flat_top_breakout backtest identical before/after
- [ ] run_experiment.py --pattern bull_flag still works
- [ ] run_experiment.py --pattern flat_top_breakout still works
- [ ] risk_overrides behavior unchanged

### Trade Log Functionality
- [ ] Existing trades display correctly
- [ ] Filtering works
- [ ] Detail panel works
- [ ] Loads without error when no shadow trades exist

### Navigation and Routing
- [ ] All 8 existing pages accessible
- [ ] Keyboard shortcuts for existing pages unchanged
- [ ] 9th page accessible
- [ ] Page transitions work
- [ ] Deep linking unbroken

### Config Gating
- [ ] experiments.enabled=false → experiment endpoints return 503
- [ ] experiments.enabled=false → spawner/evaluator skip
- [ ] experiments.enabled=false → Experiments page shows disabled state
- [ ] experiments.enabled=false → Shadow Trades tab still shows counterfactual data

### REST API Compatibility
- [ ] All 4 existing experiment endpoints unchanged
- [ ] Counterfactual accuracy endpoint unchanged
- [ ] All endpoints return 401 for unauthenticated requests

### Counterfactual Pipeline
- [ ] SignalRejectedEvent subscription unchanged
- [ ] Shadow position tracking unchanged
- [ ] Write path unchanged
- [ ] Fire-and-forget preserved
- [ ] 90-day retention unchanged

### Test Suite Health
- [ ] All pre-existing pytest pass (4,405 baseline)
- [ ] All pre-existing Vitest pass (700 baseline, 1 known failure)
- [ ] New tests per estimates (~36 pytest, ~8 Vitest)

---

## Escalation Criteria

### Tier 3 Triggers
1. Fingerprint backward incompatibility (golden hash test fails)
2. BacktestEngine reference data requires changes beyond backtest_engine.py
3. ExperimentConfig extra="forbid" conflict with exit_overrides
4. Trade Log tab breaks existing page architecture
5. 9th page navigation breaks keyboard shortcut scheme

### Scope Reduction Triggers
1. CounterfactualStore query >2s on 90-day data → add pagination
2. ABCD backtest >5 min for single-symbol/month → document, exclude from quick examples
3. PM candle data missing >50% of test symbols → reduce test scope
4. Frontend sessions exceed 13 after fixes → split into sub-sessions
