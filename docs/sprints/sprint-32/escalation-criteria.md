# Sprint 32: Escalation Criteria

## Tier 3 Escalation Triggers

These conditions require stopping implementation and escalating to a Tier 3 architectural review in Claude.ai:

1. **Throughput degradation:** Shadow variant processing causes >10% increase in candle processing latency for live strategies as measured by comparing pre-variant and post-variant processing times. This would indicate the architectural approach of running all variants on the same event bus is fundamentally flawed.

2. **Memory explosion:** Variant spawning (5 variants × 7 patterns = 35 shadow strategies) causes >2× memory increase at startup compared to the 12-strategy baseline. Would indicate that the PatternBasedStrategy wrapper is too heavy for mass instantiation and needs a lightweight shadow-only wrapper.

3. **Event Bus contention:** Shadow variant signal processing creates backpressure on the event bus that delays live signal processing. The Event Bus is FIFO per subscriber (DEC-025) — 35+ additional subscribers could theoretically create ordering issues.

4. **Fingerprint collision:** Two meaningfully different parameter configurations produce the same fingerprint hash. This is a determinism/correctness issue that undermines the entire experiment tracking system.

5. **CounterfactualTracker overload:** The existing CounterfactualTracker was designed for rejected signals (~dozens per day). Shadow variants could generate hundreds of shadow positions. If the tracker's SQLite writes or position monitoring can't handle the volume, the architecture needs revision.

## HALT Triggers

These conditions require immediate halt — do not proceed to the next session:

1. **Factory regression:** `build_pattern_from_config()` fails to construct any of the 7 existing patterns with their current default configs. This means the factory broke backward compatibility.

2. **Startup failure:** ARGUS fails to start with `experiments.enabled: false` (the default). The experiment pipeline must be invisible when disabled.

3. **Test suite regression:** Any pre-existing test failure introduced by the sprint's changes. Full suite must pass at every close-out.

4. **Config silent drop:** A detection parameter specified in YAML is ignored by the Pydantic model and the pattern uses a different value than what's in the config file. This is the exact bug this sprint is designed to prevent.

## WARNING Conditions

These are concerning but do not require halting:

1. **BacktestEngine performance:** Experiment runner sweep takes >60 minutes for a 50-point grid on a single pattern. Not a blocker (can optimize later) but indicates the grid density may need to be reduced.

2. **Variant spawner startup time:** >10 seconds to spawn all variants at startup. Not a blocker for paper trading but would be unacceptable for production.

3. **Promotion evaluator insufficient data:** After wiring, if the evaluator consistently finds insufficient shadow data to make decisions, the `promotion_min_shadow_trades` threshold may need adjustment. This is a tuning issue, not an architectural issue.
