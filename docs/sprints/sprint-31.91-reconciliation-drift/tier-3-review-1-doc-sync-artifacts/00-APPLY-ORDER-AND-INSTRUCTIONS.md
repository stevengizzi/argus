# Doc-Sync Apply Order & Operator Instructions (AMENDED v4 — Apr 27 debrief findings folded in)

**Sprint 31.91 Tier 3 Architectural Review #1 — Doc-Sync Pass + Metarepo Protocol Amendment + Apr 27 Paper-Session Debrief Findings**
**Generated:** 2026-04-27
**Tier 3 verdict:** PROCEED (Sessions 0+1a+1b+1c, OCA architecture)
**ARGUS anchor commit:** `bf7b869` on `main` (Session 1c review verdict CLEAR)
**Metarepo anchor:** `claude-workflow` `main`, `protocols/tier-3-review.md` v1.0.0

**Amendment history:**
- v1: original 9-artifact draft (Tier 3 verdict only).
- v2: expanded to 12 artifacts — added DEF-213, verdict artifact, Session 5a.1 prompt amendment, metarepo protocol amendment.
- v3: Tier 3 review #1 doc-sync content expansion (CLAUDE.md DEF-213 row, etc.).
- **v4 (current): folds in Apr 27 paper-session debrief findings.**
  - **Critical correction:** Apr 27 paper session ran PRE-OCA (Sessions 0-1c had not yet landed at `bf7b869`). Apr 27's 43-symbol cascade is another DEF-204 manifestation on pre-fix code, NOT a test of OCA architecture. The first OCA-effective paper session will be Apr 28 or later.
  - DEF-211 extended scope to fold in Apr 27 Findings 3 + 4 (three coupled deliverables D1+D2+D3 for Sprint 31.93).
  - New DEF-214 filed (Apr 27 Finding 1: EOD verification timing race + side-aware classification + distinct alert paths) — sprint-gating to Session 5a.1.
  - New DEF-215 filed (Apr 27 Finding 2: reconciliation per-cycle log spam) — DEFERRED with sharp revisit trigger.
  - Patch 09 (Session 5a.1 amendment) extended to cover BOTH DEF-213 and DEF-214 (adds Pre-Flight Check 8 + new top-level Requirement 0.5).
  - Patch 10 (verdict artifact) gains an "Apr 27 paper-session debrief inputs" section noting the timeline correction.
  - Patch 01 (decision-log) DEC-386 Impact + Cross-References rows updated.

---

## What this pass does

### ARGUS repo (Prompt 1, 10 patches)

Documentation-only sync pass. **No production code touched.** Captures the architectural commitments from Tier 3 review #1 + the Apr 27 paper-session debrief findings:

- **DEC-386 written** (decision-log.md + dec-index.md) under new Sprint 31.91 section.
- **Six DEFs filed in CLAUDE.md:**
  - DEF-209 (formal filing of SbC-reserved field-preservation defer + Concern D extension).
  - DEF-211 (Sprint 31.93 sprint-gating, EXTENDED SCOPE — three coupled deliverables D1+D2+D3 per Apr 27 Findings 3+4: ReconstructContext parameter + IMPROMPTU-04 startup invariant gate refactor + boot-time adoption-vs-flatten policy decision).
  - DEF-212 (Sprint 31.92 sprint-gating: IBKRConfig wiring into OrderManager).
  - DEF-213 (Session 5a.1 sprint-gating: SystemAlertEvent.metadata schema + atomic emitter migration).
  - DEF-214 (Session 5a.1 sprint-gating: EOD verification timing race + side-aware classification + distinct alert paths) — Apr 27 debrief Finding 1.
  - DEF-215 (DEFERRED with sharp revisit trigger: reconciliation per-cycle log spam) — Apr 27 debrief Finding 2.
- **RSK-DEF-204 status downgraded** to "PARTIALLY MITIGATED" (will move further once Apr 28+ OCA-effective paper sessions show clean mass-balance).
- **RSK-DEC-386-DOCSTRING newly filed** (risk-register.md, time-bounded by Sprint 31.93).
- **architecture.md** §3.3 (cancel_all_orders ABC) + §3.7 (DEF-204 reframed + new OCA Architecture subsection).
- **pre-live-transition-checklist.md** Sprint 31.91 gate list.
- **live-operations.md** OCA Architecture Operations section (rollback, lock-step, failure-mode response, spike trigger registry).
- **project-knowledge.md** Latest-DEC pointer advanced.
- **Session 5a.1 impl prompt amended** with TWO sprint-gating items: Requirement 0 (DEF-213 schema work) + Requirement 0.5 (DEF-214 EOD verification fix). Both are inserts before existing Requirement 1; existing requirement numbers are preserved.
- **NEW: Stable repo verdict artifact** at `docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md` so the verdict survives Claude.ai conversation rollover. Includes Apr 27 paper-session debrief inputs section noting the pre-OCA timeline.
- **Active-sprint summary** in CLAUDE.md updated with corrected Apr 27 timeline framing AND elevated **OPERATOR DAILY MITIGATION — REQUIRED, NOT OPTIONAL** language (Apr 27 the operator forgot, ~$70K notional shorts overnight).

