# SPRINT-CLOSE-B — Close-out

**Session:** SPRINT-CLOSE-B — Core project doc sync
**Kickoff:** [`SPRINT-CLOSE-B-kickoff.md`](SPRINT-CLOSE-B-kickoff.md)
**Date:** 2026-04-24
**Self-assessment:** CLEAN
**Safety tag:** `safe-during-trading` — documentation only

---

## 1. Files Modified (10 — 1 root + 9 docs)

| # | File | Summary of changes |
|---|---|---|
| 1 | `CLAUDE.md` | Active-sprint line rewritten with Sprint 31.9 SEAL marker + 5-way next-sprint operator decision; Tests line gains Sprint 31.9 net delta (+146 pytest, +20 Vitest) and notes DEF-205 RESOLVED by TEST-HYGIENE-01; new bullet capturing P26/P27 retrospective candidates queued for next campaign's RETRO-FOLD. |
| 2 | `docs/sprint-history.md` | New "Sprint 31.9 — Health & Hardening Campaign-Close" section inserted before the Sprint Statistics block (covers 11 named sessions + 3 paper-session debriefs, 19 DEFs closed, 6 opened, 0 new DECs, P26/P27 candidates, A1 → DEF-204 mechanism arc). Sprint Statistics block updated: 34→35 full sprints + new campaign-close phase, ~555+→~569+ sessions, 5,780→5,946 total tests, **383→384** total decisions (with rationale), ~53→~62 calendar days. |
| 3 | `docs/project-knowledge.md` | Header banner timestamp bumped to 2026-04-24 with Sprint 31.9 closure annotation; Tests line mirrored from CLAUDE.md (5,080 pytest baseline + DEF-205 resolution); Sprints-completed enumeration extended through 31.9; Active-sprint line mirrored from CLAUDE.md; Sprint History (Summary) table gains a Sprint 31.9 row (5080+866V, no new DECs). |
| 4 | `docs/architecture.md` | 3 Sprint 31.9 deltas anchored to existing sections: (a) §3.9 Phase 3 — `check_startup_position_invariant()` (DEF-199, IMPROMPTU-04) gates `OrderManager.reconstruct_from_broker()` on non-BUY broker side; (b) §3.4.8 — periodic 4-hour `_run_periodic_retention()` task (DEF-197, IMPROMPTU-10) on `EvaluationEventStore`, addresses multi-day-session retention gap; (c) §3.7 Order Manager — NOTE block on DEF-204 mechanism (bracket children without `ocaGroup`, side-blind reconciliation), fix scope routed to `post-31.9-reconciliation-drift`. |
| 5 | `docs/decision-log.md` | New "Sprint 31.9 — Campaign-Close" section inserted after DEC-384 enumerating per-session established-pattern rationale (IMPROMPTU-04 followed DEC-369/370; IMPROMPTU-CI followed `_listener_task` cancel-await idiom; IMPROMPTU-05 standard `uv pip compile`; etc.). DEC range allocation: none. DEFs opened/closed listed. "Last updated" footer bumped. |
| 6 | `docs/dec-index.md` | New "Sprint 31.9 — Campaign-Close" section inserted after Sprint 31.85 entry (parallel to existing Sprint 31.8 format). Header still says "384 decisions" — unchanged because Sprint 31.9 added zero DECs. |
| 7 | `docs/roadmap.md` | Pre-existing "Post-Sprint-31.9 Component Ownership" subsection rewritten as a 5-section block: (a) Sprint 31.9 closure annotation with summary statistics + final HEAD `0a25592`; (b) `post-31.9-reconciliation-drift` (CRITICAL safety, 3-session adversarial-review-required horizon for DEF-204); (c) `post-31.9-component-ownership` with entry-criteria-satisfied marker; (d) `post-31.9-reconnect-recovery-and-rejectionstage`; (e) `post-31.9-alpaca-retirement`. Operator-decided ordering against Sprint 31B noted. |
| 8 | `docs/sprint-campaign.md` | New "Sprint 31.9 — Campaign-Close Pattern Evolution" section inserted before §14 Quick Reference. Documents the campaign-close model: `safe-during-trading` discipline, 3 paper-session debriefs as evidence-gathering, IMPROMPTU-CI as a CI-restoration session pattern, mechanism-signature validation. References P26/P27 captures. |
| 9 | `docs/project-bible.md` | Strategy-roster mention bumped from "As of Sprint 31.85" → "As of Sprint 31.9 (post-campaign-close)" with annotation that Sprint 31.9 did not change the roster but hardened two safety surfaces (DEF-199 fixed + validated; DEF-204 mechanism identified). |
| 10 | `docs/risk-register.md` | Two new RSK entries appended after RSK-051: **RSK-DEF-204** (Critical — upstream cascade mechanism, mitigation in effect via daily `ibkr_close_all_positions.py` + IMPROMPTU-04 EOD refusal + startup invariant; fix routed to `post-31.9-reconciliation-drift`) and **RSK-DEF-203** (Low/MONITOR — `max_concurrent_positions` WARNING-spam throttling gap, queued for next risk_manager.py touch). |

