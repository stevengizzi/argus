# Sprint 24: Sprint-Level Escalation Criteria

These criteria trigger immediate escalation to Tier 3 review or sprint halt. They apply across all sessions.

## Immediate Halt

1. **Quality Engine exception blocks ALL trading (when enabled).** If the fail-closed design means a bug in quality_engine.py prevents any signal from reaching the Risk Manager during a live session, halt immediately. Investigate whether a fallback scoring path (neutral 50 across all dimensions) should be added. This is the most dangerous failure mode — correct behavior for safety but catastrophic for missed opportunity.

2. **Canary test failure.** If Replay Harness signal count or entry prices differ pre/post sprint, strategy behavior has changed beyond the intended sizing modifications. Halt and investigate which strategy's `on_candle()` logic was inadvertently altered.

3. **Existing test suite regression.** If any of the 2,532 pytest or 446 Vitest tests that passed at sprint entry now fail and the failure is not attributable to an intentional SignalEvent field addition, halt the current session. Do not proceed until the regression is resolved.

3a. **Backtest bypass failure.** If Replay Harness with BrokerSource.SIMULATED produces different signal counts or entry prices than pre-sprint, the bypass is broken. Halt — this means backtest infrastructure is corrupted.

3b. **Legacy sizing path produces different results than pre-sprint.** When `quality_engine.enabled: false`, the system must behave identically to pre-Sprint-24. If it doesn't, the fallback path is broken.

## Escalate to Tier 3

4. **Firehose source returns zero items for >3 consecutive poll cycles during market hours.** Indicates API endpoint may have changed, authentication issue, or rate limiting. Escalate to investigate API status. The system can continue trading (catalyst dimension degrades to neutral 50) but data quality is compromised.

5. **On-demand catalyst lookup consistently timing out (>50% of calls exceed 5s).** Network or API issue affecting signal-time data freshness. Escalate to investigate. Consider increasing timeout or disabling on-demand in favor of firehose-only.

6. **Config weight sum validation fails on existing YAML files after Session 5b.** Pydantic model and YAML keys are mismatched. Escalate — this class of bug was specifically called out in the sprint planning protocol.

7. **Dynamic Sizer produces positions that consistently violate Risk Manager concentration limits.** Indicates the sizer's risk tiers are miscalibrated relative to account equity. The Risk Manager will catch these (approve-with-modification), but if it's happening on >30% of signals, the tier configuration needs review.

8. **Pattern strength scores cluster in a narrow band (<10-point spread) across diverse signal conditions.** The scoring formulas aren't differentiating meaningfully. The Quality Engine adds complexity without value. Escalate to review scoring factor weights and ranges.

## Informational (Log but Continue)

9. **Catalyst data unavailable for >50% of scored signals in a session.** Expected during early paper trading before firehose populates storage. Log daily coverage statistics. If this persists beyond 5 trading days, investigate source reliability.

10. **All signals in a session score the same grade.** Possible if market conditions are uniform. Log but don't escalate unless it persists across 3+ sessions with varied market conditions.
