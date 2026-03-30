# Sprint 29: Escalation Criteria

## Tier 3 Escalation Triggers

These conditions halt implementation and escalate to Claude.ai for architectural review:

1. **ABCD swing detection false positive rate >50%** — If manual spot-check of ABCD detections on historical data shows more than half are false positives (detecting "ABCD" patterns in random price noise), the swing detection algorithm needs architectural rethinking, not parameter tuning.

2. **PatternParam backward compatibility break** — If changing `get_default_params()` return type from `dict[str, Any]` to `list[PatternParam]` causes failures in code paths outside the pattern/backtester modules (e.g., Quality Engine, config serialization, unexpected consumers), this indicates a deeper coupling than anticipated.

3. **Pre-market candle availability failure** — If EQUS.MINI does NOT deliver extended-hours candles into PatternBasedStrategy's deque (contradicting the Sprint 27.65 fix assumption), PM High Break needs an alternative data path. This is an architectural question, not an implementation bug.

4. **Universe filter field silently ignored** — If `min_relative_volume`, `min_gap_percent`, or `min_premarket_volume` don't exist in UniverseFilterConfig and adding them requires structural changes to the filter model (not just adding a field), escalate. This means the filter model needs redesign.

5. **PatternBasedStrategy reference data hook causes initialization ordering issues** — If calling `set_reference_data()` during PatternBasedStrategy init creates circular dependencies or timing issues with Universe Manager reference data availability, the hook design needs review.

## Halt-and-Fix Triggers

These conditions halt the current session for immediate fix within scope:

1. **Existing pattern behavior change detected** — Any test failure in Bull Flag or Flat-Top after S2 retrofit that indicates changed detection or scoring behavior (not just API surface changes).

2. **PatternBacktester grid generation mismatch** — If retrofitted patterns produce grids that cause the backtester to fail or produce degenerate results (zero trades, infinite Sharpe), fix before proceeding.

3. **Config parse failure** — Any new strategy YAML that fails Pydantic validation. Fix the YAML or the model immediately.

4. **Strategy registration collision** — If registering a new strategy causes ID or name collision with existing strategies.

## Warning-and-Continue Triggers

These conditions are logged but do not halt:

1. **Smoke backtest produces zero signals** — A new pattern detecting nothing in 5 symbols × 6 months is concerning but not blocking. Log the symbols tested and the pattern parameters. May indicate overly strict detection thresholds — can be tuned post-sprint during walk-forward validation.

2. **Low test count for a session** — If a session produces fewer tests than estimated (e.g., 6 instead of 10), note in close-out but continue. The estimate may have been high.

3. **ABCD session exceeds compaction score** — S6a is pre-approved at 15 (High). If the implementation runs long, note the actual complexity but do not halt for compaction alone — the session is self-contained.