## 2. Files Explicitly NOT Modified

Verified all scope guards via `git diff`:

```
$ git diff docs/process-evolution.md      # FROZEN per Apr 21 freeze marker
(empty — preserved)
$ git diff docs/sprints/sprint-31.9/      # sealed by SPRINT-CLOSE-A
(empty)
$ git diff docs/sprints/post-31.9-*/      # DISCOVERY stubs from SPRINT-CLOSE-A
(empty)
$ git diff argus/ tests/ config/          # no runtime, test, or config changes
(empty)
$ git submodule status workflow/          # workflow submodule pointer unchanged
(unchanged)
```

`process-evolution.md` FROZEN marker confirmed at session start (line 1: `# ARGUS — Process Evolution [FROZEN]`).

## 3. Statistics Cross-Validation

All numbers in updated docs trace back to `SPRINT-31.9-SUMMARY.md` (canonical) or were independently re-derived per the kickoff's Pre-Session Verification §Final Statistics:

| Statistic | Source | Cited in |
|---|---|---|
| Final HEAD `0a25592` | git log | sprint-history.md, roadmap.md |
| Pytest 5,080 | SUMMARY.md §Campaign Test Delta | CLAUDE.md, project-knowledge.md, sprint-history.md |
| Vitest 866 | SUMMARY.md §Campaign Test Delta | CLAUDE.md, project-knowledge.md, sprint-history.md |
| Net delta +146 pytest / +20 Vitest | SUMMARY.md table | CLAUDE.md, project-knowledge.md, sprint-history.md |
| 19 DEFs closed (campaign-close phase) | SUMMARY.md §DEF Register Delta + SPRINT-CLOSE-A-closeout §1 | sprint-history.md (with explicit closure-list note explaining the kickoff's "24" miscount) |
| 6 DEFs opened (DEF-201–206) | SUMMARY.md §DEF Register Delta | sprint-history.md, decision-log.md |
| 0 new DECs | SUMMARY.md §DEC Delta | decision-log.md, dec-index.md, sprint-history.md |
| 11 named sessions + 3 paper-session debriefs | SUMMARY.md §Session Index | sprint-history.md, sprint-campaign.md |
| Calendar 3 days (Apr 22 – Apr 24) | `git log --since=2026-04-22 --until=2026-04-25` first/last | sprint-history.md, sprint-campaign.md, decision-log.md |
| 56 campaign-close commits since IMPROMPTU-04 | `git log 0623801..HEAD --oneline | wc -l` | sprint-history.md |
| Metarepo commits 3 (`63be1b6` + `ac3747a` + `edf69a5`) | SUMMARY.md §Campaign Lessons | sprint-history.md |
| Submodule pointer advances 3 (`aa952f9` → `204462e` → `ec7e795`) | SUMMARY.md §Campaign Lessons | sprint-history.md |

**Closure-list reconciliation note (preserved in sprint-history.md):** the kickoff's Requirement 2a literal text listed 24 closed DEFs. Per SPRINT-CLOSE-A-closeout's exact-grep verification (CLAUDE.md), 5 of those (DEF-152/153/154/158/161) were closed by earlier campaign sessions (Sprints 31.75 / 31.8 / 31.85) before IMPROMPTU-04 anchored the campaign-close window. Authoritative count is 19. SPRINT-CLOSE-B used the SUMMARY-canonical count of 19 and added an explicit reconciliation note in sprint-history.md to prevent the discrepancy from re-surfacing in future doc syncs. This is consistent with the kickoff's directive: "Pull these from `SPRINT-31.9-SUMMARY.md`" + "verify exact list from SUMMARY."

## 4. Total-Decisions Correction (383 → 384)

`docs/sprint-history.md` Sprint Statistics block previously read `383 (DEC-001 through DEC-383; no new DECs in Sprints 29.5, 32, ...)`. Per the kickoff's Pre-Session Verification §Final Statistics:

> Total decisions count: should be 384 (DEC-001 through DEC-384, last entry is DEC-384 added in pre-31.9 FIX-01 audit).

Verified at session start: `tail -10 docs/decision-log.md` showed `*Next DEC: 385*` confirming DEC-384 is the highest assigned. Pre-existing Sprint 31.85 closeout did not catch the discrepancy because that block was only edited on Apr 20 to add the Sprint 31.85 row; the prior `383` count was carried forward verbatim.

The corrected line now reads:

```
**Total decisions:** 384 (DEC-001 through DEC-384; no new DECs in Sprints 29.5, 32, 32.5, 32.75, 32.8, 32.9, 32.95, Apr 3 hotfix, 31A, 31A.5, 31A.75, 31.5, DEF-151 fix, Sweep Impromptu, 31.8 impromptus, 31.85 Parquet consolidation, or Sprint 31.9 campaign-close — campaign followed established patterns)
```

`dec-index.md` header was already at 384 — left unchanged.

## 5. DEF-204 RSK Entry — Confirmed Present

`grep -c "RSK-DEF-204" docs/risk-register.md` → 1. Format follows existing RSK entry pattern (Field/Value table with Date Identified, Category, Severity, Likelihood, Description, Mitigation in effect, Owner, Status, Cross-references). Mitigation language matches the kickoff Requirement 10a:

- Operator runs `scripts/ibkr_close_all_positions.py` daily at session close.
- IMPROMPTU-04's A1 fix (DEF-199) refuses to amplify these at EOD (1.00× signature) and escalates to operator with CRITICAL alert.
- `ArgusSystem._startup_flatten_disabled` invariant gates `OrderManager.reconstruct_from_broker()` on non-BUY broker side.

DEF-203 RSK entry (`RSK-DEF-203`) also appended per kickoff Requirement 10b — Low priority, MONITOR-only, Owner: next `argus/core/risk_manager.py` touch.

## 6. Final Green CI URL

Pending — populated after commit + push. To be backfilled into this closeout per RULE-050 once the SPRINT-CLOSE-B commit's CI run reports green. (SPRINT-CLOSE-A established this backfill pattern; SPRINT-CLOSE-B follows it.)

## 7. Closing Statement

Sprint 31.9 is now SEALED at all three levels:

- **Campaign-internal artifacts** sealed by SPRINT-CLOSE-A (commit `e095a39`): `SPRINT-31.9-SUMMARY.md` canonical, RUNNING-REGISTER + CAMPAIGN-COMPLETENESS-TRACKER + CAMPAIGN-CLOSE-PLAN with SEAL/ARCHIVE banners, 4 post-31.9 DISCOVERY stubs created.
- **Project-wide doc sync** sealed by SPRINT-CLOSE-B (this commit): 9 core docs + CLAUDE.md updated to reflect Sprint 31.9's outcomes, P26/P27 captured, 384-decisions count corrected, post-31.9-reconciliation-drift horizon visible in roadmap.
- **CI** to be backfilled with green-run URL on next push.

Build-track unblocked. Sprint 31.9 closure was the entry-criterion for `post-31.9-component-ownership`; that gate is now satisfied. Operator decides next-sprint priority across {`post-31.9-reconciliation-drift` (recommended first per safety priority — DEF-204 CRITICAL), `post-31.9-component-ownership`, `post-31.9-reconnect-recovery-and-rejectionstage`, `post-31.9-alpaca-retirement`, Sprint 31B Research Console / Variant Factory}. Operational mitigation in effect until DEF-204 lands: operator runs `scripts/ibkr_close_all_positions.py` daily at session close.

## 8. Next-Session Note

SPRINT-CLOSE-B is the **final session** of Sprint 31.9. Operator's next decision is which post-31.9 horizon (or Sprint 31B) runs first. The kickoff explicitly recommended `post-31.9-reconciliation-drift` first per safety priority — DEF-204's CRITICAL safety classification + concrete 3-session fix plan documented in IMPROMPTU-11 makes it the highest-leverage next sprint. Sprint 31B (Research Console / Variant Factory) is non-safety-critical and can wait.

The next campaign's RETRO-FOLD will pick up P26 (mechanism-signature-vs-symptom-aggregate validation principle) and P27 (CI-discipline drift when red is "known cosmetic"), both queued in `SPRINT-31.9-SUMMARY.md` §Campaign Lessons.

---

**Self-assessment:** CLEAN. All 10 in-scope files updated; all scope guards (process-evolution.md, sprint-31.9/, post-31.9-*/, argus/, tests/, config/, workflow/) verified empty in `git diff`. All statistics cross-validated against SPRINT-31.9-SUMMARY.md. Total-decisions corrected from 383 to 384 with rationale in close-out §4. DEF-204 + DEF-203 RSK entries present.
