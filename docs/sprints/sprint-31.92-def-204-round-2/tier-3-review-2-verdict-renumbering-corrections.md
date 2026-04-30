# Tier 3 Review #2 Verdict — Numbering Corrections

**Date:** 2026-04-30
**Reason:** The Tier 3 Review #2 verdict (the ESCALATE-A1 / S1a-INCONCLUSIVE verdict, authored 2026-04-30 and originally filed at `tier-3-review-1-verdict.md` by an operator-side path error) assigned DEF numbers 213–218 and DEC numbers 389/390 for sprint-internal and cross-sprint follow-ups. Post-verdict cross-checks against `CLAUDE.md` and `docs/dec-index.md` confirmed all DEF numbers and the verdict-side DEC-389 were already assigned. Per RULE-015 (verify next number before assignment) and the Numbering Hygiene rule in `doc-updates.md`, Sprint 31.92's DEFs and DECs are renumbered.

The verdict artifact itself is NOT modified after authoring — verdict files are point-in-time historical records. The renumbered numbers are applied throughout `tier-3-review-2-verdict.md` (the new canonical landing path) and all mid-sync files; this corrections document is the canonical mapping that the sprint-close doc-sync (and all subsequent references) consume.

## Review numbering correction

The Phase A Tier 3 review (authored 2026-04-29 in a Claude.ai conversation; landed at `tier-3-review-1-verdict.md` via commit `26875fe`) is the canonical **Tier 3 Review #1** for Sprint 31.92 per `protocols/tier-3-review.md`'s naming rule (*"where N is the review iteration within this sprint, starting at 1"*). The Phase A review's trigger was Outcome C — independent design review during Phase A re-entry after Round 1 + Round 2 each caught Critical findings of the same primitive-semantics class.

The ESCALATE-A1 review (authored 2026-04-30; trigger: A-class halt A1 fired on S1a spike returning `status: INCONCLUSIVE`) was originally filed at `tier-3-review-1-verdict.md` by an operator-side path error — the new verdict text was written into the existing Review #1 file path, overwriting the Phase A Tier 3 verdict's content in the working tree. The discovery occurred mid-sync when Claude Code inspected the verdict file's commit history (single commit `26875fe`, content matching Phase A) versus its working-tree content (ESCALATE-A1).

**Surgery applied at commit (this commit):**
- `tier-3-review-1-verdict.md` restored from commit `26875fe` to its original Phase A Tier 3 content. No history rewrite required — the working-tree modification was reverted via `git checkout 26875fe -- <path>`.
- ESCALATE-A1 verdict text re-filed at the new canonical path `tier-3-review-2-verdict.md` with title heading and `Verdict artifact landing` line corrected to reflect the Review #2 numbering.
- This corrections file (originally `tier-3-review-1-verdict-renumbering-corrections.md`) renamed to `tier-3-review-2-verdict-renumbering-corrections.md` via `git mv`; the doc-sync manifest similarly renamed.

| Original (path-error) | Corrected (canonical) | Subject |
|---|---|---|
| `tier-3-review-1-verdict.md` working-tree content (ESCALATE-A1) | `tier-3-review-2-verdict.md` | The 2026-04-30 ESCALATE-A1 / S1a-INCONCLUSIVE Tier 3 review |
| `tier-3-review-1-verdict.md` committed content (Phase A — `26875fe`) | `tier-3-review-1-verdict.md` (restored) | The 2026-04-29 Phase A Tier 3 review (Outcome C) |
| `tier-3-review-1-verdict-renumbering-corrections.md` | `tier-3-review-2-verdict-renumbering-corrections.md` | This file — DEF + DEC + RSK + path corrections for Tier 3 Review #2 |
| `tier-3-review-1-doc-sync-manifest.md` | `tier-3-review-2-doc-sync-manifest.md` | The mid-sprint doc-sync manifest for Tier 3 Review #2 |

The path-error origin: the operator-facing handoff for the 2026-04-30 ESCALATE-A1 review used the placeholder filename `tier-3-review-1-verdict.md` without checking that the slot was already occupied by the Phase A Tier 3 verdict committed at `26875fe`. Standard protocol is "where N is the review iteration within this sprint, starting at 1" — applied correctly, the 2026-04-30 review is iteration #2.

## DEF Renumbering Map

| Verdict-side | CLAUDE.md-side | Title | Sprint home |
|---|---|---|---|
| DEF-213 | DEF-236 | Mode A propagation measurement bug (Cat A.1) | 31.92 (sprint-internal) |
| DEF-214 | DEF-237 | Side-blind `_flatten()` in S1a harness (Cat A.2) | 31.92 (sprint-internal) |
| DEF-215 | DEF-238 | Axis (ii)/(iv) instrumentation no fail-loud (Cat B.3) | 31.92 (sprint-internal) |
| DEF-216 | DEF-239 | `ibkr_close_all_positions.py` audit | 31.92 (sprint-internal) — RESOLVED-VERIFIED-NO-FIX 2026-04-30 |
| DEF-217 | DEF-240 | S1b sister-spike same bug class | 31.92 (sprint-internal) |
| DEF-218 | DEF-241 | Sprint 31.94 reconnect-recovery dependency on informational axes | 31.94 (cross-sprint) |

