# Sprint 32.5: What This Sprint Does NOT Do

## Out of Scope

1. **Standalone strategy retrofit to variant framework:** ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, and Red-to-Green are NOT converted to PatternModule/variant form. That's Sprint 33 scope.
2. **ABCD O(n³) optimization:** DEF-122 remains open. The swing detection algorithm is accepted as-is; backtest runtime documented but not improved.
3. **New PatternModule patterns:** No new patterns are created. Only the existing 7 are wired into BacktestEngine.
4. **Real-time experiment monitoring:** Experiment sweeps remain batch/CLI operations. No WebSocket push for in-progress sweeps.
5. **Parameter heatmap visualization:** Complex D3 heatmap of parameter space is deferred. The Experiments page shows a table and list view, not a visual parameter landscape.
6. **3D visualizations on Experiments page:** No Three.js. Follows established 2D patterns (tables, Recharts, lists).
7. **Live position management from Experiments UI:** The Experiments page and Shadow Trades tab are read-only. No promote/demote buttons, no manual variant mode switching from UI.
8. **Experiment runner trigger from UI:** Sweeps are launched via CLI (`scripts/run_experiment.py`) only. No "Run Experiment" button in the app.
9. **Fingerprint migration:** Existing variants in experiments.db keep their detection-only fingerprints. New variants with exit_overrides get expanded fingerprints. Both schemes coexist; no migration script.
10. **Adaptive Capital Intelligence implementation:** DEF-133 produces a vision document ONLY. No code, no interfaces, no data models.
11. **Dedicated /summary endpoint for counterfactual stats:** Summary statistics are computed client-side from positions data via TanStack Query. No server-side aggregation endpoint.

## Edge Cases to Reject

1. **First day of data range for reference-data patterns (gap_and_go, premarket_high_break):** No prior day available. Expected behavior: log a warning, skip that day. Do NOT crash or return invalid data.
2. **Sparse PM candle data for premarket_high_break:** Some symbols/dates may have no pre-market candles in EQUS.MINI. Expected behavior: set_reference_data receives no PM high; pattern skips that symbol-date. Do NOT synthesize or estimate PM high.
3. **Shadow positions with variant_id=None:** Counterfactual positions created before Sprint 32 (variant system didn't exist). Expected behavior: display in Shadow Trades tab with "N/A" or "-" for variant fields. Do NOT filter them out.
4. **Empty experiment state:** No experiments have been run, no variants spawned, no shadow trades accumulated. Expected behavior: empty state messaging on both UI surfaces. Do NOT show broken/loading state.
5. **exit_overrides with keys that don't match ExitManagementConfig fields:** Expected behavior: deep_update applies them, but Pydantic validation in the strategy config catches invalid fields. Log warning if override keys don't correspond to known exit config fields. Do NOT silently ignore.
6. **Extremely large experiment grid (exit × detection combinatorial explosion):** Expected behavior: grid generates all combinations. CLI user is responsible for choosing reasonable sweep dimensions. Do NOT add grid size limits in this sprint.

## Scope Boundaries

- **Do NOT modify:** `core/events.py`, `core/regime.py`, `execution/order_manager.py`, `intelligence/counterfactual.py` (tracker write/subscription logic), any strategy files under `strategies/` (strategy detection/signal logic), `core/exit_math.py`, `core/config.py` (ExitManagementConfig read-only reference)
- **Do NOT optimize:** ABCD swing detection O(n³), CounterfactualStore write path, ExperimentStore write path
- **Do NOT refactor:** Existing BacktestEngine architecture (only add pattern support, don't restructure), existing Trade Log page (only add tab, don't reorganize), existing Experiments REST routes (only add endpoints, don't restructure)
- **Do NOT add:** Variant archival/deletion, experiment scheduling/cron, A/B testing framework, variant performance alerts, email/notification integration for promotions, export functionality for experiment results

## Interaction Boundaries

- This sprint does NOT change the behavior of: existing 4 experiment REST endpoints (Sprint 32), counterfactual accuracy endpoint (Sprint 27.7), shadow strategy mode LIVE/SHADOW mechanics, PromotionEvaluator's autonomous promotion/demotion logic, CounterfactualTracker's position tracking and fill model, Event Bus subscription patterns, existing 8 navigation pages
- This sprint does NOT affect: Order Manager execution path, Risk Manager gating, Quality Engine scoring, Learning Loop analysis, Orchestrator allocation, any live/paper trading behavior, any existing strategy behavior

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Standalone strategy retrofit to variant framework | 33 | (new DEF at planning) |
| ABCD swing detection optimization | Unscheduled | DEF-122 |
| Parameter space heatmap visualization | Unscheduled | (new DEF at planning) |
| Real-time experiment monitoring WebSocket | Unscheduled | (new DEF at planning) |
| Experiment runner UI trigger | Unscheduled | (new DEF at planning) |
| Fingerprint migration for existing variants | Unscheduled | (new DEF at planning) |
| Variant promote/demote from UI | Unscheduled | (new DEF at planning) |
| Adaptive Capital Intelligence Phase 1 | ~34-35 | (new DEF from vision doc) |
