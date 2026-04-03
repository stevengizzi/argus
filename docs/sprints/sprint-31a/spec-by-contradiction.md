# Sprint 31A: What This Sprint Does NOT Do

## Out of Scope

1. **ABCD O(n³) optimization (DEF-122):** ABCD swing detection remains O(n³). The parameter sweep in S6 will be slower for ABCD but is not blocked. Optimization deferred until it actually blocks a sweep.

2. **Time-of-day signal conditioning (DEF-125):** No time-of-day parameter dimensions added. New patterns have operating windows but no intra-window time modulation.

3. **Regime-strategy interaction profiles (DEF-126):** No per-strategy regime sensitivity tuning. New patterns use the same regime filtering as all existing strategies (only `crisis` blocks).

4. **Standalone strategy modifications:** ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, and Red-to-Green are not modified. R2G's existing `initialize_prior_closes()` wiring is unchanged — only PMH and GapAndGo gain new reference data wiring.

5. **Experiment pipeline infrastructure changes:** The pipeline (VariantSpawner, ExperimentRunner, PromotionEvaluator, ExperimentStore) is not modified. Only the pattern registry/mapping and experiments.yaml are updated.

6. **Frontend / UI work:** No new pages, no UI components, no styling changes. The 3 new strategies will appear automatically in existing UI components (Trade Log, Orchestrator, Pattern Library) via the strategy identity system — but no new strategy-specific identity assignments (colors, badges, letters) are created in this sprint. Those require a UI session.

7. **Strategy identity assignments (colors/badges/letters):** The strategy identity system (Sprint 32.75) uses a fixed palette. New strategies will use auto-fallback styling until a UI polish session assigns specific identities. Not in scope.

8. **Exit management tuning:** No changes to `config/exit_management.yaml` or `strategy_exit_overrides`. New patterns use sensible defaults defined in their strategy config YAML's `exit_management` section, following the same structure as existing patterns.

9. **Learning Loop interaction:** No changes to Learning Loop V1. New patterns will naturally be observed by OutcomeCollector once they produce trades/counterfactuals.

10. **Short selling (Sprint 30):** All new patterns are long-only. Short-side detection deferred until longs are profitable.

11. **Backtest re-validation of existing strategies:** DEF-143 fix enables proper validation, but re-running all existing strategy backtests is not in S6's scope. S6 focuses on PatternModule parameter sweeps. Full re-validation is a separate effort.

12. **UM `min_premarket_volume` enforcement at routing level:** The UM routing table does not filter on `min_premarket_volume`. It's a config field checked at detection time. No change to this behavior.

## Edge Cases to Reject

1. **Micro Pullback with no clear impulse:** If the prior move doesn't meet `min_impulse_percent` threshold, return None from detect(). Do not attempt to find "weaker" impulses.

2. **VWAP Bounce when VWAP unavailable:** If VWAP indicator returns None or 0.0, return None. Do not substitute with a moving average or synthetic VWAP.

3. **VWAP Bounce when price has been below VWAP:** If the `min_prior_trend_bars` above-VWAP requirement is not met, return None. Do not enter on a "first touch from below" — that's VWAP Reclaim territory.

4. **Narrow Range Breakout downward:** Only long entries. If the breakout is below the consolidation low, return None. Short entries are Sprint 30 scope.

5. **Narrow Range Breakout with exactly 1 narrowing bar:** `min_narrowing_bars ≥ 2` enforced by Pydantic Field bound. A single bar is not a consolidation pattern.

6. **PMH with lookback_bars=400 but zero backfill:** If IntradayCandleStore has no bars (cold start mid-session), PMH simply won't fire until enough bars accumulate organically. This is correct behavior — PMH needs PM data.

7. **BacktestEngine config_overrides for non-PatternModule strategies:** DEF-143 fix only applies to the 7 `_create_*_strategy()` methods for PatternModule patterns. The 5 standalone strategy creation methods are unchanged.

8. **Parameter sweep finds no qualifying variants for a pattern:** Document the pattern's best results and why they didn't qualify. Do not lower the qualification thresholds (Sharpe > 0.5, trades ≥ 30, expectancy > 0). The pattern remains active in base configuration.

## Scope Boundaries

- Do NOT modify: `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/intelligence/learning/` (entire directory), `argus/ai/` (entire directory), `argus/api/` (no API route changes), `argus/ui/` (no frontend changes), existing pattern files (`bull_flag.py`, `flat_top_breakout.py`, `dip_and_rip.py`, `hod_break.py`, `gap_and_go.py`, `abcd.py` — read-only reference), existing strategy config YAMLs (no parameter changes), `argus/data/universe_manager.py` (no routing changes)

- Do NOT optimize: ABCD O(n³) swing detection. If ABCD sweep is slow, accept it and document timing.

- Do NOT refactor: PatternBasedStrategy's candle accumulation logic beyond the `min_detection_bars` threshold change. The backfill mechanism is correct; only the "what constitutes enough bars" check changes.

- Do NOT add: WebSocket endpoints, REST API routes, database tables, new SQLite databases, frontend components, or AI layer changes.

## Interaction Boundaries

- This sprint does NOT change the behavior of: Event Bus, Order Manager (beyond DEF-144 tracking attrs), Risk Manager, Orchestrator, AI Layer, Learning Loop, or any existing strategy's signal generation
- This sprint does NOT affect: position management, bracket orders, exit management engine, reconciliation, or any trading execution path
- This sprint does NOT change: the experiment pipeline's promotion/demotion logic, the CounterfactualTracker, or the quality engine scoring formula
- New patterns interact with the system through the established PatternBasedStrategy wrapper — no new interaction patterns are introduced

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| ABCD O(n³) optimization | Pre-scale sweep | DEF-122 |
| Time-of-day signal conditioning | Sprint 33+ | DEF-125 |
| Regime-strategy interaction profiles | Sprint 33+ | DEF-126 |
| Strategy identity assignments for new patterns | Next UI polish sprint | (new — log during sprint) |
| UM min_premarket_volume routing enforcement | Unscheduled | (new — log during sprint) |
| Short-side detection for new patterns | Sprint 30 | — |
| Full re-validation of all 12 existing strategies | Separate effort | — |
