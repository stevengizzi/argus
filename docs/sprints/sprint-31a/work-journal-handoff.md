# Sprint 31A Work Journal — Handoff Prompt

> Paste this into a fresh Claude.ai conversation to create the Sprint 31A Work Journal.
> This is the in-flight triage conversation for tracking session verdicts, issues,
> DEF/DEC assignments, and producing the final doc-sync prompt.

---

## Sprint Context

**Sprint 31A: Pattern Expansion III — Reach 15 Strategies**

**Goal:** Fix DEF-143 (BacktestEngine pattern init) and DEF-144 (debrief safety_summary), resolve PMH 0-trade root cause, add 3 new PatternModule strategies (Micro Pullback, VWAP Bounce, Narrow Range Breakout), and run full parameter sweep across all 10 PatternModule patterns.

**Execution mode:** Human-in-the-loop

**Test baseline:** ~4,674 pytest + 846 Vitest (0 failures)

**Estimated test delta:** ~51 new pytest tests → ~4,725 pytest + 846 Vitest

---

## Session Breakdown

| Session | Scope | Creates | Modifies | Score |
|---------|-------|---------|----------|-------|
| S1 | DEF-143 BacktestEngine fix + DEF-144 debrief safety_summary | tests | engine.py, order_manager.py, debrief_export.py | 13 (Med) |
| S2 | PMH 0-trade fix (min_detection_bars + lookback + ref data) | tests | base.py, pattern_strategy.py, premarket_high_break.py, main.py | 14 (High) |
| S3 | Micro Pullback pattern (complete) | micro_pullback.py + YAMLs + tests | config.py, main.py, backtest/config.py, engine.py, factory.py, runner.py | ~13 adj |
| S4 | VWAP Bounce pattern (complete) | vwap_bounce.py + YAMLs + tests | same 6 files | ~12 adj |
| S5 | NR Breakout pattern (complete) | narrow_range_breakout.py + YAMLs + tests | same 6 files | ~12 adj |
| S6 | Parameter sweep + experiments.yaml | results doc | experiments.yaml | 5 (Low) |

**Dependency chain:** S1 → S2 → S3 → S4 → S5 → S6 (all sequential, no parallelization)

---

## Do Not Modify List

These files/directories must NOT be modified during Sprint 31A:
- `argus/core/orchestrator.py`
- `argus/core/risk_manager.py`
- `argus/intelligence/learning/` (entire directory)
- `argus/ai/` (entire directory)
- `argus/api/` (no route changes)
- `argus/ui/` (no frontend changes)
- Existing pattern files: `bull_flag.py`, `flat_top_breakout.py`, `dip_and_rip.py`, `hod_break.py`, `gap_and_go.py`, `abcd.py` (read-only reference)
- Existing strategy config YAMLs
- `argus/data/universe_manager.py`

---

## Issue Category Definitions

When issues arise during implementation, classify them:

- **SCOPE_GAP:** Something the spec didn't address but the implementation needs. Requires a decision on how to handle it.
- **BUG_IN_PRIOR:** A bug in existing code discovered during implementation that blocks or affects this sprint's work.
- **DESIGN_REVISION:** The planned design doesn't work as specified and needs revision.
- **CARRY_FORWARD:** Work that should have been in this session but couldn't be completed.
- **OBSERVATION:** Non-blocking finding worth tracking for future reference.

---

## Escalation Triggers

### Tier 3 Escalation (STOP — escalate to Claude.ai)
1. DEF-143 fix breaks existing backtest results
2. min_detection_bars changes existing pattern behavior
3. New pattern signals appear outside operating window
4. Test count decreases at any session
5. Parameter sweep shows BacktestEngine still ignoring config_overrides

### Handle Within Session
- Cross-validation test failures → fix divergent values
- Indicator unavailable → compute from candle data
- S2 reference data wiring exceeds budget → defer to S2b
- Pattern sweep finds 0 qualifying variants → document, don't lower thresholds
- ABCD sweep slow → expected (DEF-122)

---

## DEF/DEC Number Reservations

- **DEF range:** DEF-145 through DEF-155
- **DEC range:** DEC-382 through DEC-390 (if needed — unlikely)

**IMPORTANT:** Before assigning any DEF/DEC number, grep the actual files:
```bash
grep -rn "DEF-14[5-9]\|DEF-15[0-5]" docs/ CLAUDE.md
grep -rn "DEC-38[2-9]\|DEC-390" docs/ CLAUDE.md
```

---

## Session Tracking Template

For each session, track:

```
### Session [N] — [Title]
**Status:** [NOT_STARTED / IN_PROGRESS / COMPLETE]
**Verdict:** [CLEAR / CONCERNS / CONCERNS_RESOLVED / ESCALATE]
**Test delta:** pytest [before] → [after] (+[delta]), Vitest [before] → [after] (+[delta])
**Issues:**
- [issue category]: [description] → [resolution or DEF-N]
**Carry-forward:** [items for next session, if any]
```

---

## At Sprint Close

When all 6 sessions are complete:

1. Produce the Work Journal Close-Out with:
   - Sprint summary (goal, sessions, test delta, verdicts)
   - DEF numbers assigned (with status)
   - Any DEC decisions made
   - Carry-forward items
   - Final test counts

2. Produce the doc-sync prompt using `templates/doc-sync-automation-prompt.md` from the workflow metarepo, embedding the close-out data so the doc-sync session has full visibility.
