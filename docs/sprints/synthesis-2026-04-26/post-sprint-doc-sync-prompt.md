# Post-Sprint Doc-Sync: synthesis-2026-04-26

> **When to use this prompt:** After Sessions 0–6 have all completed with verdict CLEAR or CONCERNS_RESOLVED, before declaring sprint complete. This prompt handles Section B (post-sprint metarepo doc-sync) + Section C2 (argus boot-commit-logging DEF entry) + the deferred placeholder-SHA resolution from Session 2.
>
> **Where to run:** A fresh Claude Code session targeting both the `argus/` repo and the `argus/workflow/` submodule. Estimated time: ~25 minutes.
>
> **Source-of-truth:** `argus/docs/sprints/synthesis-2026-04-26/doc-update-checklist.md` Sections B + C + E.

## Pre-Flight Checks

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** (Per the keystone Pre-Flight wiring landed in Session 1.)

2. **Verify Sessions 0–6 all complete:**
   ```bash
   for s in 0 1 2 3 4 5 6; do
       if [ -f argus/docs/sprints/synthesis-2026-04-26/session-${s}-closeout.md ]; then
           verdict=$(grep -A1 "verdict" argus/docs/sprints/synthesis-2026-04-26/session-${s}-review.md 2>/dev/null | grep -oE "(CLEAR|CONCERNS_RESOLVED|CONCERNS|ESCALATE)" | head -1)
           echo "Session $s: $verdict"
       else
           echo "Session $s: MISSING CLOSE-OUT"
       fi
   done
   ```
   All 7 sessions must show CLEAR or CONCERNS_RESOLVED. Any MISSING / CONCERNS / ESCALATE → **HALT and report**.

3. **Verify pre-sprint count baseline.** Document the README's CURRENT (stale) counts before fixing them, so the diff is auditable:
   ```bash
   grep -E "[0-9]+ protocol|[0-9]+ template|[0-9]+ cross-project rule" argus/workflow/README.md
   # Expected: stale counts ("14 protocols", "10 templates", "36 cross-project rules")

   echo "=== Actual counts post-sprint ==="
   ls argus/workflow/protocols/*.md | wc -l           # Expected: 19
   ls argus/workflow/templates/*.md | wc -l           # Expected: 13
   grep -c "^RULE-" argus/workflow/claude/rules/universal.md  # Expected: 53
   ls argus/workflow/schemas/*.md | wc -l             # Expected: 4 (unchanged)
   ls argus/workflow/claude/skills/*.md | wc -l       # Expected: 5 (unchanged)
   ```

4. Verify clean working tree in both repos.

## Objective

Reconcile the metarepo's meta-files with the post-sprint state, advance the argus submodule pointer, log the boot-commit-logging deferred item on the argus side, and resolve the placeholder commit SHAs in the evolution-note Synthesis status headers.

## Requirements

This prompt is structured into 5 sub-phases, ordered by repository (metarepo first, then argus, then verification).

### Sub-Phase 1: README.md count drift correction

In `argus/workflow/README.md`:

Locate the "Repository Structure" code block (around lines 13–28). Update the comment annotations:

**Before:**
```
├── protocols/           # How to run each type of conversation (14 protocols)
├── templates/           # Fill-in-the-blank sprint artifacts (10 templates)
├── schemas/             # Structured output schemas for runner/review (4 schemas)
├── claude/              # Claude Code configuration (universal)
│   ├── skills/          # close-out, review, canary-test, diagnostic, doc-sync
│   ├── rules/           # universal.md (36 cross-project rules)
│   └── agents/          # builder, reviewer, doc-sync-agent
├── runner/              # Autonomous Sprint Runner (Python package, 13 modules)
├── scaffold/            # New project starter kit
├── scripts/             # scaffold.sh, setup.sh, sync.sh
```

