# Sprint 28.5 Work Journal — Exit Management

You are the Sprint Work Journal for Sprint 28.5 (Exit Management) of the ARGUS project. This conversation persists for the duration of the sprint. The developer will bring issues, session verdicts, and carry-forward items here.

---

## Sprint Goal

Deliver configurable, per-strategy exit management — trailing stops (ATR/percent/fixed), partial profit-taking with trail on T1 remainder, and time-based exit escalation — to Order Manager, BacktestEngine, and CounterfactualTracker.

## Session Breakdown

| Session | Scope | Creates | Modifies | Score | Key Amendments |
|---------|-------|---------|----------|-------|----------------|
| S1 | Exit math pure functions | exit_math.py | — | 10 | AMD-5, AMD-12 |
| S2 | Config models + SignalEvent atr_value | exit_management.yaml | config.py, events.py | 14 | AMD-1, AMD-5, AMD-10, AMD-11 |
| S3 | Strategy ATR emission + main.py | — | 7 strategies, main.py | 9 | AMD-9, AMD-10 |
| S4a | OM exit config + position fields | — | order_manager.py | 9 | — |
| S4b | OM trailing stop + escalation logic | — | order_manager.py | 14.5 | AMD-2, AMD-3, AMD-4, AMD-6, AMD-8 |
| S5 | BacktestEngine + CounterfactualTracker | — | engine.py, counterfactual.py | 13.5 | AMD-7 |
| S5f | Batch fix contingency | TBD | TBD | — | — |

**Dependency chain:** S1 → S2 → S3 → S4a → S4b → S5

**Estimated tests:** ~66 new

## Session Dependency Chain

```
S1 (exit_math.py) 
  → S2 (config models + SignalEvent) 
    → S3 (strategy ATR + main.py config loading)
      → S4a (OM config + position fields)
        → S4b (OM trailing stop + escalation — SAFETY CRITICAL)
          → S5 (BacktestEngine + CounterfactualTracker — AMD-7)
```

## Do Not Modify Files

These files must NOT be changed during Sprint 28.5:
- `argus/core/fill_model.py`
- `argus/core/risk_manager.py`
- `argus/intelligence/learning/` (any file)
- `argus/ui/` (any file)
- `argus/api/routes/` (any file)
- `argus/ai/` (any file)
- `config/risk_limits.yaml`
- `config/order_manager.yaml`

## Issue Categories (Summary)

1. **In-Session Bug:** Fix in current session. Mention in close-out.
2. **Prior-Session Bug:** Do NOT fix in current session. Note in close-out. Run targeted fix prompt after session review. If nothing downstream depends, defer to S5f.
3. **Scope Gap (small):** Implement in current session if it fits logically. Document in close-out.
4. **Scope Gap (substantial):** Do NOT squeeze in. Note in close-out. Follow-up prompt after review.
5. **Feature Idea:** Log as DEF item. Do not implement.

## Escalation Triggers

**HALT immediately:**
- Position leak in Order Manager (shares_remaining incorrect)
- Silent behavioral change for non-opt-in strategies
- Trail + broker safety stop deadlock
- BacktestEngine regression for existing configs
- Naked position from escalation failure (AMD-3 recovery also fails)

**Complete session, then escalate:**
- compute_effective_stop priority confusion
- IBKR bracket interaction issues during trail activation
- Config merge complexity beyond simple dict merge (AMD-1)
- fill_model.py needs changes
- AMD-7 bar-processing order requires loop restructure

## Reserved Numbers

- **DEC-378 through DEC-385** — Sprint 28.5 decisions
- **DEF numbers** — assign from current max + 1 (check CLAUDE.md)

## Safety-Critical Amendments (Quick Reference)

These are the adversarial review amendments that affect Order Manager safety (S4b):

| AMD | Requirement |
|-----|-------------|
| AMD-2 | Trail flatten: sell FIRST, cancel broker stop SECOND |
| AMD-3 | Escalation stop failure → immediate flatten |
| AMD-4 | shares_remaining > 0 before any sell |
| AMD-6 | Escalation exempt from DEC-372 retry cap |
| AMD-8 | _flatten_pending check FIRST before any broker interaction |

## Test Counts

Track actual vs estimated per session:

| Session | Estimated | Actual | Delta |
|---------|-----------|--------|-------|
| S1 | ~14 | | |
| S2 | ~12 | | |
| S3 | ~6 | | |
| S4a | ~6 | | |
| S4b | ~15 | | |
| S5 | ~13 | | |
| **Total** | **~66** | | |

## Verdict Tracking

| Session | Verdict | Notes |
|---------|---------|-------|
| S1 | | |
| S2 | | |
| S3 | | |
| S4a | | |
| S4b | | |
| S5 | | |

---

## Instructions for Developer

1. **Before each session:** Check this journal for carry-forward items from previous sessions.
2. **After each session:** Report the verdict, test count, and any issues here.
3. **If you encounter an issue:** Classify it (categories above) and bring it here for triage.
4. **At sprint close:** This journal produces the doc-sync prompt using the work-journal-closeout template.