### Metarepo (Prompt 2, 1 patch)

Workflow protocol amendment to `protocols/tier-3-review.md`:

- Workflow-version 1.0.0 → 1.0.1.
- Output schema item 3 (new): require "New DEF entries (for items carrying forward to sprints other than the one just reviewed)."
- Output schema item 7 (new): require "stable repo verdict artifact."
- Renumbers existing items 3-7 → 4-9.

---

## Files in this artifact set (13 total)

```
doc-sync-artifacts/
├── 00-APPLY-ORDER-AND-INSTRUCTIONS.md            ← this file (v4)
├── 01-decision-log.md.patch.md                   ← DEC-386 entry (v3 — Impact + Cross-Refs include Apr 27 findings)
├── 02-dec-index.md.patch.md                      ← Sprint 31.91 section + ⊘ Reserved legend
├── 03-CLAUDE.md.patch.md                         ← v3 — DEF-209/211(ext)/212/213/214/215 + state advance + Apr 27 framing
├── 04-architecture.md.patch.md                   ← §3.3 ABC + §3.7 OCA architecture
├── 05-pre-live-transition-checklist.md.patch.md  ← Sprint 31.91 gate list
├── 06-risk-register.md.patch.md                  ← RSK-DEF-204 update + RSK-DEC-386-DOCSTRING
├── 07-live-operations.md.patch.md                ← OCA operations (rollback, lock-step, etc.)
├── 08-project-knowledge.md.patch.md              ← Latest DEC pointer advance
├── 09-session-5a.1-impl-prompt.amendment.md      ← v3 — covers BOTH DEF-213 (Req 0) + DEF-214 (Req 0.5)
├── 10-tier-3-review-1-verdict.create.md          ← v3 — adds Apr 27 paper-session debrief inputs section
├── 11-metarepo-tier-3-review.md.patch.md         ← Metarepo protocol amendment (different repo!)
└── 12-claude-code-prompts.md                     ← Ready-to-paste Claude Code prompts
```

---

## Patches by repo

### ARGUS repo (10 patches, executed by Prompt 1):

| Order | Patch file | Target file (or action) | Approx LOC delta |
|-------|------------|-------------------------|-----|
| 1 | 10-tier-3-review-1-verdict.create.md | CREATE: docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-verdict.md | +220 lines (new file with Apr 27 debrief section) |
| 2 | 01-decision-log.md.patch.md | docs/decision-log.md | +30 lines (DEC-386 + footer; Impact + Cross-Refs cover Apr 27 findings) |
| 3 | 02-dec-index.md.patch.md | docs/dec-index.md | +9 lines |
| 4 | 04-architecture.md.patch.md | docs/architecture.md | +75 lines |
| 5 | 06-risk-register.md.patch.md | docs/risk-register.md | +25 lines |
| 6 | 05-pre-live-transition-checklist.md.patch.md | docs/pre-live-transition-checklist.md | +60 lines |
| 7 | 07-live-operations.md.patch.md | docs/live-operations.md | +100 lines |
| 8 | 08-project-knowledge.md.patch.md | docs/project-knowledge.md | 2 single-line replacements |
| 9 | 09-session-5a.1-impl-prompt.amendment.md | docs/sprints/sprint-31.91-reconciliation-drift/sprint-31.91-session-5a.1-impl.md | +180 lines (header + 2 pre-flight checks + Req 0 + Req 0.5) |
| 10 | 03-CLAUDE.md.patch.md | CLAUDE.md (LAST per pass-consistency rule) | +6 DEF rows + 2 single-line updates |

Total ARGUS: ~720 lines added across 10 doc files; 0 lines of code touched.

### Metarepo (1 patch, executed by Prompt 2):

| Order | Patch file | Target file | Approx LOC delta |
|-------|------------|-------------|-----|
| 1 | 11-metarepo-tier-3-review.md.patch.md | protocols/tier-3-review.md | +6 lines |

---

## What this pass does NOT do

- Sprint 31.91 in-sprint doc updates (those land at sprint close).
- `docs/sprint-history.md` row for Sprint 31.91 (sprint close).
- `docs/sprint-campaign.md` (campaign close).
- Code changes to address Tier 3 Concerns A, B, D, E, F (deferred per routing).
- **Code changes for DEF-213 + DEF-214 themselves** — those are Session 5a.1's actual implementation work; the patches here only update the prompt to scope that work explicitly.
- Code changes for any of the Apr 27 debrief findings — Findings 3+4 land in Sprint 31.93 (DEF-211 extended); Finding 1 lands in Session 5a.1 (DEF-214); Finding 2 stays deferred (DEF-215).

DEF-213 and DEF-214 are addressed by this pass via the Session 5a.1 prompt amendment (Patch 9), because that's a prompt-level change. The actual code work happens when Session 5a.1 itself runs.