**After:**
```
├── protocols/           # How to run each type of conversation (19 protocols)
├── templates/           # Fill-in-the-blank sprint artifacts (13 templates)
├── schemas/             # Structured output schemas for runner/review (4 schemas)
├── claude/              # Claude Code configuration (universal)
│   ├── skills/          # close-out, review, canary-test, diagnostic, doc-sync
│   ├── rules/           # universal.md (53 cross-project rules)
│   └── agents/          # builder, reviewer, doc-sync-agent
├── runner/              # Autonomous Sprint Runner (Python package, 13 modules)
├── scaffold/            # New project starter kit
├── scripts/             # scaffold.sh, setup.sh, sync.sh, phase-2-validate.py
```

Three edits: protocols count, templates count, rules count + scripts/ comment append.

(The runner-module count "13 modules" is unchanged this sprint — verify via `ls argus/workflow/runner/*.py | wc -l`. If it has drifted independently from prior work, log as a deferred observation; do not fix in this sprint.)

**Verification:**
```bash
grep -E "([0-9]+) protocol" argus/workflow/README.md
# Expected: "19 protocols"

grep -E "([0-9]+) template" argus/workflow/README.md
# Expected: "13 templates"

grep -E "([0-9]+) cross-project rule" argus/workflow/README.md
# Expected: "53 cross-project rules"

grep "phase-2-validate" argus/workflow/README.md
# Expected: 1 match (in scripts/ comment)

# No other lines changed
git diff HEAD argus/workflow/README.md | grep "^[+-]" | grep -v "^+++\|^---" | wc -l
# Expected: ≤ 8 (4 line removals + 4 line additions max)
```

### Sub-Phase 2: Resolve placeholder SHAs in evolution-note Synthesis status headers

In Session 2, three evolution notes received a `**Synthesis status:**` header line with a placeholder commit SHA (`<pending-final-synthesis-sprint-commit>`). This sub-phase resolves that placeholder.

