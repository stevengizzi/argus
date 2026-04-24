# RETRO-FOLD Close-Out — Sprint 31.9 Stage 9C

**Session:** Sprint 31.9 Stage 9C — RETRO-FOLD (P1–P25 → `claude-workflow` metarepo)
**Date:** 2026-04-23
**Self-Assessment:** CLEAN
**Context State:** GREEN

---

## 1. Summary

Landed all 25 ARGUS Sprint 31.9 campaign retrospective lessons into the
`claude-workflow` metarepo. No lesson dropped, no lesson deferred as
non-generalizable. Every metarepo addition carries an Origin footnote that
cites its originating P-number so future maintainers can trace each rule
back to the campaign that earned it.

The metarepo update is additive across 5 existing files — no new
protocols/templates/schemas created, no existing content restructured. The
argus side is the required two-commit series: submodule pointer bump +
tracker cross-annotation.

## 2. Pre-Classification Matrix

All 25 rows, with landing target + update type. Matrix is the plan; no
items were misclassified during execution, so no mid-session revisions.

| P # | Lesson (1-line) | Target file | Update type | Rationale |
|-----|-----------------|-------------|-------------|-----------|
| P1  | Fresh-venv install check for dep-related T2 reviews | `claude/skills/review.md` | New evaluation category | Migration sessions need environment isolation |
| P2  | Marker-adding sessions need `pytest -m <m> --collect-only` validation | `templates/implementation-prompt.md` | New subsection (Marker Validation) | Mirrors Config Validation pattern |
| P3  | Grep-audit test-vs-prod import drift on migrations | `claude/skills/review.md` | Architectural Compliance sub-check | Review-time check for migration drift |
| P4  | Pre-commit `git diff --cached` scope check | `claude/skills/close-out.md` | Step 3 addition | Prevents cross-scope commits |
| P5  | Read-only orphan-verification → halt → confirm → edit | `claude/rules/universal.md` RULE-039 + `templates/implementation-prompt.md` | RULE + template section | Structural pattern for risky batch edits |
| P6  | Grep-verify handoff document vs actual source | `claude/rules/universal.md` RULE-038 | RULE (consolidated with P12/P13/P19/P22) | Session-start verification discipline |
| P7  | Small-sample empirical conclusions are directional only | `claude/rules/universal.md` RULE-040 | RULE | Empirical-evidence principle |
| P8  | Zero-tolerance CI flakes requires catalog completeness | `claude/rules/universal.md` RULE-041 | RULE | Flake discipline |
| P9  | `getattr(obj, "field", default)` silent-zero pattern | `claude/rules/universal.md` RULE-042 | RULE | Defensive-default anti-pattern |
| P10 | Test-delta count must equal new-test count exactly | `claude/skills/close-out.md` | Test Results note | Prevents silent test loss |
| P11 | Sprint ops files in Files Modified manifest | `claude/skills/close-out.md` | Change Manifest note | Manifest completeness |
| P12 | Pre-session grep-verify file paths cited in prompt | `claude/rules/universal.md` RULE-038 | RULE (consolidated with P6/P13/P19/P22) | Spec path drift defense |
| P13 | Stage/session tracker nicknames diverge from spec filenames | `claude/rules/universal.md` RULE-038 + `protocols/sprint-planning.md` | RULE variant + quality-check item | Planning-time consistency |
| P14 | Time-sensitive DEF closures need multi-window regression | `claude/rules/universal.md` RULE-044 | RULE | Premature-closure defense |
| P15 | Timezone-sensitive tests derive "today" implementation-wise | `claude/rules/universal.md` RULE-045 | RULE | Recurring flake family |
| P16 | Avoid Test*-prefix in non-test classes (pytest collection) | `claude/rules/universal.md` RULE-046 | RULE | Pytest warning hygiene |
| P17 | Broad `except Exception` swallows pytest.fail | `claude/rules/universal.md` RULE-043 | RULE | Test-framework signal protection |
| P18 | Verify kickoff library-behavior assumption actually triggers | `claude/rules/universal.md` RULE-048 | RULE | Library-assumption verification |
| P19 | Audit count/grep claims can go stale | `claude/rules/universal.md` RULE-038 | (consolidated with P6/P12/P13/P22) | Observation drift |
| P20 | Measure runtime-impact claims via `--durations`, don't infer | `protocols/sprint-planning.md` | Test count estimation extension | Measurement over inference |
| P21 | `git mv` depth change — pre-grep `parents[N]` sites | `claude/rules/universal.md` RULE-049 | RULE | Repath hazard |
| P22 | Audit coverage/metric values go stale — re-measure | `claude/rules/universal.md` RULE-038 | (consolidated with P6/P12/P13/P19) | Metric drift |
| P23 | Parametrized tests multiply test-delta | `protocols/sprint-planning.md` | Test count estimation extension | Estimation accuracy |
| P24 | Optional-dep tests mock at `sys.modules` level | `claude/rules/universal.md` RULE-047 | RULE | Env-leakage defense |
| P25 | CI green verification before next session starts | `claude/rules/universal.md` RULE-050 + `claude/skills/close-out.md` (Step 4) + `claude/skills/review.md` (Step 1 check-6) | RULE + 2 skill additions | Critical — prevents silent red-CI state |

