# Sprint 32.5: Escalation Criteria

## Tier 3 Escalation Triggers

These conditions require pausing implementation and escalating to a Claude.ai architectural review:

1. **Fingerprint backward incompatibility.** If the expanded `compute_parameter_fingerprint()` produces a different hash for detection-only variants (no exit_overrides) than the pre-expansion version. This would mean existing variant data becomes orphaned. Golden hash test failure is the signal.

2. **BacktestEngine reference data requires architectural changes beyond backtest_engine.py.** If supplying prior close / PM high to patterns via `set_reference_data()` requires modifying the HistoricalDataFeed, SynchronousEventBus, or TheoreticalFillModel. The intent is a localized change within the BacktestEngine's per-day simulation loop, not a cross-cutting concern.

3. **ExperimentConfig extra="forbid" conflict with exit_overrides.** If adding `exit_overrides` to the config schema requires changing the `extra="forbid"` setting or restructuring the config model hierarchy. This would weaken an existing safety guard.

4. **Trade Log tab architecture breaks existing page.** If adding the Shadow Trades tab requires restructuring the Trade Log page's state management, routing, or data flow in a way that risks the existing trade display. The tab must be purely additive.

5. **9th page navigation breaks keyboard shortcut scheme.** If the existing 1-8 keyboard shortcut mapping doesn't naturally accommodate a 9th page, requiring a shortcut scheme redesign.

## Scope Reduction Triggers

These conditions call for reducing scope rather than escalating:

1. **CounterfactualStore query performance >2s on 90-day data.** Add pagination to the positions endpoint. Defer complex date-range aggregations.

2. **ABCD backtest exceeds 5 minutes for single-symbol, single-month.** Document the limitation and exclude ABCD from "quick sweep" examples. DEF-122 remains open.

3. **PM candle data missing for >50% of test symbols.** Reduce premarket_high_break test scope to symbols with known PM data. Document data availability constraints.

4. **Frontend sessions exceed 13 compaction score after accounting for visual review fixes.** Split into additional sub-sessions rather than cramming fixes into the contingency slot.

## In-Flight Triage Criteria

Issues discovered during implementation that do NOT require escalation:

- Minor type mismatches between API response and frontend expectations → fix in same session
- Empty state UI needs adjustment → handle in contingency session (S6f/S7f)
- Additional test cases needed beyond estimate → add if within session scope, defer if not
- Config field naming inconsistency → fix immediately, note in close-out
