# Sprint synthesis-2026-04-26: Doc Update Checklist

> Documents whose state must be reconciled with the sprint's outputs. Most updates land **within** Sessions 0–6 (the sprint IS doc work); a smaller set requires post-sprint reconciliation after Session 6 closes.
>
> The post-sprint items are typically handled by a brief **doc-sync session** (Claude Code or operator-direct) that runs after Session 6's Tier 2 review clears. This sprint's doc-sync is unusually light because the sprint-internal sessions handle most updates — but a few items genuinely belong outside the session boundaries (cross-repo work, README count drift correction, optional propagation).

---

## Section A: Within-Sprint Updates (handled by Sessions 0–6)

These are listed for visibility; each has an explicit acceptance gate in the relevant session.

### Session 0 — Argus-side input set
- [ ] `argus/docs/sprints/sprint-31.9/SPRINT-31.9-SUMMARY.md` — append P28 + P29 to §Campaign Lessons
- [ ] *Optional:* `argus/CLAUDE.md` — add `## Rules` section pointing at `.claude/rules/universal.md`

### Session 1 — Keystone wiring + RULE additions
- [ ] `workflow/claude/rules/universal.md` — add RULE-051 / 052 / 053; append 5th sub-bullet to RULE-038; bump version 1.0 → 1.1
- [ ] `workflow/claude/skills/close-out.md` — strengthen Step 3 (FLAGGED blocks commit + push); minor version bump
- [ ] `workflow/templates/implementation-prompt.md` — keystone Pre-Flight step 1; operator-choice block; no-cross-referencing rule; section-order discipline; version 1.2.0 → 1.3.0
- [ ] `workflow/templates/review-prompt.md` — keystone Pre-Flight step; version 1.1.0 → 1.2.0

### Session 2 — Mechanical housekeeping
- [ ] `workflow/templates/work-journal-closeout.md` — Hybrid Mode section; minor version bump
- [ ] `workflow/templates/doc-sync-automation-prompt.md` — Between-Session Doc-Sync section; minor version bump
- [ ] `workflow/scaffold/CLAUDE.md` — add `## Rules` section
- [ ] `workflow/evolution-notes/README.md` — synthesis-status convention documented
- [ ] `workflow/evolution-notes/2026-04-21-argus-audit-execution.md` — additive `**Synthesis status:**` header line
- [ ] `workflow/evolution-notes/2026-04-21-debrief-absorption.md` — same
- [ ] `workflow/evolution-notes/2026-04-21-phase-3-fix-generation-and-execution.md` — same

### Session 3 — campaign-orchestration + impromptu-triage extension
- [ ] `workflow/protocols/campaign-orchestration.md` — NEW file (~250–350 lines)
- [ ] `workflow/protocols/impromptu-triage.md` — extend with two-session scoping variant; minor version bump
- [ ] `workflow/bootstrap-index.md` — Conversation Type entry for "Campaign Orchestration / Absorption / Close" + Protocol Index row

### Session 4 — operational-debrief
- [ ] `workflow/protocols/operational-debrief.md` — NEW file (~150–200 lines)
- [ ] `workflow/bootstrap-index.md` — Conversation Type entry for "Operational Debrief" + Protocol Index row

### Session 5 — templates + validator
- [ ] `workflow/templates/stage-flow.md` — NEW (~80–120 lines)
- [ ] `workflow/templates/scoping-session-prompt.md` — NEW (~80–120 lines)
- [ ] `workflow/scripts/phase-2-validate.py` — NEW (~50 lines)
- [ ] `workflow/bootstrap-index.md` — Template Index rows for both new templates

### Session 6 — Audit expansion + sprint-planning cross-reference
- [ ] `workflow/protocols/codebase-health-audit.md` — major expansion 1.0.0 → **2.0.0** (Phase 1/2/3 full content; rejected-safety-tag-taxonomy addendum; tiered hot-files; phase-2-validate gate; F1–F10 generalized terminology coverage)
- [ ] `workflow/protocols/sprint-planning.md` — one-line cross-reference to `campaign-orchestration.md`; minor version bump

---

## Section B: Post-Sprint Metarepo Doc-Sync

