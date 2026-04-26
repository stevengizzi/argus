# Sprint synthesis-2026-04-26: Sprint-Level Regression Checklist

> Cross-session invariants. The Tier 2 reviewer runs every item below at each session's review (not just the session that introduced the relevant content). This catches regressions where a later session inadvertently undoes or weakens an earlier session's work.
>
> Distinct from **session-specific** regression checklists (embedded in each session's implementation prompt) which cover invariants relevant only to that session's diff.
>
> Each item: invariant statement → verification command → expected outcome → what counts as a violation. Most items are grep/diff-based (mechanical). Where judgment is needed, it's flagged.

---

## Section 1: Sealed-Content Invariants

These check that content marked "do not modify" (per kickoff constraints + spec-by-contradiction §"Do NOT modify") stays preserved across all 6 sessions.

### R1. RULE-001 through RULE-050 bodies preserved byte-for-byte (except RULE-038 5th sub-bullet)

**Verify (run at every session's review):**
```bash
git show <pre-sprint-sha>:workflow/claude/rules/universal.md > /tmp/pre.md
git show HEAD:workflow/claude/rules/universal.md > /tmp/post.md
diff /tmp/pre.md /tmp/post.md
```

**Expected:** Diff shows ONLY:
- Append at end of file: new sections containing RULE-051, RULE-052, RULE-053
- Inside RULE-038 block: insertion of 5th sub-bullet (precise wording per spec §3); existing 4 sub-bullets unchanged
- Header version bump `<!-- workflow-version: 1.0 -->` → `<!-- workflow-version: 1.1 -->`
- Header date bump

**Violation:** Any line change inside RULE-001 through RULE-050 bodies (excluding the RULE-038 sub-bullet append). Triggers escalation criterion A3.

---

### R2. RETRO-FOLD origin footnotes preserved verbatim

**Verify:**
```bash
git show <pre-sprint-sha>:workflow/claude/rules/universal.md | grep -B1 -A4 "Origin: Sprint 31.9 retro" > /tmp/pre-footnotes.txt
git show HEAD:workflow/claude/rules/universal.md | grep -B1 -A4 "Origin: Sprint 31.9 retro" > /tmp/post-footnotes.txt
diff /tmp/pre-footnotes.txt /tmp/post-footnotes.txt
```

Same check on:
- `workflow/claude/skills/close-out.md`
- `workflow/claude/skills/review.md`
- `workflow/protocols/sprint-planning.md`
- `workflow/templates/implementation-prompt.md`

**Expected:** All 25 RETRO-FOLD origin footnotes (P1–P25 references) byte-identical between pre-sprint and HEAD.

**Violation:** Any change to RETRO-FOLD's origin-footnote wording, even cosmetic (whitespace, capitalization, punctuation). Triggers escalation criterion A3.

---

### R3. Evolution-note bodies byte-frozen

**Verify (run after Session 2 + every subsequent session):**
```bash
for note in workflow/evolution-notes/2026-04-21-*.md; do
    pre=$(git show <pre-sprint-sha>:$note 2>/dev/null)
    post=$(git show HEAD:$note)
    # Strip metadata block (top section ending with first ---), compare bodies
    pre_body=$(echo "$pre" | awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==2){p=1; next}} p')
    post_body=$(echo "$post" | awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==2){p=1; next}} p')
    diff <(echo "$pre_body") <(echo "$post_body") || echo "BODY DIFFERS in $note"
done
```

**Expected:** Body content (lines below the metadata block's closing `---`) byte-identical pre/post across all 3 evolution notes. Only the metadata block has the additive `**Synthesis status:**` line.

**Violation:** Any change to body lines, including whitespace-only changes. Triggers escalation criterion A2.

---

### R4. ARGUS runtime / tests / configs not touched

**Verify (every session, especially Session 0):**
```bash
git diff <pre-sprint-sha>..HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/
```

**Expected:** Empty output. The ONLY argus-side changes permitted are:
- `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` (Session 0 P28+P29 backfill)
- `argus/CLAUDE.md` (Session 0 optional `## Rules` section)
- `argus/workflow` submodule pointer (operator advances after metarepo sessions land)

**Violation:** Any path matched. Triggers escalation criterion A1. **HARD constraint** — no judgment override.

---

### R5. RETRO-FOLD-touched skill/template additions preserved

**Verify:**
```bash
git diff <pre-sprint-sha>..HEAD -- workflow/claude/skills/review.md workflow/claude/skills/diagnostic.md workflow/claude/skills/canary-test.md workflow/claude/skills/doc-sync.md
```

**Expected:** review.md / diagnostic.md / canary-test.md / doc-sync.md unchanged across the sprint (none of these files appear in any session's modify list).

**Violation:** Any diff in these files. Escalates per spec-by-contradiction "Do NOT modify" list.

---

## Section 2: Structural Integrity Invariants

These verify that the sprint's intended structure (keystone wiring, bootstrap routing, version headers) is in place after the relevant session and remains stable through subsequent sessions.

### R6. Keystone Pre-Flight wiring present + imperative

**Verify (run at every session's review starting Session 1):**
```bash
# Implementation prompt template
grep -c "Read .*\.claude/rules/universal\.md" workflow/templates/implementation-prompt.md
grep -B2 -A4 "Read .*\.claude/rules/universal\.md" workflow/templates/implementation-prompt.md | grep -E "(binding|treat|apply)" | head -3

# Review prompt template
grep -c "Read .*\.claude/rules/universal\.md" workflow/templates/review-prompt.md
grep -B2 -A4 "Read .*\.claude/rules/universal\.md" workflow/templates/review-prompt.md | grep -E "(binding|treat|apply)" | head -3
```

**Expected:** Both templates contain a Pre-Flight step with imperative wording binding the reader to the rules file. Match count ≥ 1 per template.

**Violation:** Either template missing the keystone, OR phrasing is advisory ("you may," "consider," "if helpful"). Triggers escalation criterion B1. **Highest-leverage edit in the sprint**; this check is non-negotiable on every session's review.

---

### R7. Bootstrap routing for new protocols + templates present

**Verify (run starting Session 3, 4, 5):**

After Session 3:
```bash
grep -E "(Campaign Orchestration|Campaign Absorption|Campaign Close)" workflow/bootstrap-index.md
grep "campaign-orchestration\.md" workflow/bootstrap-index.md
```

After Session 4:
```bash
grep -E "Operational Debrief" workflow/bootstrap-index.md
grep "operational-debrief\.md" workflow/bootstrap-index.md
```

After Session 5:
```bash
grep "stage-flow\.md\|scoping-session-prompt\.md" workflow/bootstrap-index.md
```

**Expected:** Each new file has at least one match in the "Conversation Type → What to Read" section AND at least one match in the relevant Index table (Protocol Index for protocols; Template Index for templates).

**Violation:** New file committed without bootstrap routing entry. Triggers escalation criterion B2. **Auto-effect-defining check** — without routing, the new file is a sit-there doc.

---

### R8. Workflow-version headers monotonic + correct

**Verify (run at every session's review):**
```bash
for f in workflow/claude/rules/universal.md \
         workflow/claude/skills/close-out.md \
         workflow/templates/implementation-prompt.md \
         workflow/templates/review-prompt.md \
         workflow/templates/work-journal-closeout.md \
         workflow/templates/doc-sync-automation-prompt.md \
         workflow/protocols/codebase-health-audit.md \
         workflow/protocols/impromptu-triage.md \
         workflow/protocols/sprint-planning.md \
         workflow/protocols/campaign-orchestration.md \
         workflow/protocols/operational-debrief.md \
         workflow/templates/stage-flow.md \
         workflow/templates/scoping-session-prompt.md; do
    if [ -f "$f" ]; then
        pre=$(git show <pre-sprint-sha>:$f 2>/dev/null | grep "workflow-version" | head -1)
        post=$(grep "workflow-version" "$f" | head -1)
        echo "$f: pre=[$pre] post=[$post]"
    fi
done
```

**Expected:**
- `claude/rules/universal.md`: 1.0 → 1.1
- `claude/skills/close-out.md`: minor bump (e.g., 1.0.0 → 1.1.0)
- `templates/implementation-prompt.md`: 1.2.0 → 1.3.0
- `templates/review-prompt.md`: 1.1.0 → 1.2.0
- `templates/work-journal-closeout.md`: minor bump
- `templates/doc-sync-automation-prompt.md`: minor bump
- `protocols/codebase-health-audit.md`: 1.0.0 → **2.0.0** (major bump — Phase 2/3 expansion)
- `protocols/impromptu-triage.md`: minor bump (e.g., 1.1.0 → 1.2.0)
- `protocols/sprint-planning.md`: minor bump if cross-reference adds non-trivial content; otherwise patch
- New files: `1.0.0`

**Violation:** Any version bumped downward, OR `codebase-health-audit.md` not at 2.0.0 by Session 6 close-out, OR new file missing version header. Triggers escalation criterion C1.

---

### R9. New file headers complete (workflow-version + last-updated)

**Verify (after each new file's creating session):**
```bash
for f in workflow/protocols/campaign-orchestration.md \
         workflow/protocols/operational-debrief.md \
         workflow/templates/stage-flow.md \
         workflow/templates/scoping-session-prompt.md; do
    if [ -f "$f" ]; then
        head -3 "$f"
    fi
done
```

**Expected:** Each new file's first 3 lines contain:
```
<!-- workflow-version: 1.0.0 -->
<!-- last-updated: 2026-04-26 -->
```
followed by the H1 title.

**Violation:** Missing or malformed header. Tier 2 catches in CONCERNS (auto-fix in-session).

---

### R10. Symlink targets continue to resolve

**Verify (judgmental — run after Session 1 + Session 2):**
The synthesis sprint does not move, rename, or delete any file in `workflow/claude/rules/`, `workflow/claude/skills/`, or `workflow/claude/agents/`. Existing project-side symlinks pointing at these paths continue to resolve.

```bash
ls workflow/claude/rules/universal.md
ls workflow/claude/skills/close-out.md workflow/claude/skills/review.md workflow/claude/skills/diagnostic.md workflow/claude/skills/canary-test.md workflow/claude/skills/doc-sync.md
```

**Expected:** All paths exist as files (no move/rename/delete).

**Violation:** Any of these files renamed or moved. Triggers escalation per spec-by-contradiction §"Do NOT add" / "Do NOT refactor."

---

## Section 3: Quality Invariants

These verify content quality across the sprint (origin footnotes, generalized terminology, cross-reference integrity).

### R11. Every metarepo addition has an Origin footnote

**Verify (run at every session's review):**
```bash
# Count Origin footnotes citing this synthesis sprint or its source notes
grep -rn "Origin:.*synthesis-2026-04-26\|Origin:.*2026-04-21.*evolution\|Origin:.*P26\|Origin:.*P27\|Origin:.*P28\|Origin:.*P29\|Origin:.*P30\|Origin:.*P31\|Origin:.*P32\|Origin:.*P33\|Origin:.*P34" workflow/
```

**Expected:** At least one Origin footnote per substantive new section. The disposition matrix in Phase A enumerated ~25 distinct codifications; expect ~25–35 Origin footnotes total across the sprint's diff (some additions consolidate multiple inputs in one footnote).

**Violation:** A new section, RULE, or protocol exists without an Origin footnote. Tier 2 CONCERNS (in-session fix); becomes ESCALATE if multiple new sections lack footnotes (suggests a systemic miss).

---

### R12. F1–F10 generalized-terminology coverage

**Verify (run at every session's review starting Session 3):**

For each session that creates or modifies content involving the F1–F10 findings:
```bash
# F1: "Work Journal conversation" → "campaign coordination surface"
grep -c "Work Journal conversation" <files-modified-in-session>  # Existing reference is OK only in templates/work-journal-closeout.md context; new content should use generalized term

# F2: recurring-event-driven framing in operational-debrief.md
grep -E "(periodic|event-driven|recurring)" workflow/protocols/operational-debrief.md  # Expect ≥3 matches

# F3: "execution-anchor commit" not "boot commit"
grep -c "boot commit\|execution-anchor commit" workflow/protocols/operational-debrief.md  # New protocol uses execution-anchor; "boot commit" appears only as the ARGUS-specific example

# F4: tiered hot-files
grep -E "(recent-bug|recent-churn|post-incident|maintained.list|code-ownership)" workflow/protocols/codebase-health-audit.md  # Expect ≥5 matches in Phase 2

# F5: 3 non-trading examples for fingerprint pattern
grep -B2 -A10 "fingerprint-before-behavior-change\|fingerprint.before.behavior" workflow/protocols/codebase-health-audit.md | grep -E "(pricing|invoice|A/B|cohort|model.version|recommendation)" | head -5  # Expect references to non-trading scenarios

# F6: generalized absorption axes (no "audit-execution-state" verbatim — should be more general)
grep -B2 -A2 "absorption.axis\|absorption.dimension\|axes" workflow/protocols/campaign-orchestration.md  # Should reference work-execution-state generally

# F7: stage-flow has 3 formats
grep -E "(ASCII|Mermaid|ordered.list)" workflow/templates/stage-flow.md  # Expect all 3

# F8: closed-item terminology in Phase 1 spot check
grep -B2 -A4 "DEF Health Spot.Check\|spot.check" workflow/protocols/codebase-health-audit.md | grep -E "(closed-item|equivalent|Linear|GitHub)"  # Expect generalized terminology

# F9: squash-merge caveat
grep -B2 -A4 "git.commit.body\|state.oracle" workflow/protocols/codebase-health-audit.md | grep -E "(squash|PR|GitHub Action)"  # Expect caveat

# F10: 7-point-check appendix conditional framing
grep -B2 -A4 "7-point\|seven-point\|tracking conversation" workflow/protocols/campaign-orchestration.md | grep -E "(if.*tracking|when.*coordination|applies.*conversation)"  # Expect conditional framing
```

**Expected:** Each F# has a positive grep result in the appropriate file/section. Session 6 close-out must include a table mapping each F# to its addressing file/section (acceptance gate for Session 6).

**Violation:** Missing F# coverage. Triggers escalation criterion B4 (if Session 6 close-out's mapping is incomplete) or CONCERNS (if Tier 2 catches it before close-out).

---

### R13. Safety-tag taxonomy appears ONLY in rejected-pattern addendum

**Verify (run at every session's review):**
```bash
grep -rE "(safe-during-trading|weekend-only|read-only-no-fix-needed|deferred-to-defs)" workflow/protocols/ workflow/templates/ workflow/claude/skills/ workflow/scripts/
```

**Expected:** Matches appear ONLY in `workflow/protocols/codebase-health-audit.md` Phase 2's `### Anti-pattern (do not reinvent)` addendum, with surrounding context that frames the taxonomy as "empirically overruled," "do not reinvent," etc.

**Violation:** Any match outside the addendum, OR matches inside the addendum without rejection-framing context. Triggers escalation criterion B3.

---

### R14. Cross-references resolve

**Verify (run after Session 5 — when all forward-deps should be resolved):**
```bash
# Session 3's forward-dep on Session 5's output
grep -oE "templates/scoping-session-prompt\.md" workflow/protocols/impromptu-triage.md
ls workflow/templates/scoping-session-prompt.md  # Must exist

# Other cross-references
grep -roE "(protocols/|templates/|claude/skills/|claude/rules/|scripts/)[a-z0-9-]+\.(md|py)" workflow/protocols/campaign-orchestration.md workflow/protocols/operational-debrief.md workflow/templates/stage-flow.md workflow/templates/scoping-session-prompt.md workflow/protocols/codebase-health-audit.md | sort -u | while read ref; do
    if [ ! -f "workflow/$ref" ]; then
        echo "BROKEN REFERENCE: workflow/$ref"
    fi
done
```

**Expected:** Every path-based cross-reference in new content resolves to an actual file in the metarepo.

**Violation:** Broken reference. CONCERNS (in-session fix) unless it's the Session 3 → Session 5 forward-dep failing after Session 5 close-out (then it's ESCALATE per criterion C4).

---

### R15. Bootstrap-index existing entries unchanged

**Verify (run after every session that modifies bootstrap-index.md):**
```bash
git show <pre-sprint-sha>:workflow/bootstrap-index.md > /tmp/bootstrap-pre.md
diff /tmp/bootstrap-pre.md workflow/bootstrap-index.md | grep "^<"
```

**Expected:** Diff's `<` lines (deletions from pre-sprint state) should be empty — only `>` lines (additions) should appear. Existing entries in "Conversation Type → What to Read," Protocol Index, Template Index, and Schema Index are unchanged.

**Violation:** Any existing entry modified. Triggers escalation per spec-by-contradiction "Do NOT refactor" boundary.

---

## Section 4: Process Invariants

These verify the sprint's process discipline (close-outs, version stamps, dependency chain).

### R16. Each session's close-out file present at expected path

**Verify (run during sprint, after each session):**
```bash
ls argus/docs/sprints/synthesis-2026-04-26/session-{0,1,2,3,4,5,6}-closeout.md
```

**Expected:** After Session N closes, file `session-N-closeout.md` exists in the sprint directory, contains structured close-out report (per `claude/skills/close-out.md`), and includes the structured JSON appendix (`json:structured-closeout`).

**Violation:** Missing close-out, OR malformed JSON appendix. Tier 2 CONCERNS unless multiple close-outs missing (then ESCALATE per criterion D2).

---

### R17. Session pre-flight verifies prior session's outputs

**Verify (Session 1+ pre-flight):**
- Session 1 pre-flight: grep for P28/P29 in argus SUMMARY.md → halt if not found (verifies Session 0 landed)
- Session 2 pre-flight: grep for keystone Pre-Flight wiring in implementation-prompt.md → halt if not found (verifies Session 1 landed)
- Session 3 pre-flight: grep for evolution-note synthesis-status headers → halt if not found (verifies Session 2 landed)
- Session 4 pre-flight: ls campaign-orchestration.md → halt if not found
- Session 5 pre-flight: ls operational-debrief.md → halt if not found
- Session 6 pre-flight: ls all 3 new templates + phase-2-validate.py → halt if any not found

**Expected:** Each session pre-flight halts if expected prior-session output is missing.

**Violation:** Pre-flight check missing or skipped. Tier 2 CONCERNS (the implementer should add the check before proceeding); ESCALATE if implementer proceeded past a missing prior output.

---

### R18. No new top-level metarepo directories

**Verify:**
```bash
git diff <pre-sprint-sha>..HEAD --name-status -- workflow/ | awk '$1=="A"' | awk -F'/' '{print $2}' | sort -u
```

**Expected:** All new files appear under existing directories (`protocols/`, `templates/`, `claude/`, `runner/`, `schemas/`, `scripts/`, `scaffold/`, `evolution-notes/`). No new top-level subdirectories.

**Violation:** New top-level directory introduced. Triggers escalation per spec-by-contradiction §"Do NOT add."

---

### R19. No new dependencies introduced

**Verify (after Session 5 — the only Python addition):**
```bash
head -20 workflow/scripts/phase-2-validate.py
grep -E "^(import|from)" workflow/scripts/phase-2-validate.py | sort -u
```

**Expected:** Only stdlib imports. Specifically the `csv` module + maybe `sys`, `argparse`, `pathlib`. Nothing from PyPI.

**Violation:** Non-stdlib import. Tier 2 CONCERNS (rewrite in stdlib) or ESCALATE if a PyPI dep is judged unavoidable (operator decides whether to introduce it).

---

### R20. Argus runtime untouched throughout (continuous verification)

This is R4 restated as a continuous check: runs at every session's Tier 2 review, not just the session that creates the most risk. The grep is cheap; the regression mode (a Session 3 commit accidentally drifting into argus runtime) is real.

**Verify (every session):**
```bash
git diff <pre-sprint-sha>..HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/
```

**Expected:** Empty. Permanently. Until sprint completion.

**Violation:** Same as R4. Hard escalation per A1.

---

## Tier 2 Reviewer Workflow

For each session's Tier 2 review:

1. **Run R1, R2, R5, R10, R20** unconditionally (sealed-content + structural integrity, cheap to verify).
2. **Run R3** after Session 2.
3. **Run R6** after Session 1 + every subsequent session (keystone wiring is the highest-leverage check).
4. **Run R7** after Sessions 3, 4, 5 (per their respective bootstrap entries).
5. **Run R8** after every session that bumps a version.
6. **Run R9** after Sessions 3, 4, 5 (new files only).
7. **Run R11, R12, R13** at every session's review starting from when relevant content lands.
8. **Run R14** after Session 5 (forward-dep resolution).
9. **Run R15** after every session that touches bootstrap-index.md.
10. **Run R16, R17, R18, R19** at the relevant session's review.

The Tier 2 review prompt (Phase D artifact) embeds these checks per session; the @reviewer subagent runs them as part of the structured-verdict generation.

If ANY check produces a violation:
- Cross-reference against escalation-criteria.md to determine ESCALATE vs CONCERNS.
- For CONCERNS: implementer fixes in-session via post-review-fix loop.
- For ESCALATE: stop the sprint, route to operator.

---

## Coverage Summary

| Risk surfaced in spec | Regression check | Detection layer |
|---|---|---|
| RETRO-FOLD content semantic regression | R1, R2 | Mechanical diff |
| Evolution-note body modification | R3 | Mechanical diff |
| ARGUS runtime modified | R4, R20 | Mechanical path filter |
| Keystone wiring miss | R6 | Mechanical grep + imperative-phrasing check |
| Bootstrap routing miss | R7 | Mechanical grep on bootstrap-index |
| Workflow-version regression | R8 | Mechanical version comparison |
| F1–F10 finding not addressed | R12 | Mechanical grep per F# + Session 6 close-out mapping |
| Safety-tag taxonomy reintroduction | R13 | Mechanical grep with framing-context check |
| Cross-reference broken | R14 | Mechanical file-existence check |
| Origin footnote missing | R11 | Mechanical grep count |
| Compaction-driven regression | (See escalation C3) | Tier 2 judgment |
| Symlink target moved | R10 | Mechanical file-existence check |
| New file lacks version header | R9 | Mechanical head + grep |
| New top-level directory | R18 | Mechanical diff path analysis |
| New PyPI dependency | R19 | Mechanical import scan |

The 9 risks from spec §Relevant Risks all have at least one regression check. Compaction risk (the one judgment-based item) is handled via the Tier 2 reviewer's structured-verdict process per escalation criterion C3, not via this checklist.