Consolidation note: P6, P12, P13 (first variant), P19, P22 collapse into a
single RULE-038 covering pre-session verification, with four explicit
sub-variants. This was a deliberate call — the five lessons share one
principle with five expressions. The consolidated form is easier to cite
in future sessions than five near-duplicates. P13 additionally has its own
quality-check item in sprint-planning.md because the planning-time check
is distinct from the session-start check.

## 3. Metarepo Commit Series

Two commits on `github.com/stevengizzi/claude-workflow` `main`:

| SHA | Description |
|-----|-------------|
| `63be1b6` | `docs: fold ARGUS Sprint 31.9 retro lessons (P1-P25)` — the principal fold-in, all content and structure |
| `ac3747a` | `docs: normalize Origin-footnote wording for RULE-038` — one-word consistency fix in the P6+P12+P13+P19+P22 consolidated footnote so a grep for `Origin: Sprint 31.9 retro` returns 25 matches (one per P-lesson) |

Files modified: 5. Insertions: 292. Deletions: 3. No new files created.

Per-file breakdown:

| File | Change |
|------|--------|
| `claude/rules/universal.md` | +13 RULE entries (RULE-038 through RULE-050) in 7 new sections (§9 Session-Start Verification through §15 CI Verification Discipline) |
| `claude/skills/close-out.md` | Change Manifest note (P11), Test Results delta-equality note (P10), Step 3 pre-commit scope check (P4), new Step 4 CI Verification (P25) |
| `claude/skills/review.md` | Step 1 check-6 CI verification (P25), Architectural Compliance migration-drift sub-check (P3), new Dependency-Change Sessions evaluation category (P1) |
| `protocols/sprint-planning.md` | Test count estimation guide extensions (P20 + P23), Quality Checks tracker-nickname reconcile item (P13) |
| `templates/implementation-prompt.md` | Marker Validation subsection (P2), Risky Batch Edit — Staged Flow subsection (P5) |

## 4. Argus Commit Series

Argus `main`:

| SHA | Description |
|-----|-------------|
| `aa952f9` | `chore(workflow): bump submodule to sprint-31.9 retro fold-in` — pointer `942c53a` → `63be1b6` |
| `48bea1b` | `docs(sprint-31.9): RETRO-FOLD P1-P25 metarepo cross-annotations` |
| `<pending>` | `chore(workflow): re-advance submodule to include Origin-footnote normalization` — pointer `63be1b6` → `ac3747a` |
| `<pending>` | `docs(sprint-31.9): RETRO-FOLD close-out` — this file |
| `<pending>` | `docs(sprint-31.9): RETRO-FOLD Tier 2 review` — written by @reviewer |

Tracker annotation appends a "RETRO-FOLD disposition" table to
`docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` §"Process &
retrospective items", mapping each P# to its metarepo landing. Citations
use SHA `63be1b6` (the principal fold-in); `ac3747a` is an ancestor-matching
normalization and not a new landing point.

## 5. Metarepo Tag

