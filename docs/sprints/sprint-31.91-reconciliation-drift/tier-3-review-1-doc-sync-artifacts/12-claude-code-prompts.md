# Patch 12 — Claude Code Prompts (READY FOR COPY-PASTE)

**Two prompts.** Run them in the order below. Each is scoped to a single repo and produces a single commit.

**Why two prompts and not one:** The ARGUS-repo work and the metarepo work are genuinely different things — different review templates, different commit messages, different audiences. Bundling them creates a long mouthful commit and forces the @reviewer subagent to context-switch between two review postures. Splitting respects the protocol boundary cleanly.

---

## PROMPT 1 — ARGUS Repo (run from your `argus` working directory)

**Estimated runtime:** 5-10 minutes (Claude Code reads, applies 9 patches, validates, invokes @reviewer, commits).
**What you'll be asked to confirm:** the diff before commit; potentially clarifications if any anchor verification fails.

### Pre-flight (you do these once before launching Claude Code):

1. Confirm you are on `main` and at the Tier 3 anchor commit:

   ```bash
   cd /path/to/argus
   git status
   # Expected: "On branch main" and "Your branch is up to date with 'origin/main'"
   git log -1 --oneline
   # Expected: bf7b869 docs(sprint-31.91): session 1c Tier 2 review verdict (CLEAR)
   ```

2. Confirm the doc-sync artifacts directory is accessible. **Place the entire `doc-sync-artifacts/` directory somewhere Claude Code can read it** — typical convention is to drop it in the repo root as a sibling of `docs/`, or under `docs/sprints/sprint-31.91-reconciliation-drift/` for clean filing:

   ```bash
   # Option A (transient, easy to clean up): drop at repo root
   cp -r ~/Downloads/doc-sync-artifacts /path/to/argus/

   # Option B (filed in sprint folder, survives the doc-sync as a record):
   mkdir -p /path/to/argus/docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts
   cp ~/Downloads/*.md /path/to/argus/docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts/
   ```

   **Option B is cleaner** — the artifacts become part of the repo record permanently. Option A requires you to delete the directory before commit so it doesn't show up in `git status`. **The prompt below assumes Option B.** Adjust the paths if you choose Option A.

3. Tests should be green at this commit (pre-flight sanity):

   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -q
   # Expected: 5,128 passed (per Session 1c close-out).
   ```

### The prompt (paste this entire block into Claude Code):

```
SPRINT 31.91 TIER 3 REVIEW #1 — DOC-SYNC PASS (ARGUS REPO)

You are executing a documentation-only sync pass against the ARGUS repo on `main`. This pass implements the documentation commitments surfaced by Sprint 31.91 Tier 3 architectural review #1 (Sessions 0+1a+1b+1c, OCA architecture, verdict PROCEED 2026-04-27 at anchor commit bf7b869).

Pre-flight:

1. Read .claude/rules/universal.md in full. RULE-038 (anchor verification before edits), RULE-019 (NEVER delete tests), RULE-050 (CI green required), RULE-007 (no scope creep).

2. Read these files to load context:
   - CLAUDE.md (the canonical context file you are about to amend)
   - docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md (Sprint 31.91 sprint spec — for cross-referencing scope)
   - docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts/00-APPLY-ORDER-AND-INSTRUCTIONS.md (the apply order; updated below to reflect 9 patches)

3. Verify branch is `main`, working tree is clean, latest commit is bf7b869:
   git status
   git log -1 --oneline
   If any of these fail, halt and report.

4. Run scoped tests to confirm green starting state:
   python -m pytest --ignore=tests/test_main.py -n auto -q
   Expected: 5,128 passed. If not, halt and report.