**Determine the principal synthesis commit.** The synthesis sprint's substantive content landed across Sessions 1–6. Use the **Session 1 commit SHA** as the synthesis sprint's anchor (per the recommendation in `doc-update-checklist.md` Section B6 + Sub-Phase 4 of Session 2's prompt). Session 1 is when the keystone wiring landed — the sprint structurally took effect at that commit.

```bash
cd argus/workflow
SESSION_1_SHA=$(git log --grep="synthesis-2026-04-26 S1" --pretty=format:"%H" -n 1)
echo "Session 1 commit SHA: $SESSION_1_SHA"
cd ..
```

If `$SESSION_1_SHA` is empty (commit-message convention drifted), fall back to: the first commit in `cd argus/workflow && git log --since=2026-04-26 --pretty=format:"%H" --reverse | head -1`.

**For each of the 3 evolution notes,** replace the placeholder:

```bash
for note in 2026-04-21-argus-audit-execution.md \
            2026-04-21-debrief-absorption.md \
            2026-04-21-phase-3-fix-generation-and-execution.md; do
    sed -i.bak "s/<pending-final-synthesis-sprint-commit>/$SESSION_1_SHA/" \
        argus/workflow/evolution-notes/$note
    rm argus/workflow/evolution-notes/${note}.bak
done
```

**Verify the bodies are still byte-identical** (this is critical — sed should ONLY have changed the metadata header line):

```bash
for note in 2026-04-21-argus-audit-execution.md \
            2026-04-21-debrief-absorption.md \
            2026-04-21-phase-3-fix-generation-and-execution.md; do
    cd argus/workflow
    pre=$(git show "$SESSION_1_SHA":evolution-notes/$note | awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==1){p=1; next}} p')
    post=$(awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==1){p=1; next}} p' evolution-notes/$note)
    if [ "$pre" != "$post" ]; then
        echo "BODY DIFFERS in $note — REVIEW IMMEDIATELY"
    else
        echo "Body unchanged: $note"
    fi
    cd ../..
done
# Expected: 3 lines reading "Body unchanged: ..."
```

If any line reports BODY DIFFERS, **HALT and escalate** — this would indicate the sed pattern matched somewhere unintended.

**Verify the placeholder is replaced with a valid SHA:**
```bash
for note in 2026-04-21-argus-audit-execution.md \
            2026-04-21-debrief-absorption.md \
            2026-04-21-phase-3-fix-generation-and-execution.md; do
    grep "Synthesis status" argus/workflow/evolution-notes/$note
done
# Expected output: each line shows commit <40-char hex SHA>, NO placeholder
grep -c "pending-final-synthesis-sprint-commit" argus/workflow/evolution-notes/2026-04-21-*.md
# Expected: 0
```

### Sub-Phase 3: Optional verifications (no edits expected)

These are no-edit verifications per `doc-update-checklist.md` Section B3, B4, B5, B6, B7. Document the outcomes in the post-sprint doc-sync close-out for the audit trail.

**B3 — VERSIONING.md current-version line:**
```bash
grep "Current Version" -A1 argus/workflow/VERSIONING.md
# Expected: still "v1.0.0 — Initial extraction from ARGUS (March 2026)"
# Recommendation: leave untouched (deferred reconciliation; logged in close-out)
```

**B4 — CLASSIFICATION.md:** No update needed (one-time migration mapping; new content is metarepo-native). Confirm `git diff HEAD argus/workflow/CLASSIFICATION.md` returns empty.

**B5 — MIGRATION.md:** No update needed. Confirm `git diff HEAD argus/workflow/MIGRATION.md` returns empty.

**B6 — evolution-notes/README.md:** Verify the synthesis-status convention documented in Session 2 matches the actual format applied to the 3 notes:
```bash
# Format from convention
grep -A2 "format is:" argus/workflow/evolution-notes/README.md | head -5

# Format actually applied
grep "Synthesis status" argus/workflow/evolution-notes/2026-04-21-argus-audit-execution.md
```
Should align (`SYNTHESIZED in <sprint> (commit <SHA>)`).

**B7 — bootstrap-index.md last-updated date:** Recommendation per `doc-update-checklist.md` is to skip (the file currently has no version header; adding one is a meta-decision deferred to a future strategic check-in). Document this as a deferred observation in the close-out.

### Sub-Phase 4: Cross-reference final integrity sweep (Section B8)

Run the cross-reference resolution sweep across all files modified or created in this sprint:

```bash
cd argus/workflow

# Find all files modified in the synthesis sprint commits
SPRINT_FILES=$(git log --since=2026-04-26 --pretty=format:"" --name-only | sort -u | grep -v "^$")
echo "Files modified in sprint:"
echo "$SPRINT_FILES"
echo ""

# Check cross-references in each
echo "=== Cross-reference resolution check ==="
for f in $SPRINT_FILES; do
    if [ -f "$f" ]; then
        BROKEN=$(grep -oE "(protocols/|templates/|claude/(skills|rules|agents)/|schemas/|scripts/|scaffold/|evolution-notes/|runner/)[a-z0-9_-]+\.(md|py|sh|yaml)" "$f" | sort -u | while read ref; do
            if [ ! -e "$ref" ]; then
                echo "  BROKEN in $f → $ref"
            fi
        done)
        if [ -n "$BROKEN" ]; then
            echo "$BROKEN"
        fi
    fi
done

cd ../..
```

**Expected:** No "BROKEN in ..." output. If any broken references found, route them via either:
- A small follow-on commit to fix the reference (if the broken-link target exists at a different path).
- A deferred observation entry (if the link is a known-future-work reference that should be a TODO).

### Sub-Phase 5: Argus-side reconciliation

#### Step 5a: Submodule pointer advancement

If you've run Sub-Phases 1 + 2, the metarepo has new commits not yet reflected in the argus submodule pointer. Advance:

```bash
cd argus/workflow
git add README.md evolution-notes/2026-04-21-*.md
git commit -m "docs(synthesis-2026-04-26): post-sprint doc-sync — README counts + evolution-note SHA resolution"
git push origin main

cd ..
git add workflow
```

(Don't commit yet — Sub-Phase 5b adds the argus-side DEF entry to the same commit.)

#### Step 5b: Argus deferred-items entry for boot-commit-logging

In argus's deferred-items document (typical locations: `argus/CLAUDE.md` Deferred Items section, or `argus/docs/risk-register.md`, or `argus/docs/argus-defs.md` — operator's project organization varies). Locate the existing pattern + add a new DEF entry.

The next available DEF number — find it via:
```bash
grep -hE "^(DEF|### DEF)-[0-9]+" argus/CLAUDE.md argus/docs/*.md 2>/dev/null | grep -oE "DEF-[0-9]+" | sort -V | tail -3
# Expected: shows the highest-numbered existing DEFs
```

Use the next available integer as the new DEF number. (Per project knowledge, ARGUS is currently around DEF-205+; verify before assuming.)

Add the entry:

```markdown
### DEF-XXX: Boot-commit logging automation

**Status:** OPEN (post-31.9 deferred)
**Priority:** Low — current manual approach works; automation is a quality-of-life improvement.
**Origin:** synthesis-2026-04-26 Phase A pushback round 2.

**Description:** ARGUS currently records the execution-anchor commit (HEAD SHA at startup) manually before each operational session. The metarepo's `protocols/operational-debrief.md` §2 documents this as a recommended automation: the live system should write the execution-anchor commit to a known location at startup so the operator doesn't have to remember.

**Suggested implementation:** Log the SHA in the lifespan startup phase (in `argus/main.py`'s lifespan function) to `logs/boot-history.jsonl`, one line per startup with timestamp + SHA + brief startup metadata (build version, environment, etc.).

**Trigger condition:** When the next argus session touches `argus/main.py` lifespan, fold in the boot-history logger.

**References:**
- `workflow/protocols/operational-debrief.md` §2 (Execution-Anchor Commit Correlation)
- `argus/docs/protocols/market-session-debrief.md` (the ARGUS-specific debrief consumes the boot-commit pair)
```

Replace `XXX` with the actual next DEF number.

#### Step 5c: Optional argus CLAUDE.md `## Rules` section (if Session 0 skipped)

```bash
grep -i "^## Rules$" argus/CLAUDE.md
```

If empty → add the section now. Insertion point: after a "Communication Style" or "Workflow" section, or at the end before any deferred-items table. Content:

```markdown
## Rules

This project follows the universal rules in `.claude/rules/universal.md` (auto-loaded by Claude Code at session start per the implementation-prompt template's Pre-Flight step). Project-specific rules live alongside in `.claude/rules/` (e.g., `backtesting.md` for ARGUS-specific patterns).

The keystone Pre-Flight wiring (in `templates/implementation-prompt.md` and `templates/review-prompt.md`) ensures every implementation and review session reads `universal.md` deterministically — universal RULEs apply regardless of whether they're inline-referenced in any specific prompt.
```

If `## Rules` already exists (Session 0 added it), skip — verify presence and document in close-out.

#### Step 5d: Commit argus-side changes

```bash
git add CLAUDE.md docs/  # adjust paths to wherever the DEF entry landed
git commit -m "docs(synthesis-2026-04-26): post-sprint argus reconciliation — submodule advance + DEF-XXX boot-commit-logging + optional Rules section"
git push
```

Wait for green CI on the argus push; record URL.

## Constraints

- **Do NOT modify** any path under `argus/argus/`, `argus/tests/`, `argus/config/`, `argus/scripts/`. Triggers escalation criterion A1.
- **Do NOT modify** Sessions 0–6 outputs beyond the explicit Sub-Phase 2 SHA resolution. Stable.
- **Do NOT modify** evolution-note bodies (still byte-frozen). Sub-Phase 2 ONLY changes the metadata header line.
- **Do NOT introduce** new RULEs, new protocols, new templates, or new scripts. This is a reconciliation pass, not new content.
- **Do NOT bump** workflow-version on any file unless a Sub-Phase explicitly requires it (Sub-Phase 1 doesn't bump README's version since README has no version header).
- **Do NOT update** VERSIONING.md "Current Version" line (deferred per `doc-update-checklist.md` Section B3 recommendation).
- **Do NOT add** version headers to files that lack them (CLASSIFICATION.md, MIGRATION.md, scaffold/CLAUDE.md, bootstrap-index.md — all decisions deferred to future strategic check-in).
- **Do NOT update** other-projects' submodule pointers (MuseFlow / Grove etc.). That's operator-direct per `doc-update-checklist.md` Section D.

## Test Targets

No executable code, no tests. Verification is grep + diff + ls based.

## Definition of Done

- [ ] Sub-Phase 1: README.md counts updated (19 protocols / 13 templates / 53 cross-project rules); scripts/ comment includes phase-2-validate.py
- [ ] Sub-Phase 2: All 3 evolution-note `<pending-final-synthesis-sprint-commit>` placeholders replaced with Session 1 SHA; evolution-note bodies byte-identical (verified)
- [ ] Sub-Phase 3: VERSIONING.md / CLASSIFICATION.md / MIGRATION.md / B6 verifications run; outcomes documented in close-out (deferred items logged)
- [ ] Sub-Phase 4: Cross-reference integrity sweep returns no broken links (or any broken links resolved)
- [ ] Sub-Phase 5a: Metarepo commits + push; argus submodule pointer advanced
- [ ] Sub-Phase 5b: Argus DEF-XXX boot-commit-logging entry added; DEF number doesn't collide
- [ ] Sub-Phase 5c: Argus CLAUDE.md `## Rules` section either confirmed-present or added
- [ ] Sub-Phase 5d: Argus commit + push; green CI
- [ ] Close-out report written to `argus/docs/sprints/synthesis-2026-04-26/post-sprint-doc-sync-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|---|---|
| Evolution-note bodies byte-identical | Sub-Phase 2 verification loop returns 3 "Body unchanged" lines |
| No safety-tag taxonomy reintroduced | `grep -E "safe-during-trading\|weekend-only\|read-only-no-fix-needed\|deferred-to-defs" argus/workflow/` returns matches ONLY in `protocols/codebase-health-audit.md` §2.9 |
| ARGUS runtime untouched | `cd argus && git diff HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/` returns empty |
| README counts match reality | Sub-Phase 1 verification commands all return expected values |
| All cross-references resolve | Sub-Phase 4 sweep returns no BROKEN |
| DEF number contiguous | New DEF doesn't skip or collide with existing argus DEFs |
| No new files in metarepo | `git status argus/workflow/` shows only modifications, no `??` (untracked) entries |

## Close-Out

Follow `.claude/skills/close-out.md`. Write to `argus/docs/sprints/synthesis-2026-04-26/post-sprint-doc-sync-closeout.md`.

**The close-out should include:**
- All Sub-Phase verifications + outputs
- The DEF number assigned for boot-commit-logging
- Confirmation of CLAUDE.md `## Rules` section (added or already-present)
- The Session 1 SHA used for placeholder resolution
- Any deferred observations (VERSIONING.md, bootstrap-index.md version header, etc.)
- Cross-reference sweep result

**The close-out's structured-closeout JSON appendix** completes the sprint record. After this commit, sprint synthesis-2026-04-26 is structurally complete.

## Tier 2 Review (Mandatory — @reviewer Subagent)

Standard invocation. Review writes to `argus/docs/sprints/synthesis-2026-04-26/post-sprint-doc-sync-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Evolution-note body byte-preservation** — Sub-Phase 2's sed operation must have ONLY changed the metadata header line on each of 3 notes.
2. **README counts match reality** — verifiable independently via `ls | wc -l` and `grep -c`.
3. **No drift outside scope** — only the explicit files in Sub-Phases 1, 2, 5b, 5c (optional) modified.
4. **DEF number contiguity** in the argus deferred-items addition.
5. **Cross-reference sweep** clean (no broken links across the entire post-sprint metarepo state).
6. **Stable VERSIONING.md / CLASSIFICATION.md / MIGRATION.md** — no edits.

## Sprint-End Final Steps

After this prompt completes successfully:

1. **Sprint summary.** Write `argus/docs/sprints/synthesis-2026-04-26/SPRINT-SUMMARY.md` per the work-journal-handoff.md "Sprint-End Wrap-Up" guidance.
2. **Mark sprint complete** in argus's CLAUDE.md "Active Sprint" section.
3. **Optional propagation** to MuseFlow / Grove / other projects (operator-direct, per `doc-update-checklist.md` Section D — discretionary).

The sprint is now durably complete. The next planning conversation can reference the new metarepo state (19 protocols, 13 templates, 53 RULEs, the keystone Pre-Flight wiring, the rejected safety-tag taxonomy guarded against by the codebase-health-audit §2.9 anti-pattern addendum) as authoritative.
