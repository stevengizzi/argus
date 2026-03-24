# Review Context: Sprint 27.65 — Market Session Safety + Operational Fixes

## Sprint Spec Summary

Impromptu sprint addressing 18 issues discovered during the March 24, 2026
paper trading session. The critical finding: duplicate flatten orders from the
Order Manager's time-stop loop created $2.8M in phantom short positions at IBKR.

## Sprint-Level Regression Checklist

| Check | How to Verify |
|-------|---------------|
| Normal stop-loss path works | Test: position hits stop → single SELL order → position closed |
| Normal target-hit path works | Test: position hits T1/T2 → bracket closes → position closed |
| Time-stop fires exactly once | Test: position exceeds time limit → one flatten order → no duplicates |
| Bracket legs use actual fill price | Test: signal entry != fill price → targets/stops adjusted to fill basis |
| Shutdown cancels orders | Test: shutdown sequence → reqGlobalCancel called before disconnect |
| Risk Manager allows unlimited positions when configured | Test: max_concurrent=0 → no position limit check |
| CandleStore accumulates bars | Test: CandleEvent published → store has bar for symbol |
| Observatory funnel shows counts | Test: pipeline endpoint returns non-zero stage counts |
| Session Timeline shows 7 strategies | Visual: Dashboard timeline has all 7 strategy rows |

## Sprint-Level Escalation Criteria

Escalate to Tier 3 if:
1. Any change to Order Manager introduces a new path where orders can be
   submitted without risk checks
2. Position reconciliation auto-corrects (it should only warn, not act)
3. Bracket amendment logic could cancel brackets without replacing them,
   leaving a position unprotected
4. Any change breaks the existing `BrokerSource.SIMULATED` bypass path
5. Changes to Risk Manager affect the circuit breaker or daily loss limit logic
