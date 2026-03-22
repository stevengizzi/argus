# Sprint 27: Adversarial Review Revision Rationale

## Review Conducted
Inline adversarial review during sprint planning conversation, after spec-level artifacts were generated.

## Challenges Raised and Dispositions

| ID | Challenge | Severity | Disposition |
|----|-----------|----------|-------------|
| AR-1 | Engine/fill model metadata should be recorded in output | Low | **Accepted.** Added to S5 scope — output DB records `engine_type` and `fill_model`. |
| AR-2 | Bar-level fill model limitation for scalping strategies | Low | **Accepted.** Added documentation note to sprint spec. ORB Scalp results from BacktestEngine should be compared against Replay Harness before trusting. |
| AR-3 | Cost validation failure mode unspecified | Medium | **Accepted.** Fail-closed: if `metadata.get_cost()` raises, treat as non-zero and halt. `verify_zero_cost=False` bypass exists. Added to S2 acceptance criteria. |
| AR-4 | Walk-forward WFE incomparability across engines | Low | **Accepted.** `oos_engine` field added to WindowResult and WalkForwardResult. DEC-047 recalibration deferred to Sprint 21.6. |

## Challenges Considered and Dismissed

| Challenge | Why Dismissed |
|-----------|---------------|
| SyncBus handler dispatch order diverging from production EventBus | Single-strategy-per-run eliminates multi-handler concurrency. SyncBus sequential ordering is actually more deterministic. |
| Bar-level fill model systematic bias large enough to invalidate results | 1-minute bar ranges are typically small relative to strategy risk parameters. Bias is conservative (favors stops), which is the safe direction. |
| 20% trade count divergence tolerance too loose/tight | This is a directional sanity check, not a conformance gate. The exact threshold will be calibrated empirically in S6 equivalence tests. |

## Impact on Artifacts

- Sprint spec: 4 acceptance criteria additions (AR-1 through AR-4)
- Session breakdown: No changes (additions fit within existing test estimates)
- Compaction scores: No changes
- Escalation criteria: No changes needed
- Regression checklist: No changes needed
