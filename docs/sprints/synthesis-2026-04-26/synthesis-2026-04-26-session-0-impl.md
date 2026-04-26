# Sprint synthesis-2026-04-26, Session 0: Argus-Side Input-Set Backfill

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (RULE-001 through RULE-053 — the latter three land later in Sprint 1, but RULE-001 through RULE-050 are already in effect) applies regardless of whether any specific rule is referenced inline below.

   *Note: this Pre-Flight step is the keystone wiring that Session 1 will land in `templates/implementation-prompt.md`. For Session 0, you're applying it manually before that wiring exists in the metarepo template — same effect.*

2. Read these files to load context:
   - `argus/docs/sprints/synthesis-2026-04-26/sprint-spec.md`
   - `argus/docs/sprints/synthesis-2026-04-26/spec-by-contradiction.md`
   - `argus/docs/sprints/synthesis-2026-04-26/regression-checklist.md`
   - `argus/docs/sprints/synthesis-2026-04-26/escalation-criteria.md`
   - `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` (the file you'll be modifying — read fully to find the §Campaign Lessons section and understand existing P26 + P27 entries)

3. Verify you are on the correct branch: `main` (in argus repo).

4. Verify git working tree is clean: `git status` returns no uncommitted changes.

5. Confirm session ordering: this is Session 0 of synthesis-2026-04-26. No prior sessions. Sessions 1+ depend on this session committing first.

## Objective

Append two retrospective candidates (P28 + P29) to `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` §Campaign Lessons so the synthesis input set referenced by Sessions 1–6 (metarepo work) is durable. Optionally add a `## Rules` section to `argus/CLAUDE.md` if not already present.

## Requirements

### Required: Append P28 + P29 to SPRINT-31.9-SUMMARY.md

In `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` §Campaign Lessons, after the existing P27 candidate entry and before the §Session Index section, append the following two entries (preserving the exact format used by P26 + P27):

```markdown
- **P28 candidate:** *Session implementers should treat kickoff statistics as
  directional input requiring grep-verification, not ground truth. Closeouts
  should explicitly disclose any kickoff-vs-actual discrepancies with attribution
  rather than quietly conform to the kickoff's stated numbers.* Origin:
  SPRINT-CLOSE-A-closeout's correction of the kickoff's "24 closed DEFs" figure
  to the grep-verified 19 (5 of the 24 — DEF-152/153/154/158/161 — were closed
  by earlier campaign sessions before IMPROMPTU-04 anchored the campaign-close
  window). The implementer flagged the discrepancy in the closeout via RULE-038
  grep-verify rather than silently propagating the wrong number to
  SPRINT-31.9-SUMMARY.md. Generalization: this extends RULE-038's grep-verify
  discipline into a closeout-level disclosure practice — distinct from RULE-038
  itself because it covers what to do when a discrepancy is found (the closeout
  reporting protocol), not just the verification step. To capture in next
  campaign's RETRO-FOLD scope.

- **P29 candidate:** *Architecturally-sealed documents (e.g.,
  `process-evolution.md` FROZEN markers, sealed sprint folders, ARCHIVE-banner
  files) require defensive verification at session start, not just trust in the
  kickoff's instructions to avoid them.* Origin: SPRINT-CLOSE-B's pre-flight
  check #5 explicitly grep-verified the FROZEN marker still existed before
  allowing the session to proceed. If a future operator removes the freeze
  marker, the kickoff's avoidance instruction would silently bypass an important
  architectural decision. Generalization: any session that operates near
  sealed/frozen documents should encode the seal as a verifiable assertion at
  session start. The verification protects against the seal being silently
  removed elsewhere. To capture in next campaign's RETRO-FOLD scope.
```

**Insertion point:** Locate the end of the existing P27 candidate entry. Insert the P28 + P29 blocks immediately after it. Preserve the bullet style and indentation of P26 + P27 verbatim.

**Verification commands** (run after the edit):
```bash
grep -c "^- \*\*P2[6789] candidate:\*\*" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md
# Expected: 4

grep -A2 "^- \*\*P28 candidate" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md | head -3
grep -A2 "^- \*\*P29 candidate" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md | head -3
# Expected: both return matches with the canonical wording

# Verify P26 + P27 unchanged (byte-identical to pre-sprint state)
git diff HEAD argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md | grep "^-" | grep -v "^---" | wc -l
# Expected: 0 (no deletions; only additions)
```

### Optional: Add `## Rules` section to argus/CLAUDE.md

First check whether the section already exists:
```bash
grep -i "^## Rules$\|^## Rule\b" argus/CLAUDE.md | head -3
```

If a `## Rules` section is present (any reasonable variant): skip this requirement; document in close-out as "Already present, skipped per Pre-Flight check."

If absent: insert the following section in `argus/CLAUDE.md`. Choose an insertion point that fits the existing structure (a natural location is after a "Communication Style" or "Workflow" section, or at the end of the file before any deferred-items table — operator's CLAUDE.md style varies by project, so use judgment).

```markdown
## Rules

This project follows the universal rules in `.claude/rules/universal.md` (auto-loaded by Claude Code at session start per the implementation-prompt template's Pre-Flight step). Project-specific rules live alongside in `.claude/rules/` (e.g., `backtesting.md` for ARGUS-specific patterns).

The keystone Pre-Flight wiring (in `templates/implementation-prompt.md` and `templates/review-prompt.md`) ensures every implementation and review session reads `universal.md` deterministically — universal RULEs apply regardless of whether they're inline-referenced in any specific prompt.
```

If the section is absent and you've added it, document in close-out as "Added; insertion point: <line number>."

## Constraints

- **Do NOT modify** any path under `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`. The kickoff hard constraint is non-overridable; ANY commit to those paths triggers escalation criterion A1.
- **Do NOT modify** the existing P26 or P27 entries in `SPRINT-31.9-SUMMARY.md`. They are byte-frozen; preserve verbatim. Append-only.
- **Do NOT reformat** the §Campaign Lessons section beyond inserting P28 + P29.
- **Do NOT modify** any other files in `argus/docs/sprints/sprint-31.9/` (the entire sprint-31.9 folder is sealed by SPRINT-CLOSE per the pre-existing operational record; only SPRINT-31.9-SUMMARY.md is the explicitly permitted target for this backfill).
- **Do NOT touch** any metarepo files (`argus/workflow/`). Metarepo work is Sessions 1–6.
- **Do NOT introduce** any new top-level files in argus.
- **Do NOT modify** ARGUS's CLAUDE.md beyond the optional `## Rules` section addition. If you find drift in CLAUDE.md (typos, stale references), log as a deferred observation in close-out — do not fix.

## Test Targets

This session creates no executable code, no tests, and no Python. The "test" is the verification commands listed under Requirements.

- **Existing tests:** unaffected (no code touched).
- **New tests:** none.
- **Verification:** run the two grep commands listed under "Required" — both must return expected results. Capture the outputs in the close-out report.

## Definition of Done

- [ ] P28 + P29 entries appended to `SPRINT-31.9-SUMMARY.md` §Campaign Lessons
- [ ] Existing P26 + P27 entries preserved byte-identical (verified via diff)
- [ ] §Campaign Lessons total candidate count is exactly 4 (verified via grep -c)
- [ ] *Optional:* `## Rules` section in `argus/CLAUDE.md` either confirmed-present or added (per branching above)
- [ ] No files modified outside the explicitly-permitted set (`SPRINT-31.9-SUMMARY.md` + optionally `argus/CLAUDE.md`)
- [ ] Close-out report written to file (see Close-Out section below)
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| ARGUS runtime untouched | `git diff HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/` returns empty |
| Sprint-31.9 sealed-folder respected | `git diff HEAD --name-only argus/docs/sprints/sprint-31.9/` matches ONLY `SPRINT-31.9-SUMMARY.md` |
| Existing P26 + P27 unchanged | `git diff HEAD argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` shows only insertion lines (no `<` deletion lines outside whitespace context) |
| Workflow metarepo untouched | `git diff HEAD --name-only -- argus/workflow/` returns empty |

## Close-Out

After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include the structured JSON appendix at the end, fenced with ` ```json:structured-closeout `. See the close-out skill for the full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`argus/docs/sprints/synthesis-2026-04-26/session-0-closeout.md`

Do NOT just print the report. Create the file, write the full report (including the structured JSON appendix), and commit it as part of the session's commit series.

**Commit pattern:**
```bash
git add argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md
git add argus/CLAUDE.md  # only if optional Rules section was added
git commit -m "docs(synthesis-2026-04-26 S0): backfill P28+P29 in SPRINT-31.9-SUMMARY"

# Then commit the close-out separately
git add argus/docs/sprints/synthesis-2026-04-26/session-0-closeout.md
git commit -m "docs(synthesis-2026-04-26 S0): close-out report"

git push
```

Wait for CI to complete on the final commit; record the green CI URL in the close-out (per RULE-050 + close-out.md Step 4).

## Tier 2 Review (Mandatory — @reviewer Subagent)

After the close-out is written to file and committed, invoke the @reviewer subagent to perform Tier 2 review within this same session.

Provide the @reviewer with:

1. The review context file: `argus/docs/sprints/synthesis-2026-04-26/review-context.md`
2. The close-out report path: `argus/docs/sprints/synthesis-2026-04-26/session-0-closeout.md`
3. The diff range: `git diff HEAD~2..HEAD` (covers the SUMMARY backfill commit + the close-out commit)
4. Files that should NOT have been modified: anything outside `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` and optionally `argus/CLAUDE.md`

The @reviewer will produce its review report (with structured JSON verdict) and write it to:
`argus/docs/sprints/synthesis-2026-04-26/session-0-review.md`

The @reviewer is a fresh-context read-only subagent; it doesn't inherit this session's context. It reads the review-context.md to know the sprint contract.

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session, append a "Post-Review Fixes" section to the close-out report, and append a "Post-Review Resolution" annotation to the review report. Update the structured verdict JSON: `"verdict": "CONCERNS"` → `"verdict": "CONCERNS_RESOLVED"`. Commit the updated files.

If the @reviewer reports CLEAR or ESCALATE, skip this section entirely.

## Session-Specific Review Focus (for @reviewer)

1. **P26 + P27 byte-frozen:** verify these entries are unchanged via diff against pre-session HEAD.
2. **P28 + P29 wording matches the spec:** the wording in this session's diff should match the canonical statements in `argus/docs/sprints/synthesis-2026-04-26/sprint-spec.md` — minor formatting variation (line wrapping) is acceptable; semantic divergence is CONCERNS.
3. **Insertion point preserves §Campaign Lessons structure:** the section's existing organization (bulleted candidate list under heading) should be unchanged; P28 + P29 added as parallel bullets.
4. **Optional CLAUDE.md change is bounded:** if `## Rules` section was added, it should be the only edit to `argus/CLAUDE.md`. If section was already present, the file should be unchanged.
5. **No scope creep:** verify no other argus files were modified.

## Sprint-Level Regression Checklist (for @reviewer)

See `argus/docs/sprints/synthesis-2026-04-26/review-context.md` §"Embedded Document 3: Sprint-Level Regression Checklist." For Session 0, the relevant checks are R3 (evolution-note bodies — N/A for Session 0 since no evolution-note edits), R4 (ARGUS runtime untouched — applies), R10 (symlink targets — N/A since no metarepo work), R20 (continuous ARGUS-runtime check — applies), R16 (close-out file present — applies).

## Sprint-Level Escalation Criteria (for @reviewer)

See `argus/docs/sprints/synthesis-2026-04-26/review-context.md` §"Embedded Document 4: Sprint-Level Escalation Criteria." For Session 0, the most relevant triggers are A1 (ARGUS runtime modified), D1 (Session 0 not landed before Session 1 begins — N/A here since this IS Session 0), and C3 (compaction-driven regression — unlikely for a session this small but still verifiable).
