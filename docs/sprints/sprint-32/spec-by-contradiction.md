# Sprint 32: What This Sprint Does NOT Do

## Out of Scope

1. **Non-PatternModule strategy variants:** ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, and Red-to-Green do not use the PatternModule interface. Variant spawning and the experiment pipeline only cover the 7 PatternModule patterns. Retrofitting the standalone strategies is a separate sprint (~Sprint 33).

2. **Hot-reload of parameters:** Changing detection parameters requires a restart. Intraday adaptation of *which variant is live vs shadow* is supported (mode changes), but the parameters themselves are frozen at startup. Full intraday parameter adaptation is deferred to post-Sprint 34.

3. **Anti-fragility / degradation detection / automatic rollback:** If a promoted config underperforms, the promotion evaluator can demote it back to shadow, but there is no automatic "this config degraded over time" detection with rollback to a previous known-good config. Deferred to Sprint 33.5.

4. **Actual parameter tuning:** This sprint builds the infrastructure. It does not run sweeps or promote any specific configurations. The operator runs their first sweep manually after the sprint is complete.

5. **Novel strategy discovery:** The Continuous Discovery Pipeline (Sprint 36+) where ARGUS invents new detection logic is not part of this sprint. This sprint only creates variants of existing human-designed templates.

6. **UI changes:** No frontend modifications. Experiment data is exposed via REST API only. A dedicated Experiments page is a future sprint.

7. **ABCD O(n³) optimization (DEF-122):** The ABCD swing detection algorithm remains O(n³). Parameter sweeps at scale will be slow for ABCD. Optimization is a prerequisite for large ABCD grid searches but is not this sprint.

8. **Learning Loop V2 auto-approval:** The existing ConfigProposalManager (Sprint 28) is not modified. The promotion evaluator is a separate autonomous system. Merging the two into a unified auto-approval pipeline is Sprint 40.

9. **Cross-strategy ensemble optimization:** Promotion evaluates variants independently. Portfolio-level "does adding this variant improve the ensemble?" analysis is Sprint 34–35 scope.

10. **Variant-specific exit management:** All variants of a given pattern template share the same exit management config. Per-variant exit tuning is deferred.

## Edge Cases to Reject

1. **Variant with same parameters as base strategy:** The spawner should detect this (identical fingerprint) and skip spawning a duplicate. Log at INFO level.

2. **Zero valid variants after backtest pre-filter:** If all grid points fail the minimum bar, log a WARNING and spawn zero variants. Do not fall back to spawning unvalidated variants.

3. **Promotion evaluator runs with insufficient shadow data:** If a variant has fewer than `promotion_min_shadow_trades`, skip evaluation. Do not extrapolate from small samples.

4. **Multiple variants promoted for the same pattern simultaneously:** This is allowed and expected (non-zero-sum). The system does not enforce a "one live variant per template" constraint.

5. **Shadow variant generates a signal for a symbol where a live variant of the same pattern already has an open position:** The shadow signal routes to CounterfactualTracker normally. No special handling needed — the existing shadow mode routing (Sprint 27.7) already handles this.

6. **Experiment runner called for a pattern with no Parquet cache data:** Return an error result with clear message. Do not fall back to live data.

7. **Config YAML has detection params outside PatternParam bounds:** Pydantic Field validators reject at startup with a clear validation error. Do not clamp silently.

## Scope Boundaries

- **Do NOT modify:** Any file in `argus/strategies/` other than `pattern_strategy.py` (and only if strictly necessary), any non-PatternModule strategy file (`orb_breakout.py`, `orb_scalp.py`, `vwap_reclaim.py`, `afternoon_momentum.py`, `red_to_green.py`), `argus/core/orchestrator.py`, `argus/intelligence/learning/` package, `argus/intelligence/counterfactual.py`, any frontend file in `argus/ui/`
- **Do NOT optimize:** ABCD O(n³) swing detection, BacktestEngine performance, Parquet cache I/O
- **Do NOT refactor:** Existing strategy construction in `main.py` beyond replacing pattern constructors with factory calls. Do not restructure the startup sequence.
- **Do NOT add:** New PatternModule patterns, new standalone strategies, new Event Bus event types (use existing SignalRejectedEvent for shadow routing), new frontend pages or components

## Interaction Boundaries

- This sprint does NOT change the behavior of: Orchestrator strategy registration API, Risk Manager gating logic, Order Manager signal processing, CounterfactualTracker signal handling, Event Bus publish/subscribe
- This sprint does NOT affect: Live trading execution path (all new code is config-gated behind `experiments.enabled: false`), existing Learning Loop V1 proposals, existing shadow mode routing, Quality Engine scoring

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Non-PatternModule strategy variants | Sprint 33 | DEF-129 (new) |
| Anti-fragility / degradation detection | Sprint 33.5 | (existing scope) |
| ABCD O(n³) optimization | Unscheduled | DEF-122 |
| Intraday parameter adaptation | Sprint 34+ | DEF-130 (new) |
| Cross-strategy ensemble optimization | Sprint 34–35 | (existing scope) |
| Experiments UI page | Unscheduled | DEF-131 (new) |
| Variant-specific exit management | Unscheduled | DEF-132 (new) |
| Learning Loop V2 auto-approval merge | Sprint 40 | (existing scope) |
| Per-variant capital allocation | Unscheduled | DEF-133 (new) |
