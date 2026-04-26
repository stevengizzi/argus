# Sprint synthesis-2026-04-26, Session 1: Keystone Pre-Flight Wiring + RULE Additions + Close-Out Strengthening

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (RULE-001 through RULE-050; RULEs 051/052/053 are landing in this session) applies regardless of whether any specific rule is referenced inline below.

2. **Verify Session 0 has landed.** This session depends on the synthesis input set being durable (P28+P29 in SPRINT-31.9-SUMMARY.md):
   ```bash
   grep -c "^- \*\*P2[6789] candidate:\*\*" argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md
   ```
   Must return 4. If it returns 2 (only P26+P27), Session 0 was not run — **HALT and report**. Do not proceed with Session 1 until Session 0 is complete (escalation criterion D1).

3. Read these files to load context:
   - `argus/docs/sprints/synthesis-2026-04-26/review-context.md` (the Sprint Spec + Spec by Contradiction + Regression Checklist + Escalation Criteria, all embedded)
   - `argus/workflow/claude/rules/universal.md` (current RULE-001 through RULE-050; you'll be appending RULE-051/052/053 and adding a sub-bullet to RULE-038)
   - `argus/workflow/claude/skills/close-out.md` (current Step 3 wording; you'll be strengthening it)
   - `argus/workflow/templates/implementation-prompt.md` (current Pre-Flight Checks structure; you'll be inserting the keystone step + adding 3 small extensions elsewhere in the file)
   - `argus/workflow/templates/review-prompt.md` (you'll be inserting the keystone Pre-Flight step here too)
   - `argus/docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md` §"Pre-Classification Matrix" (boundary check: confirm RULE-038 through RULE-050 are the existing sealed RULEs; you must not modify their bodies)

4. Verify you are on the correct branch: `main` (in argus repo). All metarepo edits will be made on the `main` branch of the `claude-workflow` submodule (commits land in the metarepo, then argus's submodule pointer advances).

5. Verify git working tree is clean: `git status` returns no uncommitted changes (in both argus and the workflow submodule).

## Objective

Land four metarepo edits that together activate every existing universal RULE deterministically + add three new RULEs + strengthen close-out's FLAGGED-blocks-commit semantics + extend the implementation-prompt template with three small additions:

1. **Keystone wiring**: insert a new Pre-Flight step 1 in `templates/implementation-prompt.md` and `templates/review-prompt.md` that reads `.claude/rules/universal.md` and treats its contents as binding for the session. This single change retroactively activates RETRO-FOLD's P1–P25 RULE coverage and ensures every future RULE auto-fires at session start.

2. **Three new RULEs + RULE-038 sub-bullet**: add RULE-051 (P26), RULE-052 (P27), RULE-053 (P29) to `claude/rules/universal.md`; append the 5th sub-bullet to RULE-038 (P28).

3. **Close-out strengthening**: update `claude/skills/close-out.md` Step 3 wording so FLAGGED self-assessment blocks commit AND push (formerly only push).

4. **Three implementation-prompt template extensions**: operator-choice block, no-cross-referencing rule, and section-order discipline note.

## Requirements

This session is structured into 4 sub-phases. Do them in order. Commit after each substantive sub-phase if context budget warrants; otherwise, single commit at the end is fine.

### Sub-Phase 1: Keystone Pre-Flight wiring (HIGHEST PRIORITY)

**This is the single highest-leverage edit in the entire sprint. If everything else fails, this must land.**

In `argus/workflow/templates/implementation-prompt.md`:

Locate the existing "## Pre-Flight Checks" section (currently around line 13). The section currently begins with a numbered list starting at "1. Read these files to load context:". Insert a NEW step 1 before the existing step 1, and renumber the existing steps. The new step 1 reads:

```markdown
1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt.
```

The renumbered subsequent steps remain unchanged (the existing "Read these files to load context" becomes step 2, the existing test-baseline step becomes step 3, etc.).

Also bump the version header at the top of the file:
- `<!-- workflow-version: 1.2.0 -->` → `<!-- workflow-version: 1.3.0 -->`
- `<!-- last-updated: YYYY-MM-DD -->` → `<!-- last-updated: 2026-04-26 -->`

In `argus/workflow/templates/review-prompt.md`:

Locate the existing review-prompt structure. The current template doesn't have a numbered Pre-Flight section per se (it has an "## Instructions" section at the top). Insert a new "## Pre-Flight" section between "## Instructions" and "## Review Context" with the following content:

```markdown
## Pre-Flight

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this review.** The full set of universal RULE entries (currently RULE-001 through RULE-053) applies regardless of whether any specific rule is referenced inline in this prompt — particularly RULE-013 (read-only mode) which governs the entire review session.
```

Bump the version header:
- `<!-- workflow-version: 1.1.0 -->` → `<!-- workflow-version: 1.2.0 -->`
- `<!-- last-updated: YYYY-MM-DD -->` → `<!-- last-updated: 2026-04-26 -->`

**Verification:**
```bash
grep -c "Read .*\.claude/rules/universal\.md" argus/workflow/templates/implementation-prompt.md
# Expected: ≥ 1

grep -c "Read .*\.claude/rules/universal\.md" argus/workflow/templates/review-prompt.md
# Expected: ≥ 1

grep -B2 -A2 "Read .*\.claude/rules/universal\.md" argus/workflow/templates/implementation-prompt.md | grep -E "(binding|treat)" | head -1
# Expected: at least one match (imperative phrasing present)

grep -B2 -A2 "Read .*\.claude/rules/universal\.md" argus/workflow/templates/review-prompt.md | grep -E "(binding|treat)" | head -1
# Expected: at least one match
```

Capture all 4 verification outputs in the close-out.

### Sub-Phase 2: RULE-051, RULE-052, RULE-053 + RULE-038 5th sub-bullet

In `argus/workflow/claude/rules/universal.md`:

Bump the version header at the top of the file:
- Look for `# Universal Rules` H1 + `# Version: 1.0` line below it
- Update version line to `# Version: 1.1`

**Append a 5th sub-bullet to RULE-038.** Locate RULE-038 (currently has 4 sub-bullets: File paths / Grep-observable claims / Metric values / Tracker nicknames vs filenames). Add a 5th sub-bullet AFTER the existing 4 and BEFORE the closing paragraph "When the re-verification disagrees…":

```markdown
- **Kickoff statistics in close-outs.** Closeouts should explicitly disclose any kickoff-vs-actual discrepancies with attribution rather than quietly conform to the kickoff's stated numbers. Treating kickoff statistics as directional input requiring grep-verification is RULE-038's session-start posture; surfacing discrepancies in the closeout is the disclosure follow-through. Don't propagate a wrong number from kickoff to summary just because the kickoff said it.
```

Then update the Origin footnote for RULE-038 to add P28 to the consolidation list:
- Existing: `<!-- Origin: Sprint 31.9 retro, P6 + P12 + P13 + P19 + P22 (consolidated). ... -->`
- Updated: `<!-- Origin: Sprint 31.9 retro, P6 + P12 + P13 + P19 + P22 + synthesis-2026-04-26 P28 (consolidated). Evidence for P28: SPRINT-CLOSE-A-closeout.md §1 corrected the kickoff's "24 closed DEFs" figure to the grep-verified 19 (5 of the 24 — DEF-152/153/154/158/161 — were closed by earlier campaign sessions before IMPROMPTU-04 anchored the campaign-close window); the implementer flagged the discrepancy in closeout via grep-verify rather than silent conformance. ... -->` (preserve all existing evidence text; add the P28 evidence after the existing evidence).

**Add new section §16 (Fix Validation) with RULE-051.** Append at the end of the file (after RULE-050's closing footnote):

```markdown

---

## 16. Fix Validation

RULE-051: When validating a fix against a recurring symptom, verify against the mechanism signature (e.g., a measurable doubling ratio, a specific log-line correlation, a checksum), not the symptom aggregate (e.g., "the bug appears at EOD"). The mechanism signature is the falsifiable part; the symptom aggregate is the dependent variable. Any fix-validation session should explicitly identify the mechanism signature before running the validation. If the mechanism signature was preserved across debrief docs, a recurring symptom can be correctly attributed to a NEW mechanism rather than misattributed as the previous bug regressing.

<!-- Origin: synthesis-2026-04-26 P26. Evidence: ARGUS Apr 24 paper-session
     debrief preserved the 2.00× math from the DEF-199 fix validation
     (yesterday's mechanism signature). When 44 unexpected shorts surfaced
     today, the 1.00× ratio (set-equality, not 2× doubling) discriminated
     DEF-199 (closed) from DEF-204 (new mechanism: bracket children without
     OCA + side-blind reconciliation). Without the preserved mechanism
     signature, today's cascade would have been misattributed as a
     DEF-199 regression and IMPROMPTU-04 would have been incorrectly
     reopened. Captured in IMPROMPTU-11-mechanism-diagnostic.md
     §Retrospective Candidate. -->
```

**Update §15 (CI Verification Discipline) with RULE-052.** Find the existing RULE-050 in §15 and append RULE-052 to the same section:

```markdown

RULE-052: When CI turns red for a known cosmetic reason, explicitly log that assumption at each subsequent commit rather than treating it as silent ambient noise. The test is: "if a genuine regression slipped in, would I still notice?" CI-discipline drift on a known-cosmetic red can mask a real regression for the duration of the streak; without per-commit acknowledgment, the cosmetic-status assumption hardens into ambient noise. Operationally: each commit that pushes onto a red-CI baseline must include in its message body a one-line assertion of the cosmetic cause + a verification grep that the cosmetic cause hasn't shifted.

<!-- Origin: synthesis-2026-04-26 P27. Evidence: Sprint 31.9's 6-commit
     CI-red streak between Apr 22 and Apr 24 was correctly diagnosed as
     cosmetic (DEF-205 date-decay) but had masked any potential real
     regression for ~24 hours because each subsequent commit treated the
     red status as ambient. TEST-HYGIENE-01 closed DEF-205 and restored
     the 5,080 baseline; the streak was retrospectively confirmed cosmetic-
     only, but the period of unverified status was a real risk window. -->
```

**Add new section §17 (Architectural-Seal Verification) with RULE-053.** Append after RULE-052's section:

```markdown

---

## 17. Architectural-Seal Verification

RULE-053: Architecturally-sealed documents (e.g., FROZEN markers on long-form analysis files, sealed sprint folders, ARCHIVE-banner files) require defensive verification at session start, not just trust in the kickoff's instructions to avoid them. Any session that operates near sealed/frozen documents should encode the seal as a verifiable assertion at session start (e.g., grep for the FROZEN marker; halt if absent). The verification protects against the seal being silently removed elsewhere — without it, a future kickoff's avoidance instruction would silently bypass an important architectural decision if the marker is gone.

This rule is a sibling of RULE-038 (session-start grep-verification of factual claims) but distinct: RULE-038 verifies external assertions about current code state; RULE-053 verifies positive assertions about sealed-content protection. Action-on-failure differs: RULE-038 disagreement → flag/ignore the stale claim; RULE-053 missing seal → escalate (the seal's removal is itself the issue, not the work being attempted).

<!-- Origin: synthesis-2026-04-26 P29. Evidence: SPRINT-CLOSE-B-closeout.md
     §2 documents pre-flight check #5 explicitly grep-verified the
     `process-evolution.md` FROZEN marker still existed before allowing
     the session to proceed. If a future operator removes the freeze
     marker, the kickoff's avoidance instruction would silently bypass
     the architectural decision. Defensive verification at session start
     is the protection. -->
```

**Verification:**
```bash
grep -c "^RULE-051:\|^RULE-052:\|^RULE-053:" argus/workflow/claude/rules/universal.md
# Expected: 3

grep -c "Origin: synthesis-2026-04-26" argus/workflow/claude/rules/universal.md
# Expected: ≥ 3 (at minimum; one per new RULE)

grep -c "synthesis-2026-04-26 P28" argus/workflow/claude/rules/universal.md
# Expected: ≥ 1 (in RULE-038's updated Origin footnote)

# Verify RULE-038 through RULE-050 bodies preserved (use diff against pre-session HEAD)
git diff HEAD argus/workflow/claude/rules/universal.md | grep "^-" | grep -v "^---" | grep -v "^- \*\*Kickoff statistics" | wc -l
# Expected: 0 (no deletions other than possibly the version-line bump if it was on a deleted+inserted pair)
```

Capture all verification outputs in close-out.

### Sub-Phase 3: Close-out skill strengthening (Step 3)

In `argus/workflow/claude/skills/close-out.md`:

Locate Step 3 ("Commit"). The current text reads (around line 97):
```
1. Stage changes (prefer explicit paths over `git add -A` to avoid accidentally
   committing untracked files outside session scope).
2. **Pre-commit scope check.** Run `git diff --name-only --cached` and confirm
   every staged path is within the session's declared scope (the Change Manifest).
   If a staged file is not in the manifest — either add it to the manifest (and
   justify why it was touched) or unstage it. Do not commit a mixed-scope diff.
   <!-- Origin: Sprint 31.9 retro, P4. -->
3. Commit with message: `[Sprint X.Y] [session scope summary]`
4. Push to remote: `git push`

Do NOT push if self-assessment is FLAGGED — wait for developer review of the close-out.
```

Strengthen the FLAGGED line at the bottom. Replace:
```
Do NOT push if self-assessment is FLAGGED — wait for developer review of the close-out.
```

with:
```
**Do NOT stage, commit, or push if self-assessment is FLAGGED.** The original wording said "Do NOT push if FLAGGED," but pushing was already too late — staged-but-uncommitted changes still risk being committed by the next operator action, and committed-but-unpushed changes still cause CI runs on the next push. Stop earlier in the pipeline: if FLAGGED, write the close-out report, surface the FLAGGED finding to the operator, and wait for guidance before any git operation beyond the close-out commit itself.

<!-- Origin: synthesis-2026-04-26 (strengthening of P4-era close-out
     discipline). The original "Do NOT push if FLAGGED" wording allowed
     the implementer to stage + commit, then halt before push — but
     staged-and-committed work has implicit downstream effects (next
     git operation, IDE state) that the FLAGGED gate should prevent
     entirely. Strengthen to "Do NOT stage, commit, or push." -->
```

Bump the close-out skill's version header (if present) to next minor version, or add one if absent:
- If the file currently has `<!-- workflow-version: X.Y.Z -->`, bump minor.
- If absent, add `<!-- workflow-version: 1.1.0 --> <!-- last-updated: 2026-04-26 -->` at the top.

**Verification:**
```bash
grep -B1 -A2 "stage, commit, or push" argus/workflow/claude/skills/close-out.md
# Expected: at least one match (the strengthened wording)

grep -c "Do NOT push if self-assessment is FLAGGED" argus/workflow/claude/skills/close-out.md
# Expected: 0 (the original wording is replaced, not retained)
```

### Sub-Phase 4: Implementation-prompt template extensions

In `argus/workflow/templates/implementation-prompt.md` (already touched in Sub-Phase 1 for the keystone):

Add three new subsections. Use judgment about insertion location, but follow these guidelines:

**(a) Operator Choice block** — insert as a new subsection between the existing "## Constraints" and "## Canary Tests" sections (or equivalent natural location):

```markdown
## Operator Choice (if applicable)

[Include this section for sessions that present multiple architectural options
where operator judgment is required between option A and option B (or A/B/C).
This template lets the operator pre-check before pasting into Claude Code, and
downstream sessions reference the resulting choice via git state, not via
re-prompting.]

The operator must check ONE option below before this prompt is pasted into
Claude Code. If the operator fails to check an option, Claude Code defaults
to the option labeled "default" or, if none is labeled, the smallest-blast-
radius option, and surfaces this default-application in the close-out's
Judgment Calls section.

- [ ] Option A (default — smallest blast radius): [description]
- [ ] Option B: [description]
- [ ] Option C: [description]

Downstream sessions that depend on this choice should NOT re-prompt the
operator. Instead, they reference the state of `main` after this session's
commit, with conditional instructions per option (e.g., "if Option B was
chosen, this session's work collapses to X").

<!-- PLANNING NOTE: Origin: synthesis-2026-04-26 N3.5. Use this section only
     when an architectural decision genuinely requires operator judgment
     mid-sprint and downstream sessions depend on the choice. Don't use
     for cosmetic preferences. -->
```

**(b) No-Cross-Referencing rule** — add to the "## Constraints" section as a new bullet:

```markdown
- Do NOT cross-reference other session prompts. This prompt is standalone;
  it must be pasteable into a fresh Claude Code session with zero knowledge
  of other session prompts. Even sessions with clear coupling handle the
  coupling via prose instructions referencing the state of `main`, not via
  cross-prompt references. (Origin: synthesis-2026-04-26 ID3.1.)
```

**(c) Section-Order Discipline note** — add as a "## Section Ordering" subsection near the bottom of the template (before or after the existing close-out invocation), or as a footer note:

```markdown
## Section Ordering

This template's section order matches the implementation execution order:
Pre-Flight → Objective → Requirements → Constraints → Operator Choice (if
applicable) → Canary Tests (if applicable) → Test Targets → Definition of
Done → Regression Checklist → Close-Out → Tier 2 Review → Post-Review Fix
Documentation → Session-Specific Review Focus → Sprint-Level Regression
Checklist → Sprint-Level Escalation Criteria.

Visual order matches execution order so Claude Code instances following the
template top-to-bottom proceed in the correct sequence. Do NOT reorder
sections when filling in the template — the close-out report's
self-assessment gates whether commit happens, and Tier 2 review runs after
commit. Reordering visually inverts this and risks confusion.

<!-- PLANNING NOTE: Origin: synthesis-2026-04-26 N3.8. Without this note,
     prompts have been generated where Tier 2 Review precedes Commit
     visually even when prose described correct execution order. -->
```

**Verification:**
```bash
grep -c "## Operator Choice" argus/workflow/templates/implementation-prompt.md
# Expected: ≥ 1

grep -c "Do NOT cross-reference other session prompts" argus/workflow/templates/implementation-prompt.md
# Expected: ≥ 1

grep -c "## Section Ordering" argus/workflow/templates/implementation-prompt.md
# Expected: ≥ 1
```

## Constraints

- **Do NOT modify** any path under `argus/argus/`, `argus/tests/`, `argus/config/`, or `argus/scripts/`. Triggers escalation criterion A1.
- **Do NOT modify** RULE-001 through RULE-050 bodies in `claude/rules/universal.md`. The ONLY permitted edit inside RULE-038 is the 5th sub-bullet append; everything else (RULE-001 through RULE-050) is byte-frozen. Triggers escalation criterion A3.
- **Do NOT modify** RETRO-FOLD's existing Origin footnotes (RULE-038 through RULE-050) other than the explicit RULE-038 footnote update (which appends `+ synthesis-2026-04-26 P28` and adds the P28 evidence sentence).
- **Do NOT modify** evolution notes (`workflow/evolution-notes/2026-04-21-*.md`). They get touched in Session 2 (header-only); Session 1 doesn't touch them at all.
- **Do NOT modify** files outside the explicit Requirements list (universal.md, close-out.md, implementation-prompt.md, review-prompt.md). Any other metarepo file modified triggers a scope-creep escalation per D3.
- **Do NOT introduce** new files in any directory.
- **Do NOT introduce** new RULEs beyond RULE-051/052/053 (numbering must be contiguous).

## Test Targets

This session creates no executable code, no tests, and no Python. Verification is grep-based per the four sub-phases above.

- **Existing tests:** unaffected (no code touched).
- **New tests:** none.
- **Verification:** run all grep commands listed under each Sub-Phase. Capture outputs in close-out.

## Definition of Done

- [ ] **Sub-Phase 1:** Keystone Pre-Flight wiring landed in BOTH `templates/implementation-prompt.md` AND `templates/review-prompt.md`. Wording is imperative ("read," "treat as binding"). Both files have version-header bumps.
- [ ] **Sub-Phase 2:** RULE-051, RULE-052, RULE-053 added; RULE-038 has 5th sub-bullet; RULE-038 Origin footnote updated to include `synthesis-2026-04-26 P28`. RULE-001 through RULE-050 bodies preserved byte-for-byte (verified by diff). Version line in universal.md bumped to 1.1.
- [ ] **Sub-Phase 3:** Close-out Step 3 FLAGGED wording strengthened from "Do NOT push if FLAGGED" to "Do NOT stage, commit, or push if FLAGGED" with rationale comment. Version-header bump.
- [ ] **Sub-Phase 4:** Three template extensions in implementation-prompt.md (Operator Choice block, No-Cross-Referencing rule in Constraints, Section Ordering subsection).
- [ ] All verification grep commands run; outputs captured in close-out.
- [ ] No files modified outside the explicit set.
- [ ] No RULE-001–050 body modifications (verified via diff).
- [ ] Close-out report written to `argus/docs/sprints/synthesis-2026-04-26/session-1-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Keystone wiring imperative | `grep -B2 -A2 ".claude/rules/universal.md" workflow/templates/implementation-prompt.md \| grep -E "(binding\|treat)"` returns ≥1 (same for review-prompt.md) |
| RULE-001–050 bodies unchanged | `git diff HEAD workflow/claude/rules/universal.md` shows only: RULE-038 sub-bullet append + RULE-038 Origin footnote update + new sections §16 (RULE-051) + §17 (RULE-053) appended + RULE-052 added to existing §15 + version line bump. No other body changes. |
| RETRO-FOLD origin footnote integrity | `grep -c "Origin: Sprint 31.9 retro" workflow/claude/rules/universal.md` ≥ 13 (the original 13 RETRO-FOLD footnotes preserved; consolidation update on RULE-038 keeps the original P6/12/13/19/22 references) |
| Close-out FLAGGED strengthening | `grep "stage, commit, or push" workflow/claude/skills/close-out.md` ≥ 1 |
| Implementation-prompt.md template extensions | All 3 grep checks from Sub-Phase 4 pass |
| Version bumps applied | universal.md → 1.1; implementation-prompt.md → 1.3.0; review-prompt.md → 1.2.0; close-out.md → minor bump |
| ARGUS runtime untouched | `git diff HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/` returns empty |
| No evolution-notes touched | `git diff HEAD --name-only -- workflow/evolution-notes/` returns empty |

## Close-Out

After all 4 sub-phases complete and all verifications pass, follow the close-out skill in `.claude/skills/close-out.md`. The strengthened Step 3 (FLAGGED-blocks-stage-commit-push) takes effect immediately for THIS session's own close-out — verify your self-assessment is CLEAN or MINOR_DEVIATIONS before staging.

The close-out report MUST include the structured JSON appendix at the end, fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file:**
`argus/docs/sprints/synthesis-2026-04-26/session-1-closeout.md`

**Commit pattern (cross-repo: metarepo + argus):**

The metarepo edits land in the `claude-workflow` submodule (workflow/) on its `main` branch. After the metarepo commit, advance argus's submodule pointer.

```bash
# In workflow/ submodule:
cd argus/workflow
git add claude/rules/universal.md claude/skills/close-out.md templates/implementation-prompt.md templates/review-prompt.md
git commit -m "synthesis-2026-04-26 S1: keystone Pre-Flight wiring + RULE-051/052/053 + close-out FLAGGED strengthening + template extensions"
git push origin main

# In argus/ root:
cd ..
git add workflow
git add docs/sprints/synthesis-2026-04-26/session-1-closeout.md
git commit -m "synthesis-2026-04-26 S1: advance workflow submodule + close-out report"
git push
```

Wait for CI to complete on the argus push; record the green CI URL in the close-out (per RULE-050).

## Tier 2 Review (Mandatory — @reviewer Subagent)

After commits land and CI is green, invoke the @reviewer subagent.

Provide the @reviewer with:

1. The review context file: `argus/docs/sprints/synthesis-2026-04-26/review-context.md`
2. The close-out report path: `argus/docs/sprints/synthesis-2026-04-26/session-1-closeout.md`
3. The diff range: BOTH the metarepo diff (`cd workflow && git diff HEAD~1 && cd ..`) AND the argus diff (`git diff HEAD~1`). Cross-repo, so the @reviewer must check both.
4. Files that should NOT have been modified: anything outside the explicit set in Requirements + Constraints

The @reviewer writes its review report to:
`argus/docs/sprints/synthesis-2026-04-26/session-1-review.md`

## Post-Review Fix Documentation

If the @reviewer reports CONCERNS and you fix the findings within this same session, append "Post-Review Fixes" to the close-out + "Post-Review Resolution" to the review report; update the structured verdict to `CONCERNS_RESOLVED`. Commit the updated files.

## Session-Specific Review Focus (for @reviewer)

1. **Keystone wiring imperative phrasing** (highest-priority check). Both `templates/implementation-prompt.md` and `templates/review-prompt.md` Pre-Flight sections must contain `"Read \`.claude/rules/universal.md\` in full and treat its contents as binding for this session."` or semantically equivalent imperative wording. Advisory phrasing is escalation criterion B1.
2. **RULE-001 through RULE-050 byte-preservation**. Diff against pre-session HEAD must show changes ONLY in: RULE-038 sub-bullet (the new 5th bullet), RULE-038 Origin footnote (P28 added to consolidation list + new evidence sentence), file-version line, and end-of-file appends (RULE-051 in new §16; RULE-052 in existing §15; RULE-053 in new §17). Any other RULE body change is escalation criterion A3.
3. **RULE-051, RULE-052, RULE-053 each have an Origin footnote** citing synthesis-2026-04-26 + the relevant P-number + concrete evidence.
4. **Close-out Step 3 strengthening** is in place; original "Do NOT push if FLAGGED" wording is replaced (not retained alongside).
5. **Three implementation-prompt.md template extensions** all present (Operator Choice block, No-Cross-Referencing rule, Section Ordering subsection).
6. **Version bumps applied correctly** (4 files; see Definition of Done).
7. **Cross-repo commit hygiene:** metarepo commit + argus submodule pointer advance + close-out commit. No metarepo orphan commits.

## Sprint-Level Regression Checklist (for @reviewer)

See `argus/docs/sprints/synthesis-2026-04-26/review-context.md` §"Embedded Document 3: Sprint-Level Regression Checklist." For Session 1, the relevant checks are R1 (RULE-001–050 bodies preserved), R2 (RETRO-FOLD origin footnotes preserved), R6 (keystone Pre-Flight present + imperative — primary check this session), R8 (workflow-version monotonic + correct), R20 (ARGUS runtime untouched), R16 (close-out file present).

## Sprint-Level Escalation Criteria (for @reviewer)

See `argus/docs/sprints/synthesis-2026-04-26/review-context.md` §"Embedded Document 4: Sprint-Level Escalation Criteria." For Session 1, the most relevant triggers: A3 (RETRO-FOLD content semantic regression — highest risk this session), B1 (keystone wiring missing or advisory — sprint failure if missed), C1 (workflow-version regression).
