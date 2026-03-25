# Sprint 27.7: Escalation Criteria

These conditions should trigger an immediate halt and escalation to the Work Journal for triage. Do not attempt to fix in-session without classification.

## Hard Halts (Stop and Escalate)

1. **BacktestEngine regression after fill model extraction.** If BacktestEngine produces different trade results (different fills, different P&L, different trade count) after the TheoreticalFillModel extraction in Session 1, HALT. Do not proceed to Session 2. The shared fill model is a foundational correctness guarantee — if it changes behavior, every downstream consumer is affected.

2. **Fill priority disagreement.** If the extracted `evaluate_bar_exit()` function produces a different exit decision than the original inline code for any test case, HALT. Reconcile before proceeding. This includes edge cases: same-bar stop+target, time stop on a bar that also hits stop, EOD close when stop is also breached.

3. **Event bus ordering violation.** If `SignalRejectedEvent` publishing in `_process_signal()` causes CandleEvents or OrderApprovedEvents to be delivered out of FIFO order, HALT. This would indicate the event bus contract (DEC-025) is being violated.

4. **Existing test failures.** Any pre-existing test that fails after a session's changes → HALT. Classify as a regression and root-cause before continuing. The only acceptable existing-test modification is updating BacktestEngine tests to import from the new `fill_model` module (Session 1).

5. **`_process_signal()` behavioral change for live-mode strategies.** If any test or manual inspection reveals that the signal processing flow for `mode: live` strategies has changed behavior (different order approval/rejection, different share counts, different timing), HALT. The counterfactual system must be purely additive.

## Soft Halts (Investigate, May Continue)

6. **CounterfactualStore write failures during integration tests.** If SQLite writes fail intermittently during Session 3b/4 integration tests, investigate aiosqlite concurrency. May continue if failures are test-environment-specific (e.g., WAL mode not enabled). If failures reproduce consistently, escalate.

7. **IntradayCandleStore backfill returns unexpected data.** If the `get_bars()` API returns bars outside the requested time range, or returns empty when bars should exist, investigate the store's market-hours filter. May continue with backfill disabled (forward-only monitoring is functional).

8. **Session compaction warning.** If any session approaches the ~80% context utilization mark before completing all deliverables, stop and log progress. Use the "backfill is the pressure valve" contingency for Session 1 if needed. For Session 3b, YAML config changes can be deferred to a manual step.

## Not Escalation (Expected Behavior)

- CounterfactualTracker receiving zero candle events in tests that don't set up a candle stream → expected, use mock events.
- FilterAccuracy returning None for breakdowns with < 10 samples → expected, that's the minimum threshold.
- Shadow mode tests needing a mock strategy → expected, real strategies don't need to be instantiated.