## DEC Renumbering Map

| Verdict-side | dec-index.md-side | Title | Sprint home |
|---|---|---|---|
| DEC-389 | DEC-390 | S1a Decision-Rule Amendment (rule-amendment subset; axis (i) binds; axes (ii)/(iv) informational; axis (iii) deleted) | 31.92 (sprint-close materialization, Pattern B) |
| DEC-390 | DEC-391 | Sprint-close 4-layer DEF-204 architectural closure (DEC-391 builds on DEC-390) | 31.92 (sprint-close materialization, Pattern B) |

**Collision origin:** verdict-side `DEC-389` was already materialized at Sprint 31.915 sprint-close on 2026-04-28 for `Config-Driven evaluation.db Retention` (`docs/dec-index.md:522`). The Tier 3 reviewer (fresh Claude.ai conversation) extrapolated DEC numbers from the sprint-handoff prompt's anticipated ceiling without grep-verifying against the live `dec-index.md`. Sprint 31.915 sealed two days before the verdict was authored and consumed DEC-389 in the interim. The collision was resolved at this surgery commit by renumbering verdict-side DEC-389 → DEC-390 (next available) and verdict-side DEC-390 → DEC-391.

## RSK Renaming Map

| Verdict-side | risk-register.md-side | Title |
|---|---|---|
| RSK-DEC389-31.94-COUPLING | RSK-DEC390-31.94-COUPLING | DEC-390 amended-rule coupling to Sprint 31.94 reconnect-recovery |
| RSK-MODE-D-CONTAMINATION-RECURRENCE | (unchanged) | Mode D contamination recurrence (spike v2 gate) |
| RSK-VERDICT-VS-FAI-3-COMPATIBILITY | (unchanged) | DEC-390 verdict vs FAI #3 compatibility caveat |

The two unchanged RSKs are name-stable (no DEC number embedded in the slug). RSK-DEC389-31.94-COUPLING is renamed RSK-DEC390-31.94-COUPLING to track the rule amendment's renumbering.

## Reading guide for future readers

- The verdict artifact (`tier-3-review-2-verdict.md`) uses the renumbered numbers throughout (DEF-236–241, DEC-390 for rule amendment, DEC-391 for 4-layer closure forward reference, RSK-DEC390-31.94-COUPLING). The verdict body's narrative was renumbered at this surgery commit; the original verdict-side numbers are preserved in the verdict's "Verdict-side numbering provenance" notes for traceability.
- CLAUDE.md DEF table, all impl prompts, all close-outs from Unit 2 onward use the renumbered numbers.
- DEC-390's text (when materialized at sprint-close) references the renumbered numbers.
- The Sprint 31.92 work-journal-closeout doc-sync handoff at sprint-end uses the renumbered numbers.

## Process-evolution lesson

Two failure modes surfaced together at this surgery:

**(a) DEF/DEC numbering drift.** The Tier 3 reviewer (fresh Claude.ai conversation) had no visibility into CLAUDE.md's DEF table or `dec-index.md`'s DEC ceiling when assigning numbers; the sprint handoff prompt only enumerated numbers ANTICIPATED for Sprint 31.92 (highest DEF: DEF-212; highest DEC: DEC-388). Tier 3 reasonably extrapolated upward from there. Sprint 31.91 had sealed two days earlier and filed DEF-213 through at least DEF-235; Sprint 31.915 (single-session impromptu) consumed DEC-389 the day before the verdict was authored. The Work Journal failed to cross-check verdict-assigned numbers against the live tables before pinning them into the running register.

**(b) Review-iteration path collision.** The ESCALATE-A1 verdict was filed at `tier-3-review-1-verdict.md` without checking that the slot was already occupied by the Phase A Tier 3 verdict committed at `26875fe`. The protocol's "where N is the review iteration within this sprint, starting at 1" rule was correct — but the operator-facing handoff used the placeholder filename without iterating N.

**Recommendation for next sprint's Tier 3 briefing prompt:** include in the briefing prompt's sprint-context block (1) current "Highest existing DEF number" via grep against CLAUDE.md, (2) current "Highest existing DEC number" via grep against `docs/dec-index.md`, AND (3) "Existing Tier 3 verdict iterations in this sprint" via `ls docs/sprints/<sprint>/tier-3-review-*-verdict.md`. The reviewer can then extrapolate from the live ceiling rather than the sprint-handoff anticipated ceiling, and the operator-facing handoff names the next iteration explicitly.