These run after Session 6's Tier 2 review clears. Recommended approach: a single Claude Code session targeting the metarepo, ~15 minutes.

### B1. README.md count drift correction

**Why:** The metarepo's `README.md` lines 14–24 cite specific counts that are stale (RETRO-FOLD did not update them; this sprint compounds the drift). After Session 6 closes:

- "14 protocols" → **19 protocols** (17 pre-sprint + 2 new: campaign-orchestration, operational-debrief)
- "10 templates" → **13 templates** (11 pre-sprint + 2 new: stage-flow, scoping-session-prompt)
- "universal.md (36 cross-project rules)" → **universal.md (53 cross-project rules)** (36 pre-RETRO-FOLD + 13 from RETRO-FOLD + 4 from this sprint; verifiable: `grep -c "^RULE-" workflow/claude/rules/universal.md` == 53)
- Skills count line — unchanged at 5 (close-out, review, canary-test, diagnostic, doc-sync)
- Schemas count line — unchanged at 4

**Action:** Update README.md lines 14–22 to reflect actual counts. Single commit.

**Verification:** Counts in README.md match `ls workflow/protocols/*.md | wc -l`, `ls workflow/templates/*.md | wc -l`, `grep -c "^RULE-" workflow/claude/rules/universal.md`.

### B2. Optional: README.md "scripts/" line

**Why:** `README.md` line 24 currently reads `scripts/             # scaffold.sh, setup.sh, sync.sh`. After Session 5, there's also `phase-2-validate.py`. The drift is tiny; either:
- Update the comment to `# scaffold.sh, setup.sh, sync.sh, phase-2-validate.py`, OR
- Generalize to `# Setup, sync, and validation utilities`