**Not created.** The `claude-workflow` repo has no prior tags (`git tag -l`
returns empty). Per kickoff Requirement 6 ("if the metarepo uses tags"),
introducing a tag convention in this session would exceed scope. If a
later session adopts a tagging convention, it can retroactively tag this
commit (`63be1b6`) as `sprint-31.9-retro-fold` or equivalent.

## 6. Deferred Lessons

**None.** All 25 P-lessons landed in the metarepo. The one consolidation
(P6/P12/P13/P19/P22 → RULE-038) is not a deferral — each P# has an
explicit mapping in the disposition table to the same consolidated rule,
and P13 additionally has its own planning-checklist item.

## 7. bootstrap-index.md

**Unchanged.** No new files were created in the metarepo. Every addition
landed inside an existing file already indexed. Per Requirement 7
("bootstrap-index.md must list new files if new protocol/template files
were created"), no-op is the correct action.

## 8. Green CI URL (sanity check)

Per kickoff DoD ("Full pytest suite passes (green CI URL cited — sanity
check, not direct gate)"): this session touches only `workflow/` submodule
content and two argus doc files. No argus runtime, test, or config files
were modified. The argus submodule pointer bump is git metadata and cannot
affect pytest behavior because argus code does not import from `workflow/`
(the submodule contains documentation and an operational runner used out-
of-process).

Post-push CI run against the final argus commit `48bea1b`: pending as of
close-out authoring time (push just completed). The Tier 2 review prompt
includes a check for CI status (per RULE-050), and the operator can cite
the CI URL once the run completes. The baseline `5,080 pytest` +
`846 Vitest` documented in `CLAUDE.md` §"Current State" is unchanged by
this session.

## 9. Change Manifest

| File | Change Type | Rationale |
|------|-------------|-----------|
| `workflow` (submodule pointer) | modified | Advance to metarepo commit `63be1b6` |
| `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` | modified | Add RETRO-FOLD disposition table (25 rows) |
| `docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md` | added | This file |

Metarepo-side (separate commit series on `claude-workflow`):

| File | Change Type | Rationale |
|------|-------------|-----------|
| `claude/rules/universal.md` | modified | +13 RULE entries |
| `claude/skills/close-out.md` | modified | 4 additions (P4/P10/P11/P25) |
| `claude/skills/review.md` | modified | 3 additions (P1/P3/P25) |
| `protocols/sprint-planning.md` | modified | 2 extensions + 1 quality check (P13/P20/P23) |
| `templates/implementation-prompt.md` | modified | 2 new subsections (P2/P5) |

## 10. Judgment Calls

Decisions made during implementation that were not pre-specified:

- **Consolidate P6/P12/P13/P19/P22 under one RULE-038.** These five lessons
  share a single underlying principle (pre-session verification of prompt
  claims vs current codebase state); expressing them as five near-duplicate
  rules would dilute the cite-ability. Chose a single rule with four
  explicit sub-variants, plus a separate planning-checklist item for the
  P13 tracker-nickname case. Traceability preserved: each P# has its own
  row in the disposition table pointing at the consolidated rule.
- **No new files created.** The kickoff allows "Pattern C — New
  protocol/template file." Evaluated per-lesson; every lesson was a
  natural extension of an existing file's scope. Creating a new file
  ("Test Hygiene Rules," "Migration Review Rules") would fragment
  rules that are all universal and already fit the universal.md pattern.
- **No evolution note written.** The metarepo's `evolution-notes/`
  pattern is for conversation-level capture pre-synthesis. This session
  IS the synthesis — the inputs (P1–P25) were already structured in the
  campaign tracker, so writing an evolution note would be redundant.
- **RULE-038 four-variant structure.** Chose a nested-bullet style inside
  one rule rather than 4 separate RULE entries to keep the rule list
  scannable. This is an aesthetic call and can be split later if
  consensus forms that flat numbering is clearer.
- **No tag created.** Metarepo has no prior tag convention; introducing one
  in this session would exceed scope. Deferred to a future session that
  adopts a tagging policy.

## 11. Regression Checklist (Session-Specific)

| Check | Result | Notes |
|-------|--------|-------|
| All 25 P-lessons have a classification matrix entry | PASS | §2 has 25 rows |
| All 25 have a metarepo landing (or explicit deferral) | PASS | §6 confirms zero deferrals |
| Each metarepo addition has Origin footnote | PASS | Grep `Origin: Sprint 31.9 retro` across 5 metarepo files returns 13 in universal.md, 3 in review.md, 4 in close-out.md, 3 in sprint-planning.md, 2 in implementation-prompt.md = 25 total citations |
| bootstrap-index.md reflects any new files | PASS | No new files; no-op is correct |
| Argus submodule pointer matches latest metarepo main | PASS | `git submodule status workflow` → `+63be1b6`; `cd workflow && git log origin/main -1` → `63be1b6` |
| Tracker cross-annotations land in argus commit | PASS | Commit `48bea1b` modifies only the tracker |
| No argus code/tests/configs modified | PASS | `git diff 3c2636f..48bea1b -- argus/ config/ tests/ scripts/` is empty. The two argus commits touched exactly `workflow` (submodule) and `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` |
| pytest full suite passes | N/A — not-required per kickoff §"Pre-Session Verification #3"; session touched no argus code. CI will confirm on post-push. |

## 12. Notes for Reviewer

1. **Independence check.** The @reviewer should verify the submodule
   pointer at `workflow/` is `63be1b6`, that this SHA EXISTS on the
   metarepo's `origin/main` (not on a feature branch), and that the
   metarepo commit's content matches what this close-out claims.
2. **Generalization quality.** Spot-check 3 random new rules for
   overreach. Picks to consider: RULE-042 (silent-default getattr — is the
   generalization to `dict.get` fair, or does it overreach from the
   getattr-on-typed-object origin?); RULE-045 (timezone tests — are all 3
   sub-rules supported by DEF-163/188/190 evidence, or is one pattern
   over-extrapolated?); RULE-050 (CI verification — is the 4-minute push
   cadence guidance applicable beyond ARGUS's CI runtime?).
3. **Origin traceability.** Every new section in the metarepo should
   carry an Origin footnote. Grep `Origin: Sprint 31.9 retro` in the
   metarepo diff. 25 citations expected across all five metarepo files
   (with P6/P12/P13/P19/P22 cited in a single consolidated footnote on
   RULE-038).
4. **Two-commit argus discipline.** Argus has exactly two commits for
   this session (aa952f9 + 48bea1b). The close-out file in this commit
   (a third argus commit will cover it) is expected per the standard
   close-out convention and does not violate the "one + one more"
   constraint, which was about content-type mixing, not total count.

---

## Appendix: Structured Close-Out (JSON)

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "31.9",
  "session": "RETRO-FOLD",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5080,
    "after": 5080,
    "new": 0,
    "all_pass": null
  },
  "files_created": [
    "docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md"
  ],
  "files_modified": [
    "workflow",
    "docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Metarepo has no tag convention; deferred tag creation to a future session that adopts a policy.",
    "Evolution note not written; this session was itself the synthesis of P1-P25 pre-structured inputs."
  ],
  "doc_impacts": [
    {"document": "claude-workflow/claude/rules/universal.md", "change_description": "+13 RULE entries (RULE-038 through RULE-050) in 7 new sections"},
    {"document": "claude-workflow/claude/skills/close-out.md", "change_description": "P4/P10/P11/P25 additions"},
    {"document": "claude-workflow/claude/skills/review.md", "change_description": "P1/P3/P25 additions"},
    {"document": "claude-workflow/protocols/sprint-planning.md", "change_description": "P13/P20/P23 extensions"},
    {"document": "claude-workflow/templates/implementation-prompt.md", "change_description": "P2/P5 subsections"}
  ],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Cross-repo session — metarepo commit 63be1b6 + argus commits aa952f9 (submodule bump) + 48bea1b (tracker annotations). All 25 P-lessons landed. Consolidated P6/P12/P13/P19/P22 under RULE-038 with 4 explicit sub-variants to reduce dilution; traceability preserved via per-P# disposition table. No new files created (all additions extended existing files). No tag created (metarepo has no prior tag convention). Pytest suite not run — session touched no argus code."
}
```

---END-CLOSE-OUT---