Apply the 10 patches in the doc-sync-artifacts directory in the order below. The apply order is intentionally serialized:

  Order  | Patch file                                           | Target file (or action)
  -------|------------------------------------------------------|-------------------------------------------------------
   1     | 10-tier-3-review-1-verdict.create.md                 | CREATE NEW FILE: docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md
   2     | 01-decision-log.md.patch.md                          | EDIT: docs/decision-log.md
   3     | 02-dec-index.md.patch.md                             | EDIT: docs/dec-index.md
   4     | 04-architecture.md.patch.md                          | EDIT: docs/architecture.md
   5     | 06-risk-register.md.patch.md                         | EDIT: docs/risk-register.md
   6     | 05-pre-live-transition-checklist.md.patch.md         | EDIT: docs/pre-live-transition-checklist.md
   7     | 07-live-operations.md.patch.md                       | EDIT: docs/live-operations.md
   8     | 08-project-knowledge.md.patch.md                     | EDIT: docs/project-knowledge.md
   9     | 09-session-5a.1-impl-prompt.amendment.md             | EDIT: docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5a.1-impl.md
  10     | 03-CLAUDE.md.patch.md                                | EDIT: CLAUDE.md (LAST — most-read file landed last for consistency during pass)

For EACH patch:

a. Read the patch file. Identify the "Anchor verification" section. Read the target file in the cited line ranges to confirm the cited text matches verbatim.

b. If anchors don't match (drift from another commit), DO NOT silently re-anchor. Report the drift, name which patch, name which file, name what was expected vs what was found, and HALT. The doc-sync pass is meant to apply cleanly against bf7b869; drift indicates either you are not at the right commit or the patch was authored against a different state.

c. If anchors match: apply each "Find / Replace" block in the patch in the order it appears. Use exact-string find/replace (not regex). After each find/replace, optionally re-view the modified region to confirm the edit landed correctly.

d. For Patch 1 (the new verdict file): use create_file (not str_replace). Confirm the parent directory docs/sprints/sprint-31.91-reconciliation-drift/ exists; if it does not, halt (this would mean you are not at the expected sprint state).

After all 10 patches land, run validation:

A. Cross-reference grep — confirm DEC-386 appears in 7 distinct files (decision-log.md, dec-index.md, architecture.md, risk-register.md, project-knowledge.md, CLAUDE.md, plus the new tier-3-review-1-verdict.md):

   grep -l DEC-386 docs/decision-log.md docs/dec-index.md docs/architecture.md docs/risk-register.md docs/project-knowledge.md CLAUDE.md docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md

   Expected: 7 paths printed.

B. Cross-reference grep — confirm DEF-211/212/213/214/215 appear in CLAUDE.md AND at least one cross-reference target each:

   grep -l DEF-211 CLAUDE.md docs/decision-log.md docs/risk-register.md docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md
   grep -l DEF-212 CLAUDE.md docs/decision-log.md docs/architecture.md docs/live-operations.md docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md
   grep -l DEF-213 CLAUDE.md docs/decision-log.md docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5a.1-impl.md docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md
   grep -l DEF-214 CLAUDE.md docs/decision-log.md docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5a.1-impl.md docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md
   grep -l DEF-215 CLAUDE.md docs/decision-log.md docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md

   Each of these greps should print at least 2 paths.

C. Latest-DEC pointer grep — confirm both CLAUDE.md and project-knowledge.md say "Latest: DEC-386":

   grep -n "Latest:" CLAUDE.md docs/project-knowledge.md

   Expected output: both files contain "Latest: DEC-386 ..." lines.

D. Reserved-DEC marker grep — confirm dec-index.md marks DEC-385 / DEC-387 / DEC-388 as reserved:

   grep -n "DEC-385\|DEC-387\|DEC-388" docs/dec-index.md

   Expected: DEC-385 / DEC-387 / DEC-388 each have a ⊘ Reserved entry under the Sprint 31.91 section.

E. Code-was-not-touched assertion. The doc-sync pass MUST NOT touch any code under argus/ or tests/:

   git diff --stat -- argus/ tests/

   Expected: empty (no files changed under those directories).

F. Run the full test suite:

   python -m pytest --ignore=tests/test_main.py -n auto -q
   python -m pytest tests/test_main.py -q

   Expected: 5,128 passed (--ignore version) and 39 passed / 5 skipped (test_main.py). The doc-sync pass should not change test counts because no code was touched.

If ANY validation step fails, HALT, report which step, what was expected, what was found.

Tier 2 review (mandatory, even for doc-only changes per RULE-006):

