# Sprint 27.95: Escalation Criteria

## Tier 3 Escalation Triggers

1. **Reconciliation change breaks position lifecycle tests** — If modifying reconciliation logic causes failures in unrelated position management tests (open, close, bracket, fill handling), halt and escalate. This suggests the position tracking data model has undocumented coupling.

2. **Overflow routing blocks signals that should reach broker** — If the overflow check incorrectly prevents signals from reaching IBKR when position count is below threshold, or if the position count query returns incorrect values, halt and investigate. This is a correctness-critical path.

3. **_process_signal() flow change breaks quality pipeline or risk manager** — If inserting the overflow check alters the order of operations such that Quality Engine scoring, Risk Manager gating, or CounterfactualTracker shadow mode routing produces different results, halt and escalate. The overflow check must be purely additive — inserted after RM approval, before order placement.

4. **Stop resubmission cap causes unprotected positions** — If the emergency flatten after retry exhaustion fails (e.g., flatten also rejected by IBKR), the position is left without stop protection and without a flatten in flight. If this scenario is discovered during testing, escalate to design a fallback (e.g., cancel all orders for the symbol and wait for EOD flatten).

5. **Startup flatten closes positions that should be kept** — If the zombie cleanup logic incorrectly identifies a legitimate ARGUS-tracked position as "unknown" and flattens it at startup, this is data-destructive. Halt and fix the matching logic before proceeding.

## Session-Level Halt Conditions

- Any session's pre-flight test run shows failures not present at sprint entry → investigate before proceeding
- Any session introduces a test hang (test suite doesn't complete within 10 minutes) → halt, likely asyncio issue
- Modification to `_process_signal()` causes signal count divergence vs. baseline → halt, flow integrity compromised
