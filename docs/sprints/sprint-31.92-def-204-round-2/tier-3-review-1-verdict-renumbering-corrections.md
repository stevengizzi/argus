# Tier 3 Review #1 Verdict — DEF Renumbering Corrections

**Date:** 2026-04-30
**Reason:** The Tier 3 Review #1 verdict (`tier-3-review-1-verdict.md`, 2026-04-30) assigned DEF numbers 213–218 for sprint-internal and cross-sprint follow-ups. Post-verdict cross-check against `CLAUDE.md` confirmed all six numbers were already assigned to Sprint 31.91 follow-ups (highest existing: DEF-235). Per RULE-015 (verify next number before assignment) and the Numbering Hygiene rule in `doc-updates.md`, Sprint 31.92's DEFs are renumbered starting at DEF-236.

The verdict artifact itself is NOT modified — verdict files are point-in-time historical records. This corrections file is the canonical mapping that the mid-sprint doc-sync (and all subsequent references) consume.

## Renumbering Map

| Verdict-side | CLAUDE.md-side | Title | Sprint home |
|---|---|---|---|
| DEF-213 | DEF-236 | Mode A propagation measurement bug (Cat A.1) | 31.92 (sprint-internal) |
| DEF-214 | DEF-237 | Side-blind `_flatten()` in S1a harness (Cat A.2) | 31.92 (sprint-internal) |
| DEF-215 | DEF-238 | Axis (ii)/(iv) instrumentation no fail-loud (Cat B.3) | 31.92 (sprint-internal) |
| DEF-216 | DEF-239 | `ibkr_close_all_positions.py` audit | 31.92 (sprint-internal) — RESOLVED-VERIFIED-NO-FIX 2026-04-30 |
| DEF-217 | DEF-240 | S1b sister-spike same bug class | 31.92 (sprint-internal) |
| DEF-218 | DEF-241 | Sprint 31.94 reconnect-recovery dependency on informational axes | 31.94 (cross-sprint) |

## Reading guide for future readers

- The verdict artifact (`tier-3-review-1-verdict.md`) uses the verdict-side numbers throughout.
- CLAUDE.md DEF table, all impl prompts, all close-outs from Unit 2 onward use the CLAUDE.md-side numbers.
- DEC-389's text (when materialized at sprint-close) references the CLAUDE.md-side numbers.
- The Sprint 31.92 work-journal-closeout doc-sync handoff at sprint-end uses the CLAUDE.md-side numbers.

## Process-evolution lesson

The Tier 3 reviewer (fresh Claude.ai conversation) had no visibility into CLAUDE.md's DEF table when assigning numbers; the sprint handoff prompt only enumerated DEF numbers ANTICIPATED for Sprint 31.92 (highest: DEF-212). Tier 3 reasonably extrapolated upward from there. Sprint 31.91 had sealed two days earlier and filed DEF-213 through at least DEF-235 in the same range. The Work Journal failed to cross-check verdict-assigned DEF numbers against the live CLAUDE.md table before pinning them into the running register; collision was discovered only when Claude Code touched the DEF-216 row at Unit 2 setup.

Recommendation for next sprint's Tier 3 briefing prompt: include current "Highest existing DEF number" in the briefing prompt's sprint-context block so the reviewer can extrapolate from the live ceiling rather than the sprint-handoff anticipated ceiling.