---

## Validation summary (matches Prompt 1's validation steps)

After ARGUS Prompt 1 completes:

- A. `grep -l DEC-386` returns 7 paths.
- B. `grep -l DEF-211/212/213/214/215` each returns ≥2 paths.
- C. `grep -n "Latest:"` shows DEC-386 in CLAUDE.md and project-knowledge.md.
- D. `grep -n "DEC-385\|DEC-387\|DEC-388"` shows reserved markers in dec-index.md.
- E. `git diff --stat -- argus/ tests/` is empty (no code touched).
- F. Test counts unchanged: 5,128 + 39 / 5 skip pytest.

After metarepo Prompt 2 completes:

- workflow-version is 1.0.1.
- New DEF entries + verdict artifact phrases appear with bold emphasis in protocols/tier-3-review.md.

---

## Total time estimate

- Pre-flight: 5 minutes
- Prompt 1 execution: 12-18 minutes (more patches; longer @reviewer pass)
- Prompt 2 execution: 5 minutes
- Work journal update: 5 minutes

**Total: ~30-35 minutes end-to-end.**

---

## Where to put each file

```
argus/docs/sprints/sprint-31.91-reconciliation-drift/
├── tier-3-review-1-verdict.md                       ← lands here via Prompt 1 (Patch 10)
├── tier-3-review-1-doc-sync-artifacts/              ← place ALL 13 artifacts here
│   ├── 00-APPLY-ORDER-AND-INSTRUCTIONS.md
│   ├── 01-decision-log.md.patch.md
│   ├── ... (all 13 files)
│   └── 12-claude-code-prompts.md
├── sprint-spec.md                                    ← (existing)
├── sprint-31.91-session-5a.1-impl.md                 ← (existing; Patch 9 amends this)
└── ... (other existing sprint files)
```

```bash
mkdir -p /path/to/argus/docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts
cp ~/Downloads/00-*.md ~/Downloads/01-*.md ~/Downloads/02-*.md ~/Downloads/03-*.md \
   ~/Downloads/04-*.md ~/Downloads/05-*.md ~/Downloads/06-*.md ~/Downloads/07-*.md \
   ~/Downloads/08-*.md ~/Downloads/09-*.md ~/Downloads/10-*.md ~/Downloads/11-*.md \
   ~/Downloads/12-*.md \
   /path/to/argus/docs/sprints/sprint-31.91-reconciliation-drift/tier-3-review-1-doc-sync-artifacts/
```

---

## Steps to run the Claude Code commands

### Step 1 — Pre-flight (~5 min)

```bash
cd /path/to/argus
git status                      # On main, clean
git log -1 --oneline            # bf7b869 docs(sprint-31.91): session 1c Tier 2 review verdict (CLEAR)
python -m pytest --ignore=tests/test_main.py -n auto -q   # 5,128 passed
```

```bash
cd /path/to/claude-workflow
git status                      # On main, clean
```

### Step 2 — Place artifacts (~2 min)

Run the `mkdir` + `cp` block above.

### Step 3 — Run Prompt 1 (ARGUS) (~12-18 min)

1. Open Claude Code with working directory `/path/to/argus`.
2. Open `12-claude-code-prompts.md` and copy **PROMPT 1** (the entire code block).
3. Paste into Claude Code.
4. Watch it execute — apply 10 patches, run 6 validation steps, invoke @reviewer, commit, push.
5. Review the diff before push: 10 doc files modified, 1 new file created, 0 code files touched.

### Step 4 — Run Prompt 2 (metarepo) (~5 min)

1. Open Claude Code with working directory `/path/to/claude-workflow`.
2. Copy **PROMPT 2** from `12-claude-code-prompts.md`. Replace the inline placeholder with Patch 11's content.
3. Watch it execute — single patch, single commit, push.

### Step 5 — Close the Tier 3 review loop (~5 min)

In your Sprint 31.91 work journal conversation, post a close-out note:

> Tier 3 review #1 verdict PROCEED. Doc-sync pass landed in ARGUS commit `<sha>` (10 doc files updated, verdict artifact created); metarepo amendment in commit `<sha>` (workflow-version 1.0.1). DEC-386 written; DEF-209/211(extended)/212/213/214/215 filed; RSK-DEC-386-DOCSTRING filed; Session 5a.1 impl prompt amended for both DEF-213 (Requirement 0 schema work) and DEF-214 (Requirement 0.5 EOD verification fix). Apr 27 paper-session debrief findings folded in: Findings 3+4 → DEF-211 extended scope (Sprint 31.93), Finding 1 → DEF-214 (Session 5a.1), Finding 2 → DEF-215 (deferred). **Apr 27 ran PRE-OCA** — first OCA-effective paper session is Apr 28 or later. Sprint 31.91 cleared to proceed to Session 2a.

That closes the Tier 3 loop. Sprint 31.91 implementation continues with Session 2a per the existing sprint plan.
