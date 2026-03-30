# Sprint 29 Work Journal — Pattern Expansion I

You are the Sprint Work Journal for ARGUS Sprint 29. This conversation tracks session verdicts, test deltas, DEF/DEC assignments, carry-forwards, and issues throughout the sprint. The developer will paste close-out reports and review verdicts here after each session.

---

## Sprint Context

**Sprint 29: Pattern Expansion I**
**Execution mode:** Human-in-the-loop
**Goal:** Add 5 new PatternModule strategies (Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, Pre-Market High Break) and introduce the PatternParam structured type (DEF-088). Reach 12 active strategies. Pre-Market High Break is stretch scope — droppable.

**Starting test baseline:** ~3,955 pytest + 680 Vitest (0 failures)
**Expected test delta:** +90 tests → ~4,045 pytest + 680 Vitest

---

## Session Breakdown

| Session | Scope | Score | Creates | Modifies | Key Risk |
|---------|-------|-------|---------|----------|----------|
| S1 | PatternParam + reference data hook | 8 Low | PatternParam in base.py | base.py, pattern_strategy.py | ABC signature change |
| S2 | Retrofit BF/FT + backtester grid | 12 Med | — | bull_flag.py, flat_top.py, vectorbt_pattern.py | Backward compat |
| S3 | Dip-and-Rip | 12 Med | dip_and_rip.py + configs | exit_management.yaml, registration | min_relative_volume in model |
| S4 | HOD Break | 12 Med | hod_break.py + configs | exit_management.yaml, registration | — |
| S5 | Gap-and-Go | 13 Med | gap_and_go.py + configs | exit_management.yaml, registration | min_gap_percent in model; first ref data user |
| S6a | ABCD core algorithm | 15 High | abcd.py | — | Swing detection complexity |
| S6b | ABCD config + wiring | 9 Low | abcd configs | exit_management.yaml, registration | Smoke backtest may find zero detections |
| S7 | Pre-Market High Break [STRETCH] | 13 Med | premarket_high_break.py + configs | exit_management.yaml, registration | PM candle timezone; min_premarket_volume in model |
| S8 | Integration verification | ~10 Med | integration tests | — | Cross-pattern issues |

**Dependency chain:** S1 → S2 → S3 → S4 → S5 → S6a → S6b → S7 → S8 (strictly serial)

---

## File Locks

After S1 completes:
- **LOCKED:** `strategies/patterns/base.py`, `strategies/pattern_strategy.py`

After S2 completes:
- **LOCKED:** `strategies/patterns/bull_flag.py`, `strategies/patterns/flat_top_breakout.py`, `backtest/vectorbt_pattern.py`

**Do NOT modify (entire sprint):**
`core/events.py`, `execution/order_manager.py`, `core/risk_manager.py`, `analytics/evaluation.py`, `intelligence/learning/` (entire dir), `intelligence/counterfactual.py`, `core/fill_model.py`, `ui/` (entire frontend), `api/` (no new endpoints), `ai/` (no AI changes)

---

## Issue Categories

**Category 1 — In-Session Bug:** Fix in same session. Note in close-out.
**Category 2 — Prior-Session Bug:** Do NOT fix in current session. Note in close-out. Run targeted fix prompt after current session's review. If nothing downstream depends on it, defer to post-sprint.
**Category 3 — Scope Gap:** Classify as small (handle in session), medium (add to next session), or large (escalate to this journal for triage).
**Category 4 — Feature Idea:** Log as DEF item. Do not implement.
**Category 5 — Spec Defect:** Escalate to this journal. May require spec amendment.

---

## Escalation Triggers

**Tier 3 (halt sprint, escalate to Claude.ai):**
1. ABCD swing detection false positive rate >50%
2. PatternParam backward compatibility break outside pattern/backtester modules
3. Pre-market candle availability failure
4. Universe filter field silently ignored requiring model redesign
5. Reference data hook initialization ordering issues

**Halt-and-Fix:**
1. Existing pattern behavior change after retrofit
2. PatternBacktester grid mismatch
3. Config parse failure
4. Strategy registration collision

**Warning-and-Continue:**
1. Smoke backtest zero signals
2. Low test count
3. ABCD complexity overrun

---

## Reserved Numbers

- **DEC-382 through DEC-395** (14 slots for Sprint 29 decisions)
- **DEF-109+** (deferred items discovered during implementation)
- **RSK-049+** (new risks)

---

## Session Tracking Template

When the developer pastes a close-out and review verdict, record:

```
### Session [N] — [Date]
**Verdict:** [CLEAR / CONCERNS / CONCERNS_RESOLVED / ESCALATE]
**Tests:** +[N] new (total: [N] pytest + [N] Vitest)
**Files created:** [list]
**Files modified:** [list]
**Issues found:** [list or "none"]
**DECs issued:** [list or "none"]
**DEFs logged:** [list or "none"]
**Carry-forward:** [items for next session or "none"]
**Notes:** [anything notable]
```

---

## Doc-Sync Prompt Generation

At sprint close (after S8), generate the doc-sync prompt from a fresh repo clone. The doc-sync must update:
- `docs/project-knowledge.md` — Active Strategies table (add 5 rows), test counts, sprint history row, build track queue
- `CLAUDE.md` — strategy count, PatternParam reference, new files
- `docs/sprint-history.md` — Sprint 29 entry
- `docs/decision-log.md` — DEC-382+ entries
- `docs/dec-index.md` — new DEC references
- `docs/strategies/` — 5 new STRATEGY_*.md spec sheets
- `docs/roadmap.md` — mark Sprint 29 complete
- DEF registry — mark DEF-088 resolved, add DEF-109/110 if created

Use surgical find-and-replace instructions, not narrative descriptions.
