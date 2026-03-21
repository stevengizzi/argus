# Sprint 26: Escalation Criteria

These conditions should trigger an immediate halt and escalation to the Work Journal / developer review.

## Critical (Halt Immediately)

1. **PatternModule ABC interface does not support BacktestEngine use case.** If during S1 implementation, the detect()/score() interface cannot cleanly accept historical candle sequences (not just live CandleEvents), halt and redesign. The ABC must work for both live and backtesting contexts.

2. **Existing strategy tests fail after any session.** If any of the 4 existing strategy test suites (orb_breakout, orb_scalp, vwap_reclaim, afternoon_momentum) fail, halt and investigate before proceeding. These files should not have been modified.

3. **BaseStrategy interface modification required.** If implementing R2G or PatternBasedStrategy requires changing the BaseStrategy abstract interface (new abstract methods, signature changes), halt. This would affect all 4 existing strategies and is out of scope.

4. **SignalEvent schema change required.** If R2G or patterns need new fields on SignalEvent, halt. The event schema is frozen. Use `signal_context` dict for strategy-specific metadata.

5. **Quality Engine changes required.** If the Quality Engine cannot score new strategies with the existing interface (pattern_strength → composite score), halt. The scoring algorithm must not change.

## Significant (Document and Assess)

6. **VectorBT walk-forward WFE < 0.3 for Red-to-Green.** This is the primary strategy in the sprint. If it fails validation, document the results, set `pipeline_stage: "exploration"`, and discuss with developer before S9 integration. R2G may still be wired in disabled.

7. **VectorBT walk-forward WFE < 0.3 for both Bull Flag AND Flat-Top.** One pattern failing is acceptable (set to exploration stage). Both patterns failing suggests the PatternBasedStrategy wrapper or detection logic has fundamental issues. Document and review.

8. **S4 (PatternBasedStrategy) compaction at <60% completion.** S4 scores 14 (boundary). If implementation shows signs of compaction before the wrapper is functionally complete, halt S4 and split into S4a (wrapper core) and S4b (tests + telemetry).

9. **R2G state machine requires more than 5 states.** If during S2/S3 implementation, the state machine needs 6+ states, document the rationale and assess whether the additional complexity is warranted vs. simplifying the entry logic.

10. **Integration wiring (S9) causes Orchestrator capital allocation failures.** If adding 3 new strategies causes the equal-weight allocator to produce unreasonable per-strategy allocations (e.g., <5% each with 7 strategies), document and assess whether allocation logic needs adjustment.

11. **config.py becomes unwieldy (>1000 lines).** Currently ~908 lines. Adding 3 new config classes + loaders adds ~100–150 lines. If it exceeds 1000, document as a DEF item for future config module split but do not refactor in this sprint.

## Informational (Log in Work Journal)

12. **R2G gap-down pattern scarce in historical data.** If VectorBT finds very few gap-down reversals in the test data (e.g., <50 total trades), log the finding. This doesn't block the sprint but affects backtest statistical significance.

13. **Pattern detection latency exceeds 1ms per candle.** Performance target. If exceeded, log but do not optimize in this sprint.

14. **Vitest count lower than expected.** If existing PatternCard/PatternDetail components handle new strategies without modification, fewer Vitest tests may be needed. This is a positive outcome (good existing abstraction), not a problem.
