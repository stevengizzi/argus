# Sprint 31.9 RETRO-FOLD: P1–P25 Campaign Lessons → `claude-workflow` Metarepo

> Drafted Phase 2. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other session prompts in this campaign. **Cross-repo session** — touches `workflow/` submodule; this is the one session in the campaign where RULE-018 does not apply by definition.

## Scope

**Finding addressed:**
The Sprint 31.9 campaign accumulated 25 lessons (P1–P25) captured in
`docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md`. These lessons
are project-specific in their capture but universal in their applicability —
they need to land in the `claude-workflow` metarepo so future sprints and
future projects benefit. The fold-in is the bridge from "local campaign
learning" to "universal protocol knowledge."

**Target repo:** `github.com/stevengizzi/claude-workflow`

**Files likely touched (in the metarepo):**
- `protocols/*.md` — existing protocols gain new invariants from specific P-lessons
- `templates/*.md` — existing templates absorb patterns (e.g., P24 sys.modules mock technique)
- `rules/*.md` (if exists) — lessons that are universal rules get new RULE-NNN entries
- `CHANGELOG.md` (or equivalent) — tracks the fold-in across protocol/template versions
- Possibly new files: if a lesson warrants its own protocol/template (e.g., "canary-test-for-safety-fix.md"), create it

**Files likely touched (in argus):**
- `workflow/` submodule pointer bumped to new metarepo commit SHA
- `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — annotate each P-lesson with its metarepo destination (protocol file + commit SHA)
- `docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md` (NEW — close-out)

**Safety tag:** `safe-during-trading` — metarepo edits don't affect the argus runtime. The submodule pointer bump is a commit that only updates git metadata. Paper trading continues.

**Theme:** Convert specific P1–P25 lessons into general protocol/template/rule updates in the workflow metarepo, preserving the specific-project context as a cross-reference so future maintainers can trace each addition back to its origin sprint.

## Unique Context

This is the ONLY session in the campaign where:
- You WILL modify `workflow/` content (exception to RULE-018 by design)
- You WILL push to `claude-workflow` remote (the metarepo), not just argus
- Your commits span TWO repos — `claude-workflow` (the content) + argus (the submodule pointer bump)
- The review profile is ADAPTED — metarepo quality criteria are somewhat different from argus-code quality criteria

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline — OK"
# Paper trading continues.
```

### 2. Verify metarepo access + submodule state

```bash
# Submodule status
cd /home/claude/argus
git submodule status workflow
# Expected: a SHA + path + branch indicator

# Enter the submodule
cd workflow
git status
git branch --show-current
# Expected: clean + on main (or whatever metarepo branch is canonical)

# Verify remote access:
git remote -v
# Expected: origin = github.com/stevengizzi/claude-workflow.git

git fetch origin
git log --oneline -3
# Expected: recent metarepo history visible

cd ..  # back to argus root
```

If the submodule is detached-HEAD, checkout the canonical branch (likely `main`) in the submodule before proceeding.

