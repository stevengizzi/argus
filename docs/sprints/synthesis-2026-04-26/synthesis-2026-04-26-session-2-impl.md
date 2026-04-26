# Sprint synthesis-2026-04-26, Session 2: Mechanical Housekeeping (Templates + Scaffold + Evolution-Notes)

## Pre-Flight Checks

Before making any changes:

1. **Read `.claude/rules/universal.md` in full and treat its contents as binding for this session.** Per the keystone Pre-Flight wiring landed in Session 1, this read is now standard for every session — but worth re-asserting at the top of this session's prompt for clarity.

2. **Verify Session 1 has landed.** This session depends on the keystone wiring being committed (Session 2's Hybrid Mode addition cross-references the keystone behavior):
   ```bash
   cd argus/workflow
   grep -c "Read .*\.claude/rules/universal\.md" templates/implementation-prompt.md
   # Must return ≥ 1
   grep -c "^RULE-051:\|^RULE-052:\|^RULE-053:" claude/rules/universal.md
   # Must return 3
   cd ..
   ```
   If either check fails, Session 1 was not run or did not complete — **HALT and report**. Do not proceed (escalation criterion D1).

3. Read these files to load context:
   - `argus/docs/sprints/synthesis-2026-04-26/review-context.md` (full sprint contract, embedded)
   - `argus/workflow/templates/work-journal-closeout.md` (you'll be adding a Hybrid Mode section)
   - `argus/workflow/templates/doc-sync-automation-prompt.md` (you'll be adding a Between-Session Doc-Sync section)
   - `argus/workflow/scaffold/CLAUDE.md` (you'll be adding a `## Rules` section)
   - `argus/workflow/evolution-notes/README.md` (you'll be documenting the synthesis-status convention)
   - `argus/workflow/evolution-notes/2026-04-21-argus-audit-execution.md` (you'll be adding ONE metadata header line; body untouched)
   - `argus/workflow/evolution-notes/2026-04-21-debrief-absorption.md` (same)
   - `argus/workflow/evolution-notes/2026-04-21-phase-3-fix-generation-and-execution.md` (same)

4. Verify clean working tree in both argus and workflow submodule.

## Objective

Land seven mechanical extensions to existing metarepo files plus three additive metadata headers on the evolution notes:

1. Hybrid Mode section in `templates/work-journal-closeout.md` (covers non-standard-shape campaigns: audit, multi-sprint refactor, migration)
2. Between-Session Doc-Sync section in `templates/doc-sync-automation-prompt.md` (covers find/replace patches between sessions during a campaign)
3. `## Rules` section in `scaffold/CLAUDE.md` (defensive backup wiring for new projects bootstrapped after this sprint)
4. Synthesis-status convention documented in `evolution-notes/README.md`
5–7. `**Synthesis status:**` header line added to each of the 3 evolution notes (additive metadata only; bodies byte-frozen)

## Requirements

This session is structured into 4 sub-phases. Bodies of evolution notes must be preserved byte-for-byte; only the metadata header gets a new line.

### Sub-Phase 1: Hybrid Mode in work-journal-closeout.md

In `argus/workflow/templates/work-journal-closeout.md`:

Add a new section titled "## Hybrid Mode (Non-Standard-Shape Campaigns)" near the end of the template (after existing sections; before any closing template content). The section content:

```markdown
## Hybrid Mode (Non-Standard-Shape Campaigns)

[Use this section instead of the standard Work Journal close-out when the campaign is non-standard-shape — typically audit campaigns (20+ sessions, multi-stage, parallelism), multi-sprint refactors, or migrations. Standard sprints (3–8 serial sessions) use the close-out structure above; do not adopt Hybrid Mode for them.]

A non-standard-shape campaign produces a hybrid handoff document whose top half is campaign-specific and whose bottom half points at this template's standard close-out structure for the final session's deliverable. The campaign coordination surface (a Claude.ai Work Journal conversation, an issue tracker with a campaign label, or a wiki page with a running register — any persistent surface that tracks DEFs, findings, and produces a draftable handoff at close) reads the hybrid handoff once, then ingests paste-able close-out and review blocks from each session per `claude/skills/close-out.md` and `claude/skills/review.md`. At campaign end, the coordination surface produces a filled-in doc-sync prompt per `templates/doc-sync-automation-prompt.md` (human-in-the-loop mode) or a structured close-out block (autonomous mode).

Universal rules apply per the keystone Pre-Flight wiring in `templates/implementation-prompt.md` — the Hybrid Mode handoff does NOT need to re-document them.

### Hybrid Handoff Top Half (Campaign-Specific)

The top half of a hybrid handoff document captures (operator-judgment per campaign — these are typical fields, not a strict schema):

- **Baseline.** Test count, lockfile state, branch state, paper-trading or operational state at campaign start.
- **Multi-stage execution plan.** A list or DAG of sessions in dependency order; references `templates/stage-flow.md` for visual format if non-linear.
- **Paste protocol.** Where the operator pastes each session's close-out + review blocks (the campaign coordination surface).
- **Running register format.** DEFs, findings, deferred items, scope additions, judgment calls — accumulated across sessions, not per-session.
- **Escalation criteria specific to this campaign.** When to halt and route to the operator vs. continue with CONCERNS.
- **Campaign regression checklist.** Cross-cutting invariants the campaign must preserve.
- **Cross-track synthesis** (if multi-track campaign). The campaign's final session(s) produce a narrative covering all tracks plus any cross-track recommendations.

### Hybrid Handoff Bottom Half (Standard Close-Out Reference)

The bottom half of a hybrid handoff points at `templates/work-journal-closeout.md` (this file) §"Sprint summary" through §"Doc sync" for the final session's deliverable. The campaign's final session produces a standard work-journal close-out, just one that has been informed by the multi-session running register accumulated above.

### When NOT to use Hybrid Mode

- Standard sprints with 3–8 serial sessions and a single coordination surface.
- Single-session impromptus.
- Sprints where the work fits the standard close-out structure without modification.

If in doubt, use the standard close-out structure; switch to Hybrid Mode only when its accumulated-running-register pattern is clearly necessary.

<!-- Origin: synthesis-2026-04-26 N3.6. Evidence: ARGUS Sprint 31.9 campaign-
     close used a hybrid pattern — the standard work-journal-closeout
     template covered the final session's deliverable, but the campaign-
     internal artifacts (CAMPAIGN-CLOSE-PLAN.md, RUNNING-REGISTER.md,
     CAMPAIGN-COMPLETENESS-TRACKER.md) sat above it as the campaign-
     specific layer. Hybrid Mode formalizes that two-layer structure. -->
```

Bump the file's workflow-version header to next minor (e.g., 1.0.0 → 1.1.0) and update last-updated to 2026-04-26.

**Verification:**
```bash
grep -c "## Hybrid Mode" argus/workflow/templates/work-journal-closeout.md
# Expected: ≥ 1
grep -c "campaign coordination surface" argus/workflow/templates/work-journal-closeout.md
# Expected: ≥ 1 (per F1 generalized terminology)
```

### Sub-Phase 2: Between-Session Doc-Sync in doc-sync-automation-prompt.md

In `argus/workflow/templates/doc-sync-automation-prompt.md`:

Add a new section titled "## Between-Session Doc-Sync (Campaign Mode)" near the end of the template. The section content:

```markdown
## Between-Session Doc-Sync (Campaign Mode)

[The standard doc-sync template above covers post-sprint reconciliation. This subsection covers a different cadence: between-session doc-sync within a long-running campaign, where small targeted updates land between successive Claude Code sessions to keep CLAUDE.md and other coordination docs current with the running register.]

A between-session doc-sync prompt is a tiny, targeted operation. Unlike a full doc-sync (which reconciles everything at sprint close), a between-session doc-sync handles a specific small update — typically a DEF closure, a metric update (test count, file count), or a status-line refresh. It uses find/replace patches with explicit pre-state verification and post-state grep checks.

### Structure of a Between-Session Doc-Sync Prompt

```
# Between-Session Doc-Sync: <description>

## Pre-State Verification
[Grep commands the implementer runs first to confirm the document is in
the expected state before the patch lands. If the pre-state doesn't
match, halt and report.]

```bash
grep "<expected-string>" <file-path>
# Expected: <count>
```

## Patch
[Exact find/replace pairs. Use ` ```text ` blocks rather than diff syntax;
the implementer applies them via str_replace tools.]

**File:** `<path>`

**Find:** ...
**Replace with:** ...

## Post-State Verification
[Grep commands run after the patch to confirm the new state. Mirror the
pre-state checks.]

```bash
grep "<new-string>" <file-path>
# Expected: <count>
```

## Commit Message
[Exact commit message text the implementer should use.]

```
docs(<scope>): <short description>
```

## Report Back
[Specific paste-back format the implementer returns: confirmation that
pre-state matched, that patch landed, that post-state matched, and the
commit SHA.]
```

### When to Use Between-Session Doc-Sync

- During a long-running campaign with 5+ sessions where coordination docs (CLAUDE.md, sprint-history.md, etc.) drift between sessions.
- For mechanical updates that don't require operator judgment but DO require precision (specific find/replace with verifiable state transitions).
- To prevent end-of-sprint doc-sync from accumulating ~12 small edits in one session.

### When NOT to Use

- For substantive content changes that require operator judgment (use a full doc-sync session instead).
- For changes that touch multiple files (use a doc-sync session that handles them coherently).
- For tiny single-line changes during the implementer's own session — fold those into the session's own commits with the relevant changes.

<!-- Origin: synthesis-2026-04-26 P34. ARGUS Sprint 31.9 campaign-close ran
     ~12 between-session doc-sync prompts via the campaign-tracking
     conversation, each with this structure (pre-verify / patch / post-
     verify / commit / report-back). Existing doc-sync template covered
     sprint-end only; this addition covers campaign-internal cadence. -->
```

Bump version header to next minor.

**Verification:**
```bash
grep -c "## Between-Session Doc-Sync" argus/workflow/templates/doc-sync-automation-prompt.md
# Expected: ≥ 1
grep -c "Pre-State Verification\|Post-State Verification" argus/workflow/templates/doc-sync-automation-prompt.md
# Expected: ≥ 2 (one each)
```

### Sub-Phase 3: `## Rules` section in scaffold/CLAUDE.md

In `argus/workflow/scaffold/CLAUDE.md`:

Add a new `## Rules` section. The scaffold file is short and template-style; insert the section as a top-level heading near the top of the file (after the project-name placeholder header and before "## Active Sprint" — that placement makes Rules visible early in the per-project context Claude Code reads at session start).

Content:

```markdown
## Rules

This project follows the universal rules in `.claude/rules/universal.md` (auto-loaded by Claude Code at session start per the implementation-prompt template's Pre-Flight step). Project-specific rules live alongside in `.claude/rules/` (e.g., `<project>-specific.md`).

The keystone Pre-Flight wiring (in `templates/implementation-prompt.md` and `templates/review-prompt.md`) ensures every implementation and review session reads `universal.md` deterministically — universal RULEs apply regardless of whether they're inline-referenced in any specific prompt.

Do not enumerate specific RULEs in this section. Adding new RULEs to `universal.md` should not require updating every project's `CLAUDE.md`. The keystone Pre-Flight wiring is the propagation mechanism.
```

Note that the scaffold file does NOT have a workflow-version header currently (it's a template for new projects; it gets a per-project DATE header instead). Don't add a version header.

**Verification:**
```bash
grep -c "^## Rules$" argus/workflow/scaffold/CLAUDE.md
# Expected: ≥ 1
grep -c "Do not enumerate specific RULEs" argus/workflow/scaffold/CLAUDE.md
# Expected: ≥ 1
```

### Sub-Phase 4: Evolution-notes README synthesis-status convention + 3 evolution-note status headers

#### Step 4a: evolution-notes/README.md

In `argus/workflow/evolution-notes/README.md`:

Add a new section titled "## Synthesis Status Convention" between the existing "## Workflow: Extract → Synthesize → Implement" and "## Template" sections. Content:

```markdown
## Synthesis Status Convention

When a synthesis sprint consumes one or more evolution notes, the synthesizing sprint's first session updates each consumed note with a one-line `**Synthesis status:**` header at the top of the note's metadata block (the section above the first body `---` separator). The format is:

```
**Synthesis status:** SYNTHESIZED in <sprint-name> (commit <SHA>). See <protocol-or-template-path>, ... for the resulting metarepo additions.
```

Where:
- `<sprint-name>` is the synthesizing sprint's identifier (e.g., `synthesis-2026-04-26`).
- `<commit <SHA>>` is the metarepo commit that landed the synthesis (the principal fold-in commit; subsequent normalization commits are not cited here).
- The reference to resulting metarepo additions points at the highest-level outputs (typically protocol files; not every modified line).

A note's status header has these possible values:

| Status | Meaning |
|---|---|
| (no header) | PENDING — note has not been consumed by any synthesis sprint |
| `SYNTHESIZED in <sprint> (commit <SHA>)` | Note consumed; metarepo additions landed at the cited commit |
| `SUPERSEDED by <new-note>` | A later evolution note replaces this one (rare; use only when the original captured a fundamentally different framing later refined) |
| `DEFERRED PENDING <condition>` | Note has been read by a synthesis sprint but explicit deferral happened (e.g., a candidate pattern was reviewed and deferred to next strategic check-in) |

The body of an evolution note is byte-frozen after capture. The metadata header is the only mutable part; status updates are additive metadata, not body edits.

<!-- Origin: synthesis-2026-04-26 (this sprint introduces the convention).
     The 3 evolution notes from 2026-04-21 are the first to receive a
     SYNTHESIZED status header; future synthesis sprints follow the same
     pattern. -->
```

**Verification:**
```bash
grep -c "## Synthesis Status Convention" argus/workflow/evolution-notes/README.md
# Expected: ≥ 1
grep -c "PENDING\|SYNTHESIZED\|SUPERSEDED\|DEFERRED PENDING" argus/workflow/evolution-notes/README.md
# Expected: ≥ 4 (the table rows)
```

#### Step 4b: Add `**Synthesis status:**` header to each of the 3 evolution notes

For each of the 3 evolution notes in `argus/workflow/evolution-notes/`:

- `2026-04-21-argus-audit-execution.md`
- `2026-04-21-debrief-absorption.md`
- `2026-04-21-phase-3-fix-generation-and-execution.md`

Locate the metadata header block at the top of the file (lines containing `**Date:**`, `**Conversation title:**`, `**Contributes to:**`). After the last existing metadata line and BEFORE the first `---` separator that begins the body, insert ONE new line:

```
**Synthesis status:** SYNTHESIZED in synthesis-2026-04-26 (commit <S2-METAREPO-COMMIT-SHA>). See `protocols/campaign-orchestration.md`, `protocols/operational-debrief.md`, `protocols/codebase-health-audit.md` for the resulting metarepo additions.
```

**Note on commit SHA:** The synthesis sprint's metarepo commits land progressively across Sessions 1–6. At the time of this Session 2 edit, only Session 1's metarepo commit exists. Two options:

(a) Use a placeholder `<commit SHA pending Sessions 3+>` and have the post-sprint doc-sync prompt (Section B of doc-update-checklist.md) update it to the final synthesis-sprint principal commit SHA.

(b) Use the Session 1 commit SHA (the keystone-wiring commit) as the synthesis sprint's anchor. Every subsequent session advances the metarepo, but Session 1 is when the sprint structurally took effect.

**Recommendation: (a)** — placeholder. The post-sprint doc-sync sweep updates the SHA once the full synthesis lands. This keeps the SHA reference accurate.

**Implementation:** insert the header line with literal text `(commit <pending-final-synthesis-sprint-commit>)`. Document in close-out that the placeholder is intentional and points at Section B post-sprint doc-sync for resolution.

**Critical: do NOT modify any body content.** The body of each note is everything below the first `---` separator. Body lines must be byte-identical to pre-session HEAD.

**Verification:**
```bash
for note in 2026-04-21-argus-audit-execution.md \
            2026-04-21-debrief-absorption.md \
            2026-04-21-phase-3-fix-generation-and-execution.md; do
    grep -c "^**Synthesis status:**" argus/workflow/evolution-notes/$note
    # Expected: 1 per file
done

# Critically: verify bodies are unchanged
for note in 2026-04-21-argus-audit-execution.md \
            2026-04-21-debrief-absorption.md \
            2026-04-21-phase-3-fix-generation-and-execution.md; do
    pre=$(git show HEAD:workflow/evolution-notes/$note 2>/dev/null | awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==1){p=1; next}} p')
    post=$(awk 'BEGIN{p=0; sep=0} /^---$/{sep++; if(sep==1){p=1; next}} p' argus/workflow/evolution-notes/$note)
    if [ "$pre" != "$post" ]; then
        echo "BODY DIFFERS in $note — REVIEW IMMEDIATELY"
    else
        echo "Body unchanged: $note"
    fi
done
# Expected: 3 lines reading "Body unchanged: ..."
```

Capture all verification outputs in close-out.

## Constraints

- **Do NOT modify** any path under `argus/argus/`, `argus/tests/`, `argus/config/`, `argus/scripts/`. Triggers escalation criterion A1.
- **Do NOT modify** any line below the first `---` separator in any of the 3 evolution notes. Body content is byte-frozen. Triggers escalation criterion A2.
- **Do NOT modify** files outside the explicit list (`work-journal-closeout.md`, `doc-sync-automation-prompt.md`, `scaffold/CLAUDE.md`, `evolution-notes/README.md`, 3 evolution notes). Any other file modified triggers scope-creep escalation per D3.
- **Do NOT modify** Session 1's outputs (universal.md, close-out.md, implementation-prompt.md, review-prompt.md). They are stable; do not "improve" them.
- **Do NOT enumerate specific RULEs** in `scaffold/CLAUDE.md`'s `## Rules` section. The keystone wiring propagates RULEs without per-project enumeration.
- **Do NOT add** workflow-version headers to files that don't have them currently (scaffold/CLAUDE.md is template-style; bootstrap-index.md decision deferred to a future strategic check-in).

## Test Targets

No executable code, no tests. Verification is grep-based per sub-phase + body-byte-preservation diff for evolution notes.

## Definition of Done

- [ ] Sub-Phase 1: Hybrid Mode section in `work-journal-closeout.md`; uses "campaign coordination surface" terminology (F1); version header bumped
- [ ] Sub-Phase 2: Between-Session Doc-Sync section in `doc-sync-automation-prompt.md`; version header bumped
- [ ] Sub-Phase 3: `## Rules` section in `scaffold/CLAUDE.md`; no enumeration of specific RULEs
- [ ] Sub-Phase 4a: Synthesis Status Convention section in `evolution-notes/README.md` with 4-row status table
- [ ] Sub-Phase 4b: All 3 evolution notes have `**Synthesis status:**` header line; bodies byte-identical to pre-session HEAD (verified by diff)
- [ ] All verification grep + body-diff commands run; outputs captured in close-out
- [ ] No scope creep beyond the explicit file list
- [ ] Close-out report written to `argus/docs/sprints/synthesis-2026-04-26/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| Evolution-note bodies byte-identical | Run the per-note body-diff loop in Sub-Phase 4b verification; expect 3 "Body unchanged" lines |
| Session 1 outputs untouched | `git diff HEAD workflow/claude/rules/universal.md workflow/claude/skills/close-out.md workflow/templates/implementation-prompt.md workflow/templates/review-prompt.md` returns empty |
| ARGUS runtime untouched | `git diff HEAD --name-only -- argus/argus/ argus/tests/ argus/config/ argus/scripts/` returns empty |
| F1 generalized terminology | Hybrid Mode section uses "campaign coordination surface" not "Work Journal conversation" exclusively (Work Journal mentioned as one example) |
| Version bumps applied | work-journal-closeout.md and doc-sync-automation-prompt.md have minor version bumps; scaffold/CLAUDE.md has no version (correct for template) |
| No new RULE numbers | universal.md unchanged from Session 1 |

## Close-Out

Follow `.claude/skills/close-out.md`. Verify the strengthened Step 3 (FLAGGED-blocks-stage-commit-push from Session 1) before staging.

Write close-out to `argus/docs/sprints/synthesis-2026-04-26/session-2-closeout.md`.

**Commit pattern:**
```bash
cd argus/workflow
git add templates/work-journal-closeout.md templates/doc-sync-automation-prompt.md scaffold/CLAUDE.md evolution-notes/README.md evolution-notes/2026-04-21-*.md
git commit -m "synthesis-2026-04-26 S2: Hybrid Mode + Between-Session Doc-Sync + scaffold ## Rules + evolution-notes synthesis status convention"
git push origin main

cd ..
git add workflow docs/sprints/synthesis-2026-04-26/session-2-closeout.md
git commit -m "synthesis-2026-04-26 S2: advance workflow submodule + close-out report"
git push
```

Wait for green CI; record URL in close-out.

## Tier 2 Review (Mandatory — @reviewer Subagent)

After commits + green CI, invoke @reviewer.

Provide:
1. Review context: `argus/docs/sprints/synthesis-2026-04-26/review-context.md`
2. Close-out: `argus/docs/sprints/synthesis-2026-04-26/session-2-closeout.md`
3. Diff range: metarepo (`cd workflow && git diff HEAD~1`) + argus (`git diff HEAD~1`)
4. Files NOT to have been modified: anything outside the 7 listed

@reviewer writes review report to `argus/docs/sprints/synthesis-2026-04-26/session-2-review.md`.

## Post-Review Fix Documentation

Standard post-review-fix loop if CONCERNS reported (see implementation-prompt.md template — note the keystone Pre-Flight wiring landed in Session 1 means @reviewer will already have the universal-rules context).

## Session-Specific Review Focus (for @reviewer)

1. **Evolution-note body byte-preservation** — highest-priority check. Diff each of the 3 notes; the diff must show ONLY the `**Synthesis status:**` line addition in the metadata block. Any change to lines below the first `---` separator is ESCALATE per criterion A2.
2. **F1 generalized-terminology coverage** in the Hybrid Mode section — uses "campaign coordination surface" with examples; does not mandate Work Journal conversation as the universal pattern.
3. **Synthesis Status Convention has the 4-row status table** with PENDING / SYNTHESIZED / SUPERSEDED / DEFERRED PENDING.
4. **Scaffold `## Rules` section does NOT enumerate specific RULEs** — defensive against future maintenance burden.
5. **Session 1 outputs untouched** (Session 2 doesn't drift back into Session 1's files).
6. **Placeholder commit SHA** in evolution-note headers — the close-out should explicitly note that `<pending-final-synthesis-sprint-commit>` is intentional and points at post-sprint doc-sync (Section B of doc-update-checklist.md) for resolution.

## Sprint-Level Regression Checklist (for @reviewer)

See review-context.md §"Embedded Document 3." For Session 2: R3 (evolution-note bodies — primary check), R5 (RETRO-FOLD-touched skills/templates), R8 (workflow-version), R10 (symlinks), R20 (ARGUS runtime), R16 (close-out file).

## Sprint-Level Escalation Criteria (for @reviewer)

See review-context.md §"Embedded Document 4." For Session 2: A2 (evolution-note body modification — highest risk this session), A1 (ARGUS runtime modified), C3 (compaction signals).
