# Sprint 28.5: Escalation Criteria

> **Revision:** Post-adversarial review (March 29, 2026). AMD references added.

These criteria define when an implementation session should halt and escalate to Tier 3 review (Claude.ai architectural conversation) rather than attempting to resolve in-session.

---

## Critical Escalations (HALT immediately)

1. **Position leak in Order Manager.** Any code path where `shares_remaining` on a ManagedPosition could become incorrect (negative, exceeding original shares, or not tracked through a trail/escalation exit). Position leaks mean unmonitored shares in the market.

2. **Silent behavioral change for non-opt-in strategies.** If a strategy with `trailing_stop.enabled: false` and `escalation.enabled: false` produces any different behavior after this sprint — in Order Manager, BacktestEngine, or CounterfactualTracker — this is a regression that must be escalated before proceeding.

3. **Trail + broker safety stop deadlock.** If the AMD-2 order-of-operations (sell first, cancel second) creates a scenario where neither the trail flatten nor the broker safety stop can execute (e.g., mutual cancellation, circular dependency), halt and escalate.

4. **BacktestEngine regression.** If running an existing strategy backtest (e.g., ORB Breakout with current config, no exit management overrides) produces different results after the sprint's changes, halt. This means the integration changed evaluation behavior for strategies that didn't opt in.

5. **Naked position from escalation failure.** If AMD-3 recovery (flatten on failed escalation stop resubmission) itself fails, leaving a position with no broker stop and no pending flatten, halt and escalate. This is the worst-case failure mode for the escalation system.

## Significant Escalations (complete current session, then escalate)

6. **Escalation stop + trail stop + original stop priority confusion.** If the `compute_effective_stop()` logic becomes unclear about which stop source should win in edge cases (e.g., escalation says breakeven but trail says higher), escalate for architectural review of the priority model.

7. **IBKR bracket order interaction issues during trail activation.** If the T1 fill → trail activation → broker stop coexistence pattern produces unexpected IBKR behavior (e.g., IBKR auto-cancels the safety stop when the trail flatten is submitted), escalate. This may require a design change to the belt-and-suspenders pattern.

8. **Config merge complexity (AMD-1).** If field-level deep merge produces unexpected behavior with nested config structures (e.g., phase list merging, partial escalation overrides), escalate. The `deep_update()` utility should be simple recursive dict merge — if it requires special-case logic, the config model needs rethinking.

9. **TheoreticalFillModel pressure.** If BacktestEngine or CounterfactualTracker trail logic requires changes to `evaluate_bar_exit()` in `fill_model.py` (which is in the "do not modify" list), escalate to reconsider the architecture. The intent is to keep trail state external to the fill model.

10. **AMD-7 bar-processing order violation.** If implementing the prior-state-first bar-processing order requires restructuring BacktestEngine's bar loop in ways that affect non-trail behavior, escalate. The change should be additive (insert trail/escalation logic at correct points), not a loop restructure.

## Informational Flags (log in Work Journal, no halt)

11. **ATR computation variance across strategies (AMD-9).** If different strategies compute ATR using different periods despite the AMD-9 standardization guidance, log the discrepancy. This doesn't block the sprint but should be tracked.

12. **Test count exceeding estimate by >50%.** If any session requires significantly more tests than estimated, log in work journal for compaction scoring calibration.

---

## DEC/DEF Reservation

- **DEC-378 through DEC-385** reserved for Sprint 28.5 decisions.
- **DEF numbers** assigned as needed from current max + 1 (check CLAUDE.md at sprint start).