**Action:** Update line 24 (operator's preference of wording).

### B3. VERSIONING.md — current-version line

**Why:** `VERSIONING.md` line 59 still reads `**v1.0.0** — Initial extraction from ARGUS (March 2026)`. This was already stale post-RETRO-FOLD. The metarepo has accumulated substantial additions but no tag has been issued.

**Action:** Two acceptable options:
- (a) **Leave untouched** (consistent with the spec-by-contradiction OUT item #9 "no tag convention introduced this sprint"). The drift compounds slightly but stays within the existing posture.
- (b) **Update the bottom of VERSIONING.md** to add a brief "Post-baseline additions" note — listing RETRO-FOLD + synthesis-2026-04-26 commit ranges as untagged additions, deferring the tag convention to a future strategic check-in. Doesn't introduce a tag; documents that there ARE additions.

**Recommendation: (a) — leave untouched.** Defer the version-record reconciliation to whenever a tag convention is adopted. Document this choice in the post-sprint doc-sync close-out as a deferred observation.

### B4. CLASSIFICATION.md — no update needed

**Why:** CLASSIFICATION.md documents the one-time ARGUS → metarepo migration. New protocols/templates added in subsequent sprints (RETRO-FOLD; this sprint) are NOT additions to that historical record. They're metarepo-native.

**Action:** None. Verify untouched.

### B5. MIGRATION.md — no update needed

**Why:** MIGRATION.md is a one-time migration guide. Doesn't reference counts, protocol names, or anything affected by this sprint.

**Action:** None. Verify untouched.

### B6. evolution-notes/README.md — verify (already updated in Session 2)

**Why:** Session 2 documents the synthesis-status convention. Post-sprint check: the convention as documented matches what was actually applied to the 3 evolution notes.

**Action:** Spot-check that the format documented in `evolution-notes/README.md` (e.g., `**Synthesis status:** SYNTHESIZED in <sprint-name> (commit <SHA>)`) matches the actual headers landed on the 3 notes in Session 2.

**Verification:**
```bash
diff <(grep "^**Synthesis status:**" workflow/evolution-notes/2026-04-21-argus-audit-execution.md | head -1 | sed 's/SYNTHESIZED in [^(]*/SYNTHESIZED in [SPRINT]/') \
     <(grep "^**Synthesis status:**" workflow/evolution-notes/2026-04-21-debrief-absorption.md | head -1 | sed 's/SYNTHESIZED in [^(]*/SYNTHESIZED in [SPRINT]/')
```
Format consistent across all 3 notes. README convention matches.

### B7. Optional: bootstrap-index.md last-updated date

**Why:** The bootstrap-index.md doesn't currently have a version header (verified in Phase A — most files have one but not bootstrap-index). If we want it tracked, this sprint could add one.

**Action:** Two options:
- (a) Skip — preserve existing posture (no version header on bootstrap-index)
- (b) Add `<!-- workflow-version: 1.1.0 --> <!-- last-updated: 2026-04-26 -->` to bootstrap-index.md as a one-time additive

**Recommendation: (a) — skip.** Adding versioning to a previously-unversioned file is a meta-decision that deserves a strategic check-in, not a unilateral synthesis-sprint addition. Document in post-sprint doc-sync close-out as a deferred observation.

### B8. Cross-reference final integrity sweep

**Verify after all metarepo updates land:**
```bash
# All path-based cross-references in NEW or MODIFIED files in this sprint
git diff <pre-sprint-sha>..HEAD --name-only -- workflow/ | while read f; do
    if [ -f "workflow/$f" ]; then
        # Extract path-like references; check each resolves
        grep -oE "(protocols/|templates/|claude/(skills|rules|agents)/|schemas/|scripts/|scaffold/|evolution-notes/|runner/)[a-z0-9_-]+\.(md|py|sh|yaml)" "workflow/$f" | sort -u | while read ref; do
            if [ ! -e "workflow/$ref" ]; then
                echo "BROKEN: workflow/$f → workflow/$ref"
            fi
        done
    fi
done
```

**Expected:** No "BROKEN:" output.

**Action:** If broken references found, route via doc-sync to a fix commit; if widespread, escalate.

---

## Section C: Post-Sprint Argus-Side Doc-Sync

These are operator-handled in the argus repo after the metarepo updates land.

### C1. Submodule pointer advancement

**Why:** Argus tracks the metarepo via submodule. The pointer must advance to include this sprint's metarepo HEAD so argus session prompts pull in the new content.

**Action:**
```bash
cd ~/projects/argus  # or operator's path
cd workflow
git pull origin main
cd ..
git add workflow
git commit -m "chore(workflow): advance submodule to synthesis-2026-04-26 HEAD"
git push
```

**Verification:** `git submodule status workflow` shows the new metarepo SHA.

### C2. Argus deferred items list — boot-commit logging automation

**Why:** Phase A established that ARGUS-side automation of execution-anchor-commit logging is out of scope for this sprint but worth tracking. The new `protocols/operational-debrief.md` (Session 4) explicitly flags "Recommended automation: project-specific" — this is the placeholder that ARGUS should fill.

**Action:** Add an ARGUS deferred item entry. Format follows the existing argus DEF / deferred items convention:

```markdown
### DEF-XXX: Boot-commit logging automation

**Status:** OPEN (post-31.9 deferred)
**Description:** ARGUS currently records the boot commit (HEAD SHA at startup) manually before each operational session. The metarepo's `protocols/operational-debrief.md` documents this as a recommended automation: the live system should write the boot commit to a known location at startup so the operator doesn't have to remember. Suggested implementation: log the SHA in the lifespan startup phase to `logs/boot-history.jsonl` (one line per startup) with timestamp + SHA + brief startup metadata.
**Priority:** Low — current manual approach works; automation is a quality-of-life improvement.
**Origin:** synthesis-2026-04-26 Phase A pushback round 2 (boot-commit codification reflects current ARGUS reality; automation explicitly deferred).
**Trigger condition:** When next argus session touches `argus/main.py` lifespan, fold in the boot-history logger.
```

Place in argus's CLAUDE.md Deferred Items section or `docs/risk-register.md`, depending on convention. The DEF number is the next available in the argus DEF range (likely DEF-207 or higher; verify via `grep -c "^DEF-" argus/CLAUDE.md` or equivalent).

**Verification:** New DEF entry visible in argus's deferred-items document; DEF number doesn't collide.

### C3. Argus CLAUDE.md `## Rules` section — verify (handled in Session 0 if applicable)

**Why:** Session 0 optionally adds a `## Rules` section to argus's `CLAUDE.md` if not already present. Post-sprint check: confirm the section exists and matches the expected format.

**Action:** If Session 0 skipped this (operator chose not to add it then), add it now:

```markdown
## Rules

This project follows the universal rules in `.claude/rules/universal.md` (auto-loaded by Claude Code at session start per the implementation-prompt template's Pre-Flight step). Project-specific rules live alongside in `.claude/rules/` (e.g., `backtesting.md` for ARGUS-specific patterns).
```

**Verification:** `grep "## Rules" ~/projects/argus/CLAUDE.md` returns ≥ 1.

### C4. Argus sprint-history.md — no entry needed

**Why:** synthesis-2026-04-26 is a metarepo synthesis sprint, not an ARGUS sprint. It doesn't deliver argus-side runtime functionality and shouldn't appear in argus's sprint-history.md.

**Action:** Confirm no argus sprint-history.md edit. If the operator wants a brief note that "metarepo updated to include synthesis-2026-04-26," that goes in argus's CLAUDE.md "Last metarepo sync" line or similar — operator's choice. NOT mandatory.

### C5. Argus decision-log.md — no entry needed

**Why:** This sprint adds 0 new ARGUS DECs (the changes are metarepo-side). RETRO-FOLD's pattern was the same.

**Action:** None.

### C6. Argus project-knowledge.md — minor optional update

**Why:** project-knowledge.md mentions the workflow metarepo. After this sprint's substantive additions, the workflow capabilities have grown materially.

**Action (optional):** Add a one-line note in the workflow section: "Metarepo updated 2026-04-26 with synthesis sprint — adds campaign-orchestration protocol, operational-debrief protocol, stage-flow + scoping-session-prompt templates, codebase-health-audit Phase 2/3 expansion."

If the operator considers project-knowledge.md churn-sensitive (it's read by every Claude.ai session), skip this.

---

## Section D: Other-Project Doc-Sync (Out of Strict Scope)

Listed for awareness. Operator handles each at their discretion.

### D1. MuseFlow / Grove / other projects' submodule pointer advancement

**Why:** Each project that uses the workflow metarepo as a submodule has its own pointer; advancing each pulls in this sprint's additions.

**Action:** Per-project, when convenient:
```bash
cd ~/projects/<project>
cd workflow
git pull origin main
cd ..
./workflow/scripts/setup.sh  # re-symlink in case structure changed
git add workflow
git commit -m "chore(workflow): advance submodule to synthesis-2026-04-26"
```

Note: `./workflow/scripts/setup.sh` re-execution should be idempotent (no breakage if already-set-up project re-runs it). Verified via the script's existing handling of pre-existing symlinks.

### D2. Other-project CLAUDE.md `## Rules` section addition

**Why:** Same defensive backup wiring as ARGUS's. Without it, the keystone Pre-Flight wiring still works (it reads `.claude/rules/universal.md` from the implementation prompt), but the explicit `## Rules` section provides resilience if a future Claude Code update changes session-start auto-discovery.

**Action:** Per-project, optional. Operator decides per-project.

### D3. Other-project deferred items — boot-commit logging

**Why:** If MuseFlow / Grove have a continuously-running daemon analogous to ARGUS's, they may benefit from the same boot-commit logging automation.

**Action:** Per-project, operator-judgment. Probably not applicable to most projects (request/response services don't have a boot-commit-per-cycle pattern).

---

## Section E: Verification Sweep (Final Doc-Sync Action)

Run after all Section A–C items complete:

### E1. All within-sprint updates landed
```bash
# Each session's modifies/creates list verified via git log + diff
for s in 0 1 2 3 4 5 6; do
    if [ -f argus/docs/sprints/synthesis-2026-04-26/session-${s}-closeout.md ]; then
        echo "Session $s closeout: PRESENT"
    else
        echo "Session $s closeout: MISSING"
    fi
done
```
All 7 close-outs (Session 0 + Sessions 1-6) present.

### E2. All Section B post-sprint metarepo updates landed
```bash
# README counts match reality
grep -E "[0-9]+ protocol" workflow/README.md  # Should show 19
grep -E "[0-9]+ template" workflow/README.md  # Should show 13
grep -E "[0-9]+ cross-project rules" workflow/README.md  # Should show 53
```

### E3. All Section C argus-side updates landed (where applicable)
```bash
cd ~/projects/argus
git submodule status workflow  # Pointer advanced
grep -i "boot.commit.logging\|execution.anchor.commit" CLAUDE.md docs/risk-register.md 2>/dev/null  # DEF-XXX present
```

### E4. Regression checklist (`regression-checklist.md`) — all items pass
Run R1 through R20 from `regression-checklist.md` Section 4 ("Tier 2 Reviewer Workflow") one final time against the post-sprint state. All should pass.

### E5. Escalation criteria (`escalation-criteria.md`) — none triggered
Confirm no Category A or Category B escalation triggered during the sprint. If any did and was resolved, the close-out documents resolution; if any is still open, sprint is not complete.

### E6. Sprint close-out
After all verifications pass:
- Write a brief sprint-close summary to `argus/docs/sprints/synthesis-2026-04-26/SPRINT-SUMMARY.md` (one-pager: deliverables landed, sessions run, link to each close-out, link to each Tier 2 review, anything deferred to future)
- Mark sprint complete in argus's CLAUDE.md "Active Sprint" section

---

## Doc-Sync Coverage Map

| Sprint output | Within-sprint update | Post-sprint update | Where |
|---|---|---|---|
| RULE-051/052/053 | Session 1 | — | Section A |
| RULE-038 5th sub-bullet | Session 1 | — | Section A |
| Keystone Pre-Flight (impl + review templates) | Session 1 | — | Section A |
| close-out skill strengthening | Session 1 | — | Section A |
| Template extensions (Hybrid Mode + Between-Session Doc-Sync + scaffold ## Rules) | Session 2 | — | Section A |
| Evolution-notes README + 3 status headers | Session 2 | (verify in B6) | Section A + B |
| campaign-orchestration.md + impromptu-triage extension | Session 3 | — | Section A |
| operational-debrief.md | Session 4 | — | Section A |
| stage-flow.md + scoping-session-prompt.md + phase-2-validate.py | Session 5 | — | Section A |
| codebase-health-audit.md major expansion + sprint-planning cross-ref | Session 6 | — | Section A |
| Bootstrap-index.md routing entries | Sessions 3, 4, 5 | — | Section A |
| README count drift | — | Section B1 | After Session 6 |
| Optional README scripts/ comment | — | Section B2 | After Session 6 |
| VERSIONING.md current-version line | — | Section B3 (deferred) | (deferred to next strategic check-in) |
| evolution-notes README format consistency | Session 2 | Section B6 (verify) | After Session 6 |
| Cross-reference final sweep | — | Section B8 | After Session 6 |
| Argus submodule pointer | — | Section C1 | After all metarepo work |
| Argus boot-commit-logging DEF entry | — | Section C2 | After Session 4 (operational-debrief lands) |
| Argus CLAUDE.md ## Rules verification | Session 0 (optional) | Section C3 | If Session 0 skipped |
| Other-project doc-syncs (MuseFlow / Grove) | — | Section D1, D2, D3 | Operator's discretion |

---

## Estimated Time

- **Within-sprint updates** (Sections A — Sessions 0-6): ~7.5 hours total operator-attended (per session breakdown).
- **Post-sprint metarepo doc-sync** (Section B): ~15 minutes.
- **Post-sprint argus doc-sync** (Section C): ~10 minutes.
- **Other-project propagation** (Section D): ~5 minutes per project; operator's discretion.
- **Verification sweep** (Section E): ~10 minutes.

Total post-sprint doc-sync work: **~25–35 minutes** beyond Sessions 0-6.

---

## Doc-Sync Owner

- **Sections A:** Each session's implementer (Claude Code in Sessions 0-6).
- **Section B:** A short Claude Code doc-sync session, OR operator-direct.
- **Section C:** Operator-direct in the argus repo (commits aren't part of the metarepo synthesis).
- **Section D:** Operator-direct, per-project, when convenient.
- **Section E:** Operator-direct (the final verification is judgmental + cross-cutting).

If Section B is run as a Claude Code doc-sync session, it can be invoked via `templates/doc-sync-automation-prompt.md` (which Session 2's "Between-Session Doc-Sync" addition supplements). The prompt for that session is generated as part of Phase D's deliverables — it's a small "post-Session-6 doc-sync" prompt template.