Invoke @reviewer subagent with this scope:
"Doc-only Tier 2 review of Sprint 31.91 Tier 3 review #1 doc-sync pass. Verify:
(1) zero files under argus/ or tests/ are modified
(2) every patch applied at the documented anchor (no drift from the cited line numbers in any patch's anchor verification section)
(3) every cross-reference resolves (DEC-386, DEF-209/211/212/213, RSK-DEC-386-DOCSTRING, the verdict artifact path)
(4) markdown formatting is preserved (tables align, code fences close, headings nest correctly)
(5) version footers updated where the patch said to (decision-log.md, risk-register.md v1.7→v1.8, live-operations.md v1.4→v1.5, dec-index.md header counts and date)
Verdict: CLEAR / CONCERNS / ESCALATE."

If reviewer returns CONCERNS, address each concern before commit. If ESCALATE, halt and report.

Commit (single commit for the entire doc-sync pass):

git add CLAUDE.md docs/decision-log.md docs/dec-index.md docs/architecture.md docs/risk-register.md docs/pre-live-transition-checklist.md docs/live-operations.md docs/project-knowledge.md docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5a.1-impl.md docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md

# Optionally also add the doc-sync-artifacts directory if you used Option B in pre-flight:
git add docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts/

git status   # confirm only doc files staged; no code under argus/ or tests/

git commit -m "docs(sprint-31.91): Tier 3 review #1 doc-sync — DEC-386 + DEF-209/211ext/212/213/214/215 + RSK + 5a.1 amendment + verdict artifact + Apr 27 debrief findings

Captures architectural commitments from Tier 3 architectural review #1
(Sessions 0+1a+1b+1c, OCA architecture; combined diff 9b7246c^..bf7b869)
PLUS Apr 27 paper-session debrief findings.

Verdict: PROCEED. Verdict artifact at
docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md.

Apr 27 paper session ran PRE-OCA — Sessions 0-1c had not yet landed. The
43-symbol short cascade is another DEF-204 manifestation on pre-fix code,
not a test of OCA architecture. First OCA-effective paper session is
Apr 28 or later.

Doc updates:
- decision-log.md: DEC-386 (OCA-group threading + broker-only safety)
  written under new ## Sprint 31.91 section. Impact + Cross-Refs include
  Apr 27 debrief findings. Footer Next-DEC advanced.
- dec-index.md: Sprint 31.91 section added with DEC-386 active +
  DEC-385/387/388 reserved. Legend updated with ⊘ Reserved marker.
- architecture.md §3.3: cancel_all_orders ABC interface + semantics block.
- architecture.md §3.7: DEF-204 paragraph reframed as 'active fix in
  flight'; new 'OCA Architecture (Sprint 31.91 Sessions 0+1a+1b+1c)'
  subsection added.
- risk-register.md: RSK-DEF-204 status updated to PARTIALLY MITIGATED;
  new RSK-DEC-386-DOCSTRING entry for the time-bounded
  reconstruct_from_broker contract. Footer v1.7 → v1.8.
- pre-live-transition-checklist.md: new 'Sprint 31.91' section with
  the 18-session gate list and HARD prerequisite that Session 5a.1
  must land before live-trading transition.
- live-operations.md: new 'OCA Architecture Operations' section
  covering rollback procedure, _OCA_TYPE_BRACKET lock-step,
  cancel-propagation timeout response, and spike-script trigger
  registry. Footer v1.4 → v1.5.
- project-knowledge.md: Most-cited DEC list and Reference Latest-DEC
  pointer advanced from DEC-384 to DEC-386.
- session-5a.1-impl.md: amendment header + Pre-Flight Checks 7 (DEF-213
  schema check) + 8 (DEF-214 EOD verification path) + new conditional
  Requirement 0 (DEF-213 schema work) + new Requirement 0.5 (DEF-214
  poll-until-flat-with-timeout + side-aware classification + distinct
  alert paths).
- tier-3-review-1-verdict.md: NEW — stable repo verdict artifact with
  Apr 27 paper-session debrief inputs section noting the pre-OCA
  timeline.
- CLAUDE.md: DEF-209/211(ext)/212/213/214/215 filed; Active sprint state
  advanced to 'Sprint 31.91 in flight'; Apr 27 timeline corrected;
  OPERATOR DAILY MITIGATION elevated to REQUIRED-NOT-OPTIONAL framing
  (Apr 27 the operator forgot, ~\$70K notional shorts overnight);
  Latest-DEC pointer updated.

Apr 27 debrief findings folded in:
- Finding 1 (EOD verification timing race) → DEF-214, Session 5a.1
  sprint-gating, Patch 9 Requirement 0.5.
- Finding 2 (reconciliation per-cycle log spam) → DEF-215, DEFERRED with
  sharp revisit trigger (revisit only if observed lasting ≥10 cycles
  AFTER Sprint 31.91 sealed for ≥5 paper sessions).
- Finding 3 (max_concurrent_positions counts broker-only longs) → folded
  into DEF-211 extended scope (D3 boot-time adoption-vs-flatten policy).
- Finding 4 (boot-time reconciliation policy + IMPROMPTU-04 gate) →
  folded into DEF-211 extended scope (D1 ReconstructContext + D2 gate
  refactor + D3 adoption policy). Sprint 31.93 cannot be sealed without
  all three of D1+D2+D3.

No code changes. 5,128 + 39 / 5 skip pytest unchanged. Sprint 31.91
implementation continues with Session 2a per existing sprint plan."

git push origin main

Report:
- Confirmation of clean apply (no anchor drift on any patch)
- Confirmation that all 6 validation steps passed
- @reviewer verdict
- Commit SHA
- Final git log -1 --oneline output
```

---

## PROMPT 2 — claude-workflow Metarepo (run from your `claude-workflow` working directory)

**Estimated runtime:** 2-3 minutes.
**What you'll be asked to confirm:** the diff before commit.

### Pre-flight:

1. Confirm you are on `main` in the metarepo:

   ```bash
   cd /path/to/claude-workflow
   git status
   # Expected: "On branch main" and clean working tree
   ```

2. The patch artifact is already accessible alongside the others. Use the same `doc-sync-artifacts/` directory you used for Prompt 1 — Patch 11 (`11-metarepo-tier-3-review.md.patch.md`) is in there. Either copy it into the metarepo working directory transiently, or reference it from wherever you have it:

   ```bash
   # If you placed artifacts under argus/ in Option B for Prompt 1:
   cat /path/to/argus/docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts/11-metarepo-tier-3-review.md.patch.md

   # Option B equivalent for the metarepo: drop it under a notes/ folder if your metarepo has one, or just hold it in /tmp.
   ```

### The prompt (paste this into Claude Code, with working directory set to the metarepo):

```
WORKFLOW METAREPO — TIER 3 PROTOCOL AMENDMENT (workflow-version 1.0.0 → 1.0.1)

You are amending protocols/tier-3-review.md in the claude-workflow metarepo. The amendment was surfaced by ARGUS Sprint 31.91 Tier 3 review #1 (2026-04-27): the Tier 3 protocol's canonical Output schema enumerates DEC entries and RSK entries but does NOT explicitly enumerate "New DEF entries (for items carrying forward to sprints other than the one just reviewed)" or "stable repo verdict artifact." This near-missed Concern C as a DEF candidate during the ARGUS review.

Pre-flight:

1. Verify branch is `main`, working tree is clean:
   git status
   git log -1 --oneline
   If not clean, halt and report.

2. Read protocols/tier-3-review.md in full. Confirm the current state matches the anchors in patch 11:
   - Line 1: <!-- workflow-version: 1.0.0 -->
   - Line 2: <!-- last-updated: 2026-03-12 -->
   - Lines 6-7: **Context:** / **Frequency:** / **Output:** preamble block
   - Line 83: ## Output
   - Lines 85-92: existing 7-item Output enumeration

3. Identify the location of the Patch 11 file. The Patch 11 content is provided inline below if you don't have the file accessible:

[Paste the entire content of `11-metarepo-tier-3-review.md.patch.md` here when you run this prompt. Or: if you placed the artifacts under argus/.../tier-3-review-1-doc-sync-artifacts/, the prompt can `cat` that path directly. Adjust this paragraph to reflect your choice.]

Apply Patch 11's three find/replace blocks (Patch A: workflow-version + last-updated; Patch B: Output preamble line; Patch C: canonical Output enumeration with bold-emphasis on the two new items DEF entries and verdict artifact). Use exact-string find/replace; no regex.

After applying, validate:

A. Markdown render check: confirm the file still parses cleanly. The old 7-item enumeration is now 9 items, with items 3 and 7 added (DEF entries; verdict artifact).

B. Workflow-version updated:
   grep -n "workflow-version\|last-updated" protocols/tier-3-review.md
   Expected: workflow-version 1.0.1, last-updated 2026-04-27.

C. Bold emphasis preserved:
   grep -n "New DEF entries\|stable repo verdict artifact" protocols/tier-3-review.md
   Expected: both phrases appear with leading **bold** markdown.

D. No other protocol files changed:
   git diff --stat
   Expected: only protocols/tier-3-review.md is modified.

Tier 2 review:

If your metarepo has an established review template for protocol amendments, invoke it. If not (most likely), perform a manual sanity check:
- Does the amendment add information without removing or contradicting existing protocol guidance? (Should: yes — it's purely additive.)
- Does §5 'Documentation Reconciliation' (which already mentions DEF entries) remain consistent with the new Output schema? (Should: yes — §5 line 77 already says 'What should be deferred? (DEF entries)'; the amendment just makes the Output schema enumerate this in parallel.)
- Is the workflow-version bump appropriate? (1.0.0 → 1.0.1 for an additive non-breaking change.)

Commit:

git add protocols/tier-3-review.md
git status   # confirm only protocols/tier-3-review.md staged

git commit -m "protocols(tier-3-review): require DEF entries + verdict artifact in output

Workflow-version 1.0.0 → 1.0.1.

Two changes to Output schema:
- Item 3 (new): DEF entries for items carrying forward to sprints other
  than the one just reviewed. ARGUS Sprint 31.91 Tier 3 review #1
  surfaced that the prior schema named DECs/RSKs but not DEFs as
  canonical output, leading to a near-miss on a sprint-gating forcing
  function (Concern C — SystemAlertEvent.metadata schema gap).
- Item 7 (new): stable repo verdict artifact at
  docs/sprints/<sprint>/tier-3-review-N-verdict.md, surviving Claude.ai
  conversation transcript rollover.

Renumbers existing items 3-7 → 4-9. Bold emphasis on the two new
items so reviewers skim-reading can't miss them.

§5 'Documentation Reconciliation' already mentioned DEF entries as
a deferral category (line 77); the Output schema now enumerates this
in parallel rather than relying on §5 alone.

Origin: ARGUS Sprint 31.91 Tier 3 review #1 (2026-04-27, verdict
PROCEED, anchor commit bf7b869 on the argus repo). Verdict artifact
at argus/docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md."

git push origin main

Report:
- Confirmation of clean apply
- Workflow-version bump confirmed
- Commit SHA
- Final git log -1 --oneline output
```

---

## Application notes

- **Run order:** Prompt 1 (ARGUS) THEN Prompt 2 (metarepo). The reverse order also works since the two repos are independent, but ARGUS-first is conventional and matches how the doc-sync flow surfaced the protocol gap (the ARGUS review uncovered it).
- **Time budget total:** ~10-15 minutes of Claude Code execution + ~5-10 minutes of your review of each commit's diff before push. Total: 30-45 minutes.
- **What if @reviewer raises CONCERNS in Prompt 1?** Address them in-conversation, then have Claude Code re-run the validation and re-invoke @reviewer. Once CLEAR, commit. The most likely concern is a markdown formatting glitch (table alignment, etc.); mechanical to fix.
- **What if anchor verification fails on a patch?** Most likely cause: someone (you, or an autonomous sprint runner) committed something between bf7b869 and now. Check `git log bf7b869..HEAD --oneline` to see what landed; if it's an unrelated cosmetic edit you can re-anchor manually; if it's a content change to one of the target files, that's a real conflict and the doc-sync needs to be re-authored against the new state.
- **The "Option B" placement (artifacts under sprint folder) leaves a permanent record** — useful for forensic traceability if anyone later asks "where did the Tier 3 review artifacts come from?" The directory `tier-3-review-1-doc-sync-artifacts/` parallels the verdict artifact's filename and stays organized.