### 3. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count: __________ (baseline)
```

Not strictly required (this session modifies docs/protocols, not argus code), but useful to confirm the submodule pointer bump at session end doesn't break anything.

### 4. Branch & workspace

In argus (work directly on `main` per campaign pattern):
```bash
git checkout main
git pull --ff-only
git status  # Expected: clean
```

In the workflow metarepo (inside `argus/workflow/`):
```bash
cd workflow
git checkout main
git pull --ff-only
git status  # Expected: clean
```

## Pre-Flight Context Reading

1. Read these files:
   - `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md` — P1–P25 lessons. This is the canonical source. Every P-entry includes (a) the lesson text, (b) the session where it was learned, (c) why it matters universally.
   - `docs/sprints/sprint-31.9/CAMPAIGN-CLOSE-PLAN.md` §"RETRO-FOLD" — if the plan pre-specified target files for specific lessons, follow those.
   - `bootstrap-index.md` — the index of metarepo protocols. Understand the existing taxonomy (protocols vs templates vs schemas).
   - Inside the workflow submodule:
     - `workflow/protocols/*.md` — scan titles; understand which protocols exist and their coverage
     - `workflow/templates/*.md` — scan titles
     - `workflow/CHANGELOG.md` if present — understand the format and rhythm of past updates

2. For each of P1–P25, pre-classify the landing target:
   - **Protocol update** — lessons that refine existing protocols (e.g., "sprint planning should add X step")
   - **Template update** — lessons that belong in templates (e.g., "implementation-prompt.md should include canary-test requirement")
   - **New rule** — universal "always do X" or "never do X" statements (e.g., P25 "green CI must be verified before next session")
   - **New protocol/template** — lessons substantive enough to warrant their own file
   - **Not fold-able** — too project-specific to generalize (defer to argus-only doc)

## Objective

1. Land all 25 P-lessons in the `claude-workflow` metarepo — each either in an
   updated existing file or as a new file. No lesson is dropped silently; if
   a lesson is deemed not-generalizable, that decision is documented in the
   close-out.
2. Bump the argus `workflow/` submodule pointer to the new metarepo commit SHA.
3. Cross-annotate `CAMPAIGN-COMPLETENESS-TRACKER.md` so each P-lesson has a
   pointer to its metarepo destination.
4. Push to both repos. Metarepo gets a meaningful tag (e.g., `sprint-31.9-retro`) if the project uses tags.

## Requirements

### Requirement 1: Pre-classification matrix

Before editing anything, produce a classification matrix of all 25 lessons. Format:

```markdown
| P # | Lesson (1-line) | Target file | Update type | Rationale |
|-----|-----------------|-------------|-------------|-----------|
| P1  | ...             | protocols/sprint-planning.md | section addition | Sprint-planning phase B... |
| P2  | ...             | templates/implementation-prompt.md | new subsection | ... |
| ... |                 |             |             |             |
```

This matrix is the plan. Put it in the close-out as §2. If during fold-in you discover a lesson's target was misclassified, update the matrix + proceed.

### Requirement 2: Fold each lesson

For each P-lesson, perform the classified update:

**Pattern A — Section addition to existing file:**
1. Open the target file
2. Identify the semantically appropriate section (or add a new section)
3. Add the lesson content, generalized (strip argus-specific names; keep the pattern/principle)
4. Add a "Background" footnote or inline reference to the sprint where it was learned: `<!-- Added from Sprint 31.9 campaign retro (P{N}). Context: {brief}. -->`

**Pattern B — New rule in a rules file:**
1. Identify the rules file (either a general one or a protocol-specific one)
2. Assign next sequential `RULE-NNN` ID
3. Write the rule as an imperative statement with rationale
4. Cross-reference any existing protocol/template that should cite it

**Pattern C — New protocol/template file:**
1. Create the file with a descriptive name
2. Structure follows existing conventions (frontmatter + body + appendices)
3. Register in `bootstrap-index.md` (or the metarepo's equivalent index)
4. Link from any existing files that now depend on the new one

**Pattern D — Documented deferral:**
If a lesson is genuinely not generalizable, write a close-out note explaining why, and add the lesson to `docs/` (argus-side) as an argus-specific note file. Do NOT simply drop it.

### Requirement 3: Preserve the specific-context cross-reference

Universal protocols lose their force if readers can't find the concrete example that motivated them. For each P-lesson landed in the metarepo, the updated section MUST include a brief "Origin" or "Background" footnote:

```markdown
<!-- Origin: Sprint 31.9 campaign retro, P24. Learned during FIX-13a
     when a coverage-only import in test_main.py tripped a fork worker
     hang that the sys.modules mock technique solved. -->
```

This is non-negotiable — the traceability is what makes retro-folded lessons
credible to future maintainers. Without origin context, lessons look like
arbitrary rules.

### Requirement 4: Argus-side cross-annotation

In `docs/sprints/sprint-31.9/CAMPAIGN-COMPLETENESS-TRACKER.md`, for each P-lesson entry, append a line:
```
**Landed in metarepo:** `{file}` §{section}, commit `{metarepo-SHA}`.
```

This closes the loop — operators reading the argus tracker can trace forward to the metarepo landing.

### Requirement 5: Submodule pointer bump

After all metarepo commits land + push to `origin/main` on the metarepo:

```bash
cd /home/claude/argus
cd workflow
git pull --ff-only  # Get the landed retro commits
cd ..
git add workflow
git commit -m "chore(workflow): bump submodule to sprint-31.9 retro fold-in"
git push origin main
```

### Requirement 6: Metarepo tag (optional, follow project convention)

If the metarepo uses tags (check existing tag history), tag the retro-fold-in commit:
```bash
cd workflow
git tag sprint-31.9-retro-fold
git push origin sprint-31.9-retro-fold
```

### Requirement 7: bootstrap-index.md update

If new protocol/template files were created, `bootstrap-index.md` must list them. This is the operator's top-level map; omissions there make the new content invisible.

## Constraints

- **Do NOT modify** any argus runtime code, tests, or configs. The argus side of this session is exactly: the submodule pointer bump + the CAMPAIGN-COMPLETENESS-TRACKER annotations. No more.
- **Do NOT generalize** lessons beyond what's supported by the campaign's actual evidence. If a lesson applies in 1 specific scenario, don't write it as a universal rule.
- **Do NOT drop** lessons silently. Every P-lesson has a named disposition: folded into X, or explicitly deferred with reason.
- **Do NOT rewrite** existing protocols beyond the addition of new content. If a section needs substantive restructuring to accommodate a new lesson, flag it and defer — this session is additive, not reformative.
- **Do NOT mix** metarepo commits with argus commits. The metarepo repo gets its own commit series; argus gets exactly one commit (submodule pointer bump) + one more (tracker annotations).
- **Do NOT push** to the metarepo from a non-main branch without explicit sanctioning. If any protocol change is contested, land on a feature branch and note in the close-out; operator may review before merge.
- Work on `main` in both repos unless a specific lesson demands otherwise.

## Test Targets

- pytest full suite unchanged (no argus code touched beyond submodule + tracker)
- No new tests in argus
- Metarepo side has no tests (it's documentation)

## Definition of Done

- [ ] Pre-classification matrix exists (in close-out)
- [ ] All 25 P-lessons have a named disposition
- [ ] Metarepo commits landed + pushed to `origin/main` on `claude-workflow`
- [ ] Metarepo tag created + pushed (if project uses tags)
- [ ] Each metarepo addition has an "Origin" / "Background" footnote
- [ ] `bootstrap-index.md` updated if new files were added
- [ ] Argus `workflow/` submodule pointer bumped + committed + pushed
- [ ] `CAMPAIGN-COMPLETENESS-TRACKER.md` cross-annotated with metarepo destinations
- [ ] `RUNNING-REGISTER.md` — RETRO-FOLD row complete with both repos' commit SHAs
- [ ] Close-out at `docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md`
- [ ] Tier 2 review at `docs/sprints/sprint-31.9/RETRO-FOLD-review.md`
- [ ] Full pytest suite passes (green CI URL cited — sanity check, not direct gate)

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| All 25 P-lessons have a classification matrix entry | Count rows |
| All 25 have a metarepo landing (or explicit deferral) | Per-entry read |
| Each metarepo addition has Origin footnote | Grep for "Origin:" in metarepo diff |
| bootstrap-index.md reflects any new files | Diff check |
| Argus submodule pointer matches latest metarepo main | `git submodule status workflow` |
| Tracker cross-annotations land in argus commit | Grep for "Landed in metarepo" |
| No argus code/tests/configs modified | `git diff argus/ config/ tests/ -- ':!workflow'` empty |
| pytest full suite passes | Test count unchanged |

## Close-Out

Write close-out to: `docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md`

Include:
1. **Pre-classification matrix** (full 25 rows)
2. **Metarepo commit series** — ordered list of commit SHAs + one-line descriptions
3. **Argus commit series** — submodule pointer bump SHA + tracker annotation SHA
4. **Metarepo tag (if created)** — tag name + SHA
5. **Deferred lessons (if any)** — explicit list with reasoning
6. **bootstrap-index.md diff summary** — what entries were added
7. **Green CI URL** for argus post-submodule-bump (sanity check)

## Tier 2 Review (Mandatory — @reviewer subagent, adapted profile)

The metarepo review profile differs from argus-code: focus on taxonomy + generalization quality + traceability, not on test coverage or runtime safety.

Invoke @reviewer after close-out.

Provide:
1. Review context: this kickoff + CAMPAIGN-COMPLETENESS-TRACKER.md (P1–P25 source)
2. Close-out path: `docs/sprints/sprint-31.9/RETRO-FOLD-closeout.md`
3. Two diff ranges:
   - Argus: `git log --oneline origin/main -5`
   - Metarepo: `cd workflow && git log --oneline origin/main -20`
4. Files that should NOT have been modified in argus:
   - Any `argus/` code file
   - Any `config/` file
   - Any `tests/` file
   - Any argus `docs/*` file OTHER than CAMPAIGN-COMPLETENESS-TRACKER.md, RUNNING-REGISTER.md, and the two close-out/review files
   - Any audit-2026-04-21 doc back-annotation

The @reviewer writes to `docs/sprints/sprint-31.9/RETRO-FOLD-review.md`.

## Session-Specific Review Focus (for @reviewer)

1. **Verify all 25 lessons are accounted for.** Any unfolded lesson must have explicit deferral rationale.
2. **Verify each metarepo addition has Origin traceability.** Footnote grep: every new or modified section in the metarepo should cite P{N} origin.
3. **Verify generalization quality.** Pick 3 random lessons and check that the metarepo wording doesn't overreach: "when X, consider Y" generalized from "in Sprint 31.9, doing X in FIX-13a-CI-hotfix worked" is fine; "always do Y everywhere" from a single instance is not.
4. **Verify bootstrap-index.md completeness.** New files in the metarepo must be index-listed.
5. **Verify submodule pointer actually advanced.** The argus commit must bump the SHA to a REAL metarepo commit that EXISTS on `origin/main`.
6. **Verify no argus runtime change.** Strict diff check.
7. **Verify tag (if used) matches convention.** Don't invent a new tag style if the metarepo has a prior convention.

## Sprint-Level Regression Checklist (for @reviewer)

- pytest net delta = 0
- Vitest count unchanged
- No argus scope violation
- Two-repo commit series is internally consistent (argus pointer matches metarepo SHA)

## Sprint-Level Escalation Criteria (for @reviewer)

Trigger ESCALATE if ANY of:
- Lessons dropped without explicit deferral
- Metarepo addition missing Origin footnote
- bootstrap-index.md NOT updated when new files added
- Submodule pointer points at a SHA not on metarepo `origin/main`
- Argus code/tests/configs modified
- Audit-report back-annotation modified
- Overreach in generalization (rule applied too broadly for the evidence)
- pytest full suite broken by submodule bump

## Post-Review Fix Documentation

Standard protocol.

## Operator Handoff

1. Close-out markdown block
2. Review markdown block
3. **Metarepo changes summary** — N files modified, M new files, K new RULE-NNN entries
4. **Argus changes summary** — 1 submodule bump + 1 tracker annotation commit
5. **Metarepo tag** (if created)
6. **Deferred lessons** (if any, listed)
7. Green CI URL (argus-side sanity check)
8. One-line summary: `Session RETRO-FOLD complete. Close-out: {verdict}. Review: {verdict}. Metarepo commits: {N} on `claude-workflow`. Argus commits: {argus-SHA-1, argus-SHA-2}. All 25 P-lessons landed (or explicitly deferred). CI: {URL}.`
